# RNNoise model weights (for ffmpeg's `arnndn` filter)

Speech noise-suppression weights used by `ffmpeg -af arnndn=m=<file>`.
`arnndn` runs the RNNoise recurrent neural network - real AI denoising, no
Python, no torch, and ffmpeg already ships the filter.

| file | source |
|---|---|
| `sh.rnnn` | `GregorR/rnnoise-models` - `somnolent-hogwash-2018-09-01` |
| `bd.rnnn` | `GregorR/rnnoise-models` - `beguiling-drafter-2018-08-30` |

Fetched 2026-09-08 by direct raw download of the two weight files (no clone).
These are model weights, not executable code, so the skillspector gate does not
apply in its usual form - and that gate's documented binary path is currently
missing on this machine anyway (see `~/.claude/skills/skillspector-gate/`).
Flagging that here rather than pretending a scan happened.

Usage: see `scripts/video/README.md`.
