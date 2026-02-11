"""
Execute Primitive

External operations on platforms and entities.

Usage:
  Execute(action="platform.sync", target="platform:slack")
  Execute(action="platform.publish", target="deliverable:uuid", via="platform:twitter")
  Execute(action="platform.send", target="platform:slack", params={channel: "#general", message: "Hello!"})
  Execute(action="deliverable.generate", target="deliverable:uuid")
"""

from typing import Any

from .refs import parse_ref, resolve_ref


EXECUTE_TOOL = {
    "name": "Execute",
    "description": """Perform external operations.

Actions:
- platform.sync: Pull latest from platform
- platform.publish: Push deliverable content to platform
- platform.send: Send ad-hoc message to platform (Slack, Gmail, Notion)
- platform.auth: Initiate OAuth connection
- deliverable.generate: Run content generation
- deliverable.schedule: Update schedule
- deliverable.approve: Approve pending version
- memory.extract: Extract from conversation

Examples:
- Execute(action="platform.sync", target="platform:slack")
- Execute(action="deliverable.generate", target="deliverable:uuid-123")
- Execute(action="platform.publish", target="deliverable:uuid", via="platform:twitter")
- Execute(action="platform.send", target="platform:slack", params={channel: "#general", message: "Hello!"})
- Execute(action="platform.send", target="platform:gmail", params={to: "user@example.com", subject: "Hi", body: "Hello!"})""",
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
        "description": "Publish deliverable content to platform",
        "target_types": ["deliverable"],
        "requires": ["via"],
    },
    "platform.send": {
        "description": "Send ad-hoc message to platform (not tied to a deliverable)",
        "target_types": ["platform"],
        "params_schema": {
            "slack": {"required": ["channel", "message"]},
            "gmail": {"required": ["to", "subject", "body"]},
            "notion": {"required": ["page_id", "content"]},
        },
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
        "platform.send": _handle_platform_send,
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
    versions = auth.client.table("deliverable_versions").select("*").eq(
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
    """
    Generate deliverable content.

    ADR-042: Simplified single-call flow replacing 3-step pipeline.
    Inline execution - no job queue, no chained work_tickets.
    """
    from services.deliverable_execution import execute_deliverable_generation

    # Execute inline with simplified flow
    result = await execute_deliverable_generation(
        client=auth.client,
        user_id=auth.user_id,
        deliverable=entity,
        trigger_context={"type": "execute_primitive"},
    )

    if not result.get("success"):
        raise ValueError(result.get("message", "Generation failed"))

    return {
        "status": result.get("status", "staged"),
        "version_id": result.get("version_id"),
        "version_number": result.get("version_number"),
        "draft": result.get("draft"),
        "message": result.get("message"),
    }


async def _handle_deliverable_approve(auth, entity, ref, via, params):
    """Approve pending deliverable version."""
    deliverable_id = entity.get("id")
    version_id = params.get("version_id")

    if not version_id:
        # Get latest pending version
        versions = auth.client.table("deliverable_versions").select("*").eq(
            "deliverable_id", deliverable_id
        ).eq("status", "pending_approval").order("version_number", desc=True).limit(1).execute()

        if not versions.data:
            raise ValueError("No pending version to approve")

        version_id = versions.data[0]["id"]

    # Approve
    from datetime import datetime, timezone

    auth.client.table("deliverable_versions").update({
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


async def _handle_platform_send(auth, entity, ref, via, params):
    """
    Send ad-hoc message to platform.

    Unlike platform.publish (which sends deliverable content), this sends
    arbitrary messages directly to platforms - useful for quick comms like
    "Hey, following up on our conversation...".

    Params by platform:
    - Slack: {channel: "#general" or "@user", message: "..."}
    - Gmail: {to: "email@example.com", subject: "...", body: "..."}
    - Notion: {page_id: "...", content: "..."} (creates a comment or block)
    """
    import logging
    from integrations.core.client import get_mcp_manager, MCP_AVAILABLE
    from integrations.core.tokens import get_token_manager

    logger = logging.getLogger(__name__)

    provider = entity.get("provider")
    if not provider:
        raise ValueError("Platform entity missing provider")

    # Validate required params per platform
    action_def = ACTION_CATALOG.get("platform.send", {})
    params_schema = action_def.get("params_schema", {})
    platform_schema = params_schema.get(provider, {})
    required_params = platform_schema.get("required", [])

    missing = [p for p in required_params if not params.get(p)]
    if missing:
        raise ValueError(f"platform.send to {provider} requires params: {', '.join(missing)}")

    # Get integration credentials
    integration = auth.client.table("user_integrations").select(
        "access_token_encrypted, metadata, status"
    ).eq("user_id", auth.user_id).eq("provider", provider).single().execute()

    if not integration.data:
        raise ValueError(f"No {provider} integration found. Connect it first.")

    if integration.data.get("status") != "active":
        raise ValueError(f"{provider} integration is not active")

    # Decrypt token
    token_manager = get_token_manager()
    access_token = token_manager.decrypt(integration.data["access_token_encrypted"])
    metadata = integration.data.get("metadata", {}) or {}

    # Dispatch by provider
    if provider == "slack":
        return await _send_slack_message(auth, params, access_token, metadata, logger)
    elif provider == "gmail":
        return await _send_gmail_message(auth, params, access_token, metadata, logger)
    elif provider == "notion":
        return await _send_notion_content(auth, params, access_token, metadata, logger)
    else:
        raise ValueError(f"platform.send not supported for {provider}")


async def _send_slack_message(auth, params, access_token, metadata, logger):
    """
    Send a Slack message via MCP.

    Supports:
    - Channel IDs (C...): Posts to channel
    - Channel names (#...): Posts to channel
    - User IDs (U...): Auto-opens DM and posts there
    - "self": DMs the user who authorized the integration

    ADR-047: Auto-open DM for user IDs enables direct messaging.
    """
    import json
    from integrations.core.client import get_mcp_manager, MCP_AVAILABLE
    from integrations.platform_registry import validate_params, map_params_to_mcp

    if not MCP_AVAILABLE:
        raise ValueError("MCP not available. Install: pip install mcp")

    channel = params.get("channel")
    message = params.get("message")
    team_id = metadata.get("team_id")

    if not team_id:
        raise ValueError("Missing team_id in Slack integration metadata")

    # Resolve "self" to the authed user's Slack ID
    if channel and channel.lower() == "self":
        authed_user_id = metadata.get("authed_user_id")
        if not authed_user_id:
            raise ValueError(
                "Cannot resolve 'self' - authed_user_id not in integration metadata. "
                "Reconnect Slack to capture your user ID, or use list_platform_resources to find it."
            )
        channel = authed_user_id
        logger.info(f"[PLATFORM_SEND] Resolved 'self' to user ID {channel}")

    # Validate params using registry (after resolving 'self')
    is_valid, errors = validate_params("slack", {"channel": channel, "message": message})
    if not is_valid:
        raise ValueError(f"Invalid Slack params: {'; '.join(errors)}")

    mcp = get_mcp_manager()

    # Auto-open DM if channel is a user ID (starts with U)
    target_channel = channel
    is_dm = False

    if channel and channel.startswith("U"):
        logger.info(f"[PLATFORM_SEND] Detected user ID {channel}, opening DM channel...")

        dm_channel_id = await mcp.open_slack_dm(
            user_id=auth.user_id,
            slack_user_id=channel,
            bot_token=access_token,
            team_id=team_id,
        )

        if not dm_channel_id:
            raise ValueError(
                f"Could not open DM with user {channel}. "
                f"Ensure the bot has permission to message this user."
            )

        target_channel = dm_channel_id
        is_dm = True
        logger.info(f"[PLATFORM_SEND] Opened DM channel {dm_channel_id} for user {channel}")

    # Map params to MCP-expected names using registry
    mcp_args = map_params_to_mcp("slack", {"channel": target_channel, "message": message})

    result = await mcp.call_tool(
        user_id=auth.user_id,
        provider="slack",
        tool_name="slack_post_message",
        arguments=mcp_args,
        env={
            "SLACK_BOT_TOKEN": access_token,
            "SLACK_TEAM_ID": team_id
        }
    )

    # Parse MCP result - handle CallToolResult object
    message_ts = None
    permalink = None
    error_message = None

    if isinstance(result, dict):
        message_ts = result.get("ts")
        permalink = result.get("permalink")
        if "error" in result:
            error_message = result.get("error")
    elif hasattr(result, "content"):
        # MCP CallToolResult - parse content
        for content_item in result.content:
            if hasattr(content_item, "text"):
                try:
                    parsed = json.loads(content_item.text)
                    if isinstance(parsed, dict):
                        message_ts = parsed.get("ts")
                        permalink = parsed.get("permalink")
                        if "error" in parsed:
                            error_message = parsed.get("error")
                except (json.JSONDecodeError, TypeError):
                    # Check if raw text indicates error
                    if "error" in content_item.text.lower():
                        error_message = content_item.text
            # Check for isError flag on content item
            if hasattr(content_item, "isError") and content_item.isError:
                error_message = getattr(content_item, "text", "MCP tool execution failed")

    # Check for isError on result itself
    if hasattr(result, "isError") and result.isError:
        error_message = error_message or "MCP tool execution failed"

    if error_message:
        raise ValueError(f"Slack MCP error: {error_message}")

    logger.info(f"[PLATFORM_SEND] Sent Slack message to {target_channel}, ts={message_ts}")

    return {
        "status": "sent",
        "provider": "slack",
        "channel": target_channel,
        "original_target": channel,
        "is_dm": is_dm,
        "message_ts": message_ts,
        "permalink": permalink,
        "message": f"Message sent to {channel}" + (" (DM)" if is_dm else ""),
    }


async def _send_gmail_message(auth, params, access_token, metadata, logger):
    """Send a Gmail message via Gmail API."""
    import os
    from integrations.core.client import get_mcp_manager
    from integrations.core.types import ExportStatus

    to = params.get("to")
    subject = params.get("subject")
    body = params.get("body")
    cc = params.get("cc")

    # Gmail requires OAuth refresh flow - need refresh_token from metadata
    refresh_token = metadata.get("refresh_token")
    if not refresh_token:
        raise ValueError("Missing refresh_token in Gmail integration metadata")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured")

    mcp = get_mcp_manager()

    result = await mcp.send_gmail_message(
        user_id=auth.user_id,
        to=to,
        subject=subject,
        body=body,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        cc=cc,
    )

    if result.status != ExportStatus.SUCCESS:
        raise ValueError(result.error_message or "Failed to send email")

    logger.info(f"[PLATFORM_SEND] Sent Gmail to {to}")

    return {
        "status": "sent",
        "provider": "gmail",
        "to": to,
        "message_id": result.external_id,
        "message": f"Email sent to {to}",
    }


async def _send_notion_content(auth, params, access_token, metadata, logger):
    """Add content to Notion page via MCP."""
    from integrations.core.client import get_mcp_manager, MCP_AVAILABLE

    if not MCP_AVAILABLE:
        raise ValueError("MCP not available. Install: pip install mcp")

    page_id = params.get("page_id")
    content = params.get("content")

    mcp = get_mcp_manager()

    # Use notion-update-page to append a comment/block
    result = await mcp.call_tool(
        user_id=auth.user_id,
        provider="notion",
        tool_name="notion-create-comment",
        arguments={
            "page_id": page_id,
            "text": content,
        },
        env={"NOTION_TOKEN": access_token}
    )

    logger.info(f"[PLATFORM_SEND] Added Notion comment to page {page_id}")

    return {
        "status": "sent",
        "provider": "notion",
        "page_id": page_id,
        "message": f"Content added to Notion page",
    }
