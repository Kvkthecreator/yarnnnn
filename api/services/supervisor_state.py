"""The Supervisor app's served state (ADR-656 §7 → ADR-658 D5) — two bands, read.

The app's surface renders DECLARED sections, so something must answer what each
one shows. That is this module for two of them: bounded reads over material
that ALREADY EXISTS.

    needs-you  → `mentions.list_mentions`  (ADR-605/637's attention derivation)
    note       → one rendered `.md` from the workspace

The third band — `work`, the app's reason (ADR-658 D5) — is NOT composed here:
it is the standing roster, and the roster has ONE reader, `GET /api/standing`
(routes/standing_work.py). A second composition of the same rows in this
payload would be the two-readers drift ADR-637 ended for attention; the
surface mounts the one route directly, beside this state.

⚠️ `threads` is DELETED (ADR-658 §2): a list of chat conversations answered
nothing a member asks, and it read `chat_sessions` — so a first-time member
opened to an empty band. The kind, its renderer and `THREAD_CAP` are gone.

⭐ NOTHING HERE IS A NEW SOURCE OF TRUTH. Each band is a READING of a ledger
that other surfaces already read — which is the test ADR-435 set and the last
composition failed. The difference is the COMPOSITION.

⚠️ EVERY BAND DEGRADES CLOSED AND INDEPENDENTLY. This payload drives a surface;
a band that cannot be read returns empty rather than failing the pane, and one
band's failure never blanks the other. The ADR-630/653 posture for a
member-facing read: a broken part must not be able to take the whole surface
down with it.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: How many unresolved mentions the band shows. Small on purpose — the band's
#: discipline is that most of the time there is nothing to raise, and a long
#: "waiting on you" list is the noise failure with a scrollbar.
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
    """The two composed bands. Never raises.

    ⚠️ The bands are read INDEPENDENTLY and each degrades to its own empty.
    One unreadable band must not blank the surface — a pane that goes dark
    because a mention query timed out has told the member their work vanished.
    """
    return {
        "needs_you": _needs_you(workspace_id, user_id),
        "note": _note(client, user_id),
    }
