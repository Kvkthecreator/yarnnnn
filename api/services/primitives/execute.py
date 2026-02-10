"""
Execute Primitive

External operations on platforms and entities.

Usage:
  Execute(action="platform.sync", target="platform:slack")
  Execute(action="platform.publish", target="deliverable:uuid", via="platform:twitter")
  Execute(action="deliverable.generate", target="deliverable:uuid")
"""

from typing import Any

from .refs import parse_ref, resolve_ref


EXECUTE_TOOL = {
    "name": "Execute",
    "description": """Perform external operations.

Actions:
- platform.sync: Pull latest from platform
- platform.publish: Push content to platform
- platform.auth: Initiate OAuth connection
- deliverable.generate: Run content generation
- deliverable.schedule: Update schedule
- deliverable.approve: Approve pending version
- memory.extract: Extract from conversation

Examples:
- Execute(action="platform.sync", target="platform:slack")
- Execute(action="deliverable.generate", target="deliverable:uuid-123")
- Execute(action="platform.publish", target="deliverable:uuid", via="platform:twitter")""",
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
ACTION_CATALOG = {
    "platform.sync": {
        "description": "Sync latest content from platform",
        "target_types": ["platform"],
    },
    "platform.publish": {
        "description": "Publish content to platform",
        "target_types": ["deliverable"],
        "requires": ["via"],
    },
    "platform.auth": {
        "description": "Initiate platform OAuth flow",
        "target_types": ["platform"],
    },
    "deliverable.generate": {
        "description": "Generate deliverable content",
        "target_types": ["deliverable"],
    },
    "deliverable.schedule": {
        "description": "Update deliverable schedule",
        "target_types": ["deliverable"],
    },
    "deliverable.approve": {
        "description": "Approve pending deliverable version",
        "target_types": ["deliverable"],
    },
    "memory.extract": {
        "description": "Extract memories from conversation",
        "target_types": ["session"],
    },
    "work.run": {
        "description": "Execute work immediately",
        "target_types": ["work"],
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
        "platform.sync": _handle_platform_sync,
        "platform.publish": _handle_platform_publish,
        "deliverable.generate": _handle_deliverable_generate,
        "deliverable.approve": _handle_deliverable_approve,
        "work.run": _handle_work_run,
    }
    return handlers.get(action)


async def _handle_platform_sync(auth, entity, ref, via, params):
    """Sync latest from platform."""
    provider = entity.get("provider")

    # Trigger sync job
    from services.job_queue import enqueue_job

    job_id = await enqueue_job(
        "platform_sync",
        user_id=auth.user_id,
        provider=provider,
    )

    return {
        "status": "started",
        "job_id": job_id,
        "provider": provider,
        "message": f"Started syncing {provider}",
    }


async def _handle_platform_publish(auth, entity, ref, via, params):
    """Publish deliverable to platform."""
    from .refs import parse_ref, resolve_ref

    # Parse 'via' platform
    via_ref = parse_ref(via)
    platform = await resolve_ref(via_ref, auth)

    if not platform:
        raise ValueError(f"Platform not found: {via}")

    provider = platform.get("provider")
    deliverable_id = entity.get("id")

    # Get latest approved version
    versions = await auth.client.table("deliverable_versions").select("*").eq(
        "deliverable_id", deliverable_id
    ).eq("status", "approved").order("version_number", desc=True).limit(1).execute()

    if not versions.data:
        raise ValueError("No approved version to publish")

    version = versions.data[0]

    # Trigger publish
    from services.delivery import deliver_to_platform

    result = await deliver_to_platform(
        auth=auth,
        deliverable=entity,
        version=version,
        platform=platform,
    )

    return {
        "status": "published" if result.get("success") else "failed",
        "provider": provider,
        "version": version.get("version_number"),
        "message": f"Published to {provider}",
    }


async def _handle_deliverable_generate(auth, entity, ref, via, params):
    """Generate deliverable content."""
    deliverable_id = entity.get("id")

    # Get next version number
    versions = await auth.client.table("deliverable_versions").select("version_number").eq(
        "deliverable_id", deliverable_id
    ).order("version_number", desc=True).limit(1).execute()

    next_version = (versions.data[0]["version_number"] + 1) if versions.data else 1

    # Create pending version
    from uuid import uuid4
    from datetime import datetime, timezone

    version_id = str(uuid4())
    await auth.client.table("deliverable_versions").insert({
        "id": version_id,
        "deliverable_id": deliverable_id,
        "version_number": next_version,
        "status": "generating",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Trigger generation pipeline
    from services.job_queue import enqueue_job

    job_id = await enqueue_job(
        "deliverable_generate",
        deliverable_id=deliverable_id,
        version_id=version_id,
        user_id=auth.user_id,
    )

    return {
        "status": "generating",
        "version_id": version_id,
        "version_number": next_version,
        "job_id": job_id,
        "message": f"Generating version {next_version}",
    }


async def _handle_deliverable_approve(auth, entity, ref, via, params):
    """Approve pending deliverable version."""
    deliverable_id = entity.get("id")
    version_id = params.get("version_id")

    if not version_id:
        # Get latest pending version
        versions = await auth.client.table("deliverable_versions").select("*").eq(
            "deliverable_id", deliverable_id
        ).eq("status", "pending_approval").order("version_number", desc=True).limit(1).execute()

        if not versions.data:
            raise ValueError("No pending version to approve")

        version_id = versions.data[0]["id"]

    # Approve
    from datetime import datetime, timezone

    await auth.client.table("deliverable_versions").update({
        "status": "approved",
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", version_id).execute()

    return {
        "status": "approved",
        "version_id": version_id,
        "message": "Version approved",
    }


async def _handle_work_run(auth, entity, ref, via, params):
    """Execute work immediately."""
    work_id = entity.get("id")

    from services.job_queue import enqueue_job

    job_id = await enqueue_job(
        "work_execute",
        work_id=work_id,
        user_id=auth.user_id,
    )

    return {
        "status": "started",
        "work_id": work_id,
        "job_id": job_id,
        "message": "Work execution started",
    }
