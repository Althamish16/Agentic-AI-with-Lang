"""
backend/langgraph_demos.py — Day 3 "LangGraph Core" live modules.

Mirrors backend/slide_demos.py: each module is a self-contained teaching demo
that returns a JSON event list the frontend animates step-by-step. Where Day-1
slides teach ONE concept per tab, Day-3 modules walk students through the guts
of a `Planner → Executor → Memory` LangGraph, from "why chains fail" all the way
to a live `.stream()` execution with state diffs.

Each module returns:

    {
        "kind": "slide_demo",           # reuses Day-1 render pipeline
        "mode": "module",               # tells the UI to say "Module N" not "Slide N"
        "slide": <int>,                 # module number (drives the sub-tab order)
        "title": "<module title>",
        "subtitle": "<one-line teaching frame>",
        "steps": [ { "type": "...", ...payload }, ... ]
    }

Step-type vocabulary (superset of Day-1)
----------------------------------------
Reused from slide_demos.SlideRecorder:
  heading / note / prompt_block / model_response / tool_call / observation /
  tag / table / final / takeaway

New Day-3 types (rendered in frontend/src/components/DayResult.jsx):
  state_json      — TypedDict state snapshot; optional prev + highlight[] for diff
  graph_mermaid   — Mermaid flowchart source + list of "active" nodes to glow
  node_flash      — "the planner node fires" indicator (node + status)
  route_decision  — {condition, value, branch}: shows the conditional edge choice
  code_view       — Python snippet + optional highlighted line for the code tab
  progress        — {current, total, label}: step X of N bar for the executor loop
  compare_grid    — two side-by-side mini-panels (used by ReAct vs Plan-Execute)
  loop_meter      — {iterations, tokens, warning}: the runaway-loop counter

All LLM work goes through `config.get_llm` (Azure gpt-5.4 in this repo). Modules
that don't need the LLM run OFFLINE so the whole Day-3 tour can be demonstrated
without burning tokens — only Modules 3, 5, 6, 10 actually call the model.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# LGRecorder — append-typed-dicts API mirroring SlideRecorder, plus the
# LangGraph-specific step helpers (state_json / graph_mermaid / …).
# ═══════════════════════════════════════════════════════════════════════════
class LGRecorder:
    def __init__(self, module: int, title: str, subtitle: str) -> None:
        self.module = module
        self.title = title
        self.subtitle = subtitle
        self.steps: List[Dict[str, Any]] = []

    # --- primitives shared with SlideRecorder -----------------------------
    def heading(self, label: str, desc: str = "") -> None:
        self.steps.append({"type": "heading", "label": label, "desc": desc})

    def note(self, text: str) -> None:
        self.steps.append({"type": "note", "text": text})

    def prompt_block(self, label: str, text: str) -> None:
        self.steps.append({"type": "prompt_block", "label": label, "text": text})

    def model_response(self, text: str, who: str = "Model") -> None:
        self.steps.append({"type": "model_response", "who": who, "text": text})

    def tag(self, label: str, text: str) -> None:
        self.steps.append({"type": "tag", "label": label, "text": text})

    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        self.steps.append({"type": "table", "headers": headers, "rows": rows})

    def final_answer(self, text: str) -> None:
        self.steps.append({"type": "final", "text": text})

    def takeaway(self, text: str) -> None:
        self.steps.append({"type": "takeaway", "text": text})

    # --- new: Day-3 specific ---------------------------------------------
    def state_json(
        self,
        state: dict,
        *,
        prev: dict | None = None,
        highlight: List[str] | None = None,
        note: str = "",
        title: str = "State",
    ) -> None:
        """A live `TypedDict` snapshot. If `prev` is given, the UI shows a diff
        badge next to changed keys and animates them; `highlight` lets us force
        the glow even when the value is the same shape (e.g. first write)."""
        self.steps.append(
            {
                "type": "state_json",
                "title": title,
                "state": state,
                "prev": prev,
                "highlight": highlight or [],
                "note": note,
            }
        )

    def graph_mermaid(
        self,
        markup: str,
        *,
        active: List[str] | None = None,
        note: str = "",
        title: str = "",
    ) -> None:
        """A Mermaid flowchart to render. `active` lists nodes the UI should
        pulse (the currently-executing node)."""
        self.steps.append(
            {
                "type": "graph_mermaid",
                "markup": markup,
                "active": active or [],
                "note": note,
                "title": title,
            }
        )

    def node_flash(self, node: str, label: str = "", status: str = "active") -> None:
        """Fires the "node lights up" badge. status ∈ {active, done, pending, error}."""
        self.steps.append(
            {"type": "node_flash", "node": node, "label": label, "status": status}
        )

    def route_decision(self, condition: str, value: bool, branch: str, desc: str = "") -> None:
        self.steps.append(
            {
                "type": "route_decision",
                "condition": condition,
                "value": value,
                "branch": branch,
                "desc": desc,
            }
        )

    def code_view(
        self,
        code: str,
        *,
        language: str = "python",
        title: str = "",
        highlight: List[int] | None = None,
    ) -> None:
        self.steps.append(
            {
                "type": "code_view",
                "language": language,
                "title": title,
                "code": code,
                "highlight": highlight or [],
            }
        )

    def progress(self, current: int, total: int, label: str = "") -> None:
        self.steps.append(
            {"type": "progress", "current": current, "total": total, "label": label}
        )

    def compare_grid(self, left: dict, right: dict) -> None:
        """left/right = {title, subtitle, chips: [...], items: [{k, v}] }."""
        self.steps.append({"type": "compare_grid", "left": left, "right": right})

    def loop_meter(self, iterations: int, tokens: int, warning: bool = False, note: str = "") -> None:
        self.steps.append(
            {
                "type": "loop_meter",
                "iterations": iterations,
                "tokens": tokens,
                "warning": warning,
                "note": note,
            }
        )

    # --- output -----------------------------------------------------------
    def payload(self) -> Dict[str, Any]:
        return {
            "kind": "slide_demo",
            "mode": "module",
            "slide": self.module,
            "title": self.title,
            "subtitle": self.subtitle,
            "steps": self.steps,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Reusable Mermaid snippets — kept as constants so the same graph shows up in
# multiple modules with the "active node" glow shifting between them.
# ═══════════════════════════════════════════════════════════════════════════
_CHAIN_MERMAID = """flowchart LR
  START([START]) --> P[Prompt]
  P --> L[LLM]
  L --> O[Output]
  O --> END([END])
"""

_LG_MERMAID = """flowchart TD
  START([START]) --> planner[[Planner]]
  planner --> executor[[Executor]]
  executor --> router{route?}
  router -- more work --> executor
  router -- done --> synthesize[[Synthesize]]
  synthesize --> END([END])
"""

_LG_MERMAID_WITH_MEMORY = """flowchart TD
  START([START]) --> planner[[Planner]]
  planner --> executor[[Executor]]
  executor --> memory[(Memory / State)]
  memory --> router{route?}
  router -- loop --> executor
  router -- done --> synthesize[[Synthesize]]
  synthesize --> END([END])
"""

_REACT_MERMAID = """flowchart TD
  A[Thought] --> B[Action]
  B --> C[Observation]
  C --> A
  C -- done --> D([Answer])
"""

_INFINITE_MERMAID = """flowchart LR
  P[[Planner]] --> E[[Executor]]
  E --> P
"""


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 1 — Introduction: Chain vs LangGraph
# ═══════════════════════════════════════════════════════════════════════════
def module_01() -> Dict[str, Any]:
    rec = LGRecorder(
        1,
        "Introduction · Chain vs LangGraph",
        "Why we outgrow the straight line — and what a graph gives us in return.",
    )
    rec.heading("PART A · THE TRADITIONAL CHAIN", "one direction, no branches, no loops")
    rec.graph_mermaid(_CHAIN_MERMAID, note="A LangChain LCEL chain is a pipe: prompt | llm | parser. Beautiful when the answer is a single hop.")
    rec.tag("STRENGTH", "Predictable · easy to reason about · trivial to test.")
    rec.tag("LIMIT", "Cannot decide, retry, branch, or remember across steps.")

    rec.heading("PART B · THE LANGGRAPH AGENT", "nodes + edges + a shared State that flows through them")
    rec.graph_mermaid(
        _LG_MERMAID_WITH_MEMORY,
        active=["planner"],
        note="Same idea, but now Planner decomposes the goal, Executor works one sub-question at a time, and a conditional router LOOPS back until every step is done.",
    )
    rec.tag("PLANNER", "Turns a fuzzy goal into a concrete plan.")
    rec.tag("EXECUTOR", "Does the work for the next open step.")
    rec.tag("ROUTER", "Inspects state and picks the next node — this is the loop.")
    rec.tag("MEMORY", "Every node reads/writes the same TypedDict state.")

    rec.takeaway(
        "A chain is a recipe. A graph is a kitchen with stations, a plan on the wall, "
        "and someone (the router) deciding who cooks next. Everything else on Day 3 is "
        "just detail on those four boxes."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 2 — Why chains can't retry (and why we need loops)
# ═══════════════════════════════════════════════════════════════════════════
def module_02() -> Dict[str, Any]:
    rec = LGRecorder(
        2,
        "Why Chains Fail",
        "A chain can only move forward. Real agents need to look back.",
    )
    rec.heading("SCENARIO", "The user asked 3 sub-questions. The first attempt half-fails.")
    rec.graph_mermaid(_CHAIN_MERMAID, active=["L"], note="A pure chain runs each node exactly once.")
    rec.tag("STEP", "Chain answers sub-question 1 · ✓")
    rec.tag("STEP", "Chain answers sub-question 2 · ✓")
    rec.tag("FAIL", "Sub-question 3 returns a low-confidence draft. The chain has no way to notice and no way to retry.")
    rec.node_flash("Output", label="ships bad answer — nowhere to loop back to", status="error")

    rec.heading("SAME SCENARIO IN LANGGRAPH", "a conditional edge makes retry a first-class citizen")
    rec.graph_mermaid(_LG_MERMAID, active=["router"], note="The router checks state and CAN send flow back to the executor.")
    rec.tag("STEP", "Executor answers 1 · router sees more work → loop")
    rec.tag("STEP", "Executor answers 2 · router sees more work → loop")
    rec.tag("STEP", "Executor answers 3 · router sees low confidence → loop AGAIN with a retry")
    rec.node_flash("router", label="conditional edge fires: back to executor", status="active")
    rec.tag("PASS", "Retry succeeds · synthesize runs · quality answer shipped.")

    rec.takeaway(
        "The single most important idea on Day 3: `add_conditional_edges` is the "
        "difference between a chain and an agent. Loops turn a fixed pipeline into "
        "something that can decide and recover."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 3 — Live state visualization (real LLM call — Planner writes state)
# ═══════════════════════════════════════════════════════════════════════════
def module_03(question: str = "") -> Dict[str, Any]:
    from shared.planner import plan_research
    from shared.rag import answer_question

    q = (question or "How do vector databases power RAG?").strip()

    rec = LGRecorder(
        3,
        "State Visualization",
        "Watch the shared TypedDict change after every node fires.",
    )
    rec.note("Every LangGraph node returns a partial update; LangGraph MERGES it into state. We show state before and after each merge.")

    # STATE 0 — freshly initialized
    state0 = {"question": q, "topic": "", "plan": [], "cursor": 0, "results": [], "final": ""}
    rec.state_json(state0, title="STATE — initial", note="Only `question` is set. The other fields are placeholders the nodes will fill.")

    # STATE 1 — after planner
    rec.node_flash("planner", label="LLM call: decomposing the question…", status="active")
    plan = plan_research(q)
    state1 = {**state0, "topic": plan.topic, "plan": plan.sub_questions, "cursor": 0, "results": []}
    rec.state_json(
        state1,
        prev=state0,
        highlight=["topic", "plan", "cursor"],
        title="STATE — after planner_node",
        note="topic + plan populated · cursor reset to 0. The planner's return value has been merged into state.",
    )

    # STATE 2 — after ONE executor iteration
    rec.node_flash("executor", label=f"answering sub-question 1/{len(plan.sub_questions)} via RAG…", status="active")
    sub0 = plan.sub_questions[0]
    r0 = answer_question(sub0, k=3)
    entry = {"sub_question": sub0, "answer": r0["answer"], "sources": r0["sources"]}
    state2 = {**state1, "results": [entry], "cursor": 1}
    rec.state_json(
        state2,
        prev=state1,
        highlight=["results", "cursor"],
        title="STATE — after executor iteration 1",
        note="cursor advanced 0 → 1 · results grew by one entry. The router will now check `cursor < len(plan)` — TRUE → loop back to executor.",
    )
    rec.route_decision(
        condition="state['cursor'] < len(state['plan'])",
        value=True,
        branch="executor",
        desc=f"cursor={state2['cursor']}, plan has {len(plan.sub_questions)} items → keep looping.",
    )

    rec.takeaway(
        "State isn't a black box — it's a plain dict you can print. Once you can see "
        "each node's diff, everything else (memory, reducers, checkpointing) becomes "
        "obvious plumbing."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 4 — Graph builder (visual + code)
# ═══════════════════════════════════════════════════════════════════════════
def module_04() -> Dict[str, Any]:
    rec = LGRecorder(
        4,
        "Graph Builder · nodes + edges",
        "The three-line recipe that turns Day-1 + Day-2 code into a Day-3 graph.",
    )
    rec.heading("THE CANONICAL SHAPE", "planner → executor ↺ → synthesize → END")
    rec.graph_mermaid(_LG_MERMAID, note="Each `[[Planner]]` box is a Python function you already wrote — LangGraph just wires them.")

    rec.heading("STEP 1 · declare the shared State (TypedDict)")
    rec.code_view(
        (
            "class ResearchState(TypedDict, total=False):\n"
            "    question: str\n"
            "    topic:    str\n"
            "    plan:     list[str]\n"
            "    cursor:   int\n"
            "    results:  list[dict]\n"
            "    final:    str"
        ),
        title="the contract every node reads/writes",
    )

    rec.heading("STEP 2 · turn Day-1 & Day-2 helpers into nodes")
    rec.code_view(
        (
            "def planner_node(state):        # Day 1\n"
            "    p = plan_research(state['question'])\n"
            "    return {'topic': p.topic, 'plan': p.sub_questions, 'cursor': 0, 'results': []}\n"
            "\n"
            "def executor_node(state):        # Day 2\n"
            "    sub_q = state['plan'][state['cursor']]\n"
            "    r = answer_question(sub_q, k=3)\n"
            "    entry = {'sub_question': sub_q, 'answer': r['answer'], 'sources': r['sources']}\n"
            "    return {'results': state['results'] + [entry], 'cursor': state['cursor'] + 1}"
        ),
        title="each node returns a partial state update",
    )

    rec.heading("STEP 3 · assemble the graph")
    rec.code_view(
        (
            "g = StateGraph(ResearchState)\n"
            "g.add_node('planner',   planner_node)\n"
            "g.add_node('executor',  executor_node)\n"
            "g.add_node('synthesize', synthesize_node)\n"
            "\n"
            "g.add_edge(START, 'planner')\n"
            "g.add_edge('planner', 'executor')\n"
            "g.add_conditional_edges(     # <-- the loop!\n"
            "    'executor', route_after_executor,\n"
            "    {'executor': 'executor', 'synthesize': 'synthesize'})\n"
            "g.add_edge('synthesize', END)\n"
            "\n"
            "app = g.compile()"
        ),
        title="`add_conditional_edges` is the whole difference from a chain",
        highlight=[8, 9, 10, 11],
    )
    rec.takeaway(
        "Three additions to a straight chain give you a full agent: TypedDict state, "
        "conditional edges, and a compile step. You keep every helper from Day 1–2."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 5 — Planner demo (live LLM)
# ═══════════════════════════════════════════════════════════════════════════
def module_05(question: str = "") -> Dict[str, Any]:
    from shared.planner import plan_research

    q = (question or "Research Tesla's business, product line, and main competitors").strip()

    rec = LGRecorder(
        5,
        "Planner Demo · decomposition in action",
        "One fuzzy goal in, a typed plan out. This IS the first node.",
    )
    rec.graph_mermaid(_LG_MERMAID, active=["planner"], note="We're inside the planner node right now.")
    rec.prompt_block("HUMAN", q)
    rec.node_flash("planner", label="calling the LLM with a Pydantic parser…", status="active")

    plan = plan_research(q)

    rec.model_response(
        "topic: " + plan.topic + "\n" + "\n".join(f"{i + 1}. {sq}" for i, sq in enumerate(plan.sub_questions)),
        who="Planner (validated ResearchPlan)",
    )
    rec.state_json(
        {"topic": plan.topic, "plan": plan.sub_questions, "cursor": 0},
        highlight=["topic", "plan"],
        title="what the planner writes into state",
        note="Sub-questions are ordered. `cursor: 0` tells the executor which one to work on first.",
    )
    rec.node_flash("planner", label="done — control passes to executor", status="done")
    rec.takeaway(
        "The planner isn't magical — it's the Day-1 LCEL chain `prompt | llm | PydanticOutputParser`. "
        "Making it a graph node just means calling it inside a function that returns a state update."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 6 — Executor demo (live LLM+RAG)
# ═══════════════════════════════════════════════════════════════════════════
def module_06(question: str = "") -> Dict[str, Any]:
    from shared.planner import plan_research
    from shared.rag import answer_question

    q = (question or "How do vector databases power RAG?").strip()

    rec = LGRecorder(
        6,
        "Executor Demo · one step at a time",
        "The executor grabs `plan[cursor]`, does the work, and advances the cursor.",
    )
    rec.graph_mermaid(_LG_MERMAID, active=["executor"], note="Zooming in on the executor node.")

    rec.node_flash("planner", label="(already done above)", status="done")
    plan = plan_research(q)
    total = len(plan.sub_questions)
    rec.state_json({"plan": plan.sub_questions, "cursor": 0, "results": []}, title="STATE — entering the executor")

    # ONE iteration only — this is the "one step" that the executor node performs.
    rec.progress(current=1, total=total, label=f"iteration 1 of {total}")
    rec.node_flash("executor", label=f"answering: “{plan.sub_questions[0]}”", status="active")
    r = answer_question(plan.sub_questions[0], k=3)
    rec.observation("retrieved " + str(len(r["sources"])) + " sources · " + ", ".join(r["sources"]))
    rec.model_response(r["answer"], who="Executor (answer + citations)")

    entry = {"sub_question": plan.sub_questions[0], "answer": r["answer"], "sources": r["sources"]}
    rec.state_json(
        {"plan": plan.sub_questions, "cursor": 1, "results": [entry]},
        prev={"plan": plan.sub_questions, "cursor": 0, "results": []},
        highlight=["cursor", "results"],
        title="STATE — after one executor iteration",
        note="cursor moved forward · one entry appended to results.",
    )
    rec.route_decision(
        condition="state['cursor'] < len(state['plan'])",
        value=True,
        branch="executor",
        desc=f"cursor=1, plan has {total} items → back to executor (next slide).",
    )
    rec.takeaway(
        "Every executor call is one iteration of the loop. Because state is merged, we "
        "never accidentally overwrite earlier findings — we APPEND them via `results + [entry]`."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 7 — Conditional routing (no LLM)
# ═══════════════════════════════════════════════════════════════════════════
def module_07() -> Dict[str, Any]:
    rec = LGRecorder(
        7,
        "Conditional Routing",
        "The router is one Python function — but it's the whole point of Day 3.",
    )
    rec.code_view(
        (
            "def route_after_executor(state) -> str:\n"
            "    # Look at state and return the KEY of the next node.\n"
            "    if state['cursor'] < len(state['plan']):\n"
            "        return 'executor'   # keep looping\n"
            "    return 'synthesize'      # done — assemble the final answer"
        ),
        title="the router itself",
        highlight=[3, 4],
    )

    rec.heading("THREE DIFFERENT STATES → THREE DIFFERENT BRANCHES", "same graph, different routes")
    rec.state_json({"plan": ["Q1", "Q2", "Q3"], "cursor": 1}, title="Case A · one done, two to go")
    rec.route_decision(condition="1 < 3", value=True, branch="executor", desc="loop back — more work remains")

    rec.state_json({"plan": ["Q1", "Q2", "Q3"], "cursor": 2}, title="Case B · two done, one to go")
    rec.route_decision(condition="2 < 3", value=True, branch="executor", desc="still more work — loop again")

    rec.state_json({"plan": ["Q1", "Q2", "Q3"], "cursor": 3}, title="Case C · all done")
    rec.route_decision(condition="3 < 3", value=False, branch="synthesize", desc="cursor caught the length → jump out of the loop")

    rec.graph_mermaid(_LG_MERMAID, active=["router"], note="Visualization: the diamond is the router. Two edges leave it, only one fires each turn.")

    rec.takeaway(
        "Force-continue, force-end, force-replan — every one of them is a tweak to this "
        "5-line function. That's how flexible conditional edges are."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 8 — Memory / reducers (no LLM)
# ═══════════════════════════════════════════════════════════════════════════
def module_08() -> Dict[str, Any]:
    rec = LGRecorder(
        8,
        "Memory · how state grows without clobbering itself",
        "Reducers turn per-node UPDATES into merged, accumulating state.",
    )
    rec.note("Every node returns a *partial* dict. LangGraph merges each return into state — the merge rule for a field is called its REDUCER.")

    rec.code_view(
        (
            "# Default reducer: overwrite. Good for scalars like `cursor` or `topic`.\n"
            "# For lists we usually want APPEND — either explicit or via `Annotated[..., add]`.\n"
            "from operator import add\n"
            "from typing import Annotated, TypedDict\n"
            "\n"
            "class ResearchState(TypedDict, total=False):\n"
            "    plan:    list[str]\n"
            "    cursor:  int                  # overwrite\n"
            "    results: Annotated[list[dict], add]   # APPEND across nodes"
        ),
        title="reducers make growth safe",
        highlight=[7, 8],
    )

    rec.heading("WATCH RESULTS ACCUMULATE", "three executor iterations, three merges")

    base = {"plan": ["Q1", "Q2", "Q3"], "cursor": 0, "results": []}
    rec.state_json(base, title="STATE — empty")

    s1 = {**base, "cursor": 1, "results": [{"sub_question": "Q1", "answer": "a1", "sources": ["A"]}]}
    rec.state_json(s1, prev=base, highlight=["cursor", "results"], title="after iteration 1")

    s2 = {
        **s1,
        "cursor": 2,
        "results": s1["results"] + [{"sub_question": "Q2", "answer": "a2", "sources": ["B"]}],
    }
    rec.state_json(s2, prev=s1, highlight=["cursor", "results"], title="after iteration 2")

    s3 = {
        **s2,
        "cursor": 3,
        "results": s2["results"] + [{"sub_question": "Q3", "answer": "a3", "sources": ["C"]}],
    }
    rec.state_json(s3, prev=s2, highlight=["cursor", "results"], title="after iteration 3")

    rec.takeaway(
        "Same idea as `add_messages` for chat: the state field owns the merge rule, so "
        "nodes can return small deltas without worrying about clobbering their siblings' work."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 9 — ReAct vs Plan-Execute
# ═══════════════════════════════════════════════════════════════════════════
def module_09() -> Dict[str, Any]:
    rec = LGRecorder(
        9,
        "ReAct vs Plan-Execute",
        "Two loop shapes, two different bets about what the agent should decide.",
    )
    rec.compare_grid(
        left={
            "title": "ReAct · Think → Act → Observe → repeat",
            "subtitle": "Every turn is a new decision — maximum adaptability, more calls.",
            "chips": ["reactive", "one-step-at-a-time", "flexible"],
            "items": [
                {"k": "planning", "v": "implicit — decided each turn"},
                {"k": "turns", "v": "high (one per tool call)"},
                {"k": "cost", "v": "$$$ (more LLM invocations)"},
                {"k": "adapts to surprises", "v": "very well"},
                {"k": "recovery from wrong tool", "v": "trivial — think again next turn"},
            ],
        },
        right={
            "title": "Plan-Execute · plan once, then run the steps",
            "subtitle": "Cheap and predictable — but a bad plan up front hurts.",
            "chips": ["deliberate", "batched", "cheaper"],
            "items": [
                {"k": "planning", "v": "explicit — one big plan up front"},
                {"k": "turns", "v": "low (planner + N executor calls)"},
                {"k": "cost", "v": "$ (fewer LLM invocations)"},
                {"k": "adapts to surprises", "v": "only via replanning"},
                {"k": "recovery from wrong tool", "v": "requires a replan node"},
            ],
        },
    )
    rec.graph_mermaid(_REACT_MERMAID, note="ReAct: one tight loop, thinking every turn.")
    rec.graph_mermaid(_LG_MERMAID, note="Plan-Execute (Day 3): plan once, executor loops through the plan.")
    rec.table(
        headers=["dimension", "ReAct", "Plan-Execute"],
        rows=[
            ["cost per goal", "higher", "lower"],
            ["speed", "slower", "faster"],
            ["adaptability", "high", "medium (replan needed)"],
            ["debuggability", "step-by-step reasoning", "explicit plan you can inspect"],
            ["best for", "open-ended tool use", "known workflows / research"],
        ],
    )
    rec.takeaway(
        "Day 3 teaches Plan-Execute because the plan is inspectable and the executor "
        "is easy to trace. Day 4 layers ReAct on top — the two compose, they don't compete."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 10 — Live LangGraph execution (real .stream())
# ═══════════════════════════════════════════════════════════════════════════
def module_10(question: str = "") -> Dict[str, Any]:
    """Actually compile a StateGraph and stream it end-to-end, capturing each
    node's output into a state-diff timeline. This is the module that proves
    "everything above is real, not a mockup"."""
    from typing import List, TypedDict

    from langgraph.graph import END, START, StateGraph

    from config import get_llm
    from shared.planner import plan_research
    from shared.rag import answer_question

    q = (question or "How do vector databases power RAG?").strip()

    class _RS(TypedDict, total=False):
        question: str
        topic: str
        plan: List[str]
        cursor: int
        results: List[dict]
        final: str

    def _planner(s):
        p = plan_research(s["question"])
        return {"topic": p.topic, "plan": p.sub_questions, "cursor": 0, "results": []}

    def _executor(s):
        sub = s["plan"][s["cursor"]]
        r = answer_question(sub, k=3)
        return {
            "results": s["results"] + [{"sub_question": sub, "answer": r["answer"], "sources": r["sources"]}],
            "cursor": s["cursor"] + 1,
        }

    def _route(s):
        return "executor" if s["cursor"] < len(s["plan"]) else "synthesize"

    def _synth(s):
        body = "\n\n".join(f"{r['sub_question']}: {r['answer']}" for r in s["results"])
        final = get_llm(0).invoke(
            f"Write a cohesive cited answer to '{s['question']}' from:\n{body}"
        ).content
        return {"final": final}

    g = StateGraph(_RS)
    g.add_node("planner", _planner)
    g.add_node("executor", _executor)
    g.add_node("synthesize", _synth)
    g.add_edge(START, "planner")
    g.add_edge("planner", "executor")
    g.add_conditional_edges("executor", _route, {"executor": "executor", "synthesize": "synthesize"})
    g.add_edge("synthesize", END)
    app = g.compile()

    rec = LGRecorder(
        10,
        "Live LangGraph Execution",
        "The graph you just learned about, actually running via `app.stream(...)`.",
    )
    rec.graph_mermaid(_LG_MERMAID, active=["planner"], note="We stream `updates` — each chunk is one node's return value.")

    prev = {"question": q, "topic": "", "plan": [], "cursor": 0, "results": [], "final": ""}
    rec.state_json(prev, title="STATE — before app.stream()")

    running = dict(prev)
    for chunk in app.stream({"question": q}, stream_mode="updates"):
        for name, update in chunk.items():
            rec.node_flash(name, label=f"node fired — merging {list(update.keys())} into state", status="active")
            after = {**running, **update}
            changed = [k for k in update.keys()]
            rec.state_json(
                after,
                prev=running,
                highlight=changed,
                title=f"STATE — after `{name}` merged",
            )
            running = after

    if running.get("final"):
        rec.final_answer(running["final"])
    rec.takeaway(
        "This is exactly the graph from Modules 4 & 7, executed live. The trace above is "
        "what LangSmith shows you in production — same data, prettier UI."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 11 — Code viewer (annotated source)
# ═══════════════════════════════════════════════════════════════════════════
def module_11() -> Dict[str, Any]:
    rec = LGRecorder(
        11,
        "Code Viewer · every visualization has a source",
        "The Python behind each animation. Copy it, run it, break it.",
    )
    rec.heading("planner_node", "the Day-1 chain, wrapped as a graph node")
    rec.code_view(
        (
            "def planner_node(state: ResearchState) -> dict:\n"
            "    plan = plan_research(state['question'])       # Day 1 LCEL chain\n"
            "    return {'topic': plan.topic,\n"
            "            'plan':  plan.sub_questions,\n"
            "            'cursor': 0,\n"
            "            'results': []}"
        ),
        highlight=[2],
    )
    rec.heading("executor_node", "the Day-2 RAG call, advancing the cursor")
    rec.code_view(
        (
            "def executor_node(state: ResearchState) -> dict:\n"
            "    i = state['cursor']\n"
            "    sub_q = state['plan'][i]\n"
            "    r = answer_question(sub_q, k=3)               # Day 2 RAG\n"
            "    entry = {'sub_question': sub_q,\n"
            "             'answer':       r['answer'],\n"
            "             'sources':      r['sources']}\n"
            "    return {'results': state['results'] + [entry],\n"
            "            'cursor':  i + 1}"
        ),
        highlight=[4, 8, 9],
    )
    rec.heading("route_after_executor", "the router — one line of business logic")
    rec.code_view(
        (
            "def route_after_executor(state) -> str:\n"
            "    if state['cursor'] < len(state['plan']):\n"
            "        return 'executor'\n"
            "    return 'synthesize'"
        ),
        highlight=[2, 3, 4],
    )
    rec.heading("synthesize_node", "combine everything into a final report")
    rec.code_view(
        (
            "def synthesize_node(state: ResearchState) -> dict:\n"
            "    findings = '\\n\\n'.join(\n"
            "        f\"{r['sub_question']}: {r['answer']}\" for r in state['results'])\n"
            "    final = get_llm(0).invoke(\n"
            "        f\"Write a cohesive cited answer to '{state['question']}':\\n{findings}\"\n"
            "    ).content\n"
            "    return {'final': final}"
        ),
    )
    rec.heading("wiring it up")
    rec.code_view(
        (
            "g = StateGraph(ResearchState)\n"
            "for name, fn in [('planner', planner_node),\n"
            "                 ('executor', executor_node),\n"
            "                 ('synthesize', synthesize_node)]:\n"
            "    g.add_node(name, fn)\n"
            "g.add_edge(START, 'planner')\n"
            "g.add_edge('planner', 'executor')\n"
            "g.add_conditional_edges('executor', route_after_executor,\n"
            "    {'executor': 'executor', 'synthesize': 'synthesize'})\n"
            "g.add_edge('synthesize', END)\n"
            "app = g.compile()"
        ),
        highlight=[8, 9],
    )
    rec.takeaway(
        "Fewer than 50 lines of Python. The visual complexity of Day 3 is one "
        "TypedDict + four functions + a handful of edges."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 12 — Infinite loop (why max_steps matters)
# ═══════════════════════════════════════════════════════════════════════════
def module_12() -> Dict[str, Any]:
    rec = LGRecorder(
        12,
        "Infinite Loop · why every graph needs a stop condition",
        "A router that never returns END is a graph that never returns.",
    )
    rec.graph_mermaid(_INFINITE_MERMAID, active=["P", "E"], note="Planner and Executor pointing back at each other with no exit.")
    rec.code_view(
        (
            "def route(state):\n"
            "    # BROKEN: this always sends flow back to planner, even when done.\n"
            "    return 'planner'"
        ),
        highlight=[3],
    )
    rec.heading("SIMULATED RUN", "token counter climbs, no answer arrives")
    rec.loop_meter(iterations=1, tokens=1_240, note="1 turn · warm-up")
    rec.loop_meter(iterations=5, tokens=6_800, note="the plan keeps getting re-planned")
    rec.loop_meter(iterations=15, tokens=19_200, warning=True, note="past a sane budget for one question")
    rec.loop_meter(iterations=40, tokens=52_800, warning=True, note="context window blown · runaway cost")

    rec.heading("THE FIX", "two lines of defense")
    rec.code_view(
        (
            "# 1. A step budget in the router.\n"
            "def route(state):\n"
            "    if state.get('steps', 0) >= MAX_STEPS:\n"
            "        return 'synthesize'         # forced END\n"
            "    if state['cursor'] < len(state['plan']):\n"
            "        return 'executor'\n"
            "    return 'synthesize'\n"
            "\n"
            "# 2. LangGraph's own recursion limit — a hard ceiling.\n"
            "app.invoke(inp, config={'recursion_limit': 25})"
        ),
        highlight=[3, 4, 10],
    )
    rec.takeaway(
        "Two safety belts: an explicit `MAX_STEPS` in your router, and LangGraph's "
        "`recursion_limit`. Wear both — production agents make new bugs every day."
    )
    return rec.payload()


# ═══════════════════════════════════════════════════════════════════════════
# Dispatch table — the id → callable map labs.py imports.
# ═══════════════════════════════════════════════════════════════════════════
MODULES: Dict[str, Callable[..., Dict[str, Any]]] = {
    "mod_01_intro":       module_01,
    "mod_02_chain_fail":  module_02,
    "mod_03_state":       module_03,
    "mod_04_builder":     module_04,
    "mod_05_planner":     module_05,
    "mod_06_executor":    module_06,
    "mod_07_routing":     module_07,
    "mod_08_memory":      module_08,
    "mod_09_react_vs_pe": module_09,
    "mod_10_live":        module_10,
    "mod_11_code":        module_11,
    "mod_12_loop":        module_12,
}
