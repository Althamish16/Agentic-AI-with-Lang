"""
Day 5 · Persistence — SOLUTION
================================

A single, runnable Research Assistant agent that demonstrates the FOUR pillars
of persistence-layer engineering on top of the Day 3–4 planner/executor graph:

  1. CHECKPOINTER + thread_id .......... short-term durability
  2. STATE design (TypedDict + reducer) . what actually gets persisted
  3. COMPACTION node .................... bound context so cost stays flat
  4. LONG-TERM MEMORY ................... a vector-backed fact store

Plus a CRASH-AND-RESUME demo that kills the process mid-run and proves the
same `thread_id` picks up exactly where it left off (idempotent replay).

Run it end-to-end:

    python day5/solution/memory_agent.py                 # full guided tour
    python day5/solution/memory_agent.py crash           # phase 1: crash mid-run
    python day5/solution/memory_agent.py resume          # phase 2: resume from disk

Notes
-----
• Uses `SqliteSaver` (from `langgraph.checkpoint.sqlite`) for a durable, local
  checkpoint — swap for `PostgresSaver` in production (see comment at bottom).
• Long-term memory is a Chroma collection kept LOCAL to the machine — no
  external service needed.
• Every important step prints what it did, so learners can literally see
  persistence, compaction, and recall happening in real time.
"""

from __future__ import annotations

# ── path plumbing so we can `from config import ...` when running as a script ──
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — MUST import first: loads .env and quiets noise

import sqlite3  # noqa: E402
import uuid  # noqa: E402
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
from shared.memory import (  # noqa: E402
    clear_long_term_memory,
    recall,
    remember,
)


# ─────────────────────────────────────────────────────────────────────────────
# Files & constants
# ─────────────────────────────────────────────────────────────────────────────
# Single durable checkpoint file the whole demo shares. Deleting it resets
# all threads; keeping it is what lets the crash/resume demo work across
# separate Python processes.
CHECKPOINT_DB = pathlib.Path(__file__).with_name("runs.db")

# Trigger compaction when the conversation grows past this many messages.
COMPACT_THRESHOLD = 8
# How many recent messages to keep VERBATIM (older ones get summarised).
KEEP_LAST_N = 4


# ─────────────────────────────────────────────────────────────────────────────
# (2) STATE — TypedDict with an explicit reducer on `messages`
# ─────────────────────────────────────────────────────────────────────────────
# Every node returns partial updates; LangGraph merges them into state. The
# `add_messages` reducer APPENDS new messages instead of overwriting, which is
# exactly what we want for a chat-shaped history.
#
# Fields we persist (per the spec):
#   • messages          — full conversation, appended via add_messages reducer
#   • plan              — the current research plan (sub-questions to answer)
#   • cursor            — index into plan[]; enables idempotent resume
#   • findings          — accumulated intermediate results (list of dicts)
#   • tool_outputs      — raw tool return values, keyed by (node, cursor)
#                         → also enables IDEMPOTENT replay: a resumed step
#                         checks this dict and skips re-running the tool.
#   • long_term_recall  — long-term facts pulled into short-term this turn
#   • compaction_count  — how many times compaction has fired (for the UI)
class ResearchState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    question: str
    plan: List[str]
    cursor: int
    findings: List[dict]
    tool_outputs: dict
    long_term_recall: List[str]
    compaction_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — used by nodes below
# ─────────────────────────────────────────────────────────────────────────────
def _token_estimate(msgs: List[BaseMessage]) -> int:
    """Cheap, provider-independent token estimate (~4 chars / token)."""
    return sum(len(getattr(m, "content", "") or "") for m in msgs) // 4


def _fmt_msg(m: BaseMessage) -> str:
    return f"{m.type}: {m.content}"


# ─────────────────────────────────────────────────────────────────────────────
# (4) LONG-TERM RECALL node — pulls durable facts into short-term state
#      ONLY when relevant. Keeps short-term and long-term concerns separate.
# ─────────────────────────────────────────────────────────────────────────────
def recall_node(state: ResearchState) -> dict:
    q = state.get("question", "")
    if not q:
        return {}
    hits = recall(q, k=3)
    if not hits:
        return {"long_term_recall": []}
    # Surface recalled facts as a SystemMessage so the LLM sees them next turn.
    note = SystemMessage(content="[Relevant long-term memories]\n- " + "\n- ".join(hits))
    print(f"    🧠 long-term recall: {len(hits)} fact(s) surfaced.")
    return {"long_term_recall": hits, "messages": [note]}


# ─────────────────────────────────────────────────────────────────────────────
# PLAN node — LLM writes a small research plan (sub-questions) into state.
# Idempotent: if a plan already exists (we're resuming), reuse it.
# ─────────────────────────────────────────────────────────────────────────────
def plan_node(state: ResearchState) -> dict:
    if state.get("plan"):
        print("    ↩ plan already on disk — skipping (idempotent replay).")
        return {}
    llm = get_llm(temperature=0)
    q = state["question"]
    prompt = (
        "Break the user's research question into 3 short, specific sub-questions.\n"
        "Return ONE sub-question per line, no numbering.\n\n"
        f"Question: {q}"
    )
    text = llm.invoke(prompt).content
    plan = [line.strip("-• \t") for line in text.splitlines() if line.strip()][:3]
    print(f"    📝 plan: {plan}")
    return {
        "plan": plan,
        "cursor": 0,
        "findings": [],
        "tool_outputs": {},
        "messages": [AIMessage(content="Plan:\n- " + "\n- ".join(plan))],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ACT node — answers plan[cursor] and advances the cursor.
# IDEMPOTENT: side-effectful "tool" work is dedup-keyed by (node, cursor),
# stored in state.tool_outputs. On resume we detect the key and REUSE the
# earlier result instead of calling the LLM/tool again → no double-firing.
# ─────────────────────────────────────────────────────────────────────────────
def act_node(state: ResearchState) -> dict:
    i = state["cursor"]
    sub_q = state["plan"][i]
    key = f"act:{i}"
    tool_outputs = dict(state.get("tool_outputs") or {})

    if key in tool_outputs:
        # We already ran this step on a previous (crashed) invocation. Skip.
        print(f"    ↩ step {i+1} already checkpointed — replay skipped.")
        return {"cursor": i + 1}

    llm = get_llm(temperature=0)
    print(f"    🔎 answering sub-question {i+1}/{len(state['plan'])}: {sub_q}")
    answer = llm.invoke(
        f"Answer this in ONE short sentence, plainly:\n\n{sub_q}"
    ).content

    tool_outputs[key] = answer
    finding = {"sub_question": sub_q, "answer": answer}
    return {
        "cursor": i + 1,
        "findings": (state.get("findings") or []) + [finding],
        "tool_outputs": tool_outputs,
        "messages": [AIMessage(content=f"{sub_q} → {answer}")],
    }


# ─────────────────────────────────────────────────────────────────────────────
# (3) COMPACTION node — fires when messages exceed a threshold.
# Summarises the oldest turns with the LLM, keeps the last N verbatim, then
# REPLACES the message list with [summary, *last_N]. Prints message/token
# counts before vs. after so the shrink is visible.
#
# The `add_messages` reducer normally APPENDS. To truly shrink history we
# return the special sentinel `RemoveMessage(id=...)` for the ones we drop,
# then append the summary + kept messages. That's the LangGraph-native way.
# ─────────────────────────────────────────────────────────────────────────────
def compact_node(state: ResearchState) -> dict:
    msgs = state.get("messages") or []
    before_count = len(msgs)
    before_tokens = _token_estimate(msgs)

    if before_count <= KEEP_LAST_N + 1:
        return {}  # nothing worth summarising

    old, recent = msgs[:-KEEP_LAST_N], msgs[-KEEP_LAST_N:]
    llm = get_llm(temperature=0)
    transcript = "\n".join(_fmt_msg(m) for m in old)
    summary = llm.invoke(
        "Summarise the conversation below into 3–4 concise bullets, preserving "
        "key user goals, decisions, and facts.\n\n" + transcript
    ).content
    summary_msg = SystemMessage(content=f"[Summary of {len(old)} earlier messages]\n{summary}")

    # Tell the reducer to DROP the old messages, then append summary + recents.
    drops = [RemoveMessage(id=m.id) for m in old if getattr(m, "id", None)]
    new_messages: list[BaseMessage] = [*drops, summary_msg, *recent]

    after_count = 1 + len(recent)
    after_tokens = _token_estimate([summary_msg, *recent])
    print(
        f"    🗜 compaction fired · messages {before_count} → {after_count} "
        f"· ~tokens {before_tokens} → {after_tokens}"
    )
    return {
        "messages": new_messages,
        "compaction_count": (state.get("compaction_count") or 0) + 1,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Router — after ACT we either loop, compact, or finish.
# ─────────────────────────────────────────────────────────────────────────────
def route_after_act(state: ResearchState) -> str:
    if len(state.get("messages") or []) > COMPACT_THRESHOLD:
        return "compact"
    if state["cursor"] < len(state.get("plan") or []):
        return "act"
    return "answer"


def route_after_compact(state: ResearchState) -> str:
    if state["cursor"] < len(state.get("plan") or []):
        return "act"
    return "answer"


# ─────────────────────────────────────────────────────────────────────────────
# ANSWER node — writes the final synthesized reply and saves a durable memory.
# ─────────────────────────────────────────────────────────────────────────────
def answer_node(state: ResearchState) -> dict:
    llm = get_llm(temperature=0)
    body = "\n".join(f"- {f['sub_question']}: {f['answer']}" for f in state["findings"])
    final = llm.invoke(
        f"Write a concise 3-sentence answer to '{state['question']}' from:\n{body}"
    ).content

    # Persist a lesson-learned to long-term memory (so future runs can recall it).
    remember(
        f"Topic covered: {state['question']} — {len(state['findings'])} sub-questions answered.",
        metadata={"kind": "session_summary"},
    )
    print(f"    ✅ final answer ({len(final)} chars) · long-term memory updated.")
    return {"messages": [AIMessage(content=final)]}


# ─────────────────────────────────────────────────────────────────────────────
# CRASH node — used ONLY by the crash-and-resume demo. Raises after ACT to
# simulate a mid-run failure. Because ACT already checkpointed its work, the
# next run picks up cleanly.
# ─────────────────────────────────────────────────────────────────────────────
class SimulatedCrash(RuntimeError):
    pass


def crash_node(state: ResearchState) -> dict:
    print("    💥 simulated crash AFTER step 1 (state already checkpointed).")
    raise SimulatedCrash("kaboom — simulated crash to test resume")


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────
def build_agent(checkpointer, *, crash_after_first_act: bool = False):
    g = StateGraph(ResearchState)
    g.add_node("recall", recall_node)   # long-term → short-term (relevant only)
    g.add_node("plan", plan_node)
    g.add_node("act", act_node)
    g.add_node("compact", compact_node)
    g.add_node("answer", answer_node)

    g.add_edge(START, "recall")
    g.add_edge("recall", "plan")
    # After plan, route: if we already have all findings (turn-2 replay), skip
    # straight to answer; otherwise run the next act step.
    g.add_conditional_edges(
        "plan",
        lambda s: "answer" if s.get("cursor", 0) >= len(s.get("plan") or []) and s.get("findings") else "act",
        {"act": "act", "answer": "answer"},
    )

    if crash_after_first_act:
        # Insert a crash node RIGHT after the first act so we can prove resume.
        g.add_node("boom", crash_node)
        g.add_edge("act", "boom")
        g.add_edge("boom", END)          # unreachable — raise interrupts flow
    else:
        g.add_conditional_edges("act", route_after_act,
                                {"act": "act", "compact": "compact", "answer": "answer"})
        g.add_conditional_edges("compact", route_after_compact,
                                {"act": "act", "answer": "answer"})
        g.add_edge("answer", END)

    # NOTE: SqliteSaver is great for local dev + workshops. For production,
    # swap in a Postgres checkpointer:
    #     from langgraph.checkpoint.postgres import PostgresSaver
    #     checkpointer = PostgresSaver.from_conn_string(os.environ["DATABASE_URL"])
    return g.compile(checkpointer=checkpointer)


# ─────────────────────────────────────────────────────────────────────────────
# Demos
# ─────────────────────────────────────────────────────────────────────────────
def _open_checkpointer() -> SqliteSaver:
    """Fresh connection each call — SqliteSaver isn't thread-shared friendly."""
    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    return SqliteSaver(conn)


def _rule(title: str) -> None:
    print(f"\n{'═' * 72}\n  {title}\n{'═' * 72}")


def demo_short_term_and_state():
    """Pillars (1) checkpointer + thread_id and (2) explicit state design."""
    _rule("PILLAR 1+2 · Checkpointer + thread_id, explicit State")
    agent = build_agent(_open_checkpointer())
    thread_id = "learner-thread-1"
    cfg = {"configurable": {"thread_id": thread_id}}

    # Turn 1 — full research question.
    print("\n▶ Turn 1 · question: 'How do vector databases power RAG?'")
    agent.invoke({"question": "How do vector databases power RAG?"}, cfg)

    # Turn 2 — follow-up, same thread_id. Uses persisted messages.
    print("\n▶ Turn 2 · follow-up: 'Which of those points is most important?'")
    agent.invoke(
        {"messages": [HumanMessage(content="Which of those points is most important?")]},
        cfg,
    )

    # (1) get_state() — inspect the persisted checkpoint.
    snap = agent.get_state(cfg)
    print(f"\n📸 get_state(thread='{thread_id}'):")
    print(f"    persisted messages : {len(snap.values.get('messages', []))}")
    print(f"    plan               : {snap.values.get('plan')}")
    print(f"    findings           : {len(snap.values.get('findings') or [])}")
    print(f"    compactions so far : {snap.values.get('compaction_count', 0)}")
    print(f"    next node          : {list(snap.next)!r}")


def demo_compaction():
    """Pillar (3) — force the graph past the threshold on a fresh thread."""
    _rule("PILLAR 3 · Compaction (summarise oldest, keep last N verbatim)")
    cfg = {"configurable": {"thread_id": f"compaction-{uuid.uuid4().hex[:8]}"}}

    # Seed the thread with a chatty history so we blow past COMPACT_THRESHOLD
    # WITHOUT running a plan (we're only exercising the compact node here).
    seed_msgs: list[BaseMessage] = []
    for i in range(1, 6):
        seed_msgs.append(HumanMessage(content=f"Chat turn {i}: tell me about RAG stage {i}."))
        seed_msgs.append(AIMessage(content=f"Stage {i} of RAG covers point-{i}-details ..."))

    # Prime state without running plan/act by using a tiny 1-node graph.
    prime = StateGraph(ResearchState)
    prime.add_node("seed", lambda s: {"messages": seed_msgs})
    prime.add_edge(START, "seed")
    prime.add_edge("seed", END)
    prime_agent = prime.compile(checkpointer=_open_checkpointer())
    prime_agent.invoke({}, cfg)

    # Now call compact_node directly on the persisted state.
    snap = prime_agent.get_state(cfg)
    before = snap.values.get("messages") or []
    print(f"    before → {len(before)} messages · ~{_token_estimate(before)} tokens")
    result = compact_node({"messages": before})
    after = [m for m in result["messages"] if not isinstance(m, RemoveMessage)]
    print(f"    after  → {len(after)} messages · ~{_token_estimate(after)} tokens")
    if after:
        print(f"\n    summary preview: {after[0].content[:180]}…")


def demo_long_term_memory():
    """Pillar (4) — write facts, then recall the relevant ones semantically."""
    _rule("PILLAR 4 · Long-term memory (vector-backed store)")
    clear_long_term_memory()  # reproducible run
    for fact in [
        "The user prefers concise, bulleted answers with citations.",
        "The user is building a Research Assistant with LangGraph.",
        "The user's favorite vector database is Chroma.",
        "The user runs on Windows and uses PowerShell.",
    ]:
        remember(fact, metadata={"kind": "user_preference"})
    print("    stored 4 durable facts.")

    query = "How does the user like their answers formatted?"
    hits = recall(query, k=2)
    print(f"\n    recall({query!r}, k=2):")
    for h in hits:
        print(f"      • {h}")


# ─── CRASH & RESUME ──────────────────────────────────────────────────────────
CRASH_THREAD = "resume-demo-thread"


def demo_crash():
    """Phase 1 · run the agent, deliberately crash mid-run, exit."""
    _rule("CRASH · run 1 — plan + step 1 succeed, then simulated crash")
    agent = build_agent(_open_checkpointer(), crash_after_first_act=True)
    cfg = {"configurable": {"thread_id": CRASH_THREAD}}
    try:
        agent.invoke({"question": "What are the key ideas in agent memory?"}, cfg)
    except SimulatedCrash as e:
        print(f"    ⛔ caught simulated crash: {e}")

    snap = agent.get_state(cfg)
    print("\n📸 state on disk after crash:")
    print(f"    plan     : {snap.values.get('plan')}")
    print(f"    cursor   : {snap.values.get('cursor')}   (0-indexed, next step to run)")
    print(f"    findings : {len(snap.values.get('findings') or [])} recorded")
    print(f"    next     : {list(snap.next)!r}")
    print("\n👉 Now run:  python day5/solution/memory_agent.py resume")


def demo_resume():
    """Phase 2 · same thread_id, HEALTHY graph — proves resume from disk."""
    _rule("RESUME · run 2 — SAME thread_id, no crash node this time")
    agent = build_agent(_open_checkpointer())  # note: crash_after_first_act=False
    cfg = {"configurable": {"thread_id": CRASH_THREAD}}

    snap = agent.get_state(cfg)
    print("📸 state BEFORE resume:")
    print(f"    cursor          : {snap.values.get('cursor')}")
    print(f"    findings so far : {len(snap.values.get('findings') or [])}")
    print(f"    next node       : {list(snap.next)!r}")

    if not snap.values:
        print("\n(no prior state found — run the crash phase first)")
        return

    # The crash graph left `next=['boom']` in the checkpoint. When we reload
    # it with the HEALTHY graph, that pending pointer isn't recognised so
    # LangGraph thinks the run is finished (`next=[]`). Rebase by re-recording
    # `act` as the last completed node — routing will now compute the next
    # real step (compact / act again / answer) from state.
    if not snap.values.get("findings") or list(snap.next) in ([], ["boom"]):
        print("    🔧 rebasing pending pointer  → route-after-act")
        agent.update_state(cfg, values={}, as_node="act")

    # Passing `None` as input tells LangGraph: don't push new state, just
    # continue from the persisted checkpoint. Because act_node is idempotent
    # (dedup key on tool_outputs), replayed steps do NOT double-fire.
    agent.invoke(None, cfg)

    snap2 = agent.get_state(cfg)
    print("\n📸 state AFTER resume:")
    print(f"    cursor          : {snap2.values.get('cursor')}")
    print(f"    findings total  : {len(snap2.values.get('findings') or [])}")
    tail = snap2.values.get("messages") or []
    if tail:
        print(f"    final answer    : {tail[-1].content[:160]}…")
    print("\n✅ Same thread_id continued exactly where it stopped — no re-planning, no double-firing.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if mode == "crash":
        demo_crash()
        return
    if mode == "resume":
        demo_resume()
        return

    demo_short_term_and_state()
    demo_compaction()
    demo_long_term_memory()

    _rule("Guided crash-and-resume — two separate invocations")
    demo_crash()
    print()
    demo_resume()

    print(f"\nCheckpoint file: {CHECKPOINT_DB}")
    print("Delete it to reset all threads. Swap SqliteSaver → PostgresSaver for prod.")


if __name__ == "__main__":
    main()
