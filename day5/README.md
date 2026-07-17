# Day 5 · Persistence — Memory & State (~25 min)

Extend the Day 3–4 Research Assistant agent with the **durability layer**: the
same graph, but now every step survives a process crash and every long
conversation stays affordable.

## What you build (four pillars)

| # | Pillar | What it means |
|---|--------|---------------|
| 1 | **Checkpointer + `thread_id`** | Compile the graph with a `SqliteSaver` writing to `runs.db`. Two invokes on the same `thread_id` share memory. `get_state(cfg)` prints the persisted checkpoint. |
| 2 | **State design** | An explicit `TypedDict` holding `messages` (with the `add_messages` reducer), `plan`, `cursor`, `findings`, `tool_outputs`, `long_term_recall`, `compaction_count`. Minimal but complete. |
| 3 | **Compaction node** | Fires when messages exceed a threshold. Summarises the oldest turns with the LLM, keeps the last N verbatim, then replaces the list with `[summary, *last_N]`. Prints message/token count **before vs. after** so the shrink is visible. |
| 4 | **Long-term memory** | A vector-backed store (`shared/memory.py`) the agent can `remember(fact)` and `recall(query, k=3)` from. Recall pulls facts into short-term state **only when relevant** — short-term and long-term stay decoupled. |

Plus a **crash-and-resume** demo that simulates a mid-run failure and then
re-runs on the same `thread_id` to prove it picks up where it stopped.
Replayed steps are **idempotent** (dedup keys in `tool_outputs`) so no side
effect double-fires.

## Layout

```
day5/
  starter/memory_agent.py     # scaffolding with 4 TODO blocks (start here)
  solution/memory_agent.py    # complete, runnable reference
  requirements.txt
  README.md                   # this file
```

## Run it

The whole repo shares a venv already. From the repo root:

```powershell
# Full guided tour of all four pillars + crash/resume
python day5/solution/memory_agent.py

# Just the crash phase (writes state to runs.db then exits)
python day5/solution/memory_agent.py crash

# Just the resume phase (picks up from runs.db)
python day5/solution/memory_agent.py resume
```

A `runs.db` file is written next to the script (git-ignored). Delete it to
reset all threads.

## Learner exercise

**Do this** (~25 min):

1. Open [starter/memory_agent.py](starter/memory_agent.py). Complete the four
   `# TODO (lab · pillar N)` blocks:
   - Fill in the `ResearchState` fields, including `Annotated[..., add_messages]`.
   - `return g.compile(checkpointer=checkpointer)` — not the plain `.compile()`.
   - Implement the `compact_node` body (summarise old, keep last N, `RemoveMessage`).
   - Implement `recall_node` — pull relevant facts as a `SystemMessage`.
2. Run it once (`python day5/starter/memory_agent.py`).
3. Now the persistence demo:
   ```powershell
   python day5/starter/memory_agent.py crash    # writes state, then exits
   python day5/starter/memory_agent.py resume   # SAME thread_id → picks up
   ```
   Confirm the cursor advances further AND findings grow — not restart from 0.

**Hints**

- `get_state(cfg).values` is your state dict; `.next` is the next node.
- `thread_id` must match **exactly** between runs. A typo silently starts fresh.
- Keep the last N messages verbatim so the model retains recent context.
- Print message/token counts before and after compaction — otherwise the
  shrink is invisible.

**Stretch**

- Make the agent write a **user preference** to long-term memory (e.g. "user
  likes bulleted answers"). Confirm the next session's `recall_node` surfaces
  it before planning.
- Trigger compaction automatically on every 6th message and prove the token
  estimate stays roughly flat across a long conversation.

## Production notes

- `SqliteSaver` is perfect for local dev + workshops. For production, swap it
  for a Postgres checkpointer:
  ```python
  from langgraph.checkpoint.postgres import PostgresSaver
  checkpointer = PostgresSaver.from_conn_string(os.environ["DATABASE_URL"])
  ```
- API keys come from the repo-root `.env` (same as every other day). No new
  env vars are required for Day 5.

## What carries over

The `checkpointer + thread_id` pattern is exactly how **Day 6** resumes a
killed multi-agent run, and how the **Day 7** studio pauses at a human
approval interrupt and continues later. Long-term memory + compaction plug
straight into the Day 7 agent via `shared/memory.py`.
