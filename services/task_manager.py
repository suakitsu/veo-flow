"""
任务管理器
集中管理任务状态、用户锁、后台线程调度
支持任务状态持久化到 JSON 文件，重启后恢复
支持可配置的并发限制（每用户最大并行任务数）
支持任务 TTL 自动清理（避免内存无限增长）
"""

import os
import uuid
import json
import threading
import time
from datetime import datetime
from pathlib import Path

from config import BASE_DIR
from services.logger import get_logger

log = get_logger(__name__)

TASKS_FILE = BASE_DIR / 'tasks.json'

# 并发限制配置（通过环境变量）
# 每用户最大并行任务数（默认 1）
MAX_TASKS_PER_USER = int(os.getenv('MAX_TASKS_PER_USER', '1'))
# 全局最大并行任务数（默认 0 = 不限制）
MAX_GLOBAL_TASKS = int(os.getenv('MAX_GLOBAL_TASKS', '0'))

# 任务 TTL 清理配置
# 已完成任务保留时长（秒），默认 7 天
TASK_TTL_SECONDS = int(os.getenv('TASK_TTL_SECONDS', str(7 * 24 * 3600)))
# _tasks 字典最大条目数（超出时淘汰最旧的），默认 1000
MAX_TASKS_IN_MEMORY = int(os.getenv('MAX_TASKS_IN_MEMORY', '1000'))
# 清理检查间隔（秒），默认 1 小时
TASK_CLEANUP_INTERVAL = int(os.getenv('TASK_CLEANUP_INTERVAL', str(3600)))

_lock = threading.Lock()

# 任务状态存储
_tasks: dict = {}

# 用户任务锁：ip -> set of task_ids
_user_locks: dict = {}

# 上次清理时间戳
_last_cleanup = 0.0


# 持久化

def _save_tasks():
    """将任务状态保存到 JSON 文件"""
    try:
        # 只持久化非临时任务（排除 narration 的 fake_task）
        serializable = {}
        for tid, task in _tasks.items():
            # 跳过 narration 内联创建的临时任务
            if tid.startswith('narr_') and task.get('mode') in ('narration', 'tts'):
                continue
            serializable[tid] = task
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("Failed to save tasks: %s", e)


def _load_tasks():
    """从 JSON 文件加载任务状态"""
    global _tasks
    if TASKS_FILE.exists():
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                # 将重启时仍在运行的任务标记为 interrupted
                for tid, task in data.items():
                    if task.get('status') in ('running', 'pending', 'queued'):
                        task['status'] = 'interrupted'
                        task['message'] = 'Server restarted while task was running'
                        task['progress'] = task.get('progress', 0)
                _tasks.update(data)
                log.info("Loaded %d tasks from disk", len(data))
        except Exception as e:
            log.error("Failed to load tasks: %s", e)


# 启动时加载
_load_tasks()


# TTL 清理

def _cleanup_expired_tasks():
    """清理过期的已完成任务（防内存无限增长）

    策略：
    1. 删除超过 TASK_TTL_SECONDS 的已完成/已失败/已中断任务
    2. 如果清理后仍超过 MAX_TASKS_IN_MEMORY，按创建时间淘汰最旧的
    """
    global _last_cleanup
    now = time.time()
    # 限频：每 TASK_CLEANUP_INTERVAL 秒最多清理一次
    if now - _last_cleanup < TASK_CLEANUP_INTERVAL:
        return
    _last_cleanup = now

    with _lock:
        expired_ids = []
        for tid, task in list(_tasks.items()):
            status = task.get('status', '')
            # 仅清理终态任务
            if status not in ('completed', 'error', 'interrupted'):
                continue
            created = task.get('created_at', '')
            if not created:
                # 无创建时间的视为过期
                expired_ids.append(tid)
                continue
            try:
                ct = datetime.fromisoformat(created).timestamp()
                if now - ct > TASK_TTL_SECONDS:
                    expired_ids.append(tid)
            except (ValueError, OSError):
                expired_ids.append(tid)

        for tid in expired_ids:
            _tasks.pop(tid, None)

        # 如果仍超过上限，按创建时间淘汰最旧的终态任务
        if len(_tasks) > MAX_TASKS_IN_MEMORY:
            terminal = [(tid, t) for tid, t in _tasks.items()
                       if t.get('status') in ('completed', 'error', 'interrupted')]
            terminal.sort(key=lambda x: x[1].get('created_at', ''))
            excess = len(_tasks) - MAX_TASKS_IN_MEMORY
            for tid, _ in terminal[:excess]:
                _tasks.pop(tid, None)

        if expired_ids:
            log.info("Cleanup: removed %d expired tasks", len(expired_ids))
            _save_tasks()


# 任务 CRUD

def create_task(mode: str, prompt: str, model: str, ratio: str,
                output_path: str, **extra) -> dict:
    """创建一个新任务并返回任务对象"""
    # 创建前触发清理（限频，不会每次都执行）
    _cleanup_expired_tasks()

    task_id = str(uuid.uuid4())
    task = {
        'id': task_id,
        'mode': mode,
        'prompt': prompt,
        'model': model,
        'ratio': ratio,
        'status': 'pending',
        'progress': 0,
        'message': 'Initializing...',
        'output_path': str(output_path),
        'created_at': datetime.now().isoformat(),
        **extra,
    }
    with _lock:
        _tasks[task_id] = task
        _save_tasks()
    return task


def get_task(task_id: str) -> dict | None:
    """获取任务"""
    return _tasks.get(task_id)


def update_task(task_id: str, **kwargs) -> dict | None:
    """更新任务字段并持久化"""
    with _lock:
        task = _tasks.get(task_id)
        if task:
            task.update(kwargs)
            _save_tasks()
        return task


def list_all_tasks() -> list:
    """列出所有任务（按创建时间倒序）"""
    return sorted(_tasks.values(), key=lambda x: x['created_at'], reverse=True)


def mark_error(task: dict, error_msg: str):
    """将任务标记为失败"""
    task['status'] = 'error'
    task['message'] = str(error_msg)
    with _lock:
        _save_tasks()


def mark_completed(task: dict):
    """将任务标记为完成并持久化"""
    task['status'] = 'completed'
    task['progress'] = 100
    with _lock:
        _save_tasks()


# 用户锁（防止同一 IP 超过并发限制）

def is_locked(user_ip: str) -> bool:
    """检查用户是否已达并发上限"""
    locked, _ = check_user_lock(user_ip)
    return locked


def check_user_lock(user_ip: str) -> tuple[bool, str | None]:
    """检查用户是否可提交新任务，返回 (is_locked, oldest_task_id)

    is_locked=True 表示已达并发上限，不能提交新任务
    """
    with _lock:
        active_tasks = _get_active_tasks(user_ip)

        # 检查每用户限制
        if len(active_tasks) >= MAX_TASKS_PER_USER:
            return True, active_tasks[0] if active_tasks else None

        # 检查全局限制
        if MAX_GLOBAL_TASKS > 0:
            global_active = sum(
                len(_get_active_tasks(ip)) for ip in _user_locks
            )
            if global_active >= MAX_GLOBAL_TASKS:
                return True, None

    return False, None


def _get_active_tasks(user_ip: str) -> list:
    """获取用户活跃的任务 ID 列表（清理已完成的）"""
    task_ids = _user_locks.get(user_ip, set())
    if isinstance(task_ids, str):
        # 向后兼容：旧版存储的是单个 task_id 字符串
        task_ids = {task_ids}
        _user_locks[user_ip] = task_ids

    active = []
    for tid in list(task_ids):
        task = _tasks.get(tid)
        if task and task['status'] in ('queued', 'running', 'pending'):
            active.append(tid)
        else:
            # 清理已完成的任务
            task_ids.discard(tid)
    return active


def lock_user(user_ip: str, task_id: str):
    """锁定用户（添加任务到活跃集合）"""
    with _lock:
        if user_ip not in _user_locks or isinstance(_user_locks[user_ip], str):
            _user_locks[user_ip] = set()
        _user_locks[user_ip].add(task_id)


def unlock_user(user_ip: str, task_id: str):
    """解锁用户（从活跃集合移除任务）"""
    with _lock:
        task_ids = _user_locks.get(user_ip)
        if task_ids is None:
            return
        if isinstance(task_ids, str):
            # 向后兼容
            if task_ids == task_id:
                _user_locks.pop(user_ip, None)
            return
        task_ids.discard(task_id)
        if not task_ids:
            _user_locks.pop(user_ip, None)
        log.info("Unlocked user %s after task %s", user_ip, task_id)


# 后台线程调度

def run_in_background(target, args: tuple, user_ip: str, task_id: str):
    """在后台线程中运行 target，完成后自动解锁用户并持久化"""
    def wrapper():
        task = _tasks.get(task_id)
        try:
            target(*args)
        except Exception as e:
            if task:
                mark_error(task, str(e))
            log.error("Task %s error: %s", task_id, e)
        finally:
            # 确保最终状态持久化
            with _lock:
                _save_tasks()
            unlock_user(user_ip, task_id)

    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return thread
