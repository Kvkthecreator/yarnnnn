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
import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional

from services.supabase import UserClient

# ADR-472 D1/D2: importing the IMAGES app REGISTERS its stage with the shared
# layout registry (services/studio.py::register_layouts). Without this import
# the registry holds only Studio's layouts and an IMAGES stage silently 404s at
# creation — the module IS the registration, so the import is load-bearing and
# must not be pruned as "unused".
import services.images  # noqa: F401  (import for registration side-effect)

# The cross-app layout resolver (ADR-472 D2). Module-level: the endpoints below
# use these at request time, so a function-local import in ONE handler would
# leave the others with a NameError — which is exactly what shipped and broke
# /studio/templates + /studio/vocabulary in prod (2026-07-20).
from services.studio import all_layouts, all_templates, resolve_layout

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateArtifactRequest(BaseModel):
    template: str        # a STUDIO_TEMPLATES slug
    # BOTH optional (ADR-470) — the two doors into creation:
    #   • IMMEDIATE — neither given. The artifact is born "Untitled ‹kind›" at a
    #     server-placed, disambiguated key. New hands over the workbench and the
    #     name arrives from the work (the crumb arms, offering — never demanding).
    #   • DELIBERATE — both given. The member who arrives knowing ("IR deck v3,
    #     in clients/") names it and picks a destination up front.
    # `name` is what the member TYPED (ADR-469): it becomes the <title>
    # verbatim. `path` carries only the slugified KEY.
    path: Optional[str] = None
    name: Optional[str] = None
    # ADR-472 D3 — DIMENSIONS-FIRST creation, for apps whose artifact is a
    # raster (IMAGES). A stage is born at a SIZE the way a Canva design is:
    # either a named preset ("square", "story", "ad") or an explicit W×H. Both
    # absent on a stage → the default preset; ignored entirely by flow/paged
    # document layouts, which have no fixed pixel box.
    preset: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


@router.get("/studio/templates")
async def list_templates(auth: UserClient) -> dict:
    _templates = all_templates()

    return {
        "templates": [
            {"slug": slug, "label": t["label"], "description": t["description"]}
            for slug, t in _templates.items()
        ]
    }


@router.get("/studio/artifacts")
async def list_artifacts(auth: UserClient) -> dict:
    """Recent Studio-openable artifacts — .html files in the artifact region,
    newest first. The start state renders these as a clickable list (a member
    should never have to type a path to reopen their own work).

    ADR-459: each row carries `name` + `kind` so the landing (a COMPOSITION —
    ADR-340 DP29) can read like a Mac rather than a workbench. Both are
    computed, never stored:

    - `kind` is LIFTED from the artifact's own ``data-template`` root attr
      (ADR-443 R2 — the layout IS the file). Content stays the sole source
      (ADR-456 D1); a layout switch is an attributed revision and the kind
      follows for free. Survives rename — the kind was never in the name.
    - `name` is the titleized meaning-folder the member already typed
      (`operation/ir-deck-v3/deck.html` → "IR deck v3"). DP33: the namespace
      carries meaning, so there is nothing to store.

    The Files surface (the MIRROR) is untouched and still shows the raw leaf.
    """
    from services.studio import (
        STUDIO_ARTIFACT_REGION,
        artifact_kind,
        artifact_name,
    )
    from services.workspace_context import substrate_scope_filter

    rows = (
        auth.client.table("workspace_files")
        .select("path, updated_at, summary, content")
        .eq(*substrate_scope_filter(auth.user_id))
        .like("path", f"{STUDIO_ARTIFACT_REGION}%")
        .like("path", "%.html")
        # A trashed artifact leaves Recents. `lifecycle` is NULL on rows written
        # before the column had a default, so `.neq` alone would drop them —
        # match the Files tree's own predicate (routes/workspace.py:587).
        # Load-bearing since ADR-470 D5: untitled artifacts are `active` and
        # Trash is their ONLY cleanup, so without this a member who trashes
        # three abandoned "Untitled document"s still sees all three here.
        .or_("lifecycle.is.null,lifecycle.neq.archived")
        .order("updated_at", desc=True)
        .limit(20)
        .execute()
    ).data or []
    return {
        "artifacts": [
            {
                "path": r["path"],
                "updated_at": r.get("updated_at"),
                "summary": r.get("summary"),
                # Both facts are LIFTED from the same content the row already
                # carries (ADR-469 / ADR-459 D1) — no extra read, no storage.
                "name": artifact_name(r["path"], r.get("content")),
                **artifact_kind(r.get("content")),
            }
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
        STUDIO_MEASURES,
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
        # ADR-461 D4 — the measures: a property whose MECHANISM is enumerable
        # but whose VALUE is not. Served with its BOUND so the FE clamps from
        # the kernel's declaration rather than a hardcoded guess (the kernel
        # names the bound; nothing downstream invents one).
        "measures": [
            {
                "key": k,
                "label": m["label"],
                "applies": m["applies"],
                "unit": m["unit"],
                "min": m["min"],
                "max": m["max"],
                "css_var": m["css_var"],
                "description": m["description"],
            }
            for k, m in STUDIO_MEASURES.items()
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
            {
                "slug": s,
                "label": l["label"],
                "description": l["description"],
                # The composition seam (see STUDIO_LAYOUT_MODES). The chrome
                # derives from it: `paged` gets the New-‹noun› gallery + the
                # navigator strip; `flow` gets neither — insert is located at
                # the pointer. Served so the kernel names the category once and
                # the FE never hardcodes a layout slug.
                "mode": l["mode"],
            }
            for s, l in all_layouts().items()
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
        # DESIGN-SYSTEMS.md §6 — the manage panel reads these (already computed
        # by resolve; additive, so Apply which only wants skin_element is
        # unaffected): the flattened sources (the files), the synonym bridge,
        # and any warnings (an external font URL the picker must surface).
        "sources": ds.get("sources", []),
        "maps": ds.get("maps", {}),
        "warnings": ds.get("warnings", []),
    }


@router.post("/studio/design-systems/import")
async def import_design_system_route(
    auth: UserClient,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
) -> dict:
    """Import a design-system export (.zip) → a conforming meaning-folder.

    The door for the mechanism ADR-449 D1 assumed and never built. A ZIP
    because that is what a design system IS on the way over — every export
    (Claude Design, Figma, a repo's tokens/) ships a folder, and a folder
    reaches a browser as an archive. The member picks one file; the flatten,
    the manifest, and the binary lane are the server's job.

    Returns the receipt, warnings included: what landed, what was skipped as
    vendor material, and anything the flatten could not resolve. A warning is
    the product here — an import that half-lands silently is the failure this
    whole arc exists to prevent.
    """
    import io
    import zipfile

    from services.design_system_import import import_design_system

    raw = await file.read()
    if len(raw) > _MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"That archive is larger than {_MAX_IMPORT_BYTES // 1_000_000}MB.",
        )
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="That file is not a .zip — export the design-system folder as an archive.",
        )

    files: dict = {}
    for info in zf.infolist():
        if info.is_dir() or info.file_size > _MAX_MEMBER_FILE_BYTES:
            continue
        rel = info.filename
        # A real export zips the FOLDER, so every path carries its name as a
        # prefix ("YARNNN Design System/tokens/colors.css"). Strip one leading
        # segment when every entry shares it — otherwise the manifest's
        # folder-relative `css:` paths would never resolve.
        files[rel] = zf.read(info)
    files = _strip_common_root(files)
    if not files:
        raise HTTPException(status_code=400, detail="That archive is empty.")

    # The name a member recognises, best evidence first: what they typed, then
    # the archive's own wrapper folder, then the FILE they picked. The live
    # YARNNN export zips its contents at the ROOT (no wrapper), so root_name is
    # None and the filename is the only thing left carrying "YARNNN Design
    # System" — without it every import would be called "Design system".
    display = (
        (name or "").strip()
        or _zip_root_name(raw)
        or re.sub(r"\.zip$", "", (file.filename or ""), flags=re.I).strip()
        or "Design system"
    )
    folder = f"/workspace/design-system/{_slugify(display)}"
    result = import_design_system(
        auth.client, user_id=auth.user_id, folder=folder,
        display_name=display, files=files,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Import failed."))
    return result


#: A design-system archive is tokens + a few assets. The live YARNNN export is
#: 2MB with a 508KB vendor bundle inside it; 25MB is the bucket's own file
#: ceiling and a generous roof for a folder of CSS.
_MAX_IMPORT_BYTES = 25_000_000
_MAX_MEMBER_FILE_BYTES = 10_000_000


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "design-system"


def _zip_root_name(raw: bytes) -> Optional[str]:
    """The archive's own folder name — the display name a member recognises."""
    import io
    import zipfile

    try:
        names = [n for n in zipfile.ZipFile(io.BytesIO(raw)).namelist() if not n.startswith("__")]
    except Exception:  # noqa: BLE001
        return None
    roots = {n.split("/")[0] for n in names if "/" in n}
    return roots.pop() if len(roots) == 1 else None


def _strip_common_root(files: dict) -> dict:
    """Drop the shared top folder every zipped export carries.

    Without this, `styles.css` lands at `<folder>/YARNNN Design System/
    styles.css` while the manifest says `css: [styles.css]` — the resolve
    would find nothing and the picker would offer a skin that styles nothing.
    """
    real = {k: v for k, v in files.items() if not k.startswith("__MACOSX/")}
    if not real:
        return {}
    roots = {k.split("/")[0] for k in real if "/" in k}
    if len(roots) != 1 or any("/" not in k for k in real):
        return real
    root = roots.pop() + "/"
    return {k[len(root):]: v for k, v in real.items() if k != root}


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


class RenameArtifactRequest(BaseModel):
    path: str  # the artifact's CURRENT path
    name: str  # the new operator-facing NAME (free text; slugified here)


@router.post("/studio/artifacts/rename")
async def rename_artifact(req: RenameArtifactRequest, auth: UserClient) -> dict:
    """Rename an artifact by its NAME — which is its MEANING FOLDER.

    `operation/prd-for-yarnnn/document.html` is named "Prd for yarnnn". The leaf
    is a TYPE marker (document/deck/article/page.html) that names the layout, so
    the generic file-rename was renaming the type, not the artifact — you could
    rename `document.html` to `report.html` and the artifact's name would not
    move at all (ADR-459's `artifact_name` reads the folder).

    So renaming means moving the folder: every file under it, one MoveFile each
    (assets, data, the artifact), then a retitle so the h1 follows. One member
    act; the substrate sees N attributed moves + at most one retitle revision.

    Not atomic — MoveFile is per-path and there is no multi-path transaction.
    A partial failure stops and reports what moved, rather than pretending. In
    practice an artifact folder holds one file (verified against the live
    workspace), so N is 1 and the window is theoretical; the loop exists so a
    folder that grows assets doesn't silently half-rename.
    """
    from services.naming import disambiguate, path_slug
    from services.studio import STUDIO_ARTIFACT_REGION
    from services.workspace_context import substrate_scope_filter

    raw = (req.path or "").strip()
    path = raw if raw.startswith("/") else f"/workspace/{raw}"
    if not path.endswith(".html") or ".." in path or not path.startswith(STUDIO_ARTIFACT_REGION):
        raise HTTPException(status_code=403, detail=f"Not a Studio artifact path: {path}")

    # The name → a folder slug, the artifact's KEY. `path_slug` is the single
    # implementation (services/naming.py) both entrances share — create and
    # rename can never disagree about what a name becomes.
    #
    # The slug no longer has to CARRY the name (ADR-469): the typed name goes
    # into the artifact's <title> below, verbatim. That's what lets a name with
    # no Latin characters be accepted here instead of 422'd — it slugs to a
    # disambiguated `untitled-*` key while reading back exactly as typed.
    typed = (req.name or "").strip()
    if not typed:
        raise HTTPException(status_code=422, detail="A name is required.")
    slug = path_slug(typed)

    parts = [p for p in path.split("/") if p]
    region_tail = [p for p in STUDIO_ARTIFACT_REGION.split("/") if p]
    parent = parts[-2] if len(parts) >= 2 else None
    if not parent or parent in region_tail:
        raise HTTPException(
            status_code=422,
            detail="This artifact has no meaning folder to rename — move it into one first.",
        )
    if parent == slug:
        # Same KEY — but the typed name may still differ in case or script
        # (`ir deck` → `IR deck`, or any edit to a name that slugs to the same
        # ASCII). The folder doesn't move; the title still must (ADR-469).
        retitled_only = _retitle_to(auth, path, typed).get("retitled", False)
        return {
            "success": True,
            "path": path,
            "renamed": False,
            "reason": "same_folder",
            "name": typed,
            "retitled": retitled_only,
        }

    old_folder = "/" + "/".join(parts[:-1])
    region_prefix = "/" + "/".join(parts[:-2])

    # The key must be unique. A DISTINCT typed name landing on an occupied key
    # is disambiguated (`untitled`, `untitled-2`) rather than refused — under
    # ADR-469 the key no longer carries the name, so two artifacts sharing a
    # key is a naming-collision of no consequence to the member: each still
    # reads back as what they typed. Pre-468 this 409'd, which made a Korean
    # workspace unable to name a second document at all.
    siblings = (
        auth.client.table("workspace_files")
        .select("path")
        .eq(*substrate_scope_filter(auth.user_id))
        .like("path", f"{region_prefix}/%")
        .execute()
    ).data or []
    # The sibling's meaning folder = the first segment after the region prefix.
    # Derived from the prefix, not from an index into a leading-slash split.
    taken = {
        rest.split("/")[0]
        for rest in (
            r["path"][len(region_prefix) + 1 :]
            for r in siblings
            if r["path"].startswith(f"{region_prefix}/")
        )
        if rest and "/" in rest
    } - {parent}
    slug = disambiguate(slug, taken)
    new_folder = f"{region_prefix}/{slug}"

    rows = (
        auth.client.table("workspace_files")
        .select("path")
        .eq(*substrate_scope_filter(auth.user_id))
        .like("path", f"{old_folder}/%")
        .execute()
    ).data or []
    if not rows:
        raise HTTPException(status_code=404, detail=f"No artifact at {path}")

    from services.primitives.registry import execute_primitive

    moved: list[str] = []
    new_path = path
    for row in sorted(r["path"] for r in rows):
        dst = new_folder + row[len(old_folder):]
        result = await execute_primitive(
            auth, "MoveFile", {"path": row, "new_path": dst, "scope": "workspace"}
        )
        if not (isinstance(result, dict) and result.get("success")):
            detail = (result or {}).get("message", "Rename failed")
            raise HTTPException(
                status_code=400,
                detail=(f"{detail} — {len(moved)} of {len(rows)} files moved."
                        if moved else detail),
            )
        moved.append(dst)
        if row == path:
            new_path = dst

    logger.info("[STUDIO] renamed folder %s -> %s (%d files)", old_folder, new_folder, len(moved))

    # The retitle so the h1 follows (the docstring's promise, the FE's
    # expectation at commitRename's "the retitle is a server-side write"). One
    # member act moves BOTH names. A no-op on paged layouts / authored titles —
    # and best-effort: a retitle failure must not undo a successful rename.
    retitled = False
    try:
        # The TYPED name, verbatim — not a reconstruction from the new folder
        # (ADR-469). This is the whole point: `한글 문서` reaches the title
        # intact while the folder key is a disambiguated `untitled-N`.
        retitled = _retitle_to(auth, new_path, typed).get("retitled", False)
    except Exception:
        logger.warning("[STUDIO] rename succeeded but retitle failed for %s", new_path)

    return {
        "success": True,
        "path": new_path,
        "renamed": True,
        "moved": len(moved),
        "name": typed,
        "retitled": retitled,
    }


class RetitleArtifactRequest(BaseModel):
    path: str  # the artifact's CURRENT path; its stem becomes the title


def _retitle_to(auth: UserClient, path: str, title: str | None = None) -> dict:
    """Retitle an artifact — the shared body behind BOTH the explicit /retitle
    endpoint AND the rename endpoint (which folds it in so a rename is one
    member act that moves both names together).

    `title` is what the member TYPED (ADR-469). Pass it and it is written
    verbatim — casing and script survive, because the title is now the name's
    authoritative home rather than a reconstruction of it. Omit it (the bare
    /retitle endpoint, which has only a path) and it falls back to
    `artifact_name`, which lifts the existing title or degrades to the folder.

    Renamed from `_retitle_to_match_filename` (2026-07-20): the old name
    described the old direction of travel. The filename no longer dictates the
    title — under ADR-469 the causality runs the other way, from the typed name
    into BOTH the title (verbatim) and the folder key (slugified).

    The rename half of "the name is one fact" (2026-07-15): a rename used to
    move the file and leave the artifact's own <h1> saying the old thing — two
    names for one thing, only the filename real. This is Studio's opinion (an
    h1 IS a title), so it lives here with the layout registry, deliberately NOT
    in the generic move endpoint that every surface shares.

    No-ops (retitled=False) when nothing should change — a paged layout (its h1
    is a thesis, not a title), an already-authored title, or a byte-identical
    result. A no-op writes NO revision. Returns a result dict; raises only on a
    genuinely missing artifact.
    """
    from services.authored_substrate import write_revision
    from services.studio import STUDIO_LAYOUTS, artifact_name, set_artifact_title
    from services.workspace_context import substrate_scope_filter

    row = (
        auth.client.table("workspace_files")
        .select("content")
        .eq(*substrate_scope_filter(auth.user_id))
        .eq("path", path)
        .limit(1)
        .execute()
    ).data
    if not row:
        raise HTTPException(status_code=404, detail=f"No artifact at {path}")
    content = row[0].get("content") or ""

    template = re.search(r'data-template="([^"]+)"', content)
    layout = resolve_layout(template.group(1)) if template else None
    is_flow = bool(layout and layout["mode"] == "flow")

    # The typed name wins; without one, fall back to the artifact's own name.
    name = (title or "").strip() or artifact_name(path, content)

    # `set_h1` is the ADR-459-era guard, unchanged: a deck's h1 is its thesis
    # and a page's is its headline, so only a flow layout's h1 is a title.
    #
    # But <title> is written for EVERY layout — it is metadata, never authored
    # (set_artifact_title's own contract), and under ADR-469 it is where the
    # name LIVES. The old code returned early on a paged layout and so never
    # wrote it; a renamed deck kept its old <title> and the landing card
    # silently reverted to the folder slug. Guarding the h1 is right; guarding
    # the title was the bug.
    updated = set_artifact_title(content, name, set_h1=is_flow)
    if updated == content:
        # Already titled, or the member has authored their own title (the
        # placeholder guard in set_artifact_title) — their words win.
        return {"success": True, "retitled": False, "reason": "no_change"}

    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=path,
        content=updated,
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"Studio: name → '{name}'",
        summary=f"Named '{name}'",
    )
    return {"success": True, "retitled": True}


@router.post("/studio/artifacts/retitle")
async def retitle_artifact(req: RetitleArtifactRequest, auth: UserClient) -> dict:
    """Retitle an artifact from its own name (explicit endpoint; the shared body
    is `_retitle_to`). Carries no typed name, so the helper falls back to
    `artifact_name`. See that helper for the full contract."""
    from services.studio import STUDIO_ARTIFACT_REGION

    raw = (req.path or "").strip()
    path = raw if raw.startswith("/") else f"/workspace/{raw}"
    if not path.endswith(".html") or ".." in path or not path.startswith(STUDIO_ARTIFACT_REGION):
        raise HTTPException(status_code=403, detail=f"Not a Studio artifact path: {path}")
    return _retitle_to(auth, path)


@router.get("/studio/citable")
async def list_citable(auth: UserClient) -> dict:
    """Citable workspace objects for the insert menu (ADR-440 v1.1) —
    images + tables the member can reference into an artifact. Workspace-wide
    (citations reach anywhere the member may read; the powerbox gates reads
    downstream), newest first.

    Carries `head_version_id` so a citation can be PINNED at the moment it is
    made (ADR-440 D5). The pin was delegated to the lane ("stamp it when you
    have the head revision id... otherwise leave it empty") and consequently
    never got written — 0 populated pins across the live workspace, because a
    mechanical insert never had the rev to stamp. Serving it here makes the
    deterministic path the default and the lane's judgment the exception.
    """
    from services.workspace_context import substrate_scope_filter

    def _q():
        return (
            auth.client.table("workspace_files")
            .select("path, updated_at, head_version_id")
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

    def _row(r: dict) -> dict:
        return {
            "path": r["path"],
            "updated_at": r.get("updated_at"),
            # The pin. May be None for a file predating ADR-209's chain — the
            # citation still works (the pin is a fallback for a moved/deleted
            # path, never the happy-path resolver), it just can't be pinned.
            "head_version_id": r.get("head_version_id"),
        }

    return {
        "images": [_row(r) for r in images],
        "tables": [_row(r) for r in tables],
    }


def _untitled_path(auth: UserClient, template: str) -> str:
    """Where an UNNAMED artifact lands (ADR-470) — the immediate door.

    `untitled-document/document.html`, then `untitled-document-2/…`. The key
    is built from the same `path_slug` + `disambiguate` the named door uses
    (ADR-469), against the artifact region's existing meaning folders — one key
    rule, so the two doors cannot drift into different collision behaviour.

    It lands in the ORDINARY region, not a `drafts/` namespace: an untitled
    artifact is real work that hasn't been named yet, not a separate class of
    thing. DP33 — the state is data (the placeholder title it carries), the
    namespace stays meaning. Naming it later is a retitle, and moving it is the
    member's Move verb; neither is forced by where it was born.
    """
    from services.naming import disambiguate, path_slug
    from services.studio import STUDIO_ARTIFACT_REGION, STUDIO_LAYOUTS
    from services.workspace_context import substrate_scope_filter

    lay = resolve_layout(template)
    label = lay["label"].lower() if lay else template
    base = path_slug(f"untitled {label}")

    rows = (
        auth.client.table("workspace_files")
        .select("path")
        .eq(*substrate_scope_filter(auth.user_id))
        .like("path", f"{STUDIO_ARTIFACT_REGION}%")
        .execute()
    ).data or []
    # STUDIO_ARTIFACT_REGION already carries its trailing slash — never append
    # one (that yielded `/workspace/operation//untitled-document/…`).
    prefix = STUDIO_ARTIFACT_REGION
    taken = {
        rest.split("/")[0]
        for rest in (r["path"][len(prefix):] for r in rows if r["path"].startswith(prefix))
        if rest and "/" in rest
    }
    return f"{prefix}{disambiguate(base, taken)}/{template}.html"


@router.post("/studio/artifacts")
async def create_artifact(req: CreateArtifactRequest, auth: UserClient) -> dict:
    from services.authored_substrate import write_revision
    from services.studio import STUDIO_ARTIFACT_REGION
    from services.workspace_context import substrate_scope_filter

    _templates = all_templates()
    template = _templates.get(req.template)
    if not template:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown template: {req.template!r} (one of {sorted(_templates)})",
        )

    # ── Placement (ADR-470) ────────────────────────────────────────────────
    # No path = the IMMEDIATE door: the server places it. One authority for
    # where an unnamed artifact lands — the FE never invents a scratch path,
    # so there is no second placement rule to drift.
    raw = (req.path or "").strip()
    if not raw:
        raw = _untitled_path(auth, req.template)
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

    # The name is ONE fact (2026-07-15): what the member typed names the FILE
    # and titles the ARTIFACT. Creation used to name only the file and leave the
    # h1 at "Untitled document", so the artifact said one thing and the
    # substrate another — two names for one thing, only one of them real.
    #
    # ADR-469 fixes WHICH form of the name reaches the title. It used to be
    # reconstructed from the path (`artifact_name(path)`), which round-trips
    # through a lossy slug: `IR deck v3` came back `Ir deck v3`, and a name with
    # no Latin characters came back `Untitled`. The typed name now goes in
    # verbatim, and the path is left to be a mere key.
    #
    # Only a `flow` layout's h1 IS the title — a deck's h1 is the title slide's
    # thesis, a page's is its headline, and a filename has no business
    # dictating those (see set_artifact_title's guards). <title> is always set.
    from services.studio import STUDIO_LAYOUTS, set_artifact_title

    # `.get`, not a bare subscript: creation validates `req.template` against
    # STUDIO_TEMPLATES (which is derived 1:1 from STUDIO_LAYOUTS today), but a
    # future bundle-shipped template could live in one and not the other — a
    # bare `STUDIO_LAYOUTS[req.template]` would then 500. An unknown layout is
    # not flow (its h1 stays authored), matching artifact_kind's own fallback.
    _layout = resolve_layout(req.template)
    is_flow = bool(_layout and _layout["mode"] == "flow")

    # ADR-470: no name → the SKELETON'S OWN placeholder stands ("Untitled
    # document"), which every layout already ships and `_SCAFFOLD_TITLES`
    # already recognises as untouched. Deriving one from the path instead would
    # be the interrogation by proxy — the member didn't name it, so nothing may
    # invent a name on their behalf and then pretend they authored it. Leaving
    # the placeholder is what keeps the later crumb-rename an OFFER: the
    # placeholder guard in set_artifact_title lets a real name replace it,
    # where an invented one would look authored and be protected from replacement.
    name = (req.name or "").strip()
    content = (
        set_artifact_title(template["skeleton"], name, set_h1=is_flow)
        if name
        else template["skeleton"]
    )

    # ADR-472 D3: a stage carries its real dimensions on the root, as data.
    # `data-w`/`data-h` are the MARKERS (the same attribute/property split the
    # measures use); the FE maps them to --stage-w/--stage-h, and the renderer
    # (D4/D5) rasterizes at exactly this size. Only IMAGES stages take this
    # branch — a document has no pixel box, and asking one for dimensions would
    # be the aspect-token mistake in a new costume.
    from services.images import STAGE_SLUG, resolve_dimensions, stage_root_attrs

    if req.template == STAGE_SLUG:
        w, h = resolve_dimensions(
            preset_slug=req.preset, width=req.width, height=req.height
        )
        content = content.replace(
            f'<html data-template="{STAGE_SLUG}">',
            f'<html data-template="{STAGE_SLUG}" {stage_root_attrs(w, h)}>',
            1,
        )

    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=path,
        content=content,
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"Studio: create from template '{req.template}' (ADR-440)",
        summary=f"New {template['label'].lower()} created in the Studio",
    )
    logger.info("[STUDIO] created artifact path=%s template=%s", path, req.template)
    return {"success": True, "path": path, "template": req.template}
