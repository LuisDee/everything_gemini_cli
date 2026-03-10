#!/usr/bin/env node
/**
 * skill-fireworks.js
 *
 * BeforeTool hook that celebrates skill activation with a fireworks
 * animation rendered directly to /dev/tty. Runs inline (synchronously)
 * since hooks block the Gemini agent loop — the animation plays while
 * Gemini is paused, then the hook returns {"decision":"allow"}.
 *
 * Prerequisite: npm install -g firew0rks
 *
 * Usage as hook: reads BeforeTool JSON from stdin
 * Usage as test: node skill-fireworks.js --test [skill-name]
 * Debug log: /tmp/fireworks-debug.log
 */

'use strict';

const fs = require('fs');
const path = require('path');

const DEBUG_LOG = '/tmp/fireworks-debug.log';

function debug(msg) {
  try {
    fs.appendFileSync(DEBUG_LOG, `[${new Date().toISOString()}] ${msg}\n`);
  } catch {}
}

// ── Frame discovery ─────────────────────────────────────────────

function findFramesDir() {
  const candidates = [
    '/opt/homebrew/lib/node_modules/firew0rks/fireworks',
    '/usr/local/lib/node_modules/firew0rks/fireworks',
    '/usr/lib/node_modules/firew0rks/fireworks',
  ];
  for (const c of candidates) {
    try { if (fs.statSync(c).isDirectory()) return c; } catch {}
  }
  try {
    const { execSync } = require('child_process');
    const root = execSync('npm root -g', { encoding: 'utf8', timeout: 3000 }).trim();
    const dir = path.join(root, 'firew0rks', 'fireworks');
    if (fs.statSync(dir).isDirectory()) return dir;
  } catch {}
  return null;
}

// 10 frames from 150 total, ~100ms each = ~1s animation
const FRAME_INDICES = [0, 15, 30, 45, 60, 75, 90, 110, 130, 145];
const FRAME_DELAY_MS = 100;

// ── Synchronous sleep ───────────────────────────────────────────

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

// ── Animation (writes to /dev/tty, uses alternate screen buffer) ─

function playAnimation(skillName) {
  debug(`animation start: skill=${skillName}`);

  const framesDir = findFramesDir();
  if (!framesDir) {
    debug('no frames dir found');
    return;
  }

  // Preload frames as strings for single-write buffering
  const frames = [];
  for (const idx of FRAME_INDICES) {
    try {
      frames.push(fs.readFileSync(path.join(framesDir, `${idx}.txt`), 'utf8'));
    } catch {}
  }
  if (frames.length === 0) {
    debug('no frames loaded');
    return;
  }
  debug(`loaded ${frames.length} frames`);

  // Open /dev/tty for direct terminal access
  let ttyFd;
  try {
    ttyFd = fs.openSync('/dev/tty', 'w');
  } catch (err) {
    debug(`cannot open /dev/tty: ${err.message}`);
    return;
  }

  // Get terminal dimensions
  let rows = 41, cols = 80;
  try {
    const { execSync } = require('child_process');
    const size = execSync('stty size < /dev/tty 2>/dev/null', {
      encoding: 'utf8', timeout: 1000,
    }).trim().split(' ');
    if (size.length === 2) {
      rows = parseInt(size[0], 10) || 41;
      cols = parseInt(size[1], 10) || 80;
    }
  } catch {}
  debug(`terminal: ${rows}x${cols}`);

  // Pre-build banner strings
  const bannerText = ` SKILL ACTIVATED: ${skillName} `;
  const boxColor = '\x1b[95;1m';
  const textColor = '\x1b[97;1m';
  const reset = '\x1b[0m';
  const bannerTop = boxColor + '\u2554' + '\u2550'.repeat(bannerText.length) + '\u2557' + reset;
  const bannerMid = boxColor + '\u2551' + reset + textColor + bannerText + reset + boxColor + '\u2551' + reset;
  const bannerBot = boxColor + '\u255A' + '\u2550'.repeat(bannerText.length) + '\u255D' + reset;
  const bannerWidth = bannerText.length + 2;
  const bannerStartRow = Math.max(1, Math.floor(rows / 2) - 1);
  const bannerStartCol = Math.max(1, Math.floor((cols - bannerWidth) / 2) + 1);
  const bannerOverlay =
    `\x1b[${bannerStartRow};${bannerStartCol}H${bannerTop}` +
    `\x1b[${bannerStartRow + 1};${bannerStartCol}H${bannerMid}` +
    `\x1b[${bannerStartRow + 2};${bannerStartCol}H${bannerBot}`;

  try {
    // Switch to alternate screen buffer (ink is paused while hook runs)
    fs.writeSync(ttyFd, '\x1b[?1049h\x1b[?25l');  // save + alt buffer + hide cursor

    for (let i = 0; i < frames.length; i++) {
      // Build entire frame as a single string to minimize write calls (reduces tearing)
      let buf = '\x1b[H' + frames[i];  // cursor home + frame content

      // Overlay banner on last ~50% of frames
      if (i >= Math.floor(frames.length * 0.5)) {
        buf += bannerOverlay;
      }

      // Single atomic write — minimizes tearing
      fs.writeSync(ttyFd, buf);
      sleep(FRAME_DELAY_MS);
    }

    // Hold final frame briefly
    sleep(400);
    debug('animation complete');

  } catch (err) {
    debug(`animation error: ${err.message}`);
  } finally {
    // Restore: show cursor, switch back to main screen buffer
    fs.writeSync(ttyFd, '\x1b[?25h\x1b[?1049l');  // show cursor + restore main buffer
    fs.closeSync(ttyFd);
  }
}

// ── Hook entry point ────────────────────────────────────────────

function readStdin() {
  return new Promise(resolve => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', () => resolve(data));
  });
}

async function runHook() {
  const raw = await readStdin();

  let skillName = 'unknown';
  try {
    const input = JSON.parse(raw);
    skillName = input.tool_input?.name || input.tool_input?.skill_name || 'unknown';
  } catch {}

  // Play animation inline — writes to /dev/tty, not stdout
  playAnimation(skillName);

  // Output JSON to stdout (the only thing Gemini CLI reads)
  process.stdout.write(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

// ── Dispatch ────────────────────────────────────────────────────

if (process.argv[2] === '--test') {
  // Direct test mode: node skill-fireworks.js --test [skill-name]
  playAnimation(process.argv[3] || 'test-skill');
} else {
  runHook();
}
