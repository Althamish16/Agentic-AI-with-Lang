"""
Day 3 STARTER — Bridge Day.

Turn Day 1's planner + Day 2's RAG into a LangGraph StateGraph with a loop:
    START → planner → executor → (loop while sub-questions remain) → synthesize → END

Fill every "# TODO (lab):" and run:
    python day3/starter/research_graph.py "How do vector databases power RAG?"
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


class ResearchState(TypedDict, total=False):
    question: str
    topic: str
    plan: List[str]
    cursor: int
    results: List[dict]
    final: str


def planner_node(state: ResearchState) -> dict:
    node("planner", "decompose the question (Day 1 chain)")
    plan = plan_research(state["question"])
    # TODO (lab): return a state update that sets topic, plan (sub_questions),
    #             cursor=0, and results=[].
    update = {}  # <- replace
    print_state(update, title="STATE after planner")
    return update


def executor_node(state: ResearchState) -> dict:
    i = state["cursor"]
    sub_q = state["plan"][i]
    node("executor", f"answer sub-question {i + 1}/{len(state['plan'])} via RAG (Day 2)")
    res = answer_question(sub_q, k=3)
    result = {"sub_question": sub_q, "answer": res["answer"], "sources": res["sources"]}
    # TODO (lab): append `result` to results and advance the cursor by 1.
    update = {}  # <- replace
    print_state({"cursor": update.get("cursor"), "just_answered": sub_q}, title="STATE after executor")
    return update


def route_after_executor(state: ResearchState) -> str:
    # TODO (lab): return "executor" while cursor < len(plan) (keep looping),
    #             otherwise return "synthesize".
    return "synthesize"  # <- fix so the loop actually loops


def synthesize_node(state: ResearchState) -> dict:
    node("synthesize", "combine sub-answers into the final report")
    findings = "\n\n".join(
        f"Sub-question: {r['sub_question']}\nAnswer: {r['answer']}\nSources: {r['sources']}"
        for r in state["results"]
    )
    llm = get_llm(temperature=0)
    prompt = (
        f"Topic: {state['topic']}\n\nFindings:\n\n{findings}\n\n"
        f"Write a cohesive answer to: '{state['question']}'. Keep inline [n] citations."
    )
    return {"final": llm.invoke(prompt).content}


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "executor")
    # TODO (lab): add the CONDITIONAL edge from "executor" using route_after_executor,
    #             mapping "executor" -> "executor" (loop) and "synthesize" -> "synthesize".
    # g.add_conditional_edges("executor", route_after_executor, {...})
    g.add_edge("synthesize", END)
    return g.compile()


def main():
    question = " ".join(sys.argv[1:]).strip() or "How do vector databases power RAG?"
    banner("Day 3 — LangGraph Planner → Executor → Synthesize")
    print(f"Question: {question}")

    app = build_graph()
    try:
        final_state = app.invoke({"question": question})
    except Exception as e:
        print(f"\n⚠ Starter not finished yet ({type(e).__name__}). Complete the `# TODO (lab):` "
              f"gaps in planner_node / executor_node / the conditional edge, then re-run.")
        print("  (See day3/solution/research_graph.py if you get stuck.)")
        return

    rule("═")
    print("FINAL ANSWER:\n")
    print(final_state.get("final", "(no final answer — finish the TODOs!)"))


if __name__ == "__main__":
    main()
