# Veo Flow 🎬

<p align="center">
  <b>AI video generation tool that fixes segmentation and extension issues</b><br>
  Seamless frame-to-frame continuity · Native video extension · AI prompt assistant
</p>

<p align="center">
  <b>English</b> | <a href="README_CN.md">中文</a>
</p>

---

## 🤔 Problems Solved

| Common Issue | Our Solution |
|-------------|--------------|
| Long video segments don't match, characters change | Auto-extract last frame, feed to next generation |
| Video extension has jarring cuts | Upload source video or last frame, AI continues the scene |
| Poor prompts, bad results | AI assistant analyzes images, refines prompts |
| Accidental double-billing | Cost estimate + task lock prevents duplicate charges |

## ✨ Features

- **Short Video** — 4/6/8 seconds, choose model and aspect ratio
- **Long Video** — Auto-segmentation with frame-level continuity
- **Extend Video** — Upload video/last frame, AI continues naturally
- **Image Generation** — Imagen 3 for high-quality stills
- **AI Assistant** — Image analysis, prompt refinement, creative chat

## 💰 Pricing

| Model | Price | Notes |
|-------|-------|-------|
| Veo 3.1 | $0.40/sec | Latest model, best quality |
| Veo 3.1 Fast | $0.20/sec | Faster, better value ⭐ |
| Veo 3 | $0.40/sec | Stable release |
| Veo 2 | $0.50/sec | Legacy, better compatibility |
| Imagen 3 | ~$0.04/image | High quality |
| Imagen 3 Fast | ~$0.02/image | Quick generation |

**Billing:** Per second of video, not per API call. 8-second clip = $3.20 (Veo 3.1)

Cost estimate shown before every generation. Confirm to proceed.

## 🚀 Quick Start

### Requirements

- Python 3.8+
- FFmpeg (for long video concatenation)
- GCP Service Account with Vertex AI API enabled

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
#    Rename config.example.json to config.json and fill in your GCP project ID.
#    Place your authentic GCP service account key as vertex.json.
#    (You can refer to vertex.example.json for the required format)

```bash
# 3. Launch
python app.py
# Or double-click start.bat (Windows)

# 4. Open http://localhost:5000
```

## 🏗️ Architecture

```
googleVideo/
├── app.py                 # Entry point
├── config.py              # Configuration
├── start.bat              # Windows launcher
│
├── generators/            # Core generation logic
│   ├── veo.py            # Veo video generator
│   └── imagen.py         # Imagen image generator
│
├── routes/                # Flask Blueprints
│   ├── generate.py       # /api/generate, /api/extend
│   ├── gemini.py         # AI assistant endpoints
│   ├── tasks.py          # Task status & download
│   └── proxy.py          # Proxy configuration
│
├── services/              # Business logic
│   └── task_manager.py   # Task state, user locks
│
├── templates/
│   └── index.html        # Web UI
│
├── uploads/               # Uploaded files
└── outputs/               # Generated results
```

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/models` | List Veo models |
| `POST` | `/api/generate` | Generate video/image |
| `POST` | `/api/extend` | Extend existing video |
| `GET` | `/api/task/<id>` | Get task status |
| `GET` | `/api/download/<id>` | Download result |
| `POST` | `/api/analyze-image` | Analyze image with Gemini |
| `POST` | `/api/chat` | Chat with AI assistant |
| `POST` | `/api/refine-prompt` | Refine prompt with Gemini |

## ⚙️ Proxy Configuration

Built-in proxy panel (bottom-left corner). Default: `http://127.0.0.1:7897`

Or set via environment:
```bash
set HTTP_PROXY=http://your-proxy:port
set HTTPS_PROXY=http://your-proxy:port
```

## ⚠️ Important Notes

- **Billing:** Per second of generated content. Once cloud generation starts, it cannot be cancelled by closing the browser.
- **Task Lock:** One active task per IP to prevent accidental double-billing.
- **Cost Estimate:** Always shown before generation. Check before confirming.

## 📄 License

[MIT](LICENSE) © 2026 suakitsu
