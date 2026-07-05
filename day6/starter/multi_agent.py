"""
Day 6 STARTER — supervisor delegating to two sub-agents (each a sub-graph).

    supervisor → researcher (sub-graph) → supervisor → writer (sub-graph) → supervisor → END

Fill the "# TODO (lab):" gaps in the supervisor and run:
    python day6/starter/multi_agent.py "How do agents use memory and tools?"
"""

import pathlib
import sys
from typing import List, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langgraph.graph import END, START, StateGraph

from config import get_llm
from shared.planner import plan_research      # Day 1
from shared.pretty import banner, node, rule
from shared.rag import answer_question        # Day 2


class ResearchState(TypedDict, total=False):
    question: str
    plan: List[str]
    cursor: int
    findings: List[dict]


def build_researcher():
    def planner(state):
        return {"plan": plan_research(state["question"]).sub_questions, "cursor": 0, "findings": []}

    def executor(state):
        i = state["cursor"]
        res = answer_question(state["plan"][i], k=3)
        finding = {"sub_question": state["plan"][i], "answer": res["answer"], "sources": res["sources"]}
        return {"findings": state["findings"] + [finding], "cursor": i + 1}

    def more(state):
        return "executor" if state["cursor"] < len(state["plan"]) else END

    g = StateGraph(ResearchState)
    g.add_node("planner", planner)
    g.add_node("executor", executor)
    g.add_edge(START, "planner")
    g.add_edge("planner", "executor")
    g.add_conditional_edges("executor", more, {"executor": "executor", END: END})
    return g.compile()


class WriterState(TypedDict, total=False):
    question: str
    findings: List[dict]
    report: str


def build_writer():
    def write(state):
        body = "\n\n".join(f"{f['sub_question']}: {f['answer']} (sources {f['sources']})" for f in state["findings"])
        report = get_llm(temperature=0).invoke(
            f"Write a clear report answering '{state['question']}' from:\n\n{body}"
        ).content
        return {"report": report}

    g = StateGraph(WriterState)
    g.add_node("write", write)
    g.add_edge(START, "write")
    g.add_edge("write", END)
    return g.compile()


class SupervisorState(TypedDict, total=False):
    question: str
    findings: List[dict]
    report: str
    next: str


def build_supervisor():
    researcher = build_researcher()
    writer = build_writer()

    def supervisor(state: SupervisorState) -> dict:
        # TODO (lab): decide the next worker:
        #   no findings yet     -> "researcher"
        #   findings but no report -> "writer"
        #   otherwise           -> "DONE"
        decision = "DONE"  # <- replace with the rule above
        node("supervisor", f"delegate → {decision}")
        return {"next": decision}

    def researcher_node(state):
        node("researcher sub-agent", "plan + RAG over each sub-question")
        return {"findings": researcher.invoke({"question": state["question"]})["findings"]}

    def writer_node(state):
        node("writer sub-agent", "compose the report")
        return {"report": writer.invoke({"question": state["question"], "findings": state["findings"]})["report"]}

    def route(state):
        return END if state["next"] == "DONE" else state["next"]

    g = StateGraph(SupervisorState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher_node)
    g.add_node("writer", writer_node)
    g.add_edge(START, "supervisor")
    # TODO (lab): add the conditional edge from "supervisor" using `route`,
    #             mapping "researcher"->"researcher", "writer"->"writer", END->END.
    # g.add_conditional_edges("supervisor", route, {...})
    g.add_edge("researcher", "supervisor")
    g.add_edge("writer", "supervisor")
    return g.compile()


def main():
    question = " ".join(sys.argv[1:]).strip() or "How do agents use memory and tools?"
    banner("Day 6 — Multi-agent: supervisor → researcher → writer")
    print(f"Question: {question}")
    final = build_supervisor().invoke({"question": question}, {"recursion_limit": 25})
    rule("═")
    print("FINAL REPORT:\n")
    print(final.get("report", "(finish the supervisor TODOs to produce a report)"))


if __name__ == "__main__":
    main()
