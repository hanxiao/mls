# <img src="logo.svg" width="30" height="30" align="top"> MLS

**MLX Local Serving** — Unified local serving for ASR, TTS, and Translation on Apple Silicon.

![screenshot](screenshot.png)

## Purpose

This project exists primarily to empower **OpenClaw** with high-quality, local, privacy-first AI capabilities. It replaces cloud APIs for speech and translation, allowing the AI agent to:
1. **Hear** (ASR) via Qwen2.5-ASR
2. **Speak** (TTS) via Qwen2.5-TTS with custom accents (e.g., Beijing style)
3. **Translate** via TranslateGemma 12B without leaking data

## OpenClaw Integration

Add the following to your `~/.openclaw/openclaw.json` (or `TOOLS.md`) to enable the agent to use MLS:

### 1. Hearing (ASR)
Configure the `media` tool to use the CLI wrapper, which automatically tries the MLS server first (fast path) before falling back to cold start.

```json
{
  "tools": {
    "media": {
      "audio": {
        "enabled": true,
        "models": [
          {
            "type": "cli",
            "command": "~/Documents/mls/bin/qwen3-asr",
            "args": ["{{MediaPath}}"],
            "timeoutSeconds": 60
          }
        ]
      }
    }
  }
}
```

### 2. Speaking & Translating (Skills)
Since OpenClaw uses `curl` for these, register them in your `TOOLS.md` or `skills/` directory:

**TTS Skill Pattern:**
```bash
curl -X POST http://127.0.0.1:18321/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello",
    "instruct": "A young Chinese male speaker with a Beijing accent"
  }' > output.json
```

**Translate Skill Pattern:**
```bash
curl -X POST http://127.0.0.1:18321/translate \
  -H "Content-Type: application/json" \
  -d '{"q": "Text", "source": "en", "target": "zh"}'
```

## Features

- **ASR**: Qwen2.5-ASR (0.6B/1.7B) - Fast, accurate speech-to-text
- **TTS**: Qwen2.5-TTS (1.7B VoiceDesign) - Natural speech with instruct support
- **Translate**: TranslateGemma 12B - High-quality document translation (55+ languages)
- **Dashboard**: Unified web UI on port 18321 with accordion sidebar and mini-calendar

## Quick Start

**Install**
```bash
git clone https://github.com/hanxiao/mls ~/Documents/mls
cd ~/Documents/mls
uv sync
```

**Run Server**
```bash
uv run bin/server.py
# Server starts on http://127.0.0.1:18321
```

## API

### ASR
```bash
curl -X POST http://127.0.0.1:18321/transcribe \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/audio.ogg"}'
```

### TTS
```bash
curl -X POST http://127.0.0.1:18321/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "instruct": "Beijing accent"}' > output.json
```

### Translate
```bash
curl -X POST http://127.0.0.1:18321/translate \
  -H "Content-Type: application/json" \
  -d '{"q": "Hello world", "source": "en", "target": "zh"}'
```

## Models

All models run locally on Metal GPU via MLX.

- **ASR**: `mlx-community/Qwen2.5-ASR-0.6B-bf16`
- **TTS**: `mlx-community/Qwen2.5-TTS-12Hz-1.7B-VoiceDesign-bf16`
- **Translate**: `mlx-community/translategemma-12b-it-8bit`

## Requirements

- macOS 14+ with Apple Silicon
- Python 3.12+
- `uv` package manager
