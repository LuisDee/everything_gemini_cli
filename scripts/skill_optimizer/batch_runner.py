#!/usr/bin/env python3
"""Batch GEPA runner: processes all pending skills sequentially.

Reads orchestrator-state.json, runs GEPA on each pending skill,
updates state after each completion.

Usage:
    python3 batch_runner.py
    python3 batch_runner.py --max-calls 20
    python3 batch_runner.py --skill api-design  # run single skill
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

STATE_FILE = Path(__file__).parent / "orchestrator-state.json"
EVAL_DATA_DIR = Path(__file__).parent / "eval_data"


def load_state() -> dict:
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    state["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    tmp.rename(STATE_FILE)


def run_skill(skill_name: str, max_calls: int, model: str) -> dict | None:
    """Run GEPA on a single skill. Returns result dict or None on failure."""
    from skill_optimizer.optimizer import run_optimization

    data_file = EVAL_DATA_DIR / f"{skill_name}.json"
    if not data_file.exists():
        print(f"[BATCH] SKIP {skill_name}: no eval data at {data_file}")
        return None

    print(f"\n{'='*60}")
    print(f"[BATCH] Starting: {skill_name}")
    print(f"[BATCH] Time: {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    print(f"{'='*60}\n")

    try:
        result = run_optimization(
            skill_name=skill_name,
            data_file=str(data_file),
            max_calls=max_calls,
            model=model,
        )
        return result
    except Exception as exc:
        print(f"[BATCH] ERROR on {skill_name}: {exc}")
        traceback.print_exc()
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch GEPA runner")
    parser.add_argument("--max-calls", type=int, default=30)
    parser.add_argument("--model", default="gemini/gemini-3-flash-preview")
    parser.add_argument("--skill", default=None, help="Run single skill")
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    state = load_state()

    if args.skill:
        skills_to_run = [args.skill]
    else:
        skills_to_run = [
            name for name, info in state["skills"].items()
            if info["status"] == "pending"
        ]

    total = len(skills_to_run)
    print(f"[BATCH] Skills to process: {total}")
    print(f"[BATCH] Max calls per skill: {args.max_calls}")
    print(f"[BATCH] Model: {args.model}")
    print()

    for i, skill_name in enumerate(skills_to_run, 1):
        state = load_state()  # Re-read in case of external updates

        if state["skills"].get(skill_name, {}).get("status") == "completed":
            print(f"[BATCH] {skill_name} already completed, skipping")
            continue

        state["current_skill"] = skill_name
        state["skills"][skill_name]["status"] = "in_progress"
        state["skills"][skill_name]["attempts"] = state["skills"][skill_name].get("attempts", 0) + 1
        save_state(state)

        result = run_skill(skill_name, args.max_calls, args.model)

        state = load_state()  # Re-read
        if result:
            state["skills"][skill_name]["status"] = "completed"
            state["skills"][skill_name]["best_score"] = result.get("best_score")
            state["skills"][skill_name]["seed_score"] = result.get("seed_score")
            state["skills"][skill_name]["best_description"] = result.get("best_description")
            improved = result.get("best_description") != result.get("seed_description")
            print(f"\n[BATCH] DONE {skill_name} ({i}/{total}): seed={result.get('seed_score')} best={result.get('best_score')} {'IMPROVED' if improved else 'SAME'}")
        else:
            attempts = state["skills"][skill_name].get("attempts", 0)
            if attempts >= 3:
                state["skills"][skill_name]["status"] = "skipped"
                state["skills"][skill_name]["skip_reason"] = "failed 3 times"
                print(f"\n[BATCH] SKIPPED {skill_name} ({i}/{total}): failed {attempts} times")
            else:
                state["skills"][skill_name]["status"] = "pending"
                print(f"\n[BATCH] RETRY LATER {skill_name} ({i}/{total}): attempt {attempts}")

        save_state(state)

    # Final summary
    state = load_state()
    completed = sum(1 for s in state["skills"].values() if s["status"] == "completed")
    skipped = sum(1 for s in state["skills"].values() if s["status"] == "skipped")
    pending = sum(1 for s in state["skills"].values() if s["status"] == "pending")
    print(f"\n{'='*60}")
    print(f"[BATCH] FINAL: completed={completed}, skipped={skipped}, pending={pending}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
