"""
planner.py — the Day 1 "planner seed", promoted to shared/ so Day 3+ reuse it.

It is a classic LCEL chain:   PromptTemplate -> LLM -> PydanticOutputParser
turning a research question into a typed ResearchPlan (topic + 3 sub-questions).
"""

from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import get_llm
from shared.schemas import ResearchPlan

# The parser both (a) validates the model's JSON into a ResearchPlan and
# (b) generates the format instructions we inject into the prompt.
_parser = PydanticOutputParser(pydantic_object=ResearchPlan)

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a meticulous research planner. Given a research question, restate the "
            "core topic in one line and break it into exactly THREE focused, non-overlapping "
            "sub-questions that together fully cover the topic. Be specific and concrete.",
        ),
        # We pass the parser's format instructions so the model knows the exact JSON shape.
        ("human", "Research question:\n{question}\n\n{format_instructions}"),
    ]
).partial(format_instructions=_parser.get_format_instructions())


def build_planner_chain(llm=None):
    """Return the composed LCEL chain (prompt | llm | parser).

    `llm=None` -> use the shared config's default model. Pass your own to reuse the
    chain with a different temperature/model in later days.
    """
    llm = llm or get_llm(temperature=0)
    return _PROMPT | llm | _parser


def plan_research(question: str, llm=None) -> ResearchPlan:
    """Convenience wrapper used by Day 3+ and the web UI."""
    return build_planner_chain(llm).invoke({"question": question})
