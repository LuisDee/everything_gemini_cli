"""Baseline manager for A/B testing skills.

Disables/enables skills by renaming SKILL.md for baseline (without-skill) runs.
Uses a context manager with try/finally for crash safety.
"""

from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SKILLS_DIR = Path.home() / ".gemini" / "skills"
DISABLED_SUFFIX = ".SKILL.md.forge-disabled"


@contextmanager
def skill_disabled(skill_name: str) -> Iterator[None]:
    """Context manager that temporarily disables a skill.

    Renames SKILL.md -> .SKILL.md.forge-disabled so the Gemini CLI
    won't discover the skill during baseline runs.

    Usage:
        with skill_disabled("my-skill"):
            # run baseline evaluation here
            pass
    """
    skill_dir = SKILLS_DIR / skill_name
    skill_md = skill_dir / "SKILL.md"
    disabled_path = skill_dir / DISABLED_SUFFIX

    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_md}")

    # Disable
    skill_md.rename(disabled_path)
    try:
        yield
    finally:
        # Re-enable (crash-safe)
        if disabled_path.exists():
            disabled_path.rename(skill_md)


def recover_all() -> list[str]:
    """Scan all skills for orphaned .forge-disabled files and restore them.

    Call on startup to recover from crashes during baseline runs.
    Returns list of recovered skill names.
    """
    recovered = []
    if not SKILLS_DIR.exists():
        return recovered

    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        disabled_path = skill_dir / DISABLED_SUFFIX
        skill_md = skill_dir / "SKILL.md"
        if disabled_path.exists() and not skill_md.exists():
            disabled_path.rename(skill_md)
            recovered.append(skill_dir.name)
            print(f"[RECOVERY] Restored {skill_dir.name} from forge-disabled state")

    return recovered


def is_disabled(skill_name: str) -> bool:
    """Check if a skill is currently disabled by skill-forge."""
    disabled_path = SKILLS_DIR / skill_name / DISABLED_SUFFIX
    return disabled_path.exists()
