"""
ManageAgent Primitive — ADR-138 + ADR-146 pattern; ADR-235 D2 narrows action enum.

Agent lifecycle management: update, pause, resume, archive.
Follows the ManageDomains pattern — single primitive, action enum.

ADR-235 D2 (2026-04-29): the `create` action is REMOVED from the chat-surface
tool definition. There is no chat-surface pathway for creating user-authored
Agents. The `_handle_create` function and `agent_creation.create_agent_record`
are preserved as service code (signup path uses them); only the LLM-facing
surface narrows. Singular Implementation: no parallel "deprecated but works"
creation path. If users need custom Agents in the future, a new ADR introduces
a new surface.

Agents are identities that execute tasks. Scheduling, sources, delivery live on tasks.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


MANAGE_AGENT_TOOL = {
    "name": "ManageAgent",
    "description": """Manage agent lifecycle: update, pause, resume, archive.

ADR-235 D2: there is no chat surface for creating new agents. The systemic
roster (Reviewer, YARNNN, the universal specialists per ADR-176) is fixed at
signup; configure tasks against it instead of authoring new agents.

**action="update"** — Change title, role, or instructions for an existing agent.
  ManageAgent(action="update", agent_slug="researcher", agent_instructions="Also track pricing changes")
  ManageAgent(action="update", agent_slug="writer", title="Senior Editor")

**action="pause"** — Stop an agent from executing tasks.
  ManageAgent(action="pause", agent_slug="researcher")

**action="resume"** — Reactivate a paused agent.
  ManageAgent(action="resume", agent_slug="researcher")

**action="archive"** — Retire an agent permanently.
  ManageAgent(action="archive", agent_slug="researcher")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["update", "pause", "resume", "archive"],
                "description": "Lifecycle operation. Note: 'create' is intentionally absent (ADR-235 D2).",
            },
            "title": {
                "type": "string",
                "description": "For update: agent title",
            },
            "role": {
                "type": "string",
                "description": "For update: briefer, monitor, researcher, drafter, analyst, writer, planner, scout",
            },
            "agent_slug": {
                "type": "string",
                "description": "Required for update/pause/resume/archive: the agent's slug",
            },
            "agent_instructions": {
                "type": "string",
                "description": "For update: behavioral directives",
            },
        },
        "required": ["action", "agent_slug"],
    },
}


async def handle_manage_agent(auth: Any, input: dict) -> dict:
    """Route ManageAgent to appropriate action handler.

    ADR-235 D2: 'create' is removed from the LLM-facing tool definition.
    `_handle_create` and `services.agent_creation.create_agent_record` are
    preserved for the kernel/signup path; only the chat surface narrows.
    A 'create' action arriving via the LLM-facing primitive surface returns
    an explicit error.
    """
    action = input.get("action", "")

    if action == "create":
        return {
            "success": False,
            "error": "create_action_disabled",
            "message": (
                "ManageAgent(action='create') is not available via the chat "
                "primitive surface (ADR-235 D2). The systemic roster is "
                "fixed at signup; configure tasks against it instead."
            ),
        }
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
