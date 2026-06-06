# Claude Code agents & skills — integrációs design

A felhasználó már jelentős időt fektetett Claude Code-ban skill-ek, agent-ek
és MCP szerverek konfigurálásába. Ez a dokumentum azt vizsgálja meg, hogyan
tudná Hermes **addicionálisan** használni ezeket a saját 40+ beépített
tool-ja és kategorizált skill-jei mellett.

A dokumentum jelenleg **design only** — semmilyen kódot még nem ad
hozzá. A célja: tiszta döntési alap, ami alapján egy következő iterációban
elindulhat a tényleges implementáció.

---

## Mi van Claude Code-ban, amit érdemes újrahasznosítani

### 1. Slash command skill-ek

**Hely:** `~/.claude/skills/<név>/SKILL.md` (globális) vagy
`<projekt>/.claude/skills/<név>/SKILL.md` (projekt-szintű).

**Formátum:**
```yaml
---
name: <név>
description: "<egy mondat>"
---

# <Cím>

## When to use
...
```

**Tartalom:** prózai utasítások az LLM-nek + opcionális segéd-szkriptek.
Nem deklaratív tool definíció — inkább "viselkedési séma".

### 2. Sub-agents

**Hely:** `~/.claude/agents/<név>.md` vagy plugin alatt
`~/.claude/plugins/.../agents/<név>.md`.

**Formátum:**
```yaml
---
name: <név>
description: "Mire való"
tools: [Read, Grep, Bash, ...]   # vagy: All
model: sonnet | opus | haiku
---

# Rendszer prompt
...
```

**Tartalom:** önálló agent persona-k (pl. `ecc:reviewer`,
`ecc:code-explorer`, `general-purpose`). Hermes-ből nézve ezek külön
sub-agent processzek lennének.

### 3. MCP szerverek

**Hely:** `~/.claude/settings.json` `mcpServers` mezője, projekt-szintű
`.mcp.json`, vagy `claude mcp add ...` parancsból.

**Formátum:** standard MCP protokoll (JSON-RPC stdio vagy HTTP transport).

**Tartalom:** strukturált tool-ok (pl. `context7`, `firecrawl`, `exa`,
`playwright`), erőforrások és promptok.

---

## Mi van Hermes-ben, amibe ezek be tudnának kapcsolódni

### Skill rendszer

- Disk-szintű felfedezés a `skills/<kategória>/<név>/SKILL.md` mintával.
- YAML frontmatter mezői: `name`, `description`, `version`, `author`,
  `license`, `platforms`, `metadata.hermes.tags`,
  `metadata.hermes.related_skills`, `prerequisites.commands`.
- Lényegesen **gazdagabb frontmatter** mint Claude Code-é (tag-eli a
  related_skills-t, prerequisite parancsokat, platformokat).

### Tool rendszer

- 40+ beépített tool a `tools/` alatt, mindegyik egy Python modul.
- Központi `tools/registry.py` regisztrálja őket.
- **MCP tool már létezik** Hermes-ben: `tools/mcp_tool.py` + `mcp_oauth.py`
  — vagyis Hermes natívan tud MCP szervereket hívni.

### Agent rendszer

- Hermes maga **egyetlen** agent + delegate / mixture-of-agents tool-ok,
  amik sub-agent szerű viselkedést adnak.
- Nem azonos a Claude Code "sub-agent" koncepciójával (több persona,
  Task tool-on keresztül).

---

## Három integrációs út

### Út A — Skill-adapter (legkisebb, leghasznosabb)

**Mit csinálnál:** Egy új Hermes loader, ami felfedezi a Claude Code
skill-fájlokat (`~/.claude/skills/`, `<projekt>/.claude/skills/`) és
"virtuális Hermes skill"-ként mutatja őket. A frontmatter konverziója
egyszerű: `name` → `name`, `description` → `description`, hozzáadódik
egy szintetikus `metadata.hermes.tags: [claude-code-imported]`.

**Hol kell változtatás:**
- Új fájl: `skills/__loader_claude_code.py` (vagy `hermes_cli/cc_skill_loader.py`).
- Hook a meglévő skill-felfedező pipeline-ba (ahol jelenleg a
  `skills/<category>/<name>/SKILL.md`-eket olvassa).

**Előny:** A felhasználó Claude Code skill-jei **azonnal** elérhetők
Hermes-ből, nulla duplikáció. Ha ECC új skill-t telepít, automatikusan
megjelenik Hermes-ben is.

**Hátrány:** A skill-ek nyelvezete Claude Code tool-okra utal (Read, Edit,
Bash). Hermes ezeket nem azonos néven ismeri — futáskor szemantikailag
"jól érti", de nem 1:1 a tool elérhetőség (pl. Claude Code-ban van
`Glob` és `Grep`, Hermes-ben `file_operations.search` + grep).

**Mitigáció:** A loader csak felfedez és kínál — ha az LLM olyan tool-ra
hivatkozik, ami nincs meg, Hermes a saját ekvivalensét fogja meghívni.
Kísérleti tag-et adunk hozzá (`claude-code-imported`) a kontextusban.

**Becsült munka:** ~150 sor Python + 1-2 tesztfájl. Egy ülés.

---

### Út B — Agent-átadás (közepes)

**Mit csinálnál:** Új Hermes tool: `delegate_to_claude_code_agent` (mint
ahogyan `delegate_tool` már létezik a Hermes-ben). A tool input-ja egy
Claude Code agent neve (`general-purpose`, `ecc:reviewer`, stb.) és egy
prompt. Belül a `claude` CLI-t hívja meg subprocess-ként, paraméterezve,
hogy melyik agent-tel futtassa.

**Hol kell változtatás:**
- Új fájl: `tools/claude_code_agent_tool.py`.
- Regisztráció: `tools/registry.py`-ben.
- (Opcionális) Skill: `skills/workflow/delegate-cc/SKILL.md`, ami
  bemutatja mikor használjuk.

**Előny:** Hermes "specialista agent-ekhez" tud delegálni anélkül, hogy
azokat újra kellene implementálni. Pl. egy `ecc:cpp-reviewer` agent
egész más szakértelmet hoz mint Hermes alapból.

**Hátrány:**
- Két szintű agent loop (Hermes → CC agent → Claude API) — drágább és
  lassabb mint egy in-process tool hívás.
- A CC agent saját kontextusban dolgozik (nem látja a Hermes session
  állapotát). Át kell adni neki minden szükséges kontextust a prompt-ban.
- Process izoláció: ha a CC agent crashel, Hermes-nek normális process
  exit-et kell kezelnie.

**Becsült munka:** ~250 sor Python + tesztek + dokumentáció. Egy-két
ülés.

---

### Út C — MCP-bridge (legmélyebb)

**Mit csinálnál:** Felfedezi Claude Code MCP konfigurációit
(`~/.claude/settings.json`, `<projekt>/.mcp.json`) és átemeli őket
Hermes saját MCP konfigurációjába. Mivel Hermes-ben már létezik MCP
tool (`tools/mcp_tool.py`), pusztán a server URL-eket / parancsokat
kell átemelni.

**Hol kell változtatás:**
- Új fájl: `hermes_cli/cc_mcp_import.py` — felfedez + konfigurál.
- (Opcionális) CLI parancs: `hermes mcp import-claude-code`.

**Előny:** A felhasználó **összes** MCP-server tool-ja (context7,
exa, firecrawl, playwright, stb.) azonnal elérhető Hermes-ben.
Egyszer kell átemelni, utána mindenhol megy.

**Hátrány:**
- Egyes MCP szerverek OAuth-ot vagy egyéb hitelesítést használnak,
  amit Claude Code kezel — Hermes-nek külön kellene tárolni / kérni.
- Process duplikáció: ha Claude Code is fut és Hermes is, **kétszer**
  spawn-elik ugyanazt az MCP servert. Ez OK-é (legtöbb MCP server
  per-client stateless), de érdemes ellenőrizni.

**Becsült munka:** ~200 sor Python + 1 új CLI parancs. Egy ülés.

---

## Mit javaslok először

**Útvonal: A (skill-adapter) → C (MCP-bridge) → B (agent-átadás).**

Ok:
- **A** triviálisan kis munka és **azonnal** értéket ad — a felhasználó
  Claude Code skill-jei (qDo, qMin, és az ECC suite ~200 skill-je)
  egyetlen lépésben elérhetővé válnak Hermes-ből is.
- **C** ezután érdekes, mert Hermes is profitál a Claude Code-ban már
  beüzemelt MCP infrastruktúrából — nem kell külön konfigurálni
  ugyanazokat a tool-okat.
- **B** legutoljára, mert a két-szintű agent loop a legdrágább és a
  legritkábban szükséges. Csak nagyon speciális esetekben hasznos
  (pl. ha egy CC agent egyedi szakértelmet hoz, ami Hermes-nek nincs).

---

## Nyitott kérdések a tényleges implementáció előtt

1. **Skill conflict resolution.** Ha egy CC skill és egy Hermes skill
   azonos `name`-mel rendelkezik, melyik nyer? Javaslat: Hermes natív
   skill nyer (mint a provider plugin override-eknél), és figyelmeztetést
   logolunk.
2. **Skill kiválasztó UX.** A `hermes skills list` parancsban
   külön kategória legyen `claude-code` néven, vagy mixelődjenek? Inkább
   külön, hogy egyértelmű legyen a forrás.
3. **MCP secret kezelés.** A Claude Code MCP szerverek néha
   `${env:VAR}` interpolációt használnak. Hermes-nek ezt át kell vennie
   vagy explicit `.env` mapping-et kell írni.
4. **Verziókövetés.** A Claude Code skill-ek nincsenek verziózva
   (frontmatterben nincs `version` mező). Hermes nálunk megköveteli a
   `version`-t — vagy elfogadunk default-ot (`0.0.0-unversioned`) az
   import-nál, vagy nem.

Ezeket akkor érdemes megválaszolni, amikor az **A** út implementációját
elkezdjük.

---

## Nem rész e a designnak

- **Hermes skill-ek Claude Code-ban való használata** (ellentétes irány).
  Az Claude Code oldalon önálló munkát igényelne; nem tartozik ide.
- **Claude Code prompts mező** (a slash command `description:`-en
  felüli per-command prompt-fájlok). Ezek inkább interaktív UX-hez
  vannak — Hermes-ben nem nyílt kérdés, hogy ezeket átemeljük-e.
