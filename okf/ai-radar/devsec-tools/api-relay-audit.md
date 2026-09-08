---
type: tool
title: API Relay Audit
description: Local, dependency-free audit tool fingerprinting tampering by AI API relays/LLM proxies — prompt injection, model substitution, tool-call rewriting, context truncation.
tags: [supply-chain, llm-proxy, prompt-injection, audit, python, unverified]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/toby-bridges/api-relay-audit
status: unverified
supersedes: []
---

# Summary

A standalone `audit.py` (stdlib + curl only) that runs a 14-step audit
against a configured OpenAI-/Anthropic-compatible relay endpoint, using a
"canary" binary-search technique to locate exactly where context gets
truncated, and diffing behavior against known-good provider responses to
catch silent model substitution or injected system prompts. Produces a
Markdown report with a LOW/MEDIUM/HIGH verdict and explicitly disclaims
that it "does not certify a relay is safe." Has general/web3/full profiles
and a large in-repo dev diary documenting an AI-assisted build with
multiple independent review passes.

# Repo / source check — unverified

Created 2026-03-30, last push 2026-08-29, 824 stars / 79 forks / 24 open
issues, AGPL-3.0, 808 pytest-collected tests per README. Single maintainer,
no organizational backing. No obfuscated code or suspicious install hooks
found in README + linked docs, but the full `audit.py` source was not
reviewed line-by-line — cannot certify it's free of anything malicious.

# Why this is in the radar

LLM API relays/proxies (OpenAI-compatible gateways, Claude-compatible
proxies) are an under-scrutinized trust boundary; a tool purpose-built to
catch relay-side tampering (including wallet-drain-style Web3 risk) is a
novel niche not covered by any existing bundle entry.

# Notes

- Read the full `audit.py` source before any adoption decision — this entry
  is docs-level review only.
