"""
config.py — the ONE place every lab reads its model / provider / store settings.

Why this file exists
--------------------
The whole course is provider-swappable. Lab code (day1..day7 + the web UI) never
reads environment variables or constructs an LLM directly — it calls:

    from config import get_llm, get_embeddings, get_vectorstore_dir, settings

So to swap OpenAI ↔ Azure ↔ a local mock, you edit ONE .env value, not lab code.

Everything is read from `.env` (see `.env.example`) via python-dotenv.
"""

from __future__ import annotations

import os
import sys
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load .env once, from the repo root (this file's directory), so any day can be
# launched from its own folder and still find the same configuration.
REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(REPO_ROOT / ".env")

# Chroma's anonymous telemetry throws noisy (harmless) errors on some versions —
# turn it off so lab output stays clean. Must be set before chromadb is imported.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_ENABLED", "False")

# Keep teaching output readable: silence Chroma's telemetry/info logging and a
# cosmetic langgraph pending-deprecation warning. (Real errors still raise.)
import logging as _logging
import warnings as _warnings

_logging.getLogger("chromadb").setLevel(_logging.CRITICAL)
# langgraph emits a one-time PendingDeprecationWarning when its serializer imports
# (and langchain forces it past normal filters). Trigger that import here with
# stderr redirected, so the noise is swallowed once, before any lab code runs.
import contextlib as _contextlib
import io as _io

with _contextlib.redirect_stderr(_io.StringIO()), _warnings.catch_warnings():
    _warnings.simplefilter("ignore")
    try:
        import langgraph.checkpoint.serde.jsonplus  # noqa: F401
    except Exception:
        pass

# --- Make Windows terminals behave: UTF-8 output + ANSI colors ---
# The labs print box-drawing chars, ✓/⚠ glyphs and ANSI colors to make graph
# state visible. Windows' default cp1252 console would crash on those, so we
# switch stdout/stderr to UTF-8 and enable virtual-terminal (ANSI) processing.
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        import ctypes

        _k = ctypes.windll.kernel32
        _k.SetConsoleMode(_k.GetStdHandle(-11), 7)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────────
def _env(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key)
    return val if val not in (None, "") else default


def _require(key: str) -> str:
    """Fetch a required env var or fail with a friendly, actionable message
    (not a stack trace) — teaching labs should never dump tracebacks for a
    missing key."""
    val = os.getenv(key)
    if not val:
        raise SystemExit(
            f"\n[config] Missing required environment variable: {key}\n"
            f"         Copy .env.example to .env and fill it in, "
            f"or switch providers (e.g. LLM_PROVIDER=mock).\n"
        )
    return val


def _normalize_azure_endpoint(raw: str) -> str:
    """Azure endpoints get pasted in many shapes. We only want the *resource
    base*, e.g.  https://my-res.services.ai.azure.com

    Handles:
      https://my-res.services.ai.azure.com/openai/v1/responses  -> base
      https://my-res.openai.azure.com/                          -> base
      https://my-res.services.ai.azure.com                      -> base
    """
    raw = raw.strip().rstrip("/")
    marker = "/openai"
    if marker in raw:
        raw = raw[: raw.index(marker)]
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Central settings snapshot (handy for the UI /health endpoint and smoke tests)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Settings:
    llm_provider: str = field(default_factory=lambda: (_env("LLM_PROVIDER", "azure") or "azure").lower())
    embeddings_provider: str = field(default_factory=lambda: (_env("EMBEDDINGS_PROVIDER", "fastembed") or "fastembed").lower())

    # Azure
    azure_endpoint_raw: str = field(default_factory=lambda: _env("AZURE_OPENAI_ENDPOINT", "") or "")
    azure_api_version: str = field(default_factory=lambda: _env("AZURE_OPENAI_API_VERSION", "2025-04-01-preview") or "2025-04-01-preview")
    azure_chat_deployment: str = field(default_factory=lambda: _env("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "") or "")
    azure_embed_deployment: str = field(default_factory=lambda: _env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-small") or "text-embedding-3-small")

    # OpenAI
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini")

    # Embeddings
    fastembed_model: str = field(default_factory=lambda: _env("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5") or "BAAI/bge-small-en-v1.5")

    # Vector store
    chroma_dir: str = field(default_factory=lambda: _env("CHROMA_DB_DIR", ".chroma") or ".chroma")
    chroma_collection: str = field(default_factory=lambda: _env("CHROMA_COLLECTION", "research_assistant") or "research_assistant")

    # Tools
    web_search_provider: str = field(default_factory=lambda: (_env("WEB_SEARCH_PROVIDER", "mock") or "mock").lower())

    # Ports (from .env — backend_port / frontend_port)
    backend_port: int = field(default_factory=lambda: int(_env("backend_port", "5000") or "5000"))
    frontend_port: int = field(default_factory=lambda: int(_env("frontend_port", "9000") or "9000"))

    @property
    def azure_endpoint(self) -> str:
        return _normalize_azure_endpoint(self.azure_endpoint_raw) if self.azure_endpoint_raw else ""

    def summary(self) -> dict:
        """Non-secret snapshot — safe to log or return from the UI."""
        return {
            "llm_provider": self.llm_provider,
            "embeddings_provider": self.embeddings_provider,
            "azure_endpoint": self.azure_endpoint or None,
            "azure_chat_deployment": self.azure_chat_deployment or None,
            "azure_api_version": self.azure_api_version,
            "openai_model": self.openai_model,
            "fastembed_model": self.fastembed_model,
            "chroma_dir": self.chroma_dir,
            "chroma_collection": self.chroma_collection,
            "web_search_provider": self.web_search_provider,
            "backend_port": self.backend_port,
            "frontend_port": self.frontend_port,
        }


settings = Settings()


# ─────────────────────────────────────────────────────────────────────────────
# LLM factory
# ─────────────────────────────────────────────────────────────────────────────
def get_llm(temperature: float | None = 0.0, streaming: bool = False, **kwargs):
    """Return a LangChain chat model based on LLM_PROVIDER.

    `temperature=None` means "don't send a temperature" — some newer Azure
    deployments (gpt-5 / o-series) only accept their default temperature, so we
    make it easy to omit. Extra kwargs pass straight through to the model.
    """
    provider = settings.llm_provider

    if provider == "azure":
        from langchain_openai import AzureChatOpenAI

        endpoint = settings.azure_endpoint or _normalize_azure_endpoint(_require("AZURE_OPENAI_ENDPOINT"))
        params = dict(
            azure_endpoint=endpoint,
            azure_deployment=_require("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
            api_version=settings.azure_api_version,
            api_key=_require("AZURE_OPENAI_API_KEY"),
            streaming=streaming,
            **kwargs,
        )
        if temperature is not None:
            params["temperature"] = temperature
        return AzureChatOpenAI(**params)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        params = dict(
            model=settings.openai_model,
            api_key=_require("OPENAI_API_KEY"),
            streaming=streaming,
            **kwargs,
        )
        if temperature is not None:
            params["temperature"] = temperature
        return ChatOpenAI(**params)

    if provider == "mock":
        return MockChatModel()

    raise SystemExit(f"[config] Unknown LLM_PROVIDER={provider!r}. Use azure | openai | mock.")


# ─────────────────────────────────────────────────────────────────────────────
# Embeddings factory
# ─────────────────────────────────────────────────────────────────────────────
def get_embeddings():
    """Return a LangChain Embeddings object based on EMBEDDINGS_PROVIDER.

    Default is `fastembed`: a small local ONNX model (no torch, no cloud), so
    Day 2's RAG works even without an Azure *embeddings* deployment.
    """
    provider = settings.embeddings_provider

    if provider == "fastembed":
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=settings.fastembed_model)

    if provider == "azure":
        from langchain_openai import AzureOpenAIEmbeddings

        endpoint = settings.azure_endpoint or _normalize_azure_endpoint(_require("AZURE_OPENAI_ENDPOINT"))
        return AzureOpenAIEmbeddings(
            azure_endpoint=endpoint,
            azure_deployment=_require("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
            api_version=settings.azure_api_version,
            api_key=_require("AZURE_OPENAI_API_KEY"),
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small", api_key=_require("OPENAI_API_KEY"))

    if provider == "fake":
        return FakeDeterministicEmbeddings()

    raise SystemExit(f"[config] Unknown EMBEDDINGS_PROVIDER={provider!r}. Use fastembed | azure | openai | fake.")


def get_vectorstore_dir() -> Path:
    """Absolute path to the Chroma directory (kept out of git via .gitignore)."""
    p = Path(settings.chroma_dir)
    if not p.is_absolute():
        p = REPO_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# LangSmith observability (Day 7) — opt-in via env
# ─────────────────────────────────────────────────────────────────────────────
def setup_langsmith() -> bool:
    """Enable LangSmith tracing if LANGSMITH_TRACING=true and a key is present.
    Returns True if tracing was turned on. Called by Day 7 + the backend."""
    if (_env("LANGSMITH_TRACING", "false") or "false").lower() != "true":
        return False
    if not _env("LANGSMITH_API_KEY"):
        print("[config] LANGSMITH_TRACING=true but LANGSMITH_API_KEY is empty — tracing disabled.")
        return False
    # LangChain reads these standard vars automatically.
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", _env("LANGSMITH_PROJECT", "research-assistant-labs"))
    os.environ.setdefault("LANGCHAIN_PROJECT", os.environ["LANGSMITH_PROJECT"])
    os.environ.setdefault("LANGSMITH_ENDPOINT", _env("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Offline mock LLM — best-effort, so Days 1–3 can run with LLM_PROVIDER=mock
# ─────────────────────────────────────────────────────────────────────────────
class MockChatModel:
    """A tiny deterministic chat model for offline demos. It is NOT a real LLM —
    it pattern-matches the prompt and returns plausible content. Good enough to
    exercise the plumbing (chains, graphs) without any network. Tool-calling days
    (4+) need a real model."""

    # Duck-typed to look enough like a LangChain Runnable for our usage.
    def invoke(self, input, config=None, **kwargs):
        from langchain_core.messages import AIMessage

        text = _stringify(input)
        return AIMessage(content=self._respond(text))

    def stream(self, input, config=None, **kwargs):
        from langchain_core.messages import AIMessageChunk

        for chunk in self._respond(_stringify(input)).split(" "):
            yield AIMessageChunk(content=chunk + " ")

    def _respond(self, prompt: str) -> str:
        low = prompt.lower()
        if "json" in low and ("sub" in low and "question" in low):
            return (
                '{"topic": "Mock topic derived offline", '
                '"sub_questions": ["What is it?", "Why does it matter?", "How is it applied?"]}'
            )
        if "critique" in low or "reflect" in low:
            return "The draft is reasonable but could add one concrete example. Verdict: PASS."
        return "This is a deterministic offline mock answer for teaching the pipeline."

    def __or__(self, other):  # allow `mock | parser` LCEL composition
        from langchain_core.runnables import RunnableLambda

        return RunnableLambda(self.invoke) | other


def _stringify(input) -> str:
    """Flatten whatever LCEL hands the model into plain text."""
    try:
        from langchain_core.prompt_values import PromptValue

        if isinstance(input, PromptValue):
            return input.to_string()
    except Exception:
        pass
    if isinstance(input, str):
        return input
    if isinstance(input, list):
        return "\n".join(getattr(m, "content", str(m)) for m in input)
    return str(input)


# ─────────────────────────────────────────────────────────────────────────────
# Fully-offline deterministic embeddings (no downloads) — EMBEDDINGS_PROVIDER=fake
# ─────────────────────────────────────────────────────────────────────────────
class FakeDeterministicEmbeddings:
    """Hashing-based embeddings: same text -> same vector, similar words -> some
    overlap. Zero downloads, zero network. For CI / airplane mode only; retrieval
    quality is intentionally crude."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for token in text.lower().split():
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        # L2 normalize so cosine similarity behaves.
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


# ─────────────────────────────────────────────────────────────────────────────
# CLI: `python config.py` prints a non-secret config snapshot.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    print("Research Assistant Labs — resolved configuration:\n")
    print(json.dumps(settings.summary(), indent=2))
