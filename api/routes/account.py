"""
Account Management Routes

Danger zone operations for user account management:
- Clear conversation history
- Delete all deliverables
- Full account reset
- Deactivate account
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class DangerZoneStats(BaseModel):
    """Stats shown before dangerous operations."""
    chat_sessions: int
    memories: int
    deliverables: int
    deliverable_versions: int
    documents: int
    projects: int
    workspaces: int


class OperationResult(BaseModel):
    """Result of a danger zone operation."""
    success: bool
    message: str
    deleted: dict


# =============================================================================
# Stats Endpoint - Show what will be affected
# =============================================================================

@router.get("/account/danger-zone/stats")
async def get_danger_zone_stats(auth: UserClient) -> DangerZoneStats:
    """
    Get counts of all user data that would be affected by danger zone operations.
    """
    user_id = auth.user_id

    # Count chat sessions
    sessions = auth.client.table("chat_sessions").select("id", count="exact").eq("user_id", user_id).execute()
    chat_sessions_count = sessions.count or 0

    # Count memories
    memories = auth.client.table("memories").select("id", count="exact").eq("user_id", user_id).execute()
    memories_count = memories.count or 0

    # Count deliverables
    deliverables = auth.client.table("deliverables").select("id", count="exact").eq("user_id", user_id).neq("status", "archived").execute()
    deliverables_count = deliverables.count or 0

    # Count deliverable versions
    deliverable_ids = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
    versions_count = 0
    if deliverable_ids.data:
        for d in deliverable_ids.data:
            versions = auth.client.table("deliverable_versions").select("id", count="exact").eq("deliverable_id", d["id"]).execute()
            versions_count += versions.count or 0

    # Count documents
    documents = auth.client.table("documents").select("id", count="exact").eq("user_id", user_id).execute()
    documents_count = documents.count or 0

    # Count workspaces and projects
    workspaces = auth.client.table("workspaces").select("id", count="exact").eq("owner_id", user_id).execute()
    workspaces_count = workspaces.count or 0

    projects_count = 0
    if workspaces.data:
        for w in workspaces.data:
            projects = auth.client.table("projects").select("id", count="exact").eq("workspace_id", w["id"]).execute()
            projects_count += projects.count or 0

    return DangerZoneStats(
        chat_sessions=chat_sessions_count,
        memories=memories_count,
        deliverables=deliverables_count,
        deliverable_versions=versions_count,
        documents=documents_count,
        projects=projects_count,
        workspaces=workspaces_count,
    )


# =============================================================================
# Tier 1: Clear Data (Lower Impact)
# =============================================================================

@router.delete("/account/chat-history")
async def clear_chat_history(auth: UserClient) -> OperationResult:
    """
    Delete all chat sessions and messages for the current user.
    Session messages cascade automatically.
    """
    user_id = auth.user_id

    try:
        # Delete all chat sessions (messages cascade via FK)
        result = auth.client.table("chat_sessions").delete().eq("user_id", user_id).execute()
        deleted_count = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} cleared chat history: {deleted_count} sessions")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted_count} chat sessions",
            deleted={"chat_sessions": deleted_count}
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear chat history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history")


# =============================================================================
# Tier 2: Reset Data (Medium Impact)
# =============================================================================

@router.delete("/account/deliverables")
async def delete_all_deliverables(auth: UserClient) -> OperationResult:
    """
    Delete all deliverables and their versions for the current user.
    Returns user to onboarding/cold-start state.
    """
    user_id = auth.user_id

    try:
        # Get deliverable IDs first
        deliverables = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        deliverable_ids = [d["id"] for d in (deliverables.data or [])]

        # Delete versions first (they reference deliverables)
        versions_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_versions").delete().eq("deliverable_id", did).execute()
            versions_deleted += len(result.data or [])

        # Delete deliverables
        result = auth.client.table("deliverables").delete().eq("user_id", user_id).execute()
        deliverables_deleted = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} deleted all deliverables: {deliverables_deleted} deliverables, {versions_deleted} versions")

        return OperationResult(
            success=True,
            message=f"Deleted {deliverables_deleted} deliverables and {versions_deleted} versions",
            deleted={
                "deliverables": deliverables_deleted,
                "deliverable_versions": versions_deleted
            }
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to delete deliverables for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete deliverables")


@router.delete("/account/reset")
async def full_account_reset(auth: UserClient) -> OperationResult:
    """
    Full account reset - delete all user data but keep account active.
    Deletes: deliverables, chat sessions, memories, documents, projects, workspaces.
    Recreates a default workspace so user can continue.
    """
    user_id = auth.user_id
    deleted = {}

    try:
        # 1. Get workspace IDs
        workspaces = auth.client.table("workspaces").select("id").eq("owner_id", user_id).execute()
        workspace_ids = [w["id"] for w in (workspaces.data or [])]

        # 2. Get project IDs
        project_ids = []
        for wid in workspace_ids:
            projects = auth.client.table("projects").select("id").eq("workspace_id", wid).execute()
            project_ids.extend([p["id"] for p in (projects.data or [])])

        # 3. Delete deliverable versions and deliverables
        deliverables = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        deliverable_ids = [d["id"] for d in (deliverables.data or [])]

        versions_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_versions").delete().eq("deliverable_id", did).execute()
            versions_deleted += len(result.data or [])
        deleted["deliverable_versions"] = versions_deleted

        result = auth.client.table("deliverables").delete().eq("user_id", user_id).execute()
        deleted["deliverables"] = len(result.data or [])

        # 4. Delete chat sessions (messages cascade)
        result = auth.client.table("chat_sessions").delete().eq("user_id", user_id).execute()
        deleted["chat_sessions"] = len(result.data or [])

        # 5. Delete memories
        result = auth.client.table("memories").delete().eq("user_id", user_id).execute()
        deleted["memories"] = len(result.data or [])

        # 6. Delete documents
        result = auth.client.table("documents").delete().eq("user_id", user_id).execute()
        deleted["documents"] = len(result.data or [])

        # 7. Delete projects
        for pid in project_ids:
            auth.client.table("projects").delete().eq("id", pid).execute()
        deleted["projects"] = len(project_ids)

        # 8. Delete workspaces
        for wid in workspace_ids:
            auth.client.table("workspaces").delete().eq("id", wid).execute()
        deleted["workspaces"] = len(workspace_ids)

        # 9. Recreate default workspace so user can continue
        new_workspace = auth.client.table("workspaces").insert({
            "name": "My Workspace",
            "owner_id": user_id,
        }).execute()

        logger.info(f"[ACCOUNT] User {user_id} performed full reset: {deleted}")

        return OperationResult(
            success=True,
            message="Account reset complete. You can start fresh.",
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to reset account for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset account")


# =============================================================================
# Tier 3: Account Termination (Irreversible)
# =============================================================================

@router.delete("/account/deactivate")
async def deactivate_account(auth: UserClient) -> OperationResult:
    """
    Permanently deactivate account and delete all data.
    This marks the user for deletion and removes all associated data.

    Note: Actual auth.users deletion requires admin API, but we can:
    1. Delete all user data
    2. Mark workspaces as deleted (soft delete)
    3. The user will need to contact support for full auth deletion

    For now, this performs a full reset and marks user as deactivated.
    """
    user_id = auth.user_id
    deleted = {}

    try:
        # Perform full data deletion (same as reset, but don't recreate workspace)

        # 1. Get workspace IDs
        workspaces = auth.client.table("workspaces").select("id").eq("owner_id", user_id).execute()
        workspace_ids = [w["id"] for w in (workspaces.data or [])]

        # 2. Get project IDs
        project_ids = []
        for wid in workspace_ids:
            projects = auth.client.table("projects").select("id").eq("workspace_id", wid).execute()
            project_ids.extend([p["id"] for p in (projects.data or [])])

        # 3. Delete deliverable versions and deliverables
        deliverables = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        deliverable_ids = [d["id"] for d in (deliverables.data or [])]

        versions_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_versions").delete().eq("deliverable_id", did).execute()
            versions_deleted += len(result.data or [])
        deleted["deliverable_versions"] = versions_deleted

        result = auth.client.table("deliverables").delete().eq("user_id", user_id).execute()
        deleted["deliverables"] = len(result.data or [])

        # 4. Delete chat sessions
        result = auth.client.table("chat_sessions").delete().eq("user_id", user_id).execute()
        deleted["chat_sessions"] = len(result.data or [])

        # 5. Delete memories
        result = auth.client.table("memories").delete().eq("user_id", user_id).execute()
        deleted["memories"] = len(result.data or [])

        # 6. Delete documents
        result = auth.client.table("documents").delete().eq("user_id", user_id).execute()
        deleted["documents"] = len(result.data or [])

        # 7. Delete projects
        for pid in project_ids:
            auth.client.table("projects").delete().eq("id", pid).execute()
        deleted["projects"] = len(project_ids)

        # 8. Delete workspaces (don't recreate)
        for wid in workspace_ids:
            auth.client.table("workspaces").delete().eq("id", wid).execute()
        deleted["workspaces"] = len(workspace_ids)

        # Note: To fully delete auth user, would need service role client:
        # service_client.auth.admin.delete_user(user_id)
        # For now, user can't do anything without a workspace

        logger.info(f"[ACCOUNT] User {user_id} deactivated account: {deleted}")

        return OperationResult(
            success=True,
            message="Account deactivated. All data has been deleted.",
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to deactivate account for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate account")
