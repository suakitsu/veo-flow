"""
Narration (文配视频) Route
流程：
  Auto:   topic -> Gemini生成文案+图片prompt -> Imagen生图 -> gTTS语音 -> ffmpeg合成视频
  Manual: 用户上传图片+输入文案 -> gTTS语音 -> ffmpeg合成视频
"""

import os
import uuid
import json
import subprocess
import tempfile
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

from config import UPLOAD_FOLDER, OUTPUT_FOLDER

bp = Blueprint('narration', __name__, url_prefix='/api')

# ------------------- 工具函数 -------------------

def _tts_gtts(text: str, output_path: str, lang: str = 'zh') -> bool:
    """使用 gTTS 生成音频（aka MiMo 引擎）"""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_path)
        return True
    except Exception as e:
        print(f"[Narration] gTTS error: {e}")
        return False


def _tts_gemini(text: str, output_path: str, voice: str = 'Kore') -> bool:
    """使用 Gemini TTS（google-cloud-texttospeech）生成音频"""
    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code='cmn-CN',
            name=f'cmn-CN-Wavenet-A',
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
        )
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        with open(output_path, 'wb') as f:
            f.write(response.audio_content)
        return True
    except Exception as e:
        print(f"[Narration] Gemini TTS error: {e}, falling back to gTTS")
        return _tts_gtts(text, output_path)


def _create_slideshow(image_paths: list, audio_path: str, output_path: str,
                      duration_per_image: float = None) -> bool:
    """
    用 ffmpeg 将图片列表 + 音频 合成为幻灯片视频
    duration_per_image: None 则根据音频时长均分
    """
    try:
        # 获取音频时长
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            capture_output=True, text=True,
        )
        audio_dur = float(probe.stdout.strip()) if probe.returncode == 0 else 30.0

        if duration_per_image is None:
            duration_per_image = max(audio_dur / len(image_paths), 2.0)

        # 写 concat 文件
        concat_path = str(OUTPUT_FOLDER / f"narr_{uuid.uuid4().hex[:6]}_concat.txt")
        with open(concat_path, 'w') as f:
            for img in image_paths:
                f.write(f"file '{img}'\n")
                f.write(f"duration {duration_per_image:.2f}\n")
            # 最后一帧重复（ffmpeg concat 需要）
            if image_paths:
                f.write(f"file '{image_paths[-1]}'\n")

        # 生成幻灯片视频（无音频）
        slideshow_path = str(OUTPUT_FOLDER / f"narr_{uuid.uuid4().hex[:6]}_slide.mp4")
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_path,
            '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
            '-pix_fmt', 'yuv420p',
            '-r', '24',
            slideshow_path,
        ], check=True, capture_output=True)

        # 合并音频
        subprocess.run([
            'ffmpeg', '-y',
            '-i', slideshow_path,
            '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'aac',
            '-shortest',
            output_path,
        ], check=True, capture_output=True)

        # 清理临时文件
        for tmp in [concat_path, slideshow_path]:
            try:
                os.remove(tmp)
            except OSError:
                pass

        return True
    except Exception as e:
        print(f"[Narration] slideshow error: {e}")
        return False


# ------------------- API 路由 -------------------

@bp.route('/narration/auto', methods=['POST'])
def auto_narration():
    """
    Auto 模式第一步：topic -> Gemini生成文案 + 图片prompt列表
    前端会拿到文案和图片prompts，然后分别调用 /api/narration/ai-image 生图
    """
    data = request.json or {}
    topic = data.get('topic', '').strip()
    image_count = int(data.get('image_count', 3))
    duration = int(data.get('duration', 30))

    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    # 调用 Gemini 生成文案
    try:
        from generators.client import get_client
        from config import DEFAULT_GEMINI_MODEL
        client = get_client()

        system_prompt = f"""你是一个优秀的视频文案创作者。
用户提供主题，你需要生成：
1. 一段{duration}秒左右的旁白/解说文案（自然流畅，适合配音）
2. {image_count}个视觉场景的图片生成提示词（英文，适合 Imagen AI）

请严格用以下 JSON 格式回复（不要有多余的文字）：
{{
  "text": "完整的旁白文本...",
  "image_prompts": ["prompt1", "prompt2", "prompt3"]
}}"""

        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=f"主题：{topic}",
            config={'system_instruction': system_prompt},
        )

        raw = response.text.strip()
        # 提取 JSON（可能有 ```json 包裹）
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]

        result = json.loads(raw.strip())
        narr_text = result.get('text', f'This is a narration about {topic}.')
        prompts = result.get('image_prompts', [f'{topic} scene {i+1}' for i in range(image_count)])

        return jsonify({
            'text': narr_text,
            'image_prompts': prompts[:image_count],
            'duration': duration,
        })

    except Exception as e:
        # Fallback：返回占位数据
        print(f"[Narration] Gemini text gen error: {e}")
        return jsonify({
            'text': f'A beautiful story about {topic}. ' * max(1, duration // 10),
            'image_prompts': [f'{topic} scene {i+1}' for i in range(image_count)],
            'duration': duration,
        })


@bp.route('/narration/ai-image', methods=['POST'])
def ai_image():
    """
    用 Imagen 根据 prompt 生成图片，保存到 uploads，返回 filename + url
    """
    data = request.json or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    try:
        from generators.imagen import ImagenGenerator
        task = {
            'id': f'narr_img_{uuid.uuid4().hex[:8]}',
            'status': 'pending',
            'progress': 0,
            'message': '',
            'mode': 'image',
        }
        filename = f"narr_img_{uuid.uuid4().hex[:8]}.png"
        out_path = str(UPLOAD_FOLDER / filename)

        gen = ImagenGenerator()
        gen.generate(task, prompt, 'imagen-3.0-fast-generate-001', '16:9', out_path)

        return jsonify({
            'filename': filename,
            'url': f'/api/uploads/{filename}',
        })
    except Exception as e:
        print(f"[Narration] ai-image error: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/narration', methods=['POST'])
def create_narration():
    """
    合成最终视频：接受 text + images(filenames) + voice + engine
    同步执行（通常几秒内完成），返回 video_url
    """
    data = request.json or {}
    text = data.get('text', '').strip()
    images = data.get('images', [])   # list of filenames in UPLOAD_FOLDER
    voice = data.get('voice', 'mimo_default')
    engine = data.get('engine', 'mimo')

    if not text:
        return jsonify({'error': 'Text is required'}), 400
    if not images:
        return jsonify({'error': 'At least one image is required'}), 400

    task_id = uuid.uuid4().hex[:10]

    # 解析语言
    lang = 'zh' if any(ord(c) > 127 for c in text) else 'en'

    # TTS
    audio_path = str(OUTPUT_FOLDER / f"narr_{task_id}_audio.mp3")
    if engine == 'gemini':
        ok = _tts_gemini(text, audio_path, voice)
    else:
        ok = _tts_gtts(text, audio_path, lang)

    if not ok:
        return jsonify({'error': 'TTS generation failed. Please install gtts: pip install gtts'}), 500

    # 解析图片路径
    image_paths = []
    for fname in images:
        p = UPLOAD_FOLDER / fname
        if p.exists():
            image_paths.append(str(p))

    if not image_paths:
        return jsonify({'error': 'No valid images found'}), 400

    # 合成视频
    output_filename = f"narr_{task_id}.mp4"
    output_path = str(OUTPUT_FOLDER / output_filename)
    success = _create_slideshow(image_paths, audio_path, output_path)

    # 清理音频
    try:
        os.remove(audio_path)
    except OSError:
        pass

    if not success:
        return jsonify({'error': 'Video synthesis failed. Please check ffmpeg is installed.'}), 500

    # 注册到 task_manager 以便 /api/download 可以工作
    from services import task_manager as tm
    fake_task = {
        'id': f'narr_{task_id}',
        'mode': 'narration',
        'prompt': text[:100],
        'model': 'narration',
        'ratio': '16:9',
        'status': 'completed',
        'progress': 100,
        'message': 'Complete!',
        'output_path': output_path,
        'created_at': __import__('datetime').datetime.now().isoformat(),
    }
    tm._tasks[f'narr_{task_id}'] = fake_task

    return jsonify({
        'task_id': f'narr_{task_id}',
        'video_url': f'/api/download/narr_{task_id}',
        'status': 'completed',
    })
