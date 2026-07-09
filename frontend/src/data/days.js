// Rich teaching content for the Day 1–7 tabs.
// Each day: detailed explanation sections, several code snippets, and several
// independently-runnable demos (ids match backend/labs.py REGISTRY).

export const DAYS = [
  {
    n: 1,
    key: 'day1',
    title: 'AI Fundamentals — Chains, Tools & Agents',
    tag: 'From next-token prediction to multi-agent orchestration',
    accent: 'indigo',
    why: 'Every idea in Days 2–7 is one of the seven concepts on today\'s slides.',
    flow: ['LLM', 'Prompt', 'Tool', 'Chain', 'Agent', 'Memory', 'Orchestrator'],
    carriesOver: 'The mental model built today powers every later day. Slide 4 (chain) → Days 1–2 labs; Slides 5–8 (tools + agent) → Days 3–4; Slide 10 (memory) → Day 5; Slide 11 (multi-agent) → Days 6–7.',
    explain: [
      { h: 'What today covers', body: 'The **12 slides** from the deck, each with a **live demo you can run**. Slide 2 shows an LLM literally ranking next-token probabilities. Slide 5 shows a tool call step by step. Slide 7 watches an agent choose its own path. Slide 13 exercises **every** concept in one everyday task ("book me a dentist appointment").' },
      { h: 'Chain vs Tool vs Agent', body: 'A **chain** is a fixed pipeline you compose with the `|` operator: prompt → model → parse. A **tool** is a function the model can *request* — your app runs it and feeds the result back. An **agent** is an LLM that reasons, chooses tools, observes results, and decides its own next step (a runtime loop, not a frozen pipeline).' },
      { h: 'Why prompts, output parsers, and structured output', body: 'Free-form LLM prose is impossible to feed reliably into the next step. An **output parser** forces the model to return JSON validated against a **Pydantic** schema — the Day 1 coding lab uses this to produce a typed `ResearchPlan` (topic + 3 sub-questions) that Day 3\'s graph then consumes.' },
      { h: 'How LCEL wires it', body: 'LangChain Expression Language (LCEL) lets you pipe runnables: `prompt | llm | parser`. The parser does double duty — it validates the response **and** generates the "format instructions" we inject into the prompt so the model knows the exact JSON shape to produce.' },
      { h: 'Watch out', body: 'This deployment (gpt-5.4) is a **reasoning model**: it spends hidden tokens thinking before emitting output. Never pass a tiny `max_tokens` or the call will 400 before any visible token appears. All demos call `get_llm(temperature=None)` — the deployment only accepts its default temperature.' },
    ],
    snippets: [
      { title: 'A tool the model can request', code: `@tool
def get_weather(city: str) -> str:
    """Get the CURRENT weather for a city."""
    ...  # real code that your app runs, not the model` },
      { title: 'Compose a chain (LCEL)', code: `parser = PydanticOutputParser(pydantic_object=ResearchPlan)
prompt = ChatPromptTemplate.from_messages([...]).partial(
    format_instructions=parser.get_format_instructions())
chain = prompt | llm | parser        # <- this IS the chain` },
      { title: 'Agent loop by hand (Think → Act → Observe)', code: `llm = get_llm(0).bind_tools(TOOLS)
for _ in range(6):
    ai = llm.invoke(messages)
    if not ai.tool_calls: break        # agent decides it's done
    for call in ai.tool_calls:
        obs = TOOLS[call["name"]].invoke(call["args"])
        messages.append(ToolMessage(obs, tool_call_id=call["id"]))` },
    ],
    sections: [
      { id: 'slides', label: 'Slide demos', desc: 'One live demo per deck slide (2–13). Run in order for the full story.' },
      { id: 'lab', label: 'Coding lab · Output parsers', desc: 'The ResearchPlan pipeline the rest of the course reuses.' },
    ],
    demos: [
      // ─── Slide demos — one per slide from the deck ─────────────────────
      { id: 'slide2',  section: 'slides', slide: 2,  tab: 'LLM',           label: 'Slide 2 · What is an LLM?',           desc: 'Real next-token probabilities (poetry ≈ 100% "blue"; "favorite season" splits 3 ways) — then it forgets your name between calls.', needsQuestion: false },
      { id: 'slide3',  section: 'slides', slide: 3,  tab: 'Prompt',        label: 'Slide 3 · The Prompt',                desc: 'Same question asked 3×: bare → +instructions → +full context. Same model, different worlds.', needsQuestion: false },
      { id: 'slide4',  section: 'slides', slide: 4,  tab: 'Chain',         label: 'Slide 4 · Chain: fixed pipeline',     desc: 'An LCEL `rewrite | search | answer` chain shines in-scope and marches into a dead end out-of-scope.', needsQuestion: false },
      { id: 'slide5',  section: 'slides', slide: 5,  tab: 'Tools',         label: 'Slide 5 · Tools',                     desc: 'Model can\'t answer "umbrella in Tokyo?" alone → requests `get_weather`, OUR code runs it, then it answers.', needsQuestion: false },
      { id: 'slide6',  section: 'slides', slide: 6,  tab: 'Tool flow',     label: 'Slide 6 · Tool-calling flow',         desc: 'One DB question traced through all 6 steps, showing the raw tool-call JSON the model emits.', needsQuestion: false },
      { id: 'slide7',  section: 'slides', slide: 7,  tab: 'Agent',         label: 'Slide 7 · Agent loop',                desc: 'Think→Act→Observe: checks 3 cities, finds Bend sunny, THEN looks up hotels — nobody scripted that.', needsQuestion: false },
      { id: 'slide8',  section: 'slides', slide: 8,  tab: 'Chain vs Agent',label: 'Slide 8 · Chain vs Agent',            desc: 'Same goal both ways: chain ships rainy Portland; agent routes around the rain. Then the slide\'s table, filled in with what happened.', needsQuestion: false },
      { id: 'slide9',  section: 'slides', slide: 9,  tab: 'Reflect',       label: 'Slide 9 · Planning & Reflection',     desc: 'Plan → draft → quality gate FAILS with reasons → revision → PASS.', needsQuestion: false },
      { id: 'slide10', section: 'slides', slide: 10, tab: 'Memory',        label: 'Slide 10 · Memory (5 types)',         desc: '"Make it shorter" with/without history · preference saved to disk survives a new session · "book the usual room" resolves from an episode log.', needsQuestion: false },
      { id: 'slide11', section: 'slides', slide: 11, tab: 'Multi-agent',   label: 'Slide 11 · Multi-agent & Orchestrator', desc: 'Planner splits the job → 3 specialists (each with private data) → SQL agent times out and is retried → Reviewer merges the brief.', needsQuestion: false },
      { id: 'slide12', section: 'slides', slide: 12, tab: 'Analogy',       label: 'Slide 12 · Real-world analogy',       desc: 'Construction-site AND kitchen analogies side by side — a talking aid, no LLM call.', needsQuestion: false },
      { id: 'slide13', section: 'slides', slide: 13, tab: 'Capstone',      label: 'Slide 13 · Capstone',                 desc: '"Book me a dentist appointment" lights up [PROMPT] [MEMORY] [AGENT] [TOOL] [REASONING] [REFLECTION] tags as each concept fires.', needsQuestion: false },

      // ─── Coding lab — the original Day 1 ResearchPlan demos ────────────
      { id: 'plan',           section: 'lab', label: 'Plan a question',                 desc: 'Question → validated ResearchPlan JSON.', needsQuestion: true },
      { id: 'raw_vs_parsed',  section: 'lab', label: 'Raw LLM vs parsed chain',         desc: 'Same ask, unstructured text vs typed JSON — see why parsers matter.', needsQuestion: true },
      { id: 'prompt_preview', section: 'lab', label: 'Preview the real prompt',         desc: 'The exact prompt (with format instructions) sent to the model. No LLM call.', needsQuestion: true },
    ],
  },
  {
    n: 2,
    key: 'day2',
    title: 'RAG: Retrieval-Augmented Generation',
    tag: 'Loaders · chunking · embeddings · retrieval',
    accent: 'sky',
    why: 'Answers can cite real sources, which slashes hallucination.',
    flow: ['Load', 'Chunk', 'Embed', 'Store (Chroma)', 'Retrieve (sim / MMR)', 'Answer + cite'],
    carriesOver: 'Day 1’s planner is untouched. The retriever → shared/rag.py; Day 3’s executor calls it.',
    explain: [
      { h: 'What RAG does', body: 'RAG grounds answers in **your documents** instead of only the model’s memory. Pipeline: **load → chunk → embed → store (Chroma) → retrieve top-k → answer with citations.** Because knowledge lives outside the model, you update it by re-indexing — no retraining.' },
      { h: 'Chunking is a real knob', body: 'Documents are split into chunks before embedding. Too **big** dilutes the relevant signal and wastes context; too **small** loses surrounding meaning. Overlap keeps ideas that straddle a boundary. Run the chunking demo to see how size changes the number of chunks.' },
      { h: 'Embeddings & the vector store', body: 'Each chunk becomes a vector (here, a local `fastembed` model — no cloud). **Chroma** stores them and finds nearest neighbours by cosine similarity. Critical rule: use the **same** embedding model to index and query, or the vectors live in different spaces and retrieval collapses.' },
      { h: 'Similarity vs MMR', body: 'Plain **similarity** returns the closest chunks — which can be near-duplicates. **MMR** (Maximal Marginal Relevance) re-ranks to balance relevance with **diversity**, giving a more useful spread of citations.' },
    ],
    snippets: [
      { title: 'Load → chunk', code: `docs = load_documents("data/")
chunks = split_documents(docs, chunk_size=800, chunk_overlap=120)` },
      { title: 'Embed → store (Chroma)', code: `vs = Chroma.from_documents(chunks, get_embeddings(),
    collection_name="research_assistant",
    persist_directory=".chroma")` },
      { title: 'Retrieve: similarity vs MMR', code: `sim = vs.as_retriever(search_type="similarity",
    search_kwargs={"k": 4}).invoke(q)
mmr = vs.as_retriever(search_type="mmr",
    search_kwargs={"k": 4, "fetch_k": 20}).invoke(q)` },
    ],
    sections: [
      { id: 'pipeline', label: 'Pipeline demos', desc: 'One live demo per RAG stage — run left to right for the whole story.' },
    ],
    demos: [
      // ─── One tab per RAG pipeline stage (load → chunk → embed → retrieve → answer) ───
      { id: 'load',     section: 'pipeline', slide: 1, tab: 'Load',       label: 'Step 1 · Load — files → Documents',        desc: 'Load the sample docs as LangChain Document objects (text + metadata). That metadata is what makes citations possible later. No LLM call.', needsQuestion: false },
      { id: 'chunking', section: 'pipeline', slide: 2, tab: 'Chunk',      label: 'Step 2 · Chunk — split into pieces',       desc: 'See how chunk size/overlap change the number of chunks, with a sample chunk. The classic RAG quality knob. No LLM call.', needsQuestion: false },
      { id: 'embed',    section: 'pipeline', slide: 3, tab: 'Embed',      label: 'Step 3 · Embed — text → vectors',          desc: 'Turn chunks into vectors and measure how close your question lands to the nearest chunk. Close = similar meaning. No LLM call.', needsQuestion: true },
      { id: 'topk',     section: 'pipeline', slide: 4, tab: 'Retrieve',   label: 'Step 4 · Retrieve — top-k with scores',    desc: 'The actual chunks nearest the query vector, with similarity scores. No LLM call.', needsQuestion: true },
      { id: 'compare',  section: 'pipeline', slide: 5, tab: 'Sim vs MMR', label: 'Step 5 · Similarity vs MMR',               desc: 'Same k, two strategies: closest chunks vs relevant-AND-diverse chunks. No LLM call.', needsQuestion: true },
      { id: 'answer',   section: 'pipeline', slide: 6, tab: 'Answer',     label: 'Step 6 · Answer with citations',           desc: 'Retrieve, then answer using ONLY those chunks — with inline [n] citations back to the sources.', needsQuestion: true },
      { id: 'break',    section: 'pipeline', slide: 7, tab: 'Break it',   label: 'Step 7 · Break it — embedding mismatch',    desc: 'Query with a DIFFERENT embedding model than the index: retrieval silently returns the wrong chunks, no error raised. No LLM call.', needsQuestion: true },
    ],
  },
  {
    n: 3,
    key: 'day3',
    title: 'LangGraph Core',
    tag: 'Planner → Executor → Synthesize (with a loop)',
    accent: 'violet',
    why: 'Conditional edges = loops & decisions. That’s the leap from chain to agent.',
    flow: ['plan', 'executor ↺ (loop over sub-questions)', 'synthesize'],
    carriesOver: 'planner_node calls Day 1; executor_node calls Day 2. This skeleton is extended every later day.',
    explain: [
      { h: 'From line to graph', body: 'A chain runs one straight line. A **graph** models the app as nodes (units of work) and edges (how control moves). A shared **State** object flows through and each node returns updates to it.' },
      { h: 'The State', body: 'Our state holds `question, topic, plan, cursor, results, final`. The planner fills `plan` (sub-questions) and resets `cursor=0`; the executor answers `plan[cursor]` and increments the cursor; synthesize combines everything.' },
      { h: 'The conditional edge (the whole point)', body: 'After the executor runs, a **router** inspects the state: more sub-questions left? loop back to executor. Done? go to synthesize. That branch is what makes this an *agent loop* instead of a fixed pipeline — a plain chain cannot loop.' },
      { h: 'Make it visible', body: 'The solution prints state between nodes so you can literally watch the loop iterate. The demo below returns the same node-by-node trace.' },
    ],
    snippets: [
      { title: 'Typed state', code: `class ResearchState(TypedDict, total=False):
    question: str; topic: str
    plan: List[str]; cursor: int
    results: List[dict]; final: str` },
      { title: 'Nodes reuse Day 1 + Day 2', code: `def planner_node(s):   # Day 1
    p = plan_research(s["question"])
    return {"plan": p.sub_questions, "cursor": 0, "results": []}
def executor_node(s):  # Day 2
    r = answer_question(s["plan"][s["cursor"]], k=3)
    return {"results": s["results"] + [r], "cursor": s["cursor"] + 1}` },
      { title: 'The conditional edge', code: `g.add_conditional_edges("executor", route,
    {"executor": "executor",     # loop back
     "synthesize": "synthesize"}) # or finish` },
    ],
    demos: [
      { id: 'full', label: 'Run the graph', desc: 'Full plan → executor loop → synthesize, with the node trace.', needsQuestion: true },
      { id: 'plan_only', label: 'Just the planner node', desc: 'See a single node’s output in isolation.', needsQuestion: true },
      { id: 'one_step', label: 'One executor step', desc: 'Answer just the first sub-question (one loop iteration).', needsQuestion: true },
    ],
  },
  {
    n: 4,
    key: 'day4',
    title: 'Tools & Orchestration',
    tag: 'bind_tools · ToolNode · retry vs crash',
    accent: 'emerald',
    why: 'Real agents call tools — and real tools fail. Recovery is a feature.',
    flow: ['agent', 'tools_condition', 'ToolNode', 'agent', 'answer'],
    carriesOver: 'retrieve_documents IS the Day 2 retriever as a tool. Tool belt → shared/tools.py, reused Day 6/7.',
    explain: [
      { h: 'Tools turn a talker into a doer', body: 'We give the LLM a **tool belt** with `bind_tools`. Now, instead of only answering, the model can emit *tool calls*. A prebuilt **`ToolNode`** executes them and feeds results back.' },
      { h: 'Routing with tools_condition', body: 'After the agent speaks, `tools_condition` routes: if the message contains tool calls → the tools node; otherwise → END. After tools run, we loop back to the agent. That loop is the classic ReAct pattern: think → act → observe → repeat.' },
      { h: 'Tool selection', body: 'The model picks tools from their names + docstrings. Ask about course topics → it chooses `retrieve_documents` (Day 2!). Ask about breaking news → `web_search`. Run the routing demo to watch it decide.' },
      { h: 'Failure is normal — recover gracefully', body: 'We include a **deliberately breakable** tool. Unhandled, its exception crashes the run. Wrapped in a retry (or with `ToolNode(handle_tool_errors=True)`), the error becomes a message the agent can react to. Resilience is a design choice.' },
    ],
    snippets: [
      { title: 'Bind tools + ToolNode', code: `llm_with_tools = llm.bind_tools(TOOLS)
g.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
g.add_conditional_edges("agent", tools_condition)  # -> tools or END
g.add_edge("tools", "agent")  # loop back after tools run` },
      { title: 'A breakable tool', code: `@tool
def unreliable_metric(topic: str) -> str:
    """Flaky upstream — callers should retry."""
    if odd_call(): raise RuntimeError("timed out (simulated)")
    return f"Popularity for {topic}: 87/100"` },
      { title: 'Graceful recovery', code: `def call_with_retry(fn, *a, retries=3):
    for i in range(retries):
        try: return fn(*a)
        except Exception as e: last = e
    raise RuntimeError(f"failed after {retries}: {last}")` },
    ],
    demos: [
      { id: 'agent', label: 'Run the tool agent', desc: 'Watch which tools the agent calls, then its answer.', needsQuestion: true },
      { id: 'routing', label: 'Tool selection', desc: 'Three different questions → see which tool it picks for each.', needsQuestion: false },
      { id: 'resilience', label: 'Crash vs retry', desc: 'The breakable tool: unhandled crash vs graceful retry. No LLM call.', needsQuestion: false },
    ],
  },
  {
    n: 5,
    key: 'day5',
    title: 'Memory & State',
    tag: 'Short-term · long-term · compaction',
    accent: 'amber',
    why: 'Memory turns a Q&A bot into an assistant — and enables Day 6’s resume.',
    flow: ['checkpointer + thread_id', 'long-term vector memory', 'compaction'],
    carriesOver: 'The checkpointer + thread_id pattern is exactly how Day 6 resumes a killed run. → shared/memory.py.',
    explain: [
      { h: 'Short-term = the conversation', body: 'Compile the graph with a **checkpointer** and pass a `thread_id`. Every step is saved; replaying the same thread means the agent sees earlier turns. That’s how "what did I just say?" works with no extra plumbing.' },
      { h: 'Long-term = durable facts', body: 'Store notes, preferences, and findings in a dedicated **vector store** the agent writes to and recalls by semantic search — the same machinery as Day 2 RAG, pointed at the agent’s own memories instead of documents. Survives across sessions.' },
      { h: 'Compaction keeps it affordable', body: 'Conversations grow without bound and eventually blow the context window. **Compaction** replaces older turns with a concise summary while keeping recent messages verbatim — continuity without runaway cost.' },
      { h: 'Two kinds, one system', body: 'A good agent uses both: short-term for the current flow, long-term for knowledge worth keeping, and compaction to stop context from exploding.' },
    ],
    snippets: [
      { title: 'Short-term (checkpointer)', code: `app = graph.compile(checkpointer=SqliteSaver(conn))
cfg = {"configurable": {"thread_id": "conversation-1"}}
app.invoke({"messages": [...]}, cfg)   # remembers per thread` },
      { title: 'Long-term (vector memory)', code: `remember("The user's favorite DB is Chroma.")
hits = recall("what does the user like?", k=2)
# -> semantic search over stored notes` },
      { title: 'Compaction', code: `compacted = compact_messages(messages, keep_last=2)
# -> [SystemMessage(summary), ...last 2 messages]` },
    ],
    demos: [
      { id: 'short', label: 'Short-term memory', desc: 'Two turns on one thread — the 2nd remembers the 1st.', needsQuestion: false },
      { id: 'long', label: 'Long-term recall', desc: 'Save facts, then recall the relevant ones. No LLM call.', needsQuestion: false },
      { id: 'compaction', label: 'Compaction', desc: 'Squash a long chat into a summary + recent turns.', needsQuestion: false },
    ],
  },
  {
    n: 6,
    key: 'day6',
    title: 'Multi-Agent & Long Runs',
    tag: 'Supervisor → sub-agents · kill & resume',
    accent: 'rose',
    why: 'Specialization + durability: the shape of production agent systems.',
    flow: ['supervisor', 'researcher', 'writer', 'supervisor', 'done'],
    carriesOver: 'Researcher reuses Day 1 + Day 2. Resume reuses Day 5’s SqliteSaver + thread_id.',
    explain: [
      { h: 'Split work across specialists', body: 'A **supervisor** delegates to sub-agents — each its own **sub-graph** added as a node. Here: a **researcher** (plan + RAG) gathers findings, then a **writer** composes the report. The supervisor decides who works next and aggregates.' },
      { h: 'Sub-graphs as nodes', body: 'Each sub-agent is a compiled graph. The parent invokes it inside a node and merges the result into parent state. This composes cleanly and keeps each agent focused and testable.' },
      { h: 'Long-running & durable', body: 'Because state is saved by a checkpointer (Day 5), a long run can be **killed mid-flight and resumed** from exactly where it stopped — even in a new process. That’s the backbone of durable workflows.' },
      { h: 'Kill & resume', body: 'We interrupt the run before the final "write" step (simulating a crash). The findings are safely on disk; resuming continues straight into writing. Run the resume demo to see the checkpoint survive.' },
    ],
    snippets: [
      { title: 'Sub-agents', code: `researcher = build_researcher()   # a sub-graph (plan + RAG)
writer = build_writer()           # another sub-graph` },
      { title: 'Supervisor routing', code: `def supervisor(s):
    if not s.get("findings"): return {"next": "researcher"}
    if not s.get("report"):   return {"next": "writer"}
    return {"next": "DONE"}` },
      { title: 'Kill & resume', code: `app_i = g.compile(checkpointer=cp, interrupt_before=["write"])
app_i.invoke({"question": q}, cfg)   # stops before writing (crash)
# ...later / new process...
g.compile(checkpointer=cp).invoke(None, cfg)  # resume from disk` },
    ],
    demos: [
      { id: 'multi', label: 'Supervisor + sub-agents', desc: 'Watch the supervisor delegate to researcher then writer.', needsQuestion: true },
      { id: 'resume', label: 'Kill & resume', desc: 'Interrupt before writing, then resume from the checkpoint.', needsQuestion: true },
    ],
  },
  {
    n: 7,
    key: 'day7',
    title: 'Reflection, HITL & Observability',
    tag: 'Self-critique · human approval · LangSmith',
    accent: 'fuchsia',
    why: 'Self-improvement + a human checkpoint = agents you can actually ship.',
    flow: ['plan', 'research', 'write', 'reflect ↺', 'approve ⏸', 'publish'],
    carriesOver: 'Imports Day 1/2/5/6. The complete graph → shared/research_agent.py (also powers the Studio).',
    explain: [
      { h: 'Reflection (feedback loop)', body: 'After writing, a **reflect** node grades the draft against a checklist (answers the question? cited? clear?) and returns a verdict. On REVISE, it loops back to write — the agent improves its own work, capped so it can’t loop forever.' },
      { h: 'Human-in-the-loop', body: 'Before publishing, an `interrupt()` **pauses** the whole graph and surfaces the draft for a human. The reviewer approves — or sends it back with feedback for another revision. The graph resumes with `Command(resume=...)`.' },
      { h: 'Why a checkpointer is required', body: '`interrupt()` saves state and stops; resuming reloads it. That only works with a checkpointer (Day 5) and a `thread_id`. HITL and durability are the same mechanism.' },
      { h: 'Observability with LangSmith', body: 'Flip `LANGSMITH_TRACING=true` and every node, LLM call, and token is traced to smith.langchain.com — you can see exactly what the agent did and why. This is the exact agent the **Studio** tab runs live.' },
    ],
    snippets: [
      { title: 'Reflection route', code: `def route_after_reflect(s):
    if s["verdict"] == "REVISE" and s["revisions"] <= MAX:
        return "write"          # self-improve
    return "human_approval"` },
      { title: 'Human-in-the-loop gate', code: `def human_approval(s):
    decision = interrupt({"draft": s["draft"]})  # PAUSE
    return {"approved": decision["approved"]}
# resume: app.invoke(Command(resume={"approved": True}), cfg)` },
      { title: 'LangSmith tracing', code: `# .env: LANGSMITH_TRACING=true, LANGSMITH_API_KEY=...
# every node/LLM call/token shows up at smith.langchain.com` },
    ],
    demos: [
      { id: 'full', label: 'Run the full agent', desc: 'End-to-end trace, auto-approved for a self-contained demo.', needsQuestion: true },
      { id: 'reflection', label: 'Self-critique only', desc: 'Draft → critique → PASS/REVISE verdict, in isolation.', needsQuestion: true },
      { id: 'hitl', label: 'The approval gate', desc: 'Run until interrupt() pauses; see the approval request payload.', needsQuestion: true },
    ],
  },
]

export const ACCENTS = {
  indigo: { text: 'text-indigo-300', bg: 'bg-indigo-500/15', ring: 'ring-indigo-400/40', dot: 'bg-indigo-400', grad: 'from-indigo-500 to-blue-500' },
  sky: { text: 'text-sky-300', bg: 'bg-sky-500/15', ring: 'ring-sky-400/40', dot: 'bg-sky-400', grad: 'from-sky-500 to-cyan-500' },
  violet: { text: 'text-violet-300', bg: 'bg-violet-500/15', ring: 'ring-violet-400/40', dot: 'bg-violet-400', grad: 'from-violet-500 to-purple-500' },
  emerald: { text: 'text-emerald-300', bg: 'bg-emerald-500/15', ring: 'ring-emerald-400/40', dot: 'bg-emerald-400', grad: 'from-emerald-500 to-teal-500' },
  amber: { text: 'text-amber-300', bg: 'bg-amber-500/15', ring: 'ring-amber-400/40', dot: 'bg-amber-400', grad: 'from-amber-500 to-orange-500' },
  rose: { text: 'text-rose-300', bg: 'bg-rose-500/15', ring: 'ring-rose-400/40', dot: 'bg-rose-400', grad: 'from-rose-500 to-pink-500' },
  fuchsia: { text: 'text-fuchsia-300', bg: 'bg-fuchsia-500/15', ring: 'ring-fuchsia-400/40', dot: 'bg-fuchsia-400', grad: 'from-fuchsia-500 to-purple-500' },
}
