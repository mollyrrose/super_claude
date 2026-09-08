---
type: pattern
title: Cursor Self-Hosted Machines for cloud agents
description: Cursor's cloud coding agents can now execute tool calls on infrastructure the customer controls, while Cursor still plans/orchestrates — a direct answer to the "secrets leaving your network" objection to cloud agents.
tags: [cursor, coding-agent, cloud-agents, self-hosted, security]
timestamp: 2026-09-08T00:00:00Z
resource: https://cursor.com/blog/self-hosted-machines
status: current
supersedes: []
---

# Summary

Announced 2026-09-02. "My Machines" connects a single laptop/VM to a
personal account; "Team pools" are named worker queues for teams,
auto-scaling with demand. Codebase, build artifacts, and secrets stay on
the customer's own infrastructure while Cursor's cloud plans/orchestrates
the work remotely. Supported self-hosted execution backends include AWS
Lambda, Coder, Cloudflare, Daytona, Modal, Namespace, Vercel, and E2B.
Self-hosted workers also gained Linux/Mac computer-use (click, type,
screenshot, browser control).

# Repo / source check

Cursor is closed-source; verified via Cursor's own changelog/blog plus an
independent corroborating post from Cloudflare's own changelog
(`developers.cloudflare.com/changelog/post/2026-09-02-cursor-cloud-agents/`)
announcing Cursor Cloud Agents on Cloudflare Sandboxes — a strong
independent confirmation since Cloudflare has no incentive to fabricate a
partner announcement.

# Why this is in the radar

A direct architectural answer to the "secrets/code leaving your network"
objection to cloud coding agents — relevant competitive context since
Claude Code's own sandboxing/self-hosted-runner work (seen in its own
changelog, v2.1.238) is solving an adjacent problem.
