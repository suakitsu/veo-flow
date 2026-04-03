"""
代理配置路由
"""

import os
from flask import Blueprint, request, jsonify

from config import proxy_config
from generators.client import reset_client

bp = Blueprint('proxy', __name__)


@bp.route('/api/proxy', methods=['GET'])
def get_proxy():
    """获取代理状态"""
    return jsonify(proxy_config)


@bp.route('/api/proxy', methods=['POST'])
def set_proxy():
    """设置代理"""
    data = request.json
    if 'enabled' in data:
        proxy_config['enabled'] = bool(data['enabled'])
    if 'address' in data:
        proxy_config['address'] = data['address'].strip()

    if proxy_config['enabled'] and proxy_config['address']:
        os.environ['HTTP_PROXY'] = proxy_config['address']
        os.environ['HTTPS_PROXY'] = proxy_config['address']
        os.environ['http_proxy'] = proxy_config['address']
        os.environ['https_proxy'] = proxy_config['address']
    else:
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(key, None)

    # 重置客户端使新代理生效
    reset_client()

    return jsonify({'success': True, **proxy_config})
