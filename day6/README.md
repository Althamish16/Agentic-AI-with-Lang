# Day 6 · Scaling Out — Multi-agent teams & long-running, resumable workflows

**Theme.** A **supervisor** decomposes a task, delegates to **specialist
workers** (each its own sub-graph), and aggregates their output. Because state
is persisted by a **checkpointer**, a long run can be **killed mid-flight and
resumed** with the same `thread_id` — the backbone of production agent systems.

```
supervisor → researcher (sub-graph) → supervisor → writer (sub-graph) → supervisor → FINISH
                                                    ↑             │
                                       (exercise)   └── critic ───┘  (bounded revision loop)
```

Everything on this page runs **offline** by default with a deterministic mock
model (`day6/_llm.py`). Set `DAY6_PROVIDER=openai` (or `anthropic`, or
`course`) if you want to swap in a real one — nothing else changes.

## Setup

```bash
pip install -r day6/requirements.txt
# Optional — pick a real provider (offline mock is the default):
#   $env:DAY6_PROVIDER = "openai"     # + OPENAI_API_KEY
#   $env:DAY6_PROVIDER = "anthropic"  # + ANTHROPIC_API_KEY
#   $env:DAY6_PROVIDER = "course"     # use the repo's Azure OpenAI config
```

## Run

| Script | What it shows |
|---|---|
| `python day6/solution/team.py` | Full supervisor → researcher → writer delegation trace |
| `python day6/solution/team.py "custom topic"` | Same, with your topic |
| `python day6/solution/resume_demo.py` | One process: run, "crash" after N steps, resume — no work lost |
| `python day6/solution/resume_demo.py start` | Phase 1 only — leaves the checkpoint on disk |
| `python day6/solution/resume_demo.py resume` | Phase 2 only — picks up from the checkpoint |
| `python day6/exercise/critic_team.py` | Student exercise: 3-agent team with critic + token compare |
| `python day6/exercise/solution.py` | Completed exercise for reference |

The legacy scripts (`multi_agent.py`, `resume.py`) still exist so the
course-wide `README` commands keep working; the new `team.py` /
`resume_demo.py` are the teaching versions with explicit shared/private state
annotations and offline support.

## Expected output (offline mock)

```text
══════════════════════════════════════════════════════════════════════════
Day 6 · Multi-agent team demo
  provider : offline mock (deterministic, no API needed)
  topic    : multi-agent supervisor patterns
══════════════════════════════════════════════════════════════════════════

── DELEGATION TRACE ─────────────────────────────────────────────
   1. supervisor → researcher
   2. researcher gathered 3 findings
   3. supervisor → writer
   4. writer produced draft (256 chars)
   5. supervisor → FINISH
   6. FINISH → aggregate results

── SHARED-STATE SNAPSHOT ────────────────────────────────────────
  findings : 3 items
  draft    : 256 chars
  steps    : 6
```

## Learning objectives

1. **Sub-graphs as nodes.** A worker is a compiled `StateGraph`; the parent
   invokes it inside a node function and merges the result into its own
   state. Same pattern from Day 3, one level up.
2. **Shared vs isolated state.** Every field on `TeamState` is labelled
   SHARED or PRIVATE. Workers see only the shared slice they need — that's
   context isolation, and it's what lets each worker be independently
   testable and reusable.
3. **A routing key + `add_conditional_edges` is the whole "supervisor"
   pattern.** The supervisor writes `state["next"]` and a plain `route()`
   function maps it to the next node. Swap it for an LLM later and the
   wiring is unchanged.
4. **Resumability = a checkpointer + a stable `thread_id`.** Persist state
   after every node; re-invoke with `input=None` and the run continues from
   the last snapshot. This is *the same* mechanism Day 7's `interrupt()`
   uses for human-in-the-loop.
5. **Idempotent steps + step/budget caps.** Any node that might be replayed
   after a crash must be safe to run twice — and the graph must have a step
   cap so a broken supervisor cannot loop forever (`recursion_limit` + our
   own `MAX_STEPS`).
6. **When multi-agent hurts.** The exercise's token comparison shows a
   3-agent team spends more tokens than a single well-prompted LLM on small
   tasks. Multi-agent pays off when workers have heterogeneous tools, tasks
   can be parallelised, or reviewer loops improve quality enough to justify
   the extra hops.

## Files

```
day6/
├── _llm.py                    ← ONE place: swappable model provider (mock/openai/anthropic/course)
├── requirements.txt
├── solution/
│   ├── team.py                ← ★ primary deliverable — supervisor + researcher + writer
│   ├── resume_demo.py         ← ★ kill mid-run, resume from disk with same thread_id
│   ├── multi_agent.py         ← legacy demo used by the web UI (also still valid)
│   └── resume.py              ← legacy demo used by the web UI (also still valid)
├── starter/
│   ├── team.py                ← ★ same shape, with `# TODO(student)` gaps
│   ├── resume_demo.py         ← ★ starter for the resume phase
│   ├── multi_agent.py         ← legacy starter (kept for course continuity)
│   └── resume.py              ← legacy starter (kept for course continuity)
└── exercise/
    ├── README.md              ← ★ student brief: add a critic + count tokens
    ├── critic_team.py         ← ★ starter (2 TODO gaps)
    └── solution.py            ← ★ reference implementation
```

## Common pitfalls (called out in code comments too)

* **Going multi-agent too early.** A single well-prompted LLM usually wins on
  small tasks. Reach for multi-agent when specialisation, tools, or bounded
  reviewer loops actually change the outcome — not for its own sake.
* **Token/cost explosion.** Every hand-off duplicates context. Instrument
  tokens per worker (see the exercise) so the cost is visible, not silent.
* **Error propagation.** If the researcher returns garbage, the writer
  writes about garbage. Add a critic, or trust the upstream tool less.
* **Ambiguous shared-state ownership.** Two workers writing the *same* field
  will silently clobber each other unless you use a reducer. Keep worker
  outputs on distinct fields (writer→`draft`, critic→`critique`, …).
* **No step/budget cap on long runs.** LangGraph's `recursion_limit` is your
  hard stop; our own `MAX_STEPS` is a belt on top of that. Set both.
