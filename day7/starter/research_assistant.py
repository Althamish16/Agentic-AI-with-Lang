"""
Day 7 STARTER — the complete Research Assistant (capstone).

You'll add the three Day-7 mechanics to a self-contained agent:
  1) a REFLECTION route (auto-revise on a REVISE verdict)
  2) a HUMAN-IN-THE-LOOP gate using interrupt()
  3) RESUMING the paused graph with Command(resume=...)

Fill every "# TODO (lab):" and run:
    python day7/starter/research_assistant.py --auto "Should I use similarity or MMR retrieval?"
"""

import pathlib
import sys
from typing import List, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from config import get_llm, setup_langsmith
from shared.planner import plan_research     # Day 1
from shared.pretty import banner, node, rule, warn
from shared.rag import answer_question       # Day 2

MAX_AUTO_REVISIONS = 1


class AgentState(TypedDict, total=False):
    question: str
    plan: List[str]
    cursor: int
    findings: List[dict]
    draft: str
    verdict: str
    revisions: int
    approved: bool
    final: str


def _plan(state):
    node("plan", "decompose the question")
    return {"plan": plan_research(state["question"]).sub_questions, "cursor": 0, "findings": [], "revisions": 0}


def _research(state):
    i = state["cursor"]
    node("research", f"sub-question {i + 1}/{len(state['plan'])}")
    res = answer_question(state["plan"][i], k=3)
    return {"findings": state["findings"] + [{"sub_question": state["plan"][i], "answer": res["answer"], "sources": res["sources"]}], "cursor": i + 1}


def _research_more(state):
    return "research" if state["cursor"] < len(state["plan"]) else "write"


def _write(state):
    node("write", f"compose report (revision #{state.get('revisions', 0) + 1})")
    body = "\n\n".join(f"{f['sub_question']}: {f['answer']} {f['sources']}" for f in state["findings"])
    draft = get_llm(temperature=0).invoke(f"Write a cited report answering '{state['question']}' from:\n{body}").content
    return {"draft": draft, "revisions": state.get("revisions", 0) + 1}


def _reflect(state):
    node("reflect", "self-critique the draft")
    critique = get_llm(temperature=0).invoke(
        f"Critique this draft for the question '{state['question']}'. End with 'VERDICT: PASS' or 'VERDICT: REVISE'.\n\n{state['draft']}"
    ).content
    verdict = "REVISE" if "REVISE" in critique.upper().split("VERDICT:")[-1] else "PASS"
    return {"verdict": verdict}


def _route_after_reflect(state):
    # TODO (lab): return "write" to auto-revise when verdict == "REVISE" AND
    #             revisions <= MAX_AUTO_REVISIONS; otherwise return "human_approval".
    return "human_approval"  # <- replace with the real rule


def _human_approval(state):
    node("human_approval", "waiting for a human decision")
    # TODO (lab): call interrupt({...}) with the draft so the graph PAUSES here and
    #             the caller can resume with the human's decision. Assign it to `decision`.
    decision = "approve"  # <- replace with: interrupt({"draft": state["draft"], "message": "Approve?"})
    approved = str(decision).strip().lower() in {"approve", "approved", "yes", "y"}
    return {"approved": approved}


def _publish(state):
    node("publish", "finalize the report")
    tag = "APPROVED" if state.get("approved") else "PUBLISHED WITHOUT APPROVAL"
    return {"final": f"{state['draft']}\n\n--- {tag} ---"}


def build_agent():
    g = StateGraph(AgentState)
    for name, fn in [("plan", _plan), ("research", _research), ("write", _write),
                     ("reflect", _reflect), ("human_approval", _human_approval), ("publish", _publish)]:
        g.add_node(name, fn)
    g.add_edge(START, "plan")
    g.add_edge("plan", "research")
    g.add_conditional_edges("research", _research_more, {"research": "research", "write": "write"})
    g.add_edge("write", "reflect")
    g.add_conditional_edges("reflect", _route_after_reflect, {"write": "write", "human_approval": "human_approval"})
    g.add_edge("human_approval", "publish")
    g.add_edge("publish", END)
    # interrupt() REQUIRES a checkpointer.
    return g.compile(checkpointer=MemorySaver())


def main():
    args = sys.argv[1:]
    auto = "--auto" in args
    if auto:
        args.remove("--auto")
    question = " ".join(args).strip() or "Should I use similarity or MMR retrieval?"

    banner("Day 7 — Research Assistant (starter)")
    setup_langsmith()
    app = build_agent()
    cfg = {"configurable": {"thread_id": "day7-starter"}}

    result = app.invoke({"question": question}, cfg)

    # If the graph paused at the human gate, resume it.
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        rule()
        warn("HUMAN APPROVAL REQUIRED:")
        print(payload.get("draft", "")[:800], "...\n")
        decision = "approve" if auto else (input("Approve publish? [y/N]: ").strip() or "no")
        # TODO (lab): resume the paused graph with the decision:
        #             result = app.invoke(Command(resume=decision), cfg)
        pass

    final = app.get_state(cfg).values.get("final", "(finish the TODOs to publish)")
    rule("═")
    print("FINAL REPORT:\n")
    print(final)


if __name__ == "__main__":
    main()
