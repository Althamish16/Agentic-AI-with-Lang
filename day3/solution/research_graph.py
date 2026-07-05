"""
Day 3 SOLUTION — Bridge Day.

Turn Day 1's planner chain + Day 2's RAG into a LangGraph StateGraph:

    START → planner → executor → (loop while sub-questions remain) → synthesize → END

The conditional edge after `executor` is what makes this an *agent loop* rather than
a straight chain. We print state between nodes so the loop is visible.
"""

import pathlib
import sys
from typing import List, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langgraph.graph import END, START, StateGraph

from config import get_llm
from shared.planner import plan_research          # Day 1 building block
from shared.pretty import banner, node, print_state, rule
from shared.rag import answer_question            # Day 2 building block


# ── The shared State that flows through every node ───────────────────────────
class ResearchState(TypedDict, total=False):
    question: str          # the original research question
    topic: str             # planner's restatement
    plan: List[str]        # sub-questions to work through
    cursor: int            # index of the next sub-question
    results: List[dict]    # accumulated {sub_question, answer, sources}
    final: str             # synthesized answer


# ── Nodes: each returns a partial update that LangGraph merges into the state ─
def planner_node(state: ResearchState) -> dict:
    node("planner", "decompose the question (Day 1 chain)")
    plan = plan_research(state["question"])
    update = {"topic": plan.topic, "plan": plan.sub_questions, "cursor": 0, "results": []}
    print_state(update, keys=["topic", "plan", "cursor"], title="STATE after planner")
    return update


def executor_node(state: ResearchState) -> dict:
    i = state["cursor"]
    sub_q = state["plan"][i]
    node("executor", f"answer sub-question {i + 1}/{len(state['plan'])} via RAG (Day 2)")
    res = answer_question(sub_q, k=3)  # retrieve + answer with citations
    result = {"sub_question": sub_q, "answer": res["answer"], "sources": res["sources"]}
    update = {"results": state["results"] + [result], "cursor": i + 1}
    print_state(
        {"cursor": update["cursor"], "just_answered": sub_q, "sources": res["sources"]},
        title="STATE after executor",
    )
    return update


def route_after_executor(state: ResearchState) -> str:
    """CONDITIONAL EDGE: loop back to executor while work remains, else synthesize."""
    if state["cursor"] < len(state["plan"]):
        return "executor"   # ← the loop
    return "synthesize"


def synthesize_node(state: ResearchState) -> dict:
    node("synthesize", "combine sub-answers into the final report")
    findings = "\n\n".join(
        f"Sub-question: {r['sub_question']}\nAnswer: {r['answer']}\nSources: {r['sources']}"
        for r in state["results"]
    )
    llm = get_llm(temperature=0)
    prompt = (
        f"Topic: {state['topic']}\n\n"
        f"You researched these sub-questions:\n\n{findings}\n\n"
        "Write a cohesive, well-structured answer to the original question: "
        f"'{state['question']}'. Keep the inline [n] citations where relevant."
    )
    final = llm.invoke(prompt).content
    return {"final": final}


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "executor")
    # The conditional edge: executor either loops to itself or moves on.
    g.add_conditional_edges(
        "executor",
        route_after_executor,
        {"executor": "executor", "synthesize": "synthesize"},
    )
    g.add_edge("synthesize", END)
    return g.compile()


def main():
    question = " ".join(sys.argv[1:]).strip() or "How do vector databases power RAG?"
    banner("Day 3 — LangGraph Planner → Executor → Synthesize")
    print(f"Question: {question}")

    app = build_graph()
    final_state = app.invoke({"question": question})

    rule("═")
    print("FINAL ANSWER:\n")
    print(final_state["final"])


if __name__ == "__main__":
    main()
