#!/usr/bin/env node
/**
 * skill-fireworks.js
 *
 * BeforeTool hook that plays a fireworks celebration animation
 * when a skill is activated. Uses firew0rks ASCII art frames
 * rendered to the alternate screen buffer via /dev/tty.
 *
 * The hook outputs {"decision":"allow"} immediately, then spawns
 * a detached child process for the animation — zero latency added
 * to the Gemini CLI pipeline.
 *
 * Prerequisite: npm install -g firew0rks
 *
 * Usage as hook: reads BeforeTool JSON from stdin
 * Usage as animator: node skill-fireworks.js --animate <skill-name>
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

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

// Frame indices to play (15 frames from 150 total, ~100ms each = 1.5s)
const FRAME_INDICES = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140];
const FRAME_DELAY_MS = 100;

// ── Synchronous sleep (safe in detached child) ──────────────────

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

// ── Banner rendering ────────────────────────────────────────────

function buildBanner(skillName) {
  const text = ` SKILL ACTIVATED: ${skillName} `;
  const inner = text.length;
  const top    = '\u2554' + '\u2550'.repeat(inner) + '\u2557';
  const middle = '\u2551' + text + '\u2551';
  const bottom = '\u255A' + '\u2550'.repeat(inner) + '\u255D';
  return { top, middle, bottom, width: inner + 2 };
}

function overlayBanner(ttyFd, skillName, rows, cols) {
  const banner = buildBanner(skillName);
  const startRow = Math.max(1, Math.floor(rows / 2) - 1);
  const startCol = Math.max(1, Math.floor((cols - banner.width) / 2) + 1);

  // Bright magenta box with bold white text
  const boxColor = '\x1b[95;1m';    // bright magenta, bold
  const textColor = '\x1b[97;1m';   // bright white, bold
  const reset = '\x1b[0m';

  const lines = [banner.top, banner.middle, banner.bottom];
  for (let i = 0; i < lines.length; i++) {
    const row = startRow + i;
    let line = lines[i];
    // Color the middle line differently (text portion)
    if (i === 1) {
      line = boxColor + '\u2551' + reset + textColor + ` SKILL ACTIVATED: ${skillName} ` + reset + boxColor + '\u2551' + reset;
    } else {
      line = boxColor + line + reset;
    }
    fs.writeSync(ttyFd, `\x1b[${row};${startCol}H${line}`);
  }
}

// ── Animation ───────────────────────────────────────────────────

function runAnimation(skillName) {
  const framesDir = findFramesDir();
  if (!framesDir) {
    process.exit(0);
  }

  // Preload frames into memory
  const frames = [];
  for (const idx of FRAME_INDICES) {
    const framePath = path.join(framesDir, `${idx}.txt`);
    try {
      frames.push(fs.readFileSync(framePath));
    } catch {
      // Skip missing frames
    }
  }

  if (frames.length === 0) {
    process.exit(0);
  }

  let ttyFd;
  try {
    ttyFd = fs.openSync('/dev/tty', 'w');
  } catch {
    // No TTY available (e.g. piped output) — exit silently
    process.exit(0);
  }

  // Get terminal dimensions
  let rows = 41, cols = 80;
  try {
    const ttyRead = fs.openSync('/dev/tty', 'r');
    const binding = process.binding('tty_wrap');
    // Fallback: try environment or stty
    const { execSync } = require('child_process');
    const size = execSync('stty size < /dev/tty 2>/dev/null', {
      encoding: 'utf8',
      timeout: 1000,
    }).trim().split(' ');
    if (size.length === 2) {
      rows = parseInt(size[0], 10) || 41;
      cols = parseInt(size[1], 10) || 80;
    }
    fs.closeSync(ttyRead);
  } catch {}

  try {
    // Switch to alternate screen buffer, hide cursor, clear
    fs.writeSync(ttyFd, '\x1b[?1049h');  // save screen + switch to alt buffer
    fs.writeSync(ttyFd, '\x1b[?25l');    // hide cursor
    fs.writeSync(ttyFd, '\x1b[2J');      // clear screen

    // Play frames
    for (let i = 0; i < frames.length; i++) {
      fs.writeSync(ttyFd, '\x1b[H');     // cursor home
      fs.writeSync(ttyFd, frames[i]);    // render frame

      // Overlay banner on last ~60% of frames (after explosion starts)
      if (i >= Math.floor(frames.length * 0.4)) {
        overlayBanner(ttyFd, skillName, rows, cols);
      }

      sleep(FRAME_DELAY_MS);
    }

    // Hold final frame with banner briefly
    sleep(200);

  } finally {
    // Restore: show cursor, switch back to main buffer
    fs.writeSync(ttyFd, '\x1b[?25h');    // show cursor
    fs.writeSync(ttyFd, '\x1b[?1049l');  // restore main screen buffer
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

  // Always allow immediately
  process.stdout.write(JSON.stringify({ decision: 'allow' }));

  let skillName = 'unknown';
  try {
    const input = JSON.parse(raw);
    skillName = input.tool_input?.name || input.tool_input?.skill_name || 'unknown';
  } catch {}

  // Spawn animation as detached background process
  const child = spawn(process.execPath, [__filename, '--animate', skillName], {
    detached: true,
    stdio: 'ignore',
    env: { ...process.env, NODE_NO_WARNINGS: '1' },
  });
  child.unref();

  process.exit(0);
}

// ── Dispatch ────────────────────────────────────────────────────

if (process.argv[2] === '--animate') {
  runAnimation(process.argv[3] || 'unknown');
} else {
  runHook();
}
