"""
Day 2 SOLUTION — a RAG pipeline over data/.

load -> chunk -> embed -> store (Chroma) -> retrieve (similarity vs MMR) -> answer+cite

The granular helpers live in shared/rag.py so Day 3+ can reuse them; here we wire the
steps together explicitly so the mechanics are visible.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import get_embeddings, get_llm, get_vectorstore_dir, settings
from shared.pretty import banner, ok, rule
from shared.rag import (
    format_docs_with_citations,
    load_documents,
    sources_of,
    split_documents,
)

# The two RAG knobs you will tune in the lab:
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 4


def main():
    question = " ".join(sys.argv[1:]).strip() or "What is MMR and when should I use it in retrieval?"

    # 1) LOAD ------------------------------------------------------------------
    banner("Day 2 — RAG pipeline")
    docs = load_documents()
    ok(f"Loaded {len(docs)} source document(s) from data/")

    # 2) CHUNK -----------------------------------------------------------------
    chunks = split_documents(docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    ok(f"Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"\n  sample chunk[0]: {chunks[0].page_content[:160]!r}...")

    # 3) EMBED + STORE ---------------------------------------------------------
    # Reset the collection first so re-runs don't pile up duplicate vectors.
    import chromadb

    persist = str(get_vectorstore_dir())
    client = chromadb.PersistentClient(path=persist)
    try:
        client.delete_collection(settings.chroma_collection)
    except Exception:
        pass

    embeddings = get_embeddings()
    print(f"\n  embeddings provider: {settings.embeddings_provider} ({type(embeddings).__name__})")
    vs = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=settings.chroma_collection,
        persist_directory=persist,
    )
    ok(f"Embedded + stored {len(chunks)} chunks in Chroma at {settings.chroma_dir}/")

    # 4) RETRIEVE — similarity vs MMR -----------------------------------------
    print(f"\nQuestion: {question}")
    rule()
    sim_docs = vs.as_retriever(
        search_type="similarity", search_kwargs={"k": TOP_K}
    ).invoke(question)
    mmr_docs = vs.as_retriever(
        search_type="mmr", search_kwargs={"k": TOP_K, "fetch_k": 20, "lambda_mult": 0.5}
    ).invoke(question)
    print(f"  similarity top-{TOP_K} sources: {sources_of(sim_docs)}")
    print(f"  MMR        top-{TOP_K} sources: {sources_of(mmr_docs)}   (relevance + diversity)")

    # 5) ANSWER with citations -------------------------------------------------
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Answer using ONLY the numbered context. Cite sources inline like [1], [2]. "
                "If the context is insufficient, say so.",
            ),
            ("human", "Question: {question}\n\nContext:\n{context}"),
        ]
    )
    llm = get_llm(temperature=0)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"question": question, "context": format_docs_with_citations(sim_docs)})

    rule("═")
    print("ANSWER:\n")
    print(answer)
    print(f"\nSources: {sources_of(sim_docs)}")


if __name__ == "__main__":
    main()
