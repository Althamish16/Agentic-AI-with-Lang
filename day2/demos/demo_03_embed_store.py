"""
LIVE DEMO — Step 3: EMBED + STORE.

Goal on screen: each chunk becomes a vector (just a list of numbers), and on a
2-D map of those vectors, CLOSE = SIMILAR MEANING. Then the vectors go into
Chroma, whose only job is "given a vector, find the nearest stored vectors, fast".

What to do live:
  1. Show one raw vector — "this is ALL the database ever sees: numbers."
  2. Show the map: the three documents form three loose neighborhoods, and the
     mixed border zones are chunks that talk about shared ideas (memory ≈ RAG).
  3. Pick a chunk in the neighbor explorer — its top-3 neighbors are about the
     same idea, often from a DIFFERENT file. Meaning, not keywords.
  4. Click through to the Chroma expander: same vectors, now indexed.

Run standalone:  streamlit run day2/demos/demo_03_embed_store.py
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import rag_demo_common as rc

rc.page_setup(
    "🧠",
    "Step 3 · Embed — meaning becomes geometry (then into Chroma)",
    ["Embed", "Store"],
    "An embedding model turns text into a vector. Texts that MEAN similar things "
    "get vectors that are CLOSE — that's the whole trick behind semantic search.",
)

ss = st.session_state
chunks = rc.ensure_chunks()
vectors = rc.ensure_vectors()
dim = vectors.shape[1]

m1, m2, m3 = st.columns(3)
m1.metric("Chunks embedded", len(chunks))
m2.metric("Dimensions per vector", dim)
m3.metric("Embedding model", "local · no API" if "fastembed" in ss.embed_label else "API")
st.caption(f"Model: **{ss.embed_label}** — every chunk (and later, every query) goes through this exact model.")

rc.show_code("the code behind this step", f"""
from config import get_embeddings           # fastembed locally, or Azure/OpenAI via .env

embeddings = get_embeddings()
vectors = embeddings.embed_documents([c.page_content for c in chunks])
# -> {len(chunks)} vectors, each a plain list of {dim} floats. That's it. No magic.
""")

# ─────────────────────────────────────────────────────────────────────────────
# 1) A vector, shown raw — demystify it completely
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("What one embedding actually is")
first = chunks[0]
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown(
        f'<div class="card" style="border-left-color:{rc.chunk_color(0)}">'
        f'<div class="meta">chunk #1 · 📄 {first.metadata["source"]}</div>'
        f"{rc.highlight_terms(first.page_content[:300], '')}…</div>",
        unsafe_allow_html=True,
    )
with c2:
    head = ", ".join(f"{v:+.3f}" for v in vectors[0][:8])
    st.code(f"[{head},\n  … {dim - 8} more numbers]", language="text")
    st.caption("The chunk on the left, after embedding. The vector database will only ever "
               "compare lists like this — it never reads the text.")

# ─────────────────────────────────────────────────────────────────────────────
# 2) THE map: 2-D projection of the embedding space
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("The embedding space (projected to 2-D)")
pts, project, explained = rc.pca_fit(vectors)

df = pd.DataFrame({
    "x": pts[:, 0], "y": pts[:, 1],
    "source": [c.metadata["source"] for c in chunks],
    "chunk": [f"#{c.metadata['chunk_id'] + 1}" for c in chunks],
    "preview": [c.page_content[:120].replace("\n", " ") + "…" for c in chunks],
})

sel_label = st.selectbox(
    "🔎 Neighbor explorer — pick a chunk and watch its nearest neighbors light up",
    options=["(none — just show the map)"] + [
        f"#{c.metadata['chunk_id'] + 1} · {c.metadata['source']} · “{c.page_content[:70]}…”"
        for c in chunks
    ],
)

layers = [
    alt.Chart(df).mark_circle(size=170, opacity=0.75).encode(
        x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None),
        color=alt.Color("source:N", scale=alt.Scale(range=rc.DOC_COLORS),
                        legend=alt.Legend(title="source document", orient="top")),
        tooltip=["chunk", "source", "preview"],
    )
]

neighbors: list[tuple[int, float]] = []
if not sel_label.startswith("("):
    sel = int(sel_label.split("·")[0].strip().lstrip("#")) - 1
    sims = rc.cosine_matrix(vectors)[sel]
    order = np.argsort(-sims)
    neighbors = [(int(j), float(sims[j])) for j in order if j != sel][:3]
    ring = pd.DataFrame({"x": [pts[sel, 0]], "y": [pts[sel, 1]]})
    nbr = pd.DataFrame({"x": [pts[j, 0] for j, _ in neighbors],
                        "y": [pts[j, 1] for j, _ in neighbors]})
    layers.append(alt.Chart(ring).mark_point(shape="diamond", size=650, stroke="#D32F2F",
                                             strokeWidth=4, filled=False).encode(x="x:Q", y="y:Q"))
    layers.append(alt.Chart(nbr).mark_point(size=520, stroke="#F57C00", strokeWidth=3.5,
                                            filled=False).encode(x="x:Q", y="y:Q"))

st.altair_chart(alt.layer(*layers).properties(height=460), width="stretch")
st.caption(f"2-D PCA projection of the {dim}-D space (keeps {explained:.0%} of the variance). "
           "Distances are approximate — but neighborhoods are real: chunks about the same idea sit together. "
           "🔷 red diamond = your pick · 🟠 orange rings = its 3 nearest neighbors.")

if neighbors:
    st.markdown("**Nearest neighbors by cosine similarity** (1.0 = identical meaning):")
    for rank, (j, sim) in enumerate(neighbors, 1):
        c = chunks[j]
        badge = ('<span class="okflag">different file, same idea</span>'
                 if c.metadata["source"] != chunks[sel].metadata["source"] else "")
        st.markdown(
            rc.chunk_card(rank, c, rc.highlight_terms(c.page_content[:260], "") + "…",
                          rc.MMR_COLOR, extra_badge=badge, score_txt=f"cosine **{sim:.3f}**"),
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# 3) STORE: the same vectors go into Chroma
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Store: into the Chroma vector database")
rc.ensure_store()
st.success(f"✅ Chroma collection **day2_demo** now holds **{ss.store_count} vectors** "
           f"({dim} dimensions, cosine space) — each with its chunk text and metadata attached. "
           "Its one superpower: *“here's a query vector — give me the k nearest stored vectors, fast.”*")

rc.show_code("the code behind this step", """
from langchain_chroma import Chroma

vectorstore = Chroma.from_documents(          # embeds + stores in one call
    documents=chunks,
    embedding=get_embeddings(),
    persist_directory=".chroma",              # the lab persists to disk;
)                                             # this demo keeps it in memory

# (This demo pre-computed the vectors for the map above, so it hands Chroma
#  those SAME vectors — what you see plotted is exactly what got indexed.)
""")

st.success("**Takeaway:** after this step your documents are a searchable *geometry* — "
           "closeness = meaning. → Next: **4 · Retrieve** — drop a question into this space "
           "and grab its nearest neighbors.")
