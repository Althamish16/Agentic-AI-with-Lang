"""
shared/ — small, reusable building blocks that grow across the course.

Each module is introduced on the day noted below and then imported by later days,
so the labs compound instead of resetting:

    schemas.py        Day 1  Pydantic shapes (ResearchPlan, ...)
    planner.py        Day 1  the LCEL "planner seed" chain
    rag.py            Day 2  load -> chunk -> embed -> Chroma -> retrieve (+citations)
    tools.py          Day 4  @tool tools: web search, retriever, summarizer, breakable
    memory.py         Day 5  long-term vector memory + message compaction
    research_agent.py Day 6/7 the full LangGraph agent used by Day 7 + the web UI
    pretty.py         (any)  console helpers to make graph state visible
"""
