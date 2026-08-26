"""
Freshness Service - ADR-049 Context Freshness Model

Manages context freshness for agent generation.
Platforms ARE our filesystem, sync IS our git pull.

Key concepts:
- sync_registry: Tracks current sync state per source (mutable)
- source_snapshots: Records what was used at generation time (immutable)
- Freshness check: Compare sync_registry with platform state

Usage:
    from services.freshness import check_agent_freshness, record_source_snapshots

    # Before generation
    freshness = await check_agent_freshness(client, user_id, agent)

    # After generation
    await record_source_snapshots(client, run_id, sources_used)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from dateutil.parser import isoparse as _isoparse
from typing import Any, Optional
from services.workspace_context import effective_workspace_id, substrate_scope_filter
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Shared Freshness Utilities
# =============================================================================

def calculate_freshness(last_synced: Optional[str], now: Optional[datetime] = None) -> str:
    """Calculate human-readable freshness indicator.

    Single source of truth — imported by system_state.py, etc.
    """
    if not last_synced:
        return "never synced"

    if now is None:
        now = datetime.now(timezone.utc)

    try:
        from datetime import timedelta
        synced_dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00"))
        delta = now - synced_dt

        if delta < timedelta(hours=1):
            return "fresh"
        elif delta < timedelta(hours=24):
            hours = int(delta.total_seconds() // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta < timedelta(days=7):
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        else:
            return f"stale ({delta.days} days)"
    except Exception:
        return "unknown"


async def get_platform_freshness_from_registry(
    client,
    user_id: str,
    platform: str,
) -> Optional[str]:
    """Get the most recent last_synced_at for a platform from sync_registry.

    Returns the max last_synced_at across all resources for this platform,
    which is the single source of truth for "when was this platform last synced".
    """
    try:
        result = client.table("sync_registry").select(
            "last_synced_at"
        ).eq(*substrate_scope_filter(user_id)).eq("platform", platform).order(
            "last_synced_at", desc=True
        ).limit(1).execute()

        if result.data and result.data[0].get("last_synced_at"):
            return result.data[0]["last_synced_at"]
        return None
    except Exception as e:
        logger.warning(f"[FRESHNESS] Failed to get platform freshness for {platform}: {e}")
        return None


# =============================================================================
# Freshness Check (ADR-049)
# =============================================================================

# ---------------------------------------------------------------------------
# DELETED 2026-08-26 — the agent-run freshness half of this module.
# ---------------------------------------------------------------------------
#
# check_agent_freshness · get_sync_state · record_source_snapshots ·
# get_source_snapshots · compare_with_last_generation all read or wrote
# `agent_runs` for the retired agent model. Every one had ZERO callers in
# api/ and scripts/ — the callers went with routes/agents.py.
#
# compare_with_last_generation is worth naming: on an empty table it returned
# {"has_changes": True, ...} — it would have said "regenerate" forever.
#
# What survives is the platform half, which is live: calculate_freshness
# (pure) and get_platform_freshness_from_registry (routes/integrations.py).
