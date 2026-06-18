"""
API 文档路由 - 提供 Swagger UI 和 OpenAPI 规范
"""

from pathlib import Path
from flask import Blueprint, send_file, jsonify

bp = Blueprint('docs', __name__)

_OPENAPI_PATH = Path(__file__).parent.parent / 'docs' / 'openapi.yaml'


@bp.route('/api/docs/openapi.yaml')
def get_openapi_spec():
    """返回 OpenAPI 规范文件"""
    if _OPENAPI_PATH.exists():
        return send_file(_OPENAPI_PATH, mimetype='application/yaml')
    return jsonify({'error': 'OpenAPI spec not found'}), 404


@bp.route('/api/docs')
@bp.route('/api/docs/')
def swagger_ui():
    """内嵌 Swagger UI 页面"""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Veo Flow API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>body { margin: 0; }</style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: '/api/docs/openapi.yaml',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [SwaggerUIBundle.presets.apis],
                layout: 'BaseLayout',
            });
        };
    </script>
</body>
</html>'''
    return html, 200, {'Content-Type': 'text/html'}
