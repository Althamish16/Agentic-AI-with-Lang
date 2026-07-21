# Day 7 — Capstone · Reflection, HITL & Observability

The last day of the week. Everything you built on Days 1–6 comes together in
one **Research Assistant** and gets three "production" layers bolted on:

1. **Reflection** — the agent grades its own draft (LLM-as-judge + a numeric
   score) and can auto-revise. The loop has TWO stop conditions: a hard
   iteration cap **and** a score-plateau guard.
2. **Human-in-the-loop** — `interrupt()` pauses the graph at an **approval
   gate** before the high-stakes action (publish/send/pay). The state is
   persisted by the checkpointer, so the pause can wait indefinitely; the
   caller resumes with `Command(resume=...)`.
3. **Observability** — LangSmith traces every node, LLM call, and token when
   `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY=...` are set. The app runs
   cleanly with tracing OFF (no LangSmith account required for the demo).

```
plan → research → write → reflect ─(REVISE — capped + plateau guard)─┐
          ▲                          │                                │
          └──────────────────────────┘                                │
                                     └→ approval  ⏸  (interrupt HITL) │
                                              │                       │
                                          publish → END ◀─────────────┘
```

## Files

| Path | What it is |
|---|---|
| [`solution/capstone.py`](solution/capstone.py) | **Reference solution.** Self-contained, mock-safe. Reflection + plateau guard + HITL + programmatic check + LangSmith. |
| [`starter/capstone.py`](starter/capstone.py) | **Starter scaffold** with 4 clearly-marked `# TODO(student)` gaps. |
| [`solution/research_assistant.py`](solution/research_assistant.py) | Drives the shared graph in `shared/research_agent.py` (used by the web UI too). |
| [`starter/research_assistant.py`](starter/research_assistant.py) | Earlier starter for the same. |
| [`exercise/README.md`](exercise/README.md) | 25-min extension: pair the judge with a **deterministic** check + **escalate** on low confidence. |
| [`exercise/capstone.py`](exercise/capstone.py) | Exercise starter (three `# TODO(exercise)` gaps). |
| [`exercise/solution.py`](exercise/solution.py) | Exercise reference solution. |
| [`requirements.txt`](requirements.txt) | Pinned versions. |

## Setup

```powershell
# From the repo root, in your existing venv:
pip install -r day7/requirements.txt

# Fully offline demo (no keys, no network — uses the deterministic mock model):
$env:LLM_PROVIDER = "mock"
python day7/solution/capstone.py --auto
```

## Run modes

```powershell
python day7/solution/capstone.py                     # interactive approval
python day7/solution/capstone.py --auto              # auto-approve
python day7/solution/capstone.py --reject            # see the human-driven revision
python day7/solution/capstone.py "Your question here"
```

Expected output (mock, `--auto`): plan → 3 research hops → draft → reflect
(score printed) → route decision printed → PAUSE at the approval gate → the
driver resumes → publish → **FINAL REPORT** with the score trace.

## LangSmith (optional)

Turn tracing on by adding to `.env`:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=research-assistant-labs
```

Then re-run and open <https://smith.langchain.com>. You'll see every node,
every LLM call (with prompt + response), the reflection loop iterations, the
interrupt pause, and the resume — the entire decision path. With the env vars
absent the same code runs unchanged; tracing is simply off.

## Learning objectives

- **Reflection / verifier loops.** Bounded self-critique — how to build one,
  why the plateau guard matters as much as the iteration cap.
- **LLM-as-judge vs programmatic checks.** Where each fails and why real
  systems combine them (see the exercise).
- **HITL gating with `interrupt()`.** Persistence, resume semantics, when to
  gate (irreversible / high-stakes actions).
- **Observability.** Making the whole run legible in LangSmith — and why
  debugging without traces is guessing.

## Common pitfalls (and how the code avoids them)

- ❌ **Reflection loop that never converges.** ✅ We cap iterations AND require
  **measurable improvement** between iterations (`MIN_DELTA`).
- ❌ **Trusting the LLM-as-judge alone.** ✅ Pair it with a deterministic
  `programmatic_check` — auto-publish only if **both** agree (exercise).
- ❌ **No human gate on high-stakes actions.** ✅ Publish is always downstream
  of `interrupt()`; the model can't unilaterally "declare victory".
- ❌ **Self-improvement that drifts off-task.** ✅ Anchor to the question (the
  exercise's on-topic check) and to your eval dataset (stretch goal).
- ❌ **Debugging without traces.** ✅ Flip one env var — LangSmith shows the
  whole decision tree.

## What carries over

- Day 1's structured output (`ResearchPlan`) → `_plan`
- Day 2's RAG (`shared/rag.py`) → `_research` (with an offline stub fallback)
- Day 5's checkpointer → required to make `interrupt()` durable
- Day 6's supervisor/writer pattern → `_write`
- The complete web-UI-facing graph lives in
  [`shared/research_agent.py`](../shared/research_agent.py) and is what the
  Day 7 tab in the browser runs live.
