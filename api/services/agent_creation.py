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
VALID_ROLES = {"digest", "prepare", "monitor", "research", "synthesize", "orchestrate", "act", "custom"}

# Fallback scope from role (used when infer_scope can't reason about sources)
ROLE_TO_SCOPE = {
    "digest": "platform",
    "prepare": "platform",
    "monitor": "platform",
    "research": "research",
    "synthesize": "cross_platform",
    "orchestrate": "autonomous",
    "act": "autonomous",
    "custom": "knowledge",
}


def infer_scope(sources: list, role: str, mode: str = "recurring") -> str:
    """
    ADR-109: Auto-infer scope from sources + role + mode.

    Scope is never user-configured — it's derived from what the agent knows about.

    Rules:
    1. orchestrate role → autonomous
    2. proactive/coordinator mode with synthesis/research role → autonomous
    3. research role with no platform sources → research
    4. 0 platform sources → knowledge (or cross_platform fallback)
    5. 1 provider → platform
    6. 2+ providers → cross_platform
    """
    if role == "orchestrate":
        return "autonomous"

    if mode in ("proactive", "coordinator") and role in ("synthesize", "research"):
        return "autonomous"

    # Count distinct providers from integration sources
    providers = set()
    for s in sources:
        provider = (s.get("provider") or s.get("platform")) if isinstance(s, dict) else None
        if provider:
            providers.add(provider)

    if not providers:
        if role == "research":
            return "research"
        return "knowledge" if role in ("monitor", "research", "custom") else "cross_platform"

    if len(providers) == 1:
        return "platform"

    return "cross_platform"

# Columns allowed in agents table INSERT (prevents Supabase 400)
AGENT_COLUMNS = {
    "id", "user_id", "project_id", "title", "description",
    "recipient_context", "schedule", "sources",
    "status", "created_at", "updated_at", "last_run_at", "next_run_at",
    "type_config", "destination", "origin", "agent_instructions",
    "agent_memory", "mode", "proactive_next_review_at", "trigger_type",
    "trigger_config", "last_triggered_at", "scope", "role",
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
    from jobs.unified_scheduler import calculate_next_run_from_schedule

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
        "next_run_at": next_run_at,
        "recipient_context": recipient_context or {},
        "type_config": type_config or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    if instructions_text:
        agent_data["agent_instructions"] = instructions_text
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
                if role in ("synthesize", "research", "monitor", "custom"):
                    agent_md += "\n\n## Available Capabilities\nThis agent can produce rich outputs via RuntimeDispatch: PDF documents, PPTX presentations, XLSX spreadsheets, PNG/SVG charts. Use these when structured data or formatted reports would serve the recipient better than plain text."
                await ws.write("AGENT.md", agent_md,
                               summary="Agent identity and behavioral instructions")
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
