"""Prompt loader utility for loading agent prompts from files."""

import os
from typing import Optional
from pathlib import Path


# Get the prompts directory (where this __init__.py file lives)
PROMPTS_DIR = Path(__file__).parent


def load_prompt(agent_name: str) -> str:
    """
    Load a prompt from a text file for the specified agent.
    
    Args:
        agent_name: Name of the agent (e.g., 'orchestrator', 'analyst', 'coder')
    
    Returns:
        The prompt text content
    
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_file = PROMPTS_DIR / f"{agent_name.lower()}.txt"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def get_prompt(agent_name: str, default: Optional[str] = None) -> str:
    """
    Get a prompt for the specified agent, with optional default fallback.
    
    Args:
        agent_name: Name of the agent
        default: Default prompt to return if file not found
    
    Returns:
        The prompt text content or default
    """
    try:
        return load_prompt(agent_name)
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def get_all_prompts() -> dict:
    """
    Load all available prompts from the prompts directory.
    
    Returns:
        Dictionary mapping agent names to their prompts
    """
    prompts = {}
    
    if not PROMPTS_DIR.exists():
        return prompts
    
    for prompt_file in PROMPTS_DIR.glob("*.txt"):
        agent_name = prompt_file.stem
        prompts[agent_name] = load_prompt(agent_name)
    
    return prompts
