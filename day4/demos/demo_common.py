"""
demo_common.py — shared plumbing for the Day 4 LIVE DEMOS.

Same rule as day1/demos/demo_common.py:
  This module holds ONLY things that every Day 4 demo shares.
  The teaching content lives INSIDE each demo_XX_*.py so a fresher opening
  a single file sees the whole lesson without hunting.

What's shared here:
  • banner / step / note / result / takeaway  — presentation helpers
  • search_docs / web_search / summarize      — the tool belt used in demos 2 & 3
  • build_agent(...)                          — the tiny LangGraph wiring
  • FAIL_WEB_SEARCH toggle                    — flipped by demo_03 to force a break

Why the tools live here (unlike Day 1)
--------------------------------------
Day 1 demos each define their own tools inline. Day 4's demos 2 and 3 both need
the SAME three tools + SAME graph, so duplicating ~60 lines across every file
would hide the actual lesson. Read this file ONCE, then each demo file is short
and focused on the ONE thing it teaches.
"""

from __future__ import annotations

import json
import pathlib
import sys
import textwrap
from typing import Iterable

# Make the repo root importable so `config` resolves no matter the CWD, and so
# `import demo_common` works when a demo is launched directly.
_THIS_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))                     # for `import demo_common`
sys.path.insert(0, str(_THIS_DIR.parents[1]))          # repo root -> `import config`

import config  # noqa: E402,F401 — side effects: .env load + Windows UTF-8/ANSI setup

from langchain_core.messages import HumanMessage, SystemMessage        # noqa: E402
from langchain_core.tools import tool                                   # noqa: E402
from langgraph.graph import END, START, MessagesState, StateGraph       # noqa: E402
from langgraph.prebuilt import ToolNode, tools_condition                # noqa: E402

from config import get_llm                                              # noqa: E402
from shared.rag import format_docs_with_citations, get_retriever        # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Presentation helpers (same shape as day1/demos/demo_common.py)
# ─────────────────────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

_WIDTH = 74
_INNER = _WIDTH - 4


def _wrap(text: str) -> list[str]:
    return textwrap.wrap(text, width=_INNER) or [""]


def banner(slide: str, title: str, demo: str) -> None:
    """Print the big header every demo starts with."""
    top = "╔" + "═" * (_WIDTH - 2) + "╗"
    bot = "╚" + "═" * (_WIDTH - 2) + "╝"
    sep = "╟" + "─" * (_WIDTH - 2) + "╢"

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
    line = f"{YELLOW}{BOLD}▶ {label}{RESET}"
    if desc:
        line += f"  {DIM}{desc}{RESET}"
    print("\n" + line)


def note(text: str) -> None:
    for line in textwrap.wrap(text, width=_WIDTH):
        print(f"  {DIM}{line}{RESET}")


def result(text: str) -> None:
    print(f"  {GREEN}{text}{RESET}")


def warn(text: str) -> None:
    print(f"  {YELLOW}⚠ {text}{RESET}")


def takeaway(text: str) -> None:
    print(f"\n{MAGENTA}{BOLD}➜ Takeaway:{RESET} {MAGENTA}{text}{RESET}\n")


def rule(char: str = "─", width: int = _WIDTH) -> None:
    print(char * width)


# ─────────────────────────────────────────────────────────────────────────────
# THE TOOL BELT
#
# Docstrings ARE the tool's prompt. Rules of thumb:
#   • SPECIFIC (say when to use it)
#   • NON-OVERLAPPING (each tool has one job the others don't)
#   • VERB-FIRST (models pattern-match on "Search…", "Summarize…", "Compute…")
#
# We keep the tools plain top-level functions so learners can import & call
# them from any REPL: `from demo_common import search_docs`.
# ─────────────────────────────────────────────────────────────────────────────

# demo_03 flips this to True to force a failure in web_search. Kept in this
# module so any demo can toggle the flaky-provider behaviour without touching
# the tool code itself.
FAIL_WEB_SEARCH = False


@tool
def search_docs(query: str) -> str:
    """Search the indexed PDFs for a topic.

    Use this for questions about the LOCAL course knowledge base
    (RAG, LangGraph, vector databases, prompting, agent memory).
    Returns numbered, citable passages from data/.
    """
    # Wraps the Day 2 retriever unchanged — the same function that answered
    # Day 2's questions is now a tool the agent can *choose* to call.
    docs = get_retriever(k=3).invoke(query)
    return format_docs_with_citations(docs)


@tool
def web_search(query: str) -> str:
    """Search the public web for CURRENT facts NOT in the local knowledge base.

    Use only for questions the local docs can't cover (today's news, live
    prices, latest release versions).
    """
    # ---- The whole point of this try/except is TEACHING error recovery. ----
    # A tool is code that runs OUTSIDE the LLM's control (network / disk / API).
    # If we let an exception escape, ToolNode would surface it and — without
    # `handle_tool_errors=True` — the graph would crash. Returning a *readable*
    # error string is better: the model sees the string in the next turn and
    # can decide to pivot to another tool.
    try:
        if FAIL_WEB_SEARCH:
            raise RuntimeError("web_search provider timed out (simulated)")
        return _mock_web_results(query)
    except Exception as e:  # noqa: BLE001 — return-as-string is the point.
        return f"SEARCH_FAILED: {e}"


def _mock_web_results(query: str) -> str:
    """Deterministic canned snippets so the lab works offline."""
    return (
        f"(MOCK web results for {query!r})\n"
        "- Retrieval-augmented generation grounds LLMs in external documents.\n"
        "- LangGraph models agents as stateful graphs with conditional edges.\n"
        "- Chroma stores vector embeddings for fast semantic search."
    )


@tool
def summarize(text: str) -> str:
    """Condense a passage of text into 2-3 tight sentences.

    Pass in the text you want condensed — do NOT pass a question. This tool
    does not look anything up; it only shortens whatever you give it.
    """
    llm = get_llm(temperature=0)
    return llm.invoke(f"Summarize this in 2-3 sentences:\n\n{text}").content


# The default tool belt. Individual demos can pass their own list to build_agent().
TOOLS = [search_docs, web_search, summarize]


# ─────────────────────────────────────────────────────────────────────────────
# THE GRAPH — same shape as Day 3, but the "executor" is now a tool call.
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM = (
    "You are a research assistant with a tool belt: "
    "search_docs (local knowledge base — prefer this for course topics), "
    "web_search (only for facts not in the local docs), "
    "summarize (condense text you already have). "
    "Call tools when they help, then give a concise final answer."
)


def build_agent(tools: Iterable | None = None, handle_tool_errors: bool = True):
    """Compile the tool-calling graph.

    `handle_tool_errors=True` (default) makes ToolNode catch a raised exception
    and hand it back to the model as a ToolMessage — so even a truly unhandled
    crash degrades gracefully. Set False to *see* the graph crash on a raise.
    """
    tools = list(tools) if tools is not None else TOOLS

    # bind_tools() gives the model the JSON-schema signatures of each tool so
    # it can emit a *structured* tool call (name + typed args), not free text.
    llm_with_tools = get_llm(temperature=0).bind_tools(tools)

    def agent_node(state: MessagesState) -> dict:
        step("NODE: agent", "decide: answer or call a tool")
        ai = llm_with_tools.invoke(state["messages"])
        # Make the loop visible: show the *raw* structured tool call the model
        # produced. This is the JSON the ToolNode is about to execute.
        if ai.tool_calls:
            for tc in ai.tool_calls:
                payload = json.dumps({"name": tc["name"], "args": tc["args"]})
                print(f"  {BLUE}→ tool_call JSON:{RESET} {payload}")
        else:
            print(f"  {BLUE}→ no tool call — model produced a final answer{RESET}")
        return {"messages": [ai]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(tools, handle_tool_errors=handle_tool_errors))

    g.add_edge(START, "agent")
    # tools_condition is a prebuilt router that looks at the last AIMessage:
    #   has .tool_calls?  → "tools"
    #   otherwise         → END
    g.add_conditional_edges("agent", tools_condition)
    # After the tools run, ALWAYS loop back to the agent so it can read the
    # results and either call another tool or write the final answer.
    g.add_edge("tools", "agent")
    return g.compile()


def run_agent(app, question: str, system: str = SYSTEM) -> str:
    """Invoke the graph and return the final assistant message content."""
    result = app.invoke({"messages": [SystemMessage(content=system), HumanMessage(content=question)]})
    return result["messages"][-1].content
