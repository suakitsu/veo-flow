"""
统一错误响应工具

避免直接返回 str(e) 给客户端（可能泄露文件路径、SDK 内部结构、堆栈信息）。
生产环境返回通用错误消息，详细错误仅写入日志。
"""

import os
from flask import jsonify, current_app
from services.logger import get_logger

log = get_logger(__name__)

# 是否处于调试模式（调试时返回详细错误，便于开发）
def _is_debug() -> bool:
    return os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')


def error_response(message: str, status: int = 500, log_error: bool = True,
                   exception: Exception | None = None):
    """统一的 JSON 错误响应

    Args:
        message: 返回给客户端的错误消息（应为人话，不含敏感信息）
        status: HTTP 状态码
        log_error: 是否记录错误日志（默认 True）
        exception: 原始异常（仅写入日志，不返回客户端）

    Returns:
        Flask JSON 响应
    """
    if log_error:
        if exception:
            log.error("%s: %s", message, exception, exc_info=True)
        else:
            log.error(message)

    # 调试模式下返回详细错误，便于开发排查
    if _is_debug() and exception:
        return jsonify({
            'error': message,
            'detail': str(exception),
            'type': type(exception).__name__,
        }), status

    return jsonify({'error': message}), status


def safe_error_response(exception: Exception, status: int = 500,
                        public_message: str = 'Internal server error'):
    """从异常生成安全错误响应

    自动判断是否为客户端错误（4xx）并保留消息，服务端错误（5xx）用通用消息。
    """
    # 4xx 错误通常是客户端可理解的（如 "Prompt is required"）
    if 400 <= status < 500:
        return error_response(str(exception), status, log_error=False)
    # 5xx 错误用通用消息，避免泄露内部信息
    return error_response(public_message, status, exception=exception)
