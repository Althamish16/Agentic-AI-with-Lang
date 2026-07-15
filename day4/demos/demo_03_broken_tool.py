"""
LIVE DEMO 03 — Deliberately break web_search, watch the agent recover.

Goal on screen: prove that tool errors returned as STRINGS keep the loop alive.
We flip a global toggle so web_search raises internally; its try/except turns
the exception into the string "SEARCH_FAILED: ...". The model reads that string
on the next turn and pivots (usually to search_docs or to answering from its
own knowledge) instead of crashing.

    Rule of the day: never let a tool raise into the loop. Return a readable
                     error string so the model can *react* to it.

Run:
    python day4/demos/demo_03_broken_tool.py
"""

from __future__ import annotations

import demo_common as dc
from demo_common import banner, build_agent, note, rule, run_agent, step, takeaway, warn

# A question the model is likely to try web_search for FIRST (current-events flavor).
QUESTION = "What's the latest news on vector database benchmarks in 2026?"


def main() -> None:
    banner(
        "DAY 4 · DEMO 3 — Broken tool → graceful recovery",
        "Errors returned as strings keep the agent loop alive.",
        "flip a global toggle to force web_search to fail, then run the graph.",
    )

    step("STEP 1 · FORCE THE PROVIDER TO FAIL", "toggle FAIL_WEB_SEARCH = True")
    dc.FAIL_WEB_SEARCH = True
    warn("web_search will now return 'SEARCH_FAILED: ...' instead of real results.")
    note(
        "Look at demo_common.web_search — the try/except is doing the work. "
        "If we let RuntimeError escape, ToolNode would surface it and (without "
        "handle_tool_errors=True) the graph would crash."
    )

    try:
        step("STEP 2 · RUN THE GRAPH", f"Q: {QUESTION!r}")
        app = build_agent()
        answer = run_agent(app, QUESTION)

        rule("═")
        print("FINAL ANSWER (agent recovered without crashing):\n")
        print(answer)
    finally:
        dc.FAIL_WEB_SEARCH = False  # always restore, even on error

    takeaway(
        "The model saw 'SEARCH_FAILED: ...' as ordinary tool output and adapted. "
        "That is the difference between a crash and graceful recovery."
    )


if __name__ == "__main__":
    main()
