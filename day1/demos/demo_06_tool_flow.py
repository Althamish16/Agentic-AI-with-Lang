"""
LIVE DEMO — Slide 6: "Tool Calling Flow" (the 6 steps, end to end)

Goal on screen: trace ONE request through all six steps, printing the actual
structured tool call the model emits so people see it's just a filled-in form
that OUR code executes.

    1 User asks · 2 LLM decides · 3 Tool request emitted · 4 App executes ·
    5 Result returned · 6 LLM responds

Different domain from Slide 5 (a database query, not weather) so the two demos
don't blur together.

Run:
    python day1/demos/demo_06_tool_flow.py
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD
from config import get_llm


# ── The tool: a (mock) read-only database query ──────────────────────────────
@tool
def count_orders(order_date: str) -> int:
    """Return how many orders were placed on a given date (YYYY-MM-DD)."""
    # Pretend this runs `SELECT COUNT(*) FROM orders WHERE date = ?` safely.
    fake_db = {"2026-07-04": 1284, "2026-07-05": 991}
    return fake_db.get(order_date, 0)


QUESTION = "How many orders did we get on 2026-07-04?"


def main() -> None:
    banner(
        "SLIDE 6 · Tool Calling Flow",
        "The same six steps run every time a tool is involved.",
        f'"{QUESTION}" traced through all 6 steps.',
    )

    llm = get_llm(temperature=None).bind_tools([count_orders])

    # ── STEP 1 ──────────────────────────────────────────────────────────────
    step("STEP 1 · USER ASKS")
    result(QUESTION)
    messages = [HumanMessage(QUESTION)]

    # ── STEP 2 ──────────────────────────────────────────────────────────────
    step("STEP 2 · LLM DECIDES a tool is needed")
    ai = llm.invoke(messages)
    messages.append(ai)
    if not ai.tool_calls:
        result(f"Model answered without a tool: {ai.content.strip()}")
        return
    note("The model chose to call a tool instead of answering from memory.")

    # ── STEP 3 ──────────────────────────────────────────────────────────────
    call = ai.tool_calls[0]
    step("STEP 3 · TOOL REQUEST — structured call emitted")
    print(f"  {BOLD}This is exactly what the model produced (JSON):{RESET}")
    result(json.dumps({"name": call["name"], "args": call["args"], "id": call["id"]}, indent=2))
    note("It's a filled-in form, not executed code. The model can't run anything itself.")

    # ── STEP 4 ──────────────────────────────────────────────────────────────
    step("STEP 4 · APP EXECUTES the tool safely")
    observation = count_orders.invoke(call["args"])
    result(f"our code ran count_orders({call['args']!r})  →  {observation}")

    # ── STEP 5 ──────────────────────────────────────────────────────────────
    step("STEP 5 · RESULT RETURNED into the prompt")
    tool_msg = ToolMessage(content=str(observation), tool_call_id=call["id"])
    messages.append(tool_msg)
    note(f"We append a tool message (id={call['id'][:12]}…) so the model can read the result.")

    # ── STEP 6 ──────────────────────────────────────────────────────────────
    step("STEP 6 · LLM RESPONDS — final answer generated")
    final = llm.invoke(messages)
    result(f"Model: {final.content.strip()}")

    takeaway("Steps 3 and 5 are the model. Step 4 — where the real work and safety live — is your code.")


if __name__ == "__main__":
    main()
