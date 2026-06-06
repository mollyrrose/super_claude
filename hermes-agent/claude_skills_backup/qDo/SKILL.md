# qDo — Zero-friction Do (no "Yes/Yes-don't-ask/No" prompts)

## When to use

The user wants Claude Code to stop firing "Do you want to proceed?" / "Yes / Yes (and don't ask again) / No" dialogs for routine operations. This skill produces the **one-time settings snippet** they need to paste into `~/.claude/settings.json` (or the project-local `.claude/settings.json`), and tells you how to behave after that.

I cannot disable the permission prompts autonomously — modifying `settings.json` itself triggers a prompt. The snippet must be pasted by the user, or they must answer "Yes (and don't ask again)" once per tool family as the prompts come up. Either way, after one round of friction, the system is silent.

## What to do

1. **Print the snippet inline** (don't write the file yourself — the user pastes it). This is the maximally permissive routine-operations preset:

   ```json
   {
     "permissions": {
       "allow": [
         "Bash(*)",
         "PowerShell(*)",
         "Read(*)",
         "Write(*)",
         "Edit(*)",
         "Glob(*)",
         "Grep(*)",
         "ScheduleWakeup(*)",
         "Skill(*)",
         "TaskCreate(*)",
         "TaskUpdate(*)",
         "TaskList(*)",
         "Monitor(*)",
         "WebFetch(*)",
         "WebSearch(*)"
       ],
       "deny": []
     }
   }
   ```

2. **Tell the user where to paste it**:
   - Global: `C:\Users\<user>\.claude\settings.json` (Windows) or `~/.claude/settings.json` (mac/Linux)
   - Project-local: `<repo>/.claude/settings.json` — overrides global for this repo only
   - Merge with any existing `permissions.allow` entries; don't replace the whole file blindly.

3. **For tools not in the snippet** (e.g. specific MCP servers, future deferred tools), instruct: when the prompt appears, pick **"Yes (and don't ask again)"** — that auto-appends the entry.

4. **From this point on, behave with zero approval friction for routine work**:
   - No "should I proceed?" before edits, bash commands, file writes
   - No "shall I run the tests?" — just run them
   - No "let me know if you'd like me to..." — do it
   - **No multiple-choice menus at end-of-turn** ("Mit csináljunk most? A) ... B) ... C) ..."). Pick the highest-value next step, state which one and why in one line, and start it. The user will redirect if wrong.
   - **No "shall I tackle X or Y first?" / "do you want me to also do Z?"** — pick, announce, execute.

5. **Still pause for case-by-case confirmation** (the snippet does NOT bypass these — judgment still applies):
   - Destructive irreversible ops: `rm -rf` outside the repo, `git push --force`, `git reset --hard` of unpushed commits, `DROP TABLE` / `TRUNCATE`
   - Operations visible to others: sending messages (Slack/Telegram/email), posting PRs/issues/comments, modifying shared CI/CD
   - Uploading content to third-party services beyond what's already configured (paste-bins, gists, render services)
   - Anything the user previously tagged as "ask first" via a feedback memory

## Do not

- Do not edit `~/.claude/settings.json` yourself. That triggers another prompt, defeating the point. Print the snippet; let the user paste.
- Do not interpret `/qDo` as "do every dangerous thing without thinking". Only routine prompts go away. The judgment list above still applies.
- Do not re-emit this skill after the user has pasted the snippet — once the prompts stop, your job is done; just operate normally.
- Do not create new files (e.g. a workflow doc) for this — it's a one-time thing, not an ongoing artifact.
