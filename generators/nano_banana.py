"""
Nano Banana 图像生成器模块（Gemini 原生图像生成）
支持对话式图像编辑、多轮修改、4K 输出
模型：gemini-3.1-flash-image (Nano Banana 2) / gemini-3-pro-image (Pro)
"""

import time
import base64
from google.genai import types
from generators.client import get_client
from config import GEMINI_IMAGE_MODELS


class NanoBananaGenerator:
    """Gemini 原生图像生成器（对话式编辑）"""

    @staticmethod
    def _resolve_model(model: str) -> str:
        """将别名解析为实际模型 ID"""
        return GEMINI_IMAGE_MODELS.get(model, model)

    def generate(self, task: dict, prompt: str,
                 model: str = 'nano-banana-2',
                 output_path: str = None,
                 reference_image: str = None,
                 conversation_history: list = None):
        """生成或编辑图像（支持多轮对话式编辑）

        Args:
            task: 任务字典
            prompt: 用户指令（如 "把背景换成海滩" 或 "画一只猫"）
            model: 模型别名（nano-banana-2 / nano-banana-pro / nano-banana）
            output_path: 输出图片路径
            reference_image: 参考图片路径（可选，用于编辑模式）
            conversation_history: 对话历史（可选，用于多轮编辑）
                [{"role": "user", "text": "...", "image": "/path/..."},
                 {"role": "model", "text": "...", "image": "/path/..."}]
        """
        from services import history_manager as hm
        client = get_client()
        start = time.time()
        model_id = self._resolve_model(model)

        task['status'] = 'running'
        task['message'] = f'Nano Banana generating ({model})...'
        task['progress'] = 20

        # 构建多模态 contents
        contents = []

        # 如果有对话历史，先加入历史
        if conversation_history:
            for turn in conversation_history:
                parts = []
                if turn.get('text'):
                    parts.append(types.Part.from_text(text=turn['text']))
                if turn.get('image') and __import__('os').path.exists(turn['image']):
                    img = types.Part.from_bytes(
                        data=open(turn['image'], 'rb').read(),
                        mime_type='image/png',
                    )
                    parts.append(img)
                if parts:
                    contents.append(types.Content(
                        role=turn['role'],
                        parts=parts,
                    ))

        # 当前轮次：文本 + 可选参考图
        current_parts = [types.Part.from_text(text=prompt)]
        if reference_image and __import__('os').path.exists(reference_image):
            with open(reference_image, 'rb') as f:
                current_parts.append(types.Part.from_bytes(
                    data=f.read(),
                    mime_type='image/png',
                ))
        contents.append(types.Content(role='user', parts=current_parts))

        task['progress'] = 50
        task['message'] = 'Calling Gemini image model...'

        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE', 'TEXT'],
            ),
        )

        task['progress'] = 85
        task['message'] = 'Saving image...'

        # 提取图像数据
        image_data = None
        response_text = ''
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                inline = getattr(part, 'inline_data', None)
                if inline and inline.data:
                    image_data = inline.data
                elif getattr(part, 'text', None):
                    response_text += part.text

        if image_data:
            with open(output_path, 'wb') as f:
                f.write(image_data)
            elapsed = time.time() - start
            task['output_path'] = output_path
            task['status'] = 'completed'
            task['progress'] = 100
            task['message'] = 'Complete!'
            task['response_text'] = response_text
            hm.record(task['id'], prompt, model, model_id, 1, 'nano-banana',
                      '1:1', 'completed', elapsed)
            return

        elapsed = time.time() - start
        hm.record(task['id'], prompt, model, model_id, 1, 'nano-banana',
                  '1:1', 'error', elapsed)
        raise RuntimeError("No image data in Nano Banana response")
