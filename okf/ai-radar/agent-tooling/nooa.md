---
type: tool
title: NOOA (NVIDIA Object-Oriented Agents)
description: NVIDIA framework where an entire agent is one Python class — method bodies with `...` become LLM-driven actions. Promising but pre-1.0 research-alpha.
tags: [nvidia, agent-framework, open-source, research-alpha]
timestamp: 2026-08-27T00:00:00Z
resource: https://github.com/NVIDIA-NeMo/labs-OO-Agents
status: current
supersedes: []
adoption: promising-but-early-not-install-ready
---

# Summary

NOOA (v0.0.8, released 2026-07-30) is a Python framework where an entire
agent is one class: method bodies with `...` become LLM-driven actions,
regular methods stay deterministic code, docstrings serve as prompts, and
type annotations are runtime-checked contracts. Claims strong benchmark
numbers (82.2% SWE-bench Verified, 86.8% CyberGym L1, 85.1% ARC-AGI-3) at
roughly half the token cost of comparable harnesses. Released alongside
NVIDIA's announcement of a 37-member "open secure AI alliance."

# Repo / source check

Apache-2.0, 1.9k stars, 258 commits, legitimate NVIDIA-NeMo-affiliated org
repo with a real, inspectable code/class model. The README self-labels the
project "research software," pre-1.0 (v0.0.x), with explicit safety warnings
about sandboxing LLM-generated code execution. Benchmark claims are not
independently reproduced here.

# Why this is in the radar

Notable architecture idea (docstring-as-prompt, `...`-body-as-LLM-action)
worth tracking, but `adoption: promising-but-early-not-install-ready` — no
security scanner was available in this sandbox to confirm the safety of its
LLM-generated-code sandboxing story, and the project explicitly describes
itself as alpha research software. Not recommended for adoption at this
scan.

# Notes

- Re-check at v1.0 or when a skillspector-equivalent scan is available.
