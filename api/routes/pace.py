"""
Pace endpoint — kernel governance dial (ADR-312 D9).

`GET /api/pace` returns the operator's declared pace + live wake_queue
depths. Pace is the Trigger-dimension dial of the Pace + Autonomy + Persona
trifecta (ADR-298 D11) — a KERNEL governance concern, not trader-program
data. ADR-312 D9 folded this out of the legacy `/api/cockpit/*` namespace
(where trader data lived) into the kernel `/api/pace` location.

Auth boundary: derives user from `auth.user_id`. No cross-user reads.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


class PaceResponse(BaseModel):
    """ADR-298 D11 — operator pace + live queue depth for menu-bar vitals.

    Surfaces the Trigger-dimension dial of the Pace + Autonomy + Persona
    trifecta (per ADR-298 D11) alongside the wake_queue depths (paced +
    live) so the operator can see at a glance what's pending and at what
    rate it will drain.
    """

    pace_kind: Optional[str] = None      # 'hourly' | 'daily' | 'weekly' | 'continuous' | None (no pace declared)
    pace_every_iso: Optional[str] = None # numeric override (e.g., '4h'), preserved for display
    fires_per_day_cap: Optional[float] = None  # drain rate ceiling, None for continuous / no pace
    paced_lane_depth: int = 0           # pending count in the paced (cron) lane
    live_lane_depth: int = 0            # pending count in the live (addressed/substrate/manual) lane


@router.get("", response_model=PaceResponse)
async def get_pace(auth: UserClient) -> PaceResponse:
    """Return operator's declared pace + current wake_queue depths.

    Per ADR-298 D2 the queue is transient compute, not operator-readable
    substrate — but `queue_depth` is a thin telemetry-only surface for
    menu-bar display (per D2 docstring). This endpoint composes that
    helper with the operator's pace declaration.

    When the operator has no `_pace.yaml`, returns `pace_kind=None` with
    zeroed cap; the FE renders "no pace declared" copy.
    """
    from services.pace import PACE_FIRES_PER_DAY, read_pace
    from services.wake_queue import queue_depth

    try:
        pace = await read_pace(auth.client, auth.user_id)
    except Exception as exc:
        logger.warning("[PACE] read_pace failed for %s: %s", auth.user_id[:8], exc)
        pace = None

    pace_kind = pace.kind if pace is not None else None
    pace_every_iso = pace.every_iso if pace is not None else None
    fires_cap: Optional[float] = None
    if pace is not None and pace.kind != "continuous":
        fires_cap = PACE_FIRES_PER_DAY[pace.kind]

    try:
        paced_depth = queue_depth(auth.client, user_id=auth.user_id, lane="paced")
    except Exception as exc:
        logger.warning("[PACE] paced queue_depth failed: %s", exc)
        paced_depth = 0
    try:
        live_depth = queue_depth(auth.client, user_id=auth.user_id, lane="live")
    except Exception as exc:
        logger.warning("[PACE] live queue_depth failed: %s", exc)
        live_depth = 0

    return PaceResponse(
        pace_kind=pace_kind,
        pace_every_iso=pace_every_iso,
        fires_per_day_cap=fires_cap,
        paced_lane_depth=paced_depth,
        live_lane_depth=live_depth,
    )
