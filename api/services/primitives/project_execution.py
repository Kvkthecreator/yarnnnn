"""
Project Execution Primitives — ADR-120 Phase 1

PM-specific primitives for project coordination:
  CheckContributorFreshness — assess which contributors have new output
  ReadProjectStatus         — full project state (identity + freshness + assemblies + work plan)
  RequestContributorAdvance — advance a contributor's schedule to run now

All headless-only. Used by PM agents to coordinate projects.
"""

from __future__ import annotations

import json as _json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CheckContributorFreshness (headless only, ADR-120 Phase 1)
# =============================================================================

CHECK_CONTRIBUTOR_FRESHNESS_TOOL = {
    "name": "CheckContributorFreshness",
    "description": """Check which project contributors have fresh output since the last assembly.

For each contributor listed in PROJECT.md, checks when they last wrote to the
project's contributions/ folder. Compares against the last assembly date.

Returns per-contributor freshness and whether all contributions are ready.

Required: project_slug""",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_slug": {
                "type": "string",
                "description": "Project slug (e.g., 'q2-business-review')",
            },
        },
        "required": ["project_slug"],
    },
}


async def handle_check_contributor_freshness(auth: Any, input: dict) -> dict:
    """
    For each contributor in PROJECT.md, query their latest contribution date.
    Compare against last assembly date.
    """
    from services.workspace import ProjectWorkspace

    project_slug = input.get("project_slug", "").strip()
    if not project_slug:
        return {"success": False, "error": "missing_slug", "message": "project_slug is required"}

    pw = ProjectWorkspace(auth.client, auth.user_id, project_slug)

    # Read project identity
    project = await pw.read_project()
    if not project:
        return {
            "success": False,
            "error": "not_found",
            "message": f"Project not found: /projects/{project_slug}/",
        }

    # Get last assembly date
    assemblies = await pw.list_assemblies()
    last_assembly_date = None
    if assemblies:
        # Assemblies are date-named folders — latest is last when sorted
        sorted_assemblies = sorted(assemblies)
        last_assembly_date = sorted_assemblies[-1].rstrip("/")

    # Check each contributor's latest contribution
    contributors_status = []
    for c in project.get("contributors", []):
        agent_slug = c.get("agent_slug", "")
        if not agent_slug:
            continue

        # Query latest file in contributions/{agent_slug}/
        try:
            result = (
                auth.client.table("workspace_files")
                .select("updated_at")
                .eq("user_id", auth.user_id)
                .like("path", f"/projects/{project_slug}/contributions/{agent_slug}/%")
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                last_contribution = rows[0]["updated_at"]
                last_dt = datetime.fromisoformat(last_contribution.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - last_dt).days
                is_fresh = True
                if last_assembly_date:
                    is_fresh = last_contribution > last_assembly_date
            else:
                last_contribution = None
                days_since = None
                is_fresh = False
        except Exception as e:
            logger.warning(f"[PM] Freshness check failed for {agent_slug}: {e}")
            last_contribution = None
            days_since = None
            is_fresh = False

        contributors_status.append({
            "agent_slug": agent_slug,
            "expected_contribution": c.get("expected_contribution", ""),
            "last_contribution": last_contribution,
            "is_fresh": is_fresh,
            "days_since": days_since,
        })

    all_fresh = all(c["is_fresh"] for c in contributors_status) if contributors_status else False

    return {
        "success": True,
        "project_slug": project_slug,
        "contributors": contributors_status,
        "last_assembly_date": last_assembly_date,
        "all_fresh": all_fresh,
    }


# =============================================================================
# ReadProjectStatus (headless only, ADR-120 Phase 1)
# =============================================================================

READ_PROJECT_STATUS_TOOL = {
    "name": "ReadProjectStatus",
    "description": """Read full project status: identity, contributor freshness, assemblies, and work plan.

Combines PROJECT.md parsing, contributor freshness check, assembly history,
and work plan into a single comprehensive view.

Required: project_slug""",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_slug": {
                "type": "string",
                "description": "Project slug (e.g., 'q2-business-review')",
            },
        },
        "required": ["project_slug"],
    },
}


async def handle_read_project_status(auth: Any, input: dict) -> dict:
    """Full project status: identity + freshness + assemblies + work plan."""
    from services.workspace import ProjectWorkspace

    project_slug = input.get("project_slug", "").strip()
    if not project_slug:
        return {"success": False, "error": "missing_slug", "message": "project_slug is required"}

    pw = ProjectWorkspace(auth.client, auth.user_id, project_slug)

    # Project identity
    project = await pw.read_project()
    if not project:
        return {
            "success": False,
            "error": "not_found",
            "message": f"Project not found: /projects/{project_slug}/",
        }

    # Freshness (reuse the handler)
    freshness = await handle_check_contributor_freshness(auth, {"project_slug": project_slug})

    # Assembly history
    assemblies = await pw.list_assemblies()

    # Work plan (stored as /projects/{slug}/memory/work_plan.md)
    work_plan = await pw.read("memory/work_plan.md")

    return {
        "success": True,
        "project_slug": project_slug,
        "project": project,
        "freshness": freshness.get("contributors", []),
        "all_fresh": freshness.get("all_fresh", False),
        "last_assembly_date": freshness.get("last_assembly_date"),
        "assemblies": assemblies,
        "work_plan": work_plan,
    }


# =============================================================================
# RequestContributorAdvance (headless only, ADR-120 Phase 1)
# =============================================================================

REQUEST_CONTRIBUTOR_ADVANCE_TOOL = {
    "name": "RequestContributorAdvance",
    "description": """Advance a contributor agent's schedule to run now.

Used by PM agents when a specific contributor is stale or blocking assembly.
Looks up the agent by slug within the project's contributor list, then
advances their schedule (sets next_run_at to now).

Required: project_slug, agent_slug
Optional: reason""",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_slug": {
                "type": "string",
                "description": "Project slug",
            },
            "agent_slug": {
                "type": "string",
                "description": "Contributor agent slug to advance",
            },
            "reason": {
                "type": "string",
                "description": "Why this advance is needed",
            },
        },
        "required": ["project_slug", "agent_slug"],
    },
}


async def handle_request_contributor_advance(auth: Any, input: dict) -> dict:
    """
    Look up agent by slug within the project, then advance their schedule.
    """
    from services.workspace import ProjectWorkspace, get_agent_slug

    project_slug = input.get("project_slug", "").strip()
    agent_slug = input.get("agent_slug", "").strip()
    reason = input.get("reason", "PM requested advance")

    if not project_slug or not agent_slug:
        return {"success": False, "error": "missing_params", "message": "project_slug and agent_slug are required"}

    pw = ProjectWorkspace(auth.client, auth.user_id, project_slug)

    # Verify project exists and this agent is a contributor
    project = await pw.read_project()
    if not project:
        return {"success": False, "error": "not_found", "message": f"Project not found: {project_slug}"}

    contributor_slugs = [c.get("agent_slug") for c in project.get("contributors", [])]
    if agent_slug not in contributor_slugs:
        return {
            "success": False,
            "error": "not_contributor",
            "message": f"Agent '{agent_slug}' is not a contributor to project '{project_slug}'",
        }

    # Find the agent record by slug match (slug is derived from title)
    # We need to search agents table for this user where the derived slug matches
    try:
        result = (
            auth.client.table("agents")
            .select("id, title, next_run_at")
            .eq("user_id", auth.user_id)
            .eq("status", "active")
            .execute()
        )
        target_agent = None
        for a in (result.data or []):
            if get_agent_slug(a) == agent_slug:
                target_agent = a
                break

        if not target_agent:
            return {
                "success": False,
                "error": "agent_not_found",
                "message": f"Active agent with slug '{agent_slug}' not found",
            }

        # Advance schedule: set next_run_at to now
        now = datetime.now(timezone.utc).isoformat()
        auth.client.table("agents").update({
            "next_run_at": now,
            "updated_at": now,
        }).eq("id", target_agent["id"]).execute()

        logger.info(f"[PM] Advanced contributor {agent_slug} for project {project_slug}: {reason}")

        return {
            "success": True,
            "agent_slug": agent_slug,
            "agent_id": target_agent["id"],
            "next_run_at": now,
            "reason": reason,
            "message": f"Advanced {agent_slug}'s schedule to now. Reason: {reason}",
        }

    except Exception as e:
        logger.error(f"[PM] Failed to advance contributor {agent_slug}: {e}")
        return {"success": False, "error": "advance_failed", "message": str(e)}
