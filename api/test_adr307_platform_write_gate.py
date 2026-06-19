"""ADR-307 platform-write gate regression — the 2026-06-19 streamlining.

Closes the gap the finding surfaced (docs/evaluations/2026-06-19-platform-
write-gate-streamlining-FINDING.md): consequential platform writes bypassed
the uniform gate (`execute_primitive` early-returned at `is_platform_tool`
BEFORE `resolve_permission`), forcing `submit_order` to hand-roll its own
autonomy branch.

The correct streamlining = "one gate DECISION, family-shaped ENQUEUE":
  - the autonomy decision is made in ONE place (resolve_permission), for ALL
    consequential platform writes, regardless of caller;
  - a QUEUE outcome routes to a family-appropriate enqueue (capital /
    external-write) — never one queue forcing a Slack post into a file-diff;
  - the live capital path is NOT regressed: the risk gate survives as a domain
    pre-check, and an operator-approved replay (ExecuteProposal injects
    `_proposal_id`) applies without re-gating.

Run: ./venv/bin/python test_adr307_platform_write_gate.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.primitives.permission import resolve_permission, PermissionDecision  # noqa: E402
from services.platform_tools import (  # noqa: E402
    consequential_platform_family,
    is_consequential_platform_tool,
)


def _gate(auth, name, inputs, *, delegation="bounded"):
    with patch("services.review_policy.load_autonomy", return_value={}), \
         patch("services.review_policy.autonomy_for_domain",
               return_value={"delegation": delegation, "ceiling_cents": 20000}):
        return asyncio.run(resolve_permission(auth, name, inputs))


# ---------------------------------------------------------------------------
# Classifier — the single source of truth for consequence family
# ---------------------------------------------------------------------------

def test_classifier_partitions_platform_tools():
    # capital: trading + commerce money movers
    assert consequential_platform_family("platform_trading_submit_order") == "capital"
    assert consequential_platform_family("platform_commerce_issue_refund") == "capital"
    # external-write: audience-addressing sends
    assert consequential_platform_family("platform_slack_send_to_channel") == "external-write"
    assert consequential_platform_family("platform_notion_create_page") == "external-write"
    assert consequential_platform_family("platform_notion_append_block") == "external-write"
    assert consequential_platform_family("platform_email_send") == "external-write"
    # reads: NOT consequential (keep the fast early-return)
    assert consequential_platform_family("platform_slack_get_channel_history") is None
    assert consequential_platform_family("platform_trading_get_account") is None
    # operator-addressing infrastructure: NOT an audience-write (ADR-299/304 —
    # addressee structurally pinned to the operator's own identity)
    assert consequential_platform_family("platform_slack_send_message") is None
    assert consequential_platform_family("platform_notion_create_comment") is None
    assert is_consequential_platform_tool("platform_trading_submit_order")
    assert not is_consequential_platform_tool("platform_slack_get_channel_history")


# ---------------------------------------------------------------------------
# The uniform gate now engages for consequential platform writes
# ---------------------------------------------------------------------------

def test_execute_primitive_gates_consequential_platform_writes():
    """The platform-tool path is no longer an unconditional bypass: reads keep
    the fast early-return; consequential writes consult resolve_permission +
    route a QUEUE to the family enqueue."""
    from services.primitives import registry
    src = inspect.getsource(registry.execute_primitive)
    assert "is_consequential_platform_tool" in src
    assert "resolve_permission" in src
    assert "_enqueue_platform_write_proposal" in src


def test_platform_reads_never_gate():
    """A platform read resolves APPLY on the read fast-path (it is not in
    READ_ONLY_PRIMITIVES, but the gate's platform branch only engages for
    consequential writes — reads never reach resolve_permission's write
    branch)."""
    # A non-reviewer specialist calling a platform read: APPLY (non-reviewer
    # short-circuit; the consequential-platform branch does not match a read).
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="specialist:tracker")
    decision, reason = _gate(auth, "platform_trading_get_account", {})
    assert decision == PermissionDecision.APPLY
    assert reason == "non_reviewer_caller"


# ---------------------------------------------------------------------------
# External-write family — the NEW gated path (Slack/Notion audience-writes)
# ---------------------------------------------------------------------------

def test_external_write_queues_under_bounded():
    """A specialist (reviewer_caller=False) audience-write under bounded QUEUEs
    — the gate engages regardless of caller (the bug was these inheriting the
    non-reviewer free-pass)."""
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="specialist:writer")
    decision, reason = _gate(auth, "platform_slack_send_to_channel",
                             {"channel_id": "C1", "text": "hi"}, delegation="bounded")
    assert decision == PermissionDecision.QUEUE, reason
    assert reason.startswith("autonomy_requires_approval")


def test_external_write_applies_under_autonomous():
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="specialist:writer")
    decision, reason = _gate(auth, "platform_notion_create_page",
                             {"title": "x"}, delegation="autonomous")
    assert decision == PermissionDecision.APPLY, reason
    assert reason.startswith("autonomy_allows")


def test_external_write_queues_under_manual():
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="specialist:writer")
    decision, reason = _gate(auth, "platform_email_send",
                             {"to": "a@b.c"}, delegation="manual")
    assert decision == PermissionDecision.QUEUE, reason


# ---------------------------------------------------------------------------
# Capital safety floor — irreversible always routes to operator (no autonomous
# auto-bind under manual/bounded); the live path never lands here.
# ---------------------------------------------------------------------------

def test_capital_direct_call_queues_under_bounded():
    """A direct capital call WITHOUT a proposal under bounded → QUEUE
    (irreversible-always-queue safety net). This is the floor, not the live
    path."""
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="specialist:tracker")
    decision, reason = _gate(auth, "platform_trading_submit_order",
                             {"ticker": "AAPL", "side": "buy", "qty": 1,
                              "order_type": "market"}, delegation="bounded")
    assert decision == PermissionDecision.QUEUE, reason


def test_capital_direct_call_queues_under_manual():
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="specialist:tracker")
    decision, reason = _gate(auth, "platform_commerce_issue_refund",
                             {"order_id": "o1"}, delegation="manual")
    assert decision == PermissionDecision.QUEUE, reason


# ---------------------------------------------------------------------------
# THE load-bearing capital-path invariant: an operator-approved REPLAY applies
# without re-gating (ExecuteProposal injects _proposal_id). Without this the
# approve → ExecuteProposal → execute_primitive replay would re-queue forever.
# ---------------------------------------------------------------------------

def test_approved_proposal_replay_applies_without_regate():
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="operator")
    decision, reason = _gate(
        auth, "platform_trading_submit_order",
        {"ticker": "AAPL", "side": "buy", "qty": 1, "order_type": "market",
         "_proposal_id": "abc-123"},
        delegation="manual",  # even under manual, the replay applies
    )
    assert decision == PermissionDecision.APPLY, reason
    assert reason == "approved_proposal_replay"


def test_external_write_replay_applies_without_regate():
    auth = SimpleNamespace(reviewer_caller=False, user_id="u", client=None,
                           caller_identity="operator")
    decision, reason = _gate(
        auth, "platform_slack_send_to_channel",
        {"channel_id": "C1", "text": "hi", "_proposal_id": "p1"},
        delegation="manual",
    )
    assert decision == PermissionDecision.APPLY
    assert reason == "approved_proposal_replay"


# ---------------------------------------------------------------------------
# The risk gate SURVIVES as a domain pre-check (NOT deleted with the bespoke
# autonomy branch). And the bespoke `mode == autonomous` → ProposeAction branch
# is GONE from the trading writes (Singular Implementation).
# ---------------------------------------------------------------------------

def test_external_write_enqueue_shapes_decision_context():
    """The external-write family enqueue carries an EFFECT preview
    (channel/recipient + content preview), never a file diff or capital fields.
    Verifies _platform_write_preview + the family dispatch in
    _enqueue_platform_write_proposal."""
    from services.primitives import registry

    slack = registry._platform_write_preview(
        "platform_slack_send_to_channel",
        {"channel_id": "C9", "text": "ship it", "_proposal_id": "x"},
    )
    assert slack == {"channel": "C9", "preview": "ship it"}, slack

    page = registry._platform_write_preview(
        "platform_notion_create_page",
        {"parent_page_id": "P1", "title": "Q3 report", "content": "body here"},
    )
    assert page == {"parent": "P1", "title": "Q3 report", "preview": "body here"}, page

    # The dispatch-layer _proposal_id never leaks into the preview.
    assert "_proposal_id" not in slack


def test_capital_and_external_write_tools_registered():
    """The audience-write tools exist (Commit 3) and the kernel-universal
    capabilities point at them — not at the operator-addressing infra tools."""
    from services.platform_tools import (
        PLATFORM_TOOLS_BY_CAPABILITY, CAPABILITY_PROVIDER_MAP,
        SLACK_TOOLS, NOTION_TOOLS,
    )
    slack_names = {t["name"] for t in SLACK_TOOLS}
    notion_names = {t["name"] for t in NOTION_TOOLS}
    assert "platform_slack_send_to_channel" in slack_names
    assert "platform_notion_create_page" in notion_names
    assert "platform_notion_append_block" in notion_names
    assert PLATFORM_TOOLS_BY_CAPABILITY["write_slack"] == ["platform_slack_send_to_channel"]
    assert PLATFORM_TOOLS_BY_CAPABILITY["write_notion"] == [
        "platform_notion_create_page", "platform_notion_append_block",
    ]
    assert CAPABILITY_PROVIDER_MAP["write_slack"] == "slack"
    assert CAPABILITY_PROVIDER_MAP["write_notion"] == "notion"


def test_risk_gate_survives_in_trading_writes():
    from services import platform_tools
    src = inspect.getsource(platform_tools._handle_trading_tool)
    # The domain risk gate is still called on every order write.
    assert src.count("check_risk_limits") >= 3, "risk gate must remain on submit_order/bracket/trailing"
    # The bespoke autonomy branch (its tell: emitting a proposal on autonomous
    # risk-rejection) is deleted — the gate owns autonomy now.
    assert "risk_limit_violation_proposed" not in src, (
        "submit_order's bespoke `mode == autonomous` → ProposeAction branch must "
        "be deleted — the uniform gate owns the autonomy decision (ADR-307)"
    )
    assert 'if mode == "autonomous"' not in src, (
        "no platform tool gates itself on autonomy mode — that decision lives "
        "in resolve_permission (ADR-307 D1)"
    )


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
