"""
Project Type Registry — ADR-122

Single source of truth for all project scaffolding. All project creation
flows (bootstrap, Composer, TP, API routes) go through scaffold_project().

Registry is curated, code-side, deploy-time. Follows the pattern of
PLATFORM_REGISTRY, ROLE_PORTFOLIOS, ROLE_PROMPTS.

Design axiom: every project gets a PM. No exceptions. PM is project
infrastructure, not a user-facing agent — excluded from tier agent limits.

Changelog: api/prompts/CHANGELOG.md
Version: v1.3 (2026-03-20)
"""

from __future__ import annotations

import json as _json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Project Type Registry v1.3
# =============================================================================

PROJECT_TYPE_REGISTRY: dict[str, dict] = {

    # ── Platform digest types (1:1 with platform, uniqueness enforced) ──

    "slack_digest": {
        "display_name": "Slack Recap",
        "category": "platform",
        "platform": "slack",
        "description": "Daily recap of Slack activity across connected channels.",
        "objective": {
            "deliverable": "Daily Slack recap",
            "audience": "You",
            "format": "email",
            "purpose": "Stay informed on team activity without reading every message",
        },
        "members": [
            {
                "title_template": "Slack Agent",
                "role": "digest",
                "scope": "platform",
                "frequency": "daily",
                "sources_from": "platform",
            },
        ],
        "pm": True,
        "assembly_spec": "Coordinate Slack digest output and deliver to user.",
        "delivery_default": {"platform": "email"},
        "version": "2026-03-20",
    },

    "gmail_digest": {
        "display_name": "Gmail Recap",
        "category": "platform",
        "platform": "google",
        "description": "Daily recap of Gmail activity across connected labels.",
        "objective": {
            "deliverable": "Daily Gmail recap",
            "audience": "You",
            "format": "email",
            "purpose": "Inbox triage — highlights and action items surfaced daily",
        },
        "members": [
            {
                "title_template": "Gmail Agent",
                "role": "digest",
                "scope": "platform",
                "frequency": "daily",
                "sources_from": "platform",
            },
        ],
        "pm": True,
        "assembly_spec": "Coordinate Gmail digest output and deliver to user.",
        "delivery_default": {"platform": "email"},
        "version": "2026-03-20",
    },

    "notion_digest": {
        "display_name": "Notion Recap",
        "category": "platform",
        "platform": "notion",
        "description": "Daily recap of Notion activity across connected pages.",
        "objective": {
            "deliverable": "Daily Notion recap",
            "audience": "You",
            "format": "email",
            "purpose": "Track workspace changes without visiting every page",
        },
        "members": [
            {
                "title_template": "Notion Agent",
                "role": "digest",
                "scope": "platform",
                "frequency": "daily",
                "sources_from": "platform",
            },
        ],
        "pm": True,
        "assembly_spec": "Coordinate Notion digest output and deliver to user.",
        "delivery_default": {"platform": "email"},
        "version": "2026-03-20",
    },

    # ── Multi-agent project types ──

    "cross_platform_synthesis": {
        "display_name": "Cross-Platform Insights",
        "category": "synthesis",
        "platform": None,
        "description": "Weekly synthesis across multiple platforms — patterns, themes, action items.",
        "objective": {
            "deliverable": "Weekly cross-platform insights report",
            "audience": "You",
            "format": "pdf",
            "purpose": "See patterns across platforms that individual digests miss",
        },
        "members": [
            {
                "title_template": "Cross-Platform Synthesizer",
                "role": "synthesize",
                "scope": "cross_platform",
                "frequency": "weekly",
                "sources_from": "all_platforms",
            },
        ],
        "pm": True,
        "assembly_spec": "Synthesize themes across all contributor outputs into a cohesive report.",
        "delivery_default": {"platform": "email"},
        "version": "2026-03-20",
    },

    "custom": {
        "display_name": "Custom Project",
        "category": "custom",
        "platform": None,
        "description": "User-defined project with custom agents and delivery.",
        "objective": None,
        "members": [],
        "pm": True,
        "assembly_spec": None,
        "delivery_default": {"platform": "email"},
        "version": "2026-03-20",
    },
}


# =============================================================================
# Registry access functions
# =============================================================================

def get_project_type(type_key: str) -> Optional[dict]:
    """Look up a project type definition."""
    return PROJECT_TYPE_REGISTRY.get(type_key)


def get_platform_project_type(platform: str) -> Optional[tuple[str, dict]]:
    """Find the project type for a given platform (slack, google, notion).

    Returns (type_key, type_def) or None.
    """
    for key, ptype in PROJECT_TYPE_REGISTRY.items():
        if ptype.get("platform") == platform:
            return (key, ptype)
    return None


def list_project_types(category: Optional[str] = None) -> list[dict]:
    """List all project types, optionally filtered by category."""
    types = []
    for key, ptype in PROJECT_TYPE_REGISTRY.items():
        if category and ptype.get("category") != category:
            continue
        types.append({"key": key, **ptype})
    return types


# =============================================================================
# Uniqueness check
# =============================================================================

async def _check_type_uniqueness(
    client: Any, user_id: str, type_key: str, ptype: dict,
) -> Optional[str]:
    """For platform types, check if a project of this type already exists.

    Returns existing project_slug if duplicate, None if clear.
    """
    if ptype.get("category") != "platform":
        return None  # No uniqueness constraint for non-platform types

    try:
        from services.workspace import ProjectWorkspace, get_project_slug

        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "/projects/%/PROJECT.md")
            .neq("lifecycle", "archived")
            .execute()
        )
        for row in (result.data or []):
            content = row.get("content", "")
            # Check for type_key marker in PROJECT.md
            if f"**Type**: {type_key}" in content:
                # Extract slug from path: /projects/{slug}/PROJECT.md
                parts = row["path"].split("/")
                if len(parts) >= 3:
                    return parts[2]
    except Exception as e:
        logger.warning(f"[REGISTRY] Uniqueness check failed: {e}")
        return None  # Allow creation on check failure (don't block on transient errors)

    return None


# =============================================================================
# Unified scaffolding function
# =============================================================================

async def scaffold_project(
    client: Any,
    user_id: str,
    type_key: str,
    *,
    title_override: Optional[str] = None,
    objective_override: Optional[dict] = None,
    members_override: Optional[list[dict]] = None,
    contributors: Optional[list[dict]] = None,
    assembly_spec_override: Optional[str] = None,
    delivery_override: Optional[dict] = None,
    execute_now: bool = False,
) -> dict:
    """
    Scaffold a project from the registry. Single entry point for all
    project creation: bootstrap, Composer, TP, API routes.

    1. Look up type definition
    2. Enforce uniqueness (platform types: 1 per platform per user)
    3. Create project via ProjectWorkspace.write_project()
    4. Create member agents from type.members[] specs
    5. Optionally create PM agent (type.pm)
    6. Seed member workspaces with project pointers
    7. Optionally execute first agent run (execute_now)

    Returns:
        {success, project_slug, members_created: [{agent_id, title, role}],
         pm_agent_id, message}
        or {success: False, reason, message}
    """
    from services.workspace import (
        ProjectWorkspace, AgentWorkspace, get_project_slug, get_agent_slug,
    )
    from services.agent_creation import create_agent_record

    ptype = get_project_type(type_key)
    if not ptype:
        return {"success": False, "reason": "unknown_type", "message": f"Unknown project type: {type_key}"}

    # ── Uniqueness check ──
    existing_slug = await _check_type_uniqueness(client, user_id, type_key, ptype)
    if existing_slug:
        return {
            "success": False,
            "reason": "duplicate",
            "existing_slug": existing_slug,
            "message": f"Project of type '{type_key}' already exists: {existing_slug}",
        }

    # ── Resolve project metadata ──
    title = title_override or ptype["display_name"]
    objective = objective_override or ptype.get("objective") or {}
    assembly_spec = assembly_spec_override or ptype.get("assembly_spec") or ""
    delivery = delivery_override or {}

    # Resolve delivery default — auto-populate email target
    # PROJECT.md uses "channel" (not "platform") for the delivery method
    if not delivery and ptype.get("delivery_default"):
        delivery = dict(ptype["delivery_default"])
        # Normalize: registry uses "platform", PROJECT.md uses "channel"
        if "platform" in delivery and "channel" not in delivery:
            delivery["channel"] = delivery.pop("platform")
        if delivery.get("channel") == "email" and "target" not in delivery:
            try:
                from services.agent_execution import get_user_email
                user_email = get_user_email(client, user_id)
                if user_email:
                    delivery["target"] = user_email
            except Exception:
                pass

    project_slug = get_project_slug(title)

    # ── Resolve sources for member agents ──
    member_specs = members_override or ptype.get("members", [])

    async def _resolve_sources(spec: dict) -> list:
        sources_from = spec.get("sources_from")
        if sources_from == "platform":
            platform = ptype.get("platform")
            if platform:
                return await _get_platform_sources(client, user_id, platform)
        elif sources_from == "all_platforms":
            return await _get_all_platform_sources(client, user_id)
        return spec.get("sources", [])

    # ── Create member agents from specs ──
    created_members = []
    contributor_records = []

    for spec in member_specs:
        agent_title = spec.get("title_template", spec.get("title", f"{title} Agent"))
        agent_role = spec.get("role", "custom")
        agent_scope = spec.get("scope")
        agent_freq = spec.get("frequency", "daily")
        agent_sources = await _resolve_sources(spec)
        agent_instructions = spec.get("instructions")

        result = await create_agent_record(
            client=client,
            user_id=user_id,
            title=agent_title,
            role=agent_role,
            origin="system_bootstrap" if ptype["category"] == "platform" else "composer",
            scope=agent_scope,
            frequency=agent_freq,
            sources=agent_sources,
            destination=None,  # Agents produce, projects deliver — no direct agent delivery
            agent_instructions=agent_instructions,
            execute_now=execute_now,
        )

        if result.get("success"):
            agent = result["agent"]
            agent_slug = get_agent_slug(agent)
            created_members.append({
                "agent_id": result["agent_id"],
                "title": agent_title,
                "role": agent_role,
                "agent": agent,
            })
            contributor_records.append({
                "agent_slug": agent_slug,
                "agent_id": result["agent_id"],
                "expected_contribution": spec.get("expected_contribution", f"{agent_role} output"),
            })
        else:
            logger.warning(f"[REGISTRY] Member creation failed for '{agent_title}': {result.get('message')}")

    # Also add any existing contributors passed in
    if contributors:
        for c in contributors:
            contributor_records.append({
                "agent_slug": c.get("agent_slug", ""),
                "agent_id": c.get("agent_id", ""),
                "expected_contribution": c.get("expected_contribution", ""),
            })

    # ── Write PROJECT.md ──
    pw = ProjectWorkspace(client, user_id, project_slug)
    success = await pw.write_project(
        title=title,
        objective=objective,
        contributors=contributor_records,
        assembly_spec=assembly_spec,
        delivery=delivery,
        type_key=type_key,
    )

    if not success:
        return {"success": False, "reason": "write_failed", "message": "Failed to write PROJECT.md"}

    # ── Seed member workspaces with project pointers ──
    for c in contributor_records:
        if not c.get("agent_slug"):
            continue
        try:
            agent_ws = AgentWorkspace(client, user_id, c["agent_slug"])
            existing = await agent_ws.read("memory/projects.json")
            if existing:
                try:
                    projects_list = _json.loads(existing)
                except _json.JSONDecodeError:
                    projects_list = []
            else:
                projects_list = []

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
            logger.warning(f"[REGISTRY] Failed to seed member workspace {c['agent_slug']}: {e}")

    # ── Create PM agent if type requires it ──
    pm_agent_id = None
    if ptype["pm"]:
        try:
            pm_result = await create_agent_record(
                client, user_id,
                title=f"PM: {title}",
                role="pm",
                origin="composer",
                mode="recurring",
                schedule={"frequency": "daily", "time": "08:00"},
                type_config={"project_slug": project_slug},
                agent_instructions=(
                    f"Manage project '{title}': "
                    f"{assembly_spec or 'coordinate contributors and trigger assembly when ready'}"
                ),
            )
            if pm_result.get("success"):
                pm_agent_id = pm_result["agent_id"]
                logger.info(f"[REGISTRY] Created PM agent {pm_agent_id} for project {project_slug}")
                await pw.write(
                    "memory/pm_agent.json",
                    _json.dumps({"pm_agent_id": pm_agent_id, "pm_title": f"PM: {title}"}),
                    summary="PM agent reference",
                    content_type="application/json",
                )
            else:
                logger.warning(f"[REGISTRY] PM creation failed: {pm_result.get('message')}")
        except Exception as e:
            logger.warning(f"[REGISTRY] PM auto-creation failed: {e}")

    # ── Execute first member run inline if requested ──
    if execute_now and created_members:
        for cm in created_members:
            try:
                from services.agent_execution import execute_agent_generation
                exec_result = await execute_agent_generation(
                    client=client,
                    user_id=user_id,
                    agent=cm["agent"],
                    trigger_context={"type": "bootstrap", "project_slug": project_slug},
                )
                if exec_result.get("success"):
                    logger.info(
                        f"[REGISTRY] First run delivered: {cm['title']} "
                        f"v{exec_result.get('version_number', '?')}"
                    )
                    # Update next_run_at to prevent scheduler double-run
                    try:
                        from jobs.unified_scheduler import calculate_next_run_from_schedule
                        agent_schedule = cm["agent"].get("schedule", {})
                        next_run = calculate_next_run_from_schedule(agent_schedule)
                        client.table("agents").update({
                            "next_run_at": next_run.isoformat(),
                        }).eq("id", cm["agent_id"]).execute()
                    except Exception:
                        pass
                else:
                    logger.warning(f"[REGISTRY] First run failed for {cm['title']}: {exec_result.get('message')}")
            except Exception as e:
                logger.warning(f"[REGISTRY] Inline execution failed for {cm['title']}, scheduler will retry: {e}")

    # ── Activity log ──
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=client,
            user_id=user_id,
            event_type="project_scaffolded",
            summary=f"Created project '{title}' (type: {type_key}) with {len(created_members)} member(s)",
            event_ref=project_slug,
            metadata={
                "type_key": type_key,
                "category": ptype["category"],
                "platform": ptype.get("platform"),
                "members_created": [cm["agent_id"] for cm in created_members],
                "pm_agent_id": pm_agent_id,
            },
        )
    except Exception:
        pass  # Non-fatal

    logger.info(
        f"[REGISTRY] Scaffolded project '{title}' ({project_slug}), "
        f"type={type_key}, members={len(created_members)}, PM={pm_agent_id}"
    )

    return {
        "success": True,
        "project_slug": project_slug,
        "title": title,
        "type_key": type_key,
        "members_created": [
            {"agent_id": cm["agent_id"], "title": cm["title"], "role": cm["role"]}
            for cm in created_members
        ],
        "pm_agent_id": pm_agent_id,
        "message": (
            f"Project '{title}' created at /projects/{project_slug}/"
            + (f" with PM agent" if pm_agent_id else "")
            + (f" — first run executing" if execute_now else "")
        ),
    }


# =============================================================================
# Source resolution helpers
# =============================================================================

async def _get_platform_sources(client: Any, user_id: str, platform: str) -> list:
    """Get the user's selected sources for a specific platform."""
    try:
        result = (
            client.table("platform_connections")
            .select("landscape")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .single()
            .execute()
        )
        if result.data:
            landscape = result.data.get("landscape") or {}
            sources = landscape.get("selected_sources", [])
            if sources:
                return sources
    except Exception:
        pass
    return []


async def _get_all_platform_sources(client: Any, user_id: str) -> list:
    """Get selected sources across all connected platforms."""
    all_sources = []
    try:
        result = (
            client.table("platform_connections")
            .select("landscape")
            .eq("user_id", user_id)
            .in_("status", ["connected", "active"])
            .execute()
        )
        for row in (result.data or []):
            landscape = row.get("landscape") or {}
            all_sources.extend(landscape.get("selected_sources", []))
    except Exception:
        pass
    return all_sources


async def _has_synced_content(client: Any, user_id: str, platform: str) -> bool:
    """Check if platform has at least one piece of synced content."""
    try:
        result = (
            client.table("platform_content")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        return False
