"""IMAGES routes — decomposed generation (ADR-475).

Two endpoints, because IMAGES has exactly two acts Studio's machinery does not
already cover:

    POST /api/images/compose — a brief becomes a LAYERED COMPOSITION on an
                               existing stage. The stage is created by the
                               shared `POST /api/studio/artifacts` (dimensions
                               and all); composing is a separate act ON it.
    POST /api/images/export  — the browser's raster of the stage, LANDED in the
                               workspace beside the artboard as a derivation of
                               it (ADR-475 §13's opt-in, built 2026-09-07).

RENDER-TO-RASTER IS NOT HERE (removed 2026-07-22, ADR-475 §13). The server
render path — a headless browser rasterizing the composition to a PNG — never
ran in production: the Render container has no Chrome, so `/images/render` only
ever returned 503. Rasterizing is CLIENT-SIDE (the browser rasterizes the stage
it already displays); the composition stays the traceable source regardless of
who produces the flat file, so nothing about the moat depended on a server
rasterizer. The seam, the endpoint, and `render.py` are deleted rather than left
returning 503 — a broken feature removed beats a broken feature kept.

`/images/export` does NOT reopen that: the server never rasterizes. It receives
bytes the member's browser produced and records them — the same act the deleted
server path performed after rendering, sourced from the client (§13 named
exactly this). Before it, the artboard's raster only ever left as a download,
so a markdown document could not refer to the picture at all — "make an image,
put it in a document" was unbuildable by construction (ADR-572 D17 cites by
workspace PATH, and there was no path).

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

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from services.authored_substrate import write_revision
from services.supabase import UserClient, resolve_principal_id
from services.workspace_paths import operator_can_organize

# Module-level, NOT function-local. A resolver imported inside one handler is
# exactly the bug that took /studio/templates + /vocabulary down in prod on
# 2026-07-20 (a35d085's parent): every gate stayed green because the symbol was
# PRESENT in the source, and the endpoint still raised NameError at runtime.
# The gate for this module CALLS its handler for the same reason.
from services.apps.images import STAGE_SLUG, stage_dimensions
from services.apps.images.compose import compose_stage
from services.apps.images.decompose import plan_layers

logger = logging.getLogger(__name__)

router = APIRouter()


class ComposeRequest(BaseModel):
    #: The stage to compose onto — an existing IMAGES artifact.
    path: str
    #: The member's one-line brief. This is the whole input; decomposition is
    #: what turns it into objects (ADR-468 D3).
    brief: str
    # ADR-556 D3 / ADR-557 D3 — the engine override is REMOVED, and the reason
    # is NOT that IMAGES is machinery. IMAGES is a user-facing APP (ADR-467
    # residency: Designer resides here), so its engine is a PRODUCT question —
    # it just is not answered by a raw model string on the wire. This field let
    # a client name any engine straight into `route_completion` with neither
    # the `LANE_MODELS` membership check nor the ADR-439 §4 billing gate that
    # every other routed path enforces, so an unpriced model priced silently at
    # the Sonnet default. An app's engine follows its RESIDENT (declared
    # server-side by the app's own `register_app`, ADR-562 —
    # `web/lib/apps/authoring.ts` is DELETED), resolved through
    # `agents_registry.resolve_agent`, never a caller-supplied id — the same
    # rule that made Designer exist instead of `models[0]`.
    # Whether a member may CHOOSE that resident is the open Phase-2 question.


@router.post("/images/compose")
async def compose(req: ComposeRequest, auth: UserClient) -> dict:
    """Decompose a brief into named layers and compose them onto a stage.

    The four steps (ADR-468 D3), run once: decompose → route by kind →
    generate per raster leaf → compose. Lands N+1 attributed revisions (one
    per generated leaf, one for the stage) — per-object provenance requires
    per-object revisions, which is the point.
    """
    from services.authored_substrate import write_revision
    from services.authoring import STUDIO_ARTIFACT_REGION
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

    # THE draw gate (ADR-445 §9 closed / ADR-491 Phase 3) — a compose is a
    # costed, member-attributed draw (planning call + per-image engine cost);
    # gate before any model work launches.
    from services.platform_limits import check_draw
    draw_ok, draw_reason, _draw_detail = check_draw(
        auth.client,
        auth.user_id,
        workspace_id=getattr(auth, "workspace_id", None),
        principal_id=getattr(auth, "principal_id", None) or auth.user_id,
    )
    if not draw_ok:
        raise HTTPException(
            status_code=402,
            detail=(
                "This workspace's balance is exhausted — top up to continue."
                if draw_reason == "balance_exhausted"
                else "You've reached your spend cap on this workspace — ask the owner to raise it."
            ),
        )

    rows = (
        auth.client.table("workspace_files")
        .select("path,content")
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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
    layers = await plan_layers(brief)

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


# =============================================================================
# ADR-475 §13 — the raster POST-back (built 2026-09-07)
# =============================================================================

#: A PNG is the only shape the browser's rasterizer produces; anything else is
#: a caller error, refused at the door rather than landed as a mislabelled blob.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
#: 2× pixel ratio on the largest stage is well under this; the cap exists so a
#: bad client cannot land arbitrary bytes at will.
_MAX_EXPORT_BYTES = 25 * 1024 * 1024


def export_path_for(artifact_path: str) -> str:
    """Where an artboard's raster lands: `{artboard folder}/exports/{stem}.png`.

    STABLE across re-exports on purpose. A second export is a new REVISION of
    the same file — attributed, parent-pointered, walkable — never a second
    file, so a document that cites the path (`![alt](…/exports/x.png)`) keeps
    resolving after the member re-exports. Beside the artboard, not under
    `inbound/`: this is a derivation of authored work, not an arrival.
    """
    abs_path = artifact_path if artifact_path.startswith("/workspace/") else f"/workspace/{artifact_path.lstrip('/')}"
    folder, _, leaf = abs_path.rpartition("/")
    stem = leaf.rsplit(".", 1)[0] or "export"
    return f"{folder}/exports/{stem}.png"


@router.post("/images/export")
async def export_png(
    auth: UserClient,
    file: UploadFile = File(...),
    path: str = Form(...),
) -> dict:
    """Land the browser's raster of an artboard IN the workspace (ADR-475 §13).

    The member's browser rasterized the stage it displays and POSTs the PNG
    here with the artboard's path. The bytes land through `write_revision`
    (ADR-209, the single write path) as `revision_kind="derivation"` with
    `derived_from=[the artboard]` — the same edge a lane's WriteFile carries, so
    `trace` walks from the flat picture back to the layered source, and the
    Files delete-warning knows the picture depends on the artboard.

    The server does not look at the pixels beyond the PNG magic: the
    composition is the attested source; the raster is a convenience artifact
    whose provenance is the edge, not its bytes (§13).
    """
    artifact = path.strip()
    if not artifact.startswith("/workspace/"):
        artifact = f"/workspace/{artifact.lstrip('/')}"
    if not artifact.endswith(".html") or ".." in artifact:
        raise HTTPException(status_code=422, detail="path must name an artboard (.html).")

    # The artboard must exist and be reachable by THIS caller — the RLS client
    # answers both in one read. A path the caller cannot see is "not found".
    rows = (
        auth.client.table("workspace_files")
        .select("path")
        .eq("user_id", auth.user_id)
        .eq("path", artifact)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="That artboard isn't here.")

    target = export_path_for(artifact)
    # The same organize gate every member-named destination passes (ADR-555):
    # a door that accepts what the substrate would refuse is the ADR-549 F1
    # defect. An artboard under a system root cannot land an export beside it.
    if not operator_can_organize(target):
        raise HTTPException(status_code=403, detail="You can't save an export here — that location is managed by the system.")

    data = await file.read()
    if not data.startswith(_PNG_MAGIC):
        raise HTTPException(status_code=422, detail="The export must be a PNG.")
    if len(data) > _MAX_EXPORT_BYTES:
        raise HTTPException(status_code=413, detail="That export is too large.")

    leaf = artifact.rsplit("/", 1)[-1]
    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=target,
        content_bytes=data,
        content_type="image/png",
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"Export PNG of {leaf}",
        lifecycle="active",
        revision_kind="derivation",
        derived_from=[artifact],
    )
    logger.info("[IMAGES] export landed %s from %s (%d bytes)", target, artifact, len(data))
    return {"success": True, "path": target[len("/workspace/"):], "derived_from": artifact}
