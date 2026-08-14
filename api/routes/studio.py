"""Studio routes — ADR-440 (the first authoring app).

Two endpoints, both thin over the Studio's program constants
(``services/authoring.py``):

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
# layout registry (services/authoring.py::register_layouts). Without this import
# the registry holds only Studio's layouts and an IMAGES stage silently 404s at
# creation — the module IS the registration, so the import is load-bearing and
# must not be pruned as "unused".
import services.apps.images  # noqa: F401  (import for registration side-effect)

# ADR-518 D3: same contract for the Docs app — importing it registers the
# `document` type (carved out of STUDIO_LAYOUTS) with the shared registry.
import services.apps.docs  # noqa: F401  (import for registration side-effect)

# The cross-app layout resolver (ADR-472 D2). Module-level: the endpoints below
# use these at request time, so a function-local import in ONE handler would
# leave the others with a NameError — which is exactly what shipped and broke
# /studio/templates + /studio/vocabulary in prod (2026-07-20).
from services.authoring import all_layouts, all_templates, resolve_layout

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
            {
                "slug": slug,
                "label": t["label"],
                "description": t["description"],
                "app": t.get("app") or "studio",  # ADR-473 D2
            }
            for slug, t in _templates.items()
        ]
    }


@router.get("/studio/artifacts")
async def list_artifacts(auth: UserClient, app: Optional[str] = None) -> dict:
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

    ADR-473 D4: `app=` scopes the list to the types that app OWNS — the
    Finder/Preview behavior (Preview's Open dialog does not offer `.sketch`).
    Ownership is derived from the artifact's own declared type (`kind` →
    `app_for_kind`), so an app never restates which types are its own. Omitted
    → every artifact, which is what the Files surface (the un-scoped mirror,
    DP29) and any future cross-app view want.
    """
    from services.authoring import (
        STUDIO_ARTIFACT_REGION,
        app_for_kind,
        artifact_kind,
        artifact_name,
    )
    from services.workspace_context import substrate_scope_filter

    # The scope this request resolved to, computed ONCE so the query and the
    # log line can never disagree about which workspace was actually read.
    #
    # ADR-548 D8: `auth.workspace_id` MUST be passed. This call used to omit it
    # and lean on the contextvar rung — but `get_user_client` is a SYNC
    # generator, so FastAPI runs it in a threadpool and the binding never
    # reaches this async handler's context. Resolution fell through to
    # owner-resolution and served the CALLER'S OWN workspace. The log line
    # below is what caught it (2026-08-11): `ws=d5b9029b` (the request's
    # binding) beside `scope=workspace_id=4ca9c664` (what was actually read) —
    # the two disagreeing, which the comment above had declared impossible.
    _scope = substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None))

    rows = (
        auth.client.table("workspace_files")
        .select("path, updated_at, summary, content")
        .eq(*_scope)
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
        # ADR-473 D4: fetch a WIDER window than we return, because ownership is
        # decided AFTER the query (the type is lifted from content, so it is not
        # a column PostgREST can filter on). Without this the scoped app would
        # get "the newest 20 artifacts, then keep the few that are mine" — an
        # app with older work would show an empty landing while its artifacts
        # exist. Trim to the display count after filtering.
        .limit(200)
        .execute()
    ).data or []
    _DISPLAY_LIMIT = 20
    items = []
    for r in rows:
        kind = artifact_kind(r.get("content"))
        # ADR-473 D4: scope by OWNERSHIP. An unowned type (D6) belongs to no
        # app's recents but still lives in Files — absence of an owner is a
        # fallback, never an error.
        if app and app_for_kind(kind.get("kind")) != app:
            continue
        items.append(
            {
                "path": r["path"],
                "updated_at": r.get("updated_at"),
                "summary": r.get("summary"),
                # Both facts are LIFTED from the same content the row already
                # carries (ADR-469 / ADR-459 D1) — no extra read, no storage.
                "name": artifact_name(r["path"], r.get("content")),
                **kind,
            }
        )
        if len(items) >= _DISPLAY_LIMIT:
            break

    # Scoping legibility (2026-08-07). A wrong-ANSWER is invisible to the
    # observability stack: this route 200s whether it returns 12 artifacts or
    # zero, so Sentry (exceptions only) and the Render request log (status
    # codes only) both read it as healthy. A member seeing an empty Docs
    # landing in a workspace holding 12 artifacts is exactly that shape.
    #
    # The two numbers split the only fork that matters:
    #   rows=0            → the QUERY returned nothing (binding/RLS at runtime)
    #   rows>0 returned=0 → the OWNERSHIP filter dropped them (app registry)
    # Kept, not temporary: a scoping decision that cannot be read back is how
    # this class stays invisible.
    logger.info(
        "[SCOPE] artifacts user=%s ws=%s scope=%s=%s app=%s rows=%d returned=%d",
        auth.user_id,
        auth.workspace_id,
        _scope[0],
        _scope[1],
        app,
        len(rows),
        len(items),
    )

    return {
        "artifacts": items
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
    from services.design_systems import find_design_systems, read_default_design_system
    from services.authoring import (
        HEADING_RUNGS,
        MEDIA_BLOCK_KINDS,
        STUDIO_ARRANGEMENTS,
        STUDIO_BLOCKS,
        STUDIO_KERNEL_CSS_VERSION,
        block_group,
        # Underscore-named but module-canonical: it is the ONE scaffold-title
        # set, maintained by register_layouts across every app's registration
        # (ADR-518 D3), so it is not renamed for a second reader.
        _SCAFFOLD_TITLES,
        STUDIO_MEASURES,
        STUDIO_TOKENS,
        compose_kernel_style_element,
    )

    return {
        "tokens": [
            {
                "key": k,
                "label": t["label"],
                # ADR-542 D1 — WHERE (scope) and WHEN (grains) as two declared
                # axes; the compound `applies` slugs are retired from the wire.
                "scope": list(t["scope"]),
                "grains": list(t["grains"]),
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
                "scope": list(m["scope"]),
                "grains": list(m["grains"]),
                "unit": m["unit"],
                "min": m["min"],
                "max": m["max"],
                "css_var": m["css_var"],
                "description": m["description"],
            }
            for k, m in STUDIO_MEASURES.items()
        ],
        "media_kinds": sorted(MEDIA_BLOCK_KINDS),
        # ADR-539 D3 — the heading rung set, declared once in the kernel and
        # served so the outline walk, the Typography ramp, and the turn-into
        # levels all read ONE answer to "which heading levels exist". At audit
        # the system carried four different answers across eight sites.
        "heading_rungs": list(HEADING_RUNGS),
        # ADR-483 — the scaffolded titles, so the FE's name-lift can apply the
        # SAME placeholder guard the server does (`artifact_name` falls through
        # to the folder when the <title> is still a scaffold). NOT derivable
        # FE-side: a deck/page scaffold h1 is a thesis ("The headline promise."),
        # not "Untitled ‹label›", so re-deriving from the served labels would
        # fork the rule and drift. The kernel names it once; the FE reads it.
        "placeholder_titles": sorted(_SCAFFOLD_TITLES),
        "kernel_css_version": STUDIO_KERNEL_CSS_VERSION,
        "kernel_style_element": compose_kernel_style_element(),
        "design_systems": find_design_systems(auth.client, auth.user_id),
        # ADR-487 D5 — the workspace default (the house identity a new
        # artifact is born wearing). Rides the vocabulary (which already
        # carries the systems list) so the read side costs no extra fetch.
        "default_design_system": read_default_design_system(auth.client, auth.user_id),
        "blocks": [
            {
                "kind": k,
                "label": b["label"],
                "description": b["description"],
                # ADR-539 D1 — group is DERIVED from what the kind cites; the
                # wire shape is unchanged but the value can no longer disagree
                # with the citation (the ADR-538 chart/metrics mis-filing class).
                "group": block_group(b),
                "fragment": b["markup"],
                # ADR-539 D1/D2 — the behavior fields, served so the FE derives
                # instead of enumerating: tier (caret vs box on flow, the
                # ADR-525 taxonomy), convertible (Turn-into membership), cites
                # (none|source|picture — picker routing and group derivation).
                "tier": b["tier"],
                "convertible": b["convertible"],
                "cites": b["cites"],
                # ADR-528 D5 — which apps offer this kind. Absent in the row =
                # every app, served as null so the FE tests one field rather
                # than distinguishing "missing" from "empty". The endpoint has
                # no template context (it is the whole grammar, cached once and
                # read by every surface), so ownership is SERVED and the FE
                # filters by the layout it already knows — the same shape as
                # `layouts[].app`, which has been served since ADR-473 D2.
                "apps": list(b["apps"]) if "apps" in b else None,
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
                # ADR-473 D2/D3: which app OWNS this type. Served so the FE
                # resolves kind→app at runtime and never hardcodes a slug — a
                # program-shipped type stays routable with no frontend deploy.
                "app": l.get("app") or "studio",
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
                    "areas": a["areas"],
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
    from services.supabase import get_service_client

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
        # ADR-510: the binary lane rides the ADR-427 CAS seam, which is
        # seam-managed storage (service client) — same as routes/documents.
        service_client=get_service_client(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Import failed."))
    return result


class SetDefaultDesignSystemRequest(BaseModel):
    #: The manifest path to make the workspace default; null CLEARS it.
    manifest: Optional[str] = None


@router.post("/studio/design-systems/default")
async def set_default_design_system_route(
    req: SetDefaultDesignSystemRequest, auth: UserClient
) -> dict:
    """Set/clear the workspace-default design system (ADR-487 D5).

    Writes `_studio.yaml` through the one door (`write_revision`, attributed
    to the operator). The default is an inheritance rule at CREATION — a new
    artifact is born wearing it; per-artifact apply/remove always wins and
    nothing already created is touched.
    """
    import yaml

    from services.authored_substrate import write_revision
    from services.design_systems import (
        STUDIO_DEFAULTS_PATH,
        resolve_design_system,
    )
    from services.workspace_context import substrate_scope_filter

    manifest = (req.manifest or "").strip() or None
    if manifest:
        if not resolve_design_system(auth.client, auth.user_id, manifest):
            raise HTTPException(
                status_code=404, detail=f"Not a design system: {manifest}"
            )

    # Read-modify-write the yaml so future keys survive a default change.
    rows = (
        auth.client.table("workspace_files")
        .select("content")
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
        .eq("path", STUDIO_DEFAULTS_PATH)
        .limit(1)
        .execute()
    ).data or []
    try:
        parsed = yaml.safe_load(rows[0]["content"]) if rows else None
    except Exception:  # noqa: BLE001 — a corrupt config is replaced, not fatal
        parsed = None
    config = parsed if isinstance(parsed, dict) else {}
    if manifest:
        config["default_design_system"] = manifest
    else:
        config.pop("default_design_system", None)

    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=STUDIO_DEFAULTS_PATH,
        content=yaml.safe_dump(config, sort_keys=True, allow_unicode=True),
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=(
            f"Set default design system: {manifest}"
            if manifest
            else "Clear default design system"
        ),
    )
    return {"ok": True, "default_design_system": manifest}


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


class ArrangementPlanRequest(BaseModel):
    """ADR-479 — plan a re-arrangement's placements.

    `blocks` = what is on the page now ({id, kind, text}); `areas` = what the
    target arrangement declares ({name, role, place?}). Both come from the FE,
    which already holds the parsed document and the served registry.

    ADR-544 D6 — `areas` replaces `slots` on the wire, matching the registry the
    FE reads it from. There is no compatibility alias: the only caller is our own
    surface, shipped from the same commit.
    """
    blocks: list[dict]
    areas: list[dict]
    arrangement: Optional[str] = None  # the target slug, for the ledger only


@router.post("/studio/arrangement/plan")
async def plan_arrangement_route(req: ArrangementPlanRequest, auth: UserClient) -> dict:
    """ADR-479 D1 — the placement decision, as judgment.

    Returns `{"placements": [{block_id, area}, ...]}` when the plan is
    admissible, or `{"placements": null}` to tell the FE to use its mechanical
    ladder. A refusal is a normal outcome, never an error: per ADR-468 D4 the
    re-arrangement must never dead-end.

    The model NEVER emits markup — it names an Area per block, and the FE applies
    it deterministically. Validation (ADR-479 D2) enforces the closed Area
    vocabulary and TOTAL BLOCK COVERAGE, so a plan can no longer lose content.
    """
    from services.studio_arrangement_plan import plan_arrangement

    # THE draw gate (ADR-445 §9 closed / ADR-491 Phase 3) — the plan is a costed
    # judgment call drawing the shared pool; gate before launching it. A block
    # returns the mechanical-ladder fallback shape (placements: null), so the
    # FE degrades exactly as it does on a refused plan — never a dead-end
    # (ADR-468 D4) — and no model call is paid for.
    from services.platform_limits import check_draw
    draw_ok, _draw_reason, _draw_detail = check_draw(
        auth.client,
        auth.user_id,
        workspace_id=getattr(auth, "workspace_id", None),
        principal_id=getattr(auth, "principal_id", None) or auth.user_id,
    )
    if not draw_ok:
        return {"placements": None}

    placements, completion = await plan_arrangement(req.blocks or [], req.areas or [])

    # Meter here, exactly once: `route_completion` reports usage but never
    # ledgers (ADR-396 one meter, one ledger). A call that happened costs even
    # when its plan was rejected — we pay for the attempt, not the outcome.
    if completion is not None:
        try:
            from services.supabase import get_service_client
            from services.telemetry import record_execution_event

            record_execution_event(
                get_service_client(),  # service-role only — execution_events RLS
                user_id=auth.user_id,
                slug="studio-arrangement-plan",
                mode="judgment",
                trigger_type="addressed",
                status="success",
                model=completion.ledger_model,
                principal_id=getattr(auth, "principal_id", None) or auth.user_id,
                workspace_id=getattr(auth, "workspace_id", None),
                **completion.usage,
            )
        except Exception as exc:  # noqa: BLE001
            # ERROR, not warning: an unrecorded rented call is unbilled spend —
            # a correctness failure of the ADR-396 one-meter invariant.
            logger.error("[STUDIO] arrangement-plan ledger record failed: %s", exc)

    return {"placements": placements}


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
    from services.workspace_paths import operator_can_organize

    raw = (req.path or "").strip()
    path = raw if raw.startswith("/") else f"/workspace/{raw}"
    # ONE placement law (ADR-555 D2): the same predicate create_artifact,
    # create_folder and upload_documents ask. The old STUDIO_ARTIFACT_REGION
    # prefix fence outlived the create door's relaxation (ADR-549 D3 made the
    # region a DEFAULT, not a gate) — leaving a split-brain where a document
    # created beside its source accepted typing and 403'd every save.
    if not path.endswith(".html") or ".." in path or not operator_can_organize(path):
        raise HTTPException(status_code=403, detail=f"Not a writable artifact path: {path}")
    # ADR-570 D4 (repairing the ADR-501 S1 shape on THIS door): placement is
    # not permission. operator_can_organize answers "may an operator put an
    # artifact here at all"; the per-principal gate answers "may THIS caller
    # write here" (class ceiling + grants). Without it, a scoped member could
    # write .html into constitution/ or governance/ past their ceiling —
    # probe-shaped hole found in the ADR-570 scoping sweep.
    from services.primitives.workspace import _is_path_locked_for_principal

    if _is_path_locked_for_principal(auth, path):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Your grant in this workspace does not permit writing {path}. "
                "The workspace owner can widen it from the Access pane."
            ),
        )
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
    from services.authoring import STUDIO_ARTIFACT_REGION
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
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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
    from services.authoring import artifact_name, set_artifact_title
    from services.workspace_context import substrate_scope_filter

    row = (
        auth.client.table("workspace_files")
        .select("content")
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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
    from services.authoring import STUDIO_ARTIFACT_REGION

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
            .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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


def _redirect_to_free_key(
    auth: UserClient, raw: str, template: str, name: str | None
) -> str:
    """The DELIBERATE door's key, disambiguated in the caller's chosen folder.

    The FE composes `{dest}/{slug(name)}/{template}.html`. The DESTINATION is
    the member's decision and is honoured verbatim; only the meaning-folder KEY
    is recomputed, against the siblings that already exist under that
    destination. `notes/` taken → `notes-2/`.

    Two artifacts may still SHARE a meaning folder when they are different
    shapes (`notes/document.html` + `notes/deck.html`) — that is the existing
    contract and is untouched here; the disambiguation triggers on the exact
    path being occupied, which is the same condition the 409 used to fire on.

    Returns `raw` unchanged when the path is free — the overwhelmingly common
    case, and one DB read.
    """
    from services.naming import disambiguate, path_slug
    from services.workspace_context import substrate_scope_filter

    abs_raw = raw if raw.startswith("/") else f"/workspace/{raw}"
    parts = abs_raw.rsplit("/", 2)
    if len(parts) < 3:
        return raw  # No meaning folder to rename (e.g. `/workspace/deck.html`).
    dest, key, leaf = parts

    rows = (
        auth.client.table("workspace_files")
        .select("path")
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
        .like("path", f"{dest}/%")
        .execute()
    ).data or []
    existing = {r["path"] for r in rows}
    if abs_raw not in existing:
        return raw

    # Occupied. Take the sibling keys under this destination and step the key
    # until free — the same `disambiguate` the immediate door uses.
    taken = {
        rest.split("/")[0]
        for rest in (p[len(dest) + 1:] for p in existing if p.startswith(f"{dest}/"))
        if rest and "/" in rest
    }
    base = path_slug(name) if name and name.strip() else key
    return f"{dest}/{disambiguate(base, taken)}/{leaf}"


@router.post("/studio/artifacts")
async def create_artifact(req: CreateArtifactRequest, auth: UserClient) -> dict:
    from services.authored_substrate import write_revision
    from services.authoring import STUDIO_ARTIFACT_REGION
    from services.workspace_context import substrate_scope_filter

    _templates = all_templates()
    template = _templates.get(req.template)
    if not template:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown template: {req.template!r} (one of {sorted(_templates)})",
        )

    # ── Placement (ADR-549 D1/D2) ──────────────────────────────────────────
    # A creation act NAMES ITS OBJECT. There is no pathless door any more: the
    # caller proposes `{dest}/{slug(name)}/{template}.html`, the destination is
    # honoured verbatim, and the server owns the leaf meaning-folder KEY
    # (recomputed through `disambiguate`, so a second "Notes" becomes `notes-2`
    # rather than being refused — ADR-469 D4).
    #
    # ADR-470's immediate door — no path, no name, `untitled-document/…` — is
    # DELETED. It produced permanent, attributed folders named after whatever
    # the member had not yet decided (`operation/asdfadsf/document.html`). The
    # refusal is explicit rather than a silent server-side placement, because a
    # caller that sends no path has skipped a question, not chosen a default.
    raw = (req.path or "").strip()
    if not raw:
        raise HTTPException(
            status_code=422,
            detail="A new artifact needs a name — send the path it should live at.",
        )
    path = raw if raw.startswith("/") else f"/workspace/{raw}"

    # Validate BEFORE any placement query — `_redirect_to_free_key` runs a
    # prefix search against this path, and a `..` or out-of-region path must be
    # refused rather than queried with.
    if not path.endswith(".html"):
        raise HTTPException(status_code=422, detail="A Studio artifact is an .html file")
    if ".." in path:
        raise HTTPException(status_code=422, detail="Invalid path")
    # ADR-555 D2 — ONE placement law. This was `path.startswith(
    # STUDIO_ARTIFACT_REGION)`, which fenced every artifact into `operation/`
    # while `create_folder` honoured ADR-424 D2 peer folders and uploads had no
    # check at all: one filesystem, three placement laws.
    #
    # ADR-440 D6's actual rule is PRESERVED — "the app owns no namespace;
    # projects are meaning-placed folders, never `studio/…`". That was about not
    # inventing an app-named root, not about confining work to `operation/`. A
    # deck in `the-acme-deal/` satisfies D6 exactly. The region survives as the
    # DEFAULT home (ADR-549 D3's third rung), not as a gate.
    from services.workspace_paths import operator_can_organize

    if not operator_can_organize(path):
        raise HTTPException(
            status_code=403,
            detail="You can't create a file here — that location is managed by the system.",
        )

    # The DELIBERATE door's key, stepped past whatever is already there.
    path = _redirect_to_free_key(auth, path, req.template, req.name)

    # Refuse overwrite — creation is creation (MoveFile-style guard).
    #
    # Both doors now disambiguate, so this is a RACE backstop, not the ordinary
    # collision path: two concurrent creates can compute the same free key
    # between the read and the write. The loser is refused rather than
    # overwriting someone's file.
    existing = (
        auth.client.table("workspace_files")
        .select("path")
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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
    from services.authoring import set_artifact_title

    # Resolved through the registry, never a table subscript: `req.template`
    # may belong to any registered app (Docs' document, an IMAGES stage, a
    # future bundle-shipped shape) — a bare table lookup would 500 on every
    # type its module doesn't own. An unknown layout is not flow (its h1 stays
    # authored), matching artifact_kind's own fallback.
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
    from services.apps.images import STAGE_SLUG, resolve_dimensions, stage_root_attrs

    if req.template == STAGE_SLUG:
        w, h = resolve_dimensions(
            preset_slug=req.preset, width=req.width, height=req.height
        )
        content = content.replace(
            f'<html data-template="{STAGE_SLUG}">',
            f'<html data-template="{STAGE_SLUG}" {stage_root_attrs(w, h)}>',
            1,
        )

    # ── ADR-487 D5: the workspace default — born wearing the house identity ──
    # An inheritance rule at creation only: the skin element lands exactly as
    # the Design tab's Apply would land it (same compose, same marked+cited
    # element), so per-artifact remove/apply works on it unchanged. Best-effort
    # by construction — a dangling or unreadable default resolves to None and
    # the artifact is simply born skin-less (creation never breaks on a
    # convenience).
    from services.design_systems import (
        apply_skin_to_html,
        compose_skin_element,
        read_default_design_system,
        resolve_design_system,
    )

    default_manifest = read_default_design_system(auth.client, auth.user_id)
    if default_manifest:
        ds = resolve_design_system(auth.client, auth.user_id, default_manifest)
        if ds:
            content = apply_skin_to_html(
                content, compose_skin_element(ds["manifest_path"], ds["css_text"])
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
