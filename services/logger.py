"""
日志配置模块
统一管理全项目日志，支持控制台 + 文件输出、日志轮转
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import BASE_DIR

# 日志目录
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# 日志级别（通过环境变量配置）
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# 日志格式
_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

_configured = False


def setup_logging():
    """初始化全局日志配置（幂等，多次调用安全）"""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # 清除默认 handler
    root.handlers.clear()

    # 控制台 handler
    console = logging.StreamHandler()
    console.setLevel(LOG_LEVEL)
    console.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(console)

    # 主日志文件（轮转，10MB x 5）
    main_log = LOG_DIR / 'veo_flow.log'
    file_handler = RotatingFileHandler(
        main_log, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8',
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)

    # 错误日志文件（仅 ERROR 以上）
    error_log = LOG_DIR / 'error.log'
    error_handler = RotatingFileHandler(
        error_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8',
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(error_handler)

    # 降低第三方库日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)

    logging.info("Logging initialized (level=%s, dir=%s)", LOG_LEVEL, LOG_DIR)


def get_logger(name: str) -> logging.Logger:
    """获取命名 logger（自动调用 setup_logging 确保已初始化）"""
    if not _configured:
        setup_logging()
    return logging.getLogger(name)
