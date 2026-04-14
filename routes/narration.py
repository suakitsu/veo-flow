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
        import traceback
        
        print(f"[Gemini TTS] Starting with text: {text[:20]}...")
        
        client = texttospeech.TextToSpeechClient()
        print("[Gemini TTS] Client created")
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code='cmn-CN',
            name=f'cmn-CN-Wavenet-A',
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
        )
        print("[Gemini TTS] Sending request...")
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        print(f"[Gemini TTS] Response received, audio size: {len(response.audio_content)} bytes")
        
        with open(output_path, 'wb') as f:
            f.write(response.audio_content)
        print(f"[Gemini TTS] Audio saved to {output_path}")
        return True
    except Exception as e:
        print(f"[Gemini TTS] Error: {e}")
        print(f"[Gemini TTS] Traceback: {traceback.format_exc()}")
        print(f"[Narration] Gemini TTS error: {e}, falling back to gTTS")
        return _tts_gtts(text, output_path)


def _tts_openai(text: str, output_path: str, voice: str = 'alloy') -> bool:
    """使用 MiMo TTS API"""
    try:
        import requests
        import base64
        import json
        import datetime
        
        # 写入日志文件
        with open('tts_debug.log', 'a', encoding='utf-8') as log:
            log.write(f"\n[{datetime.datetime.now()}]\n")
            log.write(f"Received text: {text!r}\n")
            log.write(f"Text length: {len(text)}\n")
            log.write(f"Text bytes: {text.encode('utf-8')!r}\n")
        
        print(f"[_tts_openai] Received text: {text!r}")
        print(f"[_tts_openai] Text length: {len(text)}")
        print(f"[_tts_openai] Text bytes: {text.encode('utf-8')!r}")
        
        # 直接从 config.json 读取，避免线程问题
        with open('config.json', 'r') as f:
            cfg = json.load(f)
            key = cfg.get('api_key', '')
            base = cfg.get('api_base_url', 'https://api.xiaomimimo.com/v1')
        
        print(f"[TTS Debug] api_key present: {bool(key)}, base_url: {base}")
        if not key:
            print("[TTS Debug] No API key!")
            return False
            
        url = f"{base.rstrip('/')}/chat/completions"
        
        # MiMo TTS 使用 api-key header 和特殊格式
        headers = {
            "api-key": key,
            "Content-Type": "application/json"
        }
        
        # 映射 voice 到 MiMo 音色
        voice_map = {
            'alloy': 'mimo_default',
            'zh': 'default_zh',
            'en': 'default_eh'
        }
        mimo_voice = voice_map.get(voice, voice) if voice else 'mimo_default'
        
        payload = {
            "model": "mimo-v2-tts",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": text}
            ],
            "audio": {
                "format": "wav",
                "voice": mimo_voice
            }
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 解析 JSON 响应，提取音频数据
        data = response.json()
        if 'choices' in data and len(data['choices']) > 0:
            msg = data['choices'][0].get('message', {})
            if 'audio' in msg and 'data' in msg['audio']:
                audio_data = base64.b64decode(msg['audio']['data'])
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                return True
        
        print(f"[Narration] MiMo TTS: no audio data in response, msg keys: {msg.keys()}")
        return False
    except Exception as e:
        print(f"[Narration] MiMo TTS error: {e}")
        import traceback
        traceback.print_exc()
        return False


def _create_slideshow(image_paths: list, audio_path: str, output_path: str,
                      duration_per_image: float = None) -> bool:
    """
    将图片列表 + 音频 合成为幻灯片视频
    使用 imageio 生成视频，imageio-ffmpeg 合并音频
    """
    try:
        import imageio
        import numpy as np
        from PIL import Image
        import os
        import subprocess
        from imageio_ffmpeg import get_ffmpeg_exe

        # 获取音频时长（支持 WAV 和 MP3）
        audio_dur = 0
        if audio_path.endswith('.wav'):
            import wave
            with wave.open(audio_path, 'rb') as w:
                audio_dur = w.getnframes() / w.getframerate()
        elif audio_path.endswith('.mp3'):
            # 使用 ffprobe 获取 MP3 时长
            import subprocess
            import re
            result = subprocess.run([
                get_ffmpeg_exe(), '-i', audio_path
            ], capture_output=True, text=True)
            # 从 stderr 解析时长
            duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', result.stderr)
            if duration_match:
                h, m, s = map(float, duration_match.groups())
                audio_dur = h * 3600 + m * 60 + s
            else:
                # 默认时长
                audio_dur = 5.0
        else:
            # 默认时长
            audio_dur = 5.0

        if duration_per_image is None:
            duration_per_image = max(audio_dur / len(image_paths), 2.0)

        # 创建视频（无声）
        fps = 24
        total_frames = int(audio_dur * fps)
        frames_per_image = int(duration_per_image * fps)
        
        # 准备帧
        frames = []
        for img_path in image_paths:
            if os.path.exists(img_path):
                # 打开图片并调整大小
                img = Image.open(img_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # 调整大小为 1280x720
                img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                # 添加黑色背景
                bg = Image.new('RGB', (1280, 720), (0, 0, 0))
                # 居中粘贴
                x = (1280 - img.width) // 2
                y = (720 - img.height) // 2
                bg.paste(img, (x, y))
                
                # 转换为 numpy 数组
                frame = np.array(bg)
                # 重复帧以达到每张图片的时长
                for _ in range(frames_per_image):
                    frames.append(frame)
        
        if not frames:
            print("[Narration] No frames created")
            return False
        
        # 截断到音频时长
        frames = frames[:total_frames]
        
        # 保存无声视频
        temp_video = output_path.replace('.mp4', '_silent.mp4')
        imageio.mimsave(temp_video, frames, fps=fps, quality=8)
        
        # 使用 imageio-ffmpeg 合并视频和音频
        ffmpeg = get_ffmpeg_exe()
        subprocess.run([
            ffmpeg, '-y',
            '-i', temp_video,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            output_path
        ], check=True, capture_output=True)
        
        # 清理临时文件
        try:
            os.remove(temp_video)
        except:
            pass
        
        return True
    except Exception as e:
        print(f"[Narration] slideshow error: {e}")
        import traceback
        traceback.print_exc()
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
        # 使用 imagen-3.0-generate-002 模型（支持 enhance_prompt）
        gen.generate(task, prompt, 'imagen-3.0-generate-002', '16:9', out_path)

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
    engine = data.get('engine', 'openai')  # 默认使用 MiMo TTS

    # 调试信息
    print(f"[TTS Debug] Raw request data: {request.get_data(as_text=True)!r}")
    print(f"[TTS Debug] Parsed text: {text!r}")
    print(f"[TTS Debug] Text type: {type(text)}")
    print(f"[TTS Debug] Text bytes: {text.encode('utf-8')!r}")

    if not text:
        return jsonify({'error': 'Text is required'}), 400
    if not images:
        return jsonify({'error': 'At least one image is required'}), 400

    task_id = uuid.uuid4().hex[:10]
    
    print(f"[TTS Debug] Received text: {text!r}")
    print(f"[TTS Debug] Text length: {len(text)}")
    print(f"[TTS Debug] Text bytes: {text.encode('utf-8')!r}")

    # 解析语言
    lang = 'zh' if any(ord(c) > 127 for c in text) else 'en'

    # TTS
    # 根据引擎选择正确的音频格式扩展名
    audio_ext = '.mp3' if engine == 'gemini' else '.wav'
    audio_path = str(OUTPUT_FOLDER / f"narr_{task_id}_audio{audio_ext}")
    if engine == 'openai':
        ok = _tts_openai(text, audio_path, voice)
    elif engine == 'gemini':
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

    # 清理音频 - 临时禁用以便调试
    # try:
    #     os.remove(audio_path)
    # except OSError:
    #     pass

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
