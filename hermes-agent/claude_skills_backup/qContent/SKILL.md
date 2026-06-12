---
name: qContent
description: "Generate media content (video, image, talking-head, etc.) via the local ComfyUI install. Routes the user's natural-language request to the correct ComfyUI workflow, calls the matching `comfyui-local` MCP tool, and saves the output into `ai_video/generated/<type>/`. Use whenever the user asks for video/image/audio generation in Hungarian or English. Invoked via /qContent (canonical) OR any case variant — /qcontent, /Qcontent, /QContent, /QCONTENT all map to this same skill (case-insensitive)."
---

# qContent — Local content generation via ComfyUI

This skill is a router. The user says what they want; you decide which
ComfyUI workflow handles it, call the right MCP tool, and deliver the
output to a per-type folder inside the repo.

## Prerequisites (silent check)

Before calling any tool, verify the `comfyui-local` MCP server is
registered (`claude mcp list` shows it). If not, tell the user to run
`scripts\setup_ai_video.ps1` first and stop.

Also verify ComfyUI is actually running at `http://127.0.0.1:8188`. If
not, tell the user to start it with `ai_video\start_comfyui.bat` and stop.

## Step 1 — Classify the user's intent

Pick exactly one type from this table by reading the user's request.
Hungarian and English triggers shown side-by-side.

| Type | Triggers (HU) | Triggers (EN) | MCP tool | Workflow file |
|---|---|---|---|---|
| `text_to_video` | "csinálj egy videót arról hogy...", "5 mp klip", "rövid videó" | "generate video", "make a clip", "T2V" | `generate_video` | `ai_video/workflows/ltxv_t2v.json` |
| `talking_head` | "beszéljen", "beszélő fej", "szinkronizálj rá", "lip sync" | "talking head", "lip sync", "make this person say", "talking portrait" | `generate_talking_head` | `ai_video/workflows/float_t2v.json` |
| `image_to_video` | "animáld a képet", "kép → videó", "ebből csinálj videót" | "image to video", "animate this image", "I2V" | (not yet) | (TODO) |
| `text_to_image` | "rajzolj", "képet", "portrét csinálj" | "generate image", "make a picture", "T2I" | (not yet) | (TODO) |

If the user request maps to a `(not yet)` type, tell them: "Az i2v / t2i
ComfyUI MCP-tool még nincs bekötve — t2v és talking_head van. Ha igen,
megcsináljuk pluszként." Stop.

## Step 2 — Gather the required inputs

Required inputs depend on the type. Ask the user only for what's
missing; never make up filenames.

### `text_to_video`
- `prompt` (long, descriptive — LTX-Video needs verbose prompts; auto-extend if user gave a short one).
- Optional: `width` (default 832), `height` (default 480), `length_frames` (default 121 = ~5 s @ 24 fps), `steps` (default 20).

### `talking_head`
- `image_filename` — must already be in `ai_video/comfyui/input/`. If user gave only a path elsewhere, copy/move it to that folder first (use Bash `cp`). If user has no image, ask whether to use the sample `sam_altman_512x512.jpg` shipped with the setup script.
- `audio_filename` — same rule. If user has only text (e.g. "mondja azt hogy 'Helló világ!'"), tell them: "Ahhoz hogy ezt beszéddé alakítsam, az F5-TTS workflow-t kell külön futtatni a ComfyUI UI-ban (még nincs MCP tool hozzá). Vagy adsz egy meglévő hangfájlt és arra teszem az arcot." Wait for their answer.
- Optional: `emotion` (one of: `none`, `happy`, `sad`, `angry`, `surprise`, `fear`, `disgust`, `contempt`, `neutral`; default `none`), `fps` (default 25).
- Remind the user: FLOAT is CC BY-NC-SA 4.0 → non-commercial use only.

## Step 3 — Call the MCP tool

Invoke the matching MCP tool via the standard `mcp__comfyui-local__<tool>`
form. Examples:

- `mcp__comfyui-local__generate_video` with `{ "prompt": "...", "width": 832, "height": 480, "length_frames": 121, "steps": 20 }`
- `mcp__comfyui-local__generate_talking_head` with `{ "image_filename": "sam_altman_512x512.jpg", "audio_filename": "aud-sample-vs-1.wav", "emotion": "none", "fps": 25 }`

Tier C wall-clock expectations:
- `text_to_video` (LTX 0.9.8 base): 15-25 min per clip
- `talking_head` (FLOAT): 1-2 min per 5 s clip
- Each is wall-clock heavy; tell the user up-front so they don't think it crashed.

## Step 4 — Move the output into the project content folder

The MCP returns one or more `outputs` paths under `ai_video/comfyui/output/`.
Move (don't copy) them into the per-type project folder, with a timestamped
filename for traceability.

Target layout:

```
ai_video/generated/
- text_to_video/<YYYYMMDD-HHMMSS>_<short-slug>.mp4
- talking_head/<YYYYMMDD-HHMMSS>_<short-slug>.mp4
- image_to_video/...
- text_to_image/...
```

Steps:

1. Compute `ts = datetime.now().strftime("%Y%m%d-%H%M%S")` (UTC if mixing timezones).
2. Compute `slug` = first 6 words of the prompt or audio filename, lowercased, non-alphanumeric → `_`, max 40 chars.
3. Target dir = `ai_video/generated/<type>/`. `mkdir -p` it.
4. Use `mv` (Bash) to rename the MCP output file into the target path.
5. Print the final path back to the user as: `Output: <absolute path>`.

If `mv` fails (cross-volume, permissions), fall back to `cp` + `rm` of the source.

## Step 5 — Summarize back to the user

One-block reply in the user's language (mirror their original request's language):

```
Kész.
- Típus: <type>
- Modell: <model name> (<wall-clock> sec)
- Méret / hossz: <details>
- Output: <absolute path>
- Megjegyzés (ha van): <license / quality caveat>
```

Or English:

```
Done.
- Type: <type>
- Model: <model name> (<wall-clock> sec)
- Size / length: <details>
- Output: <absolute path>
- Note (if any): <license / quality caveat>
```

## Edge cases the runbook must handle

| Situation | Behavior |
|---|---|
| `ai_video/workflows/<wf>.json` missing | The MCP returns a clear "save the workflow first" error. Surface it to the user with the exact path; tell them to open ComfyUI -> File -> Open the matching template, then Workflow -> Export (API) into that path. |
| ComfyUI not running | MCP returns "Cannot reach ComfyUI". Tell the user to start `ai_video\start_comfyui.bat` and retry. |
| User asks for talking_head without an audio file | Don't fabricate audio. Ask: "Van meglévő wav/mp3, vagy szeretnél F5-TTS-ből generálni? (Az utóbbi még csak UI-ból megy, MCP tool nincs hozzá.)" |
| User asks for i2v/t2i | Not yet supported by the MCP — tell them, offer to add it. Stop, don't fake it. |
| Multiple outputs (rare) | Move all into the target folder, list all paths in the reply. |
| User wants something deeply NSFW / hateful / illegal | Refuse as you would in a normal chat. The local install does not change the policy. |
| User runs this in a non-`super_claude` repo | Refuse: tell them `/qContent` is specific to `super_claude` because it depends on the local ComfyUI install + MCP server there. |

## Files this skill creates

- `ai_video/generated/<type>/<ts>_<slug>.<ext>` (one or more, the moved outputs)

No git changes. The `ai_video/generated/` folder is added to `.gitignore`
on first run via a normal Edit; if it isn't there yet, append the line
silently (this is a one-time fix-up, not destructive).
