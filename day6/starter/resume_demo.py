"""
day6/starter/resume_demo.py — Day 6 STARTER · kill mid-run, then resume.

FILL IN the `# TODO(student)` gaps and run:

    python day6/starter/resume_demo.py             # both phases in one process
    python day6/starter/resume_demo.py start       # run then 'crash' mid-flight
    python day6/starter/resume_demo.py resume      # continue from the checkpoint

Reference solution: day6/solution/resume_demo.py.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

try:
    import config  # noqa: F401
except Exception:
    pass

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from day6._llm import provider_label
from day6.starter.team import (  # reuse the pieces the student already built
    MAX_STEPS,
    TEAM_INVOKE_CONFIG,
    TeamState,
    _log,
    build_researcher,
    build_writer,
)

CHECKPOINT_DB = pathlib.Path(__file__).with_name("day6_resume_starter.sqlite")
THREAD_ID = "day6-starter-run"
TOPIC = "multi-agent supervisor patterns"
INTERRUPT_AFTER_STEPS = 4


def _checkpointer() -> SqliteSaver:
    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    return SqliteSaver(conn)


def _thread_cfg() -> dict:
    return {**TEAM_INVOKE_CONFIG, "configurable": {"thread_id": THREAD_ID}}


# ─── Build the team graph, this time with a checkpointer ─────────────────────
def build_team_with_checkpointer(checkpointer):
    researcher = build_researcher()
    writer = build_writer()

    def supervisor(state: TeamState) -> dict:
        step = state.get("step") or 0
        if step >= MAX_STEPS:
            decision = "FINISH"
        elif not state.get("findings"):
            decision = "researcher"
        elif not state.get("draft"):
            decision = "writer"
        else:
            decision = "FINISH"
        return {**_log(state, f"supervisor → {decision}"), "next": decision}

    def researcher_node(state: TeamState) -> dict:
        r = researcher.invoke({"topic": state["topic"]})
        return {**_log(state, f"researcher gathered {len(r['findings'])} findings"),
                "findings": r["findings"]}

    def writer_node(state: TeamState) -> dict:
        r = writer.invoke({"topic": state["topic"], "findings": state["findings"]})
        return {**_log(state, f"writer produced draft ({len(r['draft'])} chars)"),
                "draft": r["draft"]}

    def finalize(state: TeamState) -> dict:
        return {**_log(state, "FINISH → aggregate"), "final": state.get("draft", "")}

    def route(state: TeamState) -> str:
        return {"researcher": "researcher", "writer": "writer",
                "FINISH": "finalize"}[state["next"]]

    g = StateGraph(TeamState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher_node)
    g.add_node("writer", writer_node)
    g.add_node("finalize", finalize)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route,
                            {"researcher": "researcher", "writer": "writer",
                             "finalize": "finalize"})
    g.add_edge("researcher", "supervisor")
    g.add_edge("writer", "supervisor")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


# ─── PHASE 1 · start & crash ─────────────────────────────────────────────────
def start():
    print("═" * 74)
    print(f"PHASE 1 · start · provider: {provider_label()} · thread_id: {THREAD_ID}")
    print("═" * 74)
    CHECKPOINT_DB.unlink(missing_ok=True)
    app = build_team_with_checkpointer(_checkpointer())
    cfg = _thread_cfg()

    steps_seen = 0
    try:
        for update in app.stream({"topic": TOPIC}, cfg, stream_mode="updates"):
            steps_seen += 1
            for node_name, patch in update.items():
                step_no = patch.get("step") if isinstance(patch, dict) else None
                print(f"  step {step_no or steps_seen:>2} · node={node_name}")
            if steps_seen >= INTERRUPT_AFTER_STEPS:
                raise KeyboardInterrupt("💥 simulated process death")
    except KeyboardInterrupt as e:
        print(f"\n{e}")

    snap = app.get_state(cfg)
    v = snap.values
    print(f"\n  state persisted → step={v.get('step')} findings={len(v.get('findings') or [])} "
          f"draft={'yes' if v.get('draft') else 'no'} next={list(snap.next)}")


# ─── PHASE 2 · resume ────────────────────────────────────────────────────────
def resume():
    print("═" * 74)
    print(f"PHASE 2 · resume · thread_id: {THREAD_ID}")
    print("═" * 74)
    if not CHECKPOINT_DB.exists():
        print("No checkpoint yet — run `resume_demo.py start` first.")
        return
    app = build_team_with_checkpointer(_checkpointer())
    cfg = _thread_cfg()
    snap = app.get_state(cfg)
    print(f"  loaded snapshot: step={snap.values.get('step')} "
          f"next={list(snap.next) or ['(none)']}")

    # TODO(student): resume from disk by streaming with `None` as the input.
    #                Loop over `app.stream(None, cfg, stream_mode='updates')`
    #                and print each node's name + step number.
    # ---- start of TODO ----
    # for update in app.stream(None, cfg, stream_mode="updates"):
    #     for node_name, patch in update.items():
    #         print(f"  step {patch.get('step')} · node={node_name}  (resumed)")
    # ---- end of TODO ----

    final = app.get_state(cfg).values
    print("\nFinal draft (after resume):")
    print(final.get("final") or "(finish the TODO to produce output)")


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "demo").lower()
    if mode == "start":
        start()
    elif mode == "resume":
        resume()
    else:
        start()
        print()
        resume()


if __name__ == "__main__":
    main()
