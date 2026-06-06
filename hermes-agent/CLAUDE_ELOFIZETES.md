# Hermes Claude előfizetéssel — gyors útmutató

Ez a fork úgy van beállítva, hogy a **Claude Pro / Max előfizetésedet** használja
inference-re, anélkül, hogy Anthropic API kulcsot vagy Nous Portál fiókot kellene
beszerezned. A `claude` CLI OAuth-tokenjét veszi át — ez Anthropic által
hivatalosan támogatott útvonal harmadik féltől származó eszközök számára.

## Előfeltételek

1. **Claude Code** telepítve, és `claude /login` lefuttatva legalább egyszer:
   ```powershell
   npm install -g @anthropic-ai/claude-code
   claude /login
   ```
   A login után létrejön a `~/.claude/.credentials.json` (Windows-on:
   `C:\Users\<felhasználó>\.claude\.credentials.json`).

2. **Python 3.10+** és `pip` elérhető.

3. **Git** (csak ha a forkot magadnak akarod githubon tárolni).

## Telepítés

```powershell
cd D:\projects\hermes_claude\hermes-agent
pip install -e ".[anthropic]"
```

Az `-e` (editable) install azért fontos, mert a forknak vannak helyi módosításai,
amik így mindig életbe lépnek a fájlokon. Az `[anthropic]` extra a hivatalos
Anthropic Python SDK-t telepíti — ez **kell** a Claude-hoz, mert az `anthropic`
csomag a Hermes upstream `pyproject.toml`-jában opcionális.

> Ha kihagyod az `[anthropic]` extrát, a fork auth-patch még felismeri a
> Claude Code credentialokat (csak stdlib-et használ), de az első tényleges
> hívásnál `ImportError: anthropic` hibát kapsz.

## Setup egy paranccsal

```powershell
python setup_claude_subscription.py
```

Ez ellenőrzi:
- van-e `claude` CLI a PATH-on,
- érvényes-e a Claude Code credentials fájl,
- van-e refresh token (ha lejárt az access token),

majd beállítja:
- `provider=anthropic`,
- `model=claude-opus-4.8` (csak akkor, ha még nincs modell beállítva),
- Hermes a Claude credential store-ot **közvetlenül** olvassa be minden híváskor
  — nincs token másolva `~/.hermes/.env`-be.

## Indítás

```powershell
hermes
```

## Mit csinál ez a fork az upstream Hermes-hez képest

1. **`hermes_cli/auth.py` patch** — ha indításkor nincs API kulcs env változó
   beállítva, de a Claude Code credential store érvényes, **automatikusan**
   `anthropic` providert választ. Az upstream Hermes ilyenkor azzal hal el, hogy
   "No inference provider configured" — ez a fork ezt elkerüli.

2. **`setup_claude_subscription.py`** — egyparancsos beüzemelő script.

3. **Részletes magyar nyelvű dokumentáció** (`CLAUDE_ELOFIZETES.md`, `index.md`,
   `tot.md`).

Maga az OAuth-flow, a token-frissítés és a credential-tárolás az upstream
Hermes-ben **már létezett** — csak az auto-detect indításkor hiányzott.

## Token-frissítés

Semmi tennivalód: ha lejár az access token, és van refresh token (van), Hermes
csendben frissít a következő hívás előtt. Ezt a `resolve_anthropic_token()`
függvény kezeli (`agent/anthropic_adapter.py`).

Ha valami miatt elveszik a refresh token, futtasd újra:
```powershell
claude /login
```

## Hibakeresés

| Tünet | Mit ellenőrizz |
|-------|----------------|
| `No inference provider configured` indításkor | `claude /login` lefutott-e; `~/.claude/.credentials.json` létezik-e |
| 401 az első hívásnál | Lejárt-e a refresh token is. `claude /login` újra. |
| `'claude' CLI not found` | `npm install -g @anthropic-ai/claude-code`, majd új terminál |
| `pip install` lassú | Telepítsd csak az alap függőségeket: `pip install -e ".[dev]"` (extras nélkül) |
| `hermes: command not found` PowerShell-ben | A pip a `<Python>/Scripts/` mappába tette a binárist, de az nincs PATH-on. Vagy add hozzá (pl. `D:\AppData\Python\Python313\Scripts`), vagy hívd teljes útvonallal, vagy futtasd modulként: `python -m hermes_cli` |

## Smoke teszt

A telepítés után ellenőrizhető hogy az auto-detect tényleg él:

```powershell
python tests/manual/test_claude_subscription_smoke.py
```

6 lépésben végigmegy az import → SDK → credentials → auto-detect →
token-resolution láncon. Ha mindegyik OK, élesben is működik.

## Mi NEM működik

- **Bedrock vagy más Claude-providerek** ezzel a flow-val nem mennek — azoknak
  saját auth kell. A fork nem nyúl hozzájuk.
- **Anthropic API-kulcs egyidejűleg** — ha be van állítva `ANTHROPIC_API_KEY` env
  változód, az **felülírja** ezt az auto-detectet (szándékos: explicit kulcs nyer).
