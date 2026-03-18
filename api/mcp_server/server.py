"""
YARNNN MCP Server — ADR-075

FastMCP server exposing YARNNN backend services as MCP tools.
9 tools: 6 core (ADR-075) + 3 agent identity & knowledge (ADR-116 Phase 4).

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
        "Access YARNNN context, agents, and accumulated platform knowledge. "
        "YARNNN syncs your Slack, Gmail, Notion, and Calendar — this server "
        "lets you query that accumulated context and trigger agents."
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
    """Get YARNNN system status: connected platforms, sync freshness, recent activity, and active agents.

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
async def list_agents(
    ctx: Context,
    status: Optional[str] = None,
) -> dict:
    """List your configured agents with their schedule and status.

    Returns agent titles, types, schedules, destinations, and when they last ran.
    Use this to discover what agents exist before triggering or reading output.

    Args:
        status: Filter by status. Options: "active" (default), "paused", "archived"
    """
    auth = ctx.request_context.lifespan_context["auth"]

    query = (
        auth.client.table("agents")
        .select("id, title, scope, role, status, schedule, destination, sources, last_run_at, next_run_at")
        .eq("user_id", auth.user_id)
    )
    if status:
        query = query.eq("status", status)
    else:
        query = query.eq("status", "active")

    result = query.order("created_at", desc=True).limit(20).execute()

    return {"agents": result.data or [], "count": len(result.data or [])}


@mcp.tool()
async def run_agent(
    ctx: Context,
    agent_id: str,
) -> dict:
    """Trigger an agent to execute now and deliver its output.

    Runs the full pipeline: gather context from synced platforms, generate content,
    and deliver to the configured destination (Slack, email, etc.).
    Use list_agents first to find the agent ID.

    Args:
        agent_id: The UUID of the agent to run
    """
    auth = ctx.request_context.lifespan_context["auth"]

    # Fetch the agent (with ownership check)
    try:
        agent_result = (
            auth.client.table("agents")
            .select("*")
            .eq("id", agent_id)
            .eq("user_id", auth.user_id)
            .single()
            .execute()
        )
    except Exception:
        return {"success": False, "error": "Agent not found"}

    if not agent_result.data:
        return {"success": False, "error": "Agent not found"}

    from services.agent_execution import execute_agent_generation

    result = await execute_agent_generation(
        client=auth.client,
        user_id=auth.user_id,
        agent=agent_result.data,
        trigger_context={"type": "mcp"},
    )

    return result


@mcp.tool()
async def get_agent_output(
    ctx: Context,
    agent_id: str,
    version: Optional[int] = None,
) -> dict:
    """Get the generated content from an agent's most recent (or specific) version.

    Returns the actual text output that was generated and delivered.
    Use list_agents first to find the agent ID.

    Args:
        agent_id: The UUID of the agent
        version: Specific version number to retrieve. If omitted, returns the latest.
    """
    auth = ctx.request_context.lifespan_context["auth"]

    # Verify ownership
    try:
        agent_check = (
            auth.client.table("agents")
            .select("id")
            .eq("id", agent_id)
            .eq("user_id", auth.user_id)
            .single()
            .execute()
        )
    except Exception:
        return {"success": False, "error": "Agent not found"}

    if not agent_check.data:
        return {"success": False, "error": "Agent not found"}

    # Fetch version(s)
    query = (
        auth.client.table("agent_runs")
        .select("id, version_number, status, draft_content, final_content, created_at, delivered_at")
        .eq("agent_id", agent_id)
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
    and past conversations. Includes your profile, known facts, active agents,
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


# =============================================================================
# ADR-116 Phase 4: Agent Identity & Knowledge MCP Tools
# =============================================================================

@mcp.tool()
async def get_agent_card(
    ctx: Context,
    agent_id: str,
) -> dict:
    """Get an agent's identity card — who it is, what it does, how mature it is.

    Returns structured agent identity including description, thesis summary,
    sources, schedule, and maturity signals. Use discover_agents() first to
    find agent IDs.

    Args:
        agent_id: UUID of the agent
    """
    auth = ctx.request_context.lifespan_context["auth"]
    import json
    from services.workspace import AgentWorkspace, get_agent_slug

    # Verify ownership
    result = (
        auth.client.table("agents")
        .select("id, title, role, scope, status, sources, schedule, last_run_at, created_at")
        .eq("user_id", auth.user_id)
        .eq("id", agent_id)
        .limit(1)
        .execute()
    )
    agents = result.data or []
    if not agents:
        return {"success": False, "error": "Agent not found or not accessible"}

    agent = agents[0]
    slug = get_agent_slug(agent)
    ws = AgentWorkspace(auth.client, auth.user_id, slug)

    # Try to read pre-generated card first
    card_content = await ws.read("agent-card.json")
    if card_content:
        try:
            return {"success": True, "agent_card": json.loads(card_content)}
        except json.JSONDecodeError:
            pass

    # Fallback: build card on the fly from workspace
    agent_md = await ws.read("AGENT.md")
    thesis = await ws.read("thesis.md")

    description = None
    if agent_md:
        for p in agent_md.strip().split("\n\n"):
            stripped = p.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                description = stripped[:300]
                break

    return {
        "success": True,
        "agent_card": {
            "agent_id": agent["id"],
            "title": agent["title"],
            "slug": slug,
            "role": agent.get("role"),
            "scope": agent.get("scope"),
            "status": agent.get("status"),
            "description": description,
            "thesis_summary": thesis[:300] if thesis else None,
            "sources": agent.get("sources", []),
            "schedule": agent.get("schedule"),
            "last_run_at": agent.get("last_run_at"),
        },
    }


@mcp.tool()
async def search_knowledge(
    ctx: Context,
    query: Optional[str] = None,
    content_class: Optional[str] = None,
    agent_id: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Search YARNNN's accumulated agent-produced knowledge.

    Searches digests, analyses, briefs, research, and insights produced by
    YARNNN's agent fleet. Filter by producing agent, role type, or content class.

    Args:
        query: Optional text search (topic, person, keyword)
        content_class: Optional filter: digests, analyses, briefs, research, insights
        agent_id: Optional filter by producing agent UUID
        role: Optional filter by role type: digest, prepare, monitor, research, synthesize
        limit: Max results (default 10, max 30)
    """
    auth = ctx.request_context.lifespan_context["auth"]
    from services.workspace import KnowledgeBase

    kb = KnowledgeBase(auth.client, auth.user_id)
    limit = min(limit, 30)

    has_metadata_filters = agent_id or role
    if has_metadata_filters or not query:
        results = await kb.search_by_metadata(
            query=query,
            content_class=content_class,
            agent_id=agent_id,
            role=role,
            limit=limit,
        )
    else:
        results = await kb.search(query, content_class=content_class, limit=limit)

    items = []
    for r in results:
        item = {
            "path": r.path,
            "summary": r.summary,
            "content_preview": r.content[:500] if r.content else None,
            "updated_at": str(r.updated_at) if r.updated_at else None,
        }
        if r.metadata:
            item["produced_by"] = r.metadata.get("agent_id")
            item["role"] = r.metadata.get("role")
            item["scope"] = r.metadata.get("scope")
        items.append(item)

    return {"success": True, "results": items, "count": len(items)}


@mcp.tool()
async def discover_agents(
    ctx: Context,
    role: Optional[str] = None,
    scope: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """Discover available agents by capability.

    Returns agent cards for YARNNN's agent fleet. Use this to understand
    what agents exist, what domains they cover, and what knowledge they produce.

    Args:
        role: Optional filter: digest, prepare, monitor, research, synthesize
        scope: Optional filter: platform, cross_platform, knowledge, research, autonomous
        status: Optional filter: active (default), paused
    """
    auth = ctx.request_context.lifespan_context["auth"]
    from services.workspace import AgentWorkspace, get_agent_slug

    query = (
        auth.client.table("agents")
        .select("id, title, role, scope, status, sources, schedule, last_run_at, created_at")
        .eq("user_id", auth.user_id)
        .eq("status", status or "active")
    )
    if role:
        query = query.eq("role", role)
    if scope:
        query = query.eq("scope", scope)

    result = query.order("created_at", desc=True).limit(20).execute()
    agents = result.data or []

    agent_cards = []
    for agent in agents:
        slug = get_agent_slug(agent)
        thesis_summary = None
        try:
            ws = AgentWorkspace(auth.client, auth.user_id, slug)
            thesis = await ws.read("thesis.md")
            if thesis:
                thesis_summary = thesis[:300]
        except Exception:
            pass

        agent_cards.append({
            "agent_id": agent["id"],
            "title": agent["title"],
            "role": agent.get("role"),
            "scope": agent.get("scope"),
            "sources": agent.get("sources", []),
            "thesis_summary": thesis_summary,
            "last_run_at": agent.get("last_run_at"),
        })

    return {"success": True, "agents": agent_cards, "count": len(agent_cards)}
