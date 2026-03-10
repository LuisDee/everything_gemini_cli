#!/usr/bin/env python3
"""Improve a skill's body (SKILL.md content) based on eval failures and user feedback.

Analyzes grading results and user feedback to produce specific, actionable
rewrites of the skill's instructions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.gemini_api import call_llm, extract_tag
from scripts.utils import parse_skill_md


def improve_skill(
    skill_name: str,
    skill_content: str,
    grading_results: list[dict],
    user_feedback: list[dict] | None = None,
    comparison_results: list[dict] | None = None,
    model: str = "claude-sonnet",
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    """Generate improved SKILL.md content based on failures and feedback.

    Args:
        skill_name: Name of the skill
        skill_content: Current full SKILL.md content
        grading_results: List of grading.json data from eval runs
        user_feedback: Optional list of {"eval_id": ..., "feedback": ...}
        comparison_results: Optional list of comparison.json data
        model: LLM model to use
        log_dir: Optional directory for logging
        iteration: Iteration number for logging

    Returns:
        Improved SKILL.md content (full file, including frontmatter)
    """
    # Analyze failures across all gradings
    failed_assertions = []
    for grading in grading_results:
        for exp in grading.get("expectations", []):
            if not exp.get("passed"):
                failed_assertions.append({
                    "text": exp.get("text", ""),
                    "evidence": exp.get("evidence", ""),
                })

    # Collect eval feedback suggestions
    eval_suggestions = []
    for grading in grading_results:
        ef = grading.get("eval_feedback", {})
        for s in ef.get("suggestions", []):
            eval_suggestions.append(s.get("reason", ""))

    # Collect user feedback
    feedback_items = []
    if user_feedback:
        for fb in user_feedback:
            if fb.get("feedback", "").strip():
                feedback_items.append(fb["feedback"])

    # Collect comparison insights
    comparison_insights = []
    if comparison_results:
        for comp in comparison_results:
            if comp.get("reasoning"):
                comparison_insights.append(comp["reasoning"])

    prompt = f"""You are improving a Gemini CLI skill called "{skill_name}". Your job is to rewrite the skill's SKILL.md to address specific failures identified during evaluation.

Think step by step about what changes will have the most impact.

Here is the current SKILL.md:
<current_skill>
{skill_content}
</current_skill>

## Failures to Address

### Failed Assertions
"""
    if failed_assertions:
        for fa in failed_assertions[:20]:
            prompt += f'- FAILED: "{fa["text"]}"\n'
            if fa["evidence"]:
                prompt += f'  Evidence: {fa["evidence"][:200]}\n'
    else:
        prompt += "(No assertion failures)\n"

    if feedback_items:
        prompt += "\n### User Feedback\n"
        for fb in feedback_items:
            prompt += f'- "{fb}"\n'

    if eval_suggestions:
        prompt += "\n### Grader Suggestions\n"
        for s in eval_suggestions[:10]:
            prompt += f"- {s}\n"

    if comparison_insights:
        prompt += "\n### Comparison Insights\n"
        for ci in comparison_insights[:5]:
            prompt += f"- {ci[:300]}\n"

    prompt += """

## Guidelines for Improvement

1. **Generalize from failures** -- don't add overly specific rules for individual test cases
2. **Keep it lean** -- remove instructions that aren't pulling their weight
3. **Explain the why** -- help the model understand reasoning, not just rules
4. **Look for patterns** -- if multiple failures share a root cause, address the root cause
5. **Preserve what works** -- don't rewrite parts that are already effective

Please rewrite the complete SKILL.md (including frontmatter) in <improved_skill> tags."""

    response = call_llm(prompt, model=model, max_tokens=8000, temperature=0.5)
    improved = extract_tag(response, "improved_skill")

    # Ensure frontmatter is preserved
    if not improved.startswith("---"):
        # Prepend original frontmatter
        parts = skill_content.split("---", 2)
        if len(parts) >= 3:
            improved = "---" + parts[1] + "---\n\n" + improved

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"improve_skill_iter_{iteration or 'unknown'}.json"
        log_file.write_text(json.dumps({
            "iteration": iteration,
            "prompt": prompt,
            "response": response,
            "improved_length": len(improved),
        }, indent=2))

    return improved


def main():
    parser = argparse.ArgumentParser(description="Improve skill body based on eval failures")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--grading-dir", required=True, help="Directory containing grading.json files")
    parser.add_argument("--feedback", default=None, help="Path to feedback.json")
    parser.add_argument("--model", default="claude-sonnet")
    parser.add_argument("--output", "-o", default=None, help="Output path for improved SKILL.md")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    name, _, content = parse_skill_md(skill_path)

    # Collect grading results
    grading_dir = Path(args.grading_dir)
    grading_results = []
    for gf in grading_dir.rglob("grading.json"):
        try:
            grading_results.append(json.loads(gf.read_text()))
        except json.JSONDecodeError:
            pass

    # Load user feedback
    user_feedback = None
    if args.feedback:
        fb_data = json.loads(Path(args.feedback).read_text())
        user_feedback = fb_data.get("reviews", [])

    improved = improve_skill(
        skill_name=name,
        skill_content=content,
        grading_results=grading_results,
        user_feedback=user_feedback,
        model=args.model,
    )

    if args.output:
        Path(args.output).write_text(improved)
        if args.verbose:
            print(f"Improved skill written to {args.output}", file=sys.stderr)
    else:
        print(improved)


if __name__ == "__main__":
    main()
