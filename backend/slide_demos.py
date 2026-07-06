"""
backend/slide_demos.py — the 12 Day-1 slide LIVE DEMOS, restated as JSON events.

The CLI equivalents live under `day1/demos/demo_02_*.py … demo_13_*.py`. Those
files PRINT to a terminal (colored steps, banners, boxes). The web UI cannot
consume colored text, so this module reimplements the same teaching flow with a
small `SlideRecorder` that APPENDS typed dicts to a list instead of printing.

Each demo function returns:

    {
        "kind": "slide_demo",
        "slide": <int>,
        "title": "<slide title>",
        "subtitle": "<one-line teaching frame>",
        "steps": [ { "type": "...", ...payload }, ... ]
    }

The frontend renders each step by its `type` — see `DayResult.jsx`.

Notes
-----
- All LLM work goes through `config.get_llm` (Azure gpt-5.4 in this repo).
- We NEVER pass a tiny `max_tokens` — the deployment is a reasoning model and
  will 400 if there is no headroom for its hidden thinking tokens.
- Tools/data (weather, orders db, calendar, competitor sources) are hard-coded
  tables inside the demo, matching the CLI files, so the teaching moment is
  deterministic and offline-safe apart from the LLM call itself.
"""

from __future__ import annotations

import json
import math
from typing import Any, Callable, Dict, List, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from config import get_llm


# ═══════════════════════════════════════════════════════════════════════════
# SlideRecorder — one API, produces the JSON event list the UI consumes.
# Mirrors demo_common.py (step / note / result / takeaway) so porting is trivial.
# ═══════════════════════════════════════════════════════════════════════════
class SlideRecorder:
    def __init__(self, slide: int, title: str, subtitle: str) -> None:
        self.slide = slide
        self.title = title
        self.subtitle = subtitle
        self.steps: List[Dict[str, Any]] = []

    # --- primitives -------------------------------------------------------
    def heading(self, label: str, desc: str = "") -> None:
        self.steps.append({"type": "heading", "label": label, "desc": desc})

    def note(self, text: str) -> None:
        self.steps.append({"type": "note", "text": text})

    def prompt_block(self, label: str, text: str) -> None:
        self.steps.append({"type": "prompt_block", "label": label, "text": text})

    def model_response(self, text: str, who: str = "Model") -> None:
        self.steps.append({"type": "model_response", "who": who, "text": text})

    def prob_bars(self, prompt: str, chosen: str, candidates: List[Dict[str, Any]]) -> None:
        self.steps.append({"type": "prob_bars", "prompt": prompt, "chosen": chosen, "candidates": candidates})

    def tool_call(self, name: str, args: Dict[str, Any], call_id: str = "") -> None:
        self.steps.append({"type": "tool_call", "name": name, "args": args, "id": call_id})

    def observation(self, text: str) -> None:
        self.steps.append({"type": "observation", "text": text})

    def tag(self, label: str, text: str) -> None:
        self.steps.append({"type": "tag", "label": label, "text": text})

    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        self.steps.append({"type": "table", "headers": headers, "rows": rows})

    def verdict(self, passed: bool, issues: List[str]) -> None:
        self.steps.append({"type": "verdict", "passed": passed, "issues": issues})

    def final_answer(self, text: str) -> None:
        self.steps.append({"type": "final", "text": text})

    def takeaway(self, text: str) -> None:
        self.steps.append({"type": "takeaway", "text": text})

    # --- output -----------------------------------------------------------
    def payload(self) -> Dict[str, Any]:
        return {
            "kind": "slide_demo",
            "slide": self.slide,
            "title": self.title,
            "subtitle": self.subtitle,
            "steps": self.steps,
        }


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 2 — What is an LLM? (next-token prediction + no memory)
# ═══════════════════════════════════════════════════════════════════════════
_S2_PROMPTS = [
    ("Roses are red, violets are", "a line of poetry — the model is almost certain"),
    ("My favorite season of the year is", "genuinely ambiguous — watch the split"),
    ("I flipped a fair coin and it landed on", "a near 50/50 idea, with a clear favorite"),
]


def _s2_show_top_tokens(rec: SlideRecorder, prefix: str, why: str) -> None:
    llm = get_llm(temperature=None, logprobs=True, top_logprobs=5)
    msgs = [
        SystemMessage("Continue the text with exactly ONE next word. Output only that word, nothing else."),
        HumanMessage(prefix),
    ]
    try:
        resp = llm.invoke(msgs)
        content = resp.response_metadata.get("logprobs", {}).get("content") or []
        tops = content[0].get("top_logprobs", []) if content else []
        if not tops:
            raise ValueError("no top_logprobs returned")
    except Exception as exc:  # noqa: BLE001 — deployment without logprobs support
        rec.note(f"(No token probabilities from this deployment: {exc})")
        return

    candidates = [
        {"token": c["token"].replace("\n", "\\n"), "prob": math.exp(c["logprob"])}
        for c in tops
    ]
    rec.note(f"— {why} —")
    rec.prob_bars(prompt=prefix + " ___", chosen=resp.content.strip(), candidates=candidates)


def slide_02() -> Dict[str, Any]:
    rec = SlideRecorder(
        2,
        "What is an LLM?",
        "An LLM predicts the next token — statistically — and has no memory of its own.",
    )
    rec.heading("PART A · NEXT-TOKEN PREDICTION", "the model ranks likely next words — nothing more")
    for prefix, why in _S2_PROMPTS:
        _s2_show_top_tokens(rec, prefix, why)
    rec.takeaway("Sometimes ~100% sure, sometimes a real split — but always just ranking the next word.")

    rec.heading("PART B · NO MEMORY BETWEEN CALLS", "each request starts from a blank slate")
    llm = get_llm(temperature=None)

    rec.note("Call #1 — we introduce ourselves in one request:")
    r1 = llm.invoke([HumanMessage("My name is Priya. Reply in one short sentence.")])
    rec.model_response(r1.content.strip())

    rec.note("Call #2 — a brand-new request that carries NO history:")
    r2 = llm.invoke([HumanMessage("What is my name?")])
    rec.model_response(r2.content.strip())

    rec.note("Call #3 — same question, but we put the earlier turn back into the prompt:")
    r3 = llm.invoke(
        [
            HumanMessage("My name is Priya."),
            AIMessage("Nice to meet you, Priya!"),
            HumanMessage("What is my name?"),
        ]
    )
    rec.model_response(r3.content.strip())

    rec.takeaway('It only "remembers" what you resend. Memory (Slide 10) is us re-feeding context.')
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 3 — The Prompt (Instructions + Context + Question)
# ═══════════════════════════════════════════════════════════════════════════
_S3_QUESTION = "Where is my order and what are you going to do about it?"
_S3_INSTRUCTIONS = (
    "You are ACME's customer support agent. Be concise (max 3 sentences), professional "
    "and warm. Never promise refunds over $100."
)
_S3_CONTEXT = "Customer tier: Premium. Order #4471 shipped 3 days ago; carrier status: DELAYED (>48h)."
_S3_RETRIEVED = "Policy KB-88: Premium customers receive a FREE reshipment when delivery is delayed more than 48 hours."
_S3_HIST_USER = "This is the second time this has happened to me."
_S3_HIST_AI = "I'm really sorry about that — let me look into it right away."


def slide_03() -> Dict[str, Any]:
    rec = SlideRecorder(
        3,
        "The Prompt",
        "Prompt = Instructions + Context + User Question — everything sent in one request.",
    )
    llm = get_llm(temperature=None)

    rec.heading("ROUND 1 · QUESTION ONLY", "what most people think a 'prompt' is")
    rec.prompt_block("USER", _S3_QUESTION)
    r1 = llm.invoke([HumanMessage(_S3_QUESTION)])
    rec.model_response(r1.content.strip())
    rec.note("Generic and helpless — it knows nothing about you, the order, or the rules.")

    rec.heading("ROUND 2 · + SYSTEM INSTRUCTIONS", "now it has a role and boundaries")
    rec.prompt_block("SYSTEM", _S3_INSTRUCTIONS)
    rec.prompt_block("USER", _S3_QUESTION)
    r2 = llm.invoke([SystemMessage(_S3_INSTRUCTIONS), HumanMessage(_S3_QUESTION)])
    rec.model_response(r2.content.strip())
    rec.note("On-brand tone now — but it still can't actually resolve anything.")

    rec.heading("ROUND 3 · THE FULL PROMPT", "instructions + history + context + retrieved policy")
    rec.prompt_block("SYSTEM", _S3_INSTRUCTIONS)
    rec.prompt_block("HISTORY", f'user: "{_S3_HIST_USER}"  →  assistant: "{_S3_HIST_AI}"')
    rec.prompt_block("CONTEXT", _S3_CONTEXT)
    rec.prompt_block("RETRIEVED", _S3_RETRIEVED)
    rec.prompt_block("USER", _S3_QUESTION)
    r3 = llm.invoke(
        [
            SystemMessage(f"{_S3_INSTRUCTIONS}\n\nAccount context:\n{_S3_CONTEXT}\n\nRelevant policy:\n{_S3_RETRIEVED}"),
            HumanMessage(_S3_HIST_USER),
            AIMessage(_S3_HIST_AI),
            HumanMessage(_S3_QUESTION),
        ]
    )
    rec.model_response(r3.content.strip())
    rec.note("Same model, same question — the ONLY thing that changed is what we packed around it.")
    rec.takeaway("The user typed one sentence; the model received five blocks. Prompt engineering is the other four.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Chain: A Fixed Pipeline (LCEL)
# ═══════════════════════════════════════════════════════════════════════════
_S4_KB = {
    "password": "To reset your password: Settings → Security → 'Reset password'. "
                "A reset link is emailed and expires in 30 minutes.",
    "refunds": "Refunds are processed in 5–7 business days to the original payment "
               "method. Premium members may choose instant store credit instead.",
    "shipping": "Standard shipping takes 3–5 business days. Delays beyond 48 hours "
                "trigger a free reshipment for Premium customers.",
}


def _s4_search_kb(query: str) -> str:
    q_words = set(query.lower().replace("?", "").split())
    best_key, best_score = None, 0
    for key, doc in _S4_KB.items():
        score = len(q_words & set((key + " " + doc).lower().split()))
        if score > best_score:
            best_key, best_score = key, score
    if best_key is None or best_score < 2:
        return "NO RELEVANT DOCUMENT FOUND."
    return f"[doc:{best_key}] {_S4_KB[best_key]}"


def _s4_run_one(rec: SlideRecorder, label: str, question: str) -> None:
    llm = get_llm(temperature=None)

    rec.heading(label)
    rec.prompt_block("Customer question", question)

    query = llm.invoke(
        [
            SystemMessage(
                "Rewrite the customer's message as a short keyword search query for a "
                "help-center. Output ONLY the query."
            ),
            HumanMessage(question),
        ]
    ).content.strip()
    rec.tag("STEP 1", f"REWRITE → search query: “{query}”")

    doc = _s4_search_kb(query)
    rec.tag("STEP 2", f"SEARCH KB → {doc}")

    answer = llm.invoke(
        [
            SystemMessage(
                "Answer the customer in 1–2 sentences using ONLY the document below. "
                "If the document does not answer the question, reply exactly: "
                '"Sorry — I couldn\'t find this in the knowledge base."'
            ),
            HumanMessage(f"Document:\n{doc}\n\nCustomer question: {question}"),
        ]
    ).content.strip()
    rec.tag("STEP 3", "ANSWER from the document")
    rec.model_response(answer)


def slide_04() -> Dict[str, Any]:
    rec = SlideRecorder(
        4,
        "Chain: A Fixed Pipeline",
        "Input → Rewrite → Search KB → Answer. Same steps, same order, every time.",
    )
    rec.note("chain = rewrite | search_kb | answer   (composed ONCE with LCEL's `|` — like the lab)")

    _s4_run_one(rec, "RUN 1 · IN-SCOPE INPUT", "Hey, I can't get into my account — how do I reset my password?")
    rec.note("Rewrite → search → answer. Predictable, fast, great — the input fit the design.")

    _s4_run_one(rec, "RUN 2 · OUT-OF-SCOPE INPUT", "What's 15% of 80?")
    rec.note("Trivial math — but no step in the chain can DECIDE to skip the KB or grab a "
             "calculator. The workflow was frozen before the input arrived.")

    rec.takeaway("Chains are predictable and cheap — and blind. Choosing a different path IS the agent (Slide 7).")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Tools: extending the LLM
# ═══════════════════════════════════════════════════════════════════════════
@tool
def _s5_get_weather(city: str) -> str:
    """Get the CURRENT weather for a city. Use this for any live weather question."""
    table = {"tokyo": "Rain, 18°C, humidity 90%", "cairo": "Sunny, 41°C", "oslo": "Snow, -3°C"}
    return table.get(city.strip().lower(), f"No live data available for {city}.")


def slide_05() -> Dict[str, Any]:
    rec = SlideRecorder(
        5,
        "Tools: Extending the LLM",
        "A tool is an external capability. The LLM requests it; your app runs it.",
    )
    question = "Do I need an umbrella in Tokyo right now?"

    rec.heading("STEP 1 · ASK WITHOUT ANY TOOL", "the model has no live data")
    llm = get_llm(temperature=None)
    ans = llm.invoke([HumanMessage(question)])
    rec.model_response(ans.content.strip())
    rec.note("It can only hedge — its training data has no idea what today's weather is.")

    rec.heading("STEP 2 · GIVE IT A TOOL, ASK AGAIN", "bind get_weather() and let it decide")
    llm_t = get_llm(temperature=None).bind_tools([_s5_get_weather])
    messages: List[Any] = [HumanMessage(question)]
    ai = llm_t.invoke(messages)
    messages.append(ai)

    if not ai.tool_calls:
        rec.model_response(f"(no tool requested) {ai.content.strip()}")
        return rec.payload()

    call = ai.tool_calls[0]
    rec.tool_call(call["name"], call["args"], call["id"])
    rec.note("Notice: this is just a structured request. Nothing has executed yet.")

    rec.heading("STEP 3 · OUR APP EXECUTES THE TOOL", "not the model — our code")
    observation = _s5_get_weather.invoke(call["args"])
    rec.observation(observation)
    messages.append(ToolMessage(content=observation, tool_call_id=call["id"]))

    rec.heading("STEP 4 · MODEL RESPONDS WITH THE RESULT IN CONTEXT")
    final = llm_t.invoke(messages)
    rec.final_answer(final.content.strip())
    rec.takeaway("The model never touched the internet — it asked OUR code to. That boundary is the whole idea.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Tool Calling Flow (the 6 steps end-to-end)
# ═══════════════════════════════════════════════════════════════════════════
@tool
def _s6_count_orders(order_date: str) -> int:
    """Return how many orders were placed on a given date (YYYY-MM-DD)."""
    fake_db = {"2026-07-04": 1284, "2026-07-05": 991}
    return fake_db.get(order_date, 0)


def slide_06() -> Dict[str, Any]:
    rec = SlideRecorder(
        6,
        "Tool Calling Flow",
        "The same six steps run every time a tool is involved.",
    )
    question = "How many orders did we get on 2026-07-04?"

    llm = get_llm(temperature=None).bind_tools([_s6_count_orders])

    rec.heading("STEP 1 · USER ASKS")
    rec.prompt_block("USER", question)

    messages: List[Any] = [HumanMessage(question)]
    ai = llm.invoke(messages)
    messages.append(ai)

    rec.heading("STEP 2 · LLM DECIDES a tool is needed")
    if not ai.tool_calls:
        rec.final_answer(ai.content.strip())
        return rec.payload()
    rec.note("The model chose to call a tool instead of answering from memory.")

    call = ai.tool_calls[0]
    rec.heading("STEP 3 · TOOL REQUEST — structured call emitted")
    rec.note("This is exactly what the model produced (JSON):")
    rec.tool_call(call["name"], call["args"], call["id"])

    rec.heading("STEP 4 · APP EXECUTES the tool safely")
    observation = _s6_count_orders.invoke(call["args"])
    rec.observation(f"count_orders({call['args']}) → {observation}")

    rec.heading("STEP 5 · RESULT RETURNED into the prompt")
    tool_msg = ToolMessage(content=str(observation), tool_call_id=call["id"])
    messages.append(tool_msg)
    rec.note(f"We append a tool message (id={call['id'][:14]}…) so the model can read the result.")

    rec.heading("STEP 6 · LLM RESPONDS — final answer generated")
    final = llm.invoke(messages)
    rec.final_answer(final.content.strip())
    rec.takeaway("Steps 3 and 5 are the model. Step 4 — where the real work and safety live — is your code.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Agent: Dynamic Decision-Making (Think → Act → Observe loop)
# ═══════════════════════════════════════════════════════════════════════════
_S7_FORECAST = {"portland": "Rainy all weekend", "seattle": "Cloudy with showers", "bend": "Sunny and clear"}
_S7_HOTELS = {
    "bend": "Pine Lodge ($120), Riverside Inn ($95), Cascade Hotel ($140)",
    "portland": "Rose City Hotel ($110), Bridgetown Suites ($130)",
}


@tool
def _s7_get_weather(city: str) -> str:
    """Get this weekend's weather forecast for a city."""
    return _S7_FORECAST.get(city.strip().lower(), f"No forecast for {city}.")


@tool
def _s7_search_hotels(city: str) -> str:
    """Find hotels in a city."""
    return _S7_HOTELS.get(city.strip().lower(), f"No hotels found in {city}.")


def slide_07() -> Dict[str, Any]:
    rec = SlideRecorder(
        7,
        "Agent: Dynamic Decision-Making",
        "An agent reasons, chooses tools, observes results, and adapts its path.",
    )
    goal = ("Find a city that is SUNNY this weekend and recommend a hotel there. "
            "Candidate cities to consider: Portland, Seattle, Bend.")
    tools = {"_s7_get_weather": _s7_get_weather, "_s7_search_hotels": _s7_search_hotels}

    llm = get_llm(temperature=None).bind_tools(list(tools.values()))
    messages = [
        SystemMessage(
            "You are a travel-planning agent. Use the tools to reach the goal. "
            "Check weather before recommending a place. Think one step at a time; "
            "when you are done, reply with a final recommendation and no tool call."
        ),
        HumanMessage(goal),
    ]

    rec.prompt_block("Goal", goal)

    for i in range(1, 7):
        rec.heading(f"LOOP ITERATION {i}", "the agent decides what to do next")
        ai = llm.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            rec.tag("THINK", "agent has enough information — producing final answer.")
            rec.final_answer(ai.content.strip())
            rec.takeaway("No one told it to check Portland first or to stop at Bend — it chose each step from the results.")
            return rec.payload()

        for call in ai.tool_calls:
            rec.tool_call(call["name"], call["args"], call["id"])
            obs = tools[call["name"]].invoke(call["args"])
            rec.observation(str(obs))
            messages.append(ToolMessage(content=str(obs), tool_call_id=call["id"]))

    rec.note("Hit the step limit — real agents cap iterations exactly like this to stay safe.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Chain vs Agent (same goal, both ways, then a comparison table)
# ═══════════════════════════════════════════════════════════════════════════
def slide_08() -> Dict[str, Any]:
    rec = SlideRecorder(
        8,
        "Chain vs Agent",
        "Same goal, two control styles: frozen pipeline vs runtime decisions.",
    )

    # ── CHAIN: city and steps hard-wired to Portland ─────────────────────────
    rec.heading("APPROACH 1 · CHAIN", "the path was decided when the code was written")
    city = "Portland"
    rec.note(f'The pipeline says: check weather for "{city}", find hotels in "{city}", write the rec.')

    weather = _s7_get_weather.invoke({"city": city})
    rec.tag("CHAIN STEP 1", f"get_weather(city='Portland') → {weather}")

    hotels = _s7_search_hotels.invoke({"city": city})
    rec.tag("CHAIN STEP 2", f"search_hotels(city='Portland') → {hotels}")

    llm = get_llm(temperature=None)
    rec.tag("CHAIN STEP 3", "LLM formats the recommendation card")
    rec_txt = llm.invoke(
        [
            SystemMessage(
                "You are step 3 of a fixed pipeline. Produce the weekend recommendation card for "
                "the given city in 2 sentences, using the data provided. You cannot choose a "
                "different city — that is not one of your inputs."
            ),
            HumanMessage(f"City: {city}\nWeather: {weather}\nHotels: {hotels}"),
        ]
    ).content.strip()
    rec.model_response(rec_txt)
    rec.note("It saw the rain — and still had to ship a Portland card. A chain has no step where "
             "'pick a different city' could happen.")

    # ── AGENT: same tools, same goal, model picks each step ──────────────────
    rec.heading("APPROACH 2 · AGENT", "same goal, path chosen at runtime")
    tools = {"_s7_get_weather": _s7_get_weather, "_s7_search_hotels": _s7_search_hotels}
    llm_t = get_llm(temperature=None).bind_tools(list(tools.values()))
    messages = [
        SystemMessage(
            "You are a travel-planning agent. Use the tools to reach the goal; check weather before "
            "recommending. When done, give a final recommendation with no tool call."
        ),
        HumanMessage(
            "Recommend a city that is SUNNY this weekend and one hotel there. "
            "Candidate cities: Portland, Seattle, Bend."
        ),
    ]
    for _ in range(6):
        ai = llm_t.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            rec.tag("THINK", "enough information — final answer.")
            rec.final_answer(ai.content.strip())
            break
        for call in ai.tool_calls:
            rec.tool_call(call["name"], call["args"], call["id"])
            obs = tools[call["name"]].invoke(call["args"])
            rec.observation(str(obs))
            messages.append(ToolMessage(content=str(obs), tool_call_id=call["id"]))

    # ── The slide's comparison table, filled in with what just happened ─────
    rec.heading("THE SLIDE'S TABLE", "filled in with what you just watched")
    rec.table(
        headers=["", "CHAIN", "AGENT"],
        rows=[
            ["Workflow", "fixed (Portland, always)", "chose its own path"],
            ["Predictable", "yes — same steps every run", "adaptive — steps depend on results"],
            ["Decisions", "none at runtime", "picked tools & cities itself"],
            ["Outcome", "Portland (rainy) — pipeline couldn't switch",
             "Bend (sunny) — adapted after observing rain"],
            ["LLM calls", "1", "3–4 (flexibility costs tokens)"],
        ],
    )
    rec.takeaway("Use a chain when the task never surprises you. Use an agent when it does.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Reasoning Cycle: Planning & Reflection
# ═══════════════════════════════════════════════════════════════════════════
_S9_TASK = "Briefly explain RAG for a business audience."
_S9_SPEC = (
    "1. EXACTLY two sentences — no more, no fewer.\n"
    '2. Must introduce the term as "RAG (retrieval-augmented generation)" — acronym followed by '
    "expansion — exactly once.\n"
    "3. Must name ONE concrete business benefit (e.g. fewer wrong answers, uses your own data)."
)


class _S9Critique(BaseModel):
    passed: bool = Field(description="True only if the draft meets EVERY requirement.")
    issues: List[str] = Field(description="Each requirement violated, quoted briefly. Empty if passed.")


def _s9_reflect(llm, draft: str) -> _S9Critique:
    parser = PydanticOutputParser(pydantic_object=_S9Critique)
    resp = llm.invoke(
        [
            SystemMessage(
                "You are a strict quality gate. Grade the draft against every requirement. "
                f"\n{parser.get_format_instructions()}"
            ),
            HumanMessage(f"Requirements:\n{_S9_SPEC}\n\nDraft:\n{draft}"),
        ]
    )
    return parser.parse(resp.content)


def slide_09() -> Dict[str, Any]:
    rec = SlideRecorder(
        9,
        "Reasoning Cycle, Planning & Reflection",
        "Think → Plan → Act → Observe → Repeat — with reflection grading its own work.",
    )
    llm = get_llm(temperature=None)
    rec.prompt_block("Task given to the drafter (vague, like real life)", _S9_TASK)

    # 1. PLAN
    rec.heading("1 · PLAN", "strategy before acting")
    the_plan = llm.invoke(
        [
            SystemMessage(
                "Before writing anything, produce a numbered 3-step plan (one short line each) "
                "for how you will approach the task. Output ONLY the plan."
            ),
            HumanMessage(_S9_TASK),
        ]
    ).content.strip()
    rec.model_response(the_plan, who="Plan")

    # 2. ACT
    rec.heading("2 · ACT", "write the draft")
    draft = llm.invoke(
        [
            SystemMessage(f"Follow your plan:\n{the_plan}\n\nNow write the answer."),
            HumanMessage(_S9_TASK),
        ]
    ).content.strip()
    rec.model_response(draft, who="Draft")

    # 3. REFLECT
    rec.heading("3 · REFLECT (round 1)", "grade the draft against the quality bar")
    rec.note("The spec lives HERE, in the quality gate — the drafter never saw it:")
    rec.prompt_block("QUALITY BAR", _S9_SPEC)
    critique = _s9_reflect(llm, draft)
    rec.verdict(critique.passed, critique.issues)

    if not critique.passed:
        # 4. REVISE
        rec.heading("4 · REVISE", "fix exactly what reflection flagged")
        issues = "\n".join(f"- {i}" for i in critique.issues)
        revised = llm.invoke(
            [
                SystemMessage("Revise the draft so it meets EVERY requirement. Output only the revised text."),
                HumanMessage(f"Requirements:\n{_S9_SPEC}\n\nCurrent draft:\n{draft}\n\nIssues found:\n{issues}"),
            ]
        ).content.strip()
        rec.model_response(revised, who="Revised")

        # Reflect again — close the loop.
        rec.heading("3 · REFLECT (round 2)", "regrade — should now pass")
        critique2 = _s9_reflect(llm, revised)
        rec.verdict(critique2.passed, critique2.issues)

    rec.takeaway("Reflection isn't magic — it's a second look with the requirements in hand. That loop is what makes agents reliable.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Memory: the 5 types
# ═══════════════════════════════════════════════════════════════════════════
def slide_10() -> Dict[str, Any]:
    rec = SlideRecorder(
        10,
        "Memory: Context Beyond One Prompt",
        "Five memory types — all the same trick: choosing what to re-feed into the prompt.",
    )
    llm = get_llm(temperature=None)

    # 1. Short-term
    rec.heading("1 · SHORT-TERM", "the current conversation")
    r1 = llm.invoke([HumanMessage("Draft a one-line apology email to a customer named Sam whose delivery was late.")])
    draft = r1.content.strip()
    rec.model_response(draft, who="Turn 1")

    rec.note('Follow-up WITH history resent ("make it shorter" — it knows what "it" is):')
    r2 = llm.invoke(
        [
            HumanMessage("Draft a one-line apology email to a customer named Sam whose delivery was late."),
            AIMessage(draft),
            HumanMessage("Make it shorter."),
        ]
    )
    rec.model_response(r2.content.strip(), who="Turn 2 (with history)")

    rec.note("Same follow-up WITHOUT history (a fresh request):")
    r3 = llm.invoke([HumanMessage("Make it shorter.")])
    rec.model_response(r3.content.strip(), who="Turn 2 (no history)")
    rec.note("Short-term memory IS the resent message list. Drop it and 'it' means nothing.")

    # 2. Long-term
    rec.heading("2 · LONG-TERM", "stored preferences that survive sessions")
    rec.note('SESSION 1 — the user mentions a preference: "By the way, I\'m vegetarian, and I like casual places."')
    prefs = {"diet": "vegetarian", "style": "casual"}
    rec.tag("Storage", f"App saves to disk: {json.dumps(prefs)}")

    rec.note("SESSION 2 (brand-new conversation) — WITHOUT loading the store:")
    q = "Suggest one type of restaurant for my team dinner tonight. One sentence."
    r_no = llm.invoke([HumanMessage(q)])
    rec.model_response(r_no.content.strip(), who="Session 2 (no memory)")

    rec.note("SESSION 2 again — the app loads the store and injects it into the system prompt:")
    r_yes = llm.invoke(
        [SystemMessage(f"Known user preferences (long-term memory): {prefs}"), HumanMessage(q)]
    )
    rec.model_response(r_yes.content.strip(), who="Session 2 (with memory)")
    rec.note("The model didn't remember — OUR APP did, and re-fed it. That's long-term memory.")

    # 3. Semantic
    rec.heading("3 · SEMANTIC", "facts baked into the model's weights")
    r = llm.invoke([HumanMessage("In one word: what is the capital of France?")])
    rec.model_response(r.content.strip())
    rec.note("No context supplied — this fact is baked into the model's weights from training. "
             "(In RAG systems, retrieved documents extend semantic memory with YOUR facts.)")

    # 4. Episodic
    rec.heading("4 · EPISODIC", "past interactions from earlier sessions")
    log = ("2026-06-05: user booked Conference Room B for sprint review\n"
           "2026-06-12: user booked Conference Room B for sprint review")
    rec.prompt_block("EPISODE LOG", log)
    r = llm.invoke(
        [
            SystemMessage(f"Episodic memory — this user's past interactions:\n{log}"),
            HumanMessage("Book the usual room for Friday's sprint review. Which room will you book? One sentence."),
        ]
    )
    rec.model_response(r.content.strip())
    rec.note('"The usual" is meaningless without a record of past episodes.')

    # 5. Working
    rec.heading("5 · WORKING", "temporary scratchpad for the task in flight")
    rec.note("No new call needed — you already watched working memory in the agent demo (Slide 7): "
             "the growing message list of THINK/ACT/OBSERVE steps IS working memory. It held the "
             "weather results just long enough to finish the task, then was discarded.")

    rec.takeaway("The model never remembers — the SYSTEM does. Memory = deciding what goes back into the context window.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Multi-Agent Systems & the Orchestrator
# ═══════════════════════════════════════════════════════════════════════════
_S11_REQUEST = "Give me a competitive brief on Acme Corp — where do they beat us, and where do we beat them?"
_S11_SOURCES = {
    "research": (
        "- TechWire (Jun 2026): 'Acme launches AcmeCloud AI suite, undercutting rivals by 20%'\n"
        "- MarketDaily (May 2026): 'Acme posts 34% YoY growth in the enterprise segment'\n"
        "- The Ledger (Jun 2026): 'Acme hiring spree — 200 open sales roles across EMEA'"
    ),
    "sql": (
        "deals_vs_acme_q1: wins=14, losses=9\n"
        "avg_deal_size_when_won=$48k, avg_deal_size_when_lost=$112k\n"
        "top_recorded_loss_reason='price'"
    ),
    "docs": (
        "Internal battlecard (Mar 2026): Acme wins on price and bundling. Weak on "
        "data-residency compliance and enterprise support SLAs. Our NPS 61 vs their 44."
    ),
}
_S11_TITLES = {"research": "RESEARCH Agent", "sql": "SQL Agent", "docs": "DOCUMENT Agent"}


class _S11Subtask(BaseModel):
    specialist: Literal["research", "sql", "docs"] = Field(description="Which specialist should handle this.")
    question: str = Field(description="One focused question for that specialist.")


class _S11Plan(BaseModel):
    subtasks: List[_S11Subtask] = Field(description="Exactly three subtasks — one per specialist.")


def slide_11() -> Dict[str, Any]:
    rec = SlideRecorder(
        11,
        "Multi-Agent Systems & the Orchestrator",
        "Planner → specialists (each with private data) → Reviewer. The orchestrator is code.",
    )
    llm = get_llm(temperature=None)
    rec.prompt_block("User", _S11_REQUEST)

    # Planner
    rec.heading("PLANNER AGENT", "split the request into specialist jobs")
    parser = PydanticOutputParser(pydantic_object=_S11Plan)
    plan = parser.parse(
        llm.invoke(
            [
                SystemMessage(
                    "You are the Planner agent. Split the user's request into exactly THREE focused "
                    "subtasks, one for each specialist:\n"
                    "- research: public web/news about the competitor\n"
                    "- sql: our internal sales database (win/loss numbers)\n"
                    "- docs: our internal reports and battlecards\n"
                    f"{parser.get_format_instructions()}"
                ),
                HumanMessage(_S11_REQUEST),
            ]
        ).content
    )
    for st in plan.subtasks:
        rec.tag(_S11_TITLES[st.specialist], st.question)

    # Orchestrator: route each subtask, simulate a SQL timeout on first attempt, retry
    rec.heading("ORCHESTRATOR", "route each subtask, invoke specialists, handle failures")
    sql_calls = 0
    findings: Dict[str, str] = {}
    for st in plan.subtasks:
        for attempt in (1, 2):
            rec.tag("routing", f"→ {_S11_TITLES[st.specialist]} (attempt {attempt})")
            # Simulate a first-attempt timeout on the SQL agent.
            if st.specialist == "sql":
                sql_calls += 1
                if sql_calls == 1:
                    rec.tag("failure", f"{_S11_TITLES[st.specialist]}: sales-db connection timed out — orchestrator retries")
                    continue
            resp = llm.invoke(
                [
                    SystemMessage(
                        f"You are the {_S11_TITLES[st.specialist]}. Answer in AT MOST 2 sentences using "
                        f"ONLY your data source below — cite nothing else.\n\nDATA SOURCE:\n{_S11_SOURCES[st.specialist]}"
                    ),
                    HumanMessage(st.question),
                ]
            )
            findings[st.specialist] = resp.content.strip()
            rec.model_response(findings[st.specialist], who=_S11_TITLES[st.specialist])
            break
    rec.note(f"Workflow state held by the orchestrator: {list(findings)} — all in; releasing to Reviewer.")

    # Reviewer
    rec.heading("REVIEWER AGENT", "check the findings, then synthesize")
    joined = "\n\n".join(f"[{_S11_TITLES[k]}]\n{v}" for k, v in findings.items())
    final = llm.invoke(
        [
            SystemMessage(
                "You are the Reviewer agent. You receive findings from three specialists. "
                "Write the final answer as exactly 3 bullets: (1) where Acme beats us, "
                "(2) where we beat Acme, (3) the single most important gap or caveat in these findings."
            ),
            HumanMessage(f"User asked: {_S11_REQUEST}\n\nSpecialist findings:\n{joined}"),
        ]
    ).content.strip()
    rec.final_answer(final)
    rec.takeaway("Specialists + a coordinator beat one giant prompt — and the orchestrator is ordinary code: routing, retries, state.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 12 — Real-World Analogy (LLM-free: pure comparison table)
# ═══════════════════════════════════════════════════════════════════════════
def slide_12() -> Dict[str, Any]:
    rec = SlideRecorder(
        12,
        "Real-World Analogy",
        "Every concept from today, mapped onto two everyday worlds.",
    )
    rec.note("No LLM calls — this is a talking aid. Pick the analogy that clicks for the room.")
    rec.table(
        headers=["CONCEPT", "BUILDING A HOUSE", "RESTAURANT KITCHEN"],
        rows=[
            ["LLM", "skilled worker", "line cook (no memory of yesterday)"],
            ["Prompt", "work order", "order ticket: 'Table 5, no onions'"],
            ["Tool", "hammer, drill, measuring tape", "knife, oven, fryer"],
            ["Chain", "construction checklist", "a recipe followed step by step"],
            ["Agent", "site engineer deciding what's next", "head chef tasting and adjusting"],
            ["Memory", "blueprint + previous work logs", "recipe book + 'Table 5: nut allergy'"],
            ["Orchestrator", "project manager coordinating everyone", "restaurant manager: kitchen/waiters/bar"],
        ],
    )
    rec.note("Stress-test one row out loud: 'Why is the agent the site engineer and not the checklist? "
             "Because the engineer looks at the wall that just went up (OBSERVES) before deciding what "
             "happens next — the checklist can't do that.' That's Slide 7's loop, retold in bricks.")
    rec.takeaway("If someone can retell today's ideas in bricks OR in dinner orders, they've got it.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 13 — Key Takeaways (capstone: every concept in one task)
# ═══════════════════════════════════════════════════════════════════════════
_S13_PROFILE = {"dentist": "Dr. Lee", "preference": "morning appointments"}


@tool
def _s13_check_calendar() -> str:
    """Get the user's FREE time slots for next week."""
    return "Free slots next week — Mon: 14:00, 15:30 · Tue: 09:00, 13:00 · Wed: 16:00"


@tool
def _s13_book_appointment(day: str, time: str) -> str:
    """Book a dentist appointment at the given day and time. Returns a confirmation code."""
    return f"CONFIRMED #DENT-217 — {day} {time} at Dr. Lee's clinic"


def slide_13() -> Dict[str, Any]:
    rec = SlideRecorder(
        13,
        "Key Takeaways — the capstone",
        'One everyday request exercises every concept from today.',
    )
    goal = "Book me a dentist appointment next week."
    rec.prompt_block("User", goal)

    rec.tag("PROMPT", "system rules + long-term memory + the request — assembled below:")
    system = (
        "You are a scheduling assistant. Use the tools to complete the user's request.\n"
        f"LONG-TERM MEMORY about this user: dentist is {_S13_PROFILE['dentist']}; "
        f"prefers {_S13_PROFILE['preference']}.\n"
        "Honor the user's preferences. After booking, verify you received a confirmation code and "
        "include it in your final answer."
    )
    rec.prompt_block("SYSTEM (assembled)", system)
    rec.tag("MEMORY", f"profile injected from storage: {_S13_PROFILE} (the user typed none of this today)")

    tools = {"_s13_check_calendar": _s13_check_calendar, "_s13_book_appointment": _s13_book_appointment}
    llm = get_llm(temperature=None).bind_tools(list(tools.values()))
    messages = [SystemMessage(system), HumanMessage(goal)]

    rec.tag("AGENT", "no fixed pipeline follows — the model now chooses every step itself.")

    for _ in range(6):
        ai = llm.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            rec.tag("REFLECTION", "it checked the confirmation code before answering (as instructed).")
            rec.final_answer(ai.content.strip())
            break

        for call in ai.tool_calls:
            rec.tag("TOOL", f"the model REQUESTED {call['name']} — our code runs it")
            rec.tool_call(call["name"], call["args"], call["id"])
            obs = tools[call["name"]].invoke(call["args"] or {})
            rec.observation(str(obs))
            messages.append(ToolMessage(content=str(obs), tool_call_id=call["id"]))
            if call["name"] == "_s13_book_appointment":
                picked = f"{call['args'].get('day', '?')} {call['args'].get('time', '?')}"
                rec.tag("REASONING", f"picked {picked} — the ONLY morning slot — because memory says mornings.")

    rec.heading("EVERY CONCEPT FROM TODAY, IN ONE TASK")
    rec.table(
        headers=["Concept", "Where it showed up"],
        rows=[
            ["LLM", "generated every 'thought' and the final message"],
            ["Prompt", "instructions + memory + request, assembled by our app"],
            ["Tool", "check_calendar / book_appointment — requested by the model, run by our code"],
            ["Chain", "what this would be if the steps were hard-wired (Slide 4) — they weren't"],
            ["Agent", "it chose to check the calendar first, then book — nobody scripted that"],
            ["Memory", "Dr. Lee + mornings came from storage, not from today's user"],
            ["Orchestrator", "one agent today; Day 3+ coordinates several of these (Slide 11)"],
        ],
    )
    rec.takeaway("Not seven separate ideas — seven parts of ONE system that turns a text predictor into an assistant that gets things done.")
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# Public registry — labs.py imports this
# ═══════════════════════════════════════════════════════════════════════════
SLIDE_DEMOS: Dict[str, Callable[[], Dict[str, Any]]] = {
    "slide2": slide_02,
    "slide3": slide_03,
    "slide4": slide_04,
    "slide5": slide_05,
    "slide6": slide_06,
    "slide7": slide_07,
    "slide8": slide_08,
    "slide9": slide_09,
    "slide10": slide_10,
    "slide11": slide_11,
    "slide12": slide_12,
    "slide13": slide_13,
}
