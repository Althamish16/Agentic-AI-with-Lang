"""
Day 4 SOLUTION — a tool-calling agent in LangGraph (single-file reference).

    START → agent → (tools_condition) → tools → agent → … → END
              ▲__________________________________|

This file is the *compact* version of what the demos in `day4/demos/` teach
one at a time. If you're stepping through the material for the first time,
open the demos folder instead:

    day4/demos/demo_01_tool_belt.py         # @tool = function + docstring-as-prompt
    day4/demos/demo_02_bind_and_route.py    # bind_tools + tools_condition
    day4/demos/demo_03_broken_tool.py       # errors as strings, never as raises
    day4/demos/demo_04_vague_vs_specific.py # docstrings ARE prompts
    day4/demos/demo_05_retry_backoff.py     # retry wrapper (stretch)

Run:
    python day4/solution/tool_agent.py
    python day4/solution/tool_agent.py "What is MMR and how does it help RAG?"
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "day4" / "demos"))

import config  # noqa: E402 — import FIRST: loads .env and quiets langgraph/chroma noise

# The tool belt + graph builder live in demo_common so every Day 4 file uses
# the same wiring. See day4/demos/demo_common.py for the annotated source.
from demo_common import banner, build_agent, rule, run_agent  # noqa: E402


def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or "What is MMR and how does it relate to agent memory?"
    banner(
        "DAY 4 · SOLUTION — Tool-calling agent",
        "bind_tools + ToolNode + tools_condition, all in one graph.",
        f"Q: {question!r}",
    )

    app = build_agent()                    # 3 tools bound; loop wired
    answer = run_agent(app, question)      # print each turn's raw tool_call JSON

    rule("═")
    print("FINAL ANSWER:\n")
    print(answer)


if __name__ == "__main__":
    main()
