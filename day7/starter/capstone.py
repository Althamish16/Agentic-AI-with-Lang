"""
Day 7 STARTER — capstone.py

Your job today: turn a working multi-step research agent into a *shippable* one
by adding three production layers. You will fill in every `# TODO(student):`
below (there are 5). The rest of the file is done for you — read it top to
bottom before you start typing.

Run it (offline-safe with LLM_PROVIDER=mock):

    python day7/starter/capstone.py --auto "Should I use similarity or MMR retrieval?"

You've finished when:
  1. The reflection loop revises the draft up to MAX_REVISIONS times AND stops
     early when the score plateaus.
  2. `interrupt()` pauses at the approval gate; the driver resumes with the
     human's decision.
  3. `--reject` triggers a human-driven revision, then a second approval round.

Compare with day7/solution/capstone.py after you've tried it yourself.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys
from typing import List, Optional, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — loads .env, silences chroma noise

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

from config import get_llm, setup_langsmith  # noqa: E402
from shared.pretty import banner, node, ok, rule, warn  # noqa: E402


# ─── Tuning knobs ────────────────────────────────────────────────────────────
MAX_REVISIONS = 3         # hard cap on the reflection loop
MIN_DELTA = 0.05          # score must improve by this much between iterations
PASS_SCORE = 0.85         # judge score at/above this counts as "PASS"
MIN_CITATIONS = 2         # programmatic check: report must cite ≥ N sources
LOW_CONFIDENCE = 0.65     # judge score below this → escalate to human


class State(TypedDict, total=False):
    question: str
    plan: List[str]; cursor: int; findings: List[dict]
    draft: str; critique: str; verdict: str
    score: float; scores: List[float]
    revisions: int
    check_ok: bool; check_reason: str
    approved: bool; human_feedback: str
    final: str


# ─── plan / research / write (given for you) ─────────────────────────────────
def _plan(state):
    node("plan", "decompose the question")
    q = state["question"]
    return {
        "plan": [f"What is {q.rstrip('?')}?", "Why does it matter?", "How is it applied?"],
        "cursor": 0, "findings": [], "revisions": 0, "scores": [],
    }


def _research(state):
    i = state["cursor"]; sq = state["plan"][i]
    node("research", f"sub-question {i + 1}/{len(state['plan'])}")
    try:
        from shared.rag import answer_question
        res = answer_question(sq, k=3)
        finding = {"sub_question": sq, "answer": res["answer"], "sources": res["sources"]}
    except Exception:
        finding = {"sub_question": sq, "answer": f"(offline mock) {sq}", "sources": [f"mock-{i + 1}.md"]}
    return {"findings": state["findings"] + [finding], "cursor": i + 1}


def _research_more(state):
    return "research" if state["cursor"] < len(state["plan"]) else "write"


def _write(state):
    rev = state.get("revisions", 0) + 1
    node("write", f"compose report (revision #{rev})")
    body = "\n".join(f"- {f['sub_question']} → {f['answer']} (src: {f['sources']})" for f in state["findings"])
    guidance = ""
    if state.get("verdict") == "REVISE" and state.get("critique"):
        guidance += f"\n\nAddress this critique:\n{state['critique']}"
    if state.get("human_feedback"):
        guidance += f"\n\nAlso incorporate this reviewer feedback:\n{state['human_feedback']}"
    draft = get_llm(0).invoke(
        f"Write a cited report answering '{state['question']}' using ONLY these findings "
        f"(keep inline [n] citations):\n\n{body}{guidance}"
    ).content
    return {"draft": draft, "revisions": rev}


# ─── PROGRAMMATIC CHECK (deterministic, runs alongside the judge) ────────────
_CITE = re.compile(r"\[(\d+)\]")


def programmatic_check(draft: str) -> tuple[bool, str]:
    """Count distinct [n] citations. Must be >= MIN_CITATIONS to pass."""
    n = len({int(m) for m in _CITE.findall(draft or "")})
    if n < MIN_CITATIONS:
        return False, f"only {n} citation(s); need ≥ {MIN_CITATIONS}"
    return True, f"{n} citations"


# ─── REFLECT (judge) — returns critique + numeric score ──────────────────────
_SCORE = re.compile(r"SCORE\s*[:=]\s*([01](?:\.\d+)?)", re.IGNORECASE)


def _extract_score(text):
    m = _SCORE.search(text or "")
    if m:
        try: return max(0.0, min(1.0, float(m.group(1))))
        except ValueError: pass
    up = (text or "").upper()
    return 0.90 if "VERDICT: PASS" in up else (0.60 if "VERDICT: REVISE" in up else 0.5)


def _reflect(state):
    node("reflect", "judge the draft (verdict + score)")
    critique = get_llm(0).invoke(
        "You are a STRICT editor. Grade the DRAFT for the QUESTION on: answers it? cited [n]? clear?\n"
        "Write 2-4 concrete fixes, then the LAST TWO lines must be:\n"
        "  SCORE: <0.00-1.00>\n  VERDICT: PASS|REVISE\n\n"
        f"QUESTION: {state['question']}\n\nDRAFT:\n{state['draft']}"
    ).content
    score = _extract_score(critique)
    verdict = "PASS" if ("VERDICT: PASS" in critique.upper() or score >= PASS_SCORE) else "REVISE"
    ok_check, reason = programmatic_check(state["draft"])
    return {
        "critique": critique, "score": score,
        "scores": state.get("scores", []) + [score],
        "verdict": verdict, "check_ok": ok_check, "check_reason": reason,
    }


# ─── ROUTER — the reflection loop's brain ────────────────────────────────────
def _route_after_reflect(state) -> str:
    """
    TODO(student) #1 — implement the three stopping rules for the reflection loop:

      (a) HARD CAP:  if we've already written MAX_REVISIONS times, stop revising.
                     Return "approval" to hand off to the human.
      (b) PLATEAU:   look at state["scores"]. If we have ≥ 2 scores AND the last
                     one didn't improve by at least MIN_DELTA, stop revising.
                     Return "approval". This is the guard that prevents the loop
                     from running forever when a mediocre draft can't get better.
      (c) BOTH OK:   if the judge says verdict == "PASS" AND the programmatic
                     check_ok is True, we're done → return "approval".
      Otherwise (verdict=REVISE OR check_ok=False, and we still have budget +
      the score is improving), return "write" to revise once more.
    """
    revisions = state.get("revisions", 0)
    scores = state.get("scores", []) or [state.get("score", 0.0)]

    # (a) TODO(student): hard cap
    #   if revisions >= MAX_REVISIONS: return "approval"

    # (b) TODO(student): plateau guard — improvement between the last two
    #                    scores must be at least MIN_DELTA to keep looping.
    #   if len(scores) >= 2 and (scores[-1] - scores[-2]) < MIN_DELTA:
    #       return "approval"

    # (c) TODO(student): judge + programmatic check both happy
    #   if state.get("verdict") == "PASS" and state.get("check_ok"):
    #       return "approval"

    # Until you implement the rules above the loop will never revise —
    # replace this line with `return "write"` once you've added the rules.
    return "approval"


# ─── HUMAN-IN-THE-LOOP GATE — where the graph PAUSES ─────────────────────────
def _approval(state):
    node("approval", "⏸  awaiting human decision")

    # TODO(student) #2 — pause the graph with interrupt().
    # Return the draft + everything the reviewer needs to make a decision.
    # The caller will resume with Command(resume={"approved": bool, "feedback": str})
    #
    #   decision = interrupt({
    #       "type": "approval_request",
    #       "message": "Approve publishing this report?",
    #       "draft": state["draft"],
    #       "critique": state.get("critique", ""),
    #       "score": state.get("score"),
    #       "check_ok": state.get("check_ok"),
    #       "check_reason": state.get("check_reason", ""),
    #       "escalated": state.get("score", 0.0) < LOW_CONFIDENCE,
    #   })
    decision = {"approved": True, "feedback": ""}  # <- replace with the real interrupt() call

    if isinstance(decision, dict):
        approved = bool(decision.get("approved", True))
        feedback = decision.get("feedback", "")
    else:
        approved = str(decision).strip().lower() in {"approve", "approved", "yes", "y"}
        feedback = "" if approved else str(decision)
    return {"approved": approved, "human_feedback": feedback}


def _route_after_approval(state) -> str:
    # TODO(student) #3 — route on the human's decision:
    #   • if approved → "publish"
    #   • else if revisions < MAX_REVISIONS + 1 → "write" (one more human-driven revision)
    #   • else → "publish" (ship it with a "not approved" tag)
    return "publish"


def _publish(state):
    node("publish", "finalize the report")
    tag = "✅ APPROVED" if state.get("approved") else "⚠ PUBLISHED WITHOUT APPROVAL"
    return {"final": f"{state['draft']}\n\n--- {tag} · score={state.get('score', 0):.2f} ---"}


def build_capstone():
    g = StateGraph(State)
    for name, fn in [("plan", _plan), ("research", _research), ("write", _write),
                     ("reflect", _reflect), ("approval", _approval), ("publish", _publish)]:
        g.add_node(name, fn)
    g.add_edge(START, "plan")
    g.add_edge("plan", "research")
    g.add_conditional_edges("research", _research_more, {"research": "research", "write": "write"})
    g.add_edge("write", "reflect")
    g.add_conditional_edges("reflect", _route_after_reflect, {"write": "write", "approval": "approval"})
    g.add_conditional_edges("approval", _route_after_approval, {"write": "write", "publish": "publish"})
    g.add_edge("publish", END)
    # NB: interrupt() REQUIRES a checkpointer to persist state across the pause.
    return g.compile(checkpointer=MemorySaver())


def _pump(app, inp, cfg) -> Optional[dict]:
    for chunk in app.stream(inp, cfg, stream_mode="updates"):
        if "__interrupt__" in chunk:
            return chunk["__interrupt__"][0].value
        for name, upd in chunk.items():
            if name == "reflect":
                print(f"    → score={upd.get('score', 0):.2f} verdict={upd.get('verdict')} check={upd.get('check_ok')}")
    return None


def _decide(payload, mode):
    rule(); warn("HUMAN APPROVAL REQUIRED" + (" · LOW CONFIDENCE" if payload.get("escalated") else ""))
    print(f"  score={payload.get('score')}  check_ok={payload.get('check_ok')} ({payload.get('check_reason')})")
    print(f"  critique: {(payload.get('critique') or '')[:200]}...")
    print(f"  draft:    {(payload.get('draft') or '')[:400]}...")
    rule()
    if mode == "auto":  return {"approved": True, "feedback": ""}
    if mode == "reject": return {"approved": False, "feedback": "Please add a concrete example."}
    ans = input("Approve? [y/N or free-text feedback]: ").strip()
    return {"approved": True, "feedback": ""} if ans.lower() in {"y", "yes"} else {"approved": False, "feedback": ans or "reject"}


def main():
    args = sys.argv[1:]; mode = "interactive"
    if "--auto" in args: mode = "auto"; args.remove("--auto")
    if "--reject" in args: mode = "reject"; args.remove("--reject")
    question = " ".join(args).strip() or "Should I use similarity or MMR retrieval for a RAG system?"

    banner("Day 7 CAPSTONE (starter) — fill in the TODOs")
    traced = setup_langsmith()
    ok("LangSmith tracing ENABLED") if traced else print("LangSmith OFF (set LANGSMITH_TRACING=true to enable).")

    app = build_capstone()
    cfg = {"configurable": {"thread_id": "day7-starter"}}

    payload = _pump(app, {"question": question}, cfg)
    # TODO(student) #4 — while the graph is paused at the human gate, get the
    # decision and resume it with Command(resume=decision). It may pause more
    # than once (e.g. after a human-driven revision), so keep looping.
    #
    #   while payload is not None:
    #       decision = _decide(payload, mode)
    #       payload = _pump(app, Command(resume=decision), cfg)

    final = app.get_state(cfg).values.get("final", "(finish the TODOs to publish)")
    scores = app.get_state(cfg).values.get("scores", [])
    rule("═")
    print(f"scores: {[round(s, 2) for s in scores]}")
    print(f"\nFINAL:\n{final}")


if __name__ == "__main__":
    main()
