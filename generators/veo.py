"""
Veo 视频生成器模块
支持：短视频、视频延长（官方 SDK）、长视频拼接
"""

import os
import time
import subprocess
from pathlib import Path
from google.genai import types

from generators.client import get_client
from config import (
    VEO_MODELS, OUTPUT_FOLDER,
    POLL_MAX_WAIT, POLL_INTERVALS, SEGMENT_DURATION,
)

# 检查 OpenCV
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class VeoGenerator:
    """Veo 视频生成器"""

    # ----------------------------------------------------------
    # 内部工具方法
    # ----------------------------------------------------------

    @staticmethod
    def _resolve_model(model: str) -> str:
        """将简写模型名解析为完整 model_id"""
        return VEO_MODELS.get(model, model)

    @staticmethod
    def _poll_operation(client, operation, task: dict, label: str = 'Generating'):
        """通用轮询方法，消除重复代码"""
        waited = 0
        idx = 0
        while waited < POLL_MAX_WAIT:
            if operation.done is True:
                break
            interval = POLL_INTERVALS[min(idx, len(POLL_INTERVALS) - 1)]
            time.sleep(interval)
            waited += interval
            idx += 1
            try:
                operation = client.operations.get(operation)
                progress = min(30 + int(waited / POLL_MAX_WAIT * 60), 90)
                task['progress'] = progress
                task['message'] = f'{label}... ({waited}s)'
            except Exception as e:
                task['message'] = f'Status check failed: {e}'
        return operation, waited

    @staticmethod
    def _save_video(operation, output_path: str) -> bool:
        """从 operation 结果中提取并保存视频，成功返回 True"""
        if not (operation.response and operation.response.generated_videos):
            return False
        gen = operation.response.generated_videos[0]
        if not gen.video:
            return False
        video = gen.video
        if video.video_bytes:
            with open(output_path, 'wb') as f:
                f.write(video.video_bytes)
            return True
        if getattr(video, 'uri', None):
            import requests as _req
            proxies = {
                'http': os.getenv('HTTP_PROXY'),
                'https': os.getenv('HTTPS_PROXY'),
            }
            r = _req.get(video.uri, proxies=proxies, timeout=120)
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(r.content)
            return True
        return False

    # ----------------------------------------------------------
    # 短视频生成
    # ----------------------------------------------------------

    def generate(self, task: dict, prompt: str, model: str = 'veo3.1',
                 duration: int = 8, aspect_ratio: str = "16:9",
                 output_path: str = None, reference_image: str = None,
                 negative_prompt: str = None, enhance_prompt: bool = False):
        """生成单段短视频"""
        model_id = self._resolve_model(model)
        client = get_client()

        task['status'] = 'running'
        task['message'] = 'Sending request...'
        task['progress'] = 10

        source = types.GenerateVideosSource(prompt=prompt)
        config = types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=duration,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
            enhance_prompt=enhance_prompt,
        )

        if reference_image and os.path.exists(reference_image):
            try:
                source.image = types.Image.from_file(location=reference_image)
            except Exception as e:
                print(f"Failed to load reference image: {e}")

        task['message'] = 'Generating video...'
        task['progress'] = 20

        operation = client.models.generate_videos(
            model=model_id, source=source, config=config,
        )
        task['message'] = f'Operation created: {operation.name}'
        task['progress'] = 30

        operation, _ = self._poll_operation(client, operation, task, 'Generating')

        if operation.done is not True:
            raise RuntimeError("Generation timeout")
        if operation.error:
            raise RuntimeError(str(operation.error))

        task['message'] = 'Downloading video...'
        task['progress'] = 95

        if not self._save_video(operation, output_path):
            raise RuntimeError("No video data received")

        task['output_path'] = output_path
        task['status'] = 'completed'
        task['progress'] = 100
        task['message'] = 'Complete!'

    # ----------------------------------------------------------
    # 视频延长（官方 SDK）
    # ----------------------------------------------------------

    def generate_extend(self, task: dict, prompt: str, model: str = 'veo3.1',
                        duration: int = 8, aspect_ratio: str = "16:9",
                        output_path: str = None, video_path: str = None,
                        image_path: str = None,
                        negative_prompt: str = None, enhance_prompt: bool = False):
        """基于已有视频/图片延长生成"""
        model_id = self._resolve_model(model)
        client = get_client()

        task['status'] = 'running'
        task['message'] = 'Sending request...'
        task['progress'] = 10

        source = types.GenerateVideosSource(prompt=prompt)
        if video_path and os.path.exists(video_path):
            source.video = types.Video.from_file(location=video_path)
        elif image_path and os.path.exists(image_path):
            source.image = types.Image.from_file(location=image_path)

        config = types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=duration,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
            enhance_prompt=enhance_prompt,
        )

        task['message'] = 'Generating video extension...'
        task['progress'] = 20

        operation = client.models.generate_videos(
            model=model_id, source=source, config=config,
        )
        task['message'] = f'Operation created: {operation.name}'
        task['progress'] = 30

        operation, _ = self._poll_operation(client, operation, task, 'Extending')

        if operation.done is not True:
            raise RuntimeError("Generation timeout")
        if operation.error:
            raise RuntimeError(str(operation.error))

        task['message'] = 'Downloading video...'
        task['progress'] = 95

        if not self._save_video(operation, output_path):
            raise RuntimeError("No video data received")

        task['output_path'] = output_path
        task['status'] = 'completed'
        task['progress'] = 100
        task['message'] = 'Complete!'

    # ----------------------------------------------------------
    # 长视频拼接
    # ----------------------------------------------------------

    def generate_long(self, task: dict, prompt: str, model: str,
                      total_seconds: int, aspect_ratio: str,
                      output_path: str, reference_image: str = None,
                      negative_prompt: str = None, enhance_prompt: bool = False):
        """分段生成 + ffmpeg 拼接长视频"""
        model_id = self._resolve_model(model)
        client = get_client()
        num_segments = (total_seconds + SEGMENT_DURATION - 1) // SEGMENT_DURATION

        task['message'] = f'Long video: {num_segments} segments needed'
        task['progress'] = 5

        segment_files = []
        last_frame_path = None

        for i in range(num_segments):
            task['message'] = f'Generating segment {i+1}/{num_segments}...'
            task['progress'] = int(5 + (i / num_segments * 80))

            seg_prompt = prompt if i == 0 else \
                f"{prompt}. Continue from the previous frame, maintain exact same scene and motion."

            source = types.GenerateVideosSource(prompt=seg_prompt)
            config = types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=SEGMENT_DURATION,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                enhance_prompt=enhance_prompt,
            )

            # 设置参考图
            try:
                if i == 0 and reference_image and os.path.exists(reference_image):
                    source.image = types.Image.from_file(location=reference_image)
                elif i > 0 and last_frame_path and os.path.exists(last_frame_path):
                    source.image = types.Image.from_file(location=last_frame_path)
            except Exception as e:
                task['message'] = f'Segment {i+1}/{num_segments} (no image: {e})...'

            operation = client.models.generate_videos(
                model=model_id, source=source, config=config,
            )

            operation, _ = self._poll_operation(
                client, operation, task,
                f'Segment {i+1}/{num_segments}',
            )

            if operation.done is not True or not operation.response:
                raise RuntimeError(f"Segment {i+1} failed")

            # 保存分段
            segment_path = OUTPUT_FOLDER / f"{task['id']}_seg_{i:03d}.mp4"
            video = operation.response.generated_videos[0].video
            if not video.video_bytes:
                raise RuntimeError(f"Segment {i+1} no data")

            with open(segment_path, 'wb') as f:
                f.write(video.video_bytes)
            segment_files.append(str(segment_path))

            # 提取最后一帧
            if CV2_AVAILABLE:
                try:
                    cap = cv2.VideoCapture(str(segment_path))
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    if total_frames > 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
                        ret, frame = cap.read()
                        if ret:
                            last_frame_path = str(
                                OUTPUT_FOLDER / f"{task['id']}_last_frame_{i:03d}.jpg"
                            )
                            cv2.imwrite(last_frame_path, frame)
                    cap.release()
                except Exception as e:
                    task['message'] = f'Segment {i+1} done, frame extract failed: {e}'

        # 拼接
        task['message'] = 'Concatenating segments...'
        task['progress'] = 90

        concat_file = OUTPUT_FOLDER / f"{task['id']}_concat.txt"
        with open(concat_file, 'w') as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_file), '-c', 'copy', output_path,
        ], check=True, capture_output=True)

        # 清理临时文件
        for seg in segment_files:
            try:
                os.remove(seg)
            except OSError:
                pass
        try:
            os.remove(concat_file)
        except OSError:
            pass

        task['output_path'] = output_path
        task['status'] = 'completed'
        task['progress'] = 100
        task['message'] = 'Complete!'
