---
name: qContent
description: "Generate media content (video, image, talking-head, etc.) via the local ComfyUI install from ANY project. Routes the user's natural-language request to the correct ComfyUI workflow, calls the matching `comfyui-local` MCP tool, and saves the output into `<current-project>/.scratch/generated_content/<type>/`. The ComfyUI MCP server is a Claude-Code-wide registration, so the skill works in every project as long as the `comfyui-local` MCP is reachable. Use whenever the user asks for video/image/audio generation in Hungarian or English. Invoked via /qContent (canonical) OR any case variant — /qcontent, /Qcontent, /QContent, /QCONTENT all map to this same skill (case-insensitive)."
---

# qContent — Local content generation via ComfyUI

This skill is a router. The user says what they want; you decide which
ComfyUI workflow handles it, call the right MCP tool, and deliver the
output to a per-type folder inside the repo.

## Prerequisites (silent check + auto-launch)

Before calling any tool, verify the `comfyui-local` MCP server is
registered (`claude mcp list` shows it). If not, tell the user to run
`scripts\setup_ai_video.ps1` first and stop.

Also verify ComfyUI is reachable at `http://127.0.0.1:8188`. If not,
**auto-launch it in the background — no visible window, no user
intervention.** Do NOT tell the user to start it manually; the whole
point of the background launcher is to remove that friction.

Launch:

```powershell
D:\Projects\super_claude\scripts\start_comfyui_bg.ps1
```

Then poll `http://127.0.0.1:8188/` every 2 seconds, up to 60 seconds.
The launcher uses `Start-Process -WindowStyle Hidden` so there's no
PowerShell window for the user to see — the python.exe just runs in
the background, logging to `ai_video\.comfyui.log`. PID is recorded in
`ai_video\.comfyui.pid` for later `stop_comfyui_bg.ps1` cleanup.

If still unreachable after 60 s, surface the log path to the user:
`D:\Projects\super_claude\ai_video\.comfyui.log` (and `.comfyui.err`)
so they can inspect the failure. Do not ask them to start it manually
— the boot failure is the bug to investigate, not the launch flow.

## Step 1 — Classify the user's intent

Pick exactly one type from this table by reading the user's request.
Hungarian and English triggers shown side-by-side.

| Type | Triggers (HU) | Triggers (EN) | MCP tool | Workflow file |
|---|---|---|---|---|
| `text_to_video` | "csinálj egy videót arról hogy...", "5 mp klip", "rövid videó" | "generate video", "make a clip", "T2V" | `generate_video` | `ai_video/workflows/ltxv_t2v.json` |
| `talking_head` | "beszéljen", "beszélő fej", "szinkronizálj rá", "lip sync" | "talking head", "lip sync", "make this person say", "talking portrait" | `generate_talking_head` | `ai_video/workflows/float_t2v.json` |
| `image_to_video` | "animáld a képet", "kép → videó", "ebből csinálj videót" | "image to video", "animate this image", "I2V" | `generate_image_to_video` | `ai_video/workflows/i2v.json` |
| `text_to_image` | "rajzolj", "képet", "portrét csinálj" | "generate image", "make a picture", "T2I" | `generate_image` | `ai_video/workflows/t2i.json` |

All four types are now wired up. If a workflow JSON file is missing, the
MCP returns a clear "save the workflow first" error with the exact path
and template name — surface that to the user verbatim and tell them to
open ComfyUI -> File -> Open a matching template, then **Workflow ->
Export (API)** into the exact path the error message shows.

## Step 2 — Gather the required inputs

Required inputs depend on the type. Ask the user only for what's
missing; never make up filenames.

### `text_to_video`
- `prompt` (long, descriptive — LTX-Video needs verbose prompts; auto-extend if user gave a short one).
- Optional: `width` (default 832), `height` (default 480), `length_frames` (default 121 = ~5 s @ 24 fps), `steps` (default 20).

### `text_to_image`
- `prompt` (positive prompt; subject + style + lighting).
- Optional: `width` (default 1024), `height` (default 1024), `steps` (default 20).
- Tier C VRAM limit: stick with 1024×1024 or below unless using a small model (Z-Image-Turbo).

### `image_to_video`
- `image_filename` — bare filename inside `ai_video/comfyui/input/`. Same rule as `talking_head`: copy/move into that folder first, no full paths.
- `prompt` — describes the motion or scene change (e.g. "slow zoom on the subject, gentle camera dolly").
- Optional: `width` (default 832), `height` (default 480), `length_frames` (default 121), `steps` (default 20).
- LTX I2V / Wan I2V / Hunyuan I2V are all candidates; the workflow at `ai_video/workflows/i2v.json` picks which model is used.

### `talking_head`
- `image_filename` — must already be in `ai_video/comfyui/input/`. If user gave only a path elsewhere, copy/move it to that folder first (use Bash `cp`). If user has no image, ask whether to use the sample `sam_altman_512x512.jpg` shipped with the setup script.
- `audio_filename` — same rule. If user has only text (e.g. "mondja azt hogy 'Helló világ!'"), tell them: "Ahhoz hogy ezt beszéddé alakítsam, az F5-TTS workflow-t kell külön futtatni a ComfyUI UI-ban (még nincs MCP tool hozzá). Vagy adsz egy meglévő hangfájlt és arra teszem az arcot." Wait for their answer.
- Optional: `emotion` (one of: `none`, `happy`, `sad`, `angry`, `surprise`, `fear`, `disgust`, `contempt`, `neutral`; default `none`), `fps` (default 25).
- Remind the user: FLOAT is CC BY-NC-SA 4.0 → non-commercial use only.

## Step 3 — Call the MCP tool

Invoke the matching MCP tool via the standard `mcp__comfyui-local__<tool>`
form. Examples:

- `mcp__comfyui-local__generate_video` with `{ "prompt": "...", "width": 832, "height": 480, "length_frames": 121, "steps": 20 }`
- `mcp__comfyui-local__generate_image` with `{ "prompt": "...", "width": 1024, "height": 1024, "steps": 20 }`
- `mcp__comfyui-local__generate_image_to_video` with `{ "image_filename": "frame_01.jpg", "prompt": "slow zoom in", "width": 832, "height": 480, "length_frames": 121, "steps": 20 }`
- `mcp__comfyui-local__generate_talking_head` with `{ "image_filename": "sam_altman_512x512.jpg", "audio_filename": "aud-sample-vs-1.wav", "emotion": "none", "fps": 25 }`

Tier C wall-clock expectations:
- `text_to_image` (Flux dev fp8 / Z-Image-Turbo): 20 s - 2 min per 1024^2 image
- `text_to_video` (LTX 0.9.8 base): 15-25 min per clip
- `image_to_video` (LTX I2V): 15-30 min per clip (similar to T2V; image conditioning adds little overhead)
- `talking_head` (FLOAT): 1-2 min per 5 s clip
- Each is wall-clock heavy; tell the user up-front so they don't think it crashed.

## Step 4 — Move the output into the current project's scratch folder

The MCP returns one or more `outputs` paths under ComfyUI's own
`output/` directory (wherever ComfyUI is installed — typically
`ai_video/comfyui/output/` inside the super_claude install). Move
(don't copy) them into the **current project's** `.scratch/` tree, so
generated content sticks with the project that asked for it instead of
piling up in the ComfyUI install.

Target layout (relative to whatever project is currently `cwd`):

```
<cwd>/.scratch/generated_content/
- text_to_video/<YYYYMMDD-HHMMSS>_<short-slug>.mp4
- talking_head/<YYYYMMDD-HHMMSS>_<short-slug>.mp4
- image_to_video/...
- text_to_image/...
```

Steps:

1. Resolve `cwd` to the current working directory (`Get-Location` in
   PowerShell, `pwd` in Bash). If the directory is `~/.claude` itself,
   use `~/.claude/generated_content/<type>/` instead — see global
   CLAUDE.md "Not for this directory".
2. Compute `ts = datetime.now().strftime("%Y%m%d-%H%M%S")` (UTC if mixing
   timezones).
3. Compute `slug` = first 6 words of the prompt or audio filename,
   lowercased, non-alphanumeric → `_`, max 40 chars.
4. Target dir = `<cwd>/.scratch/generated_content/<type>/`. `mkdir -p` it.
   If `.scratch/` is not in the project's `.gitignore`, silently append
   `/.scratch/` to it (one-time fix-up, mirrors the global rule about
   scratch directories).
5. Use `mv` (Bash) to rename the MCP output file into the target path.
6. Print the final path back to the user as: `Output: <absolute path>`.

If `mv` fails (cross-volume, permissions), fall back to `cp` + `rm` of
the source.

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
| User asks for i2v without specifying the reference image | Ask which image to use. Either an existing file in `ai_video/comfyui/input/`, or first call `generate_image` to make one and chain it. |
| Workflow file missing for the requested type | Surface the MCP's FileNotFoundError verbatim — it includes the exact path and template hint. Tell the user to save one from the UI; do not try to fabricate the workflow JSON. |
| Multiple outputs (rare) | Move all into the target folder, list all paths in the reply. |
| User wants something deeply NSFW / hateful / illegal | Refuse as you would in a normal chat. The local install does not change the policy. |
| User runs this in a non-`super_claude` repo | Proceed normally — the `comfyui-local` MCP is registered Claude-Code-wide and works from any project. Outputs land in the **current** project's `.scratch/generated_content/<type>/`, not in super_claude's tree. |

## Files this skill creates

- `ai_video/generated/<type>/<ts>_<slug>.<ext>` (one or more, the moved outputs)

No git changes. The `ai_video/generated/` folder is added to `.gitignore`
on first run via a normal Edit; if it isn't there yet, append the line
silently (this is a one-time fix-up, not destructive).
