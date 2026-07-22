---
name: pinterest-download
description: Download a video (or image) from any Pinterest pin URL and save it to disk. Use this whenever the user pastes a Pinterest link (pinterest.com/pin/..., ca.pinterest.com, pin.it short links, or any regional Pinterest domain) and wants to download, save, or grab the video, clip, GIF, or image from it. Trigger even if the user just says "can I save this?" or "download this" alongside a Pinterest URL, and whether they want it saved to the current folder or a specific location.
---

# Pinterest Download

Download the video or image behind one or more Pinterest pins. The bundled
`scripts/download.sh` does everything: it runs `yt-dlp` for video pins (merging
HLS video+audio into one `.mp4`) and falls back to the full-resolution image for
image-only pins.

## Usage

```bash
bash <skill-dir>/scripts/download.sh [-o OUTPUT_DIR] "<URL>" ["<URL2>" ...]
```

- `-o OUTPUT_DIR` — where to save. Omit to save in the current directory. "Save it
  here" → omit `-o`; a named folder → pass it.
- Pass **multiple URLs** to download them in one run.

Files are named `pinterest_<id>.<ext>`, so nothing overwrites. On success the
script prints `Saved: <path>` — relay that path to the user.

**Example:**

```bash
bash .claude/skills/pinterest-download/scripts/download.sh -o . \
  "https://ca.pinterest.com/pin/955748352150564605/"
```

## If it fails

- `yt-dlp is not installed` → have the user run `brew install yt-dlp`.
- `no video or image found` → the pin is likely private, deleted, or region-blocked;
  ask them to confirm the link is publicly viewable.
- The "older than 90 days" yt-dlp warning is harmless; only suggest `brew upgrade
  yt-dlp` if a download actually fails.

Don't echo raw fragment/progress spam back to the user — just confirm the save and
the final path.
