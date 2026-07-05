"""
Day 5 SOLUTION — short-term vs long-term memory + compaction.

Three self-contained demos:
  A) SHORT-TERM: a chat graph + SqliteSaver checkpointer. Two turns on the same
     thread_id — the second turn remembers the first.
  B) LONG-TERM:  write a durable memory to a vector store, then recall it later.
  C) COMPACTION: shrink a long message list into a summary + recent turns.
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


# ── A small chat graph whose memory comes entirely from the checkpointer ──────
def build_chat_agent(checkpointer):
    llm = get_llm(temperature=0)

    def chat_node(state: MessagesState) -> dict:
        # The checkpointer replays the FULL message history for this thread_id,
        # so the model naturally sees earlier turns.
        return {"messages": [llm.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("chat", chat_node)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=checkpointer)  # <- memory is enabled here


def demo_short_term():
    banner("A) SHORT-TERM memory — checkpointer + thread_id")
    checkpointer = get_sqlite_checkpointer(CHECKPOINT_DB)
    app = build_chat_agent(checkpointer)

    # A thread_id namespaces one conversation. Same id across calls = same memory.
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
    ok("The 2nd turn had no context of its own — it remembered via the checkpointer.")


def demo_long_term():
    banner("B) LONG-TERM memory — vector store write & recall")
    clear_long_term_memory()  # reproducible demo

    # Imagine these were saved during past sessions:
    remember("The user prefers concise, bulleted answers with citations.")
    remember("The user is building a Research Assistant with LangGraph for a course.")
    remember("The user's favorite vector database is Chroma.")
    ok("Saved 3 memories to the long-term vector store.")

    hits = recall("What formatting does the user like?", k=2)
    print("\nRecall('what formatting does the user like?'):")
    for h in hits:
        print("  •", h)


def demo_compaction():
    banner("C) COMPACTION — bound the context window")
    # Simulate a long conversation.
    messages = [
        HumanMessage(content="Let's research retrieval-augmented generation."),
        AIMessage(content="Sure — RAG grounds answers in retrieved documents."),
        HumanMessage(content="What about chunking?"),
        AIMessage(content="Chunk size/overlap trade off signal vs context; ~800/120 is a good start."),
        HumanMessage(content="And embeddings?"),
        AIMessage(content="Embeddings map text to vectors; use the same model to index and query."),
        HumanMessage(content="Great. Now summarize where we are."),
    ]
    print(f"Before: {len(messages)} messages")
    compacted = compact_messages(messages, keep_last=2)
    print(f"After : {len(compacted)} messages (1 summary + last 2)\n")
    print("Summary message:\n ", compacted[0].content.replace("\n", "\n  "))


def main():
    demo_short_term()
    print()
    demo_long_term()
    print()
    demo_compaction()
    rule("═")
    ok("Day 5 complete — short-term, long-term, and compaction all working.")


if __name__ == "__main__":
    main()
