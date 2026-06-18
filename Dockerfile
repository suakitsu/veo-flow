FROM python:3.11-slim

# 安装 ffmpeg（长视频拼接必需）和系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/uploads /app/outputs /app/logs

# 暴露端口
EXPOSE 5000

# 环境变量默认值
ENV FLASK_DEBUG=false
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/models')" || exit 1

# 启动命令
CMD ["python", "app.py"]
