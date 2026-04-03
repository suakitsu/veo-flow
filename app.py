#!/usr/bin/env python3
"""
Veo Flow - AI Video & Image Generation
Application entry point
"""

import os

# 初始化环境（必须最先执行，在 google.genai 导入之前）
from config import init_env, UPLOAD_FOLDER, OUTPUT_FOLDER
init_env()

# 创建 Flask 应用
from flask import Flask, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 注册路由蓝图
from routes import generate, gemini, tasks, proxy

app.register_blueprint(generate.bp)
app.register_blueprint(gemini.bp)
app.register_blueprint(tasks.bp)
app.register_blueprint(proxy.bp)


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
