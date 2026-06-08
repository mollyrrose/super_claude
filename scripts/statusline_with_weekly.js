#!/usr/bin/env node
/**
 * Statusline with 3 progress bars (half-width):
 *   model | task | $cost Nt Nf duration | dir <ctx-bar> <5h-bar> <7d-bar>
 *
 * - All three bars use the same gradient (green→yellow→orange→red) keyed off used%.
 * - 5-hour and 7-day bars also get a pace arrow on the right:
 *     ▲ green  → consumption is in the bottom third vs time-proportional (under-use)
 *     ▼ red    → consumption is in the top third (over-use)
 *     (none)  → middle band, on pace
 *
 * Reads stdin JSON Claude Code passes per refresh. Bars are 5 chars wide
 * (~half the standard 10-char ECC bar). Reset countdown appended after
 * each quota bar.
 *
 * Self-contained — does NOT spawn the ECC plugin statusline; replicates
 * the small helpers locally so we control bar width + colors uniformly.
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const MAX_STDIN = 1024 * 1024;
const BAR_WIDTH = 5;
const AUTO_COMPACT_BUFFER_PCT = 16.5;

const RESET = '\x1b[0m';
const DIM = '\x1b[2m';
const BOLD = '\x1b[1m';
const CYAN = '\x1b[36m';
const BLUE = '\x1b[34m';
const ORANGE = '\x1b[38;5;208m';
const DARK_GREEN = '\x1b[38;5;22m';
const DARK_RED = '\x1b[38;5;88m';

function formatDuration(iso) {
  if (!iso) return '';
  const elapsed = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (elapsed < 0) return '';
  if (elapsed < 60) return `${elapsed}s`;
  const mins = Math.floor(elapsed / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return remMins > 0 ? `${hours}h${remMins}m` : `${hours}h`;
}

function formatResetCountdown(epoch) {
  if (!epoch || typeof epoch !== 'number') return '';
  const secs = Math.floor(epoch - Date.now() / 1000);
  if (secs <= 0) return 'now';
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d${h}h r`;
  if (h > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')} r`;
  return `${m}m r`;
}

function elapsedPctFromReset(epoch, windowSeconds) {
  if (!epoch || typeof epoch !== 'number') return null;
  if (!windowSeconds || windowSeconds <= 0) return null;
  const remaining = Math.floor(epoch - Date.now() / 1000);
  if (remaining <= 0) return 100;
  const elapsed = Math.max(0, windowSeconds - remaining);
  return Math.max(0, Math.min(100, Math.round((elapsed / windowSeconds) * 100)));
}

function formatTokenBudget(tokens) {
  if (!tokens || tokens <= 0) return '';
  if (tokens >= 1_000_000) {
    const m = tokens / 1_000_000;
    return Number.isInteger(m) ? `${m}M` : `${m.toFixed(1)}M`;
  }
  if (tokens >= 1000) return `${Math.round(tokens / 1000)}K`;
  return `${tokens}`;
}

const _ONE_MILLION_MARKERS = ['[1m]', '-1m', '_1m', '1m-context', '1m_context'];

function detectContextLimit(model) {
  if (!model) return 200_000;
  const id = String(model.id || model.display_name || '').toLowerCase();
  if (!id) return 200_000;
  for (const marker of _ONE_MILLION_MARKERS) {
    if (id.includes(marker)) return 1_000_000;
  }
  return 200_000;
}

function ctxThresholdColor(used) {
  if (used < 50) return '\x1b[32m';
  if (used < 65) return '\x1b[33m';
  if (used < 80) return ORANGE;
  return '\x1b[5;31m';
}

// Triangle indicator: compares consumption (usedPct) against time progress (elapsedPct).
// Tolerance band = ±elapsedPct/3. Under that band → ▲ green (under-use); over → ▼ red (over-use).
function buildPaceArrow(usedPct, elapsedPct) {
  if (elapsedPct === null || elapsedPct === undefined) return '';
  if (typeof usedPct !== 'number') return '';
  const tolerance = elapsedPct / 3;
  const delta = usedPct - elapsedPct;
  if (delta < -tolerance) return `\x1b[32m▲\x1b[0m`;
  if (delta > +tolerance) return `\x1b[31m▼\x1b[0m`;
  return '';
}

// Shorten "Opus 4.7 (1M context)" → "O4.7", "Sonnet 4.6" → "S4.6", etc.
function shortenModelName(name) {
  if (!name) return name;
  const cleaned = String(name)
    .replace(/\s+context\)/g, ')')
    .replace(/\s+context\s*$/g, '');
  return cleaned
    .replace(/^Opus\s+(\d+(?:\.\d+)+)(?:\s*\([^)]*\))?\s*$/i, 'O$1')
    .replace(/^Sonnet\s+(\d+(?:\.\d+)+)(?:\s*\([^)]*\))?\s*$/i, 'S$1')
    .replace(/^Haiku\s+(\d+(?:\.\d+)+)(?:\s*\([^)]*\))?\s*$/i, 'H$1');
}

function buildBar(usedPct, colorCode, suffix = '') {
  const used = Math.max(0, Math.min(100, Math.round(usedPct)));
  const filled = used === 0 ? 0 : Math.max(1, Math.round((used / 100) * BAR_WIDTH));
  const bar = '█'.repeat(filled) + '░'.repeat(BAR_WIDTH - filled);
  if (suffix) {
    return `${colorCode}${bar}${used}%${RESET}${DIM}${suffix}${RESET}`;
  }
  return `${colorCode}${bar}${used}%${RESET}`;
}

// Per-session baseline storage: subtract the system-overhead (system prompt + skill list)
// that's present at session start / right after /clear, so the bar only shows the user's
// own context consumption. State lives in ~/.claude/.statusline_baselines.json.
function _baselinesPath() {
  const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
  return path.join(claudeDir, '.statusline_baselines.json');
}

function _readBaselines() {
  try {
    const f = _baselinesPath();
    if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, 'utf8')) || {};
  } catch {}
  return {};
}

function _writeBaselines(data) {
  try { fs.writeFileSync(_baselinesPath(), JSON.stringify(data)); } catch {}
}

const _CLEAR_DROP_THRESHOLD = 15;       // %-drop that signals a /clear event → re-baseline
const _BASELINE_TTL_DAYS = 30;

function rebaselineUsed(sessionId, rawUsed) {
  if (!sessionId || typeof rawUsed !== 'number') return rawUsed;
  const safe = String(sessionId).replace(/[^A-Za-z0-9_-]/g, '');
  if (!safe) return rawUsed;

  const data = _readBaselines();
  const entry = data[safe];
  const nowIso = new Date().toISOString();

  let baseline;
  if (!entry) {
    data[safe] = { baseline: rawUsed, maxSeen: rawUsed, ts: nowIso };
    baseline = rawUsed;
  } else if (rawUsed < entry.maxSeen - _CLEAR_DROP_THRESHOLD) {
    // Big drop → likely a /clear, re-baseline to the new low.
    data[safe] = { baseline: rawUsed, maxSeen: rawUsed, ts: nowIso };
    baseline = rawUsed;
  } else {
    data[safe] = {
      baseline: entry.baseline,
      maxSeen: Math.max(entry.maxSeen, rawUsed),
      ts: nowIso,
    };
    baseline = entry.baseline;
  }

  // Lazy cleanup of stale session entries
  const cutoff = Date.now() - _BASELINE_TTL_DAYS * 86400 * 1000;
  for (const k of Object.keys(data)) {
    if (k === safe) continue;
    const t = Date.parse(data[k] && data[k].ts || 0);
    if (!t || t < cutoff) delete data[k];
  }
  _writeBaselines(data);

  // Rescale so 0% = at baseline, 100% = full context. Threshold colors still fire correctly.
  const available = Math.max(1, 100 - baseline);
  return Math.max(0, Math.min(100, Math.round(((rawUsed - baseline) / available) * 100)));
}

function buildContextBar(remainingPct, sessionId) {
  if (remainingPct === null || remainingPct === undefined) return '';
  const usable = Math.max(
    0,
    ((remainingPct - AUTO_COMPACT_BUFFER_PCT) / (100 - AUTO_COMPACT_BUFFER_PCT)) * 100
  );
  const rawUsed = Math.max(0, Math.min(100, Math.round(100 - usable)));
  const used = rebaselineUsed(sessionId, rawUsed);
  return ` ${DIM}2Compact${RESET} ${DIM}S${RESET}` + buildBar(used, ctxThresholdColor(used), 'full');
}

function buildQuotaBar(window, _colorCode, windowSeconds, label) {
  if (!window || typeof window.used_percentage !== 'number') return '';
  const usedPct = Math.max(0, Math.min(100, Math.round(window.used_percentage)));
  const colorCode = ctxThresholdColor(usedPct);
  const bar = buildBar(window.used_percentage, colorCode, 'full');
  const reset = formatResetCountdown(window.resets_at);
  const labelStr = label ? `${DIM}${label}${RESET}` : '';
  const elapsed = elapsedPctFromReset(window.resets_at, windowSeconds);
  const arrow = buildPaceArrow(usedPct, elapsed);
  if (!reset) return `${labelStr}${bar}${arrow}`;
  let suffix = '';
  if (elapsed !== null) {
    if (elapsed === usedPct) {
      suffix = `,${elapsed}%`;
    } else {
      const color = elapsed > usedPct ? DARK_GREEN : DARK_RED;
      suffix = `,${RESET}${color}${elapsed}%${RESET}${DIM}`;
    }
  }
  return `${labelStr}${bar}${DIM}(${reset}${suffix})${RESET}${arrow}`;
}

function readCurrentTask(sessionId) {
  try {
    const safe = String(sessionId || '').replace(/[^A-Za-z0-9_-]/g, '');
    if (!safe) return '';
    const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
    const todosDir = path.join(claudeDir, 'todos');
    if (!fs.existsSync(todosDir)) return '';
    const files = fs
      .readdirSync(todosDir)
      .filter(f => f.startsWith(safe) && f.includes('-agent-') && f.endsWith('.json'))
      .map(f => ({ name: f, mtime: fs.statSync(path.join(todosDir, f)).mtime }))
      .sort((a, b) => b.mtime - a.mtime);
    if (!files.length) return '';
    const todos = JSON.parse(fs.readFileSync(path.join(todosDir, files[0].name), 'utf8'));
    const ip = todos.find(t => t.status === 'in_progress');
    return ip?.activeForm || '';
  } catch {
    return '';
  }
}

function readBridge(sessionId) {
  try {
    const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
    const safe = String(sessionId || '').replace(/[^A-Za-z0-9_-]/g, '');
    if (!safe) return null;
    const bridgePath = path.join(claudeDir, '.ecc-session-bridge', `${safe}.json`);
    if (!fs.existsSync(bridgePath)) return null;
    return JSON.parse(fs.readFileSync(bridgePath, 'utf8'));
  } catch {
    return null;
  }
}

function main() {
  let input = '';
  const t = setTimeout(() => process.exit(0), 3000);
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', c => {
    if (input.length < MAX_STDIN) input += c.substring(0, MAX_STDIN - input.length);
  });
  process.stdin.on('end', () => {
    clearTimeout(t);
    let data;
    try { data = JSON.parse(input); } catch { return; }

    const rawModel = data.model?.display_name || 'Claude';
    const model = shortenModelName(rawModel);
    const dir = data.workspace?.current_dir || process.cwd();
    const sessionId = data.session_id || '';
    const remaining = data.context_window?.remaining_percentage;
    const rl = data.rate_limits || {};

    const task = sessionId ? readCurrentTask(sessionId) : '';
    const bridge = sessionId ? readBridge(sessionId) : null;

    // Metrics segment (cost / tools / files / duration) from bridge if present.
    let metricsStr = '';
    if (bridge) {
      const parts = [];
      if (typeof bridge.total_cost_usd === 'number' && bridge.total_cost_usd > 0) {
        parts.push(`$${bridge.total_cost_usd.toFixed(2)}`);
      }
      if (typeof bridge.tool_count === 'number' && bridge.tool_count > 0) {
        parts.push(`${bridge.tool_count}t`);
      }
      if (typeof bridge.files_modified_count === 'number' && bridge.files_modified_count > 0) {
        parts.push(`${bridge.files_modified_count}f`);
      }
      const dur = formatDuration(bridge.first_timestamp);
      if (dur) parts.push(dur);
      if (parts.length) metricsStr = `${CYAN}${parts.join(' ')}${RESET}`;
    }

    // Bars
    const ctxBar = buildContextBar(remaining, sessionId);
    const fhBar = buildQuotaBar(rl.five_hour, BLUE, 5 * 3600, '5h');
    const sdBar = buildQuotaBar(rl.seven_day, ORANGE, 7 * 86400, '1w');

    // Compose segments
    const segments = [`${DIM}${model}${RESET}`];
    if (task) segments.push(`${BOLD}${task}${RESET}`);
    if (metricsStr) segments.push(metricsStr);

    const sep = ` ${DIM}│${RESET} `;
    let out = segments.join(sep) + ctxBar;
    if (fhBar) out += `${DIM}│${RESET} ${fhBar}`;
    if (sdBar) out += `${DIM}│${RESET} ${sdBar}`;

    process.stdout.write(out);
  });
}

module.exports = {
  formatDuration,
  formatResetCountdown,
  elapsedPctFromReset,
  formatTokenBudget,
  detectContextLimit,
  ctxThresholdColor,
  buildBar,
  buildContextBar,
  buildQuotaBar,
  buildPaceArrow,
  shortenModelName,
  rebaselineUsed,
};

if (require.main === module) main();
