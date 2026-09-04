"""
YARNNN Unified Scheduler — the tick (ADR-632: the steward retired; three live
lanes remain, none gated on a steward flag).

Every 5 minutes via Render cron (`schedule: "*/5 * * * *"`), stateless:

  1. Kernel skills mirror (ADR-630) — every workspace, manifest-cheap.
  2. Capture lane (ADR-393) — connector captures due on their declarations;
     behind its own `CAPTURE_LANE_ENABLED` flag.
  3. Strings lane (ADR-569/603) — standing declarations due on their
     schedule, bounded by the pool (ADR-618).
  4. Hourly: a scheduler_heartbeat activity row per active user.

What is GONE (ADR-632): the recurrence dispatch,
the substrate-event hook walker, the wake-queue reclaim + drain, and the
steward's kernel mirrors — the whole steward-gated body. The
strings and capture lanes were NESTED inside that gate; a flag meant for the
steward could switch off the only lane with production tenants (the four-day
`router_disabled` outage class). They now run unconditionally.
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
# User-email lookup (used by the delivery layer + operator-addressed sends).
# Notification-preference gating moved to services/notifications.py reading
# member_state['notification_prefs'] — ADR-489 D5 (the ADR-407 D7 fold).
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


# ---------------------------------------------------------------------------
# Dispatch loop — walks recurrence YAML declarations via the scheduling module
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------


async def run_unified_scheduler():
    """Scheduler tick — runs every 5 min via Render cron.

    Steps:
      1. Bootstrap Supabase client.
      2. Discover active users (those with platform connections) for heartbeat.
      3. Mirror kernel skills; drain the capture lane; drain the strings lane.
      4. Hourly: write scheduler_heartbeat activity_log entries per active user.
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
    # Any user with a platform connection (the retired recurrence index is no
    # longer consulted — ADR-632).
    # -------------------------------------------------------------------------
    try:
        conn_result = supabase.table("platform_connections").select("user_id").eq(
            "status", "active"
        ).execute()
        platform_user_ids = {row["user_id"] for row in (conn_result.data or [])}
    except Exception:
        platform_user_ids = set()

    active_user_ids = list(platform_user_ids)

    # -------------------------------------------------------------------------
    # ADR-630 — kernel skills mirror: every workspace, every tick, manifest-
    # cheap (one small read per workspace when nothing changed).
    # -------------------------------------------------------------------------
    try:
        from services.skills import mirror_kernel_skills_for_all_workspaces
        _sk = mirror_kernel_skills_for_all_workspaces(supabase)
        if _sk.get("written") or _sk.get("failed"):
            logger.info(
                f"[SCHED] kernel skills: {_sk['written']} written across "
                f"{_sk['workspaces']} workspace(s), {_sk['failed']} failed"
            )
    except Exception as exc:
        logger.warning("[SCHED] kernel skills mirror raised: %s", exc)

    # -------------------------------------------------------------------------
    # ADR-393 — the capture lane (its own flag; ADR-632 unwrapped it from the
    # retired steward gate).
    # -------------------------------------------------------------------------
    from services.capture_lane_gating import is_capture_lane_enabled
    if is_capture_lane_enabled():
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
    # ---------------------------------------------------------------------
    # ADR-592 (2026-08-21): the RADAR LANE IS DELETED, with the app.
    #
    # It drained every tick and each sweep was metered judgment spend
    # ("a sweep's derive is metered judgment spend" — the ADR-486 comment
    # this replaces). That is why Radar was deleted outright rather than
    # hidden behind `stage: internal`: an app nobody can reach must not
    # keep spending an operator's balance, and a dormant spend lane is
    # precisely the ambiguity a future session would have to re-derive.
    #
    # The kind='radar' rows in the `tasks` index are inert once this stops
    # claiming them; scheduling.py's radar special-cases went with it.
    # ---------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # ADR-639 — standing work: declarations due on their schedule, bounded by
    # the pool (ADR-618), through the ONE drain loop capture rides too. Zero
    # declarations → one LIKE scan → no-op. Not an app, not an agent — a
    # kernel lane (ADR-639 D4).
    # -------------------------------------------------------------------------
    try:
        from services.standing_work import drain_due_standing_work
        s_found, s_succeeded, s_failed = await drain_due_standing_work(supabase)
        if s_found > 0:
            # ⭐ A FAILING LANE MUST NOT LOG LIKE A HEALTHY ONE (ADR-618's
            # named-but-unassigned gap). This line was INFO regardless of
            # outcome, so "0/1 succeeded, 1 failed" read exactly like a
            # clean tick — and the ONLY declaration in production sat
            # `router_disabled` for four days, every run, in plain sight.
            # The scheduler never had MODEL_ROUTER_ENABLED (the CLAUDE.md
            # §5 env-drift class); the manual /run door is served by the
            # API, which does, so the lane looked alive from the surface.
            # Severity now follows the outcome. The per-run REASON is
            # logged by the drain loop itself, at the failure branch that
            # already holds it — a count alone cannot say WHY.
            level = logger.info if s_failed == 0 else logger.error
            level(
                f"[SCHED] standing work: {s_succeeded}/{s_found} run(s) succeeded, "
                f"{s_failed} failed"
            )
    except Exception as exc:
        logger.warning("[SCHED] standing lane raised: %s", exc)

    # -------------------------------------------------------------------------
    # Hourly: scheduler_heartbeat (ADR-072)
    # -------------------------------------------------------------------------
    if is_hourly_tick:
        try:
            from services.activity_log import write_activity

            heartbeat_summary = "Scheduler cycle"
            heartbeat_metadata = {
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
    # The orphan-run watchdog is DELETED (2026-08-26).
    # -------------------------------------------------------------------------
    # It reaped `agent_runs` rows stuck in status="generating" for >10 min. The
    # ONLY writer of that status was POST /api/agents/{id}/run, deleted with the
    # retired agent model — so it swept for a state nothing can produce, against
    # a table with zero rows, on EVERY 5-minute tick (~8,600 wasted round-trips
    # a month). Its docstring above also claimed "hourly", which it never was.

    logger.info("[SCHED] tick complete")


if __name__ == "__main__":
    asyncio.run(run_unified_scheduler())
