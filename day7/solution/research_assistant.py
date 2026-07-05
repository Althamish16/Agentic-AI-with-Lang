"""
Day 7 SOLUTION — the COMPLETE Research Assistant (capstone).

Adds to the multi-step agent:
  • a REFLECTION / self-critique node (feedback loop that can auto-revise)
  • a HUMAN-IN-THE-LOOP approval gate via interrupt() before publishing
  • LangSmith tracing across the whole run (opt-in via .env)

The full graph lives in shared/research_agent.py (reused by the web UI). Here we
drive it: stream the nodes, pause at the human gate, then resume.

    python day7/solution/research_assistant.py "Should I use similarity or MMR retrieval?"
    python day7/solution/research_assistant.py --auto "..."     # auto-approve (non-interactive)
    python day7/solution/research_assistant.py --reject "..."   # auto-reject (see revision loop)
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

from langgraph.types import Command

from config import setup_langsmith
from shared.pretty import banner, node, ok, rule, warn
from shared.research_agent import NODE_LABELS, build_research_agent


def get_decision(payload: dict, mode: str) -> str:
    """Return the human's publish decision. `mode` may force auto approve/reject."""
    rule()
    warn("⏸  HUMAN APPROVAL REQUIRED — review the draft before publishing:")
    print("\n" + payload["draft"][:1200] + ("..." if len(payload["draft"]) > 1200 else ""))
    rule()
    if mode == "auto":
        print("(--auto) → approving")
        return "approve"
    if mode == "reject":
        print("(--reject) → rejecting with feedback")
        return "Please add a concrete example and a one-line recommendation."
    ans = input("Approve publish? [y = approve / anything else = reject with that text]: ").strip()
    return "approve" if ans.lower() in {"y", "yes", "approve"} else (ans or "reject")


def pump(app, inp, cfg):
    """Stream node updates; return the interrupt payload if the graph paused, else None."""
    for chunk in app.stream(inp, cfg, stream_mode="updates"):
        if "__interrupt__" in chunk:
            return chunk["__interrupt__"][0].value
        for name, update in chunk.items():
            node(name, NODE_LABELS.get(name, ""))
            if name == "reflect":
                print(f"    verdict: {update.get('verdict')}")
            elif name == "write":
                print(f"    draft ready (revision #{update.get('revisions')})")
            elif name == "research":
                print(f"    answered sub-question #{update.get('cursor')}")
    return None


def main():
    args = sys.argv[1:]
    mode = "interactive"
    if "--auto" in args:
        mode = "auto"; args.remove("--auto")
    if "--reject" in args:
        mode = "reject"; args.remove("--reject")
    question = " ".join(args).strip() or "Should I use similarity or MMR retrieval for a RAG system?"

    banner("Day 7 — The Complete Research Assistant")
    traced = setup_langsmith()
    ok("LangSmith tracing ENABLED — see https://smith.langchain.com") if traced else print(
        "LangSmith tracing disabled (set LANGSMITH_TRACING=true + LANGSMITH_API_KEY in .env to enable)."
    )
    print(f"Question: {question}\n")

    app = build_research_agent()
    cfg = {"configurable": {"thread_id": "day7-capstone"}}

    payload = pump(app, {"question": question}, cfg)
    while payload is not None:  # loop while the graph keeps pausing at the human gate
        decision = get_decision(payload, mode)
        payload = pump(app, Command(resume=decision), cfg)

    final = app.get_state(cfg).values.get("final", "(no final report)")
    rule("═")
    print("FINAL REPORT:\n")
    print(final)


if __name__ == "__main__":
    main()
