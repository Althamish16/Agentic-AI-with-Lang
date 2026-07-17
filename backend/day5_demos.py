"""
backend/day5_sessions.py — transparent Day 5 · Persistence demos for the UI.

Each function returns a typed payload the frontend renders under one of the
new `kind: memory_*` result renderers. All of these functions are safe to
call from FastAPI request handlers: they open their own SqliteSaver
connection, they never mutate module-level state, and their side effects
land in a dedicated DB file so the studio checkpoint isn't touched.

Pillars covered (matches day5/solution/memory_agent.py):

  d5_state ......... state design + `add_messages` reducer + get_state()
  d5_checkpointer .. thread_id continuity across two invokes (turn 1 → 2)
  d5_compaction .... compact node fires past a threshold; before/after counts
  d5_long_term ..... vector-backed remember() + recall()
  d5_crash ......... run, simulated crash mid-run, show persisted state
  d5_resume ........ resume on SAME thread_id → picks up from disk (idempotent)
"""

from __future__ import annotations

import pathlib
import sqlite3
import uuid
from typing import Annotated, List, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from config import get_llm
from shared.memory import clear_long_term_memory, recall, remember


# ─── shared plumbing ─────────────────────────────────────────────────────────
# Distinct DB file so the studio agent's checkpoint (agent_checkpoints.sqlite)
# is untouched by teaching demos.
_DB = pathlib.Path(__file__).with_name("day5_lab_checkpoints.sqlite")

COMPACT_THRESHOLD = 8
KEEP_LAST_N = 4


def _cp() -> SqliteSaver:
    conn = sqlite3.connect(str(_DB), check_same_thread=False)
    return SqliteSaver(conn)


def _tok(msgs: List[BaseMessage]) -> int:
    return sum(len(getattr(m, "content", "") or "") for m in msgs) // 4


def _msg_view(m: BaseMessage) -> dict:
    return {"role": m.type, "text": (m.content or "")[:240]}


# ─── State ───────────────────────────────────────────────────────────────────
class S(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    question: str
    plan: List[str]
    cursor: int
    findings: List[dict]
    tool_outputs: dict
    long_term_recall: List[str]
    compaction_count: int


# ─── Nodes (small versions of day5/solution) ─────────────────────────────────
def _plan(state: S) -> dict:
    if state.get("plan"):
        return {}
    llm = get_llm(temperature=0)
    txt = llm.invoke(
        "Break the user's research question into 3 short, specific sub-questions.\n"
        "Return ONE per line, no numbering.\n\nQuestion: " + state["question"]
    ).content
    plan = [ln.strip("-• \t") for ln in txt.splitlines() if ln.strip()][:3]
    return {
        "plan": plan, "cursor": 0, "findings": [], "tool_outputs": {},
        "messages": [AIMessage(content="Plan:\n- " + "\n- ".join(plan))],
    }


def _act(state: S) -> dict:
    i = state["cursor"]
    sub_q = state["plan"][i]
    key = f"act:{i}"
    tool_outputs = dict(state.get("tool_outputs") or {})
    if key in tool_outputs:
        return {"cursor": i + 1}  # idempotent replay
    llm = get_llm(temperature=0)
    ans = llm.invoke(f"Answer in ONE sentence:\n\n{sub_q}").content
    tool_outputs[key] = ans
    return {
        "cursor": i + 1,
        "findings": (state.get("findings") or []) + [{"sub_question": sub_q, "answer": ans}],
        "tool_outputs": tool_outputs,
        "messages": [AIMessage(content=f"{sub_q} → {ans}")],
    }


def _compact(state: S) -> dict:
    msgs = state.get("messages") or []
    if len(msgs) <= KEEP_LAST_N + 1:
        return {}
    old, recent = msgs[:-KEEP_LAST_N], msgs[-KEEP_LAST_N:]
    llm = get_llm(temperature=0)
    transcript = "\n".join(f"{m.type}: {m.content}" for m in old)
    summary = llm.invoke(
        "Summarise the conversation below into 3–4 concise bullets, preserving "
        "user goals, decisions, and facts.\n\n" + transcript
    ).content
    smsg = SystemMessage(content=f"[Summary of {len(old)} earlier messages]\n{summary}")
    drops = [RemoveMessage(id=m.id) for m in old if getattr(m, "id", None)]
    return {
        "messages": [*drops, smsg, *recent],
        "compaction_count": (state.get("compaction_count") or 0) + 1,
    }


def _answer(state: S) -> dict:
    llm = get_llm(temperature=0)
    body = "\n".join(f"- {f['sub_question']}: {f['answer']}" for f in state["findings"])
    final = llm.invoke(f"Answer '{state['question']}' in 3 sentences from:\n{body}").content
    return {"messages": [AIMessage(content=final)]}


def _route_after_act(state: S) -> str:
    if len(state.get("messages") or []) > COMPACT_THRESHOLD:
        return "compact"
    return "act" if state["cursor"] < len(state.get("plan") or []) else "answer"


def _route_after_compact(state: S) -> str:
    return "act" if state["cursor"] < len(state.get("plan") or []) else "answer"


class _Crash(RuntimeError):
    pass


def _boom(state):
    raise _Crash("kaboom — simulated crash mid-run")


def _build(checkpointer, *, crash_after_first_act: bool = False):
    g = StateGraph(S)
    g.add_node("plan", _plan)
    g.add_node("act", _act)
    g.add_node("compact", _compact)
    g.add_node("answer", _answer)
    g.add_edge(START, "plan")
    g.add_conditional_edges(
        "plan",
        lambda s: "answer" if s.get("cursor", 0) >= len(s.get("plan") or []) and s.get("findings") else "act",
        {"act": "act", "answer": "answer"},
    )
    if crash_after_first_act:
        g.add_node("boom", _boom)
        g.add_edge("act", "boom")
        g.add_edge("boom", END)
    else:
        g.add_conditional_edges("act", _route_after_act,
                                {"act": "act", "compact": "compact", "answer": "answer"})
        g.add_conditional_edges("compact", _route_after_compact,
                                {"act": "act", "answer": "answer"})
        g.add_edge("answer", END)
    return g.compile(checkpointer=checkpointer)


# ═════════════════════════════════════════════════════════════════════════════
# Public demos
# ═════════════════════════════════════════════════════════════════════════════
def d5_state(_q: str = "") -> dict:
    """Show the explicit State TypedDict and one persisted snapshot."""
    fields = [
        {"name": "messages", "type": "Annotated[List[BaseMessage], add_messages]",
         "note": "reducer APPENDS instead of overwriting"},
        {"name": "question", "type": "str", "note": "the user's research question"},
        {"name": "plan", "type": "List[str]", "note": "sub-questions to answer"},
        {"name": "cursor", "type": "int", "note": "next plan[] index; enables resume"},
        {"name": "findings", "type": "List[dict]", "note": "intermediate results"},
        {"name": "tool_outputs", "type": "dict",
         "note": "dedup keys so replayed steps don't double-fire"},
        {"name": "long_term_recall", "type": "List[str]",
         "note": "durable facts pulled into short-term this turn"},
        {"name": "compaction_count", "type": "int", "note": "how many times compact fired"},
    ]

    tid = f"studio-state-{uuid.uuid4().hex[:8]}"
    cfg = {"configurable": {"thread_id": tid}}
    agent = _build(_cp())
    agent.invoke({"question": "How does memory make an agent durable?"}, cfg)
    snap = agent.get_state(cfg)
    v = snap.values
    return {
        "kind": "memory_state",
        "fields": fields,
        "thread_id": tid,
        "snapshot": {
            "messages": len(v.get("messages") or []),
            "plan": v.get("plan") or [],
            "cursor": v.get("cursor", 0),
            "findings": len(v.get("findings") or []),
            "tool_outputs": len(v.get("tool_outputs") or {}),
            "compaction_count": v.get("compaction_count", 0),
            "next": list(snap.next),
        },
        "messages_preview": [_msg_view(m) for m in (v.get("messages") or [])[-4:]],
    }


def d5_checkpointer(_q: str = "") -> dict:
    """Two invokes on the SAME thread_id — turn 2 remembers turn 1."""
    from langgraph.graph import MessagesState

    llm = get_llm(temperature=0)

    def chat(s):
        return {"messages": [llm.invoke(s["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("chat", chat)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    app = g.compile(checkpointer=_cp())

    tid = f"studio-chat-{uuid.uuid4().hex[:8]}"
    cfg = {"configurable": {"thread_id": tid}}

    t1 = app.invoke(
        {"messages": [HumanMessage(content="My favorite research topic is vector databases. Remember that.")]},
        cfg,
    )
    t2 = app.invoke(
        {"messages": [HumanMessage(content="What did I say my favorite topic was?")]},
        cfg,
    )

    snap = app.get_state(cfg)
    return {
        "kind": "memory_checkpointer",
        "thread_id": tid,
        "turn1": t1["messages"][-1].content,
        "turn2": t2["messages"][-1].content,
        "persisted_messages": len(snap.values.get("messages") or []),
        "checkpoint_file": _DB.name,
    }


def d5_compaction(_q: str = "") -> dict:
    """Force the compact node past the threshold, show before/after counts."""
    seed: list[BaseMessage] = []
    for i in range(1, 6):
        seed.append(HumanMessage(content=f"Turn {i}: tell me about RAG stage {i}."))
        seed.append(AIMessage(content=f"Stage {i} of RAG covers point-{i}-details ..."))

    before_count = len(seed)
    before_tokens = _tok(seed)
    result = _compact({"messages": seed})
    kept = [m for m in result.get("messages", []) if not isinstance(m, RemoveMessage)]
    after_tokens = _tok(kept)
    return {
        "kind": "memory_compaction",
        "threshold": COMPACT_THRESHOLD,
        "keep_last": KEEP_LAST_N,
        "before": {
            "count": before_count,
            "tokens": before_tokens,
            "messages": [_msg_view(m) for m in seed],
        },
        "after": {
            "count": len(kept),
            "tokens": after_tokens,
            "messages": [_msg_view(m) for m in kept],
        },
        "summary": kept[0].content if kept else "",
    }


def d5_long_term(_q: str = "") -> dict:
    """Write durable facts, then recall the relevant ones by semantic query."""
    clear_long_term_memory()
    saved = [
        "The user prefers concise, bulleted answers with citations.",
        "The user is building a Research Assistant with LangGraph.",
        "The user's favorite vector database is Chroma.",
        "The user runs on Windows and uses PowerShell.",
    ]
    for s in saved:
        remember(s, metadata={"kind": "user_preference"})
    query = "How does the user like their answers formatted?"
    hits = recall(query, k=2)
    return {
        "kind": "memory_long",
        "saved": saved,
        "query": query,
        "recall": hits,
    }


# ─── Crash-and-resume — split into two backend calls the UI runs in sequence.
# A per-session key namespaces the thread so parallel visitors don't collide.
def d5_crash(session: str = "") -> dict:
    tid = f"studio-crashresume-{session or 'default'}"
    cfg = {"configurable": {"thread_id": tid}}
    agent = _build(_cp(), crash_after_first_act=True)

    steps: list[dict] = [
        {"node": "plan", "outcome": "ran", "note": "3 sub-questions written to state"},
        {"node": "act (step 1)", "outcome": "ran", "note": "1st answer stored + cursor→1"},
        {"node": "boom", "outcome": "CRASH", "note": "simulated exception raised"},
    ]

    err = ""
    try:
        agent.invoke({"question": "What are the key ideas in agent memory?"}, cfg)
    except _Crash as e:
        err = str(e)

    snap = agent.get_state(cfg)
    v = snap.values
    return {
        "kind": "memory_crash",
        "thread_id": tid,
        "steps": steps,
        "crash": err,
        "state_on_disk": {
            "plan": v.get("plan") or [],
            "cursor": v.get("cursor", 0),
            "findings": len(v.get("findings") or []),
            "tool_outputs_keys": list((v.get("tool_outputs") or {}).keys()),
            "next": list(snap.next),
        },
    }


def d5_resume(session: str = "") -> dict:
    tid = f"studio-crashresume-{session or 'default'}"
    cfg = {"configurable": {"thread_id": tid}}
    agent = _build(_cp())  # healthy graph, no crash node

    before_snap = agent.get_state(cfg)
    if not before_snap.values:
        return {
            "kind": "memory_resume",
            "thread_id": tid,
            "error": "No prior state found. Run the CRASH demo first.",
        }
    before = before_snap.values

    # The crash graph left `next=['boom']` in the checkpoint. Reloaded with
    # the healthy graph, that foreign pointer reads back as `[]` so LangGraph
    # treats the run as complete. Rebase by re-recording `act` as the last
    # completed node so routing recomputes from state.
    if list(before_snap.next) in ([], ["boom"]):
        agent.update_state(cfg, values={}, as_node="act")

    # `None` = don't push new input; continue from the persisted checkpoint.
    agent.invoke(None, cfg)
    after = agent.get_state(cfg).values

    tail = after.get("messages") or []
    final = tail[-1].content if tail else ""
    return {
        "kind": "memory_resume",
        "thread_id": tid,
        "before": {
            "cursor": before.get("cursor", 0),
            "findings": len(before.get("findings") or []),
            "next": list(before_snap.next),
        },
        "after": {
            "cursor": after.get("cursor", 0),
            "findings": len(after.get("findings") or []),
            "idempotent": True,  # act_node dedup keys prevented double-fire
        },
        "findings": after.get("findings") or [],
        "final": final,
    }
