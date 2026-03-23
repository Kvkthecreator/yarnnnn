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
advances their schedule (sets next_pulse_at to now).

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
            .select("id, title, next_pulse_at")
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

        # Advance schedule: set next_pulse_at to now
        now = datetime.now(timezone.utc).isoformat()
        auth.client.table("agents").update({
            "next_pulse_at": now,
            "updated_at": now,
        }).eq("id", target_agent["id"]).execute()

        logger.info(f"[PM] Advanced contributor {agent_slug} for project {project_slug}: {reason}")

        # ADR-133: Trigger inline execution — don't wait for scheduler cron
        import asyncio
        try:
            # Fetch full agent record for process_agent
            full_agent = auth.client.table("agents").select("*").eq("id", target_agent["id"]).single().execute()
            if full_agent.data:
                from services.agent_pulse import run_agent_pulse
                from jobs.unified_scheduler import process_agent, calculate_next_pulse_at

                async def _run_inline():
                    try:
                        from services.supabase import get_service_client
                        svc = get_service_client()
                        decision = await run_agent_pulse(svc, full_agent.data)
                        if decision.action == "generate":
                            await process_agent(svc, full_agent.data)
                        # Update next_pulse_at after execution
                        next_pulse = calculate_next_pulse_at(full_agent.data, decision)
                        svc.table("agents").update({
                            "next_pulse_at": next_pulse.isoformat(),
                        }).eq("id", target_agent["id"]).execute()
                        logger.info(f"[PM] Inline execution complete for {agent_slug}: {decision.action}")
                    except Exception as e:
                        logger.error(f"[PM] Inline execution failed for {agent_slug}: {e}")

                asyncio.create_task(_run_inline())
                logger.info(f"[PM] Triggered inline execution for {agent_slug}")
        except Exception as e:
            logger.warning(f"[PM] Inline trigger failed (will fall back to scheduler): {e}")

        return {
            "success": True,
            "agent_slug": agent_slug,
            "agent_id": target_agent["id"],
            "next_pulse_at": now,
            "reason": reason,
            "message": f"Advanced {agent_slug} — executing now. Reason: {reason}",
        }

    except Exception as e:
        logger.error(f"[PM] Failed to advance contributor {agent_slug}: {e}")
        return {"success": False, "error": "advance_failed", "message": str(e)}


# =============================================================================
# UpdateWorkPlan (headless only, ADR-123 — renamed from UpdateProjectIntent)
# =============================================================================

UPDATE_WORK_PLAN_TOOL = {
    "name": "UpdateWorkPlan",
    "description": """Update a project's operational plan: assembly spec, delivery config, or work plan.

Used by PM agents to update operational settings. Does NOT change
objective, title, or contributors (those are User/TP/Composer's domain).

assembly_spec and delivery update PROJECT.md (charter).
work_plan updates the PM's memory/work_plan.md (operational planning).

Required: project_slug
Optional: assembly_spec, delivery, work_plan""",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_slug": {
                "type": "string",
                "description": "Project slug",
            },
            "assembly_spec": {
                "type": "string",
                "description": "Updated assembly instructions",
            },
            "delivery": {
                "type": "object",
                "description": "Updated delivery config: {channel, target}",
                "properties": {
                    "channel": {"type": "string"},
                    "target": {"type": "string"},
                },
            },
            "work_plan": {
                "type": "string",
                "description": "Updated work plan markdown (execution schedule, focus areas, budget allocation)",
            },
        },
        "required": ["project_slug"],
    },
}


async def handle_update_work_plan(auth: Any, input: dict) -> dict:
    """
    ADR-123: Update project's operational config.
    assembly_spec + delivery → PROJECT.md (charter, shared).
    work_plan → PM memory/work_plan.md (PM-owned operational planning).
    Preserves objective, title, and contributors — those are User/Composer's domain.
    """
    from services.workspace import ProjectWorkspace

    project_slug = input.get("project_slug", "").strip()
    if not project_slug:
        return {"success": False, "error": "missing_slug", "message": "project_slug is required"}

    pw = ProjectWorkspace(auth.client, auth.user_id, project_slug)

    # Read current project
    project = await pw.read_project()
    if not project:
        return {
            "success": False,
            "error": "not_found",
            "message": f"Project not found: /projects/{project_slug}/",
        }

    updated_fields = []

    # Update charter fields (assembly_spec, delivery) in PROJECT.md
    if "assembly_spec" in input or "delivery" in input:
        updated_assembly_spec = input.get("assembly_spec", project.get("assembly_spec", ""))
        updated_delivery = input.get("delivery", project.get("delivery", {}))

        success = await pw.write_project(
            title=project.get("title", project_slug),
            objective=project.get("objective", {}),
            contributors=project.get("contributors", []),
            assembly_spec=updated_assembly_spec,
            delivery=updated_delivery,
        )
        if not success:
            return {"success": False, "error": "write_failed", "message": "Failed to update PROJECT.md"}

        if "assembly_spec" in input:
            updated_fields.append("assembly_spec")
        if "delivery" in input:
            updated_fields.append("delivery")

    # Update work plan in PM's memory (ADR-123: operational planning in PM memory, not PROJECT.md)
    if "work_plan" in input:
        wp_success = await pw.write(
            "memory/work_plan.md",
            input["work_plan"],
            summary="PM work plan update",
            tags=["work_plan", "pm"],
        )
        if wp_success:
            updated_fields.append("work_plan")
        else:
            return {"success": False, "error": "write_failed", "message": "Failed to update work plan"}

    logger.info(f"[PM] Updated work plan for {project_slug}: {', '.join(updated_fields)}")

    return {
        "success": True,
        "project_slug": project_slug,
        "updated_fields": updated_fields,
        "message": f"Updated {', '.join(updated_fields)} for project '{project.get('title', project_slug)}'",
    }
