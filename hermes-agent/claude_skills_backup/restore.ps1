# Restore every skill from claude_skills_backup/ into ~/.claude/skills/.
#
# Usage:
#   .\restore.ps1                # restore all skills (Force-overwrite)
#   .\restore.ps1 -DryRun        # show what would happen
#   .\restore.ps1 -Only qRem,rev # restore a specific subset
#
# Safe to re-run. Each skill folder is overwritten as a whole; the
# script does not merge SKILL.md contents.

[CmdletBinding()]
param(
    [string[]]$Only = @(),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$src = Join-Path $PSScriptRoot ""   # this directory
$dst = Join-Path $env:USERPROFILE ".claude\skills"

if (-not (Test-Path $src)) {
    Write-Error "Source missing: $src"
    exit 1
}

New-Item -ItemType Directory -Force -Path $dst | Out-Null

$candidates = Get-ChildItem -Path $src -Directory | Where-Object {
    $_.Name -notmatch '^(\.|__pycache__)' -and $_.Name -ne 'tests'
}

if ($Only.Count -gt 0) {
    $candidates = $candidates | Where-Object { $Only -contains $_.Name }
    if ($candidates.Count -eq 0) {
        Write-Warning "No matches for -Only $($Only -join ', ')"
        exit 0
    }
}

$restored = 0
foreach ($skill in $candidates) {
    $target = Join-Path $dst $skill.Name
    if ($DryRun) {
        Write-Host "  would restore: $($skill.Name) -> $target"
    } else {
        if (Test-Path $target) {
            Remove-Item -Recurse -Force $target
        }
        Copy-Item -Path $skill.FullName -Destination $target -Recurse
        Write-Host "  ok: $($skill.Name)"
    }
    $restored++
}

if ($DryRun) {
    Write-Host ""
    Write-Host "Dry run — would restore $restored skill(s)."
} else {
    Write-Host ""
    Write-Host "Restored $restored skill(s) into $dst."
    Write-Host "Restart Claude Code to pick up the new skill list."
}
