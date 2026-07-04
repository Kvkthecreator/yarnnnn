"""
Workspace API — File Explorer + Navigation Endpoints

  GET  /api/workspace/nav            — structured nav for Agent OS (ADR-154)
  GET  /api/workspace/domain/:key    — entity listing for a context domain
  GET  /api/workspace/tree           — raw file/folder tree (legacy, still used by file viewer)
  GET  /api/workspace/file           — read file content by path
  PATCH /api/workspace/file          — edit file content by path

All paths are relative to the user's workspace scope in workspace_files table.
"""

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Models
# =============================================================================

class TreeNode(BaseModel):
    path: str
    name: str
    type: str  # "file" | "folder"
    updated_at: Optional[str] = None
    children: Optional[list["TreeNode"]] = None


class FileResponse(BaseModel):
    path: str
    content: Optional[str] = None
    summary: Optional[str] = None
    updated_at: Optional[str] = None
    content_type: Optional[str] = None
    content_url: Optional[str] = None
    metadata: Optional[dict] = None
    # ADR-406 D2: the head revision this content reflects — the editor holds
    # it as the base and sends it back on save (optimistic concurrency).
    head_version_id: Optional[str] = None


class FileEditRequest(BaseModel):
    path: str
    content: str
    summary: Optional[str] = None
    # ADR-209 Phase 4: optional message for the revision's authorship trailer.
    # Default is "edit file {path}"; UI revert sends "revert to r{N}"; bulk
    # edits can send any short description. Always attributed to "operator"
    # via this route.
    message: Optional[str] = None
    # ADR-406 D2: the head_version_id the editor loaded. When present, the
    # write is conditional — a moved head returns 409 with the intervening
    # revision's attribution instead of silently clobbering. Absent →
    # unconditional (legacy callers, bulk tools).
    expected_head_version_id: Optional[str] = None


class RecentArtifact(BaseModel):
    """One delivered output across the workspace (ADR-312 kernel slot #5)."""
    slug: str            # recurrence slug the output belongs to
    date: str            # dated output folder (e.g. "2026-06-04")
    path: str            # full workspace_files path
    summary: Optional[str] = None
    updated_at: Optional[str] = None


class RecentArtifactsResponse(BaseModel):
    artifacts: list[RecentArtifact]


class WorkspaceMember(BaseModel):
    """One principal with an active grant to this workspace (ADR-373 D2).

    Read-only legibility: WHO can write here, and WHAT write-regions they hold.
    In this model an MCP connector from an external LLM is a *member* (a
    foreign-llm principal), so this lists humans AND foreign-LLM/3rd-party
    principals alike. Provisioning (invite / scope) is deferred to a separate
    ADR; this is the "who can touch this workspace" view (ADR-338 management
    plane idiom).
    """
    principal_id: str                      # the stable grant key (user id / client id / slug)
    role: str                              # owner | member | own-agent | foreign-llm | platform | a2a
    label: Optional[str] = None            # humanized name (email / LLM room / slug)
    write_regions: list[str]               # the resolved write-region set (grant scopes or class-default)
    scopes_explicit: bool                  # True if narrowed by an explicit grant; False if class-default
    status: str                            # active | revoked
    granted_by: Optional[str] = None
    created_at: Optional[str] = None


class WorkspaceMembersResponse(BaseModel):
    members: list[WorkspaceMember]
    # Whether the grant-consult is the active authorization path (always True
    # post-ADR-373; surfaced so the FE can render the legibility honestly).
    grant_consult_active: bool = True


class RecentRevision(BaseModel):
    """One authored substrate change across the workspace (ADR-329 D2).

    Distinct from RecentArtifact: a RecentArtifact is a delivered *output*
    (a report). A RecentRevision is an authored *substrate change* — any
    mutation to Layer 1 (workspace_file_versions per ADR-209), regardless
    of whether it produced a deliverable. This is the data behind the
    Files "Recently authored" feed: what the system authored in the
    workspace, and by whom.
    """
    path: str                              # full workspace_files path
    authored_by: Optional[str] = None      # ADR-209 attribution taxonomy
    message: Optional[str] = None          # authorship trailer
    created_at: Optional[str] = None       # revision timestamp
    # Explorer icon-view thumbnails (2026-07-02): per-format preview material so
    # the tile shows real content, not a generic glyph. content_url → real image
    # thumbnail (resolved to a signed URL FE-side); preview → a short text
    # snippet for md/text tiles; content_type → format hint the FE dispatches on.
    content_url: Optional[str] = None      # image blob reference (→ signed URL)
    content_type: Optional[str] = None     # MIME/type hint
    preview: Optional[str] = None          # short text snippet (md/text tiles)


class RecentRevisionsResponse(BaseModel):
    revisions: list[RecentRevision]


# =============================================================================
# GET /workspace/nav — Structured navigation (ADR-154: Agent OS model)
# =============================================================================
# Returns four sections: tasks, domains, outputs, uploads.
# System files hidden. Entities counted from _tracker.md.

@router.get("/workspace/nav")
async def get_workspace_nav(auth: UserClient) -> dict:
    """Structured navigation for the Agent OS workfloor.

    Returns sections the user should see, with system files hidden.
    Tasks come from the tasks table. Domains come from the directory
    registry + _tracker.md entity counts. Outputs and uploads from
    workspace_files.

    ADR-236 Item 6 (2026-04-29): the columns selected here were aligned
    with the post-ADR-231 thin scheduling index. `mode` and `essential`
    were dropped in migration 164.

    Post-ADR-231 cleanup (2026-05-11): the previous "enrich with title from
    TASK.md" loop read `/tasks/{slug}/TASK.md` which no longer exists in
    substrate (ADR-231 D2 deleted the entire `/tasks/` filesystem tree).
    Every iteration silently fell through the exception path to `title=slug`,
    making the read loop a dead RPC. Replaced with deterministic slug → title
    derivation that produces operator-readable strings without a DB hit.
    """
    try:
        # ── Recurrences (from `tasks` thin scheduling index per ADR-231 D4) ──
        # Columns match the post-migration-164 shape. The operator-facing
        # label (Recurring vs One-time) is derived from `schedule` per ADR-163.
        tasks_result = (
            auth.client.table("tasks")
            .select("id, slug, status, schedule, next_run_at, last_run_at")
            .eq("user_id", auth.user_id)
            .order("created_at", desc=True)
            .execute()
        )
        tasks_rows = tasks_result.data or []

        # Derive operator-readable title from slug. Post-ADR-231 recurrences
        # have no `title` field — the slug IS the operator-facing handle —
        # so we humanize it (hyphens → spaces, title-case) for nav display.
        tasks = []
        for row in tasks_rows:
            slug = row["slug"]
            title = slug.replace("-", " ").replace("_", " ").title()
            tasks.append({
                "slug": slug,
                "title": title,
                "status": row.get("status", "active"),
                "schedule": row.get("schedule"),
                "next_run_at": row.get("next_run_at"),
                "last_run_at": row.get("last_run_at"),
            })

        # ── Domains (from directory registry + tracker entity counts) ──
        from services.directory_registry import WORKSPACE_DIRECTORIES, get_tracker_path

        domains = []
        for key, d in WORKSPACE_DIRECTORIES.items():
            if d.get("type") != "context":
                continue
            if key == "signals":
                continue  # Temporal log, not browseable

            entity_count = 0
            tracker_path = get_tracker_path(key)
            if tracker_path:
                try:
                    tracker_result = (
                        auth.client.table("workspace_files")
                        .select("content")
                        .eq("user_id", auth.user_id)
                        .eq("path", f"/workspace/{tracker_path}")
                        .limit(1)
                        .execute()
                    )
                    if tracker_result.data:
                        tracker_content = tracker_result.data[0].get("content", "")
                        # Count table rows (lines with | that aren't header/separator)
                        for line in tracker_content.split("\n"):
                            if line.startswith("|") and "Slug" not in line and "---" not in line and line.strip() != "|":
                                entity_count += 1
                except Exception:
                    pass

            domains.append({
                "key": key,
                "display_name": d.get("display_name", key.title()),
                "entity_count": entity_count,
                "entity_type": d.get("entity_type"),
                "path": f"/workspace/{d['path']}",
            })

        # ADR-154: Outputs section removed — tasks own their outputs directly.
        # Users see outputs by clicking tasks in the Tasks section.

        # ── Uploads (user-contributed files) ──
        uploads = []
        try:
            uploads_result = (
                auth.client.table("workspace_files")
                .select("path, updated_at, summary")
                .eq("user_id", auth.user_id)
                .like("path", "/workspace/uploads/%")
                .order("updated_at", desc=True)
                .limit(20)
                .execute()
            )
            for row in (uploads_result.data or []):
                name = row["path"].split("/")[-1]
                uploads.append({
                    "name": name,
                    "path": row["path"],
                    "updated_at": row.get("updated_at"),
                })
        except Exception:
            pass

        # ── Settings (user-visible and editable) ──
        # ADR-206: authored shared context under constitution/ + governance/ + operation/ (ADR-320 split of legacy _shared/),
        # YARNNN working-memory files under /workspace/system/.
        from services.workspace_paths import (
            PERSONA_IDENTITY_PATH, OPERATION_BRAND_PATH,
            SYSTEM_AWARENESS_PATH, SYSTEM_NOTES_PATH, SYSTEM_STYLE_PATH,
        )
        SETTINGS_FILES = [
            (PERSONA_IDENTITY_PATH, "IDENTITY.md", "Identity"),
            (OPERATION_BRAND_PATH, "BRAND.md", "Brand"),
            (SYSTEM_AWARENESS_PATH, "awareness.md", "Awareness"),
            (SYSTEM_NOTES_PATH, "notes.md", "Notes"),
            (SYSTEM_STYLE_PATH, "style.md", "Style"),
        ]
        settings = []
        for relative_path, filename, label in SETTINGS_FILES:
            path = f"/workspace/{relative_path}"
            try:
                check = (
                    auth.client.table("workspace_files")
                    .select("path, updated_at")
                    .eq("user_id", auth.user_id)
                    .eq("path", path)
                    .limit(1)
                    .execute()
                )
                if check.data:
                    settings.append({
                        "name": label,
                        "filename": filename,
                        "path": path,
                        "updated_at": check.data[0].get("updated_at"),
                    })
            except Exception:
                pass

        # ── Readiness (ADR-155: workspace maturity signal for routing) ──
        # Computed from data we already have — no extra DB queries.
        identity_setting = next((s for s in settings if s["filename"] == "IDENTITY.md"), None)
        identity_richness = "empty"
        if identity_setting:
            try:
                id_content = (
                    auth.client.table("workspace_files")
                    .select("content")
                    .eq("user_id", auth.user_id)
                    .eq("path", f"/workspace/{PERSONA_IDENTITY_PATH}")
                    .limit(1)
                    .execute()
                )
                if id_content.data:
                    text = id_content.data[0].get("content", "")
                    if text and len(text.strip()) >= 100 and text.strip().count("\n") >= 3:
                        identity_richness = "rich"
                    elif text and text.strip():
                        identity_richness = "sparse"
            except Exception:
                pass

        # ADR-156: Phase computed from raw signals — no inference_state needed
        has_domains = any(d["entity_count"] > 0 for d in domains)
        has_tasks = len(tasks) > 0

        return {
            "tasks": tasks,
            "domains": domains,
            "uploads": uploads,
            "settings": settings,
            "readiness": {
                "identity": identity_richness,
                "has_domains": has_domains,
                "has_tasks": has_tasks,
                "phase": (
                    "active" if has_tasks else
                    "ready" if (identity_richness == "rich" and has_domains) else
                    "setup"
                ),
            },
        }

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Nav query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/domain/:key — Entity listing for a context domain
# =============================================================================

@router.get("/workspace/domain/{domain_key}")
async def get_domain_entities(
    auth: UserClient,
    domain_key: str,
) -> dict:
    """List entities in a context domain with their file details.

    Returns entity cards for the domain browser view — each entity
    with its files, last updated, and content preview.
    """
    from services.directory_registry import get_directory, get_directory_path

    directory = get_directory(domain_key)
    if not directory or directory.get("type") != "context":
        raise HTTPException(status_code=404, detail=f"Domain not found: {domain_key}")

    dir_path = get_directory_path(domain_key)
    prefix = f"/workspace/{dir_path}/"

    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content, updated_at, summary")
            .eq("user_id", auth.user_id)
            .like("path", f"{prefix}%")
            .order("path")
            .limit(200)
            .execute()
        )
        rows = result.data or []

        # Separate synthesis files (domain-level) from entity files
        synthesis_files = []
        entities: dict[str, dict] = {}

        for row in rows:
            rel = row["path"].replace(prefix, "")
            parts = rel.split("/")

            # _tracker.md = hidden system file
            if parts[0] == "_tracker.md":
                continue

            # Other _prefixed files at domain root = synthesis files (user-visible)
            if len(parts) == 1 and parts[0].startswith("_"):
                name = parts[0].replace("_", "").replace(".md", "").replace("-", " ").title()
                synthesis_files.append({
                    "name": name,
                    "filename": parts[0],
                    "path": row["path"],
                    "updated_at": row.get("updated_at"),
                    "preview": (row.get("content") or "")[:200].strip() if row.get("content") else None,
                })
                continue

            if len(parts) < 2:
                continue  # Top-level domain files

            entity_slug = parts[0]
            filename = parts[1]

            if entity_slug not in entities:
                entities[entity_slug] = {
                    "slug": entity_slug,
                    "name": entity_slug.replace("-", " ").title(),
                    "files": [],
                    "last_updated": None,
                    "preview": None,
                }

            entities[entity_slug]["files"].append({
                "name": filename,
                "path": row["path"],
                "updated_at": row.get("updated_at"),
            })

            # Track most recent update
            updated = row.get("updated_at")
            if updated and (not entities[entity_slug]["last_updated"] or updated > entities[entity_slug]["last_updated"]):
                entities[entity_slug]["last_updated"] = updated

            # Use profile.md content as preview (first 200 chars)
            if filename == "profile.md" and row.get("content"):
                # Strip markdown headers for clean preview
                content = row["content"]
                preview_lines = []
                for line in content.split("\n"):
                    if line.startswith("#"):
                        continue
                    if line.strip():
                        preview_lines.append(line.strip())
                    if len(" ".join(preview_lines)) > 200:
                        break
                entities[entity_slug]["preview"] = " ".join(preview_lines)[:200]
                # Extract name from first H1
                for line in content.split("\n"):
                    if line.startswith("# "):
                        entities[entity_slug]["name"] = line[2:].strip()
                        break

        return {
            "domain_key": domain_key,
            "domain_path": f"/workspace/{dir_path}",  # actual workspace path (may differ from registry key)
            "display_name": directory.get("display_name", domain_key.title()),
            "entity_type": directory.get("entity_type"),
            "synthesis_files": synthesis_files,
            "entities": list(entities.values()),
            "entity_count": len(entities),
        }

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Domain listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/tree — File/folder tree (legacy, used by file viewer)
# =============================================================================

@router.get("/workspace/tree")
async def get_workspace_tree(
    auth: UserClient,
    root: str = Query("/workspace", description="Root path to list (default: /workspace)"),
) -> list[dict]:
    """
    Returns the workspace file tree for the explorer panel.

    Queries workspace_files for all paths under the root, then builds
    a folder/file tree structure. Supports /workspace/ (the canonical
    substrate root; ADR-320 five-root topology — subfolders include
    constitution/, governance/, persona/, operation/ (domains + reports/ +
    specs/), system/, agents/, uploads/) and /agents/.

    ADR-209 authored substrate enrichment: includes head-revision
    authored_by via the head_version_id FK → workspace_file_versions.
    PostgREST embedded select resolves the FK automatically. When
    head_version_id is NULL (file predates ADR-209 Phase 2 or hasn't
    been attributed yet), authored_by falls back to None and the FE
    shows the updated_at timestamp without an author label.
    """
    try:
        # ADR-209: include head revision authored_by via FK embed.
        # workspace_file_versions!head_version_id resolves the FK named
        # head_version_id on workspace_files → workspace_file_versions.id.
        result = (
            auth.client.table("workspace_files")
            .select(
                "path, updated_at, summary, "
                "workspace_file_versions!head_version_id(authored_by, created_at)"
            )
            .eq("user_id", auth.user_id)
            .like("path", f"{root}/%")
            # ADR-329: archived files (operator 'Delete' = trash-semantics
            # via lifecycle, ADR-209-retained) leave the active tree. NULL
            # lifecycle (the common case) still shows — .neq alone would
            # also exclude NULLs, so the OR keeps them.
            .or_("lifecycle.is.null,lifecycle.neq.archived")
            .order("path")
            .limit(500)
            .execute()
        )
        rows = result.data or []

        # ADR-395: hide the upload text PROJECTION from the tree — it's plumbing
        # (a searchable derivation read by recall, not a user file). The operator
        # sees ONE file (their PDF), not a confusing raw + `.extracted.md` pair.
        # Narrow + symmetric (is_upload_projection): only the co-located
        # inbound/uploads/**.extracted.md is hidden; a pure-text upload (no raw
        # container, no projection) and any user `.md` show normally.
        from services.documents import is_upload_projection
        rows = [r for r in rows if not is_upload_projection(r.get("path", ""))]

        # Normalize: lift authored_by + revision created_at from nested embed.
        # PostgREST returns the embed as a dict (single FK row) or None.
        for row in rows:
            embed = row.pop("workspace_file_versions", None) or {}
            row["authored_by"] = embed.get("authored_by")
            # Use revision created_at as the authoritative "last edited" time
            # when available; fall back to workspace_files.updated_at.
            if embed.get("created_at"):
                row["revision_at"] = embed["created_at"]
            else:
                row["revision_at"] = row.get("updated_at")

        # Build tree from flat paths
        tree = _build_tree(rows, root)
        return tree

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Tree query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/roots — the Files explorer tree SPINE (ADR-388 D1)
# =============================================================================

@router.get("/workspace/roots")
async def get_workspace_roots(auth: UserClient) -> list[dict]:
    """The actual top-level directories under /workspace/, for the derived
    explorer tree (ADR-388 D1 — filesystem-literal, never a hardcoded list).

    Cheap: one path scan, distinct top-level segment, counted in Python (the
    PostgREST client has no GROUP BY). Merged with WORKSPACE_ROOTS so known
    roots get friendly labels/icons and unknown/new roots still appear (raw
    name) — so the ADR-320 governance/+constitution/ roots and the ADR-376
    inbound/ lane show, and any future root the re-founding adds shows too,
    with zero code change (ADR-388 §6).

    Canonical-but-empty roots (agents/, uploads/) are included so the operator
    sees them as creatable. The response is sorted by WORKSPACE_ROOTS.order
    (unknown roots last, alphabetically). Each entry:
      {name, path, display_name, semantic_class, description, icon,
       file_count, exists}
    """
    from services.workspace_paths import WORKSPACE_ROOTS, root_metadata

    try:
        # Scan distinct top-level segments. We only need `path` (cheap select),
        # excluding archived files (mirror the tree query's lifecycle filter).
        result = (
            auth.client.table("workspace_files")
            .select("path")
            .eq("user_id", auth.user_id)
            .like("path", "/workspace/%")
            .or_("lifecycle.is.null,lifecycle.neq.archived")
            .limit(5000)
            .execute()
        )
        rows = result.data or []

        # Count files per top-level segment. A depth-1 file (e.g.
        # /workspace/_workspace_guide.md) has no segment dir — skip it (it's a
        # file, not a root); it surfaces under the root listing, not as a root.
        counts: dict[str, int] = {}
        for row in rows:
            rel = (row.get("path") or "")[len("/workspace/"):]
            if "/" not in rel:
                continue  # depth-1 file, not a root directory
            seg = rel.split("/", 1)[0]
            if not seg:
                continue
            counts[seg] = counts.get(seg, 0) + 1

        # Union of: roots that actually have files + canonical roots we always
        # show (even empty) so the operator can create into them.
        # ADR-395: `uploads` REMOVED from always-show — new uploads land in the
        # inbound/uploads/ raw lane (shown under the `inbound/` root, "Intake"),
        # so the legacy uploads/ root would otherwise render EMPTY next to
        # Intake (the operator-observed duplicate-upload-root). It now shows only
        # when it actually holds pre-ADR-395 legacy files (count > 0).
        always_show = {"agents"}
        names = set(counts) | (always_show & set(WORKSPACE_ROOTS))

        out: list[dict] = []
        for name in names:
            meta = root_metadata(name)
            count = counts.get(name, 0)
            out.append(
                {
                    "name": name,
                    "path": f"/workspace/{name}",
                    "display_name": meta["display_name"],
                    "semantic_class": meta["semantic_class"],
                    "description": meta["description"],
                    "icon": meta["icon"],
                    "file_count": count,
                    "exists": count > 0,
                    "_order": meta["order"],
                }
            )

        # Sort by known order, then alphabetically by display_name.
        out.sort(key=lambda r: (r.pop("_order"), r["display_name"].lower()))
        return out

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Roots query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/file — Read file content
# =============================================================================

@router.get("/workspace/file")
async def get_workspace_file(
    auth: UserClient,
    path: str = Query(
        ...,
        description=(
            "File path. Accepts either workspace-relative "
            "(e.g., 'constitution/MANDATE.md') matching the "
            "WriteFile(scope='workspace') convention, OR absolute "
            "(e.g., '/workspace/constitution/MANDATE.md'). The two "
            "shapes resolve to the same row — the absolute form is "
            "what's stored, the relative form is what callers usually "
            "type."
        ),
    ),
) -> FileResponse:
    """
    Read a single workspace file by path. Path is normalized to match
    UserMemory._full_path convention (services.workspace.UserMemory:670):
    workspace-relative paths get the /workspace/ prefix prepended.
    """
    # ADR-209 + ADR-235 Option A: WriteFile(scope='workspace') passes
    # workspace-relative paths ('constitution/MANDATE.md'), but
    # workspace_files.path is stored absolute ('/workspace/...'). Match
    # the UserMemory convention by normalizing here so readback after
    # write doesn't 404. Singular implementation: one normalization rule
    # per the canonical UserMemory._full_path.
    if not path.startswith("/"):
        normalized_path = f"/workspace/{path}"
    else:
        normalized_path = path

    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content, summary, updated_at, content_type, content_url, metadata, head_version_id")
            .eq("user_id", auth.user_id)
            .eq("path", normalized_path)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            # Echo the original path the caller asked for in the error
            # so they can see what they sent — but mention the normalized
            # form for debugging.
            raise HTTPException(
                status_code=404,
                detail=(
                    f"File not found: {path} "
                    f"(looked up as {normalized_path})"
                ),
            )

        row = rows[0]
        return FileResponse(
            path=row["path"],
            content=row.get("content"),
            summary=row.get("summary"),
            updated_at=row.get("updated_at"),
            content_type=row.get("content_type"),
            content_url=row.get("content_url"),
            metadata=row.get("metadata"),
            head_version_id=row.get("head_version_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] File read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/recent-artifacts — Recent delivered outputs (ADR-312 slot #5)
# =============================================================================
# Kernel-universal Home slot. Reads delivered task outputs across the WHOLE
# workspace (not per-recurrence) from workspace_files, where each
# produces_deliverable recurrence writes /workspace/operation/reports/{slug}/{date}/
# output.md (per routes/recurrences.py report_root convention). Ordered by
# recency. Self-hides on the frontend when empty (bare kernel before any
# deliverable has run). Browser-consumed only — no scheduler/MCP impact.

def _artifact_title(summary: Optional[str], slug: str) -> str:
    """Human title for a delivered artifact (plain-language pass).

    The stored `summary` is frequently a machine string — e.g.
    "Workspace write: reports/weekly-corpus-review/2026-05-26/output.md" —
    which leaks paths to the operator. Strip those shapes and fall back to
    the titleized slug so the Home reads like a Mac, not a workbench.
    """
    s = (summary or "").strip()
    # Drop a leading "Workspace write:" / "Write:" machine prefix.
    for prefix in ("Workspace write:", "Write:", "Output:"):
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):].strip()
    # If what's left looks like a path or is empty, titleize the slug.
    if not s or "/" in s or s.endswith(".md") or s.endswith(".html"):
        return slug.replace("-", " ").replace("_", " ").title() if slug else "Output"
    return s


@router.get("/workspace/recent-artifacts", response_model=RecentArtifactsResponse)
async def get_recent_artifacts(
    auth: UserClient,
    limit: int = Query(5, ge=1, le=25),
) -> RecentArtifactsResponse:
    """Recent delivered outputs across the workspace (ADR-312 Home slot #5)."""
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, summary, updated_at")
            .eq("user_id", auth.user_id)
            .like("path", "/workspace/operation/reports/%/output.md")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        artifacts: list[RecentArtifact] = []
        for row in result.data or []:
            path = row["path"]
            # /workspace/operation/reports/{slug}/{date}/output.md → slug, date
            parts = path.split("/")
            try:
                reports_idx = parts.index("reports")
                slug = parts[reports_idx + 1]
                date = parts[reports_idx + 2]
            except (ValueError, IndexError):
                slug, date = "", ""
            artifacts.append(
                RecentArtifact(
                    slug=slug,
                    date=date,
                    path=path,
                    # Operator-facing title. The stored summary is often a
                    # machine string ("Workspace write: reports/.../output.md")
                    # — strip path-shaped / "Workspace write:" summaries so the
                    # Home shows a human title, falling back to the titleized
                    # slug. Plain-language pass (2026-06-04).
                    summary=_artifact_title(row.get("summary"), slug),
                    updated_at=row.get("updated_at"),
                )
            )
        return RecentArtifactsResponse(artifacts=artifacts)
    except Exception as e:
        logger.error(f"[WORKSPACE_API] Recent artifacts read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/members — Workspace Members legibility (ADR-373 D2)
# =============================================================================
# Read-only "who can write here, and what regions" view over principal_grants.
# The grant-consult (the gate) authorizes per-principal; this surfaces the same
# facts the gate reads. Provisioning (invite / scope) is a separate ADR — this
# is legibility only.

# The class-default write-region logic now lives in services/principals.py (the
# shared principal-commons home) so the steward wake envelope reads the SAME
# roster logic this route does — Singular Implementation. Re-exported under the
# route's prior private name to keep call sites below unchanged.
from services.principals import class_default_write_regions as _class_default_write_regions


@router.get("/workspace/members", response_model=WorkspaceMembersResponse)
async def get_workspace_members(auth: UserClient) -> WorkspaceMembersResponse:
    """List the principals with an active grant to this workspace (ADR-373 D2).

    Read-only legibility surface for the Workspace Members panel. Humanizes each
    principal where possible (owner email; MCP/foreign-LLM room name) and shows
    its resolved write-region set (explicit grant scopes, else the class
    default). At N=1 this is just the owner; the surface is multi-principal-ready
    so a future member / foreign-LLM grant appears the moment it is written.
    """
    try:
        workspace_id = auth.workspace_id
        if not workspace_id:
            from services.supabase import resolve_owner_workspace_id
            workspace_id = resolve_owner_workspace_id(auth.user_id)
        if not workspace_id:
            # No workspace row yet (pre-substrate) → no members to show.
            return WorkspaceMembersResponse(members=[])

        # The grant table is the gate's authority — read it with the service
        # client (membership RLS is mid-transition; the route already scoped to
        # this workspace_id, resolved from the authenticated owner).
        from services.supabase import get_service_client
        svc = get_service_client()
        rows = (
            svc.table("principal_grants")
            .select("principal_id, role, scopes, status, granted_by, created_at")
            .eq("workspace_id", workspace_id)
            .eq("status", "active")
            .order("created_at")
            .execute()
        ).data or []

        # Humanize: owner → email (this auth IS the owner). ADR-373 D2.a:
        # foreign-LLM/platform principal_id is now the PROVIDER host-id
        # (claude.ai / chatgpt), so humanize via the host registry's friendly
        # label. A legacy client_id-keyed row (pre-D2.a, not yet migrated) falls
        # back to the mcp_oauth_clients name lookup so it still shows a name.
        from services.principal_grants import provider_label
        legacy_client_names: dict[str, str] = {}
        legacy_ids = [
            r["principal_id"] for r in rows
            if r.get("role") in ("foreign-llm", "platform", "a2a")
            and provider_label(r["principal_id"]) is None  # not a known host-id
        ]
        if legacy_ids:
            try:
                name_rows = (
                    svc.table("mcp_oauth_clients")
                    .select("client_id, client_name")
                    .in_("client_id", legacy_ids)
                    .execute()
                ).data or []
                legacy_client_names = {r["client_id"]: r.get("client_name") for r in name_rows}
            except Exception as exc:  # best-effort humanization
                logger.debug("[WORKSPACE_API] legacy member client-name lookup failed: %s", exc)

        members: list[WorkspaceMember] = []
        for r in rows:
            role = r.get("role") or "member"
            principal_id = r["principal_id"]
            scopes = r.get("scopes")
            explicit = bool(scopes)  # NULL/[] → class default
            write_regions = list(scopes) if explicit else _class_default_write_regions(role)

            label: Optional[str] = None
            if role == "owner" and principal_id == auth.user_id:
                label = auth.email or "You (owner)"
            elif role in ("foreign-llm", "platform", "a2a"):
                # Provider host-id → friendly label; legacy client_id → name lookup.
                label = (
                    provider_label(principal_id)
                    or legacy_client_names.get(principal_id)
                    or principal_id
                )

            members.append(WorkspaceMember(
                principal_id=principal_id,
                role=role,
                label=label,
                write_regions=write_regions,
                scopes_explicit=explicit,
                status=r.get("status") or "active",
                granted_by=r.get("granted_by"),
                created_at=r.get("created_at"),
            ))

        return WorkspaceMembersResponse(members=members)
    except Exception as e:
        logger.error(f"[WORKSPACE_API] Workspace members read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Member lifecycle verbs (ADR-386 D2) — NARROW + REVOKE
# =============================================================================
# Operate on grants that ALREADY exist (no invite flow). The owner grant is
# immutable from this surface (ADR-386 D4) — the helpers raise
# OwnerGrantImmutable, mapped to 403 here. Both resolve the caller's workspace
# from the authenticated owner.

class NarrowMemberRequest(BaseModel):
    scopes: list[str]   # the write-region set to narrow the member to (ADR-320 roots)


class MemberLifecycleResponse(BaseModel):
    success: bool
    principal_id: str
    action: str                      # "narrow" | "revoke"
    scopes: Optional[list[str]] = None
    tokens_deleted: Optional[int] = None


def _resolve_caller_workspace(auth: UserClient) -> str:
    workspace_id = auth.workspace_id
    if not workspace_id:
        from services.supabase import resolve_owner_workspace_id
        workspace_id = resolve_owner_workspace_id(auth.user_id)
    if not workspace_id:
        raise HTTPException(status_code=404, detail="no workspace for this caller")
    return workspace_id


@router.post("/workspace/members/{principal_id}/narrow", response_model=MemberLifecycleResponse)
async def narrow_member(principal_id: str, body: NarrowMemberRequest, auth: UserClient) -> MemberLifecycleResponse:
    """Tighten a member's write-region scopes (ADR-386 D2 — NARROW).

    Authz-only: the member stays connected, can still read; the gate's allow-list
    path then denies writes outside the narrowed set. The owner grant is
    immutable (403)."""
    from services.principal_grants import narrow_grant, OwnerGrantImmutable
    workspace_id = _resolve_caller_workspace(auth)
    try:
        narrow_grant(principal_id, workspace_id, body.scopes)
    except OwnerGrantImmutable:
        raise HTTPException(status_code=403, detail="the owner grant cannot be narrowed")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"[WORKSPACE_API] member narrow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return MemberLifecycleResponse(
        success=True, principal_id=principal_id, action="narrow", scopes=body.scopes,
    )


@router.post("/workspace/members/{principal_id}/revoke", response_model=MemberLifecycleResponse)
async def revoke_member(principal_id: str, auth: UserClient) -> MemberLifecycleResponse:
    """REVOKE = full eviction (ADR-386 D2/D3): grant revoked + OAuth tokens
    deleted. The member can no longer authenticate, read, or write; it must
    re-authorize from scratch to return. The owner grant is immutable (403)."""
    from services.principal_grants import evict_principal, OwnerGrantImmutable
    workspace_id = _resolve_caller_workspace(auth)
    try:
        result = evict_principal(principal_id, workspace_id)
    except OwnerGrantImmutable:
        raise HTTPException(status_code=403, detail="the owner grant cannot be revoked")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"[WORKSPACE_API] member revoke failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return MemberLifecycleResponse(
        success=True, principal_id=principal_id, action="revoke",
        tokens_deleted=result.get("tokens_deleted"),
    )


# =============================================================================
# Workspace member invites — ADR-404 step 5 (ADR-373 D4 provisioning UX)
# =============================================================================
# The owner invites a human by email; accepting converts the invite into an
# active member grant (ADR-386 lifecycle). Owner-only on the manage verbs;
# the accept verb authenticates the acceptor and matches the invited email.

class InviteCreateRequest(BaseModel):
    email: str


class InviteSummary(BaseModel):
    id: str
    email: str
    role: str
    status: str
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    invite_link: Optional[str] = None


class InviteListResponse(BaseModel):
    invites: list[InviteSummary]


class InviteAcceptResponse(BaseModel):
    success: bool
    workspace_id: str
    workspace_name: Optional[str] = None
    role: str


def _require_owner_workspace(auth: UserClient) -> str:
    """The invite-manage verbs are owner-only (members can't invite members)."""
    from services.workspace_invites import workspace_owner_id
    workspace_id = _resolve_caller_workspace(auth)
    if not workspace_id:
        raise HTTPException(status_code=404, detail="No workspace")
    if workspace_owner_id(workspace_id) != auth.user_id:
        raise HTTPException(status_code=403, detail="Only the workspace owner can manage invites")
    return workspace_id


@router.post("/workspace/members/invite", response_model=InviteSummary)
async def invite_member(body: InviteCreateRequest, auth: UserClient) -> InviteSummary:
    """Invite a human by email as a member (class-default write regions,
    ADR-373 D3). Re-inviting the same address refreshes the token/expiry."""
    from services.deep_links import app_url
    from services.workspace_invites import InviteError, create_invite, send_invite_email

    workspace_id = _require_owner_workspace(auth)
    try:
        invite = create_invite(
            workspace_id=workspace_id, email=body.email, invited_by=auth.user_id,
        )
    except InviteError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Best-effort email (never blocks — the returned link is the fallback).
    ws_name = None
    try:
        from services.workspace_invites import _svc
        rows = (_svc().table("workspaces").select("name")
                .eq("id", workspace_id).limit(1).execute()).data or []
        ws_name = rows[0].get("name") if rows else None
    except Exception:  # noqa: BLE001
        pass
    await send_invite_email(
        email=invite["email"], token=invite["token"],
        workspace_name=ws_name, inviter_email=auth.email,
    )

    return InviteSummary(
        id=invite["id"], email=invite["email"], role=invite["role"],
        status=invite["status"], created_at=str(invite.get("created_at") or ""),
        expires_at=str(invite.get("expires_at") or ""),
        invite_link=f"{app_url()}/invite/{invite['token']}",
    )


@router.get("/workspace/invites", response_model=InviteListResponse)
async def get_workspace_invites(auth: UserClient) -> InviteListResponse:
    from services.workspace_invites import list_invites
    workspace_id = _require_owner_workspace(auth)
    return InviteListResponse(invites=[
        InviteSummary(
            id=r["id"], email=r["email"], role=r["role"], status=r["status"],
            created_at=str(r.get("created_at") or ""),
            expires_at=str(r.get("expires_at") or ""),
        )
        for r in list_invites(workspace_id)
    ])


@router.post("/workspace/invites/{invite_id}/revoke")
async def revoke_workspace_invite(invite_id: str, auth: UserClient) -> dict:
    from services.workspace_invites import revoke_invite
    workspace_id = _require_owner_workspace(auth)
    if not revoke_invite(workspace_id, invite_id):
        raise HTTPException(status_code=404, detail="No pending invite with that id")
    return {"success": True, "id": invite_id}


@router.get("/invites/{token}")
async def preview_invite(token: str, auth: UserClient) -> dict:
    """Accept-page preview: workspace name + invited address + state."""
    from services.workspace_invites import get_invite_by_token
    invite = get_invite_by_token(token)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    return {
        "workspace_name": invite.get("workspace_name"),
        "email": invite["email"],
        "role": invite["role"],
        "status": invite["status"],
        "expires_at": invite.get("expires_at"),
    }


@router.post("/invites/{token}/accept", response_model=InviteAcceptResponse)
async def accept_workspace_invite(token: str, auth: UserClient) -> InviteAcceptResponse:
    """Convert a pending invite into an active member grant (ADR-386 D1).

    The acceptor's JWT email must match the invited address. On success the
    FE binds the commons via the X-Workspace-Id header (ADR-373 sweep spine).
    """
    from services.workspace_invites import InviteError, accept_invite
    try:
        result = accept_invite(token=token, user_id=auth.user_id, user_email=auth.email)
    except InviteError as e:
        status = {
            "not_found": 404, "expired": 410, "not_pending": 409,
            "email_mismatch": 403, "already_owner": 409,
        }.get(e.code, 400)
        raise HTTPException(status_code=status, detail=str(e))
    return InviteAcceptResponse(
        success=True,
        workspace_id=result["workspace_id"],
        workspace_name=result.get("workspace_name"),
        role=result["role"],
    )


# =============================================================================
# GET /workspace/recent-revisions — Recently authored substrate (ADR-329 D2)
# =============================================================================
# The Files "Recently authored" feed. Reads authored substrate changes across
# the WHOLE workspace from workspace_file_versions (ADR-209 revision chain),
# ordered by recency, with ADR-209 authored_by attribution. This answers
# "what did the system author in my workspace while I was away, and by whom?"
#
# Distinct from /recent-artifacts (delivered outputs / reports). This is the
# substrate-change feed — any Layer-1 mutation, deliverable or not.
#
# Layer-1-only (ADR-328 D6): surfaces ONLY authored substrate fields (path,
# authored_by, message, created_at). No Layer-2 leakage (no embeddings, no
# search internals). Read-only, workspace-scoped. Browser-consumed only —
# no scheduler/MCP impact.
#
# Hidden paths: `_`-prefixed machine-config files and signals/ temporal logs
# are excluded — same hide rule the Files explorer applies (files/page.tsx
# isHidden). They're system-accumulated state, not authored substrate the
# operator audits.

# System-strict path prefixes excluded from the authored-substrate feed.
_RECENT_REV_EXCLUDE_DIRS = ("/workspace/context/signals",)


def _is_authored_substrate_path(path: str) -> bool:
    """True if a revision path is operator-auditable authored substrate.

    Mirrors the Files explorer hide rule (files/page.tsx isHidden):
    drop `_`-prefixed machine-config files and temporal signal logs.
    """
    filename = path.rsplit("/", 1)[-1]
    if filename.startswith("_"):
        return False
    for prefix in _RECENT_REV_EXCLUDE_DIRS:
        if path.startswith(prefix):
            return False
    return True


def _thumb_preview(path: str, summary: Optional[str], content: Optional[str]) -> Optional[str]:
    """A short text snippet for an Explorer icon-view text tile (2026-07-02).

    Returns a clean ~140-char preview for markdown/text files (the common case
    in a substrate workspace), so a `.md` tile shows its first real line instead
    of a generic glyph — better than Explorer, which only shows a doc icon.
    Returns None for non-text files (images render a real thumbnail; binaries
    keep a branded glyph). Prefers the curated `summary`; else derives from
    `content`, stripping frontmatter, a `derived_from:` citation line, markdown
    heading/list markers, and blank lines.
    """
    lower = path.lower()
    if not (lower.endswith(".md") or lower.endswith(".txt")):
        return None
    if summary and summary.strip():
        return summary.strip()[:140]
    body = content or ""
    if not body.strip():
        return None
    # Strip a leading YAML frontmatter block if present.
    m = re.match(r"^---\s*\n.*?\n---\s*\n", body, re.DOTALL)
    if m:
        body = body[m.end():]
    lines = []
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("derived_from:") or s.startswith("<!--"):
            continue
        # Drop leading markdown markers (#, -, *, >) for a cleaner snippet.
        s = re.sub(r"^[#>\-\*\s]+", "", s)
        if s:
            lines.append(s)
        if len(" ".join(lines)) >= 140:
            break
    snippet = " ".join(lines).strip()
    return snippet[:140] if snippet else None


@router.get("/workspace/recent-revisions", response_model=RecentRevisionsResponse)
async def get_recent_revisions(
    auth: UserClient,
    limit: int = Query(20, ge=1, le=50),
) -> RecentRevisionsResponse:
    """Recently authored substrate changes across the workspace (ADR-329 D2).

    Two honesty filters (2026-06-30) so a Recents row always opens a real file:
      1. DEDUP by path — keep only the latest revision per path. A file written
         16× was showing 16 identical rows; the feed is "recently-changed
         FILES", not "every revision event".
      2. LIVE-FILE filter — drop paths with no current `workspace_files` row.
         A revision can outlive its file (e.g. a `remember`-dump inbox path that
         was placed/removed by judgment, ADR-368): the revision survives in the
         chain but `GET /workspace/file` 404s. Listing it produced a Recents row
         that opened to "This file isn't here". A revision to a vanished file is
         not browsable substrate, so it leaves the feed.
    """
    try:
        # Over-fetch generously: dedup + the live-file filter both shrink the
        # set, and a hot path (16 revisions to one file) collapses to one row.
        result = (
            auth.client.table("workspace_file_versions")
            .select("path, authored_by, message, created_at")
            .eq("user_id", auth.user_id)
            .order("created_at", desc=True)
            .limit(limit * 10)
            .execute()
        )

        # Dedup by path (keep first = latest, since ordered created_at desc) +
        # apply the authored-substrate hide rule.
        # ADR-395: the upload text projection is plumbing (recall reads it, the
        # operator doesn't) — keep it out of Recents too, so a raw + `.extracted.md`
        # pair never shows as two recent changes.
        from services.documents import is_upload_projection
        latest_by_path: dict[str, dict] = {}
        for row in result.data or []:
            path = row.get("path") or ""
            if not path or path in latest_by_path:
                continue
            if not _is_authored_substrate_path(path):
                continue
            if is_upload_projection(path):
                continue
            latest_by_path[path] = row

        # One round-trip to find live files AND pull per-format preview material
        # (content_url for image thumbnails, content/summary for text snippets) —
        # the Explorer icon view renders real content, not a generic glyph.
        candidate_paths = list(latest_by_path.keys())
        live: dict[str, dict] = {}
        if candidate_paths:
            existing = (
                auth.client.table("workspace_files")
                .select("path, content_url, content_type, summary, content")
                .eq("user_id", auth.user_id)
                .in_("path", candidate_paths)
                .execute()
            )
            live = {r["path"]: r for r in (existing.data or [])}

        # Emit in recency order (dict preserves insertion = created_at desc),
        # live files only, trimmed to limit.
        revisions: list[RecentRevision] = []
        for path, row in latest_by_path.items():
            f = live.get(path)
            if f is None:  # revision outlived its file → not browsable
                continue
            revisions.append(
                RecentRevision(
                    path=path,
                    authored_by=row.get("authored_by"),
                    message=row.get("message"),
                    created_at=row.get("created_at"),
                    content_url=f.get("content_url"),
                    content_type=f.get("content_type"),
                    preview=_thumb_preview(path, f.get("summary"), f.get("content")),
                )
            )
            if len(revisions) >= limit:
                break
        return RecentRevisionsResponse(revisions=revisions)
    except Exception as e:
        logger.error(f"[WORKSPACE_API] Recent revisions read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PATCH /workspace/file — Edit file content
# =============================================================================

@router.patch("/workspace/file")
async def edit_workspace_file(
    auth: UserClient,
    body: FileEditRequest,
) -> dict:
    """
    Edit a workspace file. Upserts by path.

    Allowed for user-editable files: operator-authored substrate under
    `constitution/ + governance/ + operation/ (ADR-320 split of legacy _shared/)`, reviewer principles, memory files,
    task files, and uploads.

    Path normalization matches GET /workspace/file: workspace-relative
    paths (the WriteFile(scope='workspace') convention) get the
    /workspace/ prefix prepended before the editable-prefix check runs.
    """
    raw_path = body.path
    content = body.content

    # ADR-209 + ADR-235 Option A: align with GET handler — accept both
    # absolute and workspace-relative paths. Stored shape is absolute.
    if not raw_path.startswith("/"):
        path = f"/workspace/{raw_path}"
    else:
        path = raw_path

    # Safety: only allow editing certain paths (ADR-206 relocation).
    editable_prefixes = [
        # ADR-215 R3: authored operator substrate is edited on Files with
        # `authored_by=operator` attribution. Same revision-chain path as
        # every other caller (ADR-209).
        "/workspace/persona/IDENTITY.md",
        "/workspace/operation/BRAND.md",
        "/workspace/operation/CONVENTIONS.md",
        "/workspace/constitution/MANDATE.md",
        "/workspace/governance/AUTONOMY.md",
        "/workspace/constitution/PRECEDENT.md",
        "/workspace/persona/principles.md",  # ADR-215 Phase 3 (Reviewer principles)
        "/workspace/system/",     # awareness.md, notes.md, style.md
        "/workspace/uploads/",
        "/workspace/operation/reports/",    # per-recurrence outputs + _feedback.md + _run_log.md (ADR-231 D2)
        "/workspace/context/",    # accumulated context domains (entities, _tracker.md, _feedback.md)
    ]
    if not any(path.startswith(p) or path == p for p in editable_prefixes):
        raise HTTPException(
            status_code=403,
            detail=f"File not editable via API: {path}. Only workspace config and recurrence files are editable.",
        )

    try:
        from datetime import datetime, timezone
        from services.authored_substrate import StaleWriteError, write_revision

        now = datetime.now(timezone.utc).isoformat()

        # ADR-209: operator's direct file edit routes through the Authored
        # Substrate. authored_by="operator" because this is a user-initiated
        # edit via the Context surface. Phase 4: message accepts an explicit
        # short description from UI (revert action sends "revert to r{N}").
        # ADR-406 D2: when the editor states its base, the write is
        # conditional (StaleWriteError → 409 below).
        write_kwargs: dict = {}
        if body.expected_head_version_id is not None:
            write_kwargs["expected_parent_version_id"] = body.expected_head_version_id

        write_revision(
            auth.client,
            user_id=auth.user_id,
            path=path,
            content=content,
            authored_by="operator",
            message=body.message or f"edit file {path}",
            summary=body.summary,
            **write_kwargs,
        )

        logger.info(f"[WORKSPACE_API] File edited: {path}")

        return {
            "success": True,
            "path": path,
            "updated_at": now,
        }

    except StaleWriteError as e:
        # ADR-406 D2: the conflict is a witness moment (ADR-405) — return
        # WHO moved past the caller so the surface can say it. Resolution
        # is reload + reapply (revert-as-write), never a hidden merge.
        logger.info(f"[WORKSPACE_API] Stale write rejected: {path}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "stale_write",
                "path": path,
                "expected_head_version_id": e.expected_parent_version_id,
                "current_head": e.current_head,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] File edit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ADR-209 Phase 4: Authored Substrate revision endpoints
#
# HTTP surface for the revision-aware primitives. Thin wrappers around the
# substrate helpers in services.authored_substrate — RLS via auth.user_id.
# =============================================================================

class RevisionSummary(BaseModel):
    id: str
    authored_by: str
    author_identity_uuid: Optional[str] = None
    message: str
    created_at: str
    parent_version_id: Optional[str] = None
    # Populated only in the subtree (folder Details) case — revisions there
    # span multiple files, so each row carries the file it changed. Omitted
    # (None) for the single-path (file Details) case where the path is the
    # query input and identical for every row.
    path: Optional[str] = None


class RevisionDetail(BaseModel):
    id: str
    path: str
    authored_by: str
    author_identity_uuid: Optional[str] = None
    message: str
    created_at: str
    parent_version_id: Optional[str] = None
    blob_sha: str
    content: Optional[str] = None


class RevisionListResponse(BaseModel):
    path: str
    count: int
    revisions: list[RevisionSummary]


class RevisionDiffResponse(BaseModel):
    path: str
    from_revision: RevisionSummary
    to_revision: RevisionSummary
    diff: str
    identical: bool


@router.get("/workspace/revisions", response_model=RevisionListResponse)
async def list_revisions_route(
    auth: UserClient,
    path: Optional[str] = Query(
        None,
        description="Absolute workspace path for FILE Details (e.g., /workspace/constitution/MANDATE.md). Exactly one of {path, path_prefix} is required.",
    ),
    path_prefix: Optional[str] = Query(
        None,
        description="Absolute workspace folder path for FOLDER Details — returns recent revisions across the subtree (e.g., /workspace/context/portfolio). Exactly one of {path, path_prefix} is required.",
    ),
    limit: int = Query(10, ge=1, le=100, description="Max revisions to return (newest first)"),
) -> RevisionListResponse:
    """ADR-209 Phase 4 + ADR-329 (amended): the revision chain for a node.

    Two scopes — node Details (ADR-329) renders both off this one route:
      - `path` (file Details): the revision chain for a single file, newest
        first. Drives RevisionHistoryPanel's revert/diff (RevisionSummary.path
        is None — the path is the query input).
      - `path_prefix` (folder Details): recent revisions across a folder's
        subtree, newest first, each row carrying the file it changed
        (RevisionSummary.path populated). Read-only aggregate — no revert
        (reverting an aggregate is meaningless; revert lives on file Details).

    Used by the Files surface NodeDetailsPanel.
    """
    if (path is None) == (path_prefix is None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of {path, path_prefix}.",
        )
    try:
        if path is not None:
            # File Details — exact-path chain via the substrate helper.
            from services.authored_substrate import list_revisions

            rows = list_revisions(
                auth.client,
                user_id=auth.user_id,
                path=path,
                limit=limit,
            )
            revisions = [RevisionSummary(**r) for r in rows]
            return RevisionListResponse(path=path, count=len(revisions), revisions=revisions)

        # Folder Details — subtree scan over workspace_file_versions, newest
        # first. Carries per-row path. Same Layer-1-only field set (ADR-328 D6).
        result = (
            auth.client.table("workspace_file_versions")
            .select("id, path, authored_by, author_identity_uuid, message, created_at, parent_version_id")
            .eq("user_id", auth.user_id)
            .like("path", f"{path_prefix}%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        revisions = [
            RevisionSummary(
                id=r["id"],
                authored_by=r.get("authored_by") or "system",
                author_identity_uuid=r.get("author_identity_uuid"),
                message=r.get("message") or "",
                created_at=str(r.get("created_at") or ""),
                parent_version_id=r.get("parent_version_id"),
                path=r.get("path"),
            )
            for r in (result.data or [])
        ]
        return RevisionListResponse(path=path_prefix, count=len(revisions), revisions=revisions)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] list_revisions failed for {path or path_prefix}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/revisions/{revision_id}", response_model=RevisionDetail)
async def read_revision_route(
    auth: UserClient,
    revision_id: str,
    path: str = Query(..., description="Absolute workspace path for ownership scope"),
) -> RevisionDetail:
    """ADR-209 Phase 4: read a specific historical revision's content + metadata.

    The client passes the path alongside the revision_id for clarity + RLS
    cross-check — the substrate helper enforces user scoping at the query
    layer. Used by RevisionHistoryPanel to fetch a selected revision's
    content for diff/revert preview.
    """
    try:
        from services.authored_substrate import read_revision

        rev = read_revision(
            auth.client,
            user_id=auth.user_id,
            path=path,
            revision_id=revision_id,
        )
        if rev is None:
            raise HTTPException(status_code=404, detail=f"Revision {revision_id} not found for {path}")
        return RevisionDetail(
            id=rev.id,
            path=rev.path,
            authored_by=rev.authored_by,
            author_identity_uuid=rev.author_identity_uuid,
            message=rev.message,
            created_at=str(rev.created_at) if rev.created_at else "",
            parent_version_id=rev.parent_version_id,
            blob_sha=rev.blob_sha,
            content=rev.content,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] read_revision failed for {revision_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/revisions/diff/two", response_model=RevisionDiffResponse)
async def diff_revisions_route(
    auth: UserClient,
    path: str = Query(..., description="Absolute workspace path"),
    from_rev: str = Query(..., description="Revision UUID (from) — typically older"),
    to_rev: str = Query(..., description="Revision UUID (to) — typically newer"),
) -> RevisionDiffResponse:
    """ADR-209 Phase 4: unified diff between two revisions of the same path.

    Pure-Python deterministic diff. Zero LLM cost. Used by RevisionHistoryPanel
    inline-diff view.

    Route segment is /diff/two (not /diff) to avoid colliding with the
    /revisions/{revision_id} pattern above — FastAPI would otherwise treat
    "diff" as a revision_id.
    """
    import difflib

    try:
        from services.authored_substrate import read_revision

        rev_from = read_revision(auth.client, user_id=auth.user_id, path=path, revision_id=from_rev)
        rev_to = read_revision(auth.client, user_id=auth.user_id, path=path, revision_id=to_rev)

        if rev_from is None or rev_to is None:
            raise HTTPException(status_code=404, detail="One or both revisions not found")

        from_content = rev_from.content or ""
        to_content = rev_to.content or ""

        diff_lines = list(
            difflib.unified_diff(
                from_content.splitlines(keepends=True),
                to_content.splitlines(keepends=True),
                fromfile=f"{path}@{rev_from.id[:8]}",
                tofile=f"{path}@{rev_to.id[:8]}",
                n=3,
            )
        )
        diff_text = "".join(diff_lines)

        def _summary(r) -> RevisionSummary:
            return RevisionSummary(
                id=r.id,
                authored_by=r.authored_by,
                author_identity_uuid=r.author_identity_uuid,
                message=r.message,
                created_at=str(r.created_at) if r.created_at else "",
                parent_version_id=r.parent_version_id,
            )

        return RevisionDiffResponse(
            path=path,
            from_revision=_summary(rev_from),
            to_revision=_summary(rev_to),
            diff=diff_text,
            identical=rev_from.blob_sha == rev_to.blob_sha,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] diff_revisions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Helpers
# =============================================================================

def _build_tree(rows: list[dict], root: str) -> list[dict]:
    """Build a folder/file tree from flat workspace_files paths.

    Returns list of tree nodes: {name, path, type, updated_at, children}
    """
    # Collect all unique folder paths + file entries
    folders: dict[str, dict] = {}  # path → {name, children, updated_at}
    files: list[dict] = []

    root_prefix = root.rstrip("/") + "/"

    for row in rows:
        full_path = row["path"]
        if not full_path.startswith(root_prefix):
            continue

        relative = full_path[len(root_prefix):]
        parts = relative.split("/")

        # Register all intermediate folders
        for i in range(len(parts) - 1):
            folder_path = root_prefix + "/".join(parts[:i + 1])
            if folder_path not in folders:
                folders[folder_path] = {
                    "name": parts[i],
                    "path": folder_path,
                    "type": "folder",
                    "updated_at": row.get("updated_at"),
                    "children": [],
                }
            else:
                # Update folder timestamp to most recent child
                existing_ts = folders[folder_path].get("updated_at") or ""
                new_ts = row.get("updated_at") or ""
                if new_ts > existing_ts:
                    folders[folder_path]["updated_at"] = new_ts

        # Register the file itself.
        # authored_by + revision_at are set by the tree endpoint when it
        # reads the head_version_id FK embed (ADR-209). They may be None
        # for pre-ADR-209 files or files whose head_version_id is NULL.
        files.append({
            "name": parts[-1],
            "path": full_path,
            "type": "file",
            "updated_at": row.get("revision_at") or row.get("updated_at"),
            "summary": row.get("summary"),
            "authored_by": row.get("authored_by"),
        })

    # Build parent→children relationships
    # Top-level items (direct children of root)
    top_level = []

    for file_node in files:
        parent_path = "/".join(file_node["path"].rsplit("/", 1)[:-1])
        if parent_path in folders:
            folders[parent_path]["children"].append(file_node)
        elif parent_path == root.rstrip("/"):
            top_level.append(file_node)

    for folder_path, folder_node in sorted(folders.items()):
        parent_path = "/".join(folder_path.rsplit("/", 1)[:-1])
        if parent_path in folders:
            folders[parent_path]["children"].append(folder_node)
        elif parent_path == root.rstrip("/"):
            top_level.append(folder_node)

    # Sort children by name (folders first, then files)
    def sort_children(nodes):
        for node in nodes:
            if node.get("children"):
                node["children"] = sorted(
                    node["children"],
                    key=lambda n: (0 if n["type"] == "folder" else 1, n["name"]),
                )
                sort_children(node["children"])

    top_level = sorted(top_level, key=lambda n: (0 if n["type"] == "folder" else 1, n["name"]))
    sort_children(top_level)

    return top_level


# =============================================================================
# GET /workspace/state — Workspace lifecycle status (ADR-244)
# =============================================================================
# Replaces the legacy GET /api/memory/user/onboarding-state endpoint. Single
# canonical workspace-state read for both auth/callback (lazy roster
# scaffolding gate) and the Settings → Workspace surface (program lifecycle).
#
# Side-effect preserved from the legacy endpoint: lazy roster scaffolding
# (calls initialize_workspace if no agents). Idempotent — only fires when
# zero agents exist for the user.
#
# Shape (ADR-244 D2):
#   - has_agents, activation_state, active_program_slug — preserved from
#     legacy OnboardingStateResponse for the auth/callback gate.
#   - available_programs — list of activatable bundles (mirrors the existing
#     /api/programs/activatable endpoint shape; co-located here so the
#     Workspace tab makes one round-trip).
#   - substrate_status — per-file skeleton/authored classification for the
#     core workspace files (mandate, identity, brand, autonomy, principles).
#   - capability_gaps — required-but-not-connected platforms for the active
#     bundle; closes the visibility gap between the substrate marker
#     (active_program_slug) and the capability-implicit signal
#     (bundles_active_for_workspace per ADR-224 §3).

class ProgramItem(BaseModel):
    slug: str
    title: str
    tagline: Optional[str] = None
    status: str
    deferred: bool
    oracle: dict = {}
    current_phase: Optional[str] = None
    # ADR-266 D5/D6: human label for the current phase, derived from the
    # bundle MANIFEST's `phases[].label` field. The FE renders this instead
    # of the raw enum slug (no more bare "OBSERVATION" tokens).
    current_phase_label: Optional[str] = None
    # ADR-338 D4.5: the installer "what this program will do" preview — the
    # program's four-flow declaration (DP26) surfaced BEFORE activation. Shape:
    # {flows:[{key,label,present,summary|rationale}], capabilities, watch_count,
    #  ground_truth}. None when the helper can't read the bundle.
    flow_preview: Optional[dict] = None


class SubstrateFileStatus(BaseModel):
    """Per-file classification surfaced to the Workspace tab.

    `state` semantics:
      - "skeleton" — kernel-default placeholder OR bundle template not yet
        overwritten by operator (matches `_is_skeleton_content` heuristics).
      - "authored" — operator has written substantive content.
      - "missing" — file does not exist (rare; substrate seeding failed).
    """
    path: str
    state: str  # "skeleton" | "authored" | "missing"
    last_revised_at: Optional[str] = None


class SubstrateStatus(BaseModel):
    mandate: SubstrateFileStatus
    identity: SubstrateFileStatus
    brand: SubstrateFileStatus
    autonomy: SubstrateFileStatus
    principles: SubstrateFileStatus  # /workspace/persona/principles.md


class CapabilityGap(BaseModel):
    """A capability the active bundle declares but the workspace does not
    have a corresponding active platform_connection for. Surfaces in the
    Workspace tab so operators see why autonomous execution is paused.
    """
    capability: str
    requires_platform: str
    connected: bool


class WorkspaceStateResponse(BaseModel):
    """ADR-244: canonical workspace-state response.

    Replaces ADR-138/240 OnboardingStateResponse — same auth/callback gate
    fields preserved, plus surface-tab signals.
    """
    has_agents: bool = False
    activation_state: str = "none"
    active_program_slug: Optional[str] = None
    available_programs: list[ProgramItem] = []
    substrate_status: SubstrateStatus
    capability_gaps: list[CapabilityGap] = []
    # Account-level inventory of active platform_connections, independent of
    # the active program's declared requirements. The header connections chip
    # shows demand (capability_gaps) AND inventory (connected_platforms) so the
    # two surfaces stay consistent — e.g. a program that declares no required
    # platforms (alpha-author) no longer reads "No connections required" while
    # the Connectors pane shows Slack/Notion/GitHub Connected. The pane reads
    # the same platform_connections set via /api/integrations.
    connected_platforms: list[str] = []


def _classify_file_state(content: Optional[str]) -> str:
    """Classify a workspace file as 'missing', 'skeleton', or 'authored'.

    Delegates to services.workspace_utils.classify_file_state — single
    implementation shared with workspace_init and working_memory.
    """
    from services.workspace_utils import classify_file_state
    return classify_file_state(content)


@router.get("/workspace/state", response_model=WorkspaceStateResponse)
async def get_workspace_state(request: Request, auth: UserClient) -> WorkspaceStateResponse:
    """ADR-244: workspace lifecycle state — sole canonical read.

    Side effect: triggers lazy roster scaffolding when no agents exist.
    This is the load-bearing first-login behavior the auth/callback depends
    on — preserved verbatim from the legacy onboarding-state endpoint
    (browser timezone via X-Timezone header + workspace_init_complete
    system-card write on first init).
    """
    from services.workspace import UserMemory
    from services.workspace_paths import (
        CONSTITUTION_MANDATE_PATH,
        PERSONA_IDENTITY_PATH,
        OPERATION_BRAND_PATH,
        GOVERNANCE_AUTONOMY_PATH,
        PERSONA_PRINCIPLES_PATH,
    )
    from services.working_memory import _classify_activation_state
    from services.bundle_reader import _all_slugs, _load_manifest
    from services.programs import resolve_active_program_slug, compute_capability_gaps

    # ─── Step 1: lazy roster scaffolding ────────────────────────────────
    try:
        result = (
            auth.client.table("agents")
            .select("id")
            .eq("user_id", auth.user_id)
            .neq("status", "archived")
            .limit(1)
            .execute()
        )
        has_agents = len(result.data or []) > 0

        if not has_agents:
            # ADR-286: `browser_tz` no longer threaded through workspace_init —
            # IDENTITY.md is bundle-owned, not kernel-scaffolded. Operator
            # declares timezone via chat or bundle authoring after activation.
            from services.workspace_init import initialize_workspace
            init_result = await initialize_workspace(auth.client, auth.user_id)
            has_agents = True

            # ADR-179: Write workspace_init_complete system card as persisted
            # session_messages row. Zero LLM cost. TP reads as conversation
            # history on every subsequent turn. Best-effort — workspace init
            # already succeeded; failure to write the card is non-fatal.
            if not init_result.get("already_initialized"):
                try:
                    from routes.feed import get_or_create_session, append_message
                    session = await get_or_create_session(auth.client, auth.user_id)
                    agents_created = init_result.get("agents_created", [])
                    tasks_created = init_result.get("tasks_created", [])
                    await append_message(
                        client=auth.client,
                        session_id=session["id"],
                        role="assistant",
                        content=(
                            "Your workspace is ready. Tell me what you work on "
                            "and I'll set up the rest."
                        ),
                        metadata={
                            "system_card": "workspace_init_complete",
                            "agents_created": len(agents_created),
                            "tasks_created": tasks_created,
                            "summary": "Workspace ready",
                            "pulse": "heartbeat",
                            "weight": "material",
                        },
                    )
                except Exception as card_err:
                    logger.warning(
                        f"[WORKSPACE_STATE] system_card write failed: {card_err}"
                    )
    except Exception as e:
        logger.error(f"[WORKSPACE_STATE] Lazy scaffold failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # ─── Step 2: activation state + active program slug ─────────────────
    um = UserMemory(auth.client, auth.user_id)
    mandate_content = await um.read(CONSTITUTION_MANDATE_PATH)

    # Active-program derivation and activation-state classification are
    # independent reads; keep them in separate try-blocks so a failure in
    # one never silently nulls the other. (Regression: 7e777bf dropped the
    # classifier's make_client_fn param while this call still passed it,
    # raising TypeError that swallowed the program slug for every workspace.)
    # Both the slug-resolve and the capability-gap walk now go through the
    # shared services.programs helpers — same derivation working_memory uses.
    active_program_slug: Optional[str] = resolve_active_program_slug(mandate_content)
    activation_state = "none"
    try:
        activation_state = _classify_activation_state(
            auth.user_id,
            mandate_content,
        )
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] activation-state classification failed: {exc}")

    # ─── Step 3: available programs (activatable list) ──────────────────
    available_programs: list[ProgramItem] = []
    try:
        for slug in _all_slugs():
            manifest = _load_manifest(slug)
            if not manifest:
                continue
            status = manifest.get("status")
            if status not in ("active", "deferred"):
                continue
            # ADR-266 D5/D6: derive current_phase_label from MANIFEST.phases.
            # Same shape as services.composition_resolver._bundle_metadata —
            # bundle MANIFEST is the singular source of truth for phase labels.
            current_phase = manifest.get("current_phase")
            phases = manifest.get("phases") or []
            current_phase_label = next(
                (p.get("label") for p in phases if p.get("key") == current_phase),
                None,
            )
            # ADR-338 D4.5: the installer four-flow preview (shared helper —
            # same canonical slots the activatable route + the D9 gate read).
            from services.bundle_reader import four_flow_preview
            available_programs.append(ProgramItem(
                slug=manifest.get("slug"),
                title=manifest.get("title"),
                tagline=manifest.get("tagline"),
                status=status,
                deferred=(status == "deferred"),
                oracle=manifest.get("oracle") or {},
                current_phase=current_phase,
                current_phase_label=current_phase_label,
                flow_preview=four_flow_preview(slug),
            ))
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] available_programs read failed: {exc}")

    # ─── Step 4: substrate status (per-file classification) ─────────────
    async def _read_file_status(path: str) -> SubstrateFileStatus:
        try:
            content = await um.read(path)
            return SubstrateFileStatus(
                path=path,
                state=_classify_file_state(content),
                last_revised_at=None,  # populated below via head_version_id lookup
            )
        except Exception:
            return SubstrateFileStatus(path=path, state="missing")

    substrate_status = SubstrateStatus(
        mandate=await _read_file_status(CONSTITUTION_MANDATE_PATH),
        identity=await _read_file_status(PERSONA_IDENTITY_PATH),
        brand=await _read_file_status(OPERATION_BRAND_PATH),
        autonomy=await _read_file_status(GOVERNANCE_AUTONOMY_PATH),
        principles=await _read_file_status(PERSONA_PRINCIPLES_PATH),
    )

    # last_revised_at via batched workspace_files lookup (singular round-trip)
    try:
        paths = [
            CONSTITUTION_MANDATE_PATH, PERSONA_IDENTITY_PATH, OPERATION_BRAND_PATH,
            GOVERNANCE_AUTONOMY_PATH, PERSONA_PRINCIPLES_PATH,
        ]
        rows = (
            auth.client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", auth.user_id)
            .in_("path", paths)
            .execute()
        )
        timestamps = {r["path"]: r.get("updated_at") for r in (rows.data or [])}
        substrate_status.mandate.last_revised_at = timestamps.get(CONSTITUTION_MANDATE_PATH)
        substrate_status.identity.last_revised_at = timestamps.get(PERSONA_IDENTITY_PATH)
        substrate_status.brand.last_revised_at = timestamps.get(OPERATION_BRAND_PATH)
        substrate_status.autonomy.last_revised_at = timestamps.get(GOVERNANCE_AUTONOMY_PATH)
        substrate_status.principles.last_revised_at = timestamps.get(PERSONA_PRINCIPLES_PATH)
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] timestamp lookup failed: {exc}")

    # ─── Step 5: connected platforms + capability gaps ──────────────────
    # The active platform_connections set serves two surfaces: the inventory
    # (connected_platforms — always populated, program-independent) and the
    # demand check (capability_gaps — only when a program declares required
    # platforms). Manifest-walk logic lives in services.programs
    # .compute_capability_gaps (shared with working_memory); here we fetch the
    # connected set once via the RLS client and feed both.
    connected_platforms: list[str] = []
    capability_gaps: list[CapabilityGap] = []
    try:
        connections = (
            auth.client.table("platform_connections")
            .select("platform")
            .eq("user_id", auth.user_id)
            .eq("status", "active")
            .execute()
        )
        connected = {r["platform"] for r in (connections.data or [])}
        connected_platforms = sorted(connected)
        if active_program_slug:
            capability_gaps = [
                CapabilityGap(
                    capability=g["capability"],
                    requires_platform=g["platform"],
                    connected=g["connected"],
                )
                for g in compute_capability_gaps(active_program_slug, connected)
            ]
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] platform_connections lookup failed: {exc}")

    return WorkspaceStateResponse(
        has_agents=has_agents,
        activation_state=activation_state,
        active_program_slug=active_program_slug,
        available_programs=available_programs,
        substrate_status=substrate_status,
        capability_gaps=capability_gaps,
        connected_platforms=connected_platforms,
    )


# =============================================================================
# GET /workspace/setup-bundle — Single bundled read for /workspace page (ADR-266)
# =============================================================================
# Collapses 7 round-trips (state + 6 file reads) into 1. The /workspace surface
# (WorkspaceConfigSection) calls this once on mount and on activation refresh.
# Cards keep their self-fetch fallback path for the /agents reuse surface
# (singular implementation: one card, two data-source modes selected by prop
# presence per ADR-266 D8).
#
# Each FileWithRevision returns:
#   - content: workspace_files.content (None if missing)
#   - last_revision: most recent workspace_file_versions row (ADR-209 Phase 4)
#                    used by cards to render "Updated 3 days ago by you" line.
#
# All paths absolute (/workspace/...) for symmetry with workspace_files storage.

class FileWithRevision(BaseModel):
    """One file's content + most recent revision metadata.

    `content` is None when the file does not exist (rare — substrate seeding
    failed). `last_revision` is None when no revision rows exist yet (also
    rare — every write goes through write_revision per ADR-209 Phase 2).
    """
    path: str
    content: Optional[str] = None
    last_revision: Optional[RevisionSummary] = None


class WorkspaceSetupBundleResponse(BaseModel):
    """ADR-266 D8: bundled response for /workspace page mount.

    `state` mirrors the existing /workspace/state shape verbatim — no
    duplication of derivation logic, single source of truth.

    The 6 file fields cover every substrate file the four concept cards
    (Mandate, Autonomy, Principles, Identity/Brand) consume.
    """
    state: WorkspaceStateResponse
    mandate: FileWithRevision
    autonomy_yaml: FileWithRevision
    principles_prose: FileWithRevision
    principles_yaml: FileWithRevision
    identity: FileWithRevision
    brand: FileWithRevision


@router.get("/workspace/setup-bundle", response_model=WorkspaceSetupBundleResponse)
async def get_workspace_setup_bundle(
    request: Request,
    auth: UserClient,
) -> WorkspaceSetupBundleResponse:
    """ADR-266: bundled read for the /workspace page.

    Single endpoint replaces the 7 fan-out reads (1 state + 6 file fetches)
    that WorkspaceConfigSection + 4 cards used to issue independently. The
    cards still accept self-fetch fallback when no data prop is supplied
    (preserves /agents reuse surface).

    All file reads issued in parallel via asyncio.gather. Revision lookups
    use existing list_revisions() with limit=1.
    """
    import asyncio
    from services.workspace import UserMemory
    from services.workspace_paths import (
        CONSTITUTION_MANDATE_PATH,
        PERSONA_IDENTITY_PATH,
        OPERATION_BRAND_PATH,
        GOVERNANCE_AUTONOMY_YAML_PATH,
        PERSONA_PRINCIPLES_PATH,
        PERSONA_PRINCIPLES_YAML_PATH,
    )
    from services.authored_substrate import list_revisions

    # ─── Step 1: state derivation (delegate to existing endpoint logic) ──
    # Calling get_workspace_state directly would re-trigger the lazy
    # scaffolding side-effect; that's correct here too — first mount of
    # /workspace deserves the same scaffolding gate as auth/callback.
    state = await get_workspace_state(request, auth)

    # ─── Step 2: file reads (parallel, absolute paths) ──────────────────
    # UserMemory.read takes workspace-relative paths and prefixes
    # /workspace/ internally. The path constants are relative; the
    # absolute form is what we return to the caller (matches what cards
    # currently pass to api.workspace.getFile).
    um = UserMemory(auth.client, auth.user_id)

    async def _read(rel_path: str) -> Optional[str]:
        try:
            return await um.read(rel_path)
        except Exception:
            return None

    (
        mandate_content,
        autonomy_yaml_content,
        principles_prose_content,
        principles_yaml_content,
        identity_content,
        brand_content,
    ) = await asyncio.gather(
        _read(CONSTITUTION_MANDATE_PATH),
        _read(GOVERNANCE_AUTONOMY_YAML_PATH),
        _read(PERSONA_PRINCIPLES_PATH),
        _read(PERSONA_PRINCIPLES_YAML_PATH),
        _read(PERSONA_IDENTITY_PATH),
        _read(OPERATION_BRAND_PATH),
    )

    # ─── Step 3: revision metadata (parallel, absolute paths) ───────────
    # workspace_file_versions.path is stored absolute (matches workspace_files).
    abs_paths = {
        "mandate": f"/workspace/{CONSTITUTION_MANDATE_PATH}",
        "autonomy_yaml": f"/workspace/{GOVERNANCE_AUTONOMY_YAML_PATH}",
        "principles_prose": f"/workspace/{PERSONA_PRINCIPLES_PATH}",
        "principles_yaml": f"/workspace/{PERSONA_PRINCIPLES_YAML_PATH}",
        "identity": f"/workspace/{PERSONA_IDENTITY_PATH}",
        "brand": f"/workspace/{OPERATION_BRAND_PATH}",
    }

    def _last_rev_sync(abs_path: str) -> Optional[dict]:
        try:
            rows = list_revisions(
                auth.client,
                user_id=auth.user_id,
                path=abs_path,
                limit=1,
            )
            return rows[0] if rows else None
        except Exception as exc:
            logger.warning(f"[SETUP_BUNDLE] revision lookup failed for {abs_path}: {exc}")
            return None

    # list_revisions is sync (Supabase Python client); run in threadpool
    # to keep the gather parallel without blocking the event loop.
    rev_results = await asyncio.gather(
        *(asyncio.to_thread(_last_rev_sync, abs_paths[k]) for k in abs_paths)
    )
    rev_map = dict(zip(abs_paths.keys(), rev_results))

    def _build(key: str, content: Optional[str]) -> FileWithRevision:
        rev = rev_map.get(key)
        return FileWithRevision(
            path=abs_paths[key],
            content=content,
            last_revision=RevisionSummary(**rev) if rev else None,
        )

    return WorkspaceSetupBundleResponse(
        state=state,
        mandate=_build("mandate", mandate_content),
        autonomy_yaml=_build("autonomy_yaml", autonomy_yaml_content),
        principles_prose=_build("principles_prose", principles_prose_content),
        principles_yaml=_build("principles_yaml", principles_yaml_content),
        identity=_build("identity", identity_content),
        brand=_build("brand", brand_content),
    )


# =============================================================================
# GET /workspace/home-bundle — Single bundled read for the Home (ADR-312)
# =============================================================================
# Performance: the Home (ADR-312 six-slot composition) previously fanned out
# up to 6 browser round-trips on mount — composition (useComposition) + a
# conditional workspace-state read (CTA branch) + 3 kernel-slot reads
# (proposals / recent-artifacts / judgment_log) + 2 constitution-band reads
# (MANDATE.md + _autonomy.yaml inside HomeHeader) — several of them in a
# composition→slots waterfall. This collapses the kernel-owned reads into one
# call, mirroring the ADR-266 setup-bundle pattern (7→1).
#
# Singular Implementation: this composes the EXISTING handlers
# (get_workspace_surfaces / list_proposals / get_recent_artifacts) rather than
# re-querying — one source of truth per slot. The kernel slots keep their
# self-fetch fallback on the frontend (they render standalone elsewhere), so
# this endpoint is an optimization, not a new contract surface. Browser-only —
# no scheduler/MCP caller.

class HomeBundleResponse(BaseModel):
    """ADR-312: bundled read for the Home page mount.

    `surfaces` mirrors GET /programs/surfaces verbatim (consumed by
    useComposition initialData). `proposals` is the slot-#3 pending queue,
    `recent_artifacts` slot #5, `judgment_log` slot #6 raw content (parsed
    client-side by the canonical decisions L2 parser). `mandate` +
    `autonomy_yaml` feed the constitution band (HomeHeader). Each consumer
    self-hides on empty, so absent constituents stay honest.
    """
    surfaces: dict
    proposals: list[dict]
    current_occupant: dict
    recent_artifacts: list[RecentArtifact]
    judgment_log: Optional[str] = None
    mandate: Optional[str] = None
    autonomy_yaml: Optional[str] = None


@router.get("/workspace/home-bundle", response_model=HomeBundleResponse)
async def get_home_bundle(
    request: Request,
    auth: UserClient,
) -> HomeBundleResponse:
    """ADR-312: one bundled read for the Home, replacing the per-slot fan-out.

    Composition + the three kernel-universal slots + the two constitution-band
    files, issued in parallel. Composes existing handlers (Singular
    Implementation) so each slot has one query path.
    """
    import asyncio
    from services.workspace import UserMemory
    from services.workspace_paths import (
        CONSTITUTION_MANDATE_PATH,
        GOVERNANCE_AUTONOMY_YAML_PATH,
        PERSONA_JUDGMENT_LOG_PATH,
    )
    from routes.programs import get_workspace_surfaces
    from routes.proposals import list_proposals

    um = UserMemory(auth.client, auth.user_id)

    async def _read(rel_path: str) -> Optional[str]:
        try:
            return await um.read(rel_path)
        except Exception:
            return None

    # All reads in parallel. The kernel-slot handlers are async and take the
    # same auth; the two constitution files go through UserMemory. Slot #5
    # (recent_artifacts) reuses get_recent_artifacts; slot #3 reuses
    # list_proposals; composition reuses get_workspace_surfaces.
    (
        surfaces,
        proposals_envelope,
        artifacts_response,
        mandate_content,
        autonomy_yaml_content,
        judgment_log_content,
    ) = await asyncio.gather(
        get_workspace_surfaces(auth),
        list_proposals(auth, status="pending", limit=5),
        get_recent_artifacts(auth, limit=3),
        _read(CONSTITUTION_MANDATE_PATH),
        _read(GOVERNANCE_AUTONOMY_YAML_PATH),
        _read(PERSONA_JUDGMENT_LOG_PATH),
    )

    return HomeBundleResponse(
        surfaces=surfaces,
        proposals=proposals_envelope.get("proposals", []),
        current_occupant=proposals_envelope.get("current_occupant", {}),
        recent_artifacts=artifacts_response.artifacts,
        judgment_log=judgment_log_content,
        mandate=mandate_content,
        autonomy_yaml=autonomy_yaml_content,
    )
