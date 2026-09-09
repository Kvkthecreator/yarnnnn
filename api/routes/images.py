"""IMAGES routes — the raster derivation (ADR-475 §13).

ONE endpoint, because IMAGES has exactly one act Studio's machinery does not
already cover:

    POST /api/images/export  — the browser's raster of the stage, LANDED in the
                               workspace beside the artboard as a derivation of
                               it (ADR-475 §13's opt-in, built 2026-09-07).

COMPOSE IS DELETED (2026-09-08). `POST /api/images/compose` decomposed a brief
into layers server-side and had ZERO client callers for its whole life, while
its own decomposition module said the work belonged to an agent:

    `plan_layers` is JUDGMENT: the resident (Designer) reads the brief and
    decides what objects a good ad has. That is a real design act and belongs
    to an agent, not to a rule table.

It does. DRIVEN on the real lane before deleting (never argued): a blank stage
built exactly as the create door builds one, handed to Designer with a brief,
produced a correct composition through the ORDINARY uniform verbs — three
layers, every one placed (`data-x`/`data-y`) and depth-stamped (`data-z`), the
declared dark ground honoured, the scaffold gone. `WriteFile`, nothing bespoke.

That result also retires this module's old "WHY COMPOSE IS NOT A LANE TOOL"
argument, which reasoned that a Designer-only verb would re-open ADR-467 D4's
uniform lane surface. The premise was right and the conclusion inverted: the
lane needs NO new verb, so the uniform surface was never the obstacle — it was
the answer. Keeping both paths would have been the dual implementation.

RENDER-TO-RASTER IS NOT HERE (removed 2026-07-22, ADR-475 §13). The server
render path — a headless browser rasterizing the composition to a PNG — never
ran in production: the Render container has no Chrome, so `/images/render` only
ever returned 503. Rasterizing is CLIENT-SIDE (the browser rasterizes the stage
it already displays); the composition stays the traceable source regardless of
who produces the flat file, so nothing about the moat depended on a server
rasterizer.

`/images/export` does NOT reopen that: the server never rasterizes. It receives
bytes the member's browser produced and records them — the same act the deleted
server path performed after rendering, sourced from the client (§13 named
exactly this). Before it, the artboard's raster only ever left as a download,
so a markdown document could not refer to the picture at all — "make an image,
put it in a document" was unbuildable by construction (ADR-572 D17 cites by
workspace PATH, and there was no path).

Everything else IMAGES does flows through existing machinery, exactly as the
Studio does: creation is the shared create endpoint (ADR-472 D2 registered the
stage with it), the bound lane composes and mutates the stage, the FE reads it
via GET /api/workspace/file, and the powerbox gates every path.

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

logger = logging.getLogger(__name__)

router = APIRouter()


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
    # ADR-643 D2 — one question, and the door gains the principal half it never
    # had: an export is a WRITE beside the artboard, so a member whose grant
    # does not reach that folder must not land one there.
    from services.access import resolve_access

    _export = resolve_access(auth, target, "create")
    if not _export.allowed:
        raise HTTPException(status_code=403, detail=_export.reason)

    data = await file.read()
    if not data.startswith(_PNG_MAGIC):
        raise HTTPException(status_code=422, detail="The export must be a PNG.")
    if len(data) > _MAX_EXPORT_BYTES:
        raise HTTPException(status_code=413, detail="That export is too large.")

    leaf = artifact.rsplit("/", 1)[-1]
    # ⭐ The SERVICE client for the write, never the member's JWT: a binary
    # revision uploads to the PRIVATE `workspace-cas` bucket, and a member JWT
    # is refused there (the compose handler's leaves learned this in prod on
    # 2026-07-21 — 403 on every binary; `documents.upload` rides the service
    # client for the same reason). The first click-pass of this door 500'd on
    # exactly that, behind a CORS-less failure in the browser. The existence
    # read above stays on the member's client: THAT is the authorization.
    from services.supabase import get_service_client

    write_revision(
        get_service_client(),
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
