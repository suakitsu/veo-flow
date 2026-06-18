"""
Imagen 图像生成器模块 - 生成完成后记录 history
支持 Imagen 3 / Imagen 4 (Fast / Standard / Ultra)
"""

import time
from google.genai import types
from generators.client import get_client
from config import IMAGEN_MODELS, IMAGEN_PRICING, DEFAULT_IMAGEN_MODEL
from services.retry import call_with_retry


class ImagenGenerator:
    """Imagen 图像生成器（支持 Imagen 4 三档）"""

    @staticmethod
    def _resolve_model(model: str) -> str:
        """将别名解析为实际模型 ID"""
        return IMAGEN_MODELS.get(model, model)

    @staticmethod
    def _estimate_cost(model: str) -> float:
        """预估单张图片成本（美元）"""
        return IMAGEN_PRICING.get(model, 0.04)

    def generate(self, task: dict, prompt: str,
                 model: str = DEFAULT_IMAGEN_MODEL,
                 aspect_ratio: str = "1:1", output_path: str = None,
                 negative_prompt: str = None, enhance_prompt: bool = False):
        """生成图片并更新任务状态"""
        from services import history_manager as hm
        client = get_client()
        start = time.time()
        model_id = self._resolve_model(model)

        task['status'] = 'running'
        task['message'] = f'Sending image request ({model})...'
        task['progress'] = 10
        task['cost_estimate'] = self._estimate_cost(model)

        config_args = {
            'number_of_images': 1,
            'aspect_ratio': aspect_ratio,
        }
        if negative_prompt:
            config_args['negative_prompt'] = negative_prompt
        if enhance_prompt:
            config_args['enhance_prompt'] = True

        config = types.GenerateImagesConfig(**config_args)

        task['message'] = 'Generating image...'
        task['progress'] = 40

        response = call_with_retry(
            client.models.generate_images,
            model=model_id, prompt=prompt, config=config,
        )

        task['message'] = 'Saving image...'
        task['progress'] = 90

        if response.generated_images and len(response.generated_images) > 0:
            image_data = response.generated_images[0].image
            if image_data.image_bytes:
                with open(output_path, 'wb') as f:
                    f.write(image_data.image_bytes)
                elapsed = time.time() - start
                task['output_path'] = output_path
                task['status'] = 'completed'
                task['progress'] = 100
                task['message'] = 'Complete!'
                hm.record(task['id'], prompt, model, model_id, 1, 'image',
                          aspect_ratio, 'completed', elapsed)
                return

        elapsed = time.time() - start
        hm.record(task['id'], prompt, model, model_id, 1, 'image',
                  aspect_ratio, 'error', elapsed)
        raise RuntimeError("No image data received")
