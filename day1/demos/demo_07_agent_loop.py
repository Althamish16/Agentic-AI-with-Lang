"""
LIVE DEMO — Slide 7: "Agent: Dynamic Decision-Making"

Goal on screen: show the agent picking its OWN path. We give it a goal and two
tools, then run the reasoning loop by hand so every iteration is visible:

    Think → Act (call a tool) → Observe (read the result) → Think again → …

The weather table is rigged so the FIRST candidate city is rainy: the agent has
to notice that and try another before it can succeed. Nobody scripted that path —
it emerges from what each tool result says. That is the difference from a chain.

This is a deliberately hand-written loop (no framework) so the mechanism is
obvious. Day 3 replaces it with a real LangGraph agent.

Run:
    python day1/demos/demo_07_agent_loop.py
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD, BLUE
from config import get_llm

MAX_STEPS = 6


# ── Two tools the agent may choose between ───────────────────────────────────
@tool
def get_weather(city: str) -> str:
    """Get this weekend's weather forecast for a city."""
    forecast = {"portland": "Rainy all weekend", "seattle": "Cloudy with showers", "bend": "Sunny and clear"}
    return forecast.get(city.strip().lower(), f"No forecast for {city}.")


@tool
def search_hotels(city: str) -> str:
    """Find hotels in a city."""
    hotels = {
        "bend": "Pine Lodge ($120), Riverside Inn ($95), Cascade Hotel ($140)",
        "portland": "Rose City Hotel ($110), Bridgetown Suites ($130)",
    }
    return hotels.get(city.strip().lower(), f"No hotels found in {city}.")


TOOLS = {"get_weather": get_weather, "search_hotels": search_hotels}

GOAL = (
    "Find a city that is SUNNY this weekend and recommend a hotel there. "
    "Candidate cities to consider: Portland, Seattle, Bend."
)


def main() -> None:
    banner(
        "SLIDE 7 · Agent: Dynamic Decision-Making",
        "An agent reasons, chooses tools, observes results, and adapts its path.",
        "give it a goal + 2 tools; watch it decide its own next step each loop.",
    )

    llm = get_llm(temperature=None).bind_tools(list(TOOLS.values()))
    messages = [
        SystemMessage(
            "You are a travel-planning agent. Use the tools to reach the goal. "
            "Check weather before recommending a place. Think one step at a time; "
            "when you are done, reply with a final recommendation and no tool call."
        ),
        HumanMessage(GOAL),
    ]

    print(f"  {BOLD}Goal:{RESET} {GOAL}\n")

    for i in range(1, MAX_STEPS + 1):
        step(f"LOOP ITERATION {i}", "the agent decides what to do next")
        ai = llm.invoke(messages)
        messages.append(ai)

        # No tool call ⇒ the agent has decided it's finished.
        if not ai.tool_calls:
            print(f"  {BLUE}THINK:{RESET} agent has enough information — producing final answer.")
            result(f"FINAL ANSWER: {ai.content.strip()}")
            takeaway("No one told it to check Portland first or to stop at Bend — it chose each step from the results.")
            return

        # Otherwise: run every tool it asked for and feed the observations back.
        for call in ai.tool_calls:
            print(f"  {BLUE}ACT:{RESET}     {call['name']}({', '.join(f'{k}={v!r}' for k, v in call['args'].items())})")
            observation = TOOLS[call["name"]].invoke(call["args"])
            print(f"  {DIM}OBSERVE:{RESET} {observation}")
            messages.append(ToolMessage(content=str(observation), tool_call_id=call["id"]))

    note("Hit the step limit — real agents cap iterations exactly like this to stay safe.")


if __name__ == "__main__":
    main()
