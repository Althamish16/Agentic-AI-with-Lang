# Setup & Run — Research Assistant Studio

Quick guide to install dependencies and start the **backend** (FastAPI, port 5000)
and **frontend** (Vite + React, port 9000) from scratch.

---

## Prerequisites

- **Python** 3.10 or newer — `python --version`
- **Node.js** 18 or newer — `node --version`
- **Git** (optional, only for cloning)

---

## 1) Backend setup (Python + FastAPI)

Open a terminal at the **repo root** (`D:\Agentic-AI-Handson`).

### Windows (PowerShell / cmd)

```cmd
:: 1. Create a virtual env
python -m venv .venv

:: 2. Activate it
.\.venv\Scripts\activate

:: 3. Install Python dependencies
pip install -r requirements.txt

:: 4. Configure secrets (once)
copy .env.example .env
:: then open .env in an editor and fill in your Azure OpenAI values
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env
```

### Verify the config

```cmd
python config.py
```

You should see the resolved (non-secret) config printed. If anything is missing,
fix `.env` and re-run.

---

## 2) Frontend setup (Node + Vite)

Open a **second terminal** and go into the `frontend/` folder.

```cmd
cd frontend
npm install
```

That installs React, Vite, Tailwind, and everything else the UI needs.

---

## 3) Start the app (two terminals)

You need **both** the backend and frontend running at the same time.

### Terminal 1 — Backend (FastAPI, http://localhost:5000)

From the **repo root** with the venv active:

```cmd
.\.venv\Scripts\activate
python backend\app.py
```

Leave this running. It exposes:
- `GET  /api/health` — non-secret config snapshot
- `GET  /api/run` — SSE stream of a full agent run
- `GET  /api/resume` — continue after human approval
- `GET  /api/lab/{day}` — per-day live demo runner (Days 1–7)

### Terminal 2 — Frontend (Vite dev server, http://localhost:9000)

From the **`frontend/`** folder:

```cmd
cd frontend
npm run dev
```

Vite will print a local URL. Open it in your browser:

> **http://localhost:9000**

That's it — you should see the Research Assistant Studio with Overview, Day 1–7,
and Studio tabs.

---

## 4) One-shot commands (copy-paste)

### Windows — start backend

```cmd
cd /d D:\Agentic-AI-Handson
.\.venv\Scripts\activate
python backend\app.py
```

### Windows — start frontend

```cmd
cd /d D:\Agentic-AI-Handson\frontend
npm run dev
```

### macOS / Linux — start backend

```bash
cd ~/Agentic-AI-Handson
source .venv/bin/activate
python backend/app.py
```

### macOS / Linux — start frontend

```bash
cd ~/Agentic-AI-Handson/frontend
npm run dev
```

---

## 5) Run a day's CLI demo (no UI needed)

With the venv active from the repo root:

```cmd
python day1\solution\plan.py "How does RAG improve LLM accuracy?"
python day2\solution\rag_pipeline.py "What is MMR and when should I use it?"
python day3\solution\research_graph.py "How do vector databases power RAG?"
python day4\solution\tool_agent.py "What is MMR and how does it relate to agent memory?"
python day5\solution\memory_agent.py
python day6\solution\multi_agent.py "How do agents use memory and tools?"
python day7\solution\research_assistant.py "Should I use similarity or MMR retrieval?"
```

Day 1 slide demos (one per concept):

```cmd
python day1\demos\demo_02_next_token.py
python day1\demos\demo_03_prompt.py
:: ... through demo_13_capstone.py
```

Day 2 live demo (interactive RAG pipeline web app — chunking sliders,
embedding map, similarity vs MMR, citations, break-it mode):

```cmd
streamlit run day2\demos\app.py
:: or any single page standalone, e.g.
streamlit run day2\demos\demo_04_retrieval.py
```

---

## 6) Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` on startup | Venv isn't active. Run `.\.venv\Scripts\activate`. |
| Frontend shows "Failed to fetch" | Backend isn't running on port 5000. Start Terminal 1. |
| Port 5000 already in use | Kill the old process: `Get-Process -Name python \| Stop-Process -Force` |
| Port 9000 already in use | Kill node: `Get-Process -Name node \| Stop-Process -Force` |
| Frontend edits don't show up | Hard-refresh browser: **Ctrl + Shift + R** |
| Azure OpenAI 401 / 404 | Check `AZURE_OPENAI_*` values in `.env`, then `python config.py` |
| First Day-2 run is slow | Downloads a ~130 MB local embedding model once, then works offline |

---

## 7) Stop the app

- Press **Ctrl + C** in each terminal.
- Or kill by process name (Windows PowerShell):
  ```powershell
  Get-Process -Name python | Stop-Process -Force
  Get-Process -Name node   | Stop-Process -Force
  ```
