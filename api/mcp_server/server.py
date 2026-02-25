"""
YARNNN MCP Server — ADR-075

FastMCP server exposing YARNNN backend services as MCP tools.
Phase 0: Single tool (get_status) for end-to-end validation.

Two-layer auth:
- Transport: OAuth 2.1 (Claude.ai, ChatGPT) + static bearer token (Claude Desktop)
- Data: Service key + MCP_USER_ID (all queries scoped by user_id)
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from pydantic import AnyHttpUrl
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.transport_security import TransportSecuritySettings

from mcp_server.auth import get_authenticated_client
from mcp_server.oauth_provider import YarnnnOAuthProvider

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize auth context at server startup."""
    logger.info("[MCP Server] Initializing...")
    auth = get_authenticated_client()
    logger.info(f"[MCP Server] Ready — user: {auth.user_id}")
    yield {"auth": auth}
    logger.info("[MCP Server] Shutting down")


# Determine server URL for OAuth issuer
_server_url = os.environ.get(
    "MCP_SERVER_URL", "https://yarnnn-mcp-server.onrender.com"
)

mcp = FastMCP(
    "yarnnn",
    instructions=(
        "Access YARNNN context, deliverables, and accumulated platform knowledge. "
        "YARNNN syncs your Slack, Gmail, Notion, and Calendar — this server "
        "lets you query that accumulated context and trigger deliverables."
    ),
    lifespan=lifespan,
    # OAuth 2.1 provider — enables Claude.ai connectors + ChatGPT developer mode
    auth_server_provider=YarnnnOAuthProvider(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(_server_url),
        resource_server_url=AnyHttpUrl(_server_url),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["read"],
            default_scopes=["read"],
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=["read"],
    ),
    # Disable DNS rebinding protection — Render/Cloudflare reverse proxy
    # changes the Host header. Security handled by OAuth + Render's edge.
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


# --- Tools ---


@mcp.tool()
async def get_status(
    ctx: Context,
    scope: Optional[str] = None,
    platform: Optional[str] = None,
) -> dict:
    """Get YARNNN system status: connected platforms, sync freshness, recent activity, and active deliverables.

    Use this to check what platforms are connected, when they last synced,
    whether the scheduler is running, and if there are any issues.

    Args:
        scope: What to check. Options: "full" (default), "signals", "sync", "scheduler", "jobs"
        platform: Optional filter to a specific platform (slack, gmail, notion, calendar)
    """
    auth = ctx.request_context.lifespan_context["auth"]

    from services.primitives.system_state import handle_get_system_state

    result = await handle_get_system_state(auth, {
        "scope": scope or "full",
        "platform": platform,
    })

    return result
