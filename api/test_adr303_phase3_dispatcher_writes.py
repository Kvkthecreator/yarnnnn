"""ADR-303 Phase 3 — Contract test for dispatcher-attributed silent-exit
substrate writes.

Verifies the load-bearing distinction this phase introduces:
- The dispatcher's silent-exit fallback writes to standing_intent.md
  with `authored_by="dispatcher:silent_exit_fallback"`.
- NOT `authored_by="reviewer:..."` — the distinction the reverted hotfix
  9e7c1c7 conflated, the reason ADR-303 D6 specifies dispatcher-vs-model
  attribution.
- 'dispatcher:' is a valid prefix in services.authored_substrate.

Plus: the substrate body carries exit_class metadata (text_only_mid_loop
or budget_exhausted) so post-deploy population audit per
docs/evaluations/2026-05-26-163000-posture-criterion-declaration/ §3.1
can distinguish P4 from P5 at the substrate layer.

These are unit-level contract tests. Behavioral validation comes from
the post-deploy population audit re-run against fresh substrate.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from services.authored_substrate import is_valid_author


# ---------------------------------------------------------------------------
# T1: 'dispatcher:' prefix is in the canonical author taxonomy
# ---------------------------------------------------------------------------

def test_dispatcher_prefix_is_valid_author():
    """ADR-303 D6: dispatcher-attributed substrate writes must validate
    against the canonical author taxonomy. Without this, the dispatcher
    helper would raise on every silent-exit fallback."""
    assert is_valid_author("dispatcher:silent_exit_fallback") is True


def test_dispatcher_prefix_distinct_from_reviewer_prefix():
    """The whole point of ADR-303 D6: dispatcher: and reviewer: are
    distinguishable. Future evaluations can tell model-authored intent
    from dispatcher-slot-filled fallback at the attribution layer."""
    assert is_valid_author("dispatcher:silent_exit_fallback") is True
    assert is_valid_author("reviewer:ai-reviewer-sonnet-v8") is True
    # They are not the same prefix
    assert "dispatcher:silent_exit_fallback".startswith("reviewer:") is False
    assert "reviewer:ai-reviewer-sonnet-v8".startswith("dispatcher:") is False


# ---------------------------------------------------------------------------
# T2: helper writes with dispatcher attribution + exit_class metadata
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_silent_exit_helper_uses_dispatcher_attribution_for_text_only_mid_loop():
    """ADR-303 D2+D6: text-only-mid-loop fallback must attribute the
    write as `dispatcher:silent_exit_fallback`, not `reviewer:...`."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.return_value = "test_revision_id"
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="text_only_mid_loop",
            exit_round=7,
            max_rounds=20,
            trigger="reactive",
            slug="signal-evaluation",
            prose="The model wandered into prose without wrapping in ReturnVerdict.",
        )
        assert mock_write.called
        kwargs = mock_write.call_args.kwargs
        # Load-bearing assertion: dispatcher attribution, NOT reviewer.
        assert kwargs["authored_by"] == "dispatcher:silent_exit_fallback"
        assert not kwargs["authored_by"].startswith("reviewer:")
        # Path is the canonical standing_intent.md
        assert kwargs["path"] == "/workspace/review/standing_intent.md"


@pytest.mark.asyncio
async def test_silent_exit_helper_uses_dispatcher_attribution_for_budget_exhausted():
    """Same contract for budget-exhausted (P4) — only the exit_class metadata
    differs from P5."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.return_value = "test_revision_id"
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="budget_exhausted",
            exit_round=20,
            max_rounds=20,
            trigger="reactive",
            slug="outcome-reconciliation",
            prose="Reached max_rounds without converging.",
        )
        assert mock_write.called
        kwargs = mock_write.call_args.kwargs
        assert kwargs["authored_by"] == "dispatcher:silent_exit_fallback"


@pytest.mark.asyncio
async def test_silent_exit_helper_body_carries_exit_class_metadata():
    """ADR-303 D2: substrate body must carry exit_class so post-deploy
    population audit can distinguish P4 (budget_exhausted) from P5
    (text_only_mid_loop) at the substrate layer."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.return_value = "test_revision_id"
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="text_only_mid_loop",
            exit_round=8,
            max_rounds=20,
            trigger="reactive",
            slug="signal-evaluation",
            prose="prose content",
        )
        body = mock_write.call_args.kwargs["content"]
        assert "silent_exit: text_only_mid_loop" in body
        assert "exit_round: 8" in body
        assert "max_rounds: 20" in body
        assert "posture_cell: P5" in body  # human-readable cell label


@pytest.mark.asyncio
async def test_silent_exit_helper_message_distinguishes_exit_classes():
    """ADR-209 revision message format includes exit_class so revision-
    history readers can filter by posture cell."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.return_value = "test_revision_id"
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="budget_exhausted",
            exit_round=20,
            max_rounds=20,
            trigger="reactive",
            slug="outcome-reconciliation",
            prose="prose content",
        )
        message = mock_write.call_args.kwargs["message"]
        assert "budget_exhausted" in message
        assert "20/20" in message


@pytest.mark.asyncio
async def test_silent_exit_helper_truncates_long_prose():
    """600-char snippet limit per the helper's contract — substrate revisions
    should not carry unbounded prose dumps."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    long_prose = "x" * 5000
    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.return_value = "test_revision_id"
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="text_only_mid_loop",
            exit_round=7,
            max_rounds=20,
            trigger="reactive",
            slug="test-slug",
            prose=long_prose,
        )
        body = mock_write.call_args.kwargs["content"]
        # The truncated snippet ends with the ellipsis char; original 5000
        # is not present in the body
        assert "x" * 5000 not in body
        assert "…" in body


@pytest.mark.asyncio
async def test_silent_exit_helper_never_raises_on_write_failure():
    """ADR-303 D2: dispatcher fallback failures are logged but never
    propagate. The parent fallback must still produce a verdict so the
    wake completes cleanly at the queue."""
    from agents.reviewer_agent import _dispatcher_write_silent_exit_standing_intent

    with patch("services.authored_substrate.write_revision") as mock_write:
        mock_write.side_effect = RuntimeError("simulated DB failure")
        # Should NOT raise; the helper catches Exception and logs.
        await _dispatcher_write_silent_exit_standing_intent(
            client=MagicMock(),
            user_id="test-user-id",
            exit_class="text_only_mid_loop",
            exit_round=7,
            max_rounds=20,
            trigger="reactive",
            slug="test-slug",
            prose="prose",
        )
        # No exception escaped
