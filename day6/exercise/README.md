# Day 6 · Exercise — Add a critic, count tokens

**Time:** ~25 minutes.  **Prerequisite:** you've run `day6/solution/team.py`
end-to-end and understand supervisor / researcher / writer.

## Your job

1. **Add a third worker — the `critic`.** It reads the writer's draft and
   returns either `"revise"` or `"approve"`. When the critic says `"revise"`
   the supervisor routes control **back to the writer** for one more pass.
2. **Cap the writer↔critic loop.** The pair must be able to bounce at most
   `MAX_REVISIONS` times, then finalize regardless — so a picky critic can't
   burn your budget forever.
3. **Instrument token counting.** Log input/output tokens per worker and
   print a summary at the end. Compare the totals against a single-agent
   baseline that does research + writing + critique in one context.

The starter code you edit is [`critic_team.py`](critic_team.py). It has TWO
`# TODO(student)` gaps:

* the six-way supervisor decision (`researcher` / `writer` / `critic` /
  `writer-again` / `FINISH` / `FINISH-because-out-of-steps`);
* the `add_conditional_edges` mapping the four routing keys to the four nodes.

Everything else (worker sub-graphs, token counting helpers, single-agent
baseline) is already there. Reference solution: [`solution.py`](solution.py).

## Run it

```bash
python day6/exercise/critic_team.py
python day6/exercise/critic_team.py --topic "ReAct vs plan-and-execute"
python day6/exercise/solution.py                  # the completed version
```

Expected output tail:

```
Delegation trace (team):
   1. supervisor → researcher
   2. researcher gathered 3 findings
   3. supervisor → writer
   4. writer produced draft (…) · revision 1
   5. supervisor → critic
   6. critic verdict = REVISE
   7. supervisor → writer
   8. writer produced draft (…) · revision 2
   9. supervisor → critic
  10. critic verdict = APPROVE
  11. supervisor → FINISH
  12. FINISH → aggregate

TEAM tokens per worker:
  researcher   in=…  out=…
  writer       in=…  out=…
  writer       in=…  out=…
  critic       in=…  out=…
  critic       in=…  out=…
SINGLE agent tokens:
  single       in=…  out=…
  single       in=…  out=…

Comparison
  team   total tokens = X
  single total tokens = Y
  team / single = R×
```

The mock critic is deterministic: it says **REVISE the first time** and
**APPROVE on any retry**, so the loop always resolves after exactly one
revision. If you swap in a real model (set `DAY6_PROVIDER=openai`), the
critic may approve immediately — the cap still saves you if it doesn't.

## Learning objectives

* **A bounded feedback loop is one graph edge.** `add_conditional_edges`
  from the supervisor decides when to go BACK to `writer` — that single
  decision is the whole "reviewer" pattern.
* **Every hand-off costs tokens.** The 3-agent team has to send the topic /
  findings / draft between workers; a single agent keeps everything in
  context. On small tasks the team is often *more* expensive.
* **When multi-agent pays off** (not shown here — but obvious from the
  cost curve): tasks with heterogeneous tools (SQL agent vs code agent vs
  web agent), independent parallelisable sub-tasks, or reviewer patterns
  where quality > tokens.

## STRETCH · Replace the hand-built supervisor

Replace the hand-built supervisor with the prebuilt
[`langgraph-supervisor`](https://pypi.org/project/langgraph-supervisor/):

```bash
pip install langgraph-supervisor
```

```python
from langgraph_supervisor import create_supervisor
from langchain_core.tools import tool

@tool
def do_research(topic: str) -> str:
    """Gather findings on `topic`."""
    return ...  # the researcher sub-graph as a tool

@tool
def do_writing(topic: str, findings: str) -> str:
    """Write a brief from findings."""
    ...

@tool
def do_critique(draft: str) -> str:
    """Return 'approve' or 'revise'."""
    ...

app = create_supervisor(
    tools=[do_research, do_writing, do_critique],
    model=get_llm(),
    prompt="You coordinate a research team ...",
).compile(checkpointer=...)
```

The moving pieces (workers, checkpointer, routing decision) are identical —
you're just delegating the *decision* to an LLM instead of a Python `if`.

## Common pitfalls this exercise makes visible

* **Going multi-agent too early.** The token table almost always shows the
  team is more expensive on toy tasks. Only reach for it when specialisation
  buys you something.
* **Ambiguous shared state.** `draft` is written by the writer AND read by
  the critic AND the supervisor. If two workers ever write it in the same
  step you'll get a silent overwrite — that's why the writer's outputs and
  the critic's outputs land on *different* fields (`draft` vs `critique`).
* **Loops without a cap.** If we removed `MAX_REVISIONS`, a hard-to-please
  critic would keep asking for revisions forever. Always cap runaway loops.
* **Error propagation.** If the researcher returns bad evidence the writer
  quotes it and the critic may still approve. Adding a critic is a *filter*,
  not a fix — the fix is better tools upstream.
