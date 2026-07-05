# Day 5 — Memory (Short vs Long) & State Management

**Concept.** Memory turns a Q&A bot into an assistant.
- **Short-term** = the conversation, persisted by a **checkpointer** under a
  `thread_id`. Same thread → it remembers earlier turns.
- **Long-term** = durable facts stored in a **vector memory** the agent writes to
  and later recalls semantically (same machinery as Day 2 RAG).
- **Compaction** = summarize old turns so context (and cost) stays bounded.

**Exercise.** Complete the three demos in
[starter/memory_agent.py](starter/memory_agent.py): (A) two-turn conversation that
remembers via a checkpointer + `thread_id`, (B) write & recall a long-term memory,
(C) compact a long message list.

**Run it**
```bash
python day5/solution/memory_agent.py
```
A SQLite checkpoint file is written next to the script (git-ignored).

**What carries over.** The checkpointer + `thread_id` pattern is exactly what Day 6
uses to **resume a killed run**. Long-term memory + compaction plug into the Day 7
agent. Helpers live in [shared/memory.py](../shared/memory.py).

**Stretch goal.** Give the agent a `save_memory` tool (wrap `remember`) so it decides
*itself* when something is worth remembering. Or trigger compaction automatically once
the message count crosses a threshold.
