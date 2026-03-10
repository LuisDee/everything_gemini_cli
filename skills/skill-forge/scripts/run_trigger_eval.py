#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes Gemini CLI to activate it
for a set of queries. Uses hook-based activation detection (primary)
and JSON stats (secondary).

Reuses GEPA's CLI invocation pattern with parallel execution.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.utils import (
    HOOK_LOG,
    SKILLS_DIR,
    clear_hook_log,
    parse_skill_md,
    read_hook_log,
    write_description,
)

INVOCATION_TIMEOUT = 180  # seconds


def _sanitize_prompt(prompt: str) -> str:
    """Sanitize prompt to prevent injection via control characters."""
    if not prompt or not isinstance(prompt, str):
        raise ValueError("Invalid prompt")
    if len(prompt) > 10000:
        raise ValueError(f"Prompt too long ({len(prompt)} chars, max 10000)")
    return "".join(c for c in prompt if c.isprintable() or c in "\n\t")


def run_gemini_cli(prompt: str, timeout: int = INVOCATION_TIMEOUT) -> dict:
    """Run real gemini CLI and return detection results.

    Returns:
        {
            "skills_from_log": ["tdd-workflow", ...],
            "skills_from_stats": bool,
            "activate_skill_count": int,
            "error": str | None,
            "raw_log": str,
        }
    """
    result = {
        "skills_from_log": [],
        "skills_from_stats": False,
        "activate_skill_count": 0,
        "error": None,
        "raw_log": "",
    }

    clear_hook_log()
    prompt = _sanitize_prompt(prompt)
    cmd = ["gemini", "-y", "--prompt", prompt, "--output-format", "json"]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
    except FileNotFoundError:
        result["error"] = "gemini binary not found"
        return result
    except OSError as exc:
        result["error"] = f"failed to start gemini: {exc}"
        return result

    stdout = ""
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
                pass
        result["error"] = "TIMEOUT"
        stdout = ""

    # Parse JSON stats from stdout
    if stdout:
        try:
            data = json.loads(stdout)
            tools = data.get("stats", {}).get("tools", {}).get("byName", {})
            if "activate_skill" in tools:
                result["skills_from_stats"] = True
                result["activate_skill_count"] = tools["activate_skill"].get("count", 0)
        except (json.JSONDecodeError, KeyError):
            pass

    # Read hook log (primary detection source)
    time.sleep(0.5)
    log_entries = read_hook_log()
    result["skills_from_log"] = [
        e.get("skill_name", "") for e in log_entries if e.get("skill_name")
    ]
    result["raw_log"] = HOOK_LOG.read_text() if HOOK_LOG.exists() else ""

    return result


def score_single(
    prompt: str,
    expected_skill: str,
    should_activate: bool,
    timeout: int = INVOCATION_TIMEOUT,
) -> dict:
    """Run a single query and return scored result.

    Gradient scoring:
      Positive (should_activate=True):
        1.0 - target skill activated
        0.3 - different skill activated (routing tried, wrong target)
        0.0 - no skill activated or error

      Negative (should_activate=False):
        1.0 - target skill NOT activated (correct rejection)
        0.0 - target skill incorrectly activated (false positive)
    """
    cli_result = run_gemini_cli(prompt, timeout)
    activated_skills = cli_result["skills_from_log"]

    if cli_result["error"] and cli_result["error"] != "TIMEOUT":
        return {
            "prompt": prompt,
            "expected_skill": expected_skill,
            "should_activate": should_activate,
            "score": 0.0,
            "activated": [],
            "error": cli_result["error"],
            "pass": False,
        }

    if should_activate:
        if expected_skill in activated_skills:
            score = 1.0
        elif len(activated_skills) > 0:
            score = 0.3
        else:
            score = 0.0
        did_pass = score == 1.0
    else:
        score = 0.0 if expected_skill in activated_skills else 1.0
        did_pass = score == 1.0

    return {
        "prompt": prompt,
        "expected_skill": expected_skill,
        "should_activate": should_activate,
        "score": score,
        "activated": activated_skills,
        "error": cli_result.get("error"),
        "pass": did_pass,
    }


def run_trigger_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str | None = None,
    num_workers: int = 3,
    timeout: int = INVOCATION_TIMEOUT,
    runs_per_query: int = 1,
) -> dict:
    """Run the full trigger eval set and return results.

    Note: runs are sequential per query because the hook log is shared
    global state (clear before each run, read after). Multiple workers
    can run if runs_per_query=1 (each gets its own clear/read cycle).
    """
    results = []

    # Sequential execution to avoid hook log race conditions
    for item in eval_set:
        query = item.get("query", item.get("prompt", ""))
        should_trigger = item.get("should_trigger", item.get("should_activate", True))
        expected = item.get("expected_skill", skill_name)

        query_results = []
        for run_idx in range(runs_per_query):
            r = score_single(query, expected, should_trigger, timeout)
            query_results.append(r)

        # Aggregate runs for this query
        scores = [r["score"] for r in query_results]
        passes = [r["pass"] for r in query_results]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "score": avg_score,
            "triggers": sum(1 for r in query_results if r["score"] == 1.0),
            "runs": len(query_results),
            "pass": sum(passes) / len(passes) >= 0.5 if passes else False,
            "activated": query_results[-1]["activated"] if query_results else [],
            "error": query_results[-1].get("error") if query_results else None,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description or "",
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "score": sum(r["score"] for r in results) / total if total else 0.0,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run trigger evaluation for a skill description"
    )
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description")
    parser.add_argument("--runs-per-query", type=int, default=1, help="Runs per query")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout per query")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description

    if args.verbose:
        print(f"Evaluating: {description[:80]}...", file=sys.stderr)

    output = run_trigger_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        runs_per_query=args.runs_per_query,
        timeout=args.timeout,
    )

    if args.verbose:
        s = output["summary"]
        print(f"Results: {s['passed']}/{s['total']} passed (score: {s['score']:.2f})", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            print(
                f"  [{status}] score={r['score']:.1f} "
                f"expected={r['should_trigger']}: {r['query'][:70]}",
                file=sys.stderr,
            )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
