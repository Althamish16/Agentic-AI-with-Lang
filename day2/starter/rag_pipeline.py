"""
Day 2 STARTER — build a RAG pipeline over data/.

load -> chunk -> embed -> store (Chroma) -> retrieve (similarity vs MMR) -> answer+cite

Fill every "# TODO (lab):" and run:
    python day2/starter/rag_pipeline.py "What is MMR and when should I use it?"
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

# TODO (lab): pick your RAG knobs. Try (400, 40) vs (1000, 200) and compare.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 4


def main():
    question = " ".join(sys.argv[1:]).strip() or "What is MMR and when should I use it in retrieval?"

    banner("Day 2 — RAG pipeline")
    docs = load_documents()
    ok(f"Loaded {len(docs)} source document(s) from data/")

    # TODO (lab): split the docs into chunks using CHUNK_SIZE / CHUNK_OVERLAP.
    chunks = None  # <- replace with split_documents(...)
    if chunks is None:
        print("⚠ Starter not finished: split the documents (see the TODO). See solution/ if stuck.")
        return
    ok(f"Split into {len(chunks)} chunks")

    # Reset the collection so re-runs don't duplicate vectors.
    import chromadb

    persist = str(get_vectorstore_dir())
    client = chromadb.PersistentClient(path=persist)
    try:
        client.delete_collection(settings.chroma_collection)
    except Exception:
        pass

    embeddings = get_embeddings()

    # TODO (lab): build the Chroma store from `chunks` + `embeddings`.
    #             Use Chroma.from_documents(..., collection_name=settings.chroma_collection,
    #             persist_directory=persist).
    vs = None  # <- replace
    ok("Embedded + stored chunks in Chroma")

    # TODO (lab): retrieve TOP_K docs two ways and compare the sources:
    #   sim_docs = vs.as_retriever(search_type="similarity", search_kwargs={"k": TOP_K}).invoke(question)
    #   mmr_docs = vs.as_retriever(search_type="mmr", search_kwargs={"k": TOP_K, "fetch_k": 20, "lambda_mult": 0.5}).invoke(question)
    sim_docs = []  # <- replace
    mmr_docs = []  # <- replace
    print(f"  similarity sources: {sources_of(sim_docs)}")
    print(f"  MMR        sources: {sources_of(mmr_docs)}")

    # TODO (lab): compose prompt | llm | StrOutputParser() and answer using the
    #             similarity docs as context (format_docs_with_citations(sim_docs)).
    answer = "(TODO: build the answer chain)"

    rule("═")
    print("ANSWER:\n")
    print(answer)


if __name__ == "__main__":
    main()
