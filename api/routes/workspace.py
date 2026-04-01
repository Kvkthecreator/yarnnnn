"""
Workspace API — File Explorer Endpoints

Provides the backend for the Workspace Explorer UI:
  GET  /api/workspace/tree          — file/folder tree from workspace_files
  GET  /api/workspace/file          — read file content by path
  PATCH /api/workspace/file         — edit file content by path

All paths are relative to the user's workspace scope in workspace_files table.
Supports: /workspace/*, /agents/*, /tasks/* paths.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from routes.dependencies import UserClient

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
    metadata: Optional[dict] = None


class FileEditRequest(BaseModel):
    path: str
    content: str
    summary: Optional[str] = None


# =============================================================================
# GET /workspace/tree — File/folder tree
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
            .select("path, content, summary, updated_at, metadata")
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

    # Safety: only allow editing certain paths
    editable_prefixes = [
        "/workspace/IDENTITY.md",
        "/workspace/BRAND.md",
        "/workspace/uploads/",
        "/tasks/",  # TASK.md, DELIVERABLE.md within task folders
    ]
    if not any(path.startswith(p) or path == p for p in editable_prefixes):
        raise HTTPException(
            status_code=403,
            detail=f"File not editable via API: {path}. Only workspace config and task files are editable.",
        )

    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        data = {
            "user_id": auth.user_id,
            "path": path,
            "content": content,
            "updated_at": now,
        }
        if body.summary:
            data["summary"] = body.summary

        auth.client.table("workspace_files").upsert(
            data, on_conflict="user_id,path"
        ).execute()

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
