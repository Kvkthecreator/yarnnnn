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
    """List your configured agents and their status.

    Returns agent titles, roles, scopes, and status.
    Use this to discover what agents exist before triggering or reading output.

    Args:
        status: Filter by status. Options: "active" (default), "paused", "archived"
    """
    auth = ctx.request_context.lifespan_context["auth"]

    query = (
        auth.client.table("agents")
        .select("id, title, scope, role, status")
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

    from services.task_pipeline import execute_agent_run
    from services.supabase import get_service_client

    result = await execute_agent_run(
        client=get_service_client(),
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
    """Search YARNNN's workspace content (synced platform data, agent outputs, documents).

    Searches across all workspace files using full-text search.
    Results include synced platform content, agent outputs, and shared documents.

    Args:
        query: What to search for (e.g., "project Acme decisions", "budget discussion")
        platform: Optional filter to a specific platform path prefix (slack, notion, github)
    """
    auth = ctx.request_context.lifespan_context["auth"]

    path_prefix = f"/platforms/{platform}" if platform else None

    result = auth.client.rpc("search_workspace", {
        "p_user_id": auth.user_id,
        "p_query": query,
        "p_path_prefix": path_prefix,
        "p_limit": 20,
    }).execute()

    items = []
    for r in (result.data or []):
        items.append({
            "path": r["path"],
            "content": r["content"][:500] if r.get("content") else None,
            "summary": r.get("summary"),
            "updated_at": r.get("updated_at"),
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
    and maturity signals. Use discover_agents() first to find agent IDs.

    Args:
        agent_id: UUID of the agent
    """
    auth = ctx.request_context.lifespan_context["auth"]
    import json
    from services.workspace import AgentWorkspace, get_agent_slug

    # Verify ownership
    result = (
        auth.client.table("agents")
        .select("id, title, role, scope, status, created_at")
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
        },
    }


@mcp.tool()
async def search_knowledge(
    ctx: Context,
    query: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Search YARNNN's accumulated workspace context (ADR-151).

    Searches shared context domains: competitors, market, relationships,
    projects, content, signals. Optionally filter by domain.

    Args:
        query: Optional text search (topic, entity, keyword)
        domain: Optional filter: competitors, market, relationships, projects, content, signals
        limit: Max results (default 10, max 30)
    """
    auth = ctx.request_context.lifespan_context["auth"]
    limit = min(limit, 30)

    prefix = "/workspace/context/"
    if domain:
        from services.directory_registry import get_domain_folder
        domain_folder = get_domain_folder(domain)
        if domain_folder:
            prefix = f"/workspace/{domain_folder}/"

    try:
        if query:
            result = (
                auth.client.rpc("search_workspace", {
                    "p_user_id": auth.user_id,
                    "p_query": query,
                    "p_path_prefix": prefix,
                    "p_limit": limit,
                }).execute()
            )
            rows = result.data or []
        else:
            result = (
                auth.client.table("workspace_files")
                .select("path, content, summary, updated_at")
                .eq("user_id", auth.user_id)
                .like("path", f"{prefix}%")
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            rows = result.data or []

        items = []
        for r in rows:
            items.append({
                "path": r.get("path", ""),
                "summary": r.get("summary", ""),
                "content_preview": (r.get("content") or "")[:500],
                "updated_at": r.get("updated_at"),
            })

        return {"success": True, "results": items, "count": len(items), "domain": domain}

    except Exception as e:
        return {"success": False, "error": str(e), "results": [], "count": 0}


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
        role: Optional filter: briefer, monitor, researcher, drafter, analyst, writer, planner, scout
        scope: Optional filter: platform, cross_platform, knowledge, research, autonomous
        status: Optional filter: active (default), paused
    """
    auth = ctx.request_context.lifespan_context["auth"]
    from services.workspace import AgentWorkspace, get_agent_slug

    query = (
        auth.client.table("agents")
        .select("id, title, role, scope, status, created_at")
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
            "thesis_summary": thesis_summary,
        })

    return {"success": True, "agents": agent_cards, "count": len(agent_cards)}
