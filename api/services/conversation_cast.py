"""The Conversation cast — participants + visibility windows (ADR-495).

A Conversation is PARTICIPANTS + TURNS. This module owns the participant half:
who is in a conversation, what they may read, and who may act on it.

THE SPECIES-BLINDNESS RULE (ADR-495 D3, enforced by
`api/test_adr495_conversation.py`): no function here branches on
`member_kind` to DECIDE read access. `member_kind` is used only to (a) route a
row to the right column (`principal_id` vs `agent_slug`), and (b) pre-select a
DEFAULT window at invite time. Both are dial settings in the ADR-405 D4 sense.
The authorization question — "is this principal in the cast, and from which
turn may they read?" — is answered identically for every participant.

Why this matters, recorded so it is not re-derived: ADR-495's own first draft
carried a `scope: private|shared` column and forked on human-invite. That was
species law in substrate costume — `private` meant "one human present", which
only reads as private if the Agent that sees every word is assumed not to count
as a reader. There is no scope field. There is a cast.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _svc():
    """The cast table is service-role-only RLS (migration 226), matching the
    `wake_queue` / `member_state` precedent: the API mediates authorization
    (workspace grant + cast membership), the table is not directly reachable.

    THE BUG THIS FIXES (live 500, 2026-07-29): every function here took a
    `client` and callers naturally passed `auth.client` — the USER-scoped
    client, which RLS rejects with 42501. Creating any conversation crashed at
    the first participant insert. Taking the client as a parameter was the
    defect: it made the wrong client expressible. The module now resolves its
    own, so no call site can get it wrong.
    """
    from services.supabase import get_service_client

    return get_service_client()

# ADR-495 D3 — class-differing DEFAULTS, overridable per invite. An Agent that
# cannot see the conversation cannot be useful in it (and this preserves
# today's behavior exactly); a colleague usually does not need your false
# starts, and "from now" is the conservative default when disclosure is
# irreversible. Neither is a rule: the caller may pass any window.
WINDOW_FULL_HISTORY = 0

HUMAN = "human"
AGENT = "agent"


def default_window(member_kind: str, *, current_max_sequence: int) -> int:
    """The PRE-SELECTED window for a new participant (never a decision).

    Agent → full history. Human → from now. Both overridable by an explicit
    `visible_from_sequence` at the call site; nothing downstream re-derives a
    window from the participant's class.
    """
    if member_kind == AGENT:
        return WINDOW_FULL_HISTORY
    return current_max_sequence + 1


def current_max_sequence(conversation_id: str) -> int:
    """Highest turn ordinal in the conversation; -1 when empty (so a
    from-now window on an empty conversation is 0 = everything that follows)."""
    rows = (
        _svc().table("session_messages")
        .select("sequence_number")
        .eq("session_id", conversation_id)
        .order("sequence_number", desc=True)
        .limit(1)
        .execute()
    ).data or []
    return int(rows[0]["sequence_number"]) if rows else -1


def list_participants(conversation_id: str) -> list[dict]:
    """The cast, oldest first. One list — humans and Agents together."""
    return (
        _svc().table("conversation_members")
        .select("member_kind, principal_id, agent_slug, visible_from_sequence, invited_by, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    ).data or []


def find_participant(conversation_id: str,
    *,
    principal_id: Optional[str] = None,
    agent_slug: Optional[str] = None,
) -> Optional[dict]:
    """One participant row, or None. Exactly one selector must be given."""
    if bool(principal_id) == bool(agent_slug):
        raise ValueError("give exactly one of principal_id / agent_slug")
    q = (
        _svc().table("conversation_members")
        .select("member_kind, principal_id, agent_slug, visible_from_sequence, invited_by")
        .eq("conversation_id", conversation_id)
    )
    q = q.eq("principal_id", principal_id) if principal_id else q.eq("agent_slug", agent_slug)
    rows = (q.limit(1).execute()).data or []
    return rows[0] if rows else None


def visibility_floor(conversation_id: str, principal_id: str) -> Optional[int]:
    """From which turn ordinal may this principal read? None = not in the cast.

    THIS IS THE AUTHORIZATION PRIMITIVE. Membership is read permission; the
    window is how much. No species check: the same call answers for a human
    member and (via `agent_slug`) for a named hand.
    """
    row = find_participant(conversation_id, principal_id=principal_id)
    if row is None:
        return None
    return int(row.get("visible_from_sequence") or 0)


def add_participant(conversation_id: str,
    *,
    workspace_id: Optional[str],
    member_kind: str,
    invited_by: str,
    principal_id: Optional[str] = None,
    agent_slug: Optional[str] = None,
    visible_from_sequence: Optional[int] = None,
) -> dict:
    """Idempotent participant insert. Returns {added, participant}.

    `visible_from_sequence=None` pre-selects the class default; any explicit
    integer wins. An existing participant is returned unchanged — re-inviting
    never silently widens a window (that would be a disclosure decision made by
    a no-op).
    """
    if member_kind not in (HUMAN, AGENT):
        raise ValueError(f"unknown member kind: {member_kind}")
    if member_kind == HUMAN and not principal_id:
        raise ValueError("a human participant needs principal_id")
    if member_kind == AGENT and not agent_slug:
        raise ValueError("an agent participant needs agent_slug")

    existing = find_participant(
        conversation_id,
        principal_id=principal_id if member_kind == HUMAN else None,
        agent_slug=agent_slug if member_kind == AGENT else None,
    )
    if existing:
        return {"added": False, "participant": existing}

    window = (
        int(visible_from_sequence)
        if visible_from_sequence is not None
        else default_window(
            member_kind, current_max_sequence=current_max_sequence(conversation_id)
        )
    )
    window = max(0, window)

    row = (
        _svc().table("conversation_members")
        .insert({
            "conversation_id": conversation_id,
            "workspace_id": workspace_id,
            "member_kind": member_kind,
            "principal_id": principal_id,
            "agent_slug": agent_slug,
            "visible_from_sequence": window,
            "invited_by": invited_by,
        })
        .execute()
    ).data[0]
    logger.info(
        "[CAST] +participant conv=%s kind=%s window=%d",
        str(conversation_id)[:8], member_kind, window,
    )
    return {"added": True, "participant": row}


def remove_participant(conversation_id: str,
    *,
    principal_id: Optional[str] = None,
    agent_slug: Optional[str] = None,
) -> bool:
    """Remove a participant. Returns True if a row went away.

    Removal ends future read access. It does not un-read what was already
    seen — an honest limit, stated rather than implied (ADR-495 D6).
    """
    q = _svc().table("conversation_members").delete().eq("conversation_id", conversation_id)
    q = q.eq("principal_id", principal_id) if principal_id else q.eq("agent_slug", agent_slug)
    return bool((q.execute()).data)


def agent_slugs(participants: list[dict]) -> list[str]:
    """The Agents in a cast, in join order — the addressable faces."""
    return [p["agent_slug"] for p in participants if p.get("member_kind") == AGENT and p.get("agent_slug")]


def human_ids(participants: list[dict]) -> list[str]:
    """The humans in a cast, in join order."""
    return [p["principal_id"] for p in participants if p.get("member_kind") == HUMAN and p.get("principal_id")]
