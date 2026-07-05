"""
LIVE DEMO — Slide 5: "Tools: Extending the LLM"

Goal on screen: show the tool BOUNDARY. First the model tries to answer a
live-data question and can't. Then we give it a `get_weather` tool — it doesn't
run the tool, it REQUESTS it; OUR code runs it; the result goes back; only then
does the model answer.

    Key idea: the LLM never executes tools itself.

Run:
    python day1/demos/demo_05_tools.py
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD
from config import get_llm


# ── The tool: an external capability the model can request ───────────────────
@tool
def get_weather(city: str) -> str:
    """Get the CURRENT weather for a city. Use this for any live weather question."""
    # In real life this calls a weather API. Here it's a fixed table so the demo
    # is deterministic and offline. THIS is the code that actually runs.
    table = {"tokyo": "Rain, 18°C, humidity 90%", "cairo": "Sunny, 41°C", "oslo": "Snow, -3°C"}
    return table.get(city.strip().lower(), f"No live data available for {city}.")


QUESTION = "Do I need an umbrella in Tokyo right now?"


def without_tools() -> None:
    step("STEP 1 · ASK WITHOUT ANY TOOL", "the model has no live data")
    llm = get_llm(temperature=None)
    ans = llm.invoke([HumanMessage(QUESTION)])
    result(f"Model: {ans.content.strip()}")
    note("It can only hedge — its training data has no idea what today's weather is.")


def with_tools() -> None:
    step("STEP 2 · GIVE IT A TOOL, ASK AGAIN", "bind get_weather() and let it decide")
    llm = get_llm(temperature=None).bind_tools([get_weather])

    messages = [HumanMessage(QUESTION)]
    ai = llm.invoke(messages)
    messages.append(ai)

    if not ai.tool_calls:
        result(f"Model answered directly (no tool requested): {ai.content.strip()}")
        return

    # The model did NOT answer — it emitted a structured REQUEST for our code to run.
    call = ai.tool_calls[0]
    print(f"  {BOLD}The model did not answer. It REQUESTED a tool:{RESET}")
    result(f"    → {call['name']}(city={call['args'].get('city')!r})")
    note("Notice: this is just a structured request. Nothing has executed yet.")

    step("STEP 3 · OUR APP EXECUTES THE TOOL", "not the model — our code")
    observation = get_weather.invoke(call["args"])
    result(f"    tool result: {observation}")

    # Feed the tool result back in, keyed to the request id, and let it finish.
    messages.append(ToolMessage(content=observation, tool_call_id=call["id"]))

    step("STEP 4 · MODEL RESPONDS WITH THE RESULT IN CONTEXT")
    final = llm.invoke(messages)
    result(f"Model: {final.content.strip()}")

    takeaway("The model never touched the internet — it asked OUR code to. That boundary is the whole idea.")


def main() -> None:
    banner(
        "SLIDE 5 · Tools: Extending the LLM",
        "A tool is an external capability. The LLM requests it; your app runs it.",
        f'"{QUESTION}" — impossible for the model alone, easy with a tool.',
    )
    without_tools()
    with_tools()


if __name__ == "__main__":
    main()
