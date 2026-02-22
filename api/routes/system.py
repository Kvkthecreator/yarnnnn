"""
System routes - Operations status

Provides operational visibility into background orchestration:
- Platform sync status (per-platform last/next sync)
- Background job status (signal processing, memory extraction, conversation analyst)

Mounted at /api/system
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

from services.supabase import UserClient

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class PlatformSyncStatus(BaseModel):
    """Sync status for a single platform."""
    platform: str
    connected: bool
    last_synced_at: Optional[str] = None
    next_sync_at: Optional[str] = None
    source_count: int = 0
    status: str = "unknown"  # healthy, stale, pending, disconnected


class BackgroundJobStatus(BaseModel):
    """Status of a background job type."""
    job_type: str
    last_run_at: Optional[str] = None
    last_run_status: str = "unknown"  # success, failed, never_run
    last_run_summary: Optional[str] = None
    items_processed: int = 0


class SystemStatusResponse(BaseModel):
    """System operations status overview."""
    platform_sync: list[PlatformSyncStatus]
    background_jobs: list[BackgroundJobStatus]
    tier: str = "free"
    sync_frequency: str = "2x_daily"


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(auth: UserClient):
    """
    Get system operations status.

    Returns:
    - Platform sync status per connected platform
    - Background job last-run status
    """
    user_id = auth.user_id
    now = datetime.now(timezone.utc)

    # ─── Platform Sync Status ─────────────────────────────────────────────────
    platform_sync = []

    # Get connected platforms
    platforms_result = auth.client.table("platform_connections").select(
        "platform, status, last_synced_at, landscape"
    ).eq("user_id", user_id).execute()

    # Get user tier and sync frequency
    from services.platform_limits import TIER_LIMITS

    ws_result = auth.client.table("workspaces").select(
        "subscription_status"
    ).eq("owner_id", user_id).maybe_single().execute()
    tier = ws_result.data.get("subscription_status", "free") if ws_result.data else "free"

    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    sync_frequency = limits.sync_frequency

    # Calculate next sync based on tier
    next_sync_hours = {
        "2x_daily": 6,
        "4x_daily": 4,
        "hourly": 1,
    }
    hours_between = next_sync_hours.get(sync_frequency, 6)

    all_platforms = ["slack", "gmail", "notion", "calendar"]
    connected_platforms = {p["platform"]: p for p in (platforms_result.data or [])}

    for platform in all_platforms:
        if platform in connected_platforms:
            p_data = connected_platforms[platform]
            last_synced = p_data.get("last_synced_at")
            landscape = p_data.get("landscape", {}) or {}
            selected_sources = landscape.get("selected_sources", [])

            # Calculate next sync
            next_sync = None
            status = "healthy"
            if last_synced:
                try:
                    last_dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00"))
                    next_dt = last_dt + timedelta(hours=hours_between)
                    next_sync = next_dt.isoformat()

                    # Check staleness
                    hours_since = (now - last_dt).total_seconds() / 3600
                    if hours_since > hours_between * 2:
                        status = "stale"
                except (ValueError, TypeError):
                    status = "unknown"
            else:
                status = "pending"

            platform_sync.append(PlatformSyncStatus(
                platform=platform,
                connected=True,
                last_synced_at=last_synced,
                next_sync_at=next_sync,
                source_count=len(selected_sources),
                status=status,
            ))
        else:
            platform_sync.append(PlatformSyncStatus(
                platform=platform,
                connected=False,
                status="disconnected",
            ))

    # ─── Background Jobs Status ───────────────────────────────────────────────
    background_jobs = []

    # Query activity_log for recent job runs
    job_types = [
        ("signal_processed", "Signal Processing"),
        ("memory_written", "Memory Extraction"),
        ("conversation_analyzed", "Conversation Analyst"),
    ]

    for event_type, label in job_types:
        # Get most recent event of this type
        event_result = auth.client.table("activity_log").select(
            "id, summary, metadata, created_at"
        ).eq("user_id", user_id).eq(
            "event_type", event_type
        ).order("created_at", desc=True).limit(1).execute()

        if event_result.data:
            event = event_result.data[0]
            metadata = event.get("metadata", {}) or {}
            background_jobs.append(BackgroundJobStatus(
                job_type=label,
                last_run_at=event["created_at"],
                last_run_status="success" if not metadata.get("error") else "failed",
                last_run_summary=event.get("summary"),
                items_processed=metadata.get("items_processed", 0),
            ))
        else:
            background_jobs.append(BackgroundJobStatus(
                job_type=label,
                last_run_status="never_run",
            ))

    return SystemStatusResponse(
        platform_sync=platform_sync,
        background_jobs=background_jobs,
        tier=tier,
        sync_frequency=sync_frequency,
    )
