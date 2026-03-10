#!/usr/bin/env python3
"""GEPA optimizer for Gemini CLI skill descriptions.

Uses gepa.optimize_anything to evolve skill descriptions that maximize
real skill activation in the Gemini CLI binary.

EVERY score is backed by:
  1. /tmp/gemini-skill-activations.log (hook logger)
  2. JSON stats from gemini --output-format json (stats.tools.byName)

The evaluator NEVER calls the Gemini API directly. It ONLY invokes the
real `gemini` CLI binary with --prompt.

Usage:
    python3 optimizer.py --skill tdd-workflow --data eval_data/tdd-workflow.json
    python3 optimizer.py --skill tdd-workflow --data eval_data/tdd-workflow.json --max-calls 30
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
import yaml
from pathlib import Path
from typing import Any

SKILLS_DIR = Path.home() / ".gemini" / "skills"
DESCRIPTIONS_FILE = Path(__file__).parent / "skill_descriptions.json"
RESULTS_DIR = Path(__file__).parent / "results"
STATUS_FILE = Path(__file__).parent / "gepa-status.json"
HOOK_LOG = Path("/tmp/gemini-skill-activations.log")
INVOCATION_TIMEOUT = 180  # seconds (gemini CLI has ~30s startup latency)

# ── Status heartbeat ─────────────────────────────────────────────────

_status: dict[str, Any] = {}


def _init_status(skill_name: str, total_prompts: int) -> None:
    """Initialize the status file at the start of a GEPA run."""
    global _status
    _status = {
        "skill": skill_name,
        "running": True,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_update": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "prompts_completed": 0,
        "prompts_total": total_prompts,
        "current_prompt": "",
        "last_score": None,
        "last_activated": [],
        "scores_history": [],
        "errors": 0,
        "timeouts": 0,
    }
    _write_status()


def _update_status(**kwargs: Any) -> None:
    """Update status fields and write to disk."""
    global _status
    _status.update(kwargs)
    _status["last_update"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _write_status()


def _write_status() -> None:
    """Write status JSON to disk atomically."""
    tmp = STATUS_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_status, f, indent=2)
        tmp.rename(STATUS_FILE)
    except OSError:
        pass


# ── Skill description read/write ─────────────────────────────────────

def _read_current_description(skill_name: str) -> str:
    """Read the current YAML description from a skill's SKILL.md."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("---"):
        raise ValueError(f"No YAML frontmatter in {skill_md}")
    parts = content.split("---", 2)
    fm = yaml.safe_load(parts[1])
    return fm.get("description", "")


def _write_description(skill_name: str, description: str) -> None:
    """Write a new description to a skill's SKILL.md YAML frontmatter."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---", 2)
    fm = yaml.safe_load(parts[1])
    fm["description"] = description
    new_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True, width=200)
    new_content = "---\n" + new_yaml + "---" + parts[2]
    with open(skill_md, "w", encoding="utf-8") as f:
        f.write(new_content)


def _backup_description(skill_name: str) -> str:
    """Back up description to a restore file for crash recovery."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    backup_file = SKILLS_DIR / skill_name / ".SKILL.md.gepa-backup"
    shutil.copy2(skill_md, backup_file)
    return _read_current_description(skill_name)


def _ensure_restored(skill_name: str) -> None:
    """Restore from backup if one exists (crash recovery)."""
    backup_file = SKILLS_DIR / skill_name / ".SKILL.md.gepa-backup"
    if backup_file.exists():
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        shutil.copy2(backup_file, skill_md)
        backup_file.unlink()
        print(f"[RECOVERY] Restored {skill_name} from backup after crash")


def _cleanup_backup(skill_name: str) -> None:
    """Remove backup file after successful restore."""
    backup_file = SKILLS_DIR / skill_name / ".SKILL.md.gepa-backup"
    backup_file.unlink(missing_ok=True)


def _sanitize_prompt(prompt: str) -> str:
    """Sanitize prompt to prevent injection via control characters."""
    if not prompt or not isinstance(prompt, str):
        raise ValueError("Invalid prompt")
    if len(prompt) > 10000:
        raise ValueError(f"Prompt too long ({len(prompt)} chars, max 10000)")
    return "".join(c for c in prompt if c.isprintable() or c in "\n\t")


# ── Real CLI invocation ──────────────────────────────────────────────

def _clear_hook_log() -> None:
    """Truncate the hook log file."""
    try:
        HOOK_LOG.write_text("")
    except OSError:
        pass


def _read_hook_log() -> list[dict]:
    """Read all JSON lines from the hook log."""
    entries = []
    try:
        text = HOOK_LOG.read_text().strip()
        if not text:
            return entries
        for line in text.split("\n"):
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return entries


def _run_gemini_cli(prompt: str, timeout: int = INVOCATION_TIMEOUT) -> dict:
    """Run real gemini CLI and return detection results.

    Returns:
        {
            "skills_from_log": ["tdd-workflow", ...],  # from hook log
            "skills_from_stats": bool,  # activate_skill in JSON stats
            "activate_skill_count": int,
            "error": str | None,
            "raw_log": str,  # raw hook log contents
        }
    """
    result = {
        "skills_from_log": [],
        "skills_from_stats": False,
        "activate_skill_count": 0,
        "error": None,
        "raw_log": "",
    }

    _clear_hook_log()

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
        # Still read the hook log — activations may have happened before timeout
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

    # Read hook log (primary source of which skills were activated)
    time.sleep(0.5)  # brief pause for filesystem flush
    log_entries = _read_hook_log()
    result["skills_from_log"] = [
        e.get("skill_name", "") for e in log_entries if e.get("skill_name")
    ]
    result["raw_log"] = HOOK_LOG.read_text() if HOOK_LOG.exists() else ""

    return result


# ── GEPA Evaluator ───────────────────────────────────────────────────

def evaluator(candidate: str, example: dict | None = None) -> tuple[float, dict]:
    """GEPA evaluator: score a candidate description using REAL CLI.

    Gradient scoring:
      1.0 — target skill activated
      0.3 — different skill activated (routing tried, wrong target)
      0.0 — no skill activated at all OR timeout

    For negative examples (should_activate=False):
      1.0 — target skill NOT activated (correct rejection)
      0.0 — target skill incorrectly activated (false positive)

    Args:
        candidate: The proposed skill description text.
        example: {"prompt": str, "expected_skill": str, "should_activate": bool}

    Returns:
        (score, side_info) — side_info includes raw log for GEPA ASI
    """
    if example is None:
        return 0.0, {"error": "no example provided"}

    prompt = example.get("prompt", "")
    expected = example.get("expected_skill", "")
    should_activate = example.get("should_activate", True)
    difficulty = example.get("difficulty", "unknown")

    # Update status: starting this prompt
    _update_status(current_prompt=prompt[:80])

    # 1. Write the candidate description to SKILL.md
    try:
        _write_description(expected, candidate)
    except Exception as exc:
        _update_status(errors=_status.get("errors", 0) + 1)
        return 0.0, {"error": f"failed to write description: {exc}"}

    # 2. Run real gemini CLI
    cli_result = _run_gemini_cli(prompt)

    timed_out = cli_result["error"] == "TIMEOUT"
    if timed_out:
        _update_status(timeouts=_status.get("timeouts", 0) + 1)

    # For non-timeout, non-recoverable errors, bail early
    if cli_result["error"] and cli_result["error"] != "TIMEOUT":
        _update_status(
            errors=_status.get("errors", 0) + 1,
            prompts_completed=_status.get("prompts_completed", 0) + 1,
            last_score=0.0,
            last_activated=[],
            scores_history=_status.get("scores_history", []) + [0.0],
        )
        return 0.0, {
            "error": cli_result["error"],
            "prompt": prompt[:80],
            "expected": expected,
        }

    # 3. Score based on hook log (ground truth)
    # NOTE: On timeout, _run_gemini_cli still reads the hook log,
    # so activations that happened before timeout are captured.
    activated_skills = cli_result["skills_from_log"]

    if should_activate:
        if expected in activated_skills:
            score = 1.0
        elif len(activated_skills) > 0:
            score = 0.3  # wrong skill activated
        else:
            score = 0.0  # no skill activated
    else:
        # Negative case
        score = 0.0 if expected in activated_skills else 1.0

    # Update status: completed this prompt
    _update_status(
        prompts_completed=_status.get("prompts_completed", 0) + 1,
        last_score=score,
        last_activated=activated_skills,
        scores_history=_status.get("scores_history", []) + [score],
    )

    side_info = {
        "prompt": prompt[:80],
        "expected": expected,
        "activated": activated_skills,
        "score": score,
        "difficulty": difficulty,
        "type": "positive" if should_activate else "negative",
        "timed_out": timed_out,
        "raw_log": cli_result["raw_log"],
        "stats_confirm": cli_result["skills_from_stats"],
        "activate_count": cli_result["activate_skill_count"],
    }

    return score, side_info


# ── GEPA Optimization ────────────────────────────────────────────────

def run_optimization(
    skill_name: str,
    data_file: str,
    max_calls: int = 30,
    model: str = "gemini/gemini-3-flash-preview",
) -> dict[str, Any]:
    """Run GEPA optimization for a single skill using real CLI evals."""
    from gepa.optimize_anything import (
        optimize_anything,
        GEPAConfig,
        EngineConfig,
        ReflectionConfig,
    )

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    train_examples = data.get("train", [])
    val_examples = data.get("val", [])

    if not train_examples:
        raise ValueError(f"No training examples in {data_file}")

    # Crash recovery: restore from backup if previous run was killed
    _ensure_restored(skill_name)

    # Back up the original description (creates .gepa-backup file)
    original_desc = _backup_description(skill_name)
    seed = original_desc

    # Initialize status heartbeat
    total_prompts = len(train_examples) + len(val_examples)
    _init_status(skill_name, total_prompts * max_calls)  # upper bound

    print(f"[GEPA] Optimizing skill: {skill_name}")
    print(f"[GEPA] Seed: {seed[:100]}...")
    print(f"[GEPA] Train: {len(train_examples)}, Val: {len(val_examples)}")
    print(f"[GEPA] Max calls: {max_calls}, Timeout: {INVOCATION_TIMEOUT}s/call")
    print(f"[GEPA] Reflection model: {model}")
    print(f"[GEPA] Using REAL gemini CLI (not API simulator)")
    print(f"[GEPA] Status file: {STATUS_FILE}")
    print()

    config = GEPAConfig(
        engine=EngineConfig(max_metric_calls=max_calls),
        reflection=ReflectionConfig(reflection_lm=model),
    )

    try:
        result = optimize_anything(
            seed_candidate=seed,
            evaluator=evaluator,
            dataset=train_examples,
            valset=val_examples if val_examples else None,
            objective=(
                f"Optimize the YAML description for the '{skill_name}' skill so that "
                f"the Gemini CLI's internal utility_router correctly activates it for "
                f"relevant prompts and does NOT activate it for irrelevant prompts. "
                f"The description should be concise (1-3 sentences), start with "
                f"'Use when...', and contain domain-specific keywords."
            ),
            background=(
                "This description appears in YAML frontmatter of a Gemini CLI skill file. "
                "The CLI uses a lightweight utility_router model (gemini-2.5-flash-lite) "
                "to decide which skill to activate based on the user's prompt. "
                "The description is the ONLY information used for routing. "
                "Skill activation is non-deterministic (~50-70% rate even for good descriptions). "
                "Scores: 1.0=target skill activated, 0.3=wrong skill activated, 0.0=no activation."
            ),
            config=config,
        )
    finally:
        # Always restore the original description
        _write_description(skill_name, original_desc)
        _cleanup_backup(skill_name)
        _update_status(running=False)

    # Extract best score from GEPA result
    best_score = None
    try:
        best_idx = result.best_idx
        if result.val_aggregate_scores and best_idx < len(result.val_aggregate_scores):
            best_score = float(result.val_aggregate_scores[best_idx])
    except (AttributeError, IndexError, TypeError):
        pass

    # Extract all candidate scores for the report
    all_scores = []
    try:
        all_scores = [float(s) for s in result.val_aggregate_scores]
    except (AttributeError, TypeError):
        pass

    output = {
        "skill_name": skill_name,
        "seed_description": seed,
        "best_description": str(result.best_candidate),
        "best_score": best_score,
        "seed_score": float(result.val_aggregate_scores[0]) if result.val_aggregate_scores else None,
        "all_candidate_scores": all_scores,
        "num_candidates": len(result.candidates) if hasattr(result, "candidates") else 0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file = RESULTS_DIR / f"{skill_name}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run GEPA optimization on a Gemini CLI skill description."
    )
    parser.add_argument("--skill", required=True, help="Skill name to optimize")
    parser.add_argument("--data", required=True, help="Path to eval data JSON")
    parser.add_argument("--max-calls", type=int, default=30, help="GEPA budget")
    parser.add_argument("--model", default="gemini/gemini-3-flash-preview")
    parser.add_argument("--apply", action="store_true",
                        help="Write the best description to SKILL.md")
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    output = run_optimization(
        skill_name=args.skill,
        data_file=args.data,
        max_calls=args.max_calls,
        model=args.model,
    )

    print(f"\n[GEPA] Results for {args.skill}:")
    print(f"  Seed:  {output['seed_description'][:100]}...")
    print(f"  Best:  {output['best_description'][:100]}...")
    print(f"  Score: {output['best_score']}")

    if args.apply and output["best_description"] != output["seed_description"]:
        _write_description(args.skill, output["best_description"])
        print(f"  [Applied to SKILL.md]")

    print(f"  Results saved to: {RESULTS_DIR / args.skill}.json")


if __name__ == "__main__":
    main()
