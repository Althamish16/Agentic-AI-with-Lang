"""
Day 7 SOLUTION — capstone.py

The CAPSTONE agent. Everything students learned this week meets in one graph:

  ┌──────────────────────────────────────────────────────────────────────────┐
  │  plan → research → write → reflect ─(REVISE, capped + score guard)─┐     │
  │                       ▲                                            │     │
  │                       └────────────────────────────────────────────┘     │
  │                            ↓                                             │
  │                       approval  ← interrupt() HITL gate (checkpoint)     │
  │                            ↓                                             │
  │                        publish  → END                                    │
  └──────────────────────────────────────────────────────────────────────────┘

Three "production" layers are added on top of the multi-agent research assistant:

  1. REFLECTION LOOP (bounded self-critique)
     • A judge/verifier model grades the draft AND returns a numeric score.
     • The writer revises using the judge's critique.
     • Two independent stopping rules:
        - hard cap: MAX_REVISIONS iterations
        - PLATEAU guard: stop when the score fails to improve by MIN_DELTA.
     • The plateau guard is the important half: real drafts often stop
       improving BEFORE they're "perfect", and a loop that only stops at
       PASS will burn tokens forever.

  2. HUMAN-IN-THE-LOOP APPROVAL GATE
     • The `approval` node calls interrupt({"draft": ...}) — the graph PAUSES
       and its state is persisted by the checkpointer.
     • The caller resumes with Command(resume={"approved": ..., "feedback": ...})
       and execution continues from exactly where it paused.
     • This is the mechanism you use for ANY high-stakes / irreversible action.

  3. OBSERVABILITY
     • setup_langsmith() flips LANGCHAIN_TRACING_V2 + LANGSMITH_API_KEY on
       when they're present in .env.
     • Traces appear automatically at smith.langchain.com — the app also runs
       cleanly with tracing OFF (no LangSmith account required for the demo).

The demo run at the bottom exercises every feature end-to-end, offline, using
the deterministic mock model (LLM_PROVIDER=mock) so no API keys are needed.

    python day7/solution/capstone.py                     # interactive
    python day7/solution/capstone.py --auto              # auto-approve
    python day7/solution/capstone.py --reject            # see human-driven revision
    LLM_PROVIDER=mock python day7/solution/capstone.py --auto     # fully offline
"""

from __future__ import annotations

import os
import pathlib
import re
import sys
from typing import List, Optional, TypedDict

# Make `config` + `shared` importable no matter where we're launched from.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402  (import FIRST — loads .env, silences chroma noise)

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

from config import get_llm, setup_langsmith  # noqa: E402
from shared.pretty import banner, node, ok, rule, warn  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Tuning knobs — the whole "production shape" is these five constants.
# ─────────────────────────────────────────────────────────────────────────────
MAX_REVISIONS = 3          # hard cap on the reflection loop (never loop forever)
MIN_DELTA = 0.05           # score must improve by this much between iterations
PASS_SCORE = 0.85          # "good enough" — a judge score at/above this passes
MIN_CITATIONS = 2          # programmatic check: report must cite ≥ N sources
LOW_CONFIDENCE = 0.65      # judge score below this → escalate to human even if
                           # the loop already burned its budget


# ─────────────────────────────────────────────────────────────────────────────
# Graph state — what flows between nodes. Every field is optional (total=False)
# so nodes only need to return the fields they change.
# ─────────────────────────────────────────────────────────────────────────────
class State(TypedDict, total=False):
    question: str
    plan: List[str]                # sub-questions
    cursor: int                    # which sub-question we're on
    findings: List[dict]           # [{sub_question, answer, sources}]
    draft: str                     # current report draft
    critique: str                  # judge's most recent feedback
    score: float                   # judge's most recent numeric score (0..1)
    scores: List[float]            # history — used for the plateau guard
    verdict: str                   # "PASS" | "REVISE"
    revisions: int                 # count of write attempts
    check_ok: bool                 # programmatic check (≥ MIN_CITATIONS citations)
    check_reason: str              # human-readable reason if the check failed
    approved: bool                 # human decision
    human_feedback: str            # human's revision notes (if any)
    final: str                     # published report


# ─────────────────────────────────────────────────────────────────────────────
# 1. PLAN — decompose the question into a few sub-questions.
#    (In the real assistant this is Day 1's shared/planner.py. We inline a
#    tiny mock-safe version here so this file runs standalone with no RAG.)
# ─────────────────────────────────────────────────────────────────────────────
def _plan(state: State) -> dict:
    node("plan", "decompose the question")
    q = state["question"]
    # A trivially useful decomposition that works with any question — good
    # enough for a teaching demo when Days 1-2 aren't wired up.
    sub_qs = [
        f"What is {q.rstrip('?')}?",
        f"Why does it matter?",
        f"How is it applied in practice?",
    ]
    return {"plan": sub_qs, "cursor": 0, "findings": [], "revisions": 0, "scores": []}


# ─────────────────────────────────────────────────────────────────────────────
# 2. RESEARCH — answer each sub-question. Uses Day 2's RAG when it's available;
#    otherwise falls back to a stubbed source so the graph still runs offline.
# ─────────────────────────────────────────────────────────────────────────────
def _research(state: State) -> dict:
    i = state["cursor"]
    sq = state["plan"][i]
    node("research", f"sub-question {i + 1}/{len(state['plan'])}: {sq}")
    try:
        from shared.rag import answer_question  # Day 2
        res = answer_question(sq, k=3)
        finding = {"sub_question": sq, "answer": res["answer"], "sources": res["sources"]}
    except Exception:
        # Offline fallback so the capstone runs with LLM_PROVIDER=mock.
        finding = {
            "sub_question": sq,
            "answer": f"(offline mock) A short answer to: {sq}",
            "sources": [f"mock-source-{i + 1}.md"],
        }
    return {"findings": state["findings"] + [finding], "cursor": i + 1}


def _research_more(state: State) -> str:
    """Conditional edge: loop through research, then move on to write."""
    return "research" if state["cursor"] < len(state["plan"]) else "write"


# ─────────────────────────────────────────────────────────────────────────────
# 3. WRITE — compose the report. On revision, incorporate the judge's critique
#    AND any human feedback so both channels visibly steer the next draft.
# ─────────────────────────────────────────────────────────────────────────────
def _write(state: State) -> dict:
    rev = state.get("revisions", 0) + 1
    node("write", f"compose report (revision #{rev})")
    llm = get_llm(temperature=0)
    body = "\n".join(
        f"- {f['sub_question']} → {f['answer']} (sources: {', '.join(f['sources'])})"
        for f in state["findings"]
    )
    guidance = ""
    if state.get("critique") and state.get("verdict") == "REVISE":
        guidance += f"\n\nAddress this critique:\n{state['critique']}"
    if state.get("human_feedback"):
        guidance += f"\n\nAlso incorporate this reviewer feedback:\n{state['human_feedback']}"

    prompt = (
        f"Write a well-structured research report answering: '{state['question']}'.\n"
        f"Use ONLY these findings and keep inline [n] citations for every claim:\n\n"
        f"{body}{guidance}"
    )
    draft = llm.invoke(prompt).content
    return {"draft": draft, "revisions": rev}


# ─────────────────────────────────────────────────────────────────────────────
# 4a. PROGRAMMATIC CHECK — deterministic, ALWAYS runs alongside the judge.
#     "The report cites at least MIN_CITATIONS sources." This is the kind of
#     rule you never trust an LLM-as-judge to enforce on its own.
# ─────────────────────────────────────────────────────────────────────────────
_CITE_RE = re.compile(r"\[(\d+)\]")


def programmatic_check(draft: str) -> tuple[bool, str]:
    """Return (ok, reason). Cheap, deterministic, unit-testable."""
    n = len({int(m) for m in _CITE_RE.findall(draft or "")})
    if n < MIN_CITATIONS:
        return False, f"only {n} distinct citation(s); need ≥ {MIN_CITATIONS}"
    if not (draft or "").strip():
        return False, "empty draft"
    return True, f"{n} distinct citations found"


# ─────────────────────────────────────────────────────────────────────────────
# 4b. REFLECT — the LLM-as-judge. Returns a verdict AND a numeric score so we
#     can measure IMPROVEMENT between iterations (not just PASS/FAIL).
# ─────────────────────────────────────────────────────────────────────────────
_SCORE_RE = re.compile(r"SCORE\s*[:=]\s*([01](?:\.\d+)?)", re.IGNORECASE)


def _extract_score(text: str) -> float:
    """Pull 'SCORE: 0.72' out of the judge's response. Falls back to a
    heuristic based on the verdict so mock models still produce a score."""
    m = _SCORE_RE.search(text or "")
    if m:
        try:
            return max(0.0, min(1.0, float(m.group(1))))
        except ValueError:
            pass
    # Heuristic fallback — enough signal for the plateau guard to work with
    # the deterministic mock model (which returns "Verdict: PASS").
    up = (text or "").upper()
    if "VERDICT: PASS" in up:
        return 0.90
    if "VERDICT: REVISE" in up:
        return 0.60
    return 0.50


def _reflect(state: State) -> dict:
    node("reflect", "judge the draft (verdict + score)")
    llm = get_llm(temperature=0)
    critique = llm.invoke(
        "You are a STRICT editor. Grade the DRAFT against the QUESTION on:\n"
        "  • does it answer the question? • are claims cited [n]? • is it clear?\n"
        "Write a short critique (2-4 concrete fixes), then on the LAST TWO lines write "
        "exactly:\n"
        "  SCORE: <0.00-1.00>\n"
        "  VERDICT: PASS|REVISE\n\n"
        f"QUESTION: {state['question']}\n\nDRAFT:\n{state['draft']}"
    ).content
    score = _extract_score(critique)
    verdict = "PASS" if "VERDICT: PASS" in critique.upper() or score >= PASS_SCORE else "REVISE"

    # Programmatic check runs ALONGSIDE the judge — both must agree to publish.
    check_ok, reason = programmatic_check(state["draft"])
    return {
        "critique": critique,
        "score": score,
        "scores": state.get("scores", []) + [score],
        "verdict": verdict,
        "check_ok": check_ok,
        "check_reason": reason,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. ROUTER — the reflection loop's brain. Three independent stop conditions:
#     (a) hard iteration cap    → escalate / approve
#     (b) score PLATEAU         → escalate / approve (measurable improvement req'd)
#     (c) judge + check BOTH ok → straight to approval / publish
#    Falling out to `approval` (never straight to publish) preserves the human
#    gate — the model can't unilaterally "declare victory".
# ─────────────────────────────────────────────────────────────────────────────
def _route_after_reflect(state: State) -> str:
    revisions = state.get("revisions", 0)
    scores = state.get("scores", []) or [state.get("score", 0.0)]

    # (a) hard cap
    if revisions >= MAX_REVISIONS:
        print(f"    ⛔  revision cap ({MAX_REVISIONS}) hit — escalating to human")
        return "approval"

    # (b) plateau guard — stop if we didn't improve enough since last round
    if len(scores) >= 2 and (scores[-1] - scores[-2]) < MIN_DELTA:
        print(f"    ⛔  score plateau ({scores[-2]:.2f} → {scores[-1]:.2f}, "
              f"Δ<{MIN_DELTA}) — escalating to human")
        return "approval"

    # (c) both judge and programmatic check happy → go to approval
    if state.get("verdict") == "PASS" and state.get("check_ok"):
        return "approval"

    # Otherwise revise.
    print(f"    ↻  verdict={state.get('verdict')} score={state.get('score', 0):.2f}"
          f" check_ok={state.get('check_ok')} — revising")
    return "write"


# ─────────────────────────────────────────────────────────────────────────────
# 6. APPROVAL — human-in-the-loop gate. This is where interrupt() pauses.
#    NB: interrupt() requires the graph to be compiled WITH a checkpointer,
#    otherwise there's no persistent state to resume from.
# ─────────────────────────────────────────────────────────────────────────────
def _approval(state: State) -> dict:
    node("approval", "⏸  interrupt() — awaiting human decision")

    # Auto-escalate: if the judge's confidence is LOW, add a warning so the
    # reviewer knows this shouldn't be a rubber-stamp approval.
    escalate = state.get("score", 0.0) < LOW_CONFIDENCE

    decision = interrupt({
        "type": "approval_request",
        "message": "Approve publishing this report?",
        "draft": state["draft"],
        "critique": state.get("critique", ""),
        "score": state.get("score"),
        "check_ok": state.get("check_ok"),
        "check_reason": state.get("check_reason", ""),
        "escalated": escalate,
    })

    # Accept either a dict {approved, feedback} or a bare string ("approve"/text).
    if isinstance(decision, dict):
        approved = bool(decision.get("approved", True))
        feedback = decision.get("feedback", "")
    else:
        approved = str(decision).strip().lower() in {"approve", "approved", "yes", "y", "publish"}
        feedback = "" if approved else str(decision)
    return {"approved": approved, "human_feedback": feedback}


def _route_after_approval(state: State) -> str:
    """Approved → publish. Rejected → one more revision (if budget), else publish."""
    if state.get("approved"):
        return "publish"
    if state.get("revisions", 0) < MAX_REVISIONS + 1:
        return "write"
    return "publish"


# ─────────────────────────────────────────────────────────────────────────────
# 7. PUBLISH — the "high-stakes action". In real life this is sending an email,
#    filing a ticket, opening a PR. Here we just tag the final report.
# ─────────────────────────────────────────────────────────────────────────────
def _publish(state: State) -> dict:
    node("publish", "finalize the report")
    status = "✅ APPROVED & PUBLISHED" if state.get("approved") else "⚠ PUBLISHED WITHOUT APPROVAL"
    stamp = (
        f"\n\n---\n{status}"
        f"\nscore={state.get('score', 0):.2f}"
        f"  revisions={state.get('revisions', 0)}"
        f"  check={state.get('check_reason', '')}"
    )
    return {"final": state["draft"] + stamp}


# ─────────────────────────────────────────────────────────────────────────────
# Assemble the graph. A checkpointer is REQUIRED — interrupt() persists state
# to it and Command(resume=...) reads that state back.
# ─────────────────────────────────────────────────────────────────────────────
def build_capstone(checkpointer=None):
    g = StateGraph(State)
    g.add_node("plan", _plan)
    g.add_node("research", _research)
    g.add_node("write", _write)
    g.add_node("reflect", _reflect)
    g.add_node("approval", _approval)
    g.add_node("publish", _publish)

    g.add_edge(START, "plan")
    g.add_edge("plan", "research")
    g.add_conditional_edges("research", _research_more, {"research": "research", "write": "write"})
    g.add_edge("write", "reflect")
    g.add_conditional_edges("reflect", _route_after_reflect, {"write": "write", "approval": "approval"})
    g.add_conditional_edges("approval", _route_after_approval, {"write": "write", "publish": "publish"})
    g.add_edge("publish", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


# ─────────────────────────────────────────────────────────────────────────────
# Demo driver — streams node updates so students can see the flow in real time.
# ─────────────────────────────────────────────────────────────────────────────
def _pump(app, inp, cfg) -> Optional[dict]:
    """Stream one invocation. Returns the interrupt payload if the graph paused."""
    for chunk in app.stream(inp, cfg, stream_mode="updates"):
        if "__interrupt__" in chunk:
            return chunk["__interrupt__"][0].value
        for name, upd in chunk.items():
            if name == "reflect":
                print(f"    → score={upd.get('score', 0):.2f}  verdict={upd.get('verdict')}"
                      f"  check_ok={upd.get('check_ok')} ({upd.get('check_reason', '')})")
            elif name == "write":
                print(f"    → draft ready (rev #{upd.get('revisions')})")
    return None


def _decide(payload: dict, mode: str) -> dict:
    """Return the human decision. `mode` may force auto approve/reject offline."""
    rule()
    tag = " · ⚠ LOW CONFIDENCE, ESCALATED" if payload.get("escalated") else ""
    warn(f"HUMAN APPROVAL REQUIRED{tag}")
    print(f"  score      : {payload.get('score')}")
    print(f"  check      : {'ok' if payload.get('check_ok') else 'FAIL'} — {payload.get('check_reason')}")
    print(f"  critique   : {(payload.get('critique') or '')[:200]}...")
    print(f"\n  draft (first 500 chars):\n{'  ' + (payload.get('draft') or '')[:500]}...")
    rule()
    if mode == "auto":
        print("(--auto) → approving\n")
        return {"approved": True, "feedback": ""}
    if mode == "reject":
        print("(--reject) → rejecting with feedback\n")
        return {"approved": False, "feedback": "Add a concrete example and a one-line recommendation."}
    ans = input("Approve publish? [y/N or free-text feedback]: ").strip()
    if ans.lower() in {"y", "yes", "approve"}:
        return {"approved": True, "feedback": ""}
    return {"approved": False, "feedback": ans or "reject"}


def main():
    args = sys.argv[1:]
    mode = "interactive"
    if "--auto" in args:
        mode = "auto"; args.remove("--auto")
    if "--reject" in args:
        mode = "reject"; args.remove("--reject")
    question = " ".join(args).strip() or "Should I use similarity or MMR retrieval for a RAG system?"

    banner("Day 7 CAPSTONE — reflection · HITL · observability")
    traced = setup_langsmith()
    if traced:
        ok(f"LangSmith tracing ENABLED → https://smith.langchain.com "
           f"(project={os.environ.get('LANGSMITH_PROJECT', 'default')})")
    else:
        print("LangSmith tracing OFF — set LANGSMITH_TRACING=true + LANGSMITH_API_KEY to enable.")
    print(f"Question: {question}\n")

    app = build_capstone()
    cfg = {"configurable": {"thread_id": "day7-capstone"}}

    payload = _pump(app, {"question": question}, cfg)
    while payload is not None:  # keep looping while the graph pauses (may pause more than once)
        decision = _decide(payload, mode)
        payload = _pump(app, Command(resume=decision), cfg)

    final = app.get_state(cfg).values.get("final", "(no final report)")
    scores = app.get_state(cfg).values.get("scores", [])
    rule("═")
    print(f"score trace: {[round(s, 2) for s in scores]}")
    print(f"\nFINAL REPORT:\n\n{final}")


if __name__ == "__main__":
    main()
