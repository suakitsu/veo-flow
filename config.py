"""
Veo Studio - 配置管理模块
统一管理所有环境变量、路径、模型常量
"""

import os
import json
from pathlib import Path

# 路径定义
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'outputs'
TEMPLATE_FOLDER = BASE_DIR / 'templates'
CONFIG_FILE = BASE_DIR / 'config.json'

# Veo 模型 ID 映射
VEO_MODELS = {
    'veo2': 'veo-2.0-generate-001',
    'veo3': 'veo-3.0-generate-001',
    'veo3-fast': 'veo-3.0-fast-generate-001',
    'veo3.1': 'veo-3.1-generate-001',
    'veo3.1-fast': 'veo-3.1-fast-generate-001',
}

# Gemini 模型列表
GEMINI_MODELS = {
    # Gemini 2.5 (Stable GA)
    'gemini-2.5-pro': 'Gemini 2.5 Pro',
    'gemini-2.5-flash': 'Gemini 2.5 Flash',
    'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
    # Gemini 2.0
    'gemini-2.0-flash-001': 'Gemini 2.0 Flash',
    'gemini-2.0-flash-lite-001': 'Gemini 2.0 Flash Lite',
}

DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash'

# Gemini 风格提示词模板
STYLE_PROMPTS = {
    'cinematic': 'Generate a cinematic video prompt. Focus on dramatic lighting, camera movements (dolly, crane, tracking shots), shallow depth of field, film grain. Make it feel like a Hollywood movie scene.',
    'anime': 'Generate an anime-style video prompt. Describe it as a Japanese animation scene with vibrant colors, expressive characters, dynamic action lines, and cel-shaded look.',
    'documentary': 'Generate a documentary-style video prompt. Focus on natural lighting, steady camera work, realistic details, educational tone, nature or real-world subjects.',
    'commercial': 'Generate an advertising/commercial video prompt. Focus on product appeal, clean composition, modern aesthetics, upbeat energy, brand-friendly visuals.',
    'social': 'Generate a social media video prompt optimized for short-form content. Punchy, eye-catching, trendy transitions, vertical-friendly composition, viral potential.',
    'artistic': 'Generate an artistic/experimental video prompt. Focus on abstract visuals, unconventional compositions, painterly textures, surreal elements, creative expression.',
    'realistic': 'Generate a hyper-realistic video prompt. Focus on photorealistic details, natural physics, accurate lighting, real-world settings, no stylization.',
    'fantasy': 'Generate a fantasy video prompt. Include magical elements, otherworldly landscapes, mythical creatures, ethereal lighting, epic scale.',
}

# 轮询配置
POLL_MAX_WAIT = 600           # 最大等待 10 分钟
POLL_INTERVALS = [3, 10, 30, 60, 90]  # 指数退避间隔（秒）
SEGMENT_DURATION = 8          # 长视频每段时长（秒）

# 代理配置（运行时可变）
proxy_config = {
    'enabled': True,
    'address': os.getenv('HTTP_PROXY', 'http://127.0.0.1:7897'),
}

# API 配置（用于 API Key 模式，如 xiaomimimo）
api_config = {
    'api_key': '',
    'base_url': 'https://api.xiaomimimo.com-NO-DEFAULT', # 实际上默认留空由 SDK 处理
}


def init_env():
    """初始化环境变量：代理、凭证、项目 ID"""
    # 设置代理（必须在导入 google.genai 之前）
    os.environ['HTTP_PROXY'] = os.getenv('HTTP_PROXY', 'http://127.0.0.1:7897')
    os.environ['HTTPS_PROXY'] = os.getenv('HTTPS_PROXY', 'http://127.0.0.1:7897')

    # 从 config.json 读取凭证
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
            os.environ['GCP_PROJECT_ID'] = cfg.get('project_id', '')
            
            # 模式 A：服务号 JSON 文件
            cred_path = cfg.get('credentials', '')
            if cred_path and not os.path.isabs(cred_path):
                cred_path = str(BASE_DIR / cred_path)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cred_path
            
            # 模式 B：API Key 模式 (如 xiaomimimo)
            api_config['api_key'] = cfg.get('api_key', '')
            api_config['base_url'] = cfg.get('api_base_url', '')

    # 确保目录存在
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True)
