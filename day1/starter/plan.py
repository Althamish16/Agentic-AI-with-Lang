"""
Day 1 STARTER — the "planner seed".

Goal: build an LCEL chain  ChatPromptTemplate -> LLM -> PydanticOutputParser
that turns a research question into a typed ResearchPlan (topic + 3 sub-questions).

Fill in every "# TODO (lab):" and run:
    python day1/starter/plan.py "How does RAG improve LLM accuracy?"
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


# TODO (lab): finish the schema — add a `sub_questions` field that is a list of
#             strings (exactly three). Give each field a helpful description.
class ResearchPlan(BaseModel):
    topic: str = Field(description="A concise, one-line restatement of the research topic.")
    # sub_questions: List[str] = Field(description="...")


def build_chain():
    llm = get_llm(temperature=0)

    # TODO (lab): create a PydanticOutputParser for ResearchPlan.
    parser = None  # <- replace

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a meticulous research planner. Restate the topic in one line and break "
                "it into exactly THREE focused, non-overlapping sub-questions that together cover it.",
            ),
            # TODO (lab): the human message must include BOTH {question} and the
            #             parser's {format_instructions}. Fill the placeholder below.
            ("human", "Research question:\n{question}\n\n{format_instructions}"),
        ]
    )  # TODO (lab): .partial(...) the format_instructions from the parser here.

    # TODO (lab): compose and return the chain with the `|` operator:
    #             prompt | llm | parser
    return None  # <- replace


def main():
    question = " ".join(sys.argv[1:]).strip() or "How does retrieval-augmented generation improve LLM accuracy?"
    print(f"\nResearch question: {question}\n")

    chain = build_chain()
    if chain is None:
        print("⚠ Starter not finished yet: complete the `# TODO (lab):` gaps in build_chain(), then re-run.")
        print("  (See day1/solution/plan.py if you get stuck.)")
        return

    plan = chain.invoke({"question": question})

    print("Structured plan (validated JSON):")
    print(json.dumps(plan.model_dump(), indent=2))


if __name__ == "__main__":
    main()
