"""
Coordinator Primitives — ADR-138

  CreateAgent — identity-only agent creation (title, role, instructions)

Scheduling, sources, delivery all live on tasks now (see task.py).
AdvanceAgentSchedule DELETED — next_pulse_at column dropped (ADR-138 migration 129).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CreateAgent (simplified — identity only, ADR-138)
# =============================================================================

CREATE_AGENT_TOOL = {
    "name": "CreateAgent",
    "description": """Create a new agent — a persistent identity with a role and behavioral instructions.

Agents are identities that execute tasks. Create the agent first, then assign tasks to it.

Required: title, role
Optional: agent_instructions (behavioral directives)

role: briefer|monitor|researcher|drafter|analyst|writer|planner|scout

Examples:
- CreateAgent(title="Competitive Intel", role="researcher")
- CreateAgent(title="Weekly Digest", role="briefer", agent_instructions="Focus on product launches and partnerships")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title for the agent"
            },
            "role": {
                "type": "string",
                "description": "Role: briefer, monitor, researcher, drafter, analyst, writer, planner, scout"
            },
            "agent_instructions": {
                "type": "string",
                "description": "Behavioral instructions for the agent"
            },
        },
        "required": ["title", "role"]
    }
}


async def handle_create_agent(auth: Any, input: dict) -> dict:
    """
    Handle CreateAgent primitive — identity-only agent creation (ADR-138).

    Creates an agent record with title, role, and optional instructions.
    No scheduling, sources, or delivery — those live on tasks.
    """
    from services.agent_creation import create_agent_record

    title = input.get("title", "").strip()
    role = input.get("role", "custom")
    agent_instructions = input.get("agent_instructions")

    if not title:
        return {"success": False, "error": "missing_title", "message": "title is required"}

    # Detect mode: coordinator (headless) vs chat
    coordinator_id = getattr(auth, "coordinator_agent_id", None)
    is_coordinator = coordinator_id is not None

    origin = "coordinator_created" if is_coordinator else "user_configured"

    result = await create_agent_record(
        client=auth.client,
        user_id=auth.user_id,
        title=title,
        role=role,
        origin=origin,
        agent_instructions=agent_instructions or None,
    )

    if result.get("success"):
        agent_id = result["agent_id"]

        # Activity log
        try:
            from services.activity_log import write_activity
            await write_activity(
                client=auth.client,
                user_id=auth.user_id,
                event_type="agent_scheduled",
                summary=f"Created agent: {title}",
                event_ref=agent_id,
                metadata={
                    "origin": origin,
                    "role": role,
                    "coordinator_id": coordinator_id,
                },
            )
        except Exception:
            pass

    return result
