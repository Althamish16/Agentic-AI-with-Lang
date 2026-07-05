"""
Day 4 SOLUTION — a tool-calling agent (ReAct-style) in LangGraph.

    START → agent → (tools_condition) → tools → agent → … → END

The agent (an LLM with bind_tools) decides whether to answer directly or call a
tool. ToolNode runs the chosen tool and loops back. We also demonstrate graceful
recovery from a deliberately breakable tool.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from config import get_llm
from shared.pretty import banner, node, ok, rule, warn
from shared.tools import (
    RESEARCH_TOOLS,
    call_with_retry,
    reset_flaky_tool,
    unreliable_metric,
)

SYSTEM = (
    "You are a research assistant. You have tools: retrieve_documents (the local "
    "knowledge base — prefer it for course topics), web_search (mock), summarize, and "
    "unreliable_metric. Call tools when they help, then give a concise final answer "
    "with citations where available."
)


def build_agent(handle_tool_errors: bool = True):
    """Compile the tool-calling graph.

    handle_tool_errors=True (default) makes ToolNode catch a tool exception and hand
    the error back to the model as a ToolMessage — so a flaky tool degrades instead
    of crashing. Set it False to see the graph crash on the breakable tool.
    """
    llm_with_tools = get_llm(temperature=0).bind_tools(RESEARCH_TOOLS)

    def agent_node(state: MessagesState) -> dict:
        node("agent", "decide: answer or call a tool")
        ai = llm_with_tools.invoke(state["messages"])
        if ai.tool_calls:
            for tc in ai.tool_calls:
                print(f"  → tool call: {tc['name']}({tc['args']})")
        else:
            print("  → final answer ready")
        return {"messages": [ai]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(RESEARCH_TOOLS, handle_tool_errors=handle_tool_errors))
    g.add_edge(START, "agent")
    # tools_condition routes to "tools" if the last AI msg has tool_calls, else END.
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")  # after tools run, back to the agent to continue
    return g.compile()


def resilience_demo():
    """Show crash vs. graceful recovery with the deliberately breakable tool."""
    banner("Resilience demo — a deliberately breakable tool")

    warn("1) Unhandled call (this is what a crash looks like):")
    reset_flaky_tool()
    try:
        print("   ", unreliable_metric.invoke({"topic": "RAG"}))
    except Exception as e:
        print(f"    ✗ CRASH: {e}")
        print("      → left unhandled, an exception like this kills the whole run.")

    warn("\n2) Same tool wrapped in call_with_retry (graceful recovery):")
    reset_flaky_tool()
    result = call_with_retry(lambda: unreliable_metric.invoke({"topic": "RAG"}), retries=3)
    ok(f"recovered → {result}")

    print(
        "\n   In the graph, ToolNode(handle_tool_errors=True) does the same thing "
        "automatically:\n   it turns the exception into a message the agent can read "
        "and react to."
    )


def main():
    question = " ".join(sys.argv[1:]).strip() or "What is MMR and how does it relate to agent memory?"
    banner("Day 4 — Tool-calling agent")
    print(f"Question: {question}")

    app = build_agent()
    result = app.invoke({"messages": [SystemMessage(content=SYSTEM), HumanMessage(content=question)]})

    rule("═")
    print("FINAL ANSWER:\n")
    print(result["messages"][-1].content)

    print()
    resilience_demo()


if __name__ == "__main__":
    main()
