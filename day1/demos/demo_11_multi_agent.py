"""
LIVE DEMO — Slide 11: "Multi-Agent Systems & the Orchestrator"

Goal on screen: the slide's exact flow, running for real —

    User → PLANNER agent → (RESEARCH / SQL / DOCUMENT agents) → REVIEWER → answer

and the ORCHESTRATOR doing its six jobs visibly: routing requests, invoking the
right specialist, handling a (simulated) SQL timeout with a retry, and holding
workflow state until every finding is in.

Each specialist only sees ITS OWN data source — no single agent could have
answered alone. The orchestrator here is ~30 lines of plain Python: routing is
code, intelligence is the agents.

Run:
    python day1/demos/demo_11_multi_agent.py
"""

from __future__ import annotations

from typing import List, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD, BLUE, YELLOW, RED, GREEN
from config import get_llm

USER_REQUEST = "Give me a competitive brief on Acme Corp — where do they beat us, and where do we beat them?"

# ── Each specialist's private data source (mocked; in real life: web / DB / doc store) ──
SOURCES = {
    "research": (
        "- TechWire (Jun 2026): 'Acme launches AcmeCloud AI suite, undercutting rivals by 20%'\n"
        "- MarketDaily (May 2026): 'Acme posts 34% YoY growth in the enterprise segment'\n"
        "- The Ledger (Jun 2026): 'Acme hiring spree — 200 open sales roles across EMEA'"
    ),
    "sql": (
        "deals_vs_acme_q1: wins=14, losses=9\n"
        "avg_deal_size_when_won=$48k, avg_deal_size_when_lost=$112k\n"
        "top_recorded_loss_reason='price'"
    ),
    "docs": (
        "Internal battlecard (Mar 2026): Acme wins on price and bundling. Weak on "
        "data-residency compliance and enterprise support SLAs. Our NPS 61 vs their 44."
    ),
}

AGENT_TITLES = {"research": "RESEARCH Agent", "sql": "SQL Agent", "docs": "DOCUMENT Agent"}


# ── The planner's output is TYPED (same trick as the Day 1 lab's ResearchPlan) ──
class Subtask(BaseModel):
    specialist: Literal["research", "sql", "docs"] = Field(description="Which specialist should handle this.")
    question: str = Field(description="One focused question for that specialist.")


class Plan(BaseModel):
    subtasks: List[Subtask] = Field(description="Exactly three subtasks — one per specialist.")


def planner(llm) -> Plan:
    step("PLANNER AGENT · split the request into specialist jobs")
    parser = PydanticOutputParser(pydantic_object=Plan)
    resp = llm.invoke(
        [
            SystemMessage(
                "You are the Planner agent. Split the user's request into exactly THREE focused "
                "subtasks, one for each specialist:\n"
                "- research: public web/news about the competitor\n"
                "- sql: our internal sales database (win/loss numbers)\n"
                "- docs: our internal reports and battlecards\n"
                f"{parser.get_format_instructions()}"
            ),
            HumanMessage(USER_REQUEST),
        ]
    )
    plan = parser.parse(resp.content)
    for st in plan.subtasks:
        result(f"→ {AGENT_TITLES[st.specialist]:<15}: {st.question}")
    return plan


_sql_calls = {"n": 0}


def run_specialist(llm, specialist: str, question: str) -> str:
    """One specialist agent: an LLM restricted to its own data source."""
    # Simulate real infrastructure: the SQL warehouse times out on the first attempt,
    # so the ORCHESTRATOR gets to demonstrate 'handles retries and failures'.
    if specialist == "sql":
        _sql_calls["n"] += 1
        if _sql_calls["n"] == 1:
            raise TimeoutError("sales-db connection timed out")

    resp = llm.invoke(
        [
            SystemMessage(
                f"You are the {AGENT_TITLES[specialist]}. Answer in AT MOST 2 sentences using "
                f"ONLY your data source below — cite nothing else.\n\nDATA SOURCE:\n{SOURCES[specialist]}"
            ),
            HumanMessage(question),
        ]
    )
    return resp.content.strip()


def reviewer(llm, findings: dict[str, str]) -> str:
    step("REVIEWER AGENT · check the findings, then synthesize")
    joined = "\n\n".join(f"[{AGENT_TITLES[k]}]\n{v}" for k, v in findings.items())
    resp = llm.invoke(
        [
            SystemMessage(
                "You are the Reviewer agent. You receive findings from three specialists. "
                "Write the final answer as exactly 3 bullets: (1) where Acme beats us, "
                "(2) where we beat Acme, (3) the single most important gap or caveat in these findings."
            ),
            HumanMessage(f"User asked: {USER_REQUEST}\n\nSpecialist findings:\n{joined}"),
        ]
    )
    return resp.content.strip()


def main() -> None:
    banner(
        "SLIDE 11 · Multi-Agent Systems & the Orchestrator",
        "Planner → specialists (each with private data) → Reviewer. The orchestrator is code.",
        "watch requests get routed, one agent time out and get retried, and results merge.",
    )
    llm = get_llm(temperature=None)
    print(f"  {BOLD}User:{RESET} {USER_REQUEST}")

    # ── The ORCHESTRATOR: plain Python doing the slide's six bullet points ──
    plan = planner(llm)

    findings: dict[str, str] = {}
    step("ORCHESTRATOR · route each subtask, invoke specialists, handle failures")
    for st in plan.subtasks:
        for attempt in (1, 2):
            print(f"  {YELLOW}⟳ routing →{RESET} {BOLD}{AGENT_TITLES[st.specialist]}{RESET}"
                  f"{DIM} (attempt {attempt}){RESET}")
            try:
                findings[st.specialist] = run_specialist(llm, st.specialist, st.question)
                print(f"  {GREEN}✓ {AGENT_TITLES[st.specialist]} returned:{RESET}")
                result(f"  {findings[st.specialist]}")
                break
            except TimeoutError as exc:
                print(f"  {RED}⚠ {AGENT_TITLES[st.specialist]} failed: {exc} — orchestrator retries{RESET}")
    note(f"Workflow state held by the orchestrator: {list(findings)} — all 3 in, releasing to Reviewer.")

    final = reviewer(llm, findings)
    step("FINAL ANSWER · assembled from three agents no one of which could answer alone")
    result(final)

    takeaway("Specialists + a coordinator beat one giant prompt — and the orchestrator is ordinary code: routing, retries, state.")


if __name__ == "__main__":
    main()
