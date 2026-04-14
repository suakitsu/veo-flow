"""
GenAI 客户端管理（单例模式）
"""

import os
from google import genai


_client = None


def get_client():
    """获取或创建 Gen AI 客户端（单例）"""
    global _client
    if _client is None:
        from config import api_config
        
        # 优先检查 Vertex AI 凭证
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        
        if cred_path and os.path.exists(cred_path):
            # Vertex AI 模式 (需要 vertex.json)
            project_id = os.getenv('GCP_PROJECT_ID', 'vertex-free-300')
            print(f"[GenAI Client] Using Vertex AI mode, project: {project_id}")
            _client = genai.Client(
                vertexai=True,
                project=project_id,
                location="us-central1",
            )
        else:
            # API Key 模式 (适用于 Google AI Studio 或中转服务)
            api_key = api_config.get('api_key')
            print(f"[GenAI Client] Using API Key mode")
            _client = genai.Client(
                api_key=api_key,
            )
    return _client


def reset_client():
    """重置客户端（代理变更后调用）"""
    global _client
    _client = None
