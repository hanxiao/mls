"""Standalone test of the Han voice clone - mirrors server.py's Han-branch generate path.
Does NOT touch the running MLS server. Writes /tmp/han_voice_test.wav to listen to."""
import time, numpy as np, soundfile as sf
from mlx_audio.tts.utils import load_model as tts_load_model
from mlx_audio.utils import load_audio

BASE = "/Volumes/vault/ai-models/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"
HAN  = "/Volumes/vault/ai-models/mlx-community/qwen3-tts-1.7B-han"

t0 = time.time()
print("loading base model from vault...", flush=True)
model = tts_load_model(BASE)
print(f"  loaded in {time.time()-t0:.1f}s", flush=True)

ref_audio = load_audio(f"{HAN}/ref_30s.wav", sample_rate=24000)
ref_text = open(f"{HAN}/ref_text_30s.txt", encoding="utf-8").read().strip()
print(f"ref audio frames={getattr(ref_audio,'shape',None)}, ref_text={len(ref_text)} chars", flush=True)

test_text = "大家好，我是韩小，这是一个声音克隆的测试。今天天气不错，我们来验证一下这个模型能不能学会我的声音。"
print("synthesizing in cloned voice...", flush=True)
t1 = time.time()
chunks = []
for r in model.generate(text=test_text, lang_code="chinese",
                        ref_audio=ref_audio, ref_text=ref_text, verbose=False):
    if r.audio is not None:
        chunks.append(np.array(r.audio))
full = np.concatenate(chunks)
sf.write("/tmp/han_voice_test.wav", full, 24000)
print(f"  synth in {time.time()-t1:.1f}s -> /tmp/han_voice_test.wav "
      f"({full.shape[0]/24000:.1f}s audio)", flush=True)
print("HAN_VOICE_TEST_OK", flush=True)
