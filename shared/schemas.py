"""
schemas.py — Pydantic shapes shared across days.

Introduced Day 1 (the planner's structured output) and reused everywhere the agent
needs a typed plan or a cited answer.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    """The 'planner seed' output: a topic restatement + exactly three sub-questions.

    Using a typed schema (instead of free text) is what lets Day 1's output flow
    cleanly into Day 3's graph state and beyond.
    """

    topic: str = Field(description="A concise, one-line restatement of the research topic.")
    sub_questions: List[str] = Field(
        description="Exactly three focused, non-overlapping sub-questions that, answered together, cover the topic."
    )


class Citation(BaseModel):
    """A single source reference attached to an answer."""

    source: str = Field(description="File name or URL the fact came from.")
    quote: str = Field(default="", description="Short supporting snippet from the source.")


class AnswerWithCitations(BaseModel):
    """A grounded answer plus the sources that support it (Day 2 onward)."""

    answer: str = Field(description="The synthesized answer.")
    citations: List[Citation] = Field(default_factory=list, description="Sources supporting the answer.")
