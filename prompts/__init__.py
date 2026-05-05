"""Prompt loader utility for loading agent prompts from files."""

import os
from typing import Optional
from pathlib import Path


# Get the prompts directory (where this __init__.py file lives)
PROMPTS_DIR = Path(__file__).parent


def load_prompt(agent_name: str) -> str:
    """
    Load a prompt for the specified agent.
    Prefers <agent>.md over <agent>.txt so markdown files take precedence.

    Raises:
        FileNotFoundError: if neither file exists.
    """
    name = agent_name.lower()
    for ext in (".md", ".txt"):
        path = PROMPTS_DIR / f"{name}{ext}"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    raise FileNotFoundError(
        f"No prompt file found for agent '{agent_name}' in {PROMPTS_DIR}"
    )


def get_prompt(agent_name: str, default: Optional[str] = None) -> str:
    """Return the prompt for agent_name, or default if no file exists."""
    try:
        return load_prompt(agent_name)
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def get_all_prompts() -> dict:
    """Load all available prompts (md preferred over txt)."""
    prompts: dict = {}
    if not PROMPTS_DIR.exists():
        return prompts
    seen: set = set()
    for ext in ("*.md", "*.txt"):
        for path in PROMPTS_DIR.glob(ext):
            if path.stem not in seen and path.stem != "__init__":
                prompts[path.stem] = load_prompt(path.stem)
                seen.add(path.stem)
    return prompts
