#!/usr/bin/env node
/**
 * Smoketest for the statusline process-progress feature:
 *   - process_progress.js (CLI writer)  + statusline_with_weekly.js readers.
 *
 * Uses a throwaway CLAUDE_CONFIG_DIR so it never touches real state. Run:
 *   node scripts/process_progress_smoketest.js
 * Prints "ALL PASS" + exit 0 on success; throws + exit 1 on first failure.
 */

'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const CLI = path.join(__dirname, 'process_progress.js');
const statusline = require('./statusline_with_weekly.js');

// Isolated config dir
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'procprog-'));
process.env.CLAUDE_CONFIG_DIR = tmp;
const SID = 'sess_test_001';

function cli(...a) {
  return execFileSync('node', [CLI, '--session', SID, ...a], {
    env: { ...process.env, CLAUDE_CONFIG_DIR: tmp },
    encoding: 'utf8',
  });
}

let n = 0;
function ok(label) { n++; console.log(`[ok] ${label}`); }

// 1. Empty when nothing written
assert.deepStrictEqual(statusline.readProcessProgress(SID), [], 'empty before any write');
ok('empty before any write');

// 2. Task-based pct round-trips
cli('--id', 'build', '--label', 'qGoal', '--pct', '42');
let entries = statusline.readProcessProgress(SID);
assert.strictEqual(entries.length, 1, 'one entry after set');
assert.strictEqual(entries[0].label, 'qGoal');
assert.strictEqual(entries[0].pct, 42);
ok('task-based pct round-trips');

// 3. Update same id in place (no duplicate)
cli('--id', 'build', '--pct', '77');
entries = statusline.readProcessProgress(SID);
assert.strictEqual(entries.length, 1, 'still one entry after update');
assert.strictEqual(entries[0].pct, 77);
ok('update in place, no duplicate');

// 4. Second concurrent process -> two bars
cli('--id', 'index', '--label', 'reindex', '--pct', '10');
entries = statusline.readProcessProgress(SID);
assert.strictEqual(entries.length, 2, 'two concurrent entries');
const bars = statusline.buildProcessBars(entries);
assert.ok(bars.includes('qGoal') && bars.includes('reindex'), 'bars name both processes');
assert.ok(bars.startsWith('\n'), 'bars render on a new line below');
assert.strictEqual((bars.match(/\n/g) || []).length, 2, 'two processes stack on two lines');
assert.ok(/[━─]/.test(bars) && !bars.includes('█'), 'uses slim line glyphs, not full block');
ok('two concurrent processes render two stacked slim bars');

// 5. pct clamps to 0..100
cli('--id', 'build', '--pct', '999');
assert.strictEqual(statusline.readProcessProgress(SID).find(e => e.label === 'qGoal').pct, 100, 'pct clamps high');
ok('pct clamps to 100');

// 6. Time-based (eta) derives a pct between 0 and 100
cli('--id', 'timed', '--label', 'timed', '--eta', '600');
const timed = statusline.readProcessProgress(SID).find(e => e.label === 'timed');
assert.ok(timed && timed.pct >= 0 && timed.pct <= 100, 'eta-derived pct in range');
ok('time-based eta derives pct');

// 7. --done removes a single entry
cli('--id', 'build', '--done');
assert.ok(!statusline.readProcessProgress(SID).some(e => e.label === 'qGoal'), 'done removes entry');
ok('--done removes one entry');

// 8. Stale entries (older than TTL) are dropped on read
const stateFile = path.join(tmp, '.process_progress', `${SID}.json`);
const list = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
list.push({ id: 'old', label: 'stale', pct: 50, updated_at: '2000-01-01T00:00:00Z', done: false });
fs.writeFileSync(stateFile, JSON.stringify(list));
assert.ok(!statusline.readProcessProgress(SID).some(e => e.label === 'stale'), 'stale entry dropped');
ok('stale entry dropped on read');

// 9. clear-all wipes the file
cli('--clear-all');
assert.deepStrictEqual(statusline.readProcessProgress(SID), [], 'empty after clear-all');
ok('clear-all empties state');

// 10. buildProcessBars on empty -> empty string (no stray newline)
assert.strictEqual(statusline.buildProcessBars([]), '', 'no bars when no entries');
ok('empty entries render nothing');

// cleanup
try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}

console.log(`\nALL PASS (${n} checks)`);
