---
type: pattern
title: Claude Code — August 2026 harness updates (v2.1.232-2.1.247)
description: Subagent forking on by default, cross-session messaging, a rolling MCP/hook reliability pass, and the new SendFeedback tool.
tags: [claude-code, hooks, mcp, subagents, changelog]
timestamp: 2026-08-27T00:00:00Z
resource: https://code.claude.com/docs/en/changelog
status: current
supersedes: []
---

# Summary

Three harness-relevant changes landed in the official Claude Code changelog
between v2.1.232 (2026-08-13) and v2.1.247 (2026-08-26):

1. **Subagent forking on by default.** `subagent_type: "fork"` now inherits
   the full parent conversation and prompt cache by default (previously
   opt-in via env var). Forked subagents skip re-briefing and avoid the
   "compression tax" of long sessions.
2. **Cross-session messaging.** `@name` mentions reach another live Claude
   Code session; `SendMessage` can deliver to bare session names; sessions
   get unique auto-generated names (`name-word-word`). Turns concurrent
   windows into an addressable mesh — directly relevant to this repo's own
   `coord.py` cross-window coordination layer (see project CLAUDE.md).
3. **MCP/hook reliability hardening (rolling, ~10 point releases).** Hook and
   background-agent output overflow no longer wedges sessions; MCP tool-call
   interrupts report explicit errors instead of silently returning empty
   output; empty-schema (`{}`) MCP tool arguments no longer get stringified;
   remote MCP servers in `-p`/SDK sessions auto-reconnect after drops; stdio
   MCP servers no longer receive `server/discover` before `initialize`;
   plugin marketplaces gained GitLab support and control-character name
   rejection; self-hosted runner sessions gained server-supplied hook
   support.
4. **`SendFeedback` tool (v2.1.247, 2026-08-26).** Claude can draft an
   in-session feedback report for the user to review/send via `/feedback`.

# Why this is in the radar

Item 3 lands directly on the surfaces this repo's own hook system depends on
(the `hook_dispatch.py` consolidation, silent-no-op-on-bad-input discipline,
MCP tool usage throughout). Item 2 (cross-session messaging) overlaps in
spirit with this repo's own `coord.py`/`work.md` cross-window coordination —
worth a look at whether the built-in mesh reduces the need for the custom
layer, or whether they're complementary (built-in mesh is interactive/adhoc,
`coord.py` is file-based and survives across restarts).

# Repo / source check

Closed-source harness; grounding is the official Claude Code changelog
(`resource`), corroborated by an independent explainer
(joinnextdev.com) for item 1. `code.claude.com` itself was reachable in this
pass; `claude.com`'s blog was not (egress-proxy block in this sandbox).

# Notes

- No action taken on this entry beyond recording it — evaluating whether to
  adopt cross-session `@name` messaging alongside `coord.py` is a separate,
  deliberate decision, not an automatic radar "speak up".
