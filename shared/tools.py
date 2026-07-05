"""
tools.py — the Day 4 tool belt, promoted to shared/ for Day 6/7 and the UI.

Four @tool functions the agent can call:
  • web_search        — mock by default; real Tavily search if configured
  • retrieve_documents — the Day 2 RAG retriever, exposed as a tool
  • summarize         — LLM summarizer
  • unreliable_metric — a DELIBERATELY breakable tool for the error-recovery lab

Plus `call_with_retry`, a tiny retry helper used to show graceful recovery.
"""

from __future__ import annotations

import time
from typing import Callable

from langchain_core.tools import tool

from config import get_llm, settings
from shared.rag import format_docs_with_citations, get_retriever


# ─────────────────────────────────────────────────────────────────────────────
# 1) Web search — stub by default so the lab runs offline.
# ─────────────────────────────────────────────────────────────────────────────
@tool
def web_search(query: str) -> str:
    """Search the public web for a query and return a few short result snippets.
    Use this for current events or facts not in the local knowledge base."""
    if settings.web_search_provider == "tavily":
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            results = TavilySearchResults(max_results=3).invoke({"query": query})
            return "\n".join(f"- {r['content'][:200]}" for r in results)
        except Exception as e:  # fall back to mock rather than crash the lab
            return f"[web_search] real provider failed ({e}); returning mock results.\n" + _mock_web(query)
    return _mock_web(query)


def _mock_web(query: str) -> str:
    """Deterministic canned 'search results' so Day 4 works with no API key."""
    return (
        f"(MOCK web results for {query!r} — set WEB_SEARCH_PROVIDER=tavily for real search)\n"
        "- Retrieval-augmented generation grounds LLM answers in external documents to cut hallucination.\n"
        "- LangGraph models agents as stateful graphs with conditional edges, enabling loops and tool use.\n"
        "- Vector databases like Chroma index embeddings for fast semantic similarity search."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2) Local retriever — the Day 2 RAG pipeline, now a tool the agent can choose.
# ─────────────────────────────────────────────────────────────────────────────
@tool
def retrieve_documents(query: str) -> str:
    """Retrieve the most relevant passages from the LOCAL knowledge base (the
    course's data/ folder). Prefer this for questions about RAG, LangGraph,
    vector databases, prompting, and agent memory."""
    docs = get_retriever(k=3).invoke(query)
    return format_docs_with_citations(docs)


# ─────────────────────────────────────────────────────────────────────────────
# 3) Summarizer — an LLM wrapped as a tool.
# ─────────────────────────────────────────────────────────────────────────────
@tool
def summarize(text: str) -> str:
    """Summarize a block of text into 2-3 tight sentences."""
    llm = get_llm(temperature=0)
    return llm.invoke(f"Summarize this in 2-3 sentences:\n\n{text}").content


# ─────────────────────────────────────────────────────────────────────────────
# 4) A DELIBERATELY breakable tool — for the retry / graceful-recovery lab.
#    It fails on odd-numbered calls and succeeds on even ones, so a retry (or the
#    model trying again) recovers.
# ─────────────────────────────────────────────────────────────────────────────
_call_counter = {"n": 0}


@tool
def unreliable_metric(topic: str) -> str:
    """Fetch a popularity metric for a topic from a flaky upstream service.
    NOTE: this service is unreliable and may time out — callers should retry."""
    _call_counter["n"] += 1
    if _call_counter["n"] % 2 == 1:
        raise RuntimeError("Upstream metric service timed out (simulated failure).")
    return f"Popularity index for {topic!r}: 87/100 (mock)."


def reset_flaky_tool() -> None:
    """Reset the failure counter so demos are reproducible."""
    _call_counter["n"] = 0


def call_with_retry(fn: Callable, *args, retries: int = 3, delay: float = 0.2, **kwargs):
    """Call `fn`, retrying on exception. Demonstrates graceful recovery instead of
    letting one flaky call crash the whole run."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 — we intentionally catch broadly here
            last_err = e
            print(f"    ↻ attempt {attempt}/{retries} failed: {e}")
            time.sleep(delay)
    raise RuntimeError(f"All {retries} retries failed. Last error: {last_err}")


# Convenient groups for binding.
RESEARCH_TOOLS = [web_search, retrieve_documents, summarize, unreliable_metric]
SAFE_TOOLS = [web_search, retrieve_documents, summarize]
