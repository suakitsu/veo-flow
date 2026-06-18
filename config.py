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

# Veo 模型 ID 映射（含 Veo 3.1 Lite 新档位）
VEO_MODELS = {
    'veo2': 'veo-2.0-generate-001',
    'veo3': 'veo-3.0-generate-001',
    'veo3-fast': 'veo-3.0-fast-generate-001',
    'veo3.1': 'veo-3.1-generate-001',
    'veo3.1-fast': 'veo-3.1-fast-generate-001',
    'veo3.1-lite': 'veo-3.1-lite-generate-preview',
}

# Veo 模型定价（美元/秒）—— 用于成本预估
VEO_PRICING = {
    'veo2': 0.50,
    'veo3': 0.40,
    'veo3-fast': 0.20,
    'veo3.1': 0.40,
    'veo3.1-fast': 0.15,
    'veo3.1-lite': 0.05,
}

# Imagen 模型 ID 映射（Imagen 4 三档）
IMAGEN_MODELS = {
    'imagen3': 'imagen-3.0-generate-002',
    'imagen3-fast': 'imagen-3.0-fast-generate-001',
    'imagen4': 'imagen-4.0-generate-001',
    'imagen4-fast': 'imagen-4.0-fast-generate-001',
    'imagen4-ultra': 'imagen-4.0-ultra-generate-001',
}

# Imagen 模型定价（美元/张）
IMAGEN_PRICING = {
    'imagen3': 0.04,
    'imagen3-fast': 0.02,
    'imagen4': 0.04,
    'imagen4-fast': 0.02,
    'imagen4-ultra': 0.06,
}

DEFAULT_IMAGEN_MODEL = 'imagen4-fast'

# Gemini 模型列表（含 Gemini 3.x 系列）
GEMINI_MODELS = {
    # Gemini 3.5 (最新, I/O 2026)
    'gemini-3.5-flash': 'Gemini 3.5 Flash',
    # Gemini 3.x
    'gemini-3-pro': 'Gemini 3 Pro',
    'gemini-3-flash': 'Gemini 3 Flash',
    'gemini-3.1-pro': 'Gemini 3.1 Pro',
    'gemini-3.1-flash-lite': 'Gemini 3.1 Flash Lite',
    # Gemini 2.5 (Stable GA)
    'gemini-2.5-pro': 'Gemini 2.5 Pro',
    'gemini-2.5-flash': 'Gemini 2.5 Flash',
    'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
    # Gemini 2.0
    'gemini-2.0-flash-001': 'Gemini 2.0 Flash',
    'gemini-2.0-flash-lite-001': 'Gemini 2.0 Flash Lite',
}

DEFAULT_GEMINI_MODEL = 'gemini-3.5-flash'

# Gemini 原生图像模型（Nano Banana 系列）
GEMINI_IMAGE_MODELS = {
    'nano-banana-2': 'gemini-3.1-flash-image',
    'nano-banana-pro': 'gemini-3-pro-image',
    'nano-banana': 'gemini-2.5-flash-image',
}

# Gemini TTS 模型与预置音色
GEMINI_TTS_MODELS = {
    'gemini-3.1-flash-tts': 'gemini-3.1-flash-tts-preview',
    'gemini-2.5-flash-tts': 'gemini-2.5-flash-preview-tts',
    'gemini-2.5-pro-tts': 'gemini-2.5-pro-preview-tts',
}

DEFAULT_TTS_MODEL = 'gemini-3.1-flash-tts'

# Gemini TTS 30 个预置音色
GEMINI_TTS_VOICES = [
    'Kore', 'Puck', 'Charon', 'Fenrir', 'Leda', 'Orus', 'Aoede', 'Zephyr',
    'Callirrhoe', 'Autonoe', 'Enceladus', 'Iapetus', 'Umbriel', 'Algieba',
    'Despina', 'Erinome', 'Gacrux', 'Pulcherrima', 'Achird', 'Zubenelgenubi',
    'Vindemiatrix', 'Sadachbia', 'Sadaltager', 'Sulafat', 'Laomedeia',
    'Achernar', 'Schedar', 'Rasalgethi', 'Nashira', 'Enif',
]

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
