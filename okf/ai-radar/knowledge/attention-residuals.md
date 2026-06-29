---
type: technique
title: Attention-Residuals (MoonshotAI)
description: Transformer architecture/training method (learned residual connections) — not applicable to a frozen hosted-API agent or to our file-based memory.
tags: [moonshotai, transformer, architecture, training, not-applicable]
timestamp: 2026-06-29T00:00:00Z
resource: https://github.com/MoonshotAI/Attention-Residuals
status: current
supersedes: []
adoption: not-applicable
---

# What it is

A drop-in replacement for standard Transformer residual connections: each layer
attends over all previous layer outputs via learned, input-dependent pseudo-queries,
instead of uniform fixed-weight accumulation. Addresses PreNorm dilution; reports
scaling-law and downstream gains (+7.5 GPQA-Diamond, +3.1 HumanEval). arXiv 2603.15031.

# Does it apply to US? No.

It modifies the model's internal architecture and requires control of training. We use
a **frozen hosted Claude model via API** — we cannot alter residual connections. It has
**zero applicability to our file-based hermes memory** (which is markdown files, not a
neural network). The only "lesson" is a weak analogy (selective vs uniform aggregation)
that our memory already does at the file level (recall by relevance, not dump-all).

# Repo / source check

Inspected the README (architecture/training paper, license unspecified, 2026). Verdict:
awareness only; `adoption: not-applicable`. `/radar-check` must never recommend adopting
it.
