#!/usr/bin/env python3
"""Unified optimization loop for skill descriptions.

Combines trigger eval and description improvement in a loop, tracking
history and returning the best description found. Supports train/test
split to prevent overfitting.

Dual mode:
  --mode describe: Optimize the description (trigger accuracy)
  --mode improve:  Optimize the skill body (output quality)
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

from scripts.generate_report import generate_html
from scripts.improve_description import improve_description
from scripts.run_trigger_eval import run_trigger_eval
from scripts.utils import SKILLS_DIR, parse_skill_md, write_description


def split_eval_set(
    eval_set: list[dict], holdout: float, seed: int = 42
) -> tuple[list[dict], list[dict]]:
    """Split eval set into train/test, stratified by should_trigger."""
    random.seed(seed)

    trigger = [e for e in eval_set if e.get("should_trigger", True)]
    no_trigger = [e for e in eval_set if not e.get("should_trigger", True)]

    random.shuffle(trigger)
    random.shuffle(no_trigger)

    n_trigger_test = max(1, int(len(trigger) * holdout)) if trigger else 0
    n_no_trigger_test = max(1, int(len(no_trigger) * holdout)) if no_trigger else 0

    test_set = trigger[:n_trigger_test] + no_trigger[:n_no_trigger_test]
    train_set = trigger[n_trigger_test:] + no_trigger[n_no_trigger_test:]

    return train_set, test_set


def run_loop(
    eval_set: list[dict],
    skill_path: Path,
    description_override: str | None,
    max_iterations: int,
    runs_per_query: int,
    holdout: float,
    model: str,
    verbose: bool,
    live_report_path: Path | None = None,
    log_dir: Path | None = None,
    timeout: int = 180,
) -> dict:
    """Run the eval + improvement loop."""
    name, original_description, content = parse_skill_md(skill_path)
    current_description = description_override or original_description

    # Backup original description for crash recovery
    backup_path = skill_path / ".SKILL.md.forge-backup"
    shutil.copy2(skill_path / "SKILL.md", backup_path)

    # Split into train/test
    if holdout > 0:
        train_set, test_set = split_eval_set(eval_set, holdout)
        if verbose:
            print(
                f"Split: {len(train_set)} train, {len(test_set)} test (holdout={holdout})",
                file=sys.stderr,
            )
    else:
        train_set = eval_set
        test_set = []

    history = []
    exit_reason = "unknown"

    try:
        for iteration in range(1, max_iterations + 1):
            if verbose:
                print(f"\n{'='*60}", file=sys.stderr)
                print(f"Iteration {iteration}/{max_iterations}", file=sys.stderr)
                print(f"Description: {current_description[:80]}...", file=sys.stderr)

            # Write current description to SKILL.md
            write_description(name, current_description)

            # Evaluate train + test together
            all_queries = train_set + test_set
            t0 = time.time()
            all_results = run_trigger_eval(
                eval_set=all_queries,
                skill_name=name,
                description=current_description,
                runs_per_query=runs_per_query,
                timeout=timeout,
            )
            eval_elapsed = time.time() - t0

            # Split results back into train/test
            train_queries_set = {q.get("query", q.get("prompt", "")) for q in train_set}
            train_result_list = [
                r for r in all_results["results"] if r["query"] in train_queries_set
            ]
            test_result_list = [
                r for r in all_results["results"] if r["query"] not in train_queries_set
            ]

            train_passed = sum(1 for r in train_result_list if r["pass"])
            train_total = len(train_result_list)
            train_summary = {
                "passed": train_passed,
                "failed": train_total - train_passed,
                "total": train_total,
            }
            train_results = {"results": train_result_list, "summary": train_summary}

            if test_set:
                test_passed = sum(1 for r in test_result_list if r["pass"])
                test_total = len(test_result_list)
                test_summary = {
                    "passed": test_passed,
                    "failed": test_total - test_passed,
                    "total": test_total,
                }
                test_results = {"results": test_result_list, "summary": test_summary}
            else:
                test_results = None
                test_summary = None

            history.append({
                "iteration": iteration,
                "description": current_description,
                "train_passed": train_summary["passed"],
                "train_failed": train_summary["failed"],
                "train_total": train_summary["total"],
                "train_results": train_results["results"],
                "test_passed": test_summary["passed"] if test_summary else None,
                "test_failed": test_summary["failed"] if test_summary else None,
                "test_total": test_summary["total"] if test_summary else None,
                "test_results": test_results["results"] if test_results else None,
                # Backward compat
                "passed": train_summary["passed"],
                "failed": train_summary["failed"],
                "total": train_summary["total"],
                "results": train_results["results"],
            })

            # Write live report
            if live_report_path:
                partial_output = {
                    "original_description": original_description,
                    "best_description": current_description,
                    "best_score": "in progress",
                    "iterations_run": len(history),
                    "holdout": holdout,
                    "train_size": len(train_set),
                    "test_size": len(test_set),
                    "history": history,
                }
                live_report_path.write_text(
                    generate_html(partial_output, auto_refresh=True, skill_name=name)
                )

            if verbose:
                print(
                    f"Train: {train_passed}/{train_total} passed ({eval_elapsed:.1f}s)",
                    file=sys.stderr,
                )
                if test_summary:
                    print(
                        f"Test:  {test_summary['passed']}/{test_summary['total']} passed",
                        file=sys.stderr,
                    )

            if train_summary["failed"] == 0:
                exit_reason = f"all_passed (iteration {iteration})"
                if verbose:
                    print(f"\nAll train queries passed!", file=sys.stderr)
                break

            if iteration == max_iterations:
                exit_reason = f"max_iterations ({max_iterations})"
                break

            # Improve description
            if verbose:
                print(f"\nImproving description...", file=sys.stderr)

            # Blind history (strip test scores)
            blinded_history = [
                {k: v for k, v in h.items() if not k.startswith("test_")}
                for h in history
            ]
            new_description = improve_description(
                skill_name=name,
                skill_content=content,
                current_description=current_description,
                eval_results=train_results,
                history=blinded_history,
                model=model,
                log_dir=log_dir,
                iteration=iteration,
            )

            if verbose:
                print(f"Proposed: {new_description[:80]}...", file=sys.stderr)

            current_description = new_description

    finally:
        # Restore original description
        write_description(name, original_description)
        backup_path.unlink(missing_ok=True)

    # Find best iteration by test score (or train if no test set)
    if test_set:
        best = max(history, key=lambda h: h["test_passed"] or 0)
        best_score = f"{best['test_passed']}/{best['test_total']}"
    else:
        best = max(history, key=lambda h: h["train_passed"])
        best_score = f"{best['train_passed']}/{best['train_total']}"

    if verbose:
        print(f"\nExit reason: {exit_reason}", file=sys.stderr)
        print(f"Best score: {best_score} (iteration {best['iteration']})", file=sys.stderr)

    return {
        "exit_reason": exit_reason,
        "original_description": original_description,
        "best_description": best["description"],
        "best_score": best_score,
        "best_train_score": f"{best['train_passed']}/{best['train_total']}",
        "best_test_score": f"{best['test_passed']}/{best['test_total']}" if test_set else None,
        "final_description": current_description,
        "iterations_run": len(history),
        "holdout": holdout,
        "train_size": len(train_set),
        "test_size": len(test_set),
        "history": history,
    }


def main():
    parser = argparse.ArgumentParser(description="Run eval + improve loop")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override starting description")
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--runs-per-query", type=int, default=1)
    parser.add_argument("--holdout", type=float, default=0.4)
    parser.add_argument("--model", default="claude-sonnet")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout per query")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--report", default="auto",
        help="HTML report path ('auto' for temp file, 'none' to disable)",
    )
    parser.add_argument("--results-dir", default=None, help="Save outputs here")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, _, _ = parse_skill_md(skill_path)

    # Set up live report
    if args.report != "none":
        if args.report == "auto":
            ts = time.strftime("%Y%m%d_%H%M%S")
            live_report_path = Path(tempfile.gettempdir()) / f"skill_desc_report_{name}_{ts}.html"
        else:
            live_report_path = Path(args.report)
        live_report_path.write_text(
            "<html><body><h1>Starting optimization...</h1>"
            "<meta http-equiv='refresh' content='5'></body></html>"
        )
        webbrowser.open(str(live_report_path))
    else:
        live_report_path = None

    results_dir = None
    if args.results_dir:
        ts = time.strftime("%Y-%m-%d_%H%M%S")
        results_dir = Path(args.results_dir) / ts
        results_dir.mkdir(parents=True, exist_ok=True)

    log_dir = results_dir / "logs" if results_dir else None

    output = run_loop(
        eval_set=eval_set,
        skill_path=skill_path,
        description_override=args.description,
        max_iterations=args.max_iterations,
        runs_per_query=args.runs_per_query,
        holdout=args.holdout,
        model=args.model,
        verbose=args.verbose,
        live_report_path=live_report_path,
        log_dir=log_dir,
        timeout=args.timeout,
    )

    json_output = json.dumps(output, indent=2)
    print(json_output)

    if results_dir:
        (results_dir / "results.json").write_text(json_output)
    if live_report_path:
        live_report_path.write_text(generate_html(output, auto_refresh=False, skill_name=name))
        print(f"\nReport: {live_report_path}", file=sys.stderr)
    if results_dir and live_report_path:
        (results_dir / "report.html").write_text(
            generate_html(output, auto_refresh=False, skill_name=name)
        )


if __name__ == "__main__":
    main()
