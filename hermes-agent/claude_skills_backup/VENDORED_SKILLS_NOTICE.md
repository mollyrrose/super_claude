# Vendored third-party skills — notice + scan record

These skill directories are vendored (skill dirs only, not the upstream
`benchmarks/`/`tests/`/`src/`) from third-party repos. Each was scanned with
NVIDIA skillspector before install; see `~/.claude/.skillspector_log.jsonl`.

| Skill dir(s) | Upstream | License | skillspector | Decision |
|---|---|---|---|---|
| `improve` | shadcn/improve | see IMPROVE_LICENSE.md | 65 HIGH | installed (sole flag is its own anti-injection safety rule) |
| `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-help` | DietrichGebert/ponytail (MIT) | PONYTAIL_LICENSE.txt | 100 CRITICAL | installed (malice flags all in benchmarks/; runtime-clean) |
| `drawio-skill` | Agents365-ai/drawio-skill | DRAWIO_SKILL_LICENSE.txt | 100 CRITICAL | installed (runtime flags are XML-comment false positives) |
| `arbor-*` (11) | RUC-NLPIR/Arbor (Apache-2.0) | ARBOR_LICENSE.txt | 100 CRITICAL | kept (risky code lives in src/ CLI we never run; skill-only usage) |

The CRITICAL scores were reviewed line-by-line: they are dominated by auxiliary
code, inherent agent behavior (a skill instructing an AI to run code / use tools),
and literal false positives. No actual malice was found in any runtime path. The
scans were overridden per explicit user decision on 2026-06-17.

Our augmentations (how these are wired into qMin/qRev/qPlan/qUpd) live in those
skills, not in the vendored content, so upstream stays updatable.
