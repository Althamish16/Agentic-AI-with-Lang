"""
rag.py — the Day 2 RAG building block, promoted to shared/ for Day 3+ and the UI.

Pipeline:  load documents -> split into chunks -> embed -> store in Chroma
           -> retrieve top-k (similarity or MMR) -> answer with citations.

Embeddings + the Chroma directory come from config.py, so the whole thing is
provider-swappable (local fastembed by default; Azure/OpenAI if you set the env).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Literal

from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import REPO_ROOT, get_embeddings, get_llm, get_vectorstore_dir, settings

DATA_DIR = REPO_ROOT / "data"

# ── Defaults are deliberately visible so Day 2 can tune them in the lab ──
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120
DEFAULT_K = 4


# ─────────────────────────────────────────────────────────────────────────────
# 1) LOAD
# ─────────────────────────────────────────────────────────────────────────────
def load_documents(data_dir: str | Path | None = None) -> List[Document]:
    """Load every .md / .txt file under data/ as LangChain Documents.
    TextLoader stamps metadata['source'] with the file path — that's our citation."""
    data_dir = Path(data_dir or DATA_DIR)
    docs: List[Document] = []
    for path in sorted(data_dir.rglob("*")):
        if path.suffix.lower() in {".md", ".txt"}:
            docs.extend(TextLoader(str(path), encoding="utf-8").load())
    if not docs:
        raise SystemExit(f"[rag] No .md/.txt documents found under {data_dir}")
    return docs


# ─────────────────────────────────────────────────────────────────────────────
# 2) SPLIT (chunk)
# ─────────────────────────────────────────────────────────────────────────────
def split_documents(
    docs: List[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Document]:
    """Chunk size/overlap are the classic RAG knobs — too big dilutes signal,
    too small loses context. add_start_index lets us point back into the file."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    return splitter.split_documents(docs)


# ─────────────────────────────────────────────────────────────────────────────
# 3) EMBED + STORE (Chroma)
# ─────────────────────────────────────────────────────────────────────────────
def get_vectorstore(embeddings=None) -> Chroma:
    """Open (or create) the persistent Chroma collection. Same object used to add
    documents and to query — Chroma persists to disk automatically."""
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings or get_embeddings(),
        persist_directory=str(get_vectorstore_dir()),
    )


def index_is_empty(vs: Chroma) -> bool:
    return len(vs.get(limit=1).get("ids", [])) == 0


def build_index(
    data_dir: str | Path | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    reset: bool = True,
) -> Chroma:
    """Full (re)index of data/ into Chroma. Returns the populated vector store."""
    embeddings = get_embeddings()
    persist = str(get_vectorstore_dir())

    if reset:
        # Drop any prior collection so re-runs are clean (and so switching the
        # embedding model — which changes vector dimensions — never conflicts).
        import chromadb

        client = chromadb.PersistentClient(path=persist)
        try:
            client.delete_collection(settings.chroma_collection)
        except Exception:
            pass

    docs = load_documents(data_dir)
    chunks = split_documents(docs, chunk_size, chunk_overlap)
    vs = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=settings.chroma_collection,
        persist_directory=persist,
    )
    return vs


def ensure_index(data_dir: str | Path | None = None) -> Chroma:
    """Return a ready-to-query store, building the index on first use."""
    vs = get_vectorstore()
    if index_is_empty(vs):
        vs = build_index(data_dir, reset=False)
    return vs


# ─────────────────────────────────────────────────────────────────────────────
# 4) RETRIEVE
# ─────────────────────────────────────────────────────────────────────────────
def get_retriever(
    k: int = DEFAULT_K,
    search_type: Literal["similarity", "mmr"] = "similarity",
    vs: Chroma | None = None,
):
    """Build a retriever. `mmr` (Maximal Marginal Relevance) trades a little
    relevance for diversity, avoiding near-duplicate chunks."""
    vs = vs or ensure_index()
    search_kwargs = {"k": k}
    if search_type == "mmr":
        search_kwargs["fetch_k"] = max(4 * k, 20)  # pull a wider pool, then diversify
        search_kwargs["lambda_mult"] = 0.5
    return vs.as_retriever(search_type=search_type, search_kwargs=search_kwargs)


def format_docs_with_citations(docs: List[Document]) -> str:
    """Render retrieved chunks as a numbered, citable context block."""
    blocks = []
    for i, d in enumerate(docs, 1):
        src = os.path.basename(d.metadata.get("source", "unknown"))
        blocks.append(f"[{i}] (source: {src})\n{d.page_content.strip()}")
    return "\n\n".join(blocks)


def sources_of(docs: List[Document]) -> List[str]:
    """De-duplicated list of source file names, in first-seen order."""
    seen: List[str] = []
    for d in docs:
        src = os.path.basename(d.metadata.get("source", "unknown"))
        if src not in seen:
            seen.append(src)
    return seen


# ─────────────────────────────────────────────────────────────────────────────
# 5) ANSWER (retrieve -> stuff -> LLM), with citations
# ─────────────────────────────────────────────────────────────────────────────
_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a research assistant. Answer the question using ONLY the numbered context. "
            "Cite sources inline like [1], [2]. If the context is insufficient, say so plainly.",
        ),
        ("human", "Question: {question}\n\nContext:\n{context}"),
    ]
)


def answer_question(
    question: str,
    k: int = DEFAULT_K,
    search_type: Literal["similarity", "mmr"] = "similarity",
    llm=None,
) -> dict:
    """Retrieve, then answer with inline citations. Returns answer + sources + docs."""
    retriever = get_retriever(k=k, search_type=search_type)
    docs = retriever.invoke(question)
    llm = llm or get_llm(temperature=0)
    chain = _ANSWER_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"question": question, "context": format_docs_with_citations(docs)})
    return {"answer": answer, "sources": sources_of(docs), "docs": docs}
