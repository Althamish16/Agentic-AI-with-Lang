"""
day6/starter/team.py — Day 6 STARTER · a multi-agent team.

FILL IN the `# TODO(student)` gaps and run:

    python day6/starter/team.py "How do supervisors delegate to sub-agents?"

Reference solution: day6/solution/team.py.
"""

from __future__ import annotations

import operator
import pathlib
import sys
from typing import Annotated, List, Literal, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

try:
    import config  # noqa: F401
except Exception:  # pragma: no cover
    pass

from langgraph.graph import END, START, StateGraph

from day6._llm import get_llm, provider_label


# ═════════════════════════════════════════════════════════════════════════════
# TeamState — SHARED across the team.
# Every field is labelled so it's obvious which ones a worker is allowed to
# see (SHARED) and which live INSIDE a worker's sub-graph (PRIVATE).
# ═════════════════════════════════════════════════════════════════════════════
class TeamState(TypedDict, total=False):
    topic: str                                          # SHARED
    findings: List[dict]                                # SHARED (researcher → writer)
    draft: str                                          # SHARED (writer → supervisor)
    trace: Annotated[List[str], operator.add]           # SHARED · append-only log
    step: int                                           # SHARED · monotonic counter
    next: Literal["researcher", "writer", "FINISH"]     # SHARED · routing key
    final: str                                          # SHARED · aggregated result


MAX_STEPS = 12
TEAM_INVOKE_CONFIG: dict = {"recursion_limit": 25}


# ─── mocked "web" tool the researcher uses (offline & deterministic) ────────
_FAKE_CORPUS = {
    "definition": "A multi-agent team routes work through a supervisor that delegates to specialists.",
    "practice":   "In practice the supervisor decides who works next and aggregates the results.",
    "trade-off":  "Trade-off: more tokens and latency vs better modularity and clearer failure isolation.",
    "pitfall":    "Common pitfall: adopting multi-agent too early on tasks a single agent could handle.",
}


def web_search(query: str) -> str:
    """STUB tool. Returns a canned snippet keyed by the strongest word."""
    for k, v in _FAKE_CORPUS.items():
        if k in query.lower():
            return f'"{v}" — mock-source.example/{k}'
    return f'"{_FAKE_CORPUS["definition"]}" — mock-source.example/definition'


# ═════════════════════════════════════════════════════════════════════════════
# Worker #1 — RESEARCHER (its own sub-graph)
# ═════════════════════════════════════════════════════════════════════════════
class _ResearcherState(TypedDict, total=False):
    topic: str
    sub_questions: List[str]    # PRIVATE
    cursor: int                 # PRIVATE
    findings: List[dict]        # returned to shared state


def build_researcher():
    def plan(state):
        llm = get_llm()
        raw = llm.invoke(
            f"Break the topic '{state['topic']}' into 3 short sub-questions.\n"
            "Return ONE per line, no numbering."
        ).content
        subs = [ln.strip("-• \t") for ln in raw.splitlines() if ln.strip()][:3]
        if not subs:
            subs = [f"What is {state['topic']}?"]
        return {"sub_questions": subs, "cursor": 0, "findings": []}

    def search(state):
        i = state["cursor"]
        sub_q = state["sub_questions"][i]
        snippet = web_search(sub_q)
        return {
            "findings": state["findings"] + [{"sub_question": sub_q, "evidence": snippet}],
            "cursor": i + 1,
        }

    def more(state):
        return "search" if state["cursor"] < len(state["sub_questions"]) else END

    g = StateGraph(_ResearcherState)
    g.add_node("plan", plan)
    g.add_node("search", search)
    g.add_edge(START, "plan")
    g.add_edge("plan", "search")
    g.add_conditional_edges("search", more, {"search": "search", END: END})
    return g.compile()


# ═════════════════════════════════════════════════════════════════════════════
# Worker #2 — WRITER (its own sub-graph)
# ═════════════════════════════════════════════════════════════════════════════
class _WriterState(TypedDict, total=False):
    topic: str
    findings: List[dict]
    draft: str


def build_writer():
    def write(state):
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
# The TEAM graph
# ═════════════════════════════════════════════════════════════════════════════
def _log(state, msg):
    return {"step": (state.get("step") or 0) + 1, "trace": [msg]}


def build_team():
    researcher = build_researcher()
    writer = build_writer()

    def supervisor(state: TeamState) -> dict:
        """Decide the routing key. Rules:
             no findings  → "researcher"
             findings, no draft → "writer"
             draft present or step budget hit → "FINISH"
        """
        step = state.get("step") or 0

        # TODO(student): fill in the four-way decision below.
        # Hint: use state.get("findings") and state.get("draft"), and the
        # MAX_STEPS constant as a safety belt.
        decision: str = "FINISH"  # <-- replace this line

        return {**_log(state, f"supervisor → {decision}"), "next": decision}

    def researcher_node(state: TeamState) -> dict:
        # Hand the worker ONLY the shared slice it needs — that's context isolation.
        result = researcher.invoke({"topic": state["topic"]})
        return {
            **_log(state, f"researcher gathered {len(result['findings'])} findings"),
            "findings": result["findings"],
        }

    def writer_node(state: TeamState) -> dict:
        result = writer.invoke({"topic": state["topic"], "findings": state["findings"]})
        return {
            **_log(state, f"writer produced draft ({len(result['draft'])} chars)"),
            "draft": result["draft"],
        }

    def finalize(state: TeamState) -> dict:
        return {**_log(state, "FINISH → aggregate"), "final": state.get("draft", "")}

    def route(state: TeamState) -> str:
        # TODO(student): map the routing key to the next node name.
        # Return "researcher", "writer" or "finalize".
        return "finalize"  # <-- replace this line

    g = StateGraph(TeamState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher_node)
    g.add_node("writer", writer_node)
    g.add_node("finalize", finalize)
    g.add_edge(START, "supervisor")
    # TODO(student): add the conditional edge from "supervisor" using `route`,
    #                mapping the three routing keys to the three node names.
    # g.add_conditional_edges("supervisor", route, {...})
    g.add_edge("researcher", "supervisor")   # workers report BACK to supervisor
    g.add_edge("writer", "supervisor")
    g.add_edge("finalize", END)
    return g.compile()


# ─── demo runner ─────────────────────────────────────────────────────────────
def main():
    topic = " ".join(sys.argv[1:]).strip() or "multi-agent supervisor patterns"
    print("═" * 74)
    print(f"Day 6 · Multi-agent starter · provider: {provider_label()}")
    print(f"  topic: {topic}")
    print("═" * 74)

    team = build_team()
    final = team.invoke({"topic": topic}, TEAM_INVOKE_CONFIG)
    print("\nDelegation trace:")
    for i, line in enumerate(final.get("trace") or [], 1):
        print(f"  {i:>2}. {line}")
    print("\nFinal draft:")
    print(final.get("final") or "(finish the TODOs to produce a draft)")


if __name__ == "__main__":
    main()
