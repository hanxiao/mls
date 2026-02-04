# Qwen3-ASR History

Local speech-to-text transcription server using Qwen3-ASR on Apple Silicon via MLX. Keeps the model loaded in memory for fast inference and saves transcription history with audio files.

## Requirements

- macOS with Apple Silicon (M1/M2/M3)
- Python 3.12+
- ffmpeg (for audio conversion)

## Installation

```bash
# Clone and setup
cd ~/Documents/qwen3-asr-history
./setup.sh
```

This will:
1. Create a Python virtual environment
2. Install dependencies (mlx-audio, fastapi, uvicorn)
3. Install the launchd service for automatic startup
4. Symlink the wrapper script to ~/.local/bin/

## Usage

### CLI wrapper

```bash
# Transcribe audio file (Chinese by default)
qwen3-asr recording.ogg

# Specify language
qwen3-asr recording.ogg en
```

### API endpoints

The server runs on `http://127.0.0.1:18321`:

- `GET /health` - Health check
- `POST /transcribe` - Transcribe audio file
  ```json
  {"path": "/absolute/path/to/audio.ogg", "language": "zh"}
  ```
- `GET /history` - Web UI for browsing transcription history
- `GET /api/dates` - List dates with transcripts
- `GET /api/transcripts/{date}` - Get transcripts for a date
- `GET /audio/{date}/{filename}` - Serve audio file

### Service management

```bash
# Check service status
launchctl list | grep qwen3-asr

# Stop service
launchctl unload ~/Library/LaunchAgents/ai.openclaw.qwen3-asr.plist

# Start service
launchctl load ~/Library/LaunchAgents/ai.openclaw.qwen3-asr.plist

# View logs
tail -f ~/Documents/qwen3-asr-history/logs/server.log
```

## Data

Transcription history is stored in `./history/` with the following structure:

```
history/
  2026-02-03/
    transcripts.jsonl    # Transcript records
    recording-001.ogg    # Original audio files
    recording-002.ogg
```

Each line in `transcripts.jsonl`:
```json
{"timestamp": "2026-02-03T10:30:00", "audio_file": "recording-001.ogg", "text": "...", "duration_ms": 234.5}
```
