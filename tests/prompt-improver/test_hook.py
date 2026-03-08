#!/usr/bin/env python3
"""
Tests for the prompt-improver hook (Gemini CLI BeforeModel format)
Tests bypass prefixes, evaluation wrapping, and JSON output format
"""
import json
import subprocess
import sys
from pathlib import Path

# Path to the hook script
HOOK_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "hooks" / "improve-prompt.py"


def make_gemini_input(prompt):
    """Create Gemini BeforeModel stdin format"""
    return json.dumps({
        "session_id": "test-session",
        "hook_event_name": "BeforeModel",
        "timestamp": "2024-01-01T00:00:00Z",
        "cwd": "/tmp/test",
        "llm_request": {
            "model": "gemini-2.5-flash",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "config": {}
        }
    })


def make_gemini_input_with_history(history_messages, prompt):
    """Create Gemini BeforeModel stdin with conversation history"""
    messages = list(history_messages)
    messages.append({"role": "user", "content": prompt})
    return json.dumps({
        "session_id": "test-session",
        "hook_event_name": "BeforeModel",
        "timestamp": "2024-01-01T00:00:00Z",
        "cwd": "/tmp/test",
        "llm_request": {
            "model": "gemini-2.5-flash",
            "messages": messages,
            "config": {}
        }
    })


def run_hook(prompt, history=None):
    """Run the hook script with given prompt and return parsed output"""
    if history:
        input_data = make_gemini_input_with_history(history, prompt)
    else:
        input_data = make_gemini_input(prompt)

    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=input_data,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Hook failed (exit {result.returncode}): {result.stderr}")

    return json.loads(result.stdout)


def get_last_user_content(output):
    """Extract the last user message content from hook output"""
    messages = output.get("hookSpecificOutput", {}).get("llm_request", {}).get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def test_bypass_asterisk():
    """Test that * prefix strips the prefix and passes through"""
    output = run_hook("* just add a comment")

    assert output.get("decision") == "allow"
    content = get_last_user_content(output)
    assert content == "just add a comment"
    assert not content.startswith("*")
    print("  pass: Asterisk bypass test")


def test_bypass_slash():
    """Test that / prefix passes through unchanged (slash commands)"""
    output = run_hook("/commit")

    assert output.get("decision") == "allow"
    # Slash commands pass through without modification
    assert "hookSpecificOutput" not in output or \
           "llm_request" not in output.get("hookSpecificOutput", {})
    print("  pass: Slash command bypass test")


def test_bypass_hash():
    """Test that # prefix passes through unchanged (memorize feature)"""
    output = run_hook("# remember to use TypeScript")

    assert output.get("decision") == "allow"
    assert "hookSpecificOutput" not in output or \
           "llm_request" not in output.get("hookSpecificOutput", {})
    print("  pass: Hash prefix bypass test")


def test_evaluation_prompt():
    """Test that normal prompts get evaluation wrapper"""
    output = run_hook("fix the bug")

    assert output.get("decision") == "allow"
    content = get_last_user_content(output)

    # Should contain evaluation prompt
    assert "PROMPT EVALUATION" in content
    assert "fix the bug" in content
    assert "EVALUATE" in content

    # Should mention using the skill for vague cases
    assert "prompt-improver skill" in content.lower() or "skill" in content.lower()

    # Should have proceed/clear logic
    assert "clear" in content.lower() or "proceed" in content.lower()

    print("  pass: Evaluation prompt test")


def test_json_output_format():
    """Test that output follows correct Gemini JSON schema"""
    output = run_hook("test prompt")

    # Must have decision
    assert "decision" in output
    assert output["decision"] == "allow"

    # Must have hookSpecificOutput with llm_request.messages
    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert "llm_request" in hook_output
    assert "messages" in hook_output["llm_request"]
    assert isinstance(hook_output["llm_request"]["messages"], list)

    # Messages should preserve structure
    messages = hook_output["llm_request"]["messages"]
    assert len(messages) > 0
    assert messages[-1]["role"] == "user"

    print("  pass: JSON output format test")


def test_empty_prompt():
    """Test handling of empty prompt"""
    output = run_hook("")

    assert output.get("decision") == "allow"
    content = get_last_user_content(output)

    # Empty prompt should still get evaluation wrapper
    assert "PROMPT EVALUATION" in content or "EVALUATE" in content
    print("  pass: Empty prompt test")


def test_multiline_prompt():
    """Test handling of multiline prompts"""
    prompt = """refactor the auth system
to use async/await
and add error handling"""

    output = run_hook(prompt)

    assert output.get("decision") == "allow"
    content = get_last_user_content(output)

    # Should preserve multiline content in evaluation
    assert "refactor the auth system" in content
    print("  pass: Multiline prompt test")


def test_special_characters():
    """Test handling of special characters in prompts"""
    output = run_hook('fix the "bug" in user\'s code & database')

    assert output.get("decision") == "allow"
    content = get_last_user_content(output)

    # Should contain the original prompt
    assert "bug" in content
    assert "user" in content or "users" in content
    print("  pass: Special characters test")


def test_conversation_history_preserved():
    """Test that conversation history is preserved in output"""
    history = [
        {"role": "user", "content": "What is the project about?"},
        {"role": "assistant", "content": "It's a web application..."},
    ]
    output = run_hook("fix the bug", history=history)

    assert output.get("decision") == "allow"
    messages = output.get("hookSpecificOutput", {}).get("llm_request", {}).get("messages", [])

    # Should have all messages (2 history + 1 current)
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is the project about?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "It's a web application..."
    assert messages[2]["role"] == "user"
    assert "PROMPT EVALUATION" in messages[2]["content"]

    print("  pass: Conversation history preserved test")


def test_model_preserved():
    """Test that model field is preserved in output"""
    output = run_hook("test prompt")

    assert output.get("decision") == "allow"
    llm_request = output.get("hookSpecificOutput", {}).get("llm_request", {})
    assert llm_request.get("model") == "gemini-2.5-flash"

    print("  pass: Model preserved test")


def test_malformed_json():
    """Test handling of malformed JSON input"""
    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="not valid json",
        capture_output=True,
        text=True
    )

    # Should not crash
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output.get("decision") == "allow"

    print("  pass: Malformed JSON test")


def run_all_tests():
    """Run all tests"""
    tests = [
        test_bypass_asterisk,
        test_bypass_slash,
        test_bypass_hash,
        test_evaluation_prompt,
        test_json_output_format,
        test_empty_prompt,
        test_multiline_prompt,
        test_special_characters,
        test_conversation_history_preserved,
        test_model_preserved,
        test_malformed_json,
    ]

    print(f"Running {len(tests)} hook tests...\n")

    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed.append((test.__name__, e))

    print(f"\n{'='*60}")
    if failed:
        print(f"FAILED: {len(failed)}/{len(tests)} tests failed")
        for name, error in failed:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(tests)} hook tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
