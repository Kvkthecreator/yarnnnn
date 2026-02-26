"""
Account Management Routes

- Notification preferences (email settings)
- Data & Privacy operations (consolidated purge features):
  - Tier 1: Selective purge (individual data types)
  - Tier 2: Category reset (grouped deletions)
  - Tier 3: Full actions (reset, deactivate)
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient, get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class DangerZoneStats(BaseModel):
    """Comprehensive stats for all user data that can be purged."""
    # Tier 1: Individual data types
    chat_sessions: int
    memories: int
    documents: int
    work_tickets: int

    # Content subtotals
    deliverables: int
    deliverable_versions: int
    work_outputs: int

    # Platform content (ADR-072)
    platform_content: int

    # Integrations
    platform_connections: int
    integration_import_jobs: int
    export_logs: int

    # Hierarchy
    workspaces: int


class OperationResult(BaseModel):
    """Result of a danger zone operation."""
    success: bool
    message: str
    deleted: dict


class NotificationPreferences(BaseModel):
    """User notification preferences for email."""
    email_deliverable_ready: bool = True
    email_deliverable_failed: bool = True
    email_work_complete: bool = True
    email_weekly_digest: bool = True
    email_suggestion_created: bool = True  # ADR-060


class NotificationPreferencesUpdate(BaseModel):
    """Partial update for notification preferences."""
    email_deliverable_ready: Optional[bool] = None
    email_deliverable_failed: Optional[bool] = None
    email_work_complete: Optional[bool] = None
    email_weekly_digest: Optional[bool] = None
    email_suggestion_created: Optional[bool] = None  # ADR-060


# =============================================================================
# Notification Preferences
# =============================================================================

@router.get("/account/notification-preferences")
async def get_notification_preferences(auth: UserClient) -> NotificationPreferences:
    """
    Get user's notification preferences.
    Returns defaults (all true) if no preferences have been set.
    """
    user_id = auth.user_id

    try:
        result = auth.client.table("user_notification_preferences").select("*").eq("user_id", user_id).execute()

        if result.data and len(result.data) > 0:
            prefs = result.data[0]
            return NotificationPreferences(
                email_deliverable_ready=prefs.get("email_deliverable_ready", True),
                email_deliverable_failed=prefs.get("email_deliverable_failed", True),
                email_work_complete=prefs.get("email_work_complete", True),
                email_weekly_digest=prefs.get("email_weekly_digest", True),
                email_suggestion_created=prefs.get("email_suggestion_created", True),  # ADR-060
            )

        # Return defaults if no preferences set
        return NotificationPreferences()

    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to get notification preferences for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification preferences")


@router.patch("/account/notification-preferences")
async def update_notification_preferences(
    auth: UserClient,
    update: NotificationPreferencesUpdate
) -> NotificationPreferences:
    """
    Update user's notification preferences.
    Creates preferences row if it doesn't exist (upsert).
    Only updates fields that are provided.
    """
    user_id = auth.user_id

    try:
        # Check if preferences exist
        existing = auth.client.table("user_notification_preferences").select("id").eq("user_id", user_id).execute()

        # Build update data (only non-None fields)
        update_data = {k: v for k, v in update.model_dump().items() if v is not None}

        if not update_data:
            # No fields to update, return current preferences
            return await get_notification_preferences(auth)

        if existing.data and len(existing.data) > 0:
            # Update existing row
            result = auth.client.table("user_notification_preferences").update(
                {**update_data, "updated_at": "now()"}
            ).eq("user_id", user_id).execute()
        else:
            # Insert new row with defaults + updates
            insert_data = {
                "user_id": user_id,
                "email_deliverable_ready": True,
                "email_deliverable_failed": True,
                "email_work_complete": True,
                "email_weekly_digest": True,
                "email_suggestion_created": True,  # ADR-060
                **update_data
            }
            result = auth.client.table("user_notification_preferences").insert(insert_data).execute()

        logger.info(f"[ACCOUNT] User {user_id} updated notification preferences: {update_data}")

        # Return updated preferences
        return await get_notification_preferences(auth)

    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to update notification preferences for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification preferences")


# =============================================================================
# Stats Endpoint - Show what will be affected
# =============================================================================

@router.get("/account/danger-zone/stats")
async def get_danger_zone_stats(auth: UserClient) -> DangerZoneStats:
    """
    Get counts of all user data for danger zone operations.
    Returns comprehensive stats for the Data & Privacy section.
    """
    user_id = auth.user_id

    try:
        # Count chat sessions
        sessions = auth.client.table("chat_sessions").select("id", count="exact").eq("user_id", user_id).execute()
        chat_sessions_count = sessions.count or 0

        # Count memories (ADR-059: user_context, entry-type keys only)
        memories = auth.client.table("user_context").select("id", count="exact").eq("user_id", user_id).or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%").execute()
        memories_count = memories.count or 0

        # Count documents
        documents = auth.client.table("filesystem_documents").select("id", count="exact").eq("user_id", user_id).execute()
        documents_count = documents.count or 0

        # Count work tickets
        work_tickets = auth.client.table("work_tickets").select("id", count="exact").eq("user_id", user_id).execute()
        work_tickets_count = work_tickets.count or 0

        # Count work outputs (through tickets)
        work_ids = auth.client.table("work_tickets").select("id").eq("user_id", user_id).execute()
        work_outputs_count = 0
        for w in (work_ids.data or []):
            outputs = auth.client.table("work_outputs").select("id", count="exact").eq("ticket_id", w["id"]).execute()
            work_outputs_count += outputs.count or 0

        # Count deliverables (exclude archived)
        deliverables = auth.client.table("deliverables").select("id", count="exact").eq("user_id", user_id).neq("status", "archived").execute()
        deliverables_count = deliverables.count or 0

        # Count deliverable versions
        deliverable_ids = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        versions_count = 0
        for d in (deliverable_ids.data or []):
            versions = auth.client.table("deliverable_versions").select("id", count="exact").eq("deliverable_id", d["id"]).execute()
            versions_count += versions.count or 0

        # Count integrations
        integrations = auth.client.table("platform_connections").select("id", count="exact").eq("user_id", user_id).execute()
        integrations_count = integrations.count or 0

        # Count import jobs
        import_jobs = auth.client.table("integration_import_jobs").select("id", count="exact").eq("user_id", user_id).execute()
        import_jobs_count = import_jobs.count or 0

        # Count export logs
        export_logs = auth.client.table("export_log").select("id", count="exact").eq("user_id", user_id).execute()
        export_logs_count = export_logs.count or 0

        # Count platform content (ADR-072)
        platform_content = auth.client.table("platform_content").select("id", count="exact").eq("user_id", user_id).execute()
        platform_content_count = platform_content.count or 0

        # Count workspaces
        workspaces = auth.client.table("workspaces").select("id", count="exact").eq("owner_id", user_id).execute()
        workspaces_count = workspaces.count or 0

        return DangerZoneStats(
            chat_sessions=chat_sessions_count,
            memories=memories_count,
            documents=documents_count,
            work_tickets=work_tickets_count,
            work_outputs=work_outputs_count,
            deliverables=deliverables_count,
            deliverable_versions=versions_count,
            platform_content=platform_content_count,
            platform_connections=integrations_count,
            integration_import_jobs=import_jobs_count,
            export_logs=export_logs_count,
            workspaces=workspaces_count,
        )

    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to get danger zone stats for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get account stats")


# =============================================================================
# Tier 1: Selective Purge (Individual Data Types)
# =============================================================================

@router.delete("/account/chat-history")
async def clear_chat_history(auth: UserClient) -> OperationResult:
    """
    Delete all chat sessions and messages for the current user.
    Session messages cascade automatically via FK.
    """
    user_id = auth.user_id

    try:
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


@router.delete("/account/memories")
async def clear_all_memories(auth: UserClient) -> OperationResult:
    """
    Delete all memories for the current user.
    Includes user memories and project-scoped memories.
    """
    user_id = auth.user_id

    try:
        # ADR-059: Delete entry-type keys from user_context (fact:/instruction:/preference:)
        result = auth.client.table("user_context").delete().eq("user_id", user_id).or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%").execute()
        deleted_count = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} cleared all memories: {deleted_count}")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted_count} memories",
            deleted={"memories": deleted_count}
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear memories for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear memories")


@router.delete("/account/documents")
async def clear_all_documents(auth: UserClient) -> OperationResult:
    """
    Delete all documents and their chunks for the current user.
    Chunks cascade automatically via FK.
    """
    user_id = auth.user_id

    try:
        result = auth.client.table("filesystem_documents").delete().eq("user_id", user_id).execute()
        deleted_count = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} cleared all documents: {deleted_count}")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted_count} documents",
            deleted={"documents": deleted_count}
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear documents for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear documents")


@router.delete("/account/work")
async def clear_work_history(auth: UserClient) -> OperationResult:
    """
    Delete all work tickets and outputs for the current user.
    Work outputs cascade automatically via FK.
    """
    user_id = auth.user_id

    try:
        result = auth.client.table("work_tickets").delete().eq("user_id", user_id).execute()
        deleted_count = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} cleared work history: {deleted_count} tickets")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted_count} work tickets",
            deleted={"work_tickets": deleted_count}
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear work history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear work history")


# =============================================================================
# Tier 2: Category Reset (Grouped Deletions)
# =============================================================================

@router.delete("/account/content")
async def clear_all_content(auth: UserClient) -> OperationResult:
    """
    Delete all content (deliverables and work history).
    Returns user to cold-start state for content generation.
    """
    user_id = auth.user_id
    deleted = {}

    try:
        # Delete deliverable versions first (FK constraint)
        deliverables = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        deliverable_ids = [d["id"] for d in (deliverables.data or [])]

        versions_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_versions").delete().eq("deliverable_id", did).execute()
            versions_deleted += len(result.data or [])
        deleted["deliverable_versions"] = versions_deleted

        # Delete deliverables
        result = auth.client.table("deliverables").delete().eq("user_id", user_id).execute()
        deleted["deliverables"] = len(result.data or [])

        # Delete work tickets (outputs cascade)
        result = auth.client.table("work_tickets").delete().eq("user_id", user_id).execute()
        deleted["work_tickets"] = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} cleared all content: {deleted}")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted['deliverables']} deliverables and {deleted['work_tickets']} work tickets",
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear content for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear content")


@router.delete("/account/context")
async def clear_all_context(auth: UserClient) -> OperationResult:
    """
    Delete all context data (memories, documents, chat history).
    Removes all learned context about the user.
    """
    user_id = auth.user_id
    deleted = {}

    try:
        # Delete chat sessions (messages cascade)
        result = auth.client.table("chat_sessions").delete().eq("user_id", user_id).execute()
        deleted["chat_sessions"] = len(result.data or [])

        # Delete all user_context rows (ADR-059)
        result = auth.client.table("user_context").delete().eq("user_id", user_id).execute()
        deleted["memories"] = len(result.data or [])

        # Delete documents (chunks cascade)
        result = auth.client.table("filesystem_documents").delete().eq("user_id", user_id).execute()
        deleted["documents"] = len(result.data or [])

        # Delete synced platform content (ADR-072)
        result = auth.client.table("platform_content").delete().eq("user_id", user_id).execute()
        deleted["platform_content"] = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} cleared all context: {deleted}")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted['memories']} memories, {deleted['documents']} documents, {deleted['chat_sessions']} chats, {deleted['platform_content']} synced items",
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear context for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear context")


@router.delete("/account/integrations")
async def clear_all_integrations(auth: UserClient) -> OperationResult:
    """
    Disconnect all integrations and clear import/export history.
    OAuth tokens will be deleted - user must reconnect.
    """
    user_id = auth.user_id
    deleted = {}

    try:
        # Delete export logs
        result = auth.client.table("export_log").delete().eq("user_id", user_id).execute()
        deleted["export_logs"] = len(result.data or [])

        # Delete import jobs
        result = auth.client.table("integration_import_jobs").delete().eq("user_id", user_id).execute()
        deleted["integration_import_jobs"] = len(result.data or [])

        # Delete sync registry records
        result = auth.client.table("sync_registry").delete().eq("user_id", user_id).execute()
        deleted["sync_registry"] = len(result.data or [])

        # Delete sync configs
        result = auth.client.table("integration_sync_config").delete().eq("user_id", user_id).execute()
        deleted["integration_sync_config"] = len(result.data or [])

        # Delete export preferences (through deliverables)
        deliverables = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        prefs_deleted = 0
        for d in (deliverables.data or []):
            result = auth.client.table("deliverable_export_preferences").delete().eq("deliverable_id", d["id"]).execute()
            prefs_deleted += len(result.data or [])
        deleted["export_preferences"] = prefs_deleted

        # Delete user integrations (OAuth tokens)
        result = auth.client.table("platform_connections").delete().eq("user_id", user_id).execute()
        deleted["platform_connections"] = len(result.data or [])

        logger.info(f"[ACCOUNT] User {user_id} cleared all integrations: {deleted}")

        return OperationResult(
            success=True,
            message=f"Disconnected {deleted['platform_connections']} integrations and cleared history",
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear integrations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear integrations")


# =============================================================================
# Tier 3: Full Actions (High Impact)
# =============================================================================

@router.delete("/account/reset")
async def full_account_reset(auth: UserClient) -> OperationResult:
    """
    Full account reset - delete all user data but keep account active.
    Deletes: deliverables, chat sessions, memories, documents, work, integrations.
    Recreates a default workspace so user can continue.
    """
    user_id = auth.user_id
    deleted = {}

    try:
        # 1. Get workspace IDs
        workspaces = auth.client.table("workspaces").select("id").eq("owner_id", user_id).execute()
        workspace_ids = [w["id"] for w in (workspaces.data or [])]

        # 2. Delete deliverable versions and deliverables
        deliverables = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        deliverable_ids = [d["id"] for d in (deliverables.data or [])]

        versions_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_versions").delete().eq("deliverable_id", did).execute()
            versions_deleted += len(result.data or [])
        deleted["deliverable_versions"] = versions_deleted

        result = auth.client.table("deliverables").delete().eq("user_id", user_id).execute()
        deleted["deliverables"] = len(result.data or [])

        # 3. Delete work tickets (outputs cascade)
        result = auth.client.table("work_tickets").delete().eq("user_id", user_id).execute()
        deleted["work_tickets"] = len(result.data or [])

        # 4. Delete chat sessions (messages cascade)
        result = auth.client.table("chat_sessions").delete().eq("user_id", user_id).execute()
        deleted["chat_sessions"] = len(result.data or [])

        # 5. Delete all user_context rows (ADR-059)
        result = auth.client.table("user_context").delete().eq("user_id", user_id).execute()
        deleted["memories"] = len(result.data or [])

        # 6. Delete documents
        result = auth.client.table("filesystem_documents").delete().eq("user_id", user_id).execute()
        deleted["documents"] = len(result.data or [])

        # 6b. Delete synced platform content (ADR-072)
        result = auth.client.table("platform_content").delete().eq("user_id", user_id).execute()
        deleted["platform_content"] = len(result.data or [])

        # 7. Delete integration data
        result = auth.client.table("export_log").delete().eq("user_id", user_id).execute()
        deleted["export_logs"] = len(result.data or [])

        result = auth.client.table("integration_import_jobs").delete().eq("user_id", user_id).execute()
        deleted["integration_import_jobs"] = len(result.data or [])

        result = auth.client.table("sync_registry").delete().eq("user_id", user_id).execute()
        deleted["sync_registry"] = len(result.data or [])

        result = auth.client.table("integration_sync_config").delete().eq("user_id", user_id).execute()
        deleted["integration_sync_config"] = len(result.data or [])

        prefs_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_export_preferences").delete().eq("deliverable_id", did).execute()
            prefs_deleted += len(result.data or [])
        deleted["export_preferences"] = prefs_deleted

        result = auth.client.table("platform_connections").delete().eq("user_id", user_id).execute()
        deleted["platform_connections"] = len(result.data or [])

        # 7b. Delete notification preferences
        try:
            auth.client.table("user_notification_preferences").delete().eq("user_id", user_id).execute()
        except Exception:
            pass  # Table may not exist yet for this user

        # 8. Delete workspaces
        for wid in workspace_ids:
            auth.client.table("workspaces").delete().eq("id", wid).execute()
        deleted["workspaces"] = len(workspace_ids)

        # 9. Recreate default workspace so user can continue
        auth.client.table("workspaces").insert({
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


@router.delete("/account/deactivate")
async def deactivate_account(auth: UserClient) -> OperationResult:
    """
    Permanently deactivate account and delete all data.
    Uses service role to delete from auth.users.
    """
    user_id = auth.user_id
    deleted = {}

    try:
        # 1. Get workspace IDs
        workspaces = auth.client.table("workspaces").select("id").eq("owner_id", user_id).execute()
        workspace_ids = [w["id"] for w in (workspaces.data or [])]

        # 2. Delete deliverable versions and deliverables
        deliverables = auth.client.table("deliverables").select("id").eq("user_id", user_id).execute()
        deliverable_ids = [d["id"] for d in (deliverables.data or [])]

        versions_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_versions").delete().eq("deliverable_id", did).execute()
            versions_deleted += len(result.data or [])
        deleted["deliverable_versions"] = versions_deleted

        result = auth.client.table("deliverables").delete().eq("user_id", user_id).execute()
        deleted["deliverables"] = len(result.data or [])

        # 3. Delete work tickets (outputs cascade)
        result = auth.client.table("work_tickets").delete().eq("user_id", user_id).execute()
        deleted["work_tickets"] = len(result.data or [])

        # 4. Delete chat sessions
        result = auth.client.table("chat_sessions").delete().eq("user_id", user_id).execute()
        deleted["chat_sessions"] = len(result.data or [])

        # 5. Delete all user_context rows (ADR-059)
        result = auth.client.table("user_context").delete().eq("user_id", user_id).execute()
        deleted["memories"] = len(result.data or [])

        # 6. Delete documents
        result = auth.client.table("filesystem_documents").delete().eq("user_id", user_id).execute()
        deleted["documents"] = len(result.data or [])

        # 6b. Delete synced platform content (ADR-072)
        result = auth.client.table("platform_content").delete().eq("user_id", user_id).execute()
        deleted["platform_content"] = len(result.data or [])

        # 7. Delete integration data
        result = auth.client.table("export_log").delete().eq("user_id", user_id).execute()
        deleted["export_logs"] = len(result.data or [])

        result = auth.client.table("integration_import_jobs").delete().eq("user_id", user_id).execute()
        deleted["integration_import_jobs"] = len(result.data or [])

        result = auth.client.table("sync_registry").delete().eq("user_id", user_id).execute()
        deleted["sync_registry"] = len(result.data or [])

        result = auth.client.table("integration_sync_config").delete().eq("user_id", user_id).execute()
        deleted["integration_sync_config"] = len(result.data or [])

        prefs_deleted = 0
        for did in deliverable_ids:
            result = auth.client.table("deliverable_export_preferences").delete().eq("deliverable_id", did).execute()
            prefs_deleted += len(result.data or [])
        deleted["export_preferences"] = prefs_deleted

        result = auth.client.table("platform_connections").delete().eq("user_id", user_id).execute()
        deleted["platform_connections"] = len(result.data or [])

        # 7b. Delete notification preferences
        try:
            auth.client.table("user_notification_preferences").delete().eq("user_id", user_id).execute()
        except Exception:
            pass  # Table may not exist yet for this user

        # 8. Delete workspaces (don't recreate)
        for wid in workspace_ids:
            auth.client.table("workspaces").delete().eq("id", wid).execute()
        deleted["workspaces"] = len(workspace_ids)

        # 9. Delete from auth.users using service role
        try:
            service_client = get_service_client()
            service_client.auth.admin.delete_user(user_id)
            deleted["auth_user"] = 1
            logger.info(f"[ACCOUNT] User {user_id} auth record deleted")
        except Exception as auth_error:
            # Log but don't fail - user data is already deleted
            logger.warning(f"[ACCOUNT] Failed to delete auth user {user_id}: {auth_error}")
            deleted["auth_user"] = 0

        logger.info(f"[ACCOUNT] User {user_id} deactivated account: {deleted}")

        return OperationResult(
            success=True,
            message="Account deactivated. All data has been deleted.",
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to deactivate account for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate account")
