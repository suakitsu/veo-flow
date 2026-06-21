"""
请求工具函数
"""

import os
from flask import request


def get_client_ip() -> str:
    """获取客户端真实 IP

    优先级：
    1. X-Forwarded-For 第一个 IP（仅当请求来自可信代理时）
    2. X-Real-IP（仅当请求来自可信代理时）
    3. request.remote_addr（直连场景，默认）

    安全策略：
    - 默认不信任 X-Forwarded-For（避免伪造 IP 绕过并发锁）
    - 必须显式配置 TRUSTED_PROXIES 环境变量才启用 XFF 解析
    - TRUSTED_PROXIES 为逗号分隔的代理 IP 白名单
    """
    # 可信代理白名单
    # 默认为空 → 不信任任何 XFF，仅用 remote_addr（最安全）
    trusted_proxies_raw = os.getenv('TRUSTED_PROXIES', '')
    trusted_proxies = {p.strip() for p in trusted_proxies_raw.split(',') if p.strip()}

    remote_addr = request.remote_addr or 'unknown'

    # 仅当配置了可信代理，且当前请求来自可信代理时，才使用 XFF
    # 这样可以防止攻击者伪造 XFF 头绕过每用户并发锁
    if trusted_proxies and remote_addr in trusted_proxies:
        # X-Forwarded-For: client, proxy1, proxy2 — 取第一个（最原始的客户端）
        xff = request.headers.get('X-Forwarded-For', '')
        if xff:
            client_ip = xff.split(',')[0].strip()
            if client_ip:
                return client_ip

        # X-Real-IP（Nginx 常用）
        xri = request.headers.get('X-Real-IP', '')
        if xri:
            return xri.strip()

    # 默认返回直连 IP（不可伪造）
    return remote_addr
