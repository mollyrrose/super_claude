---
type: tool
title: OpenClaw 2.0
description: Massively adopted (389k-star) open-source, locally-run agent harness/personal-assistant runtime with 20+ channel integrations; 2.0 repositions it as team/enterprise infrastructure.
tags: [agent-harness, autonomous-agent, open-source, self-hosted, security-architecture]
timestamp: 2026-09-08T00:00:00Z
resource: https://github.com/openclaw/openclaw
status: current
supersedes: []
---

# Summary

OpenClaw is an MIT-licensed, foundation-stewarded (501(c)(3), no commercial
owner) open-source AI agent harness that runs locally on user hardware,
pairs with pluggable model providers (Claude, Codex, local models), and
connects to 20+ messaging platforms plus native macOS/iOS/Android/Windows/
Linux apps. OpenClaw 2.0 (released 2026-08-30) reworks installation, adds a
redesigned control UI (Gateway cold-start cut from ~1.6s to ~575ms),
explicit per-session permission modes with workspace-anchored filesystem
access, private credential prompts kept out of chat/model context,
conversation search, and distributed/shared cloud sessions. Its security
model is "one trust boundary per gateway": unknown DM senders require
approval by default, and tools run on-host unless sandboxing is separately
configured — secondary coverage (The Register, via search summary) flagged
that the new shared-session feature lacks network/filesystem-level
isolation guarantees.

# Repo / source check

Verified directly: MIT license, 389.2k stars, 81.8k forks, 500+
contributors — active and legitimate. Release date and contributor/PR
counts for 2.0 itself come from secondary press (VentureBeat, MarkTechPost,
InfoQ, explainx.ai) reached only via search snippets — direct fetches to
those sites were blocked by this sandbox's egress proxy, so treat those
specific figures and the security-boundary criticism as unverified pending
a primary-source read.

# Why this is in the radar

Arguably the largest open-source project in this space by star count, now
explicitly repositioning as team/enterprise infrastructure — a direct
architectural neighbor to Claude Code-style agent harnesses. The security
posture (host-level tool execution unless sandboxed, no inherent network
isolation on shared sessions) is a concrete risk pattern worth tracking if
this project or its users ever consider using or forking it.
