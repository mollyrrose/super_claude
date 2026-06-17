<#
.SYNOPSIS
  Launch Claude Code against the GLM (z.ai) Anthropic-compatible endpoint.

.DESCRIPTION
  Groundwork launcher. Points Claude Code at z.ai instead of Anthropic for THIS
  session only, so a normally launched `claude` stays on Anthropic Opus. Nothing
  is written to settings.json -- closing this window (or just running `claude`)
  is the kill switch.

  DORMANT until a z.ai API key exists. Set it in your shell first, never in a
  tracked file:
      $env:ZAI_API_KEY = "<your-key>"     # this session only
      setx ZAI_API_KEY "<your-key>"        # persist (new shells)

  Docs: https://docs.z.ai/devpack/quick-start

.NOTES
  Tier mapping resolves the existing subagent model-routing policy onto GLM:
  the opus/sonnet/haiku aliases used when delegating subagents map to GLM models
  via the ANTHROPIC_DEFAULT_*_MODEL env vars below. Today every tier defaults to
  the GLM flagship (GLM-5.2). Once z.ai's cheaper/faster variant id is known,
  point HAIKU + SMALL_FAST at it so light/mechanical work runs on the cheap tier
  -- exactly the "delegate light work to a lower tier" rule, just on GLM. Confirm
  exact model ids against z.ai's model list before relying on them.
#>

param(
    # Flagship / heavy tier (plan, design, audit). Confirm id at z.ai.
    [string]$Flagship = "GLM-5.2",
    # Mid tier (implementation, tests). Set to a cheaper GLM when available.
    [string]$Mid      = "GLM-5.2",
    # Fast / cheap tier (mechanical work + background tasks). Set to GLM Air/Flash
    # variant once its id is confirmed.
    [string]$Fast     = "GLM-5.2"
)

if (-not $env:ZAI_API_KEY) {
    Write-Error "ZAI_API_KEY is not set. Set it first:  `$env:ZAI_API_KEY = '<your-key>'  (see -? help). Aborting so nothing runs un-authenticated."
    exit 1
}

# Endpoint + auth (z.ai Anthropic-compatible API).
$env:ANTHROPIC_BASE_URL   = "https://api.z.ai/api/anthropic"
$env:ANTHROPIC_AUTH_TOKEN = $env:ZAI_API_KEY
$env:API_TIMEOUT_MS       = "3000000"

# Per-tier mapping so opus/sonnet/haiku subagent delegation resolves to GLM.
$env:ANTHROPIC_DEFAULT_OPUS_MODEL   = $Flagship
$env:ANTHROPIC_DEFAULT_SONNET_MODEL = $Mid
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL  = $Fast
$env:ANTHROPIC_SMALL_FAST_MODEL     = $Fast
$env:ANTHROPIC_MODEL                = $Flagship

Write-Host "[claude-glm] endpoint=$($env:ANTHROPIC_BASE_URL)  flagship=$Flagship  mid=$Mid  fast=$Fast"
Write-Host "[claude-glm] kill switch: close this window or run plain 'claude' for Anthropic Opus."

# Hand off remaining args to Claude Code.
& claude @args
