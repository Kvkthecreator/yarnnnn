"""
Working Memory Builder - ADR-063: Four-Layer Model + ADR-072: System State Awareness

Builds the working memory injected into the TP system prompt at session start.
Analogous to Claude Code reading CLAUDE.md — TP reads what's explicitly stated,
nothing inferred by background jobs.

Sources (Memory + Activity layers only):
  /memory/ files — MEMORY.md, preferences.md, notes.md (ADR-108, replaces user_memory table)
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
    project_slug: Optional[str] = None,  # ADR-119 P4b
) -> dict:
    """
    Build the working memory object for TP system prompt injection.

    Args:
        user_id: The authenticated user's ID
        client: Supabase client instance
        agent: Optional agent dict for scoped context (ADR-087).
                     Expected keys: id, title, scope, role, user_id.
                     agent_instructions/agent_memory used only for lazy workspace migration.
        project_slug: Optional project slug for project-scoped context (ADR-119 P4b).

    Returns:
        Dict structured for JSON serialization into the prompt.
        Designed to stay under ~2,000 tokens (+ ~500 for agent/project scope).
    """
    # Parallelize independent DB queries via thread pool.
    # Each thread gets its own Supabase client to avoid httpx connection pool
    # thread-safety issues (sync supabase client shares non-threadsafe httpx pool).
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    def _make_client():
        return _create_supabase_client(url, key)

    memory_files, agents, platforms, sessions, system_summary = await asyncio.gather(
        asyncio.to_thread(_get_user_memory_files_sync, user_id, _make_client()),
        asyncio.to_thread(_get_active_agents_sync, user_id, _make_client()),
        asyncio.to_thread(_get_connected_platforms_sync, user_id, _make_client()),
        asyncio.to_thread(_get_recent_sessions_sync, user_id, _make_client()),
        asyncio.to_thread(_get_system_summary_sync, user_id, _make_client()),
    )

    working_memory = {
        "profile": _extract_profile_from_file(memory_files.get("MEMORY.md")),
        "preferences": _extract_preferences_from_file(memory_files.get("preferences.md")),
        "known": _extract_known_from_file(memory_files.get("notes.md")),
        "agents": agents,
        "platforms": platforms,
        "recent_sessions": sessions,
        "system_summary": system_summary,
        "system_reference": _build_system_reference(platforms),
    }

    # ADR-087: Inject agent-scoped context if session is scoped
    if agent:
        working_memory["scoped_agent"] = await _extract_agent_scope(agent, client)

    # ADR-119 P4b: Inject project-scoped context if session is project-scoped
    if project_slug:
        working_memory["scoped_project"] = await _extract_project_scope(
            project_slug, client, user_id
        )

    return working_memory


def _get_user_memory_files_sync(user_id: str, client: Any) -> dict[str, str]:
    """Read /memory/ files from workspace_files (sync, for thread pool). ADR-108."""
    from services.workspace import UserMemory
    um = UserMemory(client, user_id)
    return um.read_all_sync()


def _extract_profile_from_file(content: Optional[str]) -> dict:
    """Extract profile from MEMORY.md content. ADR-108."""
    from services.workspace import UserMemory
    profile = UserMemory._parse_memory_md(content)
    # Ensure all expected keys exist
    for key in ("name", "role", "company", "timezone", "summary"):
        profile.setdefault(key, None)
    return profile


def _extract_preferences_from_file(content: Optional[str]) -> list[dict]:
    """Extract preferences from preferences.md content. ADR-108."""
    from services.workspace import UserMemory
    prefs = UserMemory._parse_preferences_md(content)
    return [{"platform": k, **v} for k, v in prefs.items()]


def _extract_known_from_file(content: Optional[str]) -> list[dict]:
    """Extract facts/instructions/preferences from notes.md content. ADR-108."""
    from services.workspace import UserMemory
    notes = UserMemory._parse_notes_md(content)
    return [
        {"type": n["type"], "content": n["content"], "source": "filesystem"}
        for n in notes
    ]


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
        "role": agent.get("role", "custom"),
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


async def _extract_project_scope(project_slug: str, client: Any, user_id: str) -> dict:
    """
    ADR-119 P4b: Extract project-scoped context for working memory injection.

    Returns structured dict with project title, intent, contributor status,
    recent activity, and work plan snippet.
    """
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(client, user_id, project_slug)
    project = await pw.read_project()
    if not project:
        return {"slug": project_slug, "error": "not_found"}

    scope: dict[str, Any] = {
        "slug": project_slug,
        "title": project.get("title", ""),
        "objective": project.get("objective", {}),
        "contributors": project.get("contributors", []),
        "status": project.get("status", "active"),
    }

    # Recent assemblies (last 3 date-folder names)
    try:
        assemblies = await pw.list_assemblies()
        if assemblies:
            scope["recent_assemblies"] = assemblies[-3:]
    except Exception:
        pass

    # Work plan snippet (if PM has written one)
    try:
        work_plan = await pw.read("memory/work_plan.md")
        if work_plan:
            scope["work_plan"] = work_plan[:500]
    except Exception:
        pass

    return scope


def _build_system_reference(platforms: list) -> dict:
    """
    Build TP's system reference — programmatic self-awareness of YARNNN capabilities.

    Analogous to Claude Code reading CLAUDE.md at session start. This gives TP
    recursive awareness of what project types exist, what agent roles are available,
    and what the connected platforms can do. Maintained by code, not by hand.

    Generated from:
      - project_registry.py (PROJECT_TYPE_REGISTRY)
      - agent_framework.py (ROLE_PORTFOLIOS, SKILL_ENABLED_ROLES)
      - Connected platforms (from working memory query)
    """
    from services.project_registry import PROJECT_TYPE_REGISTRY
    from services.agent_framework import ROLE_PORTFOLIOS, SKILL_ENABLED_ROLES

    # --- Project types ---
    project_types = []
    for key, ptype in PROJECT_TYPE_REGISTRY.items():
        entry: dict[str, Any] = {
            "key": key,
            "name": ptype["display_name"],
            "category": ptype["category"],
        }
        if ptype.get("platform"):
            entry["platform"] = ptype["platform"]
        if ptype.get("description"):
            entry["description"] = ptype["description"]
        entry["pm"] = ptype.get("pm", False)
        entry["agents_count"] = len(ptype.get("agents", []))
        project_types.append(entry)

    # --- Agent roles ---
    roles = []
    for role_name, tracks in ROLE_PORTFOLIOS.items():
        duties_at_senior = [d["duty"] for d in tracks.get("senior", [])]
        roles.append({
            "role": role_name,
            "duties": duties_at_senior,
            "has_output_skills": role_name in SKILL_ENABLED_ROLES,
        })

    # --- Connected platform names (derived from already-fetched platforms) ---
    connected = [p.get("platform") for p in platforms if p.get("status") in ("active", "connected")]

    # --- Platform → project type mapping ---
    platform_project_map = {}
    for key, ptype in PROJECT_TYPE_REGISTRY.items():
        plat = ptype.get("platform")
        if plat:
            platform_project_map[plat] = key

    return {
        "project_types": project_types,
        "agent_roles": roles,
        "connected_platforms": connected,
        "platform_project_map": platform_project_map,
    }


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
    Derives freshness from sync_registry (per-resource truth).
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
        "platform_sync_freshness": [],
        "pending_reviews_count": 0,
        "failed_jobs_24h": 0,
    }

    try:
        # 1. Per-platform sync freshness (from sync_registry — single source of truth)
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

    # ADR-119 P4b: Scoped project context
    scoped_project = working_memory.get("scoped_project")
    if scoped_project and not scoped_project.get("error"):
        title = scoped_project.get("title", "Untitled")
        lines.append(f"\n### Current project: {title}")

        objective = scoped_project.get("objective", {})
        if objective.get("purpose"):
            lines.append(f"**Purpose:** {objective['purpose']}")
        if objective.get("deliverable"):
            lines.append(f"**Deliverable:** {objective['deliverable']}")

        contributors = scoped_project.get("contributors", [])
        if contributors:
            lines.append(f"\n**Contributors:** {len(contributors)}")
            for c in contributors[:5]:
                slug = c.get("agent_slug", "?")
                contrib = c.get("expected_contribution", "")
                lines.append(f"- {slug}{f': {contrib}' if contrib else ''}")

        assemblies = scoped_project.get("recent_assemblies", [])
        if assemblies:
            lines.append(f"\n**Recent assemblies:** {', '.join(assemblies)}")

        work_plan = scoped_project.get("work_plan")
        if work_plan:
            lines.append(f"\n**Work plan:**\n{work_plan}")

    # System Reference — TP's self-awareness of YARNNN capabilities
    system_ref = working_memory.get("system_reference", {})
    if system_ref:
        lines.append("\n### System reference")

        # Project types
        project_types = system_ref.get("project_types", [])
        if project_types:
            lines.append("\n**Project types** (use these with CreateProject — don't improvise):")
            for pt in project_types:
                pm_tag = " [has PM]" if pt.get("pm") else ""
                plat_tag = f" (platform: {pt['platform']})" if pt.get("platform") else ""
                lines.append(f"- `{pt['key']}`: {pt['name']}{plat_tag}{pm_tag} — {pt.get('description', '')}")

        # Platform → project type mapping
        ppm = system_ref.get("platform_project_map", {})
        connected = system_ref.get("connected_platforms", [])
        if ppm and connected:
            lines.append("\n**Connected platform → project type:**")
            for plat in connected:
                ptype_key = ppm.get(plat)
                if ptype_key:
                    lines.append(f"- {plat} → `{ptype_key}`")
                else:
                    lines.append(f"- {plat} → no platform-specific type (use `custom`)")

        # Agent roles
        agent_roles = system_ref.get("agent_roles", [])
        if agent_roles:
            lines.append("\n**Agent roles:**")
            for r in agent_roles:
                skills_tag = " [output skills]" if r.get("has_output_skills") else ""
                duties = ", ".join(r["duties"]) if r.get("duties") else r["role"]
                lines.append(f"- `{r['role']}`: duties at senior = {duties}{skills_tag}")

    # System Summary (ADR-072) — structured operational state
    system_summary = working_memory.get("system_summary", {})
    if system_summary:
        lines.append(f"\n### System status")

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
