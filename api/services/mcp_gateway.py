"""
MCP Gateway Client

ADR-050: Client for calling the MCP Gateway service.
Routes platform tool calls from TP to the Node.js gateway.
"""

import os
import logging
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Gateway URL - defaults to local dev, override in production
MCP_GATEWAY_URL = os.environ.get("MCP_GATEWAY_URL", "http://localhost:3000")


async def call_platform_tool(
    provider: str,
    tool: str,
    args: dict[str, Any],
    token: str,
    metadata: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """
    Call a platform tool via the MCP Gateway.

    Args:
        provider: Platform provider (slack, notion)
        tool: Tool name (e.g., slack_post_message)
        args: Tool arguments
        token: Platform access token
        metadata: Additional auth metadata (e.g., team_id for Slack)

    Returns:
        Tool result dict with success flag
    """
    url = f"{MCP_GATEWAY_URL}/api/mcp/tools/{provider}/{tool}"

    payload = {
        "args": args,
        "auth": {
            "token": token,
            "metadata": metadata or {},
        },
    }

    logger.info(f"[MCP-GATEWAY] Calling {provider}/{tool}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()

            if response.status_code != 200:
                logger.error(f"[MCP-GATEWAY] Error: {data.get('error')}")
                return {
                    "success": False,
                    "error": data.get("error", "Gateway error"),
                    "provider": provider,
                    "tool": tool,
                }

            logger.info(f"[MCP-GATEWAY] Success: {provider}/{tool}")
            return {
                "success": True,
                "result": data.get("result"),
                "provider": provider,
                "tool": tool,
            }

    except httpx.TimeoutException:
        logger.error(f"[MCP-GATEWAY] Timeout calling {provider}/{tool}")
        return {
            "success": False,
            "error": "Gateway timeout",
            "provider": provider,
            "tool": tool,
        }
    except Exception as e:
        logger.error(f"[MCP-GATEWAY] Exception: {e}")
        return {
            "success": False,
            "error": str(e),
            "provider": provider,
            "tool": tool,
        }


async def list_provider_tools(provider: str) -> list[dict[str, str]]:
    """
    List available tools for a provider.

    Returns:
        List of tool definitions
    """
    url = f"{MCP_GATEWAY_URL}/api/mcp/tools/{provider}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            data = response.json()

            if data.get("success"):
                return data.get("tools", [])
            return []

    except Exception as e:
        logger.error(f"[MCP-GATEWAY] Failed to list tools for {provider}: {e}")
        return []


def is_gateway_available() -> bool:
    """
    Check if MCP Gateway is configured.

    Returns True if MCP_GATEWAY_URL is set (either production or localhost).
    For local dev, start the gateway with `npm run dev` in mcp-gateway/.
    """
    return bool(MCP_GATEWAY_URL)
