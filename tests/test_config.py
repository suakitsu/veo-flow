"""
config.py 单元测试
验证模型映射、价格表、默认值
"""
import pytest


class TestVeoModels:
    def test_veo_models_contains_all_tiers(self):
        from config import VEO_MODELS
        assert 'veo2' in VEO_MODELS
        assert 'veo3' in VEO_MODELS
        assert 'veo3.1' in VEO_MODELS
        assert 'veo3.1-fast' in VEO_MODELS
        assert 'veo3.1-lite' in VEO_MODELS

    def test_veo_model_ids_are_strings(self):
        from config import VEO_MODELS
        for alias, model_id in VEO_MODELS.items():
            assert isinstance(model_id, str)
            assert model_id.startswith('veo-')

    def test_veo_pricing_has_all_models(self):
        from config import VEO_PRICING, VEO_MODELS
        for alias in VEO_MODELS:
            assert alias in VEO_PRICING, f"Missing pricing for {alias}"

    def test_veo_lite_is_cheapest(self):
        from config import VEO_PRICING
        lite_price = VEO_PRICING['veo3.1-lite']
        fast_price = VEO_PRICING['veo3.1-fast']
        assert lite_price < fast_price


class TestImagenModels:
    def test_imagen4_tiers_exist(self):
        from config import IMAGEN_MODELS
        assert 'imagen4' in IMAGEN_MODELS
        assert 'imagen4-fast' in IMAGEN_MODELS
        assert 'imagen4-ultra' in IMAGEN_MODELS

    def test_default_imagen_is_fast(self):
        from config import DEFAULT_IMAGEN_MODEL
        assert DEFAULT_IMAGEN_MODEL == 'imagen4-fast'

    def test_imagen_pricing_ultra_is_most_expensive(self):
        from config import IMAGEN_PRICING
        assert IMAGEN_PRICING['imagen4-ultra'] > IMAGEN_PRICING['imagen4']
        assert IMAGEN_PRICING['imagen4'] >= IMAGEN_PRICING['imagen4-fast']


class TestGeminiModels:
    def test_gemini_35_flash_exists(self):
        from config import GEMINI_MODELS
        assert 'gemini-3.5-flash' in GEMINI_MODELS

    def test_default_gemini_is_35_flash(self):
        from config import DEFAULT_GEMINI_MODEL
        assert DEFAULT_GEMINI_MODEL == 'gemini-3.5-flash'


class TestTTSConfig:
    def test_tts_voices_has_30_entries(self):
        from config import GEMINI_TTS_VOICES
        assert len(GEMINI_TTS_VOICES) == 30

    def test_tts_voices_contains_common_names(self):
        from config import GEMINI_TTS_VOICES
        for voice in ['Kore', 'Puck', 'Charon', 'Fenrir', 'Leda']:
            assert voice in GEMINI_TTS_VOICES

    def test_default_tts_model(self):
        from config import DEFAULT_TTS_MODEL
        assert DEFAULT_TTS_MODEL == 'gemini-3.1-flash-tts'


class TestNanoBananaModels:
    def test_nano_banana_models_exist(self):
        from config import GEMINI_IMAGE_MODELS
        assert 'nano-banana-2' in GEMINI_IMAGE_MODELS
        assert 'nano-banana-pro' in GEMINI_IMAGE_MODELS
