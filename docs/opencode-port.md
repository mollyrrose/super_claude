# OpenCode port of super_claude

Ha valaki OpenCode-ra akarja húzni ezt a projektet, ezt csináltuk és hogyan.

## Mit portoltunk, mit nem

### Portolható (megcsináltuk)

| Claude Code | OpenCode ekvivalens | Hol van |
|-------------|---------------------|---------|
| `~/.claude/CLAUDE.md` globális utasítások | `~/.config/opencode/AGENTS.md` | `~/.config/opencode/AGENTS.md` |
| Skill-ek (coder, planner, reviewer, stb.) | OpenCode agents | `~/.config/opencode/agents/*.md` |
| `/qRem` slash command | `/rem` command + template | `opencode.json` command section |
| `/qClose` slash command | `/close` command + template | `opencode.json` command section |
| `/qPlan` slash command | `/plan` command + template | `opencode.json` command section |
| Model konfig | provider + model a `opencode.json`-ban | `~/.config/opencode/opencode.json` |

### NEM portolható (Claude Code-specifikus)

- **Python hook-ok** (`UserPromptSubmit`, `PostToolUse`, `Stop`, stb.) -- OpenCode-ban JS plugin kellene, Claude Code hook API nincs
- **Skill tool trigger** (`/skill-name` -> SKILL.md betölt) -- nincs OpenCode-ban ilyen mechanizmus
- **qRev fleet** (15 párhuzamos agent 3 passzban) -- Claude Code Task tool-ra épül
- **Statusline** (context bar, process progress bar) -- Claude Code-specifikus
- **coord.py** multi-window koordináció -- Claude Code REPL-specifikus
- **Curator / hermes-learn** auto-skill pipeline -- Claude Code hook-ra épül

### Manuálisan elérhető marad (CLI-ből vagy OpenCode `bash` tool-ból)

```powershell
# Noisy output tömörítés (token-takarékos)
python D:\projects\super_claude\scripts\tokenjuice.py -- git log --oneline -20

# Nagy fájl tömörítés mielőtt a modellnek adnád
python D:\projects\super_claude\scripts\tokenjuice_condense.py --file nagy_fajl.json

# Load-gated retry runner (terhelt gépen)
python D:\projects\super_claude\scripts\load_retry_runner.py --timeout 30 -- npm test
```

---

## Fájlstruktúra amit létrehoztunk

```
~/.config/opencode/
  opencode.json          -- fő config (provider, model, agents, commands, permissions)
  AGENTS.md              -- globális utasítások (CLAUDE.md adaptálva)
  agents/
    coder.md             -- implementációs specialista
    planner.md           -- architektúra/tervezés, nem kódol
    reviewer.md          -- code review, read-only
    researcher.md        -- kutatás/elemzés, read-only
    rem.md               -- projekt orientáció (agent picker-ből)
    close.md             -- session close runbook (agent picker-ből)
  commands/              -- (referencia; a tényleges template a opencode.json-ban van)
    rem.ps1
    close.ps1
    plan.ps1
```

---

## Setup lépések (fresh install)

### 1. llama-server telepítés

```powershell
# Modell helye: C:\llama\Ornith-1.0-35B-MTP-APEX-I-Compact.gguf
# Indítás (32K kontextus):
.\llama-server.exe -m "C:\llama\Ornith-1.0-35B-MTP-APEX-I-Compact.gguf" `
  -ngl 99 --n-cpu-moe 24 --no-mmap `
  --spec-type draft-mtp --spec-draft-n-max 2 `
  --flash-attn on -c 32768 `
  --temp 0.2 --top-p 0.95 `
  --repeat-penalty 1.1 --repeat-last-n 256 `
  --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 `
  --jinja
# Várj amíg kiírja: "HTTP server listening on 127.0.0.1:8080"
```

### 2. OpenCode telepítés

```powershell
npm install -g opencode-ai   # vagy: npx opencode-ai@latest
```

### 3. Config másolás

A `~/.config/opencode/` tartalmát másold át, vagy hozd létre az alábbi `opencode.json`-nal:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "llama.cpp/ornith",
  "shell": "pwsh",
  "autoupdate": false,

  "provider": {
    "llama.cpp": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "llama-server (local)",
      "options": { "baseURL": "http://127.0.0.1:8080/v1" },
      "models": {
        "ornith": {
          "name": "Ornith 35B (local)",
          "limit": { "context": 32768, "output": 4096 }
        }
      }
    }
  },

  "instructions": ["{file:./AGENTS.md}"],

  "permission": {
    "read": "allow",
    "write": "ask",
    "edit": "ask",
    "bash": "ask",
    "webfetch": "allow",
    "task": "allow"
  },

  "command": {
    "rem": {
      "description": "Project orientation -- branch, changes, tasks, next step",
      "template": "Do these steps now, no planning: 1) run git branch --show-current, git status --short, git log --oneline -5. 2) read INDEX.md lines 1-40 if it exists. 3) read exclude/SYSTEM_STRATEGIES/TODO.md lines 1-30 if it exists. Then reply with: branch name, uncommitted files (or 'clean'), last 5 commits, open tasks, one suggested next step. Keep it short."
    },
    "close": {
      "description": "Session close -- show status, suggest commit message, wait for ok",
      "template": "Run git status --short and git diff --stat. Show what would be committed. Suggest one commit message (imperative, max 72 chars). Wait for my confirmation before running git commit. After commit, ask separately whether to push."
    },
    "plan": {
      "description": "Plan before code -- files to change, order, decisions",
      "template": "Read INDEX.md lines 1-40 if it exists. Then ask me what to plan. When I describe the task, produce: which files to change and why, what order, key decisions. No code, plan only."
    }
  },

  "agent": {
    "coder":      { "description": "Implementation specialist -- clean code, minimal diffs",              "model": "llama.cpp/ornith", "prompt": "{file:./agents/coder.md}" },
    "planner":    { "description": "Architecture and planning -- design before code",                     "model": "llama.cpp/ornith", "prompt": "{file:./agents/planner.md}" },
    "reviewer":   { "description": "Code review -- correctness, security, quality; read-only",           "model": "llama.cpp/ornith", "prompt": "{file:./agents/reviewer.md}", "permission": { "write": "deny", "edit": "deny" } },
    "researcher": { "description": "Research and analysis -- structured findings; read-only",            "model": "llama.cpp/ornith", "prompt": "{file:./agents/researcher.md}", "permission": { "write": "deny", "edit": "deny" } },
    "rem":        { "description": "Project orientation -- reads key files, produces status summary",     "model": "llama.cpp/ornith", "prompt": "{file:./agents/rem.md}", "permission": { "write": "deny", "edit": "deny" } },
    "close":      { "description": "Session close runbook -- update docs, commit, gated push",           "model": "llama.cpp/ornith", "prompt": "{file:./agents/close.md}" }
  }
}
```

### 4. AGENTS.md

A `~/.config/opencode/AGENTS.md` tartalmazza a globális viselkedési szabályokat.
Legfontosabb részek a `~/.claude/CLAUDE.md`-ből adaptálva:
- Munkastílus (read before edit, minimal diffs, verify)
- Token fegyelem (32K kontextus -- sokkal kisebb mint Claude!)
- Kódminőség (no decorative unicode, no useless comments)
- Dual-layer kérdésforma (technikai + laikus magyarázat együtt)
- USER INPUT REQUIRED banner
- Irreversible op gate (push előtt mindig kérdez)

---

## Használat

### Slash commandok (chat inputban)
| Command | Mit csinál |
|---------|-----------|
| `/rem`  | Projekt orientáció: branch, git status, TODO, next step |
| `/close` | Session lezárás: docs update, commit, push gate |
| `/plan` | Tervezési mód: fájlok, sorrend, döntések -- kód nélkül |

### Agenteket az agent picker-ben éred el (Tab vagy UI gomb)
`coder`, `planner`, `reviewer`, `researcher`, `rem`, `close`

---

## Ismert korlátok és trükkök

### 32K kontextus -- KRITIKUS

Ornith 35B lokális modell, 32K token kontextus. Ez kb. 1/6-a a Claude 200K ablakának.
Praktikus szabályok:
- Ne dobj be egész fájlokat -- kérj csak releváns részeket
- Használd a tokenjuice scripteket noisy output előtt
- Ha a modell "beragad" tervezgetésbe: rövidebb, direktebb prompt kell
- Ha compact történt: a kontextus elveszett, újra kell orientálni (`/rem`)

### Template-ek = EGYETLEN action, nem multi-step terv

Ornith `--jinja` flag-gel extended thinking módban fut. Multi-step template-re
("csináld ezt, aztán ezt, aztán azt") a modell egy "Goal/Progress/Next Steps"
planning framework-öt generál, ami felemésztia 32K kontextust mielőtt bármi
tool call történne -- majd compact, majd megint ugyanez, végtelen loop.

Szabály: **template = egyetlen bash parancs VAGY egyetlen fájl olvasás.**

Jó:
  `"template": "Run: git status --short && git log --oneline -5"`
  `"template": "Show the contents of exclude/SYSTEM_STRATEGIES/TODO.md"`

Rossz (planning loop-ot indít):
  `"template": "Read these files, then run these commands, then produce a summary..."`

Ha több dolgot kell összegyűjteni, csinálj több külön commandot (`/rem`, `/todo`,
stb.) ahelyett hogy egybe zsúfolnád.

### Connection error

Ha `Cannot connect to API` jelenik meg: a llama-server nincs elindítva.
Sorrend: llama-server -> "HTTP server listening" -> opencode indítás.
