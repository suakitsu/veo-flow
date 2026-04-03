"""
生成相关路由：视频生成、视频延长、模型列表
"""

from pathlib import Path
from flask import Blueprint, request, jsonify

from config import UPLOAD_FOLDER, OUTPUT_FOLDER
from generators.veo import VeoGenerator
from generators.imagen import ImagenGenerator
from services import task_manager as tm

bp = Blueprint('generate', __name__)


@bp.route('/api/models')
def get_models():
    """获取可用 Veo 模型列表"""
    return jsonify({
        'models': [
            {'id': 'veo3.1', 'name': 'Veo 3.1', 'max_duration': 8, 'resolutions': ['720', '1080']},
            {'id': 'veo3.1-fast', 'name': 'Veo 3.1 Fast', 'max_duration': 8, 'resolutions': ['720', '1080']},
            {'id': 'veo3', 'name': 'Veo 3', 'max_duration': 8, 'resolutions': ['720', '1080']},
            {'id': 'veo3-fast', 'name': 'Veo 3 Fast', 'max_duration': 8, 'resolutions': ['720', '1080']},
            {'id': 'veo2', 'name': 'Veo 2', 'max_duration': 8, 'resolutions': ['720']},
        ]
    })


@bp.route('/api/generate', methods=['POST'])
def generate_video():
    """生成视频/图像任务"""
    try:
        user_ip = request.remote_addr
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

        if not prompt:
            return jsonify({'error': 'Please enter a prompt'}), 400

        # 保存参考图
        image_path = None
        if 'image' in files and files['image'].filename:
            image_file = files['image']
            image_ext = Path(image_file.filename).suffix
            # 先用临时 id 再改
            import uuid
            tmp_id = str(uuid.uuid4())
            image_path = UPLOAD_FOLDER / f"{tmp_id}_ref{image_ext}"
            image_file.save(image_path)

        output_path = OUTPUT_FOLDER / "placeholder.mp4"  # 先占位

        if mode == 'image':
            output_path = OUTPUT_FOLDER / "placeholder.png"
            task = tm.create_task(mode, prompt, model, ratio, str(output_path))
            output_path = OUTPUT_FOLDER / f"{task['id']}.png"
            task['output_path'] = str(output_path)
            tm.lock_user(user_ip, task['id'])

            image_ratio = ratio if ratio in ('16:9', '9:16', '1:1') else '16:9'
            gen = ImagenGenerator()
            tm.run_in_background(
                gen.generate,
                (task, prompt, model, image_ratio, str(output_path),
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
                 negative_prompt or None, enhance_prompt),
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
                 negative_prompt or None, enhance_prompt),
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
        user_ip = request.remote_addr
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

        if not prompt:
            return jsonify({'error': 'Please enter a prompt'}), 400

        # 保存上传文件
        video_path = None
        image_path = None

        if 'video' in files and files['video'].filename:
            vf = files['video']
            ext = Path(vf.filename).suffix
            import uuid
            tmp = str(uuid.uuid4())
            video_path = UPLOAD_FOLDER / f"{tmp}_source_video{ext}"
            vf.save(video_path)
        elif 'last_frame' in files and files['last_frame'].filename:
            imgf = files['last_frame']
            ext = Path(imgf.filename).suffix
            import uuid
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
             negative_prompt or None, enhance_prompt),
            user_ip, task['id'],
        )

        return jsonify({
            'success': True,
            'task_id': task['id'],
            'message': 'Task created',
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
