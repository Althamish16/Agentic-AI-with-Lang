"""
Day 5 · Persistence — STARTER
================================

Fill in the four `# TODO (lab)` blocks to make the agent durable.

Run it (repeatedly! same thread_id each time):

    python day5/starter/memory_agent.py                 # normal run
    python day5/starter/memory_agent.py crash           # crash mid-run
    python day5/starter/memory_agent.py resume          # resume from disk

The four things you'll add:

  (1) Compile the graph with a **SqliteSaver checkpointer** and use a
      **thread_id** so state survives across runs. Prove it with `get_state()`.

  (2) Design the **State TypedDict** so it holds messages + plan + cursor +
      findings + tool_outputs. Use the `add_messages` reducer for messages so
      updates MERGE instead of clobbering.

  (3) Add a **compact node** that summarises the oldest turns once the
      conversation grows past a threshold, keeping the last N verbatim.

  (4) Add **long-term memory** — write facts to a vector store and recall
      the relevant ones back into short-term state.

Hints
-----
• `get_state(cfg)` returns a snapshot — `.values` is your state, `.next` is
  the next node to run. That's how you prove resume worked.
• `thread_id` must match EXACTLY between runs. A typo silently starts fresh.
• Idempotency: your `act` node should skip work if it's already in
  `tool_outputs` — otherwise resume double-fires side effects.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — MUST import first (loads .env)

import sqlite3  # noqa: E402
from typing import Annotated, List, TypedDict  # noqa: E402

from langchain_core.messages import (  # noqa: E402
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.graph.message import add_messages  # noqa: E402

from config import get_llm  # noqa: E402
from shared.memory import clear_long_term_memory, recall, remember  # noqa: E402


CHECKPOINT_DB = pathlib.Path(__file__).with_name("runs.db")
COMPACT_THRESHOLD = 8
KEEP_LAST_N = 4


# ─────────────────────────────────────────────────────────────────────────────
# TODO (lab · pillar 2) — STATE DESIGN
# Fill in the missing fields. Use `add_messages` on `messages` so updates
# MERGE (append) instead of overwriting.
# ─────────────────────────────────────────────────────────────────────────────
class ResearchState(TypedDict, total=False):
    # messages: Annotated[List[BaseMessage], add_messages]   # <- add me!
    question: str
    # plan: List[str]
    # cursor: int
    # findings: List[dict]
    # tool_outputs: dict           # dedup keys so replayed steps don't double-fire
    # long_term_recall: List[str]
    # compaction_count: int


# ─────────────────────────────────────────────────────────────────────────────
# TODO (lab · pillar 4) — LONG-TERM RECALL node
# Pull the top-k relevant durable facts into short-term state as a SystemMessage.
# ─────────────────────────────────────────────────────────────────────────────
def recall_node(state: ResearchState) -> dict:
    # hits = recall(state.get("question", ""), k=3)
    # if not hits: return {"long_term_recall": []}
    # note = SystemMessage(content="[Relevant long-term memories]\n- " + "\n- ".join(hits))
    # return {"long_term_recall": hits, "messages": [note]}
    return {}


def plan_node(state: ResearchState) -> dict:
    # IDEMPOTENT — reuse existing plan on resume.
    if state.get("plan"):
        return {}
    llm = get_llm(temperature=0)
    text = llm.invoke(
        "Break the user's research question into 3 short, specific sub-questions.\n"
        "Return ONE per line, no numbering.\n\n"
        f"Question: {state['question']}"
    ).content
    plan = [line.strip("-• \t") for line in text.splitlines() if line.strip()][:3]
    return {
        "plan": plan,
        "cursor": 0,
        "findings": [],
        "tool_outputs": {},
        "messages": [AIMessage(content="Plan:\n- " + "\n- ".join(plan))],
    }


def act_node(state: ResearchState) -> dict:
    i = state["cursor"]
    sub_q = state["plan"][i]
    key = f"act:{i}"
    tool_outputs = dict(state.get("tool_outputs") or {})

    # TODO (lab · idempotency) — if `key` is in tool_outputs, skip re-running
    # and just advance the cursor:
    #     if key in tool_outputs:
    #         return {"cursor": i + 1}

    llm = get_llm(temperature=0)
    answer = llm.invoke(f"Answer this in ONE short sentence:\n\n{sub_q}").content
    tool_outputs[key] = answer
    return {
        "cursor": i + 1,
        "findings": (state.get("findings") or []) + [{"sub_question": sub_q, "answer": answer}],
        "tool_outputs": tool_outputs,
        "messages": [AIMessage(content=f"{sub_q} → {answer}")],
    }


# ─────────────────────────────────────────────────────────────────────────────
# TODO (lab · pillar 3) — COMPACTION node
# Once messages > COMPACT_THRESHOLD: summarise everything BUT the last
# KEEP_LAST_N with the LLM, then replace the message list with
# [summary, *last_N]. Print token counts before vs. after so the shrink is
# visible.
# ─────────────────────────────────────────────────────────────────────────────
def compact_node(state: ResearchState) -> dict:
    msgs = state.get("messages") or []
    if len(msgs) <= KEEP_LAST_N + 1:
        return {}
    # llm = get_llm(temperature=0)
    # old, recent = msgs[:-KEEP_LAST_N], msgs[-KEEP_LAST_N:]
    # summary = llm.invoke("Summarise:\n\n" + "\n".join(f"{m.type}: {m.content}" for m in old)).content
    # drops = [RemoveMessage(id=m.id) for m in old if getattr(m, "id", None)]
    # return {"messages": [*drops, SystemMessage(content=summary), *recent],
    #         "compaction_count": (state.get("compaction_count") or 0) + 1}
    return {}


def route_after_act(state: ResearchState) -> str:
    if len(state.get("messages") or []) > COMPACT_THRESHOLD:
        return "compact"
    if state["cursor"] < len(state.get("plan") or []):
        return "act"
    return "answer"


def route_after_compact(state: ResearchState) -> str:
    return "act" if state["cursor"] < len(state.get("plan") or []) else "answer"


def answer_node(state: ResearchState) -> dict:
    llm = get_llm(temperature=0)
    body = "\n".join(f"- {f['sub_question']}: {f['answer']}" for f in state["findings"])
    final = llm.invoke(f"Answer '{state['question']}' in 3 sentences from:\n{body}").content
    # STRETCH: write a durable memory here so future runs can recall it.
    # remember(f"Topic covered: {state['question']}", metadata={"kind": "session_summary"})
    return {"messages": [AIMessage(content=final)]}


class SimulatedCrash(RuntimeError):
    pass


def crash_node(state):
    raise SimulatedCrash("kaboom — simulated crash to test resume")


def build_agent(checkpointer, *, crash_after_first_act: bool = False):
    g = StateGraph(ResearchState)
    g.add_node("recall", recall_node)
    g.add_node("plan", plan_node)
    g.add_node("act", act_node)
    g.add_node("compact", compact_node)
    g.add_node("answer", answer_node)
    g.add_edge(START, "recall")
    g.add_edge("recall", "plan")
    g.add_edge("plan", "act")
    if crash_after_first_act:
        g.add_node("boom", crash_node)
        g.add_edge("act", "boom")
        g.add_edge("boom", END)
    else:
        g.add_conditional_edges("act", route_after_act,
                                {"act": "act", "compact": "compact", "answer": "answer"})
        g.add_conditional_edges("compact", route_after_compact,
                                {"act": "act", "answer": "answer"})
        g.add_edge("answer", END)

    # TODO (lab · pillar 1) — compile WITH the checkpointer:
    #     return g.compile(checkpointer=checkpointer)
    return g.compile()


def _open_checkpointer() -> SqliteSaver:
    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    return SqliteSaver(conn)


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").lower()

    # TODO (lab · pillar 1) — use the SAME thread_id every run so resume works.
    cfg = {"configurable": {"thread_id": "learner-thread-1"}}

    if mode == "crash":
        agent = build_agent(_open_checkpointer(), crash_after_first_act=True)
        try:
            agent.invoke({"question": "What are the key ideas in agent memory?"}, cfg)
        except SimulatedCrash as e:
            print("caught:", e)
        print("state on disk:", agent.get_state(cfg).values.get("cursor"))
        return

    if mode == "resume":
        agent = build_agent(_open_checkpointer())
        snap = agent.get_state(cfg)
        before = snap.values
        print("before resume · cursor =", before.get("cursor"), "findings =", len(before.get("findings") or []))
        # If the crash graph left `next=['boom']`, rebase the pending pointer
        # onto the healthy graph's routing by re-recording the last node.
        if list(snap.next) in ([], ["boom"]):
            agent.update_state(cfg, values={}, as_node="act")
        agent.invoke(None, cfg)  # None = continue from checkpoint
        after = agent.get_state(cfg).values
        print("after  resume · cursor =", after.get("cursor"), "findings =", len(after.get("findings") or []))
        return

    # Normal end-to-end run.
    agent = build_agent(_open_checkpointer())
    agent.invoke({"question": "How do vector databases power RAG?"}, cfg)
    snap = agent.get_state(cfg)
    print("messages:", len(snap.values.get("messages", [])))
    print("plan    :", snap.values.get("plan"))


if __name__ == "__main__":
    main()
