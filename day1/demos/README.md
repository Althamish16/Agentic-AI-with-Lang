# Day 1 — Live Demos

Four runnable demos for the Day 1 slides. Each prints a **clear boxed header**
naming its slide, then walks the concept live using the course's Azure gpt-5.4
model (via `config.get_llm`). Run them from the repo root with the venv active.

| Slide | Concept | Command |
|------|---------|---------|
| **2** | An LLM just predicts the next token (and has no memory) | `python day1/demos/demo_02_next_token.py` |
| **5** | A tool is a capability the LLM *requests* but your app *runs* | `python day1/demos/demo_05_tools.py` |
| **6** | The 6-step tool-calling flow, end to end | `python day1/demos/demo_06_tool_flow.py` |
| **7** | An agent chooses its own path: Think → Act → Observe → repeat | `python day1/demos/demo_07_agent_loop.py` |

**Presenting order:** run each demo when you reach its slide. Demos 5 → 6 → 7 build
on each other (single tool call → the full flow → a tool-using loop), so running
them in sequence tells one story.

**Notes**
- All demos call `get_llm(temperature=None)` so they work on gpt-5 / reasoning
  deployments that only accept their default temperature.
- Demo 2 tries to show real token probabilities (`logprobs`). If your deployment
  doesn't return them, it falls back gracefully to showing the single next word.
- Demos 5–7 use small hard-coded "tools" (weather / a mock orders DB / hotels) so
  they're deterministic and run fully offline apart from the LLM call itself.
- Offline dry run (no Azure needed): `LLM_PROVIDER=mock` exercises the plumbing of
  demo 2, but the tool-calling demos (5–7) need a real model.
