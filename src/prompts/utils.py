from __future__ import annotations
from pathlib import Path

PROMPT_DIR = Path(__file__).parent

class PromptNotFound(Exception):
    pass

def load_prompt(name: str) -> str:
    """
    Load a .txt prompt from src/prompts/.
    Raises PromptNotFound if the file is missing.
    """
    p = PROMPT_DIR / name
    if not p.exists():
        raise PromptNotFound(f"Prompt file not found: {p}")
    return p.read_text(encoding="utf-8")
