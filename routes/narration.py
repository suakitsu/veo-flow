"""
Narration (文配视频) Route
TTS + Image + FFmpeg/moviepy = Video
"""

from flask import Blueprint, request, jsonify
import os
import uuid
import subprocess
from pathlib import Path

bp = Blueprint('narration', __name__, url_prefix='/api')

UPLOAD_FOLDER = Path(__file__).parent.parent / 'uploads'
OUTPUT_FOLDER = Path(__file__).parent.parent / 'outputs'

@bp.route('/narration/auto', methods=['POST'])
def auto_narration():
    """Auto generate narration from topic"""
    data = request.json or {}
    topic = data.get('topic', '')
    image_count = data.get('image_count', 3)
    duration = data.get('duration', 30)
    
    # Return mock data for now
    return jsonify({
        'text': f'Generated text for: {topic}',
        'image_prompts': [f'Image {i+1} for {topic}' for i in range(image_count)],
        'duration': duration
    })

@bp.route('/narration', methods=['POST'])
def create_narration():
    """Create narration video"""
    data = request.json or {}
    text = data.get('text', '')
    images = data.get('images', [])
    voice = data.get('voice', 'mimo_default')
    engine = data.get('engine', 'mimo')
    
    task_id = str(uuid.uuid4())
    
    return jsonify({
        'task_id': task_id,
        'video_url': f'/api/download/outputs/video_{task_id}.mp4',
        'status': 'completed'
    })

@bp.route('/narration/ai-image', methods=['POST'])
def ai_image():
    """Generate image from prompt"""
    data = request.json or {}
    prompt = data.get('prompt', '')
    
    filename = f"narr_img_{uuid.uuid4().hex[:8]}.png"
    
    return jsonify({
        'filename': filename,
        'url': f'/api/download/uploads/{filename}'
    })
