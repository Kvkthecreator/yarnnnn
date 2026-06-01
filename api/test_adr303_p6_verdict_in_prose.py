"""ADR-303 §9 P6 — Contract test for verdict-in-prose recovery.

The moat-thesis pre-ship-audit silent-exited 2× because a long rule-by-rule
audit verdict was emitted as a TEXT block instead of a ReturnVerdict tool call
(channel-shape mismatch — ReturnVerdict.reasoning is sized for 2-5 sentences).
The pre-amendment loop fabricated a contradicting `stand_down`.

This gate guards the two load-bearing pieces of the §9 fix:
  1. `_looks_like_verdict` distinguishes a synthesized-but-unwrapped verdict
     (P6) from a genuinely-confused text-only exit (P5) — so the dispatcher
     recovers the real verdict instead of fabricating `stand_down`.
  2. The dispatcher fallback carries the recovered verdict + the new
     `verdict_in_prose_unrecovered` exit_class in honest substrate.

Evidence: docs/evaluations/2026-05-30-054957-author-produce-corpus-piece/
findings-silent-exit-reproduction.md
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from agents.reviewer_agent import _looks_like_verdict


# ---------------------------------------------------------------------------
# T1: _looks_like_verdict — the P5-vs-P6 discriminator
# ---------------------------------------------------------------------------

def test_audit_structure_prose_detected_as_defer():
    """The actual moat-thesis repro shape: a rule-by-rule audit document
    emitted as prose, no explicit verdict token → defer (audit ran, headline
    missing), NOT None (which would route to text_only_mid_loop)."""
    prose = (
        "## Pre-Ship Audit: moat-thesis\n"
        "### Rule 1: voice-fingerprint-match\n"
        "Substrate read: _voice.md declared fingerprint..."
    )
    assert _looks_like_verdict(prose) == "defer"


def test_explicit_reject_token_recovered():
    assert _looks_like_verdict("The draft trips the anti-slop floor. REJECT.") == "reject"


def test_explicit_approve_token_recovered():
    assert _looks_like_verdict("I approve this — voice fingerprint matches.") == "approve"


def test_explicit_defer_token_recovered():
    assert _looks_like_verdict("This should be deferred with a directive on para 3.") == "defer"


def test_real_stand_down_prose_is_not_a_wrong_channel_verdict():
    """A genuine stand-down in prose must return None so it routes to the
    existing text_only_mid_loop path — NOT misclassified as a recoverable
    verdict. This is the conservative edge that keeps P5 behavior unchanged."""
    assert _looks_like_verdict("Upstream data is stale; I'm standing down until refresh.") is None


def test_empty_and_neutral_prose_return_none():
    assert _looks_like_verdict("") is None
    assert _looks_like_verdict("   ") is None
    assert _looks_like_verdict("Some neutral narration about nothing in particular.") is None


# ---------------------------------------------------------------------------
# T2: dispatcher fallback carries recovered verdict + new exit_class
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatcher_carries_recovered_verdict_for_p6():
    """When recovery fails (nudged once, still text-only), the dispatcher
    fallback records the RECOVERED verdict (e.g. reject) + the
    verdict_in_prose_unrecovered exit_class — NOT a fabricated stand_down."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.return_value = "rev_id"
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="verdict_in_prose_unrecovered",
            exit_round=9,
            max_rounds=20,
            trigger="reactive",
            slug="pre-ship-audit",
            prose="## Pre-Ship Audit\n### Rule 1...\nREJECT — anti-slop floor tripped.",
            recovered_verdict="reject",
        )
        assert mock_write.called
        kwargs = mock_write.call_args.kwargs
        # honest attribution preserved
        assert kwargs["authored_by"] == "dispatcher:silent_exit_fallback"
        # body carries the recovered verdict + P6 cell
        assert "recovered_verdict: reject" in kwargs["content"]
        assert "P6 (verdict-in-prose, unrecovered)" in kwargs["content"]
        assert "verdict_in_prose_unrecovered" in kwargs["content"]
        # and it explicitly does NOT claim a fabricated stand_down
        assert "synthesized a `stand_down`" not in kwargs["content"]
        # message names the new exit class
        assert "verdict_in_prose_unrecovered" in kwargs["message"]


@pytest.mark.asyncio
async def test_dispatcher_p5_path_unchanged_defaults_stand_down():
    """Genuinely-confused P5 (no recovered verdict) still synthesizes
    stand_down — the unchanged path. Guards against P6 regressing P5."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.return_value = "rev_id"
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="text_only_mid_loop",
            exit_round=6,
            max_rounds=20,
            trigger="reactive",
            slug="signal-evaluation",
            prose="I'm not sure what to make of this envelope.",
        )
        kwargs = mock_write.call_args.kwargs
        assert "recovered_verdict: stand_down" in kwargs["content"]
        assert "P5 (text-only-mid-loop)" in kwargs["content"]
        assert "synthesized a `stand_down`" in kwargs["content"]
