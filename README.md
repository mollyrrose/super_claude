# super_claude

> Claude Code setup, ami a **Claude Pro / Max előfizetésedet** használja inference-re,
> kibővítve egy ~165-elemes skill-bundle-lel, automata skill-curate-tel és smart
> prompt-routerrel. Külön Anthropic / OpenAI API kulcs nem kell az alapfunkciókhoz.

---

## Mit tartalmaz a repo

```
hermes-agent/
├── claude_code_integration/    ← a tényleges Claude Code integráció (hookok, curator, lifecycle, router)
├── claude_skills_backup/        ← ~165 skill (Hermes-eredetűek átalakítva + saját kiegészítések)
├── CLAUDE_ELOFIZETES.md         ← beüzemelési útmutató (Claude Pro/Max OAuth)
└── INTEGRATION_CLAUDE_CODE.md   ← integrációs architektúra leírás
```

Az upstream Hermes-runtime összes többi része (agent core, gateway, TUI, web, docker
stb.) szándékosan **nincs** ebben a repóban — a Claude Code integrációhoz nincs rá
szükség. Ha az teljes Hermes-fork kell, lásd <https://github.com/nousresearch/hermes-agent>.

## Mit tud

- **Automata önTanulás** — a `Stop` hook minden befejezett sessiont queue-be tesz; a
  következő prompt elején Claude **a saját session-jében** átolvassa, és magas-bizonyosságú,
  ismétlődő pattern-ekből új skilleket ír közvetlenül `~/.claude/skills/hermes-auto-<slug>/`
  alá. Külön API-hívás nincs — a Pro/Max előfizetésed fedi a költséget.
- **Skill-bundle** — ~165 specializált skill: kód-review, build-fixer-ek, design-segédek,
  domain-tudás (finance, legal, marketing), saját workflow-skillek (qPlan, qRem, qMin,
  qUpd, qDo, rev, hunt, think, learn, write, …).
- **Smart prompt router** — minden user-prompt elejére futó deterministic hook, ami a
  prompt mintázata alapján opcionálisan skill-ajánlást fűz hozzá (build hibák → build-resolver,
  „review my code" → code-review-expert, stb.). LLM-mentes — szabályalapú.
- **Skill-lifecycle** — 7 naponta egyszer fut egy deterministic pass, ami 90 coding-day
  óta nem használt skilleket `~/.claude/skills-archive/` alá mozgat. Bicikli-elv: csak
  az aktivitásos napok számítanak.

## Telepítés

### Előfeltételek

1. **Claude Code** telepítve és bejelentkezve:
   ```powershell
   npm install -g @anthropic-ai/claude-code
   claude /login
   ```
   A login után létrejön `~/.claude/.credentials.json` (Windows-on:
   `C:\Users\<user>\.claude\.credentials.json`).

2. **Python 3.10+** és `pip`.

### Lépések

```powershell
# 1. Klónozd ide vagy bármilyen állandó helyre
git clone git@github.com:mollyrrose/super_claude.git D:\projects\super_claude
cd D:\projects\super_claude

# 2. Telepítsd a skill bundle-t és kapcsold be a hookokat
python hermes-agent\claude_code_integration\install_into_claude_code.py
```

Az installer:
- bemásolja a `claude_skills_backup/*` skilleket a `~/.claude/skills/hermes-*` alá,
- bedrótozza a `Stop`, `PreCompact`, `UserPromptSubmit` hookokat a `~/.claude/settings.json`-be,
- létrehoz egy üres `~/.claude/.hermes_curator_queue.json` queue-t.

Ha kézzel akarod beállítani, a wiring példa a [`hermes-agent/INTEGRATION_CLAUDE_CODE.md`](hermes-agent/INTEGRATION_CLAUDE_CODE.md) végén van.

### Ellenőrzés

```powershell
claude --version
# Indíts egy Claude session-t, futtass egy /qRem vagy bármelyik hermes-* parancsot.
```

## Hogyan működik az auto-curate (röviden)

Részletes leírás: [`hermes-agent/INTEGRATION_CLAUDE_CODE.md`](hermes-agent/INTEGRATION_CLAUDE_CODE.md).

1. **Stop hook** (session vége): csak queue-bejegyzést ír — instant, ingyen, offline.
2. **UserPromptSubmit hook** (következő prompt eleje): ha a queue threshold-ja telve
   (alapból 3 session vagy 7 nap), utasítást told Claude-nak a `additionalContext`-en
   keresztül: „A user kérése előtt csendben curate-eld a queue-t."
3. **Claude saját** a saját session-jében átolvassa a régi transcripteket, és magas-bizonyosságú,
   legalább 2 sessionben ismétlődő, generikus pattern-eket talál → `~/.claude/skills/hermes-auto-<slug>/SKILL.md`
   alá ír. Konzervatív: zero new skill egy queue-ból a default elvárt eredmény.
4. A válasz tetején egy státusz-sor jelzi: `· curator: drained N session(s), wrote M auto-skill(s)`,
   utána normálisan válaszol a user promptjára.

Az új skillek **azonnal** elérhetőek slash-parancsként.

## Konfigurálás

A repo nem tárol semmilyen titkos kulcsot. A `claude_code_integration/` hookok a Claude OAuth
tokent használják (`~/.claude/.credentials.json`), amit a `claude /login` hoz létre. **Ne**
commit-old soha a `.credentials.json`-t, sem a `.hermes_*.json` állapot-fájlokat — a
beépített `.gitignore` ezeket kizárja.

Ha más OpenAI / Anthropic / GitHub kulcsokat is használsz Claude-skillekben, a `~/.claude/settings.json`
`env` mezőjében tárold, **NEM** a repóban.

## Licenc

- Az upstream Hermes-eredetű kód (`hermes-agent/claude_code_integration/` és a
  `claude_skills_backup/hermes-*` skillek) az eredeti Apache 2.0 licensze alatt
  marad — lásd [`hermes-agent/LICENSE`](hermes-agent/LICENSE).
- A repo-specifikus kiegészítések (ez a README, a fork-szintű módosítások)
  ugyanúgy Apache 2.0.

## Upstream

- Hermes Agent: <https://github.com/nousresearch/hermes-agent>
- Claude Code: <https://github.com/anthropics/claude-code>
