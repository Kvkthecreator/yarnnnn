"""ADR-352 regression gate — ask-vs-act as a governance-derived outcome.

Clarify is gate-owned (no longer read-only). The ask-gate in resolve_permission
derives APPLY/DENY from the witness dial (_autonomy.yaml delegation):

  - bounded/manual            → APPLY (operator wants to witness; asking is theirs)
  - autonomous, no flag       → DENY  (the seat must act; ADR-344 (A) quiet-world)
  - autonomous, structural_gap→ APPLY (the ADR-344 (B) escalation — only ask permitted)
  - non-reviewer caller        → APPLY (asking scoped to the Reviewer seat, ADR-293)

Run: api/venv/bin/python -m pytest api/test_adr352_ask_gate.py -q
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.primitives.permission import (  # noqa: E402
    resolve_permission,
    PermissionDecision,
    READ_ONLY_PRIMITIVES,
    is_read_only,
)


def _gate(auth, inputs, *, delegation):
    with patch("services.review_policy.load_autonomy", return_value={}), \
         patch("services.review_policy.autonomy_for_domain",
               return_value={"delegation": delegation, "ceiling_cents": 20000}):
        return asyncio.run(resolve_permission(auth, "Clarify", inputs))


def _reviewer_auth():
    return SimpleNamespace(reviewer_caller=True, user_id="u", client=None,
                           caller_identity="reviewer:ai:reviewer-sonnet-v8")


# ---------------------------------------------------------------------------
# D1 — Clarify is no longer read-only (it is gate-owned).
# ---------------------------------------------------------------------------

def test_clarify_not_read_only():
    assert "Clarify" not in READ_ONLY_PRIMITIVES
    assert not is_read_only("Clarify")
    # ReturnVerdict stays read-only — only Clarify was reclassified.
    assert "ReturnVerdict" in READ_ONLY_PRIMITIVES
    assert is_read_only("ReturnVerdict")


# ---------------------------------------------------------------------------
# D2 — the ask-gate derivation from the witness dial.
# ---------------------------------------------------------------------------

def test_autonomous_no_flag_denies_act_is_default():
    """The kvk-finding case: autonomous + a plain enumerated ask → DENY (act)."""
    decision, reason = _gate(
        _reviewer_auth(),
        {"question": "Wait for Monday, or override the signal rule?",
         "options": ["A: wait", "B: override"]},
        delegation="autonomous",
    )
    assert decision == PermissionDecision.DENY
    assert reason == "ask_denied:autonomous_default_is_act"


def test_autonomous_structural_gap_applies():
    """The ADR-344 (B) escalation is the one ask autonomous permits."""
    decision, reason = _gate(
        _reviewer_auth(),
        {"question": "No organ originates the next piece — author a compose "
                     "recurrence (Path B) or reinterpret the mandate?",
         "structural_gap": True},
        delegation="autonomous",
    )
    assert decision == PermissionDecision.APPLY
    assert reason == "ask_permitted:structural_gap"


def test_autonomous_structural_gap_must_be_true_not_truthy():
    """Fail-closed: only the literal boolean True opens the valve, not a
    truthy string that a confused model might pass."""
    decision, _ = _gate(
        _reviewer_auth(),
        {"question": "q", "structural_gap": "yes"},
        delegation="autonomous",
    )
    assert decision == PermissionDecision.DENY


def test_bounded_applies_witness_wants_choice():
    decision, reason = _gate(
        _reviewer_auth(), {"question": "q", "options": ["a", "b"]},
        delegation="bounded",
    )
    assert decision == PermissionDecision.APPLY
    assert reason == "ask_permitted:witness_mode:bounded"


def test_manual_applies_witness_wants_choice():
    decision, reason = _gate(
        _reviewer_auth(), {"question": "q"}, delegation="manual",
    )
    assert decision == PermissionDecision.APPLY
    assert reason == "ask_permitted:witness_mode:manual"


# ---------------------------------------------------------------------------
# D2 — scoping: asking is governed for the Reviewer seat only.
# ---------------------------------------------------------------------------

def test_non_reviewer_caller_may_ask_freely():
    """Operator / headless / MCP callers are not the installed judgment;
    the witness dial does not govern their asking. APPLY without touching
    load_autonomy (the branch returns before the policy read)."""
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="operator")
    decision, reason = asyncio.run(
        resolve_permission(auth, "Clarify", {"question": "q"})
    )
    assert decision == PermissionDecision.APPLY
    assert reason == "ask_permitted:non_reviewer_caller"


# ---------------------------------------------------------------------------
# Fail-open on policy-read error (asking defaults to witness-mode APPLY —
# a denied ask under uncertainty would silently swallow a genuine escalation).
# ---------------------------------------------------------------------------

def test_ask_gate_fails_open_on_policy_error():
    auth = _reviewer_auth()
    with patch("services.review_policy.load_autonomy",
               side_effect=RuntimeError("boom")):
        decision, reason = asyncio.run(
            resolve_permission(auth, "Clarify", {"question": "q"})
        )
    assert decision == PermissionDecision.APPLY
    assert reason.startswith("ask_gate_error:")


# ---------------------------------------------------------------------------
# D4 — the Clarify tool advertises structural_gap + drops the permissive copy.
# ---------------------------------------------------------------------------

def test_clarify_tool_description_and_schema():
    from services.primitives.registry import CLARIFY_TOOL
    desc = CLARIFY_TOOL["description"]
    assert "structural_gap" in CLARIFY_TOOL["input_schema"]["properties"]
    # The forbidden permissive phrasing is gone.
    assert "want to offer choices" not in desc
    # The escalation framing is present.
    assert "structural" in desc.lower()


# ---------------------------------------------------------------------------
# D5 — the persona-frame shrank: the runtime is named as the enforcer.
# ---------------------------------------------------------------------------

def test_frame_points_at_ask_gate_not_just_prose():
    frame_src = (API_DIR / "agents" / "reviewer_agent.py").read_text()
    # The frame now references the ADR-352 enforcement rather than relying on
    # imperative prose alone.
    assert "ADR-352" in frame_src
    assert "structural_gap" in frame_src
    # The old hard-coded "(1)... or (2)... or (3)...?" enumeration sermon is gone.
    assert "(1)... or (2)... or (3)...?" not in frame_src


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
