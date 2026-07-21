# Day 7 — Exercise: pair the judge with a programmatic check + escalate

**Time**: ~25 minutes.  **Prereq**: you've finished `day7/starter/capstone.py`.

## Why

An LLM-as-judge is convenient but *not* reliable — it will happily "PASS" a
draft that quietly dropped its citations, invented a source, or wandered off
topic. Production agents pair the judge with **deterministic** checks, then
route to a human when confidence is low.

You'll turn the capstone into a system that only auto-publishes when **both**
signals agree, and escalates to a human otherwise.

## Learning objectives

1. **LLM-as-judge vs programmatic checks** — where each fails, why you need both.
2. **Escalation** — how to route to `interrupt()` when confidence is low
   instead of quietly auto-publishing.
3. **Observability** — open LangSmith and read the full decision path.

## What to build

Open `day7/exercise/capstone.py` (a copy of the solution with three
`# TODO(exercise):` gaps) and implement:

### 1. `programmatic_check(draft)` — deterministic pass/fail
Return `(True, reason)` **only** when the draft satisfies **all** of:
- contains at least **2 distinct** `[n]` citations;
- is non-empty and at least 200 characters long;
- mentions the question's key noun (a crude on-topic guard).

Return `(False, reason)` otherwise, with a short human-readable reason.

### 2. `route_after_reflect` — require BOTH signals
Auto-publish is only allowed when **both**:
- the judge's `verdict == "PASS"` **and** `score >= PASS_SCORE`, **and**
- `programmatic_check(...)` returned `ok=True`.

Otherwise:
- if there's still revision budget AND the score is still improving
  (plateau guard), loop back to `write`;
- otherwise send it to the human `approval` gate (never straight to publish).

### 3. Escalation on low confidence
Even when a draft "passes" the judge, if `score < LOW_CONFIDENCE` (0.65),
route to `approval` (with `escalated=True` in the interrupt payload) so a
human decides. Never let a low-confidence draft auto-publish.

## Stretch — tiny eval dataset

1. Create `day7/exercise/eval_dataset.py` with 4–6 `(question, expected_topic)`
   examples.
2. Write `day7/exercise/eval_run.py` that runs the capstone against each
   example with two different reflection prompts (v1 vs v2), and reports the
   average score, revision count, and auto-publish rate per prompt.
3. If LangSmith is on, tag each run with `metadata={"prompt_version": "v1"}`
   so you can compare in the UI.

## How to run

```powershell
# Offline (no keys required):
$env:LLM_PROVIDER = "mock"
python day7/exercise/capstone.py --auto "Should I use similarity or MMR retrieval?"

# With a real model + LangSmith (optional):
# add LANGSMITH_TRACING=true and LANGSMITH_API_KEY=... to .env
python day7/exercise/capstone.py "Should I use similarity or MMR retrieval?"
```

## Expected behaviour

- A short, uncited draft is caught by `programmatic_check` even if the judge PASSes it.
- A judge-PASS with a low score (< 0.65) gets escalated to the human gate.
- Approving in the UI publishes; rejecting sends it back to `write` once.
- With LangSmith on, the full decision path is visible in the trace tree.

## Common pitfalls the exercise trains against

- **Judge-alone gates:** looks safe, silently ships bad outputs.
- **Plateau blindness:** loop caps aren't enough — require *measurable improvement*.
- **No human gate on irreversible actions:** always require HITL for
  publish/send/pay/delete.
- **Debugging without traces:** with LangSmith off you're guessing; turn it on
  and read the tree.
