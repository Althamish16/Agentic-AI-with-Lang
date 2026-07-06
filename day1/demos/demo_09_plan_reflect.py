"""
LIVE DEMO — Slide 9: "Reasoning Cycle, Planning & Reflection"

Goal on screen: watch the full cycle do real work —

    PLAN (strategy before acting) → ACT (draft) → REFLECT (grade the draft
    against a quality bar) → REVISE → REFLECT again → PASS

Setup that guarantees reflection catches something: the DRAFTER only gets a vague
request ("briefly explain RAG for a business audience") — the way requests arrive
in real life. The precise spec lives in the REFLECTION step (a quality gate /
LLM-as-judge), so the first draft almost always violates it and gets fixed.

Run:
    python day1/demos/demo_09_plan_reflect.py
"""

from __future__ import annotations

from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from demo_common import banner, step, note, result, takeaway, GREEN, RED, RESET, BOLD
from config import get_llm

TASK = "Briefly explain RAG for a business audience."

# The quality bar — the REFLECTION step grades against this. (The drafter never sees it,
# just like real drafts are written before anyone re-reads the acceptance criteria.)
SPEC = """1. EXACTLY two sentences — no more, no fewer.
2. Must introduce the term as "RAG (retrieval-augmented generation)" — acronym followed by expansion — exactly once.
3. Must name ONE concrete business benefit (e.g. fewer wrong answers, uses your own data)."""


class Critique(BaseModel):
    """Structured verdict from the reflection step — typed, like the lab's ResearchPlan."""
    passed: bool = Field(description="True only if the draft meets EVERY requirement.")
    issues: List[str] = Field(description="Each requirement violated, quoted briefly. Empty if passed.")


def plan(llm) -> str:
    step("1 · PLAN — strategy before acting")
    p = llm.invoke(
        [
            SystemMessage("Before writing anything, produce a numbered 3-step plan (one short "
                          "line each) for how you will approach the task. Output ONLY the plan."),
            HumanMessage(TASK),
        ]
    ).content.strip()
    result(p)
    return p


def act(llm, the_plan: str) -> str:
    step("2 · ACT — write the draft")
    draft = llm.invoke(
        [
            SystemMessage(f"Follow your plan:\n{the_plan}\n\nNow write the answer."),
            HumanMessage(TASK),
        ]
    ).content.strip()
    result(f'Draft: "{draft}"')
    return draft


def reflect(llm, draft: str, round_no: int) -> Critique:
    step(f"3 · REFLECT (round {round_no}) — grade the draft against the quality bar")
    note("The spec lives HERE, in the quality gate — the drafter never saw it:")
    for line in SPEC.splitlines():
        print(f"      {line}")
    parser = PydanticOutputParser(pydantic_object=Critique)
    resp = llm.invoke(
        [
            SystemMessage("You are a strict quality gate. Grade the draft against every requirement. "
                          f"\n{parser.get_format_instructions()}"),
            HumanMessage(f"Requirements:\n{SPEC}\n\nDraft:\n{draft}"),
        ]
    )
    critique = parser.parse(resp.content)
    if critique.passed:
        print(f"  {GREEN}{BOLD}✓ VERDICT: PASS{RESET}")
    else:
        print(f"  {RED}{BOLD}✗ VERDICT: NEEDS REVISION{RESET}")
        for issue in critique.issues:
            print(f"    {RED}• {issue}{RESET}")
    return critique


def revise(llm, draft: str, critique: Critique) -> str:
    step("4 · REVISE — fix exactly what reflection flagged")
    issues = "\n".join(f"- {i}" for i in critique.issues)
    fixed = llm.invoke(
        [
            SystemMessage("Revise the draft so it meets EVERY requirement. Output only the revised text."),
            HumanMessage(f"Requirements:\n{SPEC}\n\nCurrent draft:\n{draft}\n\nIssues found:\n{issues}"),
        ]
    ).content.strip()
    result(f'Revised: "{fixed}"')
    return fixed


def main() -> None:
    banner(
        "SLIDE 9 · Reasoning Cycle, Planning & Reflection",
        "Think → Plan → Act → Observe → Repeat — with reflection grading its own work.",
        "a vague request, a quality gate, and a draft that gets caught and fixed.",
    )
    llm = get_llm(temperature=None)
    print(f"  {BOLD}Task given to the drafter (vague, like real life):{RESET} {TASK}")

    the_plan = plan(llm)
    draft = act(llm, the_plan)

    # The slide's cycle: Act → Reflect → (Revise → Reflect) … until the gate passes.
    for round_no in range(1, 4):
        critique = reflect(llm, draft, round_no=round_no)
        if critique.passed:
            if round_no == 1:
                note("First draft passed — rerun the demo; vague drafts usually get caught.")
            break
        draft = revise(llm, draft, critique)
    else:
        note("Still failing after 3 rounds — real systems cap reflection loops exactly like this.")

    takeaway("Reflection isn't magic — it's a second look with the requirements in hand. That loop is what makes agents reliable.")


if __name__ == "__main__":
    main()
