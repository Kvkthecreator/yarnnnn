"""Studio routes — ADR-440 (the first authoring app).

Two endpoints, both thin over the Studio's program constants
(``services/studio.py``):

- ``GET  /api/studio/templates``   — the template registry (slug/label/
                                     description; skeletons never cross the
                                     wire — creation is server-side).
- ``POST /api/studio/artifacts``   — create a new artifact from a template
                                     skeleton at a meaning-placed path.
                                     Refuses overwrite; region-gated to the
                                     member write region (ADR-440 D6 — the
                                     Studio owns no namespace, so the gate is
                                     a REGION, not a directory).

Everything else the Studio does flows through existing machinery: the bound
lane mutates the artifact (routes/lanes.py + lane_runner), the FE reads it
via GET /api/workspace/file, and the powerbox gates every path.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateArtifactRequest(BaseModel):
    path: str        # workspace-relative or absolute; must end in .html
    template: str    # a STUDIO_TEMPLATES slug


@router.get("/studio/templates")
async def list_templates(auth: UserClient) -> dict:
    from services.studio import STUDIO_TEMPLATES

    return {
        "templates": [
            {"slug": slug, "label": t["label"], "description": t["description"]}
            for slug, t in STUDIO_TEMPLATES.items()
        ]
    }


@router.post("/studio/artifacts")
async def create_artifact(req: CreateArtifactRequest, auth: UserClient) -> dict:
    from services.authored_substrate import write_revision
    from services.studio import STUDIO_ARTIFACT_REGION, STUDIO_TEMPLATES
    from services.workspace_context import substrate_scope_filter

    template = STUDIO_TEMPLATES.get(req.template)
    if not template:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown template: {req.template!r} (one of {sorted(STUDIO_TEMPLATES)})",
        )

    raw = (req.path or "").strip()
    if not raw:
        raise HTTPException(status_code=422, detail="path required")
    path = raw if raw.startswith("/") else f"/workspace/{raw}"
    if not path.endswith(".html"):
        raise HTTPException(status_code=422, detail="A Studio artifact is an .html file")
    if ".." in path:
        raise HTTPException(status_code=422, detail="Invalid path")
    if not path.startswith(STUDIO_ARTIFACT_REGION):
        raise HTTPException(
            status_code=403,
            detail=f"Studio artifacts live under {STUDIO_ARTIFACT_REGION} — "
                   "meaning-placed with the operation's work (ADR-440 D6).",
        )

    # Refuse overwrite — creation is creation (MoveFile-style guard).
    existing = (
        auth.client.table("workspace_files")
        .select("path")
        .eq(*substrate_scope_filter(auth.user_id))
        .eq("path", path)
        .limit(1)
        .execute()
    ).data or []
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"{path} already exists — open it in the Studio instead.",
        )

    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=path,
        content=template["skeleton"],
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"Studio: create from template '{req.template}' (ADR-440)",
        summary=f"New {template['label'].lower()} created in the Studio",
    )
    logger.info("[STUDIO] created artifact path=%s template=%s", path, req.template)
    return {"success": True, "path": path, "template": req.template}
