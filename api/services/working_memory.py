"""
Working Memory Builder - ADR-063: Four-Layer Model + ADR-072: System State Awareness

Builds the working memory injected into the TP system prompt at session start.
Analogous to Claude Code reading CLAUDE.md — TP reads what's explicitly stated,
nothing inferred by background jobs.

Sources (Memory + Activity layers only):
  user_memory   — stated preferences, profile, facts, instructions (Memory)
  activity_log   — recent system events: agent runs, syncs, memory writes (Activity)
  filesystem_*   — raw synced platform content (searched on demand, not in prompt)

What goes in the prompt (~2,000 tokens, + ~500 for agent scope):
  - About you: name, role, company, timezone
  - Preferences: tone_*, verbosity_*, preference:*
  - What you've told me: fact:*, instruction:*
  - Active agents (max 5)
  - Connected platforms + sync freshness (structured, not just strings) ← ADR-072
  - System summary: last signal pass, pending reviews, failed jobs ← ADR-072
  - Scoped agent: instructions + memory (if session is agent-scoped) ← ADR-087

Raw platform_content is NOT included here.
TP fetches it via Search when needed.
TP can invoke GetSystemState primitive for detailed operational state.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from supabase import create_client as _create_supabase_client

logger = logging.getLogger(__name__)

# --- Configuration ---

MAX_AGENTS = 5
MAX_PLATFORMS = 5
MAX_RECENT_SESSIONS = 3
MAX_CONTEXT_ENTRIES = 20       # Max user_memory rows to include in prompt
MAX_ACTIVITY_EVENTS = 10       # ADR-063: Recent activity events injected into prompt
SESSION_LOOKBACK_DAYS = 7
ACTIVITY_LOOKBACK_DAYS = 7     # ADR-063: Window for activity_log query
WORKING_MEMORY_TOKEN_BUDGET = 2000


async def build_working_memory(
    user_id: str,
    client: Any,
    agent: Optional[dict] = None,
) -> dict:
    """
    Build the working memory object for TP system prompt injection.

    Args:
        user_id: The authenticated user's ID
        client: Supabase client instance
        agent: Optional agent dict for scoped context (ADR-087).
                     Expected keys: id, title, agent_type, user_id.
                     agent_instructions/agent_memory used only for lazy workspace migration.

    Returns:
        Dict structured for JSON serialization into the prompt.
        Designed to stay under ~2,000 tokens (+ ~500 for agent scope).
    """
    # Parallelize independent DB queries via thread pool.
    # Each thread gets its own Supabase client to avoid httpx connection pool
    # thread-safety issues (sync supabase client shares non-threadsafe httpx pool).
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    def _make_client():
        return _create_supabase_client(url, key)

    context_rows, agents, platforms, sessions, system_summary = await asyncio.gather(
        asyncio.to_thread(_get_user_memory_sync, user_id, _make_client()),
        asyncio.to_thread(_get_active_agents_sync, user_id, _make_client()),
        asyncio.to_thread(_get_connected_platforms_sync, user_id, _make_client()),
        asyncio.to_thread(_get_recent_sessions_sync, user_id, _make_client()),
        asyncio.to_thread(_get_system_summary_sync, user_id, _make_client()),
    )

    working_memory = {
        "profile": _extract_profile(context_rows),
        "preferences": _extract_preferences(context_rows),
        "known": _extract_known(context_rows),
        "agents": agents,
        "platforms": platforms,
        "recent_sessions": sessions,
        "system_summary": system_summary,
    }

    # ADR-087: Inject agent-scoped context if session is scoped
    if agent:
        working_memory["scoped_agent"] = await _extract_agent_scope(agent, client)

    return working_memory


def _get_user_memory_sync(user_id: str, client: Any) -> list[dict]:
    """Fetch all user_memory rows (sync, for thread pool)."""
    try:
        result = client.table("user_memory").select(
            "key, value, source, confidence"
        ).eq("user_id", user_id).limit(MAX_CONTEXT_ENTRIES).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch user_memory: {e}")
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


async def _extract_agent_scope(agent: dict, client: Any) -> dict:
    """
    Extract agent-scoped context for working memory injection (ADR-087).

    ADR-106 Phase 2: All reads from workspace files (source of truth).
    Returns structured dict with instructions, observations, goal, session history.
    DB columns only used for lazy migration via ensure_seeded().
    """
    agent_id = agent.get("id")

    # ADR-106 Phase 2: Read from workspace (source of truth)
    from services.workspace import AgentWorkspace, get_agent_slug
    ws = AgentWorkspace(client, agent.get("user_id"), get_agent_slug(agent))
    await ws.ensure_seeded(agent)  # Lazy migration

    instructions = (await ws.read("AGENT.md") or "").strip()

    scope = {
        "id": agent_id,
        "title": agent.get("title", "Untitled"),
        "type": agent.get("agent_type", "custom"),
    }

    if instructions:
        scope["instructions"] = instructions

    # Query scoped session summaries via agent_id FK (ADR-087 Phase 2)
    if agent_id:
        try:
            sessions_result = (
                client.table("chat_sessions")
                .select("summary, created_at")
                .eq("agent_id", agent_id)
                .not_.is_("summary", "null")
                .order("created_at", desc=True)
                .limit(3)
                .execute()
            )
            scoped_sessions = sessions_result.data or []
            if scoped_sessions:
                scope["session_summaries"] = [
                    {
                        "date": s.get("created_at", "")[:10],
                        "summary": (s.get("summary") or "")[:300],
                    }
                    for s in scoped_sessions
                ]
        except Exception as e:
            logger.warning(f"[WORKING_MEMORY] Failed to fetch scoped sessions: {e}")

    # ADR-106 Phase 2: Read observations and goal from workspace (source of truth)
    ws_observations = await ws.get_observations()
    if ws_observations:
        scope["observations"] = ws_observations[-5:]

    ws_goal = await ws.get_goal()
    if ws_goal:
        scope["goal"] = ws_goal

    # Fetch latest version preview + provenance — so TP can see what was last generated
    if agent_id:
        try:
            version_result = (
                client.table("agent_runs")
                .select("version_number, status, draft_content, final_content, created_at, delivery_status, source_snapshots, metadata")
                .eq("agent_id", agent_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if version_result.data:
                v = version_result.data[0]
                content = v.get("final_content") or v.get("draft_content") or ""
                scope["latest_version"] = {
                    "version_number": v.get("version_number"),
                    "status": v.get("status"),
                    "created_at": (v.get("created_at") or "")[:10],
                    "delivery_status": v.get("delivery_status"),
                    "content_preview": content[:400] + "..." if len(content) > 400 else content,
                }
                # ADR-049 evolution: inject source provenance so TP can explain
                # what context was used without needing tool calls
                snapshots = v.get("source_snapshots") or []
                if snapshots:
                    scope["latest_version"]["sources"] = [
                        {
                            "platform": s.get("platform"),
                            "name": s.get("resource_name") or s.get("resource_id"),
                            "items_used": s.get("items_used", s.get("item_count", 0)),
                        }
                        for s in snapshots
                    ]
                meta = v.get("metadata") or {}
                if meta.get("items_fetched"):
                    scope["latest_version"]["total_items_fetched"] = meta["items_fetched"]
                if meta.get("strategy"):
                    scope["latest_version"]["strategy"] = meta["strategy"]
        except Exception as e:
            logger.warning(f"[WORKING_MEMORY] Failed to fetch latest version: {e}")

    return scope


def _get_active_agents_sync(user_id: str, client: Any) -> list:
    """Fetch active agents summary (sync, for thread pool)."""
    agents = []
    total_count = 0

    try:
        count_result = client.table("agents").select(
            "id", count="exact"
        ).eq("user_id", user_id).eq("status", "active").execute()

        total_count = count_result.count or 0

        result = client.table("agents").select(
            "id, title, status, schedule, recipient_context, next_run_at, updated_at"
        ).eq("user_id", user_id).eq("status", "active").order(
            "updated_at", desc=True
        ).limit(MAX_AGENTS).execute()

        if result.data:
            for d in result.data:
                schedule = d.get("schedule", {}) or {}
                recipient = d.get("recipient_context", {}) or {}

                agents.append({
                    "id": d["id"],
                    "title": d.get("title", "Untitled"),
                    "frequency": schedule.get("frequency", "unknown"),
                    "recipient": recipient.get("name", "unspecified"),
                    "next_run": d.get("next_run_at"),
                })

        if total_count > MAX_AGENTS:
            agents.append({
                "_note": f"... and {total_count - MAX_AGENTS} more active agents"
            })

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch agents: {e}")

    return agents


def _get_connected_platforms_sync(user_id: str, client: Any) -> list:
    """Fetch connected platform summary (sync, for thread pool).

    Derives freshness from sync_registry (per-resource truth),
    not platform_connections.last_synced_at.
    """
    from services.freshness import calculate_freshness

    platforms = []

    try:
        # Get connections for status
        conn_result = client.table("platform_connections").select(
            "platform, status"
        ).eq("user_id", user_id).order("platform").limit(MAX_PLATFORMS).execute()

        if not conn_result.data:
            return platforms

        # Get max last_synced_at per platform from sync_registry (single query)
        registry_result = client.table("sync_registry").select(
            "platform, last_synced_at"
        ).eq("user_id", user_id).execute()

        # Build max last_synced_at per platform
        max_synced: dict[str, str] = {}
        for row in (registry_result.data or []):
            p = row.get("platform", "")
            ts = row.get("last_synced_at")
            if ts and (p not in max_synced or ts > max_synced[p]):
                max_synced[p] = ts

        now = datetime.now(timezone.utc)

        for p in conn_result.data:
            platform_name = p.get("platform", "unknown")
            status = p.get("status", "unknown")
            last_synced = max_synced.get(platform_name)

            platforms.append({
                "platform": platform_name,
                "status": status,
                "last_synced": last_synced,
                "freshness": calculate_freshness(last_synced, now),
            })

            # Google OAuth stores one "gmail" row covering both Gmail and Calendar
            if platform_name == "gmail":
                cal_synced = max_synced.get("calendar")
                platforms.append({
                    "platform": "calendar",
                    "status": status,
                    "last_synced": cal_synced,
                    "freshness": calculate_freshness(cal_synced, now),
                })

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch platforms: {e}")

    return platforms


def _get_recent_sessions_sync(user_id: str, client: Any) -> list:
    """Fetch recent session summaries (sync, for thread pool)."""
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


def _get_system_summary_sync(user_id: str, client: Any) -> dict:
    """Build structured system summary (sync, for thread pool). ADR-072."""
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
            from services.freshness import calculate_freshness

            row = signal_result.data[0]
            metadata = row.get("metadata", {}) or {}
            created_at = row.get("created_at")

            actions_taken = metadata.get("actions_taken", [])
            agents_triggered = metadata.get("agents_triggered", [])

            summary["last_signal_pass"] = {
                "when": calculate_freshness(created_at, now),
                "actions_count": len(actions_taken),
                "agents_triggered": len(agents_triggered),
            }

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch last signal pass: {e}")

    try:
        # 2. Per-platform sync freshness (from sync_registry — single source of truth)
        from services.freshness import calculate_freshness

        # Connections for status only
        conn_result = (
            client.table("platform_connections")
            .select("platform, status")
            .eq("user_id", user_id)
            .execute()
        )

        # sync_registry for freshness + resource counts (single query)
        registry_result = (
            client.table("sync_registry")
            .select("platform, last_synced_at")
            .eq("user_id", user_id)
            .execute()
        )

        # Build max last_synced_at and resource count per platform
        max_synced: dict[str, str] = {}
        resource_counts: dict[str, int] = {}
        for row in (registry_result.data or []):
            p = row.get("platform", "")
            ts = row.get("last_synced_at")
            resource_counts[p] = resource_counts.get(p, 0) + 1
            if ts and (p not in max_synced or ts > max_synced[p]):
                max_synced[p] = ts

        platform_freshness = []
        for p in (conn_result.data or []):
            platform = p.get("platform", "unknown")
            status = p.get("status", "unknown")
            last_synced = max_synced.get(platform)

            platform_freshness.append({
                "platform": platform,
                "status": status,
                "freshness": calculate_freshness(last_synced, now),
                "resources_synced": resource_counts.get(platform, 0),
            })

            # Google OAuth stores one "gmail" row covering both Gmail and Calendar
            if platform == "gmail":
                cal_synced = max_synced.get("calendar")
                platform_freshness.append({
                    "platform": "calendar",
                    "status": status,
                    "freshness": calculate_freshness(cal_synced, now),
                    "resources_synced": resource_counts.get("calendar", 0),
                })

        summary["platform_sync_freshness"] = platform_freshness

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch platform sync freshness: {e}")

    try:
        # 3. Pending reviews (agent versions with status=draft)
        # Use a direct query approach that works with the schema
        pending_result = (
            client.table("agent_runs")
            .select("id, agent_id, agents!inner(user_id)")
            .eq("agents.user_id", user_id)
            .in_("status", ["draft"])
            .execute()
        )

        summary["pending_reviews_count"] = len(pending_result.data or [])

    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch pending reviews (join query): {e}")
        # Fallback: try simpler query
        try:
            # Get user's agent IDs first
            agents_result = (
                client.table("agents")
                .select("id")
                .eq("user_id", user_id)
                .execute()
            )
            agent_ids = [d["id"] for d in (agents_result.data or [])]

            if agent_ids:
                pending_result = (
                    client.table("agent_runs")
                    .select("id", count="exact")
                    .in_("agent_id", agent_ids)
                    .in_("status", ["draft"])
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
            .gte("created_at", cutoff)
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

    # Agents (WORK)
    agents = working_memory.get("agents", [])
    if agents:
        lines.append(f"\n### Active agents")
        for d in agents:
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
            if status == "active":
                lines.append(f"- {p.get('platform')}: {freshness}")
            else:
                lines.append(f"- {p.get('platform')}: {status}")

    # Recent Sessions (HISTORY) — only rendered if summaries exist
    sessions = working_memory.get("recent_sessions", [])
    if sessions:
        lines.append(f"\n### Recent conversations")
        for s in sessions:
            lines.append(f"- {s.get('date')}: {s.get('summary')}")

    # ADR-087: Scoped agent context — instructions + memory for active agent
    scoped = working_memory.get("scoped_agent")
    if scoped:
        title = scoped.get("title", "Untitled")
        dtype = scoped.get("type", "custom").replace("_", " ").title()
        did = scoped.get("id", "")
        lines.append(f"\n### Current agent: {title} ({dtype})")
        if did:
            lines.append(f"**Ref:** `agent:{did}`")

        instructions = scoped.get("instructions")
        if instructions:
            lines.append(f"\n**Instructions:**\n{instructions}")

        summaries = scoped.get("session_summaries", [])
        if summaries:
            lines.append("\n**Recent sessions:**")
            for s in summaries:
                lines.append(f"- {s.get('date', '')}: {s.get('summary', '')}")

        observations = scoped.get("observations", [])
        if observations:
            lines.append("\n**Observations:**")
            for obs in observations:
                lines.append(f"- {obs.get('date', '')}: {obs.get('note', '')}")

        goal = scoped.get("goal")
        if goal:
            lines.append(f"\n**Goal:** {goal.get('description', '')}")
            status = goal.get("status", "")
            if status:
                lines.append(f"Status: {status}")
            milestones = goal.get("milestones", [])
            if milestones:
                lines.append(f"Milestones: {', '.join(milestones)}")

        latest_version = scoped.get("latest_version")
        if latest_version:
            v_num = latest_version.get("version_number", "?")
            v_status = latest_version.get("status", "unknown")
            v_date = latest_version.get("created_at", "unknown")
            v_delivery = latest_version.get("delivery_status")
            delivery_note = f" (delivery: {v_delivery})" if v_delivery else ""
            lines.append(f"\n**Latest version:** v{v_num} ({v_status}{delivery_note}, {v_date})")
            preview = latest_version.get("content_preview", "")
            if preview:
                lines.append(f"```\n{preview}\n```")

    # System Summary (ADR-072) — structured operational state
    system_summary = working_memory.get("system_summary", {})
    if system_summary:
        lines.append(f"\n### System status")

        # Last signal pass
        signal_pass = system_summary.get("last_signal_pass")
        if signal_pass:
            when = signal_pass.get("when", "unknown")
            actions = signal_pass.get("actions_count", 0)
            triggered = signal_pass.get("agents_triggered", 0)
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

    return "\n".join(lines)
