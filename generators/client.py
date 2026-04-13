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
        api_key = api_config.get('api_key')
        
        if api_key:
            # API Key 模式 (适用于 Google AI Studio 或中转服务)
            # 注意：某些中转需要设置 base_url，SDK 0.3.0 目前对 base_url 支持有限
            # 我们直接初始化，由 SDK 查找环境变量或配置
            _client = genai.Client(
                api_key=api_key,
                # 如果是中转地址，官方 SDK 可能不支持，需注意
            )
        else:
            # 默认：Vertex AI 模式 (需要 vertex.json)
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
