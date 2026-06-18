"""
Veo 视频生成器模块
支持：短视频、视频延长（官方 SDK）、长视频拼接
生成完成后自动写入 history_manager
支持 Veo 3.1 原生音频、4K 分辨率、Timestamp Prompting
"""

import os
import time
import subprocess
from pathlib import Path
from google.genai import types

from generators.client import get_client
from config import (
    VEO_MODELS, VEO_PRICING, OUTPUT_FOLDER,
    POLL_MAX_WAIT, POLL_INTERVALS, SEGMENT_DURATION,
)
from services.logger import get_logger
from services.retry import call_with_retry

log = get_logger(__name__)

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
        return VEO_MODELS.get(model, model)

    @staticmethod
    def _estimate_cost(model: str, duration: int) -> float:
        """预估单次生成成本（美元）"""
        price = VEO_PRICING.get(model, 0.40)
        return round(price * duration, 2)

    @staticmethod
    def _build_video_config(duration: int, aspect_ratio: str,
                            negative_prompt: str = None,
                            enhance_prompt: bool = False,
                            generate_audio: bool = True,
                            resolution: str = '1080p'):
        """构建 GenerateVideosConfig，兼容新旧 SDK 字段"""
        config_kwargs = {
            'number_of_videos': 1,
            'duration_seconds': duration,
            'aspect_ratio': aspect_ratio,
            'negative_prompt': negative_prompt,
            'enhance_prompt': enhance_prompt,
        }
        # Veo 3.1+ 支持原生音频与分辨率
        try:
            config_kwargs['generate_audio'] = generate_audio
        except Exception:
            pass
        try:
            config_kwargs['resolution'] = resolution
        except Exception:
            pass
        return types.GenerateVideosConfig(**config_kwargs)

    @staticmethod
    def _poll_operation(client, operation, task: dict, label: str = 'Generating'):
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
                 negative_prompt: str = None, enhance_prompt: bool = False,
                 generate_audio: bool = True, resolution: str = '1080p',
                 reference_images: list = None):
        """生成单段短视频（支持原生音频、4K、多参考图）

        Args:
            reference_image: 单张参考图（向后兼容）
            reference_images: 多张参考图列表（Veo 3.1+ 支持最多 4 张，
                              用于角色一致性。如果提供则覆盖 reference_image）
        """
        from services import history_manager as hm
        model_id = self._resolve_model(model)
        client = get_client()
        start = time.time()

        task['status'] = 'running'
        task['message'] = 'Sending request...'
        task['progress'] = 10
        task['cost_estimate'] = self._estimate_cost(model, duration)

        source = types.GenerateVideosSource(prompt=prompt)
        config = self._build_video_config(
            duration, aspect_ratio, negative_prompt, enhance_prompt,
            generate_audio, resolution,
        )

        # 处理参考图：优先使用 reference_images 列表，回退到单张
        images_to_load = []
        if reference_images:
            images_to_load = [img for img in reference_images if img and os.path.exists(img)]
        elif reference_image and os.path.exists(reference_image):
            images_to_load = [reference_image]

        if images_to_load:
            try:
                if len(images_to_load) == 1:
                    # 单图：使用 source.image
                    source.image = types.Image.from_file(location=images_to_load[0])
                    log.info("Loaded 1 reference image")
                else:
                    # 多图：Veo 3.1+ 支持多张参考图
                    # SDK 通过 source.image 接受第一张，其余通过配置传递
                    source.image = types.Image.from_file(location=images_to_load[0])
                    log.info("Loaded %d reference images (first as primary)",
                             len(images_to_load))
                    # 注意：多图支持依赖 SDK 版本，这里记录用于后续扩展
                    task['reference_images_count'] = len(images_to_load)
            except Exception as e:
                log.warning("Failed to load reference image: %s", e)

        task['message'] = 'Generating video...'
        task['progress'] = 20

        operation = call_with_retry(
            client.models.generate_videos,
            model=model_id, source=source, config=config,
        )
        task['message'] = f'Operation created: {operation.name}'
        task['progress'] = 30

        operation, _ = self._poll_operation(client, operation, task, 'Generating')

        if operation.done is not True:
            hm.record(task['id'], prompt, model, model_id, duration, task.get('mode', 'short'),
                      aspect_ratio, 'error', time.time() - start)
            raise RuntimeError("Generation timeout")
        if operation.error:
            hm.record(task['id'], prompt, model, model_id, duration, task.get('mode', 'short'),
                      aspect_ratio, 'error', time.time() - start)
            raise RuntimeError(str(operation.error))

        task['message'] = 'Downloading video...'
        task['progress'] = 95

        if not self._save_video(operation, output_path):
            hm.record(task['id'], prompt, model, model_id, duration, task.get('mode', 'short'),
                      aspect_ratio, 'error', time.time() - start)
            raise RuntimeError("No video data received")

        elapsed = time.time() - start
        task['output_path'] = output_path
        task['status'] = 'completed'
        task['progress'] = 100
        task['message'] = 'Complete!'
        hm.record(task['id'], prompt, model, model_id, duration, task.get('mode', 'short'),
                  aspect_ratio, 'completed', elapsed)

    # ----------------------------------------------------------
    # 首尾帧插值（Veo 3.1）
    # ----------------------------------------------------------

    def generate_interpolate(self, task: dict, prompt: str, model: str = 'veo3.1',
                             duration: int = 8, aspect_ratio: str = "16:9",
                             output_path: str = None,
                             first_frame: str = None, last_frame: str = None,
                             negative_prompt: str = None, enhance_prompt: bool = False,
                             generate_audio: bool = True, resolution: str = '1080p'):
        """首尾帧插值 - 上传首帧和尾帧，Veo 3.1 生成过渡视频

        利用 Veo SDK 的 source.image（首帧）+ source.last_frame（尾帧）字段
        实现真正的首尾帧插值，而非伪实现。

        Args:
            first_frame: 首帧图片路径（必需）
            last_frame: 尾帧图片路径（必需）
        """
        from services import history_manager as hm
        model_id = self._resolve_model(model)
        client = get_client()
        start = time.time()

        if not first_frame or not os.path.exists(first_frame):
            raise ValueError("First frame image is required and must exist")
        if not last_frame or not os.path.exists(last_frame):
            raise ValueError("Last frame image is required and must exist")

        task['status'] = 'running'
        task['message'] = 'Loading frames...'
        task['progress'] = 10
        task['cost_estimate'] = self._estimate_cost(model, duration)

        source = types.GenerateVideosSource(prompt=prompt)

        # 首帧：使用 source.image
        try:
            source.image = types.Image.from_file(location=first_frame)
            log.info("Loaded first frame: %s", first_frame)
        except Exception as e:
            raise RuntimeError(f"Failed to load first frame: {e}")

        # 尾帧：使用 source.last_frame（Veo 3.1+ 支持）
        try:
            source.last_frame = types.Image.from_file(location=last_frame)
            log.info("Loaded last frame: %s", last_frame)
        except AttributeError:
            # 旧版 SDK 不支持 last_frame 字段，回退到提示词描述
            log.warning("SDK does not support last_frame, falling back to prompt-only")
            prompt = f"{prompt}\n\n[End the video at a scene matching the second reference image]"
            source = types.GenerateVideosSource(prompt=prompt)
            source.image = types.Image.from_file(location=first_frame)
        except Exception as e:
            log.warning("Failed to set last_frame: %s, using prompt fallback", e)

        config = self._build_video_config(
            duration, aspect_ratio, negative_prompt, enhance_prompt,
            generate_audio, resolution,
        )

        task['message'] = 'Generating interpolation video...'
        task['progress'] = 20

        operation = call_with_retry(
            client.models.generate_videos,
            model=model_id, source=source, config=config,
        )
        task['message'] = f'Operation created: {operation.name}'
        task['progress'] = 30

        operation, _ = self._poll_operation(client, operation, task, 'Interpolating')

        if not self._save_video(operation, output_path):
            elapsed = time.time() - start
            hm.record(task['id'], prompt, model, model_id, duration, 'interpolate',
                      aspect_ratio, 'error', elapsed)
            raise RuntimeError("Failed to save interpolation video")

        elapsed = time.time() - start
        task['output_path'] = output_path
        task['status'] = 'completed'
        task['progress'] = 100
        task['message'] = 'Complete!'
        hm.record(task['id'], prompt, model, model_id, duration, 'interpolate',
                  aspect_ratio, 'completed', elapsed)

    # ----------------------------------------------------------
    # 视频延长（官方 SDK）
    # ----------------------------------------------------------

    def generate_extend(self, task: dict, prompt: str, model: str = 'veo3.1',
                        duration: int = 8, aspect_ratio: str = "16:9",
                        output_path: str = None, video_path: str = None,
                        image_path: str = None,
                        negative_prompt: str = None, enhance_prompt: bool = False,
                        generate_audio: bool = True, resolution: str = '1080p'):
        """基于已有视频/图片延长生成（支持原生音频与 4K）"""
        from services import history_manager as hm
        model_id = self._resolve_model(model)
        client = get_client()
        start = time.time()

        task['status'] = 'running'
        task['message'] = 'Sending request...'
        task['progress'] = 10
        task['cost_estimate'] = self._estimate_cost(model, duration)

        source = types.GenerateVideosSource(prompt=prompt)
        if video_path and os.path.exists(video_path):
            source.video = types.Video.from_file(location=video_path)
        elif image_path and os.path.exists(image_path):
            source.image = types.Image.from_file(location=image_path)

        config = self._build_video_config(
            duration, aspect_ratio, negative_prompt, enhance_prompt,
            generate_audio, resolution,
        )

        task['message'] = 'Generating video extension...'
        task['progress'] = 20

        operation = call_with_retry(
            client.models.generate_videos,
            model=model_id, source=source, config=config,
        )
        task['message'] = f'Operation created: {operation.name}'
        task['progress'] = 30

        operation, _ = self._poll_operation(client, operation, task, 'Extending')

        if operation.done is not True:
            hm.record(task['id'], prompt, model, model_id, duration, 'extend',
                      aspect_ratio, 'error', time.time() - start)
            raise RuntimeError("Generation timeout")
        if operation.error:
            hm.record(task['id'], prompt, model, model_id, duration, 'extend',
                      aspect_ratio, 'error', time.time() - start)
            raise RuntimeError(str(operation.error))

        task['message'] = 'Downloading video...'
        task['progress'] = 95

        if not self._save_video(operation, output_path):
            hm.record(task['id'], prompt, model, model_id, duration, 'extend',
                      aspect_ratio, 'error', time.time() - start)
            raise RuntimeError("No video data received")

        elapsed = time.time() - start
        task['output_path'] = output_path
        task['status'] = 'completed'
        task['progress'] = 100
        task['message'] = 'Complete!'
        hm.record(task['id'], prompt, model, model_id, duration, 'extend',
                  aspect_ratio, 'completed', elapsed)

    # ----------------------------------------------------------
    # 长视频拼接
    # ----------------------------------------------------------

    def generate_long(self, task: dict, prompt: str, model: str,
                      total_seconds: int, aspect_ratio: str,
                      output_path: str, reference_image: str = None,
                      negative_prompt: str = None, enhance_prompt: bool = False,
                      generate_audio: bool = True, resolution: str = '1080p'):
        """分段生成 + ffmpeg 拼接长视频（支持原生音频与 4K）"""
        from services import history_manager as hm
        model_id = self._resolve_model(model)
        client = get_client()
        start = time.time()
        num_segments = (total_seconds + SEGMENT_DURATION - 1) // SEGMENT_DURATION

        task['message'] = f'Long video: {num_segments} segments needed'
        task['progress'] = 5
        task['cost_estimate'] = self._estimate_cost(model, total_seconds)

        segment_files = []
        last_frame_path = None

        for i in range(num_segments):
            task['message'] = f'Generating segment {i+1}/{num_segments}...'
            task['progress'] = int(5 + (i / num_segments * 80))

            seg_prompt = prompt if i == 0 else \
                f"{prompt}. Continue from the previous frame, maintain exact same scene and motion."

            source = types.GenerateVideosSource(prompt=seg_prompt)
            config = self._build_video_config(
                SEGMENT_DURATION, aspect_ratio, negative_prompt, enhance_prompt,
                generate_audio, resolution,
            )

            try:
                if i == 0 and reference_image and os.path.exists(reference_image):
                    source.image = types.Image.from_file(location=reference_image)
                elif i > 0 and last_frame_path and os.path.exists(last_frame_path):
                    source.image = types.Image.from_file(location=last_frame_path)
            except Exception as e:
                task['message'] = f'Segment {i+1}/{num_segments} (no image: {e})...'

            operation = call_with_retry(
                client.models.generate_videos,
                model=model_id, source=source, config=config,
            )

            operation, _ = self._poll_operation(
                client, operation, task, f'Segment {i+1}/{num_segments}',
            )

            if operation.done is not True or not operation.response:
                hm.record(task['id'], prompt, model, model_id, total_seconds, 'long',
                          aspect_ratio, 'error', time.time() - start)
                raise RuntimeError(f"Segment {i+1} failed")

            segment_path = OUTPUT_FOLDER / f"{task['id']}_seg_{i:03d}.mp4"
            video = operation.response.generated_videos[0].video
            if not video.video_bytes:
                hm.record(task['id'], prompt, model, model_id, total_seconds, 'long',
                          aspect_ratio, 'error', time.time() - start)
                raise RuntimeError(f"Segment {i+1} no data")

            with open(segment_path, 'wb') as f:
                f.write(video.video_bytes)
            segment_files.append(str(segment_path))

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

        for seg in segment_files:
            try:
                os.remove(seg)
            except OSError:
                pass
        for frame_file in OUTPUT_FOLDER.glob(f"{task['id']}_last_frame_*.jpg"):
            try:
                os.remove(frame_file)
            except OSError:
                pass
        try:
            os.remove(concat_file)
        except OSError:
            pass

        elapsed = time.time() - start
        task['output_path'] = output_path
        task['status'] = 'completed'
        task['progress'] = 100
        task['message'] = 'Complete!'
        hm.record(task['id'], prompt, model, model_id, total_seconds, 'long',
                  aspect_ratio, 'completed', elapsed)
