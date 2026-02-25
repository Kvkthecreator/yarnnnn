"""
Freshness Service - ADR-049 Context Freshness Model

Manages context freshness for deliverable generation.
Platforms ARE our filesystem, sync IS our git pull.

Key concepts:
- sync_registry: Tracks current sync state per source (mutable)
- source_snapshots: Records what was used at generation time (immutable)
- Freshness check: Compare sync_registry with platform state

Usage:
    from services.freshness import check_deliverable_freshness, record_source_snapshots

    # Before generation
    freshness = await check_deliverable_freshness(client, user_id, deliverable)
    if not freshness["all_fresh"]:
        await sync_stale_sources(client, user_id, freshness["stale_sources"])

    # After generation
    await record_source_snapshots(client, version_id, sources_used)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Freshness Check (ADR-049)
# =============================================================================

async def check_deliverable_freshness(
    client,
    user_id: str,
    deliverable: dict,
    staleness_threshold_hours: int = 24,
) -> dict:
    """
    Check if deliverable sources are fresh enough for generation.

    Compares sync_registry state with configured staleness threshold.

    Args:
        client: Supabase client
        user_id: User UUID
        deliverable: Deliverable dict with 'sources' field
        staleness_threshold_hours: Hours before source is considered stale

    Returns:
        {
            "all_fresh": bool,
            "stale_sources": [{platform, resource_id, resource_name, last_synced_at, hours_stale}],
            "fresh_sources": [{platform, resource_id, resource_name, last_synced_at}],
            "never_synced": [{platform, resource_id, resource_name}]
        }
    """
    sources = deliverable.get("sources", [])
    if not sources:
        return {
            "all_fresh": True,
            "stale_sources": [],
            "fresh_sources": [],
            "never_synced": [],
        }

    now = datetime.now(timezone.utc)
    threshold = now.timestamp() - (staleness_threshold_hours * 3600)

    stale_sources = []
    fresh_sources = []
    never_synced = []

    for source in sources:
        platform = source.get("provider") or source.get("platform")
        resource_id = source.get("resource_id")
        resource_name = source.get("resource_name", "")

        if not platform or not resource_id:
            continue

        # Check sync_registry for this source
        sync_state = await get_sync_state(client, user_id, platform, resource_id)

        if not sync_state:
            never_synced.append({
                "platform": platform,
                "resource_id": resource_id,
                "resource_name": resource_name,
            })
            continue

        last_synced_at = sync_state.get("last_synced_at")
        if not last_synced_at:
            never_synced.append({
                "platform": platform,
                "resource_id": resource_id,
                "resource_name": resource_name,
            })
            continue

        # Parse timestamp
        if isinstance(last_synced_at, str):
            last_synced_at = datetime.fromisoformat(last_synced_at.replace("Z", "+00:00"))

        synced_ts = last_synced_at.timestamp()
        hours_stale = (now.timestamp() - synced_ts) / 3600

        if synced_ts < threshold:
            stale_sources.append({
                "platform": platform,
                "resource_id": resource_id,
                "resource_name": resource_name or sync_state.get("resource_name", ""),
                "last_synced_at": last_synced_at.isoformat(),
                "hours_stale": round(hours_stale, 1),
            })
        else:
            fresh_sources.append({
                "platform": platform,
                "resource_id": resource_id,
                "resource_name": resource_name or sync_state.get("resource_name", ""),
                "last_synced_at": last_synced_at.isoformat(),
            })

    all_fresh = len(stale_sources) == 0 and len(never_synced) == 0

    return {
        "all_fresh": all_fresh,
        "stale_sources": stale_sources,
        "fresh_sources": fresh_sources,
        "never_synced": never_synced,
    }


async def get_sync_state(
    client,
    user_id: str,
    platform: str,
    resource_id: str,
) -> Optional[dict]:
    """
    Get current sync state from sync_registry.

    Returns:
        {last_synced_at, platform_cursor, item_count, source_latest_at, resource_name}
        or None if not found
    """
    try:
        result = client.table("sync_registry").select(
            "last_synced_at, platform_cursor, item_count, source_latest_at, resource_name"
        ).eq("user_id", user_id).eq("platform", platform).eq("resource_id", resource_id).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.warning(f"[FRESHNESS] Failed to get sync state: {e}")
        return None


# =============================================================================
# Sync Registry Updates
# =============================================================================

async def update_sync_registry(
    client,
    user_id: str,
    platform: str,
    resource_id: str,
    resource_name: Optional[str] = None,
    platform_cursor: Optional[str] = None,
    item_count: int = 0,
    source_latest_at: Optional[datetime] = None,
    last_error: Optional[str] = None,
) -> Optional[str]:
    """
    Update sync_registry after a sync operation.

    Uses upsert to create or update the registry entry.
    On success (last_error=None), clears any previous error.
    On error, sets last_error and last_error_at without updating last_synced_at.

    Returns:
        UUID of the registry entry, or None on failure
    """
    try:
        now = datetime.now(timezone.utc)

        if last_error:
            # Error path: record the error without updating last_synced_at
            data = {
                "user_id": user_id,
                "platform": platform,
                "resource_id": resource_id,
                "last_error": last_error[:500],  # Truncate to avoid bloat
                "last_error_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            if resource_name:
                data["resource_name"] = resource_name
        else:
            # Success path: update sync state and clear any previous error
            data = {
                "user_id": user_id,
                "platform": platform,
                "resource_id": resource_id,
                "last_synced_at": now.isoformat(),
                "item_count": item_count,
                "updated_at": now.isoformat(),
                "last_error": None,
                "last_error_at": None,
            }
            if resource_name:
                data["resource_name"] = resource_name
            if platform_cursor:
                data["platform_cursor"] = platform_cursor
            if source_latest_at:
                data["source_latest_at"] = source_latest_at.isoformat()

        result = client.table("sync_registry").upsert(
            data,
            on_conflict="user_id,platform,resource_id"
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get("id")
        return None
    except Exception as e:
        logger.error(f"[FRESHNESS] Failed to update sync_registry: {e}")
        return None


# =============================================================================
# Source Snapshots (ADR-049)
# =============================================================================

async def record_source_snapshots(
    client,
    version_id: str,
    sources_used: list[dict],
) -> bool:
    """
    Record source snapshots on deliverable_version after generation.

    This creates an immutable audit trail of what sources were used.

    Args:
        client: Supabase client
        version_id: UUID of the deliverable_version
        sources_used: List of source configs that were used

    Returns:
        True on success, False on failure
    """
    try:
        snapshots = []
        now = datetime.now(timezone.utc)

        for source in sources_used:
            platform = source.get("provider") or source.get("platform")
            resource_id = source.get("resource_id")

            if not platform or not resource_id:
                continue

            # Get current sync state for this source
            sync_state = await get_sync_state(
                client,
                source.get("user_id", ""),  # May need to pass this
                platform,
                resource_id
            )

            snapshot = {
                "platform": platform,
                "resource_id": resource_id,
                "resource_name": source.get("resource_name") or (sync_state or {}).get("resource_name"),
                "synced_at": now.isoformat(),
            }

            if sync_state:
                snapshot["platform_cursor"] = sync_state.get("platform_cursor")
                snapshot["item_count"] = sync_state.get("item_count", 0)
                snapshot["source_latest_at"] = sync_state.get("source_latest_at")

            snapshots.append(snapshot)

        # Update the version record
        result = client.table("deliverable_versions").update({
            "source_snapshots": snapshots
        }).eq("id", version_id).execute()

        return bool(result.data)
    except Exception as e:
        logger.error(f"[FRESHNESS] Failed to record source snapshots: {e}")
        return False


async def get_source_snapshots(
    client,
    version_id: str,
) -> list[dict]:
    """
    Get source snapshots from a deliverable_version.

    Useful for comparing "what changed since last generation".
    """
    try:
        result = client.table("deliverable_versions").select(
            "source_snapshots"
        ).eq("id", version_id).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get("source_snapshots", [])
        return []
    except Exception as e:
        logger.warning(f"[FRESHNESS] Failed to get source snapshots: {e}")
        return []


# =============================================================================
# Targeted Sync (ADR-049)
# =============================================================================

async def sync_stale_sources(
    client,
    user_id: str,
    stale_sources: list[dict],
) -> dict:
    """
    Sync only stale sources before generation.

    This is targeted sync - not blanket. Only syncs what's needed.

    Args:
        client: Supabase client
        user_id: User UUID
        stale_sources: List of stale source dicts from check_deliverable_freshness

    Returns:
        {
            "synced": [{platform, resource_id, success}],
            "failed": [{platform, resource_id, error}]
        }
    """
    from services.job_queue import enqueue_job

    synced = []
    failed = []

    for source in stale_sources:
        platform = source.get("platform")
        resource_id = source.get("resource_id")
        resource_name = source.get("resource_name", "")

        try:
            # Enqueue targeted sync job for single stale source
            job_id = await enqueue_job(
                "platform_sync",
                user_id=user_id,
                provider=platform,
                selected_sources=[resource_id] if resource_id else None,
            )

            synced.append({
                "platform": platform,
                "resource_id": resource_id,
                "job_id": job_id,
                "success": True,
            })
            logger.info(f"[FRESHNESS] Enqueued sync for {platform}:{resource_id}")
        except Exception as e:
            failed.append({
                "platform": platform,
                "resource_id": resource_id,
                "error": str(e),
            })
            logger.error(f"[FRESHNESS] Failed to enqueue sync for {platform}:{resource_id}: {e}")

    return {
        "synced": synced,
        "failed": failed,
    }


# =============================================================================
# Freshness Comparison (for "what changed")
# =============================================================================

async def compare_with_last_generation(
    client,
    user_id: str,
    deliverable_id: str,
) -> dict:
    """
    Compare current sync state with last generation's snapshots.

    Useful for understanding what's new since last generation.

    Returns:
        {
            "has_changes": bool,
            "changes": [{platform, resource_id, items_added, time_since_last}],
            "last_version_id": str or None
        }
    """
    try:
        # Get last completed version
        result = client.table("deliverable_versions").select(
            "id, source_snapshots, created_at"
        ).eq("deliverable_id", deliverable_id).in_(
            "status", ["staged", "approved", "delivered"]
        ).order("version_number", desc=True).limit(1).execute()

        if not result.data:
            return {
                "has_changes": True,  # No prior version, always generate
                "changes": [],
                "last_version_id": None,
            }

        last_version = result.data[0]
        last_snapshots = last_version.get("source_snapshots", [])

        if not last_snapshots:
            return {
                "has_changes": True,
                "changes": [],
                "last_version_id": last_version["id"],
            }

        changes = []
        now = datetime.now(timezone.utc)

        for snapshot in last_snapshots:
            platform = snapshot.get("platform")
            resource_id = snapshot.get("resource_id")

            # Get current sync state
            current = await get_sync_state(client, user_id, platform, resource_id)

            if not current:
                continue

            # Compare
            last_item_count = snapshot.get("item_count", 0)
            current_item_count = current.get("item_count", 0)
            items_added = current_item_count - last_item_count

            last_synced = snapshot.get("synced_at")
            if last_synced:
                if isinstance(last_synced, str):
                    last_synced = datetime.fromisoformat(last_synced.replace("Z", "+00:00"))
                hours_since = (now - last_synced).total_seconds() / 3600
            else:
                hours_since = None

            if items_added > 0 or (hours_since and hours_since > 24):
                changes.append({
                    "platform": platform,
                    "resource_id": resource_id,
                    "resource_name": snapshot.get("resource_name"),
                    "items_added": max(0, items_added),
                    "hours_since_last": round(hours_since, 1) if hours_since else None,
                })

        return {
            "has_changes": len(changes) > 0,
            "changes": changes,
            "last_version_id": last_version["id"],
        }
    except Exception as e:
        logger.error(f"[FRESHNESS] Failed to compare generations: {e}")
        return {
            "has_changes": True,  # On error, assume changes
            "changes": [],
            "last_version_id": None,
        }
