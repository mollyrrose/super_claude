# Refresh the snapshot from the current ~/.claude/skills/ state.
#
# Usage:
#   .\refresh.ps1            # rewrite the snapshot; stage; commit interactively
#   .\refresh.ps1 -NoCommit  # just rewrite + stage, do not commit
#   .\refresh.ps1 -DryRun    # show what would happen

[CmdletBinding()]
param(
    [switch]$NoCommit,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$dst = $PSScriptRoot
$src = Join-Path $env:USERPROFILE ".claude\skills"
$repo = Split-Path -Parent $dst

if (-not (Test-Path $src)) {
    Write-Error "Source not found: $src"
    exit 1
}

Write-Host "Source : $src"
Write-Host "Target : $dst"

if ($DryRun) {
    $srcCount = (Get-ChildItem -Path $src -Directory).Count
    Write-Host ""
    Write-Host "Dry run -- would replace snapshot with $srcCount skill folder(s)."
    exit 0
}

# Wipe contents of $dst (but keep $dst itself + this script + README + restore.ps1).
$keep = @("README.md", "restore.ps1", "refresh.ps1")
Get-ChildItem -Path $dst -Force | Where-Object {
    $keep -notcontains $_.Name
} | Remove-Item -Recurse -Force

# Copy each skill directory in.
Get-ChildItem -Path $src -Directory | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dst -Recurse
}

# Strip any nested .git directories that came over from skills that
# were git-cloned into ~/.claude/skills/. Without this they would
# show up as untracked-content submodules in the fork's git status.
$nestedGit = Get-ChildItem -Path $dst -Recurse -Force -Directory `
    -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq ".git" }

foreach ($g in $nestedGit) {
    # Pack files in .git/objects/pack/*.idx are read-only on Windows;
    # clear the attribute before delete so Remove-Item does not bail.
    Get-ChildItem -Path $g.FullName -Recurse -Force -File |
        ForEach-Object { $_.IsReadOnly = $false }
    Remove-Item -Path $g.FullName -Recurse -Force
    Write-Host "  stripped nested .git: $($g.FullName)"
}

Write-Host "Snapshot refreshed."

if ($NoCommit) {
    Write-Host 'Staging skipped (-NoCommit). Run ''git add claude_skills_backup'' yourself.'
    exit 0
}

Push-Location $repo
try {
    git add claude_skills_backup
    Write-Host ''
    Write-Host 'Staged. Inspect with: git diff --cached --stat -- claude_skills_backup'
    Write-Host 'Commit suggestion:    git commit -m ''Refresh claude_skills_backup snapshot'''
} finally {
    Pop-Location
}
