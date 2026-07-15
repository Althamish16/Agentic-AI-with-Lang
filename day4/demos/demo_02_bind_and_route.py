"""
LIVE DEMO 02 — bind_tools + tools_condition (the whole graph in one file).

Goal on screen: put the tool belt on the LLM, wire the LangGraph loop, and ask
an ambiguous-sounding question. The room watches the raw tool_call JSON scroll
by, then the agent loops back with the result and answers.

    START → agent → (tools_condition) → tools → agent → … → END
              ▲__________________________________|

Why "ambiguous"? A phrase like "What does the course say about MMR retrieval?"
COULD go to web_search (the word "search" is right there!) — but a well-written
docstring for search_docs pulls the model to the LOCAL knowledge base every time.

Run:
    python day4/demos/demo_02_bind_and_route.py
"""

from __future__ import annotations

from demo_common import banner, build_agent, note, rule, run_agent, step, takeaway

# One line worth speaking out loud in the room:
QUESTION = "What does the course say about MMR retrieval and how it differs from plain similarity?"


def main() -> None:
    banner(
        "DAY 4 · DEMO 2 — bind_tools + tools_condition",
        "The LLM chooses a tool; ToolNode runs it; the graph loops back.",
        "watch the raw tool_call JSON for an ambiguous-sounding question.",
    )

    step("STEP 1 · BUILD THE GRAPH", "3 tools bound to the LLM, tools_condition routes")
    app = build_agent()
    note(
        "tools_condition looks at the LAST AIMessage:  has .tool_calls → 'tools' node; "
        "otherwise → END. The 'tools → agent' back-edge is what turns this into a loop."
    )

    step("STEP 2 · ASK THE QUESTION", f"Q: {QUESTION!r}")
    answer = run_agent(app, QUESTION)

    rule("═")
    print("FINAL ANSWER:\n")
    print(answer)

    takeaway(
        "The model didn't run any tool — it *asked for one*. ToolNode ran it and "
        "handed the result back on the next loop. That's the entire ReAct pattern."
    )


if __name__ == "__main__":
    main()
