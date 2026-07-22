"""IMAGES routes — decomposed generation (ADR-475).

One endpoint, because IMAGES has exactly one act Studio's machinery does not
already cover:

    POST /api/images/compose — a brief becomes a LAYERED COMPOSITION on an
                               existing stage. The stage is created by the
                               shared `POST /api/studio/artifacts` (dimensions
                               and all); composing is a separate act ON it.

RENDER-TO-RASTER IS NOT HERE (removed 2026-07-22, ADR-475 §13). The server
render path — a headless browser rasterizing the composition to a PNG — never
ran in production: the Render container has no Chrome, so `/images/render` only
ever returned 503. Export is a CLIENT-SIDE fast-follow (the browser rasterizes
the stage it already displays); the composition stays the traceable source
regardless of who produces the flat file, so nothing about the moat depended on
a server rasterizer. The seam, the endpoint, and `render.py` are deleted rather
than left returning 503 — a broken feature removed beats a broken feature kept.

Everything else IMAGES does flows through existing machinery, exactly as the
Studio does: creation is the shared create endpoint (ADR-472 D2 registered the
stage with it), the bound lane mutates the stage, the FE reads it via
GET /api/workspace/file, and the powerbox gates every path.

WHY COMPOSE IS NOT A LANE TOOL: ADR-467 D4 ratified a UNIFORM lane surface —
every lane gets the same verbs, and per-agent reach is unrepresentable. A
`GenerateImage` verb only Designer-in-IMAGES could use would be that
settlement being re-opened. Composition is instead a SERVER-SIDE act the
member (or a lane, via the same HTTP surface) invokes, which is where ADR-472
D5 already put rendering. The lane still edits the result with the five verbs
it always had.

Canonical reference: docs/adr/ADR-475-decomposed-generation.md
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient, resolve_principal_id

# Module-level, NOT function-local. A resolver imported inside one handler is
# exactly the bug that took /studio/templates + /vocabulary down in prod on
# 2026-07-20 (a35d085's parent): every gate stayed green because the symbol was
# PRESENT in the source, and the endpoint still raised NameError at runtime.
# The gate for this module CALLS its handler for the same reason.
from services.images import STAGE_SLUG, stage_dimensions
from services.images.compose import compose_stage
from services.images.decompose import plan_layers

logger = logging.getLogger(__name__)

router = APIRouter()


class ComposeRequest(BaseModel):
    #: The stage to compose onto — an existing IMAGES artifact.
    path: str
    #: The member's one-line brief. This is the whole input; decomposition is
    #: what turns it into objects (ADR-468 D3).
    brief: str
    #: Optional engine override for the PLANNING call (not the raster engine).
    model: Optional[str] = None


@router.post("/images/compose")
async def compose(req: ComposeRequest, auth: UserClient) -> dict:
    """Decompose a brief into named layers and compose them onto a stage.

    The four steps (ADR-468 D3), run once: decompose → route by kind →
    generate per raster leaf → compose. Lands N+1 attributed revisions (one
    per generated leaf, one for the stage) — per-object provenance requires
    per-object revisions, which is the point.
    """
    from services.authored_substrate import write_revision
    from services.studio import STUDIO_ARTIFACT_REGION
    from services.workspace_context import substrate_scope_filter

    path = req.path if req.path.startswith("/") else f"/workspace/{req.path}"
    if ".." in path or not path.endswith(".html"):
        raise HTTPException(status_code=422, detail="Invalid stage path")
    if not path.startswith(STUDIO_ARTIFACT_REGION):
        raise HTTPException(
            status_code=403,
            detail=f"IMAGES stages live under {STUDIO_ARTIFACT_REGION} (ADR-440 D6).",
        )
    brief = (req.brief or "").strip()
    if not brief:
        raise HTTPException(status_code=422, detail="A brief is required to compose")

    rows = (
        auth.client.table("workspace_files")
        .select("path,content")
        .eq(*substrate_scope_filter(auth.user_id))
        .eq("path", path)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        raise HTTPException(status_code=404, detail=f"{path} does not exist")
    stage_html = rows[0].get("content") or ""

    # Composition is an IMAGES act. Refusing a document here is not pedantry:
    # the layers carry `block-staged` geometry, which is inert on a flow
    # layout — the objects would stack in document order and the member would
    # get a garbled document instead of an error (ADR-473's type→app rule made
    # the artifact's own declared type the authority, so this reads it).
    if f'data-template="{STAGE_SLUG}"' not in stage_html:
        raise HTTPException(
            status_code=422,
            detail="Composition targets an IMAGES stage — this artifact is not one.",
        )

    width, height = stage_dimensions(stage_html)
    layers = await plan_layers(brief, model=req.model)

    result = compose_stage(
        auth.client,
        user_id=auth.user_id,
        stage_path=path,
        layers=layers,
        width=width,
        height=height,
        # The member asked; the member is the author. The engine that produced
        # a leaf is recorded ON the leaf (`data-gen-model`), which is the
        # ADR-460 D2 split: the face is the member, the fact is on the object.
        authored_by="operator",
        stage_html=stage_html,
        # ADR-373/445: generation cost is attributed to the acting principal.
        principal_id=resolve_principal_id(auth),
    )

    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=path,
        content=result["html"],
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"IMAGES: compose '{brief[:100]}' ({result['layers']} layers)",
        summary=f"Composed {result['layers']} layers from a brief",
        # `derived_from` is LIFTED at the write door from the `data-ref`
        # citations this composition just wrote (ADR-448) — the stage's
        # reference edge to its own generated leaves is recorded without this
        # caller restating it.
    )
    logger.info(
        "[IMAGES] composed path=%s layers=%d generated=%d",
        path, result["layers"], result["generated"],
    )
    return {
        "success": True,
        "path": path,
        "layers": result["layers"],
        "generated": result["generated"],
        "assets": result["assets"],
    }
