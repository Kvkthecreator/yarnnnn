"""
YARNNN MCP Server — ADR-075

FastMCP server exposing YARNNN backend services as MCP tools.
Phase 1: Full tool surface (6 tools).

Two-layer auth:
- Transport: OAuth 2.1 (Claude.ai, ChatGPT) + static bearer token (Claude Desktop)
- Data: Service key + MCP_USER_ID (all queries scoped by user_id)

Tool handlers call service functions directly (same layer REST routes use).
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


@mcp.tool()
async def list_deliverables(
    ctx: Context,
    status: Optional[str] = None,
) -> dict:
    """List your configured deliverables with their schedule and status.

    Returns deliverable titles, types, schedules, destinations, and when they last ran.
    Use this to discover what deliverables exist before triggering or reading output.

    Args:
        status: Filter by status. Options: "active" (default), "paused", "archived"
    """
    auth = ctx.request_context.lifespan_context["auth"]

    query = (
        auth.client.table("deliverables")
        .select("id, title, deliverable_type, status, schedule, destination, sources, last_run_at, next_run_at")
        .eq("user_id", auth.user_id)
    )
    if status:
        query = query.eq("status", status)
    else:
        query = query.eq("status", "active")

    result = query.order("created_at", desc=True).limit(20).execute()

    return {"deliverables": result.data or [], "count": len(result.data or [])}


@mcp.tool()
async def run_deliverable(
    ctx: Context,
    deliverable_id: str,
) -> dict:
    """Trigger a deliverable to execute now and deliver its output.

    Runs the full pipeline: gather context from synced platforms, generate content,
    and deliver to the configured destination (Slack, email, etc.).
    Use list_deliverables first to find the deliverable ID.

    Args:
        deliverable_id: The UUID of the deliverable to run
    """
    auth = ctx.request_context.lifespan_context["auth"]

    # Fetch the deliverable (with ownership check)
    try:
        del_result = (
            auth.client.table("deliverables")
            .select("*")
            .eq("id", deliverable_id)
            .eq("user_id", auth.user_id)
            .single()
            .execute()
        )
    except Exception:
        return {"success": False, "error": "Deliverable not found"}

    if not del_result.data:
        return {"success": False, "error": "Deliverable not found"}

    from services.deliverable_execution import execute_deliverable_generation

    result = await execute_deliverable_generation(
        client=auth.client,
        user_id=auth.user_id,
        deliverable=del_result.data,
        trigger_context={"type": "mcp"},
    )

    return result


@mcp.tool()
async def get_deliverable_output(
    ctx: Context,
    deliverable_id: str,
    version: Optional[int] = None,
) -> dict:
    """Get the generated content from a deliverable's most recent (or specific) version.

    Returns the actual text output that was generated and delivered.
    Use list_deliverables first to find the deliverable ID.

    Args:
        deliverable_id: The UUID of the deliverable
        version: Specific version number to retrieve. If omitted, returns the latest.
    """
    auth = ctx.request_context.lifespan_context["auth"]

    # Verify ownership
    try:
        del_check = (
            auth.client.table("deliverables")
            .select("id")
            .eq("id", deliverable_id)
            .eq("user_id", auth.user_id)
            .single()
            .execute()
        )
    except Exception:
        return {"success": False, "error": "Deliverable not found"}

    if not del_check.data:
        return {"success": False, "error": "Deliverable not found"}

    # Fetch version(s)
    query = (
        auth.client.table("deliverable_versions")
        .select("id, version_number, status, draft_content, final_content, created_at, delivered_at")
        .eq("deliverable_id", deliverable_id)
    )
    if version:
        query = query.eq("version_number", version)
    else:
        query = query.order("version_number", desc=True).limit(1)

    result = query.execute()

    if not result.data:
        return {"success": False, "error": "No versions found"}

    v = result.data[0]
    return {
        "success": True,
        "version_number": v.get("version_number"),
        "status": v.get("status"),
        "content": v.get("final_content") or v.get("draft_content"),
        "delivered_at": v.get("delivered_at"),
    }


@mcp.tool()
async def get_context(ctx: Context) -> dict:
    """Get YARNNN's accumulated knowledge about you: profile, preferences, memories, and platform status.

    Returns your working memory — what YARNNN has learned from synced platforms
    and past conversations. Includes your profile, known facts, active deliverables,
    and connected platform status.
    """
    auth = ctx.request_context.lifespan_context["auth"]

    from services.working_memory import build_working_memory

    memory = await build_working_memory(auth.user_id, auth.client)

    return {"success": True, "context": memory}


@mcp.tool()
async def search_content(
    ctx: Context,
    query: str,
    platform: Optional[str] = None,
) -> dict:
    """Search YARNNN's synced platform content (Slack messages, emails, Notion pages, calendar events).

    Searches across all synced and accumulated content using text matching.
    Results are from cached/synced data, not live platform queries.

    Args:
        query: What to search for (e.g., "project Acme decisions", "budget discussion")
        platform: Optional filter to a specific platform (slack, gmail, notion, calendar)
    """
    auth = ctx.request_context.lifespan_context["auth"]

    from services.platform_content import search_platform_content

    platforms = [platform] if platform else None

    results = await search_platform_content(
        db_client=auth.client,
        user_id=auth.user_id,
        query_text=query,
        platforms=platforms,
        limit=20,
    )

    items = []
    for item, score in results:
        items.append({
            "platform": item.platform,
            "resource_name": item.resource_name,
            "content": item.content[:500] if item.content else None,
            "title": item.title,
            "author": item.author,
            "timestamp": item.source_timestamp.isoformat() if item.source_timestamp else None,
            "score": score,
        })

    return {"success": True, "results": items, "count": len(items)}
