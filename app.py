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

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 注册路由蓝图
from routes import generate, gemini, tasks, proxy, narration

app.register_blueprint(generate.bp)
app.register_blueprint(gemini.bp)
app.register_blueprint(tasks.bp)
app.register_blueprint(proxy.bp)
app.register_blueprint(narration.bp)


# ------------------------------------------------------------------
# Templates API
# ------------------------------------------------------------------

import json
TEMPLATES_FILE = Path(__file__).parent / 'templates.json'


def _load_templates():
    if TEMPLATES_FILE.exists():
        with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
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
    print("=" * 50)
    print("  Veo Flow - AI Video & Image Generation")
    print("=" * 50)
    print(f"  Upload folder : {UPLOAD_FOLDER}")
    print(f"  Output folder : {OUTPUT_FOLDER}")
    print(f"  Open          : http://localhost:5000")
    print()

    if not os.getenv('GCP_PROJECT_ID'):
        print("  ⚠️  Warning: GCP_PROJECT_ID not set")
        print()

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
