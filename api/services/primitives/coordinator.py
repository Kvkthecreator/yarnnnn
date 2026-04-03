"""
ManageAgent Primitive — ADR-138 + ADR-146 pattern

Agent lifecycle management: create, update, pause, resume, archive.
Follows the ManageTask/ManageDomains pattern — single primitive, action enum.

Agents are identities that execute tasks. Scheduling, sources, delivery live on tasks.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


MANAGE_AGENT_TOOL = {
    "name": "ManageAgent",
    "description": """Manage agent lifecycle: create, update, pause, resume, archive.

**action="create"** — Create a new agent identity with a role.
  ManageAgent(action="create", title="Competitive Intel", role="researcher")
  ManageAgent(action="create", title="Weekly Digest", role="briefer", agent_instructions="Focus on product launches")

**action="update"** — Change title, role, or instructions for an existing agent.
  ManageAgent(action="update", agent_slug="competitive-intel", agent_instructions="Also track pricing changes")
  ManageAgent(action="update", agent_slug="weekly-digest", title="Daily Digest")

**action="pause"** — Stop an agent from executing tasks.
  ManageAgent(action="pause", agent_slug="competitive-intel")

**action="resume"** — Reactivate a paused agent.
  ManageAgent(action="resume", agent_slug="competitive-intel")

**action="archive"** — Retire an agent permanently.
  ManageAgent(action="archive", agent_slug="competitive-intel")

role options: briefer, monitor, researcher, drafter, analyst, writer, planner, scout""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "pause", "resume", "archive"],
                "description": "Lifecycle operation",
            },
            "title": {
                "type": "string",
                "description": "For create/update: agent title",
            },
            "role": {
                "type": "string",
                "description": "For create: briefer, monitor, researcher, drafter, analyst, writer, planner, scout",
            },
            "agent_slug": {
                "type": "string",
                "description": "For update/pause/resume/archive: the agent's slug",
            },
            "agent_instructions": {
                "type": "string",
                "description": "For create/update: behavioral directives",
            },
        },
        "required": ["action"],
    },
}


async def handle_manage_agent(auth: Any, input: dict) -> dict:
    """Route ManageAgent to appropriate action handler."""
    action = input.get("action", "create")

    if action == "create":
        return await _handle_create(auth, input)
    elif action == "update":
        return await _handle_update(auth, input)
    elif action in ("pause", "resume", "archive"):
        return await _handle_status_change(auth, input, action)
    else:
        return {"success": False, "error": "invalid_action", "message": f"Unknown action: {action}"}


async def _handle_create(auth: Any, input: dict) -> dict:
    """Create a new agent — identity only (ADR-138)."""
    from services.agent_creation import create_agent_record

    title = input.get("title", "").strip()
    role = input.get("role", "custom")
    agent_instructions = input.get("agent_instructions")

    if not title:
        return {"success": False, "error": "missing_title", "message": "action=create requires title"}
    if not role or role == "custom":
        return {"success": False, "error": "missing_role", "message": "action=create requires role"}

    # Detect mode: coordinator (headless) vs chat
    coordinator_id = getattr(auth, "coordinator_agent_id", None)
    origin = "coordinator_created" if coordinator_id else "user_configured"

    result = await create_agent_record(
        client=auth.client,
        user_id=auth.user_id,
        title=title,
        role=role,
        origin=origin,
        agent_instructions=agent_instructions or None,
    )

    if result.get("success"):
        try:
            from services.activity_log import write_activity
            await write_activity(
                client=auth.client,
                user_id=auth.user_id,
                event_type="agent_scheduled",
                summary=f"Created agent: {title}",
                event_ref=result["agent_id"],
                metadata={"origin": origin, "role": role, "action": "create"},
            )
        except Exception:
            pass

    return result


async def _handle_update(auth: Any, input: dict) -> dict:
    """Update agent title, role, or instructions."""
    agent_slug = input.get("agent_slug", "").strip()
    if not agent_slug:
        return {"success": False, "error": "missing_slug", "message": "action=update requires agent_slug"}

    # Resolve agent by slug
    agent = _resolve_agent(auth.client, auth.user_id, agent_slug)
    if not agent:
        return {"success": False, "error": "not_found", "message": f"Agent '{agent_slug}' not found"}

    agent_id = agent["id"]
    updates = {}

    if input.get("title"):
        updates["title"] = input["title"].strip()
    if input.get("role"):
        updates["role"] = input["role"]

    # Update DB fields if any
    if updates:
        try:
            auth.client.table("agents").update(updates).eq("id", agent_id).execute()
        except Exception as e:
            return {"success": False, "error": "db_error", "message": str(e)}

    # Update workspace instructions if provided
    instructions = input.get("agent_instructions")
    if instructions is not None:
        try:
            from services.workspace import AgentWorkspace
            ws = AgentWorkspace(auth.client, auth.user_id, agent_slug)
            await ws.write("AGENT.md", instructions, summary="Instructions updated via ManageAgent")
        except Exception as e:
            logger.warning(f"[MANAGE_AGENT] Failed to write AGENT.md for {agent_slug}: {e}")

    changes = list(updates.keys())
    if instructions is not None:
        changes.append("agent_instructions")

    return {
        "success": True,
        "action": "update",
        "agent_id": agent_id,
        "agent_slug": agent_slug,
        "changes": changes,
        "message": f"Updated {agent_slug}: {', '.join(changes)}",
    }


async def _handle_status_change(auth: Any, input: dict, action: str) -> dict:
    """Pause, resume, or archive an agent."""
    agent_slug = input.get("agent_slug", "").strip()
    if not agent_slug:
        return {"success": False, "error": "missing_slug", "message": f"action={action} requires agent_slug"}

    agent = _resolve_agent(auth.client, auth.user_id, agent_slug)
    if not agent:
        return {"success": False, "error": "not_found", "message": f"Agent '{agent_slug}' not found"}

    status_map = {"pause": "paused", "resume": "active", "archive": "archived"}
    new_status = status_map[action]
    agent_id = agent["id"]

    try:
        auth.client.table("agents").update(
            {"status": new_status}
        ).eq("id", agent_id).execute()
    except Exception as e:
        return {"success": False, "error": "db_error", "message": str(e)}

    try:
        from services.activity_log import write_activity
        await write_activity(
            client=auth.client,
            user_id=auth.user_id,
            event_type="agent_scheduled",
            summary=f"Agent {action}d: {agent.get('title', agent_slug)}",
            event_ref=agent_id,
            metadata={"action": action, "new_status": new_status},
        )
    except Exception:
        pass

    return {
        "success": True,
        "action": action,
        "agent_id": agent_id,
        "agent_slug": agent_slug,
        "status": new_status,
        "message": f"{agent.get('title', agent_slug)} is now {new_status}",
    }


def _resolve_agent(client, user_id: str, slug: str) -> dict | None:
    """Look up agent by slug."""
    try:
        result = client.table("agents").select("*").eq(
            "user_id", user_id
        ).eq("slug", slug).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None
