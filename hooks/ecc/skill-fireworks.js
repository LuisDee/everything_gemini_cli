#!/usr/bin/env node
/**
 * skill-fireworks.js
 *
 * BeforeTool hook that celebrates skill activation with a fireworks
 * animation rendered to /dev/tty via a detached background process.
 *
 * Uses Gemini CLI's systemMessage for an inline banner (guaranteed visible),
 * then spawns a brief fireworks animation that writes directly to /dev/tty
 * without switching screen buffers (compatible with ink-based renderers).
 *
 * Prerequisite: npm install -g firew0rks
 *
 * Usage as hook: reads BeforeTool JSON from stdin
 * Usage as animator: node skill-fireworks.js --animate <skill-name>
 * Debug log: /tmp/fireworks-debug.log
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

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
  // Fallback: ask npm
  try {
    const { execSync } = require('child_process');
    const root = execSync('npm root -g', { encoding: 'utf8', timeout: 3000 }).trim();
    const dir = path.join(root, 'firew0rks', 'fireworks');
    if (fs.statSync(dir).isDirectory()) return dir;
  } catch {}
  return null;
}

// Play 8 frames from 150 total, ~120ms each = ~1s animation
const FRAME_INDICES = [0, 20, 40, 60, 80, 100, 120, 140];
const FRAME_DELAY_MS = 120;

// ── Synchronous sleep (safe in detached child) ──────────────────

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

// ── Animation (writes to /dev/tty, no alt screen buffer) ────────

function runAnimation(skillName) {
  debug(`animate start: skill=${skillName}`);

  const framesDir = findFramesDir();
  if (!framesDir) {
    debug('no frames dir found, exiting');
    process.exit(0);
  }
  debug(`frames dir: ${framesDir}`);

  // Preload frames into memory
  const frames = [];
  for (const idx of FRAME_INDICES) {
    const framePath = path.join(framesDir, `${idx}.txt`);
    try {
      frames.push(fs.readFileSync(framePath));
    } catch {
      debug(`missing frame: ${framePath}`);
    }
  }

  if (frames.length === 0) {
    debug('no frames loaded, exiting');
    process.exit(0);
  }
  debug(`loaded ${frames.length} frames`);

  let ttyFd;
  try {
    ttyFd = fs.openSync('/dev/tty', 'w');
  } catch (err) {
    debug(`cannot open /dev/tty: ${err.message}`);
    process.exit(0);
  }
  debug('opened /dev/tty for writing');

  // Get terminal dimensions
  let rows = 41, cols = 80;
  try {
    const { execSync } = require('child_process');
    const size = execSync('stty size < /dev/tty 2>/dev/null', {
      encoding: 'utf8',
      timeout: 1000,
    }).trim().split(' ');
    if (size.length === 2) {
      rows = parseInt(size[0], 10) || 41;
      cols = parseInt(size[1], 10) || 80;
    }
  } catch {}
  debug(`terminal: ${rows}x${cols}`);

  // Build banner
  const bannerText = ` SKILL ACTIVATED: ${skillName} `;
  const bannerWidth = bannerText.length + 2;
  const boxColor = '\x1b[95;1m';
  const textColor = '\x1b[97;1m';
  const reset = '\x1b[0m';
  const bannerTop = boxColor + '\u2554' + '\u2550'.repeat(bannerText.length) + '\u2557' + reset;
  const bannerMid = boxColor + '\u2551' + reset + textColor + bannerText + reset + boxColor + '\u2551' + reset;
  const bannerBot = boxColor + '\u255A' + '\u2550'.repeat(bannerText.length) + '\u255D' + reset;

  try {
    // Save cursor position, hide cursor
    fs.writeSync(ttyFd, '\x1b7');       // save cursor
    fs.writeSync(ttyFd, '\x1b[?25l');   // hide cursor
    fs.writeSync(ttyFd, '\n'.repeat(rows)); // scroll down to make room
    debug('wrote scroll padding');

    // Play frames — position at top-left of the scrolled region
    for (let i = 0; i < frames.length; i++) {
      // Move cursor to top of the animation area
      fs.writeSync(ttyFd, `\x1b[${rows}A`);  // move up N rows
      fs.writeSync(ttyFd, '\x1b[H');          // cursor home (top-left)
      fs.writeSync(ttyFd, '\x1b[2J');         // clear screen
      fs.writeSync(ttyFd, '\x1b[H');          // cursor home again
      fs.writeSync(ttyFd, frames[i]);         // render frame

      // Overlay banner on last ~50% of frames
      if (i >= Math.floor(frames.length * 0.5)) {
        const startRow = Math.max(1, Math.floor(rows / 2) - 1);
        const startCol = Math.max(1, Math.floor((cols - bannerWidth) / 2) + 1);
        fs.writeSync(ttyFd, `\x1b[${startRow};${startCol}H${bannerTop}`);
        fs.writeSync(ttyFd, `\x1b[${startRow + 1};${startCol}H${bannerMid}`);
        fs.writeSync(ttyFd, `\x1b[${startRow + 2};${startCol}H${bannerBot}`);
      }

      sleep(FRAME_DELAY_MS);
    }

    // Hold final frame briefly
    sleep(300);
    debug('animation complete');

  } catch (err) {
    debug(`animation error: ${err.message}\n${err.stack}`);
  } finally {
    // Clear and restore
    fs.writeSync(ttyFd, '\x1b[2J');     // clear screen
    fs.writeSync(ttyFd, '\x1b[?25h');   // show cursor
    fs.writeSync(ttyFd, '\x1b8');       // restore cursor
    fs.closeSync(ttyFd);
  }

  process.exit(0);
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

  // Return allow + systemMessage banner (guaranteed visible by Gemini CLI)
  const banner = `\x1b[95;1m\u2728 SKILL ACTIVATED: ${skillName} \u2728\x1b[0m`;
  process.stdout.write(JSON.stringify({
    decision: 'allow',
    systemMessage: banner,
  }));

  // Spawn animation as detached background process
  try {
    const child = spawn(process.execPath, [__filename, '--animate', skillName], {
      detached: true,
      stdio: 'ignore',
      env: { ...process.env, NODE_NO_WARNINGS: '1' },
    });
    child.unref();
    debug(`spawned animate child pid=${child.pid} for skill=${skillName}`);
  } catch (err) {
    debug(`spawn failed: ${err.message}`);
  }

  process.exit(0);
}

// ── Dispatch ────────────────────────────────────────────────────

if (process.argv[2] === '--animate') {
  runAnimation(process.argv[3] || 'unknown');
} else {
  runHook();
}
