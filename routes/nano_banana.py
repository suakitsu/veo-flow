"""
Nano Banana 路由 - Gemini 原生图像生成与对话式编辑
支持：单次生成、参考图编辑、多轮对话编辑
"""

import os
import uuid
from flask import Blueprint, request, jsonify
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, GEMINI_IMAGE_MODELS
from generators.nano_banana import NanoBananaGenerator
from services import task_manager as tm
from services.request_utils import get_client_ip
from services.file_security import save_upload_safely

bp = Blueprint('nano_banana', __name__)


@bp.route('/api/nano-banana/models')
def get_models():
    """获取可用的 Nano Banana 模型列表"""
    return jsonify({
        'models': [
            {'id': k, 'name': v, 'type': 'nano-banana'}
            for k, v in GEMINI_IMAGE_MODELS.items()
        ],
    })


@bp.route('/api/nano-banana/generate', methods=['POST'])
def generate_image():
    """
    Nano Banana 图像生成 / 编辑

    表单参数：
      - prompt: 必填，生成/编辑指令
      - model: 模型别名（默认 nano-banana-2）
      - image: 参考图片（可选，用于编辑模式）
      - conversation: JSON 字符串，对话历史（可选，多轮编辑）

    返回：task_id，前端轮询 /api/task/<id> 获取进度
    """
    from pathlib import Path

    data = request.form
    files = request.files

    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    model = data.get('model', 'nano-banana-2')

    # 处理参考图（使用安全工具防路径穿越+类型校验）
    ref_image_path = None
    if 'image' in files and files['image'].filename:
        saved_path, err = save_upload_safely(files['image'], prefix='nb_ref_')
        if saved_path is None:
            return jsonify({'error': f'Invalid image upload: {err}'}), 400
        ref_image_path = str(saved_path)

    # 处理对话历史
    conversation_history = None
    conv_str = data.get('conversation')
    if conv_str:
        import json
        try:
            conversation_history = json.loads(conv_str)
        except json.JSONDecodeError:
            pass

    # 创建任务
    user_ip = get_client_ip()
    if tm.is_locked(user_ip):
        return jsonify({'error': 'Another task is running. Please wait.'}), 429

    task = tm.create_task('nano-banana', prompt, model, '1:1', '')
    output_path = OUTPUT_FOLDER / f"{task['id']}.png"
    task['output_path'] = str(output_path)
    tm.lock_user(user_ip, task['id'])

    gen = NanoBananaGenerator()
    tm.run_in_background(
        gen.generate,
        (task, prompt, model, str(output_path),
         ref_image_path, conversation_history),
        user_ip, task['id'],
    )

    return jsonify({
        'task_id': task['id'],
        'status': 'pending',
        'message': 'Nano Banana generation started',
    })
