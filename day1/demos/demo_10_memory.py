"""
LIVE DEMO — Slide 10: "Memory: Context Beyond One Prompt"

Goal on screen: all five memory types from the slide, each shown doing its job —
and the punchline that they are ALL one trick: choosing what to put back into
the next prompt.

  1. SHORT-TERM  — "make it shorter" works only if the conversation is resent
  2. LONG-TERM   — a preference saved to disk survives a brand-new session
  3. SEMANTIC    — facts the model already knows (no context needed)
  4. EPISODIC    — past interactions injected → "book the usual" resolves
  5. WORKING     — the scratchpad an agent keeps while a task is in flight

Run:
    python day1/demos/demo_10_memory.py
"""

from __future__ import annotations

import json
import pathlib

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD
from config import get_llm

# Long-term memory lives OUTSIDE the model — here, a tiny JSON file on disk.
STORE = pathlib.Path(__file__).resolve().parent / ".memory_store.json"


def short_term(llm) -> None:
    step("1 · SHORT-TERM — the current conversation")
    r1 = llm.invoke([HumanMessage("Draft a one-line apology email to a customer named Sam "
                                  "whose delivery was late.")])
    draft = r1.content.strip()
    result(f'Model: "{draft}"')

    note('Follow-up WITH history resent ("make it shorter" — it knows what "it" is):')
    r2 = llm.invoke(
        [
            HumanMessage("Draft a one-line apology email to a customer named Sam whose delivery was late."),
            AIMessage(draft),
            HumanMessage("Make it shorter."),
        ]
    )
    result(f'Model: "{r2.content.strip()}"')

    note("Same follow-up WITHOUT history (a fresh request):")
    r3 = llm.invoke([HumanMessage("Make it shorter.")])
    result(f'Model: "{r3.content.strip()}"')
    note("Short-term memory IS the resent message list. Drop it and 'it' means nothing.")


def long_term(llm) -> None:
    step("2 · LONG-TERM — stored preferences that survive sessions")

    note("SESSION 1 — the user mentions a preference; the APP saves it to disk:")
    print(f'    {DIM}user: "By the way, I\'m vegetarian, and I like casual places."{RESET}')
    STORE.write_text(json.dumps({"diet": "vegetarian", "style": "casual"}), encoding="utf-8")
    result(f"saved → {STORE.name}: {STORE.read_text(encoding='utf-8')}")
    note("(Real systems use an LLM to extract facts worth keeping — the storage idea is the same.)")

    note("SESSION 2 (brand-new conversation) — WITHOUT loading the store:")
    q = "Suggest one type of restaurant for my team dinner tonight. One sentence."
    r1 = llm.invoke([HumanMessage(q)])
    result(f'Model: "{r1.content.strip()}"')

    note("SESSION 2 again — the app loads the store and injects it into the system prompt:")
    prefs = json.loads(STORE.read_text(encoding="utf-8"))
    r2 = llm.invoke(
        [
            SystemMessage(f"Known user preferences (long-term memory): {prefs}"),
            HumanMessage(q),
        ]
    )
    result(f'Model: "{r2.content.strip()}"')
    note("The model didn't remember — OUR APP did, and re-fed it. That's long-term memory.")


def semantic(llm) -> None:
    step("3 · SEMANTIC — facts and knowledge")
    r = llm.invoke([HumanMessage("In one word: what is the capital of France?")])
    result(f'Model: "{r.content.strip()}"')
    note("No context supplied — this fact is baked into the model's weights from training. "
         "(In RAG systems, retrieved documents extend semantic memory with YOUR facts.)")


def episodic(llm) -> None:
    step("4 · EPISODIC — past interactions")
    log = ("2026-06-05: user booked Conference Room B for sprint review\n"
           "2026-06-12: user booked Conference Room B for sprint review")
    note("The app injects an interaction log from previous sessions:")
    for line in log.splitlines():
        print(f"      {DIM}{line}{RESET}")
    r = llm.invoke(
        [
            SystemMessage(f"Episodic memory — this user's past interactions:\n{log}"),
            HumanMessage("Book the usual room for Friday's sprint review. Which room will you book? One sentence."),
        ]
    )
    result(f'Model: "{r.content.strip()}"')
    note('"The usual" is meaningless without a record of past episodes.')


def working() -> None:
    step("5 · WORKING — temporary scratchpad for the task in flight")
    note("No new call needed — you already watched working memory today: in the agent demo "
         "(Slide 7), the growing message list of THINK/ACT/OBSERVE steps was working memory. "
         "It held the weather results just long enough to finish the task, then was discarded.")


def main() -> None:
    banner(
        "SLIDE 10 · Memory: Context Beyond One Prompt",
        "Five memory types — all the same trick: choosing what to re-feed into the prompt.",
        "watch each type turn a stateless predictor into a stateful assistant.",
    )
    if STORE.exists():
        STORE.unlink()  # fresh run every time
    llm = get_llm(temperature=None)

    short_term(llm)
    long_term(llm)
    semantic(llm)
    episodic(llm)
    working()

    takeaway("The model never remembers — the SYSTEM does. Memory = deciding what goes back into the context window.")


if __name__ == "__main__":
    main()
