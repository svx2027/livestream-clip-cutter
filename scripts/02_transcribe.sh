#!/usr/bin/env bash
# Local transcription with mlx-whisper (Apple-Silicon GPU only -- see the
# README's "Honest scope"), word-level timestamps. Streams per-segment lines
# so progress can be tracked live: with --verbose False, mlx-whisper only
# writes output at the very end and a piped Python stdout is block-buffered,
# so a transcription that's actually working looks hung for ~15 minutes.
#
# Usage: scripts/02_transcribe.sh <lang> <primary|secondary>
#   <lang>      language code passed straight to Whisper, e.g. en, hi
#   primary     large-v3, best quality -- use for the language you will
#               actually cut clips from (accurate word timestamps)
#   secondary   large-v3-turbo, a fast full-file cross-check pass only.
#               Do NOT trust this alone to prove a window is free of the
#               primary language: forcing the wrong language onto Whisper
#               translates or drops it instead of flagging it. The decisive
#               check is the per-window re-read in scripts/06b_window_hi_each.py.
#
# Domain vocabulary: if your source has jargon Whisper tends to mis-hear
# (product names, acronyms, proper nouns), put a sentence or two of it in
# config/initial_prompt.txt and it is passed to Whisper as a priming prompt
# on the primary pass. See config/initial_prompt.example.txt for the shape.
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
export PYTHONUNBUFFERED=1

LANG="${1:?pass a language code, e.g. en or hi}"
PASS="${2:?pass primary or secondary}"

case "$PASS" in
  primary)   MODEL="mlx-community/whisper-large-v3-mlx" ;;
  secondary) MODEL="mlx-community/whisper-large-v3-turbo" ;;
  *) echo "second argument must be primary|secondary" >&2; exit 1 ;;
esac

AUDIO="source/audio.m4a"
OUT="transcripts/${LANG}"
mkdir -p "$OUT"

PROMPT_FILE="config/initial_prompt.txt"
EXTRA=()
if [ "$PASS" = "primary" ] && [ -f "$PROMPT_FILE" ]; then
  EXTRA+=(--initial-prompt "$(cat "$PROMPT_FILE")")
fi

echo "=== mlx-whisper | model=$MODEL | lang=$LANG ($PASS) -> $OUT ==="
time mlx_whisper "$AUDIO" \
  --model "$MODEL" \
  --language "$LANG" --task transcribe \
  --word-timestamps True \
  --condition-on-previous-text False \
  --output-dir "$OUT" \
  --output-format all \
  --verbose True \
  ${EXTRA[@]+"${EXTRA[@]}"}
echo "DONE lang=$LANG pass=$PASS"
