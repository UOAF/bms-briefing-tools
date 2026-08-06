from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "bms-briefing-planner"


def read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8-sig")


def load_skill_prompt() -> str:
    """Load the reusable skill as policy/context for local or remote LLMs."""
    parts = [
        read_text_if_exists(SKILL_DIR / "SKILL.md"),
        read_text_if_exists(SKILL_DIR / "references" / "workflow.md"),
        read_text_if_exists(SKILL_DIR / "references" / "brief-criteria.md"),
        read_text_if_exists(SKILL_DIR / "references" / "image-qa.md"),
    ]
    return "\n\n---\n\n".join(part for part in parts if part)
