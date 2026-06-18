"""
task_manager.py 单元测试
验证任务创建、持久化、用户锁
"""
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def temp_tasks(monkeypatch):
    """使用临时文件作为 tasks.json"""
    temp_path = Path(tempfile.mktemp(suffix='.json'))
    temp_path.write_text('{}')

    from services import task_manager as tm
    monkeypatch.setattr(tm, 'TASKS_FILE', temp_path)
    # 清空内存中的任务
    tm._tasks.clear()
    tm._user_locks.clear()
    yield temp_path
    temp_path.unlink(missing_ok=True)


class TestTaskCRUD:
    def test_create_task_returns_task_with_id(self, temp_tasks):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        assert task['id']
        assert task['mode'] == 'short'
        assert task['status'] == 'pending'
        assert task['progress'] == 0

    def test_get_task_returns_created_task(self, temp_tasks):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        fetched = tm.get_task(task['id'])
        assert fetched is task

    def test_get_nonexistent_task_returns_none(self, temp_tasks):
        from services import task_manager as tm
        assert tm.get_task('nonexistent') is None

    def test_update_task_persists(self, temp_tasks):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        tm.update_task(task['id'], status='running', progress=50)
        assert tm.get_task(task['id'])['status'] == 'running'
        assert tm.get_task(task['id'])['progress'] == 50

    def test_mark_error_sets_status(self, temp_tasks):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        tm.mark_error(task, 'Something went wrong')
        assert task['status'] == 'error'
        assert 'Something went wrong' in task['message']


class TestUserLock:
    def test_lock_and_check(self, temp_tasks):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        tm.lock_user('1.2.3.4', task['id'])
        assert tm.is_locked('1.2.3.4') is True

    def test_unlock_clears_lock(self, temp_tasks):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        tm.lock_user('1.2.3.4', task['id'])
        tm.unlock_user('1.2.3.4', task['id'])
        assert tm.is_locked('1.2.3.4') is False

    def test_completed_task_does_not_lock(self, temp_tasks):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        tm.lock_user('1.2.3.4', task['id'])
        tm.mark_completed(task)
        # 完成后不应再锁定
        assert tm.is_locked('1.2.3.4') is False


class TestPersistence:
    def test_task_saved_to_disk(self, temp_tasks):
        from services import task_manager as tm
        import json
        task = tm.create_task('short', 'persist test', 'veo3.1', '16:9', '/out.mp4')
        with open(temp_tasks, 'r') as f:
            data = json.load(f)
        assert task['id'] in data

    def test_interrupted_status_on_reload(self, temp_tasks, monkeypatch):
        from services import task_manager as tm
        task = tm.create_task('short', 'test', 'veo3.1', '16:9', '/out.mp4')
        tm.update_task(task['id'], status='running', progress=50)

        # 模拟重启：清空内存并重新加载
        tm._tasks.clear()
        tm._load_tasks()

        reloaded = tm.get_task(task['id'])
        assert reloaded['status'] == 'interrupted'
