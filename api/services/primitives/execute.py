"""
Execute Primitive

External operations on YARNNN entities. For platform MCP operations,
use MCP tools directly (ADR-048).

Usage:
  Execute(action="platform.publish", target="agent:uuid", via="platform:twitter")
  Execute(action="agent.generate", target="agent:uuid")

Note: platform.sync removed (ADR-085) — use RefreshPlatformContent primitive instead.
"""

from typing import Any

from .refs import parse_ref, resolve_ref


EXECUTE_TOOL = {
    "name": "Execute",
    "description": """Perform YARNNN orchestration operations.

Actions:
- platform.publish: Push approved agent content to platform
- agent.generate: Run content generation pipeline
- agent.schedule: Update agent schedule
- agent.approve: Approve pending version
- agent.acknowledge: Append a lightweight observation to agent memory from conversation context (use when user shares relevant information that should persist, but doesn't warrant full generation)
- memory.extract: Extract from conversation

NOTE: For direct platform operations (send messages, search pages, etc.),
use MCP tools directly: mcp__slack__*, mcp__notion__*, etc. (ADR-048)

NOTE: platform.sync removed — use RefreshPlatformContent(platform="...") instead (ADR-085).

Examples:
- Execute(action="agent.generate", target="agent:uuid-123")
- Execute(action="agent.acknowledge", target="agent:uuid-123", params={note: "User confirmed Q4 data is now finalized"})
- Execute(action="platform.publish", target="agent:uuid", via="platform:twitter")
- Execute(action="agent.approve", target="agent:uuid")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action to perform (e.g., 'platform.sync')"
            },
            "target": {
                "type": "string",
                "description": "Target entity reference"
            },
            "via": {
                "type": "string",
                "description": "Platform to use for publishing (for platform.publish)"
            },
            "params": {
                "type": "object",
                "description": "Additional action parameters"
            }
        },
        "required": ["action", "target"]
    }
}


# Action catalog with descriptions
# ADR-048: platform.send and platform.search removed - use MCP tools directly
# ADR-085: platform.sync removed - use RefreshPlatformContent primitive instead
ACTION_CATALOG = {
    "platform.publish": {
        "description": "Publish approved agent content to platform",
        "target_types": ["agent"],
        "requires": ["via"],
    },
    "agent.generate": {
        "description": "Generate agent content",
        "target_types": ["agent"],
    },
    "agent.schedule": {
        "description": "Update agent schedule",
        "target_types": ["agent"],
    },
    "agent.approve": {
        "description": "Approve pending agent version",
        "target_types": ["agent"],
    },
    "agent.acknowledge": {
        "description": "Append observation to agent memory (ADR-091: lightweight context update, no generation)",
        "target_types": ["agent"],
    },
    "memory.extract": {
        "description": "Extract memories from conversation",
        "target_types": ["session"],
    },
}


async def handle_execute(auth: Any, input: dict) -> dict:
    """
    Handle Execute primitive.

    Args:
        auth: Auth context with user_id and client
        input: {"action": "...", "target": "...", "via": "...", "params": {...}}

    Returns:
        {"success": True, "result": {...}, "action": "..."}
        or {"success": False, "error": "...", "message": "..."}
    """
    action = input.get("action", "")
    target = input.get("target", "")
    via = input.get("via")
    params = input.get("params", {})

    if not action:
        return {
            "success": False,
            "error": "missing_action",
            "message": "Action is required",
        }

    if not target:
        return {
            "success": False,
            "error": "missing_target",
            "message": "Target reference is required",
        }

    # Validate action exists
    action_def = ACTION_CATALOG.get(action)
    if not action_def:
        # Provide helpful message for removed actions
        if action in ("platform.send", "platform.search"):
            return {
                "success": False,
                "error": "action_moved",
                "message": f"'{action}' has been removed. Use MCP tools directly: "
                           f"mcp__slack__* for Slack, mcp__notion__* for Notion (ADR-048).",
                "available_actions": list(ACTION_CATALOG.keys()),
            }
        if action == "platform.sync":
            return {
                "success": False,
                "error": "action_moved",
                "message": "'platform.sync' has been replaced by RefreshPlatformContent(platform='...') "
                           "which runs a synchronous sync and returns results (ADR-085).",
                "available_actions": list(ACTION_CATALOG.keys()),
            }
        return {
            "success": False,
            "error": "unknown_action",
            "message": f"Unknown action: {action}. Use List(pattern='action:*') to see available actions.",
            "available_actions": list(ACTION_CATALOG.keys()),
        }

    # Parse target
    try:
        target_ref = parse_ref(target)
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_target",
            "message": str(e),
        }

    # Validate target type
    valid_types = action_def.get("target_types", [])
    if valid_types and target_ref.entity_type not in valid_types:
        return {
            "success": False,
            "error": "invalid_target_type",
            "message": f"Action '{action}' requires target type: {', '.join(valid_types)}",
        }

    # Check required params
    required = action_def.get("requires", [])
    missing = [r for r in required if not input.get(r)]
    if missing:
        return {
            "success": False,
            "error": "missing_params",
            "message": f"Action '{action}' requires: {', '.join(missing)}",
        }

    # Resolve target entity
    try:
        target_entity = await resolve_ref(target_ref, auth)
        if not target_entity:
            return {
                "success": False,
                "error": "target_not_found",
                "message": f"Target not found: {target}",
            }
    except Exception as e:
        return {
            "success": False,
            "error": "resolve_failed",
            "message": str(e),
        }

    # Dispatch to action handler
    handler = _get_action_handler(action)
    if not handler:
        return {
            "success": False,
            "error": "no_handler",
            "message": f"No handler implemented for action: {action}",
        }

    try:
        result = await handler(auth, target_entity, target_ref, via, params)
        return {
            "success": True,
            "result": result,
            "action": action,
            "target": target,
            "message": result.get("message", f"Executed {action}"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": "execution_failed",
            "message": str(e),
            "action": action,
            "target": target,
        }


def _get_action_handler(action: str):
    """Get handler function for action."""
    handlers = {
        "platform.publish": _handle_platform_publish,
        "agent.generate": _handle_agent_generate,
        "agent.approve": _handle_agent_approve,
        "agent.acknowledge": _handle_agent_acknowledge,
    }
    return handlers.get(action)


async def _handle_platform_publish(auth, entity, ref, via, params):
    """Publish agent to platform."""
    from .refs import parse_ref, resolve_ref

    # Parse 'via' platform
    via_ref = parse_ref(via)
    platform = await resolve_ref(via_ref, auth)

    if not platform:
        raise ValueError(f"Platform not found: {via}")

    provider = platform.get("provider")
    agent_id = entity.get("id")

    # Get latest approved version
    versions = auth.client.table("agent_runs").select("*").eq(
        "agent_id", agent_id
    ).eq("status", "approved").order("version_number", desc=True).limit(1).execute()

    if not versions.data:
        raise ValueError("No approved version to publish")

    version = versions.data[0]

    # Trigger publish
    from services.delivery import deliver_to_platform

    result = await deliver_to_platform(
        auth=auth,
        agent=entity,
        version=version,
        platform=platform,
    )

    return {
        "status": "published" if result.get("success") else "failed",
        "provider": provider,
        "version": version.get("version_number"),
        "message": f"Published to {provider}",
    }


async def _handle_agent_generate(auth, entity, ref, via, params):
    """
    Generate agent content.

    ADR-042: Simplified single-call flow replacing 3-step pipeline.
    Inline execution - no job queue, no chained work_tickets.
    """
    from services.agent_execution import execute_agent_generation

    # Execute inline with simplified flow
    result = await execute_agent_generation(
        client=auth.client,
        user_id=auth.user_id,
        agent=entity,
        trigger_context={"type": "execute_primitive"},
    )

    if not result.get("success"):
        raise ValueError(result.get("message", "Generation failed"))

    return {
        "status": result.get("status", "staged"),
        "run_id": result.get("run_id"),
        "version_number": result.get("version_number"),
        "draft": result.get("draft"),
        "message": result.get("message"),
    }


async def _handle_agent_approve(auth, entity, ref, via, params):
    """Approve pending agent version."""
    agent_id = entity.get("id")
    version_id = params.get("run_id")

    if not version_id:
        # Get latest pending version
        versions = auth.client.table("agent_runs").select("*").eq(
            "agent_id", agent_id
        ).eq("status", "pending_approval").order("version_number", desc=True).limit(1).execute()

        if not versions.data:
            raise ValueError("No pending version to approve")

        version_id = versions.data[0]["id"]

    # Approve
    from datetime import datetime, timezone

    auth.client.table("agent_runs").update({
        "status": "approved",
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", version_id).execute()

    return {
        "status": "approved",
        "run_id": run_id,
        "message": "Run approved",
    }


async def _handle_agent_acknowledge(auth, entity, ref, via, params):
    """
    Lightweight context update: append an observation to workspace.

    ADR-106 Phase 2: Writes to workspace memory/observations.md (source of truth).
    ADR-091: Graduated response — lighter than full generation.
    """
    note = params.get("note", "").strip()
    if not note:
        raise ValueError("params.note is required for agent.acknowledge")

    from services.workspace import AgentWorkspace, get_agent_slug

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(entity))
    count = await ws.append_observation(note, source="user")

    return {
        "status": "acknowledged",
        "note": note,
        "observations_total": count,
        "message": f"Noted: \"{note[:80]}{'...' if len(note) > 80 else ''}\"",
    }


