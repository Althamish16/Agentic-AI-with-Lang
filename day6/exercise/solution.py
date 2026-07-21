"""
day6/exercise/solution.py — reference solution for the critic exercise.

This is the completed version of `critic_team.py` (the six-way supervisor rule
and the conditional edge). It's here so students can compare after they've
had a go; run it the same way:

    python day6/exercise/solution.py --topic "multi-agent supervisor patterns"
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

try:
    import config  # noqa: F401
except Exception:
    pass

from langgraph.graph import END, START, StateGraph

# Reuse everything from the starter — we only need to overwrite the supervisor
# and the wiring line the student had to fill in.
from day6._llm import provider_label
from day6.exercise.critic_team import (
    CriticTeamState,
    INVOKE_CFG,
    MAX_REVISIONS,
    MAX_STEPS,
    _log,
    _print_tokens,
    build_critic,
    build_researcher,
    build_writer,
    count_tokens,
    run_single_agent,
)


def build_critic_team():
    researcher = build_researcher()
    writer = build_writer()
    critic = build_critic()

    def supervisor(state: CriticTeamState) -> dict:
        step = state.get("step") or 0
        revisions = state.get("revisions") or 0

        if step >= MAX_STEPS:
            decision = "FINISH"
        elif not state.get("findings"):
            decision = "researcher"
        elif not state.get("draft"):
            decision = "writer"
        elif not state.get("critique"):
            decision = "critic"
        elif state.get("verdict") == "revise" and revisions < MAX_REVISIONS:
            # bounded writer↔critic loop
            decision = "writer"
        else:
            decision = "FINISH"

        return {**_log(state, f"supervisor → {decision}"), "next": decision}

    def researcher_node(state):
        r = researcher.invoke({"topic": state["topic"]})
        return {
            **_log(state, f"researcher gathered {len(r['findings'])} findings"),
            "findings": r["findings"],
            "tokens": [{
                "worker": "researcher",
                "input_tokens": count_tokens(state["topic"]) * (1 + len(r["findings"])),
                "output_tokens": sum(count_tokens(f["evidence"]) for f in r["findings"]),
            }],
        }

    def writer_node(state):
        r = writer.invoke({"topic": state["topic"], "findings": state["findings"]})
        return {
            **_log(state, f"writer produced draft ({len(r['draft'])} chars) · revision {(state.get('revisions') or 0) + 1}"),
            "draft": r["draft"],
            "revisions": (state.get("revisions") or 0) + 1,
            "verdict": "revise",   # clear so the critic must judge again
            "tokens": [{
                "worker": "writer",
                "input_tokens": count_tokens(state["topic"]) + sum(count_tokens(f["evidence"]) for f in state["findings"]),
                "output_tokens": count_tokens(r["draft"]),
            }],
        }

    def critic_node(state):
        r = critic.invoke({"topic": state["topic"], "draft": state["draft"]})
        return {
            **_log(state, f"critic verdict = {r['verdict'].upper()}"),
            "critique": r["critique"],
            "verdict": r["verdict"],
            "tokens": [{
                "worker": "critic",
                "input_tokens": count_tokens(state["draft"]),
                "output_tokens": count_tokens(r["critique"]),
            }],
        }

    def finalize(state):
        return {**_log(state, "FINISH → aggregate"), "final": state.get("draft", "")}

    def route(state):
        return {
            "researcher": "researcher",
            "writer": "writer",
            "critic": "critic",
            "FINISH": "finalize",
        }[state["next"]]

    g = StateGraph(CriticTeamState)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher_node)
    g.add_node("writer", writer_node)
    g.add_node("critic", critic_node)
    g.add_node("finalize", finalize)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route, {
        "researcher": "researcher", "writer": "writer",
        "critic": "critic", "finalize": "finalize",
    })
    g.add_edge("researcher", "supervisor")
    g.add_edge("writer", "supervisor")
    g.add_edge("critic", "supervisor")
    g.add_edge("finalize", END)
    return g.compile()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="multi-agent supervisor patterns")
    args = ap.parse_args()

    print("═" * 74)
    print(f"Day 6 · Exercise solution · provider: {provider_label()}")
    print(f"  topic: {args.topic}")
    print("═" * 74)

    team = build_critic_team()
    state = team.invoke({"topic": args.topic}, INVOKE_CFG)
    print("\nDelegation trace (team):")
    for i, line in enumerate(state.get("trace") or [], 1):
        print(f"  {i:>2}. {line}")
    print("\nFinal draft (team):")
    print(state.get("final") or "(empty)")

    single = run_single_agent(args.topic)
    print("\nSingle-agent output:")
    print(single["final"])

    team_total = _print_tokens("TEAM tokens per worker:", state.get("tokens") or [])
    single_total = _print_tokens("SINGLE agent tokens:", single["tokens"])

    print("\nComparison")
    print(f"  team   total tokens = {team_total}")
    print(f"  single total tokens = {single_total}")
    if single_total:
        ratio = team_total / single_total
        print(f"  team / single = {ratio:.2f}×")


if __name__ == "__main__":
    main()
