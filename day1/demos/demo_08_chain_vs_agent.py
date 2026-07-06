"""
LIVE DEMO — Slide 8: "Chain vs Agent"

Goal on screen: the SAME goal solved both ways, side by side:

    Goal: recommend a SUNNY weekend city (Portland / Seattle / Bend) + a hotel.

  CHAIN  — the workflow was frozen when the code was written: it always checks
           Portland and always recommends Portland. Portland is rainy. Too bad —
           there is no step where "switch city" could happen.
  AGENT  — same goal, but the model picks each next step from what it observes:
           it discovers the rain and routes around it to Bend.

Then we print the slide's comparison table filled in with what ACTUALLY happened.

Run:
    python day1/demos/demo_08_chain_vs_agent.py
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD, BLUE, YELLOW
from config import get_llm

MAX_STEPS = 6

# ── Shared mock data (identical for both approaches — only the CONTROL differs) ──
FORECAST = {"portland": "Rainy all weekend", "seattle": "Cloudy with showers", "bend": "Sunny and clear"}
HOTELS = {
    "portland": "Rose City Hotel ($110), Bridgetown Suites ($130)",
    "bend": "Pine Lodge ($120), Riverside Inn ($95), Cascade Hotel ($140)",
}


@tool
def get_weather(city: str) -> str:
    """Get this weekend's weather forecast for a city."""
    return FORECAST.get(city.strip().lower(), f"No forecast for {city}.")


@tool
def search_hotels(city: str) -> str:
    """Find hotels in a city."""
    return HOTELS.get(city.strip().lower(), f"No hotels found in {city}.")


TOOLS = {"get_weather": get_weather, "search_hotels": search_hotels}
GOAL = ("Recommend a city that is SUNNY this weekend and one hotel there. "
        "Candidate cities: Portland, Seattle, Bend.")


# ─────────────────────────────────────────────────────────────────────────────
# APPROACH 1 — CHAIN: steps and city fixed at design time
# ─────────────────────────────────────────────────────────────────────────────
def run_chain() -> str:
    print(f"\n{YELLOW}{BOLD}━━ APPROACH 1 · CHAIN — the path was decided when the code was written ━━{RESET}")
    city = "Portland"  # ← hard-wired into the workflow. No runtime decision exists.
    note(f'The pipeline says: check weather for "{city}", find hotels in "{city}", write the rec.')

    step("CHAIN STEP 1 · get_weather (city fixed = Portland)")
    weather = get_weather.invoke({"city": city})
    result(weather)

    step("CHAIN STEP 2 · search_hotels (city fixed = Portland)")
    hotels = search_hotels.invoke({"city": city})
    result(hotels)

    step("CHAIN STEP 3 · LLM formats the recommendation card")
    llm = get_llm(temperature=None)
    rec = llm.invoke(
        [
            SystemMessage("You are step 3 of a fixed pipeline. Produce the weekend recommendation "
                          "card for the given city in 2 sentences, using the data provided. "
                          "You cannot choose a different city — that is not one of your inputs."),
            HumanMessage(f"City: {city}\nWeather: {weather}\nHotels: {hotels}"),
        ]
    ).content.strip()
    result(rec)
    note("It saw the rain — and still had to ship a Portland card. A chain has no step "
         "where 'pick a different city' could happen.")
    return "Portland (rainy), no switch"


# ─────────────────────────────────────────────────────────────────────────────
# APPROACH 2 — AGENT: same goal, the model chooses each next step
# ─────────────────────────────────────────────────────────────────────────────
def run_agent() -> str:
    print(f"\n{YELLOW}{BOLD}━━ APPROACH 2 · AGENT — same goal, path chosen at runtime ━━{RESET}")
    llm = get_llm(temperature=None).bind_tools(list(TOOLS.values()))
    messages = [
        SystemMessage("You are a travel-planning agent. Use the tools to reach the goal; check "
                      "weather before recommending. When done, give a final recommendation with no tool call."),
        HumanMessage(GOAL),
    ]

    for _ in range(MAX_STEPS):
        ai = llm.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            print(f"  {BLUE}THINK:{RESET} enough information — final answer.")
            result(ai.content.strip())
            return "Bend (sunny) — it adapted"
        for call in ai.tool_calls:
            print(f"  {BLUE}ACT:{RESET}     {call['name']}({call['args']})")
            obs = TOOLS[call["name"]].invoke(call["args"])
            print(f"  {DIM}OBSERVE:{RESET} {obs}")
            messages.append(ToolMessage(content=str(obs), tool_call_id=call["id"]))
    return "(hit step limit)"


def comparison_table(chain_outcome: str, agent_outcome: str) -> None:
    step("THE SLIDE'S TABLE — filled in with what you just watched")
    rows = [
        ("", "CHAIN", "AGENT"),
        ("Workflow", "fixed (Portland, always)", "chose its own path"),
        ("Predictable", "yes — same steps every run", "adaptive — steps depend on results"),
        ("Decisions", "none at runtime", "picked tools & cities itself"),
        ("Outcome", chain_outcome, agent_outcome),
        ("LLM calls", "1", "3–4 (flexibility costs tokens)"),
    ]
    w1, w2, w3 = 13, 30, 38
    for i, (a, b, c) in enumerate(rows):
        style = BOLD if i == 0 else ""
        print(f"  {style}{a:<{w1}}│ {b:<{w2}}│ {c:<{w3}}{RESET}")
        if i == 0:
            print(f"  {'─' * w1}┼{'─' * (w2 + 1)}┼{'─' * w3}")


def main() -> None:
    banner(
        "SLIDE 8 · Chain vs Agent",
        "Same goal, two control styles: frozen pipeline vs runtime decisions.",
        "the chain ships a rainy-city recommendation; the agent routes around the rain.",
    )
    chain_outcome = run_chain()
    agent_outcome = run_agent()
    comparison_table(chain_outcome, agent_outcome)
    takeaway("Use a chain when the task never surprises you. Use an agent when it does.")


if __name__ == "__main__":
    main()
