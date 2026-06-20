#!/usr/bin/env python3
"""Smoketest for the new qPlan cross-model critics: subq_critic.py and
claude_critic.py. Exercises pure helpers + opt-in/skip behavior WITHOUT making
any network call or spawning `claude`. Run:
    python cross_model_critics_smoketest.py
Prints per-check lines + 'ALL PASS'; non-zero exit on first failure."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claude_critic as cc  # noqa: E402
import subq_critic as sq  # noqa: E402

n = 0


def check(cond, label):
    global n
    n += 1
    if not cond:
        print(f"[fail] {label}")
        sys.exit(1)
    print(f"[ok] {label}")


# --- subq: base url + default model ---
os.environ.pop("SUBQ_BASE_URL", None)
check(sq.base_url() == "https://api.subq.ai/v1", "subq default base url")
os.environ["SUBQ_BASE_URL"] = "https://example.test/v1/"
check(sq.base_url() == "https://example.test/v1", "subq base url override strips trailing slash")
os.environ.pop("SUBQ_BASE_URL", None)
check(sq.DEFAULT_MODEL == "subq-preview", "subq default model is subq-preview")

# --- subq: opt-in skip when no key (subprocess, real script) ---
env = dict(os.environ)
env.pop("SUBQ_API_KEY", None)
r = subprocess.run([sys.executable, str(HERE / "subq_critic.py")],
                   input='{"task":"t","plan":"p","ledger":[]}',
                   capture_output=True, text=True, env=env)
check(r.returncode == 2 and "SUBQ_API_KEY" in r.stderr, "subq exits 2 with clear msg when no key")

# --- claude_critic: build_prompt embeds the input json ---
p = cc.build_prompt("do X", "PLAN BODY", [{"text": "prior"}])
check("PLAN BODY" in p and "do X" in p and "prior" in p and "ONLY the JSON" in p,
      "claude build_prompt embeds task/plan/ledger")

# --- claude_critic: sanitized_env strips GLM overrides, keeps the rest ---
dirty = {
    "ANTHROPIC_BASE_URL": "https://glm",
    "ANTHROPIC_AUTH_TOKEN": "glmtok",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-flag",
    "ZAI_API_KEY": "z",
    "PATH": "/usr/bin",
    "HOME": "/home/u",
}
clean = cc.sanitized_env(dirty)
check("ANTHROPIC_BASE_URL" not in clean and "ANTHROPIC_AUTH_TOKEN" not in clean
      and "ANTHROPIC_DEFAULT_OPUS_MODEL" not in clean and "ZAI_API_KEY" not in clean,
      "sanitized_env strips GLM/z.ai overrides")
check(clean.get("PATH") == "/usr/bin" and clean.get("HOME") == "/home/u",
      "sanitized_env keeps unrelated vars")

# --- claude_critic: extract_json tolerant parsing ---
check(cc.extract_json('{"verdict":"minor issue","suggestions":[]}')["verdict"] == "minor issue",
      "extract_json fast path")
fenced = 'Sure:\n```json\n{"verdict":"no material issue","suggestions":[]}\n```\nDone.'
check(cc.extract_json(fenced)["verdict"] == "no material issue",
      "extract_json finds object inside prose/fences")
nested = 'noise {"a":{"b":1},"verdict":"major issue","suggestions":[{"text":"x"}]} trailing'
check(cc.extract_json(nested)["verdict"] == "major issue",
      "extract_json handles nested braces + trailing prose")
try:
    cc.extract_json("no json here")
    bad = False
except ValueError:
    bad = True
check(bad, "extract_json raises on no-json")

# --- claude_critic: pick_backend logic ---
saved = {k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "CLAUDE_CRITIC_BACKEND")}
os.environ.pop("CLAUDE_CRITIC_BACKEND", None)
os.environ["ANTHROPIC_API_KEY"] = "sk-test"
check(cc.pick_backend() == "api", "pick_backend -> api when ANTHROPIC_API_KEY set")
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["CLAUDE_CRITIC_BACKEND"] = "cli"
check(cc.pick_backend() == "cli", "pick_backend honors forced cli")
for k, v in saved.items():
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v

print(f"\nALL PASS ({n} checks)")
