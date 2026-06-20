#!/bin/bash
# Re-download all MLS models to the vault drive in the layouts bin/server.py expects.
# Logs each step; continues past individual failures.
set -u
export HF_HOME="/Volumes/vault/ai-models/huggingface"
HF="/Users/hanxiao/Documents/mls/.venv/bin/hf"
VAULT="/Volumes/vault"
LOG() { echo "$(date '+%H:%M:%S') $*"; }

# repo -> HF cache (loaded by repo id via mlx-audio / huggingface_hub)
CACHE_REPOS=(
  "mlx-community/Qwen3-ASR-1.7B-8bit"
  "mlx-community/Qwen3-ASR-0.6B-bf16"
  "mlx-community/whisper-large-v3-turbo-asr-fp16"
  "mlx-community/whisper-large-v3-asr-8bit"
  "jinaai/jina-embeddings-v5-omni-small-mlx"
)

# repo -> flat local dir  (format: "repo|abs_dir")
LOCAL_REPOS=(
  "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16|$VAULT/ai-models/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"
  "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16|$VAULT/ai-models/mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16"
  "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit|$VAULT/ai-models/mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit"
  "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16|$VAULT/ai-models/mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
  "mlx-community/translategemma-12b-it-8bit|$VAULT/ai-models/mlx-community/translategemma-12b-it-8bit"
  "jinaai/jina-vlm-mlx|$VAULT/ai-models/jinaai/jina-vlm-mlx"
)

LOG "=== HF-cache models (HF_HOME=$HF_HOME) ==="
for r in "${CACHE_REPOS[@]}"; do
  LOG ">> cache: $r"
  "$HF" download "$r" >/dev/null 2>>/tmp/mls_dl_err.log && LOG "   OK $r" || LOG "   FAIL $r"
done

LOG "=== flat local-dir models ==="
for entry in "${LOCAL_REPOS[@]}"; do
  repo="${entry%%|*}"; dir="${entry##*|}"
  LOG ">> local: $repo -> $dir"
  "$HF" download "$repo" --local-dir "$dir" >/dev/null 2>>/tmp/mls_dl_err.log && LOG "   OK $repo" || LOG "   FAIL $repo"
done

LOG "=== DONE. Disk usage: ==="
du -sh "$VAULT/ai-models" 2>/dev/null
echo "ALL_DOWNLOADS_COMPLETE"
