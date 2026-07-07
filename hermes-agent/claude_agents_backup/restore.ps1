# Restore agent definitions from claude_agents_backup/ into ~/.claude/agents/.
#
# Usage:
#   .\restore.ps1             # restore all agents (Force-overwrite)
#   .\restore.ps1 -DryRun     # show what would happen

[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = "Stop"

$src = $PSScriptRoot
$dst = Join-Path $env:USERPROFILE ".claude\agents"

New-Item -ItemType Directory -Force -Path $dst | Out-Null

$files = Get-ChildItem -Path $src -Filter "*.md" | Where-Object { $_.Name -ne "README.md" }

foreach ($f in $files) {
    $target = Join-Path $dst $f.Name
    if ($DryRun) {
        Write-Host "would copy $($f.Name) -> $target"
    } else {
        Copy-Item $f.FullName $target -Force
        Write-Host "restored $($f.Name)"
    }
}
