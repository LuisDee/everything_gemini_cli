#!/usr/bin/env node
/**
 * skill-activation-logger.js
 *
 * BeforeTool hook that logs every activate_skill call to
 * /tmp/gemini-skill-activations.log as a JSON line.
 *
 * Always allows the tool call through (never blocks).
 *
 * Stdin format (Gemini BeforeTool):
 *   { tool_name, tool_input: { name: "<skill_name>" }, session_id, ... }
 *
 * Stdout: { "decision": "allow" }
 */

'use strict';

const fs = require('fs');
const LOG_PATH = '/tmp/gemini-skill-activations.log';

function readStdin() {
  return new Promise(resolve => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', () => resolve(data));
  });
}

async function main() {
  const raw = await readStdin();

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    // Non-JSON input — allow and exit
    process.stdout.write(JSON.stringify({ decision: 'allow' }));
    process.exit(0);
  }

  const toolName = input.tool_name || '';
  const skillName = input.tool_input?.name || input.tool_input?.skill_name || '';

  // Log the activation
  const entry = {
    timestamp: new Date().toISOString(),
    tool_name: toolName,
    skill_name: skillName,
    session_id: input.session_id || '',
  };

  try {
    fs.appendFileSync(LOG_PATH, JSON.stringify(entry) + '\n');
  } catch (err) {
    // Log failure should never block the tool
    process.stderr.write(`skill-activation-logger: write failed: ${err.message}\n`);
  }

  // Always allow
  process.stdout.write(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

main();
