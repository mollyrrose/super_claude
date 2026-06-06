# Hermes → Claude Code integráció

Ez a mappa **nem érinti** sem a Hermes upstream-et sem a Claude Code-ot.
Egy oldalsó híd: Hermes hasznos részeit átviszi Claude Code-ba úgy, hogy
mindkettő frissíthető marad (Claude Code `npm update`-tel, Hermes git
pull-lal).

## Mi kerül telepítésre

1. **Skill bundle** — 83 Hermes skill átalakítva Claude Code formátumra,
   `~/.claude/skills/hermes-<név>/` alá másolva. Slash-parancsként
   használhatók.
2. **/hermes-curate** + **/hermes-learn** slash command-ok — Claude saját
   self-learning eszközei a `~/.claude/skills/hermes-{curate,learn}/`
   alatt.
3. **Két hook a `~/.claude/settings.json`-ban**, mindkettő LLM-mentes:
   - `Stop` — minden session végén (a) queue-bejegyzést ír
     (`~/.claude/.hermes_curator_queue.json`), (b) szkenneli a transcript-et
     Skill-tool-hívásokra és frissíti a használati számlálókat
     (`~/.claude/.hermes_skill_state.json`).
   - `UserPromptSubmit` — minden prompt elejére (a) **utasítást** told
     Claude-nak ha a queue threshold-ja megvan (auto-curate), (b)
     lefuttatja a deterministic skill-lifecycle passt 7 naponta
     egyszer (auto-archive 90 nap után).

## Hogyan működik a self-learning Claude-on keresztül

Régi terv volt egy Stop hookból külön Anthropic API hívást indítani — ez
zárult, mert Anthropic mostantól a subscription kvótát csak a Claude
Code-nak adja, a third-party app-oknak nem.

Az új architektúra: **Claude maga csinálja a curate-et, a saját
session-jében**. A folyamat:

1. Te (vagy Claude) befejezel egy session-t. A Stop hook **csak
   regisztrálja** a session-t egy queue fájlba (instant, ingyen, offline).
2. Következő (vagy bármely későbbi) session első prompt-jánál a
   UserPromptSubmit hook ránéz a queue-ra. Ha ≥3 session vár, vagy
   ≥7 nap telt el az utolsó drain óta, **utasítást ad Claude-nak**
   (additionalContext-en keresztül): a user prompt előtt csendben
   drain-eld a queue-t, majd válaszolj.
3. Claude **automatikusan végrehajtja** a curate-et a user prompt
   feldolgozása előtt: olvassa a queue-t, minden transcript fájlt
   átnéz, ha talál **magas-bizonyosságú, ismétlődő** pattern-t,
   közvetlenül `~/.claude/skills/hermes-auto-<slug>/` alá ír SKILL.md-t.
   Nincs `skills-pending/` review-mappa — a user nem akar manuális
   review-t.
4. Claude prepend-el egy egy-soros státusz-sort a válasza tetején:
   `· curator: drained N session(s), wrote M auto-skill(s)` — opcionálisan
   egy 2. sorral listázza az új skill slug-okat. Utána normál módon
   válaszol a te tényleges promptodra.
5. Mindez a **saját session kontextusából** megy — a Pro/Max
   subscription-öd fedi a költséget, ugyanúgy mintha bármi mást
   csinálna a session-ben.
6. Te **nem csinálsz semmit**. Az új `hermes-auto-*` skill-ek azonnal
   használhatóak.

## Skill usage tracking és lifecycle (Hermes-stílus, Claude-natívan)

A Stop hook minden session után parseolja a transcript-et és minden
`Skill` tool-hívásra növel egy számlálót. Idővel Claude megtudja:

- melyik skill-eket használod gyakran (`total_uses`),
- mikor használta utoljára egy adott skill-t (`last_used`).

Állapotfájl: `~/.claude/.hermes_skill_state.json`.

### A napok **aktív napokban** mérődnek

Az "X napja nincs használva" nem a naptári napokra utal, hanem az
**active day**-ekre: olyan UTC napokra, amikor legalább egyszer
lefutott a Stop hook (vagyis programoztál Claude Code-ban).

Praktikusan: ha 3 hónapig nem nyúlsz a géphez, **0 active day** telik
el → semmi sem fog stale-ré válni vagy archiválódni. Amint újra
elkezdesz dolgozni, a clock onnan folytatja ahol abbahagyta.

Tárolás: az `~/.claude/.hermes_skill_state.json` egy `active_days`
listát tart fenn (sorted UTC dátum stringek), amibe a Stop hook
minden session vége után beilleszti a mai napot (ha még nincs benne).
Cap ~2000 entrynél (~5,5 év), efölött a legrégibb 25%-ot vágja.

### A lifecycle pass

A UserPromptSubmit hook 7 active naponta egyszer
(`HERMES_SKILL_MAINTENANCE_INTERVAL_DAYS`) deterministic lifecycle
passt futtat:

| Életciklus | Mikor | Mit csinál |
|------------|-------|------------|
| **stale** | 30 **active** napja nincs használat | `stale_since` jelölés állapotfájlban (skill érintetlen marad) |
| **archive** | 90 **active** napja nincs használat | A skill mappáját átköltözteti `~/.claude/skills-archive/<név>/` alá — **nem törlés**, Claude Code nem látja többé, de visszamozgatható |
| **pinned bypass** | `pinned: true` a SKILL.md frontmatterben | Soha nem archive-olódik, stale-jelölés is törlődik |
| **védett** | `hermes-curate`, `hermes-learn`, `hermes-maintain` nevek | Soha nem érintve (a self-learning infrastruktúra megmarad) |

Env változókkal állítható (mindegyik **active** napokban):
- `HERMES_SKILL_STALE_AFTER_DAYS` (alap: 30)
- `HERMES_SKILL_ARCHIVE_AFTER_DAYS` (alap: 90)
- `HERMES_SKILL_MAINTENANCE_INTERVAL_DAYS` (alap: 7)

Például egy intenzív heti 5 napos rutinban az alapértelmezett 30
active nap kb. 6 naptári hét — egy szabadság vagy más projekt miatti
szünet ezt nem rontja el.

### Skill visszahozása az archive-ból

```powershell
Move-Item ~/.claude/skills-archive/<név> ~/.claude/skills/<név>
```

A használati számláló érintetlen (a `last_used` ott marad, csak az
`archived_at` megy törlésre amikor a hook újra látja a használatot).

### Skill kipinelése (auto-archive megelőzés)

A skill SKILL.md frontmatterébe egy sor:
```yaml
pinned: true
```
Ettől soha nem archiválódik, akármennyit nem használod.

## In-session skill capture: `/hermes-learn`

A curator a session VÉGE után fut, néha napokkal később. A `/hermes-learn`
viszont **menet közben** fogja a friss kontextust:

- Beírod a chat-be: `/hermes-learn` (vagy "save ezt mint skill")
- Claude azonnal megnézi az utolsó 20–60 turn-t, eldönti hogy
  van-e benne újra-használható shape
- Ha igen: SKILL.md-t ír `~/.claude/skills/hermes-auto-<slug>/` alá
- Ha nem (még folyamatban van, vagy túl projekt-specifikus): mondja és
  továbblép

A friss kontextus miatt általában **pontosabb skill-t ad** mint a
queue-based curator.

## Biztonsági korlátok az auto-promotálás körül

Mivel nincs human-in-the-loop:

- A skill **csak akkor írhat**, ha a pattern **legalább 2 sessionben
  felbukkant** VAGY egyetlen sessionben, de nyilvánvalóan generikus.
- Mindig `hermes-auto-` prefixet kap → könnyen szűrhető és tömegesen
  törölhető (`Remove-Item -Recurse ~/.claude/skills/hermes-auto-*`).
- Soha nem ír felül létező `hermes-auto-*` skillt.
- Soha nem ír a `hermes-*` (auto nélküli) prefix alá — az a konverter
  területe.
- A SKILL.md instrukciói szándékosan **konzervatívak**: a "0 új skill
  az 5 session-ből" elfogadott eredmény. Inkább kevés jó skill, mint
  sok rossz.

Ha mégis egy auto-skill rossznak bizonyul:
```powershell
Remove-Item -Recurse ~/.claude/skills/hermes-auto-<slug>
```

**Nincs `/hermes-curate` parancs kézzel.** Ha mégis akarsz manuálisan
futtatni, lehet — a slash command megmaradt — de a default flow
teljesen automatikus.

**Anthropic API kulcs nem kell. Gemini sem kell. Ollama sem kell.
Semmilyen külön konfig nem kell.**

## Telepítés

```powershell
python -m claude_code_integration.install_into_claude_code --dry-run
```

A `--dry-run` előbb megmutatja mit tenne. Ha rendben:

```powershell
python -m claude_code_integration.install_into_claude_code
```

Három lépést csinál (mindegyik kihagyható flaggel):
- `[1]` Konvertálja a Hermes skill-eket → `~/.claude/skills/hermes-*/`
- `[2]` Telepíti a `/hermes-curate` slash commandot → `~/.claude/skills/hermes-curate/`
- `[3]` Beír 2 hookot a `~/.claude/settings.json`-ba (Stop + UserPromptSubmit)

A meglévő `settings.json`-t **biztonsági másolatba teszi** `.json.bak`
néven, mielőtt írna. Idempotens: ha már regisztrálva vannak a hookok,
nem duplázza őket.

**Restart kell** minden nyitott Claude Code session-höz, hogy a hookok
életbe lépjenek — egyszer.

### Telepítő flag-ek

| Flag | Mit csinál |
|------|------------|
| `--dry-run` | Csak kiírja mit tenne, nem ír |
| `--skip-skills` | A Hermes skill bundle-t kihagyja |
| `--skip-curate-skill` | A `/hermes-curate` skillt kihagyja |
| `--skip-hooks` | A két hookot nem regisztrálja |
| `--overwrite-skills` | Lecseréli a meglévő `hermes-*` skill-eket |

## Konfiguráció (opcionális env változókkal)

| Env var | Default | Mit állít |
|---------|---------|-----------|
| `HERMES_CURATOR_PENDING_FOR_REMINDER` | `3` | Mennyi queue-bejegyzéstől szóljon |
| `HERMES_CURATOR_DAYS_FOR_REMINDER` | `7` | Hány napig csendben mielőtt szólna |
| `HERMES_CURATOR_SILENT` | unset | `1`-re állítva: soha nem szól |

PowerShell példa:
```powershell
[Environment]::SetEnvironmentVariable("HERMES_CURATOR_DAYS_FOR_REMINDER", "14", "User")
```

## Smart-router (prompt-shape → skill suggestion)

A `UserPromptSubmit` hookba egy második script is beregisztrálva van a
curator mellett: `smart_router_prompt_hook.py`. Minden user prompt
elejére ránéz a prompt szövegére, és **ajánl egy skillt** ha azonosít
egy known-good shape-et. Pure-Python regex classifier, **nincs LLM
hívás** — instant, ingyen, offline.

A logikai szabályok külön fájlban (`smart_router_rules.py`):

| Prompt shape | Trigger példák | Ajánlott skill |
|---|---|---|
| Bug / regression report | `Traceback`, `error:`, `nem működik`, `used to work`, `crashed` | `/hunt` |
| Release / PR / pre-merge | `ready to release`, `ready to merge`, `PR ready`, `before commit` | `/check` |
| Audit / sprint close | `review my code`, `audit`, `sprint close`, `nézd át` | `/rev` |
| Research / deep-dive | `deep-dive`, `help me understand`, `mélyebben` | `/learn` |
| Design / planning | `how should I`, `should we`, `compare X vs Y`, `hogyan érdemes` | `/think` |
| Multi-file refactor / feature | `implement … feature`, `refactor the…`, 3+ file path mentioned | `/think` |

A router **konzervatív**:
- < 4 szó → no suggestion
- explicit slash command (`/something`) → no suggestion (a user már döntött)
- nem egyértelmű match → no suggestion
- magyar **és** angol kulcsszavak támogatva

`/qMin` szándékosan **nincs** a router szabályaiban — már automatikusan
fut session végén külön mechanizmuson keresztül; nem kell duplikáltan
ajánlani.

A suggestion `additionalContext`-en keresztül érkezik, max 400 karakter,
és **csak hint** — a model és a user szabadon felülbírálhatja. A
curator hook ugyanezen az event-en fut párhuzamosan; outputjaik
concat-elődnek.

### Mit látsz használat közben (smart-router)

Egy non-trivial prompt-nál (pl. "how should I refactor this?") a model
látja a kontextusban:
```
[smart-router hint] This prompt looks like a design / planning / value-
judgment question — /think drafts a validated plan first. Consider invoking
`/think` unless the user explicitly chose a different approach or the
request is smaller than the hint suggests. This is a suggestion, not
enforcement — the user can override.
```

Trivi prompt (`ls`, `git status`, "thanks") esetén a router semmit nem
injectál — no-op.

### Tesztek

A classifier 32 unit tesztje a `test_smart_router_rules.py`-ban. Futtatás
a `claude_code_integration/` mappából:

```powershell
python -m unittest test_smart_router_rules -v
```

## Mit látsz használat közben

### Session vége

A Claude Code log-ban (vagy ha látod a hook outputot):
```
[hermes-curator/stop] enqueued — queue_size=2 user_turns=18
```
vagy:
```
[hermes-curator/stop] skipped — only 3 user turns (<4)
```

### Új session első promptja (auto-curate, auto-promote)

Ha a queue threshold megvan, Claude **a kontextusban** kap egy
utasítást: "a válasz előtt drain-eld a queue-t, és az új skill-eket
közvetlenül `~/.claude/skills/hermes-auto-*/` alá írd". A user (te) ezt
nem feltétlenül látja közvetlenül — viszont **látja a végeredményt**:
a Claude válasza tetején egy egy-soros státusz-sor jelenik meg, opcionálisan
egy második sorral a slug-listával:
```
· curator: drained 5 session(s), wrote 2 auto-skill(s)
  → hermes-auto-pdf-pivot-table, hermes-auto-tdd-migration-script

[itt jön Claude válasza a te promptodra]
```

Ha a curate nem sikerült (pl. queue fájl olvashatatlan), Claude
egy soron megemlíti és normál módon folytatja a választ.

### Skill candidate promoválása

```powershell
ls ~/.claude/skills-pending/
# Ha tetszik egy:
mv ~/.claude/skills-pending/<dátum>-<név> ~/.claude/skills/<végleges-név>
```

Ha nem tetszik, törölheted nyugodtan.

## Mi NEM tartozik ide

- **MCP-szerverek és Hermes tool-jainak kitevése** — kihagytuk a tervből
  (Claude Code beépített tool-jai elég jók).
- **Curator automatikus skill-promotálás** — szándékos: a `pending`
  mappa a human-in-the-loop biztosíték. Nem akarunk olyat hogy egy
  félresikerült session SKILL-t hagy a default helyen, ami minden
  jövőbeli session-be belekever.
- **Külső LLM API hívás a hookból** — törölve. A self-learning Claude
  saját session kvótájából megy.

## Hibakeresés

| Tünet | Mit ellenőrizz |
|-------|----------------|
| Stop hook nem fut | Restart-oltad-e Claude Code-ot az install után? `cat ~/.claude/settings.json` mutatja-e a `hooks.Stop` entry-t |
| Reminder soha nem jelenik meg | Queue üres-e? `cat ~/.claude/.hermes_curator_queue.json` |
| `/hermes-curate` parancsot nem ismeri | `ls ~/.claude/skills/hermes-curate/SKILL.md` létezik-e |
| Túl gyakran szól | Növeld `HERMES_CURATOR_PENDING_FOR_REMINDER`-t vagy `HERMES_CURATOR_DAYS_FOR_REMINDER`-t |
| Egyáltalán ne szóljon | `HERMES_CURATOR_SILENT=1` |
| Stop hook hibák | Claude Code log-ban `[hermes-curator/stop]` sorok |
| Minden prompt-nál `· curator: drain failed (claude_code_integration not importable)` | A drain step a `mark_drained_cli.py` wrapper-en megy keresztül (`sys.path.insert`-tel); ha a direktíva mégis közvetlen `python -c "from claude_code_integration..."`-tal próbál, a sub-mappa nincs `sys.path`-on → `ModuleNotFoundError`. Ellenőrizd: `curator_core.py:should_remind()` szövegében szerepel-e a `mark_drained_cli.py` parancs |

## Eltávolítás

```powershell
# Skill bundle törlése
Remove-Item -Recurse ~/.claude/skills/hermes-*

# /hermes-curate eltávolítás
Remove-Item -Recurse ~/.claude/skills/hermes-curate

# Hook deregisztráció — vagy edit-eld manuálisan a settings.json-t,
# vagy állítsd vissza a backupot:
Copy-Item ~/.claude/settings.json.bak ~/.claude/settings.json

# Curator állapot tisztítása
Remove-Item ~/.claude/.hermes_curator_queue.json
Remove-Item ~/.claude/.hermes_curator_state.json
Remove-Item -Recurse ~/.claude/skills-pending
```
