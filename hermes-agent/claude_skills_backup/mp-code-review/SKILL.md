---
name: mp-code-review
description: Two-axis review of a diff -- Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/PRD asked for?). Runs both reviews in parallel sub-agents and reports them side by side. Use when reviewing a branch, PR, WIP changes, or any "review since X" request.
source: https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/
license: MIT
---

# mp-code-review (Matt Pocock two-axis review)

Two-axis review of the diff between `HEAD` and a fixed point the user supplies:

- **Standards** -- does the code conform to this repo's documented coding standards?
- **Spec** -- does the code faithfully implement the originating issue / PRD / spec?

Both axes run as **parallel sub-agents** so they don't pollute each other's context, then this skill aggregates their findings.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point -- a commit SHA, branch name, tag, `main`, `HEAD~5`, etc. If they didn't specify one, ask for it.

Capture the diff command: `git diff <fixed-point>...HEAD` (three-dot, comparison against the merge-base). Also note the list of commits via `git log <fixed-point>..HEAD --oneline`.

Before going further, confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail here -- not inside two parallel sub-agents.

### 2. Identify the spec source

Look for the originating spec, in this order:
1. Issue references in the commit messages (`#123`, `Closes #45`) -- fetch via the issue tracker.
2. A path the user passed as an argument.
3. A PRD/spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing found, ask. If there is no spec, the **Spec** sub-agent reports "no spec available".

### 3. Identify the standards sources

Anything in the repo that documents how code should be written (`CODING_STANDARDS.md`, `CONTRIBUTING.md`).

On top of repo-documented standards, the Standards axis always carries the **smell baseline** (from Fowler's Refactoring ch.3) -- a fixed set of heuristics:

- **Mysterious Name** -- a function, variable, or type whose name doesn't reveal intent. Fix: rename it.
- **Duplicated Code** -- the same logic shape in more than one hunk or file. Fix: extract and share.
- **Feature Envy** -- a method that reaches into another object's data more than its own. Fix: move the method.
- **Data Clumps** -- the same few fields keep travelling together. Fix: bundle into one type.
- **Primitive Obsession** -- a primitive standing in for a domain concept. Fix: give the concept its own type.
- **Repeated Switches** -- the same switch/if-cascade on the same type recurs. Fix: polymorphism or one shared map.
- **Shotgun Surgery** -- one logical change forces scattered edits across many files. Fix: gather into one module.
- **Divergent Change** -- one file is edited for several unrelated reasons. Fix: split by responsibility.
- **Speculative Generality** -- abstraction added for needs the spec doesn't have. Fix: inline it back.
- **Message Chains** -- long `a.b().c().d()` navigation. Fix: hide the walk behind one method.
- **Middle Man** -- a class that mostly just delegates onward. Fix: cut it, call the real target direct.
- **Refused Bequest** -- a subclass that ignores or overrides most of what it inherits. Fix: use composition.

Two rules:
- **The repo overrides.** A documented repo standard always wins over the baseline.
- **Always a judgement call.** Each smell is a labelled heuristic, never a hard violation.

### 4. Spawn both sub-agents in parallel

Send a single message with two Agent tool calls. Use the general-purpose subagent for both.

**Standards sub-agent prompt -- include:**
- The full diff command and commit list.
- The list of standards-source files found.
- The smell baseline pasted in full.
- Brief: "Report -- per file/hunk -- (a) every place the diff violates a documented standard: cite the standard; and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls. Skip anything tooling already enforces. Under 400 words."

**Spec sub-agent prompt -- include:**
- The diff command and commit list.
- The path or fetched contents of the spec.
- Brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec sub-agent and note this in the final report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings. Do **not** merge or rerank findings -- the two axes are deliberately separate.

End with a one-line summary: total findings per axis, and the worst issue within each axis (if any). Don't pick a single winner across axes.

## Why two axes

A change can pass one axis and fail the other:
- Code that follows every standard but implements the wrong thing -> **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions -> **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.
