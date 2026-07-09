# Day 2 — Live Demos (interactive RAG web app)

An interactive Streamlit app that makes every stage of the RAG pipeline
**visible**: `Load → Split → Embed → Store → Embed query → Retrieve → Augment → Generate`.
Same spirit as `day1/demos/` — **one self-contained file per concept** — but as a
web UI, because chunk blocks, embedding maps and retrieval comparisons need pixels.

## Run it

```bash
# the whole suite, with horizontal sub-tabs across the top (recommended for class):
streamlit run day2/demos/app.py

# …or any single demo standalone (each file fills in earlier stages with defaults):
streamlit run day2/demos/demo_04_retrieval.py
```

| Page | Concept | What the room sees |
|------|---------|--------------------|
| **0 · Big picture** | the full pipeline | 8-step map + one-click "run the whole indexing phase" with live counts |
| **1 · Load** | `Document` objects | files (built-in samples or your own .txt/.md/.pdf) opened up into `page_content` + `metadata` — the metadata that later becomes the citation |
| **2 · Chunking playground** | `RecursiveCharacterTextSplitter` | the document painted as **colored chunk blocks**, re-split live as you drag `chunk_size` / `chunk_overlap`; candy-stripes = the overlap owned by two chunks |
| **3 · Embed + store** | embeddings, Chroma | one raw 384-number vector, then a **2-D map of embedding space** where close = similar meaning; a neighbor explorer; the vectors landing in Chroma |
| **4 · Similarity vs MMR** | retrieval strategies | the SAME question retrieved both ways, side by side: red **near-duplicate flags** in the similarity column, diverse picks in the MMR column, plus a document map and the query as a point in embedding space |
| **5 · Answer + citations** | augment + generate | the retrieved chunks, the **EXACT final prompt**, the grounded answer with colored `[n]` badges, and citation cards tracing each badge to file + character offset |
| **6 · Break it** | failure modes | healthy vs broken, same question: chunks too small (fragments), too huge (dilution), or a **query/index embedding-model mismatch** (silently random retrieval) — optional side-by-side LLM answers as the finale |

## How the story flows

Navigate with the **horizontal sub-tabs** across the top (same feel as Day 1's
slide tabs — the active tab is highlighted; only that page's code runs). The pages
share one pipeline state (docs → chunks → vectors → index), shown live in the
**sidebar X-ray** on every page, alongside run-context chips (which model /
embedder is live). Change the chunking in demo 2 and demo 4 retrieves from the
re-chunked index. The 🔄 button resets the story.

Every page has a **“👩‍💻 the code behind this step”** expander showing the 5–10
lines of plain LangChain that produced what's on screen — the same API as the lab
(`day2/starter/rag_pipeline.py` / `shared/rag.py`).

## Notes

- **Offline-friendly:** embeddings are local by default (`fastembed`, one small
  ONNX download on first run, cached afterwards). If even that fails, pages fall
  back to a hashing mock instead of dying on stage. Only demos 5/6's *answer*
  buttons need a real LLM (`LLM_PROVIDER=mock` keeps them runnable with a canned
  reply; retrieval stays fully real).
- **Sample docs are rigged** (like Day 1's hard-coded tool tables):
  `sample_docs/*.md` restate key ideas in multiple places, so similarity search
  reliably returns near-duplicates and MMR visibly wins. Real corpora do this too.
- **Your `.chroma/` is safe:** the demo indexes into an **in-memory** Chroma
  collection; the lab's persisted index is never touched.
- The LLM is called with `get_llm(temperature=None)` and **no** `max_tokens` cap —
  gpt-5-class reasoning deployments need the headroom.
- Uploading a PDF requires `pypdf` (in `requirements.txt`).
