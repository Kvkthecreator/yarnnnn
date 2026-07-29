"""ADR-502 + ADR-503 regression gate.

ADR-502 — a conversation with people is direct: the reply set derives from
the cast (2+ humans, no agent → broadcast, no engine reply); multi-human
transcripts carry authorship; edit-and-resend verifies the author.

ADR-503 — the wallet follows the grant: /api/user/limits nulls the dollar
fields without billing authority; the boolean balance states ship to all.

Source-anchored where the logic lives in route closures; the response-model
half is EXECUTED (pydantic construction).

Run: cd api && python3 -m pytest test_adr502_503_gate.py -q
"""

from __future__ import annotations

import pathlib

import pytest

API = pathlib.Path(__file__).parent
WEB = API.parent / "web"


# ---------------------------------------------------------------------------
# ADR-502 — the direct-conversation rule
# ---------------------------------------------------------------------------


def _lanes_src() -> str:
    return (API / "routes/lanes.py").read_text()


def test_dm_rule_lives_in_the_shared_turn_core():
    """The cast check must sit in _turn_stream_response (send AND regenerate
    ride it), before the draw gate (a broadcast costs nothing)."""
    src = _lanes_src()
    core = src.index("def _turn_stream_response")
    gate = src.index("check_draw", core)
    dm = src.index("humans >= 2 and agents == 0", core)
    assert dm < gate, "the DM branch must run before the draw gate"


def test_dm_turn_stamps_authorship():
    src = _lanes_src()
    assert 'authored_by=f"member:{auth.user_id}"' in src
    assert '"author_principal_id": auth.user_id' in src


def test_dm_done_frame_is_marked_direct():
    src = _lanes_src()
    assert '"direct": True' in src


def test_edit_and_resend_verifies_the_author():
    """role=user alone let one participant truncate the other's words."""
    src = _lanes_src()
    assert '(row.get("metadata") or {}).get("author_principal_id")' in src.replace("(\n", "(")
    idx = src.index("author_principal_id"), src.index("_delete_transcript_tail(auth, lane_id")
    assert idx[0] < idx[1], "author check must precede the tail truncate"
    # And the row select actually fetches the metadata it checks.
    assert '"id, role, sequence_number, metadata"' in src


def test_fe_direct_conversation_wiring():
    lane_panel = (WEB / "components/chat-surface/LanePanel.tsx").read_text()
    assert "authorPrincipalId" in lane_panel
    assert "isDirect" in lane_panel
    # Foreign user rows never offer edit-and-resend.
    assert "m.role === 'user' && !foreign && !m.id.startsWith('local-')" in lane_panel
    chat = (WEB / "components/chat-surface/ChatSurface.tsx").read_text()
    assert "laneOtherHumans" in chat
    assert "Direct chat" in chat
    client = (WEB / "lib/api/client.ts").read_text()
    assert "direct: evt.direct === true" in client


# ---------------------------------------------------------------------------
# ADR-503 — the wallet follows the grant
# ---------------------------------------------------------------------------


def test_limits_response_model_supports_the_split():
    """EXECUTED: the model accepts a member-shaped payload (null wallet) and
    an owner-shaped one, and defaults stay owner-compatible."""
    from routes.integrations import UserLimitsResponse

    member = UserLimitsResponse(
        balance_usd=None,
        spend_usd=1.25,
        raw_balance_usd=None,
        allowance_usd=None,
        topup_balance_usd=None,
        tier="starter",
        is_subscriber=True,
        billing_authority=False,
        balance_exhausted=False,
        balance_low=True,
    )
    assert member.balance_usd is None and member.billing_authority is False
    owner = UserLimitsResponse(
        balance_usd=36.93,
        spend_usd=1.25,
        raw_balance_usd=38.18,
        is_subscriber=True,
    )
    assert owner.billing_authority is True and owner.balance_usd == 36.93


def test_limits_handler_gates_the_wallet_on_authority():
    src = (API / "routes/integrations.py").read_text()
    fn = src.index("def get_user_limits")
    window = src[fn: fn + 2200]
    assert "has_billing_authority" in window
    assert "balance if authority else None" in window
    assert "balance_exhausted=balance <= 0" in window


def test_derive_balance_respects_the_split():
    usage = (WEB / "lib/subscription/usage.ts").read_text()
    assert "billing_authority === false || limits.balance_usd == null" in usage


def test_surfaces_render_the_member_state():
    menu = (WEB / "components/shell/UserMenu.tsx").read_text()
    assert "managed by the owner" in menu
    bell = (WEB / "components/shell/AttentionCenter.tsx").read_text()
    assert "The owner manages billing" in bell
    pane = (WEB / "components/subscription/UsagePaneBody.tsx").read_text()
    assert "managed by its owner" in pane


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
