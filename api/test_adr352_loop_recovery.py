"""ADR-352 loop-recovery gate — the bugs the unit ask-gate could NOT catch.

The unit gate (test_adr352_ask_gate.py) proves resolve_permission returns DENY.
But the live 5x batch (2026-06-21) exposed that a DENY was being SWALLOWED
downstream:

  Bug 1 — invoke_freddie set `clarify_called_this_round = True` on ANY Clarify
          call, so a gate-DENIED Clarify still fired the "question surfaced →
          ReturnVerdict(stand_down)" nudge and closed the turn. The seat never
          acted.
  Bug 2 — surface_freddie_actions stamped clarify_question/options onto the
          persisted operator-facing message for ANY Clarify, so a DENIED
          Clarify's enumerated A/B question leaked to the operator as if asked.

Both are source-guarded here (the web package has no Python-driveable full-loop
harness for the live LLM; these assert the success-guard is present at both
sites, the regression that the batch caught).

Run: api/venv/bin/python -m pytest api/test_adr352_loop_recovery.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _src(rel: str) -> str:
    return (API_DIR / rel).read_text()


# ---------------------------------------------------------------------------
# Bug 1 — the close-the-turn nudge must gate on Clarify SUCCESS.
# ---------------------------------------------------------------------------

def test_clarify_nudge_gated_on_success():
    src = _src("agents/freddie_agent.py")
    # The flag that triggers the close-turn nudge must require the Clarify to
    # have succeeded (gate APPLIED), not merely been called.
    assert 'if name == "Clarify" and actions_taken[-1]["success"]:' in src, (
        "clarify_called_this_round must be set only when the Clarify SUCCEEDED "
        "(ADR-352 — a gate-denied Clarify must not close the turn)"
    )
    # The bare unconditional form must be gone.
    assert 'if name == "Clarify":\n                    clarify_called_this_round = True' not in src, (
        "the unconditional clarify_called_this_round assignment must be removed"
    )


# ---------------------------------------------------------------------------
# Bug 2 — the operator-facing question must surface only on Clarify SUCCESS.
# ---------------------------------------------------------------------------

def test_clarify_surfacing_gated_on_success():
    src = _src("services/freddie_chat_surfacing.py")
    assert 'if tool == "Clarify" and success:' in src, (
        "surface_freddie_actions must stamp clarify_question/options only when "
        "the Clarify SUCCEEDED (ADR-352 — a denied Clarify must not leak its "
        "enumerated question to the operator)"
    )


def test_streaming_surfacing_already_success_guarded():
    """The live SSE path already guards on success (wake.py:1660). This pins
    that invariant so a future refactor doesn't regress it."""
    src = _src("services/wake.py")
    # Both the live and drain tool_end emitters guard the narration on success.
    assert src.count("success\n                and tool_name not in _COGNITION_ONLY") >= 1 or \
           src.count("if (\n                success") >= 1, (
        "wake.py tool_end surfacing must remain success-guarded"
    )


# ---------------------------------------------------------------------------
# The denied-Clarify result carries forward guidance (ADR-318 reason-forward).
# ---------------------------------------------------------------------------

def test_ask_denied_message_forces_action():
    src = _src("services/primitives/registry.py")
    assert 'reason == "ask_denied:autonomous_default_is_act"' in src
    # The message must tell the seat to ACT and how to re-ask legitimately.
    assert "Do NOT enumerate options" in src
    assert "structural_gap=true" in src


# ---------------------------------------------------------------------------
# The gate decision is observable (always-on telemetry) — so a live eval reads
# the decision instead of inferring it from downstream surfacing.
# ---------------------------------------------------------------------------

def test_ask_gate_decision_logged():
    src = _src("services/primitives/permission.py")
    assert "[ASK-GATE]" in src, "the ask-gate must emit an always-on decision log line"
    assert "_resolve_ask_gate" in src


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
