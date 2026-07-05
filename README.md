# Research Assistant Labs — Agentic AI with LangChain & LangGraph

A 7-day, instructor-led course where **one project grows a new layer each day**. You
start with a single LCEL chain and finish with a complete, self-improving **Research
Assistant** — plus a polished **web UI** that streams the agent's thinking live.

> Everything runs on **Azure OpenAI** (chat) + **local embeddings** (fastembed, no
> extra deployment needed). All model/provider settings live in one place:
> [`config.py`](config.py), driven by [`.env`](.env.example). Swap providers without
> touching lab code.

---

## What you build, day by day

| Day | Concept | What carries over |
|----|---------|-------------------|
| **1** | Chains vs Agents vs Tools · prompt templates · **output parsers** | The **planner seed** → `shared/planner.py` |
| **2** | Loaders · chunking · embeddings · **RAG** over `data/` | The retriever → `shared/rag.py` |
| **3** | **LangGraph** core: Planner→Executor→Synthesize with a looping conditional edge | Reuses Day 1 + Day 2; skeleton for all later days |
| **4** | **Tools** & orchestration: `bind_tools`, `ToolNode`, retry vs crash | Tool belt → `shared/tools.py` |
| **5** | **Memory**: checkpointer + `thread_id`, long-term vector memory, compaction | Memory → `shared/memory.py` |
| **6** | **Multi-agent** supervisor→sub-agents · kill & **resume** a long run | Reuses Day 1/2/5 |
| **7** | **Reflection** loop · **human-in-the-loop** (`interrupt()`) · **LangSmith** | The complete agent → `shared/research_agent.py` (also powers the UI) |

Each `dayN/` has a self-contained `README.md`, a `starter/` (with `# TODO (lab):`
gaps) and a complete, runnable `solution/`.

---

## Setup (once)

**Prerequisites:** Python 3.10+ and (for the web UI) Node 18+.

```bash
# 1) Create & activate a virtual env
python -m venv .venv
#   PowerShell:
.\.venv\Scripts\Activate.ps1
#   Git Bash / macOS / Linux:
source .venv/Scripts/activate        # (Windows)   |   source .venv/bin/activate (mac/linux)

# 2) Install Python deps
pip install -r requirements.txt

# 3) Configure secrets
copy .env.example .env                # PowerShell:  copy   |  bash:  cp .env.example .env
#   then edit .env and fill in your Azure OpenAI values (already set for this course).
```

Verify your configuration any time:
```bash
python config.py            # prints the resolved (non-secret) config
```

> **First run note:** Day 2 downloads a small local embedding model (~130 MB) once,
> then works fully offline.

---

## Run any day

From the repo root with the venv active (or just prefix with `.venv\Scripts\python.exe`):

| Day | Solution command |
|----|------------------|
| 1 | `python day1/solution/plan.py "How does RAG improve LLM accuracy?"` |
| 2 | `python day2/solution/rag_pipeline.py "What is MMR and when should I use it?"` |
| 3 | `python day3/solution/research_graph.py "How do vector databases power RAG?"` |
| 4 | `python day4/solution/tool_agent.py "What is MMR and how does it relate to agent memory?"` |
| 5 | `python day5/solution/memory_agent.py` |
| 6 | `python day6/solution/multi_agent.py "How do agents use memory and tools?"`<br>`python day6/solution/resume.py`  *(kill & resume demo)* |
| 7 | `python day7/solution/research_assistant.py "Should I use similarity or MMR retrieval?"` |

Each day also has a `starter/` version (same path, `starter/` instead of `solution/`)
with `# TODO (lab):` gaps for learners. Starters run without crashing and tell you
what's left to complete.

Day 7 flags: `--auto` (auto-approve, non-interactive) · `--reject` (see the revision loop).

---

## The Web UI — Research Assistant Studio 🎛️

A React app with two modes, both powered by the same backend:

1. **Teaching tabs (Overview + Day 1–7).** Each day tab explains the concept in plain
   language with an animated flow diagram + key code, and has a **▶ Run live** button
   that executes *that day's real code* on the backend and shows the result
   (structured plan, RAG citations, node trace, tool calls + retry, memory recall,
   supervisor decisions, reflection…). Great for demoing one concept at a time to
   newcomers.
2. **Studio tab.** Runs the **complete Day 7 agent** and streams its inner workings
   live over SSE: plan → research (with citations) → write → self-critique →
   **human approval gate** → publish.

```bash
# Terminal 1 — API (FastAPI, port 5000)
python backend/app.py

# Terminal 2 — UI (Vite, port 9000)
cd frontend
npm install        # first time only
npm run dev
```

Open **http://localhost:9000**. Ports come from `.env` (`backend_port` /
`frontend_port`); the Vite dev server proxies `/api` → the backend.

**Demo tip (explaining "one process" to beginners):** it's actually *2 processes,
1 agent* — a Python **"brain"** (backend :5000) runs the LangGraph agent, a web
**"face"** (frontend :9000) shows it. Teach each "station" on Days 1–7, then open the
Studio to watch the *whole kitchen run one order end-to-end* — the same code, wired
into one agent. The **Overview** tab spells this out with a diagram.

Backend endpoints: `GET /api/health`, `GET /api/lab/{day}` (per-day live run),
`GET /api/run` + `GET /api/resume` (Studio SSE stream + human approval).

---

## Repo structure

```
research-assistant-labs/
├─ config.py            # ONE place for model/embeddings/vector-store config (reads .env)
├─ requirements.txt     # all Python deps (lightly pinned)
├─ .env.example         # every required variable (copy to .env)
├─ shared/              # building blocks that grow across days
│  ├─ planner.py  rag.py  tools.py  memory.py  research_agent.py  schemas.py  pretty.py
├─ data/                # sample docs for RAG (RAG, vector DBs, LangGraph, prompting, memory)
├─ day1/ … day7/        # each: README.md + starter/ + solution/
├─ backend/             # FastAPI :5000 — streams the Day 7 agent over SSE
└─ frontend/            # React + Vite + Tailwind :9000 — the Studio UI
```

---

## Swapping providers & offline mode

Everything is controlled from `.env`:

| Variable | Options | Notes |
|----------|---------|-------|
| `LLM_PROVIDER` | `azure` · `openai` · `mock` | `mock` = offline deterministic LLM (Days 1–3) |
| `EMBEDDINGS_PROVIDER` | `fastembed` · `azure` · `openai` · `fake` | `fastembed` local default; `fake` = zero-download |
| `WEB_SEARCH_PROVIDER` | `mock` · `tavily` | Day 4 web search; `mock` needs no key |
| `LANGSMITH_TRACING` | `false` · `true` | Day 7 observability (needs `LANGSMITH_API_KEY`) |

Missing keys fail with a **clear message**, not a stack trace. Changing
`EMBEDDINGS_PROVIDER` changes vector dimensions — re-run Day 2 to re-index.

---

## Troubleshooting

- **`Missing required environment variable`** → copy `.env.example` to `.env` and fill it in.
- **UI shows "backend down"** → start `python backend/app.py` (port 5000) first.
- **Azure auth/deploy errors** → check `AZURE_OPENAI_*` in `.env`; run `python config.py`.
- **Chroma dimension mismatch** → you switched embedding models; delete `.chroma/` and re-run Day 2.
- **Windows console glyphs/colors** → handled automatically in `config.py` (UTF-8 + ANSI).

---

*Built for the "Agentic AI with LangChain & LangGraph" course — intermediate → advanced.*
