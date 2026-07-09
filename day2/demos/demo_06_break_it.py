"""
LIVE DEMO — Step 6: BREAK IT ON PURPOSE.

Goal on screen: the three classic silent RAG killers, each shown as
HEALTHY (lab defaults) vs BROKEN — same question, same corpus, same k:

  🤏 chunks too small   -> fragments: great scores, no usable context
  🐘 chunks too huge    -> dilution: the answer is buried in noise
  🔀 embedding mismatch -> query and index in different coordinate systems:
                           retrieval returns near-random chunks, and NOTHING errors

What to do live: pick a scenario, read the two columns, then (with a real LLM
configured) click "Generate both answers" for the final gut-punch: the broken
pipeline produces a confident-sounding but empty or wrong answer.

Run standalone:  streamlit run day2/demos/demo_06_break_it.py
"""

from __future__ import annotations

import html
import pathlib

import streamlit as st

import rag_demo_common as rc
from config import get_llm, settings

rc.page_setup(
    "💥",
    "Step 6 · Break it — why the knobs matter",
    ["Split", "Embed", "Embed query", "Retrieve"],
    "RAG failures are usually SILENT: no exception, just quietly bad answers. "
    "Here we cause all three classics on purpose.",
)

ss = st.session_state
healthy_store = rc.ensure_store()
HEALTHY = f"size {rc.DEFAULT_CHUNK_SIZE} · overlap {rc.DEFAULT_CHUNK_OVERLAP} · one model for index & query"

SCENARIOS = {
    "🤏 Chunks too small (size 120, overlap 0)": "small",
    "🐘 Chunks too huge (size 3500, overlap 0)": "huge",
    "🔀 Different embedding model for query vs index": "mismatch",
}
label = st.radio("Choose your sabotage", list(SCENARIOS), horizontal=True)
mode = SCENARIOS[label]

preset = st.pills("Question", rc.SAMPLE_QUESTIONS, selection_mode="single", key="p6")
query = st.text_input("Your question", value=preset or ss.get("last_query") or rc.SAMPLE_QUESTIONS[0])
if not query.strip():
    st.stop()
ss.last_query = query.strip()
query = ss.last_query
k = rc.DEFAULT_K


# ─────────────────────────────────────────────────────────────────────────────
# Build the broken pipeline (cached per scenario so switching back is instant)
# ─────────────────────────────────────────────────────────────────────────────
def build_broken_index(chunk_size: int, chunk_overlap: int):
    """A fresh mini-pipeline with bad chunking: split -> embed -> in-memory Chroma.
    Identical code to the healthy pipeline — ONLY the numbers differ."""
    from langchain_chroma import Chroma
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                              chunk_overlap=chunk_overlap, add_start_index=True)
    chunks = splitter.split_documents(rc.ensure_docs())
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = i
        c.metadata["source"] = pathlib.Path(str(c.metadata.get("source", "?"))).name
    vectors = rc.embed_texts(tuple(c.page_content for c in chunks), "course")

    client = rc.chroma_client()  # shared in-memory client, separate collection
    try:
        client.delete_collection("day2_broken")
    except Exception:
        pass
    col = client.create_collection("day2_broken", metadata={"hnsw:space": "cosine"})
    col.add(ids=[str(i) for i in range(len(chunks))],
            documents=[c.page_content for c in chunks],
            metadatas=[c.metadata for c in chunks],
            embeddings=vectors.tolist())
    emb, _ = rc.get_embedder("course")
    return chunks, Chroma(client=client, collection_name="day2_broken", embedding_function=emb)


cache = ss.setdefault("broken_cache", {})
cache_key = f"{mode}|{ss.get('store_fp')}"

if mode in ("small", "huge"):
    size, overlap = (120, 0) if mode == "small" else (3500, 0)
    if cache_key not in cache:
        with st.spinner(f"Building the broken index (chunk_size={size})…"):
            cache[cache_key] = build_broken_index(size, overlap)
    broken_chunks, broken_store = cache[cache_key]
    broken_desc = f"size {size} · overlap {overlap} · same embedding model"
    broken_hits = broken_store.similarity_search_with_score(query, k=k)
    rc.show_code("the ONLY thing we changed", f"""
splitter = RecursiveCharacterTextSplitter(
    chunk_size={size},      # ← was {rc.DEFAULT_CHUNK_SIZE}
    chunk_overlap={overlap},        # ← was {rc.DEFAULT_CHUNK_OVERLAP}
)
# everything else — docs, embedding model, Chroma, k={k} — is identical
""")
else:
    # THE MISMATCH: same collection, but the query embedder is a different model.
    # This is exactly the real-world bug: index built with model A, query code
    # wired to model B. Note that NOTHING raises — the vectors just don't align.
    from langchain_chroma import Chroma

    wrong_emb, wrong_label = rc.get_embedder("hashing")
    broken_desc = f"index: {ss.embed_label} · query: {wrong_label}"
    broken_view = Chroma(client=ss.store_client, collection_name="day2_demo",
                         embedding_function=wrong_emb)  # ← the bug, in one line
    try:
        broken_hits = broken_view.similarity_search_with_score(query, k=k)
        mismatch_error = None
    except Exception as exc:
        broken_hits, mismatch_error = [], exc
    rc.show_code("the ONLY thing we changed", f"""
index_embeddings = get_embeddings()                  # {ss.embed_label}
query_embeddings = SomeOtherEmbeddingModel()         # {wrong_label}

vectorstore = Chroma(..., embedding_function=query_embeddings)  # ← the bug
docs = vectorstore.similarity_search(question, k={k})
# vectors from different models live in UNRELATED coordinate systems:
# "nearest" neighbors of the query are now essentially random chunks.
""")

healthy_hits = healthy_store.similarity_search_with_score(query, k=k)

# ─────────────────────────────────────────────────────────────────────────────
# Side by side: healthy vs broken
# ─────────────────────────────────────────────────────────────────────────────
def render_hits(hits, border: str, note_len: bool = False):
    for rank, (doc, dist) in enumerate(hits, 1):
        n = len(doc.page_content)
        extra = f" · <b>{n:,} chars</b>" if note_len else ""
        st.markdown(
            rc.chunk_card(rank, doc,
                          rc.highlight_terms(doc.page_content[:300], query)
                          + ("…" if n > 300 else ""),
                          border, score_txt=f"similarity **{1 - dist:.3f}**{extra}"),
            unsafe_allow_html=True,
        )


left, right = st.columns(2, gap="medium")
with left:
    st.markdown(f'<h3 style="color:{rc.BOTH_COLOR}">✅ Healthy pipeline</h3>', unsafe_allow_html=True)
    st.caption(HEALTHY)
    render_hits(healthy_hits, rc.BOTH_COLOR)

with right:
    st.markdown('<h3 style="color:#C62828">💥 Broken pipeline</h3>', unsafe_allow_html=True)
    st.caption(broken_desc)
    if mode == "mismatch" and mismatch_error:
        st.error(f"Chroma refused the query outright: **{mismatch_error}**\n\n"
                 "You got lucky — the two models have different vector dimensions, so the bug "
                 "is at least LOUD. With same-dimension models (like here when both are 384-d) "
                 "it fails silently instead.")
    else:
        render_hits(broken_hits, "#C62828", note_len=(mode == "huge"))

# The verdict to read out loud
if mode == "small":
    avg = int(sum(len(d.page_content) for d, _ in broken_hits) / max(len(broken_hits), 1))
    st.error(f"**What broke:** every retrieved chunk is a ~{avg}-char fragment. Scores can look "
             "GREAT (short focused text matches easily) — but no chunk carries a complete thought, "
             "so the model has nothing solid to answer from. **Fragments retrieve well and answer badly.**")
elif mode == "huge":
    avg = int(sum(len(d.page_content) for d, _ in broken_hits) / max(len(broken_hits), 1))
    st.error(f"**What broke:** each retrieved chunk is ~{avg:,} chars — nearly a whole document. "
             "Similarity drops (one vector now 'means' ten topics at once) and the context window "
             "fills with mostly-irrelevant text the model must dig through. **Dilution.**")
else:
    st.error("**What broke:** the query was embedded into a DIFFERENT coordinate system than the "
             "index. Compare the similarity scores and sources with the healthy column — the picks "
             "are essentially random, and **no exception was raised anywhere**. This is why you "
             "always re-index after switching embedding models.")

# ─────────────────────────────────────────────────────────────────────────────
# Optional finale: let the LLM answer from both contexts
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
if st.button("🎤 Generate BOTH answers with the LLM (the gut-punch)",
             disabled=(mode == "mismatch" and mismatch_error is not None)):
    from langchain_core.messages import HumanMessage, SystemMessage
    from shared.rag import format_docs_with_citations

    if settings.llm_provider == "mock":
        st.warning("`LLM_PROVIDER=mock` — both answers will be canned; the contrast needs a real model.")

    def grounded_answer(docs) -> str:
        return get_llm(temperature=None).invoke([
            SystemMessage("You are a research assistant. Answer the question using ONLY the "
                          "numbered context. Cite sources inline like [1], [2]. If the context "
                          "is insufficient, say so plainly."),
            HumanMessage(f"Question: {query}\n\nContext:\n{format_docs_with_citations(docs)}"),
        ]).content

    a, b = st.columns(2, gap="medium")
    try:
        with a, st.spinner("Healthy answer…"):
            st.markdown(f'<div class="card" style="border-left-color:{rc.BOTH_COLOR}">'
                        f'<div class="meta">✅ answer from the healthy context</div>'
                        f"{html.escape(grounded_answer([d for d, _ in healthy_hits]))}</div>",
                        unsafe_allow_html=True)
        with b, st.spinner("Broken answer…"):
            st.markdown(f'<div class="card" style="border-left-color:#C62828">'
                        f'<div class="meta">💥 answer from the broken context</div>'
                        f"{html.escape(grounded_answer([d for d, _ in broken_hits]))}</div>",
                        unsafe_allow_html=True)
    except Exception as exc:
        st.error(f"LLM call failed: {exc} — check .env, or demo the retrieval columns alone.")

st.success("**Takeaway:** when RAG misbehaves, read the retrieved chunks BEFORE blaming the model. "
           "Chunking and embedding consistency decide answer quality — and their failures are silent. "
           "That's the whole reason steps 2–4 of this pipeline get their own demos.")
