"""
backend/day2_sessions.py — dynamic, user-uploaded corpora for the Day 2 RAG tab.

The classroom flow: a learner uploads their own .txt/.md/.pdf files, we run the
FULL indexing pipeline on them (load → split → embed → store) and hand back a
stage-by-stage summary so the UI can show the process *live and transparently*.
Every later Day-2 demo (retrieve, similarity vs MMR, answer, break-it) then runs
against that per-session index instead of the built-in data/ corpus.

Design notes
- One index per upload, keyed by a short session id the browser keeps and passes
  back on each demo run. Kept in memory (dict) — ephemeral, like a live demo.
- We index into the SAME Chroma directory the course already uses, but under a
  unique collection name per session, so we reuse one client/path (no clashes)
  and never touch the shared `research_assistant` collection.
"""

from __future__ import annotations

import os
import tempfile
import uuid

# Session store: sid -> {"docs", "chunks", "vs", "col", "dim", "files"}
_SESSIONS: dict[str, dict] = {}

# Guardrails so a classroom upload can't exhaust memory.
MAX_FILES = 8
MAX_BYTES_PER_FILE = 2_000_000  # 2 MB
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120


def _load_uploads(files: list[tuple[str, bytes]]):
    """Turn (filename, bytes) pairs into LangChain Document objects — the same
    shape TextLoader/PyPDFLoader produce, so the rest of the pipeline is identical
    whether the text came from disk or from a browser upload."""
    from langchain_core.documents import Document

    docs = []
    for name, data in files:
        if not data:
            continue
        if len(data) > MAX_BYTES_PER_FILE:
            raise ValueError(f"{name} is larger than {MAX_BYTES_PER_FILE // 1_000_000} MB.")
        low = name.lower()
        if low.endswith(".pdf"):
            from langchain_community.document_loaders import PyPDFLoader

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            try:
                pages = PyPDFLoader(tmp_path).load()  # 1 Document per page
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            for d in pages:
                d.metadata["source"] = name
            docs.extend(pages)
        else:  # .txt / .md / anything text-ish
            text = data.decode("utf-8", "replace")
            docs.append(Document(page_content=text, metadata={"source": name}))
    return docs


def ingest(
    files: list[tuple[str, bytes]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> tuple[str, list[dict], dict]:
    """Run the whole indexing phase on the uploaded files and return
    (session_id, stages, meta). `stages` is the transparent, per-step trace the
    UI animates; `meta` is a tiny summary for the corpus badge."""
    if len(files) > MAX_FILES:
        raise ValueError(f"Please upload at most {MAX_FILES} files.")

    from config import get_embeddings, get_vectorstore_dir, settings
    from shared.rag import split_documents

    # 1) LOAD
    docs = _load_uploads(files)
    if not docs:
        raise ValueError("No readable text found in the uploaded files.")

    # 2) SPLIT
    chunks = split_documents(docs, chunk_size, chunk_overlap)
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = i
        c.metadata["source"] = os.path.basename(str(c.metadata.get("source", "?")))

    # 3) EMBED + 4) STORE (Chroma, one fresh collection per session)
    emb = get_embeddings()
    dim = len(emb.embed_query("dimension probe"))
    sid = uuid.uuid4().hex[:12]
    col = f"day2_upload_{sid}"

    from langchain_chroma import Chroma

    vs = Chroma.from_documents(
        documents=chunks,
        embedding=emb,
        collection_name=col,
        persist_directory=str(get_vectorstore_dir()),
    )

    _SESSIONS[sid] = {
        "docs": docs,
        "chunks": chunks,
        "vs": vs,
        "col": col,
        "dim": dim,
        "files": [os.path.basename(n) for n, _ in files if _],
    }

    model = {
        "fastembed": f"fastembed · {settings.fastembed_model} (local, no API)",
        "azure": "Azure OpenAI embeddings",
        "openai": "OpenAI text-embedding-3-small",
    }.get(settings.embeddings_provider, settings.embeddings_provider)

    stages = [
        {
            "stage": "load",
            "label": "1 · Load",
            "detail": f"{len(docs)} document object(s) · {sum(len(d.page_content) for d in docs):,} characters",
            "items": [
                {"source": os.path.basename(str(d.metadata.get("source", "?"))), "chars": len(d.page_content)}
                for d in docs
            ],
        },
        {
            "stage": "split",
            "label": "2 · Split",
            "detail": f"{len(chunks)} chunks (size {chunk_size}, overlap {chunk_overlap})",
            "sample": chunks[0].page_content[:240].strip(),
        },
        {
            "stage": "embed",
            "label": "3 · Embed",
            "detail": f"{len(chunks)} vectors × {dim} dimensions · {model}",
        },
        {
            "stage": "store",
            "label": "4 · Store",
            "detail": f"Chroma collection ready · {len(chunks)} vectors (cosine)",
        },
    ]
    meta = {"files": _SESSIONS[sid]["files"], "chunks": len(chunks), "dim": dim, "docs": len(docs)}
    return sid, stages, meta


def resolve(sid: str | None) -> dict | None:
    """Return the stored session context for a session id, or None."""
    return _SESSIONS.get(sid or "")
