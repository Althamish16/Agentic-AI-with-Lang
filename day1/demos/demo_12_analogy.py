"""
LIVE DEMO — Slide 12: "Real-World Analogy"

No LLM calls here — this one is a talking aid. It prints the slide's construction
analogy AND a second one (a restaurant kitchen) side by side, so you can ask the
room "which one clicks for you?" while it's on screen. Two analogies means both
the technical and non-technical halves of the audience get one that lands.

Run:
    python day1/demos/demo_12_analogy.py
"""

from __future__ import annotations

from demo_common import banner, step, note, takeaway, DIM, RESET, BOLD, CYAN, GREEN

ROWS = [
    # concept        building a house                        restaurant kitchen
    ("LLM",          "skilled worker",                        "line cook (no memory of yesterday)"),
    ("Prompt",       "work order",                            "order ticket: 'Table 5, no onions'"),
    ("Tool",         "hammer, drill, measuring tape",         "knife, oven, fryer"),
    ("Chain",        "construction checklist",                "a recipe followed step by step"),
    ("Agent",        "site engineer deciding what's next",    "head chef tasting and adjusting"),
    ("Memory",       "blueprint + previous work logs",        "recipe book + 'Table 5: nut allergy'"),
    ("Orchestrator", "project manager coordinating everyone", "restaurant manager: kitchen/waiters/bar"),
]


def main() -> None:
    banner(
        "SLIDE 12 · Real-World Analogy",
        "Every concept from today, mapped onto two everyday worlds.",
        "ask the room which analogy clicks — construction site or kitchen?",
    )

    w1, w2, w3 = 14, 40, 40
    print(f"  {BOLD}{'CONCEPT':<{w1}}│ {'BUILDING A HOUSE':<{w2}}│ {'RESTAURANT KITCHEN':<{w3}}{RESET}")
    print(f"  {'─' * w1}┼{'─' * (w2 + 1)}┼{'─' * w3}")
    for concept, house, kitchen in ROWS:
        print(f"  {CYAN}{BOLD}{concept:<{w1}}{RESET}│ {house:<{w2}}│ {GREEN}{kitchen:<{w3}}{RESET}")

    print()
    step("HOW TO USE THIS SLIDE LIVE")
    note("Pick one row and stress-test it out loud. E.g. 'Why is the agent the site engineer "
         "and not the checklist? Because the engineer looks at the wall that just went up "
         "(OBSERVES) before deciding what happens next — the checklist can't do that.' "
         "That's Slide 7's loop, retold in bricks.")

    takeaway("If someone can retell today's ideas in bricks OR in dinner orders, they've got it.")


if __name__ == "__main__":
    main()
