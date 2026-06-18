#!/usr/bin/env python3
"""
Veo Flow - AI Video & Image Generation
Application entry point — thin router layer
"""

import os
from pathlib import Path

# 初始化环境（必须最先执行，在 google.genai 导入之前）
from config import init_env, UPLOAD_FOLDER, OUTPUT_FOLDER
init_env()

# 初始化日志（在 Flask 之前，确保所有模块可用）
from services.logger import setup_logging
setup_logging()

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# CORS 白名单（通过环境变量配置，逗号分隔；默认仅允许本地）
_cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')
CORS(app, origins=[o.strip() for o in _cors_origins.split(',') if o.strip()])

# 注册路由蓝图
from routes import generate, gemini, tasks, proxy, narration, nano_banana, docs

app.register_blueprint(generate.bp)
app.register_blueprint(gemini.bp)
app.register_blueprint(tasks.bp)
app.register_blueprint(proxy.bp)
app.register_blueprint(narration.bp)
app.register_blueprint(nano_banana.bp)
app.register_blueprint(docs.bp)

# 启动文件清理后台服务
from services.cleanup import start_cleanup_service
start_cleanup_service()

# 注册 API 鉴权中间件（通过 API_KEY 环境变量启用）
from services.auth import auth_middleware
app.before_request(auth_middleware)


# ------------------------------------------------------------------
# Templates API
# ------------------------------------------------------------------

import json
TEMPLATES_FILE = Path(__file__).parent / 'templates.json'


def _load_templates():
    if TEMPLATES_FILE.exists():
        with open(TEMPLATES_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return {"categories": []}


@app.route('/api/templates')
def get_templates():
    return jsonify(_load_templates())


@app.route('/api/templates/render', methods=['POST'])
def render_template_api():
    import re
    data = request.json or {}
    result = data.get('template', '')
    variables = data.get('variables', {})
    for key, value in variables.items():
        result = result.replace('{' + key + '}', value)
    remaining = re.findall(r'\{(\w+)\}', result)
    return jsonify({'prompt': result, 'remaining_variables': remaining,
                    'complete': len(remaining) == 0})


# ------------------------------------------------------------------
# History / Stats API
# ------------------------------------------------------------------

from services import history_manager as hm


@app.route('/api/history')
def get_history():
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    return jsonify(hm.get_history(limit, offset))


@app.route('/api/history/stats')
def get_stats():
    return jsonify(hm.get_stats())


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    hm.clear()
    return jsonify({'success': True})


@app.route('/api/history/thumbnail/<task_id>')
def get_thumbnail(task_id):
    """生成历史记录的缩略图

    - 图片：直接返回缩略图
    - 视频：用 ffmpeg 抽取第 1 秒作为缩略图
    """
    import os
    import subprocess
    import tempfile
    from flask import send_file, abort
    from imageio_ffmpeg import get_ffmpeg_exe

    # 从 history 中查找记录
    history = hm._load()
    entry = next((h for h in history if h['id'] == task_id), None)
    if not entry or not entry.get('output_path'):
        abort(404)

    output_path = entry['output_path']
    if not os.path.exists(output_path):
        abort(404)

    # 图片直接返回
    if output_path.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return send_file(output_path, mimetype='image/png')

    # 视频抽取缩略图
    thumb_dir = os.path.join(tempfile.gettempdir(), 'veo_thumbs')
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, f'{task_id}_thumb.jpg')

    if not os.path.exists(thumb_path):
        try:
            subprocess.run([
                get_ffmpeg_exe(), '-y', '-i', output_path,
                '-ss', '00:00:01', '-vframes', '1',
                '-vf', 'scale=320:-1',
                thumb_path,
            ], capture_output=True, timeout=10)
        except Exception:
            abort(500)

    if os.path.exists(thumb_path):
        return send_file(thumb_path, mimetype='image/jpeg')
    abort(404)


# ------------------------------------------------------------------
# Main page
# ------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == '__main__':
    import logging
    startup_log = logging.getLogger(__name__)
    startup_log.info("=" * 50)
    startup_log.info("  Veo Flow - AI Video & Image Generation")
    startup_log.info("=" * 50)
    startup_log.info("  Upload folder : %s", UPLOAD_FOLDER)
    startup_log.info("  Output folder : %s", OUTPUT_FOLDER)
    startup_log.info("  Open          : http://localhost:5000")

    if not os.getenv('GCP_PROJECT_ID'):
        startup_log.warning("  GCP_PROJECT_ID not set")

    # debug 模式由环境变量控制（生产环境必须为 false）
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=5000, debug=debug_mode, use_reloader=False)
