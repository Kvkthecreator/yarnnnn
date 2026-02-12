"""
Platform Registry - ADR-047

Structured configuration for platform-specific behaviors, quirks, and validation.
TP consumes this registry to generate accurate guidance.

Usage:
    from integrations.platform_registry import get_platform_config, get_tp_guidance

    config = get_platform_config("slack")
    guidance = get_tp_guidance("slack")  # For TP system prompt
"""

from typing import Any, Optional
import re


# =============================================================================
# Platform Registry
# =============================================================================

PLATFORM_REGISTRY: dict[str, dict[str, Any]] = {
    "slack": {
        "display_name": "Slack",
        "mcp_server": "@modelcontextprotocol/server-slack",
        "transport": "stdio",

        "params": {
            "channel": {
                "description": "Slack channel or user to send message to",
                "mcp_name": "channel_id",  # What MCP actually expects
                "valid_patterns": [
                    r"^C[A-Z0-9]+$",  # Channel ID: C0123ABC456
                    r"^#[\w-]+$",     # Channel name: #general
                    r"^U[A-Z0-9]+$",  # User ID: U0123ABC456 (auto-opens DM)
                    r"^self$",        # "self" resolves to authed user (case-insensitive)
                ],
                "valid_examples": ["C0123ABC456", "#general", "U0123ABC456", "self"],
                "invalid_patterns": [
                    r"^@",  # @mentions don't work
                ],
                "invalid_examples": ["@me", "@self", "@username"],
                "resolution_tool": "list_platform_resources",
                "error_hint": "Use channel ID (C...), #channel-name, user ID (U...), or 'self' for DM to yourself.",
            },
            "message": {
                "description": "Message content to send",
                "mcp_name": "text",
                "valid_patterns": [r".+"],  # Any non-empty string
            },
        },

        # ADR-050: Platform tools via MCP Gateway
        "capabilities": {
            "send_message": {
                "supported": True,
                "platform_tool": "platform_slack_send_message",
                "notes": "Use channel_id param (C..., #name, U... for DM)",
            },
            "send_dm": {
                "supported": True,
                "platform_tool": "platform_slack_send_message",
                "notes": "Use user ID (U...) as channel_id - auto-opens DM. For 'self', use list_integrations to get authed_user_id.",
            },
            "list_channels": {
                "supported": True,
                "platform_tool": "platform_slack_list_channels",
            },
        },

        "auth": {
            "type": "oauth",
            "token_field": "access_token_encrypted",
            "metadata_required": ["team_id"],
        },

        "quirks": [
            "Use platform_slack_* tools directly (ADR-050)",
            "@username/@me/@self are NOT valid - use user ID (U...) instead",
            "User IDs (U...) auto-open DM channel before sending",
            "Bot must be invited to private channels",
        ],

        "version": "2026-02-12",
    },

    "gmail": {
        "display_name": "Gmail",
        "mcp_server": None,  # Direct API, not MCP
        "transport": "direct_api",

        "params": {
            "to": {
                "description": "Recipient email address",
                "valid_patterns": [r"^[^@]+@[^@]+\.[^@]+$"],  # Basic email pattern
                "valid_examples": ["user@example.com"],
            },
            "subject": {
                "description": "Email subject line",
                "valid_patterns": [r".+"],
            },
            "body": {
                "description": "Email body content",
                "valid_patterns": [r".+"],
            },
            "cc": {
                "description": "CC recipients (optional)",
                "valid_patterns": [r"^[^@]+@[^@]+\.[^@]+$"],
                "optional": True,
            },
        },

        # ADR-046: Platform tools via Direct API
        "capabilities": {
            "search": {
                "supported": True,
                "platform_tool": "platform_gmail_search",
                "notes": "Search messages with Gmail query syntax",
            },
            "get_thread": {
                "supported": True,
                "platform_tool": "platform_gmail_get_thread",
                "notes": "Get full email thread/conversation",
            },
            "send": {
                "supported": True,
                "platform_tool": "platform_gmail_send",
                "notes": "Send email - confirm recipient first",
            },
            "create_draft": {
                "supported": True,
                "platform_tool": "platform_gmail_create_draft",
                "notes": "Preferred for review workflow",
            },
        },

        "auth": {
            "type": "oauth_refresh",
            "token_field": "access_token_encrypted",
            "metadata_required": ["refresh_token"],
            "env_required": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        },

        "quirks": [
            "Use platform_gmail_* tools directly (ADR-046)",
            "Uses refresh_token flow, not direct access_token",
            "Access token refreshed automatically on each call",
            "Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars",
            "Prefer create_draft over send for deliverables",
        ],

        "version": "2026-02-12",
    },

    "notion": {
        "display_name": "Notion",
        "mcp_server": "@notionhq/notion-mcp-server",
        "transport": "stdio",
        "transport_args": ["--transport", "stdio"],

        "params": {
            "page_id": {
                "description": "Notion page ID or URL",
                "mcp_name": "page_id",  # Used in parent object: {page_id: ...}
                "valid_patterns": [
                    r"^[a-f0-9-]{32,36}$",  # UUID format (with or without dashes)
                    r"^[a-f0-9]{32}$",      # UUID without dashes
                    r"^https://.*notion\.(so|site)/",  # Notion URL
                ],
                "valid_examples": ["abc123def456", "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "https://notion.so/workspace/Page-abc123"],
                "invalid_patterns": [
                    r"^@",  # @mentions don't work
                ],
                "invalid_examples": ["@page", "page-name"],
                "resolution_tool": "notion-search",
                "error_hint": "Use page UUID (with or without dashes) or full Notion URL. Use notion-search to find pages.",
            },
            "content": {
                "description": "Content to add to page (as comment or page content)",
                "mcp_name": "rich_text",  # For comments, wrapped in rich_text array
                "valid_patterns": [r".+"],
            },
        },

        # ADR-050: Platform tools via MCP Gateway
        "capabilities": {
            "search": {
                "supported": True,
                "platform_tool": "platform_notion_search",
                "notes": "Returns page IDs for use with other Notion tools",
            },
            "add_comment": {
                "supported": True,
                "platform_tool": "platform_notion_create_comment",
                "notes": "Add comment to a page by page_id",
            },
        },

        "auth": {
            "type": "oauth",
            "token_field": "access_token_encrypted",
            "env_name": "NOTION_TOKEN",
        },

        "quirks": [
            "Use platform_notion_* tools directly (ADR-050)",
            "Page IDs work with or without dashes (UUIDv4 format)",
            "Page must be shared with the integration to access",
            "Comments require commenting permission on the page",
        ],

        "version": "2026-02-12",
    },
}


# =============================================================================
# Registry Access Functions
# =============================================================================

def get_platform_config(provider: str) -> Optional[dict[str, Any]]:
    """Get configuration for a platform."""
    return PLATFORM_REGISTRY.get(provider)


def get_supported_platforms() -> list[str]:
    """Get list of supported platform providers."""
    return list(PLATFORM_REGISTRY.keys())


def get_param_config(provider: str, param_name: str) -> Optional[dict[str, Any]]:
    """Get configuration for a specific parameter."""
    config = PLATFORM_REGISTRY.get(provider)
    if not config:
        return None
    return config.get("params", {}).get(param_name)


# =============================================================================
# Validation Functions
# =============================================================================

def validate_param(provider: str, param_name: str, value: str) -> tuple[bool, Optional[str]]:
    """
    Validate a parameter value against platform rules.

    Returns:
        (is_valid, error_message)
    """
    param_config = get_param_config(provider, param_name)
    if not param_config:
        return (True, None)  # Unknown param, allow it

    # Check invalid patterns first
    invalid_patterns = param_config.get("invalid_patterns", [])
    for pattern in invalid_patterns:
        if re.match(pattern, value):
            error_hint = param_config.get("error_hint", f"Invalid format for {param_name}")
            invalid_examples = param_config.get("invalid_examples", [])
            return (False, f"{error_hint} (invalid: {', '.join(invalid_examples)})")

    # Check valid patterns
    valid_patterns = param_config.get("valid_patterns", [])
    if valid_patterns:
        for pattern in valid_patterns:
            if re.match(pattern, value):
                return (True, None)
        # No valid pattern matched
        valid_examples = param_config.get("valid_examples", [])
        error_hint = param_config.get("error_hint", f"Invalid format for {param_name}")
        return (False, f"{error_hint} (valid: {', '.join(valid_examples)})")

    return (True, None)


def validate_params(provider: str, params: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate all parameters for a platform operation.

    Returns:
        (all_valid, list_of_errors)
    """
    errors = []
    config = get_platform_config(provider)
    if not config:
        return (True, [])  # Unknown platform, allow

    param_configs = config.get("params", {})

    # Check required params
    for param_name, param_config in param_configs.items():
        if param_config.get("optional"):
            continue
        if param_name not in params or not params[param_name]:
            errors.append(f"Missing required parameter: {param_name}")

    # Validate provided params
    for param_name, value in params.items():
        if value and isinstance(value, str):
            is_valid, error = validate_param(provider, param_name, value)
            if not is_valid:
                errors.append(error)

    return (len(errors) == 0, errors)


# =============================================================================
# TP Guidance Generation
# =============================================================================

def get_tp_guidance(provider: str) -> str:
    """
    Generate TP guidance from registry.

    This is used to dynamically build TP system prompt sections
    instead of hardcoding platform-specific documentation.
    """
    config = get_platform_config(provider)
    if not config:
        return ""

    lines = [f"**{config['display_name']} Integration**"]

    # Parameter guidance
    params = config.get("params", {})
    for param_name, param_config in params.items():
        invalid = param_config.get("invalid_examples", [])
        valid = param_config.get("valid_examples", [])

        if invalid:
            lines.append(f"- `{param_name}`: Use {valid}, NOT {invalid}")
        elif valid:
            lines.append(f"- `{param_name}`: e.g., {', '.join(valid)}")

        if param_config.get("resolution_tool"):
            lines.append(f"  - Find valid values: `{param_config['resolution_tool']}`")

    # Quirks
    quirks = config.get("quirks", [])
    if quirks:
        lines.append("")
        lines.append("**Known quirks:**")
        for quirk in quirks[:3]:  # Limit to top 3 for brevity
            lines.append(f"- {quirk}")

    return "\n".join(lines)


def get_all_tp_guidance() -> str:
    """Generate TP guidance for all platforms."""
    sections = []
    for provider in get_supported_platforms():
        guidance = get_tp_guidance(provider)
        if guidance:
            sections.append(guidance)
    return "\n\n".join(sections)


# =============================================================================
# MCP Parameter Mapping
# =============================================================================

def map_params_to_mcp(provider: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Map user-facing parameter names to MCP-expected names.

    Example:
        map_params_to_mcp("slack", {"channel": "#general", "message": "Hi"})
        -> {"channel_id": "#general", "text": "Hi"}
    """
    config = get_platform_config(provider)
    if not config:
        return params

    param_configs = config.get("params", {})
    mapped = {}

    for param_name, value in params.items():
        param_config = param_configs.get(param_name, {})
        mcp_name = param_config.get("mcp_name", param_name)
        mapped[mcp_name] = value

    return mapped
