"""
backend/app.py — FastAPI server (port 5000) for the Research Assistant Studio.

It runs the COMPLETE Day 7 agent (shared/research_agent.py) and streams its inner
workings to the browser over Server-Sent Events (SSE), so the UI can visualize
plan → research → write → reflect → approve → publish in real time.

Endpoints
  GET  /api/health                         non-secret config snapshot
  GET  /api/run?question=&thread_id=        SSE stream of a run (pauses at approval)
  GET  /api/resume?thread_id=&approved=&feedback=   SSE stream continuing after approval

Run it (from the repo root, venv active):
  python backend/app.py
  # or: uvicorn backend.app:app --port 5000 --reload
"""

import json
import pathlib
import sys

# Make the repo root importable so `config` + `shared` resolve regardless of CWD.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import config  # noqa: E402 — import FIRST: loads .env, quiets noise
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from langgraph.types import Command  # noqa: E402

from config import setup_langsmith, settings  # noqa: E402
from shared.memory import get_sqlite_checkpointer  # noqa: E402
from shared.research_agent import NODE_LABELS, build_research_agent  # noqa: E402

# One durable agent for the whole server; thread_id namespaces each conversation.
setup_langsmith()  # enable tracing if configured in .env
CHECKPOINT_DB = pathlib.Path(__file__).with_name("agent_checkpoints.sqlite")
AGENT = build_research_agent(get_sqlite_checkpointer(CHECKPOINT_DB))

app = FastAPI(title="Research Assistant Studio API")

# The Vite frontend runs on :9000 (and 127.0.0.1). Allow it to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.frontend_port}",
        f"http://127.0.0.1:{settings.frontend_port}",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _translate_node(name: str, update: dict) -> dict:
    """Turn a raw graph update into a friendly UI event."""
    ev = {"event": "node", "node": name, "label": NODE_LABELS.get(name, "")}
    if name == "plan":
        ev.update(topic=update.get("topic"), plan=update.get("plan", []))
    elif name == "research":
        findings = update.get("findings") or []
        if findings:
            ev.update(cursor=update.get("cursor"), sub_question=findings[-1]["sub_question"], sources=findings[-1]["sources"])
    elif name == "write":
        ev.update(revision=update.get("revisions"), draft=update.get("draft"))
    elif name == "reflect":
        ev.update(verdict=update.get("verdict"), critique=update.get("critique"))
    elif name == "publish":
        ev.update(final=update.get("final"))
    return ev


def _pump(inp, cfg):
    """Sync generator yielding SSE strings for one (start or resume) invocation.
    Starlette runs this in a threadpool, so blocking LLM calls don't stall the loop."""
    paused = False
    try:
        for chunk in AGENT.stream(inp, cfg, stream_mode="updates"):
            if "__interrupt__" in chunk:
                val = chunk["__interrupt__"][0].value
                yield _sse({"event": "approval_required", "draft": val.get("draft", ""), "critique": val.get("critique", "")})
                paused = True
                continue
            for name, update in chunk.items():
                yield _sse(_translate_node(name, update))
        if not paused:
            final = AGENT.get_state(cfg).values.get("final")
            yield _sse({"event": "final", "final": final})
    except Exception as e:  # surface errors to the UI instead of a dead stream
        yield _sse({"event": "error", "message": f"{type(e).__name__}: {e}"})
    yield _sse({"event": "done"})


@app.get("/api/health")
def health():
    return {"status": "ok", "config": settings.summary(), "langsmith": setup_langsmith()}


# Per-day "Run live" endpoints for the teaching tabs (see backend/labs.py).
try:
    from backend import labs
except ImportError:  # when launched as `python backend/app.py`
    import labs


@app.get("/api/lab/{day}")
def lab(day: int, demo: str = "", question: str = ""):
    """Run one of a day's demos live and return a typed result for the UI."""
    return labs.run(day, demo, question)


@app.get("/api/run")
def run(question: str, thread_id: str = "studio"):
    cfg = {"configurable": {"thread_id": thread_id}}

    def gen():
        yield _sse({"event": "start", "question": question})
        yield from _pump({"question": question}, cfg)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.get("/api/resume")
def resume(thread_id: str = "studio", approved: bool = True, feedback: str = ""):
    cfg = {"configurable": {"thread_id": thread_id}}
    decision = {"approved": approved, "feedback": feedback}

    def gen():
        yield _sse({"event": "resumed", "approved": approved})
        yield from _pump(Command(resume=decision), cfg)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


# Optionally serve a built frontend (frontend/dist) so `python backend/app.py` alone
# can serve the whole app in production. In dev you use the Vite server on :9000.
_dist = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _dist.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    print(f"\n  Research Assistant Studio API → http://localhost:{settings.backend_port}")
    print(f"  Frontend (Vite) expected on   → http://localhost:{settings.frontend_port}\n")
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)
