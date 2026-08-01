<#
.SYNOPSIS
  Restore the ~/.claude config on a (possibly new) machine FROM this repo's
  sanitized mirror (home_dotclaude/) + the repo's scripts/ and skills backup.
  Reverse of sync_claude_config.ps1.

.DESCRIPTION
  - settings.json: [USER] -> current profile name; [REDACTED:<NAME>] secret tokens
    are filled from matching environment variables ($env:<NAME>) when present,
    otherwise LEFT as a placeholder with a warning (never invents a key). The
    existing live settings.json is backed up first.
  - CLAUDE.md: copied into ~/.claude/.
  - scripts/*.py,*.js -> ~/.claude/scripts/ (skip with -NoScripts).
  - claude_skills_backup/* -> ~/.claude/skills/ (skip with -NoSkills).

.NOTES
  Repo root and Python path are stored as [REPO] / [PY] tokens in the mirror and
  filled from THIS clone's location and a Python found on PATH (or $env:CLAUDE_PYTHON),
  so no specific drive (e.g. D:) or install path is required. Kill switch: don't run
  it (it only writes under ~/.claude and backs up what it overwrites).
#>
[CmdletBinding()]
param(
  [string]$ClaudeHome = (Join-Path $env:USERPROFILE '.claude'),
  [switch]$NoScripts,
  [switch]$NoSkills
)
$ErrorActionPreference = 'Stop'

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$mirror   = Join-Path $repoRoot 'home_dotclaude'
New-Item -ItemType Directory -Force -Path $ClaudeHome | Out-Null

# --- settings.json: de-tokenize ---
$src = Join-Path $mirror 'settings.json'
if (Test-Path $src) {
  $raw   = Get-Content -LiteralPath $src -Raw
  $uname = Split-Path $env:USERPROFILE -Leaf
  $raw   = $raw.Replace('[USER]', $uname)

  # [REPO] -> this clone's actual root (no hard-coded drive). JSON needs \\ for \.
  $raw = $raw.Replace('[REPO]', $repoRoot.Replace('\', '\\'))

  # [PY] -> a Python interpreter found on THIS machine (env override, then PATH).
  $py = $env:CLAUDE_PYTHON
  if (-not $py) { $py = (Get-Command python  -ErrorAction SilentlyContinue).Source }
  if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
  if (-not $py) { $py = (Get-Command py      -ErrorAction SilentlyContinue).Source }
  if (-not $py) { $py = 'C:\Python313\python.exe'; Write-Warning "no Python on PATH; [PY] defaulted to $py — install Python or set `$env:CLAUDE_PYTHON and re-run." }
  if ($raw -match '\[PY\]') { Write-Host "[ok] [PY] -> $py" }
  $raw = $raw.Replace('[PY]', $py.Replace('\', '\\'))

  $tokens = [regex]::Matches($raw, '\[REDACTED:([A-Za-z0-9_]+)\]') |
            ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
  foreach ($name in $tokens) {
    $val = [Environment]::GetEnvironmentVariable($name)
    if ($val) {
      $raw = $raw.Replace("[REDACTED:$name]", $val)
      Write-Host "[ok] filled $name from environment"
    } else {
      Write-Warning "secret $name not in environment; left as [REDACTED:$name]. Set `$env:$name and re-run, or edit settings.json."
    }
  }

  $dest = Join-Path $ClaudeHome 'settings.json'
  if (Test-Path $dest) {
    $bak = "$dest.bak.$(Get-Date -Format yyyyMMdd-HHmmss)"
    Copy-Item -LiteralPath $dest -Destination $bak -Force
    Write-Host "[ok] backed up existing settings.json -> $bak"
  }
  Write-Utf8NoBom $dest $raw
  Write-Host "[ok] settings.json restored"
} else {
  Write-Warning "mirror settings.json not found at $src"
}

# --- CLAUDE.md ---
$cm = Join-Path $mirror 'CLAUDE.md'
if (Test-Path $cm) {
  Copy-Item -LiteralPath $cm -Destination (Join-Path $ClaudeHome 'CLAUDE.md') -Force
  Write-Host "[ok] CLAUDE.md restored"
}

# --- scripts ---
if (-not $NoScripts) {
  $srcScripts = Join-Path $repoRoot 'scripts'
  if (Test-Path $srcScripts) {
    $sdst = Join-Path $ClaudeHome 'scripts'
    New-Item -ItemType Directory -Force -Path $sdst | Out-Null
    Get-ChildItem -LiteralPath $srcScripts -File |
      Where-Object { $_.Extension -in '.py', '.js' } |
      ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $sdst -Force }
    Write-Host "[ok] scripts (*.py,*.js) copied to $sdst"
  }
}

# --- skills ---
if (-not $NoSkills) {
  $sb = Join-Path $repoRoot 'hermes-agent\claude_skills_backup'
  if (Test-Path $sb) {
    $kdst = Join-Path $ClaudeHome 'skills'
    New-Item -ItemType Directory -Force -Path $kdst | Out-Null
    Copy-Item -Path (Join-Path $sb '*') -Destination $kdst -Recurse -Force
    Write-Host "[ok] skills restored to $kdst"
  } else {
    Write-Host "[i] no claude_skills_backup/ in repo; skipping skills"
  }
}

Write-Host ""
Write-Host "Next steps on a new machine:"
Write-Host "  1. Install Python 3.x (any drive; on PATH, or set `$env:CLAUDE_PYTHON) and Node.js."
Write-Host "     [REPO] and [PY] are filled from THIS clone + the Python found here, so no"
Write-Host "     specific drive (D:) or install location is required."
Write-Host "  2. Install plugins from settings.json enabledPlugins (ecc, ruflo-core) via /plugin."
Write-Host "  3. Set API keys, then re-run so they fill in:"
Write-Host "       setx OPENAI_API_KEY <key>;  setx DEEPSEEK_API_KEY <key>"
