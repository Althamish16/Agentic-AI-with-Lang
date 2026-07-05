"""
pretty.py — tiny console helpers so learners can SEE the agent's state change.

Teaching goal: from Day 3 on, the loop between graph nodes should be visible.
These helpers print state snapshots with clear separators.
"""

from __future__ import annotations

import json
from typing import Any

# ANSI colors (fall back gracefully if the terminal ignores them)
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def rule(char: str = "─", width: int = 74) -> None:
    print(char * width)


def banner(title: str) -> None:
    rule("═")
    print(f"{BOLD}{title}{RESET}")
    rule("═")


def node(name: str, note: str = "") -> None:
    """Announce which node is running."""
    tail = f" {DIM}{note}{RESET}" if note else ""
    print(f"\n{CYAN}▶ NODE: {BOLD}{name}{RESET}{tail}")


def _shorten(value: Any, limit: int = 300) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f" …(+{len(value) - limit} chars)"
    if isinstance(value, list):
        return [_shorten(v, limit) for v in value]
    if isinstance(value, dict):
        return {k: _shorten(v, limit) for k, v in value.items()}
    return value


def print_state(state: dict, keys: list[str] | None = None, title: str = "STATE") -> None:
    """Pretty-print (a subset of) the graph state so the loop is legible."""
    shown = {k: state.get(k) for k in keys} if keys else dict(state)
    print(f"{YELLOW}  {title}:{RESET}")
    try:
        text = json.dumps(_shorten(shown), indent=2, default=str)
    except TypeError:
        text = str(_shorten(shown))
    for line in text.splitlines():
        print(f"  {line}")


def ok(msg: str) -> None:
    print(f"{GREEN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠ {msg}{RESET}")
