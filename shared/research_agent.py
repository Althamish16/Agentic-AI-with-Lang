"""
research_agent.py — THE COMPLETE Research Assistant (Day 7), reused by the web UI.

It composes every prior layer into one LangGraph:

    plan → research (RAG loop) → write → reflect ─(revise?)─┐
              ▲                              │               │
              └──────────────────────────────┘  (self-improve, capped)
                                             │
                                     human_approval  ← interrupt() HITL gate
                                             │
                                          publish → END

Layers reused:
  • plan      → Day 1 planner (shared/planner.py)
  • research  → Day 2 RAG     (shared/rag.py)
  • write     → Day 6 writer
  • reflect   → Day 7 self-critique (feedback loop)
  • approval  → Day 7 human-in-the-loop via interrupt()
  • memory    → compiled with a checkpointer (Day 5)   ← required for interrupt()
"""

from __future__ import annotations

from typing import List, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from config import get_llm
from shared.planner import plan_research
from shared.rag import answer_question

MAX_AUTO_REVISIONS = 1   # how many times reflection may auto-revise before the human gate


class AgentState(TypedDict, total=False):
    question: str
    topic: str
    plan: List[str]
    cursor: int
    findings: List[dict]
    draft: str
    critique: str
    verdict: str            # "PASS" | "REVISE"
    revisions: int
    human_feedback: str
    approved: bool
    final: str


# ── plan (Day 1) ─────────────────────────────────────────────────────────────
def _plan(state: AgentState) -> dict:
    p = plan_research(state["question"])
    return {"topic": p.topic, "plan": p.sub_questions, "cursor": 0, "findings": [], "revisions": 0}


# ── research loop (Day 2/3) ──────────────────────────────────────────────────
def _research(state: AgentState) -> dict:
    i = state["cursor"]
    res = answer_question(state["plan"][i], k=3)
    finding = {"sub_question": state["plan"][i], "answer": res["answer"], "sources": res["sources"]}
    return {"findings": state["findings"] + [finding], "cursor": i + 1}


def _research_more(state: AgentState) -> str:
    return "research" if state["cursor"] < len(state["plan"]) else "write"


# ── write / revise (Day 6) ───────────────────────────────────────────────────
def _write(state: AgentState) -> dict:
    llm = get_llm(temperature=0)
    body = "\n\n".join(
        f"Sub-question: {f['sub_question']}\nAnswer: {f['answer']}\nSources: {f['sources']}"
        for f in state["findings"]
    )
    guidance = ""
    if state.get("critique") and state.get("verdict") == "REVISE":
        guidance += f"\n\nRevise to address this critique:\n{state['critique']}"
    if state.get("human_feedback"):
        guidance += f"\n\nAlso incorporate this reviewer feedback:\n{state['human_feedback']}"

    draft = llm.invoke(
        f"Write a clear, well-structured research report answering: '{state['question']}'.\n"
        f"Use ONLY these findings and keep inline [n] citations:\n\n{body}{guidance}"
    ).content
    return {"draft": draft, "revisions": state.get("revisions", 0) + 1}


# ── reflect / self-critique (Day 7 feedback loop) ────────────────────────────
def _reflect(state: AgentState) -> dict:
    llm = get_llm(temperature=0)
    critique = llm.invoke(
        "You are a strict editor. Review the DRAFT against the question. Check: does it "
        "answer the question, are claims cited [n], is it clear and non-repetitive?\n"
        "Reply with a short critique, then on the LAST line write exactly 'VERDICT: PASS' "
        "or 'VERDICT: REVISE'.\n\n"
        f"Question: {state['question']}\n\nDRAFT:\n{state['draft']}"
    ).content
    verdict = "REVISE" if "REVISE" in critique.upper().split("VERDICT:")[-1] else "PASS"
    return {"critique": critique, "verdict": verdict}


def _route_after_reflect(state: AgentState) -> str:
    if state["verdict"] == "REVISE" and state.get("revisions", 0) <= MAX_AUTO_REVISIONS:
        return "write"          # self-improve
    return "human_approval"


# ── human-in-the-loop gate (Day 7) ───────────────────────────────────────────
def _human_approval(state: AgentState) -> dict:
    """Pause and wait for a human decision before publishing.

    interrupt() saves state and stops the graph. The caller resumes with
    Command(resume=<decision>), where <decision> is either a string
    ('approve'/'reject') or a dict {'approved': bool, 'feedback': str}.
    """
    decision = interrupt(
        {
            "type": "approval_request",
            "message": "Approve publishing this report?",
            "draft": state["draft"],
            "critique": state.get("critique", ""),
        }
    )
    if isinstance(decision, dict):
        approved = bool(decision.get("approved", True))
        feedback = decision.get("feedback", "")
    else:
        approved = str(decision).strip().lower() in {"approve", "approved", "yes", "y", "publish"}
        feedback = "" if approved else str(decision)
    return {"approved": approved, "human_feedback": feedback}


def _route_after_approval(state: AgentState) -> str:
    if state.get("approved"):
        return "publish"
    # Rejected: allow one human-driven revision, otherwise publish as-is.
    if state.get("revisions", 0) <= MAX_AUTO_REVISIONS + 1:
        return "write"
    return "publish"


# ── publish (finalize) ───────────────────────────────────────────────────────
def _publish(state: AgentState) -> dict:
    status = "✅ APPROVED & PUBLISHED" if state.get("approved") else "⚠ PUBLISHED WITHOUT APPROVAL (revision budget spent)"
    return {"final": f"{state['draft']}\n\n---\n{status}"}


def build_research_agent(checkpointer=None):
    """Compile the full agent. A checkpointer is REQUIRED for the interrupt() HITL
    gate; we default to an in-memory one so the graph is always runnable."""
    g = StateGraph(AgentState)
    g.add_node("plan", _plan)
    g.add_node("research", _research)
    g.add_node("write", _write)
    g.add_node("reflect", _reflect)
    g.add_node("human_approval", _human_approval)
    g.add_node("publish", _publish)

    g.add_edge(START, "plan")
    g.add_edge("plan", "research")
    g.add_conditional_edges("research", _research_more, {"research": "research", "write": "write"})
    g.add_edge("write", "reflect")
    g.add_conditional_edges("reflect", _route_after_reflect, {"write": "write", "human_approval": "human_approval"})
    g.add_conditional_edges("human_approval", _route_after_approval, {"write": "write", "publish": "publish"})
    g.add_edge("publish", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


# Human-readable labels for each node (used by the CLI and the web UI).
NODE_LABELS = {
    "plan": "Planning — decompose the question",
    "research": "Researching — retrieve + answer each sub-question (RAG)",
    "write": "Writing — compose the report",
    "reflect": "Reflecting — self-critique the draft",
    "human_approval": "Approval — waiting for a human decision",
    "publish": "Publishing — finalize the report",
}
