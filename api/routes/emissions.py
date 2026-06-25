"""
Emissions endpoint — the operation's outbound boundary (ADR-370, Context → Out lens).

`GET /api/emissions` projects a read-only ledger of what this operation
emitted to the outside world on the operator's behalf: operator-addressing
dispatches (email / Slack / Notion sends) — what shipped, to whom, when, and
whether it landed.

This is a LEGIBILITY view, never a send affordance. Operator-addressing
writes are SYSTEM INFRASTRUCTURE (ADR-299/304), not workspace capabilities;
the Out lens surfaces what already happened, it does not initiate sends.

No new table (ADR-370): the ledger is a read-only union over the two
existing emission records —
  - `destination_delivery_log` — multi-destination delivery results for
    workspace/agent outputs (email/Slack/Notion), migration 032.
  - `notifications` (channel='email') — operator-addressing email sends
    incl. the ADR-317 daily P&L email (source_type='system'), migration 041.

Auth boundary: derives user from `auth.user_id`. No cross-user reads (RLS).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


class Emission(BaseModel):
    """One outbound crossing — a send to the outside world.

    Normalized across the two source ledgers so the Out lens renders a single
    chronological list regardless of which table recorded the send.
    """

    id: str
    channel: str                      # email | slack | notion | in_app
    status: str                       # pending | delivering | delivered | sent | failed
    destination: Optional[str] = None  # recipient/target, best-effort human label
    external_url: Optional[str] = None  # link to the landed artifact, when known
    error_message: Optional[str] = None
    source: str                       # which ledger: 'delivery' | 'notification'
    created_at: str
    completed_at: Optional[str] = None


def _label_destination(dest: object) -> Optional[str]:
    """Best-effort human label for a jsonb destination blob.

    destination_delivery_log.destination is a jsonb describing the target
    (channel-specific shape). We surface a readable label without asserting a
    fixed schema across channels.
    """
    if isinstance(dest, dict):
        for key in ("email", "recipient", "channel", "page", "url", "name", "label"):
            val = dest.get(key)
            if isinstance(val, str) and val:
                return val
        return None
    if isinstance(dest, str) and dest:
        return dest
    return None


@router.get("", response_model=list[Emission])
async def get_emissions(auth: UserClient, limit: int = 100) -> list[Emission]:
    """List operator-addressing emissions (most recent first).

    Read-only union over `destination_delivery_log` + `notifications`
    (email channel). Merged, sorted by created_at desc, capped at `limit`.
    """
    user_id = auth.user_id
    client = auth.client
    emissions: list[Emission] = []

    # --- destination_delivery_log (agent/workspace output deliveries) ---
    try:
        rows = (
            client.table("destination_delivery_log")
            .select(
                "id, platform, status, destination, external_url, "
                "error_message, created_at, completed_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        for r in rows:
            emissions.append(
                Emission(
                    id=str(r["id"]),
                    channel=(r.get("platform") or "unknown"),
                    status=(r.get("status") or "unknown"),
                    destination=_label_destination(r.get("destination")),
                    external_url=r.get("external_url"),
                    error_message=r.get("error_message"),
                    source="delivery",
                    created_at=str(r.get("created_at")),
                    completed_at=(
                        str(r["completed_at"]) if r.get("completed_at") else None
                    ),
                )
            )
    except Exception:  # noqa: BLE001 — read-only legibility; degrade, don't fail the lens
        logger.warning("emissions: destination_delivery_log read failed", exc_info=True)

    # --- notifications (operator-addressing email sends incl. ADR-317 P&L) ---
    try:
        rows = (
            client.table("notifications")
            .select("id, channel, status, message, error_message, created_at, sent_at")
            .eq("user_id", user_id)
            .eq("channel", "email")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        for r in rows:
            msg = r.get("message")
            emissions.append(
                Emission(
                    id=str(r["id"]),
                    channel="email",
                    status=(r.get("status") or "unknown"),
                    # notifications has no structured recipient — the operator
                    # is the implicit target; surface a snippet for legibility.
                    destination=(msg[:80] if isinstance(msg, str) else None),
                    external_url=None,
                    error_message=r.get("error_message"),
                    source="notification",
                    created_at=str(r.get("created_at")),
                    completed_at=(str(r["sent_at"]) if r.get("sent_at") else None),
                )
            )
    except Exception:  # noqa: BLE001
        logger.warning("emissions: notifications read failed", exc_info=True)

    # Merge: most-recent first, capped at limit.
    emissions.sort(key=lambda e: e.created_at, reverse=True)
    return emissions[:limit]
