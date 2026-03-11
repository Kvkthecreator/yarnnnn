"""
Workspace Primitives — ADR-106 / ADR-107

Headless-only primitives that let reasoning agents interact with their
workspace and the shared knowledge base during generation.

- ReadWorkspace: read from agent's workspace
- WriteWorkspace: write to agent's workspace (thesis, observations, working notes)
- SearchWorkspace: full-text search within agent's workspace
- QueryKnowledge: search /knowledge/ filesystem + platform_content fallback
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions
# =============================================================================

READ_WORKSPACE_TOOL = {
    "name": "ReadWorkspace",
    "description": """Read a file from your workspace.

Your workspace contains your accumulated knowledge:
- AGENT.md — your identity and behavioral instructions (like CLAUDE.md)
- thesis.md — your current understanding of your domain
- memory/observations.md — observations from past review passes
- memory/preferences.md — learned preferences from user edits
- memory/{topic}.md — topic-scoped memory files
- working/{topic}.md — your intermediate research notes
- runs/v{N}.md — your past outputs

Use this to review your prior work before generating new output.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path within your workspace (e.g., 'thesis.md', 'working/competitive-landscape.md')"
            }
        },
        "required": ["path"]
    }
}


WRITE_WORKSPACE_TOOL = {
    "name": "WriteWorkspace",
    "description": """Write a file to your workspace for future reference.

Use this to persist insights that should survive across runs:
- Update thesis.md with refined domain understanding
- Save working/{topic}.md with research notes
- Append observations to memory/observations.md
- Save topic-scoped memory to memory/{topic}.md

Your workspace persists between runs. What you write now, you can read in future executions.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path (e.g., 'thesis.md', 'working/launch-readiness.md')"
            },
            "content": {
                "type": "string",
                "description": "Content to write"
            },
            "mode": {
                "type": "string",
                "enum": ["overwrite", "append"],
                "description": "Write mode: 'overwrite' replaces the file, 'append' adds to end. Default: overwrite"
            }
        },
        "required": ["path", "content"]
    }
}


SEARCH_WORKSPACE_TOOL = {
    "name": "SearchWorkspace",
    "description": """Search your workspace for relevant content.

Searches across all your files: thesis, memory, working notes, past runs.
Use this to find specific information from your accumulated knowledge.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "path_prefix": {
                "type": "string",
                "description": "Optional: limit search to a subdirectory (e.g., 'working/' or 'runs/')"
            }
        },
        "required": ["query"]
    }
}


QUERY_KNOWLEDGE_TOOL = {
    "name": "QueryKnowledge",
    "description": """Search the shared knowledge base.

The knowledge base contains:
- Agent-produced knowledge artifacts (digests, analyses, briefs, research, insights)
- Synced content from connected platforms (Slack, Gmail, Notion, Calendar) via fallback

Use this to find evidence relevant to your domain. Search by topic, person, keyword.
Much more targeted than receiving a full platform dump — query for what you need.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (topic, person, keyword)"
            },
            "content_class": {
                "type": "string",
                "enum": ["digests", "analyses", "briefs", "research", "insights"],
                "description": "Optional: limit to a specific knowledge category"
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10, max 30)",
                "default": 10
            }
        },
        "required": ["query"]
    }
}


LIST_WORKSPACE_TOOL = {
    "name": "ListWorkspace",
    "description": """List files in your workspace.

See what's in your workspace: thesis, memory, working notes, past runs.
Call with no arguments to see top-level files, or pass a path to list a subdirectory.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Optional: subdirectory to list (e.g., 'working/', 'runs/'). Default: list top-level."
            }
        },
        "required": []
    }
}


# =============================================================================
# Handlers
# =============================================================================

async def handle_read_workspace(auth: Any, input: dict) -> dict:
    """Handle ReadWorkspace primitive."""
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context", "message": "ReadWorkspace requires agent context"}

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    path = input.get("path", "")

    content = await ws.read(path)
    if content is None:
        return {
            "success": True,
            "found": False,
            "message": f"File not found: {path}. Use ListWorkspace to see available files.",
        }

    return {
        "success": True,
        "found": True,
        "path": path,
        "content": content,
    }


async def handle_write_workspace(auth: Any, input: dict) -> dict:
    """Handle WriteWorkspace primitive."""
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context", "message": "WriteWorkspace requires agent context"}

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    path = input.get("path", "")
    content = input.get("content", "")
    mode = input.get("mode", "overwrite")

    if mode == "append":
        success = await ws.append(path, content)
    else:
        success = await ws.write(path, content)

    if success:
        return {"success": True, "path": path, "mode": mode}
    return {"success": False, "error": "write_failed", "message": f"Failed to write: {path}"}


async def handle_search_workspace(auth: Any, input: dict) -> dict:
    """Handle SearchWorkspace primitive."""
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context", "message": "SearchWorkspace requires agent context"}

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    query = input.get("query", "")
    path_prefix = input.get("path_prefix")

    results = await ws.search(query, path_prefix=path_prefix)

    return {
        "success": True,
        "query": query,
        "count": len(results),
        "results": [
            {"path": r.path, "summary": r.summary, "content_preview": r.content}
            for r in results
        ],
    }


async def handle_query_knowledge(auth: Any, input: dict) -> dict:
    """Handle QueryKnowledge primitive — searches /knowledge/ and falls back to platform_content."""
    from services.workspace import KnowledgeBase

    kb = KnowledgeBase(auth.client, auth.user_id)
    query = input.get("query", "")
    content_class = input.get("content_class")
    limit = min(input.get("limit", 10), 30)

    results = await kb.search(query, content_class=content_class, limit=limit)

    if not results:
        # Fall back to searching platform_content for external data
        return await _fallback_platform_content_search(auth, query, None, limit)

    return {
        "success": True,
        "query": query,
        "content_class": content_class,
        "count": len(results),
        "results": [
            {"path": r.path, "summary": r.summary, "content_preview": r.content}
            for r in results
        ],
    }


async def handle_list_workspace(auth: Any, input: dict) -> dict:
    """Handle ListWorkspace primitive."""
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context", "message": "ListWorkspace requires agent context"}

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    path = input.get("path", "")

    files = await ws.list(path)

    return {
        "success": True,
        "path": path or "/",
        "files": files,
        "count": len(files),
    }


async def _fallback_platform_content_search(auth: Any, query: str, platform: str = None, limit: int = 10) -> dict:
    """
    Fallback: search platform_content for external platform data when
    /knowledge/ has no results. Only searches external platforms (not yarnnn).
    """
    try:
        q = (
            auth.client.table("platform_content")
            .select("id, platform, resource_name, content, author, source_timestamp")
            .eq("user_id", auth.user_id)
            .neq("platform", "yarnnn")  # Exclude legacy yarnnn rows if any remain
            .textSearch("content", query, {"type": "websearch"})
            .limit(limit)
        )
        if platform:
            q = q.eq("platform", platform)

        result = q.order("source_timestamp", desc=True).execute()

        items = result.data or []
        return {
            "success": True,
            "query": query,
            "count": len(items),
            "source": "platform_content",
            "results": [
                {
                    "path": f"platform_content/{i['platform']}/{i.get('resource_name', 'unknown')}",
                    "summary": f"{i['platform']}:{i.get('resource_name', '')} by {i.get('author', 'unknown')}",
                    "content_preview": i["content"][:500],
                }
                for i in items
            ],
        }
    except Exception as e:
        logger.warning(f"[KNOWLEDGE] Fallback search failed: {e}")
        return {
            "success": True,
            "query": query,
            "count": 0,
            "results": [],
            "message": "No knowledge base content found. Connected platforms may not have synced yet.",
        }
