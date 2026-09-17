"""Member-app routes — the declaration, served to its own surface (ADR-653).

ONE read route. An app's surface needs what the surfaces roster deliberately
WITHHOLDS: the declared sections it renders, and the agent whose name band 2
carries (APP-BUILDER-UX §2.2). The roster row carries neither, on purpose —
`surface_row` is gate-asserted to hold no `agent`, `resident`, `model` or any
authority-shaped key, because it rides the payload every shell load fetches.

So the split is: the ROSTER says an app exists and how to reach it; this route
says what it looks like when you open it. One row on every load, one detail
read when a member actually opens the pane.

⚠️ NO WRITE DOOR HERE. A declaration is an ordinary workspace file, authored
through the ordinary file verbs by a member or their agent (ADR-653 D6's
"editing is chat", APP-BUILDER-UX §3.4). A bespoke PATCH would be a second
authoring face for a thing the substrate already versions and attributes —
and, worse, a door whose body could carry keys `write_revision` never sees.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{slug}")
async def get_member_app(slug: str, auth: UserClient) -> dict:
    """One member app's declaration, shaped for its surface (ADR-653 D3.c).

    404 when the app does not exist OR cannot render. `read_member_app`
    already refuses a declaration carrying a `problem`, which is the same
    posture the roster takes (`_resolve_member_app_surfaces` withholds it):
    a surface a member could foreground and we could not draw is the
    empty-window class ADR-653 §10.1 cost us, and it is refused at the source
    rather than rendered blank.

    ⚠️ WHAT IS SERVED, AND WHAT IS NOT. The agent's NAME reaches the client
    (band 2 says who is minding this work). Its CHARACTER does not: that is
    the turn's material, composed server-side into the lane frame, and a
    surface has no use for it. Nothing engine-, tool- or reach-shaped appears
    here at all — a declaration cannot carry one (`AGENT_KEYS`), so there is
    nothing that COULD leak.
    """
    from services.member_apps import read_member_app

    decl = read_member_app(auth.client, auth.user_id, slug)
    if decl is None:
        raise HTTPException(status_code=404, detail=f"Unknown app: {slug}")

    return {
        "slug": decl.slug,
        "name": decl.name,
        "about": decl.about,
        # Band 2 — who is minding this. The name only.
        "agent_name": decl.agent_name,
        "sections": decl.sections,
        # The member's own file, so the surface can point at what it renders
        # FROM (everything is files, and an app is no exception).
        "declaration_path": decl.declaration_path,
    }
