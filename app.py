#!/usr/bin/env python3
"""
Veo Flow - AI Video & Image Generation
Application entry point
"""

import os
import json
from pathlib import Path
from datetime import datetime

# 初始化环境（必须最先执行，在 google.genai 导入之前）
from config import init_env, UPLOAD_FOLDER, OUTPUT_FOLDER
init_env()

# 创建 Flask 应用
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 数据文件
HISTORY_FILE = Path(__file__).parent / 'history.json'
TEMPLATES_FILE = Path(__file__).parent / 'templates.json'

# 加载模板
def load_templates():
    if TEMPLATES_FILE.exists():
        with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"categories": []}

# 加载历史
def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"history": [], "total_cost": 0, "total_generations": 0}

# 保存历史
def save_history(data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 注册路由蓝图
from routes import generate, gemini, tasks, proxy, narration

app.register_blueprint(generate.bp)
app.register_blueprint(gemini.bp)
app.register_blueprint(tasks.bp)
app.register_blueprint(proxy.bp)
app.register_blueprint(narration.bp)

# Templates API
@app.route('/api/templates')
def get_templates():
    return jsonify(load_templates())

@app.route('/api/templates/<id>')
def get_template(id):
    templates = load_templates()["templates"]
    t = next((x for x in templates if x["id"] == id), None)
    return jsonify(t or {"error": "Not found"})

# History API
@app.route('/api/history')
def get_history():
    data = load_history()
    return jsonify(data)

@app.route('/api/history/stats')
def get_stats():
    data = load_history()
    history = data.get("history", [])
    completed = [h for h in history if h.get("status") == "completed"]
    return jsonify({
        "total_cost": data.get("total_cost", 0),
        "total_generations": data.get("total_generations", 0),
        "success_rate": round(len(completed) / len(history) * 100, 1) if history else 0,
        "avg_time": round(sum(h.get("elapsed", 0) for h in completed) / len(completed), 1) if completed else 0
    })

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    save_history({"history": [], "total_cost": 0, "total_generations": 0})
    return jsonify({"success": True})

@app.route('/')
def index():
    """返回前端页面"""
    return render_template('index.html')


# 启动
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
