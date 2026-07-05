"""
memory.py — the Day 5 memory toolkit, promoted to shared/ for Day 6/7 and the UI.

Three ideas:
  • SHORT-TERM memory  → a durable checkpointer keyed by thread_id (SqliteSaver).
  • LONG-TERM memory   → a separate Chroma collection the agent writes to / recalls.
  • COMPACTION         → replace old messages with a summary to bound context size.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

from langchain_chroma import Chroma
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from config import get_embeddings, get_llm, get_vectorstore_dir


# ─────────────────────────────────────────────────────────────────────────────
# SHORT-TERM: a SQLite-backed checkpointer.
# Because it persists to a file, the same thread_id survives across process runs —
# that's what makes Day 6's "kill mid-run and resume" possible.
# ─────────────────────────────────────────────────────────────────────────────
def get_sqlite_checkpointer(path: str | Path) -> SqliteSaver:
    """Return a durable checkpointer writing to `path`. check_same_thread=False so
    it works from web servers and background threads too."""
    conn = sqlite3.connect(str(path), check_same_thread=False)
    return SqliteSaver(conn)


# ─────────────────────────────────────────────────────────────────────────────
# LONG-TERM: a dedicated Chroma collection for the agent's own memories.
# Same retrieval machinery as RAG (Day 2), pointed at notes instead of documents.
# ─────────────────────────────────────────────────────────────────────────────
LTM_COLLECTION = "long_term_memory"


def _ltm_store() -> Chroma:
    return Chroma(
        collection_name=LTM_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(get_vectorstore_dir()),
    )


def remember(text: str, metadata: dict | None = None) -> None:
    """Write a durable memory (a short note) the agent can recall later."""
    _ltm_store().add_texts([text], metadatas=[metadata or {}])


def recall(query: str, k: int = 3) -> List[str]:
    """Semantically recall the most relevant stored memories for a query."""
    return [d.page_content for d in _ltm_store().similarity_search(query, k=k)]


def clear_long_term_memory() -> None:
    """Wipe the long-term memory collection (handy for reproducible demos)."""
    import chromadb

    client = chromadb.PersistentClient(path=str(get_vectorstore_dir()))
    try:
        client.delete_collection(LTM_COLLECTION)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# COMPACTION: summarize old turns so the context window (and cost) stays bounded.
# ─────────────────────────────────────────────────────────────────────────────
def compact_messages(messages: List[BaseMessage], keep_last: int = 2, llm=None) -> List[BaseMessage]:
    """Replace all but the last `keep_last` messages with a single summary message.
    Returns a NEW, shorter message list that preserves the important context."""
    if len(messages) <= keep_last + 1:
        return messages  # nothing worth compacting yet

    llm = llm or get_llm(temperature=0)
    old, recent = messages[:-keep_last], messages[-keep_last:]
    transcript = "\n".join(f"{m.type}: {m.content}" for m in old)
    summary = llm.invoke(
        "Summarize the following conversation so far, preserving key facts, user "
        f"preferences, and decisions. Be concise:\n\n{transcript}"
    ).content
    return [SystemMessage(content=f"[Summary of earlier conversation]\n{summary}")] + list(recent)
