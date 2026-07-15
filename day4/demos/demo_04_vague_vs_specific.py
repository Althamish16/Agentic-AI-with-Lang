"""
LIVE DEMO 04 — Vague vs. specific tool description (same code, different docstring).

Goal on screen: prove that tool descriptions ARE prompt engineering. We define
`calc_vague` and `calc_specific` with IDENTICAL implementations but different
docstrings. Run the SAME question twice with the SAME graph, swapping only
which calculator is on the belt. Watch the tool_call JSON change.

    Run A (vague):    docstring says "Do a computation."
                      → model usually skips the tool or mis-picks.
    Run B (specific): docstring names operators + shows examples + says when.
                      → model calls it with a clean expression.

Run:
    python day4/demos/demo_04_vague_vs_specific.py
"""

from __future__ import annotations

from langchain_core.tools import tool

from demo_common import (
    banner,
    build_agent,
    note,
    rule,
    run_agent,
    search_docs,
    step,
    summarize,
    takeaway,
    web_search,
)


# ── Sandboxed evaluator — same body for both tools ───────────────────────────
def _safe_eval(expression: str) -> str:
    """Whitelisted arithmetic evaluator — no builtins, no names, no attribute
    access, just numeric operators. Never use bare eval() on model output."""
    allowed = set("0123456789+-*/(). %")
    if not expression or any(ch not in allowed for ch in expression):
        return f"CALC_REJECTED: {expression!r} contains disallowed characters."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307 — sandboxed
    except Exception as e:  # noqa: BLE001
        return f"CALC_FAILED: {e}"


# ── The two tool variants (same code, different docstring) ───────────────────
@tool
def calc_vague(expression: str) -> str:
    """Do a computation."""
    # ^ Deliberately terrible. The model has no idea WHEN to use this vs.
    #   summarize vs. answering directly. Expect it to be skipped.
    return _safe_eval(expression)


@tool
def calc_specific(expression: str) -> str:
    """Evaluate a numeric arithmetic expression written in Python syntax
    (operators: + - * / % ** and parentheses; digits and decimals only).

    Use this for ANY question that reduces to a number, e.g. "12.5% of 240",
    "(3.14 * 2**2)", "1024 / 8". Pass ONLY the expression, not the word problem.
    Do NOT use for text summarisation or document lookup.
    """
    return _safe_eval(expression)


QUESTION = "What is 256 divided by 4, and then that result times 3?"


def _run(label: str, calc_tool) -> str:
    print(f"\n{'─' * 26} run {label} {'─' * 26}")
    app = build_agent(tools=[search_docs, web_search, summarize, calc_tool])
    return run_agent(app, QUESTION)


def main() -> None:
    banner(
        "DAY 4 · DEMO 4 — Tool description IS prompt engineering",
        "Same function, different docstring, opposite tool-selection behaviour.",
        "run one question with the vague calc, then with the specific one.",
    )

    step("STEP 1 · WHAT WE'RE ASKING", f"Q: {QUESTION!r}")
    note(
        "Both runs have search_docs + web_search + summarize + one calculator. "
        "The ONLY thing that changes is the calculator's docstring."
    )

    step("STEP 2 · RUN A — vague docstring ('Do a computation.')")
    ans_a = _run("A · VAGUE", calc_vague)
    print(f"\nRun A final answer: {ans_a}")

    step("STEP 3 · RUN B — specific docstring (operators, examples, boundaries)")
    ans_b = _run("B · SPECIFIC", calc_specific)
    print(f"\nRun B final answer: {ans_b}")

    rule("═")
    takeaway(
        "The vague tool gets ignored (or wrong-picked); the specific one gets called "
        "with a clean expression. Docstrings are prompts — write them like prompts."
    )


if __name__ == "__main__":
    main()
