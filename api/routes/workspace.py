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
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
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


class FileEditRequest(BaseModel):
    path: str
    content: str
    summary: Optional[str] = None
    # ADR-209 Phase 4: optional message for the revision's authorship trailer.
    # Default is "edit file {path}"; UI revert sends "revert to r{N}"; bulk
    # edits can send any short description. Always attributed to "operator"
    # via this route.
    message: Optional[str] = None


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
    """
    try:
        # ── Tasks (from DB) ──
        tasks_result = (
            auth.client.table("tasks")
            .select("id, slug, status, mode, schedule, next_run_at, last_run_at, essential")
            .eq("user_id", auth.user_id)
            .order("created_at", desc=True)
            .execute()
        )
        tasks_rows = tasks_result.data or []

        # Enrich with titles from TASK.md
        tasks = []
        for row in tasks_rows:
            slug = row["slug"]
            # Read title from TASK.md
            title = slug  # fallback
            try:
                task_md_result = (
                    auth.client.table("workspace_files")
                    .select("content")
                    .eq("user_id", auth.user_id)
                    .eq("path", f"/tasks/{slug}/TASK.md")
                    .limit(1)
                    .execute()
                )
                if task_md_result.data:
                    content = task_md_result.data[0].get("content", "")
                    for line in content.split("\n"):
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
            except Exception:
                pass

            tasks.append({
                "slug": slug,
                "title": title,
                "status": row.get("status", "active"),
                "mode": row.get("mode"),
                "schedule": row.get("schedule"),
                "next_run_at": row.get("next_run_at"),
                "last_run_at": row.get("last_run_at"),
                "essential": bool(row.get("essential", False)),
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
        # ADR-206: authored shared context under /workspace/context/_shared/,
        # YARNNN working-memory files under /workspace/memory/.
        from services.workspace_paths import (
            SHARED_IDENTITY_PATH, SHARED_BRAND_PATH,
            MEMORY_AWARENESS_PATH, MEMORY_NOTES_PATH, MEMORY_STYLE_PATH,
        )
        SETTINGS_FILES = [
            (SHARED_IDENTITY_PATH, "IDENTITY.md", "Identity"),
            (SHARED_BRAND_PATH, "BRAND.md", "Brand"),
            (MEMORY_AWARENESS_PATH, "awareness.md", "Awareness"),
            (MEMORY_NOTES_PATH, "notes.md", "Notes"),
            (MEMORY_STYLE_PATH, "style.md", "Style"),
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
                    .eq("path", f"/workspace/{SHARED_IDENTITY_PATH}")
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
    a folder/file tree structure. Supports /workspace/, /agents/, /tasks/.
    """
    try:
        # Query all files under this root
        result = (
            auth.client.table("workspace_files")
            .select("path, updated_at, summary")
            .eq("user_id", auth.user_id)
            .like("path", f"{root}/%")
            .order("path")
            .limit(500)
            .execute()
        )
        rows = result.data or []

        # Build tree from flat paths
        tree = _build_tree(rows, root)
        return tree

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Tree query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/file — Read file content
# =============================================================================

@router.get("/workspace/file")
async def get_workspace_file(
    auth: UserClient,
    path: str = Query(..., description="Full file path (e.g., /workspace/IDENTITY.md)"),
) -> FileResponse:
    """
    Read a single workspace file by path.
    """
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content, summary, updated_at, content_type, content_url, metadata")
            .eq("user_id", auth.user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

        row = rows[0]
        return FileResponse(
            path=row["path"],
            content=row.get("content"),
            summary=row.get("summary"),
            updated_at=row.get("updated_at"),
            content_type=row.get("content_type"),
            content_url=row.get("content_url"),
            metadata=row.get("metadata"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] File read failed: {e}")
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

    Allowed for user-editable files: IDENTITY.md, BRAND.md, TASK.md,
    DELIVERABLE.md, and files in /workspace/uploads/.
    """
    path = body.path
    content = body.content

    # Safety: only allow editing certain paths (ADR-206 relocation).
    editable_prefixes = [
        # ADR-215 R3: authored operator substrate is edited on Files with
        # `authored_by=operator` attribution. Same revision-chain path as
        # every other caller (ADR-209).
        "/workspace/context/_shared/IDENTITY.md",
        "/workspace/context/_shared/BRAND.md",
        "/workspace/context/_shared/CONVENTIONS.md",
        "/workspace/context/_shared/MANDATE.md",
        "/workspace/review/principles.md",  # ADR-215 Phase 3 (Reviewer principles)
        "/workspace/memory/",     # awareness.md, notes.md, style.md
        "/workspace/uploads/",
        "/tasks/",                # TASK.md, DELIVERABLE.md within task folders
    ]
    if not any(path.startswith(p) or path == p for p in editable_prefixes):
        raise HTTPException(
            status_code=403,
            detail=f"File not editable via API: {path}. Only workspace config and task files are editable.",
        )

    try:
        from datetime import datetime, timezone
        from services.authored_substrate import write_revision

        now = datetime.now(timezone.utc).isoformat()

        # ADR-209: operator's direct file edit routes through the Authored
        # Substrate. authored_by="operator" because this is a user-initiated
        # edit via the Context surface. Phase 4: message accepts an explicit
        # short description from UI (revert action sends "revert to r{N}").
        write_revision(
            auth.client,
            user_id=auth.user_id,
            path=path,
            content=content,
            authored_by="operator",
            message=body.message or f"edit file {path}",
            summary=body.summary,
        )

        logger.info(f"[WORKSPACE_API] File edited: {path}")

        return {
            "success": True,
            "path": path,
            "updated_at": now,
        }

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
    path: str = Query(..., description="Absolute workspace path (e.g., /workspace/context/_shared/MANDATE.md)"),
    limit: int = Query(10, ge=1, le=100, description="Max revisions to return (newest first)"),
) -> RevisionListResponse:
    """ADR-209 Phase 4: return the revision chain for a workspace path.

    Newest first. Used by the RevisionHistoryPanel component to render
    "who has edited this file, when, with what message."
    """
    try:
        from services.authored_substrate import list_revisions

        rows = list_revisions(
            auth.client,
            user_id=auth.user_id,
            path=path,
            limit=limit,
        )
        revisions = [RevisionSummary(**r) for r in rows]
        return RevisionListResponse(path=path, count=len(revisions), revisions=revisions)
    except Exception as e:
        logger.error(f"[WORKSPACE_API] list_revisions failed for {path}: {e}")
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

        # Register the file itself
        files.append({
            "name": parts[-1],
            "path": full_path,
            "type": "file",
            "updated_at": row.get("updated_at"),
            "summary": row.get("summary"),
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
