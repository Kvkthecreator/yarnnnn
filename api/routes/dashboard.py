"""
Dashboard routes — ADR-122 Phase 5: Project-first dashboard.

Minimal, clean payload: projects with nested agents (excluding PMs),
connected platforms, attention items. No computed stats, no maturity
recomputation, no composer feed — those return when underlying data
handling is refactored.

All agents belong to projects (ADR-122). Standalone agents removed
from dashboard — accessible at /agents directly.

Mounted at /api/dashboard
"""

import json as _json
import logging
import re

from fastapi import APIRouter
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

from services.supabase import UserClient

router = APIRouter()


def _extract_type_key(content: str) -> str | None:
    """Extract type_key from PROJECT.md content without full parse."""
    match = re.search(r'\*\*Type\*\*:\s*(\S+)', content or "")
    return match.group(1) if match else None


def _extract_title(content: str) -> str:
    """Extract title (first H1) from PROJECT.md content."""
    for line in (content or "").split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_purpose(content: str) -> str | None:
    """Extract Purpose from PROJECT.md Objective section."""
    in_objective = False
    for line in (content or "").split("\n"):
        if line.strip().startswith("## Objective"):
            in_objective = True
            continue
        if in_objective and line.strip().startswith("## "):
            break
        if in_objective and "**Purpose**:" in line:
            return line.split("**Purpose**:", 1)[1].strip()
    return None


@router.get("/summary")
async def get_dashboard_summary(client: UserClient):
    """
    GET /api/dashboard/summary

    Project-first dashboard payload. Three queries:
    1. agents (non-archived)
    2. platform_connections (connected)
    3. workspace_files (PROJECT.md + memory/projects.json)
    """
    user_id = client.user_id
    db = client.client

    # ── 1. All non-archived agents ──────────────────────────────────────
    agents_raw = []
    try:
        result = (
            db.table("agents")
            .select("id, title, status, origin, role, scope, sources, last_run_at, next_run_at, schedule")
            .eq("user_id", user_id)
            .neq("status", "archived")
            .execute()
        )
        agents_raw = result.data or []
    except Exception as e:
        logger.warning(f"[DASHBOARD] Agent query failed: {e}")

    agents_by_id = {a["id"]: a for a in agents_raw}

    # ── 2. Connected platforms ──────────────────────────────────────────
    connected_platforms = []
    try:
        result = (
            db.table("platform_connections")
            .select("platform, status")
            .eq("user_id", user_id)
            .in_("status", ["connected", "active"])
            .execute()
        )
        connected_platforms = [r["platform"] for r in (result.data or [])]
    except Exception as e:
        logger.warning(f"[DASHBOARD] Platform query failed: {e}")

    # ── 3. Workspace files: PROJECT.md + memory/projects.json ───────────
    # Single query for both project identity and agent→project memberships
    workspace_rows = []
    try:
        result = (
            db.table("workspace_files")
            .select("path, content, summary, updated_at, lifecycle")
            .eq("user_id", user_id)
            .or_("path.like./projects/%/PROJECT.md,path.like./agents/%/memory/projects.json")
            .in_("lifecycle", ["active", "delivered"])
            .execute()
        )
        workspace_rows = result.data or []
    except Exception as e:
        logger.warning(f"[DASHBOARD] Workspace query failed: {e}")

    # Parse projects
    projects_map: dict[str, dict] = {}  # slug → project info
    for row in workspace_rows:
        path = row["path"]
        if path.endswith("/PROJECT.md"):
            parts = path.split("/")
            if len(parts) >= 3:
                slug = parts[2]
                content = row.get("content", "")
                projects_map[slug] = {
                    "project_slug": slug,
                    "title": _extract_title(content),
                    "type_key": _extract_type_key(content),
                    "purpose": _extract_purpose(content),
                    "updated_at": row.get("updated_at"),
                    "agents": [],  # populated below (excludes PM agents)
                }

    # Parse agent→project memberships
    agent_project_map: dict[str, list[str]] = {}  # agent_slug → [project_slugs]
    for row in workspace_rows:
        path = row["path"]
        if path.endswith("/memory/projects.json"):
            # Extract agent slug from /agents/{slug}/memory/projects.json
            parts = path.split("/")
            if len(parts) >= 4:
                agent_slug = parts[2]
                try:
                    memberships = _json.loads(row.get("content", "[]"))
                    for m in memberships:
                        ps = m.get("project_slug", "")
                        if ps:
                            agent_project_map.setdefault(agent_slug, []).append(ps)
                except (_json.JSONDecodeError, TypeError):
                    pass

    # Build agent slug → agent_id reverse lookup
    from services.workspace import get_agent_slug
    slug_to_id: dict[str, str] = {}
    for agent in agents_raw:
        slug = get_agent_slug(agent)
        slug_to_id[slug] = agent["id"]

    # Assign agents to projects (PM agents excluded — they're infrastructure)
    for agent_slug, project_slugs in agent_project_map.items():
        agent_id = slug_to_id.get(agent_slug)
        if not agent_id or agent_id not in agents_by_id:
            continue
        agent = agents_by_id[agent_id]
        if agent.get("role") == "pm":
            continue
        for ps in project_slugs:
            if ps in projects_map:
                projects_map[ps]["agents"].append(_format_agent(agent))

    # Projects sorted by updated_at desc
    projects = sorted(projects_map.values(), key=lambda p: p.get("updated_at") or "", reverse=True)

    # ── 4. Attention items ──────────────────────────────────────────────
    attention = []
    for a in agents_raw:
        if a.get("status") == "paused" and a.get("origin") in ("composer", "system_bootstrap"):
            # Find which project this agent belongs to
            a_slug = get_agent_slug(a)
            project_slugs = agent_project_map.get(a_slug, [])
            if project_slugs and project_slugs[0] in projects_map:
                proj = projects_map[project_slugs[0]]
                attention.append({
                    "type": "auto_paused",
                    "message": f"'{proj['title']}' project: '{a['title']}' was auto-paused",
                    "agent_id": a["id"],
                    "project_slug": project_slugs[0],
                })
            else:
                attention.append({
                    "type": "auto_paused",
                    "message": f"'{a['title']}' was auto-paused — review or archive",
                    "agent_id": a["id"],
                })

    # Recent failed runs (last 3 days)
    try:
        three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        active_ids = [a["id"] for a in agents_raw if a.get("status") == "active"]
        if active_ids:
            result = (
                db.table("agent_runs")
                .select("agent_id")
                .in_("agent_id", active_ids)
                .eq("status", "failed")
                .gte("created_at", three_days_ago)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            seen = set()
            for row in (result.data or []):
                faid = row["agent_id"]
                if faid not in seen and faid in agents_by_id:
                    seen.add(faid)
                    attention.append({
                        "type": "failed",
                        "message": f"'{agents_by_id[faid]['title']}' had a failed run",
                        "agent_id": faid,
                    })
    except Exception as e:
        logger.warning(f"[DASHBOARD] Failed runs query failed: {e}")

    return {
        "projects": projects,
        "connected_platforms": connected_platforms,
        "attention": attention,
    }


def _format_agent(agent: dict) -> dict:
    """Format an agent row for the dashboard response."""
    return {
        "id": agent["id"],
        "title": agent["title"],
        "status": agent.get("status"),
        "origin": agent.get("origin"),
        "role": agent.get("role"),
        "scope": agent.get("scope"),
        "sources": agent.get("sources", []),
        "last_run_at": agent.get("last_run_at"),
        "next_run_at": agent.get("next_run_at"),
    }
