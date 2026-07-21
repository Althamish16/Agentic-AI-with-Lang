"""
day6/solution/resume_demo.py — kill mid-run, resume from disk, no work lost.

The team from `team.py` is compiled with a **SqliteSaver** checkpointer and a
fixed `thread_id`. We drive it step-by-step; after N steps we simulate a
process death (KeyboardInterrupt). A second invocation with the **same
thread_id** and `input=None` picks up exactly where the first stopped —
which is what makes long-running agents production-grade.

Run it
──────
    python day6/solution/resume_demo.py            # one process, both phases
    python day6/solution/resume_demo.py start      # start & 'crash'
    python day6/solution/resume_demo.py resume     # resume from the checkpoint

Design notes
────────────
• `thread_id` is the ONLY thing that ties the two invocations together.
  Change it and you're on a fresh conversation — the previous state is
  still on disk, just under a different key.
• Steps are IDEMPOTENT: rerunning `researcher` with the same findings does
  not duplicate them (we compare cursor to `sub_questions` length inside
  the worker). This matters because a resumed graph may re-run the *last*
  in-flight node before continuing.
• `MAX_STEPS` + LangGraph's `recursion_limit` cap total work so a broken
  supervisor cannot loop forever.
• A LangGraph best-practice: `SqliteSaver` uses one connection, so we set
  `check_same_thread=False` (helper does this) to be safe from background
  threads / async servers.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

try:  # optional
    import config  # noqa: F401
except Exception:  # pragma: no cover
    pass

from langgraph.checkpoint.sqlite import SqliteSaver

from day6._llm import provider_label
from day6.solution.team import MAX_STEPS, TEAM_INVOKE_CONFIG, TeamState

CHECKPOINT_DB = pathlib.Path(__file__).with_name("day6_resume.sqlite")
THREAD_ID = "day6-long-run"
TOPIC = "multi-agent supervisor patterns"

# Interrupt after this many step-increments — the researcher does one
# supervisor→researcher hop that produces the first findings; we cut power
# right after that so resume has to finish (write + finalize).
INTERRUPT_AFTER_STEPS = 4


def _checkpointer() -> SqliteSaver:
    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    return SqliteSaver(conn)


def _thread_cfg() -> dict:
    return {**TEAM_INVOKE_CONFIG, "configurable": {"thread_id": THREAD_ID}}


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — start the run, then simulate a crash mid-flight.
# ─────────────────────────────────────────────────────────────────────────────
def start() -> None:
    print("═" * 74)
    print("PHASE 1 · start the long run (will 'crash' mid-flight)")
    print(f"  provider   : {provider_label()}")
    print(f"  thread_id  : {THREAD_ID}")
    print(f"  checkpoint : {CHECKPOINT_DB.name}")
    print("═" * 74)

    # Fresh checkpoint file so the demo is reproducible.
    CHECKPOINT_DB.unlink(missing_ok=True)

    # Recompile the team from team.py with a checkpointer attached so every
    # node's output persists to `CHECKPOINT_DB` after it runs.
    app = _build_team_with_checkpointer(_checkpointer())

    cfg = _thread_cfg()
    steps_seen = 0
    try:
        # `stream()` yields one dict per node execution. That's how we can
        # count STEPS and abort right in the middle.
        for update in app.stream({"topic": TOPIC}, cfg, stream_mode="updates"):
            steps_seen += 1
            for node_name, patch in update.items():
                step_no = patch.get("step") if isinstance(patch, dict) else None
                print(f"  step {step_no or steps_seen:>2} · node={node_name}")
            if steps_seen >= INTERRUPT_AFTER_STEPS:
                raise KeyboardInterrupt("💥 simulated process death")
    except KeyboardInterrupt as e:
        print(f"\n{e}")

    # State on disk survives the crash. Show what we've got.
    snap = app.get_state(cfg)
    v = snap.values
    print("\n── STATE PERSISTED TO DISK ───────────────────────────────────")
    print(f"  step        : {v.get('step')}")
    print(f"  findings    : {len(v.get('findings') or [])}")
    print(f"  draft       : {'yes' if v.get('draft') else 'no'}")
    print(f"  next node   : {list(snap.next) or ['(none)']}")
    print(f"  trace items : {len(v.get('trace') or [])}")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — resume with the SAME thread_id and input=None.
# ─────────────────────────────────────────────────────────────────────────────
def resume() -> None:
    print("═" * 74)
    print("PHASE 2 · resume from the checkpoint")
    print(f"  thread_id  : {THREAD_ID}")
    print("═" * 74)

    if not CHECKPOINT_DB.exists():
        print("No checkpoint file — run `resume_demo.py start` first.")
        return

    app = _build_team_with_checkpointer(_checkpointer())
    cfg = _thread_cfg()
    snap = app.get_state(cfg)
    if not snap.values:
        print("Checkpoint file has no state for this thread_id.")
        return

    v = snap.values
    print(f"  Loaded step={v.get('step')} findings={len(v.get('findings') or [])} "
          f"draft={'yes' if v.get('draft') else 'no'}")
    print(f"  Next node from disk : {list(snap.next) or ['(supervisor)']}")

    # input=None means "continue from where you left off". LangGraph resumes
    # from the last persisted checkpoint; anything already produced is kept.
    resumed_steps = 0
    for update in app.stream(None, cfg, stream_mode="updates"):
        resumed_steps += 1
        for node_name, patch in update.items():
            step_no = patch.get("step") if isinstance(patch, dict) else None
            print(f"  step {step_no or resumed_steps:>2} · node={node_name}   (resumed)")
        if resumed_steps > MAX_STEPS:  # belt: never spin forever
            print("  step cap hit — stopping the resumed run.")
            break

    final = app.get_state(cfg).values
    print("\n── FINAL RESULT (produced AFTER the resume) ─────────────────")
    print(final.get("final") or "(empty)")


# ─────────────────────────────────────────────────────────────────────────────
# Local helper: recompile team.build_team() with a checkpointer.
# team.build_team() intentionally has no checkpointer so it can be reused by
# the offline demo. Here we swap one in for the durable-run story.
# ─────────────────────────────────────────────────────────────────────────────
def _build_team_with_checkpointer(checkpointer):
    """Compile the team.py graph shape but with a checkpointer attached."""
    from langgraph.graph import END, START, StateGraph

    from day6.solution.team import (
        build_researcher,
        build_writer,
        _log,
        MAX_STEPS as _MAX,
    )

    researcher = build_researcher()
    writer = build_writer()

    def supervisor(state):
        step = state.get("step") or 0
        if step >= _MAX:
            decision = "FINISH"
        elif not state.get("findings"):
            decision = "researcher"
        elif not state.get("draft"):
            decision = "writer"
        else:
            decision = "FINISH"
        return {**_log(state, f"supervisor → {decision}"), "next": decision}

    def researcher_node(state):
        result = researcher.invoke({"topic": state["topic"]})
        return {
            **_log(state, f"researcher gathered {len(result['findings'])} findings"),
            "findings": result["findings"],
        }

    def writer_node(state):
        result = writer.invoke({"topic": state["topic"], "findings": state["findings"]})
        return {
            **_log(state, f"writer produced draft ({len(result['draft'])} chars)"),
            "draft": result["draft"],
        }

    def finalize(state):
        return {**_log(state, "FINISH → aggregate"), "final": state.get("draft", "")}

    def route(state):
        return {"researcher": "researcher", "writer": "writer",
                "FINISH": "finalize"}[state["next"]]

    g = StateGraph(TeamState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher_node)
    g.add_node("writer", writer_node)
    g.add_node("finalize", finalize)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route,
                            {"researcher": "researcher", "writer": "writer", "finalize": "finalize"})
    g.add_edge("researcher", "supervisor")
    g.add_edge("writer", "supervisor")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
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
