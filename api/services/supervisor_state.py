"""The Supervisor app's served state (ADR-656 §7) — its three bands, read.

The app's surface renders DECLARED sections, so something must answer what each
one shows. That is this module: three bounded reads, one per band, each over
material that ALREADY EXISTS.

    needs-you  → `mentions.list_mentions`  (ADR-605/637's attention derivation)
    threads    → the member's conversations (`chat_sessions` + cast membership)
    note       → one rendered `.md` from the workspace

⭐ NOTHING HERE IS A NEW SOURCE OF TRUTH. Each band is a READING of a ledger
that other surfaces already read — which is the test ADR-435 set and the last
composition failed. The difference is the COMPOSITION: no other surface shows
work in flight, so this one redirects to nothing.

⚠️ EVERY BAND DEGRADES CLOSED AND INDEPENDENTLY. This payload drives a surface;
a band that cannot be read returns empty rather than failing the pane, and one
band's failure never blanks the other two. The ADR-630/653 posture for a
member-facing read: a broken part must not be able to take the whole surface
down with it.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: How many threads the band shows. A bound read: this runs on a surface the
#: member opens, and a supervisor that lists two hundred conversations has
#: answered "what is underway" with "everything", which is the same as nothing.
THREAD_CAP = 30

#: How many unresolved mentions the band shows. Smaller than the thread cap on
#: purpose — band 2's discipline is that most of the time there is nothing to
#: raise, and a long "waiting on you" list is the noise failure with a scrollbar.
NEEDS_YOU_CAP = 10

#: The app's own note. `supervisor/` holds what the app knows ABOUT the work as
#: a whole; the work itself lives where it belongs (ADR-384, directory is
#: meaning) and is never copied here.
DECISIONS_PATH = "/workspace/supervisor/DECISIONS.md"


def _needs_you(workspace_id: str, user_id: str) -> list[dict]:
    """Band: *what is waiting on me?* — the ONE attention derivation.

    ⚠️ Reuses `mentions.list_mentions` rather than re-deriving. ADR-637 gives
    attention ONE cursor, advanced by visiting; a second reader with its own
    idea of "unresolved" would make the badge and this band disagree, which is
    the two-authorities defect ADR-495 D3 records for the cast.
    """
    try:
        from services.mentions import list_mentions

        rows = list_mentions(workspace_id, user_id, limit=NEEDS_YOU_CAP) or []
    except Exception as exc:  # noqa: BLE001 — a band never fails the surface
        logger.warning("[SUPERVISOR] needs-you unavailable: %s", exc)
        return []

    return [
        {
            "lane_id": r.get("conversation_id"),
            "title": r.get("conversation_name") or "a conversation",
            "excerpt": r.get("excerpt") or "",
            "at": r.get("at"),
        }
        for r in rows
        if r.get("conversation_id")
    ]


def _threads(client: Any, user_id: str) -> list[dict]:
    """Band: *what is underway?* — the member's conversations, newest first.

    ⭐ THE KIND THIS APP EXISTS FOR. No other surface shows work in flight:
    Files shows files, Chat shows one conversation at a time, Notifications
    shows what already happened. This band is why the app is not the
    "glorified redirect" ADR-435 deleted the last composition for being.

    The resident is DERIVED per row (`_lane_agent`), never stored — so a thread
    reads as belonging to whoever its app declares TODAY (ADR-597 D1).
    """
    try:
        from routes.lanes import _lane_agent

        rows = (
            client.table("chat_sessions")
            .select("id, status, context_metadata, updated_at")
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("updated_at", desc=True)
            .limit(THREAD_CAP)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[SUPERVISOR] threads unavailable: %s", exc)
        return []

    out: list[dict] = []
    for row in rows:
        meta = ((row.get("context_metadata") or {}).get("lane")) or {}
        if not meta:
            continue  # not a lane — a legacy session shape, not work in flight
        out.append({
            "lane_id": row.get("id"),
            "title": meta.get("name") or "Untitled",
            # The app this thread belongs to — the routing edge (ADR-656 §4).
            # Empty means it belongs to nothing, which is the gap routing fills.
            "app": meta.get("app") or "",
            "agent": _lane_agent(meta) or "",
            "at": row.get("updated_at"),
        })
    return out


def _note(client: Any, user_id: str) -> Optional[dict]:
    """Band: *what did we decide?* — one rendered `.md`, or None.

    Absent is a normal state, not an error: a workspace that has decided
    nothing yet has no file, and the surface says so in its own words.
    """
    try:
        from services.workspace_context import substrate_scope_filter

        rows = (
            client.table("workspace_files")
            .select("path, content")
            .eq(*substrate_scope_filter(user_id))
            .eq("path", DECISIONS_PATH)
            .limit(1)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[SUPERVISOR] note unavailable: %s", exc)
        return None

    if not rows:
        return None
    content = (rows[0].get("content") or "").strip()
    if not content:
        return None
    return {"path": rows[0].get("path"), "content": content}


def supervisor_state(client: Any, user_id: str, workspace_id: str) -> dict:
    """The three bands, composed. Never raises.

    ⚠️ The bands are read INDEPENDENTLY and each degrades to its own empty.
    One unreadable band must not blank the surface — a pane that goes dark
    because a mention query timed out has told the member their work vanished.
    """
    return {
        "needs_you": _needs_you(workspace_id, user_id),
        "threads": _threads(client, user_id),
        "note": _note(client, user_id),
    }
