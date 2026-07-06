"""
LIVE DEMO — Slide 2: "What is an LLM?"

Goal on screen: make "it just predicts the next token, statistically" and
"it has no memory between calls" concrete and undeniable.

Two parts:
  A) NEXT-TOKEN PREDICTION — we ask the model to continue a sentence and print the
     TOP candidate next tokens with their probabilities (via `logprobs`). Some
     sentences are near-certain (blue ≈ 100%); others are a genuine split
     (summer 66% / spring 24% / autumn 9%). Either way it's just ranking words.
  B) NO MEMORY — a fresh request has forgotten what you said in the previous one,
     "unless you remind them" (i.e. put it back in the prompt).

Run:
    python day1/demos/demo_02_next_token.py
"""

from __future__ import annotations

import math

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from demo_common import banner, step, note, result, takeaway, DIM, RESET, GREEN
from config import get_llm

# Prompts chosen to span the range from "almost certain" to "genuinely split", so
# the probability distribution is visible rather than always collapsing to 100%.
PROMPTS = [
    ("Roses are red, violets are", "a line of poetry — the model is almost certain"),
    ("My favorite season of the year is", "genuinely ambiguous — watch the split"),
    ("I flipped a fair coin and it landed on", "a near 50/50 idea, with a clear favorite"),
]


def _show_top_tokens(prefix: str) -> None:
    """Ask the model to continue `prefix` and print the candidate next tokens with
    probabilities. NOTE: no max_tokens cap — gpt-5-class reasoning models spend
    hidden tokens thinking, so a tiny cap would error before any word appears."""
    llm = get_llm(temperature=None, logprobs=True, top_logprobs=5)
    msgs = [
        SystemMessage("Continue the text with exactly ONE next word. Output only that word, nothing else."),
        HumanMessage(prefix),
    ]
    try:
        resp: AIMessage = llm.invoke(msgs)
        content = resp.response_metadata.get("logprobs", {}).get("content") or []
        tops = content[0].get("top_logprobs", [])
        if not tops:
            raise ValueError("no top_logprobs returned")
    except Exception as exc:  # deployment without logprobs support -> still make the point
        note(f"(No token probabilities from this deployment: {exc})")
        result(f'"{prefix} ___"  →  the model picked the single most likely word.')
        return

    print(f'  Prompt: {DIM}"{prefix} ___"{RESET}   (chosen: {GREEN}{resp.content.strip()}{RESET})')
    print("  Probability the model assigned to each candidate next token:\n")
    for cand in tops:
        tok = cand["token"].replace("\n", "\\n")
        prob = math.exp(cand["logprob"])  # logprob -> probability
        bar = "█" * max(1, round(prob * 30))
        print(f"    {GREEN}{tok:<12}{RESET} {prob * 100:5.1f}%  {GREEN}{bar}{RESET}")


def part_a_next_token() -> None:
    step("PART A · NEXT-TOKEN PREDICTION", "the model ranks likely next words — nothing more")
    for prefix, why in PROMPTS:
        print(f"\n{DIM}  — {why} —{RESET}")
        _show_top_tokens(prefix)
    takeaway("Sometimes ~100% sure, sometimes a real split — but always just ranking the next word.")


def part_b_no_memory() -> None:
    step("PART B · NO MEMORY BETWEEN CALLS", "each request starts from a blank slate")
    llm = get_llm(temperature=None)

    # Call 1 — we tell it our name (in its OWN isolated request).
    note("Call #1  — we introduce ourselves in one request:")
    r1 = llm.invoke([HumanMessage("My name is Priya. Reply in one short sentence.")])
    result(f"Model: {r1.content.strip()}")

    # Call 2 — a brand-new request with NO history. It has forgotten.
    note("Call #2  — a brand-new request that carries NO history:")
    r2 = llm.invoke([HumanMessage("What is my name?")])
    result(f"Model: {r2.content.strip()}")

    # Call 3 — same question, but we REMIND it by putting the fact back in the prompt.
    note("Call #3  — same question, but we put the earlier turn back into the prompt:")
    r3 = llm.invoke(
        [
            HumanMessage("My name is Priya."),
            AIMessage("Nice to meet you, Priya!"),
            HumanMessage("What is my name?"),
        ]
    )
    result(f"Model: {r3.content.strip()}")

    takeaway('It only "remembers" what you resend. Memory (Slide 10) is us re-feeding context.')


def main() -> None:
    banner(
        "SLIDE 2 · What is an LLM?",
        "An LLM predicts the next token — statistically — and has no memory of its own.",
        "watch it rank next-word candidates, then watch it forget your name.",
    )
    part_a_next_token()
    part_b_no_memory()


if __name__ == "__main__":
    main()
