"""
API 鉴权中间件
通过 API Key 保护写操作端点（生成、删除等）
只读端点（模型列表、文档、静态页面）无需鉴权

配置方式：
  环境变量 API_KEY=your-secret-key
  留空则禁用鉴权（仅开发环境推荐）

请求方式：
  Header: Authorization: Bearer your-secret-key
  或:     X-API-Key: your-secret-key
"""

import os
import hmac
from functools import wraps
from flask import request, jsonify, g

from services.logger import get_logger

log = get_logger(__name__)

# 从环境变量读取 API Key（留空则禁用鉴权）
API_KEY = os.getenv('API_KEY', '').strip()

# 完全公开的精确路径（只读端点 + 静态资源）
# 注意：使用精确匹配避免前缀绕过（如 /api/history/clear 不能匹配 /api/history）
PUBLIC_EXACT_PATHS = {
    '/',
    '/api/models',
    '/api/docs',
    '/api/narration/tts/voices',
    '/api/nano-banana/models',
    '/api/templates',
    '/api/stats',
    '/api/history',
    '/api/tasks',
}

# 公开路径前缀（仅用于真正的子路径只读场景，需谨慎）
PUBLIC_PREFIXES = (
    '/static/',
    '/api/docs/',
)

# 公开路径的正则规则（GET 请求的只读动态路径）
# 格式：(前缀, 允许的方法集合)
PUBLIC_GET_PATTERNS = (
    # /api/task/<id> GET 轮询放行（task_id 是 UUID 难以枚举）
    ('/api/task/', frozenset({'GET'})),
    # /api/download/<id> GET 下载放行
    ('/api/download/', frozenset({'GET'})),
    # /api/uploads/<filename> GET 上传文件预览
    ('/api/uploads/', frozenset({'GET'})),
    # /api/history/thumbnail/<task_id> GET 缩略图
    ('/api/history/thumbnail/', frozenset({'GET'})),
)

# 不需要鉴权的路径后缀（静态资源）
PUBLIC_SUFFIXES = ('.png', '.jpg', '.jpeg', '.css', '.js', '.ico', '.svg', '.webp')


def is_public_path(path: str, method: str = 'GET') -> bool:
    """判断路径是否为公开路径（无需鉴权）

    使用精确匹配 + 显式前缀，避免 startswith 误匹配子路径。
    例如 /api/history 是公开的，但 /api/history/clear 不是。
    """
    if not path:
        return True

    # 精确匹配
    if path in PUBLIC_EXACT_PATHS:
        return True

    # 静态前缀
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True

    # GET 请求的动态只读路径
    if method in frozenset({'GET'}):
        for prefix, allowed_methods in PUBLIC_GET_PATTERNS:
            if method in allowed_methods and path.startswith(prefix):
                return True

    # 静态资源后缀
    for suffix in PUBLIC_SUFFIXES:
        if path.endswith(suffix):
            return True

    return False


def extract_api_key() -> str:
    """从请求中提取 API Key

    仅支持 Header 方式，避免 query parameter 导致 URL 日志泄露。
    """
    # 1. Authorization: Bearer xxx
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    # 2. X-API-Key header
    xkey = request.headers.get('X-API-Key', '')
    if xkey:
        return xkey.strip()
    return ''


def require_api_key(f):
    """装饰器：要求请求携带有效 API Key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            # 未配置 API Key，跳过鉴权
            return f(*args, **kwargs)

        provided = extract_api_key()
        if not provided:
            log.warning("Auth failed: no API key provided (path=%s, ip=%s)",
                        request.path, getattr(g, 'client_ip', 'unknown'))
            return jsonify({'error': 'API key required'}), 401

        # 使用 hmac.compare_digest 防止时序攻击
        if not hmac.compare_digest(provided, API_KEY):
            log.warning("Auth failed: invalid API key (path=%s, ip=%s)",
                        request.path, getattr(g, 'client_ip', 'unknown'))
            return jsonify({'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)
    return decorated


def auth_middleware():
    """Flask before_request 钩子：全局鉴权检查

    使用方式（在 app.py 中）：
        from services.auth import auth_middleware
        app.before_request(auth_middleware)
    """
    # 未配置 API Key 则跳过
    if not API_KEY:
        return None

    path = request.path
    if is_public_path(path, request.method):
        return None

    provided = extract_api_key()
    if not provided:
        log.warning("Auth failed: no API key (path=%s)", path)
        return jsonify({'error': 'API key required'}), 401

    if not hmac.compare_digest(provided, API_KEY):
        log.warning("Auth failed: invalid API key (path=%s)", path)
        return jsonify({'error': 'Invalid API key'}), 403

    return None
