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


@router.get("/studio/artifacts")
async def list_artifacts(auth: UserClient) -> dict:
    """Recent Studio-openable artifacts — .html files in the artifact region,
    newest first. The start state renders these as a clickable list (a member
    should never have to type a path to reopen their own work)."""
    from services.studio import STUDIO_ARTIFACT_REGION
    from services.workspace_context import substrate_scope_filter

    rows = (
        auth.client.table("workspace_files")
        .select("path, updated_at, summary")
        .eq(*substrate_scope_filter(auth.user_id))
        .like("path", f"{STUDIO_ARTIFACT_REGION}%")
        .like("path", "%.html")
        .order("updated_at", desc=True)
        .limit(20)
        .execute()
    ).data or []
    return {
        "artifacts": [
            {"path": r["path"], "updated_at": r.get("updated_at"), "summary": r.get("summary")}
            for r in rows
        ]
    }


@router.get("/studio/vocabulary")
async def get_vocabulary(auth: UserClient) -> dict:
    """The block + layout + arrangement + TOKEN registries (ADR-443 R4/D5 +
    ADR-447 + ADR-453) — the ONE kernel-seeded grammar, served so the FE
    palette, the New/Re-arrange galleries, and the Design tab render (and
    EXECUTE) from the same source the posture teaches from. `fragment` is the
    deterministic insertion payload — the FE stamps a fresh data-block-id and
    writes. `grain`/`slots` carry the arrangement's composition shape (the FE
    derives a wireframe thumbnail from them — ADR-447 D7.1; slot `role` gates
    what can land in a slot — ADR-453 D5). `tokens` + `kernel_style_element`
    carry the property layer (the FE upserts the marked element on token ops —
    the ADR-453 D2 retrofit). `design_systems` is ADR-449 discovery (the
    Design tab's document scope). Grammar, not schema."""
    from services.design_systems import find_design_systems
    from services.studio import (
        MEDIA_BLOCK_KINDS,
        STUDIO_ARRANGEMENTS,
        STUDIO_BLOCKS,
        STUDIO_KERNEL_CSS_VERSION,
        STUDIO_LAYOUTS,
        STUDIO_TOKENS,
        compose_kernel_style_element,
    )

    return {
        "tokens": [
            {
                "key": k,
                "label": t["label"],
                "applies": t["applies"],
                "values": t["values"],
                "description": t["description"],
            }
            for k, t in STUDIO_TOKENS.items()
        ],
        "media_kinds": sorted(MEDIA_BLOCK_KINDS),
        "kernel_css_version": STUDIO_KERNEL_CSS_VERSION,
        "kernel_style_element": compose_kernel_style_element(),
        "design_systems": find_design_systems(auth.client, auth.user_id),
        "blocks": [
            {
                "kind": k,
                "label": b["label"],
                "description": b["description"],
                "group": b["group"],
                "fragment": b["markup"],
            }
            for k, b in STUDIO_BLOCKS.items()
        ],
        "layouts": [
            {"slug": s, "label": l["label"], "description": l["description"]}
            for s, l in STUDIO_LAYOUTS.items()
        ],
        "arrangements": {
            layout: [
                {
                    "slug": s,
                    "label": a["label"],
                    "description": a["description"],
                    "grain": a["grain"],
                    "slots": a["slots"],
                    "fragment": a["fragment"],
                }
                for s, a in arrangements.items()
            ]
            for layout, arrangements in STUDIO_ARRANGEMENTS.items()
        },
    }


@router.get("/studio/design-systems/resolve")
async def resolve_design_system_route(manifest: str, auth: UserClient) -> dict:
    """Resolve one design system to its composed, MARKED skin element
    (ADR-449 D2 via ADR-453 D4 — the Design tab's Apply). The FE lands it
    through the one mechanical write door (`applySkin`, the FE mirror of
    `apply_skin_to_html`); this endpoint only composes — it never writes."""
    from services.design_systems import compose_skin_element, resolve_design_system

    ds = resolve_design_system(auth.client, auth.user_id, manifest)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Not a design system: {manifest}")
    return {
        "name": ds["name"],
        "manifest_path": ds["manifest_path"],
        "skin_element": compose_skin_element(ds["manifest_path"], ds["css_text"]),
    }


class WriteArtifactRequest(BaseModel):
    path: str
    content: str
    expected_head_version_id: Optional[str] = None
    message: Optional[str] = None


@router.post("/studio/artifacts/write")
async def write_artifact(req: WriteArtifactRequest, auth: UserClient) -> dict:
    """The Studio's MECHANICAL write door (ADR-444) — deterministic,
    member-executed structural operations (insert a block, add a slide, apply
    a slide layout) computed in the FE and landed as ONE operator-attributed
    revision. CAS-guarded (ADR-406): a stale base 409s with the intervening
    attribution instead of silently clobbering a lane write."""
    from services.authored_substrate import StaleWriteError, write_revision
    from services.studio import STUDIO_ARTIFACT_REGION

    raw = (req.path or "").strip()
    path = raw if raw.startswith("/") else f"/workspace/{raw}"
    if not path.endswith(".html") or ".." in path or not path.startswith(STUDIO_ARTIFACT_REGION):
        raise HTTPException(status_code=403, detail=f"Not a Studio artifact path: {path}")
    if not (req.content or "").strip():
        raise HTTPException(status_code=422, detail="content required")

    write_kwargs: dict = {}
    if req.expected_head_version_id is not None:
        write_kwargs["expected_parent_version_id"] = req.expected_head_version_id
    try:
        new_head_version_id = write_revision(
            auth.client,
            user_id=auth.user_id,
            path=path,
            content=req.content,
            authored_by="operator",
            author_identity_uuid=auth.user_id,
            message=req.message or "Studio: structural edit",
            summary=req.message or "Structural edit in the Studio",
            **write_kwargs,
        )
    except StaleWriteError as e:
        raise HTTPException(
            status_code=409,
            detail=f"The artifact changed under you (expected {e.expected_parent_version_id or '<none>'}) — it will reload.",
        )
    # Return the new head version so the FE can advance its CAS base WITHOUT a
    # refetch — the invisible-save path: a member's own text edit lands silently
    # (the canvas already shows the typed result), no iframe reload, no caret
    # jump. The next write CAS-chains off this id.
    return {"success": True, "path": path, "head_version_id": new_head_version_id}


@router.get("/studio/citable")
async def list_citable(auth: UserClient) -> dict:
    """Citable workspace objects for the insert menu (ADR-440 v1.1) —
    images + tables the member can reference into an artifact. Workspace-wide
    (citations reach anywhere the member may read; the powerbox gates reads
    downstream), newest first."""
    from services.workspace_context import substrate_scope_filter

    def _q():
        return (
            auth.client.table("workspace_files")
            .select("path, updated_at")
            .eq(*substrate_scope_filter(auth.user_id))
            .order("updated_at", desc=True)
            .limit(24)
        )

    images = (
        _q()
        .or_(
            "path.ilike.%.png,path.ilike.%.jpg,path.ilike.%.jpeg,"
            "path.ilike.%.gif,path.ilike.%.webp,path.ilike.%.svg"
        )
        .execute()
    ).data or []
    tables = (_q().ilike("path", "%.csv").execute()).data or []
    return {
        "images": [{"path": r["path"], "updated_at": r.get("updated_at")} for r in images],
        "tables": [{"path": r["path"], "updated_at": r.get("updated_at")} for r in tables],
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
