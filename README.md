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

- **Short Video** — 4/6/8 seconds choosing models and aspect ratios.
- **Long Video** — Auto-segmentation with frame-level continuity using frame-to-frame technology.
- **Extend Video** — Upload any video/last frame, the AI continues the scene naturally.
- **Narration (🎙️ NEW)** — Auto-mode (Topic to full video) or Manual-mode (Your photos + scripts).
  - Supports **Gemini TTS** (emotional WaveNet voices) and **MiMo TTS** (Chinese optimized).
  - Auto-segment long text for TTS compatibility.
- **Storyboard (🎬 NEW)** — Multi-shot batch generation with auto-concatenation (FFmpeg).
- **Dashboard (📊 NEW)** — Track cost, success rates, and full generation history.
- **AI Image Generation (🖼️ NEW)** — Imagen 3 integration for custom images.
- **AI Assistant** — Image analysis, prompt refinement, creative chat with Gemini.
- **Prompt Templates** — 19+ Pro templates for products, anime, landscapes, etc.

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
#    A. API Key Mode (Recommended for xiaomimimo/Third-party):
#       Edit config.json: set "api_key", "api_base_url", and "project_id".
#    B. Vertex AI Mode (Standard):
#       Place your GCP service account key as vertex.json and set "project_id" in config.json.

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
│   ├── imagen.py         # Imagen image generator
│   └── client.py         # Unified GenAI client
│
├── routes/                # Flask Blueprints
│   ├── generate.py       # Short/Long/Image/Batch APIs
│   ├── narration.py      # TTS & Narration workflow
│   ├── gemini.py         # AI assistant endpoints
│   ├── tasks.py          # Task status & download
│   └── proxy.py          # Proxy configuration
│
├── services/              # Business logic
│   ├── task_manager.py   # Task state, user locks
│   └── history_manager.py# Thread-safe history & stats
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
| `POST` | `/api/generate` | Generate video/image |
| `POST` | `/api/batch` | Batch generation (Storyboard) |
| `POST` | `/api/narration` | TTS Video synthesis |
| `GET`  | `/api/history` | Get generation logs |
| `GET`  | `/api/templates` | List prompt templates |
| `GET`  | `/api/task/<id>` | Get task status |
| `POST` | `/api/analyze-image`| Analyze image with Gemini |

## ⚙️ Configuration

### TTS Engines

| Engine | Requirements | Best For |
|--------|-------------|----------|
| `gemini` | GCP credentials (`vertex.json`) | Emotional voices, English |
| `openai` | MiMo API key | Chinese text, no VPN needed |
| `gtts` | Internet + gtts package | Fallback option |

**Config example** (`config.json`):
```json
{
  "project_id": "your-gcp-project",
  "credentials": "vertex.json",
  "api_key": "your-mimo-key",
  "api_base_url": "https://api.xiaomimimo.com/v1"
}
```

### PowerShell UTF-8 (Windows)

For Chinese text support, set encoding before requests:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

### TTS Character Limits

- **MiMo TTS**: ~40-50 characters per request (auto-segmented for longer text)
- **Gemini TTS**: Higher limits, better for English

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
