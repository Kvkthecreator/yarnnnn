"""IMAGES routes — decomposed generation + render-to-raster (ADR-475).

Two endpoints, because IMAGES has exactly two acts Studio's machinery does not
already cover — and they are the two halves of what makes it a different app:

    POST /api/images/compose — a brief becomes a LAYERED COMPOSITION on an
                               existing stage. The stage is created by the
                               shared `POST /api/studio/artifacts` (dimensions
                               and all); composing is a separate act ON it.
    POST /api/images/render  — the composition rasterizes to a PNG that lands
                               as an ATTRIBUTED DERIVATION of it (ADR-472 D4).
                               Studio's export LEAVES the system (print/PDF);
                               this one stays in it, traceable to the exact
                               revision that produced it.

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
from services.images.render import get_render_backend, inline_citations, raster_path

logger = logging.getLogger(__name__)

router = APIRouter()


class RenderRequest(BaseModel):
    #: The stage to rasterize. The composition is the source; the PNG that
    #: comes back is a derivation OF it (ADR-472 D4).
    path: str


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


@router.post("/images/render")
async def render(req: RenderRequest, auth: UserClient) -> dict:
    """Rasterize a stage; land the PNG as an attributed derivation of it.

    THE MOAT CLAIM, made structural. The raster is not an export that leaves
    the system — it is a revision IN it, carrying:

        revision_kind = "derivation"      (ADR-423 — a derived act)
        derived_from  = [the stage path]  (ADR-448 — the reference edge)

    so `trace` walks the PNG back to the composition, and the Files surface's
    "N files were made from this" warning knows the ad exists. No design tool
    can answer "which revision of which composition produced this image?"
    because in every one of them the export is a dead end.
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

    backend = get_render_backend()
    if not backend.available():
        # 503, not 500: the deployment cannot rasterize, which is a fact about
        # the host the member can act on — distinct from "your export failed".
        raise HTTPException(
            status_code=503,
            detail="No rendering engine is available on this deployment.",
        )

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
    if f'data-template="{STAGE_SLUG}"' not in stage_html:
        raise HTTPException(
            status_code=422,
            detail="Rendering targets an IMAGES stage — this artifact is not one.",
        )

    width, height = stage_dimensions(stage_html)
    # Citations become bytes for the renderer ONLY (the projection, never a
    # second source — ADR-456). Nothing here is written back to the stage.
    projected = inline_citations(auth.client, user_id=auth.user_id, html=stage_html)

    try:
        png = backend.render(projected, width=width, height=height)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[IMAGES] render failed for %s: %s", path, exc)
        raise HTTPException(status_code=502, detail=f"Rendering failed: {exc}") from exc

    out = raster_path(path)
    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=out,
        content_bytes=png,
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"IMAGES: render {width}x{height} from {path}",
        content_type="image/png",
        lifecycle="active",
        # The two fields that make this a derivation rather than a file that
        # happens to sit nearby. Passing `derived_from` explicitly is what
        # ADR-448 calls a DECLARED derive act — the edge is a fact about this
        # revision, recorded at the write door.
        revision_kind="derivation",
        derived_from=[path],
    )
    logger.info("[IMAGES] rendered path=%s -> %s (%dx%d, %dB)",
                path, out, width, height, len(png))
    return {
        "success": True,
        "path": out,
        "source": path,
        "width": width,
        "height": height,
        "bytes": len(png),
        "engine": backend.name,
    }
