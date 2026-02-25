"""
YARNNN MCP Server — ADR-075

FastMCP server exposing YARNNN backend services as MCP tools.
Phase 0: Single tool (get_status) for end-to-end validation.

The server initializes auth once at startup (lifespan) and registers
tools that wrap existing service functions. No new query logic —
handlers are thin adapters to proven backend code.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context

from mcp_server.auth import get_authenticated_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize auth context at server startup."""
    logger.info("[MCP Server] Initializing...")
    auth = get_authenticated_client()
    logger.info(f"[MCP Server] Ready — user: {auth.user_id}")
    yield {"auth": auth}
    logger.info("[MCP Server] Shutting down")


mcp = FastMCP(
    "yarnnn",
    instructions=(
        "Access YARNNN context, deliverables, and accumulated platform knowledge. "
        "YARNNN syncs your Slack, Gmail, Notion, and Calendar — this server "
        "lets you query that accumulated context and trigger deliverables."
    ),
    lifespan=lifespan,
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
