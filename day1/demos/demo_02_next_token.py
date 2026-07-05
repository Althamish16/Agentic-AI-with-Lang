"""
LIVE DEMO — Slide 2: "What is an LLM?"

Goal on screen: make "it just predicts the next token, statistically" and
"it has no memory between calls" concrete and undeniable.

Two parts:
  A) NEXT-TOKEN PREDICTION — we ask the model to continue a sentence and, when the
     deployment supports it, print the TOP-5 candidate next tokens with their
     probabilities. Trivia and poetry are answered by the SAME mechanism.
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


def _show_top_tokens(prefix: str) -> bool:
    """Ask the model to continue `prefix` and print the top candidate next tokens
    with probabilities. Returns True if logprobs were available, else False."""
    # logprobs / top_logprobs ask the API to reveal the probability distribution
    # over the next token — the clearest possible view of "it's just prediction".
    llm = get_llm(temperature=None, logprobs=True, top_logprobs=5, max_tokens=1)
    msgs = [
        SystemMessage(
            "Continue the text with exactly ONE next word. Output only that word, nothing else."
        ),
        HumanMessage(prefix),
    ]
    try:
        resp: AIMessage = llm.invoke(msgs)
        content = resp.response_metadata.get("logprobs", {}).get("content") or []
        first = content[0]
        tops = first.get("top_logprobs", [])
        if not tops:
            raise ValueError("no top_logprobs returned")
    except Exception as exc:  # deployment may not support logprobs (some reasoning models)
        note(f"(This deployment didn't return token probabilities: {exc})")
        result(f'"{prefix}"  →  "{_continue_one_word(prefix)}"')
        note("That single word is simply the highest-probability continuation.")
        return False

    print(f'  Prompt: {DIM}"{prefix}"{RESET}')
    print(f"  Top candidate next tokens (model's probability distribution):\n")
    for cand in tops:
        tok = cand["token"].replace("\n", "\\n")
        prob = math.exp(cand["logprob"])  # logprob -> probability
        bar = "█" * max(1, round(prob * 30))
        print(f"    {GREEN}{tok:<14}{RESET} {prob*100:5.1f}%  {GREEN}{bar}{RESET}")
    return True


def _continue_one_word(prefix: str) -> str:
    """Fallback when logprobs aren't available: just get the single next word."""
    llm = get_llm(temperature=None, max_tokens=1)
    msgs = [
        SystemMessage("Continue with exactly ONE next word. Output only that word."),
        HumanMessage(prefix),
    ]
    return llm.invoke(msgs).content.strip()


def part_a_next_token() -> None:
    step("PART A · NEXT-TOKEN PREDICTION", "poetry and trivia use the SAME mechanism")

    print(f"\n{DIM}  — A line of poetry —{RESET}")
    _show_top_tokens("Roses are red, violets are")

    print(f"\n{DIM}  — A trivia fact (same machinery, no 'knowing') —{RESET}")
    _show_top_tokens("The capital of France is")

    takeaway("The model isn't recalling facts — it's ranking likely next words.")


def part_b_no_memory() -> None:
    step("PART B · NO MEMORY BETWEEN CALLS", "each request starts from a blank slate")
    llm = get_llm(temperature=None)

    # Call 1 — we tell it our name (in its OWN isolated request).
    note('Call #1  — we introduce ourselves in one request:')
    r1 = llm.invoke([HumanMessage("My name is Priya. Reply in one short sentence.")])
    result(f"Model: {r1.content.strip()}")

    # Call 2 — a brand-new request with NO history. It has forgotten.
    note('Call #2  — a brand-new request that carries NO history:')
    r2 = llm.invoke([HumanMessage("What is my name?")])
    result(f"Model: {r2.content.strip()}")

    # Call 3 — same question, but we REMIND it by putting the fact back in the prompt.
    note('Call #3  — same question, but we put the earlier turn back into the prompt:')
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
