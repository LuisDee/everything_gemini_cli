"""Shared utilities for skill-forge scripts."""

from __future__ import annotations

import json
import yaml
from pathlib import Path

SKILLS_DIR = Path.home() / ".gemini" / "skills"
HOOK_LOG = Path("/tmp/gemini-skill-activations.log")


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content).

    Handles YAML multiline indicators (>, |, >-, |-).
    """
    content = (skill_path / "SKILL.md").read_text()
    lines = content.split("\n")

    if lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("SKILL.md missing frontmatter (no closing ---)")

    name = ""
    description = ""
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if line.startswith("name:"):
            name = line[len("name:"):].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:"):].strip()
            if value in (">", "|", ">-", "|-"):
                continuation_lines: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (
                    frontmatter_lines[i].startswith("  ")
                    or frontmatter_lines[i].startswith("\t")
                ):
                    continuation_lines.append(frontmatter_lines[i].strip())
                    i += 1
                description = " ".join(continuation_lines)
                continue
            else:
                description = value.strip('"').strip("'")
        i += 1

    return name, description, content


def write_description(skill_name: str, description: str) -> None:
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


def read_hook_log() -> list[dict]:
    """Read all JSON lines from the hook activation log."""
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


def clear_hook_log() -> None:
    """Truncate the hook log file."""
    try:
        HOOK_LOG.write_text("")
    except OSError:
        pass


def normalize_eval_data(data: list[dict] | dict) -> list[dict]:
    """Normalize eval data to a flat list of eval items.

    Accepts either:
    - A list of {"query": ..., "should_trigger": ...} dicts
    - A dict with "train" and/or "val" keys (GEPA format)
    """
    if isinstance(data, list):
        return data
    items = []
    if "train" in data:
        items.extend(data["train"])
    if "val" in data:
        items.extend(data["val"])
    return items
