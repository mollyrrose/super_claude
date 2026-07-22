#!/usr/bin/env bash
#
# Download the video (or image) from one or more Pinterest pins.
#
# Usage:
#   download.sh [-o OUTPUT_DIR] <url> [url2 url3 ...]
#
# - Tries yt-dlp first (video pins, incl. HLS video+audio -> single .mp4).
# - Falls back to the full-resolution image for image-only pins.
# - Handles regional domains (ca./uk./...) and pin.it short links.
#
# Exit codes: 0 all ok · 1 bad usage · 2 one or more downloads failed

set -uo pipefail

OUT_DIR="."
while [[ "${1:-}" == "-o" ]]; do OUT_DIR="$2"; shift 2; done

if [[ $# -eq 0 ]]; then
  echo "Usage: download.sh [-o OUTPUT_DIR] <url> [url2 ...]" >&2
  exit 1
fi
if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "ERROR: yt-dlp is not installed. Install with: brew install yt-dlp" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
FAILED=0

download_one() {
  local url="$1"
  # Name by pin id when present; else let yt-dlp supply its own id (handles pin.it).
  local pin_id base
  pin_id="$(printf '%s' "$url" | grep -oE '/pin/[0-9]+' | grep -oE '[0-9]+' | head -n1)"
  base="pinterest_${pin_id:-%(id)s}"

  echo ">> $url"
  if yt-dlp --no-warnings "$url" -o "${OUT_DIR}/${base}.%(ext)s" 2>/tmp/pin_err; then
    local f; f="$(ls -t "${OUT_DIR}/pinterest_"* 2>/dev/null | head -n1)"
    [[ -n "$f" ]] && { echo "   Saved: $f"; return 0; }
  fi

  # Image fallback: scrape the pin page, upgrade the CDN path to full resolution.
  echo "   No video — trying image..."
  local html img hires ext out
  html="$(curl -fsSL -A 'Mozilla/5.0' "$url" 2>/dev/null)"
  img="$(printf '%s' "$html" | grep -oE 'https://i\.pinimg\.com/[^"'"'"']+\.(jpg|jpeg|png|gif|webp)' | head -n1)"
  if [[ -z "$img" ]]; then
    echo "   ERROR: no video or image found (pin may be private/deleted)." >&2
    return 1
  fi
  hires="$(printf '%s' "$img" | sed -E 's#i\.pinimg\.com/[0-9]+x[0-9]*/#i.pinimg.com/originals/#')"
  ext="${hires##*.}"; out="${OUT_DIR}/pinterest_${pin_id:-image}.${ext}"
  if curl -fsSL -A 'Mozilla/5.0' "$hires" -o "$out" 2>/dev/null \
     || curl -fsSL -A 'Mozilla/5.0' "$img" -o "$out" 2>/dev/null; then
    echo "   Saved: $out"; return 0
  fi
  echo "   ERROR: found image but download failed: $img" >&2
  return 1
}

for url in "$@"; do
  download_one "$url" || FAILED=1
done

exit $FAILED
