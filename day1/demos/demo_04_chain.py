"""
LIVE DEMO — Slide 4: "Chain: A Fixed Pipeline"

Goal on screen: a chain is a PREDEFINED sequence — every input marches through the
same steps, in the same order, with no decisions. We build the slide's exact
pipeline with LCEL (`|` composition, same as the Day 1 lab):

    Customer question → Rewrite → Search knowledge base → Answer

Then we run TWO inputs through it:
  1) an in-scope question   → the pipeline shines
  2) an out-of-scope one    → the pipeline marches through anyway and dead-ends,
                              because a chain has no step where it could DECIDE
                              to do something different (that's Slide 7 — agents).

Run:
    python day1/demos/demo_04_chain.py
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from demo_common import banner, step, note, result, takeaway, DIM, RESET
from config import get_llm

# ── A tiny help-center "knowledge base" (step 2 searches this) ───────────────
KB = {
    "password": "To reset your password: Settings → Security → 'Reset password'. "
                "A reset link is emailed and expires in 30 minutes.",
    "refunds": "Refunds are processed in 5–7 business days to the original payment "
               "method. Premium members may choose instant store credit instead.",
    "shipping": "Standard shipping takes 3–5 business days. Delays beyond 48 hours "
                "trigger a free reshipment for Premium customers.",
}


def search_kb(query: str) -> str:
    """Deterministic keyword search — deliberately dumb, so the pipeline is transparent."""
    q_words = set(query.lower().replace("?", "").split())
    best_key, best_score = None, 0
    for key, doc in KB.items():
        score = len(q_words & set((key + " " + doc).lower().split()))
        if score > best_score:
            best_key, best_score = key, score
    if best_key is None or best_score < 2:
        return "NO RELEVANT DOCUMENT FOUND."
    return f"[doc:{best_key}] {KB[best_key]}"


def tap(label: str, key: str) -> RunnableLambda:
    """A pass-through pipeline stage that just prints — so the fixed steps are visible."""
    def _show(d: dict) -> dict:
        step(label)
        result(str(d[key]))
        return d
    return RunnableLambda(_show)


def build_pipeline():
    """Compose the slide's pipeline with LCEL — exactly like the Day 1 lab's `|`."""
    llm = get_llm(temperature=None)

    rewrite = (
        ChatPromptTemplate.from_messages(
            [
                ("system", "Rewrite the customer's message as a short keyword search query "
                           "for a help-center. Output ONLY the query."),
                ("human", "{question}"),
            ]
        )
        | llm
        | StrOutputParser()
    )

    answer = (
        ChatPromptTemplate.from_messages(
            [
                ("system", "Answer the customer in 1–2 sentences using ONLY the document below. "
                           "If the document does not answer the question, reply exactly: "
                           "\"Sorry — I couldn't find this in the knowledge base.\""),
                ("human", "Document:\n{doc}\n\nCustomer question: {question}"),
            ]
        )
        | llm
        | StrOutputParser()
    )

    # The pipeline. Fixed at build time — every invoke() walks these same steps:
    return (
        RunnablePassthrough.assign(query=rewrite)                        # STEP 1
        | tap("STEP 1 · REWRITE → search query", "query")
        | RunnablePassthrough.assign(doc=RunnableLambda(lambda d: search_kb(d["query"])))  # STEP 2
        | tap("STEP 2 · SEARCH KB → best document", "doc")
        | answer                                                          # STEP 3
    )


def main() -> None:
    banner(
        "SLIDE 4 · Chain: A Fixed Pipeline",
        "Input → Rewrite → Search KB → Answer. Same steps, same order, every time.",
        "one input that fits the pipeline, one that doesn't — the chain can't tell the difference.",
    )
    note("chain = rewrite | search_kb | answer   (composed ONCE with LCEL's `|` — like the lab)")
    chain = build_pipeline()

    # ── Run 1: the pipeline was designed for exactly this ───────────────────
    print(f"\n{DIM}{'─' * 74}{RESET}")
    q1 = "Hey, I can't get into my account — how do I reset my password?"
    step("RUN 1 · IN-SCOPE INPUT")
    result(q1)
    final1 = chain.invoke({"question": q1})
    step("STEP 3 · ANSWER from the document")
    result(final1.strip())
    note("Rewrite → search → answer. Predictable, fast, great — the input fit the design.")

    # ── Run 2: same fixed steps, wrong kind of problem ───────────────────────
    print(f"\n{DIM}{'─' * 74}{RESET}")
    q2 = "What's 15% of 80?"
    step("RUN 2 · OUT-OF-SCOPE INPUT", "watch it march through the SAME steps anyway")
    result(q2)
    final2 = chain.invoke({"question": q2})
    step("STEP 3 · ANSWER from the document")
    result(final2.strip())
    note("Trivial math — but no step in the chain can DECIDE to skip the KB or grab a "
         "calculator. The workflow was frozen before the input arrived.")

    takeaway("Chains are predictable and cheap — and blind. Choosing a different path IS the agent (Slide 7).")


if __name__ == "__main__":
    main()
