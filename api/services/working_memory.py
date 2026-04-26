"""
Working Memory Builder - ADR-063 Four-Layer Model

Builds the working memory injected into the TP system prompt at session start.
Analogous to Claude Code reading CLAUDE.md — TP reads what's explicitly stated,
nothing inferred by background jobs.

Sources:
  /memory/ files — MEMORY.md, style.md, notes.md (ADR-108, replaces user_memory table)
  activity_log   — recent system events: task runs, integrations, scheduler heartbeat
  workspace_files — identity, brand, awareness, context domain health

What goes in the prompt (~3,000 tokens, + ~500 for agent scope):
  - Identity: IDENTITY.md content (name, role, company, work context) ← ADR-144/156
  - Brand: BRAND.md content ← ADR-143
  - Awareness: AWARENESS.md — TP's persistent situational notes (shift handoff)
  - Active tasks (max 10): slug, mode, status, schedule, last/next run ← ADR-149
  - Context domains: per-domain file count + freshness + health ← ADR-151
  - Workspace state: unified signal — identity/brand gaps, tasks stale, budget, agent health ← ADR-156
  - Preferences: tone_*, verbosity_*
  - What you've told me: fact:*, instruction:*
  - Active agents (max 5)
  - Connected platforms + selected-source state
  - System summary: pending reviews / failed jobs
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

    # ADR-143 + ADR-206: Read brand + orchestration playbook from workspace
    from services.workspace_paths import (
        SHARED_BRAND_PATH, SHARED_IDENTITY_PATH,
        MEMORY_PLAYBOOK_PATH, MEMORY_AWARENESS_PATH,
    )
    brand_content = memory_files.get("BRAND.md", "")
    orchestration_playbook = await asyncio.to_thread(
        _get_workspace_file_sync, user_id, MEMORY_PLAYBOOK_PATH, _make_client()
    )

    # ADR-144 + ADR-206: Read identity + awareness + conversation summary + compute context readiness
    identity_content, awareness_content, conversation_summary = await asyncio.gather(
        asyncio.to_thread(_get_workspace_file_sync, user_id, SHARED_IDENTITY_PATH, _make_client()),
        asyncio.to_thread(_get_workspace_file_sync, user_id, MEMORY_AWARENESS_PATH, _make_client()),
        asyncio.to_thread(_get_workspace_file_sync, user_id, "memory/conversation.md", _make_client()),
    )
    task_count, doc_count, recent_uploads, recent_authorship, recent_md_signal = await asyncio.gather(
        asyncio.to_thread(_count_tasks_sync, user_id, _make_client()),
        asyncio.to_thread(_count_documents_sync, user_id, _make_client()),
        asyncio.to_thread(_get_recent_uploads_sync, user_id, _make_client()),
        # ADR-209 Phase 3: recent substrate authorship aggregation
        asyncio.to_thread(_get_recent_authorship_sync, user_id, _make_client()),
        # ADR-220 Commit C: narrative-side rollup signal — does /workspace/memory/recent.md
        # exist and have entries? Used as the second one-liner pointer in the compact index
        # (counterpart to the substrate-authorship line). Detail lives in the file; YARNNN
        # reads on demand via ReadFile.
        asyncio.to_thread(_get_recent_md_signal_sync, user_id, _make_client()),
    )

    # ADR-151: Fetch active tasks + context domain health for TP meta-awareness
    # ADR-172: Balance replaces work_budget signal
    active_tasks, context_domains, balance_info, agent_health = await asyncio.gather(
        asyncio.to_thread(_get_active_tasks_sync, user_id, _make_client()),
        asyncio.to_thread(_get_context_domain_health_sync, user_id, _make_client()),
        asyncio.to_thread(_get_balance_sync, user_id, _make_client()),
        asyncio.to_thread(_get_agent_health_sync, user_id, _make_client()),
    )

    # Compute stale tasks (hasn't run in 2x its schedule)
    tasks_stale = _count_stale_tasks(active_tasks)

    working_memory = {
        "preferences": _extract_preferences_from_file(memory_files.get("style.md")),
        "known": _extract_known_from_file(memory_files.get("notes.md")),
        "identity": identity_content,
        "brand": brand_content.strip() if brand_content else None,
        "awareness": awareness_content,
        "conversation_summary": conversation_summary,
        "orchestration_playbook": orchestration_playbook,
        "agents": agents,
        "platforms": platforms,
        "recent_sessions": sessions,
        "system_summary": system_summary,
        "system_reference": _build_system_reference(platforms),
        "user_shared_files": user_shared_files,
        # ADR-149/151: Active tasks + context domain health
        "active_tasks": active_tasks,
        "context_domains": context_domains,
        # ADR-162 Sub-phase B: Recent uploads — TP should consider processing these
        "recent_uploads": recent_uploads,
        # ADR-209 Phase 3: Recent substrate authorship — one-line "what happened" signal
        "recent_authorship": recent_authorship,
        # ADR-220 Commit C: narrative-side recent.md rollup signal — counterpart
        # to recent_authorship. {"exists": bool, "total": int, "by_role": dict, "updated_at": iso}
        "recent_md": recent_md_signal,
        # ADR-156: Unified workspace state — single signal for TP awareness
        "workspace_state": {
            # Identity
            "identity": _classify_richness(identity_content),
            "brand": _classify_richness(brand_content),
            # Content
            "documents": doc_count,
            "context_domains": len([d for d in context_domains if d.get("file_count", 0) > 0 and not d.get("temporal")]) if context_domains else 0,
            # Work
            "tasks_active": task_count,
            "tasks_stale": tasks_stale,
            # Balance (ADR-172)
            "balance_usd": balance_info.get("balance", 0.0),
            "balance_exhausted": balance_info.get("exhausted", False),
            # Health (only flagged agents)
            "agents_flagged": agent_health,
            # ADR-204: Intelligence Cockpit signals — domain entity coverage + outcome platform detection
            "domain_entity_counts": {
                d["domain"]: d.get("file_count", 0)
                for d in (context_domains or [])
                if not d.get("temporal") and d.get("file_count", 0) > 0
            },
            "outcome_connected": any(
                p.get("platform") in {"alpaca", "lemonsqueezy"} and p.get("status") == "active"
                for p in platforms
            ),
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


def _count_stale_tasks(active_tasks: list[dict]) -> int:
    """Count tasks that haven't run in 2x their expected schedule. ADR-156."""
    from datetime import datetime, timezone, timedelta

    SCHEDULE_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}
    now = datetime.now(timezone.utc)
    stale = 0
    for task in active_tasks:
        if task.get("status") != "active":
            continue
        schedule = task.get("schedule", "")
        last_run = task.get("last_run")
        if not last_run or not schedule:
            continue
        expected_days = SCHEDULE_DAYS.get(schedule)
        if not expected_days:
            continue
        try:
            last_dt = datetime.fromisoformat(last_run.replace(" ", "T") + ":00+00:00")
            if (now - last_dt) > timedelta(days=expected_days * 2):
                stale += 1
        except (ValueError, TypeError):
            continue
    return stale


def _classify_richness(content: Optional[str]) -> str:
    """Classify workspace file richness: empty | sparse | rich. ADR-144."""
    if not content or not content.strip():
        return "empty"
    stripped = content.strip()
    # Sparse = exists but very short (e.g., just a heading)
    if len(stripped) < 100 or stripped.count("\n") < 3:
        return "sparse"
    return "rich"


    # _get_inference_state DELETED — TP judges from raw context_domains data directly


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


def _get_recent_authorship_sync(user_id: str, client: Any) -> dict:
    """Recent substrate authorship counts (ADR-209 Phase 3).

    Returns counts of revisions landed in the last 24 hours, grouped by
    the cognitive-layer prefix of authored_by. Used by the compact index
    to surface a one-line "what has been happening" signal so YARNNN
    can reason about recent substrate activity without reading files.

    Example return:
        {
            "window_hours": 24,
            "total": 23,
            "by_layer": {"operator": 3, "yarnnn": 12, "agent": 5, "system": 3},
        }

    Returns {"window_hours": 24, "total": 0, "by_layer": {}} when quiet
    or on error (non-fatal).
    """
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        result = (
            client.table("workspace_file_versions")
            .select("authored_by")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .limit(500)  # cap the window — one line of output, don't need more
            .execute()
        )
        rows = result.data or []
        by_layer: dict[str, int] = {}
        for r in rows:
            author = (r.get("authored_by") or "").strip()
            if not author:
                continue
            # Prefix before ":" is the cognitive layer (operator, yarnnn,
            # agent, specialist, reviewer, system). "operator" has no colon.
            layer = author.split(":", 1)[0] if ":" in author else author
            by_layer[layer] = by_layer.get(layer, 0) + 1
        return {
            "window_hours": 24,
            "total": sum(by_layer.values()),
            "by_layer": by_layer,
        }
    except Exception:
        return {"window_hours": 24, "total": 0, "by_layer": {}}


def _get_recent_md_signal_sync(user_id: str, client: Any) -> dict:
    """ADR-220 Commit C: signal about /workspace/memory/recent.md.

    Returns metadata enough to render the compact-index one-liner without
    loading the full file content. Counterpart to recent_authorship (which
    summarizes substrate mutations); recent.md summarizes narrative
    invocations (reviewer verdicts, agent task completions, MCP writes,
    system events) — material non-conversation entries written by
    narrative_digest task.

    Returns: {"exists": bool, "total": int, "by_role": dict, "updated_at": iso | None}.
    Quiet/missing returns {"exists": False, "total": 0, "by_role": {}, "updated_at": None}.

    Implementation: parse the markdown header lines we write in
    `narrative_digest._format_recent_md` ("Last updated: X · 24h window · N material entries"
    + per-role section headers like "## Reviewer verdicts (N)"). Avoid loading
    the full file body — we only need the signal. If the file is missing or
    can't be parsed, surface as not-exists and the compact index renders no
    pointer.
    """
    try:
        result = (
            client.table("workspace_files")
            .select("content, updated_at")
            .eq("user_id", user_id)
            .eq("path", "/workspace/memory/recent.md")
            .limit(1)
            .execute()
        )
        if not result.data:
            return {"exists": False, "total": 0, "by_role": {}, "updated_at": None}
        row = result.data[0]
        content = row.get("content") or ""
        if not content.strip():
            return {"exists": False, "total": 0, "by_role": {}, "updated_at": None}

        # Parse the per-role section counts. Pattern: "## {Header} (N)".
        import re
        by_role: dict[str, int] = {}
        # Map header text → role-key for the compact-index summary.
        header_to_role = {
            "Reviewer verdicts": "reviewer",
            "Agent task completions": "agent",
            "External (MCP) writes": "external",
            "System events": "system",
        }
        for header_text, role_key in header_to_role.items():
            m = re.search(rf"^##\s+{re.escape(header_text)}\s+\((\d+)\)\s*$", content, re.MULTILINE)
            if m:
                by_role[role_key] = int(m.group(1))

        # Total: sum of per-role counts (not the header line — the header line
        # may include older entries beyond what's rendered, but per-role section
        # counts are authoritative).
        total = sum(by_role.values())
        return {
            "exists": True,
            "total": total,
            "by_role": by_role,
            "updated_at": row.get("updated_at"),
        }
    except Exception:
        return {"exists": False, "total": 0, "by_role": {}, "updated_at": None}


def _get_recent_uploads_sync(user_id: str, client: Any) -> list[dict]:
    """Recent document uploads (sync, for thread pool). ADR-162 Sub-phase B.

    Returns documents uploaded in the last 7 days. Used by the compact index
    to surface "pending uploads" — uploads that arrived outside an active
    chat session and that TP should consider processing via UpdateContext.

    The 7-day window is intentionally generous: a user who uploads on day 1
    and chats on day 5 should still see TP offer to read the document. Older
    uploads are not surfaced because they've either been processed already or
    the user has explicitly chosen not to mention them.
    """
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        result = (
            client.table("filesystem_documents")
            .select("id, filename, uploaded_at")
            .eq("user_id", user_id)
            .gte("uploaded_at", cutoff)
            .order("uploaded_at", desc=True)
            .limit(5)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


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
    """Get context domain health summary for TP awareness (sync). ADR-174 Phase 1.

    Filesystem-first: queries workspace_files for all paths under /workspace/context/,
    groups by the first directory segment after context/. Registry provides display
    names and temporal flags as a lookup layer — it does not determine what gets reported.

    Domains created by TP outside the declared registry (e.g., /workspace/context/customers/)
    appear automatically as soon as they contain files. No registry update required.

    Returns list of {domain, file_count, latest_update, health, temporal} for each
    non-empty directory found under /workspace/context/.
    """
    from services.directory_registry import WORKSPACE_DIRECTORIES

    # Build a registry lookup for display metadata (temporal flag, known domain keys).
    # Keys are the directory segment name (e.g., "competitors", "slack").
    registry_meta: dict[str, dict] = {}
    for key, defn in WORKSPACE_DIRECTORIES.items():
        path = defn.get("path", "")
        if path.startswith("context/"):
            segment = path[len("context/"):].rstrip("/")
            if segment:
                registry_meta[segment] = {
                    "temporal": defn.get("temporal", False),
                }

    try:
        # Single query: all files under /workspace/context/ for this user.
        result = (
            client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/%")
            .in_("lifecycle", ["active", "delivered"])
            .execute()
        )
        rows = result.data or []
    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] context domain query failed: {e}")
        return []

    # Group by first directory segment after /workspace/context/
    from collections import defaultdict
    groups: dict[str, list[str]] = defaultdict(list)  # segment → [updated_at, ...]
    for row in rows:
        path = row.get("path", "")
        # /workspace/context/{segment}/...
        remainder = path[len("/workspace/context/"):]
        if not remainder:
            continue
        segment = remainder.split("/")[0]
        if segment:
            groups[segment].append(row.get("updated_at", ""))

    domains = []
    for segment, timestamps in sorted(groups.items()):
        file_count = len(timestamps)
        latest = max(t for t in timestamps if t)[:10] if any(timestamps) else None
        meta = registry_meta.get(segment, {})
        domains.append({
            "domain": segment,
            "file_count": file_count,
            "latest_update": latest,
            "health": "active" if file_count > 1 else "seeded",
            "temporal": meta.get("temporal", False),
        })

    return domains


def _get_user_memory_files_sync(user_id: str, client: Any) -> dict[str, str]:
    """Read /memory/ files from workspace_files (sync, for thread pool). ADR-108."""
    from services.workspace import UserMemory
    um = UserMemory(client, user_id)
    return um.read_all_sync()


    # _get_work_index_sync DELETED (ADR-156: WORK.md dissolved post ADR-132)


    # _extract_profile_from_file DELETED (ADR-156: IDENTITY.md renders directly)


def _extract_preferences_from_file(content: Optional[str]) -> list[dict]:
    """Extract preferences from style.md content. ADR-108."""
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
      - agent_framework.py (ALL_ROLES — capability bundles per type)
      - Connected platforms (from working memory query)
    """
    from services.orchestration import ALL_ROLES, has_asset_capabilities

    # --- Agent types (ADR-130: deterministic capability bundles) ---
    roles = []
    for type_name, type_def in ALL_ROLES.items():
        if type_name == "pm":
            continue  # PM type removed
        roles.append({
            "role": type_name,
            "capabilities": type_def["capabilities"],
            "has_asset_capabilities": has_asset_capabilities(type_name),
            "description": type_def.get("description", ""),
        })

    # --- Connected platform names (derived from already-fetched platforms) ---
    connected = [p.get("platform") for p in platforms if p.get("status") == "active"]

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
    """Fetch connected platform summary (sync, for thread pool)."""
    from services.freshness import calculate_freshness

    platforms = []

    try:
        # Get connections for status
        conn_result = client.table("platform_connections").select(
            "platform, status, landscape"
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
            landscape = p.get("landscape", {}) or {}
            selected_sources = landscape.get("selected_sources", []) or []

            platforms.append({
                "platform": platform_name,
                "status": status,
                "last_activity_at": last_synced,
                "freshness": calculate_freshness(last_synced, now),
                "selected_sources_count": len(selected_sources),
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
    """Build structured system summary (sync, for thread pool)."""
    summary: dict[str, Any] = {
        "pending_reviews_count": 0,
        "failed_jobs_24h": 0,
    }

    try:
        # Pending reviews (agent versions with status=draft)
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


def _get_balance_sync(user_id: str, client: Any) -> dict:
    """Fetch effective balance status (sync, for thread pool). ADR-172."""
    try:
        from services.platform_limits import get_effective_balance
        balance = get_effective_balance(client, user_id)
        return {"balance": round(balance, 4), "exhausted": balance <= 0}
    except Exception as e:
        logger.warning(f"[WORKING_MEMORY] Failed to fetch balance: {e}")
        return {"balance": 0.0, "exhausted": False}


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


def _format_entity_index(working_memory: dict, surface_context: Optional[dict] = None) -> str:
    """ADR-186: Compact index for entity-scoped profile.

    Shows: entity being viewed, its relevant context domains, one-line workspace
    summary, balance status, memory file references. Omits: full task list, full
    domain list, onboarding gaps, team summary, recent uploads.

    Target: ~300 tokens (well under the 600-token ceiling).
    """
    lines = ["## Entity Context\n"]

    # --- One-line workspace summary (escape hatch) ---
    ws = working_memory.get("workspace_state", {})
    tasks_active = ws.get("tasks_active", 0)
    domains_active = ws.get("context_domains", 0)
    lines.append(f"Workspace: {tasks_active} active tasks | {domains_active} context domains")

    # Balance warning (only if exhausted)
    if ws.get("balance_exhausted"):
        lines.append(f"- Balance: EXHAUSTED")

    # --- Surface context (what entity the user is viewing) ---
    if surface_context:
        task_slug = surface_context.get("taskSlug")
        agent_slug = surface_context.get("agentSlug")
        if task_slug:
            lines.append(f"\nScoped to task: **{task_slug}**")
            # Find this task in active_tasks for freshness info
            active_tasks = working_memory.get("active_tasks", [])
            for t in active_tasks:
                if t.get("slug") == task_slug:
                    parts = []
                    if t.get("mode"):
                        parts.append(t["mode"])
                    if t.get("schedule"):
                        parts.append(t["schedule"])
                    if t.get("status"):
                        parts.append(t["status"])
                    if t.get("last_run"):
                        parts.append(f"last ran {t['last_run']}")
                    if t.get("next_run"):
                        parts.append(f"next {t['next_run']}")
                    if parts:
                        lines.append(f"- {' · '.join(parts)}")
                    break
        elif agent_slug:
            lines.append(f"\nScoped to agent: **{agent_slug}**")

    # --- Context domains relevant to this entity (compact) ---
    context_domains = working_memory.get("context_domains", [])
    if context_domains:
        # Show all domains but very compact — entity profile needs domain awareness
        # for feedback routing (domain changes vs task changes)
        canonical = [d for d in context_domains if not d.get("temporal") and d.get("file_count", 0) > 0]
        if canonical:
            domain_strs = [f"{d['domain']}/ ({d.get('file_count', 0)})" for d in canonical[:6]]
            lines.append(f"\nDomains: {', '.join(domain_strs)}")

    # --- Agent health flags (only if flagged) ---
    flagged = ws.get("agents_flagged", [])
    if flagged:
        lines.append("\nAgent health flags:")
        for ah in flagged:
            lines.append(f"- {ah['title']}: {ah['flag']}")

    # --- Key file references (always included) ---
    lines.append("\n### Key files (read with LookupEntity or entity-layer tools)")
    lines.append("- `/workspace/context/_shared/MANDATE.md` — what the workspace is running")
    lines.append("- `/workspace/context/_shared/AUTONOMY.md` — delegation ceiling")
    lines.append("- `/workspace/context/_shared/PRECEDENT.md` — durable interpretations and boundary cases")
    lines.append("- `/workspace/context/_shared/IDENTITY.md` — who the user is")
    lines.append("- `/workspace/memory/awareness.md` — your shift notes")
    lines.append("- `/workspace/memory/notes.md` — stable facts and preferences")

    return "\n".join(lines)


def format_compact_index(
    working_memory: dict,
    surface_context: Optional[dict] = None,
    profile: str = "workspace",
) -> str:
    """
    ADR-159 + ADR-168 + ADR-174 + ADR-186: Compact index for TP system prompt.

    ADR-186: Profile-aware rendering.
      - "workspace": Full workspace overview (all tasks, all domains, all health).
      - "entity": Scoped to the entity being viewed (entity health, its domains,
        one-line workspace summary for escape-hatch awareness).

    Hard 600-token ceiling (ADR-174 Phase 1). Enforced after formatting:
    - Dev: AssertionError if exceeded (catches regressions early)
    - Prod: Warning logged + deterministic truncation applied

    Three tiers:
      1. This compact index (always in prompt)
      2. Last 5 messages (rolling window, handled by chat.py)
      3. On-demand files (TP reads via LookupEntity for entity-layer refs)
    """
    # ADR-186: Entity profile gets a scoped compact index
    if profile == "entity":
        return _format_entity_index(working_memory, surface_context)

    lines = ["## Workspace Index\n"]

    # --- Workspace state (unified signal) ---
    ws = working_memory.get("workspace_state", {})
    identity = ws.get("identity", "empty")
    brand = ws.get("brand", "empty")
    tasks_active = ws.get("tasks_active", 0)
    tasks_stale = ws.get("tasks_stale", 0)
    docs = ws.get("documents", 0)
    domains_active = ws.get("context_domains", 0)

    # ADR-206: Three operator-facing layers. Compact index now renders
    # Intent (authored rules), Deliverables (what the operator sees and acts on),
    # Operation (execution substrate) as labeled sections so YARNNN reasons in
    # the operator's vocabulary, not task-slug internals.

    # === Intent (authored rules) ===
    lines.append("### Intent (authored rules)")
    lines.append(f"- Identity: {identity} · Brand: {brand} · {docs} uploaded documents")
    if identity in ("empty", "sparse"):
        lines.append("- Gap: workspace identity not declared — elicit operation + domain + platform + rules")
    if ws.get("budget_exhausted"):
        lines.append(f"- Budget: EXHAUSTED ({ws.get('credits_used', 0)}/{ws.get('credits_limit', 0)})")

    # === Deliverables (what the operator sees and acts on) ===
    lines.append("\n### Deliverables (the operator's surface)")
    proposals_pending = ws.get("proposals_pending", 0)
    if proposals_pending:
        lines.append(f"- {proposals_pending} proposal{'s' if proposals_pending != 1 else ''} awaiting review (/review)")
    active_tasks = working_memory.get("active_tasks", [])
    produces_deliverable = [t for t in active_tasks if (t.get("output_kind") or "").strip() == "produces_deliverable"]
    if produces_deliverable:
        lines.append(f"- {len(produces_deliverable)} deliverable-producing task{'s' if len(produces_deliverable) != 1 else ''} in the loop")
    if tasks_stale > 0:
        lines.append(f"- {tasks_stale} task{'s' if tasks_stale != 1 else ''} stale (past expected cadence)")
    if proposals_pending == 0 and not produces_deliverable and tasks_stale == 0 and identity == "rich":
        lines.append("- No proposals pending, no deliverables scheduled. Offer to start a loop.")

    # === Operation (execution substrate — drill-down only) ===
    lines.append("\n### Operation (infrastructure — drill-down only)")
    lines.append(f"- {tasks_active} active task{'s' if tasks_active != 1 else ''} · {domains_active} context domain{'s' if domains_active != 1 else ''}")
    agents = working_memory.get("agents", [])
    real_agents = [a for a in agents if "_note" not in a]
    user_authored = [a for a in real_agents if a.get("origin") not in ("system_bootstrap",)]
    if user_authored:
        lines.append(f"- {len(user_authored)} user-authored agent{'s' if len(user_authored) != 1 else ''}")

    # --- Active tasks (compact: slug + schedule + freshness) ---
    if active_tasks:
        lines.append(f"\nActive tasks ({len(active_tasks)}):")
        for t in active_tasks[:8]:  # Cap at 8
            parts = [f"**{t['slug']}**"]
            if t.get("schedule"):
                parts.append(t["schedule"])
            else:
                parts.append("on-demand")
            if t.get("last_run"):
                parts.append(f"ran {t['last_run']}")
            if t.get("next_run"):
                parts.append(f"next {t['next_run']}")
            lines.append(f"- {' · '.join(parts)}")

    # --- Context domains (one line each: name + health) ---
    context_domains = working_memory.get("context_domains", [])
    if context_domains:
        canonical = [d for d in context_domains if not d.get("temporal")]
        temporal = [d for d in context_domains if d.get("temporal") and d.get("file_count", 0) > 0]
        if canonical:
            lines.append("\nDomains:")
            for d in canonical:
                count = d.get("file_count", 0)
                health = d.get("health", "empty")
                lines.append(f"- {d['domain']}/: {health} ({count} files)")
        if temporal:
            lines.append("\nPlatform observations:")
            for d in temporal:
                lines.append(f"- {d['domain']}/: {d.get('file_count', 0)} files")

    # --- Platforms (connected status only) ---
    platforms = working_memory.get("platforms", [])
    connected = [p for p in platforms if p.get("status") == "active"]
    if connected:
        names = ", ".join(p.get("platform", "?") for p in connected)
        lines.append(f"\nPlatforms: {names}")

    # --- Recent uploads (ADR-162 Sub-phase B) ---
    # Surface uploads from the last 7 days. TP should proactively offer to
    # process these via UpdateContext when the user is in chat. Empty list
    # means no recent uploads — silent.
    recent_uploads = working_memory.get("recent_uploads", [])
    if recent_uploads:
        lines.append(f"\nRecent uploads ({len(recent_uploads)} in last 7 days) — consider offering to process via UpdateContext:")
        for u in recent_uploads[:3]:
            lines.append(f"- {u.get('filename', 'document')} (uploaded {u.get('uploaded_at', '')[:10]})")

    # --- Recent substrate authorship (ADR-209 Phase 3) ---
    # One compact line: who has been writing to the workspace lately. Helps
    # YARNNN reason about current activity ("the operator just edited X"
    # / "the reconciler ran") without reading files. Silent when quiet.
    authorship = working_memory.get("recent_authorship") or {}
    if authorship.get("total", 0) > 0:
        by_layer = authorship.get("by_layer") or {}
        # Render in priority order so the operator's activity leads.
        priority = ["operator", "yarnnn", "reviewer", "agent", "specialist", "system"]
        parts = []
        for layer in priority:
            n = by_layer.get(layer, 0)
            if n:
                parts.append(f"{layer} ({n})")
        if parts:
            lines.append(f"\nRecent activity (24h, {authorship['total']} revisions): {', '.join(parts)} — use ListRevisions/ReadRevision/DiffRevisions to inspect.")

    # --- Recent narrative events (ADR-220 Commit C) ---
    # Counterpart to the substrate-authorship line above. The substrate axis
    # answers "who wrote what file"; this axis answers "what invocations
    # happened" — material non-conversation entries (reviewer verdicts, agent
    # task completions, MCP writes, system events) rolled up into recent.md
    # by the narrative_digest task. YARNNN reads recent.md on demand.
    recent_md = working_memory.get("recent_md") or {}
    if recent_md.get("exists") and recent_md.get("total", 0) > 0:
        by_role = recent_md.get("by_role") or {}
        # Display order: operator-facing first.
        priority = ["reviewer", "agent", "external", "system"]
        parts = []
        for role in priority:
            n = by_role.get(role, 0)
            if n:
                parts.append(f"{n} {role}")
        if parts:
            lines.append(
                f"\nRecent events (24h, {recent_md['total']} material non-conversation): "
                f"{', '.join(parts)} — read /workspace/memory/recent.md if needed."
            )

    # --- Surface context (what user is currently viewing) ---
    if surface_context:
        page = surface_context.get("type", "chat")
        agent_slug = surface_context.get("agentSlug")
        task_slug = surface_context.get("taskSlug")
        if agent_slug:
            lines.append(f"\nCurrently viewing: Agents > {agent_slug}")
            # Surface-aware: include agent's domain detail
            scoped = working_memory.get("scoped_agent")
            if scoped:
                title = scoped.get("title", agent_slug)
                instructions = scoped.get("instructions")
                if instructions:
                    # First 200 chars of AGENT.md as context
                    preview = instructions.strip()[:200]
                    if len(instructions.strip()) > 200:
                        preview += "..."
                    lines.append(f"Agent instructions preview: {preview}")
                lines.append(f"(Read full AGENT.md: `/agents/{agent_slug}/AGENT.md`)")
        elif task_slug:
            lines.append(f"\nCurrently viewing: Task > {task_slug}")
            lines.append(f"(Read full task: `/tasks/{task_slug}/TASK.md`)")
        elif page == "context":
            lines.append("\nCurrently viewing: Context (workspace explorer)")
        else:
            lines.append("\nCurrently viewing: Home")

    # --- Prior conversation context (brief preview) ---
    conversation_summary = working_memory.get("conversation_summary")
    if conversation_summary and conversation_summary.strip():
        # Extract just the first 3 lines of content (after the header)
        conv_lines = [l for l in conversation_summary.strip().split("\n") if l.strip() and not l.startswith("#")]
        if conv_lines:
            preview = " | ".join(conv_lines[:3])
            if len(preview) > 200:
                preview = preview[:200] + "..."
            lines.append(f"\nPrior conversation: {preview}")

    # --- File references (TP reads on demand) ---
    lines.append("\n### Key files (read with ReadFile if you need detail)")
    lines.append("- `/workspace/context/_shared/MANDATE.md` — what the workspace is running")
    lines.append("- `/workspace/context/_shared/AUTONOMY.md` — delegation ceiling")
    lines.append("- `/workspace/context/_shared/PRECEDENT.md` — durable interpretations and boundary cases")
    lines.append("- `/workspace/context/_shared/IDENTITY.md` — who the user is")
    lines.append("- `/workspace/context/_shared/BRAND.md` — visual style and voice")
    lines.append("- `/workspace/memory/awareness.md` — your shift notes from prior sessions")
    lines.append("- `/workspace/memory/conversation.md` — summary of earlier conversation")
    lines.append("- `/workspace/memory/notes.md` — stable facts and user preferences")
    lines.append("- `/workspace/memory/recent.md` — recent material non-conversation events (ADR-220)")

    # --- Agent health flags (only if flagged) ---
    flagged = ws.get("agents_flagged", [])
    if flagged:
        lines.append("\nAgent health flags:")
        for ah in flagged:
            lines.append(f"- {ah['title']}: {ah['flag']}")

    output = "\n".join(lines)

    # ADR-174 Phase 1: 600-token ceiling enforcement.
    # 1 token ≈ 4 chars (conservative estimate).
    _TOKEN_CEILING = 600
    _CHAR_CEILING = _TOKEN_CEILING * 4  # 2400 chars

    if len(output) > _CHAR_CEILING:
        import os
        if os.environ.get("ENV", "production") == "development":
            actual_tokens = len(output) // 4
            raise AssertionError(
                f"format_compact_index exceeded {_TOKEN_CEILING}-token ceiling: "
                f"~{actual_tokens} tokens ({len(output)} chars). "
                f"Trim the offending section."
            )
        else:
            logger.warning(
                f"[WORKING_MEMORY] compact index exceeded ceiling: "
                f"~{len(output)//4} tokens. Truncating."
            )
            output = output[:_CHAR_CEILING] + "\n... (truncated — workspace index too large)"

    return output



# format_for_prompt() DELETED — was legacy 3-8K token dump, superseded by
# format_compact_index() (ADR-159). Zero production callers (only tests).
# Removed 2026-04-16 per singular implementation discipline.
