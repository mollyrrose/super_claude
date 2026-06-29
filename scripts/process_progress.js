#!/usr/bin/env node
/**
 * process_progress.js — writer for the statusline process-progress bars.
 *
 * A long-running process (a /qGoal, /tw, a workflow, any multi-minute job)
 * calls this to publish "I'm ~N% done" so the statusline can render a thin
 * bar below the quota bars (see statusline_with_weekly.js: readProcessProgress
 * / buildProcessBars).
 *
 * State lives in ~/.claude/.process_progress/<session>.json as a JSON array of
 * entries: {id,label,pct,started_at,eta_seconds,updated_at,done}. The file is
 * keyed by session so concurrent windows don't show each other's processes;
 * with no session it falls back to _fallback.json (single-window convenience).
 *
 * Usage:
 *   node process_progress.js --id build --label "qGoal" --pct 42
 *   node process_progress.js --id build --label "qGoal" --eta 600   # time-based
 *   node process_progress.js --id build --done                       # remove one
 *   node process_progress.js --clear-all                             # remove all
 *   # session: --session <sid>, else $CLAUDE_SESSION_ID, else _fallback file
 *
 * Exits 0 on success, 1 on bad input. Never throws on a missing/corrupt state
 * file — it is rebuilt. Kill switch: delete the file or run --clear-all; the
 * statusline simply renders nothing when there are no active entries.
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

function parseArgs(argv) {
  const a = {};
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (!t.startsWith('--')) continue;
    const key = t.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith('--')) {
      a[key] = true; // flag
    } else {
      a[key] = next;
      i++;
    }
  }
  return a;
}

function processDir() {
  const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
  return path.join(claudeDir, '.process_progress');
}

function safeSession(sid) {
  return String(sid || '').replace(/[^A-Za-z0-9_-]/g, '');
}

function stateFile(sid) {
  const safe = safeSession(sid);
  // nosemgrep: path-join-resolve-traversal -- `safe` is sanitized by safeSession() to [A-Za-z0-9_-]; no traversal possible
  return path.join(processDir(), `${safe || '_fallback'}.json`);
}

function readState(file) {
  try {
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (Array.isArray(raw)) return raw;
    if (raw && Array.isArray(raw.processes)) return raw.processes;
  } catch {}
  return [];
}

function writeState(file, list) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(list));
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const sid = args.session || process.env.CLAUDE_SESSION_ID || '';
  const file = stateFile(sid);
  const nowIso = new Date().toISOString();

  if (args['clear-all']) {
    try { if (fs.existsSync(file)) fs.unlinkSync(file); } catch {}
    process.stdout.write('cleared-all\n');
    return 0;
  }

  const id = args.id ? String(args.id) : '';
  if (!id) {
    process.stderr.write('process_progress: --id <name> is required (or --clear-all)\n');
    return 1;
  }

  let list = readState(file);
  const idx = list.findIndex(e => e && e.id === id);

  if (args.done || args.clear) {
    if (idx >= 0) {
      list.splice(idx, 1);
      writeState(file, list);
    }
    process.stdout.write(`done ${id}\n`);
    return 0;
  }

  const existing = idx >= 0 ? list[idx] : null;
  const entry = {
    id,
    label: args.label !== undefined ? String(args.label) : (existing && existing.label) || id,
    started_at: (existing && existing.started_at) || nowIso,
    updated_at: nowIso,
    done: false,
  };

  if (args.pct !== undefined && args.pct !== true) {
    const pct = Math.max(0, Math.min(100, Math.round(Number(args.pct))));
    if (Number.isNaN(pct)) {
      process.stderr.write('process_progress: --pct must be a number 0-100\n');
      return 1;
    }
    entry.pct = pct;
  }
  if (args.eta !== undefined && args.eta !== true) {
    const eta = Math.round(Number(args.eta));
    if (Number.isNaN(eta) || eta <= 0) {
      process.stderr.write('process_progress: --eta must be a positive number of seconds\n');
      return 1;
    }
    entry.eta_seconds = eta;
  } else if (existing && typeof existing.eta_seconds === 'number') {
    entry.eta_seconds = existing.eta_seconds;
  }

  if (entry.pct === undefined && entry.eta_seconds === undefined) {
    process.stderr.write('process_progress: provide --pct <0-100> or --eta <seconds>\n');
    return 1;
  }

  if (idx >= 0) list[idx] = entry; else list.push(entry);
  writeState(file, list);
  process.stdout.write(`set ${id} ${entry.pct !== undefined ? entry.pct + '%' : 'eta ' + entry.eta_seconds + 's'}\n`);
  return 0;
}

if (require.main === module) {
  process.exit(main());
}

module.exports = { parseArgs, stateFile, readState, writeState, safeSession };
