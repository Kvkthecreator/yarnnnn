"""
GetSystemState Primitive — ADR-072: System State Awareness

Aggregates operational state from across YARNNN's infrastructure into a queryable
snapshot. Gives TP the same visibility into system state that a human operator
would have.

Data sources:
  - activity_log: Last signal_processed, last platform_synced per platform, scheduler_heartbeat
  - sync_registry: Per-resource sync freshness
  - integration_import_jobs: Active/failed job state
  - signal_history: Recent signal activity
  - platform_connections: Available resources (landscape)

This is a read-only aggregation layer — no writes, no side effects.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


# --- Tool Definition ---

GET_SYSTEM_STATE_TOOL = {
    "name": "GetSystemState",
    "description": """Get a snapshot of YARNNN's operational state.

Use when the user asks about system status, sync state, or "what happened":
- "What happened last night?" → check scheduler_heartbeat, signal processing
- "Why didn't my digest run?" → check deliverable execution state
- "Is Slack syncing?" → check per-platform sync freshness
- "What platforms are connected?" → check platform connections with landscape

Returns structured SystemStateSnapshot with:
- last_signal_pass: When signals were last processed, what was triggered
- platform_sync_status: Per-platform sync freshness with resource details
- pending_reviews: Count of deliverable versions awaiting review
- failed_jobs: Any failed import jobs in last 24 hours
- scheduler_health: Last heartbeat, items processed

This is system introspection, not content search. Use Search for content.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["full", "signals", "sync", "scheduler", "jobs"],
                "description": "Which state to fetch. Default: 'full' (all state)"
            },
            "platform": {
                "type": "string",
                "description": "Filter to specific platform (slack, gmail, notion, calendar)"
            }
        },
        "required": []
    }
}


# --- Data Structures ---

@dataclass
class SignalPassSummary:
    """Summary of the last signal processing pass."""
    last_run_at: Optional[str] = None
    signals_evaluated: int = 0
    actions_taken: list[str] = field(default_factory=list)
    deliverables_triggered: list[str] = field(default_factory=list)
    reasoning_summary: Optional[str] = None


@dataclass
class PlatformSyncStatus:
    """Sync status for a single platform."""
    platform: str
    status: str  # active, disconnected, error
    last_synced_at: Optional[str] = None
    freshness: str = "unknown"
    resources: list[dict] = field(default_factory=list)  # From sync_registry
    landscape: list[dict] = field(default_factory=list)  # Available resources


@dataclass
class SchedulerHealth:
    """Health of the unified scheduler."""
    last_heartbeat_at: Optional[str] = None
    last_cycle_summary: Optional[str] = None
    deliverables_checked: int = 0
    deliverables_triggered: int = 0
    signals_created: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class FailedJob:
    """A failed import job."""
    job_id: str
    platform: str
    resource_name: str
    error_message: str
    failed_at: str


@dataclass
class SystemStateSnapshot:
    """Complete system state snapshot for TP consumption."""
    captured_at: str
    last_signal_pass: Optional[SignalPassSummary] = None
    platform_sync_status: list[PlatformSyncStatus] = field(default_factory=list)
    pending_reviews_count: int = 0
    failed_jobs: list[FailedJob] = field(default_factory=list)
    scheduler_health: Optional[SchedulerHealth] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "captured_at": self.captured_at,
            "last_signal_pass": {
                "last_run_at": self.last_signal_pass.last_run_at,
                "signals_evaluated": self.last_signal_pass.signals_evaluated,
                "actions_taken": self.last_signal_pass.actions_taken,
                "deliverables_triggered": self.last_signal_pass.deliverables_triggered,
                "reasoning_summary": self.last_signal_pass.reasoning_summary,
            } if self.last_signal_pass else None,
            "platform_sync_status": [
                {
                    "platform": p.platform,
                    "status": p.status,
                    "last_synced_at": p.last_synced_at,
                    "freshness": p.freshness,
                    "resources": p.resources,
                    "landscape": p.landscape,
                }
                for p in self.platform_sync_status
            ],
            "pending_reviews_count": self.pending_reviews_count,
            "failed_jobs": [
                {
                    "job_id": j.job_id,
                    "platform": j.platform,
                    "resource_name": j.resource_name,
                    "error_message": j.error_message,
                    "failed_at": j.failed_at,
                }
                for j in self.failed_jobs
            ],
            "scheduler_health": {
                "last_heartbeat_at": self.scheduler_health.last_heartbeat_at,
                "last_cycle_summary": self.scheduler_health.last_cycle_summary,
                "deliverables_checked": self.scheduler_health.deliverables_checked,
                "deliverables_triggered": self.scheduler_health.deliverables_triggered,
                "signals_created": self.scheduler_health.signals_created,
                "errors": self.scheduler_health.errors,
            } if self.scheduler_health else None,
        }


# --- Handler ---

async def handle_get_system_state(auth: Any, input: dict) -> dict:
    """
    Handle GetSystemState primitive.

    Args:
        auth: Auth context with user_id and client
        input: {"scope": "full|signals|sync|scheduler|jobs", "platform": "..."}

    Returns:
        {"success": True, "state": SystemStateSnapshot.to_dict(), "message": "..."}
    """
    scope = input.get("scope", "full")
    platform_filter = input.get("platform")

    user_id = auth.user_id
    client = auth.client

    now = datetime.now(timezone.utc)
    snapshot = SystemStateSnapshot(captured_at=now.isoformat())

    try:
        # Fetch components based on scope
        if scope in ("full", "signals"):
            snapshot.last_signal_pass = await _get_last_signal_pass(client, user_id)

        if scope in ("full", "sync"):
            snapshot.platform_sync_status = await _get_platform_sync_status(
                client, user_id, platform_filter
            )

        if scope in ("full", "scheduler"):
            snapshot.scheduler_health = await _get_scheduler_health(client, user_id)
            snapshot.pending_reviews_count = await _get_pending_reviews_count(client, user_id)

        if scope in ("full", "jobs"):
            snapshot.failed_jobs = await _get_failed_jobs(client, user_id)

        return {
            "success": True,
            "state": snapshot.to_dict(),
            "message": _format_state_message(snapshot),
        }

    except Exception as e:
        logger.error(f"[GetSystemState] Failed to build snapshot: {e}")
        return {
            "success": False,
            "error": "state_fetch_failed",
            "message": str(e),
        }


# --- Data Fetchers ---

async def _get_last_signal_pass(client: Any, user_id: str) -> Optional[SignalPassSummary]:
    """Fetch the most recent signal_processed event from activity_log."""
    try:
        result = (
            client.table("activity_log")
            .select("created_at, metadata")
            .eq("user_id", user_id)
            .eq("event_type", "signal_processed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            row = result.data[0]
            metadata = row.get("metadata", {}) or {}
            return SignalPassSummary(
                last_run_at=row.get("created_at"),
                signals_evaluated=metadata.get("signals_evaluated", 0),
                actions_taken=metadata.get("actions_taken", []),
                deliverables_triggered=metadata.get("deliverables_triggered", []),
                reasoning_summary=metadata.get("reasoning_summary"),
            )

        return None

    except Exception as e:
        logger.warning(f"[GetSystemState] Failed to get signal pass: {e}")
        return None


async def _get_platform_sync_status(
    client: Any,
    user_id: str,
    platform_filter: Optional[str] = None,
) -> list[PlatformSyncStatus]:
    """Fetch per-platform sync status with resource-level detail."""
    statuses = []
    now = datetime.now(timezone.utc)

    try:
        # Get platform connections
        query = (
            client.table("platform_connections")
            .select("platform, status, last_synced_at, landscape")
            .eq("user_id", user_id)
        )
        if platform_filter:
            query = query.eq("platform", platform_filter)

        connections_result = query.execute()

        for conn in (connections_result.data or []):
            platform = conn.get("platform", "unknown")
            last_synced = conn.get("last_synced_at")

            # Calculate freshness
            freshness = _calculate_freshness(last_synced, now)

            # Get per-resource sync state from sync_registry
            resources = await _get_resource_sync_state(client, user_id, platform)

            # Parse landscape (available resources)
            landscape_raw = conn.get("landscape", {}) or {}
            landscape = _parse_landscape(landscape_raw, platform)

            statuses.append(PlatformSyncStatus(
                platform=platform,
                status=conn.get("status", "unknown"),
                last_synced_at=last_synced,
                freshness=freshness,
                resources=resources,
                landscape=landscape,
            ))

        return statuses

    except Exception as e:
        logger.warning(f"[GetSystemState] Failed to get platform sync status: {e}")
        return []


async def _get_resource_sync_state(
    client: Any,
    user_id: str,
    platform: str,
) -> list[dict]:
    """Fetch per-resource sync state from sync_registry."""
    try:
        result = (
            client.table("sync_registry")
            .select("resource_id, resource_name, last_synced_at, item_count")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .order("last_synced_at", desc=True)
            .limit(10)  # Top 10 most recently synced resources
            .execute()
        )

        resources = []
        now = datetime.now(timezone.utc)

        for row in (result.data or []):
            last_synced = row.get("last_synced_at")
            resources.append({
                "resource_id": row.get("resource_id"),
                "resource_name": row.get("resource_name"),
                "last_synced_at": last_synced,
                "freshness": _calculate_freshness(last_synced, now),
                "item_count": row.get("item_count", 0),
            })

        return resources

    except Exception as e:
        logger.warning(f"[GetSystemState] Failed to get resource sync state: {e}")
        return []


def _parse_landscape(landscape_raw: dict, platform: str) -> list[dict]:
    """Parse landscape JSON into list of available resources."""
    resources = []

    if platform == "slack":
        # Slack landscape: channels, dms
        for channel in landscape_raw.get("channels", []):
            resources.append({
                "type": "channel",
                "id": channel.get("id"),
                "name": channel.get("name"),
            })

    elif platform == "gmail":
        # Gmail landscape: labels
        for label in landscape_raw.get("labels", []):
            resources.append({
                "type": "label",
                "id": label.get("id"),
                "name": label.get("name"),
            })

    elif platform == "notion":
        # Notion landscape: pages, databases
        for page in landscape_raw.get("pages", []):
            resources.append({
                "type": "page",
                "id": page.get("id"),
                "name": page.get("title"),
            })

    elif platform == "calendar":
        # Calendar landscape: calendars
        for cal in landscape_raw.get("calendars", []):
            resources.append({
                "type": "calendar",
                "id": cal.get("id"),
                "name": cal.get("summary"),
            })

    return resources[:20]  # Cap at 20 resources


async def _get_scheduler_health(client: Any, user_id: str) -> Optional[SchedulerHealth]:
    """Fetch the most recent scheduler_heartbeat event for this user."""
    try:
        result = (
            client.table("activity_log")
            .select("created_at, summary, metadata")
            .eq("user_id", user_id)
            .eq("event_type", "scheduler_heartbeat")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            row = result.data[0]
            metadata = row.get("metadata", {}) or {}
            return SchedulerHealth(
                last_heartbeat_at=row.get("created_at"),
                last_cycle_summary=row.get("summary"),
                deliverables_checked=metadata.get("deliverables_checked", 0),
                deliverables_triggered=metadata.get("deliverables_triggered", 0),
                signals_created=metadata.get("signals_created", 0),
                errors=metadata.get("errors", []) or [],
            )

        return None

    except Exception as e:
        logger.warning(f"[GetSystemState] Failed to get scheduler health: {e}")
        return None


async def _get_pending_reviews_count(client: Any, user_id: str) -> int:
    """Count deliverable versions awaiting review (status=draft or status=suggested)."""
    try:
        result = (
            client.table("deliverable_versions")
            .select("id", count="exact")
            .eq("deliverables.user_id", user_id)
            .in_("status", ["draft", "suggested"])
            .execute()
        )

        return result.count or 0

    except Exception as e:
        logger.warning(f"[GetSystemState] Failed to get pending reviews: {e}")
        return 0


async def _get_failed_jobs(client: Any, user_id: str) -> list[FailedJob]:
    """Fetch failed import jobs from last 24 hours."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        result = (
            client.table("integration_import_jobs")
            .select("id, provider, resource_name, error_message, updated_at")
            .eq("user_id", user_id)
            .eq("status", "failed")
            .gte("updated_at", cutoff)
            .order("updated_at", desc=True)
            .limit(10)
            .execute()
        )

        jobs = []
        for row in (result.data or []):
            jobs.append(FailedJob(
                job_id=row.get("id", ""),
                platform=row.get("provider", "unknown"),
                resource_name=row.get("resource_name", "unknown"),
                error_message=row.get("error_message", "No error message"),
                failed_at=row.get("updated_at", ""),
            ))

        return jobs

    except Exception as e:
        logger.warning(f"[GetSystemState] Failed to get failed jobs: {e}")
        return []


# --- Helpers ---

def _calculate_freshness(last_synced: Optional[str], now: datetime) -> str:
    """Calculate human-readable freshness indicator."""
    if not last_synced:
        return "never synced"

    try:
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


def _format_state_message(snapshot: SystemStateSnapshot) -> str:
    """Generate human-readable summary of system state."""
    parts = []

    # Signal processing
    if snapshot.last_signal_pass:
        sp = snapshot.last_signal_pass
        if sp.last_run_at:
            freshness = _calculate_freshness(sp.last_run_at, datetime.now(timezone.utc))
            action_count = len(sp.actions_taken)
            parts.append(f"Last signal pass: {freshness} ({action_count} actions)")
        else:
            parts.append("No signal processing recorded")
    else:
        parts.append("No signal processing recorded")

    # Platforms
    if snapshot.platform_sync_status:
        connected = [p for p in snapshot.platform_sync_status if p.status == "active"]
        parts.append(f"{len(connected)} platform(s) connected")

    # Scheduler
    if snapshot.scheduler_health:
        sh = snapshot.scheduler_health
        if sh.last_heartbeat_at:
            freshness = _calculate_freshness(sh.last_heartbeat_at, datetime.now(timezone.utc))
            parts.append(f"Scheduler: {freshness}")
        else:
            parts.append("Scheduler: no heartbeat")
    else:
        parts.append("Scheduler: no heartbeat")

    # Issues
    if snapshot.failed_jobs:
        parts.append(f"{len(snapshot.failed_jobs)} failed job(s) in last 24h")

    if snapshot.pending_reviews_count > 0:
        parts.append(f"{snapshot.pending_reviews_count} item(s) awaiting review")

    return " | ".join(parts)
