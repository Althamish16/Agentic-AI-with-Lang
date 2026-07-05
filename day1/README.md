# Day 1 — Chains vs Agents vs Tools · Prompt Templates & Output Parsers

**Concept.** A *chain* runs a fixed sequence (prompt → model → parse). An *agent*
decides its own next step at runtime. A *tool* is a function the model can call.
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
