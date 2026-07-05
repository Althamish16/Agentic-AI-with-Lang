# Day 7 — Feedback Loops · Human-in-the-Loop · Observability *(Capstone)*

**Concept.** Three finishing touches turn the agent into a trustworthy assistant:
- **Reflection / self-critique** — the agent grades its own draft and can auto-revise
  (a feedback loop).
- **Human-in-the-loop** — `interrupt()` pauses the graph at an **approval gate** before
  publishing; a human approves or sends it back with feedback.
- **Observability** — **LangSmith** traces every node, LLM call, and token.

```
plan → research → write → reflect ─(REVISE, capped)─┐
          ▲                          │              │
          └──────────────────────────┘             │
                                     └→ human_approval ⏸ → publish → END
```

**Exercise.** Complete the reflection route, the `interrupt()` gate, and the resume
call in [starter/research_assistant.py](starter/research_assistant.py).

**Run it**
```bash
# Interactive approval gate:
python day7/solution/research_assistant.py "Should I use similarity or MMR retrieval?"
# Non-interactive:
python day7/solution/research_assistant.py --auto   "..."   # auto-approve
python day7/solution/research_assistant.py --reject "..."   # see the revision loop
```

**Enable LangSmith (optional).** In `.env` set `LANGSMITH_TRACING=true` and
`LANGSMITH_API_KEY=...`, then re-run and open https://smith.langchain.com.

**What carries over — EVERYTHING.** This capstone imports Day 1 (planner), Day 2
(RAG), Day 5 (checkpointer, required for `interrupt()`), and Day 6 (writer). The
complete graph lives in [shared/research_agent.py](../shared/research_agent.py) and is
exactly what the **web UI** (`backend/` + `frontend/`) runs.

**Stretch goal.** Add a second reviewer persona to reflection, or let the human *edit*
the draft (not just approve/reject) before publishing.
