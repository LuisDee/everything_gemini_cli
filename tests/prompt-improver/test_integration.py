#!/usr/bin/env python3
"""
Integration tests for the prompt-improver system (Gemini CLI)
Tests the complete flow from hook to skill
"""
import json
import subprocess
import sys
from pathlib import Path

# Paths
GEMINI_ROOT = Path(__file__).parent.parent.parent
HOOK_SCRIPT = GEMINI_ROOT / "scripts" / "hooks" / "improve-prompt.py"
SKILL_DIR = GEMINI_ROOT / "skills" / "prompt-improver"


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


def run_hook(prompt):
    """Run the hook script with given prompt"""
    input_data = make_gemini_input(prompt)

    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=input_data,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)


def get_last_user_content(output):
    """Extract the last user message content from hook output"""
    messages = output.get("hookSpecificOutput", {}).get("llm_request", {}).get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def test_end_to_end_flow():
    """Test complete flow from prompt to evaluation"""
    output = run_hook("add authentication")

    # Should get evaluation wrapper
    content = get_last_user_content(output)
    assert "PROMPT EVALUATION" in content or "EVALUATE" in content
    assert "add authentication" in content

    # Should mention skill for vague cases
    assert "skill" in content.lower()

    print("  pass: End-to-end flow works (normal prompt -> evaluation wrapper)")


def test_bypass_flow():
    """Test that bypass mechanism works end-to-end"""
    # Test asterisk bypass
    output = run_hook("* just do it")
    content = get_last_user_content(output)
    assert content == "just do it"
    assert "skill" not in content.lower()

    # Test slash command
    output = run_hook("/commit")
    assert output.get("decision") == "allow"

    # Test hash prefix
    output = run_hook("# note for later")
    assert output.get("decision") == "allow"

    print("  pass: Bypass mechanisms work end-to-end")


def test_skill_file_integrity():
    """Test that all skill files are present and valid"""
    # Check SKILL.md
    skill_md = SKILL_DIR / "SKILL.md"
    assert skill_md.exists(), "SKILL.md missing"

    content = skill_md.read_text()
    assert content.startswith("---\n"), "SKILL.md missing YAML frontmatter"
    assert "name: prompt-improver" in content, "Skill name incorrect"

    # Check reference files
    references_dir = SKILL_DIR / "references"
    assert references_dir.exists(), "references directory missing"

    expected_refs = [
        "question-patterns.md",
        "research-strategies.md",
        "examples.md",
    ]

    for ref in expected_refs:
        ref_file = references_dir / ref
        assert ref_file.exists(), f"Missing reference file: {ref}"

    print("  pass: All skill files present and valid")


def test_token_overhead():
    """Test that hook overhead is reasonable"""
    output = run_hook("test")

    content = get_last_user_content(output)

    # Rough character count (tokens ~ chars/4 for English)
    char_count = len(content)
    estimated_tokens = char_count // 4

    # Should be under 250 tokens
    assert estimated_tokens < 300, \
        f"Hook overhead too high: ~{estimated_tokens} tokens (expected <300)"

    print(f"  pass: Token overhead acceptable: ~{estimated_tokens} tokens (<300)")


def test_hook_output_consistency():
    """Test that hook output is consistent across different prompts"""
    prompts = [
        "fix the bug",
        "add tests",
        "refactor code",
        "implement feature X",
    ]

    for prompt in prompts:
        output = run_hook(prompt)

        # All should have correct structure
        assert output.get("decision") == "allow"
        assert "hookSpecificOutput" in output
        assert "llm_request" in output["hookSpecificOutput"]
        assert "messages" in output["hookSpecificOutput"]["llm_request"]

        # All should have evaluation wrapper
        content = get_last_user_content(output)
        assert "EVALUATE" in content or "evaluate" in content.lower()
        assert prompt in content

    print(f"  pass: Hook output consistent across {len(prompts)} different prompts")


def test_architecture_separation():
    """Test that architecture properly separates concerns"""
    # Hook should be reasonably sized (< 150 lines)
    # Gemini version is larger than Claude due to message array manipulation + multimodal support
    hook_lines = len(HOOK_SCRIPT.read_text().split("\n"))
    assert hook_lines < 150, f"Hook too large: {hook_lines} lines (expected <150)"

    # Hook should contain evaluation logic
    hook_content = HOOK_SCRIPT.read_text()
    assert "PROMPT EVALUATION" in hook_content or "EVALUATE" in hook_content

    # SKILL.md should contain research and question logic (4 phases)
    skill_content = (SKILL_DIR / "SKILL.md").read_text()
    assert "Phase 1" in skill_content or "phase 1" in skill_content.lower()
    assert "Phase 2" in skill_content or "phase 2" in skill_content.lower()
    assert "Research" in skill_content

    # Skill should mention being invoked for vague prompts
    assert "vague" in skill_content.lower()

    print("  pass: Architecture properly separates concerns (hook evaluates, skill enriches)")


def test_gemini_protocol_compliance():
    """Test that hook output follows Gemini BeforeModel protocol"""
    output = run_hook("test prompt")

    # Must have decision field
    assert "decision" in output, "Missing 'decision' field"
    assert output["decision"] in ["allow", "block"], \
        f"Invalid decision: {output['decision']}"

    # hookSpecificOutput must have llm_request with messages
    hook_output = output.get("hookSpecificOutput", {})
    llm_request = hook_output.get("llm_request", {})
    messages = llm_request.get("messages", [])

    assert isinstance(messages, list), "messages must be a list"
    assert len(messages) > 0, "messages must not be empty"

    # Each message must have role and content
    for msg in messages:
        assert "role" in msg, f"Message missing 'role': {msg}"
        assert "content" in msg, f"Message missing 'content': {msg}"

    print("  pass: Gemini protocol compliance verified")


def run_all_tests():
    """Run all integration tests"""
    tests = [
        test_end_to_end_flow,
        test_bypass_flow,
        test_skill_file_integrity,
        test_token_overhead,
        test_hook_output_consistency,
        test_architecture_separation,
        test_gemini_protocol_compliance,
    ]

    print(f"Running {len(tests)} integration tests...\n")

    failed = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed.append((test.__name__, e))
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
        print(f"SUCCESS: All {len(tests)} integration tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
