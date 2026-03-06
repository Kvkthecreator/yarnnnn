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
# Purge Configuration
# =============================================================================

MEMORY_ENTRY_FILTER = "key.like.fact:%,key.like.instruction:%,key.like.preference:%"

# Full reset = clear all user-scoped product data while keeping auth account active.
# Workspaces are handled separately (deleted + default recreated).
FULL_RESET_USER_TABLES: tuple[str, ...] = (
    "activity_log",
    "chat_sessions",
    "deliverable_proposals",
    "deliverables",  # Cascades deliverable_versions/export prefs/delivery logs
    "destination_delivery_log",
    "event_trigger_log",
    "export_log",
    "filesystem_documents",
    "integration_import_jobs",
    "integration_sync_config",
    "notifications",
    "platform_connections",
    "platform_content",
    "project_resources",
    "slack_user_cache",
    "sync_registry",
    "synthesizer_context_log",
    "user_interaction_patterns",
    "user_memory",
    "user_notification_preferences",
    "user_platform_styles",
)

# Optional/rolling tables (not guaranteed to exist in all environments).
OPTIONAL_USER_TABLES: tuple[str, ...] = (
    "trigger_event_log",
)

MCP_OAUTH_TABLES: tuple[str, ...] = (
    "mcp_oauth_codes",
    "mcp_oauth_access_tokens",
    "mcp_oauth_refresh_tokens",
)


# =============================================================================
# Response Models
# =============================================================================

class DangerZoneStats(BaseModel):
    """Comprehensive stats for all user data that can be purged."""
    # Tier 1: Individual data types
    chat_sessions: int
    memories: int
    documents: int

    # Content subtotals
    deliverables: int
    deliverable_versions: int

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
    email_suggestion_created: bool = True


class NotificationPreferencesUpdate(BaseModel):
    """Partial update for notification preferences."""
    email_deliverable_ready: Optional[bool] = None
    email_deliverable_failed: Optional[bool] = None
    email_suggestion_created: Optional[bool] = None


# =============================================================================
# Internal Helpers
# =============================================================================

def _is_missing_relation_error(error: Exception) -> bool:
    message = str(error).lower()
    return "relation" in message and "does not exist" in message


def _count_rows_for_user(
    client,
    table: str,
    user_id: str,
    *,
    user_column: str = "user_id",
    or_filter: Optional[str] = None,
    optional: bool = False,
) -> int:
    """Count rows in a user-scoped table (optionally filtered)."""
    try:
        query = client.table(table).select("*", count="exact").eq(user_column, user_id)
        if or_filter:
            query = query.or_(or_filter)
        result = query.execute()
        return result.count or 0
    except Exception as error:
        if optional and _is_missing_relation_error(error):
            logger.info(f"[ACCOUNT] Optional table missing during count: {table}")
            return 0
        if optional:
            logger.warning(f"[ACCOUNT] Optional count failed for {table}: {error}")
            return 0
        raise


def _delete_rows_for_user(
    client,
    table: str,
    user_id: str,
    *,
    user_column: str = "user_id",
    or_filter: Optional[str] = None,
    optional: bool = False,
) -> int:
    """Delete rows in a user-scoped table and return deleted count."""
    try:
        deleted_count = _count_rows_for_user(
            client,
            table,
            user_id,
            user_column=user_column,
            or_filter=or_filter,
            optional=optional,
        )
        if deleted_count == 0:
            return 0

        query = client.table(table).delete().eq(user_column, user_id)
        if or_filter:
            query = query.or_(or_filter)
        query.execute()
        return deleted_count
    except Exception as error:
        if optional and _is_missing_relation_error(error):
            logger.info(f"[ACCOUNT] Optional table missing during delete: {table}")
            return 0
        if optional:
            logger.warning(f"[ACCOUNT] Optional delete failed for {table}: {error}")
            return 0
        raise


def _get_user_deliverable_ids(client, user_id: str) -> list[str]:
    result = client.table("deliverables").select("id").eq("user_id", user_id).execute()
    return [d["id"] for d in (result.data or [])]


def _delete_export_preferences_for_user(client, user_id: str) -> int:
    """
    Delete deliverable_export_preferences for all deliverables owned by user.
    Table has no user_id column, so we resolve via deliverable IDs.
    """
    deliverable_ids = _get_user_deliverable_ids(client, user_id)
    if not deliverable_ids:
        return 0

    count_result = (
        client.table("deliverable_export_preferences")
        .select("*", count="exact")
        .in_("deliverable_id", deliverable_ids)
        .execute()
    )
    deleted_count = count_result.count or 0
    if deleted_count > 0:
        client.table("deliverable_export_preferences").delete().in_("deliverable_id", deliverable_ids).execute()
    return deleted_count


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
                email_suggestion_created=prefs.get("email_suggestion_created", True),
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
            auth.client.table("user_notification_preferences").update(
                {**update_data, "updated_at": "now()"}
            ).eq("user_id", user_id).execute()
        else:
            # Insert new row with defaults + updates
            insert_data = {
                "user_id": user_id,
                "email_deliverable_ready": True,
                "email_deliverable_failed": True,
                "email_suggestion_created": True,
                **update_data
            }
            auth.client.table("user_notification_preferences").insert(insert_data).execute()

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
        # Use service role for consistent counts even when user RLS is read-limited.
        client = get_service_client()

        # Count chat sessions
        sessions = client.table("chat_sessions").select("*", count="exact").eq("user_id", user_id).execute()
        chat_sessions_count = sessions.count or 0

        # Count memories (ADR-059: user_memory, entry-type keys only)
        memories = (
            client.table("user_memory")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .or_(MEMORY_ENTRY_FILTER)
            .execute()
        )
        memories_count = memories.count or 0

        # Count documents
        documents = client.table("filesystem_documents").select("*", count="exact").eq("user_id", user_id).execute()
        documents_count = documents.count or 0

        # Count deliverables (exclude archived)
        deliverables = (
            client.table("deliverables")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .neq("status", "archived")
            .execute()
        )
        deliverables_count = deliverables.count or 0

        # Count deliverable versions (single query instead of N+1).
        deliverable_ids = _get_user_deliverable_ids(client, user_id)
        versions_count = 0
        if deliverable_ids:
            versions = (
                client.table("deliverable_versions")
                .select("*", count="exact")
                .in_("deliverable_id", deliverable_ids)
                .execute()
            )
            versions_count = versions.count or 0

        # Count integrations
        integrations = client.table("platform_connections").select("*", count="exact").eq("user_id", user_id).execute()
        integrations_count = integrations.count or 0

        # Count import jobs
        import_jobs = client.table("integration_import_jobs").select("*", count="exact").eq("user_id", user_id).execute()
        import_jobs_count = import_jobs.count or 0

        # Count export logs
        export_logs = client.table("export_log").select("*", count="exact").eq("user_id", user_id).execute()
        export_logs_count = export_logs.count or 0

        # Count platform content (ADR-072)
        platform_content = client.table("platform_content").select("*", count="exact").eq("user_id", user_id).execute()
        platform_content_count = platform_content.count or 0

        # Count workspaces
        workspaces = client.table("workspaces").select("*", count="exact").eq("owner_id", user_id).execute()
        workspaces_count = workspaces.count or 0

        return DangerZoneStats(
            chat_sessions=chat_sessions_count,
            memories=memories_count,
            documents=documents_count,
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
        client = get_service_client()
        deleted_count = _delete_rows_for_user(client, "chat_sessions", user_id)

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
        client = get_service_client()
        # ADR-059: Delete entry-type keys from user_memory (fact:/instruction:/preference:)
        deleted_count = _delete_rows_for_user(
            client,
            "user_memory",
            user_id,
            or_filter=MEMORY_ENTRY_FILTER,
        )

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
        client = get_service_client()
        deleted_count = _delete_rows_for_user(client, "filesystem_documents", user_id)

        logger.info(f"[ACCOUNT] User {user_id} cleared all documents: {deleted_count}")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted_count} documents",
            deleted={"documents": deleted_count}
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear documents for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear documents")


# =============================================================================
# Tier 2: Category Reset (Grouped Deletions)
# =============================================================================

@router.delete("/account/content")
async def clear_all_content(auth: UserClient) -> OperationResult:
    """
    Delete content-generation artifacts and deliverables.
    Keeps context sources and account-level settings intact.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        # Deliverable-related planning and execution traces.
        deleted["deliverable_proposals"] = _delete_rows_for_user(client, "deliverable_proposals", user_id)
        deleted["user_interaction_patterns"] = _delete_rows_for_user(client, "user_interaction_patterns", user_id)
        deleted["event_trigger_log"] = _delete_rows_for_user(client, "event_trigger_log", user_id)
        deleted["trigger_event_log"] = _delete_rows_for_user(client, "trigger_event_log", user_id, optional=True)

        # Deliverables cascade to versions + export preferences + delivery logs.
        deleted["deliverables"] = _delete_rows_for_user(client, "deliverables", user_id)

        logger.info(f"[ACCOUNT] User {user_id} cleared all content: {deleted}")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted['deliverables']} deliverables and related content history",
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear content for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear content")


@router.delete("/account/context")
async def clear_all_context(auth: UserClient) -> OperationResult:
    """
    Delete all context data (memories, documents, chat history, synced content, sync state).
    Removes all learned context about the user.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        deleted["chat_sessions"] = _delete_rows_for_user(client, "chat_sessions", user_id)
        deleted["memories"] = _delete_rows_for_user(client, "user_memory", user_id)
        deleted["documents"] = _delete_rows_for_user(client, "filesystem_documents", user_id)
        deleted["platform_content"] = _delete_rows_for_user(client, "platform_content", user_id)
        # Keep connection objects but reset sync-state metadata to avoid "still synced" mismatches.
        deleted["sync_registry"] = _delete_rows_for_user(client, "sync_registry", user_id)
        deleted["integration_sync_config"] = _delete_rows_for_user(client, "integration_sync_config", user_id)
        deleted["slack_user_cache"] = _delete_rows_for_user(client, "slack_user_cache", user_id, optional=True)

        logger.info(f"[ACCOUNT] User {user_id} cleared all context: {deleted}")

        return OperationResult(
            success=True,
            message=(
                f"Cleared {deleted['memories']} memories, {deleted['documents']} documents, "
                f"{deleted['chat_sessions']} chats, and {deleted['platform_content']} synced items"
            ),
            deleted=deleted
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear context for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear context")


@router.delete("/account/integrations")
async def clear_all_integrations(auth: UserClient) -> OperationResult:
    """
    Disconnect all integrations and clear integration-related state/history.
    This includes synced platform content and sync metadata.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        deleted["export_logs"] = _delete_rows_for_user(client, "export_log", user_id)
        deleted["integration_import_jobs"] = _delete_rows_for_user(client, "integration_import_jobs", user_id)
        deleted["sync_registry"] = _delete_rows_for_user(client, "sync_registry", user_id)
        deleted["integration_sync_config"] = _delete_rows_for_user(client, "integration_sync_config", user_id)
        deleted["platform_content"] = _delete_rows_for_user(client, "platform_content", user_id)
        deleted["slack_user_cache"] = _delete_rows_for_user(client, "slack_user_cache", user_id, optional=True)
        deleted["export_preferences"] = _delete_export_preferences_for_user(client, user_id)
        deleted["platform_connections"] = _delete_rows_for_user(client, "platform_connections", user_id)

        logger.info(f"[ACCOUNT] User {user_id} cleared all integrations: {deleted}")

        return OperationResult(
            success=True,
            message=(
                f"Disconnected {deleted['platform_connections']} integrations and "
                f"cleared integration sync/history data"
            ),
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
    Full account reset: delete all user-scoped product data, keep auth account active.
    Recreates a default workspace so the user can continue immediately.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        for table in FULL_RESET_USER_TABLES:
            deleted[table] = _delete_rows_for_user(client, table, user_id)
        for table in OPTIONAL_USER_TABLES:
            deleted[table] = _delete_rows_for_user(client, table, user_id, optional=True)
        for table in MCP_OAUTH_TABLES:
            deleted[table] = _delete_rows_for_user(client, table, user_id, optional=True)

        # Workspaces are retained for account continuity, but reset to a single default.
        deleted["workspaces"] = _delete_rows_for_user(
            client, "workspaces", user_id, user_column="owner_id"
        )
        client.table("workspaces").insert({
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
    Permanently deactivate account and delete auth identity.
    Auth deletion cascades all FK-linked user data.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        service_client = get_service_client()

        # Delete auth identity first. This must succeed; otherwise deactivate fails.
        try:
            service_client.auth.admin.delete_user(user_id)
            deleted["auth_user"] = 1
        except Exception as auth_error:
            logger.error(f"[ACCOUNT] Failed to delete auth user {user_id}: {auth_error}")
            raise HTTPException(status_code=500, detail="Failed to deactivate account")

        # Best-effort cleanup for token tables that don't FK to auth.users.
        for table in MCP_OAUTH_TABLES:
            deleted[table] = _delete_rows_for_user(
                service_client, table, user_id, optional=True
            )

        logger.info(f"[ACCOUNT] User {user_id} deactivated account: {deleted}")

        return OperationResult(
            success=True,
            message="Account deactivated. All data has been deleted.",
            deleted=deleted
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to deactivate account for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate account")
