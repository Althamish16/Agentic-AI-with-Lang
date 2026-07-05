# Day 4 — Tool Usage & Orchestration

**Concept.** Tools turn a text generator into an agent that *acts*. We give the LLM
a **tool belt** with `bind_tools`, run tool calls with a prebuilt **`ToolNode`**, and
route with **`tools_condition`**: after the agent speaks, either run the requested
tool and loop back, or finish.

```
START → agent → (tools_condition) → tools → agent → … → END
```

We also add a **deliberately breakable tool** (`unreliable_metric`) to show the
difference between a **crash** and **graceful recovery** (retry + `ToolNode`'s
built-in `handle_tool_errors`).

**Exercise.** Wire the tool belt and routing in
[starter/tool_agent.py](starter/tool_agent.py). Tools live in
[shared/tools.py](../shared/tools.py): `web_search` (mock), `retrieve_documents`
(Day 2 RAG!), `summarize`, and `unreliable_metric`.

**Run it**
```bash
python day4/solution/tool_agent.py "What is MMR and how does it relate to agent memory?"
```

**What carries over.** `retrieve_documents` IS the Day 2 retriever exposed as a tool.
This tool belt is reused by Day 6's sub-agents and the final Day 7 agent.

**Stretch goal.** Set `WEB_SEARCH_PROVIDER=tavily` + `TAVILY_API_KEY` in `.env` for
real web search. Or flip `handle_tool_errors=False` in `build_agent()` and watch the
flaky tool crash the graph instead of recovering.
