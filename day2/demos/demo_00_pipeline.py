"""
LIVE DEMO — Step 0: The big picture.

The anchor slide of the day: the whole RAG pipeline on one screen, plus a
one-click "run everything with defaults" so the audience sees the pipeline
actually execute (with live counts) before we zoom into each stage.

Run standalone:            streamlit run day2/demos/demo_00_pipeline.py
Run the whole demo suite:  streamlit run day2/demos/app.py
"""

from __future__ import annotations

import streamlit as st

import rag_demo_common as rc

rc.page_setup(
    "🗺️",
    "Day 2 · RAG — the whole pipeline",
    rc.STAGES,  # every stage lit: this page IS the map
    "Retrieval-Augmented Generation: ground the model's answer in YOUR documents — with citations.",
)

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown("""
### Two phases, eight steps

**⚙️ Indexing (ahead of time)**
1. **Load** — read files into LangChain `Document` objects
2. **Split** — cut them into overlapping chunks *(the big quality knob)*
3. **Embed** — turn each chunk into a vector: *close = similar meaning*
4. **Store** — put vectors + text + metadata into **Chroma**

**⚡ Query (when a question arrives)**
5. **Embed the query** — with the **same** model as the index
6. **Retrieve top-k** — *similarity* (closest) or *MMR* (close **and** diverse)
7. **Augment** — paste the retrieved chunks into the prompt as numbered context
8. **Generate** — the LLM answers **only from that context**, citing `[1] [2]`
""")

with right:
    st.markdown("### ▶ Watch it run, end to end")
    st.caption("Same defaults as the lab: chunk_size 800 · overlap 120 · top-k 4.")
    if st.button("🚀 Run the full indexing pipeline now", type="primary", width="stretch"):
        with st.status("Running the indexing phase…", expanded=True) as status:
            docs = rc.ensure_docs()
            st.write(f"**1 · Load** → {len(docs)} documents ({sum(len(d.page_content) for d in docs):,} chars)")
            chunks = rc.ensure_chunks()
            st.write(f"**2 · Split** → {len(chunks)} chunks (size {st.session_state.chunk_size}, "
                     f"overlap {st.session_state.chunk_overlap})")
            vecs = rc.ensure_vectors()
            st.write(f"**3 · Embed** → {vecs.shape[0]} vectors, **{vecs.shape[1]} dimensions** each")
            rc.ensure_store()
            st.write(f"**4 · Store** → Chroma collection with {st.session_state.store_count} vectors")
            status.update(label="Index ready — the sidebar now shows every stage ✅", state="complete")
        st.success("Now open **1 · Load** and walk the stages one by one — the state carries over.")

    st.markdown("### 🧭 Today's demos")
    st.markdown("""
| Page | You will see |
|---|---|
| **1 · Load** | files become `Document` objects |
| **2 · Split** | chunks as colored blocks, sliders live |
| **3 · Embed + Store** | chunks as points in space |
| **4 · Retrieve** | similarity vs MMR, side by side |
| **5 · Answer** | grounded answer with citations |
| **6 · Break it** | why bad settings wreck RAG |
""")

st.divider()
st.caption("Every page has a “👩‍💻 the code behind this step” expander — what you see on screen "
           "is always 5–10 lines of plain LangChain, the same API you'll use in the lab "
           "(day2/starter/rag_pipeline.py).")
