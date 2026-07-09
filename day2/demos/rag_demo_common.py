"""
rag_demo_common.py — shared plumbing for the Day 2 LIVE DEMO web app.

Design rule (same as day1/demos/demo_common.py): this module holds ONLY
presentation helpers and pipeline *state* shared between pages. The actual
LangChain calls — TextLoader, RecursiveCharacterTextSplitter, embeddings,
Chroma, retrievers, the answer chain — live INSIDE each demo_XX file, so a
student reading one file sees the real API for that stage, complete.

The pipeline state flows through st.session_state so the pages tell ONE story:
    demo_01 loads docs -> demo_02 chunks them -> demo_03 embeds + stores
    -> demo_04 retrieves -> demo_05 answers -> demo_06 breaks it on purpose.
Every page can ALSO run standalone (streamlit run day2/demos/demo_04_...py):
the ensure_*() helpers silently run the earlier stages with defaults.
"""

from __future__ import annotations

import hashlib
import html
import pathlib
import re
import sys

import numpy as np
import streamlit as st

# Make the repo root importable so `config` resolves no matter the CWD, and so
# `import rag_demo_common` works when a page is launched directly.
THIS_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))                    # for `import rag_demo_common`
sys.path.insert(0, str(THIS_DIR.parents[1]))         # repo root -> `import config`

import config  # noqa: E402  (also silences Chroma telemetry + fixes Windows console)
from config import settings  # noqa: E402

SAMPLE_DIR = THIS_DIR / "sample_docs"

# ── Defaults: same numbers as shared/rag.py so the demo matches the lab ──────
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120
DEFAULT_K = 4

# ── Classroom color coding (kept consistent across ALL pages) ────────────────
# Pastel chunk colors with dark text — readable from the back of the room.
PALETTE = [
    "#BBDEFB", "#C8E6C9", "#FFE0B2", "#E1BEE7",
    "#F8BBD0", "#FFF9C4", "#B2EBF2", "#FFCCBC",
    "#D7CCC8", "#DCEDC8", "#B3E5FC", "#F0F4C3",
]
SIM_COLOR = "#1565C0"    # similarity search = blue
MMR_COLOR = "#E65100"    # MMR search        = orange
BOTH_COLOR = "#2E7D32"   # picked by both    = green
DOC_COLORS = ["#1565C0", "#E65100", "#2E7D32", "#6A1B9A", "#C2185B"]  # per source doc

SAMPLE_QUESTIONS = [
    "What chunk size should I use for RAG?",
    "What is MMR and when should I use it instead of similarity search?",
    "Why must the query use the same embedding model as the index?",
    "How can an agent remember things across sessions?",
    "What does a vector database actually do?",
]


def chunk_color(i: int) -> str:
    return PALETTE[i % len(PALETTE)]


def doc_color(i: int) -> str:
    return DOC_COLORS[i % len(DOC_COLORS)]


# ─────────────────────────────────────────────────────────────────────────────
# Page chrome: set_page_config + big classroom fonts + the pipeline sidebar
# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
/* Brand palette (echoes Day 1's indigo→fuchsia deck) */
:root {
  --brand1: #4f46e5; --brand2: #db2777;
  --ink: #0f172a; --muted: #64748b; --line: #e2e8f0;
}

/* Big, readable-from-the-back-row typography */
html { font-size: 18px; }
.block-container { padding-top: 1.3rem; max-width: 1360px; }
h1 { font-size: 2.05rem !important; letter-spacing: -.01em; color: var(--ink); }
h2 { font-size: 1.5rem !important; }
h3 { font-size: 1.2rem !important; }

/* ── Native top navigation → gradient pill SUB-TABS (like Day 1's SlideTabs) ── */
[data-testid="stTopNav"] {
  background: linear-gradient(180deg, #f8fafc, #eef2ff);
  border-bottom: 1px solid var(--line);
  padding: .4rem .7rem;
}
[data-testid="stTopNavLink"] {
  border-radius: 12px; padding: .32rem .85rem; margin: .12rem .1rem;
  font-weight: 700; color: var(--muted); border: 1px solid transparent;
  transition: all .15s ease;
}
[data-testid="stTopNavLink"]:hover {
  background: #ffffff; color: var(--ink); border-color: var(--line);
}
[data-testid="stTopNavLink"][aria-current="page"],
[data-testid="stTopNavLink"][aria-current="page"] * {
  color: #ffffff !important;
}
[data-testid="stTopNavLink"][aria-current="page"] {
  background: linear-gradient(135deg, var(--brand1), var(--brand2));
  box-shadow: 0 4px 14px rgba(79,70,229,.35);
}

/* Run-context chips (which model / embedder is live) under the title */
.ctx { display: flex; flex-wrap: wrap; gap: .4rem; margin: .1rem 0 .7rem; }
.ctx .c {
  font-size: .78rem; font-weight: 700; border-radius: 999px;
  padding: .14rem .65rem; background: #eef2ff; color: #3730a3;
  border: 1px solid #e0e7ff;
}
.ctx .c.ok { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.ctx .c.warn { background: #fef3c7; color: #92400e; border-color: #fde68a; }

/* The flowing document text with colored chunk blocks (demo 2) */
.chunk-text {
  font-size: 1.02rem; line-height: 1.9; white-space: pre-wrap;
  font-family: ui-sans-serif, system-ui, sans-serif; color: #111;
  background: #fff; border: 1px solid #ddd; border-radius: 10px;
  padding: 1rem 1.2rem;
}
.chunk-text span { border-radius: 3px; }

/* Small numbered chip marking where a chunk starts */
.chip {
  display: inline-block; font-size: 0.72rem; font-weight: 700; color: #111;
  border: 1px solid rgba(0,0,0,.35); border-radius: 8px; padding: 0 .35rem;
  margin-right: .15rem; vertical-align: text-top; background: #fff;
}

/* Retrieved-chunk cards (demos 4-6) */
.card {
  border: 1px solid var(--line); border-left: 10px solid #ccc; border-radius: 12px;
  padding: .75rem 1rem; margin-bottom: .7rem; background: #fff; color: #111;
  font-size: .98rem; line-height: 1.55;
  box-shadow: 0 1px 3px rgba(15,23,42,.06), 0 6px 16px rgba(15,23,42,.04);
}
.card .meta { font-size: .82rem; color: #555; margin-bottom: .25rem; }
.card mark { background: #FFF176; padding: 0 2px; border-radius: 2px; }
.dupflag {
  display: inline-block; background: #FFCDD2; color: #B71C1C; font-weight: 700;
  font-size: .8rem; border-radius: 6px; padding: .05rem .45rem; margin-left: .4rem;
}
.okflag {
  display: inline-block; background: #C8E6C9; color: #1B5E20; font-weight: 700;
  font-size: .8rem; border-radius: 6px; padding: .05rem .45rem; margin-left: .4rem;
}

/* Inline citation badges in the generated answer (demo 5) */
.cite {
  display: inline-block; min-width: 1.5em; text-align: center; font-weight: 800;
  color: #111; border: 1.5px solid rgba(0,0,0,.4); border-radius: 7px;
  padding: 0 .3rem; margin: 0 .12rem; font-size: .85rem;
}

/* The per-document chunk map (demo 4): one row of blocks per source file */
.docmap { margin-bottom: .55rem; }
.docmap .lbl { font-size: .85rem; font-weight: 700; margin-bottom: .15rem; }
.docmap .row { display: flex; gap: 2px; height: 30px; }
.docmap .blk {
  flex-grow: 1; border-radius: 4px; background: #E0E0E0; min-width: 6px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: .72rem; font-weight: 800;
}

/* Pipeline stage stepper shown at the top of every page */
.flow { display: flex; flex-wrap: wrap; gap: .3rem; align-items: center;
        font-size: .92rem; margin: .1rem 0 .8rem; padding: .5rem .6rem;
        background: #f8fafc; border: 1px solid var(--line); border-radius: 14px; }
.flow .st { border: 1.5px solid var(--line); border-radius: 10px; padding: .2rem .6rem;
            color: var(--muted); background: #fff; font-weight: 600; }
.flow .st.on { border-color: transparent; color: #fff; font-weight: 800;
               background: linear-gradient(135deg, var(--brand1), var(--brand2));
               box-shadow: 0 3px 10px rgba(79,70,229,.3); }
.flow .arr { color: #cbd5e1; font-weight: 700; }

/* Section-heading accent + primary button polish */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--brand1), var(--brand2));
  border: 0; font-weight: 700; box-shadow: 0 4px 14px rgba(79,70,229,.3);
}
[data-testid="stSidebar"] { background: #fbfcfe; border-right: 1px solid var(--line); }
</style>
"""

# The canonical pipeline, used for the banner on every page.
STAGES = ["Load", "Split", "Embed", "Store", "Embed query", "Retrieve", "Augment", "Generate"]


def inject_css() -> None:
    """Inject the classroom stylesheet once per run. Safe to call repeatedly —
    the top-nav rules apply globally even though app.py renders the tab strip
    before the active page runs page_setup()."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _run_context_chips() -> str:
    """Small chips naming what's actually powering the demo right now — so the
    room always knows which model / embedder is live (matches Day 1's header)."""
    llm = settings.llm_provider
    model = (settings.azure_chat_deployment or settings.openai_model or "—") if llm != "mock" else "offline"
    embed = st.session_state.get("embed_label") or f"{settings.embeddings_provider} (not loaded yet)"
    llm_cls = "c warn" if llm == "mock" else "c"
    embed_cls = "c ok" if ("local" in embed or "fastembed" in embed) else "c"
    return (
        '<div class="ctx">'
        f'<span class="{llm_cls}">🧠 LLM: {html.escape(llm)} · {html.escape(model)}</span>'
        f'<span class="{embed_cls}">🔢 embeddings: {html.escape(embed)}</span>'
        f'<span class="c">🗂️ store: in-memory Chroma (your .chroma/ untouched)</span>'
        "</div>"
    )


def page_setup(icon: str, title: str, active_stages: list[str], tagline: str = "") -> None:
    """Every demo page starts here: page config (guarded — only the first call
    per run wins), classroom CSS, run-context chips, the pipeline stepper with
    THIS page's stage(s) lit up, and the live pipeline-state sidebar."""
    try:
        st.set_page_config(page_title="Day 2 · RAG live demo", page_icon="🔎", layout="wide")
    except Exception:
        pass  # already set by app.py / another page this run
    inject_css()

    st.title(f"{icon} {title}")
    st.markdown(_run_context_chips(), unsafe_allow_html=True)

    bits = []
    for s in STAGES:
        cls = "st on" if s in active_stages else "st"
        bits.append(f'<span class="{cls}">{html.escape(s)}</span>')
    st.markdown(
        '<div class="flow">' + '<span class="arr">→</span>'.join(bits) + "</div>",
        unsafe_allow_html=True,
    )
    if tagline:
        st.caption(tagline)
    _sidebar_state()


def _sidebar_state() -> None:
    """Sidebar = live X-ray of the pipeline: what each stage has produced so far.
    This is what keeps the demo transparent — the audience always sees the
    current docs/chunks/vectors/store, whichever page is on screen."""
    ss = st.session_state
    with st.sidebar:
        st.subheader("🔬 Pipeline state (live)")

        docs = ss.get("docs")
        st.markdown(("✅" if docs else "⬜") + f" **1 · Load** — {len(docs)} docs" if docs else "⬜ **1 · Load** — nothing yet")
        if docs:
            for i, name in enumerate(ss.get("doc_names", [])):
                st.markdown(
                    f'<span style="color:{doc_color(i)}">●</span> {html.escape(name)}',
                    unsafe_allow_html=True,
                )

        chunks = ss.get("chunks")
        if chunks:
            st.markdown(f"✅ **2 · Split** — {len(chunks)} chunks "
                        f"(size {ss.chunk_size}, overlap {ss.chunk_overlap})")
        else:
            st.markdown("⬜ **2 · Split** — not chunked yet")

        vecs = ss.get("vectors")
        if vecs is not None:
            st.markdown(f"✅ **3 · Embed** — {vecs.shape[0]} × **{vecs.shape[1]}-d** vectors")
            st.caption(f"model: {ss.get('embed_label', '?')}")
        else:
            st.markdown("⬜ **3 · Embed** — no vectors yet")

        if ss.get("store") is not None:
            st.markdown(f"✅ **4 · Store** — Chroma · {ss.store_count} vectors")
        else:
            st.markdown("⬜ **4 · Store** — no index yet")

        q = ss.get("last_query")
        st.markdown(f"✅ **5 · Query** — “{html.escape(q)}”" if q else "⬜ **5 · Query** — no question asked yet")

        st.divider()
        if st.button("🔄 Reset pipeline", width="stretch"):
            for key in ("docs", "doc_names", "chunks", "chunk_size", "chunk_overlap",
                        "vectors", "embed_label", "store", "store_fp", "store_count",
                        "last_query", "broken_cache"):
                ss.pop(key, None)
            st.cache_data.clear()
            st.rerun()
        st.caption("Resets docs, chunks, vectors and the index — start the story fresh.")


# ─────────────────────────────────────────────────────────────────────────────
# Embedders — the "course" model (config.get_embeddings) + a deliberately
# different one ("hashing") used by demo 6 to break query/index consistency.
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading embedding model (first run downloads it once)…")
def get_embedder(key: str = "course"):
    """Returns (embedder, human_label). Falls back to offline hashing embeddings
    if the configured model can't load (no internet, missing deployment), so the
    demo NEVER dies on stage."""
    if key == "hashing":
        return config.FakeDeterministicEmbeddings(), "hashing mock (offline, word-count based)"
    try:
        emb = config.get_embeddings()
        emb.embed_query("warm-up ping")  # probe now so failures happen here, not mid-demo
        label = {
            "fastembed": f"fastembed · {settings.fastembed_model} (local, no API)",
            "azure": f"Azure OpenAI · {settings.azure_embed_deployment}",
            "openai": "OpenAI · text-embedding-3-small",
            "fake": "hashing mock (offline)",
        }.get(settings.embeddings_provider, settings.embeddings_provider)
        return emb, label
    except Exception as exc:
        st.warning(f"Configured embeddings unavailable ({exc}) — using offline hashing fallback.")
        return config.FakeDeterministicEmbeddings(), "hashing mock (offline fallback)"


@st.cache_data(show_spinner="Embedding chunks…")
def embed_texts(texts: tuple[str, ...], key: str = "course") -> np.ndarray:
    """Embed a batch of texts -> (n, dim) matrix. Cached, so moving between pages
    (or re-running a page) never re-embeds the same chunks."""
    emb, _ = get_embedder(key)
    return np.asarray(emb.embed_documents(list(texts)), dtype=np.float32)


def embed_query_vec(text: str, key: str = "course") -> np.ndarray:
    emb, _ = get_embedder(key)
    return np.asarray(emb.embed_query(text), dtype=np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# ensure_*() — run earlier pipeline stages with defaults so ANY page can be
# opened first (each demo file is standalone-runnable).
# ─────────────────────────────────────────────────────────────────────────────
def ensure_docs():
    """Stage 1 default: load the three built-in sample_docs/ as Documents."""
    ss = st.session_state
    if ss.get("docs"):
        return ss.docs
    from langchain_community.document_loaders import TextLoader

    docs, names = [], []
    for path in sorted(SAMPLE_DIR.glob("*.md")):
        docs.extend(TextLoader(str(path), encoding="utf-8").load())
        names.append(path.name)
    ss.docs, ss.doc_names = docs, names
    return docs


def ensure_chunks():
    """Stage 2 default: split with the course defaults (800 / 120)."""
    ss = st.session_state
    ss.setdefault("chunk_size", DEFAULT_CHUNK_SIZE)
    ss.setdefault("chunk_overlap", DEFAULT_CHUNK_OVERLAP)
    if ss.get("chunks"):
        return ss.chunks
    return set_chunks(ss.chunk_size, ss.chunk_overlap)


def set_chunks(chunk_size: int, chunk_overlap: int):
    """(Re)split the loaded docs and stamp each chunk with a stable chunk_id.
    Changing the split invalidates everything downstream (vectors + store)."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    ss = st.session_state
    docs = ensure_docs()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, add_start_index=True
    )
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = i
        c.metadata["source"] = pathlib.Path(c.metadata.get("source", "?")).name
    ss.chunk_size, ss.chunk_overlap, ss.chunks = chunk_size, chunk_overlap, chunks
    ss.pop("vectors", None)
    ss.pop("store", None)
    ss.pop("store_fp", None)
    return chunks


def ensure_vectors() -> np.ndarray:
    """Stage 3 default: embed every chunk with the course embedding model."""
    ss = st.session_state
    chunks = ensure_chunks()
    if ss.get("vectors") is not None and len(ss.vectors) == len(chunks):
        return ss.vectors
    _, label = get_embedder("course")
    ss.vectors = embed_texts(tuple(c.page_content for c in chunks), "course")
    ss.embed_label = label
    return ss.vectors


def chroma_client():
    """ONE Chroma client for the whole demo, writing to a throw-away temp folder —
    so the lab's .chroma/ index is never touched. A single shared client (parked on
    the `config` module, which survives Streamlit reruns) because chromadb misbehaves
    when a process creates multiple clients; each demo uses its own collection."""
    client = getattr(config, "_day2_demo_chroma_client", None)
    if client is None:
        import tempfile

        import chromadb

        client = chromadb.PersistentClient(path=tempfile.mkdtemp(prefix="day2_demo_chroma_"))
        config._day2_demo_chroma_client = client
    return client


def ensure_store():
    """Stage 4 default: put chunks + their PRECOMPUTED vectors into an in-memory
    Chroma collection (cosine space), wrapped for LangChain retrievers. We pass
    the same vectors shown on the map — no re-embedding, no magic."""
    from langchain_chroma import Chroma

    ss = st.session_state
    chunks = ensure_chunks()
    vectors = ensure_vectors()
    fp = _fingerprint(ss)
    if ss.get("store") is not None and ss.get("store_fp") == fp:
        return ss.store

    client = chroma_client()
    try:
        client.delete_collection("day2_demo")
    except Exception:
        pass
    col = client.create_collection("day2_demo", metadata={"hnsw:space": "cosine"})
    col.add(
        ids=[str(c.metadata["chunk_id"]) for c in chunks],
        documents=[c.page_content for c in chunks],
        metadatas=[c.metadata for c in chunks],
        embeddings=vectors.tolist(),
    )
    emb, _ = get_embedder("course")
    ss.store = Chroma(client=client, collection_name="day2_demo", embedding_function=emb)
    ss.store_client = client  # demo 6 re-wires this collection with a WRONG query embedder
    ss.store_fp, ss.store_count = fp, col.count()
    return ss.store


def _fingerprint(ss) -> str:
    raw = f"{ss.get('chunk_size')}|{ss.get('chunk_overlap')}|{ss.get('doc_names')}|{len(ss.get('chunks', []))}"
    return hashlib.md5(raw.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Math helpers (pure numpy — no sklearn dependency)
# ─────────────────────────────────────────────────────────────────────────────
def pca_fit(X: np.ndarray):
    """Fit a 2-D PCA projection. Returns (points, project_fn, explained_ratio).
    project_fn maps any new vector (e.g. the query) into the same 2-D map."""
    X = np.asarray(X, dtype=np.float64)
    mu = X.mean(axis=0)
    Xc = X - mu
    _, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    pts = Xc @ Vt[:2].T
    var = S ** 2
    explained = float(var[:2].sum() / var.sum()) if var.sum() else 0.0
    return pts, (lambda v: (np.asarray(v, dtype=np.float64) - mu) @ Vt[:2].T), explained


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(a @ b / denom)


def cosine_matrix(A: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity of the rows of A."""
    A = np.asarray(A, float)
    n = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
    return n @ n.T


# ─────────────────────────────────────────────────────────────────────────────
# HTML renderers (all colors/sizes match the CSS above)
# ─────────────────────────────────────────────────────────────────────────────
_WORD = re.compile(r"[A-Za-z][A-Za-z\-']+")
_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "for",
         "on", "with", "what", "when", "why", "how", "should", "must", "can", "does",
         "do", "i", "my", "it", "that", "this", "use", "using", "instead"}


def highlight_terms(text: str, query: str) -> str:
    """HTML-escape `text`, then <mark> every non-stopword from the query — so the
    audience instantly sees WHY a chunk matched."""
    terms = {w.lower() for w in _WORD.findall(query)} - _STOP
    out = html.escape(text)
    for t in sorted(terms, key=len, reverse=True):
        out = re.sub(rf"(?i)\b({re.escape(t)}\w*)", r"<mark>\1</mark>", out)
    return out


def chunk_card(rank: int, chunk, body_html: str, border: str, extra_badge: str = "",
               score_txt: str = "") -> str:
    """One retrieved-chunk card: rank, source file, position, optional score/badge."""
    meta = chunk.metadata
    return (
        f'<div class="card" style="border-left-color:{border}">'
        f'<div class="meta"><b style="color:{border}">#{rank}</b> · '
        f'📄 {html.escape(str(meta.get("source", "?")))} · chunk {meta.get("chunk_id", "?")} '
        f'· char {meta.get("start_index", "?")}'
        f'{" · " + score_txt if score_txt else ""}{extra_badge}</div>'
        f"{body_html}</div>"
    )


def chunked_doc_html(text: str, spans: list[tuple[int, int, int]]) -> str:
    """Render a document's full text with each chunk as a colored block and each
    OVERLAP region as candy-stripes of the two chunks' colors. `spans` is a list
    of (start, end, global_chunk_index) from the splitter's add_start_index."""
    points = sorted({0, len(text), *(s for s, _, _ in spans), *(e for _, e, _ in spans)})
    parts: list[str] = []
    starts = {s: i for s, _, i in spans}  # where to place the "#n" chip
    for a, b in zip(points, points[1:]):
        seg = html.escape(text[a:b])
        covering = [i for s, e, i in spans if s <= a and b <= e]
        if a in starts:
            i = starts[a]
            parts.append(f'<span class="chip" style="border-color:{chunk_color(i)}">#{i + 1}</span>')
        if len(covering) >= 2:  # overlap: stripes of both chunk colors
            c1, c2 = chunk_color(covering[0]), chunk_color(covering[1])
            style = (f"background: repeating-linear-gradient(135deg, {c1} 0 9px, {c2} 9px 18px);"
                     f"font-weight:600;")
            parts.append(f'<span style="{style}" title="overlap: chunks '
                         f'#{covering[0] + 1} and #{covering[1] + 1} both contain this text">{seg}</span>')
        elif len(covering) == 1:
            parts.append(f'<span style="background:{chunk_color(covering[0])}">{seg}</span>')
        else:  # separator text the splitter dropped between chunks
            parts.append(f'<span style="color:#999">{seg}</span>')
    return f'<div class="chunk-text">{"".join(parts)}</div>'


def doc_map_html(chunks, marks: dict[int, tuple[str, str]]) -> str:
    """The 'where in the documents did retrieval land?' strip: one row per source
    file, one block per chunk (width ∝ chunk length). `marks` maps chunk_id to
    (color, label) — e.g. blue "S1" for similarity rank 1, orange "M2" for MMR."""
    by_src: dict[str, list] = {}
    for c in chunks:
        by_src.setdefault(c.metadata["source"], []).append(c)
    rows = []
    for src, cs in by_src.items():
        blocks = []
        for c in cs:
            cid = c.metadata["chunk_id"]
            color, label = marks.get(cid, ("#E0E0E0", ""))
            title = html.escape(c.page_content[:110].replace('"', "'")) + "…"
            blocks.append(
                f'<div class="blk" style="flex-grow:{len(c.page_content)};background:{color}" '
                f'title="chunk {cid}: {title}">{label}</div>'
            )
        rows.append(f'<div class="docmap"><div class="lbl">📄 {html.escape(src)}</div>'
                    f'<div class="row">{"".join(blocks)}</div></div>')
    return "".join(rows)


def show_code(label: str, code: str) -> None:
    """'The code behind this step' expander — every page uses one so the audience
    can always connect what they SEE to the 5 lines of LangChain that did it."""
    with st.expander(f"👩‍💻 {label}", expanded=False):
        st.code(code.strip(), language="python")
