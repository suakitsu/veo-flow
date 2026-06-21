"""
文件安全工具

统一处理：
- 路径穿越防护（safe_join + realpath 校验）
- 文件类型白名单校验
- 文件大小校验
"""

import os
from pathlib import Path
from werkzeug.utils import safe_join

from config import (
    UPLOAD_FOLDER, OUTPUT_FOLDER,
    ALLOWED_UPLOAD_EXTS, ALLOWED_IMAGE_EXTS, ALLOWED_VIDEO_EXTS,
    MAX_UPLOAD_SIZE,
)
from services.logger import get_logger

log = get_logger(__name__)


def is_path_safe(base_dir: Path, target: Path) -> bool:
    """校验 target 路径是否仍在 base_dir 内（防路径穿越）

    使用 realpath 解析符号链接与 ../ 等相对路径。
    """
    try:
        base_real = os.path.realpath(str(base_dir))
        target_real = os.path.realpath(str(target))
        # 确保 target 是 base_dir 的子路径
        return os.path.commonpath([base_real, target_real]) == base_real
    except (ValueError, OSError):
        return False


def safe_resolve_upload(filename: str) -> Path | None:
    """安全解析上传目录下的文件路径

    返回 Path 对象（如果安全且存在），否则 None。
    """
    if not filename:
        return None
    # 禁止任何路径分隔符（仅允许纯文件名）
    if '/' in filename or '\\' in filename or '..' in filename:
        log.warning("Rejected path traversal attempt: %s", filename)
        return None
    # werkzeug safe_join 防止绝对路径与 ../
    safe_path = safe_join(str(UPLOAD_FOLDER), filename)
    if not safe_path:
        return None
    p = Path(safe_path)
    if not p.exists() or not is_path_safe(UPLOAD_FOLDER, p):
        return None
    return p


def validate_upload_file(file_storage) -> tuple[bool, str]:
    """校验上传文件：扩展名 + 大小

    返回 (is_valid, error_message)
    """
    if not file_storage or not file_storage.filename:
        return False, 'No file uploaded'

    # 扩展名校验
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        return False, f'File type {ext} not allowed. Allowed: {sorted(ALLOWED_UPLOAD_EXTS)}'

    # 大小校验（通过 content_length 头，最终保存时还会校验）
    file_storage.stream.seek(0, 2)  # seek to end
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)  # reset
    if size > MAX_UPLOAD_SIZE:
        return False, f'File too large. Max size: {MAX_UPLOAD_SIZE // (1024*1024)} MB'
    if size == 0:
        return False, 'Empty file'

    return True, ''


def save_upload_safely(file_storage, prefix: str = 'upload_') -> tuple[Path | None, str]:
    """安全保存上传文件

    自动生成 UUID 文件名，校验类型与大小，防路径穿越。
    返回 (saved_path, filename) 或 (None, error_message)
    """
    import uuid

    is_valid, err = validate_upload_file(file_storage)
    if not is_valid:
        return None, err

    ext = Path(file_storage.filename).suffix.lower()
    filename = f"{prefix}{uuid.uuid4().hex[:12]}{ext}"
    save_path = UPLOAD_FOLDER / filename

    try:
        file_storage.save(save_path)
    except OSError as e:
        log.error("Failed to save upload: %s", e)
        return None, f'Save failed: {e}'

    # 二次校验：保存后路径仍在 UPLOAD_FOLDER 内
    if not is_path_safe(UPLOAD_FOLDER, save_path):
        try:
            save_path.unlink()
        except OSError:
            pass
        return None, 'Path traversal detected'

    return save_path, filename
