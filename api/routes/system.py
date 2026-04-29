"""
System routes - Operations status (ADR-073, ADR-141)

Provides operational visibility into background orchestration:
- Platform connection status with per-resource detail from sync_registry
- Background job status from activity_log (task execution + system health)
- Scheduler heartbeat observability

ADR-141/153/156 cleanup: Platform sync cron, memory extraction, session summaries,
Composer heartbeat, and content cleanup are all deleted. The scheduler now only does
task execution, workspace cleanup, and lifecycle hygiene.

Mounted at /api/system
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

from services.supabase import UserClient
from services.platform_limits import get_next_sync_time

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class ResourceSyncStatus(BaseModel):
    """Per-resource sync detail from sync_registry."""
    resource_id: str
    resource_name: Optional[str] = None
    last_synced_at: Optional[str] = None
    item_count: int = 0
    has_cursor: bool = False
    status: str = "unknown"  # fresh, recent, stale, never_synced
    last_error: Optional[str] = None
    last_error_at: Optional[str] = None


class PlatformSyncStatus(BaseModel):
    """Connection status for a single platform."""
    platform: str
    connected: bool
    last_synced_at: Optional[str] = None
    next_sync_at: Optional[str] = None
    source_count: int = 0
    status: str = "unknown"  # healthy, stale, pending, disconnected
    resources: list[ResourceSyncStatus] = []


class BackgroundJobStatus(BaseModel):
    """Status of a background job type."""
    job_type: str
    last_run_at: Optional[str] = None
    last_run_status: str = "unknown"  # success, failed, never_run
    last_run_summary: Optional[str] = None
    items_processed: int = 0
    schedule_description: Optional[str] = None  # ADR-084: when this job is expected to run


class SystemStatusResponse(BaseModel):
    """System operations status overview."""
    platform_sync: list[PlatformSyncStatus]
    background_jobs: list[BackgroundJobStatus]
    tier: str = "free"
    sync_frequency: str = "2x_daily"


# Static schedule descriptions for background jobs
# ADR-141/153/156/164: task_executed events deleted — status sourced from
# tasks.last_run_at + agent_runs. Only scheduler_heartbeat remains in activity_log.
JOB_SCHEDULE_DESCRIPTIONS = {
    "Workspace Cleanup": "Daily (back office task)",
    "Agent Hygiene": "Daily (back office task)",
    "Scheduler Heartbeat": "Hourly",
}



# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(auth: UserClient):
    """
    Get system operations status.

    Returns:
    - Platform sync status per connected platform with per-resource detail
    - Content accumulation counts
    - Background job last-run status
    """
    user_id = auth.user_id
    now = datetime.now(timezone.utc)

    # ─── Tier & Frequency ──────────────────────────────────────────────────────
    from services.platform_limits import TIER_LIMITS

    ws_result = auth.client.table("workspaces").select(
        "subscription_status"
    ).eq("owner_id", user_id).limit(1).execute()
    ws_rows = ws_result.data if ws_result else []
    tier = ws_rows[0].get("subscription_status", "free") if ws_rows else "free"

    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    sync_frequency = limits.sync_frequency

    # ADR-084: Freshness thresholds for resource status badges
    freshness_hours = {
        "1x_daily": 24,
        "2x_daily": 12,
        "4x_daily": 6,
        "hourly": 1,
    }
    hours_between = freshness_hours.get(sync_frequency, 12)

    # ─── User Timezone (ADR-206: from /workspace/context/_shared/IDENTITY.md) ───
    user_tz_str = "UTC"
    try:
        from services.workspace import UserMemory
        from services.workspace_paths import SHARED_IDENTITY_PATH
        um = UserMemory(auth.client, user_id)
        profile = UserMemory._parse_memory_md(um.read_sync(SHARED_IDENTITY_PATH))
        user_tz_str = profile.get("timezone") or "UTC"
    except Exception as e:
        logger.debug(f"Failed to fetch user timezone: {e}")

    # ─── Platform Connections (status + landscape only; freshness from sync_registry) ──
    platforms_result = auth.client.table("platform_connections").select(
        "platform, status, landscape"
    ).eq("user_id", user_id).execute()
    connection_rows = platforms_result.data or []

    # ─── Sync Registry (single query, partition by platform) ───────────────────
    registry_result = auth.client.table("sync_registry").select(
        "platform, resource_id, resource_name, last_synced_at, platform_cursor, item_count, last_error, last_error_at"
    ).eq("user_id", user_id).execute()

    # Group by platform
    registry_by_platform: dict[str, list[dict]] = {}
    for row in (registry_result.data or []):
        p = row["platform"]
        registry_by_platform.setdefault(p, []).append(row)

    # ─── Build Platform Connection Status ────────────────────────────────────────
    platform_sync = []
    all_platforms = ["slack", "notion"]  # ADR-131: Gmail/Calendar sunset

    def _get_active_connection(logical_platform: str) -> Optional[dict]:
        candidates = (logical_platform,)
        for candidate in candidates:
            row = next((r for r in connection_rows if r.get("platform") == candidate), None)
            if row and row.get("status") == "active":
                return row
        return None

    for platform in all_platforms:
        p_data = _get_active_connection(platform)
        if p_data:
            landscape = p_data.get("landscape", {}) or {}
            selected_sources = landscape.get("selected_sources", [])

            # Build per-resource status from sync_registry
            registry_rows = registry_by_platform.get(platform, [])
            resources = []
            latest_sync_dt = None

            for row in registry_rows:
                r_last_synced = row.get("last_synced_at")
                r_status = "never_synced"
                if r_last_synced:
                    try:
                        r_dt = datetime.fromisoformat(r_last_synced.replace("Z", "+00:00"))
                        hours_since = (now - r_dt).total_seconds() / 3600
                        if hours_since <= hours_between:
                            r_status = "fresh"
                        elif hours_since <= hours_between * 2:
                            r_status = "recent"
                        else:
                            r_status = "stale"

                        if latest_sync_dt is None or r_dt > latest_sync_dt:
                            latest_sync_dt = r_dt
                    except (ValueError, TypeError):
                        r_status = "unknown"

                resources.append(ResourceSyncStatus(
                    resource_id=row["resource_id"],
                    resource_name=row.get("resource_name"),
                    last_synced_at=r_last_synced,
                    item_count=row.get("item_count", 0),
                    has_cursor=bool(row.get("platform_cursor")),
                    status=r_status,
                    last_error=row.get("last_error"),
                    last_error_at=row.get("last_error_at"),
                ))

            # Derive platform-level status from resources
            if resources:
                stale_count = sum(1 for r in resources if r.status == "stale")
                never_count = sum(1 for r in resources if r.status == "never_synced")
                if stale_count > 0:
                    platform_status = "stale"
                elif never_count == len(resources):
                    platform_status = "pending"
                else:
                    platform_status = "healthy"
            else:
                # No sync_registry entries — platform connected but never synced
                platform_status = "pending"

            # Compute last_synced_at and next_sync_at
            # ADR-084: Use schedule-aware calculation instead of last_sync + hours
            last_synced_str = latest_sync_dt.isoformat() if latest_sync_dt else None
            next_sync = get_next_sync_time(sync_frequency, user_tz_str)

            platform_sync.append(PlatformSyncStatus(
                platform=platform,
                connected=True,
                last_synced_at=last_synced_str,
                next_sync_at=next_sync,
                source_count=len(selected_sources),
                status=platform_status,
                resources=resources,
            ))
        else:
            platform_sync.append(PlatformSyncStatus(
                platform=platform,
                connected=False,
                status="disconnected",
            ))

    # ─── Background Jobs Status ───────────────────────────────────────────────
    # ADR-231 D2: back-office collapses to a single shared audit log at
    # /workspace/_shared/back-office-audit.md. Status comes from tasks.last_run_at
    # (the scheduling index, scheduler-maintained) + the latest audit-log entry
    # for the slug. The per-task /tasks/{slug}/outputs/{date}/manifest.json layout
    # was retired by ADR-231 D2; ALL back-office firings append to one audit file.
    background_jobs = []

    back_office_task_slugs = [
        ("back-office-workspace-cleanup", "Workspace Cleanup"),
        ("back-office-agent-hygiene", "Agent Hygiene"),
    ]

    # Read the shared audit log once and parse per-slug entries on demand.
    audit_result = auth.client.table("workspace_files").select("content").eq(
        "user_id", user_id
    ).eq("path", "/workspace/_shared/back-office-audit.md").limit(1).execute()
    audit_text = (audit_result.data or [{}])[0].get("content", "")

    import re as _re
    def _summary_for_slug(slug: str) -> Optional[str]:
        # Match ## [<timestamp>] <slug> ... block, take the most recent one.
        # The dispatcher writes entries with "## [{ts}] {slug}\n- Executor: ...\n- Summary: <text>".
        pattern = rf"## \[[^\]]+\] {_re.escape(slug)}\n(?:- [^\n]+\n)*?- Summary:\s*([^\n]+)"
        matches = _re.findall(pattern, audit_text)
        return matches[-1].strip() if matches else None

    for task_slug, label in back_office_task_slugs:
        task_result = auth.client.table("tasks").select(
            "id, last_run_at, status"
        ).eq("user_id", user_id).eq("slug", task_slug).limit(1).execute()

        task_row = (task_result.data or [None])[0]
        if task_row and task_row.get("last_run_at"):
            background_jobs.append(BackgroundJobStatus(
                job_type=label,
                last_run_at=task_row["last_run_at"],
                last_run_status="success",
                last_run_summary=_summary_for_slug(task_slug),
            ))
        elif task_row:
            background_jobs.append(BackgroundJobStatus(
                job_type=label,
                last_run_status="never_run",
            ))

    # --- Scheduler heartbeat: still written to activity_log hourly ---
    hb_result = auth.client.table("activity_log").select(
        "id, summary, metadata, created_at"
    ).eq("user_id", user_id).eq(
        "event_type", "scheduler_heartbeat"
    ).order("created_at", desc=True).limit(1).execute()

    if hb_result.data:
        hb = hb_result.data[0]
        hb_meta = hb.get("metadata", {}) or {}
        background_jobs.append(BackgroundJobStatus(
            job_type="Scheduler Heartbeat",
            last_run_at=hb["created_at"],
            last_run_status="success" if not hb_meta.get("error") else "failed",
            last_run_summary=hb.get("summary"),
            items_processed=hb_meta.get("items_processed", 0),
        ))
    else:
        background_jobs.append(BackgroundJobStatus(
            job_type="Scheduler Heartbeat",
            last_run_status="never_run",
        ))

    # ADR-153: Sync schedule observability removed — no platform sync cron.
    # Platform data flows through task execution now.

    # Add schedule descriptions to background jobs
    for job in background_jobs:
        job.schedule_description = JOB_SCHEDULE_DESCRIPTIONS.get(job.job_type)

    return SystemStatusResponse(
        platform_sync=platform_sync,
        background_jobs=background_jobs,
        tier=tier,
        sync_frequency=sync_frequency,
    )


@router.get("/sync-timestamps")
async def get_sync_timestamps(auth: UserClient):
    """
    Lightweight endpoint for polling sync completion.

    Returns max last_synced_at per platform from sync_registry.
    Single DB query — designed for frequent polling during manual pipeline runs.
    """
    result = auth.client.table("sync_registry").select(
        "platform, last_synced_at"
    ).eq("user_id", auth.user_id).execute()

    timestamps: dict[str, str] = {}
    for row in (result.data or []):
        p = row["platform"]
        ts = row.get("last_synced_at")
        if ts and (p not in timestamps or ts > timestamps[p]):
            timestamps[p] = ts

    return {"timestamps": timestamps}
