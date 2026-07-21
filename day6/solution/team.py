"""
day6/solution/team.py — Day 6 SOLUTION · Multi-agent team (supervisor + workers).

    ┌──────────┐        ┌──────────────┐        ┌────────┐
    │ supervisor│──────▶│  researcher  │──┐   ┌▶│ writer │──┐
    └──────────┘        └──────────────┘  │   │ └────────┘  │
          ▲   ▲                            │   │             │
          └───┴────────────────────────────┴───┴─────────────┘
                  routing key: "researcher" | "writer" | FINISH

Design goals for the lab
────────────────────────
1. **Workers are sub-graphs.** `build_researcher()` and `build_writer()`
   each compile their own `StateGraph`; the parent plugs each one in as a
   node. This is the composable pattern from Day 3 (workers = graphs) with
   the tool-using shape from Day 4.
2. **Explicit state ownership.** Every field on `TeamState` is annotated as
   SHARED (all agents see it) or PRIVATE (scoped to one worker). The workers
   receive ONLY the shared slice they need — that's context isolation, and
   it's the whole point of decomposing into agents.
3. **Supervisor decides via a routing key.** It writes `next` into state; a
   plain `route()` function reads it and `add_conditional_edges` maps it to
   the right node. No LLM prompt-parsing here — just a data flow.
4. **Offline by default.** `_llm.get_llm()` returns a deterministic mock
   when no API key is set, so the demo runs end-to-end with no network.

Run it
──────
    python day6/solution/team.py
    python day6/solution/team.py "How do agents combine memory and tools?"

Common pitfalls this lab makes visible
──────────────────────────────────────
• Going multi-agent too early: a single well-prompted LLM often beats a
  team on small tasks. See the exercise `single_agent()` for a comparison.
• Token/cost explosion: every hand-off duplicates context. The exercise
  instrument counts input tokens per worker so you can *see* the tax.
• Error propagation: if the researcher returns garbage, the writer happily
  writes about garbage. That's why the exercise adds a `critic`.
• Ambiguous shared state: two workers writing the same field silently clobber
  each other. Keep worker outputs on distinct fields (or use a reducer).
• No step/budget cap: LangGraph's `recursion_limit` keeps the whole team
  from looping forever.  We set it in `TEAM_INVOKE_CONFIG` below.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Annotated, List, Literal, TypedDict

# Make the repo importable when the file is launched directly.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# Loads .env if present, but Day 6 works without it. Also configures the
# console for UTF-8 on Windows so the trace glyphs render.
try:  # optional — the mock LLM path doesn't need it
    import config  # noqa: F401
except Exception:  # pragma: no cover
    pass

from langgraph.graph import END, START, StateGraph

from day6._llm import get_llm, provider_label

# `operator.add` is the classic list-reducer: when a node returns a list on
# a field annotated with add_messages/add, LangGraph APPENDS to it instead
# of overwriting. That's how our shared `trace` field accumulates safely
# even though every worker writes to it.
import operator


# ═════════════════════════════════════════════════════════════════════════════
# Team state — every field labelled SHARED or PRIVATE.
#
# SHARED   → visible to every node in the team graph. Change these carefully:
#            two workers writing the same shared field can clobber each other
#            unless the field uses a reducer (like `Annotated[..., operator.add]`).
# PRIVATE  → belongs to one worker's SUB-GRAPH; the parent never reads or
#            writes it directly. The worker exposes only its *output* back
#            to the team's shared state.
# ═════════════════════════════════════════════════════════════════════════════
class TeamState(TypedDict, total=False):
    # ── SHARED (the whole team sees these) ──────────────────────────────
    topic: str                                          # SHARED · the user's question
    findings: List[dict]                                # SHARED · researcher → writer
    draft: str                                          # SHARED · writer → supervisor
    trace: Annotated[List[str], operator.add]           # SHARED · delegation log (append-only)
    step: int                                           # SHARED · monotonic step counter
    next: Literal["researcher", "writer", "FINISH"]     # SHARED · routing key
    # ── DERIVED ────────────────────────────────────────────────────────
    final: str                                          # SHARED · aggregated result


# Small hard caps so a broken supervisor can't loop forever. LangGraph enforces
# `recursion_limit` at compile-time; we add our own `MAX_STEPS` as a belt.
MAX_STEPS = 12
TEAM_INVOKE_CONFIG: dict = {"recursion_limit": 25}


# ═════════════════════════════════════════════════════════════════════════════
# Worker #1 — RESEARCHER  (its own compiled StateGraph)
#
# Private state (never leaked to the parent):
#   • sub_questions : List[str]   — decomposition of the topic
#   • cursor        : int         — which sub-question is next
#
# Tool:
#   • web_search(query) → str     — a STUBBED offline search. Real teams
#                                    would bind_tools() a live search here.
# ═════════════════════════════════════════════════════════════════════════════
class _ResearcherState(TypedDict, total=False):
    topic: str                    # PRIVATE (copied in from shared.topic)
    sub_questions: List[str]      # PRIVATE
    cursor: int                   # PRIVATE
    findings: List[dict]          # returned back to the shared TeamState


# A stubbed tool. The docstring is the prompt the model would see if we bound
# it through `bind_tools`. Keeping the tool CANNED means the demo is 100 %
# reproducible; the exercise shows how to swap in a real one.
_FAKE_CORPUS = {
    "definition": "It is the practice of coordinating multiple specialised agents so each handles a bounded slice of a task.",
    "practice":   "In practice, a supervisor delegates to workers, aggregates their outputs, and decides when the job is done.",
    "trade-off":  "The main trade-off is more tokens and latency in exchange for better modularity and clearer failure isolation.",
    "pitfall":    "The classic pitfall is adopting multi-agent too early — a single well-prompted LLM often outperforms a team on small tasks.",
}


def web_search(query: str) -> str:
    """STUB · pretend to search the web. Returns a canned snippet keyed by the
    strongest content word in the query. Real code would call a search API."""
    q = query.lower()
    for k, v in _FAKE_CORPUS.items():
        if k in q:
            return f'"{v}" — mock-source.example/{k}'
    # generic fallback so every sub-question gets *some* signal
    return f'"{_FAKE_CORPUS["definition"]}" — mock-source.example/definition'


def build_researcher():
    """Compile the researcher sub-graph:  plan → search (loop) → END."""

    def plan(state: _ResearcherState) -> dict:
        llm = get_llm()
        raw = llm.invoke(
            f"Break the topic '{state['topic']}' into 3 short sub-questions.\n"
            "Return ONE per line, no numbering."
        ).content
        subs = [ln.strip("-• \t") for ln in raw.splitlines() if ln.strip()][:3]
        # if the model returned nothing useful, guarantee at least one sub-question
        if not subs:
            subs = [f"What is {state['topic']}?"]
        return {"sub_questions": subs, "cursor": 0, "findings": []}

    def search(state: _ResearcherState) -> dict:
        i = state["cursor"]
        sub_q = state["sub_questions"][i]
        # Call the tool. In a bind_tools()-based version the model would emit a
        # tool_call and a ToolNode would run this — same shape, different
        # plumbing.
        snippet = web_search(sub_q)
        finding = {"sub_question": sub_q, "evidence": snippet}
        return {
            "findings": state["findings"] + [finding],
            "cursor": i + 1,
        }

    def more(state: _ResearcherState) -> str:
        return "search" if state["cursor"] < len(state["sub_questions"]) else END

    g = StateGraph(_ResearcherState)
    g.add_node("plan", plan)
    g.add_node("search", search)
    g.add_edge(START, "plan")
    g.add_edge("plan", "search")
    g.add_conditional_edges("search", more, {"search": "search", END: END})
    return g.compile()


# ═════════════════════════════════════════════════════════════════════════════
# Worker #2 — WRITER  (its own compiled StateGraph)
#
# The writer sees ONLY {topic, findings} from the shared state. It has no
# access to the researcher's internal sub_questions/cursor: that's context
# isolation, and it's what makes each worker independently reusable.
# ═════════════════════════════════════════════════════════════════════════════
class _WriterState(TypedDict, total=False):
    topic: str               # PRIVATE input (from shared)
    findings: List[dict]     # PRIVATE input (from shared)
    draft: str               # output returned to shared TeamState


def build_writer():
    def write(state: _WriterState) -> dict:
        llm = get_llm()
        bulleted = "\n".join(f"- {f['sub_question']}: {f['evidence']}"
                             for f in state["findings"])
        draft = llm.invoke(
            f"Write a concise research brief on '{state['topic']}' using ONLY these findings:\n\n"
            f"{bulleted}\n\nKeep it under 12 lines."
        ).content
        return {"draft": draft}

    g = StateGraph(_WriterState)
    g.add_node("write", write)
    g.add_edge(START, "write")
    g.add_edge("write", END)
    return g.compile()


# ═════════════════════════════════════════════════════════════════════════════
# Supervisor + team graph
#
# The supervisor is a plain function today (rule-based) — clear teaching signal.
# Swap it for `bind_tools()` on an LLM later and nothing else changes.
# ═════════════════════════════════════════════════════════════════════════════
def _log(state: TeamState, msg: str) -> dict:
    """Return a partial state that BOTH bumps `step` AND appends to `trace`.
    We keep this in one place so every worker logs consistently."""
    return {"step": (state.get("step") or 0) + 1, "trace": [msg]}


def build_team():
    researcher = build_researcher()
    writer = build_writer()

    # ── supervisor node ────────────────────────────────────────────────
    def supervisor(state: TeamState) -> dict:
        """Decide who works next. Writes the routing key `next` into state.

        Rules (deterministic on purpose — easy to test):
          1. no findings yet         → "researcher"
          2. findings but no draft   → "writer"
          3. draft is present        → "FINISH"
          4. step budget exceeded    → "FINISH" (belt & braces)
        """
        step = state.get("step") or 0
        if step >= MAX_STEPS:
            decision = "FINISH"
        elif not state.get("findings"):
            decision = "researcher"
        elif not state.get("draft"):
            decision = "writer"
        else:
            decision = "FINISH"
        return {
            **_log(state, f"supervisor → {decision}"),
            "next": decision,
        }

    # ── researcher NODE inside the team ────────────────────────────────
    def researcher_node(state: TeamState) -> dict:
        # Hand the worker ONLY the shared slice it needs. Everything else in
        # `state` (draft, trace, step, next…) is NOT passed in. That's the
        # isolation contract — the worker cannot depend on parent internals.
        result = researcher.invoke({"topic": state["topic"]})
        return {
            **_log(state, f"researcher gathered {len(result['findings'])} findings"),
            "findings": result["findings"],
        }

    # ── writer NODE inside the team ────────────────────────────────────
    def writer_node(state: TeamState) -> dict:
        result = writer.invoke({"topic": state["topic"], "findings": state["findings"]})
        return {
            **_log(state, f"writer produced draft ({len(result['draft'])} chars)"),
            "draft": result["draft"],
        }

    # ── finalizer — the terminal aggregator ────────────────────────────
    def finalize(state: TeamState) -> dict:
        return {
            **_log(state, "FINISH → aggregate results"),
            "final": state.get("draft", ""),
        }

    # ── routing helper ────────────────────────────────────────────────
    def route(state: TeamState) -> str:
        """Read the supervisor's routing key and map it to the next node."""
        return {"researcher": "researcher", "writer": "writer", "FINISH": "finalize"}[state["next"]]

    # ── assemble the team graph ───────────────────────────────────────
    g = StateGraph(TeamState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher_node)
    g.add_node("writer", writer_node)
    g.add_node("finalize", finalize)

    g.add_edge(START, "supervisor")
    # A single conditional edge from the supervisor. The routing key lives in
    # state["next"]; `route()` maps it to a real node name — this is what
    # makes the supervisor pattern composable.
    g.add_conditional_edges(
        "supervisor",
        route,
        {"researcher": "researcher", "writer": "writer", "finalize": "finalize"},
    )
    # workers report BACK to the supervisor so it can decide the next step
    g.add_edge("researcher", "supervisor")
    g.add_edge("writer", "supervisor")
    g.add_edge("finalize", END)

    return g.compile()


# ═════════════════════════════════════════════════════════════════════════════
# Demo runner — prints a delegation trace: supervisor → researcher → writer → FINISH
# ═════════════════════════════════════════════════════════════════════════════
def run_demo(topic: str) -> dict:
    print("═" * 74)
    print("Day 6 · Multi-agent team demo")
    print(f"  provider : {provider_label()}")
    print(f"  topic    : {topic}")
    print("═" * 74)

    team = build_team()
    final_state = team.invoke({"topic": topic}, TEAM_INVOKE_CONFIG)

    print("\n── DELEGATION TRACE ─────────────────────────────────────────────")
    for i, line in enumerate(final_state.get("trace", []), start=1):
        print(f"  {i:>2}. {line}")

    print("\n── SHARED-STATE SNAPSHOT ────────────────────────────────────────")
    print(f"  findings : {len(final_state.get('findings') or [])} items")
    print(f"  draft    : {len(final_state.get('draft') or '')} chars")
    print(f"  steps    : {final_state.get('step')}")

    print("\n── FINAL DRAFT ──────────────────────────────────────────────────")
    print(final_state.get("final") or "(empty)")
    return final_state


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]).strip() or "multi-agent supervisor patterns"
    run_demo(q)
