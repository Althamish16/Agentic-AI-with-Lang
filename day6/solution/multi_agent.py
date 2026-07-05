"""
Day 6 SOLUTION — a supervisor delegating to two sub-agents (each a sub-graph).

    supervisor → researcher (sub-graph) → supervisor → writer (sub-graph) → supervisor → END

• researcher sub-agent: plan (Day 1) + retrieve per sub-question (Day 2)  → findings
• writer sub-agent:      compose a polished report from the findings
• supervisor:            decides who works next, then aggregates
"""

import pathlib
import sys
from typing import List, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langgraph.graph import END, START, StateGraph

from config import get_llm
from shared.planner import plan_research      # Day 1
from shared.pretty import banner, node, print_state, rule
from shared.rag import answer_question        # Day 2


# ─────────────────────────────────────────────────────────────────────────────
# Sub-agent #1: the RESEARCHER (its own sub-graph: planner → executor loop)
# ─────────────────────────────────────────────────────────────────────────────
class ResearchState(TypedDict, total=False):
    question: str
    plan: List[str]
    cursor: int
    findings: List[dict]


def build_researcher():
    def planner(state: ResearchState) -> dict:
        p = plan_research(state["question"])
        return {"plan": p.sub_questions, "cursor": 0, "findings": []}

    def executor(state: ResearchState) -> dict:
        i = state["cursor"]
        sub_q = state["plan"][i]
        res = answer_question(sub_q, k=3)
        finding = {"sub_question": sub_q, "answer": res["answer"], "sources": res["sources"]}
        return {"findings": state["findings"] + [finding], "cursor": i + 1}

    def more(state: ResearchState) -> str:
        return "executor" if state["cursor"] < len(state["plan"]) else END

    g = StateGraph(ResearchState)
    g.add_node("planner", planner)
    g.add_node("executor", executor)
    g.add_edge(START, "planner")
    g.add_edge("planner", "executor")
    g.add_conditional_edges("executor", more, {"executor": "executor", END: END})
    return g.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Sub-agent #2: the WRITER (a small sub-graph that composes the report)
# ─────────────────────────────────────────────────────────────────────────────
class WriterState(TypedDict, total=False):
    question: str
    findings: List[dict]
    report: str


def build_writer():
    def write(state: WriterState) -> dict:
        llm = get_llm(temperature=0)
        body = "\n\n".join(
            f"Sub-question: {f['sub_question']}\nAnswer: {f['answer']}\nSources: {f['sources']}"
            for f in state["findings"]
        )
        report = llm.invoke(
            f"Write a clear, well-structured research report answering: '{state['question']}'.\n"
            f"Base it ONLY on these findings and keep the [n] citations:\n\n{body}"
        ).content
        return {"report": report}

    g = StateGraph(WriterState)
    g.add_node("write", write)
    g.add_edge(START, "write")
    g.add_edge("write", END)
    return g.compile()


# ─────────────────────────────────────────────────────────────────────────────
# The SUPERVISOR graph: delegates to sub-agents (as nodes) and aggregates.
# ─────────────────────────────────────────────────────────────────────────────
class SupervisorState(TypedDict, total=False):
    question: str
    findings: List[dict]
    report: str
    next: str


def build_supervisor():
    researcher = build_researcher()
    writer = build_writer()

    def supervisor(state: SupervisorState) -> dict:
        # A simple rule-based supervisor (in production this could be an LLM).
        if not state.get("findings"):
            decision = "researcher"
        elif not state.get("report"):
            decision = "writer"
        else:
            decision = "DONE"
        node("supervisor", f"delegate → {decision}")
        return {"next": decision}

    def researcher_node(state: SupervisorState) -> dict:
        node("researcher sub-agent", "plan + RAG over each sub-question")
        result = researcher.invoke({"question": state["question"]})
        print(f"  ↳ gathered {len(result['findings'])} findings")
        return {"findings": result["findings"]}

    def writer_node(state: SupervisorState) -> dict:
        node("writer sub-agent", "compose the report from findings")
        result = writer.invoke({"question": state["question"], "findings": state["findings"]})
        return {"report": result["report"]}

    def route(state: SupervisorState) -> str:
        return END if state["next"] == "DONE" else state["next"]

    g = StateGraph(SupervisorState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher_node)
    g.add_node("writer", writer_node)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route, {"researcher": "researcher", "writer": "writer", END: END})
    g.add_edge("researcher", "supervisor")  # report back to the supervisor
    g.add_edge("writer", "supervisor")
    return g.compile()


def main():
    question = " ".join(sys.argv[1:]).strip() or "How do agents use memory and tools?"
    banner("Day 6 — Multi-agent: supervisor → researcher → writer")
    print(f"Question: {question}")

    app = build_supervisor()
    final = app.invoke({"question": question}, {"recursion_limit": 25})

    rule("═")
    print("FINAL REPORT:\n")
    print(final["report"])


if __name__ == "__main__":
    main()
