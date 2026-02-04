#!/usr/bin/env python3
"""
Persistent Qwen3-ASR transcription server.
Keeps model loaded in memory for fast inference.
Saves transcription history to ~/Documents/qwen3-asr-history/history/
"""
import os
import sys
import tempfile
import subprocess
import time
import json
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Lazy imports for mlx_audio (heavy)
model = None
load_fn = None
generate_fn = None

MODEL_NAME = "mlx-community/Qwen3-ASR-0.6B-bf16"
HOST = "127.0.0.1"
PORT = 18321
PROJECT_DIR = Path(__file__).parent.parent.resolve()
HISTORY_DIR = PROJECT_DIR / "history"

app = FastAPI(title="Qwen3-ASR Server")

def save_to_history(audio_path: str, text: str, duration_ms: float):
    """Save transcription to history."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    day_dir = HISTORY_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    # Copy audio file
    audio_src = Path(audio_path)
    audio_dest = day_dir / audio_src.name
    try:
        shutil.copy2(audio_src, audio_dest)
    except Exception as e:
        print(f"Warning: could not copy audio file: {e}")
        return

    # Append to transcripts.jsonl
    record = {
        "timestamp": now.isoformat(),
        "audio_file": audio_src.name,
        "text": text,
        "duration_ms": round(duration_ms, 2)
    }
    jsonl_path = day_dir / "transcripts.jsonl"
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

class TranscribeRequest(BaseModel):
    path: str
    language: str = "zh"

class TranscribeResponse(BaseModel):
    text: str
    latency_ms: float

def load_model():
    """Load model once at startup."""
    global model, load_fn, generate_fn

    print(f"Loading model {MODEL_NAME}...")
    start = time.time()

    from mlx_audio.stt import load
    from mlx_audio.stt.generate import generate_transcription

    load_fn = load
    generate_fn = generate_transcription
    model = load(MODEL_NAME)

    elapsed = time.time() - start
    print(f"Model loaded in {elapsed:.2f}s")
    return model

def convert_to_wav(audio_path: str) -> str:
    """Convert audio to 16kHz mono WAV for best results."""
    wav_path = tempfile.mktemp(suffix=".wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path,
        "-ar", "16000", "-ac", "1", wav_path
    ], capture_output=True)
    return wav_path

@app.on_event("startup")
async def startup_event():
    load_model()

@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_NAME, "loaded": model is not None}

@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(req: TranscribeRequest):
    global model

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not os.path.exists(req.path):
        raise HTTPException(status_code=400, detail=f"Audio file not found: {req.path}")

    start = time.time()

    # Convert to WAV
    wav_path = convert_to_wav(req.path)

    try:
        # Use a temp file for output
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            output_path = f.name.replace(".txt", "")

        # Generate transcription using the loaded model
        segments = generate_fn(
            model=model,
            audio=wav_path,
            output_path=output_path,
            format="txt",
            verbose=False,
            language=req.language
        )

        # Read the output
        txt_file = output_path + ".txt"
        if os.path.exists(txt_file):
            with open(txt_file, "r") as f:
                text = f.read().strip()
            os.unlink(txt_file)
        else:
            # Try to extract from segments directly
            if segments:
                text = " ".join(s.get("text", "") for s in segments if isinstance(s, dict))
            else:
                text = str(segments) if segments else ""

    finally:
        # Cleanup
        if os.path.exists(wav_path):
            os.unlink(wav_path)

    latency_ms = (time.time() - start) * 1000

    # Save to history
    if text:
        save_to_history(req.path, text, latency_ms)

    return TranscribeResponse(text=text, latency_ms=latency_ms)

@app.get("/api/dates")
async def get_dates():
    """Get list of dates with transcription history."""
    dates = []
    if HISTORY_DIR.exists():
        for d in sorted(HISTORY_DIR.iterdir(), reverse=True):
            if d.is_dir() and (d / "transcripts.jsonl").exists():
                dates.append(d.name)
    return JSONResponse(dates)

@app.get("/api/transcripts/{date}")
async def get_transcripts(date: str):
    """Get transcripts for a specific date."""
    jsonl_path = HISTORY_DIR / date / "transcripts.jsonl"
    if not jsonl_path.exists():
        raise HTTPException(status_code=404, detail="No transcripts for this date")

    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return JSONResponse(records)

@app.get("/audio/{date}/{filename}")
async def get_audio(date: str, filename: str):
    """Serve audio file."""
    audio_path = HISTORY_DIR / date / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, media_type="audio/ogg")

HISTORY_HTML = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASR History</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a1a; color: #e0e0e0; }
        .container { display: flex; height: 100vh; }
        .sidebar { width: 200px; background: #252525; border-right: 1px solid #333; overflow-y: auto; }
        .main { flex: 1; padding: 20px; overflow-y: auto; }
        h1 { padding: 20px; font-size: 18px; border-bottom: 1px solid #333; }
        .date-item { padding: 12px 20px; cursor: pointer; border-bottom: 1px solid #333; }
        .date-item:hover { background: #333; }
        .date-item.active { background: #0066cc; }
        .transcript { background: #252525; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
        .transcript-time { color: #888; font-size: 12px; margin-bottom: 5px; }
        .transcript-text { font-size: 15px; line-height: 1.5; }
        .transcript-meta { color: #666; font-size: 11px; margin-top: 8px; }
        .play-btn { background: #0066cc; color: white; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; margin-top: 8px; }
        .play-btn:hover { background: #0077ee; }
        audio { width: 100%; margin-top: 8px; height: 32px; }
        .empty { color: #666; text-align: center; padding: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>ASR History</h1>
            <div id="dates"></div>
        </div>
        <div class="main">
            <div id="transcripts"><div class="empty">Select a date</div></div>
        </div>
    </div>
    <script>
        let currentDate = null;
        let currentAudio = null;

        async function loadDates() {
            const res = await fetch('/api/dates');
            const dates = await res.json();
            const container = document.getElementById('dates');
            if (dates.length === 0) {
                container.innerHTML = '<div class="empty">No history</div>';
                return;
            }
            container.innerHTML = dates.map(d =>
                `<div class="date-item" data-date="${d}">${d}</div>`
            ).join('');
            container.querySelectorAll('.date-item').forEach(el => {
                el.onclick = () => loadTranscripts(el.dataset.date);
            });
            loadTranscripts(dates[0]);
        }

        async function loadTranscripts(date) {
            currentDate = date;
            document.querySelectorAll('.date-item').forEach(el => {
                el.classList.toggle('active', el.dataset.date === date);
            });
            const res = await fetch(`/api/transcripts/${date}`);
            const records = await res.json();
            const container = document.getElementById('transcripts');
            if (records.length === 0) {
                container.innerHTML = '<div class="empty">No transcripts</div>';
                return;
            }
            container.innerHTML = records.map((r, i) => {
                const time = new Date(r.timestamp).toLocaleTimeString('zh-CN');
                return `
                    <div class="transcript">
                        <div class="transcript-time">${time}</div>
                        <div class="transcript-text">${escapeHtml(r.text)}</div>
                        <div class="transcript-meta">${r.audio_file} - ${r.duration_ms.toFixed(0)}ms</div>
                        <button class="play-btn" onclick="playAudio('${date}', '${r.audio_file}', this)">Play</button>
                    </div>
                `;
            }).join('');
        }

        function playAudio(date, filename, btn) {
            if (currentAudio) { currentAudio.pause(); currentAudio.remove(); }
            const audio = document.createElement('audio');
            audio.src = `/audio/${date}/${filename}`;
            audio.controls = true;
            audio.autoplay = true;
            btn.parentNode.appendChild(audio);
            currentAudio = audio;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        loadDates();
    </script>
</body>
</html>
"""

@app.get("/history", response_class=HTMLResponse)
async def history_page():
    """Serve the history viewer HTML page."""
    return HISTORY_HTML

if __name__ == "__main__":
    print(f"Starting Qwen3-ASR server on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
