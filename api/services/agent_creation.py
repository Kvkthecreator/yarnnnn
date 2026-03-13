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
VALID_SKILLS = {"digest", "prepare", "monitor", "research", "synthesize", "orchestrate", "act", "custom"}

# Infer scope from skill when not provided
SKILL_TO_SCOPE = {
    "digest": "platform",
    "prepare": "platform",
    "monitor": "platform",
    "research": "research",
    "synthesize": "cross_platform",
    "orchestrate": "autonomous",
    "act": "autonomous",
    "custom": "knowledge",
}

# Columns allowed in agents table INSERT (prevents Supabase 400)
AGENT_COLUMNS = {
    "id", "user_id", "project_id", "title", "description",
    "recipient_context", "template_structure", "schedule", "sources",
    "status", "created_at", "updated_at", "last_run_at", "next_run_at",
    "type_config", "destination", "platform_variant", "destinations",
    "is_synthesizer", "domain_id", "origin", "agent_instructions",
    "agent_memory", "mode", "proactive_next_review_at", "trigger_type",
    "trigger_config", "last_triggered_at", "scope", "skill",
}


# =============================================================================
# Core creation function
# =============================================================================

async def create_agent_record(
    client: Any,
    user_id: str,
    title: str,
    skill: str = "custom",
    origin: str = "user_configured",
    *,
    scope: Optional[str] = None,
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
    from jobs.unified_scheduler import calculate_next_run_from_schedule

    if not title or not title.strip():
        return {"success": False, "error": "missing_title", "message": "title is required"}

    # Validate and default skill
    if skill not in VALID_SKILLS:
        skill = "custom"

    # Infer scope from skill if not provided or invalid
    if not scope or scope not in VALID_SCOPES:
        scope = SKILL_TO_SCOPE.get(skill, "knowledge")

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

    # Calculate next_run_at
    now = datetime.now(timezone.utc)
    if execute_now:
        next_run_at = now.isoformat()
    else:
        next_run = calculate_next_run_from_schedule(sched)
        next_run_at = next_run.isoformat()

    # Resolve instructions
    instructions_text = agent_instructions
    if not instructions_text:
        from services.agent_pipeline import DEFAULT_INSTRUCTIONS
        instructions_text = DEFAULT_INSTRUCTIONS.get(skill, DEFAULT_INSTRUCTIONS.get("custom", ""))

    entity_id = str(uuid4())

    agent_data = {
        "id": entity_id,
        "user_id": user_id,
        "title": title.strip(),
        "skill": skill,
        "scope": scope,
        "mode": mode,
        "origin": origin,
        "status": "active",
        "sources": sources or [],
        "schedule": sched,
        "next_run_at": next_run_at,
        "recipient_context": recipient_context or {},
        "type_config": type_config or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

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
                await ws.write("AGENT.md", instructions_text,
                               summary="Agent identity and behavioral instructions")
            except Exception as e:
                logger.warning(f"[AGENT_CREATION] Workspace seed failed for {entity_id}: {e}")

        logger.info(f"[AGENT_CREATION] Created: {title} ({entity_id}), origin={origin}, skill={skill}")

        return {
            "success": True,
            "agent_id": entity_id,
            "agent": agent,
            "message": f"Created agent '{title}' — {'queued for immediate generation' if execute_now else 'scheduled ' + sched.get('frequency', 'weekly')}.",
        }

    except Exception as e:
        logger.error(f"[AGENT_CREATION] Failed: {e}")
        return {"success": False, "error": "creation_failed", "message": str(e)}
