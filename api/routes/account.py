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
    WorkspaceResolutionError,
    _collect_blob_shas,
    _delete_rows,
    _delete_workspace_files,
    _delete_workspace_blobs,
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
    tasks: int
    chat_sessions: int
    platform_connections: int
    # `agents` + `agent_runs` counts REMOVED 2026-08-26 (migration 248 drops
    # both tables). `work_history_files` replaces `agent_runs` as the L1 card's
    # number BECAUSE THE CARD IS GATED ON IT: the old gate was
    # `agent_runs === 0`, which had been permanently true, so "Clear Work
    # History" was a button nobody could press. This counts what L1 actually
    # deletes — the dated report output folders and per-run logs.
    work_history_files: int
    # ADR-194 Reviewer queue — pending proposals the user has in flight.
    # Surfaced so Clear Workspace / Full Reset confirmation copy can tell
    # the user what will be discarded.
    action_proposals: int


class OperationResult(BaseModel):
    """Result of a purge operation."""
    success: bool
    message: str
    deleted: dict


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


def _resolve_or_deny(user_id: str, workspace_id: Optional[str] = None) -> Optional[str]:
    """Resolve the workspace for a DESTRUCTIVE act, or refuse the act.

    `None` legitimately means "this user has no workspace" (N=1) and stays
    allowed. A resolution FAILURE is not that — it used to collapse into the
    same None, which let the authority gate wave the act through while the
    delete scope silently narrowed to `user_id`. Refuse instead: an act that
    destroys every member's work may not be authorized by an error.
    """
    try:
        # ADR-548 D8: pass the REQUEST BINDING. The contextvar does not reach
        # an async handler, so omitting it silently targets the caller's own
        # workspace while the authority gate + pane header name the pinned one.
        return resolve_purge_workspace(user_id, workspace_id)
    except WorkspaceResolutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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


# _user_agent_ids DELETED 2026-08-26 (migration 248 drops the `agents` and
# `agent_runs` tables it scoped). See the run-count helpers below.

# ADR-425 §2 (2026-08-20) — `_count_workspace_paths` and
# `_delete_workspace_file_versions_by_path` are DELETED with the L3 platform
# disconnect that was their only caller. Both existed to count/wipe
# /workspace/context/{slack,notion,github}/, a path with zero writers (0 rows
# in prod). Connector raw lands in inbound/ and is deliberately KEPT on
# disconnect (ADR-582 D2), so nothing replaces them.


# _count_user_agent_runs / _delete_user_agent_runs DELETED 2026-08-26.
# Both walked `agents` -> `agent_runs`, the retired model's tables, which
# migration 248 drops. They already short-circuited to 0 on the empty
# tables, so the L1 "Clear Work History" card reported "0 run records" and
# the purge issued zero writes. A purge must cover a table regardless of
# row count — but not a table that no longer exists.

# ADR-489 D5: the notification-preference routes are DELETED — the one prefs
# store is member_state['notification_prefs'] (GET/PUT /api/member-state/
# notification_prefs), per (workspace, principal). The
# user_notification_preferences table dropped in migration 223.

# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/account/danger-zone/stats")
async def get_danger_zone_stats(auth: UserClient) -> DangerZoneStats:
    """Get counts of all user data for the Account tab."""
    user_id = auth.user_id
    try:
        client = get_service_client()

        # ADR-501: the stats PREVIEW must count what the workspace-scoped
        # purges (ADR-476) will actually delete — workspace content counts by
        # workspace, with user_id as the N=1 fallback (_purge_scope). Account
        # objects (platform_connections, ADR-425) stay user-keyed.
        # Read-only preview: a resolution failure degrades to user_id scoping
        # rather than 500ing the pane. Only the DESTRUCTIVE paths below treat a
        # failure as a denial.
        try:
            # ADR-548 D8 — the preview must count the workspace the purge will
            # actually act on, binding included, or the numbers describe a
            # different workspace than the one the button clears.
            ws = resolve_purge_workspace(user_id, getattr(auth, "workspace_id", None))
        except WorkspaceResolutionError:
            ws = None

        def _count_ws(table: str, *, optional: bool = False) -> int:
            try:
                result = (
                    _purge_scope(
                        client.table(table).select("*", count="exact"), user_id, ws
                    ).execute()
                )
                return result.count or 0
            except Exception:
                if optional:
                    return 0
                raise

        workspace_files = _count_ws("workspace_files")
        tasks = _count_ws("tasks")
        chat_sessions = _count_ws("chat_sessions")
        platform_connections = _count_rows(client, "platform_connections", user_id)

        # What L1 actually clears — the same three path patterns
        # `clear_work_history` deletes. Counted, not guessed: the card's
        # number and its enabled/disabled state must describe one thing.
        # `_count_workspace_pattern` is the SAME helper `_delete_workspace_pattern`
        # counts with — reused rather than re-spelled, so the number on the card
        # and the number the delete reports can never disagree.
        work_history_files = sum(
            _count_workspace_pattern(client, user_id, pattern, ws)
            for pattern in (
                "/workspace/operation/reports/%/%/%",
                "/workspace/operation/reports/%/_run_log.md",
                "/workspace/operation/operations/%/_run_log.md",
            )
        )

        # ADR-194 Reviewer queue — in-flight proposals
        action_proposals = _count_ws("action_proposals", optional=True)

        return DangerZoneStats(
            workspace_files=workspace_files,
            work_history_files=work_history_files,
            tasks=tasks,
            chat_sessions=chat_sessions,
            platform_connections=platform_connections,
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
    ws = _resolve_or_deny(user_id, getattr(auth, "workspace_id", None))
    _require_workspace_clear_authority(user_id, ws)

    try:
        client = get_service_client()

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
                f"Cleared work history: {deleted['report_outputs']} output files, "
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
    - export_log
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
    - member_state notification_prefs (ADR-489 D5 — rides the member_state row)
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
    _require_workspace_clear_authority(user_id, _resolve_or_deny(user_id, getattr(auth, "workspace_id", None)))

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


# ADR-425 §2 + ADR-582 D2 (2026-08-20) — the bulk `DELETE /account/integrations`
# is DELETED, along with its Disconnect Platforms card.
#
#   - ADR-425 §2: "There is no shared 'workspace connections' concept for
#     humans." A credential is an ACCOUNT object, and each connector feature
#     owns its own teardown — a second bulk path was always a duplicate.
#   - ADR-582 D2 SUPERSEDED its teardown model: disconnect deletes the
#     connection row and deliberately KEEPS the landed raw ("cited raw stays
#     as evidence"). This endpoint implemented the ADR-158 wipe-the-context
#     model that D2 replaced.
#   - Its file half targeted /workspace/context/{slack,notion,github}/ — ZERO
#     writers in the API, 0 rows in prod. Connector raw lands in inbound/.
#   - Its UI promised "Pause platform-bot agents"; this handler's own
#     docstring said "no bot to pause".
#
# The singular path is DELETE /integrations/{provider} (routes/integrations.py).
# sync_registry / export_log / integration_sync_config were all 0 rows in prod
# and the OAuth path already cleans sync_registry per platform, so the removal
# orphans nothing.

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
      - Task state: tasks.
      - Interaction: chat_sessions (cascades session_messages), activity_log,
        notifications, execution_events (ADR-291 cost ledger),
        wake_queue (ADR-298 transient wake compute — no auth cascade).
      - Integrations: platform_connections, sync_registry, integration_sync_config,
        export_log, destination_delivery_log, event_trigger_log.
      - Uploads: filesystem_documents (cascades filesystem_chunks).
      - MCP: mcp_oauth_codes / _access_tokens / _refresh_tokens.
      - Prefs: member_state (notification_prefs + shell state — ADR-489 D5).
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
            # "agents" LEFT this list — migration 248 drops the table.
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
        ]
        for table in tables:
            deleted[table] = _delete_rows(client, table, user_id, optional=True)

        # MCP OAuth tables
        for table in ("mcp_oauth_codes", "mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
            deleted[table] = _delete_rows(client, table, user_id, optional=True)

        # Reset workspace row to default
        from services.supabase import DEFAULT_WORKSPACE_NAME
        deleted["workspaces"] = _delete_rows(client, "workspaces", user_id, user_column="owner_id")
        client.table("workspaces").insert({
            "name": DEFAULT_WORKSPACE_NAME,
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
        # ADR-561: collect the cited content BEFORE the revision chain goes —
        # the revisions are the only thing that names the blob. Without this the
        # bucket objects survive account deletion unreachably, and the response
        # message below ("all data has been deleted") would be false.
        blob_shas = _collect_blob_shas(service_client, user_id)
        deleted["workspace_file_versions"] = _delete_rows(service_client, "workspace_file_versions", user_id, optional=True)
        deleted["workspace_files"] = _delete_workspace_files(service_client, user_id)
        # ADR-561: the blob rows + their bucket objects, now that no revision cites
        # them. Best-effort per blob (the helper swallows individual failures), so a
        # storage hiccup leaves collectable rows rather than aborting the deletion.
        deleted["workspace_blobs"] = _delete_workspace_blobs(
            service_client, user_id, blob_shas
        )
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
            # ADR-561: names what was removed rather than asserting totality.
            # Blob collection is best-effort per object, so "all data" was a
            # claim this path could not keep.
            message=(
                "Account deleted. Your workspace files, their revision history, "
                "and your account record have been removed."
            ),
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
