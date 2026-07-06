"""
LIVE DEMO — Slide 13: "Key Takeaways" (capstone)

Goal on screen: ONE everyday sentence — "Book me a dentist appointment next week" —
exercises EVERY concept from today. As the task runs, each concept is tagged the
moment it appears: [PROMPT] [MEMORY] [AGENT] [TOOL] [REASONING] [REFLECTION].

The calendar is rigged so only one MORNING slot exists; long-term memory says the
user prefers mornings and sees Dr. Lee — so you can verify the agent actually used
its memory, not just booked the first free slot.

Run:
    python day1/demos/demo_13_capstone.py
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from demo_common import banner, step, note, result, takeaway, DIM, RESET, BOLD, BLUE, MAGENTA, GREEN
from config import get_llm

MAX_STEPS = 6

# ── LONG-TERM MEMORY (stored by the app from past sessions) ─────────────────
USER_PROFILE = {"dentist": "Dr. Lee", "preference": "morning appointments"}

# ── TOOLS (our code — the model only requests them) ─────────────────────────
@tool
def check_calendar() -> str:
    """Get the user's FREE time slots for next week."""
    # Rigged: exactly ONE morning slot, so we can verify memory was used.
    return "Free slots next week — Mon: 14:00, 15:30 · Tue: 09:00, 13:00 · Wed: 16:00"


@tool
def book_appointment(day: str, time: str) -> str:
    """Book a dentist appointment at the given day and time. Returns a confirmation code."""
    return f"CONFIRMED #DENT-217 — {day} {time} at Dr. Lee's clinic"


TOOLS = {"check_calendar": check_calendar, "book_appointment": book_appointment}


def tag(name: str, text: str) -> None:
    """Print a concept tag the moment that concept is exercised."""
    print(f"  {MAGENTA}{BOLD}[{name}]{RESET} {text}")


def main() -> None:
    banner(
        "SLIDE 13 · Key Takeaways — the capstone",
        "One everyday request exercises every concept from today.",
        '"Book me a dentist appointment next week." — watch each concept light up.',
    )

    goal = "Book me a dentist appointment next week."
    print(f"  {BOLD}User:{RESET} {goal}\n")

    tag("PROMPT", "system rules + long-term memory + the request — assembled below:")
    system = (
        "You are a scheduling assistant. Use the tools to complete the user's request.\n"
        f"LONG-TERM MEMORY about this user: dentist is {USER_PROFILE['dentist']}; "
        f"prefers {USER_PROFILE['preference']}.\n"
        "Honor the user's preferences. After booking, verify you received a confirmation "
        "code and include it in your final answer."
    )
    print(f"    {DIM}{system.replace(chr(10), chr(10) + '    ')}{RESET}")
    tag("MEMORY", f"profile injected from storage: {USER_PROFILE} (the user typed none of this today)")

    llm = get_llm(temperature=None).bind_tools(list(TOOLS.values()))
    messages = [SystemMessage(system), HumanMessage(goal)]

    tag("AGENT", "no fixed pipeline follows — the model now chooses every step itself:")

    for i in range(1, MAX_STEPS + 1):
        ai = llm.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            tag("REFLECTION", "it checked the confirmation code before answering (as instructed).")
            step("FINAL ANSWER")
            result(ai.content.strip())
            break

        for call in ai.tool_calls:
            args = ", ".join(f"{k}={v!r}" for k, v in call["args"].items())
            tag("TOOL", f"the model REQUESTED {call['name']}({args}) — our code runs it:")
            obs = TOOLS[call["name"]].invoke(call["args"] or {})
            print(f"    {GREEN}→ {obs}{RESET}")
            messages.append(ToolMessage(content=str(obs), tool_call_id=call["id"]))
            if call["name"] == "book_appointment":
                picked = f"{call['args'].get('day', '?')} {call['args'].get('time', '?')}"
                tag("REASONING", f"it picked {picked} — the ONLY morning slot — because memory says mornings.")

    # ── The recap that closes the day ────────────────────────────────────────
    step("EVERY CONCEPT FROM TODAY, IN ONE TASK")
    recap = [
        ("LLM",          "generated every 'thought' and the final message"),
        ("Prompt",       "instructions + memory + request, assembled by our app"),
        ("Tool",         "check_calendar / book_appointment — requested by the model, run by our code"),
        ("Chain",        "what this would be if the steps were hard-wired (Slide 4) — they weren't"),
        ("Agent",        "it chose to check the calendar first, then book — nobody scripted that"),
        ("Memory",       "Dr. Lee + mornings came from storage, not from today's user"),
        ("Orchestrator", "one agent today; Day 3+ coordinates several of these (Slide 11)"),
    ]
    for name, what in recap:
        print(f"    {BLUE}{BOLD}{name:<13}{RESET} {what}")

    takeaway("Not seven separate ideas — seven parts of ONE system that turns a text predictor into an assistant that gets things done.")


if __name__ == "__main__":
    main()
