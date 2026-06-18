"""
Flask 应用集成测试
验证核心 API 端点可访问、返回正确格式
"""
import pytest
import sys
import os

# 确保使用临时凭证，不真正调用 GCP
os.environ.setdefault('GCP_PROJECT_ID', 'test-project')


@pytest.fixture
def client():
    """创建 Flask 测试客户端"""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestModelsEndpoint:
    def test_get_models_returns_200(self, client):
        r = client.get('/api/models')
        assert r.status_code == 200

    def test_models_response_has_veo_and_imagen(self, client):
        r = client.get('/api/models')
        data = r.get_json()
        assert 'veo_models' in data
        assert 'imagen_models' in data

    def test_veo_models_include_lite(self, client):
        r = client.get('/api/models')
        data = r.get_json()
        veo_ids = [m['id'] for m in data['veo_models']]
        assert 'veo3.1-lite' in veo_ids

    def test_imagen_models_include_4_tiers(self, client):
        r = client.get('/api/models')
        data = r.get_json()
        imagen_ids = [m['id'] for m in data['imagen_models']]
        assert 'imagen4' in imagen_ids
        assert 'imagen4-fast' in imagen_ids
        assert 'imagen4-ultra' in imagen_ids


class TestTaskEndpoints:
    def test_get_nonexistent_task_returns_404(self, client):
        r = client.get('/api/task/nonexistent-id')
        assert r.status_code == 404

    def test_list_tasks_returns_200(self, client):
        r = client.get('/api/tasks')
        assert r.status_code == 200
        assert 'tasks' in r.get_json()


class TestTTSVoicesEndpoint:
    def test_get_voices_returns_list(self, client):
        r = client.get('/api/narration/tts/voices')
        assert r.status_code == 200
        data = r.get_json()
        assert 'voices' in data
        assert len(data['voices']) == 30
        assert 'Kore' in data['voices']


class TestNanoBananaModelsEndpoint:
    def test_get_nano_banana_models(self, client):
        r = client.get('/api/nano-banana/models')
        assert r.status_code == 200
        data = r.get_json()
        assert 'models' in data
        ids = [m['id'] for m in data['models']]
        assert 'nano-banana-2' in ids


class TestDocsEndpoint:
    def test_swagger_ui_returns_html(self, client):
        r = client.get('/api/docs')
        assert r.status_code == 200
        assert 'text/html' in r.content_type

    def test_openapi_yaml_returns_yaml(self, client):
        r = client.get('/api/docs/openapi.yaml')
        assert r.status_code == 200


class TestMultiSpeakerTTSEndpoint:
    def test_missing_text_returns_400(self, client):
        r = client.post('/api/narration/tts/multi-speaker',
                        json={'speakers': {'A': 'Kore'}})
        assert r.status_code == 400

    def test_single_speaker_returns_400(self, client):
        r = client.post('/api/narration/tts/multi-speaker',
                        json={'text': 'Hello', 'speakers': {'A': 'Kore'}})
        assert r.status_code == 400

    def test_invalid_voice_returns_400(self, client):
        r = client.post('/api/narration/tts/multi-speaker',
                        json={'text': 'Hello', 'speakers': {'A': 'InvalidVoice', 'B': 'Kore'}})
        assert r.status_code == 400
