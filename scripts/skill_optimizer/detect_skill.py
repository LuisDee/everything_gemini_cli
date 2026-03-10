#!/usr/bin/env python3
"""GEPA skill activation detector for Gemini CLI.

Runs Gemini CLI with a test prompt and detects which skill (if any) was
activated by polling the session transcript while Gemini runs.  Kills the
process early once activation is detected (no need to wait for full execution).

Usage (CLI):
    python3 detect_skill.py --prompt "Write TDD tests first" --expected tdd-workflow

Usage (module):
    from skill_optimizer.detect_skill import detect_skill_activation
    result = detect_skill_activation("Write TDD tests first", "tdd-workflow")
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

TRANSCRIPT_DIR = Path.home() / ".gemini" / "tmp" / "gemini" / "chats"


def _get_existing_transcripts() -> set[str]:
    """Return the set of transcript file paths that currently exist."""
    if not TRANSCRIPT_DIR.is_dir():
        return set()
    return {str(p) for p in TRANSCRIPT_DIR.glob("session-*.json")}


def _find_new_transcripts(before: set[str]) -> list[str]:
    """Return new transcript files sorted by mtime (newest first)."""
    if not TRANSCRIPT_DIR.is_dir():
        return []
    current = {str(p) for p in TRANSCRIPT_DIR.glob("session-*.json")}
    new_files = current - before
    return sorted(new_files, key=lambda p: os.path.getmtime(p), reverse=True)


def _extract_skills_from_transcript(transcript_path: str) -> list[str]:
    """Parse a transcript JSON file and return all activated skill names."""
    skills: list[str] = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return skills

    for msg in data.get("messages", []):
        for tc in msg.get("toolCalls", []):
            if tc.get("name") == "activate_skill":
                skill_name = tc.get("args", {}).get("name")
                if skill_name:
                    skills.append(skill_name)
    return skills


def _check_new_transcripts_for_skills(before: set[str]) -> list[str]:
    """Check all new transcript files for activated skills."""
    all_skills: list[str] = []
    for path in _find_new_transcripts(before):
        all_skills.extend(_extract_skills_from_transcript(path))
    return all_skills


def detect_skill_activation(
    prompt: str, expected_skill: str, timeout: int = 60
) -> dict[str, Any]:
    """Run Gemini CLI with *prompt* and detect which skill was activated.

    Uses Popen to poll transcripts while Gemini runs.  Kills the process
    early once activation is detected — no need to wait for full execution.

    Args:
        prompt: The user prompt to send to Gemini CLI.
        expected_skill: The skill name we expect to be activated.
        timeout: Maximum seconds to wait for the Gemini CLI process.

    Returns:
        A dict with keys:
            activated   - True if the expected skill was activated.
            skill_name  - First skill activated (or None).
            all_skills  - List of all skills activated during the session.
            prompt      - The prompt that was sent.
            expected    - The expected skill name.
            error       - Error description (or None on success).
    """
    result: dict[str, Any] = {
        "activated": False,
        "skill_name": None,
        "all_skills": [],
        "prompt": prompt,
        "expected": expected_skill,
        "error": None,
    }

    # 1. Snapshot existing transcripts before launching Gemini.
    before = _get_existing_transcripts()

    # 2. Launch Gemini CLI as a subprocess (non-blocking).
    cmd = ["gemini", "--prompt", prompt, "--output-format", "json", "-y"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,  # new process group for clean kill
        )
    except FileNotFoundError:
        result["error"] = "gemini binary not found in PATH"
        return result
    except OSError as exc:
        result["error"] = f"failed to run gemini: {exc}"
        return result

    # 3. Poll for skill activation while Gemini runs.
    deadline = time.monotonic() + timeout
    poll_interval = 2.0  # seconds between checks
    detected_skills: list[str] = []
    early_kill = False

    try:
        while time.monotonic() < deadline:
            # Check if Gemini has exited on its own.
            retcode = proc.poll()
            if retcode is not None:
                break

            # Poll transcripts for skill activation.
            detected_skills = _check_new_transcripts_for_skills(before)
            if detected_skills:
                # We found activation — kill the process early.
                early_kill = True
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        proc.wait(timeout=3)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        pass
                break

            time.sleep(poll_interval)
        else:
            # Timeout reached — kill the process.
            result["error"] = f"gemini process timed out after {timeout}s"
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    proc.wait(timeout=3)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    pass
    finally:
        # Ensure cleanup.
        try:
            proc.kill()
            proc.wait(timeout=3)
        except (ProcessLookupError, OSError):
            pass

    # 4. Final check — if we didn't detect skills during polling,
    #    check transcripts one more time (they may have been written
    #    just before the process exited or was killed).
    if not detected_skills:
        time.sleep(1)  # brief pause for filesystem flush
        detected_skills = _check_new_transcripts_for_skills(before)

    # 5. Build result.
    result["all_skills"] = detected_skills
    if detected_skills:
        result["skill_name"] = detected_skills[0]
        if early_kill:
            result["error"] = None  # clear timeout error if we got a result
    result["activated"] = expected_skill in detected_skills

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect which Gemini CLI skill is activated by a prompt."
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="The prompt to send to Gemini CLI.",
    )
    parser.add_argument(
        "--expected",
        required=True,
        help="The skill name we expect to be activated.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for the Gemini CLI process (default: 60).",
    )
    args = parser.parse_args()

    result = detect_skill_activation(
        prompt=args.prompt,
        expected_skill=args.expected,
        timeout=args.timeout,
    )
    json.dump(result, sys.stdout, indent=2)
    print()  # trailing newline

    # Exit with non-zero if the expected skill was NOT activated.
    sys.exit(0 if result["activated"] else 1)


if __name__ == "__main__":
    main()
