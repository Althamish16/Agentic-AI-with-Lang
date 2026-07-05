"""
Day 5 STARTER — short-term vs long-term memory + compaction.

Complete the three "# TODO (lab):" gaps and run:
    python day5/starter/memory_agent.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from config import get_llm
from shared.memory import (
    clear_long_term_memory,
    compact_messages,
    get_sqlite_checkpointer,
    recall,
    remember,
)
from shared.pretty import banner, ok, rule

CHECKPOINT_DB = pathlib.Path(__file__).with_name("day5_checkpoints.sqlite")


def build_chat_agent(checkpointer):
    llm = get_llm(temperature=0)

    def chat_node(state: MessagesState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("chat", chat_node)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    # TODO (lab): compile WITH the checkpointer so memory is enabled:
    #             return g.compile(checkpointer=checkpointer)
    return g.compile()


def demo_short_term():
    banner("A) SHORT-TERM memory — checkpointer + thread_id")
    checkpointer = get_sqlite_checkpointer(CHECKPOINT_DB)
    app = build_chat_agent(checkpointer)

    # TODO (lab): use the SAME thread_id for both turns so the agent remembers.
    thread = {"configurable": {"thread_id": "learner-conversation-1"}}

    turn1 = app.invoke(
        {"messages": [HumanMessage(content="My favorite research topic is vector databases. Remember that.")]},
        thread,
    )
    print("Turn 1 →", turn1["messages"][-1].content)

    turn2 = app.invoke(
        {"messages": [HumanMessage(content="What did I say my favorite topic was?")]},
        thread,
    )
    print("Turn 2 →", turn2["messages"][-1].content)


def demo_long_term():
    banner("B) LONG-TERM memory — vector store write & recall")
    clear_long_term_memory()

    # TODO (lab): remember() a couple of durable facts about the user.
    # remember("The user prefers concise, bulleted answers with citations.")

    # TODO (lab): recall() the most relevant memories for a query and print them.
    hits = []  # <- replace with recall("What formatting does the user like?", k=2)
    for h in hits:
        print("  •", h)


def demo_compaction():
    banner("C) COMPACTION — bound the context window")
    messages = [
        HumanMessage(content="Let's research retrieval-augmented generation."),
        AIMessage(content="Sure — RAG grounds answers in retrieved documents."),
        HumanMessage(content="What about chunking?"),
        AIMessage(content="Chunk size/overlap trade off signal vs context."),
        HumanMessage(content="Now summarize where we are."),
    ]
    print(f"Before: {len(messages)} messages")
    # TODO (lab): compact to a summary + the last 2 messages.
    compacted = messages  # <- replace with compact_messages(messages, keep_last=2)
    print(f"After : {len(compacted)} messages")


def main():
    demo_short_term()
    print()
    demo_long_term()
    print()
    demo_compaction()
    rule("═")
    ok("Finish the TODOs to see all three memory types working.")


if __name__ == "__main__":
    main()
