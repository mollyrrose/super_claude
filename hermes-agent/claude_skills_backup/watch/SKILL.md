---
name: "watch"
description: "Watch and understand a video (URL or local path). Downloads with yt-dlp, extracts scene-aware frames with ffmpeg, pulls transcript from captions (Whisper API fallback), hands result to Claude to answer questions about the video. Trigger: /watch <url-or-path> [question]. Source: bradautomates/claude-video (MIT). Requires: ffmpeg, yt-dlp, optional Groq or OpenAI API key for Whisper."
version: "0.2.0"
author: bradautomates (ported to this setup)
license: MIT
tags: [video, media, watch, ffmpeg, yt-dlp, whisper, transcript, frames]
argument-hint: "<video-url-or-path> [question]"
allowed-tools: Bash, Read, AskUserQuestion
homepage: https://github.com/bradautomates/claude-video
---

# /watch

You do not have a video input; this skill gives you one. A Python script gets captions first,
optionally downloads the video, extracts frames as JPEGs (scene-aware, or fast keyframes at
efficient detail), gets a timestamped transcript (native captions first, then Whisper API as
fallback), and prints frame paths. You then Read each frame path to see the images and combine
them with the transcript to answer the user.

## IMPORTANT: This skill requires a local installation

The watch script and its dependencies must be present. If not installed:

```
Installation requires:
  1. ffmpeg   (brew install ffmpeg / apt install ffmpeg / winget install Gyan.FFmpeg)
  2. yt-dlp   (pip install yt-dlp)
  3. Optional: Groq or OpenAI API key in ~/.config/watch/.env for Whisper transcription

Install the skill from source:
  npx skills add bradautomates/claude-video
  -- or --
  Clone https://github.com/bradautomates/claude-video and run install.sh
```

If the scripts are missing, tell the user to install the dependencies above and point them to
https://github.com/bradautomates/claude-video.

## Resolve SKILL_DIR

Set SKILL_DIR to the absolute path of the directory containing this SKILL.md.
Every python3 command below uses SKILL_DIR/scripts/watch.py.

Guard:
```bash
SKILL_DIR="<absolute path of the directory containing the SKILL.md you Read>"
if [ ! -f "$SKILL_DIR/scripts/watch.py" ]; then
  echo "ERROR: scripts/watch.py not found. Install the skill first." >&2
  exit 1
fi
```

On Windows, substitute python for python3.

## When to use

- User pastes a video URL (YouTube, Vimeo, X, TikTok, Twitch clip, most yt-dlp-supported sites)
- User points at a local video file (.mp4, .mov, .mkv, .webm, etc.)
- User types /watch <url-or-path> [question]

## Recommended limits

- Best accuracy: videos under 10 minutes.
- Universal rate cap: 2 fps.
- Frame ceiling by detail mode (WATCH_DETAIL in ~/.config/watch/.env, or --detail flag):
  - transcript -- no frames, transcript only
  - efficient -- up to 50 frames (keyframes)
  - balanced (default) -- up to 100 frames (scene-aware)
  - token-burner -- uncapped scene-aware (soft warning past 250 frames)

## Workflow

Step 0 -- Setup preflight (first /watch in a session):
```bash
python3 "${SKILL_DIR}/scripts/setup.py" --check
```
Exit 0 = ready. If non-zero: 2=missing binaries, 3=no Whisper key, 4=both.
Run `python3 "${SKILL_DIR}/scripts/setup.py"` to install / scaffold ~/.config/watch/.env.
On genuine first run (--json shows first_run: true), ask the user for a Groq/OpenAI API
key and their preferred detail mode via AskUserQuestion, then write into ~/.config/watch/.env.

Step 1 -- Parse user input: separate video source from any question.

Step 2 -- Run the watch script:
```bash
python3 "${SKILL_DIR}/scripts/watch.py" "<source>"
```
Optional flags: --detail, --start T, --end T, --timestamps T1,T2,..., --max-frames N,
--resolution W, --fps F, --out-dir DIR, --whisper groq|openai, --no-whisper, --no-dedup.

Step 3 -- Read every frame path the script lists (parallel Read calls, chronological order).

Step 4 -- Answer the user using both frames and transcript. Cite timestamps.

Step 5 -- Clean up: `rm -rf <working-dir>` unless user may ask follow-ups.

## Kill Switch

Delete ~/.claude/skills/watch/ to remove this skill.
Binary dependencies (ffmpeg, yt-dlp) and ~/.config/watch/.env are separate; removing
this SKILL.md only removes the Claude Code trigger, not those tools.
