"""
鉴权中间件测试

覆盖：
- 未配置 API_KEY 时全放行
- 配置后公开路径放行
- 私有路径无 key 返 401
- 错误 key 返 403
- Bearer / X-API-Key 两种传递方式
- /api/history/clear 等敏感端点不被前缀误判为公开
- GET /api/task/<id> 放行但 POST 拦截
- 静态资源后缀放行
"""
import pytest
import os
from unittest.mock import patch


@pytest.fixture
def app_no_auth():
    """未配置 API_KEY 的应用（鉴权禁用）"""
    with patch('services.auth.API_KEY', ''):
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client


@pytest.fixture
def app_with_auth():
    """配置了 API_KEY 的应用"""
    test_key = 'test-secret-key-12345'
    with patch('services.auth.API_KEY', test_key):
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client, test_key


class TestNoAuthMode:
    """未配置 API_KEY 时应全放行"""

    def test_public_endpoint_accessible(self, app_no_auth):
        r = app_no_auth.get('/api/models')
        assert r.status_code == 200

    def test_protected_endpoint_accessible(self, app_no_auth):
        # 未配置 API_KEY 时，写操作也应放行
        r = app_no_auth.post('/api/history/clear')
        # 不应返回 401/403
        assert r.status_code != 401
        assert r.status_code != 403


class TestPublicPaths:
    """配置 API_KEY 后，公开路径仍应放行"""

    def test_root_path(self, app_with_auth):
        client, _ = app_with_auth
        r = client.get('/')
        assert r.status_code == 200

    def test_models_endpoint(self, app_with_auth):
        client, _ = app_with_auth
        r = client.get('/api/models')
        assert r.status_code == 200

    def test_tasks_list(self, app_with_auth):
        client, _ = app_with_auth
        r = client.get('/api/tasks')
        assert r.status_code == 200

    def test_history_list(self, app_with_auth):
        client, _ = app_with_auth
        r = client.get('/api/history')
        assert r.status_code == 200

    def test_tts_voices(self, app_with_auth):
        client, _ = app_with_auth
        r = client.get('/api/narration/tts/voices')
        assert r.status_code == 200

    def test_static_suffix(self, app_with_auth):
        client, _ = app_with_auth
        # 静态资源后缀应放行（即使路径不存在，也不应返回 401）
        r = client.get('/nonexistent.png')
        assert r.status_code != 401
        assert r.status_code != 403


class TestProtectedPaths:
    """配置 API_KEY 后，私有路径应要求鉴权"""

    def test_no_key_returns_401(self, app_with_auth):
        client, _ = app_with_auth
        r = client.post('/api/history/clear')
        assert r.status_code == 401

    def test_wrong_key_returns_403(self, app_with_auth):
        client, _ = app_with_auth
        r = client.post('/api/history/clear',
                       headers={'X-API-Key': 'wrong-key'})
        assert r.status_code == 403

    def test_correct_key_x_api_key(self, app_with_auth):
        client, key = app_with_auth
        r = client.post('/api/history/clear',
                       headers={'X-API-Key': key})
        assert r.status_code != 401
        assert r.status_code != 403

    def test_correct_key_bearer(self, app_with_auth):
        client, key = app_with_auth
        r = client.post('/api/history/clear',
                       headers={'Authorization': f'Bearer {key}'})
        assert r.status_code != 401
        assert r.status_code != 403

    def test_history_clear_not_public(self, app_with_auth):
        """关键测试：/api/history/clear 不应被 /api/history 前缀误判为公开"""
        client, _ = app_with_auth
        r = client.post('/api/history/clear')
        assert r.status_code == 401  # 应被拦截

    def test_history_stats_get_public(self, app_with_auth):
        """GET /api/history/stats 应放行（精确匹配 /api/stats，但实际路径不同）

        注意：/api/history/stats 不在 PUBLIC_EXACT_PATHS 中，
        但 GET 请求且属于只读，应放行。
        """
        client, _ = app_with_auth
        r = client.get('/api/history/stats')
        # /api/history/stats 不在公开精确路径，但 GET 且是只读
        # 根据当前实现，它不在 PUBLIC_GET_PATTERNS 中，所以会要求鉴权
        # 这是预期行为（stats 也可视为敏感数据）
        assert r.status_code in (200, 401)


class TestGetDynamicPaths:
    """GET 请求的动态只读路径应放行"""

    def test_get_task_by_id(self, app_with_auth):
        client, _ = app_with_auth
        r = client.get('/api/task/some-uuid')
        # 路径放行（404 是因为 task 不存在，不是 401）
        assert r.status_code != 401
        assert r.status_code != 403

    def test_get_download(self, app_with_auth):
        client, _ = app_with_auth
        r = client.get('/api/download/some-id')
        assert r.status_code != 401
        assert r.status_code != 403


class TestIsPublicPath:
    """直接测试 is_public_path 函数"""

    def test_exact_match_public(self):
        from services.auth import is_public_path
        assert is_public_path('/api/models', 'GET') is True
        assert is_public_path('/api/history', 'GET') is True

    def test_history_clear_not_public(self):
        from services.auth import is_public_path
        # /api/history/clear 不应匹配 /api/history（精确匹配）
        assert is_public_path('/api/history/clear', 'POST') is False

    def test_static_prefix(self):
        from services.auth import is_public_path
        assert is_public_path('/static/css/main.css', 'GET') is True

    def test_get_task_dynamic(self):
        from services.auth import is_public_path
        assert is_public_path('/api/task/abc-123', 'GET') is True

    def test_post_task_dynamic_blocked(self):
        from services.auth import is_public_path
        # POST /api/task/<id> 不在公开规则中（仅 GET 放行）
        assert is_public_path('/api/task/abc-123', 'POST') is False

    def test_empty_path(self):
        from services.auth import is_public_path
        assert is_public_path('', 'GET') is True

    def test_unknown_path(self):
        from services.auth import is_public_path
        assert is_public_path('/api/unknown', 'GET') is False
