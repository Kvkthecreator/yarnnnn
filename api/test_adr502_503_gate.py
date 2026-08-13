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
    ride it), before the draw gate (a broadcast costs nothing).

    This used to grep the literal `humans >= 2 and agents == 0`. The rule is
    now `direct = humans >= 2 and not cast_agents` — the same rule, spelled
    against the cast's Agent LIST rather than a count, because the list is also
    what names the responder (ADR-495 D3, group-cell fix 2026-07-30). Asserting
    on the PLACEMENT of the decision keeps the invariant (a broadcast is never
    metered) without pinning its spelling.
    """
    src = _lanes_src()
    core = src.index("def _turn_stream_response")
    gate = src.index("check_draw", core)
    cast_read = src.index("list_participants(lane_id)", core)
    dm = src.index("if direct:", core)
    assert cast_read < dm, "the cast is read before the direct decision"
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
    # `isDirect` → `hasOtherHumans` (2026-07-30). The old name bundled "other
    # humans are here" with "no Agent is here"; the polling gate wants only the
    # first, and under the old name a group chat WITH an Agent never polled.
    assert "hasOtherHumans" in lane_panel
    assert "isDirect" not in lane_panel.replace("RENAMED from `isDirect`", "")
    # Foreign user rows never offer edit-and-resend.
    assert "m.role === 'user' && !foreign && !m.id.startsWith('local-')" in lane_panel
    chat = (WEB / "components/chat-surface/ChatSurface.tsx").read_text()
    assert "laneOtherHumans" in chat
    assert "Direct chat" in chat
    client = (WEB / "lib/api/client.ts").read_text()
    assert "direct: evt.direct === true" in client


# ---------------------------------------------------------------------------
# THE GROUP CELL — 2+ humans AND an Agent (audited 2026-07-30)
#
# The cell nobody built or tested. ADR-502 covered solo (engine replies) and
# direct (nobody replies); the ORDINARY GROUP CHAT — people plus a colleague —
# was never a case, and three defects lived there: user rows written with no
# `author_principal_id` (so every participant's message rendered as the
# viewer's own), polling switched off by the Agent's presence, and a responder
# read from the creation-time scalar instead of the cast (so an Agent invited
# later never answered).
# ---------------------------------------------------------------------------


def test_user_row_attribution_is_written_once_for_every_cast_shape():
    """ONE user-row write, not one per branch.

    The attribution used to live on the direct branch alone. A group chat took
    the other branch and wrote `authored_by="operator"` with no
    `author_principal_id` — the field the FE aligns own-vs-other on.
    """
    src = _lanes_src()
    core = src.index("def _turn_stream_response")
    body = src[core : src.index("\n@router", core)]
    # CODE ONLY. The first cut of this assert matched its own explanatory
    # comment (which quotes the old `authored_by="operator"` spelling to record
    # what was wrong) and failed on correct code — a gate that greps prose is
    # testing the prose.
    code = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # Exactly one user-row write in the whole turn core.
    assert code.count('role="user"') == 1, (
        "two spellings of a lane user row is what made the group cell unreadable"
    )
    # And it is the attributed one.
    assert 'authored_by=f"member:{auth.user_id}"' in code
    assert 'authored_by="operator"' not in code, (
        "a lane user row is authored by the member who typed it, at every cast size"
    )


def test_the_responder_comes_from_the_cast():
    """ADR-495 D3 promised N Agents with addressing; the reply path read
    `lane_meta["agent"]` — the creation-time scalar the cast retired. So an
    Agent invited via the participants drill-in never replied.

    RE-DERIVED 2026-08-13. This gate pinned the literal expression
    `cast_agents[0] if cast_agents else lane_meta.get("agent")`, which was the
    INTERIM shape — join order, unconditionally — and its own docstring said so
    ("ADR-495 D3 promised N Agents WITH ADDRESSING"). Freezing the placeholder
    made the promised fix read as a violation. The standing laws are asserted
    instead, by EXECUTION where possible: the cast names the responder, the
    runner is given it, and `lane_meta` remains the pre-cast fallback only.
    """
    src = _lanes_src()
    core = src.index("def _turn_stream_response")
    body = src[core : src.index("\n@router", core)]
    assert "select_responder(" in body, "addressing selects who answers"
    assert "agent=responder" in body, "the runner is given the cast's Agent"
    assert 'lane_meta.get("agent")' in body, "pre-cast lanes keep their fallback"

    # The law, executed rather than spelled: an addressed Agent answers, and a
    # cast-mate is reachable — the two things `cast_agents[0]` made impossible.
    from services.addressing import select_responder

    cast = [
        {"member_kind": "agent", "agent_slug": "sonnet"},
        {"member_kind": "agent", "agent_slug": "lisa"},
    ]
    roster = {"sonnet": {"name": "Thinker"}, "lisa": {"name": "Lisa"}}
    assert select_responder("@lisa hi", cast, roster=roster) == ("lisa", "addressed"), (
        "the second Agent in a cast must be reachable — join order alone made "
        "every face after the first structurally unreachable"
    )
    assert select_responder("hi", cast[:1], roster=roster)[0] == "sonnet", (
        "a sole Agent still answers implicitly (ADR-492 D3's degenerate case)"
    )
    assert select_responder("hi", [], roster=roster, fallback="designer") == (
        "designer", "lane_agent",
    ), "a pre-cast lane still falls back to its creation-time scalar"


def test_polling_follows_the_people_not_the_absence_of_an_agent():
    chat = (WEB / "components/chat-surface/ChatSurface.tsx").read_text()
    assert "hasOtherHumans={laneOtherHumans(activeLane).length > 0}" in chat
    # laneOtherHumans must NOT bail out when an Agent is in the cast — that
    # early return is what disabled group-chat freshness. Anchored on the NEXT
    # declaration rather than a named sibling: this used to slice to
    # `const laneHasAgent`, which was deleted when naming went species-blind,
    # so the gate crashed on a change it had no opinion about.
    start = chat.index("const laneOtherHumans")
    helper = chat[start : chat.index("const lane", start + 10)]
    assert "member_kind === 'agent'" not in helper, (
        "who the PEOPLE are cannot depend on whether an Agent is also present"
    )


def test_the_room_is_named_species_blind():
    """A group is a group whatever its members are (ADR-495 D1 + ADR-405 §5).

    Operator-observed 2026-08-03: a cast of {you, Lisa, Thinker} rendered as
    "Lisa · Critic · GPT-5" with a "3 people" chip — naming ran the humans
    first and fell through to "the lane's Agent" when there were none, so one
    member became the room's whole identity and the other vanished. A group of
    three read as a 1:1 with a spec sheet.
    """
    chat = (WEB / "components/chat-surface/ChatSurface.tsx").read_text()
    # The title comes from EVERY participant but the viewer, not from humans.
    assert "const laneOthers" in chat
    start = chat.index("const laneLabel")
    body = chat[start : chat.index("const lane", start + 10)]
    assert "laneOthers(lane)" in body, "the title is derived from the whole cast"
    assert "laneOtherHumans" not in body, (
        "the title must not ask which participants are human"
    )
    # ONE count, read by both the chip and the sub-label, so they cannot
    # disagree (the shipped pair did: whole-cast vs humans+1).
    assert "const laneMemberCount" in chat
    assert "participantCount={laneMemberCount(activeLane)}" in chat
    # And the chip says "members", never "people", for a mixed cast.
    header = (WEB / "components/chat-surface/ConversationHeader.tsx").read_text()
    assert "{participantCount} members" in header
    assert "{participantCount} people" not in header


def test_add_is_a_first_class_header_act():
    """Growing the cast is the primary act on a conversation from outside the
    transcript. It was reachable only inside Details, which read as 'there is
    no invite here' (operator-observed 2026-08-03)."""
    header = (WEB / "components/chat-surface/ConversationHeader.tsx").read_text()
    assert "onAddParticipant" in header, "the header carries a dedicated add act"
    assert "UserPlus" in header
    chat = (WEB / "components/chat-surface/ChatSurface.tsx").read_text()
    # It routes to its OWN door, landing with the invite already open.
    assert "onAddParticipant={() => setParam({ detail: 'add' })}" in chat
    assert "startAdding={detailParam === 'add'}" in chat
    detail = (WEB / "components/chat-surface/ConversationDetail.tsx").read_text()
    assert "useState(startAdding)" in detail


def test_the_invite_names_its_next_step():
    """Almost every live workspace has ONE human, so the People section was
    empty with no hint that adding a colleague is possible — and the workspace
    invite lives on another surface with nothing linking to it."""
    detail = (WEB / "components/chat-surface/ConversationDetail.tsx").read_text()
    assert "Invite someone to the workspace" in detail
    # The pane slug is VERIFIED against workspace-settings' own switch, not
    # guessed (`access` was the first guess and does not exist).
    assert "params={{ pane: 'members' }}" in detail
    ws = (WEB / "app/(authenticated)/workspace-settings/page.tsx").read_text()
    assert 'case "members":' in ws, "the linked pane exists"


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
