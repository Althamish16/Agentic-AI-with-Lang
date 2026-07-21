"""
day6/_llm.py — the ONE place Day 6 code resolves a chat model.

The Day 6 hands-on lab must run offline (no live API needed) so students can
concentrate on the multi-agent + resume story, not their API key. This module
picks a provider once and every worker imports `get_llm()` from here.

Priority order (edit `PROVIDER` OR set env DAY6_PROVIDER):

    "auto"      → try the course-wide config.get_llm() → OpenAI → Anthropic → mock
    "mock"      → force the offline mock (deterministic, no keys, no network)
    "openai"    → use OPENAI_API_KEY   via langchain-openai
    "anthropic" → use ANTHROPIC_API_KEY via langchain-anthropic
    "course"    → use the repo's config.get_llm() (Azure OpenAI by default)

Swap the provider by changing ONE env var. Nothing else in Day 6 imports a
model directly. That is the discipline this file enforces.
"""

from __future__ import annotations

import os
import re
from typing import Any, List

# ── Choose your provider in ONE place ────────────────────────────────────────
PROVIDER = os.getenv("DAY6_PROVIDER", "auto").lower()


# ═════════════════════════════════════════════════════════════════════════════
# The offline mock — deterministic, no network, ~0 latency.
# ═════════════════════════════════════════════════════════════════════════════
class _MockAI:
    """Duck-typed 'AIMessage': callers just read `.content`."""

    def __init__(self, content: str):
        self.content = content
        self.type = "ai"


class _MockChat:
    """A deterministic stand-in for a chat model.

    The heuristics here are just enough for the Day 6 workers:
      • planner-like prompts   → N terse sub-questions
      • writer-like prompts    → a short structured brief
      • critic-like prompts    → REVISE the first time, APPROVE on any retry
      • anything else          → a short mock reply

    Because the mock is DETERMINISTIC every demo produces the same output every
    run — great for teaching (students see the exact same trace the instructor
    saw). Swap in a real model by editing DAY6_PROVIDER when you want variety.

    Note the CLASS-level `_critic_calls`: every `get_llm()` returns a fresh
    `_MockChat` instance, so an instance counter would reset before every
    critique. The class-level counter accumulates across the whole process,
    which is what lets the writer↔critic loop resolve (REVISE the first time
    → APPROVE on any subsequent call within the same run).
    """

    _critic_calls: int = 0

    def reset_critic(self) -> None:
        """Reset the class-level critic counter (call this between demo runs
        if you want each run to see REVISE-then-APPROVE independently)."""
        type(self)._critic_calls = 0

    def invoke(self, prompt: Any) -> _MockAI:
        text = prompt if isinstance(prompt, str) else str(getattr(prompt, "content", prompt))
        low = text.lower()

        # ── critic-style prompt (checked FIRST — the trigger is a phrase that
        # only appears in the critic sub-graph, so the writer branch below
        # cannot mis-fire even when its prompt contains the draft) ─────────
        if "you are a critic" in low:
            type(self)._critic_calls += 1
            if type(self)._critic_calls == 1:
                return _MockAI(
                    "VERDICT: REVISE\n"
                    "Feedback: Add one concrete example and tighten the summary "
                    "into a single sentence."
                )
            return _MockAI(
                "VERDICT: APPROVE\nFeedback: Clear scope, cited findings, good takeaway."
            )

        # ── planner-style prompt ─────────────────────────────────────────
        n_match = re.search(r"(\d+)\s*(?:short\s*)?sub[-\s]?question", low)
        if n_match or ("break" in low and "sub" in low and "question" in low):
            topic = self._extract_topic(text)
            n = int(n_match.group(1)) if n_match else 3
            pool = [
                f"What is {topic}?",
                f"How does {topic} work in practice?",
                f"When should {topic} be preferred over alternatives?",
                f"What are the main trade-offs of {topic}?",
                f"What are common pitfalls when adopting {topic}?",
            ]
            return _MockAI("\n".join(pool[:n]))

        # ── writer-style prompt ──────────────────────────────────────────
        if ("write" in low or "compose" in low) and (
            "report" in low or "brief" in low
        ):
            topic = self._extract_topic(text)
            findings = self._extract_findings(text)
            bullets = "\n".join(f"- {f}" for f in findings) or f"- key point about {topic}"
            return _MockAI(
                f"# {topic.strip().title()}\n\n"
                f"**Summary.** This brief distils what the researcher gathered about "
                f"{topic}.\n\n"
                f"**Key points**\n{bullets}\n\n"
                f"**Takeaway.** Use the points above to guide the next step."
            )

        # ── fallback ─────────────────────────────────────────────────────
        return _MockAI(f"(mock reply for: {text[:120].strip()}...)")

    # helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_topic(text: str) -> str:
        m = re.search(r"'([^']{2,120})'", text) or re.search(r'"([^"]{2,120})"', text)
        if m:
            return m.group(1)
        m = re.search(r"about\s+(.+?)[.\n]", text, re.IGNORECASE)
        return (m.group(1) if m else "the topic").strip()

    @staticmethod
    def _extract_findings(text: str) -> List[str]:
        return [
            ln.strip("-•* \t").strip()
            for ln in text.splitlines()
            if ln.strip().startswith(("-", "•", "*"))
        ][:6]


# ═════════════════════════════════════════════════════════════════════════════
# Real-provider probes (each returns None if unavailable)
# ═════════════════════════════════════════════════════════════════════════════
def _try_course_llm():
    """The repo's own get_llm() — Azure OpenAI or whatever config.py says."""
    try:
        from config import get_llm as _course_get_llm  # type: ignore

        return _course_get_llm(temperature=0)
    except Exception:
        return None


def _try_openai():
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
    except Exception:
        return None


def _try_anthropic():
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        from langchain_anthropic import ChatAnthropic  # type: ignore

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            temperature=0,
        )
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════════════════════
def get_llm():
    """Return a chat model, resolved from PROVIDER (env DAY6_PROVIDER)."""
    if PROVIDER == "mock":
        return _MockChat()
    if PROVIDER == "openai":
        return _try_openai() or _MockChat()
    if PROVIDER == "anthropic":
        return _try_anthropic() or _MockChat()
    if PROVIDER == "course":
        return _try_course_llm() or _MockChat()

    # auto — try real providers first, fall back to mock so demos never fail.
    for probe in (_try_course_llm, _try_openai, _try_anthropic):
        m = probe()
        if m is not None:
            return m
    return _MockChat()


def provider_label() -> str:
    """Human label for the currently-selected provider (for banners / UI)."""
    m = get_llm()
    kind = type(m).__name__
    if kind == "_MockChat":
        return "offline mock (deterministic, no API needed)"
    return f"{kind} (DAY6_PROVIDER={PROVIDER})"


__all__ = ["get_llm", "provider_label", "PROVIDER"]
