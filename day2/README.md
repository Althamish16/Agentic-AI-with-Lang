# Day 2 — Document Loaders & Chunking · Embeddings & Retrieval (RAG)

**Concept.** RAG grounds answers in your documents. The pipeline is:
**load → chunk → embed → store (Chroma) → retrieve top-k → answer with citations.**
Chunking size/overlap and the search strategy (**similarity** vs **MMR**) are the
knobs that most affect answer quality.

**Exercise.** Build a RAG pipeline over [data/](../data/). Compare *similarity*
retrieval (closest chunks) against *MMR* (relevant **and** diverse), then answer a
question with inline `[1][2]` citations. Fill the `# TODO (lab):` gaps in
[starter/rag_pipeline.py](starter/rag_pipeline.py).

**Run it**
```bash
python day2/solution/rag_pipeline.py "What is MMR and when should I use it?"
```
Embeddings run **locally** by default (fastembed, no cloud) — first run downloads a
small model once. Chroma persists to `.chroma/` (git-ignored).

**What carries over.** Day 1's planner is untouched. Today's pipeline is packaged in
[shared/rag.py](../shared/rag.py) (`build_index`, `get_retriever`,
`answer_question`) — Day 3's executor node calls exactly these.

**Stretch goal.** Change `chunk_size`/`chunk_overlap` and watch which chunks get
retrieved. Or set `EMBEDDINGS_PROVIDER=azure` in `.env` (needs an embeddings
deployment) and re-run — note you must re-index because vector dimensions change.
