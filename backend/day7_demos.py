"""
backend/day7_demos.py — TRANSPARENT Day 7 sub-tab demos.

Each demo returns a `slide_demo` payload (rendered by frontend/src/components
/DayResult.jsx > SlideDemo) so learners SEE the full flow in the browser:

  M1 · Reflection loop  — draft → judge (score) → plateau guard → stop
  M2 · Programmatic check — deterministic pass/fail alongside the judge
  M3 · Judge + check    — both must agree before auto-publish
  M4 · Human gate       — the interrupt() payload + resume semantics
  M5 · Escalation       — low judge confidence → escalate to human
  M6 · Full capstone    — end-to-end trace through the real shared graph
  M7 · Observability    — LangSmith on/off, what the trace looks like

These are OFFLINE-safe: they short-circuit LLM output shape when needed and
never require a live API.
"""

from __future__ import annotations

import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from config import setup_langsmith, settings  # noqa: E402

# Import the capstone building blocks so the studio demos and the CLI show
# the SAME logic — no drift between what students read and what they see.
from day7.solution.capstone import (  # noqa: E402
    LOW_CONFIDENCE,
    MAX_REVISIONS,
    MIN_CITATIONS,
    MIN_DELTA,
    PASS_SCORE,
    _extract_score,
    programmatic_check,
)


# ─── shared helpers ──────────────────────────────────────────────────────────
def _wrap(title: str, subtitle: str, steps: list) -> dict:
    return {"kind": "slide_demo", "mode": "module", "slide": 1,
            "title": title, "subtitle": subtitle, "steps": steps}


def _heading(label: str, desc: str = "") -> dict:
    return {"type": "heading", "label": label, "desc": desc}


def _note(text: str) -> dict:
    return {"type": "note", "text": text}


def _tag(label: str, text: str) -> dict:
    return {"type": "tag", "label": label, "text": text}


def _code(title: str, code: str) -> dict:
    return {"type": "code_view", "title": title, "code": code}


def _verdict(passed: bool, issues=None) -> dict:
    return {"type": "verdict", "passed": passed, "issues": issues or []}


def _final(text: str) -> dict:
    return {"type": "final", "text": text}


def _takeaway(text: str) -> dict:
    return {"type": "takeaway", "text": text}


# ═════════════════════════════════════════════════════════════════════════════
# M1 · Reflection loop — the plateau guard is the real teaching point
# ═════════════════════════════════════════════════════════════════════════════
def m1_reflection(_q: str = "") -> dict:
    """A hand-run 3-iteration loop showing scores, deltas, and the plateau
    guard firing before the hard cap."""
    scores = [0.55, 0.72, 0.74]  # improve, improve, plateau
    steps = [
        _heading("What a bounded reflection loop looks like",
                 "Two independent stopping rules: (a) hard cap, (b) score plateau."),
        _code("The router (from day7/solution/capstone.py)", '''def _route_after_reflect(state):
    if revisions >= MAX_REVISIONS: return "approval"           # (a) hard cap
    if len(scores) >= 2 and (scores[-1] - scores[-2]) < MIN_DELTA:
        return "approval"                                       # (b) plateau
    if verdict == "PASS" and check_ok: return "approval"        # (c) both agree
    return "write"                                              # keep revising'''),
        _heading("Iteration 1", "First draft"),
        _tag("SCORE", f"{scores[0]:.2f}   verdict=REVISE   → revise"),
        _heading("Iteration 2", "Δ = +0.17 → keep going"),
        _tag("SCORE", f"{scores[1]:.2f}   Δ={scores[1] - scores[0]:+.2f} ≥ {MIN_DELTA}   → revise"),
        _heading("Iteration 3", f"Δ = +0.02 → below MIN_DELTA ({MIN_DELTA}) → PLATEAU"),
        _tag("SCORE", f"{scores[2]:.2f}   Δ={scores[2] - scores[1]:+.2f} < {MIN_DELTA}   ⛔ escalate"),
        {"type": "route_decision", "chose": "approval",
         "options": ["write", "approval"],
         "because": f"score plateau ({scores[1]:.2f} → {scores[2]:.2f}, Δ<{MIN_DELTA})"},
        _takeaway("Without the plateau guard, a mediocre draft that can't improve "
                  "will burn tokens until the hard cap. Always require MEASURABLE improvement."),
    ]
    return _wrap("Reflection loop · bounded self-critique",
                 f"cap={MAX_REVISIONS} · min-delta={MIN_DELTA} · pass-score={PASS_SCORE}",
                 steps)


# ═════════════════════════════════════════════════════════════════════════════
# M2 · Programmatic check — deterministic, unit-testable, no LLM
# ═════════════════════════════════════════════════════════════════════════════
def m2_programmatic(_q: str = "") -> dict:
    """Run the programmatic check against 4 drafts so students see exactly
    what it catches vs waves through — no LLM involved."""
    drafts = [
        ("Draft A — 0 citations",
         "MMR balances relevance and diversity in retrieval."),
        ("Draft B — 1 citation",
         "MMR balances relevance and diversity [1] in retrieval systems."),
        ("Draft C — 2 distinct citations",
         "Similarity picks the closest chunks [1] while MMR adds diversity [2]."),
        ("Draft D — 3 citations (one duplicate)",
         "Similarity picks the closest chunks [1] while MMR [2] adds diversity [1] and coverage [3]."),
    ]
    rows = [["draft", "distinct [n]", "≥ MIN_CITATIONS", "ok?"]]
    steps = [
        _heading("Deterministic guardrail", f"Must contain at least {MIN_CITATIONS} distinct [n] citations."),
        _code("The check", '''_CITE = re.compile(r"\\[(\\d+)\\]")

def programmatic_check(draft: str) -> tuple[bool, str]:
    n = len({int(m) for m in _CITE.findall(draft or "")})
    if n < MIN_CITATIONS:
        return False, f"only {n} citation(s); need >= {MIN_CITATIONS}"
    return True, f"{n} distinct citations"'''),
    ]
    for name, draft in drafts:
        ok, reason = programmatic_check(draft)
        steps.append(_heading(name))
        steps.append(_note(f'"{draft}"'))
        steps.append(_verdict(ok, issues=[] if ok else [reason]))
        steps.append(_tag("REASON", reason))
    steps.append(_takeaway("The judge could easily miss a missing citation. A 5-line regex "
                           "never will. Keep the deterministic checks alongside the LLM judge."))
    return _wrap("Programmatic check · deterministic pass/fail",
                 "No LLM. Cheap, reliable, unit-testable.",
                 steps)


# ═════════════════════════════════════════════════════════════════════════════
# M3 · Judge + check — both must agree before publish
# ═════════════════════════════════════════════════════════════════════════════
def m3_judge_and_check(_q: str = "") -> dict:
    cases = [
        # (label, judge_verdict, judge_score, check_ok, expected_route)
        ("Judge PASS · check FAIL",  "PASS",   0.90, False, "write (fix citations)"),
        ("Judge REVISE · check PASS", "REVISE", 0.60, True,  "write (address critique)"),
        ("Judge PASS · check PASS · high confidence", "PASS", 0.92, True, "approval → auto-publish"),
        ("Judge PASS · check PASS · LOW confidence",  "PASS", 0.58, True, "approval → ESCALATE"),
    ]
    steps = [
        _heading("Auto-publish requires BOTH signals",
                 "The judge alone will happily approve uncited drafts. The check alone will "
                 "wave through fluent nonsense. Pair them."),
        {"type": "table",
         "headers": ["scenario", "judge", "score", "check", "→ router picks"],
         "rows": [[c[0], c[1], f"{c[2]:.2f}", "ok" if c[3] else "FAIL", c[4]] for c in cases]},
        _takeaway("The router in the exercise implements exactly this decision matrix."),
    ]
    return _wrap("Judge + programmatic check · both must agree",
                 f"LOW_CONFIDENCE = {LOW_CONFIDENCE} · below this we escalate even on PASS",
                 steps)


# ═════════════════════════════════════════════════════════════════════════════
# M4 · Human gate — anatomy of an interrupt()
# ═════════════════════════════════════════════════════════════════════════════
def m4_human_gate(_q: str = "") -> dict:
    steps = [
        _heading("interrupt() = pause + persist",
                 "The graph stops, its state is saved by the checkpointer, and the caller "
                 "resumes with Command(resume=<decision>) — possibly seconds or days later."),
        _code("The gate node", '''def _approval(state):
    decision = interrupt({                       # ← this PAUSES the graph
        "type": "approval_request",
        "draft": state["draft"],
        "score": state.get("score"),
        "check_ok": state.get("check_ok"),
        "escalated": state.get("score", 0) < LOW_CONFIDENCE,
    })
    approved = bool(decision.get("approved"))
    return {"approved": approved, "human_feedback": decision.get("feedback", "")}'''),
        _code("Resuming from the driver", '''# on the outside — after collecting the human's decision:
app.invoke(Command(resume={"approved": True, "feedback": ""}), cfg)
# execution continues from EXACTLY where it paused, using the checkpointed state.'''),
        _heading("Why the checkpointer is mandatory"),
        _tag("RULE", "interrupt() only works when the graph is compiled with a checkpointer."),
        _tag("RULE", "The `thread_id` in cfg is what pins state to a specific conversation."),
        _tag("RULE", "Persist across process restarts by using SqliteSaver instead of MemorySaver."),
        _takeaway("Never gate on the LLM. Gate on interrupt() before any irreversible action "
                  "(publish, send, pay, delete)."),
    ]
    return _wrap("Human-in-the-loop · interrupt() + resume",
                 "The mechanism you use for every high-stakes action.",
                 steps)


# ═════════════════════════════════════════════════════════════════════════════
# M5 · Escalation — even PASS can be routed to a human when confidence is low
# ═════════════════════════════════════════════════════════════════════════════
def m5_escalation(_q: str = "") -> dict:
    steps = [
        _heading("Trust ≠ verdict", f"score < LOW_CONFIDENCE ({LOW_CONFIDENCE}) → escalate to human."),
        {"type": "compare_grid",
         "title": "How the router treats two PASS drafts",
         "left":  {"title": "High-confidence PASS", "rows": [
             ["verdict", "PASS"], ["score", "0.92"], ["check_ok", "true"],
             ["route", "approval → auto-publish"]]},
         "right": {"title": "Low-confidence PASS (escalate)", "rows": [
             ["verdict", "PASS"], ["score", "0.58"], ["check_ok", "true"],
             ["route", "approval → ESCALATED to human"]]}},
        _code("Escalation flag in the interrupt payload", '''decision = interrupt({
    "type": "approval_request",
    "draft": state["draft"],
    "escalated": state.get("score", 0.0) < LOW_CONFIDENCE,  # ← UI badges this in red
    ...
})'''),
        _takeaway("Escalation is CHEAP insurance. When a low-confidence draft ships silently, "
                  "you learn about it from users, not from your traces."),
    ]
    return _wrap("Escalation · route low-confidence drafts to humans",
                 f"LOW_CONFIDENCE threshold = {LOW_CONFIDENCE}",
                 steps)


# ═════════════════════════════════════════════════════════════════════════════
# M6 · Full capstone — run the SHARED research agent, stream a live trace
# ═════════════════════════════════════════════════════════════════════════════
def m6_full(q: str = "") -> dict:
    """Reuse the same graph the Studio tab runs, capture every hop as a
    slide_demo step. Auto-approves so it completes in one call."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    steps: list = [_heading("Live end-to-end run", "The exact graph the Studio tab drives.")]
    try:
        from shared.research_agent import NODE_LABELS, build_research_agent
        app = build_research_agent(MemorySaver())
    except Exception as e:
        # Offline fallback: the shared RAG chain needs a real provider.
        steps.append(_tag("SKIPPED", f"shared graph unavailable in this environment: {e}"))
        steps.append(_note("Configure a real LLM_PROVIDER + Chroma index to run the full "
                           "graph. The Studio tab uses the same code path."))
        return _wrap("Capstone · full run (offline fallback)",
                     "Requires a real LLM provider to hit the shared research agent.",
                     steps)
    cfg = {"configurable": {"thread_id": f"lab7-{uuid.uuid4()}"}}

    def _pump(inp):
        for chunk in app.stream(inp, cfg, stream_mode="updates"):
            if "__interrupt__" in chunk:
                return chunk["__interrupt__"][0].value
            for name, upd in chunk.items():
                label = NODE_LABELS.get(name, "")
                if name == "research":
                    findings = upd.get("findings") or []
                    if findings:
                        steps.append(_tag(name.upper(),
                                          f"answered: {findings[-1]['sub_question']}  "
                                          f"(sources: {', '.join(findings[-1]['sources'])})"))
                elif name == "write":
                    steps.append(_tag(name.upper(), f"draft ready (revision #{upd.get('revisions')})"))
                elif name == "reflect":
                    steps.append(_verdict(upd.get("verdict") == "PASS",
                                          issues=[] if upd.get("verdict") == "PASS"
                                                    else [(upd.get("critique") or "").splitlines()[-1][:120]]))
                else:
                    steps.append(_tag(name.upper(), label))
        return None

    try:
        payload = _pump({"question": q or "Should I use similarity or MMR retrieval for a RAG system?"})
        if payload is not None:
            steps.append(_heading("interrupt() fired", "graph paused at approval gate — auto-approving for the demo"))
            steps.append(_tag("PAUSED", f"draft chars: {len(payload.get('draft', ''))} · "
                                        f"critique: {(payload.get('critique') or '')[:120]}..."))
            _pump(Command(resume={"approved": True, "feedback": ""}))
        final = app.get_state(cfg).values.get("final", "(no final)")
        steps.append(_final(final))
    except Exception as e:
        steps.append(_tag("ERROR", f"{type(e).__name__}: {e}"))
        steps.append(_note("This live demo needs a real LLM_PROVIDER. Modules 1–5 and 7 show the "
                           "same concepts without any live model calls."))
    steps.append(_takeaway("Every hop above is exactly what the CLI capstone prints — same code, "
                           "same graph. The Studio tab lets you take over the approval decision."))
    return _wrap("Capstone · full run", "plan → research → write → reflect → approve → publish", steps)


# ═════════════════════════════════════════════════════════════════════════════
# M7 · Observability — LangSmith on/off
# ═════════════════════════════════════════════════════════════════════════════
def m7_observability(_q: str = "") -> dict:
    traced = setup_langsmith()
    steps = [
        _heading("One env var flips everything on"),
        _code(".env snippet", 'LANGSMITH_TRACING=true\nLANGSMITH_API_KEY=lsv2_...\nLANGSMITH_PROJECT=research-assistant-labs'),
        _tag("STATUS", "✅ ENABLED — traces at https://smith.langchain.com" if traced
                       else "○ OFF — the code above runs unchanged; tracing simply doesn't happen."),
        _heading("What you'll see in the trace tree"),
        _note("• every node (plan/research/write/reflect/approval/publish) as a span"),
        _note("• every LLM call with its prompt, response, latency, and token counts"),
        _note("• the reflection loop's revision hops, one span per iteration"),
        _note("• the interrupt() pause and the resume, with the payload attached"),
        _takeaway("Debugging an agent without traces is guessing. Turn it on before you need it."),
    ]
    return _wrap("Observability · LangSmith",
                 f"provider: {settings.llm_provider} · tracing currently: {'ON' if traced else 'OFF'}",
                 steps)


DEMOS = {
    "m1_reflection":   m1_reflection,
    "m2_programmatic": m2_programmatic,
    "m3_judge_check":  m3_judge_and_check,
    "m4_hitl":         m4_human_gate,
    "m5_escalation":   m5_escalation,
    "m6_full":         m6_full,
    "m7_observe":      m7_observability,
}
