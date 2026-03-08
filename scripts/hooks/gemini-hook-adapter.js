#!/usr/bin/env node
/**
 * Gemini CLI Hook Adapter
 *
 * Translates between Gemini CLI hook protocol and ECC hook scripts.
 *
 * Gemini CLI sends JSON on stdin with tool_name, tool_input, session_id etc.
 * ECC hooks expect similar JSON and output raw text on stdout.
 *
 * This adapter:
 * 1. Reads Gemini-format stdin JSON
 * 2. Sets GEMINI_SESSION_ID env from session_id field
 * 3. Pipes stdin to child ECC hook script
 * 4. Converts child output to Gemini protocol:
 *    - Exit 0 + empty stdout → (no output, allow)
 *    - Exit 0 + stdout content → {"systemMessage":"<content>"}
 *    - Exit 2 → exit 2 (Gemini's native block signal)
 * 5. Always forwards stderr
 *
 * Usage: node gemini-hook-adapter.js <child-script-path> [args...]
 */

'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const MAX_STDIN = 1024 * 1024;

function readStdinRaw() {
  return new Promise(resolve => {
    let raw = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => {
      if (raw.length < MAX_STDIN) {
        const remaining = MAX_STDIN - raw.length;
        raw += chunk.substring(0, remaining);
      }
    });
    process.stdin.on('end', () => resolve(raw));
    process.stdin.on('error', () => resolve(raw));
  });
}

async function main() {
  const args = process.argv.slice(2);
  const childScript = args[0];
  const childArgs = args.slice(1);

  if (!childScript) {
    // No script specified, pass through
    const raw = await readStdinRaw();
    process.stdout.write(raw);
    process.exit(0);
  }

  const raw = await readStdinRaw();

  // Extract session_id from Gemini input and set as env var
  const env = { ...process.env };
  try {
    const input = JSON.parse(raw);
    if (input.session_id) {
      env.GEMINI_SESSION_ID = input.session_id;
      // Backward compat for child scripts that read CLAUDE_SESSION_ID
      env.CLAUDE_SESSION_ID = input.session_id;
    }
    if (input.transcript_path) {
      env.GEMINI_TRANSCRIPT_PATH = input.transcript_path;
      env.CLAUDE_TRANSCRIPT_PATH = input.transcript_path;
    }
  } catch {
    // Non-JSON input, pass through as-is
  }

  // Resolve child script path
  const scriptPath = path.isAbsolute(childScript)
    ? childScript
    : path.resolve(__dirname, childScript);

  // Spawn child hook script
  const result = spawnSync('node', [scriptPath, ...childArgs], {
    input: raw,
    encoding: 'utf8',
    env,
    cwd: process.cwd(),
    timeout: 30000,
  });

  // Forward stderr to stderr (Gemini CLI displays it)
  if (result.stderr) {
    process.stderr.write(result.stderr);
  }

  const exitCode = Number.isInteger(result.status) ? result.status : 0;

  if (exitCode === 2) {
    // Child wants to block — use Gemini's native exit 2 block
    process.exit(2);
  }

  // Exit 0: convert child stdout to Gemini JSON protocol
  const childOutput = (result.stdout || '').trim();

  if (childOutput) {
    // Check if child already output valid JSON (some hooks do)
    try {
      const parsed = JSON.parse(childOutput);
      // If it's already Gemini-compatible JSON, pass through
      if (parsed.decision || parsed.systemMessage) {
        process.stdout.write(JSON.stringify(parsed));
        process.exit(0);
      }
    } catch {
      // Not JSON — wrap as systemMessage
    }

    // Try to see if the child output modified the input (ECC pattern:
    // hooks output the modified input JSON back on stdout)
    try {
      const parsed = JSON.parse(childOutput);
      // If child returned modified input (has tool_input), pass through
      // Gemini CLI will use the modified version
      if (parsed.tool_input || parsed.tool_name) {
        process.stdout.write(childOutput);
        process.exit(0);
      }
    } catch {
      // Not JSON at all — wrap as systemMessage
    }

    // Plain text output — wrap as systemMessage for Gemini
    process.stdout.write(JSON.stringify({ systemMessage: childOutput }));
  }

  // Empty output = allow (no stdout needed for Gemini)
  process.exit(0);
}

main().catch(err => {
  process.stderr.write(`[GeminiHookAdapter] Error: ${err.message}\n`);
  process.exit(0);
});
