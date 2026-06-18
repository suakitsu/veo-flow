"""
请求工具函数
"""

import os
from flask import request


def get_client_ip() -> str:
    """获取客户端真实 IP

    优先级：
    1. X-Forwarded-For 第一个 IP（Nginx/CDN 场景）
    2. X-Real-IP（部分代理设置）
    3. request.remote_addr（直连场景）

    注意：X-Forwarded-For 可被伪造，生产环境应配合可信代理白名单使用。
    可通过 TRUSTED_PROXIES 环境变量配置可信代理 IP（逗号分隔）。
    """
    # 可信代理白名单（空则信任所有 X-Forwarded-For）
    trusted_proxies = os.getenv('TRUSTED_PROXIES', '').split(',')
    trusted_proxies = [p.strip() for p in trusted_proxies if p.strip()]

    remote_addr = request.remote_addr or 'unknown'

    # 如果配置了可信代理，且当前请求来自可信代理，才使用 X-Forwarded-For
    if not trusted_proxies or remote_addr in trusted_proxies:
        # X-Forwarded-For: client, proxy1, proxy2 — 取第一个（最原始的客户端）
        xff = request.headers.get('X-Forwarded-For', '')
        if xff:
            # 取第一个 IP（最接近客户端的）
            client_ip = xff.split(',')[0].strip()
            if client_ip:
                return client_ip

        # X-Real-IP（Nginx 常用）
        xri = request.headers.get('X-Real-IP', '')
        if xri:
            return xri.strip()

    return remote_addr
