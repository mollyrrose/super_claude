# AI Video Pipeline — Setup Guide

This guide installs a hybrid AI-video stack for `super_claude`:

- **Local**: ComfyUI + LTX-Video 0.9.8 distilled fp8 (2B) — free, runs on consumer GPUs, ~5-15 minutes per 5 s 480p clip on an RTX 4070 Laptop
- **Cloud**: OpenAI Sora 2 / Sora 2 Pro — $0.10-$0.30 per second, ~1-3 minutes per clip, higher quality

Both surfaces are exposed to Claude Code as MCP servers (`comfyui-local`, `sora-cloud`).

## TL;DR

```powershell
cd D:\projects\super_claude
.\scripts\setup_ai_video.ps1
```

Then follow the printed next steps (register MCPs, optionally save workflow JSON, optionally set Sora API key). The script is idempotent — safe to re-run.

---

## Hardware tiers

The setup script auto-detects VRAM and picks the highest tier the machine can run. You can override with `-Tier <letter>`.

| Tier | VRAM       | RAM    | LTX model                       | Resolution / length         | Wall-clock per 5s clip |
|------|------------|--------|---------------------------------|-----------------------------|------------------------|
| S    | >=48 GB    | >=64GB | LTX-2 22B BF16 (full)           | 1080p / 10 s / 24 fps       | 1-3 min                |
| A    | 24-47 GB   | >=64GB | LTX-2 22B BF16 or NVFP8         | 720p / 8 s / 24 fps         | 2-5 min                |
| B    | 12-23 GB   | >=32GB | LTX 0.9.8 fp8 or LTX-2 GGUF Q5  | 480-720p / 5 s / 24 fps     | 3-8 min                |
| **C**| **8-11 GB**| **>=32GB** | **LTX 0.9.8 distilled fp8 (2B)** | **832x480 / 5 s / 24 fps** | **5-15 min**           |
| D    | 4-7 GB     | >=32GB | LTX 0.9.8 GGUF Q3/Q2            | 512x320 / 3-4 s             | 10-30 min              |
| E    | CPU-only   | >=16GB | LTX 0.9.8 GGUF Q2 (CPU)         | 384x256 / 2-3 s             | 30-90 min (impractical) |

> The current setup script covers **Tier C** end-to-end. Other tiers print guidance and stop short of downloads — see *Extending to other tiers* at the bottom.

---

## What the install actually does (Tier C)

1. **Hardware check** — `nvidia-smi`, total RAM, free disk on the target drive
2. **Clone ComfyUI** — `git clone https://github.com/comfyanonymous/ComfyUI` into `ai_video/comfyui/`, then `git checkout <pinned>` (see `scripts/setup_ai_video.ps1` for the current pinned commit)
3. **Create isolated venv** — `python -m venv ai_video/comfyui/.venv`
4. **Install PyTorch cu126** — `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126` (~3 GB)
5. **Install ComfyUI requirements** — `pip install -r requirements.txt` (~500 MB)
6. **Download LTX models** from official Lightricks Hugging Face repo (~23.5 GB on disk):
   - `ltxv-2b-0.9.8-distilled-fp8.safetensors` (4.15 GB) -> `models/checkpoints/`
   - `vae/diffusion_pytorch_model.safetensors` -> renamed to `models/vae/ltx_vae.safetensors` (1.56 GB)
   - `text_encoders/` 4 shards (~17.7 GB) -> `models/text_encoders/t5xxl/`
7. **Generate launcher** — `ai_video/start_comfyui.bat` with the right Tier C flags
8. **Install MCP server deps** — `pip install --user mcp openai` (system Python, so Claude Code can spawn the MCP servers without activating any venv)

9. **Register MCP servers with Claude Code** — the script does this for you if the `claude` CLI is on PATH. If it's missing, the script prints the two commands you need to run manually. Re-running the script after registering is safe (already-registered MCPs are skipped).

Steps you do manually after the script (a few minutes):

10. **Set the Sora API key** (only if you want cloud video):

    Either set the env var:
    ```powershell
    $env:OPENAI_API_KEY = "sk-..."
    ```

    Or write the key to a gitignored file:
    ```powershell
    "sk-..." | Out-File -NoNewline ~/.claude/.openai_api_key
    ```

11. **Save a workflow JSON for local video** (one-time):

    - Run `ai_video\start_comfyui.bat` (opens at `http://127.0.0.1:8188`)
    - In the UI: **Browse Templates -> Video -> LTX-Video**
    - **Important**: pick a template that uses **LTX 0.9.8** (the model the script downloads). LTX-2.3 templates expect ~12 GB additional model files (22B diffusion, spatial upscaler, distillation LoRA) that the Tier C download does NOT include — they will show "missing model" errors in the UI.
    - Use **Save (API Format)** to write to `ai_video\workflows\ltxv_t2v.json`

    The `comfyui_mcp.py` server reads this JSON and patches prompt + dimensions + length into it on every `generate_video` call. The filename must be exactly `ltxv_t2v.json` (set via `COMFYUI_WORKFLOW_DIR` + `WORKFLOW_TEMPLATE_NAME` if you want to override).

12. **Restart Claude Code** so it loads the new MCP servers, then test:

    ```
    Use the comfyui-local generate_video tool with prompt "a slow push-in on a misty pine forest at dawn"
    ```

---

## What worked, what didn't (from the first install on RTX 4070 Laptop, 2026-06-12)

### Worked

- **Direct Python install of ComfyUI** (`git clone` + venv + `pip install torch ... --index-url cu126` + `pip install -r requirements.txt`) — clean, fast (~10 minutes), no surprises. PyTorch 2.12.0+cu126 + CUDA 12.6 toolkit + RTX 4070 driver 560.76 = green.
- **Lightricks/LTX-Video 0.9.8 distilled fp8** — official Hugging Face repo, MIT/Open Weights license, total ~23.5 GB download. The `--fp8_e4m3fn-text-enc` ComfyUI flag is what makes the T5 fit in 8 GB VRAM at all.
- **Custom thin Python MCP servers** (`comfyui_mcp.py`, `sora_mcp.py`) — small (~370 / ~313 lines), stdlib-only except `mcp` and `openai`, auditable, bundled with the project. No Node.js, no Docker.
- **ComfyUI launch on Tier C** — confirmed `http://127.0.0.1:8188/system_stats` returns a healthy response in ~38 seconds with the flags `--lowvram --reserve-vram 1 --preview-method taesd --fp8_e4m3fn-text-enc`. `comfy-aimdo` (the included DynamicVRAM extension) gives an extra ~1 GB effective VRAM via on-the-fly swap.

### Didn't work

- **ComfyUI Desktop installer** (NSIS-Electron from <https://comfy.org/download>). Both `/S` silent mode and an interactive double-click crashed silently at the same place — Windows Event Log showed `Exception 0xc0000005` in `System.dll`, every time. The installer file checksum verified clean (signed by Drip Artificial Inc, the Comfy Org parent) — it's a real installer that just doesn't run on this Win11 build (10.0.26200.8655). **The script skips this entirely** and goes straight to the Python install.
- **`pip install -r requirements.txt` from the wrong directory** — easy mistake from the home folder. The script always `cd`-s explicitly before pip so this can't happen.
- **`cmd /c "...bat"` background launch with output capture** — the launch worked but the output was empty in the captured file. Direct `Start-Process python.exe -RedirectStandardOutput` works and shows the full ComfyUI banner. The script uses the direct form.

### Not blocking, but to know

- **LTX-2.3 (22B) does not fit Tier C** — the 22B param model can't be reduced to 8 GB VRAM even at GGUF Q2, so we use LTX 0.9.8 (2B distilled fp8) instead. LTX-2.3 is for Tier S/A only.
- **Workflow JSON is required** — `comfyui_mcp.py` won't work until you save a workflow from the UI to `ai_video/workflows/ltxv_t2v.json`. The server's error message walks you through it. Auto-generating one is on the TODO — see *Future work*.

---

## Verification

After the script finishes:

```powershell
# 1. ComfyUI launches and responds
.\ai_video\start_comfyui.bat
# In another shell, after ~30-60 s:
curl http://127.0.0.1:8188/system_stats

# 2. MCP servers are registered
claude mcp list
# Should show: comfyui-local, sora-cloud

# 3. Python parses both MCP servers
& "C:/Python313/python.exe" -c "import ast; ast.parse(open(r'D:/projects/super_claude/hermes-agent/claude_code_integration/mcp_servers/comfyui_mcp.py', encoding='utf-8').read()); print('ok')"

# 4. Test generation (after restarting Claude Code so it loads the MCPs)
#    Ask Claude: "use comfyui-local to generate a 5-second clip of a misty forest"
```

---

## Troubleshooting

| Symptom                                                   | Cause                                                    | Fix                                                                                                                |
|-----------------------------------------------------------|----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `nvidia-smi` not found                                    | No NVIDIA driver installed                               | Install the driver from NVIDIA's site; re-run script                                                               |
| `python` not found or version < 3.10                      | Python 3.10+ not on PATH                                 | Install Python 3.13 from python.org, check "Add to PATH"                                                           |
| `git clone` fails                                         | git not installed or network                             | Install Git for Windows, check connection                                                                          |
| `pip install torch ...` fails with `No matching distribution` | PyTorch CUDA wheel not available for your Python version | Either downgrade Python to 3.12, or change the `--index-url` to `whl/cu124`, or fall back to CPU wheels (very slow) |
| ComfyUI OOM during generation                             | Tier picked too high                                     | Re-run script with `-Tier D` to step down                                                                          |
| `comfyui-local` MCP shows "ConnectionRefused"             | ComfyUI not running                                      | Run `ai_video\start_comfyui.bat` first                                                                             |
| `comfyui-local` returns "No workflow at ..."              | Step 11 not done                                         | Save a workflow from the ComfyUI UI in API format                                                                  |
| `sora-cloud` returns "API key not found"                  | Step 10 not done                                         | Set `OPENAI_API_KEY` or write `~/.claude/.openai_api_key`                                                           |
| ComfyUI Desktop installer crash (`System.dll 0xc0000005`) | NSIS-Electron incompatibility on Win11 26200             | Skip Desktop, use the Python install (this is what the script does by default)                                     |

---

## File layout after install

```
D:\projects\super_claude\
- ai_video\
   - comfyui\                          (gitignored — ~30 GB total)
      - main.py
      - .venv\                         (Python venv with PyTorch + reqs)
      - models\
         - checkpoints\ltxv-2b-0.9.8-distilled-fp8.safetensors    (4.15 GB)
         - vae\ltx_vae.safetensors                                (1.56 GB)
         - text_encoders\t5xxl\model-0000{1,2,3,4}-of-00004.safetensors  (17.7 GB)
      - output\                        (generated MP4s land here)
   - workflows\ltxv_t2v.json           (you save this from the UI — not gitignored)
   - start_comfyui.bat                 (gitignored — generated per-machine)
- hermes-agent\claude_code_integration\mcp_servers\
   - __init__.py
   - comfyui_mcp.py                    (local LTX-Video MCP server)
   - sora_mcp.py                       (OpenAI Sora MCP server)
- scripts\
   - setup_ai_video.ps1                (this guide's installer)
- docs\AI_VIDEO_SETUP.md               (this file)
```

---

## Security and privacy

- **No API keys in the repo.** `*.openai_api_key` is gitignored; `OPENAI_API_KEY` env var is read only at MCP-call time.
- **MCP servers run as separate processes.** Claude Code spawns them via `claude mcp add` over stdio. They never modify each other's state or ComfyUI's installation.
- **No model file is committed.** `/ai_video/comfyui/` and `/ai_video/models/` are gitignored — the script downloads them locally per-machine.
- **All downloads come from official sources only.** ComfyUI from `github.com/comfyanonymous`, PyTorch from `download.pytorch.org`, LTX models from `huggingface.co/Lightricks`, OpenAI SDK from PyPI.
- **The script doesn't auto-push to git** — you commit and push separately.

---

## Costs (Sora-only)

- Sora 2: `$0.10/sec`. A 5 s clip = ~$0.50, a 10 s clip = ~$1.00
- Sora 2 Pro: `$0.30/sec`. A 5 s clip = ~$1.50, a 10 s clip = ~$3.00
- Local ComfyUI: free (electricity only)

Set a budget alert on the OpenAI dashboard before using `sora-cloud` from agentic loops.

---

## Future work

- **Bundle a known-good `ltxv_t2v.json` API workflow** so step 11 becomes automatic. Today the workflow is user-saved because the exact node IDs / connections depend on the ComfyUI template version, and shipping a stale one would silently break.
- **Per-tier auto-fallback**: if generation OOMs, step the tier down (e.g. C -> D) and retry once. The `comfyui_mcp.py` server currently returns the raw error; teaching it to retry is on the roadmap.
- **Tier S/A/B/D/E support in the script.** Currently the script knows the tier table but only fully automates Tier C. Other tiers print guidance and stop. PRs welcome.
- **Re-detect command**: `scripts\setup_ai_video.ps1 -Redetect` prints the current tier without touching anything — useful when moving to a new machine.

---

## Extending to other tiers

For Tier B (12-23 GB VRAM) — use LTX 0.9.8 fp8 same as Tier C but drop `--lowvram`, raise resolution. Edit `start_comfyui.bat` and the workflow JSON's `width`/`height` defaults.

For Tier S/A (24+ GB VRAM) — switch to LTX-2.3 22B from <https://github.com/Lightricks/ComfyUI-LTXVideo>. Different model files (Gemma-3 text encoder, not T5), different workflow templates. The setup script's `Get-LtxTier` function picks the right tier name; the install body for non-C tiers is a TODO.

For Tier D (4-7 GB VRAM) — switch to GGUF Q3 quants. Requires the `ComfyUI-GGUF` (city96) custom node. The script does NOT install custom nodes today; doing so safely is the next step.

For Tier E (CPU only) — set `--cpu` in the launcher. Expect 30-90 minutes per clip. Use `sora-cloud` instead for any real work.
