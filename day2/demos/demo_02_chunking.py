"""
LIVE DEMO — Step 2: SPLIT (the chunking playground).

Goal on screen: the document literally painted as colored chunk blocks, redrawn
in real time as you drag two sliders. Candy-stripes = the overlap region that
belongs to BOTH neighboring chunks.

What to do live:
  1. Start at the defaults (800 / 120) — point out the stripes between blocks.
  2. Drag chunk_size down to ~150: confetti. Each block is a fragment —
     "would YOU understand this block on its own?"
  3. Drag chunk_size up to 2000: three giant blocks — "one block, ten topics —
     what single question is this block similar to?"
  4. Drag overlap to 0: stripes vanish — ideas on a boundary now get cut in half.

Run standalone:  streamlit run day2/demos/demo_02_chunking.py
"""

from __future__ import annotations

import pathlib

import altair as alt
import pandas as pd
import streamlit as st

import rag_demo_common as rc

rc.page_setup(
    "✂️",
    "Step 2 · Split — the chunking playground",
    ["Split"],
    "chunk_size and chunk_overlap are THE quality knobs of RAG. "
    "Too big dilutes meaning, too small loses context.",
)

ss = st.session_state
rc.ensure_docs()

# ─────────────────────────────────────────────────────────────────────────────
# The two knobs — every drag re-splits and repaints instantly
# ─────────────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 2, 1])
size = c1.slider("chunk_size (characters)", 100, 2000, ss.get("chunk_size", rc.DEFAULT_CHUNK_SIZE), 50,
                 help="Max characters per chunk. The splitter prefers paragraph/sentence breaks.")
overlap = c2.slider("chunk_overlap (characters)", 0, min(500, size - 50),
                    min(ss.get("chunk_overlap", rc.DEFAULT_CHUNK_OVERLAP), size - 50), 10,
                    help="How much of the end of each chunk is repeated at the start of the next.")
with c3:
    st.write("")
    if st.button("↺ Lab defaults", help=f"{rc.DEFAULT_CHUNK_SIZE} / {rc.DEFAULT_CHUNK_OVERLAP}"):
        rc.set_chunks(rc.DEFAULT_CHUNK_SIZE, rc.DEFAULT_CHUNK_OVERLAP)
        st.rerun()

# Re-split only when the knobs actually moved (splitting also invalidates
# the vectors + index downstream — chunks changed, so everything must rebuild).
if not ss.get("chunks") or size != ss.get("chunk_size") or overlap != ss.get("chunk_overlap"):
    rc.set_chunks(size, overlap)
chunks = ss.chunks

rc.show_code("the code behind this step", f"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size={size},          # ← left slider
    chunk_overlap={overlap},        # ← right slider
    add_start_index=True,       # remember each chunk's position for citations
)
chunks = splitter.split_documents(docs)   # -> {len(chunks)} chunks
# "Recursive" = try to cut on paragraphs first, then sentences, then words —
# so blocks below tend to end at natural boundaries, not mid-word.
""")

lens = [len(c.page_content) for c in chunks]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Chunks produced", len(chunks))
m2.metric("Avg chunk length", f"{int(sum(lens) / len(lens))} chars")
m3.metric("Longest / shortest", f"{max(lens)} / {min(lens)}")
m4.metric("Overlap", f"{overlap} chars" + (f" (~{round(100 * overlap / size)}%)" if size else ""))

# ─────────────────────────────────────────────────────────────────────────────
# THE visual: each document painted as colored chunk blocks + striped overlaps
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("The document, painted as chunks")
st.markdown(
    '<div class="flow">'
    '<span class="st" style="background:#BBDEFB;color:#111">colored block = one chunk</span>'
    '<span class="st" style="background:repeating-linear-gradient(135deg,#BBDEFB 0 9px,#C8E6C9 9px 18px);color:#111">'
    "stripes = overlap (text in BOTH chunks)</span>"
    '<span class="st">#n = chunk number</span>'
    '<span class="st" style="color:#999">grey = separators the splitter dropped</span>'
    "</div>",
    unsafe_allow_html=True,
)

tabs = st.tabs([f"📄 {name}" for name in ss.doc_names])
for tab, doc in zip(tabs, ss.docs):
    with tab:
        # Match this source document with its chunks via metadata (source + page),
        # then place them by the start_index the splitter recorded.
        doc_key = (pathlib.Path(str(doc.metadata.get("source", "?"))).name,
                   doc.metadata.get("page"))
        spans = [
            (c.metadata["start_index"],
             c.metadata["start_index"] + len(c.page_content),
             c.metadata["chunk_id"])
            for c in chunks
            if (c.metadata["source"], c.metadata.get("page")) == doc_key
        ]
        st.caption(f"{len(spans)} chunks in this document")
        st.markdown(rc.chunked_doc_html(doc.page_content, spans), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Chunk-size distribution — proof the splitter respects natural boundaries
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📊 Chunk sizes at a glance", expanded=False):
    df = pd.DataFrame({
        "chunk": [f"#{c.metadata['chunk_id'] + 1}" for c in chunks],
        "characters": lens,
        "source": [c.metadata["source"] for c in chunks],
        "order": range(len(chunks)),
    })
    st.altair_chart(
        alt.Chart(df).mark_bar().encode(
            x=alt.X("chunk:N", sort=alt.EncodingSortField("order"), title="chunk"),
            y=alt.Y("characters:Q", title="characters"),
            color=alt.Color("source:N", scale=alt.Scale(range=rc.DOC_COLORS)),
            tooltip=["chunk", "source", "characters"],
        ).properties(height=260),
        width="stretch",
    )
    st.caption("Bars stop short of chunk_size when the splitter finds a paragraph break first — "
               "that's the 'Recursive' part doing its job.")

st.success("**Takeaway:** chunks are what gets embedded, retrieved and cited — the model never "
           "sees 'the document', only these blocks. Choose the block size so ONE block ≈ ONE idea. "
           "→ Next: **3 · Embed** each block into a vector.")
