"""ADR-303 Phase 4 — Contract test for the visibility-first failure-
surfacing invert at services/reviewer_chat_surfacing.py.

Verifies:
- SILENCE_FAILURE_REASONS denylist is narrow (transient noise only).
- should_surface_failed_action defaults to surface (visibility-first
  default) for unknown failure reasons.
- Denylisted failures (rate_limited, transient_network) are silenced.
- Operator-relevant failures (path_locked, schema_validation_failed,
  etc.) surface — they are NOT in the denylist, even though they
  aren't pre-enumerated.
- narrate_reviewer_action_blocked composes informative messages
  carrying tool + target + failure_reason.

These are unit-level contract tests. Behavioral validation comes from
the post-deploy population audit re-run per
docs/evaluations/2026-05-26-163000-posture-criterion-declaration §3.
"""

from __future__ import annotations

from services.reviewer_chat_surfacing import (
    SILENCE_FAILURE_REASONS,
    should_surface_failed_action,
    narrate_reviewer_action_blocked,
)


# ---------------------------------------------------------------------------
# T1: denylist is narrow by design (ADR-303 D3)
# ---------------------------------------------------------------------------

def test_silence_denylist_is_narrow():
    """The denylist intentionally starts with only known transient-noise
    classes. Operator-relevant failures are NEVER on it. The narrowness
    is the discipline."""
    # All entries must be transient infrastructure noise, not operator-
    # actionable. The list grows only through observation of new
    # transient-noise classes — never preemptively.
    expected_initial_classes = frozenset({
        "rate_limited",
        "transient_network",
        "retried_successfully_in_cycle",
    })
    assert SILENCE_FAILURE_REASONS == expected_initial_classes


# ---------------------------------------------------------------------------
# T2: visibility-first default behavior
# ---------------------------------------------------------------------------

def test_unknown_failure_reason_defaults_to_surface():
    """ADR-303 D3 visibility-first default: unknown failure reasons
    surface, not silence. The cost of false-surfacing is one extra
    feed entry; the cost of false-filtering is invisible cognition.
    The asymmetry favors surfacing."""
    action = {
        "tool": "WriteFile",
        "success": False,
        "failure_reason": "some_novel_failure_class",
    }
    assert should_surface_failed_action(action) is True


def test_missing_failure_reason_defaults_to_surface():
    """No failure_reason captured → still surface. The narrative entry
    will explain the action failed without a specific reason; operator
    decides if it warrants follow-up."""
    action = {"tool": "WriteFile", "success": False}
    assert should_surface_failed_action(action) is True


def test_empty_failure_reason_defaults_to_surface():
    """Empty string failure_reason → still surface."""
    action = {"tool": "WriteFile", "success": False, "failure_reason": ""}
    assert should_surface_failed_action(action) is True


def test_whitespace_failure_reason_defaults_to_surface():
    """Whitespace-only failure_reason → still surface (treated as empty)."""
    action = {"tool": "WriteFile", "success": False, "failure_reason": "   "}
    assert should_surface_failed_action(action) is True


# ---------------------------------------------------------------------------
# T3: denylist silences known transient noise
# ---------------------------------------------------------------------------

def test_rate_limited_failure_is_silenced():
    """Known transient infrastructure noise — silenced."""
    action = {
        "tool": "platform_trading_get_account",
        "success": False,
        "failure_reason": "rate_limited",
    }
    assert should_surface_failed_action(action) is False


def test_transient_network_failure_is_silenced():
    action = {
        "tool": "WebSearch",
        "success": False,
        "failure_reason": "transient_network",
    }
    assert should_surface_failed_action(action) is False


# ---------------------------------------------------------------------------
# T4: operator-relevant failure reasons surface (load-bearing assertion)
# ---------------------------------------------------------------------------

def test_path_locked_failure_surfaces():
    """ADR-303 D3 load-bearing: WriteFile refused by lock-set is exactly
    the operator-actionable signal that motivated the visibility-first
    invert. MUST surface."""
    action = {
        "tool": "WriteFile",
        "success": False,
        "failure_reason": "path_locked",
        "input": {"path": "/workspace/governance/_autonomy.yaml"},
    }
    assert should_surface_failed_action(action) is True


def test_capability_required_missing_failure_surfaces():
    """Platform tool called for capability not connected → operator may
    want to connect it. Surface."""
    action = {
        "tool": "platform_trading_get_account",
        "success": False,
        "failure_reason": "capability_required_missing",
    }
    assert should_surface_failed_action(action) is True


def test_schema_validation_failed_surfaces():
    """ProposeAction with invalid shape → operator may want to amend
    principles or the proposal schema. Surface."""
    action = {
        "tool": "ProposeAction",
        "success": False,
        "failure_reason": "schema_validation_failed",
    }
    assert should_surface_failed_action(action) is True


def test_permission_denied_surfaces():
    """Explicit operator-policy refusal — definitely operator-actionable."""
    action = {
        "tool": "WriteFile",
        "success": False,
        "failure_reason": "permission_denied",
    }
    assert should_surface_failed_action(action) is True


# ---------------------------------------------------------------------------
# T5: narration composes informative blocked-action messages
# ---------------------------------------------------------------------------

def test_blocked_narration_includes_target_and_failure_reason():
    # ADR-365 (register follows consumer): the blocked line is operator-facing.
    # ADR-303's visibility intent (the operator can SEE the failure + act on it)
    # is preserved via the failure reason + target; the internal tool name and
    # the word "blocked" are the internal vocabulary ADR-365 drops.
    body = narrate_reviewer_action_blocked(
        "WriteFile",
        "",
        failure_reason="path_locked",
        inp={"path": "/workspace/governance/_autonomy.yaml"},
    )
    assert "path_locked" in body
    assert "/workspace/governance/_autonomy.yaml" in body
    # Plain-English, not "Reviewer attempted WriteFile … blocked".
    assert "couldn't" in body.lower()


def test_blocked_narration_handles_missing_failure_reason():
    body = narrate_reviewer_action_blocked(
        "ProposeAction",
        "",
        failure_reason=None,
        inp={},
    )
    # Still informative that something didn't complete (ADR-303 visibility),
    # in plain English (ADR-365).
    assert "couldn't" in body.lower()


def test_blocked_narration_extracts_target_from_various_input_shapes():
    # path is the most common
    b1 = narrate_reviewer_action_blocked("WriteFile", "", failure_reason="x", inp={"path": "/p"})
    assert "/p" in b1
    # slug for Schedule
    b2 = narrate_reviewer_action_blocked("Schedule", "", failure_reason="x", inp={"slug": "my-rec"})
    assert "my-rec" in b2
    # name as fallback
    b3 = narrate_reviewer_action_blocked("OtherTool", "", failure_reason="x", inp={"name": "thing"})
    assert "thing" in b3


# ---------------------------------------------------------------------------
# T6: successful actions are unaffected by the invert (should_surface
# is only consulted for failures; success path is unchanged)
# ---------------------------------------------------------------------------

def test_should_surface_only_called_for_failed_actions_in_loop():
    """Sanity: the helper signature accepts the action dict. Successful
    actions still flow through the existing narrate_reviewer_action
    success-path; the visibility-first invert doesn't change success
    behavior. This is documented at the call site in surface_reviewer_actions."""
    # The helper itself only looks at failure_reason — for a success-action
    # dict the function technically returns based on failure_reason absence
    # (no failure_reason → defaults to surface). But the caller only
    # consults this helper when `success` is False, so the success path
    # is unaffected. This test documents the caller-discipline contract.
    success_action = {"tool": "WriteFile", "success": True}
    # If a caller ever invoked us on a success action, default-surface
    # would apply. That's harmless — but the documented usage is
    # failure-only.
    assert should_surface_failed_action(success_action) is True
