#!/usr/bin/env bash
set -u
W="${1:?usage: build_montage.sh <workdir>}"
cd "$W"
: > concat.txt
i=0
while IFS='|' read -r base start end label; do
  [ -z "${base:-}" ] && continue
  i=$((i+1))
  src=$(ls "D:/Svajc/$base".* 2>/dev/null | grep -iE '\.(mov|mp4)$' | head -1)
  [ -z "$src" ] && { echo "MISSING $base"; continue; }
  dur=$(awk -v a="$start" -v b="$end" 'BEGIN{printf "%.3f", b-a}')
  out=$(printf "parts/%02d_%s.mp4" "$i" "$base")
  if [ ! -f "$out" ]; then
    ffmpeg -y -loglevel error -ss "$start" -t "$dur" -i "$src" \
      -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1" \
      -af "highpass=f=80,arnndn=m=sh.rnnn,speechnorm=e=6.25:r=0.00001:l=1" \
      -c:v libx264 -crf 20 -preset veryfast -pix_fmt yuv420p \
      -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart "$out" \
      && echo "[$i/14] OK  $base ${start}-${end}  ($dur s)  $label" \
      || { echo "[$i/14] FAIL $base"; continue; }
  else
    echo "[$i/14] skip $base"
  fi
  echo "file '$out'" >> concat.txt
done < edl.txt
echo "--- osszefuzes ---"
ffmpeg -y -loglevel error -f concat -safe 0 -i concat.txt -c copy montage.mp4 \
  && echo "MONTAZS KESZ: $W/montage.mp4" || echo "CONCAT HIBA"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 montage.mp4 2>/dev/null
