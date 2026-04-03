"""
GenAI 客户端管理（单例模式）
"""

import os
from google import genai


_client = None


def get_client():
    """获取或创建 Gen AI 客户端（线程安全的单例）"""
    global _client
    if _client is None:
        project_id = os.getenv('GCP_PROJECT_ID', 'vertex-free-300')
        _client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1",
        )
    return _client


def reset_client():
    """重置客户端（代理变更后调用）"""
    global _client
    _client = None
