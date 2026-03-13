"""
Coordinator Primitives — ADR-092 Phase 5, updated ADR-111

  CreateAgent         — creates an agent (chat + headless, unified)
  AdvanceAgentSchedule — sets next_run_at=now on an existing agent (headless only)

CreateAgent uses shared create_agent_record() from agent_creation.py.
In headless/coordinator mode: origin=coordinator_created, execute_now=True, dedup via workspace.
In chat mode: origin=user_configured, respects user-specified schedule.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CreateAgent (chat + headless, ADR-111)
# =============================================================================

CREATE_AGENT_TOOL = {
    "name": "CreateAgent",
    "description": """Create a new agent for the user.

Use this to create a recurring agent based on the user's request.
Always confirm the agent config with the user before calling this in chat.

Required: title, skill
Optional: agent_instructions, sources, frequency, day, time, timezone,
          recipient_name, recipient_role, audience, tone, detail_level,
          dedup_key (coordinator mode only)

skill: digest|prepare|monitor|research|synthesize|orchestrate|act|custom
frequency: daily|weekly|biweekly|monthly (default: weekly)

Examples:
- CreateAgent(title="Slack Recap", skill="digest", frequency="daily")
- CreateAgent(title="Weekly Status", skill="synthesize", frequency="weekly", recipient_name="Sarah")
- CreateAgent(title="Meeting Prep", skill="prepare", frequency="daily", time="08:00")

Always use the user's stated frequency — don't override with defaults.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title for the agent"
            },
            "skill": {
                "type": "string",
                "description": "Skill: digest, prepare, synthesize, monitor, research, orchestrate, act, custom"
            },
            "agent_instructions": {
                "type": "string",
                "description": "Behavioral instructions for the agent"
            },
            "sources": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Data sources. In coordinator mode, inherits coordinator sources if omitted."
            },
            "frequency": {
                "type": "string",
                "description": "Schedule frequency: daily, weekly, biweekly, monthly"
            },
            "day": {
                "type": "string",
                "description": "Day of week for weekly+ schedules (e.g. monday)"
            },
            "time": {
                "type": "string",
                "description": "Time of day (e.g. 09:00)"
            },
            "timezone": {
                "type": "string",
                "description": "Timezone (e.g. America/New_York)"
            },
            "recipient_name": {
                "type": "string",
                "description": "Name of the recipient"
            },
            "recipient_role": {
                "type": "string",
                "description": "Role of the recipient"
            },
            "audience": {
                "type": "string",
                "description": "Target audience: manager, team, stakeholders, executive"
            },
            "tone": {
                "type": "string",
                "description": "Tone: formal, conversational"
            },
            "detail_level": {
                "type": "string",
                "description": "Detail level: brief, standard, detailed"
            },
            "trigger_context": {
                "type": "object",
                "description": "Context passed to generation run (coordinator mode)"
            },
            "dedup_key": {
                "type": "string",
                "description": "Unique key to prevent duplicates (coordinator mode)"
            }
        },
        "required": ["title", "skill"]
    }
}


async def handle_create_agent(auth: Any, input: dict) -> dict:
    """
    Handle CreateAgent primitive — unified for chat + headless (ADR-111).

    In headless/coordinator mode:
      - origin=coordinator_created
      - execute_now=True (next_run_at=now)
      - Sources inherited from coordinator if not specified
      - Dedup log appended to coordinator workspace

    In chat mode:
      - origin=user_configured
      - Respects user-specified schedule
      - No dedup handling (TP manages via conversation)
    """
    from services.agent_creation import create_agent_record

    title = input.get("title", "").strip()
    skill = input.get("skill", "custom")
    agent_instructions = input.get("agent_instructions", "")
    sources = input.get("sources")
    dedup_key = input.get("dedup_key", "")
    trigger_context = input.get("trigger_context", {})

    # Detect mode: coordinator (headless) vs chat
    coordinator_id = getattr(auth, "coordinator_agent_id", None)
    is_coordinator = coordinator_id is not None

    # Build recipient_context from flat fields
    recipient_context = {}
    if input.get("recipient_name"):
        recipient_context["name"] = input["recipient_name"]
    if input.get("recipient_role"):
        recipient_context["role"] = input["recipient_role"]

    # Build type_config from flat fields
    type_config = {}
    for field in ["audience", "tone", "detail_level", "subject", "format"]:
        if input.get(field):
            type_config[field] = input[field]

    if is_coordinator:
        # Coordinator mode: inherit sources, execute immediately
        if sources is None:
            sources = getattr(auth, "agent_sources", []) or []

        result = await create_agent_record(
            client=auth.client,
            user_id=auth.user_id,
            title=title,
            skill=skill,
            origin="coordinator_created",
            agent_instructions=agent_instructions or None,
            sources=sources,
            schedule={"frequency": "once"},
            mode="recurring",
            trigger_type="manual",
            execute_now=True,
            recipient_context=recipient_context or None,
            type_config=type_config or None,
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
                    summary=f"Coordinator created: {title}",
                    event_ref=agent_id,
                    metadata={
                        "coordinator_id": coordinator_id,
                        "skill": skill,
                        "dedup_key": dedup_key,
                        "trigger_context": trigger_context,
                    },
                )
            except Exception:
                pass

            # Append to coordinator's workspace dedup log
            try:
                from services.workspace import AgentWorkspace
                coord_result = auth.client.table("agents").select("title").eq("id", coordinator_id).single().execute()
                coord_title = (coord_result.data or {}).get("title", "")
                coord_slug = coord_title.lower().strip()
                coord_slug = "".join(c if c.isalnum() or c == "-" else "-" for c in coord_slug)
                coord_slug = "-".join(p for p in coord_slug.split("-") if p)[:50] or str(coordinator_id)[:36]
                coord_ws = AgentWorkspace(auth.client, auth.user_id, coord_slug)
                await coord_ws.append_created_agent(title, dedup_key)
            except Exception:
                pass

            result["dedup_key"] = dedup_key

        return result

    else:
        # Chat mode: user-configured, respect schedule
        result = await create_agent_record(
            client=auth.client,
            user_id=auth.user_id,
            title=title,
            skill=skill,
            origin="user_configured",
            agent_instructions=agent_instructions or None,
            sources=sources or [],
            frequency=input.get("frequency"),
            day=input.get("day"),
            time=input.get("time"),
            timezone_str=input.get("timezone"),
            recipient_context=recipient_context or None,
            type_config=type_config or None,
        )

        return result


# =============================================================================
# AdvanceAgentSchedule (headless only, ADR-092)
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
            pass

        return {
            "success": True,
            "agent_id": agent_id,
            "title": d.get("title"),
            "message": f"Advanced '{d.get('title')}' — will run on next scheduler tick.",
        }

    except Exception as e:
        logger.error(f"[COORDINATOR] AdvanceAgentSchedule failed: {e}")
        return {"success": False, "error": "advance_failed", "message": str(e)}
