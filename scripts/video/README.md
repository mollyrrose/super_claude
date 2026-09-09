# Video retake montage pipeline

Turns a folder of raw takes - where the same sentence is attempted several
times and the last attempt is usually the good one - into a single montage of
only the good attempts, with AI noise reduction on the speech.

Built 2026-09-08 for a set of 4K talking-head takes; nothing here is specific
to that shoot.

## Requirements

- `ffmpeg` on PATH (must include the `arnndn` filter - check with
  `ffmpeg -filters | grep arnndn`).
- `faster-whisper` (`pip install --user faster-whisper`). Runs on CPU, int8.
- RNNoise model weights in `assets/rnnoise-models/` (`sh.rnnn`, `bd.rnnn`) -
  already vendored in this repo, see that folder's note.

## Steps

1. **Extract audio** (16 kHz mono WAV, one per take) into `<workdir>/audio/`:
   ```bash
   ffmpeg -i take.mov -vn -ac 1 -ar 16000 -c:a pcm_s16le audio/take.wav
   ```
2. **Transcribe** with word-level timestamps:
   ```bash
   python scripts/video/transcribe.py <workdir>
   ```
   Writes `<workdir>/transcripts/<take>.json` - segments with start/end and
   per-word timing and confidence.
3. **Choose the takes.** Read the transcripts and write `<workdir>/edl.txt`,
   one cut per line:
   ```
   BASENAME|START_SEC|END_SEC|free-text label
   ```
   Rule of thumb that held up in practice: the *last* attempt of a sentence in
   a file is the usable one, and long uninterrupted runs inside one file are
   worth keeping whole - they read as a single shot instead of a cut fest.
4. **Build**:
   ```bash
   bash scripts/video/build_montage.sh <workdir>
   ```
   Each cut is normalised to 1920x1080 / 30 fps / yuv420p and gets the audio
   chain `highpass=f=80, arnndn (RNNoise), speechnorm`, then all parts are
   concatenated with `-c copy` into `<workdir>/montage.mp4`.

## Notes

- `arnndn` needs the model path **relative to ffmpeg's cwd**. An absolute
  Windows path breaks the filter parser on the drive-letter colon, and Git Bash
  mangles the escaped form - so the build script copies the `.rnnn` next to the
  work dir and refers to it by bare filename.
- Keep the source footage out of git. This repo's `exclude/` is ignored; use a
  work dir under there.
