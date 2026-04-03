"""
Gemini AI 助手路由：图像分析、提示词优化、对话
"""

import os
import json
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify
from google.genai import types

from config import (
    UPLOAD_FOLDER, GEMINI_MODELS, DEFAULT_GEMINI_MODEL, STYLE_PROMPTS,
)
from generators.client import get_client

bp = Blueprint('gemini', __name__)


def _validate_gemini_model(model: str) -> str:
    """校验 Gemini 模型名，无效则返回默认"""
    return model if model in GEMINI_MODELS else DEFAULT_GEMINI_MODEL


def _clean_json_response(text: str) -> str:
    """清理 Gemini 返回的 markdown 代码块"""
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        lines = [l for l in lines if not l.startswith('```')]
        text = '\n'.join(lines)
    return text


@bp.route('/api/gemini-models')
def get_gemini_models():
    """获取可用 Gemini 模型列表"""
    return jsonify({
        'models': [{'id': k, 'name': v} for k, v in GEMINI_MODELS.items()],
        'default': DEFAULT_GEMINI_MODEL,
    })


@bp.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """用 Gemini 分析参考图并生成提示词"""
    result_text = ''
    try:
        files = request.files
        data = request.form

        style = data.get('style', 'cinematic')
        target = data.get('target', 'video')
        custom_instruction = data.get('instruction', '').strip()
        gemini_model = _validate_gemini_model(data.get('gemini_model', DEFAULT_GEMINI_MODEL))

        if 'image' not in files or not files['image'].filename:
            return jsonify({'error': 'Please upload an image'}), 400

        image_file = files['image']
        tmp_path = UPLOAD_FOLDER / f"analyze_{datetime.now().timestamp()}{Path(image_file.filename).suffix}"
        image_file.save(tmp_path)

        try:
            client = get_client()
            image_data = types.Part.from_image(types.Image.from_file(location=str(tmp_path)))
            style_guide = STYLE_PROMPTS.get(style, STYLE_PROMPTS['cinematic'])

            if target == 'image':
                base_prompt = f"""Analyze this reference image in detail. Then generate a high-quality image generation prompt based on it.

Style guidance: {style_guide}

{f'Additional instruction: {custom_instruction}' if custom_instruction else ''}

Your response must be a JSON object with these fields:
- "description": A brief description of what's in the image (1-2 sentences)
- "style": The visual style detected (e.g. "photorealistic", "illustration", "anime")
- "prompt": A detailed image generation prompt (English, 50-150 words) that captures the essence and style of this image
- "negative_prompt": What to avoid (short, comma-separated)

Return ONLY the JSON, no markdown formatting."""
            else:
                base_prompt = f"""Analyze this reference image in detail. Then generate a high-quality video generation prompt based on it.

Style guidance: {style_guide}

{f'Additional instruction: {custom_instruction}' if custom_instruction else ''}

Your response must be a JSON object with these fields:
- "description": A brief description of what's in the image (1-2 sentences)
- "style": The visual style detected (e.g. "cinematic", "anime", "documentary")
- "prompt": A detailed video prompt (English, 50-200 words) describing the scene as a video. Include camera movement, lighting, mood, action/motion.
- "negative_prompt": What to avoid (short, comma-separated)
- "suggested_duration": Recommended duration in seconds (4, 6, or 8)
- "suggested_ratio": Recommended aspect ratio ("16:9" or "9:16")

Return ONLY the JSON, no markdown formatting."""

            response = client.models.generate_content(
                model=gemini_model,
                contents=[image_data, base_prompt],
            )
            result_text = _clean_json_response(response.text)
            result = json.loads(result_text)
            return jsonify({'success': True, **result})

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse Gemini response: {e}', 'raw': result_text}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/chat', methods=['POST'])
def chat_with_gemini():
    """与 Gemini 对话"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        context = data.get('context', '')
        gemini_model = _validate_gemini_model(data.get('gemini_model', DEFAULT_GEMINI_MODEL))

        if not message:
            return jsonify({'error': 'Please enter a message'}), 400

        client = get_client()

        system_prompt = """You are a creative director specializing in AI-generated video and image content.
Help the user refine their prompts, suggest creative ideas, and provide technical advice for video/image generation.
Be concise and practical. When generating prompts, always use English.
If the user asks in Chinese, respond in Chinese but keep generated prompts in English."""

        contents = []
        if context:
            contents.append(f"Current context: {context}")
        contents.append(message)

        response = client.models.generate_content(
            model=gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )

        return jsonify({'success': True, 'reply': response.text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/refine-prompt', methods=['POST'])
def refine_prompt():
    """用 Gemini 优化提示词"""
    result_text = ''
    try:
        data = request.json
        prompt = data.get('prompt', '').strip()
        target = data.get('target', 'video')
        style = data.get('style', 'cinematic')
        gemini_model = _validate_gemini_model(data.get('gemini_model', DEFAULT_GEMINI_MODEL))

        if not prompt:
            return jsonify({'error': 'Please enter a prompt'}), 400

        client = get_client()
        style_guide = STYLE_PROMPTS.get(style, STYLE_PROMPTS['cinematic'])

        refine_instruction = f"""Take this rough prompt and transform it into a professional, detailed {'video' if target == 'video' else 'image'} generation prompt.

Style: {style_guide}

Original prompt: {prompt}

Your response must be a JSON object:
- "prompt": The refined prompt (English, 50-200 words, highly detailed)
- "negative_prompt": What to avoid (comma-separated)
- "changes": Brief explanation of what you improved (1-2 sentences)

Return ONLY the JSON, no markdown."""

        response = client.models.generate_content(
            model=gemini_model,
            contents=[refine_instruction],
        )

        result_text = _clean_json_response(response.text)
        result = json.loads(result_text)
        return jsonify({'success': True, **result})

    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse response', 'raw': result_text}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
