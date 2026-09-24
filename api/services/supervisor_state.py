"""The Supervisor app's served state (ADR-656 §7 → ADR-658 D5 → ADR-666 D8) — one band, read.

The app's surface renders DECLARED sections, so something must answer what each
one shows. For the one band built from material that is NOT a run and NOT a
declaration, that is this module:

    needs-you  → `mentions.list_mentions`  (ADR-605/637's attention derivation)

Every other band reads its ONE route directly (ADR-666 D8):

    running · recent  → `GET /api/runs`      (routes/runs.py) — the run ledger
    needs-you (runs)  → the same read: runs waiting on the viewer, recent failures
    work              → `GET /api/standing`  (routes/standing_work.py) — the roster

A second composition of those rows here would be the two-readers drift ADR-637
ended for attention.

⚠️ `note` is DELETED (ADR-666 D8): `DECISIONS.md` had no writer (ADR-656 §8 said
so) and no workspace held one (0 rows, 2026-09-24) — a band that rendered its
honest empty forever. `threads` went before it (ADR-658 §2).

⚠️ THE BAND DEGRADES CLOSED. A read that fails returns empty rather than failing
the pane (the ADR-630/653 posture for a member-facing read).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: How many unresolved mentions the band shows. Small on purpose — the band's
#: discipline is that most of the time there is nothing to raise, and a long
#: "waiting on you" list is the noise failure with a scrollbar.
NEEDS_YOU_CAP = 10


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


def supervisor_state(client: Any, user_id: str, workspace_id: str) -> dict:
    """The composed band. Never raises."""
    return {"needs_you": _needs_you(workspace_id, user_id)}
