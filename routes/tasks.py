"""
任务状态 & 文件下载路由
"""

import os
from flask import Blueprint, jsonify, send_file

from services import task_manager as tm

bp = Blueprint('tasks', __name__)


@bp.route('/api/task/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    task = tm.get_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    return jsonify({
        'id': task['id'],
        'status': task['status'],
        'progress': task['progress'],
        'message': task['message'],
        'output_url': (
            f'/api/download/{task_id}'
            if task['status'] == 'completed' and os.path.exists(task.get('output_path', ''))
            else None
        ),
    })


@bp.route('/api/download/<task_id>')
def download_file(task_id):
    """下载生成的视频或图片"""
    task = tm.get_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    output_path = task.get('output_path', '')
    if not output_path or not os.path.exists(output_path):
        return jsonify({'error': 'File not found'}), 404

    is_image = task.get('mode') == 'image'
    filename = f"imagen_{task_id}.png" if is_image else f"veo_{task_id}.mp4"
    mimetype = 'image/png' if is_image else 'video/mp4'

    return send_file(
        output_path,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype,
    )


@bp.route('/api/tasks')
def list_tasks():
    """列出所有任务"""
    all_tasks = tm.list_all_tasks()
    return jsonify({
        'tasks': [
            {
                'id': t['id'],
                'mode': t.get('mode', 'unknown'),
                'prompt': (t['prompt'][:50] + '...') if len(t.get('prompt', '')) > 50 else t.get('prompt', ''),
                'status': t['status'],
                'progress': t['progress'],
                'created_at': t.get('created_at', ''),
            }
            for t in all_tasks
        ]
    })
