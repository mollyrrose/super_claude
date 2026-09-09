---
type: model
title: K2-Horizon-MoVA-36B-A4B (IFM / MBZUAI)
description: Sparse open-weights model with Mixture-of-Values attention; evaluated for a speed-motivated role in this setup and not adopted.
tags: [k2-horizon, ifm, mbzuai, mova, sparse, moe, open-weights, evaluated-not-adopted]
timestamp: 2026-09-08T00:00:00Z
resource: https://huggingface.co/IFM/K2-Horizon-MoVA-36B-A4B
status: current
supersedes: []
adoption: EVALUATED-not-adopted
---

# Summary

Released 2026-09-03 by IFM (Institute of Foundation Models, MBZUAI) as the
sparse member of the six-model K2 Horizon family (0.9B-375B). Apache-2.0,
open weights.

**MoVA = Mixture-of-Values attention.** Extends sparsity to the *value*
component of attention, unlike ordinary MoE which routes only the FFN.
FlashAttention + GQA compatible. The model card names the mechanism but does
not detail it; training code is not released yet.

Not to be confused with the 2026 "Mixture of Vision Experts" MoVA paper
(arXiv 2404.13046) - unrelated, name collision only.

| Property | Value |
|---|---|
| Params | model card: 36B total / 4B active. vLLM recipe: **37.44B / 5.95B active** (contradiction) |
| Context | 524288 native; vLLM recipe serves `--max-model-len 131072` |
| Weights | BF16 only, 74.9 GB. **No official quantization.** |
| Recommended HW | 2x H200, TP=2, SGLang / FlashAttention-3 |
| Endpoint | OpenAI-compatible (vLLM server, platform.ifm.ai, Cerebras, Nebius). **No Anthropic-compatible endpoint.** |
| Tool calling | Supported (`--tool-call-parser k2_horizon`, XML default). tau3-Banking 26.8, Terminal-Bench 2.1 58.6 |
| Code | SciCode 38.9 (dense rivals 43.6 / 43.4) |
| Reasoning | GPQA Diamond 80.8 (vs 86.7); HLE 25.2 (vs 28.4) |

# Why this is in the radar

Evaluated 2026-09-08 for one specific question: **is its speed advantage -
not its knowledge - useful anywhere in this setup?** Answer: no. Recorded so
the evaluation does not have to be repeated.

1. **The speed claim is unmeasured.** No published tokens/sec, latency or
   throughput for this model anywhere. "Faster" is inferred from the active
   parameter count - and that count is itself contradictory (see table).
   IFM's ~3x throughput claim attaches to a diffusion-distillation technique
   across the family, not verifiably to this variant.
2. **It is reachable exactly where speed does not matter.** The qPlan panel's
   generic OpenAI-compatible critic clients (`subq_critic.py`,
   `glm_critic.py`) take `*_BASE_URL` / `*_MODEL` / `*_API_KEY` overrides, so a
   hosted endpoint could be wired in today with zero code. But that is a
   single critic call where latency is irrelevant - and the role wants a
   *strong, different-family* model, which this is not.
3. **It is not reachable where speed would matter.** The latency-dominated
   fleets (`/qRev` 15 agents x 3 passes, `focus-group` 215 personas) are
   `Task` calls bound to the session provider; per-agent endpoints cannot be
   selected. Only a session-wide OpenAI->Anthropic translating proxy plus a
   haiku-alias remap would reach them.
4. **Even via proxy it would be slower, not faster.** Weak multi-turn tool
   use (tau3-Banking 26.8/100) would trip qRev's own tripwire - "an agent
   returning after 0-1 tool uses is a failed dispatch, re-dispatch it" -
   turning a latency win into a repeat-dispatch loss.
5. **And more expensive.** The fleet is subscription-covered ("no per-token
   bill"). Trading a flat rate for a metered API to buy wall-clock is a net
   loss.

# Source check

Open weights, Apache-2.0, no repo audit applicable (model weights, not a tool
repo) - so no skillspector gate. Grounding: HF model card, vLLM recipe page,
GGUF repo, plus three independent write-ups. The 36B/A4B vs 37.44B/5.95B
discrepancy is a genuine contradiction between the model card and the vLLM
recipe, not a transcription error on our side.

# Notes

- **Filter for any future speed test:** if a hosted endpoint benchmarks fast,
  first establish whether that is the *model* or the *hardware* (Cerebras).
  If it is the hardware, every model on that host is equally fast and the
  whole MoVA/A4B argument is irrelevant.
- **Revisit if:** measured throughput is published, OR official quantization
  ships (removing the 2x H200 floor), OR Claude Code gains per-subagent
  endpoint selection.
