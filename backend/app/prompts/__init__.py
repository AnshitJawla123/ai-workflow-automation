"""Versioned prompt registry. Each prompt has a markdown source for docs and a
loader for runtime substitution.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict

PROMPTS_DIR = Path(__file__).parent


def load(name: str) -> str:
    p = PROMPTS_DIR / f"{name}.md"
    return p.read_text(encoding="utf-8")


def render(name: str, **kwargs) -> str:
    tpl = load(name)
    for k, v in kwargs.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    return tpl


def all_prompts() -> Dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in PROMPTS_DIR.glob("*.md")}
