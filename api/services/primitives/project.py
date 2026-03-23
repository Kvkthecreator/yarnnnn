"""
Project Primitives — ADR-119 Phase 2

  CreateProject  — creates a project folder with PROJECT.md + seeds contributor workspaces
  ReadProject    — reads project identity, contributors, assemblies

Projects are cross-agent collaboration spaces. Each project lives at
/projects/{slug}/ with a coordination contract (PROJECT.md) that defines
what the assembled output looks like and which agents contribute.
"""

from __future__ import annotations

import json as _json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CreateProject (chat + headless, ADR-119 Phase 2)
# =============================================================================

CREATE_PROJECT_TOOL = {
    "name": "CreateProject",
    "description": """Create a new project. Three modes:

1. **Work project** (recommended — just pass title): The system infers the right agent type,
   lifecycle, and objective from the project name. "Fundraising" → drafter (bounded).
   "Competitive tracking" → scout (persistent). "Client: Acme" → briefer (persistent).
   Every project gets a PM + 1 contributor agent matched to the work type.

2. **Platform project** (use type_key): For platform digests only.
   Available type_keys: slack_digest, notion_digest.
   Auto-creates digest agent + PM. Use when user connects a platform.

3. **Custom project** (explicit agents): Assembles existing agents into a collaboration project.
   Pass title, objective, contributors, assembly_spec, delivery.

MULTI-STEP WORKFLOW — when user uploads a file and wants a project:
1. Use Search to read the uploaded document content
2. Extract: project name, deliverable type, audience, purpose
3. Call CreateProject with informed title + objective
4. The file will be available to the project's agents via Search

Examples:
  CreateProject(title="Fundraising")  ← auto-infers drafter type, bounded lifecycle
  CreateProject(title="Competitive Watch")  ← auto-infers scout type
  CreateProject(title="Slack Recap", type_key="slack_digest")
  CreateProject(
    title="Q2 Board Deck",
    objective={deliverable: "Board presentation", audience: "Investors", format: "presentation", purpose: "Q2 performance review"}
  )""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Project title — also used for agent type inference when no type_key provided"
            },
            "type_key": {
                "type": "string",
                "description": "Project type from registry. Usually NOT needed — type inference from title is preferred. Use only for: slack_digest, notion_digest.",
            },
            "objective": {
                "type": "object",
                "description": "Project objective (north star): {deliverable, audience, format, purpose}",
                "properties": {
                    "deliverable": {"type": "string"},
                    "audience": {"type": "string"},
                    "format": {"type": "string"},
                    "purpose": {"type": "string"},
                },
            },
            "contributors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "expected_contribution": {"type": "string"},
                    },
                    "required": ["agent_id"],
                },
                "description": "Existing agents that contribute to this project (not needed with type_key)",
            },
            "assembly_spec": {
                "type": "string",
                "description": "How contributions combine into the final output",
            },
            "delivery": {
                "type": "object",
                "description": "Delivery config: {channel, target}",
                "properties": {
                    "channel": {"type": "string"},
                    "target": {"type": "string"},
                },
            },
        },
        "required": ["title"],
    },
}


async def handle_create_project(auth: Any, input: dict) -> dict:
    """
    Handle CreateProject primitive.

    If type_key matches a registry entry, delegates to scaffold_project() which
    creates the project AND its member agents together (ADR-122).
    Otherwise falls through to manual project creation (existing contributors).
    """
    from services.workspace import ProjectWorkspace, AgentWorkspace, get_project_slug, get_agent_slug

    title = input.get("title", "").strip()
    if not title:
        return {"success": False, "error": "missing_title", "message": "title is required"}

    objective = input.get("objective", input.get("intent", {}))  # ADR-123: accept both during transition
    contributors_input = input.get("contributors", [])
    assembly_spec = input.get("assembly_spec", "")
    delivery = input.get("delivery", {})
    type_key = input.get("type_key")  # ADR-122: project type registry key

    # ADR-122/132: Registry-based scaffolding — type_key or title-based inference
    if type_key or not contributors_input:
        from services.project_registry import get_project_type, scaffold_project, infer_topic_type

        if type_key:
            # Explicit type_key — platform digests
            ptype = get_project_type(type_key)
            if ptype:
                return await scaffold_project(
                    client=auth.client,
                    user_id=auth.user_id,
                    type_key=type_key,
                    title_override=title if title != ptype["display_name"] else None,
                    objective_override=objective if objective else None,
                    delivery_override=delivery if delivery else None,
                    execute_now=True,
                )
        else:
            # No type_key, no contributors — infer from title (ADR-132 work-first)
            inferred_type, inferred_lifecycle, inferred_purpose = infer_topic_type(title)
            inferred_type_key = "bounded_deliverable" if inferred_lifecycle == "bounded" else "workspace"

            return await scaffold_project(
                client=auth.client,
                user_id=auth.user_id,
                type_key=inferred_type_key,
                scope_name=title,
                objective_override=objective if objective else {
                    "deliverable": f"{title} {'deliverable' if inferred_lifecycle == 'bounded' else 'update'}",
                    "audience": "You",
                    "format": "email",
                    "purpose": inferred_purpose,
                },
                contributors_override=[{
                    "title_template": f"{{scope_name}} {inferred_type.title()}",
                    "role": inferred_type,
                    "scope": "cross_platform",
                    "frequency": "weekly" if inferred_lifecycle == "persistent" else "on_demand",
                    "sources_from": "work_unit",
                }] if inferred_type != "briefer" else None,
                delivery_override=delivery if delivery else None,
                execute_now=True,
            )

    project_slug = get_project_slug(title)

    # Resolve contributor agents → get their slugs
    # Supports UUID, slug, or title as agent_id (Orchestrator may pass any form)
    contributors = []
    for c in contributors_input:
        agent_id = c.get("agent_id", "").strip()
        expected = c.get("expected_contribution", "")
        if not agent_id:
            continue

        try:
            agent_data = None

            # Try UUID lookup first
            is_uuid = len(agent_id) == 36 and "-" in agent_id
            if is_uuid:
                result = (
                    auth.client.table("agents")
                    .select("id, title")
                    .eq("id", agent_id)
                    .eq("user_id", auth.user_id)
                    .maybe_single()
                    .execute()
                )
                agent_data = result.data if result else None

            # Fall back to title match (case-insensitive via ilike)
            if not agent_data:
                result = (
                    auth.client.table("agents")
                    .select("id, title")
                    .eq("user_id", auth.user_id)
                    .ilike("title", agent_id.replace("-", " "))
                    .maybe_single()
                    .execute()
                )
                agent_data = result.data if result else None

            # Fall back to slug derivation match — compare derived slugs
            if not agent_data:
                all_agents = (
                    auth.client.table("agents")
                    .select("id, title")
                    .eq("user_id", auth.user_id)
                    .eq("status", "active")
                    .execute()
                )
                target_slug = agent_id.lower().replace(" ", "-")
                for a in (all_agents.data or []):
                    if get_agent_slug(a) == target_slug:
                        agent_data = a
                        break

            if agent_data:
                agent_slug = get_agent_slug(agent_data)
                contributors.append({
                    "agent_slug": agent_slug,
                    "agent_id": agent_data["id"],
                    "expected_contribution": expected,
                })
            else:
                logger.warning(f"[PROJECT] Contributor agent not found: {agent_id}")
        except Exception as e:
            logger.warning(f"[PROJECT] Failed to look up contributor {agent_id}: {e}")

    # Create ProjectWorkspace and write PROJECT.md
    pw = ProjectWorkspace(auth.client, auth.user_id, project_slug)

    success = await pw.write_project(
        title=title,
        objective=objective,
        contributors=contributors,
        assembly_spec=assembly_spec,
        delivery=delivery,
        type_key=type_key,
    )

    if not success:
        return {"success": False, "error": "write_failed", "message": "Failed to write PROJECT.md"}

    # Seed each contributor's workspace with a project pointer
    for c in contributors:
        try:
            agent_ws = AgentWorkspace(auth.client, auth.user_id, c["agent_slug"])

            # Read existing projects.json or create new
            existing = await agent_ws.read("memory/projects.json")
            if existing:
                try:
                    projects_list = _json.loads(existing)
                except _json.JSONDecodeError:
                    projects_list = []
            else:
                projects_list = []

            # Add this project if not already present
            if not any(p.get("project_slug") == project_slug for p in projects_list):
                projects_list.append({
                    "project_slug": project_slug,
                    "title": title,
                    "expected_contribution": c["expected_contribution"],
                })

            await agent_ws.write(
                "memory/projects.json",
                _json.dumps(projects_list, indent=2),
                summary=f"Project memberships ({len(projects_list)} projects)",
                content_type="application/json",
            )
        except Exception as e:
            logger.warning(f"[PROJECT] Failed to seed contributor workspace {c['agent_slug']}: {e}")

    # ADR-120 Phase 1: Auto-create PM agent for this project
    pm_agent_id = None
    try:
        from services.agent_creation import create_agent_record

        pm_result = await create_agent_record(
            auth.client, auth.user_id,
            title=f"Project Manager: {title}",
            role="pm",
            origin="composer",
            mode="recurring",
            schedule={"frequency": "daily", "time": "08:00"},
            type_config={"project_slug": project_slug},
            agent_instructions=f"Manage project '{title}': {assembly_spec or 'coordinate contributors and trigger assembly when ready'}",
        )
        if pm_result.get("success"):
            pm_agent_id = pm_result["agent_id"]
            logger.info(f"[PROJECT] ADR-120: Created PM agent {pm_agent_id} for project {project_slug}")
            # Store PM agent ID in project workspace memory
            await pw.write(
                "memory/pm_agent.json",
                _json.dumps({"pm_agent_id": pm_agent_id, "pm_title": f"PM: {title}"}),
                summary="PM agent reference",
                content_type="application/json",
            )
        else:
            logger.warning(f"[PROJECT] ADR-120: PM creation failed: {pm_result.get('message')}")
    except Exception as e:
        logger.warning(f"[PROJECT] ADR-120: PM auto-creation failed: {e}")

    logger.info(f"[PROJECT] ADR-119 P2 + ADR-120: Created project '{title}' ({project_slug}) with {len(contributors)} contributors, PM={pm_agent_id}")

    return {
        "success": True,
        "project_slug": project_slug,
        "title": title,
        "contributors": [{"agent_slug": c["agent_slug"], "agent_id": c["agent_id"]} for c in contributors],
        "pm_agent_id": pm_agent_id,
        "message": f"Project '{title}' created at /projects/{project_slug}/" + (f" with PM agent" if pm_agent_id else ""),
    }


# =============================================================================
# ReadProject (chat + headless, ADR-119 Phase 2)
# =============================================================================

READ_PROJECT_TOOL = {
    "name": "ReadProject",
    "description": """Read a project's identity, contributors, and assembly history.

Returns the parsed PROJECT.md, list of contributing agents with their files,
and any assembled outputs.

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


async def handle_read_project(auth: Any, input: dict) -> dict:
    """
    Handle ReadProject primitive.

    Reads PROJECT.md → parsed dict, lists contributors + their files,
    lists assemblies.
    """
    from services.workspace import ProjectWorkspace

    project_slug = input.get("project_slug", "").strip()
    if not project_slug:
        return {"success": False, "error": "missing_slug", "message": "project_slug is required"}

    pw = ProjectWorkspace(auth.client, auth.user_id, project_slug)

    # Parse PROJECT.md
    project = await pw.read_project()
    if not project:
        return {
            "success": False,
            "error": "not_found",
            "message": f"Project not found: /projects/{project_slug}/PROJECT.md",
        }

    # List contributors and their files
    contributor_slugs = await pw.list_contributors()
    contributions = {}
    for slug in contributor_slugs:
        files = await pw.list_contributions(slug)
        contributions[slug] = files

    # List assemblies
    assemblies = await pw.list_assemblies()

    return {
        "success": True,
        "project_slug": project_slug,
        "project": project,
        "contributions": contributions,
        "assemblies": assemblies,
    }
