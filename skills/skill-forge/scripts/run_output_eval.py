#!/usr/bin/env python3
"""Run output quality evaluation for a skill.

Tests skill output quality by running prompts with and without the skill
enabled (using baseline_manager for A/B), then comparing results.
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

from scripts.baseline_manager import recover_all, skill_disabled
from scripts.utils import SKILLS_DIR, parse_skill_md

INVOCATION_TIMEOUT = 300  # seconds (output eval takes longer)


def run_gemini_task(
    prompt: str,
    output_dir: Path,
    timeout: int = INVOCATION_TIMEOUT,
) -> dict:
    """Run a gemini task and capture outputs.

    Returns:
        {"success": bool, "error": str | None, "duration_seconds": float}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / "transcript.md"

    cmd = ["gemini", "-y", "--prompt", prompt, "--output-format", "json"]

    start_time = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
    except (FileNotFoundError, OSError) as exc:
        return {"success": False, "error": str(exc), "duration_seconds": 0.0}

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
        return {
            "success": False,
            "error": "TIMEOUT",
            "duration_seconds": time.time() - start_time,
        }

    duration = time.time() - start_time

    # Save transcript
    transcript_path.write_text(f"## Eval Prompt\n\n{prompt}\n\n## Output\n\n{stdout}\n")

    # Save timing
    timing_path = output_dir.parent / "timing.json"
    timing_path.write_text(json.dumps({
        "total_duration_seconds": round(duration, 1),
    }, indent=2))

    return {
        "success": proc.returncode == 0,
        "error": None if proc.returncode == 0 else f"exit code {proc.returncode}",
        "duration_seconds": round(duration, 1),
    }


def run_output_eval(
    evals: list[dict],
    skill_name: str,
    workspace: Path,
    runs_per_config: int = 1,
    timeout: int = INVOCATION_TIMEOUT,
) -> dict:
    """Run output quality eval with A/B comparison.

    For each eval prompt:
    1. Run with skill enabled (with_skill)
    2. Disable skill, run baseline (without_skill)
    3. Re-enable skill

    Results are saved in workspace directory structure.
    """
    # Recover any previously crashed baseline runs
    recover_all()

    workspace.mkdir(parents=True, exist_ok=True)
    results = []

    for idx, eval_item in enumerate(evals):
        prompt = eval_item.get("prompt", eval_item.get("query", ""))
        eval_id = eval_item.get("id", idx)
        eval_dir = workspace / f"eval-{eval_id}"

        # Save eval metadata
        eval_dir.mkdir(parents=True, exist_ok=True)
        (eval_dir / "eval_metadata.json").write_text(json.dumps({
            "eval_id": eval_id,
            "prompt": prompt,
            "assertions": eval_item.get("expectations", eval_item.get("assertions", [])),
        }, indent=2))

        eval_result = {
            "eval_id": eval_id,
            "prompt": prompt[:80],
            "with_skill": [],
            "without_skill": [],
        }

        # With-skill runs
        for run_num in range(1, runs_per_config + 1):
            run_dir = eval_dir / "with_skill" / f"run-{run_num}"
            outputs_dir = run_dir / "outputs"
            print(f"  [with_skill] eval-{eval_id} run-{run_num}...", file=sys.stderr)
            result = run_gemini_task(prompt, outputs_dir, timeout)
            eval_result["with_skill"].append(result)

        # Without-skill runs (skill disabled)
        for run_num in range(1, runs_per_config + 1):
            run_dir = eval_dir / "without_skill" / f"run-{run_num}"
            outputs_dir = run_dir / "outputs"
            print(f"  [without_skill] eval-{eval_id} run-{run_num}...", file=sys.stderr)
            with skill_disabled(skill_name):
                result = run_gemini_task(prompt, outputs_dir, timeout)
            eval_result["without_skill"].append(result)

        results.append(eval_result)

    return {
        "skill_name": skill_name,
        "workspace": str(workspace),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Run output quality evaluation")
    parser.add_argument("--evals", required=True, help="Path to evals JSON")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--workspace", required=True, help="Output workspace directory")
    parser.add_argument("--runs-per-config", type=int, default=1, help="Runs per config")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per run")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    evals = json.loads(Path(args.evals).read_text())
    if isinstance(evals, dict):
        evals = evals.get("evals", [])

    skill_path = Path(args.skill_path)
    name, _, _ = parse_skill_md(skill_path)

    if args.verbose:
        print(f"Running output eval for {name}", file=sys.stderr)
        print(f"  Evals: {len(evals)}, Runs/config: {args.runs_per_config}", file=sys.stderr)

    output = run_output_eval(
        evals=evals,
        skill_name=name,
        workspace=Path(args.workspace),
        runs_per_config=args.runs_per_config,
        timeout=args.timeout,
    )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
