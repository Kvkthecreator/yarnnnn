"""
Working Memory Builder - ADR-063: Four-Layer Model + ADR-072: System State Awareness

Builds the working memory injected into the TP system prompt at session start.
Analogous to Claude Code reading CLAUDE.md — TP reads what's explicitly stated,
nothing inferred by background jobs.

Sources (Memory + Activity layers only):
  /memory/ files — MEMORY.md, preferences.md, notes.md (ADR-108, replaces user_memory table)
  activity_log   — recent system events: agent runs, syncs, memory writes (Activity)
  filesystem_*   — raw synced platform content (searched on demand, not in prompt)

What goes in the prompt (~3,000 tokens, + ~500 for agent scope):
  - Identity: IDENTITY.md content (name, role, company, work context) ← ADR-144/156
  - Brand: BRAND.md content ← ADR-143
  - Awareness: AWARENESS.md — TP's persistent situational notes (shift handoff)
  - Active tasks (max 10): slug, mode, status, schedule, last/next run ← ADR-149
  - Context domains: per-domain file count + freshness + health ← ADR-151
  - Context readiness: identity/brand/docs/tasks/domains richness ← ADR-144/151
  - Preferences: tone_*, verbosity_*, preference:*
  - What you've told me: fact:*, instruction:*
  - Active agents (max 5)
  - Connected platforms + sync freshness (structured, not just strings) ← ADR-072
  - System summary: last signal pass, pending reviews, failed jobs ← ADR-072
  - Work budget: credits used/limit/exhausted ← ADR-156
  - Agent health: flagged agents with low approval rates ← ADR-156
  - Scoped agent: instructions + memory (if session is agent-scoped) ← ADR-087

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
    project_slug: Optional[str] = None,  # Deprecated — kept for call-site compat, ignored
) -> dict:
    """
    Build the working memory object for TP system prompt injection.

    Args:
        user_id: The authenticated user's ID
        client: Supabase client instance
        agent: Optional agent dict for scoped context (ADR-087).
                     Expected keys: id, title, scope, role, user_id.
                     agent_instructions/agent_memory used only for lazy workspace migration.
        project_slug: Deprecated — ignored. Kept for call-site compatibility.

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

    memory_files, agents, platforms, sessions, system_summary = await asyncio.gather(
        asyncio.to_thread(_get_user_memory_files_sync, user_id, _make_client()),
        asyncio.to_thread(_get_active_agents_sync, user_id, _make_client()),
        asyncio.to_thread(_get_connected_platforms_sync, user_id, _make_client()),
        asyncio.to_thread(_get_recent_sessions_sync, user_id, _make_client()),
        asyncio.to_thread(_get_system_summary_sync, user_id, _make_client()),
    )

    # ADR-127: Check for global user_shared/ files
    user_shared_files = await asyncio.to_thread(
        _get_user_shared_files_sync, user_id, _make_client()
    )

    # ADR-143: Read brand + orchestration playbook from workspace
    brand_content = memory_files.get("BRAND.md", "")
    orchestration_playbook = await asyncio.to_thread(
        _get_workspace_file_sync, user_id, "playbook-orchestration.md", _make_client()
    )

    # ADR-144: Read identity + awareness + compute context readiness
    identity_content, awareness_content = await asyncio.gather(
        asyncio.to_thread(_get_workspace_file_sync, user_id, "IDENTITY.md", _make_client()),
        asyncio.to_thread(_get_workspace_file_sync, user_id, "AWARENESS.md", _make_client()),
    )
    task_count, doc_count = await asyncio.gather(
        asyncio.to_thread(_count_tasks_sync, user_id, _make_client()),
        asyncio.to_thread(_count_documents_sync, user_id, _make_client()),
    )

    # ADR-151: Fetch active tasks + context domain health for TP meta-awareness
    # ADR-156: Work budget + agent health signals (replaces Composer awareness)
    active_tasks, context_domains, work_budget, agent_health = await asyncio.gather(
        asyncio.to_thread(_get_active_tasks_sync, user_id, _make_client()),
        asyncio.to_thread(_get_context_domain_health_sync, user_id, _make_client()),
        asyncio.to_thread(_get_work_budget_sync, user_id, _make_client()),
        asyncio.to_thread(_get_agent_health_sync, user_id, _make_client()),
    )

    working_memory = {
        # ADR-156: "profile" extraction removed — IDENTITY.md is rendered directly
        "preferences": _extract_preferences_from_file(memory_files.get("preferences.md")),
        "known": _extract_known_from_file(memory_files.get("notes.md")),
        "identity": identity_content,
        "brand": brand_content.strip() if brand_content else None,
        "awareness": awareness_content,
        "orchestration_playbook": orchestration_playbook,
        "agents": agents,
        "platforms": platforms,
        "recent_sessions": sessions,
        "system_summary": system_summary,
        "system_reference": _build_system_reference(platforms),
        "user_shared_files": user_shared_files,
        # ADR-149/151: Active tasks + context domain health for TP meta-awareness
        "active_tasks": active_tasks,
        "context_domains": context_domains,
        # ADR-156: Work budget + agent health (replaces Composer awareness)
        "work_budget": work_budget,
        "agent_health": agent_health,
        # ADR-144/155: Context readiness signal for TP graduated awareness
        "context_readiness": {
            "identity": _classify_richness(identity_content),
            "brand": _classify_richness(brand_content),
            "documents": doc_count,
            "tasks": task_count,
            "context_domains": len([d for d in context_domains if d.get("file_count", 0) > 0]) if context_domains else 0,
            "inference_state": _get_inference_state(context_domains),
        },
    }

    # ADR-087: Inject agent-scoped context if session is scoped
    if agent:
        working_memory["scoped_agent"] = await _extract_agent_scope(agent, client)

    return working_memory


def _get_workspace_file_sync(user_id: str, filename: str, client: Any) -> Optional[str]:
    """Read a single /workspace/ file (sync, for thread pool). ADR-143."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", f"/workspace/{filename}")
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows and rows[0].get("content"):
            return rows[0]["content"].strip()
    except Exception:
        pass
    return None


def _classify_richness(content: Optional[str]) -> str:
    """Classify workspace file richness: empty | sparse | rich. ADR-144."""
    if not content or not content.strip():
        return "empty"
    stripped = content.strip()
    # Sparse = exists but very short (e.g., just a heading)
    if len(stripped) < 100 or stripped.count("\n") < 3:
        return "sparse"
    return "rich"


def _get_inference_state(context_domains: list | None) -> str:
    """Classify workspace inference state from context domain health. ADR-155 revised.

    Derived from ground truth (do entity files exist?) not from persisted state.
    Returns: empty | scaffolded | validated
    """
    if not context_domains:
        return "empty"
    domains_with_entities = [d for d in context_domains if d.get("file_count", 0) > 0]
    if len(domains_with_entities) >= 2:
        return "scaffolded"
    return "empty"


def _count_tasks_sync(user_id: str, client: Any) -> int:
    """Count active tasks (sync, for thread pool). ADR-144."""
    try:
        result = (
            client.table("tasks")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .neq("status", "archived")
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def _count_documents_sync(user_id: str, client: Any) -> int:
    """Count uploaded documents (sync, for thread pool). ADR-144."""
    try:
        result = (
            client.table("filesystem_documents")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def _get_active_tasks_sync(user_id: str, client: Any) -> list[dict]:
    """Get active tasks with key metadata for TP awareness (sync). ADR-149/151."""
    try:
        result = (
            client.table("tasks")
            .select("slug, mode, status, schedule, next_run_at, last_run_at")
            .eq("user_id", user_id)
            .in_("status", ["active", "paused"])
            .order("updated_at", desc=True)
            .limit(10)
            .execute()
        )
        tasks = []
        for row in (result.data or []):
            task = {
                "slug": row.get("slug"),
                "mode": row.get("mode", "recurring"),
                "status": row.get("status"),
                "schedule": row.get("schedule"),
            }
            # Format timestamps for readability
            last_run = row.get("last_run_at")
            next_run = row.get("next_run_at")
            if last_run:
                task["last_run"] = last_run[:16].replace("T", " ")
            if next_run:
                task["next_run"] = next_run[:16].replace("T", " ")
            tasks.append(task)
        return tasks
    except Exception:
        return []


def _get_context_domain_health_sync(user_id: str, client: Any) -> list[dict]:
    """Get context domain health summary for TP awareness (sync). ADR-151.

    Returns list of {domain, file_count, latest_update} for each domain
    that has files in /workspace/context/.
    """
    from services.directory_registry import CONTEXT_DOMAINS, get_domain_folder
    domains = []
    for domain_key in CONTEXT_DOMAINS:
        folder = get_domain_folder(domain_key)
        if not folder:
            continue
        prefix = f"/workspace/{folder}/"
        try:
            result = (
                client.table("workspace_files")
                .select("updated_at")
                .eq("user_id", user_id)
                .like("path", f"{prefix}%")
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            # Count files
            count_result = (
                client.table("workspace_files")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .like("path", f"{prefix}%")
                .execute()
            )
            file_count = count_result.count or 0
            latest = rows[0]["updated_at"][:10] if rows else None
            domains.append({
                "domain": domain_key,
                "file_count": file_count,
                "latest_update": latest,
                "health": "active" if file_count > 1 else ("seeded" if file_count == 1 else "empty"),
            })
        except Exception:
            domains.append({"domain": domain_key, "file_count": 0, "latest_update": None, "health": "empty"})
    return domains


def _get_user_memory_files_sync(user_id: str, client: Any) -> dict[str, str]:
    """Read /memory/ files from workspace_files (sync, for thread pool). ADR-108."""
    from services.workspace import UserMemory
    um = UserMemory(client, user_id)
    return um.read_all_sync()


    # _get_work_index_sync DELETED (ADR-156: WORK.md dissolved post ADR-132)


    # _extract_profile_from_file DELETED (ADR-156: IDENTITY.md renders directly)


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
    # DEPRECATED by ADR-125: Will be replaced by thread-aware project session
    # summaries once all agents are project-native. Legacy fallback for now.
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


def _build_system_reference(platforms: list) -> dict:
    """
    Build TP's system reference — programmatic self-awareness of YARNNN capabilities.

    Analogous to Claude Code reading CLAUDE.md at session start. This gives TP
    recursive awareness of what agent roles are available and what the connected
    platforms can do. Maintained by code, not by hand.

    Generated from:
      - agent_framework.py (AGENT_TYPES — capability bundles per type)
      - Connected platforms (from working memory query)
    """
    from services.agent_framework import AGENT_TYPES, has_asset_capabilities

    # --- Agent types (ADR-130: deterministic capability bundles) ---
    roles = []
    for type_name, type_def in AGENT_TYPES.items():
        if type_name == "pm":
            continue  # PM type removed
        roles.append({
            "role": type_name,
            "capabilities": type_def["capabilities"],
            "has_asset_capabilities": has_asset_capabilities(type_name),
            "description": type_def.get("description", ""),
        })

    # --- Connected platform names (derived from already-fetched platforms) ---
    connected = [p.get("platform") for p in platforms if p.get("status") in ("active", "connected")]

    return {
        "agent_roles": roles,
        "connected_platforms": connected,
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
            "id, title, status, role, updated_at"
        ).eq("user_id", user_id).eq("status", "active").order(
            "updated_at", desc=True
        ).limit(MAX_AGENTS).execute()

        if result.data:
            for d in result.data:
                agents.append({
                    "id": d["id"],
                    "title": d.get("title", "Untitled"),
                    "role": d.get("role", "custom"),
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


def _get_user_shared_files_sync(user_id: str, client: Any) -> list[dict]:
    """ADR-127: List global /user_shared/ files for TP awareness (sync, for thread pool)."""
    try:
        result = (
            client.table("workspace_files")
            .select("path, summary, updated_at")
            .eq("user_id", user_id)
            .like("path", "/user_shared/%")
            .eq("lifecycle", "ephemeral")
            .order("updated_at", desc=True)
            .limit(10)
            .execute()
        )
        files = []
        for row in (result.data or []):
            filename = row["path"].split("/")[-1]
            files.append({
                "filename": filename,
                "summary": row.get("summary", ""),
                "updated_at": row.get("updated_at", ""),
            })
        return files
    except Exception:
        return []


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

    # ADR-156: integration_import_jobs query removed (table deprecated, import jobs sunset)

    return summary


def _get_work_budget_sync(user_id: str, client: Any) -> dict:
    """Fetch work budget status (sync, for thread pool). ADR-156."""
    try:
        from services.platform_limits import check_credits
        allowed, used, limit = check_credits(client, user_id)
        return {"used": used, "limit": limit, "exhausted": not allowed}
    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch work budget: {e}")
        return {"used": 0, "limit": -1, "exhausted": False}


def _get_agent_health_sync(user_id: str, client: Any) -> list:
    """Fetch agent health flags — only flagged agents shown. ADR-156.

    Returns agents with low approval rates so TP can surface concerns.
    Only includes agents with >= 5 runs and < 50% approval (early warning).
    """
    try:
        agents_result = client.table("agents").select(
            "id, title, slug, role"
        ).eq("user_id", user_id).eq("status", "active").execute()
        agents = agents_result.data or []
        if not agents:
            return []

        agent_ids = [a["id"] for a in agents]

        runs_result = client.table("agent_runs").select(
            "agent_id, status"
        ).in_("agent_id", agent_ids).execute()
        runs = runs_result.data or []

        # Compute per-agent stats
        stats: dict[str, dict] = {}
        for run in runs:
            aid = run["agent_id"]
            if aid not in stats:
                stats[aid] = {"total": 0, "approved": 0}
            stats[aid]["total"] += 1
            if run.get("status") == "approved":
                stats[aid]["approved"] += 1

        flagged = []
        for agent in agents:
            aid = agent["id"]
            agent_stats = stats.get(aid)
            if not agent_stats or agent_stats["total"] < 5:
                continue
            approval_rate = agent_stats["approved"] / agent_stats["total"]
            if approval_rate < 0.50:
                flagged.append({
                    "title": agent.get("title", "Untitled"),
                    "slug": agent.get("slug", ""),
                    "approval_rate": round(approval_rate, 2),
                    "run_count": agent_stats["total"],
                    "flag": "underperforming" if approval_rate < 0.30 else "needs_attention",
                })

        return flagged
    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch agent health: {e}")
        return []


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

    # ADR-156: "About you" profile section removed — IDENTITY.md renders directly below

    # Identity (ADR-144: workspace IDENTITY.md)
    identity = working_memory.get("identity")
    if identity:
        lines.append(f"\n### Identity\n{identity}")

    # Brand (ADR-143: workspace BRAND.md)
    brand = working_memory.get("brand")
    if brand:
        lines.append(f"\n### Brand\n{brand}")

    # Awareness (persistent TP situational notes)
    awareness = working_memory.get("awareness")
    if awareness and awareness.strip():
        # Truncate to prevent prompt bloat (2000 chars ≈ 500 tokens)
        content = awareness.strip()
        if len(content) > 2000:
            content = content[:2000] + "\n\n(truncated)"
        lines.append(f"\n### Awareness (your notes from prior sessions)\n{content}")

    # Active tasks (ADR-149/151: ground truth for TP reasoning)
    active_tasks = working_memory.get("active_tasks", [])
    if active_tasks:
        lines.append(f"\n### Active tasks ({len(active_tasks)})")
        for t in active_tasks:
            parts = [f"**{t['slug']}**", t.get("mode", ""), t.get("status", "")]
            if t.get("schedule"):
                parts.append(t["schedule"])
            if t.get("last_run"):
                parts.append(f"last: {t['last_run']}")
            if t.get("next_run"):
                parts.append(f"next: {t['next_run']}")
            lines.append(f"- {' | '.join(p for p in parts if p)}")

    # Context domains (ADR-151: ground truth domain health)
    context_domains = working_memory.get("context_domains", [])
    if context_domains:
        lines.append("\n### Context domains")
        for d in context_domains:
            health = d.get("health", "empty")
            count = d.get("file_count", 0)
            latest = d.get("latest_update")
            freshness = f", updated {latest}" if latest else ""
            lines.append(f"- **{d['domain']}**: {health} ({count} files{freshness})")

    # Context readiness (ADR-144: computed ground truth signals)
    readiness = working_memory.get("context_readiness", {})
    if readiness:
        gap_lines = []
        for item, val in readiness.items():
            if val == "empty" or val == 0:
                if item == "identity":
                    gap_lines.append("- **Identity**: empty — ask user about themselves and their work")
                elif item == "brand":
                    gap_lines.append("- **Brand**: empty — suggest sharing website or communication style")
                elif item == "documents":
                    gap_lines.append("- **Documents**: none — suggest uploading key files (decks, guides, reports)")
                elif item == "tasks":
                    gap_lines.append("- **Tasks**: none — suggest deliverables from catalog once identity is meaningful")
            elif val == "sparse":
                if item == "identity":
                    gap_lines.append("- **Identity**: sparse — enrich before suggesting tasks (need role + domain + industry)")
                elif item == "brand":
                    gap_lines.append("- **Brand**: sparse — could be enriched from website or brand materials")
        if gap_lines:
            lines.append("\n### Context gaps")
            lines.extend(gap_lines)

    # Orchestration playbook (ADR-143)
    playbook = working_memory.get("orchestration_playbook")
    if playbook:
        lines.append(f"\n### Orchestration Playbook\n{playbook}")

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

    # (Topics layer removed — projects are the workstreams directly.
    #  Active projects already shown in "Active agents" section above.)

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

    # Agents (ROSTER — ADR-140)
    agents = working_memory.get("agents", [])
    if agents:
        lines.append(f"\n### Your team ({len([a for a in agents if '_note' not in a])} agents)")
        for d in agents:
            if "_note" in d:
                lines.append(f"  {d['_note']}")
            else:
                role = d.get('role', 'custom')
                title = d.get('title', 'Untitled')
                lines.append(f"- {title} ({role})")

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

    # Recent Sessions (HISTORY) — ADR-125: includes project session summaries
    sessions = working_memory.get("recent_sessions", [])
    if sessions:
        lines.append(f"\n### Recent conversations")
        for s in sessions:
            project = s.get("project")
            if project:
                lines.append(f"- {s.get('date')}: {s.get('summary')} ({project})")
            else:
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

    # ADR-127: User-shared files (global staging area)
    user_shared = working_memory.get("user_shared_files", [])
    if user_shared:
        lines.append("\n### Your shared files")
        lines.append("Files you've shared (staged in user_shared/, 30-day expiry):")
        for f in user_shared:
            summary = f.get("summary", "")
            lines.append(f"- {f['filename']}{f' — {summary}' if summary else ''}")

    # System Reference — TP's self-awareness of YARNNN capabilities
    system_ref = working_memory.get("system_reference", {})
    if system_ref:
        lines.append("\n### System reference")

        # Agent roles
        agent_roles = system_ref.get("agent_roles", [])
        if agent_roles:
            lines.append("\n**Agent roles:**")
            for r in agent_roles:
                caps = ", ".join(r.get("capabilities", [])[:4])
                lines.append(f"- `{r['role']}`: {r.get('description', '')[:80]}")

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

    # ADR-156: Work budget status
    work_budget = working_memory.get("work_budget", {})
    budget_limit = work_budget.get("limit", -1)
    if budget_limit != -1:
        used = work_budget.get("used", 0)
        exhausted = work_budget.get("exhausted", False)
        if exhausted:
            lines.append(f"\n### Work budget: EXHAUSTED ({used}/{budget_limit} credits used)")
        elif used > 0:
            lines.append(f"\n### Work budget: {used}/{budget_limit} credits used")

    # ADR-156: Agent health flags (only flagged agents shown)
    agent_health = working_memory.get("agent_health", [])
    if agent_health:
        lines.append(f"\n### Agent health concerns")
        for ah in agent_health:
            pct = f"{ah['approval_rate']:.0%}"
            lines.append(f"- {ah['title']}: {pct} approval over {ah['run_count']} runs ({ah['flag']})")

    return "\n".join(lines)
