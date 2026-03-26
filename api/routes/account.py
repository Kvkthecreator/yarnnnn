"""
Account Management Routes — ADR-122 Phase 5 rewrite

Purge actions are workspace-aware: all deletions include workspace_files,
work_credits alongside relational tables.

Three purge actions:
  1. Clear workspace — agents, projects, outputs, knowledge, activity
  2. Disconnect platforms — connections, sync state, synced content
  3. Reset account — full wipe, recreate default workspace

Plus: deactivate (permanent account deletion).
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
    """Stats for all user data that can be purged."""
    workspace_files: int
    agents: int
    projects: int
    chat_sessions: int
    platform_connections: int
    platform_content: int


class OperationResult(BaseModel):
    """Result of a purge operation."""
    success: bool
    message: str
    deleted: dict


class NotificationPreferences(BaseModel):
    """User notification preferences for email."""
    email_agent_ready: bool = True
    email_agent_failed: bool = True
    email_suggestion_created: bool = True


class NotificationPreferencesUpdate(BaseModel):
    """Partial update for notification preferences."""
    email_agent_ready: Optional[bool] = None
    email_agent_failed: Optional[bool] = None
    email_suggestion_created: Optional[bool] = None


# =============================================================================
# Internal Helpers
# =============================================================================

def _is_missing_relation_error(error: Exception) -> bool:
    message = str(error).lower()
    return "relation" in message and "does not exist" in message


def _delete_rows(client, table: str, user_id: str, *, user_column: str = "user_id", optional: bool = False) -> int:
    """Delete all rows in a user-scoped table. Returns count deleted."""
    try:
        count_result = client.table(table).select("*", count="exact").eq(user_column, user_id).execute()
        count = count_result.count or 0
        if count > 0:
            client.table(table).delete().eq(user_column, user_id).execute()
        return count
    except Exception as e:
        if optional and _is_missing_relation_error(e):
            return 0
        if optional:
            logger.warning(f"[ACCOUNT] Optional delete failed for {table}: {e}")
            return 0
        raise


def _delete_workspace_files(client, user_id: str, path_prefix: str | None = None) -> int:
    """Delete workspace_files rows, optionally filtered by path prefix."""
    try:
        query = client.table("workspace_files").select("*", count="exact").eq("user_id", user_id)
        if path_prefix:
            query = query.like("path", f"{path_prefix}%")
        count_result = query.execute()
        count = count_result.count or 0
        if count > 0:
            dq = client.table("workspace_files").delete().eq("user_id", user_id)
            if path_prefix:
                dq = dq.like("path", f"{path_prefix}%")
            dq.execute()
        return count
    except Exception as e:
        logger.warning(f"[ACCOUNT] workspace_files delete failed (prefix={path_prefix}): {e}")
        return 0


def _count_rows(client, table: str, user_id: str, *, user_column: str = "user_id", optional: bool = False) -> int:
    """Count rows in a user-scoped table."""
    try:
        result = client.table(table).select("*", count="exact").eq(user_column, user_id).execute()
        return result.count or 0
    except Exception:
        if optional:
            return 0
        raise


def _count_workspace_paths(client, user_id: str, path_prefix: str) -> int:
    """Count workspace_files rows matching a path prefix."""
    try:
        result = (
            client.table("workspace_files")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .like("path", f"{path_prefix}%")
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


# =============================================================================
# Notification Preferences
# =============================================================================

@router.get("/account/notification-preferences")
async def get_notification_preferences(auth: UserClient) -> NotificationPreferences:
    """Get user's notification preferences. Returns defaults if none set."""
    try:
        result = auth.client.table("user_notification_preferences").select("*").eq("user_id", auth.user_id).execute()
        if result.data and len(result.data) > 0:
            prefs = result.data[0]
            return NotificationPreferences(
                email_agent_ready=prefs.get("email_agent_ready", True),
                email_agent_failed=prefs.get("email_agent_failed", True),
                email_suggestion_created=prefs.get("email_suggestion_created", True),
            )
        return NotificationPreferences()
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to get notification preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification preferences")


@router.patch("/account/notification-preferences")
async def update_notification_preferences(
    auth: UserClient,
    update: NotificationPreferencesUpdate,
) -> NotificationPreferences:
    """Update user's notification preferences (upsert)."""
    user_id = auth.user_id
    try:
        existing = auth.client.table("user_notification_preferences").select("id").eq("user_id", user_id).execute()
        update_data = {k: v for k, v in update.model_dump().items() if v is not None}
        if not update_data:
            return await get_notification_preferences(auth)

        if existing.data and len(existing.data) > 0:
            auth.client.table("user_notification_preferences").update(
                {**update_data, "updated_at": "now()"}
            ).eq("user_id", user_id).execute()
        else:
            auth.client.table("user_notification_preferences").insert({
                "user_id": user_id,
                "email_agent_ready": True,
                "email_agent_failed": True,
                "email_suggestion_created": True,
                **update_data,
            }).execute()

        return await get_notification_preferences(auth)
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to update notification preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification preferences")


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/account/danger-zone/stats")
async def get_danger_zone_stats(auth: UserClient) -> DangerZoneStats:
    """Get counts of all user data for the Account tab."""
    user_id = auth.user_id
    try:
        client = get_service_client()

        workspace_files = _count_rows(client, "workspace_files", user_id)
        agents = _count_rows(client, "agents", user_id)
        projects = _count_workspace_paths(client, user_id, "/projects/")
        chat_sessions = _count_rows(client, "chat_sessions", user_id)
        platform_connections = _count_rows(client, "platform_connections", user_id)
        platform_content = _count_rows(client, "platform_content", user_id)

        return DangerZoneStats(
            workspace_files=workspace_files,
            agents=agents,
            projects=projects,
            chat_sessions=chat_sessions,
            platform_connections=platform_connections,
            platform_content=platform_content,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to get danger zone stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get account stats")


# =============================================================================
# Purge Actions
# =============================================================================

@router.delete("/account/workspace")
async def clear_workspace(auth: UserClient) -> OperationResult:
    """
    Clear all workspace data: agents, projects, outputs, knowledge, activity.

    Deletes:
    - workspace_files (all paths — agents, projects, knowledge, memory)
    - agents table (cascades agent_runs, export prefs, delivery logs)
    - chat_sessions (cascades session_messages)
    - work_credits, activity_log
    - agent_proposals, agent_context_log
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        # Workspace filesystem — the primary data store
        deleted["workspace_files"] = _delete_workspace_files(client, user_id)

        # Relational tables that reference agents/tasks
        deleted["tasks"] = _delete_rows(client, "tasks", user_id, optional=True)
        deleted["agents"] = _delete_rows(client, "agents", user_id)
        deleted["agent_proposals"] = _delete_rows(client, "agent_proposals", user_id, optional=True)
        deleted["agent_context_log"] = _delete_rows(client, "agent_context_log", user_id, optional=True)
        deleted["work_credits"] = _delete_rows(client, "work_credits", user_id, optional=True)
        deleted["chat_sessions"] = _delete_rows(client, "chat_sessions", user_id)
        deleted["activity_log"] = _delete_rows(client, "activity_log", user_id)
        deleted["user_interaction_patterns"] = _delete_rows(client, "user_interaction_patterns", user_id, optional=True)
        deleted["event_trigger_log"] = _delete_rows(client, "event_trigger_log", user_id, optional=True)
        deleted["trigger_event_log"] = _delete_rows(client, "trigger_event_log", user_id, optional=True)

        logger.info(f"[ACCOUNT] User {user_id} cleared workspace: {deleted}")

        return OperationResult(
            success=True,
            message=f"Cleared {deleted['workspace_files']} workspace files and {deleted['agents']} agents",
            deleted=deleted,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear workspace for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear workspace")


@router.delete("/account/integrations")
async def clear_integrations(auth: UserClient) -> OperationResult:
    """
    Disconnect all platforms and clear sync data.

    Deletes:
    - platform_connections, integration_import_jobs, sync_registry
    - integration_sync_config, platform_content
    - workspace_files under /knowledge/ (synced content)
    - export_log, agent_export_preferences
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        # Sync state
        deleted["export_log"] = _delete_rows(client, "export_log", user_id)
        deleted["integration_import_jobs"] = _delete_rows(client, "integration_import_jobs", user_id)
        deleted["sync_registry"] = _delete_rows(client, "sync_registry", user_id)
        deleted["integration_sync_config"] = _delete_rows(client, "integration_sync_config", user_id)
        deleted["platform_content"] = _delete_rows(client, "platform_content", user_id)
        deleted["slack_user_cache"] = _delete_rows(client, "slack_user_cache", user_id, optional=True)

        # Export preferences (no user_id column — resolve via agent_ids)
        agent_ids = [
            r["id"] for r in
            (client.table("agents").select("id").eq("user_id", user_id).execute().data or [])
        ]
        if agent_ids:
            try:
                client.table("agent_export_preferences").delete().in_("agent_id", agent_ids).execute()
                deleted["agent_export_preferences"] = len(agent_ids)
            except Exception:
                deleted["agent_export_preferences"] = 0

        # Knowledge workspace files (synced platform content)
        deleted["knowledge_files"] = _delete_workspace_files(client, user_id, "/knowledge/")

        # Platform connections last (other tables may reference them)
        deleted["platform_connections"] = _delete_rows(client, "platform_connections", user_id)

        logger.info(f"[ACCOUNT] User {user_id} cleared integrations: {deleted}")

        return OperationResult(
            success=True,
            message=f"Disconnected {deleted['platform_connections']} platforms and cleared sync data",
            deleted=deleted,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear integrations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear integrations")


@router.delete("/account/reset")
async def full_account_reset(auth: UserClient) -> OperationResult:
    """
    Full account reset: delete all user data, keep auth account active.
    Recreates a default workspace.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        # All workspace files — the primary data store
        deleted["workspace_files"] = _delete_workspace_files(client, user_id)

        # All relational tables (order matters for FK constraints)
        tables = [
            "activity_log",
            "chat_sessions",
            "agent_proposals",
            "tasks",
            "agents",
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
            "sync_registry",
            "agent_context_log",
            "user_interaction_patterns",
            "user_memory",
            "user_notification_preferences",
            "user_platform_styles",
            "work_credits",
        ]
        for table in tables:
            deleted[table] = _delete_rows(client, table, user_id, optional=True)

        # Optional tables
        for table in ("trigger_event_log", "slack_user_cache"):
            deleted[table] = _delete_rows(client, table, user_id, optional=True)

        # MCP OAuth tables
        for table in ("mcp_oauth_codes", "mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
            deleted[table] = _delete_rows(client, table, user_id, optional=True)

        # Reset workspace to default
        deleted["workspaces"] = _delete_rows(client, "workspaces", user_id, user_column="owner_id")
        client.table("workspaces").insert({
            "name": "My Workspace",
            "owner_id": user_id,
        }).execute()

        logger.info(f"[ACCOUNT] User {user_id} performed full reset: {deleted}")

        return OperationResult(
            success=True,
            message="Account reset complete. You can start fresh.",
            deleted=deleted,
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

        # Best-effort: delete workspace_files and MCP oauth before auth cascade
        deleted["workspace_files"] = _delete_workspace_files(service_client, user_id)
        for table in ("mcp_oauth_codes", "mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
            deleted[table] = _delete_rows(service_client, table, user_id, optional=True)

        # Delete auth identity — cascades all FK-linked data
        try:
            service_client.auth.admin.delete_user(user_id)
            deleted["auth_user"] = 1
        except Exception as auth_error:
            logger.error(f"[ACCOUNT] Failed to delete auth user {user_id}: {auth_error}")
            raise HTTPException(status_code=500, detail="Failed to deactivate account")

        logger.info(f"[ACCOUNT] User {user_id} deactivated account: {deleted}")

        return OperationResult(
            success=True,
            message="Account deactivated. All data has been deleted.",
            deleted=deleted,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to deactivate account for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate account")
