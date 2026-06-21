FROM python:3.11-slim

# 安装 ffmpeg（长视频拼接必需）和系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建非 root 用户（最小权限原则）
RUN useradd -r -u 1000 -m -d /home/app -s /sbin/nologin app \
    && mkdir -p /app/uploads /app/outputs /app/logs \
    && chown -R app:app /app

# 复制项目代码（.dockerignore 已排除密钥文件）
COPY --chown=app:app . .

# 切换到非 root 用户
USER app

# 暴露端口
EXPOSE 5000

# 环境变量默认值
ENV FLASK_DEBUG=false
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/models')" || exit 1

# 生产环境使用 gunicorn + gevent（支持 SSE 长连接并发）
# gevent worker 支持 SSE 流式响应；timeout=0 避免长任务被杀
CMD ["gunicorn", "-k", "gevent", "-w", "4", "--timeout", "120", "-b", "0.0.0.0:5000", "app:app"]
