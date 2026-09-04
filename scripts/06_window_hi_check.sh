#!/usr/bin/env bash
# Clean per-window secondary-language cross-check: re-transcribe ONLY the
# suggested clip windows with the faithful large-v3 model (short clips => no
# repetition hallucination, unlike a full-file forced-wrong-language pass).
# Reveals genuine secondary-language spans the primary-language-forced pass
# may have translated away.
#
# NOTE: this script only extracts the window WAVs; transcription is delegated
# to scripts/06b_window_hi_each.py, which transcribes each WAV individually.
# Passing multiple files to the mlx_whisper CLI in one call silently collides
# every output into a single file -- the Python API loop in 06b avoids that
# while still loading the model only once.
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
export PYTHONUNBUFFERED=1

WAV=analysis/win_audio
rm -rf "$WAV"; mkdir -p "$WAV"

# emit "id in out" rows from the clip list
python3 - <<'PY' > "$WAV/list.txt"
import json
d=json.load(open("analysis/clip-segments.json"))
for c in d["clips"]:
    print(c["id"], c["suggested_in"], c["suggested_out"])
PY

while read -r id a b; do
  ffmpeg -nostdin -loglevel error -y -ss "$a" -to "$b" -i source/audio.m4a \
    -ar 16000 -ac 1 "$WAV/${id}.wav"
done < "$WAV/list.txt"
echo "extracted $(ls "$WAV"/*.wav | wc -l | tr -d ' ') window clips"

python3 "$(dirname "$0")/06b_window_hi_each.py"
echo "DONE_HI_WINDOWS"
