"""
Coordinator Primitives — ADR-092 Phase 5

Headless-only write primitives for coordinator agents.

  CreateAgent         — creates a child agent with origin=coordinator_created
  AdvanceAgentSchedule — sets next_run_at=now on an existing agent

These replace signal processing's create_signal_emergent and trigger_existing actions.
Deduplication is the coordinator's responsibility via agent_memory.created_agents.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CreateAgent
# =============================================================================

CREATE_AGENT_TOOL = {
    "name": "CreateAgent",
    "description": """Create a new agent on behalf of the user.

Use when your coordinator instructions tell you to create a specific piece of work
in response to a detected condition (e.g. an upcoming meeting, a flagged email thread,
a stalled project).

Before creating, check your agent_memory.created_agents to avoid
duplicating an agent for the same underlying event (use dedup_key for this).

The created agent will run once immediately (trigger_type=manual) unless
you specify a schedule. It appears in the user's agents list with
origin=coordinator_created, attributed to this coordinator.

Required: title, skill
Optional: agent_instructions, sources (inherits coordinator's if omitted),
          trigger_context (passed to the generation run), dedup_key (for deduplication)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title for the new agent"
            },
            "skill": {
                "type": "string",
                "description": "Skill of the agent (e.g. digest, prepare, synthesize, monitor, research, orchestrate, custom)"
            },
            "agent_instructions": {
                "type": "string",
                "description": "Specific instructions for the child agent's generation"
            },
            "sources": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Data sources for the agent. Inherits coordinator sources if omitted."
            },
            "trigger_context": {
                "type": "object",
                "description": "Context passed to the generation run (e.g. meeting details, thread summary)"
            },
            "dedup_key": {
                "type": "string",
                "description": "Unique key for this event (e.g. 'brief:calendar_event_id_xyz'). Used to prevent duplicate creation."
            }
        },
        "required": ["title", "skill"]
    }
}


async def handle_create_agent(auth: Any, input: dict) -> dict:
    """
    Handle CreateAgent primitive.

    Creates a child agent with origin=coordinator_created.
    The coordinator_agent_id from auth context links it back.

    Returns {success, agent_id, title, message}
    """
    from .write import VALID_SKILLS, SKILL_TO_SCOPE

    title = input.get("title", "").strip()
    skill = input.get("skill", "custom")
    if skill not in VALID_SKILLS:
        skill = "custom"
    agent_instructions = input.get("agent_instructions", "")
    sources = input.get("sources")
    trigger_context = input.get("trigger_context", {})
    dedup_key = input.get("dedup_key", "")

    if not title:
        return {"success": False, "error": "missing_title", "message": "title is required"}

    user_id = auth.user_id
    coordinator_id = getattr(auth, "coordinator_agent_id", None)

    # Inherit sources from coordinator if not specified
    if sources is None:
        sources = getattr(auth, "agent_sources", []) or []

    now = datetime.now(timezone.utc)

    try:
        agent_data = {
            "user_id": user_id,
            "title": title,
            "skill": skill,
            "scope": SKILL_TO_SCOPE.get(skill, "knowledge"),  # ADR-109: required NOT NULL
            "mode": "recurring",  # child agents run once (manual trigger)
            "trigger_type": "manual",
            "origin": "coordinator_created",
            "status": "active",
            "sources": sources,
            "schedule": {"frequency": "once"},
            "next_run_at": now.isoformat(),  # run immediately
        }

        result = (
            auth.client.table("agents")
            .insert(agent_data)
            .execute()
        )

        if not result.data:
            return {"success": False, "error": "insert_failed", "message": "Failed to create agent"}

        new_id = result.data[0]["id"]

        # ADR-106: Workspace is singular source of truth for instructions
        if agent_instructions:
            from services.workspace import AgentWorkspace, get_agent_slug
            child_ws = AgentWorkspace(auth.client, user_id, get_agent_slug(result.data[0]))
            await child_ws.write("AGENT.md", agent_instructions,
                                 summary="Agent identity and behavioral instructions")

        logger.info(f"[COORDINATOR] Created agent: {title} ({new_id}), coordinator={coordinator_id}")

        # Write activity log
        try:
            from services.activity_log import write_activity
            await write_activity(
                client=auth.client,
                user_id=user_id,
                event_type="agent_scheduled",
                summary=f"Coordinator created: {title}",
                event_ref=new_id,
                metadata={
                    "coordinator_id": coordinator_id,
                    "skill": skill,
                    "dedup_key": dedup_key,
                    "trigger_context": trigger_context,
                },
            )
        except Exception:
            pass  # Non-fatal

        # ADR-106: Append to coordinator's workspace dedup log
        if coordinator_id:
            try:
                from services.workspace import AgentWorkspace
                # Need coordinator's slug — fetch title
                coord_result = auth.client.table("agents").select("title").eq("id", coordinator_id).single().execute()
                coord_title = (coord_result.data or {}).get("title", "")
                coord_slug = coord_title.lower().strip()
                coord_slug = "".join(c if c.isalnum() or c == "-" else "-" for c in coord_slug)
                coord_slug = "-".join(p for p in coord_slug.split("-") if p)[:50] or str(coordinator_id)[:36]

                coord_ws = AgentWorkspace(auth.client, user_id, coord_slug)
                await coord_ws.append_created_agent(title, dedup_key)
            except Exception:
                pass  # Non-fatal

        return {
            "success": True,
            "agent_id": new_id,
            "title": title,
            "dedup_key": dedup_key,
            "message": f"Created agent '{title}' — queued for immediate generation.",
        }

    except Exception as e:
        logger.error(f"[COORDINATOR] CreateAgent failed: {e}")
        return {"success": False, "error": "creation_failed", "message": str(e)}


# =============================================================================
# AdvanceAgentSchedule
# =============================================================================

ADVANCE_AGENT_SCHEDULE_TOOL = {
    "name": "AdvanceAgentSchedule",
    "description": """Advance an existing agent's schedule to run now.

Use when you detect that a condition warrants running an existing agent
immediately, rather than waiting for its next scheduled run.

This sets next_run_at to now — the scheduler will pick it up on the next 5-minute tick.
The agent's schedule is preserved; this is a one-time advancement.

Requires the agent_id of the target agent. Use Search or List
to find the right agent by title or type before calling this.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "UUID of the agent to advance"
            },
            "reason": {
                "type": "string",
                "description": "Brief reason for advancing (logged to activity log)"
            }
        },
        "required": ["agent_id"]
    }
}


async def handle_advance_agent_schedule(auth: Any, input: dict) -> dict:
    """
    Handle AdvanceAgentSchedule primitive.

    Sets next_run_at=now so the scheduler picks it up immediately.
    Preserves the agent's existing schedule config.

    Returns {success, agent_id, message}
    """
    agent_id = input.get("agent_id", "").strip()
    reason = input.get("reason", "Coordinator-initiated advancement")

    if not agent_id:
        return {"success": False, "error": "missing_id", "message": "agent_id is required"}

    user_id = auth.user_id
    now = datetime.now(timezone.utc)

    try:
        # Verify the agent belongs to this user and is active
        check = (
            auth.client.table("agents")
            .select("id, title, status, user_id")
            .eq("id", agent_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if not check or not check.data:
            return {
                "success": False,
                "error": "not_found",
                "message": f"Agent {agent_id} not found or not owned by this user",
            }

        d = check.data
        if d.get("status") not in ("active",):
            return {
                "success": False,
                "error": "not_active",
                "message": f"Agent '{d.get('title')}' is {d.get('status')} — cannot advance",
            }

        auth.client.table("agents").update({
            "next_run_at": now.isoformat(),
        }).eq("id", agent_id).execute()

        logger.info(f"[COORDINATOR] Advanced schedule: {d.get('title')} ({agent_id}), reason={reason}")

        try:
            from services.activity_log import write_activity
            await write_activity(
                client=auth.client,
                user_id=user_id,
                event_type="agent_scheduled",
                summary=f"Coordinator advanced: {d.get('title')}",
                event_ref=agent_id,
                metadata={
                    "coordinator_id": getattr(auth, "coordinator_agent_id", None),
                    "reason": reason,
                    "advanced_at": now.isoformat(),
                },
            )
        except Exception:
            pass  # Non-fatal

        return {
            "success": True,
            "agent_id": agent_id,
            "title": d.get("title"),
            "message": f"Advanced '{d.get('title')}' — will run on next scheduler tick.",
        }

    except Exception as e:
        logger.error(f"[COORDINATOR] AdvanceAgentSchedule failed: {e}")
        return {"success": False, "error": "advance_failed", "message": str(e)}
