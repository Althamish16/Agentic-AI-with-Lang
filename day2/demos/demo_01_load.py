"""
LIVE DEMO — Step 1: LOAD.

Goal on screen: files go in, LangChain `Document` objects come out — and a
Document is nothing mysterious: page_content (the text) + metadata (where it
came from). The metadata is what makes citations possible in step 5.

What to do live:
  1. Load the three built-in sample docs (one click).
  2. Open one Document and show its anatomy (page_content + metadata).
  3. Optionally drag in your own .txt/.md/.pdf and show it appear as Documents.

Run standalone:  streamlit run day2/demos/demo_01_load.py
"""

from __future__ import annotations

import html
import tempfile
from pathlib import Path

import streamlit as st
from langchain_core.documents import Document

import rag_demo_common as rc

rc.page_setup(
    "📂",
    "Step 1 · Load — files become Document objects",
    ["Load"],
    "A Document = page_content (the text) + metadata (source, page, …). "
    "Metadata is what lets us cite sources later.",
)

ss = st.session_state

# ─────────────────────────────────────────────────────────────────────────────
# Controls: built-in sample docs + optional uploads
# ─────────────────────────────────────────────────────────────────────────────
builtin_paths = sorted(rc.SAMPLE_DIR.glob("*.md"))
col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.subheader("Built-in sample documents")
    picked = st.multiselect(
        "Documents to load",
        options=[p.name for p in builtin_paths],
        default=[p.name for p in builtin_paths],
    )

with col_b:
    st.subheader("…or drop in your own")
    uploads = st.file_uploader(
        "Add .txt / .md / .pdf files (optional)",
        type=["txt", "md", "pdf"],
        accept_multiple_files=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# THE ACTUAL LOADING — this is the LangChain API, exactly as in the lab
# ─────────────────────────────────────────────────────────────────────────────
def load_selected() -> tuple[list[Document], list[str]]:
    from langchain_community.document_loaders import TextLoader

    docs: list[Document] = []
    names: list[str] = []

    for name in picked:
        path = rc.SAMPLE_DIR / name
        docs.extend(TextLoader(str(path), encoding="utf-8").load())  # 1 file -> 1 Document
        names.append(name)

    for up in uploads or []:
        if up.name.lower().endswith(".pdf"):
            from langchain_community.document_loaders import PyPDFLoader

            # PyPDFLoader reads from a path, so persist the upload to a temp file.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(up.getvalue())
            pages = PyPDFLoader(tmp.name).load()  # 1 PDF -> 1 Document PER PAGE
            for d in pages:
                d.metadata["source"] = up.name  # keep the human filename for citations
            docs.extend(pages)
        else:
            # A Document is just a small container — you can build one by hand:
            docs.append(Document(page_content=up.getvalue().decode("utf-8", "replace"),
                                 metadata={"source": up.name}))
        names.append(up.name)
    return docs, names


if st.button("📥 Load documents", type="primary"):
    docs, names = load_selected()
    if not docs:
        st.error("Pick at least one built-in doc or upload a file.")
    else:
        ss.docs, ss.doc_names = docs, names
        # New inputs invalidate everything downstream — the pipeline is honest.
        for key in ("chunks", "vectors", "store", "store_fp", "last_query", "broken_cache"):
            ss.pop(key, None)
        st.toast(f"Loaded {len(docs)} Document objects from {len(names)} files", icon="✅")

rc.show_code("the code behind this step", """
from langchain_community.document_loaders import TextLoader, PyPDFLoader

docs = TextLoader("data/rag_overview.md", encoding="utf-8").load()   # 1 Document
pages = PyPDFLoader("report.pdf").load()                             # 1 Document per page

docs[0].page_content   # -> the raw text
docs[0].metadata       # -> {"source": "data/rag_overview.md"}  ← this becomes the citation
""")

# ─────────────────────────────────────────────────────────────────────────────
# Show what we got: every Document, with its anatomy laid open
# ─────────────────────────────────────────────────────────────────────────────
if not ss.get("docs"):
    st.info("👆 Click **Load documents** to turn the files into LangChain `Document` objects.")
    st.stop()

docs = ss.docs
st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("Files loaded", len(ss.doc_names))
m2.metric("Document objects", len(docs))
m3.metric("Total characters", f"{sum(len(d.page_content) for d in docs):,}")

st.subheader("The Document objects, opened up")
st.caption("Say it out loud: a Document is JUST text + a dict of metadata. Nothing else.")

for i, doc in enumerate(docs):
    src = Path(str(doc.metadata.get("source", "?"))).name
    color = rc.doc_color(ss.doc_names.index(src) if src in ss.doc_names else i)
    label = f"Document {i}  ·  📄 {src}  ·  {len(doc.page_content):,} chars"
    if "page" in doc.metadata:
        label += f"  ·  page {doc.metadata['page']}"
    with st.expander(label, expanded=(i == 0)):
        st.markdown(
            f'<div class="card" style="border-left-color:{color}">'
            f'<div class="meta">doc.page_content — first 600 characters</div>'
            f"{html.escape(doc.page_content[:600])}…</div>",
            unsafe_allow_html=True,
        )
        st.markdown("**doc.metadata** — carried along through every later stage:")
        st.json(doc.metadata)

st.success("**Takeaway:** loaders normalize ANY format (text, PDF, HTML, Notion, …) into the same "
           "shape — so the rest of the pipeline never cares where text came from. "
           "→ Next: **2 · Split** these into chunks.")
