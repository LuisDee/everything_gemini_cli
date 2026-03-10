#!/usr/bin/env python3
"""Improve a skill description based on eval results.

Takes eval results and generates an improved description using LLM
with chain-of-thought reasoning (Gemini equivalent of extended thinking).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.gemini_api import call_llm, extract_tag
from scripts.utils import parse_skill_md


def improve_description(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    model: str = "claude-sonnet",
    test_results: dict | None = None,
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    """Call LLM to improve the description based on eval results."""
    failed_triggers = [
        r for r in eval_results["results"]
        if r["should_trigger"] and not r["pass"]
    ]
    false_triggers = [
        r for r in eval_results["results"]
        if not r["should_trigger"] and not r["pass"]
    ]

    # Build scores summary
    train_score = f"{eval_results['summary']['passed']}/{eval_results['summary']['total']}"
    if test_results:
        test_score = f"{test_results['summary']['passed']}/{test_results['summary']['total']}"
        scores_summary = f"Train: {train_score}, Test: {test_score}"
    else:
        scores_summary = f"Train: {train_score}"

    prompt = f"""You are optimizing a skill description for a Gemini CLI skill called "{skill_name}". A "skill" is a prompt with progressive disclosure -- there's a name and description that Gemini sees when deciding whether to activate the skill, and then if activated, it reads the SKILL.md which has detailed instructions.

The description appears in Gemini's internal skill list. When a user sends a query, Gemini's utility_router decides whether to activate the skill based solely on this description. Your goal is to write a description that triggers for relevant queries and doesn't trigger for irrelevant ones.

Think step by step about what patterns distinguish the successful triggers from the failures.

Here's the current description:
<current_description>
"{current_description}"
</current_description>

Current scores ({scores_summary}):
<scores_summary>
"""
    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have triggered but didn't):\n"
        for r in failed_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if false_triggers:
        prompt += "FALSE TRIGGERS (triggered but shouldn't have):\n"
        for r in false_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if history:
        prompt += "PREVIOUS ATTEMPTS (do NOT repeat these -- try something structurally different):\n\n"
        for h in history:
            train_s = f"{h.get('train_passed', h.get('passed', 0))}/{h.get('train_total', h.get('total', 0))}"
            test_s = f"{h.get('test_passed', '?')}/{h.get('test_total', '?')}" if h.get("test_passed") is not None else None
            score_str = f"train={train_s}" + (f", test={test_s}" if test_s else "")
            prompt += f'<attempt {score_str}>\n'
            prompt += f'Description: "{h["description"]}"\n'
            if "results" in h:
                prompt += "Train results:\n"
                for r in h["results"]:
                    status = "PASS" if r["pass"] else "FAIL"
                    prompt += f'  [{status}] "{r["query"][:80]}" (triggered {r["triggers"]}/{r["runs"]})\n'
            prompt += "</attempt>\n\n"

    prompt += f"""</scores_summary>

Skill content (for context on what the skill does):
<skill_content>
{skill_content[:3000]}
</skill_content>

Based on the failures, write a new description. Don't overfit to specific queries -- generalize from failures to broader categories of user intent. Keep it under 200 words. Use "Use when..." phrasing.

Tips:
- Focus on user intent, not implementation details
- Make it distinctive so it doesn't compete with other skills
- Be creative and try different structures each iteration
- Include domain-specific keywords that match user queries

Respond with only the new description in <new_description> tags."""

    response = call_llm(prompt, model=model, max_tokens=2000, temperature=0.7)
    description = extract_tag(response, "new_description")

    # Log the transcript
    transcript: dict = {
        "iteration": iteration,
        "prompt": prompt,
        "response": response,
        "parsed_description": description,
        "char_count": len(description),
        "over_limit": len(description) > 1024,
    }

    # If over 1024 chars, ask the model to shorten
    if len(description) > 1024:
        shorten_prompt = (
            f"Your description is {len(description)} characters, which exceeds "
            f"the 1024 character limit. Rewrite it under 1024 characters while "
            f"preserving the most important trigger words. "
            f"Respond with only the description in <new_description> tags."
        )
        shorten_response = call_llm(
            shorten_prompt, model=model, max_tokens=2000, temperature=0.5
        )
        shortened = extract_tag(shorten_response, "new_description")
        transcript["rewrite_response"] = shorten_response
        transcript["rewrite_description"] = shortened
        description = shortened

    transcript["final_description"] = description

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"improve_iter_{iteration or 'unknown'}.json"
        log_file.write_text(json.dumps(transcript, indent=2))

    return description


def main():
    parser = argparse.ArgumentParser(description="Improve a skill description")
    parser.add_argument("--eval-results", required=True, help="Eval results JSON path")
    parser.add_argument("--skill-path", required=True, help="Skill directory path")
    parser.add_argument("--history", default=None, help="History JSON path")
    parser.add_argument("--model", default="claude-sonnet", help="Model for improvement")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md at {skill_path}", file=sys.stderr)
        sys.exit(1)

    eval_results = json.loads(Path(args.eval_results).read_text())
    history = json.loads(Path(args.history).read_text()) if args.history else []

    name, _, content = parse_skill_md(skill_path)
    current_description = eval_results["description"]

    new_description = improve_description(
        skill_name=name,
        skill_content=content,
        current_description=current_description,
        eval_results=eval_results,
        history=history,
        model=args.model,
    )

    if args.verbose:
        print(f"Improved: {new_description}", file=sys.stderr)

    output = {
        "description": new_description,
        "history": history + [{
            "description": current_description,
            "passed": eval_results["summary"]["passed"],
            "failed": eval_results["summary"]["failed"],
            "total": eval_results["summary"]["total"],
            "results": eval_results["results"],
        }],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
