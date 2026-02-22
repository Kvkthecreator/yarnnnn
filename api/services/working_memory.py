"""
Working Memory Builder - ADR-063: Four-Layer Model + ADR-072: System State Awareness

Builds the working memory injected into the TP system prompt at session start.
Analogous to Claude Code reading CLAUDE.md — TP reads what's explicitly stated,
nothing inferred by background jobs.

Sources (Memory + Activity layers only):
  user_context   — stated preferences, profile, facts, instructions (Memory)
  activity_log   — recent system events: deliverable runs, syncs, memory writes (Activity)
  filesystem_*   — raw synced platform content (searched on demand, not in prompt)

What goes in the prompt (~2,000 tokens):
  - About you: name, role, company, timezone
  - Preferences: tone_*, verbosity_*, preference:*
  - What you've told me: fact:*, instruction:*
  - Active deliverables (max 5)
  - Connected platforms + sync freshness (structured, not just strings) ← ADR-072
  - System summary: last signal pass, pending reviews, failed jobs ← ADR-072

Raw platform_content is NOT included here.
TP fetches it via Search when needed.
TP can invoke GetSystemState primitive for detailed operational state.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Configuration ---

MAX_DELIVERABLES = 5
MAX_PLATFORMS = 5
MAX_RECENT_SESSIONS = 3
MAX_CONTEXT_ENTRIES = 20       # Max user_context rows to include in prompt
MAX_ACTIVITY_EVENTS = 10       # ADR-063: Recent activity events injected into prompt
SESSION_LOOKBACK_DAYS = 7
ACTIVITY_LOOKBACK_DAYS = 7     # ADR-063: Window for activity_log query
WORKING_MEMORY_TOKEN_BUDGET = 2000


async def build_working_memory(user_id: str, client: Any) -> dict:
    """
    Build the working memory object for TP system prompt injection.

    Args:
        user_id: The authenticated user's ID
        client: Supabase client instance

    Returns:
        Dict structured for JSON serialization into the prompt.
        Designed to stay under ~2,000 tokens.
    """
    # Load user_context rows — the single source of truth for stated preferences
    context_rows = await _get_user_context(user_id, client)

    working_memory = {
        "profile": _extract_profile(context_rows),
        "preferences": _extract_preferences(context_rows),
        "known": _extract_known(context_rows),
        "deliverables": await _get_active_deliverables(user_id, client),
        "platforms": await _get_connected_platforms(user_id, client),
        "recent_sessions": await _get_recent_sessions(user_id, client),
        # ADR-072: Replace raw activity dump with structured system summary
        "system_summary": await _get_system_summary(user_id, client),
    }

    return working_memory


async def _get_user_context(user_id: str, client: Any) -> list[dict]:
    """
    Fetch all user_context rows for the user.

    ADR-059: Single SELECT replaces four separate table queries.
    """
    try:
        result = client.table("user_context").select(
            "key, value, source, confidence"
        ).eq("user_id", user_id).limit(MAX_CONTEXT_ENTRIES).execute()

        return result.data or []

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch user_context: {e}")
        return []


def _extract_profile(rows: list[dict]) -> dict:
    """Extract profile keys: name, role, company, timezone, summary."""
    profile_keys = {"name", "role", "company", "timezone", "summary"}
    profile: dict[str, Optional[str]] = {k: None for k in profile_keys}

    for row in rows:
        key = row.get("key", "")
        if key in profile_keys:
            profile[key] = row.get("value")

    return profile


def _extract_preferences(rows: list[dict]) -> list[dict]:
    """
    Extract tone/verbosity preferences per platform.

    Keys: tone_slack, tone_gmail, verbosity_slack, verbosity_gmail, etc.
    """
    prefs: dict[str, dict] = {}

    for row in rows:
        key = row.get("key", "")
        value = row.get("value", "")

        if key.startswith("tone_"):
            platform = key[5:]  # "tone_slack" → "slack"
            prefs.setdefault(platform, {})["tone"] = value

        elif key.startswith("verbosity_"):
            platform = key[10:]  # "verbosity_slack" → "slack"
            prefs.setdefault(platform, {})["verbosity"] = value

        elif key.startswith("preference:"):
            # Flat preference entry — group under 'general'
            prefs.setdefault("general", {}).setdefault("preferences", []).append(value)

    return [{"platform": k, **v} for k, v in prefs.items()]


def _extract_known(rows: list[dict]) -> list[dict]:
    """
    Extract fact/instruction entries: keys starting with 'fact:' or 'instruction:'.
    """
    known = []
    for row in rows:
        key = row.get("key", "")
        if key.startswith("fact:") or key.startswith("instruction:") or key.startswith("preference:"):
            entry_type = key.split(":")[0]
            known.append({
                "type": entry_type,
                "content": row.get("value", ""),
                "source": row.get("source", ""),
            })
    return known


async def _get_active_deliverables(user_id: str, client: Any) -> list:
    """
    Fetch active deliverables summary for working memory.

    Returns condensed list: title, frequency, recipient, status.
    Capped at MAX_DELIVERABLES, ordered by updated_at desc.
    """
    deliverables = []
    total_count = 0

    try:
        count_result = client.table("deliverables").select(
            "id", count="exact"
        ).eq("user_id", user_id).eq("status", "active").execute()

        total_count = count_result.count or 0

        result = client.table("deliverables").select(
            "id, title, status, schedule, recipient_context, next_run_at, updated_at"
        ).eq("user_id", user_id).eq("status", "active").order(
            "updated_at", desc=True
        ).limit(MAX_DELIVERABLES).execute()

        if result.data:
            for d in result.data:
                schedule = d.get("schedule", {}) or {}
                recipient = d.get("recipient_context", {}) or {}

                deliverables.append({
                    "id": d["id"],
                    "title": d.get("title", "Untitled"),
                    "frequency": schedule.get("frequency", "unknown"),
                    "recipient": recipient.get("name", "unspecified"),
                    "next_run": d.get("next_run_at"),
                })

        if total_count > MAX_DELIVERABLES:
            deliverables.append({
                "_note": f"... and {total_count - MAX_DELIVERABLES} more active deliverables"
            })

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch deliverables: {e}")

    return deliverables


async def _get_connected_platforms(user_id: str, client: Any) -> list:
    """
    Fetch connected platform summary for working memory.
    """
    platforms = []

    try:
        result = client.table("platform_connections").select(
            "id, platform, status, last_synced_at, settings"
        ).eq("user_id", user_id).order("platform").limit(MAX_PLATFORMS).execute()

        if result.data:
            now = datetime.now(timezone.utc)

            for p in result.data:
                last_synced = p.get("last_synced_at")
                freshness = _calculate_freshness(last_synced, now)

                platforms.append({
                    "platform": p.get("platform", "unknown"),
                    "status": p.get("status", "unknown"),
                    "last_synced": last_synced,
                    "freshness": freshness,
                })

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch platforms: {e}")

    return platforms


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
            return f"{int(delta.total_seconds() // 3600)} hours ago"
        elif delta < timedelta(days=7):
            return f"{delta.days} days ago"
        else:
            return f"stale ({delta.days} days)"
    except Exception:
        return "unknown"


async def _get_recent_sessions(user_id: str, client: Any) -> list:
    """
    Fetch recent session summaries for working memory.

    Returns last N session summaries from last 7 days.
    """
    sessions = []

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=SESSION_LOOKBACK_DAYS)).isoformat()

        result = client.table("chat_sessions").select(
            "id, created_at, summary"
        ).eq("user_id", user_id).not_.is_(
            "summary", "null"
        ).gte("created_at", cutoff).order(
            "created_at", desc=True
        ).limit(MAX_RECENT_SESSIONS).execute()

        if result.data:
            for s in result.data:
                summary = s.get("summary", "")
                if summary:
                    sessions.append({
                        "date": s.get("created_at", "")[:10],
                        "summary": summary[:300],
                    })

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch recent sessions: {e}")

    return sessions


async def _get_recent_activity(user_id: str, client: Any) -> list[dict]:
    """
    Fetch recent activity events for working memory prompt injection.

    ADR-063: Activity layer — records what YARNNN has done.
    Returns last MAX_ACTIVITY_EVENTS events within ACTIVITY_LOOKBACK_DAYS.

    NOTE: Deprecated in favor of _get_system_summary (ADR-072).
    Kept for backwards compatibility during transition.
    """
    try:
        from services.activity_log import get_recent_activity
        return await get_recent_activity(
            client=client,
            user_id=user_id,
            limit=MAX_ACTIVITY_EVENTS,
            days=ACTIVITY_LOOKBACK_DAYS,
        )
    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch recent activity: {e}")
        return []


async def _get_system_summary(user_id: str, client: Any) -> dict:
    """
    Build structured system summary for working memory (ADR-072).

    Replaces raw activity_log dump with actionable system state:
    - last_signal_pass: When, what triggered
    - platform_sync_freshness: Per-platform structured freshness
    - pending_reviews_count: Items awaiting user action
    - failed_jobs_24h: Any failed jobs in last 24 hours

    This gives TP ambient awareness of system state without requiring
    explicit GetSystemState invocation.
    """
    now = datetime.now(timezone.utc)
    summary: dict[str, Any] = {
        "last_signal_pass": None,
        "platform_sync_freshness": [],
        "pending_reviews_count": 0,
        "failed_jobs_24h": 0,
    }

    try:
        # 1. Last signal processing pass
        signal_result = (
            client.table("activity_log")
            .select("created_at, metadata")
            .eq("user_id", user_id)
            .eq("event_type", "signal_processed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if signal_result.data:
            row = signal_result.data[0]
            metadata = row.get("metadata", {}) or {}
            created_at = row.get("created_at")
            freshness = _calculate_freshness(created_at, now)

            actions_taken = metadata.get("actions_taken", [])
            deliverables_triggered = metadata.get("deliverables_triggered", [])

            summary["last_signal_pass"] = {
                "when": freshness,
                "actions_count": len(actions_taken),
                "deliverables_triggered": len(deliverables_triggered),
            }

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch last signal pass: {e}")

    try:
        # 2. Per-platform sync freshness (from platform_connections + sync_registry)
        platforms_result = (
            client.table("platform_connections")
            .select("platform, status, last_synced_at")
            .eq("user_id", user_id)
            .execute()
        )

        platform_freshness = []
        for p in (platforms_result.data or []):
            platform = p.get("platform", "unknown")
            last_synced = p.get("last_synced_at")
            status = p.get("status", "unknown")

            # Get resource count from sync_registry
            try:
                resource_result = (
                    client.table("sync_registry")
                    .select("resource_id", count="exact")
                    .eq("user_id", user_id)
                    .eq("platform", platform)
                    .execute()
                )
                resource_count = resource_result.count or 0
            except Exception as e:
                logger.warning(f"[WORKING_MEMORY] Failed to fetch sync_registry count for {platform}: {e}")
                resource_count = 0

            platform_freshness.append({
                "platform": platform,
                "status": status,
                "freshness": _calculate_freshness(last_synced, now),
                "resources_synced": resource_count,
            })

        summary["platform_sync_freshness"] = platform_freshness

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch platform sync freshness: {e}")

    try:
        # 3. Pending reviews (deliverable versions with status=draft or suggested)
        # Use a direct query approach that works with the schema
        pending_result = (
            client.table("deliverable_versions")
            .select("id, deliverable_id, deliverables!inner(user_id)")
            .eq("deliverables.user_id", user_id)
            .in_("status", ["draft", "suggested"])
            .execute()
        )

        summary["pending_reviews_count"] = len(pending_result.data or [])

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch pending reviews (join query): {e}")
        # Fallback: try simpler query
        try:
            # Get user's deliverable IDs first
            deliverables_result = (
                client.table("deliverables")
                .select("id")
                .eq("user_id", user_id)
                .execute()
            )
            deliverable_ids = [d["id"] for d in (deliverables_result.data or [])]

            if deliverable_ids:
                pending_result = (
                    client.table("deliverable_versions")
                    .select("id", count="exact")
                    .in_("deliverable_id", deliverable_ids)
                    .in_("status", ["draft", "suggested"])
                    .execute()
                )
                summary["pending_reviews_count"] = pending_result.count or 0
        except Exception as e2:
            logger.warning(f"[WORKING_MEMORY] Failed to fetch pending reviews (fallback): {e2}")

    try:
        # 4. Failed jobs in last 24 hours
        cutoff = (now - timedelta(hours=24)).isoformat()

        failed_result = (
            client.table("integration_import_jobs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "failed")
            .gte("updated_at", cutoff)
            .execute()
        )

        summary["failed_jobs_24h"] = failed_result.count or 0

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch failed jobs count: {e}")

    return summary


# --- Formatting ---

def estimate_working_memory_tokens(working_memory: dict) -> int:
    """Rough token count estimation. Rule of thumb: 1 token ≈ 4 characters."""
    json_str = json.dumps(working_memory, indent=2)
    return len(json_str) // 4


def format_for_prompt(working_memory: dict) -> str:
    """
    Format working memory dict as a readable string for prompt injection.

    This is the text that goes into TP's system prompt.
    """
    lines = ["## Working Memory\n"]

    # Profile (WHO)
    profile = working_memory.get("profile", {})
    if any(v for v in profile.values() if v):
        lines.append("### About you")
        if profile.get("name"):
            role_str = f" ({profile.get('role')})" if profile.get("role") else ""
            company_str = f" at {profile.get('company')}" if profile.get("company") else ""
            lines.append(f"**{profile['name']}**{role_str}{company_str}")
        if profile.get("timezone"):
            lines.append(f"Timezone: {profile['timezone']}")
        if profile.get("summary"):
            lines.append(f"{profile['summary']}")

    # Preferences (HOW)
    preferences = working_memory.get("preferences", [])
    if preferences:
        lines.append("\n### Your preferences")
        for pref in preferences:
            platform = pref.get("platform", "unknown")
            tone = pref.get("tone")
            verbosity = pref.get("verbosity")
            parts = []
            if tone:
                parts.append(f"tone: {tone}")
            if verbosity:
                parts.append(f"verbosity: {verbosity}")
            if parts:
                lines.append(f"- **{platform}**: {', '.join(parts)}")
            # Flat preferences list
            for p in pref.get("preferences", []):
                lines.append(f"- Prefers: {p}")

    # Known facts / instructions
    known = working_memory.get("known", [])
    if known:
        lines.append("\n### What you've told me")
        for item in known:
            entry_type = item.get("type", "fact")
            content = item.get("content", "")
            type_marker = {
                "preference": "Prefers",
                "instruction": "Note",
                "fact": "",
            }.get(entry_type, "")
            if type_marker:
                lines.append(f"- {type_marker}: {content}")
            else:
                lines.append(f"- {content}")

    # Deliverables (WORK)
    deliverables = working_memory.get("deliverables", [])
    if deliverables:
        lines.append(f"\n### Active deliverables")
        for d in deliverables:
            if "_note" in d:
                lines.append(f"  {d['_note']}")
            else:
                lines.append(f"- {d.get('title')} ({d.get('frequency')}) → {d.get('recipient')}")

    # Platforms (STATUS)
    platforms = working_memory.get("platforms", [])
    if platforms:
        lines.append(f"\n### Connected platforms")
        for p in platforms:
            status = p.get("status", "unknown")
            freshness = p.get("freshness", "unknown")
            if status == "connected":
                lines.append(f"- {p.get('platform')}: {freshness}")
            else:
                lines.append(f"- {p.get('platform')}: {status}")

    # Recent Sessions (HISTORY) — only rendered if summaries exist
    sessions = working_memory.get("recent_sessions", [])
    if sessions:
        lines.append(f"\n### Recent conversations")
        for s in sessions:
            lines.append(f"- {s.get('date')}: {s.get('summary')}")

    # System Summary (ADR-072) — structured operational state
    system_summary = working_memory.get("system_summary", {})
    if system_summary:
        lines.append(f"\n### System status")

        # Last signal pass
        signal_pass = system_summary.get("last_signal_pass")
        if signal_pass:
            when = signal_pass.get("when", "unknown")
            actions = signal_pass.get("actions_count", 0)
            triggered = signal_pass.get("deliverables_triggered", 0)
            if actions > 0 or triggered > 0:
                lines.append(f"- Signal processing: {when} ({actions} actions, {triggered} triggered)")
            else:
                lines.append(f"- Signal processing: {when} (no actions)")

        # Platform sync freshness
        platform_freshness = system_summary.get("platform_sync_freshness", [])
        if platform_freshness:
            for p in platform_freshness:
                platform = p.get("platform", "unknown")
                status = p.get("status", "unknown")
                freshness = p.get("freshness", "unknown")
                resources = p.get("resources_synced", 0)

                if status == "active":
                    lines.append(f"- {platform}: {freshness} ({resources} resource{'s' if resources != 1 else ''})")
                else:
                    lines.append(f"- {platform}: {status}")

        # Pending reviews
        pending = system_summary.get("pending_reviews_count", 0)
        if pending > 0:
            lines.append(f"- Pending reviews: {pending} item{'s' if pending != 1 else ''}")

        # Failed jobs
        failed = system_summary.get("failed_jobs_24h", 0)
        if failed > 0:
            lines.append(f"- Failed jobs (24h): {failed}")

    # Fallback: Recent Activity (ADR-063) — for backwards compatibility
    elif working_memory.get("recent_activity"):
        activity = working_memory.get("recent_activity", [])
        if activity:
            lines.append(f"\n### Recent activity")
            for event in activity:
                created_at = event.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    ts = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    ts = created_at[:16]
                summary = event.get("summary", "")
                lines.append(f"- {ts} · {summary}")

    return "\n".join(lines)
