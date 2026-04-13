"""
Imagen 图像生成器模块 - 生成完成后记录 history
"""

import time
from google.genai import types
from generators.client import get_client


class ImagenGenerator:
    """Imagen 图像生成器"""

    def generate(self, task: dict, prompt: str,
                 model: str = 'imagen-3.0-generate-002',
                 aspect_ratio: str = "1:1", output_path: str = None,
                 negative_prompt: str = None, enhance_prompt: bool = False):
        """生成图片并更新任务状态"""
        from services import history_manager as hm
        client = get_client()
        start = time.time()

        task['status'] = 'running'
        task['message'] = 'Sending image request...'
        task['progress'] = 10

        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt if negative_prompt else None,
            enhance_prompt=enhance_prompt,
        )

        task['message'] = 'Generating image...'
        task['progress'] = 40

        response = client.models.generate_images(
            model=model, prompt=prompt, config=config,
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
                hm.record(task['id'], prompt, model, model, 1, 'image',
                          aspect_ratio, 'completed', elapsed)
                return

        elapsed = time.time() - start
        hm.record(task['id'], prompt, model, model, 1, 'image',
                  aspect_ratio, 'error', elapsed)
        raise RuntimeError("No image data received")
