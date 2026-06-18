"""
API 重试工具
对 Google GenAI API 调用添加自动重试机制
处理 429（限流）、500/502/503（服务器错误）、网络超时等临时性故障
"""

import os
import time
import functools
from services.logger import get_logger

log = get_logger(__name__)

# 重试配置（可通过环境变量覆盖）
MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))
INITIAL_BACKOFF = float(os.getenv('API_INITIAL_BACKOFF', '2.0'))  # 秒
MAX_BACKOFF = float(os.getenv('API_MAX_BACKOFF', '60.0'))  # 秒

# 可重试的异常类型
_RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# 可重试的 HTTP 状态码（从 google.api_core.exceptions 或响应中提取）
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    """判断异常是否可重试"""
    # 网络类异常
    if isinstance(exc, _RETRYABLE_ERRORS):
        return True

    # Google API 异常（动态检查，避免硬依赖）
    exc_str = str(exc).lower()
    if any(code in exc_str for code in ('429', '500', '502', '503', '504')):
        return True
    if any(keyword in exc_str for keyword in (
        'rate limit', 'quota', 'timeout', 'connection reset',
        'temporarily unavailable', 'service unavailable',
        'internal error', 'deadline exceeded',
    )):
        return True

    return False


def retry_api_call(max_retries: int = None, initial_backoff: float = None):
    """装饰器：对 API 调用添加指数退避重试

    Args:
        max_retries: 最大重试次数（默认从环境变量读取）
        initial_backoff: 初始退避秒数（默认从环境变量读取）

    用法:
        @retry_api_call()
        def call_veo_api(...):
            ...

        或直接包装:
        retry_api_call()(client.models.generate_videos)(...)
    """
    retries = max_retries if max_retries is not None else MAX_RETRIES
    backoff = initial_backoff if initial_backoff is not None else INITIAL_BACKOFF

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            current_backoff = backoff

            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt >= retries or not _is_retryable(e):
                        raise

                    # 指数退避 + 抖动
                    import random
                    jitter = random.uniform(0, 0.5)
                    wait_time = min(current_backoff + jitter, MAX_BACKOFF)

                    log.warning(
                        "API call %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                        func.__name__, attempt + 1, retries, str(e)[:100], wait_time,
                    )
                    time.sleep(wait_time)
                    current_backoff *= 2  # 指数退避

            raise last_exc
        return wrapper
    return decorator


def call_with_retry(func, *args, **kwargs):
    """函数式调用：对单次调用添加重试

    用法:
        result = call_with_retry(client.models.generate_videos, model=..., source=...)
    """
    return retry_api_call()(func)(*args, **kwargs)
