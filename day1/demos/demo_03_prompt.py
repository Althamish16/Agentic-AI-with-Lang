"""
LIVE DEMO — Slide 3: "The Prompt"

Goal on screen: the user types ONE sentence, but the model receives FIVE blocks:
    System instructions · Context · Conversation history · Retrieved docs · Question

We send the SAME angry customer question three times, adding one layer of prompt
each time, and watch the answer go from useless → on-brand → actually resolving
the issue. Prompt = Instructions + Context + User Question.

Run:
    python day1/demos/demo_03_prompt.py
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD, BLUE
from config import get_llm

# The one sentence the user actually types:
QUESTION = "Where is my order and what are you going to do about it?"

# Everything ELSE that goes into the prompt — invisible to the user:
INSTRUCTIONS = (
    "You are ACME's customer support agent. Be concise (max 3 sentences), professional "
    "and warm. Never promise refunds over $100."
)
CONTEXT = "Customer tier: Premium. Order #4471 shipped 3 days ago; carrier status: DELAYED (>48h)."
RETRIEVED = "Policy KB-88: Premium customers receive a FREE reshipment when delivery is delayed more than 48 hours."
HISTORY_USER = "This is the second time this has happened to me."
HISTORY_AI = "I'm really sorry about that — let me look into it right away."


def _block(label: str, text: str) -> None:
    """Print one labeled prompt block so the audience sees what the model receives."""
    print(f"    {BLUE}{BOLD}[{label}]{RESET} {DIM}{text}{RESET}")


def main() -> None:
    banner(
        "SLIDE 3 · The Prompt",
        "Prompt = Instructions + Context + User Question — everything sent in one request.",
        "the SAME question asked 3 times, adding one prompt layer each time.",
    )
    llm = get_llm(temperature=None)

    # ── Round 1: question only ────────────────────────────────────────────────
    step("ROUND 1 · QUESTION ONLY", "what most people think a 'prompt' is")
    print("  The model receives just:")
    _block("USER", QUESTION)
    r1 = llm.invoke([HumanMessage(QUESTION)])
    result(f"Model: {r1.content.strip()}")
    note("Generic and helpless — it knows nothing about you, the order, or the rules.")

    # ── Round 2: + system instructions ───────────────────────────────────────
    step("ROUND 2 · + SYSTEM INSTRUCTIONS", "now it has a role and boundaries")
    print("  The model receives:")
    _block("SYSTEM", INSTRUCTIONS)
    _block("USER", QUESTION)
    r2 = llm.invoke([SystemMessage(INSTRUCTIONS), HumanMessage(QUESTION)])
    result(f"Model: {r2.content.strip()}")
    note("On-brand tone now — but it still can't actually resolve anything.")

    # ── Round 3: the FULL prompt ─────────────────────────────────────────────
    step("ROUND 3 · THE FULL PROMPT", "instructions + history + context + retrieved policy")
    print("  The model receives ALL of this (the user still only typed one line):")
    _block("SYSTEM", INSTRUCTIONS)
    _block("HISTORY", f'user: "{HISTORY_USER}"  →  assistant: "{HISTORY_AI}"')
    _block("CONTEXT", CONTEXT)
    _block("RETRIEVED", RETRIEVED)
    _block("USER", QUESTION)
    r3 = llm.invoke(
        [
            SystemMessage(f"{INSTRUCTIONS}\n\nAccount context:\n{CONTEXT}\n\nRelevant policy:\n{RETRIEVED}"),
            HumanMessage(HISTORY_USER),
            AIMessage(HISTORY_AI),
            HumanMessage(QUESTION),
        ]
    )
    result(f"Model: {r3.content.strip()}")
    note("Same model, same question — the ONLY thing that changed is what we packed around it.")

    takeaway("The user typed one sentence; the model received five blocks. Prompt engineering is the other four.")


if __name__ == "__main__":
    main()
