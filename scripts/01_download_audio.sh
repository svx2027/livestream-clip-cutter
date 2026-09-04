#!/usr/bin/env bash
# Audio-only fetch (no MP4 is ever downloaded). Format 140 = m4a / AAC ~129 kbps.
# Usage: scripts/01_download_audio.sh <youtube-url>
#   or export SOURCE_VIDEO_URL and call it with no argument.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; source .env; set +a; fi

URL="${1:-${SOURCE_VIDEO_URL:-}}"
if [ -z "$URL" ]; then
  echo "usage: $0 <youtube-url>   (or set SOURCE_VIDEO_URL in the environment)" >&2
  exit 1
fi

mkdir -p source
yt-dlp -f 140 --no-warnings \
  -o "source/audio.%(ext)s" \
  --write-info-json --no-write-playlist-metafiles \
  "$URL"
echo "saved -> source/audio.m4a (+ audio.info.json)"
