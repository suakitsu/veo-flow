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
  或:     Query: ?api_key=your-secret-key
"""

import os
import hmac
from functools import wraps
from flask import request, jsonify, g

from services.logger import get_logger

log = get_logger(__name__)

# 从环境变量读取 API Key（留空则禁用鉴权）
API_KEY = os.getenv('API_KEY', '').strip()

# 不需要鉴权的路径前缀（只读端点 + 静态资源）
PUBLIC_PATHS = (
    '/',
    '/static/',
    '/api/models',
    '/api/docs',
    '/api/docs/',
    '/api/narration/tts/voices',
    '/api/nano-banana/models',
    '/api/templates',
    '/api/stats',
    '/api/history',
    '/api/tasks',
)

# 不需要鉴权的路径后缀
PUBLIC_SUFFIXES = ('.png', '.jpg', '.jpeg', '.css', '.js', '.ico', '.svg', '.webp')


def is_public_path(path: str) -> bool:
    """判断路径是否为公开路径（无需鉴权）"""
    if not path:
        return True
    for prefix in PUBLIC_PATHS:
        if path == prefix or path.startswith(prefix):
            return True
    for suffix in PUBLIC_SUFFIXES:
        if path.endswith(suffix):
            return True
    return False


def extract_api_key() -> str:
    """从请求中提取 API Key（支持 3 种方式）"""
    # 1. Authorization: Bearer xxx
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    # 2. X-API-Key header
    xkey = request.headers.get('X-API-Key', '')
    if xkey:
        return xkey.strip()
    # 3. Query parameter
    qkey = request.args.get('api_key', '')
    if qkey:
        return qkey.strip()
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
    if is_public_path(path):
        return None

    # GET 请求对 /api/task/ 和 /api/download/ 放行（前端轮询需要）
    if request.method == 'GET':
        if path.startswith('/api/task/') or path.startswith('/api/download/'):
            return None

    provided = extract_api_key()
    if not provided:
        log.warning("Auth failed: no API key (path=%s)", path)
        return jsonify({'error': 'API key required'}), 401

    if not hmac.compare_digest(provided, API_KEY):
        log.warning("Auth failed: invalid API key (path=%s)", path)
        return jsonify({'error': 'Invalid API key'}), 403

    return None
