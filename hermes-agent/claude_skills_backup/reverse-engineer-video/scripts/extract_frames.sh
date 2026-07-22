#!/usr/bin/env bash
# Reverse-engineer helper: break a video into evenly-spaced frames + a contact sheet.
# Usage: extract_frames.sh <video> <out_dir> [n_frames]
# Needs: ffmpeg, ffprobe.
set -euo pipefail

VIDEO="${1:?usage: extract_frames.sh <video> <out_dir> [n_frames]}"
OUT="${2:?usage: extract_frames.sh <video> <out_dir> [n_frames]}"
N="${3:-24}"

command -v ffprobe >/dev/null || { echo "ffprobe not found (install ffmpeg)"; exit 1; }
mkdir -p "$OUT"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO")
echo "duration=${DUR}s  frames=${N}  -> $OUT"

# evenly spaced timestamps across the whole clip
i=0
while [ "$i" -lt "$N" ]; do
  T=$(awk -v d="$DUR" -v n="$N" -v i="$i" 'BEGIN{printf "%.3f", d*(i+0.5)/n}')
  IDX=$(printf "%02d" "$i")
  ffmpeg -y -v error -ss "$T" -i "$VIDEO" -frames:v 1 -vf "scale=800:-1" "$OUT/frame_${IDX}.png"
  i=$((i+1))
done

# contact sheet (6 columns) so a human/model can eyeball the whole arc at once
ffmpeg -y -v error -pattern_type glob -i "$OUT/frame_*.png" \
  -filter_complex "tile=6x$(( (N+5)/6 )):margin=8:padding=8:color=white" \
  "$OUT/contact-sheet.png" 2>/dev/null || echo "(contact sheet skipped)"

echo "done: $(ls "$OUT"/frame_*.png | wc -l | tr -d ' ') frames + contact-sheet.png"
