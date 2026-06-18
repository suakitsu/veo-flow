"""
任务管理器
集中管理任务状态、用户锁、后台线程调度
支持任务状态持久化到 JSON 文件，重启后恢复
"""

import uuid
import json
import threading
from datetime import datetime
from pathlib import Path

from config import BASE_DIR

TASKS_FILE = BASE_DIR / 'tasks.json'
_lock = threading.Lock()

# 任务状态存储
_tasks: dict = {}

# 用户任务锁：ip -> task_id
_user_locks: dict = {}


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
        print(f"[TaskManager] Failed to save tasks: {e}")


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
                print(f"[TaskManager] Loaded {len(data)} tasks from disk")
        except Exception as e:
            print(f"[TaskManager] Failed to load tasks: {e}")


# 启动时加载
_load_tasks()


# 任务 CRUD

def create_task(mode: str, prompt: str, model: str, ratio: str,
                output_path: str, **extra) -> dict:
    """创建一个新任务并返回任务对象"""
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


# 用户锁（防止同一 IP 并发提交）

def is_locked(user_ip: str) -> bool:
    """检查用户是否被锁定"""
    locked, _ = check_user_lock(user_ip)
    return locked


def check_user_lock(user_ip: str) -> tuple[bool, str | None]:
    """检查用户是否有进行中的任务，返回 (is_locked, task_id)"""
    if user_ip in _user_locks:
        locked_id = _user_locks[user_ip]
        locked_task = _tasks.get(locked_id)
        if locked_task and locked_task['status'] in ('queued', 'running', 'pending'):
            return True, locked_id
        # 任务已结束，清理过期锁
        _user_locks.pop(user_ip, None)
    return False, None


def lock_user(user_ip: str, task_id: str):
    """锁定用户"""
    _user_locks[user_ip] = task_id


def unlock_user(user_ip: str, task_id: str):
    """解锁用户"""
    if _user_locks.get(user_ip) == task_id:
        _user_locks.pop(user_ip, None)
        print(f"[TaskManager] Unlocked user {user_ip} after task {task_id}")


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
            print(f"[TaskManager] Task {task_id} error: {e}")
        finally:
            # 确保最终状态持久化
            with _lock:
                _save_tasks()
            unlock_user(user_ip, task_id)

    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return thread
