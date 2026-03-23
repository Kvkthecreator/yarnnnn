"""
Agent Creation — Shared logic for all agent creation paths (ADR-111).

Single source of truth for creating agents. Called by:
- CreateAgent primitive (chat + headless)
- Onboarding bootstrap service (ADR-110)
- POST /agents route (agents.py)

Replaces the duplicated logic that was in:
- primitives/write.py (_process_agent)
- primitives/coordinator.py (handle_create_agent)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Valid values (ADR-109)
# =============================================================================

VALID_SCOPES = {"platform", "cross_platform", "knowledge", "research", "autonomous"}
# ADR-130 v2: Valid roles derived from AGENT_TYPES registry + legacy names for DB compat
from services.agent_framework import AGENT_TYPES, LEGACY_ROLE_MAP
VALID_ROLES = set(AGENT_TYPES.keys()) | set(LEGACY_ROLE_MAP.keys()) | {"act"}

# Fallback scope from role (used when infer_scope can't reason about sources)
ROLE_TO_SCOPE = {
    # v2 types
    "briefer": "platform",
    "monitor": "platform",
    "researcher": "research",
    "drafter": "cross_platform",
    "analyst": "cross_platform",
    "writer": "cross_platform",
    "planner": "platform",
    "scout": "research",
    "pm": "knowledge",
    # Legacy mappings (DB may still have old values)
    "digest": "platform",
    "prepare": "platform",
    "research": "research",
    "synthesize": "cross_platform",
    "act": "autonomous",
    "custom": "knowledge",
}


def infer_scope(sources: list, role: str, mode: str = "recurring") -> str:
    """
    ADR-109: Auto-infer scope from sources + role + mode.

    Scope is never user-configured — it's derived from what the agent knows about.

    Rules:
    1. proactive/coordinator mode with synthesis/research role → autonomous
    2. research role with no platform sources → research
    3. 0 platform sources → knowledge (or cross_platform fallback)
    4. 1 provider → platform
    5. 2+ providers → cross_platform
    """
    if mode in ("proactive", "coordinator") and role in ("synthesize", "research", "analyst", "researcher"):
        return "autonomous"

    # Count distinct providers from integration sources
    providers = set()
    for s in sources:
        provider = (s.get("provider") or s.get("platform")) if isinstance(s, dict) else None
        if provider:
            providers.add(provider)

    if not providers:
        # No platform sources — fall back to the role's default scope
        return ROLE_TO_SCOPE.get(role, "knowledge")

    if len(providers) == 1:
        return "platform"

    return "cross_platform"

# Columns allowed in agents table INSERT (prevents Supabase 400)
# NOTE: agent_instructions and agent_memory EXCLUDED — deprecated by ADR-106.
# Workspace AGENT.md and memory/*.md are the sole authority for new agents.
# DB columns kept in schema for lazy migration of pre-workspace agents.
AGENT_COLUMNS = {
    "id", "user_id", "project_id", "title", "description",
    "recipient_context", "schedule", "sources",
    "status", "created_at", "updated_at", "last_run_at", "next_pulse_at",
    "type_config", "destination", "origin",
    "mode", "trigger_type",
    "trigger_config", "last_triggered_at", "scope", "role",
    "avatar_url",
}


# =============================================================================
# Core creation function
# =============================================================================

async def create_agent_record(
    client: Any,
    user_id: str,
    title: str,
    role: str = "custom",
    origin: str = "user_configured",
    *,
    scope: Optional[str] = None,
    description: Optional[str] = None,
    agent_instructions: Optional[str] = None,
    sources: Optional[list] = None,
    schedule: Optional[dict] = None,
    frequency: Optional[str] = None,
    day: Optional[str] = None,
    time: Optional[str] = None,
    timezone_str: Optional[str] = None,
    mode: str = "recurring",
    trigger_type: Optional[str] = None,
    recipient_context: Optional[dict] = None,
    type_config: Optional[dict] = None,
    destination: Optional[dict] = None,
    execute_now: bool = False,
    extra_fields: Optional[dict] = None,
) -> dict:
    """
    Create an agent record in the database with workspace seeding.

    This is the single creation path for all agent origins:
    - user_configured (TP chat, UI form)
    - coordinator_created (coordinator agents)
    - system_bootstrap (onboarding bootstrap, ADR-110)
    - composer (composer service, ADR-111 future)

    Returns:
        {"success": True, "agent_id": str, "agent": dict, "message": str}
        or {"success": False, "error": str, "message": str}
    """
    from jobs.unified_scheduler import calculate_next_pulse_from_schedule

    if not title or not title.strip():
        return {"success": False, "error": "missing_title", "message": "title is required"}

    # Validate and default role
    if role not in VALID_ROLES:
        role = "custom"

    # Infer scope from sources + role + mode if not provided or invalid
    if not scope or scope not in VALID_SCOPES:
        scope = infer_scope(sources or [], role, mode)

    # Build schedule JSONB
    sched = schedule.copy() if schedule else {}
    if frequency and "frequency" not in sched:
        sched["frequency"] = frequency
    if day and "day" not in sched:
        sched["day"] = day
    if time and "time" not in sched:
        sched["time"] = time
    if timezone_str and "timezone" not in sched:
        sched["timezone"] = timezone_str

    # Apply schedule defaults
    sched.setdefault("frequency", "weekly")
    sched.setdefault("time", "09:00")
    sched.setdefault("timezone", "UTC")

    # Calculate next_pulse_at
    now = datetime.now(timezone.utc)
    if execute_now:
        next_pulse_at = now.isoformat()
    else:
        next_pulse = calculate_next_pulse_from_schedule(sched)
        next_pulse_at = next_pulse.isoformat()

    # Resolve instructions
    instructions_text = agent_instructions
    if not instructions_text:
        from services.agent_pipeline import DEFAULT_INSTRUCTIONS
        instructions_text = DEFAULT_INSTRUCTIONS.get(role, DEFAULT_INSTRUCTIONS.get("custom", ""))

    entity_id = str(uuid4())

    agent_data = {
        "id": entity_id,
        "user_id": user_id,
        "title": title.strip(),
        "role": role,
        "scope": scope,
        "mode": mode,
        "origin": origin,
        "status": "active",
        "sources": sources or [],
        "schedule": sched,
        "next_pulse_at": next_pulse_at,
        "recipient_context": recipient_context or {},
        "type_config": type_config or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    # NOTE: agent_instructions DB column is DEPRECATED (ADR-106).
    # Workspace AGENT.md is the sole authority. DB column kept for lazy migration
    # of pre-workspace agents via ensure_seeded() but NOT written for new agents.
    if description:
        agent_data["description"] = description

    if trigger_type:
        agent_data["trigger_type"] = trigger_type
    if destination:
        agent_data["destination"] = destination

    # Merge extra fields (e.g., coordinator-specific fields)
    if extra_fields:
        agent_data.update(extra_fields)

    # Strip to valid columns only
    agent_data = {k: v for k, v in agent_data.items() if k in AGENT_COLUMNS}

    try:
        result = client.table("agents").insert(agent_data).execute()

        if not result.data:
            return {"success": False, "error": "insert_failed", "message": "Failed to create agent"}

        agent = result.data[0]

        # ADR-106: Seed workspace AGENT.md
        if instructions_text:
            try:
                from services.workspace import AgentWorkspace, get_agent_slug
                ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
                # ADR-118: Append capability reference for agents that may produce rich outputs
                agent_md = instructions_text
                from services.agent_framework import has_asset_capabilities
                if has_asset_capabilities(role):
                    agent_md += "\n\n## Available Capabilities\nThis agent can produce rich outputs via RuntimeDispatch: PNG/SVG charts, diagrams, and images. Use these when visual data or formatted reports would serve the recipient better than plain text."
                if role == "pm":
                    project_slug = (type_config or {}).get("project_slug", "unknown")
                    agent_md += f"\n\n## Project Context\nThis PM agent coordinates project `{project_slug}`. Check contributor freshness, trigger assembly when contributions are ready, manage the work plan. Escalate to TP if stuck."
                else:
                    # ADR-128: Contributors participate in coherence protocol
                    agent_md += "\n\n## Coherence Protocol\nYou participate in a coherence protocol. You produce a self-assessment on each run that persists between executions. You receive PM assessments and contribution briefs via your workspace."
                await ws.write("AGENT.md", agent_md,
                               summary="Agent identity and behavioral instructions")

                # ADR-128 Phase 0: Seed cognitive files at creation time
                if role != "pm":
                    # Contributor: seed self_assessment.md with initial state
                    initial_date = now.strftime("%Y-%m-%d")
                    await ws.write(
                        "memory/self_assessment.md",
                        (
                            "# Self-Assessment History\n"
                            "<!-- Updated each run. Most recent first. Max 5 entries. -->\n\n"
                            f"## Initial ({initial_date})\n"
                            "- **Mandate**: Not yet assessed — awaiting first run\n"
                            "- **Domain Fitness**: Unknown\n"
                            "- **Context Currency**: Unknown\n"
                            "- **Output Confidence**: N/A\n"
                        ),
                        summary="ADR-128: initial self-assessment (awaiting first run)",
                    )
            except Exception as e:
                logger.warning(f"[AGENT_CREATION] Workspace seed failed for {entity_id}: {e}")

        logger.info(f"[AGENT_CREATION] Created: {title} ({entity_id}), origin={origin}, role={role}")

        return {
            "success": True,
            "agent_id": entity_id,
            "agent": agent,
            "message": f"Created agent '{title}' — {'queued for immediate generation' if execute_now else 'scheduled ' + sched.get('frequency', 'weekly')}.",
        }

    except Exception as e:
        logger.error(f"[AGENT_CREATION] Failed: {e}")
        return {"success": False, "error": "creation_failed", "message": str(e)}
