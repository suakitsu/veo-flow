"""
任务状态 & 文件下载路由
支持 SSE 实时进度推送
"""

import os
import json
import time
from flask import Blueprint, jsonify, send_file, Response, stream_with_context

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


@bp.route('/api/task/<task_id>/stream')
def stream_task_status(task_id):
    """SSE 端点：实时推送任务进度，任务完成后自动关闭流

    前端用法：
      const es = new EventSource('/api/task/<id>/stream');
      es.onmessage = (e) => {
          const data = JSON.parse(e.data);
          updateProgress(data.progress, data.message);
          if (data.status === 'completed' || data.status === 'error') es.close();
      };
    """
    def generate():
        last_progress = -1
        last_message = ''
        idle_count = 0

        while True:
            task = tm.get_task(task_id)
            if not task:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break

            # 只在状态变化时推送
            current_progress = task.get('progress', 0)
            current_message = task.get('message', '')
            current_status = task.get('status', 'pending')

            if current_progress != last_progress or current_message != last_message:
                payload = {
                    'id': task_id,
                    'status': current_status,
                    'progress': current_progress,
                    'message': current_message,
                    'output_url': (
                        f'/api/download/{task_id}'
                        if current_status == 'completed'
                        and os.path.exists(task.get('output_path', ''))
                        else None
                    ),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                last_progress = current_progress
                last_message = current_message
                idle_count = 0
            else:
                idle_count += 1

            # 终止条件
            if current_status in ('completed', 'error', 'interrupted'):
                break

            # 超时保护（30 分钟无变化则断开）
            if idle_count > 1800:
                yield f"data: {json.dumps({'error': 'Timeout'})}\n\n"
                break

            time.sleep(1)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


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
