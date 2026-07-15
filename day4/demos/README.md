# Day 4 — Live Demos (one per concept)

Each Day 4 concept lives in its **own runnable file**. Open the file, read the ~80
lines, run it, and the terminal narrates the story. Great for hands-on / fresher
onboarding — no scrolling through a mega-file to find the piece you care about.

## Run any single demo

```bash
python day4/demos/demo_01_tool_belt.py
python day4/demos/demo_02_bind_and_route.py
python day4/demos/demo_03_broken_tool.py
python day4/demos/demo_04_vague_vs_specific.py
python day4/demos/demo_05_retry_backoff.py
```

## The story, file by file

| # | File | Concept | What the room sees |
|---|------|---------|--------------------|
| **1** | [demo_01_tool_belt.py](demo_01_tool_belt.py) | `@tool` = function + docstring-as-prompt | Print each tool's name / description / arg schema (what the model sees), then invoke each tool DIRECTLY (no LLM) to prove they're plain functions |
| **2** | [demo_02_bind_and_route.py](demo_02_bind_and_route.py) | `bind_tools` + `ToolNode` + `tools_condition` | Ambiguous query → raw `tool_call` JSON printed inline → ToolNode runs it → agent loops back → final answer |
| **3** | [demo_03_broken_tool.py](demo_03_broken_tool.py) | Errors as strings, never as raises | Flip `FAIL_WEB_SEARCH=True`, watch `web_search` return `SEARCH_FAILED: ...`, agent reads the string and pivots without crashing |
| **4** | [demo_04_vague_vs_specific.py](demo_04_vague_vs_specific.py) | Tool descriptions are prompt engineering | Same calculator body, two docstrings — vague run skips/mis-picks; specific run calls it with a clean expression |
| **5** | [demo_05_retry_backoff.py](demo_05_retry_backoff.py) | Stretch: retry-with-backoff for flaky, idempotent calls | A fake service fails twice then succeeds; wrapper returns `RETRY_EXHAUSTED: ...` on permanent failure (never raises) |

Demos 2–4 all share the same three tools + the same tiny graph, defined once in
[demo_common.py](demo_common.py). Read that file **once** and you've seen the
whole tool-belt + graph plumbing; each demo file after that is just the ONE
lesson it exists to teach.

## When to read `demo_common.py`

Before demo 2. It contains:

- `search_docs`, `web_search`, `summarize` — the three `@tool`-decorated functions
  (docstrings written specifically, non-overlapping, verb-first)
- `build_agent(...)` — 15 lines wiring `llm.bind_tools()` + `ToolNode` +
  `tools_condition` into a `StateGraph`
- `FAIL_WEB_SEARCH` — the toggle demo 3 flips to break `web_search` on purpose
- Presentation helpers (`banner` / `step` / `note` / `result` / `takeaway`) —
  same shape as `day1/demos/demo_common.py`

## Notes

- `search_docs` reuses the **Day 2 retriever** (`shared/rag.get_retriever`) — the
  Day 2 pipeline is now a tool the agent can *choose* to call.
- `web_search` is a deterministic mock so demos run offline. Set
  `WEB_SEARCH_PROVIDER=tavily` + `TAVILY_API_KEY` in `.env` if you want real
  results (see [../../shared/tools.py](../../shared/tools.py) for the pattern).
- All demos call `get_llm(temperature=0)` — deterministic output makes the
  raw `tool_call` JSON reproducible in class.
- The one-file "solution" reference for the lab is
  [../solution/tool_agent.py](../solution/tool_agent.py) — same code, stitched
  together in a single ~80-line script for people who prefer that view.
