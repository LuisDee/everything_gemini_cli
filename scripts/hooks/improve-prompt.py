#!/usr/bin/env python3
"""
Gemini CLI Prompt Improver Hook (BeforeModel)
Evaluates prompts for clarity and wraps vague prompts with evaluation instructions.

Stdin: Gemini BeforeModel JSON with llm_request.messages
Stdout: JSON with decision + optional modified llm_request.messages
"""
import json
import sys


def output_allow(messages=None, model=None, config=None):
    """Output allow decision, optionally with modified messages."""
    output = {"decision": "allow"}
    if messages is not None:
        hook_output = {"llm_request": {"messages": messages}}
        if model is not None:
            hook_output["llm_request"]["model"] = model
        if config is not None:
            hook_output["llm_request"]["config"] = config
        output["hookSpecificOutput"] = hook_output
    print(json.dumps(output))


# Load input from stdin
try:
    input_data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    # Can't parse input - allow the model call to proceed unmodified
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

llm_request = input_data.get("llm_request", {})
if not isinstance(llm_request, dict):
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

messages = llm_request.get("messages", [])
if not isinstance(messages, list) or len(messages) == 0:
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

model = llm_request.get("model", None)
config = llm_request.get("config", None)

# Find the last user message
last_user_idx = None
for i in range(len(messages) - 1, -1, -1):
    msg = messages[i]
    if msg.get("role") == "user":
        last_user_idx = i
        break

if last_user_idx is None:
    # No user message found, pass through
    output_allow()
    sys.exit(0)

# Extract the prompt text from the last user message
last_msg = messages[last_user_idx]
content = last_msg.get("content", "")

# Handle content that may be a list of parts (multimodal)
if isinstance(content, list):
    # Extract text from parts
    prompt = ""
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            prompt += part.get("text", "")
        elif isinstance(part, str):
            prompt += part
else:
    prompt = str(content)

# Check for bypass conditions
# 1. Explicit bypass with * prefix
if prompt.startswith("*"):
    clean_prompt = prompt[1:].strip()
    modified_messages = messages.copy()
    if isinstance(content, list):
        # Rebuild parts with cleaned text
        new_parts = []
        cleaned = False
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text" and not cleaned:
                new_parts.append({"type": "text", "text": clean_prompt})
                cleaned = True
            else:
                new_parts.append(part)
        modified_messages[last_user_idx] = {**last_msg, "content": new_parts}
    else:
        modified_messages[last_user_idx] = {**last_msg, "content": clean_prompt}
    output_allow(modified_messages, model, config)
    sys.exit(0)

# 2. Slash commands (built-in or custom)
if prompt.startswith("/"):
    output_allow()
    sys.exit(0)

# 3. Memorize feature (# prefix)
if prompt.startswith("#"):
    output_allow()
    sys.exit(0)

# Escape quotes in prompt for safe embedding
escaped_prompt = prompt.replace("\\", "\\\\").replace('"', '\\"')

# Build the evaluation wrapper
wrapped_prompt = f"""PROMPT EVALUATION

Original user request: "{escaped_prompt}"

EVALUATE: Is this prompt clear enough to execute, or does it need enrichment?

PROCEED IMMEDIATELY if:
- Detailed/specific OR you have sufficient context OR can infer intent

ONLY USE SKILL if genuinely vague (e.g., "fix the bug" with no context):
- If vague:
  1. First, preface with brief note: "Hey! The Prompt Improver Hook flagged your prompt as a bit vague because [specific reason: ambiguous scope/missing context/unclear target/etc]."
  2. Then use the prompt-improver skill to research and generate clarifying questions
- The skill will guide you through research, question generation, and execution
- Trust user intent by default. Check conversation history before using the skill.

If clear, proceed with the original request. If vague, invoke the skill."""

# Modify the last user message with the wrapped prompt
modified_messages = messages.copy()
if isinstance(content, list):
    new_parts = []
    wrapped = False
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text" and not wrapped:
            new_parts.append({"type": "text", "text": wrapped_prompt})
            wrapped = True
        else:
            new_parts.append(part)
    modified_messages[last_user_idx] = {**last_msg, "content": new_parts}
else:
    modified_messages[last_user_idx] = {**last_msg, "content": wrapped_prompt}

output_allow(modified_messages, model, config)
sys.exit(0)
