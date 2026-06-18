"""
生成相关路由：视频生成、视频延长、模型列表、批量生成(storyboard)
"""

import os
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file

from config import UPLOAD_FOLDER, OUTPUT_FOLDER, IMAGEN_PRICING
from generators.veo import VeoGenerator
from generators.imagen import ImagenGenerator
from services import task_manager as tm
from services.request_utils import get_client_ip

bp = Blueprint('generate', __name__)


@bp.route('/api/models')
def get_models():
    """获取可用 Veo / Imagen 模型列表"""
    return jsonify({
        'veo_models': [
            {'id': 'veo3.1', 'name': 'Veo 3.1', 'max_duration': 8,
             'resolutions': ['720p', '1080p', '4K'], 'audio': True, 'price_per_sec': 0.40},
            {'id': 'veo3.1-fast', 'name': 'Veo 3.1 Fast', 'max_duration': 8,
             'resolutions': ['720p', '1080p'], 'audio': True, 'price_per_sec': 0.15},
            {'id': 'veo3.1-lite', 'name': 'Veo 3.1 Lite', 'max_duration': 8,
             'resolutions': ['720p', '1080p'], 'audio': True, 'price_per_sec': 0.05},
            {'id': 'veo3', 'name': 'Veo 3', 'max_duration': 8,
             'resolutions': ['720p', '1080p'], 'audio': True, 'price_per_sec': 0.40},
            {'id': 'veo3-fast', 'name': 'Veo 3 Fast', 'max_duration': 8,
             'resolutions': ['720p', '1080p'], 'audio': True, 'price_per_sec': 0.20},
            {'id': 'veo2', 'name': 'Veo 2', 'max_duration': 8,
             'resolutions': ['720p'], 'audio': False, 'price_per_sec': 0.50},
        ],
        'imagen_models': [
            {'id': k, 'name': v, 'price_per_image': IMAGEN_PRICING.get(k, 0.04)}
            for k, v in [
                ('imagen4-ultra', 'Imagen 4 Ultra'),
                ('imagen4', 'Imagen 4 Standard'),
                ('imagen4-fast', 'Imagen 4 Fast'),
                ('imagen3', 'Imagen 3'),
                ('imagen3-fast', 'Imagen 3 Fast'),
            ]
        ],
    })


@bp.route('/api/generate', methods=['POST'])
def generate_video():
    """生成视频/图像任务"""
    try:
        user_ip = get_client_ip()
        locked, locked_id = tm.check_user_lock(user_ip)
        if locked:
            task = tm.get_task(locked_id)
            return jsonify({
                'error': 'You have a task in progress. Please wait or check status.',
                'task_id': locked_id,
                'status': task['status'] if task else 'unknown',
            }), 429

        data = request.form
        files = request.files

        mode = data.get('mode', 'short')
        prompt = data.get('prompt', '').strip()
        negative_prompt = data.get('negative_prompt', '').strip()
        enhance_prompt = data.get('enhance_prompt') == 'true'
        model = data.get('model', 'veo3.1')
        ratio = data.get('ratio', '16:9')
        # Veo 3.1+ 新增参数
        generate_audio = data.get('generate_audio', 'true') == 'true'
        resolution = data.get('resolution', '1080p')

        if not prompt:
            return jsonify({'error': 'Please enter a prompt'}), 400

        # 保存参考图（支持多张，Veo 3.1 最多 4 张用于角色一致性）
        image_paths = []
        image_files = files.getlist('image') if hasattr(files, 'getlist') else [files.get('image')] if 'image' in files else []
        for img_file in image_files:
            if img_file and img_file.filename:
                image_ext = Path(img_file.filename).suffix
                tmp_id = str(uuid.uuid4())
                img_path = UPLOAD_FOLDER / f"{tmp_id}_ref{image_ext}"
                img_file.save(img_path)
                image_paths.append(str(img_path))

        # 兼容：单图模式取第一张
        image_path = image_paths[0] if image_paths else None

        if mode == 'image':
            image_model = data.get('image_model', 'imagen4-fast')
            task = tm.create_task(mode, prompt, image_model, ratio, '')
            output_path = OUTPUT_FOLDER / f"{task['id']}.png"
            task['output_path'] = str(output_path)
            tm.lock_user(user_ip, task['id'])

            image_ratio = ratio if ratio in ('16:9', '9:16', '1:1') else '16:9'
            gen = ImagenGenerator()
            tm.run_in_background(
                gen.generate,
                (task, prompt, image_model, image_ratio, str(output_path),
                 negative_prompt or None, enhance_prompt),
                user_ip, task['id'],
            )

        elif mode == 'long':
            total_seconds = int(data.get('total_seconds', 16))
            task = tm.create_task(mode, prompt, model, ratio, '', total_seconds=total_seconds)
            output_path = OUTPUT_FOLDER / f"{task['id']}.mp4"
            task['output_path'] = str(output_path)
            tm.lock_user(user_ip, task['id'])

            gen = VeoGenerator()
            tm.run_in_background(
                gen.generate_long,
                (task, prompt, model, total_seconds, ratio, str(output_path),
                 str(image_path) if image_path else None,
                 negative_prompt or None, enhance_prompt,
                 generate_audio, resolution),
                user_ip, task['id'],
            )

        else:
            # 短视频
            duration = int(data.get('duration', 8))
            task = tm.create_task(mode, prompt, model, ratio, '', duration=duration)
            output_path = OUTPUT_FOLDER / f"{task['id']}.mp4"
            task['output_path'] = str(output_path)
            tm.lock_user(user_ip, task['id'])

            gen = VeoGenerator()
            tm.run_in_background(
                gen.generate,
                (task, prompt, model, duration, ratio, str(output_path),
                 str(image_path) if image_path else None,
                 negative_prompt or None, enhance_prompt,
                 generate_audio, resolution,
                 image_paths if len(image_paths) > 1 else None),
                user_ip, task['id'],
            )

        return jsonify({
            'success': True,
            'task_id': task['id'],
            'message': 'Task created',
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/extend', methods=['POST'])
def extend_video():
    """延长视频任务"""
    try:
        user_ip = get_client_ip()
        locked, locked_id = tm.check_user_lock(user_ip)
        if locked:
            return jsonify({
                'error': 'You have a task in progress.',
                'task_id': locked_id,
            }), 429

        data = request.form
        files = request.files

        prompt = data.get('prompt', '').strip()
        negative_prompt = data.get('negative_prompt', '').strip()
        enhance_prompt = data.get('enhance_prompt') == 'true'
        model = data.get('model', 'veo3.1')
        ratio = data.get('ratio', '16:9')
        duration = int(data.get('duration', 8))
        generate_audio = data.get('generate_audio', 'true') == 'true'
        resolution = data.get('resolution', '1080p')

        if not prompt:
            return jsonify({'error': 'Please enter a prompt'}), 400

        video_path = None
        image_path = None

        if 'video' in files and files['video'].filename:
            vf = files['video']
            ext = Path(vf.filename).suffix
            tmp = str(uuid.uuid4())
            video_path = UPLOAD_FOLDER / f"{tmp}_source_video{ext}"
            vf.save(video_path)
        elif 'last_frame' in files and files['last_frame'].filename:
            imgf = files['last_frame']
            ext = Path(imgf.filename).suffix
            tmp = str(uuid.uuid4())
            image_path = UPLOAD_FOLDER / f"{tmp}_source_frame{ext}"
            imgf.save(image_path)
        else:
            return jsonify({'error': 'Source video or last frame is required'}), 400

        task = tm.create_task('extend', prompt, model, ratio, '')
        output_path = OUTPUT_FOLDER / f"{task['id']}_extended.mp4"
        task['output_path'] = str(output_path)
        tm.lock_user(user_ip, task['id'])

        gen = VeoGenerator()
        tm.run_in_background(
            gen.generate_extend,
            (task, prompt, model, duration, ratio, str(output_path),
             str(video_path) if video_path else None,
             str(image_path) if image_path else None,
             negative_prompt or None, enhance_prompt,
             generate_audio, resolution),
            user_ip, task['id'],
        )

        return jsonify({
            'success': True,
            'task_id': task['id'],
            'message': 'Task created',
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ------------------------------------------------------------------
# First-Last Frame Interpolation (Veo 3.1)
# ------------------------------------------------------------------

@bp.route('/api/interpolate', methods=['POST'])
def interpolate_frames():
    """首尾帧插值 - 上传首帧和尾帧图片，Veo 3.1 生成过渡视频

    表单参数：
      - prompt: 描述过渡效果的提示词
      - first_frame: 首帧图片（必需）
      - last_frame: 尾帧图片（必需）
      - model: 模型（默认 veo3.1）
      - duration: 时长（4/6/8 秒）
      - ratio: 宽高比
      - generate_audio: 是否生成音频
      - resolution: 分辨率
    """
    from pathlib import Path
    import uuid

    data = request.form
    files = request.files

    prompt = data.get('prompt', 'Smooth transition between the two frames').strip()
    first_frame = files.get('first_frame')
    last_frame = files.get('last_frame')

    if not first_frame or not first_frame.filename:
        return jsonify({'error': 'First frame image is required'}), 400
    if not last_frame or not last_frame.filename:
        return jsonify({'error': 'Last frame image is required'}), 400

    model = data.get('model', 'veo3.1')
    duration = int(data.get('duration', 8))
    ratio = data.get('ratio', '16:9')
    generate_audio = data.get('generate_audio', 'true') == 'true'
    resolution = data.get('resolution', '1080p')

    user_ip = get_client_ip()
    locked, _ = tm.check_user_lock(user_ip)
    if locked:
        return jsonify({'error': 'Another task is running. Please wait.'}), 429

    # 保存首尾帧
    tmp_id = str(uuid.uuid4())
    first_ext = Path(first_frame.filename).suffix or '.png'
    last_ext = Path(last_frame.filename).suffix or '.png'
    first_path = UPLOAD_FOLDER / f"{tmp_id}_first{first_ext}"
    last_path = UPLOAD_FOLDER / f"{tmp_id}_last{last_ext}"
    first_frame.save(first_path)
    last_frame.save(last_path)

    task = tm.create_task('interpolate', prompt, model, ratio, '')
    output_path = OUTPUT_FOLDER / f"{task['id']}_interp.mp4"
    task['output_path'] = str(output_path)
    tm.lock_user(user_ip, task['id'])

    # 使用真正的首尾帧插值（Veo SDK source.last_frame）
    gen = VeoGenerator()
    tm.run_in_background(
        gen.generate_interpolate,
        (task, prompt, model, duration, ratio, str(output_path),
         str(first_path), str(last_path),
         None, False, generate_audio, resolution),
        user_ip, task['id'],
    )

    return jsonify({
        'success': True,
        'task_id': task['id'],
        'message': 'Interpolation task created',
    })


# ------------------------------------------------------------------
# Batch Generation (Storyboard)
# ------------------------------------------------------------------

@bp.route('/api/batch', methods=['POST'])
def batch_generate():
    """批量生成（分镜脚本） - 接受 shots 列表，逐段生成，可选拼接"""
    import threading
    data = request.json or {}
    shots = data.get('shots', [])
    batch_name = data.get('name', f'batch_{int(datetime.now().timestamp())}')
    concat_output = data.get('concat', False)

    if not shots:
        return jsonify({'error': 'No shots provided'}), 400
    if len(shots) > 20:
        return jsonify({'error': 'Max 20 shots per batch'}), 400

    # validate prompts
    for i, s in enumerate(shots):
        if not s.get('prompt', '').strip():
            return jsonify({'error': f'Shot {i+1} has no prompt'}), 400

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    batch_task = {
        'id': batch_id,
        'name': batch_name,
        'mode': 'batch',
        'prompt': batch_name,
        'status': 'running',
        'progress': 0,
        'message': 'Starting batch...',
        'total_shots': len(shots),
        'completed_shots': 0,
        'shots': [],
        'concat': concat_output,
        'output_path': None,
        'created_at': datetime.now().isoformat(),
    }
    tm._tasks[batch_id] = batch_task  # register directly

    def run_batch():
        generator = VeoGenerator()
        shot_files = []

        try:
            for i, shot in enumerate(shots):
                shot_task_id = f"{batch_id}_shot_{i:03d}"
                prompt = shot.get('prompt', '')
                model = shot.get('model', 'veo3.1')
                duration = int(shot.get('duration', 8))
                ratio = shot.get('ratio', '16:9')
                out_path = str(OUTPUT_FOLDER / f"{shot_task_id}.mp4")

                shot_info = {
                    'index': i,
                    'prompt': prompt,
                    'model': model,
                    'duration': duration,
                    'status': 'running',
                    'output_path': None,
                }
                batch_task['shots'].append(shot_info)
                batch_task['current_shot'] = i + 1
                batch_task['message'] = f'Shot {i+1}/{len(shots)}: {prompt[:40]}...'
                batch_task['progress'] = int(i / len(shots) * 90)

                sub_task = {
                    'id': shot_task_id,
                    'mode': 'short',
                    'prompt': prompt,
                    'model': model,
                    'ratio': ratio,
                    'status': 'pending',
                    'progress': 0,
                    'message': 'Waiting...',
                    'output_path': out_path,
                    'created_at': datetime.now().isoformat(),
                }
                tm._tasks[shot_task_id] = sub_task

                try:
                    generator.generate(sub_task, prompt, model, duration, ratio, out_path)
                    shot_info['status'] = 'completed'
                    shot_info['output_path'] = out_path
                    shot_files.append(out_path)
                except Exception as e:
                    shot_info['status'] = 'error'
                    shot_info['error'] = str(e)

                batch_task['completed_shots'] = i + 1

            # 可选拼接
            if concat_output and len(shot_files) > 1:
                batch_task['message'] = 'Concatenating shots...'
                try:
                    concat_file = OUTPUT_FOLDER / f"{batch_id}_concat.txt"
                    with open(concat_file, 'w') as f:
                        for seg in shot_files:
                            f.write(f"file '{seg}'\n")
                    final_output = str(OUTPUT_FOLDER / f"{batch_id}_final.mp4")
                    subprocess.run([
                        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                        '-i', str(concat_file), '-c', 'copy', final_output,
                    ], check=True, capture_output=True)
                    batch_task['output_path'] = final_output
                    try:
                        os.remove(concat_file)
                    except OSError:
                        pass
                except Exception as e:
                    batch_task['concat_error'] = str(e)
            elif len(shot_files) == 1:
                batch_task['output_path'] = shot_files[0]

        except Exception as e:
            batch_task['error'] = str(e)
        finally:
            batch_task['status'] = 'completed'
            batch_task['progress'] = 100
            batch_task['message'] = f'Done. {batch_task["completed_shots"]}/{len(shots)} shots completed.'

    threading.Thread(target=run_batch, daemon=True).start()

    return jsonify({
        'success': True,
        'batch_id': batch_id,
        'total_shots': len(shots),
        'message': 'Batch started',
    })


@bp.route('/api/batch/<batch_id>')
def get_batch_status(batch_id):
    """查询批量任务状态"""
    task = tm.get_task(batch_id)
    if not task:
        return jsonify({'error': 'Batch not found'}), 404
    return jsonify(task)


@bp.route('/api/upload', methods=['POST'])
def upload_file():
    """通用文件上传接口（给 Narration manual 模式用）"""
    files = request.files
    if 'image' not in files or not files['image'].filename:
        return jsonify({'error': 'No file uploaded'}), 400
    f = files['image']
    ext = Path(f.filename).suffix
    filename = f"upload_{uuid.uuid4().hex[:8]}{ext}"
    save_path = UPLOAD_FOLDER / filename
    f.save(save_path)
    return jsonify({
        'filename': filename,
        'url': f'/api/uploads/{filename}',
    })


@bp.route('/api/uploads/<filename>')
def serve_upload(filename):
    """提供已上传文件的静态访问"""
    path = UPLOAD_FOLDER / filename
    if not path.exists():
        return jsonify({'error': 'File not found'}), 404
    return send_file(str(path))
