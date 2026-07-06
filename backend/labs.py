"""
backend/labs.py — "Run live" demos for the per-day teaching tabs.

Each day exposes SEVERAL named demos. A demo reuses the same shared/ building blocks
the learners studied and returns a typed result:  {"kind": "...", ...}.
The frontend renders by `kind`, so result shapes are reusable across days.

Dispatch:  GET /api/lab/{day}?demo=<id>   (defaults to the first demo for that day)
"""

from __future__ import annotations

import uuid
from typing import List, TypedDict  # module-level so nested TypedDict bodies can see them

DEFAULT_QUESTIONS = {
    1: "How does retrieval-augmented generation improve LLM accuracy?",
    2: "What is MMR and when should I use it in retrieval?",
    3: "How do vector databases power RAG?",
    4: "What is MMR and how does it relate to agent memory?",
    5: "",
    6: "How do agents use memory and tools?",
    7: "Should I use similarity or MMR retrieval for a RAG system?",
}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 1 — chains & output parsers
# ═══════════════════════════════════════════════════════════════════════════
def d1_plan(q):
    from shared.planner import plan_research

    p = plan_research(q)
    return {"kind": "plan", "topic": p.topic, "sub_questions": p.sub_questions}


def d1_raw_vs_parsed(q):
    from config import get_llm
    from shared.planner import plan_research

    raw = get_llm(0).invoke(
        f"Give me the core topic and three sub-questions for this research question: {q}"
    ).content
    p = plan_research(q)
    return {
        "kind": "raw_vs_parsed",
        "raw": raw,
        "parsed": {"topic": p.topic, "sub_questions": p.sub_questions},
    }


def d1_prompt_preview(q):
    from shared.planner import _PROMPT

    text = _PROMPT.invoke({"question": q}).to_string()
    return {"kind": "prompt_preview", "prompt": text}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 2 — RAG
# ═══════════════════════════════════════════════════════════════════════════
def d2_compare(q):
    from shared.rag import ensure_index, get_retriever, sources_of

    ensure_index()
    sim = get_retriever(k=4, search_type="similarity").invoke(q)
    mmr = get_retriever(k=4, search_type="mmr").invoke(q)
    return {
        "kind": "compare",
        "label_a": "similarity (closest)",
        "sources_a": sources_of(sim),
        "label_b": "MMR (relevance + diversity)",
        "sources_b": sources_of(mmr),
    }


def d2_answer(q):
    from shared.rag import answer_question

    a = answer_question(q, k=4)
    return {"kind": "answer", "answer": a["answer"], "sources": a["sources"]}


def d2_chunking(q):
    from shared.rag import load_documents, split_documents

    docs = load_documents()
    variants = []
    for size, overlap in [(300, 30), (800, 120), (1500, 200)]:
        chunks = split_documents(docs, chunk_size=size, chunk_overlap=overlap)
        variants.append({"size": size, "overlap": overlap, "count": len(chunks)})
    sample = split_documents(docs, 800, 120)[0].page_content[:300]
    return {"kind": "chunks", "variants": variants, "sample": sample}


def d2_topk(q):
    from shared.rag import ensure_index

    vs = ensure_index()
    hits = vs.similarity_search_with_score(q, k=4)
    import os

    items = [
        {
            "source": os.path.basename(d.metadata.get("source", "?")),
            "score": round(float(score), 4),
            "preview": d.page_content[:180].strip(),
        }
        for d, score in hits
    ]
    return {"kind": "retrieved", "items": items}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 3 — LangGraph
# ═══════════════════════════════════════════════════════════════════════════
def d3_full(q):
    from config import get_llm
    from shared.planner import plan_research
    from shared.rag import answer_question

    p = plan_research(q)
    trace = [{"node": "planner", "detail": {"topic": p.topic, "plan": p.sub_questions}}]
    findings = []
    for i, sq in enumerate(p.sub_questions):
        res = answer_question(sq, k=3)
        findings.append({"sub_question": sq, "answer": res["answer"], "sources": res["sources"]})
        trace.append({"node": "executor", "detail": {"cursor": i + 1, "sub_question": sq, "sources": res["sources"]}})
    body = "\n\n".join(f"{f['sub_question']}: {f['answer']}" for f in findings)
    final = get_llm(0).invoke(f"Write a cohesive cited answer to '{q}' from:\n{body}").content
    trace.append({"node": "synthesize", "detail": {}})
    return {"kind": "trace", "trace": trace, "final": final}


def d3_plan_only(q):
    return d1_plan(q)


def d3_one_step(q):
    from shared.planner import plan_research
    from shared.rag import answer_question

    p = plan_research(q)
    sub = p.sub_questions[0]
    a = answer_question(sub, k=3)
    return {"kind": "answer", "heading": f"One executor step · sub-question: “{sub}”", "answer": a["answer"], "sources": a["sources"]}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 4 — tools
# ═══════════════════════════════════════════════════════════════════════════
def d4_agent(q):
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    from config import get_llm
    from shared.tools import SAFE_TOOLS

    tools_by_name = {t.name: t for t in SAFE_TOOLS}
    llm = get_llm(0).bind_tools(SAFE_TOOLS)
    msgs = [
        SystemMessage(content="Use retrieve_documents for course topics, then answer concisely with citations."),
        HumanMessage(content=q),
    ]
    tool_calls = []
    for _ in range(4):
        ai = llm.invoke(msgs)
        msgs.append(ai)
        if not ai.tool_calls:
            break
        for tc in ai.tool_calls:
            tool_calls.append({"name": tc["name"], "args": tc["args"]})
            out = tools_by_name[tc["name"]].invoke(tc["args"])
            msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
    return {"kind": "tools", "tool_calls": tool_calls, "final": msgs[-1].content}


def d4_resilience(q):
    from shared.tools import reset_flaky_tool, unreliable_metric

    reset_flaky_tool()
    crash = None
    try:
        unreliable_metric.invoke({"topic": "RAG"})
    except Exception as e:
        crash = str(e)
    reset_flaky_tool()
    retry = []
    for i in range(1, 4):
        try:
            val = unreliable_metric.invoke({"topic": "RAG"})
            retry.append(f"attempt {i}: recovered → {val}")
            break
        except Exception as e:
            retry.append(f"attempt {i}: failed → {e}")
    return {"kind": "resilience", "crash": crash, "retry": retry}


def d4_routing(q):
    from config import get_llm
    from shared.tools import SAFE_TOOLS

    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_llm(0).bind_tools(SAFE_TOOLS)
    system = SystemMessage(content=(
        "You have tools: retrieve_documents (local course knowledge base), web_search "
        "(current events), summarize. Call the most appropriate tool for the request."
    ))
    questions = [
        "What is MMR in the course's retrieval material?",
        "What is the very latest news on AI regulation this week?",
        "Summarize this: RAG loads, chunks, embeds, stores, retrieves, and answers with citations.",
    ]
    cases = []
    for question in questions:
        ai = llm.invoke([system, HumanMessage(content=question)])
        cases.append({"question": question, "tools": [tc["name"] for tc in ai.tool_calls] or ["(answered directly)"]})
    return {"kind": "routing", "cases": cases}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 5 — memory
# ═══════════════════════════════════════════════════════════════════════════
def _chat_app():
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, MessagesState, StateGraph

    from config import get_llm

    llm = get_llm(0)

    def chat(state):
        return {"messages": [llm.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("chat", chat)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=MemorySaver())


def d5_short(q):
    from langchain_core.messages import HumanMessage

    app = _chat_app()
    cfg = {"configurable": {"thread_id": f"lab5-{uuid.uuid4()}"}}
    t1 = app.invoke({"messages": [HumanMessage(content="My favorite topic is vector databases. Remember that.")]}, cfg)
    t2 = app.invoke({"messages": [HumanMessage(content="What did I say my favorite topic was?")]}, cfg)
    return {"kind": "memory_short", "turn1": t1["messages"][-1].content, "turn2": t2["messages"][-1].content}


def d5_long(q):
    from shared.memory import clear_long_term_memory, recall, remember

    clear_long_term_memory()
    saved = [
        "The user prefers concise, bulleted answers with citations.",
        "The user is building a Research Assistant with LangGraph.",
        "The user's favorite vector database is Chroma.",
    ]
    for s in saved:
        remember(s)
    query = "What formatting does the user like?"
    return {"kind": "memory_long", "query": query, "saved": saved, "recall": recall(query, k=2)}


def d5_compaction(q):
    from langchain_core.messages import AIMessage, HumanMessage

    from shared.memory import compact_messages

    msgs = [
        HumanMessage(content="Let's research RAG."),
        AIMessage(content="RAG grounds answers in retrieved documents."),
        HumanMessage(content="What about chunking?"),
        AIMessage(content="Chunk size/overlap trade signal vs context."),
        HumanMessage(content="And embeddings?"),
        AIMessage(content="Embeddings map text to vectors; use the same model to index and query."),
        HumanMessage(content="Summarize where we are."),
    ]
    comp = compact_messages(msgs, keep_last=2)
    return {"kind": "compaction", "before": len(msgs), "after": len(comp), "summary": comp[0].content}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 6 — multi-agent + resume
# ═══════════════════════════════════════════════════════════════════════════
def d6_multi(q):
    from config import get_llm
    from shared.planner import plan_research
    from shared.rag import answer_question

    supervisor = [{"decision": "researcher", "note": "no findings yet → delegate to researcher"}]
    p = plan_research(q)
    findings = []
    for sq in p.sub_questions:
        res = answer_question(sq, k=2)
        findings.append({"sub_question": sq, "answer": res["answer"], "sources": res["sources"]})
    supervisor.append({"decision": "writer", "note": f"{len(findings)} findings gathered → delegate to writer"})
    body = "\n\n".join(f"- {f['sub_question']}\n  {f['answer']}" for f in findings)
    report = get_llm(0).invoke(f"Write a concise report answering '{q}' from:\n{body}").content
    supervisor.append({"decision": "DONE", "note": "report ready → finish"})
    return {
        "kind": "supervisor",
        "supervisor": supervisor,
        "findings": [{"sub_question": f["sub_question"], "sources": f["sources"]} for f in findings],
        "report": report,
    }


def d6_resume(q):
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    from config import get_llm
    from shared.planner import plan_research
    from shared.rag import answer_question

    class S(TypedDict, total=False):
        question: str
        plan: List[str]
        cursor: int
        findings: List[dict]
        report: str

    def plan_node(s):
        return {"plan": plan_research(s["question"]).sub_questions, "cursor": 0, "findings": []}

    def research_node(s):
        i = s["cursor"]
        res = answer_question(s["plan"][i], k=2)
        return {"findings": s["findings"] + [{"sub_question": s["plan"][i]}], "cursor": i + 1}

    def write_node(s):
        body = "\n".join(f"- {f['sub_question']}" for f in s["findings"])
        return {"report": get_llm(0).invoke(f"Write a short report on '{s['question']}' covering:\n{body}").content}

    def more(s):
        return "research" if s["cursor"] < len(s["plan"]) else "write"

    g = StateGraph(S)
    g.add_node("plan", plan_node)
    g.add_node("research", research_node)
    g.add_node("write", write_node)
    g.add_edge(START, "plan")
    g.add_edge("plan", "research")
    g.add_conditional_edges("research", more, {"research": "research", "write": "write"})
    g.add_edge("write", END)

    cp = MemorySaver()
    cfg = {"configurable": {"thread_id": f"lab6-{uuid.uuid4()}"}}
    app_interrupt = g.compile(checkpointer=cp, interrupt_before=["write"])
    app_plain = g.compile(checkpointer=cp)

    app_interrupt.invoke({"question": q}, cfg)  # runs plan+research, stops before write
    snap = app_interrupt.get_state(cfg)
    before = len(snap.values.get("findings", []))
    interrupted_before = list(snap.next)
    final = app_plain.invoke(None, cfg)  # resume → write → END
    return {"kind": "resume", "before_findings": before, "interrupted_before": interrupted_before, "final": final["report"]}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 7 — capstone
# ═══════════════════════════════════════════════════════════════════════════
def _agent_and_cfg():
    from langgraph.checkpoint.memory import MemorySaver

    from shared.research_agent import build_research_agent

    return build_research_agent(MemorySaver()), {"configurable": {"thread_id": f"lab7-{uuid.uuid4()}"}}


def d7_full(q):
    from langgraph.types import Command

    from shared.research_agent import NODE_LABELS

    app, cfg = _agent_and_cfg()
    trace = []

    def pump(inp):
        for chunk in app.stream(inp, cfg, stream_mode="updates"):
            if "__interrupt__" in chunk:
                return chunk["__interrupt__"][0].value
            for name, upd in chunk.items():
                step = {"node": name, "label": NODE_LABELS.get(name, "")}
                if name == "reflect":
                    step["verdict"] = upd.get("verdict")
                elif name == "write":
                    step["revision"] = upd.get("revisions")
                elif name == "research":
                    step["sub_question"] = (upd.get("findings") or [{}])[-1].get("sub_question")
                trace.append(step)
        return None

    payload = pump({"question": q})
    critique = ""
    if payload:
        critique = payload.get("critique", "")
        pump(Command(resume={"approved": True, "feedback": ""}))
    final = app.get_state(cfg).values.get("final")
    return {"kind": "trace", "trace": trace, "critique": critique, "final": final}


def d7_reflection(q):
    from config import get_llm
    from shared.rag import answer_question

    draft = answer_question(q, k=3)["answer"]
    critique = get_llm(0).invoke(
        "You are a strict editor. Critique this draft against the question (answers it? cited? clear?). "
        "End with 'VERDICT: PASS' or 'VERDICT: REVISE'.\n\n"
        f"Question: {q}\n\nDRAFT:\n{draft}"
    ).content
    verdict = "REVISE" if "REVISE" in critique.upper().split("VERDICT:")[-1] else "PASS"
    return {"kind": "critique", "draft": draft, "critique": critique, "verdict": verdict}


def d7_hitl(q):
    app, cfg = _agent_and_cfg()
    payload = None
    for chunk in app.stream({"question": q}, cfg, stream_mode="updates"):
        if "__interrupt__" in chunk:
            payload = chunk["__interrupt__"][0].value
            break
    if not payload:
        return {"kind": "approval", "draft": app.get_state(cfg).values.get("final", ""), "message": "No interrupt fired.", "critique": ""}
    return {"kind": "approval", "draft": payload.get("draft", ""), "message": payload.get("message", ""), "critique": payload.get("critique", "")}


# ═══════════════════════════════════════════════════════════════════════════
# DAY 1 — SLIDE DEMOS (one per deck slide, imported from slide_demos.py)
# ═══════════════════════════════════════════════════════════════════════════
# The 12 slide demos are self-contained: no user question required. Each is
# wrapped so the shared `run()` dispatcher can pass its ignored `q` argument.
try:
    from backend import slide_demos as _slide_demos  # normal import
except ImportError:  # when launched as `python backend/app.py`
    import slide_demos as _slide_demos  # type: ignore


def _wrap_slide(fn):
    def _run(_q=""):  # ignore the dispatcher's question argument
        return fn()
    return _run


_SLIDE_DEMOS_D1 = {name: _wrap_slide(fn) for name, fn in _slide_demos.SLIDE_DEMOS.items()}


# ═══════════════════════════════════════════════════════════════════════════
# Registry + dispatch
# ═══════════════════════════════════════════════════════════════════════════
REGISTRY = {
    1: {
        # slide demos first — one per deck slide (2..13)
        **_SLIDE_DEMOS_D1,
        # then the original coding-lab demos (ResearchPlan pipeline)
        "plan": d1_plan,
        "raw_vs_parsed": d1_raw_vs_parsed,
        "prompt_preview": d1_prompt_preview,
    },
    2: {"compare": d2_compare, "answer": d2_answer, "chunking": d2_chunking, "topk": d2_topk},
    3: {"full": d3_full, "plan_only": d3_plan_only, "one_step": d3_one_step},
    4: {"agent": d4_agent, "resilience": d4_resilience, "routing": d4_routing},
    5: {"short": d5_short, "long": d5_long, "compaction": d5_compaction},
    6: {"multi": d6_multi, "resume": d6_resume},
    7: {"full": d7_full, "reflection": d7_reflection, "hitl": d7_hitl},
}


def run(day: int, demo: str = "", question: str = "") -> dict:
    reg = REGISTRY.get(day)
    if not reg:
        return {"error": f"Unknown day {day}"}
    fn = reg.get(demo) or next(iter(reg.values()))  # default = first demo
    q = (question or "").strip() or DEFAULT_QUESTIONS.get(day, "")
    try:
        return fn(q)
    except Exception as e:  # never leak a stack trace to the UI
        return {"kind": "error", "error": f"{type(e).__name__}: {e}"}
