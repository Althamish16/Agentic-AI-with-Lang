# Day 3 — LangGraph Core · Planner → Executor → Memory  *(Bridge Day)*

**Concept.** A chain runs a fixed line; a **graph** can **loop and branch**. Today we
convert Day 1's planner and Day 2's RAG into a LangGraph `StateGraph`. A shared
**State** (`question, topic, plan, cursor, results, final`) flows through nodes:

```
START → planner → executor → (loop while sub-questions remain) → synthesize → END
                     ▲___________________|   (conditional edge)
```

The **conditional edge** is the whole point — it's what lets the agent loop over its
plan instead of running once.

**Exercise.** Wire the graph and the conditional router in
[starter/research_graph.py](starter/research_graph.py). State is printed between
nodes so you can literally watch the loop.

**Run it**
```bash
python day3/solution/research_graph.py "How do vector databases power RAG?"
```

**What carries over.** `planner_node` calls **Day 1** (`shared/planner.py`);
`executor_node` calls **Day 2** (`shared/rag.py`). Day 3 is the skeleton every later
day extends — Day 4 adds tools to the executor, Day 5 adds memory, Day 6 makes nodes
into sub-agents, Day 7 adds reflection + a human gate.

**Stretch goal.** Add a `max_steps` guard to the router so a runaway plan can't loop
forever. Or add a `notes` list to the state and have each node append a one-line log.
