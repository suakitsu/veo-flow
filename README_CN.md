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
- **分镜编辑器 (🎬 NEW)** — 批量生成多个镜头，FFmpeg 自动合成
- **数据大屏 (📊 NEW)** — 实时费用统计、成功率监控、完整历史记录
- **AI助手** — 分析参考图、优化提示词、对话建议
- **提示词模板** — 内置 19+ 套涵盖广告、动漫、风景、恐怖等专业模板

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
#    方式 A：API Key 模式 (推荐，适用于“小米米莫”等中转平台)
#       编辑 config.json：填入 "api_key"、"api_base_url" 和 "project_id" 即可。
#    方式 B：Vertex AI 模式 (官方标准)
#       将 GCP 服务账号密钥保存为 vertex.json 放入根目录，并在 config.json 中填入 "project_id"。

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
│   ├── imagen.py         # Imagen图像生成
│   └── client.py         # 统一 GenAI 客户端管理
│
├── routes/                # Flask蓝图
│   ├── generate.py       # 短/长/图/批量分镜接口
│   ├── narration.py      # 配音与自动出片工作流
│   ├── gemini.py         # AI助手接口
│   ├── tasks.py          # 任务状态和下载
│   └── proxy.py          # 代理控制
│
├── services/              # 服务层
│   ├── task_manager.py   # 任务状态、用户锁锁
│   └── history_manager.py# 线程安全记录与统计服务
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
| `POST` | `/api/generate` | 普通生成 |
| `POST` | `/api/batch` | 批量分镜生成 |
| `POST` | `/api/narration` | 配音视频合成接口 |
| `GET`  | `/api/history` | 查询费用与审计历史 |
| `GET`  | `/api/templates` | 提示词模板列表 |
| `GET`  | `/api/task/<id>` | 任务状态查询 |
| `POST` | `/api/analyze-image`| Gemini 图片分析 |

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
