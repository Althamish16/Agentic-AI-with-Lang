"""
LIVE DEMO 05 (stretch) — Retry-with-backoff makes a flaky call idempotent.

Goal on screen: wrap ANY callable so a transient error is retried a few times
before we give up. In real code you'd only apply this to safely retryable
operations (GETs, reads) — never to side-effectful writes without dedup keys.

    Rule of the day: retries turn a flaky read into a reliable one, but only
                     when the operation is idempotent (safe to repeat).

Run:
    python day4/demos/demo_05_retry_backoff.py
"""

from __future__ import annotations

import time
from typing import Callable

from demo_common import banner, note, result, rule, step, takeaway


def retry_with_backoff(
    fn: Callable[..., str],
    *args,
    retries: int = 3,
    initial_delay: float = 0.2,
    factor: float = 2.0,
    **kwargs,
) -> str:
    """Call `fn(*args, **kwargs)`, retrying with exponential backoff on error.

    Returns the successful result, or a `RETRY_EXHAUSTED: ...` string on
    permanent failure — never raises, so callers stay inside the agent loop.
    """
    delay = initial_delay
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 — we deliberately catch broadly here
            last_err = e
            print(f"    ↻ attempt {attempt}/{retries} failed: {e} (sleep {delay:.2f}s)")
            time.sleep(delay)
            delay *= factor
    return f"RETRY_EXHAUSTED: {last_err}"


def main() -> None:
    banner(
        "DAY 4 · DEMO 5 (stretch) — Retry with exponential backoff",
        "Wrap a flaky, idempotent call so transient errors self-heal.",
        "a fake service fails twice, then succeeds; wrapper never raises.",
    )

    step("STEP 1 · A FLAKY 'SERVICE'", "fails on calls #1 and #2, succeeds on #3")
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError(f"transient error on call #{calls['n']}")
        return "OK: metric=87"

    step("STEP 2 · CALL IT VIA retry_with_backoff(..., retries=5)")
    out = retry_with_backoff(flaky, retries=5, initial_delay=0.05)
    result(f"recovered after {calls['n']} attempt(s) → {out}")

    step("STEP 3 · WHAT ABOUT PERMANENT FAILURES?", "verify we get a string, not a raise")

    def always_broken() -> str:
        raise RuntimeError("upstream is down for maintenance")

    out2 = retry_with_backoff(always_broken, retries=3, initial_delay=0.02)
    result(f"returned (did NOT raise) → {out2}")

    rule("═")
    note(
        "In an agent loop, the string result flows back through ToolNode as a "
        "ToolMessage — the model sees 'RETRY_EXHAUSTED: ...' and can pivot, "
        "same pattern as demo 3's SEARCH_FAILED."
    )
    takeaway(
        "Retries are for IDEMPOTENT operations. Never wrap a write that has "
        "side effects unless you have a dedup / idempotency key."
    )


if __name__ == "__main__":
    main()
