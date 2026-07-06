# Day 1 — Live Demos (one per slide)

A runnable demo for **every content slide** of the Day 1 deck. Each prints a
**clear boxed header naming its slide**, then walks the concept live using the
course's Azure gpt-5.4 model (via `config.get_llm`). Run from the repo root with
the venv active.

| Slide | Concept | Command | What the room sees |
|------|---------|---------|--------------------|
| **2** | What is an LLM? | `python day1/demos/demo_02_next_token.py` | Real next-token probabilities (poetry ≈ 100% "blue"; "favorite season" splits 3 ways) — then it forgets your name between calls |
| **3** | The Prompt | `python day1/demos/demo_03_prompt.py` | The SAME question asked 3× — bare, +instructions, +full context — and the answer transforms |
| **4** | Chain: fixed pipeline | `python day1/demos/demo_04_chain.py` | An LCEL `rewrite \| search \| answer` pipeline that shines in-scope and marches blindly into a dead end out-of-scope |
| **5** | Tools | `python day1/demos/demo_05_tools.py` | Model can't answer "umbrella in Tokyo?" alone → requests `get_weather`, OUR code runs it, then it answers |
| **6** | Tool-calling flow | `python day1/demos/demo_06_tool_flow.py` | One DB question traced through all 6 steps, showing the raw tool-call JSON the model emits |
| **7** | Agent | `python day1/demos/demo_07_agent_loop.py` | Think→Act→Observe loop: checks 3 cities, finds Bend sunny, THEN looks up hotels — path nobody scripted |
| **8** | Chain vs Agent | `python day1/demos/demo_08_chain_vs_agent.py` | The same goal both ways: the chain ships a rainy-Portland card; the agent routes around the rain — then the slide's table, filled in with what actually happened |
| **9** | Planning & Reflection | `python day1/demos/demo_09_plan_reflect.py` | Plan → draft → a quality gate FAILS the draft (with reasons) → revision → PASS |
| **10** | Memory (5 types) | `python day1/demos/demo_10_memory.py` | "Make it shorter" with/without history · a preference saved to disk survives a new session · "book the usual room" resolves from an episode log |
| **11** | Multi-agent & Orchestrator | `python day1/demos/demo_11_multi_agent.py` | Planner splits the job → 3 specialists (each with private data) → SQL agent times out and is retried → Reviewer merges the brief |
| **12** | Real-world analogy | `python day1/demos/demo_12_analogy.py` | (no LLM) Construction-site AND kitchen analogies side by side — a talking aid |
| **13** | Key takeaways | `python day1/demos/demo_13_capstone.py` | Capstone: "book me a dentist appointment" lights up [PROMPT] [MEMORY] [AGENT] [TOOL] [REASONING] [REFLECTION] tags as each concept fires |

**Presenting order:** just run each demo when you reach its slide — they're numbered
to match. Demos 5→6→7→8 build one story (a tool call → the full flow → a tool-using
loop → the two styles compared). Demo 13 is the closer: every concept in one task.

**Notes**
- All demos call `get_llm(temperature=None)` so they work on gpt-5 / reasoning
  deployments that only accept their default temperature. Don't add a small
  `max_tokens` — reasoning models need headroom and will 400 on tiny caps.
- Demo 2 shows real token probabilities (`logprobs`); if a deployment doesn't
  return them, it degrades gracefully.
- All "tools" and data sources (weather, orders DB, KB, calendar, competitor data)
  are small hard-coded tables — deterministic, offline, and rigged so the teaching
  moment always happens (e.g. only ONE morning slot exists in demo 13, so you can
  prove the agent used its memory).
- Demo 10 writes `.memory_store.json` next to the script (deleted on each run).
- Offline dry run: `LLM_PROVIDER=mock` exercises the plumbing of demos 2–4;
  tool-calling demos (5–8, 13) and structured-output demos (9, 11) need a real model.
