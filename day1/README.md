# Day 1 — Chains vs Agents vs Tools · Prompt Templates & Output Parsers

**Concept.** A *chain* runs a fixed sequence (prompt → model → parse). An *agent*
decides its own next step at runtime. A *tool* is a function the model can call.

## Live demos — one per slide

The Day 1 deck (Slides 2–13) has a **runnable live demo per slide** in
[demos/](demos/) — each opens with a boxed header naming its slide, then shows the
concept working against the real model. Run the matching demo when you reach each
slide; see [demos/README.md](demos/README.md) for the full slide → demo map.

| Slides | Demos |
|--------|-------|
| 2 · What is an LLM? | [demo_02_next_token.py](demos/demo_02_next_token.py) — real next-token probabilities + the no-memory proof |
| 3 · The Prompt | [demo_03_prompt.py](demos/demo_03_prompt.py) — same question, 3 prompt layers, 3 very different answers |
| 4 · Chain | [demo_04_chain.py](demos/demo_04_chain.py) — a fixed LCEL pipeline: great in-scope, blind out-of-scope |
| 5–6 · Tools & the flow | [demo_05_tools.py](demos/demo_05_tools.py) · [demo_06_tool_flow.py](demos/demo_06_tool_flow.py) — the model requests, YOUR code executes |
| 7–8 · Agents vs chains | [demo_07_agent_loop.py](demos/demo_07_agent_loop.py) · [demo_08_chain_vs_agent.py](demos/demo_08_chain_vs_agent.py) — the Think→Act→Observe loop, then both styles head-to-head |
| 9 · Planning & Reflection | [demo_09_plan_reflect.py](demos/demo_09_plan_reflect.py) — a quality gate catches a bad draft and fixes it |
| 10 · Memory | [demo_10_memory.py](demos/demo_10_memory.py) — all 5 memory types, incl. one that survives a new session |
| 11 · Multi-agent | [demo_11_multi_agent.py](demos/demo_11_multi_agent.py) — planner → 3 specialists (one retried) → reviewer |
| 12–13 · Analogy & wrap-up | [demo_12_analogy.py](demos/demo_12_analogy.py) · [demo_13_capstone.py](demos/demo_13_capstone.py) — two analogies, then every concept firing in ONE task |

## The lab
Today we build the simplest useful chain with **LCEL** (LangChain Expression
Language): `PromptTemplate | LLM | OutputParser`. The output parser forces the model
to return **structured JSON** validated by a Pydantic model — this is the
**"planner seed"** every later day builds on.

**Exercise.** Turn a research question into a typed `ResearchPlan`
(`topic` + exactly 3 `sub_questions`). Fill the `# TODO (lab):` gaps in
[starter/plan.py](starter/plan.py).

**Run it**
```bash
# from the repo root, with the venv active
python day1/starter/plan.py "How does RAG improve LLM accuracy?"
python day1/solution/plan.py "How does RAG improve LLM accuracy?"
```
No question argument? A sensible default is used.

**What carries over.** Nothing yet — this is the seed. The exact chain is promoted
into [shared/planner.py](../shared/planner.py) and reused by Day 3's graph and the
web UI.

**Stretch goal.** Swap `PydanticOutputParser` for `llm.with_structured_output(ResearchPlan)`
(native tool-calling) and compare reliability. Or make the number of sub-questions a
parameter.
