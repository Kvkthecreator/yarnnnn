"""Regression gate — the silent-wake root cause (2026-06-04).

THE BUG (recurring across every alpha-trader autonomy run for weeks):
  A manual_fire of a JUDGMENT recurrence (the eval's `{fire: <slug>}` path, and
  any operator manual-fire) was mapped to trigger="addressed" in
  `_invoke_recurrence_wake`. But the context bag it builds is the recurrence-fire
  shape (recurrence_prompt + recurrence_slug, NO user_message). invoke_freddie's
  `_validate_context_shape` correctly rejected the contradictory
  (trigger=addressed, recurrence-context) pair → returned None → the dispatcher
  recorded status="success" with NULL tokens. The Reviewer NEVER RAN, but
  telemetry said success — indistinguishable from a correct no-op stand-down.
  This is why "the agent never starts trading / silently produces nothing"
  recurred through every proximate fix.

THE FIX (two layers):
  1. Root cause: a recurrence fire is `reactive` regardless of manual-vs-cron
     (the wake_source field carries the distinction). `_invoke_recurrence_wake`
     now derives trigger="reactive" always.
  2. Defense-in-depth: the dispatcher records a None return from invoke_freddie
     as status="failed" (reviewer_returned_none), not success — so any future
     silent failure is VISIBLE.

This gate locks both, plus the contract that makes the root cause provable: the
recurrence-fire context shape validates under `reactive` and FAILS under
`addressed` (which is exactly the mismatch the old mapping produced).

Run: .venv/bin/python api/test_silent_wake_trigger_fix.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS = 0
FAIL = 0


def check(name: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


# ── 1. The contract that proves the root cause ──────────────────────────────
# A recurrence-fire context (recurrence_prompt + recurrence_slug, no
# user_message) must VALIDATE under trigger=reactive and FAIL under
# trigger=addressed. The old manual_fire→addressed mapping forced the failing
# branch on every manual recurrence fire.
from agents.freddie_agent import _validate_context_shape  # noqa: E402

recurrence_ctx = {
    "recurrence_prompt": "Reconcile yesterday's outcomes.",
    "recurrence_slug": "outcome-reconciliation",
    "wake_source": "manual_fire",
}
check(
    "recurrence-fire context VALIDATES under trigger=reactive",
    _validate_context_shape("reactive", recurrence_ctx, "u") is None,
)
check(
    "recurrence-fire context FAILS under trigger=addressed (the old bug's mismatch)",
    _validate_context_shape("addressed", recurrence_ctx, "u") is not None,
)

# An addressed context (user_message) is the opposite — valid under addressed,
# invalid under reactive. Confirms the validator is shape-correct, not lenient.
addressed_ctx = {"user_message": "Reviewer, what's your read?"}
check(
    "addressed context VALIDATES under trigger=addressed",
    _validate_context_shape("addressed", addressed_ctx, "u") is None,
)


# ── 2. _invoke_recurrence_wake derives trigger=reactive (root-cause fix) ─────
wake_src = (Path(__file__).resolve().parent / "services" / "wake.py").read_text()
# The fixed derivation: trigger = "reactive" (not the old conditional).
check(
    "wake.py derives trigger='reactive' for recurrence fires (not manual_fire→addressed)",
    'trigger = "reactive"' in wake_src
    and 'trigger = "addressed" if wake_source == "manual_fire"' not in wake_src,
)


# ── 3. Dispatcher records None return as failed, not success (defense) ───────
check(
    "dispatcher records a None reviewer_output as status='failed' (reviewer_returned_none)",
    'error_reason="reviewer_returned_none"' in wake_src
    and "SILENT WAKE" in wake_src,
)
check(
    "dispatcher no longer blindly records success when reviewer_output is None",
    "_ro = reviewer_output if isinstance(reviewer_output, dict) else None" in wake_src,
)


# ── 4. invoke_freddie captures the full traceback on swallow-to-None ────────
rev_src = (Path(__file__).resolve().parent / "agents" / "freddie_agent.py").read_text()
check(
    "invoke_freddie logs full traceback (logger.exception) on its swallow-to-None path",
    "logger.exception(" in rev_src
    and "invoke_freddie raised" in rev_src,
)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
