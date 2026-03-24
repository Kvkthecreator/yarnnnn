"""
Project Type Registry — ADR-122

Single source of truth for all project scaffolding. All project creation
flows (bootstrap, Composer, TP, API routes) go through scaffold_project().

Registry is curated, code-side, deploy-time. Follows the pattern of
PLATFORM_REGISTRY and AGENT_TYPES (ADR-130).

Design axiom: every project gets a PM. No exceptions. PM is project
infrastructure, not a user-facing agent — excluded from tier agent limits.

Changelog: api/prompts/CHANGELOG.md
Version: v1.5 (2026-03-22)
"""

from __future__ import annotations

import json as _json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Project Type Registry v1.5
# =============================================================================

PROJECT_TYPE_REGISTRY: dict[str, dict] = {

    # Platform-specific types DELETED — platforms are infrastructure, not project types.
    # Bootstrap uses "workspace" type with briefer agent for platform-connected projects.
    # ADR-133: perception agents (briefer, monitor) bridge external data into projects.

    # ── Project types ──

    "workspace": {
        "display_name": "Workspace",
        "category": "work",
        "platform": None,
        "lifecycle": "persistent",
        "description": "Recurring monitoring, tracking, and reporting for an ongoing workstream.",
        "objective_template": {
            "deliverable": "Recurring {scope_name} updates",
            "audience": "You",
            "format": "email",
            "purpose": "Stay on top of {scope_name} and surface what needs attention",
        },
        "contributors_template": [
            {
                "title_template": "{scope_name} Briefer",
                "role": "briefer",
                "scope": "cross_platform",
                "frequency": "daily",
                "sources_from": "work_unit",
            },
        ],
        "pm": True,
        "assembly_spec_template": "Coordinate {scope_name} updates and deliver summary.",
        "delivery_default": {"platform": "email"},
        "version": "2026-03-23",
    },

    "bounded_deliverable": {
        "display_name": "Deliverable",
        "category": "work",
        "platform": None,
        "lifecycle": "bounded",
        "description": "A specific deliverable with a defined end state.",
        "objective_template": {
            "deliverable": "{scope_name}",
            "audience": "You",
            "format": "document",
            "purpose": "Produce {scope_name} and deliver when ready",
        },
        "contributors_template": [
            {
                "title_template": "{scope_name} Drafter",
                "role": "drafter",
                "scope": "knowledge",
                "frequency": "on_demand",
                "sources_from": "work_unit",
            },
        ],
        "pm": True,
        "pm_lightweight": True,
        "assembly_spec_template": "Produce {scope_name} and deliver when ready.",
        "delivery_default": {"platform": "email"},
        "version": "2026-03-23",
    },

    # cross_platform_synthesis + custom DELETED — subsumed by workspace type
    # All projects use workspace (persistent) or bounded_deliverable (finite)
}


# =============================================================================
# Registry access functions
# =============================================================================

def get_project_type(type_key: str) -> Optional[dict]:
    """Look up a project type definition."""
    return PROJECT_TYPE_REGISTRY.get(type_key)


# =============================================================================
# ADR-132: Topic → agent type + lifecycle inference
# =============================================================================

# Heuristic keywords for lifecycle classification
_BOUNDED_KEYWORDS = {
    "deck", "report", "presentation", "memo", "document", "proposal",
    "review", "audit", "assessment", "board", "pitch",
    "q1", "q2", "q3", "q4", "fundrais", "launch", "event",
}

# Heuristic keywords for agent type inference
# Order matters — more specific signals first, broader signals last
_TYPE_SIGNALS: list[tuple[set[str], str, str]] = [
    # Monitor first — "monitoring" is very specific intent
    ({"alert", "notify", "flag", "escalat", "watch for", "monitoring"},
     "monitor", "Watch for changes and alert on"),
    # Research before scout — "research" is explicit intent
    ({"research", "investigate", "analyze", "deep dive", "study"},
     "researcher", "Research and produce analysis on"),
    # Scout — competitive/market intelligence (without "research" which is handled above)
    ({"competitor", "competitive", "scout", "intel", "landscape"},
     "scout", "Track and surface intelligence on"),
    # Drafter — producing specific deliverables
    ({"draft", "write", "create", "produce", "prepare", "deck", "report", "memo", "pitch", "presentation", "document"},
     "drafter", "Produce deliverables for"),
    ({"metric", "data", "number", "kpi", "dashboard", "trend", "analytics"},
     "analyst", "Track metrics and surface patterns for"),
    ({"newsletter", "email", "content", "blog", "social", "update", "communication"},
     "writer", "Craft communications for"),
    ({"plan", "agenda", "meeting", "follow-up", "action item", "schedule"},
     "planner", "Prepare plans and agendas for"),
    # (monitor handled first in signal list above)
]


def infer_topic_type(topic_name: str) -> tuple[str, str, str]:
    """Infer agent type and lifecycle from a topic name.

    Returns (agent_type, lifecycle, objective_purpose).
    Heuristic-based — no LLM call. Falls back to briefer/persistent.
    """
    name_lower = topic_name.lower()

    # Lifecycle: bounded if matches deliverable keywords
    lifecycle = "persistent"
    for kw in _BOUNDED_KEYWORDS:
        if kw in name_lower:
            lifecycle = "bounded"
            break

    # Agent type: check keyword signals
    for keywords, agent_type, verb in _TYPE_SIGNALS:
        for kw in keywords:
            if kw in name_lower:
                purpose = f"{verb} {topic_name}"
                return agent_type, lifecycle, purpose

    # Default: briefer for persistent, drafter for bounded
    if lifecycle == "bounded":
        return "drafter", lifecycle, f"Produce deliverables for {topic_name}"
    return "briefer", lifecycle, f"Stay on top of {topic_name} activity"


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
    contributors_override: Optional[list[dict]] = None,
    additional_contributors: Optional[list[dict]] = None,
    assembly_spec_override: Optional[str] = None,
    delivery_override: Optional[dict] = None,
    execute_now: bool = False,
    scope_name: Optional[str] = None,
) -> dict:
    """
    Scaffold a project from the registry. Single entry point for all
    project creation: bootstrap, Composer, TP, API routes.

    1. Look up type definition
    2. Enforce uniqueness (platform types: 1 per platform per user)
    3. Create member agents from type.members[] specs
    4. Create PM agent (type.pm) — before PROJECT.md so PM is in contributor list
    5. Write PROJECT.md with all contributors (members + PM)
    6. Seed member workspaces with project pointers
    7. Optionally execute first agent run (execute_now)

    Returns:
        {success, project_slug, contributors_created: [{agent_id, title, role}],
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

    # ── ADR-132: Template interpolation for work-scoped types ──
    def _interpolate(val, scope: str):
        """Replace {scope_name} in strings and dicts."""
        if isinstance(val, str):
            return val.replace("{scope_name}", scope)
        if isinstance(val, dict):
            return {k: _interpolate(v, scope) for k, v in val.items()}
        if isinstance(val, list):
            return [_interpolate(v, scope) for v in val]
        return val

    sn = scope_name or ""

    # ── Resolve project metadata ──
    # For work-scoped types, use scope_name as title; resolve templates
    if scope_name and ptype.get("category") == "work":
        title = title_override or scope_name
        objective = objective_override or _interpolate(ptype.get("objective_template") or ptype.get("objective") or {}, sn)
        assembly_spec = assembly_spec_override or _interpolate(ptype.get("assembly_spec_template") or ptype.get("assembly_spec") or "", sn)
    else:
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
    if contributors_override:
        # Override provided — interpolate scope_name if available
        contributor_specs = _interpolate(contributors_override, sn) if sn else contributors_override
    elif scope_name and ptype.get("category") == "work":
        # Work-scoped type — use contributors_template with interpolation
        contributor_specs = _interpolate(ptype.get("contributors_template") or ptype.get("contributors", []), sn)
    else:
        contributor_specs = ptype.get("contributors", [])

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
    created_contributors = []
    contributor_records = []

    for spec in contributor_specs:
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
            type_config={"project_slug": project_slug},  # ADR-129: enable activity event enrichment
            execute_now=execute_now,
        )

        if result.get("success"):
            agent = result["agent"]
            agent_slug = get_agent_slug(agent)
            created_contributors.append({
                "agent_id": result["agent_id"],
                "title": agent_title,
                "role": agent_role,
                "agent": agent,
            })
            contributor_records.append({
                "agent_slug": agent_slug,
                "agent_id": result["agent_id"],
                "role": agent_role,
                "expected_contribution": spec.get("expected_contribution", f"{agent_role} output"),
            })
        else:
            logger.warning(f"[REGISTRY] Member creation failed for '{agent_title}': {result.get('message')}")

    # Also add any existing contributors passed in
    if additional_contributors:
        for c in additional_contributors:
            contributor_records.append({
                "agent_slug": c.get("agent_slug", ""),
                "agent_id": c.get("agent_id", ""),
                "expected_contribution": c.get("expected_contribution", ""),
            })

    # ── Create PM agent (infrastructure, NOT a contributor — ADR-122) ──
    pm_agent_id = None
    if ptype["pm"]:
        try:
            pm_result = await create_agent_record(
                client, user_id,
                title=f"Project Manager: {title}",
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
                pm_slug = get_agent_slug(pm_result["agent"])
                logger.info(f"[REGISTRY] Created PM agent {pm_agent_id} for project {project_slug}")
                # PM is project infrastructure, not a functional contributor.
                # Do NOT add to contributor_records — only functional agents belong there.
            else:
                logger.warning(f"[REGISTRY] PM creation failed: {pm_result.get('message')}")
        except Exception as e:
            logger.warning(f"[REGISTRY] PM auto-creation failed: {e}")

    # ── Write PROJECT.md (functional contributors only, PM excluded) ──
    pw = ProjectWorkspace(client, user_id, project_slug)
    # Resolve frequency from first contributor spec (or default weekly)
    project_frequency = "weekly"
    if contributor_specs:
        project_frequency = contributor_specs[0].get("frequency", "weekly")

    success = await pw.write_project(
        title=title,
        objective=objective,
        contributors=contributor_records,
        assembly_spec=assembly_spec,
        delivery=delivery,
        type_key=type_key,
        frequency=project_frequency,
    )

    if not success:
        return {"success": False, "reason": "write_failed", "message": "Failed to write PROJECT.md"}

    # ── Store PM agent reference in project memory ──
    if pm_agent_id:
        try:
            await pw.write(
                "memory/pm_agent.json",
                _json.dumps({"pm_agent_id": pm_agent_id, "pm_title": f"Project Manager: {title}"}),
                summary="PM agent reference",
                content_type="application/json",
            )
        except Exception:
            pass  # Non-fatal

    # ── ADR-128 Phase 0: Seed project cognitive files ──
    try:
        await pw.write(
            "memory/project_assessment.md",
            (
                "# Project Assessment\n"
                "<!-- Rewritten each PM pulse. -->\n\n"
                "No assessment yet — PM has not pulsed.\n"
            ),
            summary="ADR-128: initial project assessment (awaiting first PM pulse)",
        )
    except Exception as e:
        logger.warning(f"[REGISTRY] Failed to seed project_assessment.md for {project_slug}: {e}")

    # ADR-135/136: TP→PM handoff — write creation context to project chat session
    if pm_agent_id:
        try:
            from services.pm_coordination import pm_announce
            pm_agent = {"id": pm_agent_id, "title": f"Project Manager: {title}", "role": "pm"}
            contributor_names = [c.get("title", c.get("agent_slug", "?")) for c in created_contributors]
            obj_summary = objective.get("deliverable", title) if isinstance(objective, dict) else title
            cadence_text = project_frequency if project_frequency != "daily" else "daily"

            handoff_msg = (
                f"Project created: {title}. "
                f"Objective: {obj_summary}. "
                f"Team: {', '.join(contributor_names) if contributor_names else 'no contributors yet'}. "
                f"Cadence: {cadence_text}. "
                f"I'll start coordinating on my first pulse."
            )
            await pm_announce(client, user_id, project_slug, pm_agent, handoff_msg, decision_type="project_created")
        except Exception as e:
            logger.warning(f"[REGISTRY] Handoff message failed (non-fatal): {e}")

    # ADR-133: No seeding of IDENTITY.md or BRAND.md into projects.
    # Agents read /workspace/ directly at execution time. No duplication.

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

    # ── Execute first member run inline if requested ──
    if execute_now and created_contributors:
        for cm in created_contributors:
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
                    # Update next_pulse_at to prevent scheduler double-run
                    try:
                        from jobs.unified_scheduler import calculate_next_pulse_from_schedule
                        agent_schedule = cm["agent"].get("schedule", {})
                        next_run = calculate_next_pulse_from_schedule(agent_schedule)
                        client.table("agents").update({
                            "next_pulse_at": next_run.isoformat(),
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
            summary=f"Created project '{title}' (type: {type_key}) with {len(created_contributors)} member(s)",
            event_ref=project_slug,
            metadata={
                "type_key": type_key,
                "category": ptype["category"],
                "platform": ptype.get("platform"),
                "contributors_created": [cm["agent_id"] for cm in created_contributors],
                "pm_agent_id": pm_agent_id,
            },
        )
    except Exception:
        pass  # Non-fatal

    logger.info(
        f"[REGISTRY] Scaffolded project '{title}' ({project_slug}), "
        f"type={type_key}, members={len(created_contributors)}, PM={pm_agent_id}"
    )

    return {
        "success": True,
        "project_slug": project_slug,
        "title": title,
        "type_key": type_key,
        "contributors_created": [
            {"agent_id": cm["agent_id"], "title": cm["title"], "role": cm["role"]}
            for cm in created_contributors
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
