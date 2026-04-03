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
- **长视频** — 自动分段，帧级衔接
- **延长视频** — 上传视频/尾帧，AI续画
- **图像生成** — Imagen 3 高质量图片
- **AI助手** — 分析参考图、优化提示词、对话

## 费用

| 模型 | 价格 | 说明 |
|------|------|------|
| Veo 3.1 | $0.40/秒 | 最新模型，质量最好 |
| Veo 3.1 Fast | $0.20/秒 | 速度快，性价比高 ⭐ |
| Veo 3 | $0.40/秒 | 稳定版 |
| Veo 2 | $0.50/秒 | 上一代，兼容性更好 |
| Imagen 3 | ~$0.04/张 | 高质量图像 |
| Imagen 3 Fast | ~$0.02/张 | 快速生成 |

**计费方式：** 按秒计费，不是按调用次数。8秒视频 = $3.20 (Veo 3.1)

生成前会显示预估费用，确认后才扣费。

## 快速开始

### 环境要求

- Python 3.8+
- FFmpeg（长视频拼接需要）
- GCP 服务账号，开启 Vertex AI API

### 配置步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置凭证
#    将 config.example.json 复制/重命名为 config.json 并填入项目ID。
#    将 GCP 服务账号真实密钥文件放入根目录，命名为 vertex.json。
#    (你可以参考 vertex.example.json 查看密钥格式)

```bash
# 3. 启动
python app.py
# 或双击 start.bat（Windows）

# 4. 打开 http://localhost:5000
```

## 项目结构

```
googleVideo/
├── app.py                 # 入口
├── config.py              # 配置
├── start.bat              # Windows启动脚本
│
├── generators/            # 核心生成逻辑
│   ├── veo.py            # Veo视频生成
│   └── imagen.py         # Imagen图像生成
│
├── routes/                # Flask路由
│   ├── generate.py       # /api/generate, /api/extend
│   ├── gemini.py         # AI助手接口
│   ├── tasks.py          # 任务状态和下载
│   └── proxy.py          # 代理配置
│
├── services/              # 业务逻辑
│   └── task_manager.py   # 任务状态、用户锁
│
├── templates/
│   └── index.html        # 网页界面
│
├── uploads/               # 上传文件
└── outputs/               # 生成结果
```

## API接口

| 方法 | 接口 | 说明 |
|------|------|------|
| `GET` | `/api/models` | 模型列表 |
| `POST` | `/api/generate` | 生成视频/图像 |
| `POST` | `/api/extend` | 延长现有视频 |
| `GET` | `/api/task/<id>` | 查询任务状态 |
| `GET` | `/api/download/<id>` | 下载结果 |
| `POST` | `/api/analyze-image` | 用Gemini分析图片 |
| `POST` | `/api/chat` | 与AI助手对话 |
| `POST` | `/api/refine-prompt` | 优化提示词 |

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
