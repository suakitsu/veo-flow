"""
任务管理器
集中管理任务状态、用户锁、后台线程调度
"""

import uuid
import threading
from datetime import datetime


# 任务状态存储
_tasks: dict = {}

# 用户任务锁：ip -> task_id
_user_locks: dict = {}


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
    _tasks[task_id] = task
    return task


def get_task(task_id: str) -> dict | None:
    """获取任务"""
    return _tasks.get(task_id)


def list_all_tasks() -> list:
    """列出所有任务（按创建时间倒序）"""
    return sorted(_tasks.values(), key=lambda x: x['created_at'], reverse=True)


def mark_error(task: dict, error_msg: str):
    """将任务标记为失败"""
    task['status'] = 'error'
    task['message'] = str(error_msg)


# 用户锁（防止同一 IP 并发提交）

def check_user_lock(user_ip: str) -> tuple[bool, str | None]:
    """检查用户是否有进行中的任务，返回 (is_locked, task_id)"""
    if user_ip in _user_locks:
        locked_id = _user_locks[user_ip]
        locked_task = _tasks.get(locked_id)
        if locked_task and locked_task['status'] in ('queued', 'running', 'pending'):
            return True, locked_id
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
    """在后台线程中运行 target，完成后自动解锁用户"""
    def wrapper():
        task = _tasks.get(task_id)
        try:
            target(*args)
        except Exception as e:
            if task:
                mark_error(task, str(e))
            print(f"[TaskManager] Task {task_id} error: {e}")
        finally:
            unlock_user(user_ip, task_id)

    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return thread
