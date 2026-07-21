"""
Day 7 EXERCISE — capstone with programmatic checks + escalation.

Start from this file. Fill in every `# TODO(exercise):`. Compare with
`day7/exercise/solution.py` only after you've tried it yourself.

Reference: `day7/solution/capstone.py` for the "judge-only" version.

Run (offline):
    $env:LLM_PROVIDER = "mock"
    python day7/exercise/capstone.py --auto "Should I use similarity or MMR retrieval?"
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import List, Optional, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

from config import get_llm, setup_langsmith  # noqa: E402
from shared.pretty import banner, node, ok, rule, warn  # noqa: E402


MAX_REVISIONS = 3
MIN_DELTA = 0.05
PASS_SCORE = 0.85
MIN_CITATIONS = 2
MIN_DRAFT_CHARS = 200
LOW_CONFIDENCE = 0.65


class State(TypedDict, total=False):
    question: str
    plan: List[str]; cursor: int; findings: List[dict]
    draft: str; critique: str; verdict: str
    score: float; scores: List[float]
    revisions: int
    check_ok: bool; check_reason: str
    approved: bool; human_feedback: str
    final: str


# ─── plan / research / write / reflect (given) ───────────────────────────────
def _plan(state):
    node("plan", "decompose")
    q = state["question"]
    return {"plan": [f"What is {q.rstrip('?')}?", "Why does it matter?", "How is it applied?"],
            "cursor": 0, "findings": [], "revisions": 0, "scores": []}


def _research(state):
    i = state["cursor"]; sq = state["plan"][i]
    node("research", f"{i + 1}/{len(state['plan'])}")
    try:
        from shared.rag import answer_question
        r = answer_question(sq, k=3)
        f = {"sub_question": sq, "answer": r["answer"], "sources": r["sources"]}
    except Exception:
        f = {"sub_question": sq, "answer": f"(mock) {sq}", "sources": [f"mock-{i + 1}.md"]}
    return {"findings": state["findings"] + [f], "cursor": i + 1}


def _research_more(state):
    return "research" if state["cursor"] < len(state["plan"]) else "write"


def _write(state):
    rev = state.get("revisions", 0) + 1
    node("write", f"rev #{rev}")
    body = "\n".join(f"- {f['sub_question']} → {f['answer']} (src: {f['sources']})" for f in state["findings"])
    guidance = ""
    if state.get("verdict") == "REVISE" and state.get("critique"):
        guidance += f"\n\nAddress critique:\n{state['critique']}"
    if state.get("human_feedback"):
        guidance += f"\n\nReviewer feedback:\n{state['human_feedback']}"
    draft = get_llm(0).invoke(
        f"Write a cited report for '{state['question']}' using ONLY these findings "
        f"(inline [n] citations required):\n\n{body}{guidance}"
    ).content
    return {"draft": draft, "revisions": rev}


_CITE = re.compile(r"\[(\d+)\]")
_SCORE = re.compile(r"SCORE\s*[:=]\s*([01](?:\.\d+)?)", re.IGNORECASE)


# ═════════════════════════════════════════════════════════════════════════════
# TODO(exercise) #1 — programmatic_check
# Return (True, reason) ONLY when ALL of these hold:
#   • the draft contains ≥ MIN_CITATIONS distinct [n] citations,
#   • the draft is at least MIN_DRAFT_CHARS characters long,
#   • the draft mentions the question's main noun (crude on-topic guard —
#     take the longest word in `question` with len ≥ 4 and case-insensitively
#     require it to appear in the draft).
# Otherwise return (False, "<short reason>").
# ═════════════════════════════════════════════════════════════════════════════
def programmatic_check(draft: str, question: str) -> tuple[bool, str]:
    # TODO(exercise): implement the three checks above.
    #
    # cites = len({int(m) for m in _CITE.findall(draft or "")})
    # if cites < MIN_CITATIONS: return False, f"only {cites} citation(s)"
    # if len(draft or "") < MIN_DRAFT_CHARS: return False, "too short"
    # keyword = max(re.findall(r"[A-Za-z]{4,}", question or ""), key=len, default="")
    # if keyword and keyword.lower() not in (draft or "").lower():
    #     return False, f"off-topic: missing '{keyword}'"
    # return True, f"{cites} citations, on topic"
    return True, "(stub — implement me)"


def _extract_score(text):
    m = _SCORE.search(text or "")
    if m:
        try: return max(0.0, min(1.0, float(m.group(1))))
        except ValueError: pass
    up = (text or "").upper()
    return 0.90 if "VERDICT: PASS" in up else (0.60 if "VERDICT: REVISE" in up else 0.5)


def _reflect(state):
    node("reflect", "judge + programmatic check")
    critique = get_llm(0).invoke(
        "STRICT editor: grade the DRAFT for the QUESTION on answers-it / cited / clear. "
        "Give 2-4 fixes, then finish with two lines exactly:\n"
        "  SCORE: <0.00-1.00>\n  VERDICT: PASS|REVISE\n\n"
        f"QUESTION: {state['question']}\n\nDRAFT:\n{state['draft']}"
    ).content
    score = _extract_score(critique)
    verdict = "PASS" if ("VERDICT: PASS" in critique.upper() or score >= PASS_SCORE) else "REVISE"
    ok_check, reason = programmatic_check(state["draft"], state["question"])
    return {"critique": critique, "score": score,
            "scores": state.get("scores", []) + [score],
            "verdict": verdict, "check_ok": ok_check, "check_reason": reason}


# ═════════════════════════════════════════════════════════════════════════════
# TODO(exercise) #2 — router: require BOTH the judge AND the check to pass,
# and ESCALATE to the human on low confidence.
#
# The rules (in order):
#   (a) revisions >= MAX_REVISIONS         → "approval"   (hard cap)
#   (b) plateau: len(scores) >= 2 AND
#       scores[-1] - scores[-2] < MIN_DELTA → "approval"  (no measurable improvement)
#   (c) verdict == "PASS" AND check_ok AND
#       score >= LOW_CONFIDENCE            → "approval"   (auto-publish candidate)
#   (d) verdict == "PASS" AND
#       score  <  LOW_CONFIDENCE           → "approval"   (ESCALATE — pass but shaky)
#   otherwise                              → "write"      (revise again)
# ═════════════════════════════════════════════════════════════════════════════
def _route_after_reflect(state) -> str:
    # TODO(exercise): implement rules (a)–(d) above and return "approval" or "write".
    # Until you implement the rules, the loop can't stop — so as a placeholder we
    # short-circuit straight to approval. Replace this with the real router.
    return "approval"


def _approval(state):
    node("approval", "⏸  awaiting human")
    escalated = state.get("verdict") == "PASS" and state.get("score", 0.0) < LOW_CONFIDENCE
    decision = interrupt({
        "type": "approval_request",
        "message": "Approve publishing this report?",
        "draft": state["draft"],
        "critique": state.get("critique", ""),
        "score": state.get("score"),
        "check_ok": state.get("check_ok"),
        "check_reason": state.get("check_reason", ""),
        "escalated": escalated,
    })
    if isinstance(decision, dict):
        return {"approved": bool(decision.get("approved", True)), "human_feedback": decision.get("feedback", "")}
    approved = str(decision).strip().lower() in {"approve", "approved", "yes", "y"}
    return {"approved": approved, "human_feedback": "" if approved else str(decision)}


def _route_after_approval(state):
    if state.get("approved"): return "publish"
    if state.get("revisions", 0) < MAX_REVISIONS + 1: return "write"
    return "publish"


def _publish(state):
    node("publish", "finalize")
    tag = "✅ APPROVED" if state.get("approved") else "⚠ PUBLISHED WITHOUT APPROVAL"
    return {"final": f"{state['draft']}\n\n--- {tag} · score={state.get('score', 0):.2f}"
                     f" · check: {state.get('check_reason', '')}"}


def build_capstone():
    g = StateGraph(State)
    for name, fn in [("plan", _plan), ("research", _research), ("write", _write),
                     ("reflect", _reflect), ("approval", _approval), ("publish", _publish)]:
        g.add_node(name, fn)
    g.add_edge(START, "plan"); g.add_edge("plan", "research")
    g.add_conditional_edges("research", _research_more, {"research": "research", "write": "write"})
    g.add_edge("write", "reflect")
    g.add_conditional_edges("reflect", _route_after_reflect, {"write": "write", "approval": "approval"})
    g.add_conditional_edges("approval", _route_after_approval, {"write": "write", "publish": "publish"})
    g.add_edge("publish", END)
    return g.compile(checkpointer=MemorySaver())


def _pump(app, inp, cfg) -> Optional[dict]:
    for chunk in app.stream(inp, cfg, stream_mode="updates"):
        if "__interrupt__" in chunk: return chunk["__interrupt__"][0].value
        for n, u in chunk.items():
            if n == "reflect":
                print(f"    → score={u.get('score', 0):.2f} verdict={u.get('verdict')} check={u.get('check_ok')} ({u.get('check_reason')})")
    return None


def _decide(payload, mode):
    rule(); warn("HUMAN APPROVAL REQUIRED" + (" · ESCALATED (low confidence)" if payload.get("escalated") else ""))
    print(f"  score={payload.get('score')} check_ok={payload.get('check_ok')} ({payload.get('check_reason')})")
    print(f"  draft: {(payload.get('draft') or '')[:400]}..."); rule()
    if mode == "auto": return {"approved": True, "feedback": ""}
    if mode == "reject": return {"approved": False, "feedback": "Add a concrete example."}
    ans = input("Approve? [y/N or free-text]: ").strip()
    return {"approved": True} if ans.lower() in {"y", "yes"} else {"approved": False, "feedback": ans or "reject"}


def main():
    args = sys.argv[1:]; mode = "interactive"
    if "--auto" in args: mode = "auto"; args.remove("--auto")
    if "--reject" in args: mode = "reject"; args.remove("--reject")
    q = " ".join(args).strip() or "Should I use similarity or MMR retrieval for a RAG system?"

    banner("Day 7 EXERCISE — programmatic check + escalation")
    traced = setup_langsmith()
    ok("LangSmith ON") if traced else print("LangSmith OFF (optional).")

    app = build_capstone()
    cfg = {"configurable": {"thread_id": "day7-exercise"}}
    payload = _pump(app, {"question": q}, cfg)
    while payload is not None:
        payload = _pump(app, Command(resume=_decide(payload, mode)), cfg)

    st = app.get_state(cfg).values
    rule("═")
    print(f"scores: {[round(s, 2) for s in st.get('scores', [])]}")
    print(f"\nFINAL:\n{st.get('final', '(no final report)')}")


if __name__ == "__main__":
    main()
