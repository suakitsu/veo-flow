"""
history_manager.py 单元测试
验证成本计算、记录、统计
"""
import json
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def temp_history(monkeypatch):
    """使用临时文件作为 history.json"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('[]')
        temp_path = Path(f.name)

    from services import history_manager as hm
    monkeypatch.setattr(hm, 'HISTORY_FILE', temp_path)
    yield temp_path
    temp_path.unlink(missing_ok=True)


class TestModelCost:
    def test_veo_lite_cost_exists(self):
        from services.history_manager import MODEL_COST
        assert 'veo-3.1-lite-generate-preview' in MODEL_COST
        assert MODEL_COST['veo-3.1-lite-generate-preview'] == 0.05

    def test_imagen4_costs_exist(self):
        from services.history_manager import MODEL_COST
        assert MODEL_COST['imagen-4.0-generate-001'] == 0.04
        assert MODEL_COST['imagen-4.0-fast-generate-001'] == 0.02
        assert MODEL_COST['imagen-4.0-ultra-generate-001'] == 0.06

    def test_veo_fast_price_updated(self):
        """确保 veo3.1-fast 价格从 0.20 更新到 0.15"""
        from services.history_manager import MODEL_COST
        assert MODEL_COST['veo-3.1-fast-generate-001'] == 0.15


class TestRecordAndStats:
    def test_record_creates_entry(self, temp_history):
        from services import history_manager as hm
        entry = hm.record('test-1', 'test prompt', 'veo3.1', 'veo-3.1-generate-001',
                          8, 'short', '16:9', 'completed', 10.5)
        assert entry['id'] == 'test-1'
        assert entry['cost'] == round(0.40 * 8, 4)
        assert entry['status'] == 'completed'

    def test_get_stats_calculates_correctly(self, temp_history):
        from services import history_manager as hm
        hm.record('t1', 'p1', 'veo3.1', 'veo-3.1-generate-001', 8, 'short', '16:9', 'completed', 10)
        hm.record('t2', 'p2', 'veo3.1', 'veo-3.1-generate-001', 8, 'short', '16:9', 'error', 5)

        stats = hm.get_stats()
        assert stats['total_generations'] == 2
        assert stats['success_rate'] == 50.0
        assert stats['total_cost'] == round(0.40 * 8 * 2, 4)

    def test_history_capped_at_500(self, temp_history):
        from services import history_manager as hm
        for i in range(510):
            hm.record(f't{i}', 'p', 'veo3.1', 'veo-3.1-generate-001', 8, 'short', '16:9', 'completed', 1)
        history = hm._load()
        assert len(history) == 500

    def test_clear_empties_history(self, temp_history):
        from services import history_manager as hm
        hm.record('t1', 'p', 'veo3.1', 'veo-3.1-generate-001', 8, 'short', '16:9', 'completed', 1)
        hm.clear()
        assert len(hm._load()) == 0
