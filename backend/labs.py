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
    # Day 4 default is intentionally a MULTI-TOOL prompt so the agent-loop
    # demo (d4_agent) visibly picks TWO different tools across turns — proving
    # tool diversity, not just "retrieve_documents twice then answer".
    4: "Look up what our local course docs say about long-term agent memory, then search the web for a recent news headline about vector databases in 2025. Give me one combined sentence with citations.",
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
# Day 2 demos accept an optional `ctx` — a per-session uploaded corpus (see
# backend/day2_sessions.py). When present, every stage runs on the learner's
# uploaded files; when None, they fall back to the built-in data/ corpus.
def _d2_docs_chunks(ctx, chunk_size=800, chunk_overlap=120):
    if ctx:
        return ctx["docs"], ctx["chunks"]
    from shared.rag import load_documents, split_documents

    docs = load_documents()
    return docs, split_documents(docs, chunk_size, chunk_overlap)


def _d2_index(ctx):
    """The vector store to retrieve from: the uploaded session's, or the shared one."""
    if ctx:
        return ctx["vs"]
    from shared.rag import ensure_index

    return ensure_index()


def _d2_corpus_label(ctx):
    if ctx:
        return f"your {len(ctx['files'])} uploaded file(s)"
    return "the built-in sample docs"


def _cid_of(d):
    """Chunk id for display: uploaded docs carry 'chunk_id'; the built-in corpus
    carries 'start_index'. Returns None when neither is present."""
    cid = d.metadata.get("chunk_id", d.metadata.get("start_index"))
    return int(cid) if cid is not None else None


def _doc_brief(d, rank, score=None):
    """One retrieved chunk, made transparent: which file, which chunk, a preview.
    `rank` is the 1-based position the retriever gave."""
    import os

    brief = {
        "rank": rank,
        "source": os.path.basename(str(d.metadata.get("source", "?"))),
        "preview": d.page_content[:200].strip(),
    }
    cid = _cid_of(d)
    if cid is not None:
        brief["chunk_id"] = cid
    if score is not None:
        brief["score"] = round(float(score), 4)
    return brief


def _dedup_briefs(ranked, top, score_key="score", ndigits=4):
    """Collapse chunks with identical text so *distinct* content surfaces.

    `ranked` is a best-first list of (doc, value | None). Repeated chunks (same
    text, common in duplicative corpora) are merged into one brief that records
    how many copies exist and their chunk ids. Returns (briefs, collapsed) where
    `collapsed` is how many duplicate copies were folded away."""
    import os

    seen: dict[str, int] = {}
    groups: list[dict] = []
    collapsed = 0
    for doc, value in ranked:
        text = doc.page_content.strip()
        key = " ".join(text.split())  # normalize whitespace before comparing
        cid = _cid_of(doc)
        if key in seen:
            collapsed += 1
            g = groups[seen[key]]
            g["dup_count"] += 1
            if cid is not None and len(g["dup_ids"]) < 12:
                g["dup_ids"].append(cid)
            continue
        seen[key] = len(groups)
        groups.append({
            "source": os.path.basename(str(doc.metadata.get("source", "?"))),
            "preview": text[:200],
            "dup_count": 1,
            "dup_ids": [cid] if cid is not None else [],
            "_cid": cid,
            "_value": value,
        })

    briefs = []
    for r, g in enumerate(groups[:top]):
        b = {
            "rank": r + 1,
            "source": g["source"],
            "preview": g["preview"],
            "dup_count": g["dup_count"],
            "dup_ids": g["dup_ids"],
        }
        if g["_cid"] is not None:
            b["chunk_id"] = g["_cid"]
        if g["_value"] is not None:
            b[score_key] = round(float(g["_value"]), ndigits)
        briefs.append(b)
    return briefs, collapsed


def _briefs_marked(docs):
    """Brief every doc WITHOUT collapsing, but mark each chunk whose text repeats
    an earlier one in the same list (`same_as` = rank of the first occurrence).
    Used by Sim-vs-MMR so similarity's redundancy is visible next to MMR's spread."""
    briefs = []
    first_seen: dict[str, int] = {}
    for i, d in enumerate(docs):
        b = _doc_brief(d, i + 1)
        key = " ".join(d.page_content.split())
        if key in first_seen:
            b["same_as"] = first_seen[key]
        else:
            first_seen[key] = i + 1
        briefs.append(b)
    return briefs


def d2_compare(q, ctx=None):
    vs = _d2_index(ctx)
    sim = vs.as_retriever(search_type="similarity", search_kwargs={"k": 4}).invoke(q)
    # A wide fetch_k gives MMR enough distinct candidates to diversify over — with
    # the default 20 on a repetitive corpus, every candidate is a near-duplicate
    # and MMR can't do its job.
    mmr = vs.as_retriever(
        search_type="mmr", search_kwargs={"k": 4, "fetch_k": 60, "lambda_mult": 0.5}
    ).invoke(q)
    return {
        "kind": "compare",
        "corpus": _d2_corpus_label(ctx),
        "query": q,
        "label_a": "similarity (closest)",
        "docs_a": _briefs_marked(sim),
        "label_b": "MMR (relevance + diversity)",
        "docs_b": _briefs_marked(mmr),
    }


def d2_answer(q, ctx=None):
    from config import get_llm
    from shared.rag import format_docs_with_citations, sources_of

    vs = _d2_index(ctx)
    # Wide fetch_k so MMR grounds the answer in DISTINCT chunks, not k copies of
    # the same passage (which wastes context on a repetitive corpus).
    docs = vs.as_retriever(
        search_type="mmr", search_kwargs={"k": 4, "fetch_k": 60, "lambda_mult": 0.5}
    ).invoke(q)
    from langchain_core.messages import HumanMessage, SystemMessage

    answer = get_llm(temperature=None).invoke([
        SystemMessage("You are a research assistant. Answer the question using ONLY the numbered "
                      "context. Cite sources inline like [1], [2]. If the context is insufficient, "
                      "say so plainly."),
        HumanMessage(f"Question: {q}\n\nContext:\n{format_docs_with_citations(docs)}"),
    ]).content
    return {
        "kind": "answer",
        "corpus": _d2_corpus_label(ctx),
        "query": q,
        "answer": answer,
        "sources": sources_of(docs),
        # The exact numbered chunks the model was allowed to use — so it's clear
        # the answer is grounded in these and nothing else.
        "context": [_doc_brief(d, i + 1) for i, d in enumerate(docs)],
    }


def d2_chunking(q, ctx=None):
    from shared.rag import split_documents

    docs, _ = _d2_docs_chunks(ctx)
    variants = []
    for size, overlap in [(300, 30), (800, 120), (1500, 200)]:
        chunks = split_documents(docs, chunk_size=size, chunk_overlap=overlap)
        variants.append({"size": size, "overlap": overlap, "count": len(chunks)})
    sample = split_documents(docs, 800, 120)[0].page_content[:300]
    return {"kind": "chunks", "corpus": _d2_corpus_label(ctx), "variants": variants, "sample": sample}


def d2_topk(q, ctx=None):
    vs = _d2_index(ctx)
    # Pull a wide pool, then collapse identical chunks so the 4 shown are
    # DISTINCT content — otherwise a duplicative corpus returns the same chunk
    # k times and retrieval looks broken.
    hits = vs.similarity_search_with_score(q, k=30)
    items, collapsed = _dedup_briefs(hits, top=4, score_key="score", ndigits=4)
    return {
        "kind": "retrieved",
        "corpus": _d2_corpus_label(ctx),
        "query": q,
        "items": items,
        "collapsed": collapsed,
    }


def d2_load(q, ctx=None):
    """Step 1 · LOAD — show the raw documents as LangChain Document objects."""
    import os

    docs, _ = _d2_docs_chunks(ctx)
    items = [
        {
            "source": os.path.basename(d.metadata.get("source", "?")),
            "chars": len(d.page_content),
            "preview": d.page_content[:180].strip(),
        }
        for d in docs
    ]
    return {
        "kind": "documents",
        "corpus": _d2_corpus_label(ctx),
        "count": len(docs),
        "total_chars": sum(len(d.page_content) for d in docs),
        "items": items,
    }


def d2_embed(q, ctx=None):
    """Step 3 · EMBED — text becomes a vector; close vectors = similar meaning."""
    import numpy as np

    from config import get_embeddings, settings

    _, chunks = _d2_docs_chunks(ctx)
    emb = get_embeddings()
    vecs = np.asarray(emb.embed_documents([c.page_content for c in chunks]), dtype=float)
    qv = np.asarray(emb.embed_query(q), dtype=float)

    def cos(a, b):
        return float(a @ b / ((np.linalg.norm(a) * np.linalg.norm(b)) or 1.0))

    sims = [cos(qv, v) for v in vecs]
    # Rank ALL chunks by closeness, then collapse identical chunks so the top 5
    # are DISTINCT — a duplicative corpus otherwise shows the same chunk 5× at
    # the same cosine, and a single argmax chunk is often just the doc header.
    order = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)
    ranked = [(chunks[i], sims[i]) for i in order]
    neighbors, collapsed = _dedup_briefs(ranked, top=5, score_key="cosine", ndigits=3)
    model = {
        "fastembed": f"fastembed · {settings.fastembed_model} (local)",
        "azure": "Azure OpenAI embeddings",
        "openai": "OpenAI text-embedding-3-small",
    }.get(settings.embeddings_provider, settings.embeddings_provider)
    return {
        "kind": "embedding",
        "corpus": _d2_corpus_label(ctx),
        "model": model,
        "dim": int(vecs.shape[1]),
        "count": len(chunks),
        "query": q,
        "head": [round(float(x), 3) for x in qv[:8]],
        "neighbors": neighbors,
        "collapsed": collapsed,
        # kept for backward compatibility with any older frontend
        "nearest": {k: neighbors[0][k] for k in ("source", "cosine", "preview")},
    }


def d2_break(q, ctx=None):
    """Step 7 · BREAK IT — query with a DIFFERENT embedding model than the index.
    The vectors live in unrelated coordinate systems, so retrieval returns
    essentially random chunks — and NOTHING raises. Reuses the 'compare' shape."""
    from langchain_chroma import Chroma

    from config import FakeDeterministicEmbeddings, get_embeddings, get_vectorstore_dir, settings

    vs = _d2_index(ctx)
    healthy = vs.as_retriever(search_type="similarity", search_kwargs={"k": 4}).invoke(q)

    # A deliberately WRONG query embedder, sized to the index dim so it fails
    # silently (returns junk) rather than erroring on a dimension mismatch.
    dim = len(get_embeddings().embed_query("dimension probe"))
    collection = ctx["col"] if ctx else settings.chroma_collection
    wrong_vs = Chroma(
        collection_name=collection,
        embedding_function=FakeDeterministicEmbeddings(dim=dim),
        persist_directory=str(get_vectorstore_dir()),
    )
    broken = wrong_vs.similarity_search(q, k=4)
    return {
        "kind": "compare",
        "corpus": _d2_corpus_label(ctx),
        "query": q,
        "label_a": "✅ index & query use the SAME embedding model",
        "docs_a": _briefs_marked(healthy),
        "label_b": "💥 query embedded with a DIFFERENT model → wrong chunks (no error!)",
        "docs_b": _briefs_marked(broken),
    }


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
def d4_belt(q):
    """Inspect the tool belt AND invoke each tool with a canned sample.

    Two teaching layers in one demo (no LLM anywhere):
      1. What the model sees when we call bind_tools() — name, docstring,
         and typed args (the JSON schema pulled from the tool's Pydantic model).
      2. What each tool ACTUALLY returns for a canned input — proving these
         are ordinary Python functions your app runs, not model output.
    """
    from shared.tools import SAFE_TOOLS

    # Canned sample inputs chosen so every tool returns something visibly
    # different (course-topic query, generic web query, prose to condense).
    SAMPLES = {
        "retrieve_documents": {"query": "What is MMR retrieval?"},
        "search_docs":         {"query": "What is MMR retrieval?"},  # standalone-demo alias
        "web_search":          {"query": "vector database benchmarks"},
        "summarize": {"text": (
            "MMR re-ranks retrieved chunks to balance relevance with diversity, "
            "avoiding near-duplicate results common in plain similarity search."
        )},
    }

    tools = []
    for t in SAFE_TOOLS:
        schema = t.args_schema.schema() if getattr(t, "args_schema", None) else {}
        props = schema.get("properties", {}) or {}
        sample_args = SAMPLES.get(t.name, {})
        # Actually invoke the tool with the canned sample so learners see the
        # real output shape (retrieval chunks vs mock web bullets vs summary).
        try:
            sample_out = t.invoke(sample_args) if sample_args else "(no sample configured)"
        except Exception as e:  # noqa: BLE001
            sample_out = f"[error running sample: {e}]"
        sample_out = str(sample_out)
        if len(sample_out) > 480:
            sample_out = sample_out[:480] + " …"
        tools.append({
            "name": t.name,
            "description": (t.description or "").strip(),
            "args": [{"name": k, "type": v.get("type", "?")} for k, v in props.items()],
            "sample_input": sample_args,
            "sample_output": sample_out,
        })
    return {"kind": "tool_belt", "tools": tools}


def d4_agent(q):
    """Run the tool-calling agent and return a rich per-turn transcript.

    Each turn either (a) the model calls one or more tools, in which case we
    show the raw tool_call JSON + the tool result, or (b) the model produces
    a final answer, in which case we stop. This mirrors the loop taught in
    `day4/demos/demo_02_bind_and_route.py`.

    We hardcode a MULTI-TOOL question so learners actually see the loop pick
    different tools across turns (not just retrieve_documents twice). If the
    user typed their own question we honour it; otherwise the demo shows off
    tool-diversity by design.
    """
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    from config import get_llm
    from shared.tools import SAFE_TOOLS

    # Distinct, purpose-built question: forces the model to (1) retrieve from
    # local docs about agent memory, (2) run a web_search for a live fact
    # about vector-DB news, (3) optionally summarize before answering. Three
    # different tools on three different turns — the exact opposite of the
    # "retrieve twice then answer" pattern the MMR default used to produce.
    question = (q or "").strip() or (
        "Look up in our local course docs what long-term agent memory is, "
        "then search the web for the latest news about vector databases in "
        "2025, and give me a 2-sentence combined answer with citations."
    )

    tools_by_name = {t.name: t for t in SAFE_TOOLS}
    llm = get_llm(0).bind_tools(SAFE_TOOLS)
    msgs = [
        SystemMessage(content=(
            "You are a research assistant. Use retrieve_documents for course topics "
            "(RAG, LangGraph, vector DBs, prompting, memory), web_search only for "
            "facts NOT in the local docs, and summarize to condense text. Answer "
            "concisely with citations when available."
        )),
        HumanMessage(content=question),
    ]

    turns: list[dict] = []
    tool_calls: list[dict] = []          # kept for the "kind: tools" panel
    final = ""

    MAX_TURNS = 4
    for turn_no in range(1, MAX_TURNS + 1):
        ai = llm.invoke(msgs)
        msgs.append(ai)

        turn = {
            "turn": turn_no,
            "thought": (ai.content or "").strip(),
            "calls": [],
        }

        if not ai.tool_calls:
            # Final answer — no more tool calls to run.
            final = ai.content or ""
            turn["is_final"] = True
            turns.append(turn)
            break

        # Otherwise run every requested tool and record what came back.
        for tc in ai.tool_calls:
            record = {"name": tc["name"], "args": tc["args"]}
            tool_calls.append(record)
            try:
                out = tools_by_name[tc["name"]].invoke(tc["args"])
            except Exception as e:  # ToolNode's belt-and-braces behaviour
                out = f"TOOL_ERROR: {e}"
            preview = str(out)
            if len(preview) > 400:
                preview = preview[:400] + " …"
            turn["calls"].append({**record, "result": preview})
            msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
        turns.append(turn)
    else:
        # Hit MAX_TURNS without a final answer — surface it clearly.
        final = msgs[-1].content if hasattr(msgs[-1], "content") else ""

    return {
        "kind": "tools",
        "question": question,
        "turns": turns,
        "tool_calls": tool_calls,   # back-compat: existing renderer still works
        "final": final,
    }


def d4_resilience(q):
    """Three-stage story: crash → return-as-string → retry-recovers.

    Stage 1: call the flaky tool with NO safety net → catch the crash so the
             UI can show what "unhandled" actually looks like.
    Stage 2: same call wrapped so the exception becomes a readable string
             (this is the pattern real tools use — see web_search).
    Stage 3: bare retry loop — the agent tries again and (because the fake
             service fails every OTHER call) recovers on attempt 2.
    """
    from shared.tools import reset_flaky_tool, unreliable_metric

    # Stage 1 · unhandled crash ------------------------------------------------
    reset_flaky_tool()
    stage1 = {"label": "no try/except → the exception escapes"}
    try:
        stage1["result"] = unreliable_metric.invoke({"topic": "RAG"})
        stage1["ok"] = True
    except Exception as e:
        stage1["error"] = f"{type(e).__name__}: {e}"
        stage1["ok"] = False

    # Stage 2 · error returned as string --------------------------------------
    reset_flaky_tool()
    stage2 = {"label": "try/except returns 'SEARCH_FAILED: …' — agent can react"}
    try:
        stage2["result"] = unreliable_metric.invoke({"topic": "RAG"})
        stage2["ok"] = True
    except Exception as e:
        stage2["result"] = f"TOOL_FAILED: {e}"
        stage2["ok"] = False

    # Stage 3 · retry loop recovers -------------------------------------------
    reset_flaky_tool()
    retry = []
    for i in range(1, 4):
        try:
            val = unreliable_metric.invoke({"topic": "RAG"})
            retry.append({"attempt": i, "outcome": "recovered", "detail": val})
            break
        except Exception as e:
            retry.append({"attempt": i, "outcome": "failed", "detail": str(e)})

    return {
        "kind": "resilience",
        "stage1": stage1,
        "stage2": stage2,
        "retry": retry,
        # legacy fields the old renderer still reads:
        "crash": stage1.get("error"),
    }


def d4_routing(q):
    """Three questions, three expected tool picks — show how docstrings steer selection.

    For each case we also record the args the model produced (so the room can
    see how the model rewrites the user's phrasing into a clean tool argument).
    """
    from config import get_llm
    from shared.tools import SAFE_TOOLS

    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_llm(0).bind_tools(SAFE_TOOLS)
    system = SystemMessage(content=(
        "You have tools: retrieve_documents (local course knowledge base), web_search "
        "(current events / live facts), summarize (condense text you already have). "
        "Call the most appropriate tool for the request, or answer directly if none apply."
    ))
    cases_in = [
        {
            "question": "What is MMR in the course's retrieval material?",
            "expected": "retrieve_documents",
            "reason": "The phrase 'course's retrieval material' matches the local knowledge-base tool's docstring.",
        },
        {
            "question": "What is the very latest news on AI regulation this week?",
            "expected": "web_search",
            "reason": "'Latest news / this week' is time-sensitive → the docstring for web_search says use it for current facts.",
        },
        {
            "question": "Summarize this: RAG loads, chunks, embeds, stores, retrieves, and answers with citations.",
            "expected": "summarize",
            "reason": "The user already provided the text and asked to shorten it — summarize is the only tool that operates on given text.",
        },
    ]
    cases = []
    for c in cases_in:
        ai = llm.invoke([system, HumanMessage(content=c["question"])])
        picks = [{"name": tc["name"], "args": tc["args"]} for tc in ai.tool_calls] or []
        picked_names = [p["name"] for p in picks] or ["(answered directly)"]
        cases.append({
            **c,
            "tools": picked_names,             # back-compat for the old renderer
            "picks": picks,                    # new: name + args
            "match": bool(picks) and picks[0]["name"] == c["expected"],
        })
    return {"kind": "routing", "cases": cases}


def d4_vague_vs_specific(q):
    """Prompt-engineered tool descriptions: SAME implementation, opposite picks.

    Trick: on the vague side we deliberately give the calc tool a MISLEADING
    NAME (`notes`) and a totally vague docstring, so a smart model has no
    signal that this tool can do arithmetic. On the specific side the same
    function is named `calculator` with a rich, worked-example docstring.

    The system prompt intentionally does NOT hint at math, so the model has to
    infer tool purpose entirely from name + docstring — which is exactly the
    scenario a fresher will face in the real world.
    """
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import tool as tool_dec
    from pydantic import BaseModel, Field

    from config import get_llm
    from shared.tools import SAFE_TOOLS  # search_docs, web_search, summarize

    def _safe_eval(expression: str) -> str:
        allowed = set("0123456789+-*/(). %")
        if not expression or any(ch not in allowed for ch in expression):
            return f"CALC_REJECTED: {expression!r}"
        try:
            return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307
        except Exception as e:  # noqa: BLE001
            return f"CALC_FAILED: {e}"

    # ── VAGUE side: misleading name + vague description ──────────────────
    # `notes` sounds like it stores/reads notes, not arithmetic. The docstring
    # is a single generic sentence with no examples, no allowed operators, no
    # boundary rules. A smart model will USUALLY skip this tool and answer the
    # math directly from its own knowledge — a real teaching-visible outcome.
    class VagueArgs(BaseModel):
        input: str = Field(description="The input value.")

    @tool_dec(args_schema=VagueArgs)
    def notes(input: str) -> str:  # noqa: A002 — matches the vague schema
        """Utility helper."""
        return _safe_eval(input)

    # ── SPECIFIC side: aligned name + rich, example-driven description ───
    class CalcArgs(BaseModel):
        expression: str = Field(
            description="A Python arithmetic expression, e.g. '(3+4)*2' or '240*0.125'."
        )

    @tool_dec(args_schema=CalcArgs)
    def calculator(expression: str) -> str:
        """Evaluate a numeric arithmetic expression written in Python syntax.

        Allowed: digits, decimals, and the operators + - * / % ** and parentheses.
        Use this for ANY user question that reduces to a number, e.g.
            "12.5% of 240"      → 240*0.125
            "area of r=2 circle" → 3.14159*2**2
            "1024 / 8"           → 1024/8
        Pass ONLY the arithmetic expression string — never the word problem.
        Do NOT use for text summarisation or document lookup.
        """
        return _safe_eval(expression)

    question = "What is 12.5% of 240?"
    # NOTE: system prompt intentionally does NOT say "use the calculator" — the
    # model has to infer tool purpose from the docstring alone.
    system = SystemMessage(content=(
        "You are a helpful assistant. You have several tools available; look at "
        "each tool's name and description and use whichever fits the user request. "
        "If no tool fits, answer directly."
    ))

    def _run(extra_tool, label: str):
        tools = list(SAFE_TOOLS) + [extra_tool]
        by_name = {t.name: t for t in tools}
        llm = get_llm(0).bind_tools(tools)
        msgs = [system, HumanMessage(content=question)]
        picks: list[dict] = []
        for _ in range(3):
            ai = llm.invoke(msgs)
            msgs.append(ai)
            if not ai.tool_calls:
                break
            for tc in ai.tool_calls:
                picks.append({"name": tc["name"], "args": tc["args"]})
                try:
                    out = by_name[tc["name"]].invoke(tc["args"])
                except Exception as e:  # noqa: BLE001
                    out = f"TOOL_ERROR: {e}"
                msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
        final = (msgs[-1].content if hasattr(msgs[-1], "content") else "").strip()
        # Classify what happened for the UI's "outcome" pill.
        calc_names = {"notes", "calculator"}
        used_calc = any(p["name"] in calc_names for p in picks)
        used_other = any(p["name"] not in calc_names for p in picks)
        if used_calc:
            outcome = "calc-used"
        elif used_other:
            outcome = "wrong-tool"
        else:
            outcome = "no-tool"
        return {"label": label, "picks": picks, "final": final, "outcome": outcome}

    return {
        "kind": "vague_vs_specific",
        "question": question,
        "vague": {
            "tool_name": notes.name,
            "docstring": (notes.description or "").strip(),
            **_run(notes, "misleading name + vague description"),
        },
        "specific": {
            "tool_name": calculator.name,
            "docstring": (calculator.description or "").strip(),
            **_run(calculator, "aligned name + rich description with examples"),
        },
    }


def d4_backoff(q):
    """Retry-with-backoff timeline — no LLM. Mirrors demo_05_retry_backoff.py.

    Two callables:
      • flaky_recovers  — fails on attempts 1 and 2, succeeds on 3.
      • always_broken   — never succeeds; wrapper returns RETRY_EXHAUSTED string.
    Each attempt records: attempt#, delay (seconds actually slept),
    cumulative time, outcome (failed/recovered/exhausted), detail.
    """
    def _retry(fn, *, retries=5, initial_delay=0.1, factor=2.0):
        """Exponential-backoff wrapper. We don't ACTUALLY sleep (this is a demo
        that has to feel snappy in the browser) — we compute what the delay
        WOULD have been so the timeline chart can render honest widths."""
        attempts = []
        delay = 0.0                # first attempt has no wait in front of it
        cum = 0.0
        next_delay = initial_delay
        last: Exception | None = None
        for i in range(1, retries + 1):
            try:
                val = fn()
                cum += delay
                attempts.append({
                    "attempt": i, "delay": round(delay, 3), "cum": round(cum, 3),
                    "outcome": "recovered", "detail": val,
                })
                return {"attempts": attempts, "result": val, "exhausted": False, "total": round(cum, 3)}
            except Exception as e:  # noqa: BLE001
                last = e
                cum += delay
                attempts.append({
                    "attempt": i, "delay": round(delay, 3), "cum": round(cum, 3),
                    "outcome": "failed", "detail": str(e),
                })
                delay = next_delay
                next_delay *= factor
        # Exhausted — record a synthetic terminal row so the UI can show the give-up marker.
        attempts.append({
            "attempt": None, "delay": None, "cum": round(cum, 3),
            "outcome": "exhausted", "detail": f"RETRY_EXHAUSTED: {last}",
        })
        return {"attempts": attempts, "result": f"RETRY_EXHAUSTED: {last}", "exhausted": True, "total": round(cum, 3)}

    calls_a = {"n": 0}
    def flaky_recovers():
        calls_a["n"] += 1
        if calls_a["n"] < 3:
            raise RuntimeError(f"transient error on call #{calls_a['n']}")
        return "OK: metric=87"

    def always_broken():
        raise RuntimeError("upstream is down for maintenance")

    return {
        "kind": "backoff",
        "recovers": _retry(flaky_recovers, retries=5, initial_delay=0.1, factor=2.0),
        "exhausts": _retry(always_broken, retries=4, initial_delay=0.1, factor=2.0),
    }


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
# DAY 3 — LANGGRAPH MODULES (12 sub-tabs, imported from langgraph_demos.py)
# ═══════════════════════════════════════════════════════════════════════════
# Modules 3, 5, 6, 10 accept an optional question (they call the LLM). The rest
# ignore it. We wrap uniformly so `run()` can always pass `q` without checking.
try:
    from backend import langgraph_demos as _lg_demos  # normal import
except ImportError:  # when launched as `python backend/app.py`
    import langgraph_demos as _lg_demos  # type: ignore


import inspect as _inspect


def _wrap_lg(fn):
    accepts_q = "question" in _inspect.signature(fn).parameters

    def _run(q=""):
        return fn(q) if accepts_q else fn()

    return _run


_LG_MODULES_D3 = {name: _wrap_lg(fn) for name, fn in _lg_demos.MODULES.items()}


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
    2: {
        "load": d2_load,
        "chunking": d2_chunking,
        "embed": d2_embed,
        "topk": d2_topk,
        "compare": d2_compare,
        "answer": d2_answer,
        "break": d2_break,
    },
    3: {
        # 12 LangGraph "modules" — one per sub-tab
        **_LG_MODULES_D3,
        # legacy short demos (kept for backwards compatibility / quick runs)
        "full": d3_full,
        "plan_only": d3_plan_only,
        "one_step": d3_one_step,
    },
    4: {
        "belt": d4_belt,
        "agent": d4_agent,
        "routing": d4_routing,
        "vague_vs_specific": d4_vague_vs_specific,
        "resilience": d4_resilience,
        "backoff": d4_backoff,
    },
    5: {"short": d5_short, "long": d5_long, "compaction": d5_compaction},
    6: {"multi": d6_multi, "resume": d6_resume},
    7: {"full": d7_full, "reflection": d7_reflection, "hitl": d7_hitl},
}


def run(day: int, demo: str = "", question: str = "", session: str = "") -> dict:
    reg = REGISTRY.get(day)
    if not reg:
        return {"error": f"Unknown day {day}"}
    fn = reg.get(demo) or next(iter(reg.values()))  # default = first demo
    q = (question or "").strip() or DEFAULT_QUESTIONS.get(day, "")
    try:
        # Day 2 demos are session-aware: if the browser uploaded a corpus, run
        # every stage against THAT index; otherwise fall back to built-in data/.
        if day == 2:
            try:
                from backend import day2_sessions
            except ImportError:  # when launched as `python backend/app.py`
                import day2_sessions
            return fn(q, day2_sessions.resolve(session))
        return fn(q)
    except Exception as e:  # never leak a stack trace to the UI
        return {"kind": "error", "error": f"{type(e).__name__}: {e}"}
