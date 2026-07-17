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
    title: 'LangGraph Core — Planner → Executor → Memory',
    tag: 'From straight-line chains to a graph that can loop, decide & remember',
    accent: 'violet',
    why: 'Conditional edges = loops & decisions. That’s the leap from chain to agent.',
    flow: ['State (TypedDict)', 'Planner', 'Executor ↺', 'Router', 'Memory', 'Synthesize'],
    carriesOver: 'planner_node calls Day 1; executor_node calls Day 2. This skeleton is extended every later day.',
    explain: [
      { h: 'From line to graph', body: 'A chain runs one straight line. A **graph** models the app as nodes (units of work) and edges (how control moves). A shared **State** object flows through and each node returns updates to it.' },
      { h: 'The State', body: 'Our state holds `question, topic, plan, cursor, results, final`. The planner fills `plan` (sub-questions) and resets `cursor=0`; the executor answers `plan[cursor]` and increments the cursor; synthesize combines everything.' },
      { h: 'The conditional edge (the whole point)', body: 'After the executor runs, a **router** inspects the state: more sub-questions left? loop back to executor. Done? go to synthesize. That branch is what makes this an *agent loop* instead of a fixed pipeline — a plain chain cannot loop.' },
      { h: 'Make it visible', body: 'Every module below shows state before and after each node, animates the currently-active node in the graph, and (Module 10) actually streams a compiled `StateGraph` end-to-end.' },
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
    sections: [
      { id: 'modules', label: 'LangGraph modules', desc: 'One live module per sub-tab — walk them in order for the full picture.' },
    ],
    demos: [
      { id: 'mod_01_intro',       section: 'modules', slide: 1,  tab: 'M1 · Intro',        label: 'Module 1 · Chain vs LangGraph',           desc: 'Traditional chain (Prompt → LLM → Output) versus a graph that can plan, execute, route, and remember. No LLM call.',                                       needsQuestion: false },
      { id: 'mod_02_chain_fail',  section: 'modules', slide: 2,  tab: 'M2 · Why chains fail', label: 'Module 2 · Why chains fail',           desc: 'Interactive simulation: chain cannot retry a bad answer; the LangGraph version routes back through the executor and recovers. No LLM call.',                needsQuestion: false },
      { id: 'mod_03_state',       section: 'modules', slide: 3,  tab: 'M3 · State',        label: 'Module 3 · Live state visualization',     desc: 'Real planner call, then one executor step — watch the TypedDict change (highlighted diff) after every node. LLM call.',                                    needsQuestion: true },
      { id: 'mod_04_builder',     section: 'modules', slide: 4,  tab: 'M4 · Graph builder', label: 'Module 4 · Graph builder',                desc: 'The Mermaid graph and the exact `StateGraph.add_node / add_conditional_edges` code that produces it. No LLM call.',                                      needsQuestion: false },
      { id: 'mod_05_planner',     section: 'modules', slide: 5,  tab: 'M5 · Planner',      label: 'Module 5 · Planner demo',                 desc: 'One fuzzy goal → the planner writes topic + plan into state, cursor reset to 0. LLM call.',                                                                 needsQuestion: true },
      { id: 'mod_06_executor',    section: 'modules', slide: 6,  tab: 'M6 · Executor',     label: 'Module 6 · Executor demo (one step)',     desc: 'The executor grabs `plan[cursor]`, retrieves + answers, and advances the cursor. Includes a progress bar. LLM + RAG call.',                             needsQuestion: true },
      { id: 'mod_07_routing',     section: 'modules', slide: 7,  tab: 'M7 · Routing',      label: 'Module 7 · Conditional routing',          desc: 'Three states → three router decisions. The router is one Python function, and it is the whole point of Day 3. No LLM call.',                                needsQuestion: false },
      { id: 'mod_08_memory',      section: 'modules', slide: 8,  tab: 'M8 · Memory',       label: 'Module 8 · Memory & reducers',            desc: 'How `results` grows without clobbering itself across three executor iterations. `Annotated[list, add]` explained. No LLM call.',                          needsQuestion: false },
      { id: 'mod_09_react_vs_pe', section: 'modules', slide: 9,  tab: 'M9 · ReAct vs P-E', label: 'Module 9 · ReAct vs Plan-Execute',        desc: 'Side-by-side comparison: cost, speed, adaptability, and when to pick each loop shape. No LLM call.',                                                       needsQuestion: false },
      { id: 'mod_10_live',        section: 'modules', slide: 10, tab: 'M10 · Live run',    label: 'Module 10 · Live LangGraph execution',    desc: 'Actually compiles a `StateGraph` and streams `.stream(...)` — every node fire produces a state-diff card and lights up the graph. Multiple LLM calls.',   needsQuestion: true },
      { id: 'mod_11_code',        section: 'modules', slide: 11, tab: 'M11 · Code',        label: 'Module 11 · Code viewer',                 desc: 'The full Python behind every visualization — planner, executor, router, synthesize, wiring — with the loop-critical lines highlighted. No LLM call.',      needsQuestion: false },
      { id: 'mod_12_loop',        section: 'modules', slide: 12, tab: 'M12 · Infinite loop', label: 'Module 12 · Infinite loop demo',        desc: 'A broken router that never returns END: watch the token counter climb, then see the two safety belts (MAX_STEPS + recursion_limit). No LLM call.',            needsQuestion: false },
    ],
  },
  {
    n: 4,
    key: 'day4',
    title: 'Tools & Orchestration',
    tag: 'bind_tools · ToolNode · tool_selection · retry vs crash',
    accent: 'emerald',
    why: 'Real agents call tools — and real tools fail. Recovery is a feature, not an afterthought.',
    flow: ['agent', 'tools_condition', 'ToolNode', 'agent ↺', 'answer'],
    carriesOver: 'retrieve_documents IS the Day 2 retriever as a tool. Tool belt → shared/tools.py, reused Day 6/7.',
    explain: [
      { h: 'Tools turn a talker into a doer', body: 'We give the LLM a **tool belt** with `bind_tools`. The model no longer only replies with prose — it can reply with a structured **tool call** (name + typed args). A prebuilt **`ToolNode`** actually runs the tool and hands the result back as a `ToolMessage`.' },
      { h: 'Routing with tools_condition (the whole loop)', body: '`tools_condition` inspects the last AIMessage — has `.tool_calls`? → go to the tools node; else → END. After tools run, we add an edge back to the agent so it can read the result and either call another tool or write the final answer. That single conditional edge is what makes this a **loop** instead of a chain — the classic ReAct pattern.' },
      { h: 'Tool descriptions ARE prompts', body: 'The model picks tools from their names + docstrings alone. Rule of thumb: **specific, non-overlapping, verb-first**. Vague docstrings ("Do a computation.") get skipped or mis-picked; specific ones ("Evaluate a numeric expression like 12.5% of 240…") get called with clean args. The **Vague vs Specific** tab shows this happening with two calculators that share the same body.' },
      { h: 'Failure is normal — return errors as STRINGS', body: 'Tools are code that runs outside the LLM (network, disk, APIs). If we let an exception escape, `ToolNode` surfaces it and — without `handle_tool_errors=True` — the graph crashes. The pattern is to `try/except` inside the tool and return a readable string like `"SEARCH_FAILED: …"`. The model reads that string on the next turn and can *pivot*. Never raise into the loop.' },
      { h: 'Retries make idempotent tools reliable', body: 'A transient failure isn\'t the same as a permanent one. Wrap an **idempotent** call (GET, read, search) in a retry with **exponential backoff** so a flaky provider self-heals. Never wrap a side-effectful write unless you have a dedup / idempotency key.' },
    ],
    snippets: [
      { title: 'Bind tools + ToolNode + tools_condition', code: `llm_with_tools = llm.bind_tools(TOOLS)
g.add_node("agent", agent_node)          # calls llm_with_tools
g.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
g.add_edge(START, "agent")
g.add_conditional_edges("agent", tools_condition)   # -> "tools" or END
g.add_edge("tools", "agent")             # loop back after tools run` },
      { title: 'Docstring IS the prompt · specific > vague', code: `@tool
def calc_specific(expression: str) -> str:
    """Evaluate a numeric arithmetic expression written in Python syntax
    (operators: + - * / % ** and parentheses; digits and decimals only).
    Use this for ANY question that reduces to a number (e.g. "12.5% of 240").
    Pass ONLY the expression, not the word problem."""
    return safe_eval(expression)` },
      { title: 'Errors as strings, never as raises', code: `@tool
def web_search(query: str) -> str:
    """Search the public web for CURRENT facts."""
    try:
        return call_provider(query)
    except Exception as e:
        return f"SEARCH_FAILED: {e}"   # agent reads this and pivots` },
      { title: 'Retry with exponential backoff', code: `def retry(fn, *, retries=3, delay=0.2, factor=2.0):
    for i in range(retries):
        try: return fn()
        except Exception as e:
            time.sleep(delay); delay *= factor; last = e
    return f"RETRY_EXHAUSTED: {last}"` },
    ],
    sections: [
      { id: 'tools', label: 'Tool-agent demos', desc: 'Six live demos — belt → run → selection → docstring-as-prompt → resilience → backoff.' },
    ],
    demos: [
      { id: 'belt',              section: 'tools', slide: 1, tab: 'T1 · Tool belt',            label: 'Demo 1 · The tool belt (no LLM)',              desc: '`@tool` = a plain function whose docstring becomes the model\'s prompt. Inspect each tool\'s name, description, and typed args — the exact schema the model sees when the belt is bound. No LLM call.', needsQuestion: false },
      { id: 'agent',             section: 'tools', slide: 2, tab: 'T2 · Run agent',            label: 'Demo 2 · bind_tools + tools_condition loop',   desc: 'Ask a course question and watch every turn: the model\'s tool call (with raw args), the tool\'s result, and the next turn. Loops until the model produces a final answer with citations.', needsQuestion: true },
      { id: 'routing',           section: 'tools', slide: 3, tab: 'T3 · Tool selection',       label: 'Demo 3 · Tool selection per question',         desc: 'Three questions worded to steer different tools. Each row shows the expected pick, the actual pick + args, and WHY the docstring pulled the model that way.', needsQuestion: false },
      { id: 'vague_vs_specific', section: 'tools', slide: 4, tab: 'T4 · Vague vs Specific',    label: 'Demo 4 · Tool descriptions ARE prompts',       desc: 'Two calculators with identical bodies but different docstrings. Same question, same graph — watch tool selection FLIP between "skipped" and "called with a clean expression".', needsQuestion: false },
      { id: 'resilience',        section: 'tools', slide: 5, tab: 'T5 · Crash vs recover',     label: 'Demo 5 · Crash → string-return → retry',       desc: 'Three-stage story: unhandled call crashes; the same tool wrapped in try/except returns a readable "FAILED: …" string; a bare retry loop recovers on attempt #2. No LLM call.', needsQuestion: false },
      { id: 'backoff',           section: 'tools', slide: 6, tab: 'T6 · Retry + backoff',      label: 'Demo 6 · Retry with exponential backoff',      desc: 'Timeline of a flaky call: two failures, growing delays, then success on attempt #3. Second panel shows a permanently-broken call becoming a "RETRY_EXHAUSTED: …" string instead of a raise. No LLM call.', needsQuestion: false },
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
    sections: [
      { id: 'pillars', label: 'Persistence pillars', desc: 'One live demo per pillar — walk them in order for the full picture.' },
    ],
    demos: [
      { id: 'state',        section: 'pillars', slide: 1, tab: 'P1 · State',          label: 'Pillar 1 · State design (TypedDict + reducer)',        desc: 'Explicit `ResearchState` fields with `add_messages` on messages. Runs the graph once and prints the persisted snapshot (`get_state(cfg)`). LLM call.', needsQuestion: false },
      { id: 'checkpointer', section: 'pillars', slide: 2, tab: 'P2 · Checkpointer',   label: 'Pillar 2 · Checkpointer + thread_id',                  desc: 'Two invokes on the same `thread_id` — turn 2 remembers turn 1 with zero extra plumbing. Shows the SQLite file it wrote to. LLM call.', needsQuestion: false },
      { id: 'compaction',   section: 'pillars', slide: 3, tab: 'P3 · Compaction',     label: 'Pillar 3 · Compact node (summarise old, keep last N)', desc: 'Force the compact node past its threshold. Prints message & token count BEFORE vs AFTER, plus the summary that replaced the old turns. LLM call.', needsQuestion: false },
      { id: 'long',         section: 'pillars', slide: 4, tab: 'P4 · Long-term',      label: 'Pillar 4 · Long-term vector memory',                    desc: 'Save durable facts to a Chroma-backed store, then semantically recall the relevant ones. No LLM call — just embeddings.', needsQuestion: false },
      { id: 'crash',        section: 'pillars', slide: 5, tab: 'P5 · Crash',          label: 'Demo 5 · Crash mid-run (persists cursor)',             desc: 'Plan + step 1 succeed, then a simulated exception fires. State is safely on disk: plan, cursor, findings, tool_outputs. LLM call.', needsQuestion: false },
      { id: 'resume',       section: 'pillars', slide: 6, tab: 'P6 · Resume',         label: 'Demo 6 · Resume on SAME thread_id (idempotent)',       desc: 'Same `thread_id`, healthy graph — picks up from cursor 1, no re-planning, no double-fired tool calls. Run demo 5 first.', needsQuestion: false },
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
