# Day 6 — Multi-Agent (Supervisor → Sub-agents) & Long-Running Workflows

**Concept.** Big tasks split across specialists. A **supervisor** delegates to
sub-agents — each its own **sub-graph** — and aggregates their output:

```
supervisor → researcher (sub-graph: plan + RAG) → supervisor → writer (sub-graph) → supervisor → END
```

Because state is saved by a **checkpointer** (Day 5), a long run can be **killed
mid-flight and resumed** from exactly where it stopped — the basis of durable,
long-running workflows.

**Exercise.** Wire the supervisor's routing in
[starter/multi_agent.py](starter/multi_agent.py). Then run the resume demo.

**Run it**
```bash
python day6/solution/multi_agent.py "How do agents use memory and tools?"

# Long-running workflow — kill & resume (state persists in SQLite):
python day6/solution/resume.py start     # runs, then "crashes" before writing
python day6/solution/resume.py resume     # resumes from the checkpoint and finishes
python day6/solution/resume.py            # (or run both phases in one process)
```

**What carries over.** The researcher sub-agent reuses **Day 1 planner + Day 2 RAG**;
resume reuses **Day 5's SqliteSaver + thread_id**. Day 7 adds reflection + a human
gate on top of this multi-agent core.

**Stretch goal.** Make the supervisor an **LLM** that decides the next worker
(instead of the fixed rules here). Or add a third `critic` sub-agent.
