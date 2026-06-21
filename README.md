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

- **Short Video** — 4/6/8 seconds choosing models and aspect ratios. Native audio + 4K support (Veo 3.1).
- **Long Video** — Auto-segmentation with frame-level continuity using frame-to-frame technology.
- **Extend Video** — Upload any video/last frame, the AI continues the scene naturally.
- **Narration (🎙️)** — Auto-mode (Topic to full video) or Manual-mode (Your photos + scripts).
  - Supports **Gemini TTS** (30 voices, 70+ languages, multi-speaker, style control) and **MiMo TTS** (Chinese optimized).
  - Auto-segment long text for TTS compatibility.
- **Storyboard (🎬)** — Multi-shot batch generation with auto-concatenation (FFmpeg).
- **Dashboard (📊)** — Track cost, success rates, and full generation history.
- **AI Image Generation (🖼️)** — Imagen 4 (Fast/Standard/Ultra) integration for custom images.
- **AI Assistant** — Image analysis, prompt refinement, creative chat with Gemini 3.5 Flash.
- **Prompt Templates** — 19+ Pro templates for products, anime, landscapes, etc.

## 💰 Pricing

| Model | Price | Notes |
|-------|-------|-------|
| Veo 3.1 | $0.40/sec | Latest model, best quality, 4K + native audio |
| Veo 3.1 Fast | $0.15/sec | Faster, better value ⭐ |
| Veo 3.1 Lite | $0.05/sec | Cheapest, ideal for iteration |
| Veo 3 | $0.40/sec | Stable release |
| Veo 2 | $0.50/sec | Legacy, better compatibility |
| Imagen 4 Ultra | $0.06/image | 2K output, best quality |
| Imagen 4 Standard | $0.04/image | Balanced |
| Imagen 4 Fast | $0.02/image | Quick generation ⭐ |
| Gemini TTS | from $0.50/$10 per 1M tokens | 30 voices, 70+ languages |

**Billing:** Per second of video, not per API call. 8-second clip = $3.20 (Veo 3.1), $1.20 (Veo 3.1 Fast), or $0.40 (Veo 3.1 Lite). Disabling native audio saves ~33%.

Cost estimate shown before every generation. Confirm to proceed.

## 🚀 Quick Start

### Requirements

- Python 3.10+ (required by google-genai SDK 1.x+)
- FFmpeg (for long video concatenation)
- GCP Service Account with Vertex AI API enabled

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
#    A. API Key Mode (for xiaomimimo/Third-party):
#       Edit config.json: set "api_key", "api_base_url", and "project_id".
#    B. Vertex AI Mode (Standard, Recommended):
#       Place your GCP service account key as vertex.json and set "project_id" in config.json.

# 3. Launch
python app.py
# Or double-click start.bat (Windows)

# 4. Open http://localhost:5000
```

### Docker Deployment (Production)

```bash
# 1. Prepare credentials
cp config.example.json config.json   # Edit to fill project_id
cp vertex.example.json vertex.json   # Edit to fill real service account key
cp .env.example .env                 # Edit as needed

# 2. Build and start
docker compose up -d --build

# 3. View logs
docker compose logs -f
```

Production uses gunicorn + gevent (supports SSE concurrency), runs as non-root user, port bound to 127.0.0.1 only (reverse proxy required).

### API Authentication

Set the `API_KEY` environment variable to require authentication for all write endpoints:

```bash
# Header-based (recommended)
curl -H "X-API-Key: your-secret-key" http://localhost:5000/api/generate
# Or
curl -H "Authorization: Bearer your-secret-key" http://localhost:5000/api/generate
```

Read-only endpoints (models, docs, task status, history) do not require authentication.

## 🏗️ Architecture

```
veo-flow/
├── app.py                 # Entry point
├── config.py              # Configuration
├── start.bat              # Windows launcher
├── Dockerfile             # Docker image (gunicorn + gevent)
├── docker-compose.yml     # Docker Compose
│
├── generators/            # Core generation logic
│   ├── veo.py            # Veo video generator (short/long/extend/interpolate)
│   ├── imagen.py         # Imagen image generator
│   ├── nano_banana.py    # Nano Banana image generator
│   └── client.py         # Unified GenAI client (Vertex AI / API Key dual mode)
│
├── routes/                # Flask Blueprints
│   ├── generate.py       # Short/Long/Image/Batch APIs
│   ├── narration.py      # TTS & Narration workflow
│   ├── gemini.py         # AI assistant endpoints
│   ├── nano_banana.py    # Nano Banana routes
│   ├── tasks.py          # Task status, SSE stream, download
│   ├── proxy.py          # Proxy configuration
│   └── docs.py           # OpenAPI docs
│
├── services/              # Business logic
│   ├── task_manager.py   # Task state, user locks, TTL cleanup
│   ├── history_manager.py# Thread-safe history & stats
│   ├── auth.py           # API Key auth middleware
│   ├── retry.py          # Exponential backoff retry
│   ├── request_utils.py  # Real IP extraction (XFF spoofing protection)
│   ├── file_security.py  # Upload security (path traversal, type validation)
│   ├── error_handler.py  # Unified error responses (no internal leak)
│   ├── cleanup.py        # Expired file cleanup
│   └── logger.py         # Structured logging
│
├── templates/
│   └── index.html        # Web UI
│
├── tests/                # Test suite
│   ├── test_app.py       # App entry tests
│   ├── test_auth.py      # Auth middleware tests
│   ├── test_config.py    # Config tests
│   ├── test_task_manager.py # Task manager tests
│   └── test_history_manager.py # History manager tests
│
├── docs/
│   └── openapi.yaml      # OpenAPI spec
│
├── uploads/               # Uploaded files
└── outputs/               # Generated results
```

## 📡 API Reference

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/generate` | Generate video/image | Required |
| `POST` | `/api/extend` | Extend video | Required |
| `POST` | `/api/interpolate` | First-last frame interpolation | Required |
| `POST` | `/api/batch` | Batch generation (Storyboard) | Required |
| `POST` | `/api/upload` | Upload file | Required |
| `POST` | `/api/narration` | TTS Video synthesis | Required |
| `POST` | `/api/narration/auto` | Auto narration workflow | Required |
| `POST` | `/api/narration/ai-image` | AI image for narration | Required |
| `POST` | `/api/analyze-image` | Analyze image with Gemini | Required |
| `POST` | `/api/chat` | Chat with Gemini | Required |
| `POST` | `/api/refine-prompt` | Refine prompt with Gemini | Required |
| `POST` | `/api/nano-banana/generate` | Nano Banana generation | Required |
| `POST` | `/api/history/clear` | Clear history | Required |
| `POST` | `/api/proxy` | Update proxy config | Required |
| `GET`  | `/api/models` | List available models | Public |
| `GET`  | `/api/history` | Get generation logs | Public |
| `GET`  | `/api/history/stats` | Get statistics | Public |
| `GET`  | `/api/templates` | List prompt templates | Public |
| `GET`  | `/api/tasks` | List all tasks | Public |
| `GET`  | `/api/task/<id>` | Get task status | Public |
| `GET`  | `/api/task/<id>/stream` | SSE task stream | Public |
| `GET`  | `/api/download/<id>` | Download file | Public |
| `GET`  | `/api/uploads/<filename>` | Serve uploaded file | Public |

## ⚙️ Configuration

### TTS Engines

| Engine | Requirements | Best For |
|--------|-------------|----------|
| `gemini` | GCP credentials or API key | 30 voices, 70+ languages, multi-speaker, style control ⭐ |
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
