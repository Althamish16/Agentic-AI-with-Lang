"""
Day 1 SOLUTION — the "planner seed".

An LCEL chain:   ChatPromptTemplate -> LLM -> PydanticOutputParser
that converts a research question into a typed ResearchPlan (topic + 3 sub-Qs).

Mental model for today:
  • CHAIN  = a fixed pipeline you compose with `|` (what we build here).
  • AGENT  = something that decides its own next step (Day 3+).
  • TOOL   = a function the model can call (Day 4+).
"""

import json
import pathlib
import sys
from typing import List

# --- make the repo root importable so `config` resolves no matter the CWD ---
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import get_llm  # the ONE place model/provider config lives


# 1) The structured shape we want back. A typed schema is what lets this step's
#    output feed cleanly into later steps instead of being loose prose.
class ResearchPlan(BaseModel):
    topic: str = Field(description="A concise, one-line restatement of the research topic.")
    sub_questions: List[str] = Field(
        description="Exactly three focused, non-overlapping sub-questions covering the topic."
    )


def build_chain():
    """Compose prompt | llm | parser  — this IS the chain (LCEL)."""
    llm = get_llm(temperature=0)  # deterministic output is easier to parse

    # The parser does double duty: it validates the JSON into a ResearchPlan AND
    # it tells the model exactly what JSON shape to produce.
    parser = PydanticOutputParser(pydantic_object=ResearchPlan)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a meticulous research planner. Restate the topic in one line and break "
                "it into exactly THREE focused, non-overlapping sub-questions that together cover it.",
            ),
            ("human", "Research question:\n{question}\n\n{format_instructions}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    # The `|` operator wires the runnables together into one callable chain.
    return prompt | llm | parser


def main():
    question = " ".join(sys.argv[1:]).strip() or "How does retrieval-augmented generation improve LLM accuracy?"
    print(f"\nResearch question: {question}\n")

    chain = build_chain()
    plan: ResearchPlan = chain.invoke({"question": question})  # -> validated ResearchPlan

    print("Structured plan (validated JSON):")
    print(json.dumps(plan.model_dump(), indent=2))


if __name__ == "__main__":
    main()
