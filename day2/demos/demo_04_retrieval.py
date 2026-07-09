"""
LIVE DEMO — Step 4: EMBED THE QUERY + RETRIEVE — similarity vs MMR, side by side.

Goal on screen: the SAME question answered by two retrieval strategies with the
same top-k budget. Similarity happily spends the budget on near-duplicate
chunks (the sample docs repeat ideas on purpose — like every real corpus).
MMR spends it on relevant AND diverse chunks. Red flags mark the duplicates.

What to do live:
  1. Ask "What chunk size should I use for RAG?" with k=4.
  2. LEFT column: two red 'near-duplicate' flags — the same advice retrieved
     twice. Budget wasted.
  3. RIGHT column: MMR picks the advice ONCE, then adds different aspects.
  4. Show the document map — WHERE each strategy landed in the corpus.
  5. Drag MMR's λ to 1.0 (→ becomes similarity) and to 0.0 (→ diversity chaos).

Run standalone:  streamlit run day2/demos/demo_04_retrieval.py
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import rag_demo_common as rc

rc.page_setup(
    "🔍",
    "Step 4 · Retrieve — similarity vs MMR (same k, same question)",
    ["Embed query", "Retrieve"],
    "Similarity = the k closest chunks. MMR = close AND different from each other. "
    "Same budget, different information coverage.",
)

ss = st.session_state
chunks = rc.ensure_chunks()
vectors = rc.ensure_vectors()
store = rc.ensure_store()

# ─────────────────────────────────────────────────────────────────────────────
# Ask a question
# ─────────────────────────────────────────────────────────────────────────────
preset = st.pills("Try one of these", rc.SAMPLE_QUESTIONS, selection_mode="single")
query = st.text_input("Your question", value=preset or ss.get("last_query") or rc.SAMPLE_QUESTIONS[0])
c1, c2 = st.columns(2)
k = c1.slider("top-k (chunks each strategy may return)", 2, 8, rc.DEFAULT_K)
lam = c2.slider("MMR λ — 1.0 = pure relevance · 0.0 = pure diversity", 0.0, 1.0, 0.5, 0.05)
fetch_k = max(4 * k, 20)

if not query.strip():
    st.stop()
ss.last_query = query.strip()
query = ss.last_query

# ── Step 5 of the pipeline, made visible: the query becomes a vector too ─────
qvec = rc.embed_query_vec(query)
st.markdown(
    f'<div class="card" style="border-left-color:#D32F2F">'
    f'<div class="meta">the query, embedded with the <b>same model</b> as the chunks '
    f'({ss.embed_label})</div>'
    f"“{rc.highlight_terms(query, query)}” → "
    f"<code>[{', '.join(f'{v:+.2f}' for v in qvec[:6])}, … {len(qvec) - 6} more]</code></div>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# THE two retrievals — this is the real LangChain API, nothing hidden
# ─────────────────────────────────────────────────────────────────────────────
sim_hits = store.similarity_search_with_score(query, k=k)               # (doc, cosine distance)
mmr_docs = store.max_marginal_relevance_search(query, k=k, fetch_k=fetch_k, lambda_mult=lam)

rc.show_code("the code behind this step", f"""
# similarity: the {k} chunks whose vectors are closest to the query vector
hits = vectorstore.similarity_search_with_score(question, k={k})

# MMR: fetch a wide pool ({fetch_k}), then pick {k} that are relevant AND unlike each other
docs = vectorstore.max_marginal_relevance_search(
    question, k={k}, fetch_k={fetch_k}, lambda_mult={lam})

# in the lab you'll wrap the same thing as a retriever:
retriever = vectorstore.as_retriever(search_type="mmr",
                                     search_kwargs={{"k": {k}, "fetch_k": {fetch_k}}})
""")

def vec_of(doc) -> np.ndarray:
    return vectors[doc.metadata["chunk_id"]]

# Near-duplicate detection inside the similarity results: cosine ≥ 0.90 to an
# earlier-ranked pick = the budget was spent on the same information twice.
def dup_flags(docs) -> list[str]:
    flags = [""] * len(docs)
    for i in range(len(docs)):
        for j in range(i):
            sim = rc.cosine_sim(vec_of(docs[i]), vec_of(docs[j]))
            if sim >= 0.90:
                flags[i] = (f'<span class="dupflag">⚠ near-duplicate of #{j + 1} '
                            f'(cosine {sim:.2f})</span>')
                break
    return flags

sim_docs = [d for d, _ in sim_hits]
sim_flags, mmr_flags = dup_flags(sim_docs), dup_flags(mmr_docs)

# ─────────────────────────────────────────────────────────────────────────────
# Side-by-side results
# ─────────────────────────────────────────────────────────────────────────────
left, right = st.columns(2, gap="medium")

with left:
    st.markdown(f'<h3 style="color:{rc.SIM_COLOR}">🎯 Similarity search</h3>', unsafe_allow_html=True)
    st.caption("“Give me the k closest chunks.” Ruthlessly relevant — and happily redundant.")
    for rank, ((doc, dist), flag) in enumerate(zip(sim_hits, sim_flags), 1):
        st.markdown(
            rc.chunk_card(rank, doc, rc.highlight_terms(doc.page_content[:340], query) + "…",
                          rc.SIM_COLOR, extra_badge=flag,
                          score_txt=f"similarity **{1 - dist:.3f}**"),
            unsafe_allow_html=True,
        )

with right:
    st.markdown(f'<h3 style="color:{rc.MMR_COLOR}">🌈 MMR (Maximal Marginal Relevance)</h3>',
                unsafe_allow_html=True)
    st.caption(f"“Relevant to the query AND different from what I already picked.” λ = {lam}")
    for rank, (doc, flag) in enumerate(zip(mmr_docs, mmr_flags), 1):
        badge = flag or '<span class="okflag">✓ new information</span>'
        st.markdown(
            rc.chunk_card(rank, doc, rc.highlight_terms(doc.page_content[:340], query) + "…",
                          rc.MMR_COLOR, extra_badge=badge,
                          score_txt=f"similarity **{rc.cosine_sim(qvec, vec_of(doc)):.3f}**"),
            unsafe_allow_html=True,
        )

# The scoreboard sentence to read out loud:
n_dup_sim = sum(1 for f in sim_flags if f)
n_dup_mmr = sum(1 for f in mmr_flags if f)
src_sim = len({d.metadata["source"] for d in sim_docs})
src_mmr = len({d.metadata["source"] for d in mmr_docs})
st.info(f"**Scoreboard for k={k}:**  similarity → **{n_dup_sim} near-duplicate(s)**, "
        f"{src_sim} distinct source file(s) · MMR → **{n_dup_mmr} near-duplicate(s)**, "
        f"{src_mmr} distinct source file(s). Same budget — "
        + ("MMR bought more *different* information." if (n_dup_sim > n_dup_mmr or src_mmr > src_sim)
           else "try a question the corpus repeats itself about, or raise k."))

# ─────────────────────────────────────────────────────────────────────────────
# WHERE the strategies landed: the document map + the embedding map
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Where each strategy landed in the documents")
st.caption("One row per file, one block per chunk (width = chunk length). "
           "🟦 similarity-only · 🟧 MMR-only · 🟩 picked by both")
marks: dict[int, tuple[str, str]] = {}
for rank, d in enumerate(sim_docs, 1):
    marks[d.metadata["chunk_id"]] = (rc.SIM_COLOR, f"S{rank}")
for rank, d in enumerate(mmr_docs, 1):
    cid = d.metadata["chunk_id"]
    if cid in marks:
        marks[cid] = (rc.BOTH_COLOR, f"{marks[cid][1]}·M{rank}")
    else:
        marks[cid] = (rc.MMR_COLOR, f"M{rank}")
st.markdown(rc.doc_map_html(chunks, marks), unsafe_allow_html=True)

with st.expander("🗺️ …and in embedding space (the query lands as a point too)", expanded=True):
    pts, project, _ = rc.pca_fit(vectors)
    qpt = project(qvec)
    df = pd.DataFrame({
        "x": pts[:, 0], "y": pts[:, 1],
        "source": [c.metadata["source"] for c in chunks],
        "chunk": [f"#{c.metadata['chunk_id'] + 1}" for c in chunks],
        "preview": [c.page_content[:110].replace("\n", " ") + "…" for c in chunks],
    })
    base = alt.Chart(df).mark_circle(size=140, opacity=0.35, color="#9E9E9E").encode(
        x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None),
        tooltip=["chunk", "source", "preview"],
    )
    sim_ids = [d.metadata["chunk_id"] for d in sim_docs]
    mmr_ids = [d.metadata["chunk_id"] for d in mmr_docs]
    ring_sim = alt.Chart(df.iloc[sim_ids]).mark_point(size=600, stroke=rc.SIM_COLOR,
                                                      strokeWidth=4, filled=False).encode(
        x="x:Q", y="y:Q", tooltip=["chunk", "source", "preview"])
    ring_mmr = alt.Chart(df.iloc[mmr_ids]).mark_point(size=340, stroke=rc.MMR_COLOR,
                                                      strokeWidth=4, filled=False).encode(
        x="x:Q", y="y:Q", tooltip=["chunk", "source", "preview"])
    qdf = pd.DataFrame({"x": [qpt[0]], "y": [qpt[1]], "label": ["YOUR QUESTION"]})
    qmark = alt.Chart(qdf).mark_point(shape="diamond", size=700, color="#D32F2F",
                                      filled=True).encode(x="x:Q", y="y:Q", tooltip=["label"])
    st.altair_chart(alt.layer(base, ring_sim, ring_mmr, qmark).properties(height=430),
                    width="stretch")
    st.caption("🔷 red diamond = the query · 🔵 big blue rings = similarity picks (visibly clustered "
               "right around the query) · 🟠 orange rings = MMR picks (fanning out to cover more ground).")

st.success("**Takeaway:** retrieval = nearest-neighbor lookup on the query vector. Similarity "
           "maximizes closeness; MMR maximizes *information per chunk of budget*. Use MMR when "
           "your corpus repeats itself — which every real corpus does. "
           "→ Next: **5 · Answer** — feed the winners to the LLM, with citations.")
