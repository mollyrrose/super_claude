#!/usr/bin/env python3
"""Thin MCP server exposing local ComfyUI as a video-generation tool to Claude Code.

Architecture: Claude Code spawns this server via `claude mcp add`, the server
talks JSON-RPC over stdio, and forwards requests to a running ComfyUI instance
at http://127.0.0.1:8188 (Tier C launch script default). No model loading or
inference happens here — ComfyUI does all the work.

Tools exposed:
- generate_video(prompt, width, height, length_frames, steps) -> output_path
- get_queue_status() -> queue snapshot
- cancel_task(prompt_id) -> deletion confirmation

Workflow handling: the actual node graph (LTX-Video T2V) is loaded from
~/ai_video/workflows/ltxv_t2v.json (the user saves it from ComfyUI's
"Browse Templates -> Video -> LTX-Video" + "Save (API Format)"). This server
substitutes prompt + dimensions + length into the saved graph by class_type
match, never authors a graph from scratch — that responsibility stays with
ComfyUI's UI where the user can visually verify the result.

Dependencies:
- mcp (Anthropic MCP SDK, install: pip install mcp)
- stdlib only otherwise (urllib, json, time, pathlib)

Register with Claude Code:
    claude mcp add comfyui-local -- python "D:/projects/super_claude/hermes-agent/claude_code_integration/mcp_servers/comfyui_mcp.py"

Environment overrides (optional):
- COMFYUI_URL          default http://127.0.0.1:8188
- COMFYUI_WORKFLOW_DIR default D:/projects/super_claude/ai_video/workflows
- COMFYUI_OUTPUT_DIR   default <comfyui repo>/output  (used to resolve returned filenames to absolute paths)
- COMFYUI_POLL_TIMEOUT default 900 (seconds, 15 min — Tier C 5s clip takes 5-15 min)
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    sys.stderr.write(
        "ERROR: 'mcp' package not installed. Run: pip install --user mcp\n"
    )
    sys.exit(1)


COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
WORKFLOW_DIR = Path(
    os.environ.get(
        "COMFYUI_WORKFLOW_DIR",
        "D:/projects/super_claude/ai_video/workflows",
    )
)
OUTPUT_DIR = Path(
    os.environ.get(
        "COMFYUI_OUTPUT_DIR",
        "D:/projects/super_claude/ai_video/comfyui/output",
    )
)
POLL_TIMEOUT = int(os.environ.get("COMFYUI_POLL_TIMEOUT", "900"))
POLL_INTERVAL = 2.0  # seconds between /history checks

WORKFLOW_TEMPLATE_NAME = "ltxv_t2v.json"
CLIENT_ID = str(uuid.uuid4())  # stable for this server lifetime


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only — no requests dep)
# ---------------------------------------------------------------------------

def _http_post(path: str, payload: dict, timeout: float = 15.0) -> dict:
    url = f"{COMFYUI_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get(path: str, timeout: float = 15.0) -> dict:
    url = f"{COMFYUI_URL}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Workflow patching — substitute prompt + dims into saved graph by class_type
# ---------------------------------------------------------------------------

def _load_workflow_template() -> dict:
    """Load the user's saved LTX T2V workflow JSON (API format).

    Raises FileNotFoundError with a clear how-to-fix message if the file
    doesn't exist — that's the most common failure mode the first time.
    """
    path = WORKFLOW_DIR / WORKFLOW_TEMPLATE_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"No workflow at {path}. Open ComfyUI in your browser, pick "
            f"'Browse Templates -> Video -> LTX-Video' (or load any LTX T2V "
            f"workflow), and use 'Save (API Format)' to write the JSON to "
            f"that exact path. Then retry."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_workflow(
    workflow: dict,
    prompt: str,
    width: int,
    height: int,
    length_frames: int,
    steps: int,
) -> dict:
    """Patch a copy of the workflow: prompt text, dimensions, length, steps.

    Strategy: scan nodes by class_type. ComfyUI workflows in API format have
    the shape {"<node_id>": {"class_type": "...", "inputs": {...}}, ...}.

    Patches applied (only when a matching node exists — silent skip otherwise):
    - Any CLIPTextEncode / T5TextEncode with a 'text' input: set positive prompt
      on the first one found. (Negative prompt nodes typically have empty text
      so we deliberately skip empty-text nodes.)
    - EmptyLatentVideo / EmptyHunyuanLatentVideo / LTXVideoLatent: set width,
      height, length.
    - KSampler / KSamplerAdvanced: set steps.

    Returns a new dict (does not mutate the input).
    """
    out = copy.deepcopy(workflow)
    if not isinstance(out, dict):
        raise ValueError("workflow root must be a JSON object (API format)")

    set_prompt = False
    for node_id, node in out.items():
        if not isinstance(node, dict):
            continue
        ctype = node.get("class_type", "")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue

        # Prompt: text-encoder nodes with a non-empty 'text' input
        if (
            not set_prompt
            and ctype in ("CLIPTextEncode", "T5TextEncode")
            and isinstance(inputs.get("text"), str)
            and inputs.get("text", "").strip()
        ):
            inputs["text"] = prompt
            set_prompt = True

        # Dimensions + length
        if ctype in ("EmptyLatentVideo", "EmptyHunyuanLatentVideo", "LTXVideoLatent"):
            if "width" in inputs:
                inputs["width"] = width
            if "height" in inputs:
                inputs["height"] = height
            if "length" in inputs:
                inputs["length"] = length_frames
            if "num_frames" in inputs:
                inputs["num_frames"] = length_frames

        # Sampler steps
        if ctype in ("KSampler", "KSamplerAdvanced") and "steps" in inputs:
            inputs["steps"] = steps

    if not set_prompt:
        raise ValueError(
            "Could not find a positive-prompt text-encoder node in the saved "
            "workflow. Make sure the workflow has a CLIPTextEncode or "
            "T5TextEncode node with non-empty default text."
        )
    return out


# ---------------------------------------------------------------------------
# Submit + poll
# ---------------------------------------------------------------------------

def _submit_workflow(workflow: dict) -> str:
    """POST workflow to ComfyUI; return prompt_id."""
    resp = _http_post("/prompt", {"prompt": workflow, "client_id": CLIENT_ID})
    pid = resp.get("prompt_id")
    if not pid:
        raise RuntimeError(f"ComfyUI did not return a prompt_id: {resp}")
    return pid


def _wait_for_completion(prompt_id: str) -> dict:
    """Poll /history/<prompt_id> until the entry shows up + has outputs.

    Returns the history entry dict. Raises TimeoutError after POLL_TIMEOUT.
    """
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        try:
            history = _http_get(f"/history/{prompt_id}")
        except urllib.error.URLError:
            time.sleep(POLL_INTERVAL)
            continue
        entry = history.get(prompt_id)
        if entry and entry.get("outputs"):
            return entry
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(
        f"ComfyUI did not finish prompt {prompt_id} within {POLL_TIMEOUT}s "
        f"(Tier C 5s clip typically 5-15 min; raise COMFYUI_POLL_TIMEOUT if "
        f"you're consistently hitting this)."
    )


def _extract_output_paths(history_entry: dict) -> list[str]:
    """Find produced video/image file paths in the history entry's outputs.

    ComfyUI output entries look like:
        {"images": [{"filename": "...", "subfolder": "...", "type": "output"}]}
        {"gifs": [...]}, {"videos": [...]}  (depends on the save node)
    We resolve filenames to absolute paths under OUTPUT_DIR.
    """
    paths: list[str] = []
    outputs = history_entry.get("outputs", {})
    for _node_id, out in outputs.items():
        if not isinstance(out, dict):
            continue
        for key in ("images", "gifs", "videos", "files"):
            for item in out.get(key, []) or []:
                fn = item.get("filename")
                sub = item.get("subfolder", "") or ""
                if fn:
                    p = OUTPUT_DIR / sub / fn if sub else OUTPUT_DIR / fn
                    paths.append(str(p))
    return paths


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server: Server = Server("comfyui-local")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_video",
            description=(
                "Generate a video clip on the local ComfyUI instance using the "
                "saved LTX-Video T2V workflow. Substitutes prompt + dimensions "
                "into the workflow and submits to /prompt; polls /history "
                "until done. Tier C defaults (832x480, 121 frames at 24 fps = "
                "~5 s clip, 20 sampling steps) typically take 5-15 minutes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Positive prompt"},
                    "width": {"type": "integer", "default": 832},
                    "height": {"type": "integer", "default": 480},
                    "length_frames": {
                        "type": "integer",
                        "default": 121,
                        "description": "Total frames; 121 @ 24 fps = ~5 s",
                    },
                    "steps": {"type": "integer", "default": 20},
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="get_queue_status",
            description="Get ComfyUI's current queue state (running + pending).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cancel_task",
            description="Cancel a pending or running prompt by its prompt_id.",
            inputSchema={
                "type": "object",
                "properties": {"prompt_id": {"type": "string"}},
                "required": ["prompt_id"],
            },
        ),
    ]


def _ok(payload: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}, indent=2))]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "generate_video":
            prompt = arguments.get("prompt", "").strip()
            if not prompt:
                return _err("prompt is required and must be non-empty")
            width = int(arguments.get("width", 832))
            height = int(arguments.get("height", 480))
            length_frames = int(arguments.get("length_frames", 121))
            steps = int(arguments.get("steps", 20))

            template = _load_workflow_template()
            patched = _patch_workflow(
                template, prompt, width, height, length_frames, steps
            )
            t0 = time.monotonic()
            prompt_id = _submit_workflow(patched)
            entry = _wait_for_completion(prompt_id)
            paths = _extract_output_paths(entry)
            dt = time.monotonic() - t0
            return _ok(
                {
                    "prompt_id": prompt_id,
                    "duration_s": round(dt, 1),
                    "outputs": paths,
                    "workflow_template": str(WORKFLOW_DIR / WORKFLOW_TEMPLATE_NAME),
                }
            )

        if name == "get_queue_status":
            return _ok(_http_get("/queue"))

        if name == "cancel_task":
            pid = arguments.get("prompt_id", "").strip()
            if not pid:
                return _err("prompt_id is required")
            resp = _http_post("/queue", {"delete": [pid]})
            return _ok({"deleted": pid, "response": resp})

        return _err(f"unknown tool: {name}")

    except FileNotFoundError as e:
        return _err(str(e))
    except (urllib.error.URLError, ConnectionError) as e:
        return _err(
            f"Cannot reach ComfyUI at {COMFYUI_URL}: {e}. Is start_comfyui.bat "
            f"running? Default URL is http://127.0.0.1:8188."
        )
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
