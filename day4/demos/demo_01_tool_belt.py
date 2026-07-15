"""
LIVE DEMO 01 — The tool belt (no LLM, no graph).

Goal on screen: prove that `@tool` is *just* a decorated Python function whose
DOCSTRING becomes the model-facing prompt. We inspect each tool's schema, then
call each one directly (like any other function) — no LangGraph yet.

    Key idea: an LLM never "runs" a tool. It only *asks for* one by name +
              args. YOUR code (or ToolNode) is what actually runs it.

Run:
    python day4/demos/demo_01_tool_belt.py
"""

from __future__ import annotations

from demo_common import (
    BOLD,
    DIM,
    RESET,
    banner,
    note,
    result,
    rule,
    search_docs,
    step,
    summarize,
    takeaway,
    web_search,
)


def show_schema(t) -> None:
    """Print what the model sees when this tool is bound to it."""
    schema = t.args_schema.schema() if hasattr(t, "args_schema") and t.args_schema else {}
    props = schema.get("properties", {})
    arg_lines = [f"      {name}: {info.get('type', '?')}" for name, info in props.items()]
    print(f"  {BOLD}{t.name}{RESET}")
    print(f"    description (model sees this as the prompt):")
    for line in t.description.splitlines():
        print(f"      {DIM}{line}{RESET}")
    print(f"    args_schema:")
    for line in arg_lines or ["      (none)"]:
        print(line)
    print()


def main() -> None:
    banner(
        "DAY 4 · DEMO 1 — The tool belt (no LLM yet)",
        "@tool = a plain function whose docstring is the model's prompt.",
        "inspect the three tools, then call each one directly.",
    )

    step("STEP 1 · WHAT DOES THE MODEL ACTUALLY SEE?", "name + description + typed args")
    for t in (search_docs, web_search, summarize):
        show_schema(t)
    note(
        "Rules of thumb for these docstrings: specific, non-overlapping, verb-first. "
        "Vague descriptions cause wrong-tool selection — demo 4 will prove it."
    )

    step("STEP 2 · CALL search_docs DIRECTLY", "it's just a function — invoke it")
    print(search_docs.invoke({"query": "What is MMR retrieval?"})[:500] + " …")
    result("(Same output the Day 2 retriever would give you.)")

    step("STEP 3 · CALL web_search DIRECTLY", "mock provider, deterministic output")
    print(web_search.invoke({"query": "vector database benchmarks"}))

    step("STEP 4 · CALL summarize DIRECTLY", "note: takes TEXT, not a question")
    text = (
        "MMR (Maximal Marginal Relevance) re-ranks retrieved chunks to balance "
        "closeness to the query with diversity between the chunks. This avoids "
        "near-duplicate results that plain similarity search often returns."
    )
    print(summarize.invoke({"text": text}))

    rule()
    takeaway(
        "The tools are ordinary functions. bind_tools() (next demo) just tells "
        "the LLM their names, descriptions, and arg types so it can request them."
    )


if __name__ == "__main__":
    main()
