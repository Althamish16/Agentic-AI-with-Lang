"""
backend/day6_demos.py — TRANSPARENT Day 6 demos for the teaching UI.

Every function returns a payload with a specific `kind:` that maps to a
renderer in `frontend/src/components/DayResult.jsx`. The goal is that
learners SEE exactly what happens at every hop:

  • `team_topology`  — the shapes (single/supervisor/hierarchical) side-by-side,
                       plus the shared vs private state table.
  • `team_worker`    — run ONE worker (researcher or writer) in isolation,
                       expose its private state so isolation is visible.
  • `team_trace`     — full supervisor→worker→…→FINISH trace with per-step
                       input/output snapshots.
  • `team_resume`    — phase-1 (interrupted) then phase-2 (resumed) with
                       step numbers; proves state survives a crash.
  • `team_critic`    — bounded writer↔critic loop showing every revision.
  • `team_tokens`    — token comparison between the team and a single agent.

All of these run OFFLINE by default via `day6._llm.get_llm()`. Set
DAY6_PROVIDER=course|openai|anthropic to swap models without touching the UI.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.sqlite import SqliteSaver

from day6._llm import provider_label
from day6.solution.team import (
    MAX_STEPS,
    TEAM_INVOKE_CONFIG,
    build_researcher,
    build_team,
    build_writer,
    web_search,
)
from day6.solution.resume_demo import _build_team_with_checkpointer
from day6.exercise.critic_team import (
    INVOKE_CFG as CRITIC_INVOKE_CFG,
    count_tokens,
    run_single_agent,
)
from day6.exercise.solution import build_critic_team


def _reset_mock_critic() -> None:
    """The mock critic uses a class-level counter to hand out REVISE-then-APPROVE
    across a single run. Reset it at the top of each demo so the studio produces
    the exact same trace on every click (real providers just ignore this)."""
    try:
        from day6._llm import _MockChat  # type: ignore
        _MockChat._critic_calls = 0
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════════════════════
# M1 · Topology — no LLM. Explain the three shapes and the state contract.
# ═════════════════════════════════════════════════════════════════════════════
def m1_topology(_q: str = "") -> dict:
    return {
        "kind": "team_topology",
        "provider": provider_label(),
        "shapes": [
            {
                "name": "Single agent",
                "when": "Small task, homogeneous tools, quality-good-enough on the first try.",
                "cost": "1× tokens · 1× latency",
                "diagram": "user → agent → answer",
            },
            {
                "name": "Supervisor + workers  (this lab)",
                "when": "Specialised sub-tasks, each worker owns a tool or scope. Reviewer patterns.",
                "cost": "N× tokens · N× hops · clearer failure isolation",
                "diagram": "user → supervisor ↔ (researcher · writer) → FINISH",
            },
            {
                "name": "Hierarchical (teams of teams)",
                "when": "Whole departments of agents — a supervisor of supervisors.",
                "cost": "N² tokens · deep debugging cost — reach for last.",
                "diagram": "user → CEO → (research-team · writing-team) → FINISH",
            },
        ],
        "state_contract": [
            {"field": "topic",     "scope": "SHARED",  "note": "the user's question — every worker reads it"},
            {"field": "findings",  "scope": "SHARED",  "note": "researcher WRITES · writer READS"},
            {"field": "draft",     "scope": "SHARED",  "note": "writer WRITES · supervisor + critic READ"},
            {"field": "trace",     "scope": "SHARED",  "note": "append-only log (uses operator.add reducer)"},
            {"field": "step",      "scope": "SHARED",  "note": "monotonic counter — safety belt"},
            {"field": "next",      "scope": "SHARED",  "note": "routing key the supervisor writes"},
            {"field": "sub_questions", "scope": "PRIVATE (researcher)", "note": "never leaked to the parent"},
            {"field": "cursor",    "scope": "PRIVATE (researcher)",     "note": "which sub-question is next"},
        ],
        "pitfalls": [
            "Going multi-agent too early — a single well-prompted LLM often wins on small tasks.",
            "Two workers writing the SAME field silently clobber each other.",
            "No step/budget cap → a broken supervisor loops forever.",
            "Trusting worker output blindly — errors propagate across hand-offs.",
        ],
    }


# ═════════════════════════════════════════════════════════════════════════════
# M2 · Researcher in isolation — show its PRIVATE state (sub_questions, cursor)
# ═════════════════════════════════════════════════════════════════════════════
def m2_researcher(q: str = "") -> dict:
    topic = q.strip() or "multi-agent supervisor patterns"
    researcher = build_researcher()

    trace: list[dict] = []
    private_final = {}
    for update in researcher.stream({"topic": topic}, stream_mode="updates"):
        for node, patch in update.items():
            trace.append({
                "node": node,
                "patch_keys": list(patch.keys()) if isinstance(patch, dict) else [],
                "cursor": patch.get("cursor") if isinstance(patch, dict) else None,
                "findings_added": len(patch.get("findings", [])) - len(private_final.get("findings", []))
                    if isinstance(patch, dict) and "findings" in patch else 0,
            })
            if isinstance(patch, dict):
                private_final = {**private_final, **patch}

    return {
        "kind": "team_worker",
        "provider": provider_label(),
        "worker": "researcher",
        "topic": topic,
        "input_shape": ["topic"],
        "private_fields": ["sub_questions", "cursor"],
        "output_shape": ["findings"],
        "sub_questions": private_final.get("sub_questions") or [],
        "findings": private_final.get("findings") or [],
        "trace": trace,
        "note": (
            "The researcher's sub_questions and cursor NEVER reach the parent. "
            "It exposes only `findings` — that's context isolation."
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# M3 · Writer in isolation — canned findings so the writer proves it doesn't
# need to know how they were gathered.
# ═════════════════════════════════════════════════════════════════════════════
def m3_writer(q: str = "") -> dict:
    topic = q.strip() or "multi-agent supervisor patterns"
    canned = [
        {"sub_question": f"What is {topic}?", "evidence": web_search(f"definition of {topic}")},
        {"sub_question": f"How does {topic} work?", "evidence": web_search(f"practice of {topic}")},
    ]
    writer = build_writer()
    result = writer.invoke({"topic": topic, "findings": canned})
    return {
        "kind": "team_worker",
        "provider": provider_label(),
        "worker": "writer",
        "topic": topic,
        "input_shape": ["topic", "findings"],
        "private_fields": [],
        "output_shape": ["draft"],
        "findings_in": canned,
        "draft": result["draft"],
        "note": (
            "The writer sees ONLY the shared slice it needs — {topic, findings}. "
            "It cannot access the researcher's cursor or the supervisor's routing key."
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# M4 · Team run — full supervisor→worker→…→FINISH trace
# ═════════════════════════════════════════════════════════════════════════════
def m4_team(q: str = "") -> dict:
    topic = q.strip() or "multi-agent supervisor patterns"
    team = build_team()

    steps: list[dict] = []
    running_state: dict = {}
    for update in team.stream({"topic": topic}, TEAM_INVOKE_CONFIG, stream_mode="updates"):
        for node, patch in update.items():
            if isinstance(patch, dict):
                # `trace` is a reducer field — dict-spread would overwrite it,
                # so accumulate it by hand to keep the full delegation log.
                if "trace" in patch:
                    running_state["trace"] = (running_state.get("trace") or []) + patch["trace"]
                    patch = {k: v for k, v in patch.items() if k != "trace"}
                running_state = {**running_state, **patch}
            steps.append({
                "n": len(steps) + 1,
                "node": node,
                "patch_summary": _summarize_patch(patch),
                "step_field": running_state.get("step"),
                "next": running_state.get("next"),
                "findings_count": len(running_state.get("findings") or []),
                "has_draft": bool(running_state.get("draft")),
            })

    return {
        "kind": "team_trace",
        "provider": provider_label(),
        "topic": topic,
        "steps": steps,
        "trace": running_state.get("trace") or [],
        "final": running_state.get("final") or running_state.get("draft") or "",
        "findings": running_state.get("findings") or [],
        "note": (
            "One conditional edge from the supervisor is the whole delegation pattern. "
            "Workers report back so the supervisor can decide the next step."
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# M5 · Kill & resume — phase 1 crashes after N steps, phase 2 resumes.
# ═════════════════════════════════════════════════════════════════════════════
# One shared checkpoint DB for every Day-6 studio session. Each click uses a
# UNIQUE thread_id so runs never cross-contaminate — same production pattern
# as an app with per-user threads. Files are never deleted (Windows keeps
# sqlite files locked, so unlink from inside the process is unreliable).
_STUDIO_DB = pathlib.Path(__file__).with_name("day6_studio_checkpoints.sqlite")


def m5_resume(q: str = "") -> dict:
    topic = q.strip() or "multi-agent supervisor patterns"
    tid = f"studio-day6-{uuid.uuid4().hex[:8]}"

    def _cp() -> SqliteSaver:
        return SqliteSaver(sqlite3.connect(str(_STUDIO_DB), check_same_thread=False))

    def _cfg() -> dict:
        return {**TEAM_INVOKE_CONFIG, "configurable": {"thread_id": tid}}

    phase1_steps: list[dict] = []
    INTERRUPT_AFTER = 4

    try:
        app1 = _build_team_with_checkpointer(_cp())
        seen = 0
        for update in app1.stream({"topic": topic}, _cfg(), stream_mode="updates"):
            seen += 1
            for node, patch in update.items():
                phase1_steps.append({
                    "n": seen, "node": node,
                    "step_field": patch.get("step") if isinstance(patch, dict) else None,
                })
            if seen >= INTERRUPT_AFTER:
                raise KeyboardInterrupt()
    except KeyboardInterrupt:
        pass

    # ── new SqliteSaver connection = a "new process" for this thread ──
    app_ro = _build_team_with_checkpointer(_cp())
    snap = app_ro.get_state(_cfg())
    persisted = {
        "step": snap.values.get("step"),
        "findings": len(snap.values.get("findings") or []),
        "has_draft": bool(snap.values.get("draft")),
        "next": list(snap.next) or [],
        "trace_len": len(snap.values.get("trace") or []),
    }

    # Phase 2 — resume with input=None on the SAME thread_id.
    app2 = _build_team_with_checkpointer(_cp())
    phase2_steps: list[dict] = []
    seen = 0
    for update in app2.stream(None, _cfg(), stream_mode="updates"):
        seen += 1
        for node, patch in update.items():
            phase2_steps.append({
                "n": seen, "node": node,
                "step_field": patch.get("step") if isinstance(patch, dict) else None,
            })
        if seen > MAX_STEPS:
            break

    final = app2.get_state(_cfg()).values

    return {
        "kind": "team_resume",
        "provider": provider_label(),
        "topic": topic,
        "thread_id": tid,
        "interrupt_after": INTERRUPT_AFTER,
        "phase1_steps": phase1_steps,
        "persisted": persisted,
        "phase2_steps": phase2_steps,
        "final": final.get("final") or final.get("draft") or "",
        "note": (
            "The same thread_id is the ONLY thing tying phase 1 and phase 2 together. "
            "Change it and you're on a fresh conversation — the old state is still on disk, "
            "just under a different key."
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# M6 · Critic loop — bounded writer↔critic revisions
# ═════════════════════════════════════════════════════════════════════════════
def m6_critic(q: str = "") -> dict:
    topic = q.strip() or "multi-agent supervisor patterns"
    _reset_mock_critic()
    team = build_critic_team()
    state = team.invoke({"topic": topic}, CRITIC_INVOKE_CFG)
    return {
        "kind": "team_critic",
        "provider": provider_label(),
        "topic": topic,
        "trace": state.get("trace") or [],
        "revisions": state.get("revisions") or 0,
        "verdict": state.get("verdict") or "approve",
        "critique": state.get("critique") or "",
        "draft": state.get("draft") or "",
        "final": state.get("final") or "",
        "tokens": state.get("tokens") or [],
        "note": (
            "The writer↔critic bounce is one conditional edge, capped by MAX_REVISIONS. "
            "The mock critic revises once then approves — deterministic teaching signal."
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# M7 · Team vs single agent — the token cost of hand-offs
# ═════════════════════════════════════════════════════════════════════════════
def m7_tokens(q: str = "") -> dict:
    topic = q.strip() or "multi-agent supervisor patterns"
    _reset_mock_critic()
    team = build_critic_team()
    state = team.invoke({"topic": topic}, CRITIC_INVOKE_CFG)
    single = run_single_agent(topic)

    team_tokens = state.get("tokens") or []
    single_tokens = single["tokens"]
    team_total = sum(t["input_tokens"] + t["output_tokens"] for t in team_tokens)
    single_total = sum(t["input_tokens"] + t["output_tokens"] for t in single_tokens)
    return {
        "kind": "team_tokens",
        "provider": provider_label(),
        "topic": topic,
        "team": {
            "tokens": team_tokens,
            "total": team_total,
            "draft": state.get("final") or "",
        },
        "single": {
            "tokens": single_tokens,
            "total": single_total,
            "draft": single["final"],
        },
        "ratio": (team_total / single_total) if single_total else None,
        "note": (
            "Every hand-off duplicates context. On small tasks the team is usually "
            "MORE expensive; the payoff is specialised tools or bounded reviewer loops."
        ),
    }


# ─── helper ──────────────────────────────────────────────────────────────────
def _summarize_patch(patch) -> dict:
    if not isinstance(patch, dict):
        return {}
    out = {}
    for k, v in patch.items():
        if isinstance(v, list):
            out[k] = f"list({len(v)})"
        elif isinstance(v, str) and len(v) > 80:
            out[k] = v[:60] + f" …(+{len(v) - 60} chars)"
        else:
            out[k] = v
    return out


DEMOS = {
    "topology":   m1_topology,
    "researcher": m2_researcher,
    "writer":     m3_writer,
    "team":       m4_team,
    "resume":     m5_resume,
    "critic":     m6_critic,
    "tokens":     m7_tokens,
}
