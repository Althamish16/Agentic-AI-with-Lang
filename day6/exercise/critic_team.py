"""
day6/exercise/critic_team.py — STUDENT EXERCISE (starter).

Extend the Day 6 team with a third worker: the **critic**. The critic reads
the writer's draft and returns "revise" or "approve". "revise" sends control
back to the writer for one more pass; "approve" ends the run. The loop
between writer and critic is capped so it can't cycle forever.

You'll also compare tokens spent by the 3-agent team vs a *single* agent
that does research + writing + critique in one context.

Everything you need is imported from `day6.solution.team`. Fill in the
`# TODO(student)` gaps and run:

    python day6/exercise/critic_team.py
    python day6/exercise/critic_team.py --topic "ReAct vs plan-and-execute"

For the STRETCH goal, swap the hand-built supervisor for the prebuilt
`langgraph-supervisor` package (see the README).
"""

from __future__ import annotations

import argparse
import operator
import pathlib
import sys
from typing import Annotated, List, Literal, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

try:
    import config  # noqa: F401
except Exception:
    pass

from langgraph.graph import END, START, StateGraph

from day6._llm import get_llm, provider_label
from day6.solution.team import (
    MAX_STEPS as _TEAM_MAX_STEPS,
    _log,
    build_researcher,
    build_writer,
    web_search,  # re-used for the single-agent baseline
)


# ═════════════════════════════════════════════════════════════════════════════
# Team state — like day6/solution/team.py but with the CRITIC's fields added.
# ═════════════════════════════════════════════════════════════════════════════
class CriticTeamState(TypedDict, total=False):
    topic: str                                              # SHARED
    findings: List[dict]                                    # SHARED (researcher → writer)
    draft: str                                              # SHARED (writer → critic → maybe writer)
    critique: str                                           # SHARED (critic → supervisor)
    verdict: Literal["approve", "revise"]                   # SHARED · critic's decision
    revisions: int                                          # SHARED · writer↔critic cycles
    trace: Annotated[List[str], operator.add]               # SHARED · append-only
    step: int                                               # SHARED · monotonic
    next: Literal["researcher", "writer", "critic", "FINISH"]  # SHARED · routing key
    final: str                                              # SHARED · aggregated
    tokens: Annotated[List[dict], operator.add]             # SHARED · per-worker token log


# Bounded revision loop — the writer & critic bounce at most this many times.
MAX_REVISIONS = 2
MAX_STEPS = _TEAM_MAX_STEPS + 4   # a bit more slack because of the critic loop
INVOKE_CFG: dict = {"recursion_limit": 40}


# ─────────────────────────────────────────────────────────────────────────────
# Naive token counter — good enough to *compare* two runs on the same prompts.
# Not accurate to the exact tokenizer of every model, but perfectly comparable.
# ─────────────────────────────────────────────────────────────────────────────
def count_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token."""
    return max(1, len(text) // 4)


def track_llm_call(state: dict, worker: str, prompt: str, reply: str) -> dict:
    """Return a state patch that logs (worker, prompt tokens, reply tokens)."""
    return {"tokens": [{
        "worker": worker,
        "input_tokens": count_tokens(prompt),
        "output_tokens": count_tokens(reply),
    }]}


# ═════════════════════════════════════════════════════════════════════════════
# Worker #3 — CRITIC (its own sub-graph)
# ═════════════════════════════════════════════════════════════════════════════
class _CriticState(TypedDict, total=False):
    topic: str
    draft: str
    critique: str
    verdict: Literal["approve", "revise"]


def build_critic():
    def critique(state):
        llm = get_llm()
        prompt = (
            f"You are a critic. Review the following draft on '{state['topic']}' "
            f"and return VERDICT: APPROVE or VERDICT: REVISE on the first line, "
            f"then a short feedback line.\n\nDraft:\n{state['draft']}"
        )
        reply = llm.invoke(prompt).content
        first = (reply.splitlines() or [""])[0].strip().upper()
        verdict = "revise" if "REVISE" in first else "approve"
        return {
            "critique": reply,
            "verdict": verdict,
            # remember the token budget for the token summary later
            "_prompt_len": len(prompt),
            "_reply_len": len(reply),
        }

    g = StateGraph(_CriticState)
    g.add_node("critique", critique)
    g.add_edge(START, "critique")
    g.add_edge("critique", END)
    return g.compile()


# ═════════════════════════════════════════════════════════════════════════════
# The TEAM graph — supervisor + researcher + writer + critic
# ═════════════════════════════════════════════════════════════════════════════
def build_critic_team():
    researcher = build_researcher()
    writer = build_writer()
    critic = build_critic()

    def supervisor(state: CriticTeamState) -> dict:
        """Decide the next worker.

        Rules to implement:
          • no findings                        → "researcher"
          • findings, no draft                 → "writer"
          • draft, no critique                 → "critic"
          • critique verdict = "revise" AND
                revisions < MAX_REVISIONS      → "writer"        (loop back)
          • else                               → "FINISH"
          • MAX_STEPS reached                  → "FINISH"        (safety belt)
        """
        step = state.get("step") or 0
        revisions = state.get("revisions") or 0

        # TODO(student): fill in the six-way decision below.
        decision: str = "FINISH"  # <-- replace this with the rules above

        return {**_log(state, f"supervisor → {decision}"), "next": decision}

    def researcher_node(state):
        r = researcher.invoke({"topic": state["topic"]})
        # Rough token accounting for the researcher (planner + N search calls).
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
            # bump the revision counter each time the writer runs
            "revisions": (state.get("revisions") or 0) + 1,
            # clear previous verdict so the critic must re-evaluate
            "verdict": "revise",
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
    # TODO(student): add the conditional edge that maps the four routing keys
    #                to their four nodes:
    #    "researcher" → "researcher",  "writer" → "writer",
    #    "critic"     → "critic",      "FINISH" → "finalize"
    # g.add_conditional_edges("supervisor", route, {...})

    g.add_edge("researcher", "supervisor")
    g.add_edge("writer", "supervisor")
    g.add_edge("critic", "supervisor")
    g.add_edge("finalize", END)
    return g.compile()


# ═════════════════════════════════════════════════════════════════════════════
# Single-agent baseline — same task, ONE agent context.
# The team's job is fanned out across 3 sub-agents; here we do it all in ONE
# LLM context. Whichever wastes fewer tokens on this task wins the comparison.
# ═════════════════════════════════════════════════════════════════════════════
def run_single_agent(topic: str) -> dict:
    """One LLM does plan + research + write + self-critique in one context."""
    llm = get_llm()
    tokens: List[dict] = []

    # 1) plan (like the researcher's plan step)
    plan_prompt = f"Break the topic '{topic}' into 3 short sub-questions. One per line."
    plan_reply = llm.invoke(plan_prompt).content
    sub_qs = [ln.strip("-• \t") for ln in plan_reply.splitlines() if ln.strip()][:3] or [topic]
    tokens.append({"worker": "single", "input_tokens": count_tokens(plan_prompt),
                   "output_tokens": count_tokens(plan_reply)})

    # 2) research (the mock tool, same as the team)
    evidences = [{"sub_question": q, "evidence": web_search(q)} for q in sub_qs]

    # 3) write + self-critique in ONE prompt (single-context)
    bulleted = "\n".join(f"- {e['sub_question']}: {e['evidence']}" for e in evidences)
    combined_prompt = (
        f"Write a concise research brief on '{topic}' using ONLY these findings:\n\n"
        f"{bulleted}\n\nThen critique your own draft and return VERDICT: APPROVE or REVISE."
    )
    combined_reply = llm.invoke(combined_prompt).content
    tokens.append({"worker": "single", "input_tokens": count_tokens(combined_prompt),
                   "output_tokens": count_tokens(combined_reply)})

    return {"final": combined_reply, "tokens": tokens}


# ═════════════════════════════════════════════════════════════════════════════
# Runner + token summary
# ═════════════════════════════════════════════════════════════════════════════
def _print_tokens(title: str, tokens: List[dict]) -> int:
    total_in = sum(t["input_tokens"] for t in tokens)
    total_out = sum(t["output_tokens"] for t in tokens)
    print(f"\n  {title}")
    for t in tokens:
        print(f"    {t['worker']:<12} in={t['input_tokens']:>5}   out={t['output_tokens']:>5}")
    print(f"    {'TOTAL':<12} in={total_in:>5}   out={total_out:>5}   sum={total_in + total_out}")
    return total_in + total_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="multi-agent supervisor patterns")
    args = ap.parse_args()

    print("═" * 74)
    print(f"Day 6 · Exercise · provider: {provider_label()}")
    print(f"  topic: {args.topic}")
    print("═" * 74)

    # ── Team (research → write → critic → maybe revise → finalize) ──
    team = build_critic_team()
    state = team.invoke({"topic": args.topic}, INVOKE_CFG)
    print("\nDelegation trace (team):")
    for i, line in enumerate(state.get("trace") or [], 1):
        print(f"  {i:>2}. {line}")
    print("\nFinal draft (team):")
    print(state.get("final") or "(finish the TODOs to produce a draft)")

    # ── Single-agent baseline ──
    single = run_single_agent(args.topic)
    print("\nSingle-agent output:")
    print(single["final"])

    # ── Token summary ──
    team_total = _print_tokens("TEAM tokens per worker:", state.get("tokens") or [])
    single_total = _print_tokens("SINGLE agent tokens:", single["tokens"])

    print("\nComparison")
    print(f"  team   total tokens = {team_total}")
    print(f"  single total tokens = {single_total}")
    if single_total:
        ratio = team_total / single_total
        print(f"  team / single = {ratio:.2f}×   "
              f"({'team is more expensive' if ratio > 1 else 'team is cheaper'})")
    print("\nRule of thumb: multi-agent teams cost MORE tokens per task — pay that "
          "price only when specialisation, tools, or bounded reviewer loops give "
          "you back quality you couldn't get otherwise.")


if __name__ == "__main__":
    main()
