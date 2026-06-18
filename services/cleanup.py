"""
文件清理服务
定期清理 outputs/ 和 uploads/ 目录中的过期文件
TTL 通过环境变量配置，默认 7 天
"""

import os
import time
import threading
from pathlib import Path

from config import BASE_DIR, OUTPUT_FOLDER, UPLOAD_FOLDER
from services.logger import get_logger

log = get_logger(__name__)

# TTL 配置（秒），默认 7 天
OUTPUT_TTL = int(os.getenv('OUTPUT_TTL_HOURS', '168')) * 3600
UPLOAD_TTL = int(os.getenv('UPLOAD_TTL_HOURS', '24')) * 3600

# 清理间隔（秒），默认 1 小时
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL_HOURS', '1')) * 3600

# 允许的文件扩展名（安全白名单）
_ALLOWED_EXTS = {'.mp4', '.png', '.jpg', '.jpeg', '.wav', '.mp3', '.webm'}

_timer = None


def _cleanup_directory(directory: Path, ttl: int, label: str) -> int:
    """清理指定目录中超过 TTL 的文件，返回删除数量"""
    if not directory.exists():
        return 0

    now = time.time()
    deleted = 0

    for item in directory.iterdir():
        if not item.is_file():
            continue
        # 安全检查：只删除白名单扩展名
        if item.suffix.lower() not in _ALLOWED_EXTS:
            continue

        try:
            mtime = item.stat().st_mtime
            if now - mtime > ttl:
                item.unlink()
                deleted += 1
                log.info("Cleaned %s: %s (age=%.1fh)", label, item.name,
                         (now - mtime) / 3600)
        except Exception as e:
            log.warning("Failed to clean %s: %s", item, e)

    return deleted


def run_cleanup():
    """执行一次清理"""
    out_deleted = _cleanup_directory(OUTPUT_FOLDER, OUTPUT_TTL, 'output')
    upl_deleted = _cleanup_directory(UPLOAD_FOLDER, UPLOAD_TTL, 'upload')

    if out_deleted or upl_deleted:
        log.info("Cleanup complete: %d output files, %d upload files removed",
                 out_deleted, upl_deleted)


def _cleanup_loop():
    """后台清理循环"""
    log.info("File cleanup service started (interval=%dh, output_ttl=%dh, upload_ttl=%dh)",
             CLEANUP_INTERVAL // 3600, OUTPUT_TTL // 3600, UPLOAD_TTL // 3600)
    while True:
        try:
            run_cleanup()
        except Exception as e:
            log.error("Cleanup loop error: %s", e)
        time.sleep(CLEANUP_INTERVAL)


def start_cleanup_service():
    """启动后台清理线程（守护线程，幂等）"""
    global _timer
    if _timer is not None:
        return
    _timer = threading.Thread(target=_cleanup_loop, daemon=True, name='file-cleanup')
    _timer.start()
    log.info("File cleanup thread started")
