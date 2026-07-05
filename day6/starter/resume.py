"""
Day 6 STARTER — long-running workflow that survives a "crash".

A multi-step run is compiled with a SQLite checkpointer (Day 5) and interrupted
before "write" to simulate a crash. Complete the resume step and run:

    python day6/starter/resume.py            # both phases in one process
    python day6/starter/resume.py start      # run then stop before writing
    python day6/starter/resume.py resume     # continue from the checkpoint
"""

import pathlib
import sys
from typing import List, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langgraph.graph import END, START, StateGraph

from config import get_llm
from shared.memory import get_sqlite_checkpointer   # Day 5 durable checkpointer
from shared.planner import plan_research            # Day 1
from shared.pretty import banner, node, ok, rule, warn
from shared.rag import answer_question              # Day 2

CHECKPOINT_DB = pathlib.Path(__file__).with_name("day6_run_starter.sqlite")
THREAD = {"configurable": {"thread_id": "long-run-1"}}
QUESTION = "How do agents combine planning, tools, and memory?"


class RunState(TypedDict, total=False):
    question: str
    plan: List[str]
    cursor: int
    findings: List[dict]
    report: str


def _nodes(g: StateGraph):
    def plan_node(state):
        node("plan", "decompose the question")
        return {"plan": plan_research(state["question"]).sub_questions, "cursor": 0, "findings": []}

    def research_node(state):
        i = state["cursor"]
        node("research", f"sub-question {i + 1}/{len(state['plan'])}")
        res = answer_question(state["plan"][i], k=2)
        finding = {"sub_question": state["plan"][i], "answer": res["answer"], "sources": res["sources"]}
        return {"findings": state["findings"] + [finding], "cursor": i + 1}

    def write_node(state):
        node("write", "compose the final report")
        body = "\n\n".join(f"- {f['sub_question']}\n  {f['answer']}" for f in state["findings"])
        return {"report": get_llm(temperature=0).invoke(f"Write a concise report on '{state['question']}':\n\n{body}").content}

    def more(state):
        return "research" if state["cursor"] < len(state["plan"]) else "write"

    g.add_node("plan", plan_node)
    g.add_node("research", research_node)
    g.add_node("write", write_node)
    g.add_edge(START, "plan")
    g.add_edge("plan", "research")
    g.add_conditional_edges("research", more, {"research": "research", "write": "write"})
    g.add_edge("write", END)


def build_apps():
    checkpointer = get_sqlite_checkpointer(CHECKPOINT_DB)
    g = StateGraph(RunState)
    _nodes(g)
    # interrupt_before stops the graph before "write" so we can simulate a crash.
    return g.compile(checkpointer=checkpointer, interrupt_before=["write"]), g.compile(checkpointer=checkpointer)


def start(app_interrupt=None):
    banner("PHASE 1 — start the long run (will 'crash' before writing)")
    if app_interrupt is None:
        CHECKPOINT_DB.unlink(missing_ok=True)
        app_interrupt, _ = build_apps()
    app_interrupt.invoke({"question": QUESTION}, THREAD)
    snap = app_interrupt.get_state(THREAD)
    warn(f"💥 Interrupted before {snap.next} — simulating a crash.")
    ok(f"Progress saved: {len(snap.values.get('findings', []))} findings researched.")


def resume(app_plain=None):
    banner("PHASE 2 — resume from the checkpoint")
    if app_plain is None:
        _, app_plain = build_apps()
    snap = app_plain.get_state(THREAD)
    if not snap.values:
        warn("No checkpoint found — run `resume.py start` first.")
        return
    print(f"  Loaded checkpoint: {len(snap.values.get('findings', []))} findings; next = {snap.next}")

    # TODO (lab): resume the run from the checkpoint by invoking with None as input:
    #             final = app_plain.invoke(None, THREAD)
    final = None  # <- replace
    if final is None:
        warn("Finish the TODO to resume the run.")
        return
    rule("═")
    print("FINAL REPORT (after resuming):\n")
    print(final["report"])


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "demo").lower()
    if mode == "start":
        start()
    elif mode == "resume":
        resume()
    else:
        CHECKPOINT_DB.unlink(missing_ok=True)
        app_i, app_p = build_apps()
        start(app_i)
        print()
        resume(app_p)


if __name__ == "__main__":
    main()
