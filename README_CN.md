# Veo Flow 🎬

<p align="center">
  <b>AI视频生成工具，解决分段不连贯、延长突兀的问题</b><br>
  帧级衔接 · 原生视频延长 · AI提示词助手
</p>

<p align="center">
  <a href="README.md">English</a> | <b>中文</b>
</p>

---

## 解决了什么问题？

| 常见问题 | 本方案 |
|---------|--------|
| 长视频一段段生成，人物变来变去 | 自动提取每段最后一帧，下一段接着画 |
| 视频延长时画面跳一下 | 上传原视频或最后一帧，AI继续画 |
| 提示词写不好，生成效果差 | AI助手分析图片、优化提示词 |
| 点多了，账单爆炸 | 费用预估+任务锁，防止重复扣费 |

## 核心功能

- **短视频** — 4/6/8秒，选模型和比例
- **长视频** — 自动分段，各段最后一帧与下一段首帧级衔接，保持一致性
- **延长视频** — 上传视频/尾帧，AI原位续画
- **文配视频 (🎙️ NEW)** — 自动模式（输入主题出成片） or 手动模式（自选素材+配音）
  - 支持 **Gemini TTS**（情感 WaveNet 语音）和 **MiMo TTS**（中文优化）
  - 长文本自动分段，适配 TTS 限制
- **分镜编辑器 (🎬 NEW)** — 批量生成多个镜头，FFmpeg 自动合成
- **数据大屏 (📊 NEW)** — 实时费用统计、成功率监控、完整历史记录
- **AI生图 (🖼️ NEW)** — Imagen 3 集成，自定义图片生成
- **AI助手** — 分析参考图、优化提示词、对话建议
- **提示词模板** — 内置 19+ 套涵盖广告、动漫、风景、恐怖等专业模板

## 费用

| 模型 | 价格 | 说明 |
|------|------|------|
| Veo 3.1 | $0.40/秒 | 最新模型，质量最好 |
| Veo 3.1 Fast | $0.15/秒 | 速度快，性价比高 ⭐ |
| Veo 3.1 Lite | $0.10/秒 | 经济模式 |
| Veo 3 | $0.40/秒 | 稳定版 |
| Veo 3 Fast | $0.20/秒 | Veo 3 快速版 |
| Veo 2 | $0.50/秒 | 上一代，兼容性更好 |
| Imagen 4 Ultra | ~$0.06/张 | 最高质量 |
| Imagen 4 | ~$0.04/张 | 高质量图像 |
| Imagen 4 Fast | ~$0.02/张 | 快速生成 |

**计费方式：** 按秒计费，不是按调用次数。8秒视频 = $3.20 (Veo 3.1)

生成前会显示预估费用，确认后才扣费。

## 快速开始

### 环境要求

- Python 3.10+
- FFmpeg（长视频拼接需要）
- GCP 服务账号，开启 Vertex AI API

### 配置步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置凭证
#    方式 A：API Key 模式 (适用于"小米米莫"等中转平台)
#       编辑 config.json：填入 "api_key"、"api_base_url" 和 "project_id" 即可。
#    方式 B：Vertex AI 模式 (官方标准，推荐)
#       将 GCP 服务账号密钥保存为 vertex.json 放入根目录，并在 config.json 中填入 "project_id"。

# 3. 启动
python app.py
# 或双击 start.bat（Windows）

# 4. 打开 http://localhost:5000
```

### Docker 部署（生产环境推荐）

```bash
# 1. 准备凭证文件
cp config.example.json config.json   # 编辑填入 project_id
cp vertex.example.json vertex.json   # 编辑填入真实服务号密钥
cp .env.example .env                 # 编辑按需配置

# 2. 构建并启动
docker compose up -d --build

# 3. 查看日志
docker compose logs -f
```

生产环境使用 gunicorn + gevent（支持 SSE 并发），非 root 用户运行，端口仅绑定 127.0.0.1（需反向代理）。

### API 鉴权

设置环境变量 `API_KEY` 后，所有写操作端点需要鉴权：

```bash
# 请求头方式（推荐）
curl -H "X-API-Key: your-secret-key" http://localhost:5000/api/generate
# 或
curl -H "Authorization: Bearer your-secret-key" http://localhost:5000/api/generate
```

只读端点（模型列表、文档、任务查询、历史查看）无需鉴权。

## 项目结构

```
veo-flow/
├── app.py                 # 入口
├── config.py              # 配置
├── start.bat              # Windows启动脚本
├── Dockerfile             # Docker 镜像构建（gunicorn + gevent）
├── docker-compose.yml     # Docker Compose 编排
│
├── generators/            # 核心生成逻辑
│   ├── veo.py            # Veo视频生成（短/长/延长/插值）
│   ├── imagen.py         # Imagen图像生成
│   ├── nano_banana.py    # Nano Banana 图像生成
│   └── client.py         # 统一 GenAI 客户端管理（Vertex AI / API Key 双模式）
│
├── routes/                # Flask蓝图
│   ├── generate.py       # 短/长/图/批量分镜接口
│   ├── narration.py      # 配音与自动出片工作流
│   ├── gemini.py         # AI助手接口
│   ├── nano_banana.py    # Nano Banana 路由
│   ├── tasks.py          # 任务状态、SSE 流、下载
│   ├── proxy.py          # 代理控制
│   └── docs.py           # OpenAPI 文档服务
│
├── services/              # 服务层
│   ├── task_manager.py   # 任务状态、用户锁、TTL 清理
│   ├── history_manager.py# 线程安全记录与统计服务
│   ├── auth.py           # API Key 鉴权中间件
│   ├── retry.py          # 指数退避重试机制
│   ├── request_utils.py  # 真实 IP 获取（防 XFF 伪造）
│   ├── file_security.py  # 文件上传安全（路径穿越防护、类型校验）
│   ├── error_handler.py  # 统一错误响应（不泄露内部异常）
│   ├── cleanup.py        # 过期文件清理
│   └── logger.py         # 结构化日志
│
├── templates/
│   └── index.html        # 网页界面
│
├── tests/                # 测试套件
│   ├── test_app.py       # 应用入口测试
│   ├── test_auth.py      # 鉴权中间件测试
│   ├── test_config.py    # 配置测试
│   ├── test_task_manager.py # 任务管理测试
│   └── test_history_manager.py # 历史记录测试
│
├── docs/
│   └── openapi.yaml      # OpenAPI 规范
│
├── uploads/               # 上传文件
└── outputs/               # 生成结果
```

## API接口

| 方法 | 接口 | 说明 |
|------|------|------|
| `POST` | `/api/generate` | 普通生成 |
| `POST` | `/api/batch` | 批量分镜生成 |
| `POST` | `/api/narration` | 配音视频合成接口 |
| `GET`  | `/api/history` | 查询费用与审计历史 |
| `GET`  | `/api/templates` | 提示词模板列表 |
| `GET`  | `/api/task/<id>` | 任务状态查询 |
| `POST` | `/api/analyze-image`| Gemini 图片分析 |

## 配置说明

### TTS 引擎选择

| 引擎 | 要求 | 适用场景 |
|------|------|---------|
| `gemini` | GCP 凭证 (`vertex.json`) | 情感语音，英文 |
| `openai` | MiMo API key | 中文，无需翻墙 |
| `gtts` | 网络 + gtts 包 | 备用方案 |

**配置示例** (`config.json`):
```json
{
  "project_id": "your-gcp-project",
  "credentials": "vertex.json",
  "api_key": "your-mimo-key",
  "api_base_url": "https://api.xiaomimimo.com/v1"
}
```

### PowerShell UTF-8 编码 (Windows)

中文支持需要设置编码：
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

### TTS 字数限制

- **MiMo TTS**: 每段约 40-50 汉字（长文本自动分段）
- **Gemini TTS**: 限制更高，英文效果更好

## 代理配置

左下角内置代理面板，默认：`http://127.0.0.1:7897`

或通过环境变量设置：
```bash
set HTTP_PROXY=http://你的代理:端口
set HTTPS_PROXY=http://你的代理:端口
```

## 重要提示

- **计费：** 按生成内容的秒数计费。云端生成一旦开始，关闭浏览器无法取消。
- **任务锁：** 每个IP同时只能有一个任务，防止误操作重复扣费。
- **费用预估：** 每次生成前显示预估费用，确认后再扣费。

## 许可证

[MIT](LICENSE) © 2026 suakitsu
