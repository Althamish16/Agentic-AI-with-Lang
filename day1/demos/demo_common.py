"""
demo_common.py — tiny presentation helpers shared by the Day 1 LIVE DEMOS.

Purpose: keep each demo file focused on its ONE concept, while every demo opens
with the same clear, boxed header (so during the session it's obvious which
slide / concept is on screen) and prints steps + results in a consistent style.

Importing this module also imports `config`, which reconfigures the Windows
console for UTF-8 + ANSI colors — so the box-drawing characters and colors below
render correctly on the instructor's machine.
"""

from __future__ import annotations

import pathlib
import sys
import textwrap

# Make the repo root importable so `config` resolves no matter the CWD, and so
# `import demo_common` works when a demo is launched from the repo root.
_THIS_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))                     # for `import demo_common`
sys.path.insert(0, str(_THIS_DIR.parents[1]))          # repo root -> `import config`

import config  # noqa: E402,F401  (imported for its console/UTF-8/ANSI setup side effects)

# ── ANSI colors (config enabled virtual-terminal processing on Windows) ──────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

_WIDTH = 74            # total box width
_INNER = _WIDTH - 4    # text area inside "║  ... ║"


def _wrap(text: str) -> list[str]:
    """Wrap one logical line to the box's inner width."""
    if not text:
        return [""]
    return textwrap.wrap(text, width=_INNER) or [""]


def banner(slide: str, title: str, demo: str) -> None:
    """Print the big header every demo starts with.

    slide  e.g. "SLIDE 2 · What is an LLM?"
    title  the concept in a few words
    demo   one line describing what this script will show live
    """
    top = "╔" + "═" * (_WIDTH - 2) + "╗"
    bot = "╚" + "═" * (_WIDTH - 2) + "╝"
    sep = "╟" + "─" * (_WIDTH - 2) + "╢"

    def row(text: str, style: str = "") -> str:
        pad = text.ljust(_INNER)
        return f"║ {style}{pad}{RESET if style else ''} ║"

    print()
    print(CYAN + top + RESET)
    for line in _wrap(slide):
        print(CYAN + "║" + RESET + f" {BOLD}{line.ljust(_INNER)}{RESET} " + CYAN + "║" + RESET)
    print(CYAN + sep + RESET)
    for line in _wrap(title):
        print(CYAN + "║" + RESET + f" {line.ljust(_INNER)} " + CYAN + "║" + RESET)
    for line in _wrap("Live demo: " + demo):
        print(CYAN + "║" + RESET + f" {DIM}{line.ljust(_INNER)}{RESET} " + CYAN + "║" + RESET)
    print(CYAN + bot + RESET)
    print()


def step(label: str, desc: str = "") -> None:
    """A labeled step marker, e.g.  ▶ STEP 3 · TOOL REQUEST"""
    line = f"{YELLOW}{BOLD}▶ {label}{RESET}"
    if desc:
        line += f"  {DIM}{desc}{RESET}"
    print("\n" + line)


def note(text: str) -> None:
    """A dim, indented explanatory aside (teaching narration)."""
    for line in textwrap.wrap(text, width=_WIDTH):
        print(f"  {DIM}{line}{RESET}")


def result(text: str) -> None:
    """Highlight a model/tool result in green."""
    print(f"  {GREEN}{text}{RESET}")


def takeaway(text: str) -> None:
    """The one-line 'so what' to say out loud before moving to the next slide."""
    print(f"\n{MAGENTA}{BOLD}➜ Takeaway:{RESET} {MAGENTA}{text}{RESET}\n")
