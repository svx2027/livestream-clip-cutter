#!/usr/bin/env python3
"""Transcribe each window WAV individually (secondary language, large-v3) so
outputs don't collide -- passing multiple files to the mlx_whisper CLI in one
call silently writes only the last file's output, under every input's name.
Model loads once (mlx caches it). Writes <id>.hi.txt per clip. This is the
decisive per-window language check: a single full-file forced-language pass
cannot be trusted to certify a clip's language on its own, because forcing
the wrong language makes Whisper translate or drop it instead of flagging
it."""
import os, json, mlx_whisper

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, "analysis", "win_audio")
MODEL = "mlx-community/whisper-large-v3-mlx"
clips = json.load(open(os.path.join(ROOT, "analysis", "clip-segments.json")))["clips"]

for c in clips:
    wav = os.path.join(WAV, c["id"] + ".wav")
    r = mlx_whisper.transcribe(wav, path_or_hf_repo=MODEL, language="hi", verbose=False)
    txt = (r.get("text") or "").strip()
    open(os.path.join(WAV, c["id"] + ".hi.txt"), "w").write(txt)
    print(f"{c['id']} :: {txt[:200]}", flush=True)
print("DONE_EACH")
