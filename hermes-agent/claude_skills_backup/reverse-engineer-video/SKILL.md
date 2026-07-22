---
name: reverse-engineer-video
description: >-
  Reverse-engineer any reference video into a reusable, editable motion spec — break it into
  frames, extract its camera grammar, and write a spec + generation prompt you can re-shoot
  with a DIFFERENT object and design system. Use whenever the user wants to copy the feel /
  camera / motion of a video onto their own content: "recreate this video's effect", "make
  something like this but with my product", "turn this clip into a spec", "reverse engineer
  this animation", "steal the camera move from this", "break this video into frames and write
  a spec", or drops a Pinterest / TikTok / YouTube / any video URL or file and wants the same
  scroll-hero or flythrough motion for their brand. Also fires for building AI-video prompts
  (Seedance, Higgsfield, Sora, Runway) that must match an existing reference clip.
---

# Reverse-Engineer a Video → reusable motion spec

A video looks like one inseparable thing, but it splits cleanly into two layers:

- **Camera choreography** — path, framing arc, beat rhythm, bookends, the one signature move.
  This is the reusable DNA. Reverse-engineer and keep it.
- **Art direction** — the reference's object, palette, lighting, type. Disposable. The user
  replaces it with their own.

Your job: pull the first layer out of a finished clip and re-express it as (1) a frame-by-frame
**beat spec** and (2) a ready-to-run **generation prompt** for the user's object + design system.

## Workflow

### 1. Get the video

- **URL** (Pinterest, TikTok, YouTube, etc.): for Pinterest, use the `pinterest-download` skill;
  otherwise `yt-dlp "<url>" -o video.mp4` (fall back to the `yt-search-download` skill for YouTube).
- **Local file**: use the path as-is.

### 2. Break it into frames

Run the bundled script — evenly-spaced frames plus a contact sheet so you can see the whole
motion arc at once:

```bash
bash scripts/extract_frames.sh <video> <out_dir> 24
```

Then Read `<out_dir>/contact-sheet.png` (and a few individual frames) and actually *look*.

### 3. Reverse-engineer the camera grammar (the reusable core)

From the frames, extract ONLY these — ignore the reference's object and colors entirely:

- **Path shape** — orbit / dolly-through / pan / crane / flythrough?
- **Framing arc** — how does subject size change across the clip? (e.g. wide → 3/4 → tight → CU)
- **Beat count & rhythm** — how many "settle" moments; how long each holds; how fast the moves between.
- **Bookends** — how it opens and closes (a returning light, an overview frame, a logo).
- **Negative-space side** — where the subject sits so copy has room (subject right → copy left).
- **The one signature move** — the single thing that makes it feel alive.

Write these as 5–7 bullets. This bullet list is the transferable asset — offer to save it.

### 4. Take the user's swap

Ask for (or infer from context) their replacements:

| Slot | YOURS |
|---|---|
| Object | what replaces the reference's subject |
| "Turn" analog | how THEIR object reveals depth (flythrough? rotate? unfold?) |
| Palette / tokens | their design system — bg, accent, ink (point to a design-system.md if one exists) |
| Bookend motif | their equivalent of the reference's opening/closing motif |
| Copy side | per beat, which half stays empty for text |
| Beats / stations | their N stations mapped onto the reference's beat count |

### 5. Emit the beat spec

A table, one row per beat: `scroll% (or time) | camera pos + angle | what's framed | copy side`.
Keep the reference's *rhythm and framing arc*; substitute the user's stations. Same beat count,
same slow-hold / fast-move cadence, same bookends.

### 6. Emit the generation prompt

Assemble in THIS fixed order — the structure is what makes AI-video output reliable:

1. **Reference legend** — numbered images the user will upload: bookend frame first, then one
   per-beat composition, then exact logos/marks. (Number them literally 1,2,3… to match upload
   order; don't use `<<< >>>` tags in the prompt text — plain "image 1" reads cleaner.)
2. **Camera model** — one strict sentence on what the camera CAN and CANNOT do
   (e.g. "glides on horizontal/vertical rails, never rotates").
3. **Color / material law** — exact hex, "never darker/other." If a color keeps drifting across
   renders, bind it to a swatch reference image, not another adjective.
4. **Timed beats** — `0–Xs …` per station, naming the empty half each time.
5. **Invariants footer** — "each element appears once, nothing new appears, background uniform in
   every frame, first frame == last frame."

## Hard-won lessons (bake these into every prompt)

These come from real iteration and are the difference between 1 good take and 6 bad ones:

- **Pixels beat prose.** Background color, opening/closing composition, and logo identity are
  guaranteed by *reference images*, never by adjectives. Use the bookend frame as BOTH the
  start-image and end-image slot to lock the loop.
- **A recurring drift needs an image, not emphasis.** If green keeps rendering too dark after two
  tries, stop rewriting "#hex, never dark" — make a swatch PNG of the exact color and pass it as
  a reference. Same for a tile that won't disappear: remove it from the reference image itself.
- **Name the empty half every beat** — that reserved space is where sliding HTML copy will go.
- **Repeat identity invariants at the end** — "each element once, nothing merges, nothing new" —
  this is what kills duplicated, merged, and hallucinated elements.
- **Timed shot-lists beat vibe paragraphs.** The model obeys `0–1.2s / 1.2–4s …` clocks.
- **One reference video = camera only.** Never let its palette or object leak into the output.
- **Know when to stop.** AI video often re-invents one small flaw per render. After ~3 iterations,
  it's usually cheaper to accept the best take and fix the last blemish in post (a 1-second
  start/end-frame reshoot, or masking in edit) than to chase a flawless single generation.

## Output

End by giving the user, clearly separated: the **camera-grammar bullets**, the **beat spec
table**, and the **copy-paste generation prompt** — plus the frames folder path for reference.
Offer to save all three to a `.md` file in their project.
