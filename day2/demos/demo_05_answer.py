"""
LIVE DEMO — Step 5: AUGMENT + GENERATE — a grounded answer with citations.

Goal on screen: there is no magic between "retrieved chunks" and "answer".
The chunks are pasted into the prompt as numbered context — you will see the
EXACT final prompt — and the model is instructed to answer ONLY from it and to
cite [1] [2]. Every citation badge in the answer links back to a chunk card
below, which names the source file and character position. Fully traceable.

What to do live:
  1. Ask a question, keep MMR, click Generate.
  2. Scroll the exact prompt — "THIS is 'augmented' in RAG. Copy-paste. That's it."
  3. Read the answer; point at a [2] badge, then at citation card [2] below:
     same color, same text, source file + char offset. The audit trail.
  4. Ask something the docs don't cover ("who won the world cup?") —
     the model says the context doesn't contain it. Grounding = permission to
     say "I don't know".

Run standalone:  streamlit run day2/demos/demo_05_answer.py
"""

from __future__ import annotations

import html
import re

import streamlit as st

import rag_demo_common as rc
from config import get_llm, settings

rc.page_setup(
    "💬",
    "Step 5 · Augment + Generate — answer with citations",
    ["Augment", "Generate"],
    "Augment = paste the retrieved chunks into the prompt as numbered context. "
    "Generate = the LLM answers ONLY from that context, citing [1] [2].",
)

ss = st.session_state
rc.ensure_store()

# ─────────────────────────────────────────────────────────────────────────────
# Ask
# ─────────────────────────────────────────────────────────────────────────────
preset = st.pills("Try one of these", rc.SAMPLE_QUESTIONS, selection_mode="single", key="p5")
query = st.text_input("Your question", value=preset or ss.get("last_query") or rc.SAMPLE_QUESTIONS[1])
c1, c2 = st.columns(2)
k = c1.slider("top-k chunks of context", 2, 8, rc.DEFAULT_K)
strategy = c2.radio("Retrieval strategy", ["mmr", "similarity"], horizontal=True,
                    help="MMR from step 4 — diverse context usually answers better.")

if settings.llm_provider == "mock":
    st.warning("`LLM_PROVIDER=mock` — retrieval below is fully real, but the final answer "
               "will be a canned offline response. Set the provider to azure/openai for a live answer.")

go = st.button("🪄 Retrieve → build prompt → generate", type="primary")
if not go and "answer_payload" not in ss:
    st.info("👆 Ask, then click the button — the page will show every intermediate artifact.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# 1) RETRIEVE (same machinery as step 4)
# ─────────────────────────────────────────────────────────────────────────────
if go:
    ss.last_query = query.strip()
    retriever = ss.store.as_retriever(
        search_type=strategy,
        search_kwargs={"k": k, "fetch_k": max(4 * k, 20)} if strategy == "mmr" else {"k": k},
    )
    docs = retriever.invoke(ss.last_query)

    # 2) AUGMENT — the same formatting function the lab uses (shared/rag.py)
    from shared.rag import format_docs_with_citations

    context = format_docs_with_citations(docs)
    system_msg = ("You are a research assistant. Answer the question using ONLY the numbered "
                  "context. Cite sources inline like [1], [2]. If the context is insufficient, "
                  "say so plainly.")
    human_msg = f"Question: {ss.last_query}\n\nContext:\n{context}"

    # 3) GENERATE — temperature=None so gpt-5-class deployments use their default
    with st.spinner("Calling the LLM with the augmented prompt…"):
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            answer = get_llm(temperature=None).invoke(
                [SystemMessage(system_msg), HumanMessage(human_msg)]
            ).content
        except Exception as exc:
            st.error(f"LLM call failed: {exc}\n\nRetrieval above still worked — "
                     "check .env (or set LLM_PROVIDER=mock for offline).")
            st.stop()
    ss.answer_payload = {"query": ss.last_query, "docs": docs, "system": system_msg,
                         "human": human_msg, "answer": answer, "strategy": strategy, "k": k}

p = ss.answer_payload
docs, answer = p["docs"], p["answer"]

rc.show_code("the code behind this step", f"""
retriever = vectorstore.as_retriever(search_type="{p['strategy']}", search_kwargs={{"k": {p['k']}}})
docs = retriever.invoke(question)

context = format_docs_with_citations(docs)     # "[1] (source: ...)\\n<chunk text>" blocks
answer = llm.invoke([
    SystemMessage("Answer using ONLY the numbered context. Cite like [1], [2]. "
                  "If the context is insufficient, say so."),
    HumanMessage(f"Question: {{question}}\\n\\nContext:\\n{{context}}"),
]).content
""")

# ─────────────────────────────────────────────────────────────────────────────
# Every artifact on screen, in pipeline order
# ─────────────────────────────────────────────────────────────────────────────
st.subheader(f"① Retrieved context — top-{p['k']} by {p['strategy']} for “{p['query']}”")
for rank, d in enumerate(docs, 1):
    st.markdown(
        rc.chunk_card(rank, d, rc.highlight_terms(d.page_content[:300], p["query"]) + "…",
                      rc.chunk_color(rank - 1)),
        unsafe_allow_html=True,
    )

st.subheader("② The EXACT prompt sent to the model (the “augment” step)")
chars = len(p["human"]) + len(p["system"])
st.caption(f"{chars:,} characters (≈{chars // 4:,} tokens). This is all the model gets — "
           "it cannot see the files, the database, or the internet.")
with st.expander("show the full prompt", expanded=False):
    st.code(f"SYSTEM:\n{p['system']}\n\nHUMAN:\n{p['human']}", language="text")

st.subheader("③ The grounded answer")
# Turn every [n] into a colored badge matching chunk card #n above.
answer_html = html.escape(answer)
answer_html = re.sub(
    r"\[(\d+)\]",
    lambda m: (f'<span class="cite" style="background:{rc.chunk_color(int(m.group(1)) - 1)}">'
               f"{m.group(1)}</span>"),
    answer_html,
)
st.markdown(f'<div class="card" style="border-left-color:{rc.BOTH_COLOR};font-size:1.08rem">'
            f"{answer_html}</div>", unsafe_allow_html=True)

st.subheader("④ Citations — every badge traces to an exact chunk")
cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if int(n) <= len(docs)})
if not cited:
    st.caption("The answer contains no [n] citations — likely the context was insufficient "
               "(which is the honest behavior we asked for).")
for n in cited:
    d = docs[n - 1]
    st.markdown(
        f'<div class="card" style="border-left-color:{rc.chunk_color(n - 1)}">'
        f'<div class="meta"><span class="cite" style="background:{rc.chunk_color(n - 1)}">{n}</span>'
        f' 📄 <b>{html.escape(d.metadata["source"])}</b> · chunk {d.metadata["chunk_id"]} · '
        f'starts at character {d.metadata.get("start_index", "?")}</div>'
        f"{html.escape(d.page_content[:260])}…</div>",
        unsafe_allow_html=True,
    )

st.success("**Takeaway:** RAG = retrieval + a prompt template. The answer is only as good as "
           "the chunks in step ① — which is why chunking and retrieval strategy (steps 2–4) "
           "matter more than the model. → Next: **6 · Break it** — let's prove that.")
