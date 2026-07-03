"""
YARNNN Unified Scheduler — ADR-141 + ADR-164 + ADR-231 Phase 3.3

Layer 1 (this file — pure dispatcher, zero LLM cost):
- Walks `services.scheduling.get_due_declarations(client)` for due recurrence
  declarations across all users.
- For each due declaration: atomic CAS claim via
  `services.scheduling.claim_task_run`, then submit wake proposal via
  `services.wake_sources.cron_tick.dispatch_recurrence(...)` (ADR-296 v2 D1).
- Post-dispatch: `services.scheduling.record_task_run` writes last_run_at +
  recomputes next_run_at into the thin `tasks` index.
- Substrate-event walk: after recurrence dispatch, walks each active user's
  `/workspace/_hooks.yaml` against recent `workspace_file_versions` via
  `services.wake_sources.substrate_event.walk_hooks(...)`.

Layer 2 (services.wake + wake_sources — singular invocation gateway):
- The wake gateway (`submit_wake_proposal`) is the ONLY entry to the
  Reviewer's invocation surface. Five wake sources contribute proposals
  to one evaluation funnel; the Reviewer fires only on escalate.

Layer 3 (yarnnn.py — operator-present only):
- Chat mode with primitives. YARNNN is the single intelligence layer
  (ADR-156, ADR-189). Memory writes via `WriteFile(scope="workspace",
  path="system/notes.md", content=..., mode="append")` in-session per
  ADR-156 + ADR-235.

Cron: every 5 minutes via Render. `schedule: "*/5 * * * *"`. The scheduler
is fully stateless across ticks; each invocation is a fresh DB connection.

ADR-231 Phase 3.3 changes:
- DELETED: `get_due_tasks(supabase_client)` slug-keyed query against `tasks` rows.
- DELETED: `execute_due_tasks(...)` slug delegation to `task_pipeline.execute_task`.
- The scheduler now walks YAML declarations via the new scheduling module.
- The `tasks` table survives as a thin scheduling index per ADR-231 D4 Path B —
  `next_run_at` / `last_run_at` / CAS coordination only.

Back-office recurrences (outcome-reconciliation, proposal-cleanup,
reviewer-calibration, freddie-reflection, narrative-digest) dispatch through
the same `dispatch(decl)` path via the MAINTENANCE branch reading `executor:`
from the YAML. Workspace Cleanup and Agent Hygiene removed — neither had a
creation trigger and no ephemeral files accumulate in prod (audited 2026-05-02).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sentry_sdk
from datetime import datetime, timedelta, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Observability — ADR-250 Phase 1
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "production"),
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    logger.info("[SCHEDULER] Sentry initialized")


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
    """Find due recurrences and dispatch each one.

    Per ADR-261 D3 + ADR-296 v2 D1, this walks ``/workspace/_recurrences.yaml``
    for each user with due rows and submits wake proposals via the
    cron-tick wake source: ``wake_sources.cron_tick.dispatch_recurrence``.

      1. ``get_due_recurrences`` queries the thin `tasks` index for due
         rows AND re-reads each user's _recurrences.yaml.
      2. For each due (user_id, recurrence) pair: CAS claim against the
         index, then ``dispatch_recurrence(supabase, user_id, recurrence)``
         submits a wake proposal to the singular funnel. The funnel
         decides escalate (Reviewer's full cycle), mechanical (deterministic
         primitive), or skip (kernel gate failed).
      3. Post-dispatch, ``record_task_run`` writes last_run_at +
         recomputed next_run_at into the index.

    Returns (found, succeeded, failed).
    """
    from services.scheduling import (
        claim_task_run,
        get_due_recurrences,
        record_task_run,
    )
    # ADR-296 v2 D1: cron-tick wake source routes through the singular
    # wake gateway. The scheduler is no longer the dispatch caller — it
    # is the cron-tick wake source's walker.
    from services.wake_sources.cron_tick import dispatch_recurrence

    now = datetime.now(timezone.utc)
    pairs = await get_due_recurrences(supabase_client, now=now)
    found = len(pairs)
    if found == 0:
        return 0, 0, 0

    succeeded = 0
    failed = 0

    for user_id, recurrence in pairs:
        # CAS claim — read current next_run_at, atomically bump to +2h
        # sentinel. Concurrent scheduler instances skip the bumped row.
        try:
            row = (
                supabase_client.table("tasks")
                .select("next_run_at")
                .eq("user_id", user_id)
                .eq("slug", recurrence.slug)
                .limit(1)
                .execute()
            )
            original_next_run = (
                row.data[0]["next_run_at"] if row.data else None
            )
        except Exception as e:
            logger.warning(
                "[SCHED] could not read baseline next_run_at for %s/%s: %s",
                user_id[:8], recurrence.slug, e,
            )
            failed += 1
            continue

        if not claim_task_run(
            supabase_client, user_id, recurrence.slug, original_next_run
        ):
            logger.info(
                "[SCHED] %s/%s already claimed by another instance; skipping",
                user_id[:8], recurrence.slug,
            )
            continue

        result: dict = {}
        try:
            # ADR-296 v2 D1: cron-tick wake source submits a wake proposal
            # to the singular funnel. The recurrence's `mode` field
            # (judgment | mechanical) determines whether the wake escalates
            # to the Reviewer or bypasses to deterministic primitive
            # execution. Both flow through wake.submit_wake_proposal().
            result = await dispatch_recurrence(
                supabase_client, user_id, recurrence,
            )
            if result.get("success"):
                succeeded += 1
                logger.info(
                    "[SCHED] ✓ %s/%s: %s",
                    user_id[:8], recurrence.slug,
                    result.get("message", "ok"),
                )
            else:
                failed += 1
                logger.warning(
                    "[SCHED] ✗ %s/%s: %s",
                    user_id[:8], recurrence.slug,
                    result.get("message", "?"),
                )
        except Exception as e:
            failed += 1
            logger.exception(
                "[SCHED] dispatch raised for %s/%s: %s",
                user_id[:8], recurrence.slug, e,
            )
        finally:
            # Always advance next_run_at — clears the sentinel even on
            # failure so reactive recurrences don't get stuck. Cold-start
            # ordering fix: pass result.error_reason so record_task_run
            # can preserve activation-flag arming when capability_missing
            # blocked an activation fire (per ADR-272 follow-up).
            try:
                record_task_run(
                    supabase_client, user_id, recurrence,
                    last_run_at=datetime.now(timezone.utc),
                    error_reason=result.get("error_reason"),
                )
            except Exception as e:
                logger.warning(
                    "[SCHED] record_task_run failed for %s/%s: %s",
                    user_id[:8], recurrence.slug, e,
                )

    return found, succeeded, failed


# ---------------------------------------------------------------------------
# ADR-260 D4: cron-heartbeat walker DELETED.
#
# Previously: `_fire_cron_heartbeats` walked active users' `_autonomy.yaml`
# `heartbeat_triggers::cron:` entries and fired the Reviewer's heartbeat_turn
# asynchronously when due. This was the second leg of ADR-253 D5 (cron-fired
# heartbeats; the first leg fired heartbeats after substrate-change events
# via `_maybe_fire_reviewer_heartbeat`).
#
# Both legs collapse under ADR-260 D2's three-trigger model: cron wake-ups
# now fire the `scheduled` trigger via the recurrence walker
# (`dispatch_due_invocations`); substrate-change continuation is the natural
# shape of the Reviewer's real-time tool-use loop, not a separate trigger.
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

    Back-office recurrences materialize on trigger (platform connect, first
    proposal) and dispatch through the standard YAML walker path.
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
    # Include any user with a platform connection OR a tasks index row so that
    # users running programs without platform OAuth (e.g. alpha-trader) still
    # receive a heartbeat and the Settings > System panel shows activity.
    # -------------------------------------------------------------------------
    try:
        conn_result = supabase.table("platform_connections").select("user_id").eq(
            "status", "active"
        ).execute()
        platform_user_ids = {row["user_id"] for row in (conn_result.data or [])}
    except Exception:
        platform_user_ids = set()

    try:
        tasks_result = supabase.table("tasks").select("user_id").execute()
        tasks_user_ids = {row["user_id"] for row in (tasks_result.data or [])}
    except Exception:
        tasks_user_ids = set()

    active_user_ids = list(platform_user_ids | tasks_user_ids)

    # -------------------------------------------------------------------------
    # ADR-375 §6 chokepoint #1 — steward-presence gate (the load-bearing
    # Trigger gate). The due-dispatch + substrate-event walker + wake-queue
    # drain + Reviewer-pulse kernel mirrors are ALL the internal steward's
    # machinery. When AGENT_ENABLED is off (interop-first launch), this whole
    # block is skipped: nothing ever wakes the Reviewer.
    #
    # CRITICAL (interop-first-pivot §7 risk 2 / ADR-375 §6): gate the walker
    # AND the drain AS A UNIT. Gating only the drain would leave flagged-off
    # workspaces silently accumulating undrained wake_queue rows.
    #
    # `found/succeeded/failed` are initialized to 0 here so the keeper paths
    # below (the hourly heartbeat + completion log — liveness, NOT steward)
    # stay valid when the steward is off.
    # -------------------------------------------------------------------------
    from services.agent_gating import is_agent_enabled
    found, succeeded, failed = 0, 0, 0

    if is_agent_enabled():
        # ---------------------------------------------------------------------
        # ADR-231 Phase 3.3: dispatch due invocations from YAML declarations
        # (cron-tick wake source per ADR-296 v2 D1)
        # ---------------------------------------------------------------------
        found, succeeded, failed = await dispatch_due_invocations(supabase)
        if found > 0:
            logger.info(f"[SCHED] dispatch complete: {succeeded}/{found} succeeded, {failed} failed")
        else:
            logger.info("[SCHED] no due declarations")

        # ---------------------------------------------------------------------
        # ADR-393: the capture lane — deterministic intake, OUTSIDE the wake
        # funnel. Runs due _captures.yaml declarations (connector captures,
        # ground-truth state mirrors, perception watches, substrate mirrors)
        # deterministically (zero LLM), writing the per-declaration health
        # signal. Sibling maintenance phase to the recurrence dispatch above +
        # the kernel mirrors / wake drain below — captures wake no one.
        #
        # Runs BEFORE the wake drain so a capture makes substrate fresh for the
        # same tick's judgment wakes (a signal-evaluation wake reads the
        # positions/regime the capture just mirrored).
        #
        # ADR-404 D2: the capture lane is DORMANT for the commons-first launch —
        # the drain (and the GC below, which is meaningless without intake) run
        # only when CONNECTOR_CAPTURE_ENABLED is explicitly on. Inner guard, not
        # part of the AGENT_ENABLED gate: captures cut independently of the
        # steward.
        # ---------------------------------------------------------------------
        from services.connector_capture_gating import is_connector_capture_enabled
        capture_lane_on = is_connector_capture_enabled()
        if capture_lane_on:
            try:
                from services.capture.drainer import drain_due_captures
                c_found, c_succeeded, c_failed = await drain_due_captures(supabase)
                if c_found > 0:
                    logger.info(
                        f"[SCHED] captures: {c_succeeded}/{c_found} succeeded, {c_failed} failed"
                    )
            except Exception as exc:
                logger.warning("[SCHED] capture lane raised: %s", exc)

        # ---------------------------------------------------------------------
        # ADR-394 D4 / ADR-401 D4: connector raw-lane GC — evidence-bounded
        # retention. A sibling maintenance step to the capture drain. For each
        # active user, gather the raw paths a derived act cites (GROUP BY over
        # derived_from), then prune connector raw (inbound/{platform}/) that is
        # older than the workspace's retention window AND un-cited (nothing
        # engaged it — presumed noise, ages out at the dial). A CITED raw is
        # evidence in a provenance chain and is never pruned. Unknown citation
        # state (gather returned None) prunes nothing — fail-safe. inbound/mcp/
        # + inbound/web/ are not touched (own governance). Best-effort per user.
        # ADR-404 D2: gated with the capture drain above (same flag).
        # ---------------------------------------------------------------------
        if capture_lane_on:
            try:
                from services.connector_retention import (
                    gather_cited_raw_paths, prune_raw_lane,
                )
                now_iso = now.isoformat()
                gc_pruned_total = 0
                for gc_user_id in active_user_ids:
                    try:
                        cited = await gather_cited_raw_paths(supabase, gc_user_id)
                        res = await prune_raw_lane(
                            supabase, gc_user_id, now_iso, cited_paths=cited,
                        )
                        gc_pruned_total += int(res.get("pruned", 0))
                    except Exception as exc:  # noqa: BLE001 — per-user GC is best-effort
                        logger.warning(
                            "[SCHED] connector raw-lane GC failed for %s: %s",
                            gc_user_id[:8], exc,
                        )
                if gc_pruned_total > 0:
                    logger.info(
                        "[SCHED] connector raw-lane GC pruned %d stale un-cited raw file(s)",
                        gc_pruned_total,
                    )
            except Exception as exc:
                logger.warning("[SCHED] connector raw-lane GC raised: %s", exc)

        # ---------------------------------------------------------------------
        # ADR-296 v2 D1 + D2: substrate-event wake source walker.
        # For each active user, walk /workspace/_hooks.yaml against recent
        # workspace_file_versions revisions. Hook matches submit wake proposals
        # to the funnel. The transition guard in _field_change_matches ensures
        # hooks fire only on the actual transition, not on every preserving write.
        # ---------------------------------------------------------------------
        try:
            from services.wake_sources.substrate_event import walk_hooks
            substrate_event_outcomes_total = 0
            for hook_user_id in active_user_ids:
                try:
                    outcomes = await walk_hooks(supabase, hook_user_id)
                    substrate_event_outcomes_total += len(outcomes)
                except Exception as exc:
                    logger.warning(
                        "[SCHED] substrate-event walk failed for %s: %s",
                        hook_user_id[:8], exc,
                    )
            if substrate_event_outcomes_total > 0:
                logger.info(
                    "[SCHED] substrate-event walker fired %d hook(s) across %d user(s)",
                    substrate_event_outcomes_total, len(active_user_ids),
                )
        except Exception as exc:
            logger.warning("[SCHED] substrate-event walker raised: %s", exc)

        # ---------------------------------------------------------------------
        # ADR-298 Phase 3 — Wake queue drain.
        #
        # Post-cutover, the wake sources (cron-tick + substrate-event) enqueue
        # rows to wake_queue rather than dispatching the Reviewer inline.
        # After walker work, the drainer pulls pending rows per workspace,
        # acquires the single-in-flight lock per ADR-298 D1, and dispatches
        # to the Reviewer-invocation body. Paced lane respects pace cap;
        # live lane drains FIFO. Both share single-in-flight.
        #
        # Stale-lock reclaim happens FIRST so any wake stuck-locked from a
        # crashed prior tick gets reclaimed before this tick attempts drain.
        # ---------------------------------------------------------------------
        try:
            from services.wake_queue import reclaim_stale_locks
            from services.wake_drainer import drain_all_users_with_pending

            reclaimed = reclaim_stale_locks(supabase)
            if reclaimed:
                logger.info(f"[SCHED] reclaimed {reclaimed} stale wake_queue lock(s)")

            drained = await drain_all_users_with_pending(supabase)
            if drained > 0:
                logger.info(f"[SCHED] drained {drained} wake(s) from wake_queue")
        except Exception as exc:
            logger.warning("[SCHED] wake_queue drain raised: %s", exc)

        # ---------------------------------------------------------------------
        # ADR-301 kernel mirrors — Reviewer pulse envelope substrate.
        # Per-tick maintenance phase: project tasks scheduling index + recent
        # execution_events into compact substrate files (_schedule_index.md +
        # _recent_execution.md under /workspace/system/) that the Reviewer
        # reads at every wake. Both mirrors are diff-aware — most ticks write
        # nothing across most workspaces. Closes the schedule-hallucination
        # class documented in docs/evaluations/2026-05-24-045348-reviewer-
        # schedule-self-misdiagnosis/findings.md.
        #
        # Inside the ADR-375 gate: these mirror substrate the Reviewer reads
        # at wake — pointless to maintain when the steward never wakes.
        # ---------------------------------------------------------------------
        try:
            from services.kernel_mirrors import (
                mirror_schedule_index_for_all_users,
                mirror_recent_execution_for_all_users,
                mirror_calibration_for_all_users,
            )
            si_summary = await mirror_schedule_index_for_all_users(supabase)
            re_summary = await mirror_recent_execution_for_all_users(supabase)
            cal_summary = await mirror_calibration_for_all_users(supabase)
            if si_summary["written"] or re_summary["written"] or cal_summary["written"]:
                logger.info(
                    "[SCHED] kernel mirrors: schedule_index wrote %d/%d "
                    "(skip=%d, fail=%d), recent_execution wrote %d/%d "
                    "(skip=%d, fail=%d), calibration wrote %d/%d "
                    "(skip=%d, fail=%d)",
                    si_summary["written"], si_summary["users_processed"],
                    si_summary["skipped"], si_summary["failed"],
                    re_summary["written"], re_summary["users_processed"],
                    re_summary["skipped"], re_summary["failed"],
                    cal_summary["written"], cal_summary["users_processed"],
                    cal_summary["skipped"], cal_summary["failed"],
                )
        except Exception as exc:
            logger.warning("[SCHED] kernel mirrors raised: %s", exc)
    else:
        logger.info("[SCHED] AGENT_ENABLED off — steward block skipped (dispatch/walker/drain/mirrors)")

    # -------------------------------------------------------------------------
    # ADR-260 D4: cron-heartbeat walker deleted. Cron wake-ups fire the
    # `scheduled` trigger via the recurrence walker above
    # (`dispatch_due_invocations`). No second cron use.
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
