"""
System routes - Operations status (ADR-073)

Provides operational visibility into background orchestration:
- Platform sync status with per-resource detail from sync_registry
- Content accumulation from platform_content
- Background job status from activity_log

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


class PlatformContentSummary(BaseModel):
    """Content counts for a platform from platform_content."""
    total_items: int = 0
    retained_items: int = 0
    ephemeral_items: int = 0
    freshest_at: Optional[str] = None


class PlatformSyncStatus(BaseModel):
    """Sync status for a single platform."""
    platform: str
    connected: bool
    last_synced_at: Optional[str] = None
    next_sync_at: Optional[str] = None
    source_count: int = 0
    status: str = "unknown"  # healthy, stale, pending, disconnected
    resources: list[ResourceSyncStatus] = []
    content: Optional[PlatformContentSummary] = None


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
    ).eq("owner_id", user_id).maybe_single().execute()
    tier = ws_result.data.get("subscription_status", "free") if ws_result.data else "free"

    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    sync_frequency = limits.sync_frequency

    next_sync_hours = {
        "2x_daily": 6,
        "4x_daily": 4,
        "hourly": 1,
    }
    hours_between = next_sync_hours.get(sync_frequency, 6)

    # ─── Platform Connections ──────────────────────────────────────────────────
    platforms_result = auth.client.table("platform_connections").select(
        "platform, status, last_synced_at, landscape"
    ).eq("user_id", user_id).execute()

    # ─── Sync Registry (single query, partition by platform) ───────────────────
    registry_result = auth.client.table("sync_registry").select(
        "platform, resource_id, resource_name, last_synced_at, platform_cursor, item_count, last_error, last_error_at"
    ).eq("user_id", user_id).execute()

    # Group by platform
    registry_by_platform: dict[str, list[dict]] = {}
    for row in (registry_result.data or []):
        p = row["platform"]
        registry_by_platform.setdefault(p, []).append(row)

    # ─── Platform Content Counts (per platform) ───────────────────────────────
    # Map platform_connections.platform → platform_content.platform
    # Note: "google" connection provides both "gmail" and "calendar" content platforms
    content_platforms = ["slack", "gmail", "notion", "calendar"]
    content_counts: dict[str, PlatformContentSummary] = {}

    for cp in content_platforms:
        try:
            # Total non-expired
            total_result = auth.client.table("platform_content").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq("platform", cp).or_(
                f"retained.eq.true,expires_at.gt.{now.isoformat()}"
            ).execute()
            total = total_result.count or 0

            # Retained
            retained_result = auth.client.table("platform_content").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq("platform", cp).eq("retained", True).execute()
            retained = retained_result.count or 0

            # Freshest
            freshest_result = auth.client.table("platform_content").select(
                "fetched_at"
            ).eq("user_id", user_id).eq("platform", cp).order(
                "fetched_at", desc=True
            ).limit(1).execute()
            freshest_at = freshest_result.data[0]["fetched_at"] if freshest_result.data else None

            content_counts[cp] = PlatformContentSummary(
                total_items=total,
                retained_items=retained,
                ephemeral_items=total - retained,
                freshest_at=freshest_at,
            )
        except Exception:
            content_counts[cp] = PlatformContentSummary()

    # ─── Build Platform Sync Status ────────────────────────────────────────────
    platform_sync = []
    all_platforms = ["slack", "gmail", "notion", "calendar"]
    connected_platforms = {p["platform"]: p for p in (platforms_result.data or [])}

    # Map connection platform → content/registry platform names
    # "google" connection covers both gmail and calendar
    platform_content_map = {
        "slack": ["slack"],
        "google": ["gmail", "calendar"],
        "notion": ["notion"],
    }

    for platform in all_platforms:
        # Determine which connection platform owns this content platform
        conn_platform = platform
        if platform in ("gmail", "calendar"):
            conn_platform = "google"

        if conn_platform in connected_platforms:
            p_data = connected_platforms[conn_platform]
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
                # No sync_registry entries — fall back to platform_connections
                platform_status = "pending"
                fallback_synced = p_data.get("last_synced_at")
                if fallback_synced:
                    try:
                        fb_dt = datetime.fromisoformat(fallback_synced.replace("Z", "+00:00"))
                        hours_since = (now - fb_dt).total_seconds() / 3600
                        if hours_since > hours_between * 2:
                            platform_status = "stale"
                        else:
                            platform_status = "healthy"
                        latest_sync_dt = fb_dt
                    except (ValueError, TypeError):
                        pass

            # Compute last_synced_at and next_sync_at from registry data
            last_synced_str = latest_sync_dt.isoformat() if latest_sync_dt else p_data.get("last_synced_at")
            next_sync = None
            if latest_sync_dt:
                next_sync = (latest_sync_dt + timedelta(hours=hours_between)).isoformat()

            platform_sync.append(PlatformSyncStatus(
                platform=platform,
                connected=True,
                last_synced_at=last_synced_str,
                next_sync_at=next_sync,
                source_count=len(selected_sources),
                status=platform_status,
                resources=resources,
                content=content_counts.get(platform),
            ))
        else:
            platform_sync.append(PlatformSyncStatus(
                platform=platform,
                connected=False,
                status="disconnected",
            ))

    # ─── Background Jobs Status ────────────────────────────────────────────────
    background_jobs = []

    job_types = [
        ("platform_synced", "Platform Sync"),
        ("signal_processed", "Signal Processing"),
        ("memory_written", "Memory Extraction"),
        ("session_summary_written", "Session Summaries"),
        ("pattern_detected", "Pattern Detection"),
        ("conversation_analyzed", "Conversation Analysis"),
        ("deliverable_generated", "Deliverable Generation"),
        ("content_cleanup", "Content Cleanup"),
        ("scheduler_heartbeat", "Scheduler Heartbeat"),
    ]

    for event_type, label in job_types:
        if event_type == "platform_synced":
            # Aggregate recent platform_synced events (multiple platforms sync in parallel)
            sync_window = (now - timedelta(minutes=30)).isoformat()
            event_result = auth.client.table("activity_log").select(
                "id, summary, metadata, created_at"
            ).eq("user_id", user_id).eq(
                "event_type", event_type
            ).gte("created_at", sync_window).order(
                "created_at", desc=True
            ).limit(10).execute()

            if event_result.data:
                # Aggregate: combine summaries, sum items, use most recent timestamp
                latest = event_result.data[0]
                total_items = sum(
                    (e.get("metadata", {}) or {}).get("items_synced", 0)
                    for e in event_result.data
                )
                platforms = [
                    (e.get("metadata", {}) or {}).get("platform", "")
                    for e in event_result.data
                ]
                has_error = any(
                    (e.get("metadata", {}) or {}).get("error")
                    for e in event_result.data
                )
                summary = f"Synced {', '.join(p for p in platforms if p)}: {total_items} items"
                background_jobs.append(BackgroundJobStatus(
                    job_type=label,
                    last_run_at=latest["created_at"],
                    last_run_status="failed" if has_error else "success",
                    last_run_summary=summary,
                    items_processed=total_items,
                ))
            else:
                # Fall back to the single most recent event (outside 30min window)
                fallback = auth.client.table("activity_log").select(
                    "id, summary, metadata, created_at"
                ).eq("user_id", user_id).eq(
                    "event_type", event_type
                ).order("created_at", desc=True).limit(1).execute()
                if fallback.data:
                    event = fallback.data[0]
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
        else:
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
