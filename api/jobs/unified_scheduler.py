"""
YARNNN Unified Scheduler — ADR-141 + ADR-164 + ADR-231 Phase 3.3

Layer 1 (this file — pure dispatcher, zero LLM cost):
- Walks `services.scheduling.get_due_declarations(client)` for due recurrence
  declarations across all users.
- For each due declaration: atomic CAS claim via
  `services.scheduling.claim_task_run`, then dispatch via
  `services.invocation_dispatcher.dispatch(decl)`.
- Post-dispatch: `services.scheduling.record_task_run` writes last_run_at +
  recomputes next_run_at into the thin `tasks` index.

Layer 2 (services.invocation_dispatcher — Sonnet generation per shape):
- Reads the recurrence YAML, generates output, writes natural-home substrate,
  emits narrative entry. See ADR-231 D2 for the substrate matrix.

Layer 3 (yarnnn.py — operator-present only):
- Chat mode with primitives. YARNNN is the single intelligence layer
  (ADR-156, ADR-189). Memory writes via `UpdateContext(target="memory")`
  in-session per ADR-156.

Cron: every 5 minutes via Render. `schedule: "*/5 * * * *"`. The scheduler
is fully stateless across ticks; each invocation is a fresh DB connection.

ADR-231 Phase 3.3 changes:
- DELETED: `get_due_tasks(supabase_client)` slug-keyed query against `tasks` rows.
- DELETED: `execute_due_tasks(...)` slug delegation to `task_pipeline.execute_task`.
- The scheduler now walks YAML declarations via the new scheduling module.
- The `tasks` table survives as a thin scheduling index per ADR-231 D4 Path B —
  `next_run_at` / `last_run_at` / CAS coordination only.

ADR-164 unchanged: lifecycle hygiene + ephemeral cleanup remain back-office
declarations whose dispatch flows through the same `dispatch(decl)` path
(services.back_office.{agent_hygiene,workspace_cleanup} called via the
MAINTENANCE branch of the dispatcher reading `executor:` from the YAML).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User-email + notification preferences (preserved — used by delivery layer)
# ---------------------------------------------------------------------------


async def get_user_email(supabase_client, user_id: str) -> Optional[str]:
    """Get user's email for notification."""
    try:
        result = supabase_client.auth.admin.get_user_by_id(user_id)
        if result and result.user:
            return result.user.email
    except Exception as e:
        logger.warning(f"Failed to get user email: {e}")
    return None


async def should_send_email(supabase_client, user_id: str, notification_type: str) -> bool:
    """Check if user has email notifications enabled for this type.

    Args:
        supabase_client: Supabase client
        user_id: User ID
        notification_type: 'agent_ready', 'agent_failed', 'suggestion_created'

    Returns:
        True if should send email (defaults to True if no preferences set)
    """
    column_map = {
        "agent_ready": "email_agent_ready",
        "agent_failed": "email_agent_failed",
        "suggestion_created": "email_suggestion_created",
    }
    column = column_map.get(notification_type)
    if not column:
        return True

    try:
        result = supabase_client.rpc(
            "get_notification_preferences",
            {"p_user_id": user_id},
        ).execute()
        if result.data and len(result.data) > 0:
            return result.data[0].get(column, True)
        return True
    except Exception as e:
        logger.warning(f"Failed to check notification preferences for {user_id}: {e}")
        return True


# ---------------------------------------------------------------------------
# Dispatch loop — walks recurrence YAML declarations via the scheduling module
# ---------------------------------------------------------------------------


async def dispatch_due_invocations(supabase_client) -> tuple[int, int, int]:
    """Find due recurrence declarations and dispatch each one.

    Per ADR-231 Phase 3.3, this replaces the old slug-keyed `tasks` table
    delegation to `task_pipeline.execute_task`. The new flow:

      1. `get_due_declarations` queries the thin `tasks` index for due rows
         AND re-parses the YAML at declaration_path for each.
      2. For each due (user_id, decl) pair: CAS claim against the index,
         then `invocation_dispatcher.dispatch(decl)` does the work.
      3. Post-dispatch, `record_task_run` writes last_run_at + recomputed
         next_run_at into the index.

    Returns (found, succeeded, failed).
    """
    from services.scheduling import (
        claim_task_run,
        get_due_declarations,
        record_task_run,
    )
    from services.invocation_dispatcher import dispatch

    now = datetime.now(timezone.utc)
    pairs = await get_due_declarations(supabase_client, now=now)
    found = len(pairs)
    if found == 0:
        return 0, 0, 0

    succeeded = 0
    failed = 0

    for user_id, decl in pairs:
        # CAS claim — read the row's current next_run_at, atomically bump it
        # to a sentinel +2h. Concurrent scheduler instances see the bumped
        # row and skip.
        try:
            row = (
                supabase_client.table("tasks")
                .select("next_run_at")
                .eq("user_id", user_id)
                .eq("slug", decl.slug)
                .limit(1)
                .execute()
            )
            original_next_run = (
                row.data[0]["next_run_at"]
                if row.data
                else None
            )
        except Exception as e:
            logger.warning(
                "[SCHED] could not read baseline next_run_at for %s/%s: %s",
                user_id[:8], decl.slug, e,
            )
            failed += 1
            continue

        if not claim_task_run(supabase_client, user_id, decl.slug, original_next_run):
            logger.info(
                "[SCHED] %s/%s already claimed by another instance; skipping",
                user_id[:8], decl.slug,
            )
            continue

        # Dispatch
        try:
            result = await dispatch(supabase_client, user_id, decl)
            if result.get("success"):
                succeeded += 1
                logger.info("[SCHED] ✓ %s/%s: %s", user_id[:8], decl.slug, result.get("message", "ok"))
            else:
                failed += 1
                logger.warning("[SCHED] ✗ %s/%s: %s", user_id[:8], decl.slug, result.get("message", "?"))
        except Exception as e:
            failed += 1
            logger.exception("[SCHED] dispatch raised for %s/%s: %s", user_id[:8], decl.slug, e)
        finally:
            # Always advance next_run_at — clears the +2h sentinel even on failure,
            # so on-demand/reactive declarations don't get stuck.
            try:
                record_task_run(
                    supabase_client, user_id, decl,
                    last_run_at=datetime.now(timezone.utc),
                )
            except Exception as e:
                logger.warning(
                    "[SCHED] record_task_run failed for %s/%s: %s",
                    user_id[:8], decl.slug, e,
                )

    return found, succeeded, failed


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_unified_scheduler():
    """Scheduler tick — runs every 5 min via Render cron.

    Steps:
      1. Bootstrap Supabase client.
      2. Discover active users (those with platform connections) for heartbeat.
      3. Dispatch due invocations (ADR-231 Phase 3.3 path).
      4. Hourly: write scheduler_heartbeat activity_log entries per active user.
      5. Hourly: orphan-run watchdog — reap stuck `agent_runs` rows.

    The previous hourly back-office-agent-hygiene probe is preserved
    structurally; once Phase 3.5 migrates the hygiene task to a YAML
    declaration, the probe materializes via the same dispatch path
    (no separate code path).
    """
    from supabase import create_client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    now = datetime.now(timezone.utc)
    is_hourly_tick = now.minute < 5
    logger.info(f"[{now.isoformat()}] Starting unified scheduler...")

    # -------------------------------------------------------------------------
    # Discover active users for heartbeat writes.
    # -------------------------------------------------------------------------
    try:
        conn_result = supabase.table("platform_connections").select("user_id").eq(
            "status", "active"
        ).execute()
        active_user_ids = list({row["user_id"] for row in (conn_result.data or [])})
    except Exception:
        active_user_ids = []

    # -------------------------------------------------------------------------
    # ADR-231 Phase 3.3: dispatch due invocations from YAML declarations
    # -------------------------------------------------------------------------
    found, succeeded, failed = await dispatch_due_invocations(supabase)
    if found > 0:
        logger.info(f"[SCHED] dispatch complete: {succeeded}/{found} succeeded, {failed} failed")
    else:
        logger.info("[SCHED] no due declarations")

    # -------------------------------------------------------------------------
    # Hourly: scheduler_heartbeat (ADR-072)
    # -------------------------------------------------------------------------
    if is_hourly_tick:
        try:
            from services.activity_log import write_activity

            heartbeat_summary = f"Scheduler cycle: invocations={succeeded}/{found}"
            heartbeat_metadata = {
                "invocations_due": found,
                "invocations_succeeded": succeeded,
                "invocations_failed": failed,
                "cycle_started_at": now.isoformat(),
                "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
            }
            for hb_user_id in active_user_ids:
                await write_activity(
                    client=supabase,
                    user_id=hb_user_id,
                    event_type="scheduler_heartbeat",
                    summary=heartbeat_summary,
                    metadata=heartbeat_metadata,
                )
        except Exception as e:
            logger.warning(f"[SCHED] heartbeat write failed: {e}")

    # -------------------------------------------------------------------------
    # Every tick: orphan-run watchdog (Obs 07 fix)
    # -------------------------------------------------------------------------
    # Any agent_runs row stuck in status="generating" for >10 minutes is
    # treated as orphaned (Render redeploy mid-stream, OOM kill, upstream
    # API failure that didn't propagate status). Auto-transition to "failed"
    # with a diagnostic message so operators don't see infinite pending runs.
    try:
        stuck_cutoff = (now - timedelta(minutes=10)).isoformat()
        stuck = (
            supabase.table("agent_runs")
            .update({
                "status": "failed",
                "final_content": (
                    "[watchdog] Run orphaned — generating status exceeded "
                    "10 minutes without completion. Likely a deploy/OOM "
                    "interruption or silent upstream failure. Re-trigger "
                    "the recurrence to retry."
                ),
            })
            .eq("status", "generating")
            .lt("created_at", stuck_cutoff)
            .execute()
        )
        stuck_count = len(stuck.data or [])
        if stuck_count > 0:
            logger.warning(f"[WATCHDOG] reaped {stuck_count} orphaned agent_run(s) older than 10 min")
    except Exception as wd_exc:
        logger.warning(f"[WATCHDOG] orphan-run sweep failed: {wd_exc}")

    logger.info(f"Completed: invocations={succeeded}/{found}")


if __name__ == "__main__":
    asyncio.run(run_unified_scheduler())
