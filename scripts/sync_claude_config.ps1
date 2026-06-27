<#
.SYNOPSIS
  Sync the LIVE ~/.claude config INTO this repo's sanitized mirror (home_dotclaude/).
  Run this after you change ~/.claude/settings.json or ~/.claude/CLAUDE.md so the
  repo stays the source of truth and a new machine can be rebuilt from git.

.DESCRIPTION
  - settings.json: secret env values (names matching *_API_KEY / *_KEY / *TOKEN /
    *SECRET / *PASSWORD) are redacted to [REDACTED:<NAME>] tokens; the live profile
    user name is replaced with [USER]. Raw text is preserved otherwise (no JSON
    reformat), so diffs stay minimal.
  - CLAUDE.md: copied verbatim (it contains no secrets).
  Reverse of restore_claude_config.ps1.

.NOTES
  Only writes inside the repo (home_dotclaude/). Kill switch: don't run it.
  It ABORTS if a real-looking secret survives redaction, so it can't leak a key.
#>
[CmdletBinding()]
param(
  [string]$ClaudeHome = (Join-Path $env:USERPROFILE '.claude')
)
$ErrorActionPreference = 'Stop'

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$mirror   = Join-Path $repoRoot 'home_dotclaude'
New-Item -ItemType Directory -Force -Path $mirror | Out-Null

$uname = Split-Path $env:USERPROFILE -Leaf   # profile folder name, as used in paths

# --- settings.json: redact secrets + tokenize user name ---
$liveSettings = Join-Path $ClaudeHome 'settings.json'
if (Test-Path $liveSettings) {
  $raw  = Get-Content -LiteralPath $liveSettings -Raw
  $json = $raw | ConvertFrom-Json
  $secretRe = '(_API_KEY$|_KEY$|TOKEN|SECRET|PASSWORD)'
  if ($json.PSObject.Properties.Name -contains 'env' -and $json.env) {
    foreach ($p in $json.env.PSObject.Properties) {
      $val = [string]$p.Value
      if ($p.Name -match $secretRe -and $val -and $val -notmatch '^\[REDACTED') {
        $raw = $raw.Replace($val, "[REDACTED:$($p.Name)]")
      }
    }
  }
  if ($uname) { $raw = $raw -replace [regex]::Escape($uname), '[USER]' }

  # Safety gate: never leave a real-looking key in the mirror.
  if ($raw -match 'sk-[A-Za-z0-9_\-]{16,}') {
    throw "ABORT: a real-looking secret survived redaction; refusing to write the mirror."
  }
  Write-Utf8NoBom (Join-Path $mirror 'settings.json') $raw
  Write-Host "[ok] settings.json synced (secrets -> [REDACTED:*], user -> [USER])"
} else {
  Write-Warning "live settings.json not found at $liveSettings"
}

# --- CLAUDE.md: verbatim ---
$liveClaude = Join-Path $ClaudeHome 'CLAUDE.md'
if (Test-Path $liveClaude) {
  Copy-Item -LiteralPath $liveClaude -Destination (Join-Path $mirror 'CLAUDE.md') -Force
  Write-Host "[ok] CLAUDE.md synced"
} else {
  Write-Warning "live CLAUDE.md not found at $liveClaude"
}

Write-Host "[ok] sync complete -> $mirror"
Write-Host "Review 'git diff home_dotclaude/' then commit."
