"""The Supervisor app's read door (ADR-656 §7 → ADR-658 D5 → ADR-666 D8).

ONE route. The surfaces payload says the app EXISTS and how to reach it; this
says what it SHOWS when opened — the composed band (mentions), read per
request. The roster has its own ONE reader (`GET /api/standing`) and the runs
theirs (`GET /api/runs`); the surface mounts all three.

⚠️ NO WRITE DOOR HERE, and none should be added. What the supervisor knows is
either derived (mentions) or an ordinary workspace file authored
through the ordinary file verbs. A bespoke write door would be a second
authoring face for a thing the substrate already versions and attributes, and
its body could carry keys `write_revision` never sees.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/state")
async def get_supervisor_state(auth: UserClient) -> dict:
    """What the Supervisor pane composes here: the mentions half of needs-you.

    ⚠️ Fails CLOSED on an unresolvable workspace rather than falling back to
    the owner's. ADR-501's probe is the reason: omitting the explicit binding
    let the resolver reach the owner path, so a member acting in a granted
    workspace silently read their OWN — every row correct-looking and wrong.
    """
    from routes.lanes import _acting_workspace
    from services.supervisor_state import supervisor_state

    workspace_id = _acting_workspace(auth)
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No acting workspace")

    return supervisor_state(auth.client, auth.user_id, workspace_id)
