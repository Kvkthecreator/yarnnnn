"""
Account Management Routes — Layered purge + transactional reinit.

Five purge actions arranged in increasing order of destructive scope. Each
preserves the invariants from its layer's contract — see
docs/features/data-privacy.md for the full design (layer taxonomy,
invariants per layer, what gets touched at each layer).

  L1. Clear work history     — purges past run records and task output folders
                                 only. Tasks, agents, identity, accumulated
                                 context, chat sessions all preserved. The
                                 lightest possible "fresh slate" reset.
  L2. Clear workspace        — purges agents/recurrences/workspace_files/activity/chat,
                                 then re-scaffolds via initialize_workspace().
                                 Keeps platform connections.
  L3. Disconnect platforms   — purges sync state + per ADR-158 deletes the three
                                 platform-owned context directories
                                 (/workspace/context/{slack,notion,github}/),
                                 PAUSES the platform-bot agents so reconnect
                                 is a status flip.
  L4. Reset account          — full wipe (all user-scoped tables + workspaces
                                 row), then re-scaffolds via initialize_workspace().
  L5. Deactivate             — permanent account deletion (auth user drop
                                 cascades all data).

Layer invariants — what is NEVER touched by L1:
  * `tasks` table rows (the thin scheduling index per ADR-231 D4)
  * `agents` table rows
  * `chat_sessions` (the user's relationship with TP)
  * `workspace_files` outside per-recurrence report outputs and run logs —
    so `/workspace/_recurrences.yaml`, `/workspace/context/`, `_feedback.md`
    accumulations, and all operator-authored substrate are preserved
  * `activity_log` (ADR-164 already removed task-lifecycle events from this
    table; nothing in there is "work history" anymore)
  * `platform_connections`
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient, get_service_client
# Mechanical DB helpers + the L2 clear-workspace entry point live in
# services.workspace_purge (single home, ADR-209 FK ordering / ADR-298 wake
# purge). Imported back here so L1/L3/L4 keep their single implementation and
# the L2 route delegates rather than inlining the purge sequence.
from services.workspace_purge import (
    _purge_scope,
    resolve_purge_workspace,
    _delete_rows,
    _delete_workspace_files,
    _null_head_version_pointers,
    capture_active_program_slug,
    clear_workspace_for_user,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class DangerZoneStats(BaseModel):
    """Stats for all user data that can be purged."""
    workspace_files: int
    agents: int
    tasks: int
    chat_sessions: int
    platform_connections: int
    # Count of workspace_files under /workspace/context/{slack,notion,github}/
    # (ADR-158: platform-bot owned context). Replaces the old platform_content
    # field which was a dropped table (ADR-153).
    platform_context_files: int
    # ADR-166 / Phase 3: count of past task runs (work history). Sum of
    # `agent_runs` rows. Drives the L1 "Clear Work History" card stats.
    agent_runs: int
    # ADR-194 Reviewer queue — pending proposals the user has in flight.
    # Surfaced so Clear Workspace / Full Reset confirmation copy can tell
    # the user what will be discarded.
    action_proposals: int


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

# _is_missing_relation_error / _delete_rows / _delete_workspace_files /
# _null_head_version_pointers relocated to services.workspace_purge (single
# home for the L2 mechanical purge helpers) and imported above.


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


def _require_workspace_clear_authority(user_id: str, workspace_id: Optional[str]) -> None:
    """Gate the workspace-content purges on owner-grade authority (ADR-476 D2).

    L1/L2 destroy other members' work, so they are not "clear my own rows".
    Owner-default + the extensible `workspace:clear` grant scope — never a role
    enum (ADR-405).

    No workspace resolved → N=1 fallback, where the caller IS the workspace;
    allowed, preserving today's behavior for every single-member operator.
    """
    if not workspace_id:
        return
    from services.principal_grants import has_workspace_clear_authority

    if not has_workspace_clear_authority(user_id, workspace_id):
        raise HTTPException(
            status_code=403,
            detail=(
                "Clearing this workspace's content requires the workspace owner "
                "(or a principal granted `workspace:clear`). This action removes "
                "every member's work, not only your own."
            ),
        )


def _count_workspace_pattern(
    client, user_id: str, like_pattern: str, workspace_id: Optional[str] = None
) -> int:
    """Count workspace_files rows matching an arbitrary SQL LIKE pattern.

    Caller is responsible for the trailing `%` (and any internal `%` for
    cross-segment patterns like `/workspace/operation/reports/%/2026-%`).

    ADR-476 D1: workspace-scoped — work history is workspace content, so the
    count must include every member's outputs, not only the caller's.
    """
    try:
        result = (
            _purge_scope(
                client.table("workspace_files").select("*", count="exact"),
                user_id,
                workspace_id,
            )
            .like("path", like_pattern)
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


# _null_head_version_pointers relocated to services.workspace_purge (imported
# above). Still used by L4/L5 via that import.


def _delete_workspace_file_versions_by_path(client, user_id: str, path_prefix: str) -> int:
    """Delete workspace_file_versions rows under a path prefix. ADR-209 keys
    the revision chain by `(user_id, path)` directly — no FK to workspace_files
    — so path-based scoping is the correct delete criterion. Used by L3
    (platform disconnect) so that disconnecting a platform also wipes the
    Authored Substrate revision chain under the platform-owned context
    directory.
    """
    try:
        count_result = (
            client.table("workspace_file_versions")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .like("path", f"{path_prefix}%")
            .execute()
        )
        count = count_result.count or 0
        if count > 0:
            (
                client.table("workspace_file_versions")
                .delete()
                .eq("user_id", user_id)
                .like("path", f"{path_prefix}%")
                .execute()
            )
        return count
    except Exception as e:
        logger.warning(
            f"[ACCOUNT] workspace_file_versions delete failed (prefix={path_prefix}): {e}"
        )
        return 0


def _delete_workspace_pattern(
    client, user_id: str, like_pattern: str, workspace_id: Optional[str] = None
) -> int:
    """Delete workspace_files rows matching an arbitrary SQL LIKE pattern.

    Two-step (count then delete) so we can return a real count without
    forcing the caller to inspect a delete response shape.

    ADR-476 D1: workspace-scoped.
    """
    try:
        count = _count_workspace_pattern(client, user_id, like_pattern, workspace_id)
        if count > 0:
            (
                _purge_scope(
                    client.table("workspace_files").delete(), user_id, workspace_id
                )
                .like("path", like_pattern)
                .execute()
            )
        return count
    except Exception as e:
        logger.warning(f"[ACCOUNT] workspace_files delete failed (pattern={like_pattern}): {e}")
        return 0


def _user_agent_ids(client, user_id: str, workspace_id: Optional[str] = None) -> list[str]:
    """Return the agent IDs whose runs a purge may reach (scopes agent_runs ops).

    ADR-476 D1: workspace-scoped. `agent_runs` carries only `workspace_id` (no
    `user_id`), and is reached through `agents` — so scoping the agents lookup
    to the user left every other member's runs unreachable by L1.
    """
    try:
        result = _purge_scope(
            client.table("agents").select("id"), user_id, workspace_id
        ).execute()
        return [r["id"] for r in (result.data or [])]
    except Exception:
        return []


def _count_user_agent_runs(client, user_id: str, workspace_id: Optional[str] = None) -> int:
    """Count agent_runs rows in scope (via agent_id → agents). ADR-476 D1."""
    agent_ids = _user_agent_ids(client, user_id, workspace_id)
    if not agent_ids:
        return 0
    try:
        result = (
            client.table("agent_runs")
            .select("*", count="exact")
            .in_("agent_id", agent_ids)
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def _delete_user_agent_runs(client, user_id: str, workspace_id: Optional[str] = None) -> int:
    """Delete the agent_runs rows in scope. Returns count deleted. ADR-476 D1."""
    agent_ids = _user_agent_ids(client, user_id, workspace_id)
    if not agent_ids:
        return 0
    try:
        count = _count_user_agent_runs(client, user_id, workspace_id)
        if count > 0:
            (
                client.table("agent_runs")
                .delete()
                .in_("agent_id", agent_ids)
                .execute()
            )
        return count
    except Exception as e:
        logger.warning(f"[ACCOUNT] agent_runs delete failed for {user_id}: {e}")
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
        tasks = _count_rows(client, "tasks", user_id)
        chat_sessions = _count_rows(client, "chat_sessions", user_id)
        platform_connections = _count_rows(client, "platform_connections", user_id)

        # ADR-158: count files across all three platform-owned context dirs.
        platform_context_files = sum(
            _count_workspace_paths(client, user_id, prefix)
            for prefix in (
                "/workspace/context/slack/",
                "/workspace/context/notion/",
                "/workspace/context/github/",
            )
        )

        # Phase 3: count of past task runs (drives the L1 "Clear Work History" card).
        agent_runs = _count_user_agent_runs(client, user_id)

        # ADR-194 Reviewer queue — in-flight proposals
        action_proposals = _count_rows(client, "action_proposals", user_id, optional=True)

        return DangerZoneStats(
            workspace_files=workspace_files,
            agents=agents,
            tasks=tasks,
            chat_sessions=chat_sessions,
            platform_connections=platform_connections,
            platform_context_files=platform_context_files,
            agent_runs=agent_runs,
            action_proposals=action_proposals,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to get danger zone stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get account stats")


# =============================================================================
# Purge Actions
# =============================================================================

@router.delete("/account/work-history")
async def clear_work_history(auth: UserClient) -> OperationResult:
    """
    L1 — Clear work history. The lightest possible "fresh slate" reset.

    Purges past run records and recurrence output folders ONLY. Keeps everything
    that defines the workspace (recurrence YAML declarations, agents, identity,
    accumulated context, chat sessions, platform connections). Designed for the
    user who wants to "start fresh" without losing anything they've built up.

    What gets deleted:
      - All `agent_runs` rows belonging to the user (every past invocation
        execution record). FK cascades on these tables also wipe their
        dependents (e.g. `agent_export_preferences` legacy entries).
      - `workspace_files` rows where path matches `/workspace/operation/reports/%/%/%`
        (every dated DELIVERABLE output folder under any recurrence slug —
        ADR-231 D2 natural-home substrate. The three-segment pattern avoids
        the slug-root siblings (`_spec.yaml`, `_feedback.md`, etc.) which
        live at depth 2; output files live at depth 3 under a date folder).
      - `workspace_files` rows where path matches `/workspace/operation/reports/%/_run_log.md`
        and `/workspace/operation/operations/%/_run_log.md` (per-recurrence observation
        logs — re-created on next run).

    What is preserved (the L1 invariant set):
      - Every `tasks` table row (the thin scheduling index post-ADR-231).
      - Every recurrence YAML declaration (`_spec.yaml`, `_recurring.yaml`,
        `_action.yaml`, `_shared/back-office.yaml`).
      - Every `agents` table row.
      - All `chat_sessions` (the user's relationship with YARNNN).
      - All `_feedback.md` and `_intent.md` files (operator-authored guidance).
      - The entire `/workspace/context/` substrate (every accumulated context
        domain — accumulation IS the work, not run history).
      - IDENTITY.md, BRAND.md, MANDATE.md, AUTONOMY.md, AWARENESS.md.
      - All platform connections.

    No reinit needed — the L1 invariants don't include anything this
    endpoint touches. The next scheduled invocation will create a fresh
    dated output folder and a fresh `_run_log.md` automatically.

    See docs/features/data-privacy.md for the full layered model.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    # ADR-476 D1/D2: work history is WORKSPACE content — clearing it destroys
    # every member's run records and outputs, so it is an owner-grade act and
    # is scoped to the workspace rather than to the caller's own rows.
    ws = resolve_purge_workspace(user_id)
    _require_workspace_clear_authority(user_id, ws)

    try:
        client = get_service_client()

        # Run records — every past invocation
        deleted["agent_runs"] = _delete_user_agent_runs(client, user_id, ws)

        # Dated DELIVERABLE output folders under any recurrence slug.
        # Pattern `/workspace/operation/reports/%/%/%` matches anything 3+ segments deep
        # — i.e. dated subfolders like `/workspace/operation/reports/{slug}/{date}/{file}`.
        # Slug-root siblings (`_spec.yaml`, `_feedback.md`, `_intent.md`,
        # `_run_log.md`) live at depth 2 and are explicitly preserved.
        deleted["report_outputs"] = _delete_workspace_pattern(
            client, user_id, "/workspace/operation/reports/%/%/%", ws
        )

        # Per-recurrence observation logs — re-created on next run.
        deleted["report_run_logs"] = _delete_workspace_pattern(
            client, user_id, "/workspace/operation/reports/%/_run_log.md", ws
        )
        deleted["operation_run_logs"] = _delete_workspace_pattern(
            client, user_id, "/workspace/operation/operations/%/_run_log.md", ws
        )

        logger.info(f"[ACCOUNT] User {user_id} cleared work history: {deleted}")

        total = sum(deleted.values())
        report_logs = deleted.get('report_run_logs', 0) + deleted.get('operation_run_logs', 0)
        return OperationResult(
            success=True,
            message=(
                f"Cleared work history: {deleted['agent_runs']} run records, "
                f"{deleted['report_outputs']} output files, "
                f"{report_logs} run logs ({total} items total)"
            ),
            deleted=deleted,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear work history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear work history")


@router.delete("/account/workspace")
async def clear_workspace(auth: UserClient) -> OperationResult:
    """
    L2 — Clear all workspace data, then re-scaffold the workspace to a fresh-account state.

    Purge (current post-flip schema):
    - workspace_file_versions (ADR-209 authored substrate revision chain — MUST
      wipe before workspace_files since revisions reference files)
    - workspace_files (all paths — agents, context, tasks, memory)
    - tasks table (thin scheduling index per ADR-231 D4 Path B)
    - agents table (cascades agent_runs, export_log)
    - action_proposals (ADR-194 Reviewer queue — prior proposals must not
      survive a workspace reset)
    - chat_sessions (cascades session_messages)
    - activity_log (remaining diagnostic events per ADR-164)
    - filesystem_documents (cascades filesystem_chunks via FK)
    - notifications
    - event_trigger_log (ADR-040 cooldown tracking)
    - wake_queue (ADR-298 transient wake compute — no auth cascade, purged explicitly)
    - mcp_oauth_codes/access_tokens/refresh_tokens (MCP sessions)

    Preserved (L2 invariant):
    - platform_connections (user should not re-OAuth on a workspace reset)
    - user_admin_flags (admin identity survives workspace wipe — L4 only)
    - user_notification_preferences (email prefs survive workspace wipe)
    - execution_events (cost ledger — L4 only, never L2; ADR-291)
    - active program (ADR-244 D4): if a program was active before the purge,
      the bundle is re-forked during reinit so the operator lands on the
      same program with bundle templates restored. Operator's authored
      content was wiped with the rest of the workspace, but the program
      *choice* survives. Explicit deactivation (POST /api/programs/deactivate)
      is the operator's lever to drop a program.

    Reinit (transactional — same endpoint, not deferred to next page load):
    - Full workspace initialization via `initialize_workspace()` per ADR-205/206:
      * YARNNN agent row (sole infrastructure scaffolded at signup;
        Production roles lazy-create on first dispatch; platform integrations
        per ADR-207 are capability bundles bound to platform_connections,
        not agent rows)
      * Reviewer substrate at /workspace/persona/ (ADR-194)
      * Kernel-universal _shared/ skeletons ONLY (ADR-286 Single-Writer Per
        Path): PRECEDENT.md + _token_budget.yaml. MANDATE / IDENTITY / BRAND /
        AUTONOMY / _autonomy.yaml are bundle-owned — written by Phase 5
        fork_reference_workspace, NOT by the kernel. A no-program reinit
        therefore lands with those paths ABSENT (honest "unconfigured"
        semantic); the operator authors them through chat. CONVENTIONS.md is
        also program-scoped, not seeded.
      * Memory skeletons under /workspace/system/
      * Workspace narrative session (ADR-219)
      * Bundle re-fork if `active_program_slug` was captured pre-purge (ADR-244 D4)

    Per ADR-206, zero operational tasks are scaffolded at signup. Daily-update
    and back-office tasks materialize on trigger, not at signup. The reinit's
    job is to restore substrate skeletons + the YARNNN heartbeat, not tasks.
    """
    user_id = auth.user_id

    # ADR-476 D2: L2 destroys every member's work in a shared workspace, so it
    # is owner-grade. The scoping itself (D1) lives in the purge service, which
    # resolves the workspace once for the whole sequence.
    _require_workspace_clear_authority(user_id, resolve_purge_workspace(user_id))

    try:
        client = get_service_client()

        # Single L2 implementation: capture active program → purge → reinit +
        # re-fork. The same body serves the service-key harness path (soak/eval
        # clean-slate by user_id). See services/workspace_purge.py.
        summary = await clear_workspace_for_user(client, user_id)
        deleted = summary["deleted"]
        reinit_summary = summary["reinit_summary"]

        program_msg = (
            f" — re-forked program {reinit_summary['activated_program']}"
            if reinit_summary.get("activated_program") else ""
        )
        return OperationResult(
            success=True,
            message=(
                f"Cleared {deleted['workspace_files']} workspace files and "
                f"{deleted['agents']} agents; restored "
                f"{len(reinit_summary.get('agents_created', []))} agents"
                f"{program_msg}"
            ),
            deleted=deleted,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear workspace for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear workspace")


@router.delete("/account/integrations")
async def clear_integrations(auth: UserClient) -> OperationResult:
    """
    Disconnect all platforms and clear platform-owned context.

    Per ADR-158 (platform bot ownership), each platform bot owns one temporal
    context directory (`/workspace/context/{slack,notion,github}/`). This
    endpoint deletes those directories (and their per-source subfolders),
    tears down sync state, and **deletes** the platform-bot agent rows
    (ADR-205: Platform Bots are connection-bound — their agent row lifecycle
    follows platform_connections). Reconnecting a platform lazy-creates a
    fresh bot row via ensure_infrastructure_agent.

    Does NOT delete:
      - YARNNN (thinking_partner row, scaffolded at signup, platform-agnostic)
      - User-authored Agents (origin='user_configured' and similar)
      - Specialist rows that have been lazy-created (they're role-scoped,
        not platform-scoped — they survive platform disconnects)
      - Back-office recurrences (ADR-164) materialized on trigger —
        they are platform-agnostic
      - Canonical context domains under `/workspace/context/` owned by
        Specialists — unchanged by platform disconnect
      - _shared/ context (IDENTITY.md / BRAND.md / AUTONOMY.md / MANDATE.md per ADR-206; CONVENTIONS.md is program-scoped)

    ADR-207 P4a: Platform Bots are NOT agent rows — they're capability bundles
    bound to active platform_connections. Disconnect = delete connection row,
    no bot to pause. Migration 157 dropped stale bot rows once.

    ADR-209: workspace_file_versions rows under platform-owned paths must
    wipe alongside the files (no cascade on that FK).
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        # --- Sync state ---
        deleted["export_log"] = _delete_rows(client, "export_log", user_id)
        deleted["sync_registry"] = _delete_rows(client, "sync_registry", user_id)
        deleted["integration_sync_config"] = _delete_rows(client, "integration_sync_config", user_id)

        # --- Platform-owned context directories (ADR-158) ---
        # Each platform bot (as capability bundle per ADR-207) owns exactly one
        # temporal directory. Deleting here removes all per-source subfolders
        # (channels, pages, repos) and their _tracker.md files in one shot.
        # ADR-209: delete revisions under these paths first (FK order).
        context_files_deleted = 0
        revision_files_deleted = 0
        for platform_dir in ("/workspace/context/slack/", "/workspace/context/notion/", "/workspace/context/github/"):
            revision_files_deleted += _delete_workspace_file_versions_by_path(client, user_id, platform_dir)
            context_files_deleted += _delete_workspace_files(client, user_id, platform_dir)
        deleted["workspace_file_versions_platform"] = revision_files_deleted
        deleted["platform_context_files"] = context_files_deleted

        # --- Platform connections last (other tables may reference them) ---
        deleted["platform_connections"] = _delete_rows(client, "platform_connections", user_id)

        logger.info(f"[ACCOUNT] User {user_id} cleared integrations: {deleted}")

        return OperationResult(
            success=True,
            message=(
                f"Disconnected {deleted['platform_connections']} platforms, "
                f"cleared {context_files_deleted} context files"
            ),
            deleted=deleted,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] Failed to clear integrations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear integrations")


@router.delete("/account/reset")
async def full_account_reset(auth: UserClient) -> OperationResult:
    """
    L4 — Full account reset: delete all user data, keep auth account active.

    Purges every user-scoped table + workspace_files + MCP OAuth state, recreates
    the `workspaces` row, then synchronously re-scaffolds the workspace via
    `initialize_workspace()` so the endpoint returns with the fresh-account
    invariants intact (YARNNN agent row, Reviewer substrate, _shared/ skeletons,
    memory skeletons, workspace narrative session). Per ADR-206, zero operational
    tasks at signup — back-office tasks materialize on trigger. Per ADR-244 D4,
    a captured `prior_program_slug` re-forks the bundle during reinit so the
    operator's program choice survives the reset.

    See `clear_workspace` for the reasoning on why reinit is transactional.

    Current (post-flip) purge set:
      - ADR-209 Authored Substrate: workspace_file_versions (revision chain) +
        workspace_files (content). Revisions delete first — no FK cascade.
      - ADR-194 Reviewer queue: action_proposals. user_admin_flags preserved
        only when operator is a platform admin; L4 deliberately wipes it so
        a reset is a true fresh start.
      - Task / agent state: tasks, agents, agent_runs (cascaded from agents).
      - Interaction: chat_sessions (cascades session_messages), activity_log,
        notifications, execution_events (ADR-291 cost ledger),
        wake_queue (ADR-298 transient wake compute — no auth cascade).
      - Integrations: platform_connections, sync_registry, integration_sync_config,
        export_log, destination_delivery_log, event_trigger_log.
      - Uploads: filesystem_documents (cascades filesystem_chunks).
      - MCP: mcp_oauth_codes / _access_tokens / _refresh_tokens.
      - Prefs: user_notification_preferences.
    """
    user_id = auth.user_id
    deleted: dict[str, int] = {}

    try:
        client = get_service_client()

        # ADR-244 D4: same as L2 — capture the active program slug pre-purge
        # so the reinit can re-fork the bundle. Operator chose Reset, not
        # "Reset and unactivate program"; preservation is the right default.
        # Shared single implementation with L2 (services.workspace_purge).
        prior_program_slug = await capture_active_program_slug(client, user_id)

        # --- Phase 1: Purge ---
        # ADR-209 FK order: workspace_files.head_version_id → workspace_file_versions.id.
        # Null the pointer first, then wipe revisions, then wipe files.
        _null_head_version_pointers(client, user_id)
        deleted["workspace_file_versions"] = _delete_rows(client, "workspace_file_versions", user_id)

        # All workspace files — the primary data store
        deleted["workspace_files"] = _delete_workspace_files(client, user_id)

        # All relational tables (order matters for FK constraints)
        tables = [
            "activity_log",
            "chat_sessions",
            "action_proposals",           # ADR-194 Reviewer queue
            "tasks",
            "agents",                     # cascades agent_runs
            "destination_delivery_log",
            "event_trigger_log",
            "export_log",
            # filesystem_documents dropped (ADR-249) — uploads now in workspace_files
            "integration_sync_config",
            "notifications",
            "platform_connections",
            "sync_registry",
            "execution_events",           # ADR-291 unified cost ledger
            "wake_queue",                 # ADR-298 transient wake compute — no auth cascade, must purge explicitly
            "user_admin_flags",           # ADR-194 v2 Phase 2b admin scope
            "user_notification_preferences",
        ]
        for table in tables:
            deleted[table] = _delete_rows(client, table, user_id, optional=True)

        # MCP OAuth tables
        for table in ("mcp_oauth_codes", "mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
            deleted[table] = _delete_rows(client, table, user_id, optional=True)

        # Reset workspace row to default
        deleted["workspaces"] = _delete_rows(client, "workspaces", user_id, user_column="owner_id")
        client.table("workspaces").insert({
            "name": "My Workspace",
            "owner_id": user_id,
        }).execute()

        logger.info(f"[ACCOUNT] User {user_id} performed full reset: {deleted}")

        # --- Phase 2: Reinit ---
        # Restore the fresh-account invariants. Non-fatal — same rationale as clear_workspace.
        # ADR-244 D4: re-fork the captured program so the operator lands on the same
        # program with bundle templates restored.
        reinit_summary: dict = {}
        try:
            from services.workspace_init import initialize_workspace
            # ADR-414 D4: genesis is pure — the re-fork is the caller's
            # post-genesis act (activation is a hire, even on reinit).
            reinit_summary = await initialize_workspace(client, user_id)
            if prior_program_slug:
                try:
                    from services.programs import fork_reference_workspace
                    fork_summary = await fork_reference_workspace(
                        client, user_id, prior_program_slug
                    )
                    reinit_summary["activated_program"] = prior_program_slug
                    reinit_summary["fork_files_written"] = fork_summary.get(
                        "files_written", []
                    )
                except Exception as fork_err:
                    logger.error(
                        f"[ACCOUNT] Program re-fork after reset failed for "
                        f"{user_id} (program={prior_program_slug}): {fork_err}"
                    )
                    reinit_summary["fork_error"] = str(fork_err)
            logger.info(
                f"[ACCOUNT] User {user_id} reinit after reset: "
                f"{len(reinit_summary.get('workspace_files_seeded', []))} files, "
                f"program={reinit_summary.get('activated_program')}"
            )
        except Exception as reinit_err:
            logger.error(f"[ACCOUNT] Workspace reinit after reset failed for {user_id}: {reinit_err}")

        program_msg = (
            f" — re-forked program {reinit_summary['activated_program']}"
            if reinit_summary.get("activated_program") else ""
        )
        return OperationResult(
            success=True,
            message=(
                f"Account reset complete — workspace re-initialized"
                f"{program_msg}."
            ),
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

        # Best-effort: delete workspace_files + revisions + MCP oauth before auth cascade
        # (ADR-209 revision rows are not FK-cascaded from auth.users — wipe explicitly).
        # Null head_version_id pointers first to avoid the files→versions FK violation.
        _null_head_version_pointers(service_client, user_id)
        deleted["workspace_file_versions"] = _delete_rows(service_client, "workspace_file_versions", user_id, optional=True)
        deleted["workspace_files"] = _delete_workspace_files(service_client, user_id)
        # ADR-298 wake queue has no auth.users FK cascade — wipe before auth delete.
        deleted["wake_queue"] = _delete_rows(service_client, "wake_queue", user_id, optional=True)
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


# =============================================================================
# Email Wire Smoke Test
# =============================================================================
# Self-serve operator health check for the system Resend wire (api/jobs/email.py).
# Bypasses Reviewer + notifications.py + delivery.py + recurrence pipeline so a
# failure here unambiguously isolates to: RESEND_API_KEY misconfigured, Resend
# API outage, or the wire code itself. Useful after env-var rotations, Resend
# plan changes, or any "did the canary email get sent?" investigation that
# wants the Reviewer-shaped variables removed.
#
# Origin: ADR-299 Discovery 4 Path A canary v4 RED — when the Reviewer chose
# stand_down and no email landed, distinguishing "tool not in surface" from
# "wire broken" required an isolation test. See
# docs/evaluations/2026-05-25-042346-adr299-always-surface-resolution/
# for the surrounding diagnostic arc.


class EmailSmokeTestResult(BaseModel):
    """Result of a system Resend wire smoke test."""

    success: bool
    recipient: Optional[str] = None
    message_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/account/test-email")
async def send_test_email_to_operator(auth: UserClient) -> EmailSmokeTestResult:
    """Send a test email to the authenticated operator's account email.

    Direct exercise of the system Resend wire (`jobs.email.send_test_email`)
    with no Reviewer, no notifications routing, no delivery pipeline, no
    recurrence — just: resolve operator's auth email → send → return result
    (including Resend message_id on success).

    Returns 200 with `success=False` and an `error` string when the wire
    fails so the operator can see Resend's error response directly (e.g.,
    `RESEND_API_KEY not configured`, `Resend API error: 422 - ...`).
    Returns 200 with `success=True` + `message_id` on success.
    """
    user_id = auth.user_id
    try:
        from jobs.email import send_test_email
        from jobs.unified_scheduler import get_user_email

        service_client = get_service_client()
        recipient = await get_user_email(service_client, user_id)
        if not recipient:
            return EmailSmokeTestResult(
                success=False,
                error=f"Could not resolve auth email for user {user_id}",
            )

        result = await send_test_email(to=recipient)
        logger.info(
            f"[ACCOUNT] test-email to={recipient} success={result.success} "
            f"message_id={result.message_id} error={result.error}"
        )
        return EmailSmokeTestResult(
            success=result.success,
            recipient=recipient,
            message_id=result.message_id,
            error=result.error,
        )
    except Exception as e:
        logger.error(f"[ACCOUNT] test-email failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Test email failed: {e}")
