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
import glm_critic as gm  # noqa: E402
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

# --- claude_critic: cli_model_chain head + fallback + dedup ---
os.environ.pop("CLAUDE_CRITIC_CLI_MODEL", None)
check(cc.cli_model_chain() == ["opus", "sonnet", "haiku"],
      "cli_model_chain default head is opus, full fallback chain")
check(cc.cli_model_chain("sonnet") == ["sonnet", "opus", "haiku"],
      "cli_model_chain override moves model to head and dedups")
os.environ["CLAUDE_CRITIC_CLI_MODEL"] = "haiku"
check(cc.cli_model_chain() == ["haiku", "opus", "sonnet"],
      "cli_model_chain honors CLAUDE_CRITIC_CLI_MODEL env")
os.environ.pop("CLAUDE_CRITIC_CLI_MODEL", None)

# --- glm_critic: base url default + override strip ---
os.environ.pop("GLM_BASE_URL", None)
check(gm.base_url() == "https://api.z.ai/api/paas/v4", "glm default base url")
os.environ["GLM_BASE_URL"] = "https://example.test/v4/"
check(gm.base_url() == "https://example.test/v4", "glm base url override strips trailing slash")
os.environ.pop("GLM_BASE_URL", None)

# --- glm_critic: api_key prefers GLM_API_KEY, falls back to ZAI_API_KEY ---
glm_saved = {k: os.environ.get(k) for k in ("GLM_API_KEY", "ZAI_API_KEY")}
os.environ.pop("GLM_API_KEY", None)
os.environ["ZAI_API_KEY"] = "zai-test"
check(gm.api_key() == "zai-test", "glm api_key falls back to ZAI_API_KEY")
os.environ["GLM_API_KEY"] = "glm-test"
check(gm.api_key() == "glm-test", "glm api_key prefers GLM_API_KEY over ZAI_API_KEY")
for k, v in glm_saved.items():
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v

# --- glm_critic: _pick_best honors MODEL_PRIORITY (glm-5 over glm-4.6) ---
check(gm._pick_best(["glm-4-flash", "glm-4.6", "glm-5.2"]) == "glm-5.2",
      "glm _pick_best prefers glm-5.x flagship")
check(gm._pick_best(["glm-4-flash", "glm-4.6"]) == "glm-4.6",
      "glm _pick_best falls to glm-4.6 when no glm-5")

# --- glm_critic: build_messages embeds task/plan/ledger ---
gm_msgs = gm.build_messages("do Y", "GLM PLAN", [{"text": "prior-g"}])
gm_blob = json.dumps(gm_msgs)
check("GLM PLAN" in gm_blob and "do Y" in gm_blob and "prior-g" in gm_blob,
      "glm build_messages embeds task/plan/ledger")

# --- glm_critic: opt-in skip when no key (subprocess, real script) ---
genv = dict(os.environ)
genv.pop("GLM_API_KEY", None)
genv.pop("ZAI_API_KEY", None)
gr = subprocess.run([sys.executable, str(HERE / "glm_critic.py")],
                    input='{"task":"t","plan":"p","ledger":[]}',
                    capture_output=True, text=True, env=genv)
check(gr.returncode == 2 and ("GLM_API_KEY" in gr.stderr or "ZAI_API_KEY" in gr.stderr),
      "glm exits 2 with clear msg when no key")

# --- subq_critic: free-tier base url override + keyless mute ---
os.environ.pop("SUBQ_FREE_BASE_URL", None)
check(sq.base_url(free=True) == sq.base_url(free=False),
      "subq free base falls back to normal base when SUBQ_FREE_BASE_URL unset")
os.environ["SUBQ_FREE_BASE_URL"] = "https://free.subq.test/v1/"
check(sq.base_url(free=True) == "https://free.subq.test/v1",
      "subq free base honors SUBQ_FREE_BASE_URL and strips slash")
os.environ.pop("SUBQ_FREE_BASE_URL", None)

senv = dict(os.environ)
for k in ("SUBQ_API_KEY", "SUBQ_FREE_API_KEY", "SUBQ_FREE_BASE_URL", "SUBQ_TIER"):
    senv.pop(k, None)
sr = subprocess.run([sys.executable, str(HERE / "subq_critic.py")],
                    input='{"task":"t","plan":"p","ledger":[],"tier":"free"}',
                    capture_output=True, text=True, env=senv)
check(sr.returncode == 2 and "free" in sr.stderr.lower(),
      "subq-free exits 2 with clear msg when no free key/endpoint")

print(f"\nALL PASS ({n} checks)")
