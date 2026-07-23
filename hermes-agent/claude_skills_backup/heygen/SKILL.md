---
name: heygen
description: >
  HeyGen AI video generation API integration. Creates avatar videos,
  runs AI video agents, clones voices, translates video to 30+ languages,
  generates TTS audio, renders HTML to video (HyperFrames), and manages
  batch video workflows. Trigger: any request involving HeyGen video
  generation, avatar videos, AI video, voice cloning, or video translation.
version: 1.0.0
author: super_claude
tags:
  - video-generation
  - ai-video
  - heygen
  - tts
  - avatar
  - video-translation
---

# HeyGen API Skill

## When to Use

Invoke this skill when the user asks to:
- Generate an AI avatar video from a script
- Use HeyGen to create, manage, or retrieve videos
- Clone or synthesize a voice (TTS or voice cloning)
- Translate a video to another language with lip-sync
- Batch-produce multiple videos
- Set up HeyGen webhooks or check video status
- Use HeyGen's AI Video Agent ("describe a scene, get a video")
- Render HTML/CSS/JS animations as a video (HyperFrames)

## Authentication

All requests require an API key header:

```
X-Api-Key: <HEYGEN_API_KEY>
```

Base URL: `https://api.heygen.com`

Set the key as an environment variable and never hard-code it:
```bash
# store once
setx HEYGEN_API_KEY "<key>"     # Windows permanent
export HEYGEN_API_KEY="<key>"   # Unix session
```

Retrieve it from the user's HeyGen dashboard at https://app.heygen.com/settings?tab=api.

## Core Workflow

HeyGen video generation is **asynchronous**:

1. POST to create → receive `video_id`
2. GET `/{endpoint}/{video_id}` → poll `status` field
3. Status values: `pending` | `processing` | `completed` | `failed`
4. On `completed`: use `video_url` from the response

Use `callback_url` in the create request to receive a webhook instead of polling.

## API Endpoints

### 1. Video Agent (AI-driven, simplest path)

```http
POST /v3/video-agents
X-Api-Key: <key>
Content-Type: application/json

{
  "prompt": "Create a 30-second explainer video about...",
  "callback_url": "https://your-server.com/webhook"  // optional
}
```

Response: `{ "data": { "session_id": "..." } }`

Poll: `GET /v3/video-agents/{session_id}` until `status == "completed"`.

### 2. Avatar Video (manual control)

```http
POST /v3/videos
X-Api-Key: <key>
Content-Type: application/json

{
  "video_inputs": [
    {
      "character": {
        "type": "avatar",
        "avatar_id": "<avatar_id>",
        "avatar_style": "normal"  // or "circle", "closeUp"
      },
      "voice": {
        "type": "text",
        "voice_id": "<voice_id>",
        "input_text": "Hello, this is my script."
      },
      "background": {
        "type": "color",
        "value": "#ffffff"
      }
    }
  ],
  "dimension": { "width": 1280, "height": 720 },
  "callback_url": "https://your-server.com/webhook"
}
```

Response: `{ "data": { "video_id": "..." } }`

Poll: `GET /v3/videos/{video_id}`

### 3. Check Video Status

```http
GET /v3/videos/{video_id}
X-Api-Key: <key>
```

Response:
```json
{
  "data": {
    "video_id": "...",
    "status": "completed",
    "video_url": "https://files.heygen.ai/...",
    "thumbnail_url": "https://...",
    "duration": 30.5,
    "created_at": 1721234567
  }
}
```

### 4. Text-to-Speech

```http
POST /v3/voices/speech
X-Api-Key: <key>
Content-Type: application/json

{
  "voice_id": "<voice_id>",
  "text": "The text to synthesize.",
  "speed": 1.0,
  "pitch": 0
}
```

Response: audio file URL or binary stream.

### 5. List Voices

```http
GET /v3/voices?keyword=english&limit=20
X-Api-Key: <key>
```

Returns paginated list of available voices with `voice_id`, `name`, `language`, `gender`, `preview_url`.

### 6. Clone a Voice

```http
POST /v3/voices/clone
X-Api-Key: <key>
Content-Type: multipart/form-data

audio_file=<WAV/MP3, min 30s>
name=<custom name>
```

### 7. List Avatars

```http
GET /v3/avatars?limit=20
X-Api-Key: <key>
```

Returns avatar groups with `avatar_id`, `avatar_name`, `preview_image_url`.

```http
GET /v3/avatars/{avatar_id}/looks
```

Returns individual looks (outfits, poses) for an avatar.

### 8. Video Translation

```http
POST /v3/video-translate
X-Api-Key: <key>
Content-Type: application/json

{
  "video_url": "https://...",
  "output_languages": ["es", "fr", "de"],
  "title": "My translated video"
}
```

Translates with synchronized lip-sync. Supports 30+ languages (ISO 639-1 codes).

### 9. Lipsync

```http
POST /v3/lipsync
X-Api-Key: <key>
Content-Type: application/json

{
  "video_url": "https://...",
  "audio_url": "https://..."
}
```

Re-syncs existing video with new audio track.

### 10. Batch Video Generation

```http
POST /v3/videos/batch
X-Api-Key: <key>
Content-Type: application/json

{
  "requests": [
    { /* same as /v3/videos body */ },
    { /* up to 100 items */ }
  ]
}
```

### 11. HyperFrames (HTML to Video)

```http
POST /v3/hyperframes/renders
X-Api-Key: <key>
Content-Type: application/json

{
  "html": "<html><body>...</body></html>",
  "css": "body { font-family: sans-serif; }",
  "js": "/* animation script */",
  "duration": 10,
  "fps": 30,
  "dimension": { "width": 1920, "height": 1080 }
}
```

### 12. Webhooks

```http
POST /v3/webhooks
X-Api-Key: <key>
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "events": ["video.completed", "video.failed"]
}
```

Webhook payload on completion:
```json
{
  "event_type": "video.completed",
  "data": {
    "video_id": "...",
    "video_url": "...",
    "status": "completed"
  }
}
```

## Common Workflow: Script to Published Video

```python
import os, time, requests

API_KEY = os.environ["HEYGEN_API_KEY"]
BASE    = "https://api.heygen.com"
HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}

# Step 1: Get an avatar ID
avatars = requests.get(f"{BASE}/v3/avatars", headers=HEADERS).json()
avatar_id = avatars["data"]["avatars"][0]["avatar_id"]

# Step 2: Get a voice ID
voices = requests.get(f"{BASE}/v3/voices?keyword=english", headers=HEADERS).json()
voice_id = voices["data"]["voices"][0]["voice_id"]

# Step 3: Create video
payload = {
    "video_inputs": [{
        "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
        "voice": {"type": "text", "voice_id": voice_id, "input_text": "Hello world!"},
        "background": {"type": "color", "value": "#ffffff"}
    }],
    "dimension": {"width": 1280, "height": 720}
}
resp = requests.post(f"{BASE}/v3/videos", headers=HEADERS, json=payload).json()
video_id = resp["data"]["video_id"]

# Step 4: Poll until done
while True:
    status = requests.get(f"{BASE}/v3/videos/{video_id}", headers=HEADERS).json()
    s = status["data"]["status"]
    if s == "completed":
        print("Done:", status["data"]["video_url"])
        break
    elif s == "failed":
        raise RuntimeError(f"Failed: {status}")
    time.sleep(10)
```

## CLI Usage (heygen CLI tool)

```bash
# Install
pip install heygen-cli

# Auth
heygen auth login --api-key $HEYGEN_API_KEY

# List avatars
heygen avatars list

# Generate video (AI Agent mode)
heygen video create --prompt "30-second product demo for..." --output ./demo.mp4

# Translate
heygen translate --video ./demo.mp4 --languages es,fr --output ./translated/

# TTS
heygen speech --voice-id <id> --text "Hello" --output hello.mp3
```

## MCP Integration

HeyGen provides an official MCP endpoint. Add to Claude Code settings:

```json
{
  "mcpServers": {
    "heygen": {
      "command": "npx",
      "args": ["-y", "@heygen/mcp"],
      "env": { "HEYGEN_API_KEY": "${HEYGEN_API_KEY}" }
    }
  }
}
```

Or use the remote endpoint (no local install):
```
https://mcp.heygen.com/mcp?api_key=<HEYGEN_API_KEY>
```

## Rate Limits and Quotas

- Concurrent video renders: plan-dependent (check dashboard)
- Batch: max 100 items per request
- On rate limit: response includes `Retry-After` header
- Free tier: limited credits; paid plans start at $5 minimum

## Error Handling

| HTTP status | Meaning |
|-------------|---------|
| 401 | Invalid or missing `X-Api-Key` |
| 429 | Rate limit — wait `Retry-After` seconds |
| 400 | Bad request — check payload fields |
| 500 | Server error — retry with exponential backoff |

Video-level errors: check `status == "failed"` and `error_message` field in the GET response.

## Key IDs to Know

- `avatar_id`: from `GET /v3/avatars` — identifies the digital avatar
- `voice_id`: from `GET /v3/voices` — identifies the TTS voice
- `video_id`: returned by video creation — used to poll status and retrieve output
- `session_id`: returned by `/v3/video-agents` — same polling pattern

## Output Format

When reporting a completed video to the user:

```
Video ready: <video_url>
Duration: <duration>s
Thumbnail: <thumbnail_url>
```

If generating code, produce a self-contained Python or bash script with
clear variable names and inline comments explaining each API call.
