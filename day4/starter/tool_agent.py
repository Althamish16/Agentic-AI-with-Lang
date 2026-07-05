"""
Day 4 STARTER — build a tool-calling agent in LangGraph.

    START → agent → (tools_condition) → tools → agent → … → END

Fill every "# TODO (lab):" and run:
    python day4/starter/tool_agent.py "What is MMR and how does it relate to agent memory?"
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from config import get_llm
from shared.pretty import banner, node, rule
from shared.tools import RESEARCH_TOOLS

SYSTEM = (
    "You are a research assistant. Use retrieve_documents for course topics, "
    "web_search for general facts, summarize to condense, then answer concisely."
)


def build_agent(handle_tool_errors: bool = True):
    # TODO (lab): bind the RESEARCH_TOOLS to the LLM so it can call them.
    llm_with_tools = get_llm(temperature=0)  # <- add .bind_tools(RESEARCH_TOOLS)

    def agent_node(state: MessagesState) -> dict:
        node("agent", "decide: answer or call a tool")
        ai = llm_with_tools.invoke(state["messages"])
        return {"messages": [ai]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent_node)
    # TODO (lab): add a "tools" node using ToolNode(RESEARCH_TOOLS, handle_tool_errors=handle_tool_errors)
    # g.add_node("tools", ...)

    g.add_edge(START, "agent")
    # TODO (lab): add the conditional edge from "agent" using tools_condition
    #             (routes to "tools" when the model asks for a tool, else END).
    # g.add_conditional_edges("agent", tools_condition)
    # TODO (lab): after tools run, loop back to the agent.
    # g.add_edge("tools", "agent")
    return g.compile()


def main():
    question = " ".join(sys.argv[1:]).strip() or "What is MMR and how does it relate to agent memory?"
    banner("Day 4 — Tool-calling agent")
    print(f"Question: {question}")

    app = build_agent()
    result = app.invoke({"messages": [SystemMessage(content=SYSTEM), HumanMessage(content=question)]})

    rule("═")
    print("FINAL ANSWER:\n")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
