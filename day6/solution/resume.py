"""
Day 6 SOLUTION — long-running workflow that survives a "crash".

A multi-step research run (plan → research each sub-question → write) is compiled
with a SQLite checkpointer (Day 5). We interrupt it before the final "write" step to
simulate a crash; because state is on disk, a later run resumes exactly where it
stopped — even in a brand-new process.

    python day6/solution/resume.py start     # run, then stop before writing
    python day6/solution/resume.py resume     # continue from the checkpoint
    python day6/solution/resume.py            # both phases in one process (demo)
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

CHECKPOINT_DB = pathlib.Path(__file__).with_name("day6_run.sqlite")
THREAD = {"configurable": {"thread_id": "long-run-1"}}
QUESTION = "How do agents combine planning, tools, and memory?"


class RunState(TypedDict, total=False):
    question: str
    plan: List[str]
    cursor: int
    findings: List[dict]
    report: str


def _nodes(g: StateGraph):
    def plan_node(state: RunState) -> dict:
        node("plan", "decompose the question")
        p = plan_research(state["question"])
        return {"plan": p.sub_questions, "cursor": 0, "findings": []}

    def research_node(state: RunState) -> dict:
        i = state["cursor"]
        node("research", f"sub-question {i + 1}/{len(state['plan'])}")
        res = answer_question(state["plan"][i], k=2)
        finding = {"sub_question": state["plan"][i], "answer": res["answer"], "sources": res["sources"]}
        return {"findings": state["findings"] + [finding], "cursor": i + 1}

    def write_node(state: RunState) -> dict:
        node("write", "compose the final report")
        body = "\n\n".join(f"- {f['sub_question']}\n  {f['answer']}" for f in state["findings"])
        report = get_llm(temperature=0).invoke(
            f"Write a concise report answering '{state['question']}' from:\n\n{body}"
        ).content
        return {"report": report}

    def more(state: RunState) -> str:
        return "research" if state["cursor"] < len(state["plan"]) else "write"

    g.add_node("plan", plan_node)
    g.add_node("research", research_node)
    g.add_node("write", write_node)
    g.add_edge(START, "plan")
    g.add_edge("plan", "research")
    g.add_conditional_edges("research", more, {"research": "research", "write": "write"})
    g.add_edge("write", END)


def build_apps():
    """Two compilations sharing ONE checkpointer: one that stops before 'write'
    (to simulate the crash), one that runs straight through (to resume)."""
    checkpointer = get_sqlite_checkpointer(CHECKPOINT_DB)
    g = StateGraph(RunState)
    _nodes(g)
    app_interrupt = g.compile(checkpointer=checkpointer, interrupt_before=["write"])
    app_plain = g.compile(checkpointer=checkpointer)
    return app_interrupt, app_plain


def start(app_interrupt=None):
    banner("PHASE 1 — start the long run (will 'crash' before writing)")
    if app_interrupt is None:
        # fresh start: remove any old checkpoint so the demo is reproducible
        CHECKPOINT_DB.unlink(missing_ok=True)
        app_interrupt, _ = build_apps()
    app_interrupt.invoke({"question": QUESTION}, THREAD)
    snap = app_interrupt.get_state(THREAD)
    warn(f"💥 Interrupted before {snap.next} — simulating a crash.")
    ok(f"Progress saved to disk: {len(snap.values.get('findings', []))} findings researched.")


def resume(app_plain=None):
    banner("PHASE 2 — resume from the checkpoint")
    if app_plain is None:
        _, app_plain = build_apps()
    snap = app_plain.get_state(THREAD)
    if not snap.values:
        warn("No checkpoint found — run `resume.py start` first.")
        return
    print(f"  Loaded checkpoint: {len(snap.values.get('findings', []))} findings; next step = {snap.next}")
    final = app_plain.invoke(None, THREAD)  # None input = "continue from where we stopped"
    rule("═")
    print("FINAL REPORT (produced after resuming):\n")
    print(final["report"])


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "demo").lower()
    if mode == "start":
        start()
    elif mode == "resume":
        resume()
    else:
        # one-process demo: build both apps once so they share the checkpointer
        CHECKPOINT_DB.unlink(missing_ok=True)
        app_i, app_p = build_apps()
        start(app_i)
        print()
        resume(app_p)


if __name__ == "__main__":
    main()
