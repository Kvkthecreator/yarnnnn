"""
Workspace & Inter-Agent Primitives — ADR-106 / ADR-107 / ADR-116

Headless-only primitives that let reasoning agents interact with their
workspace, the shared knowledge base, and other agents.

- ReadWorkspace: read from agent's workspace
- WriteWorkspace: write to agent's workspace (thesis, observations, working notes)
- SearchWorkspace: full-text search within agent's workspace
- QueryKnowledge: search /knowledge/ filesystem with metadata filters + platform_content fallback
- DiscoverAgents: find other agents by role/scope/status (ADR-116 Phase 2)
"""

import json
import logging
from datetime import datetime, timezone
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
- working/{topic}.md — your intermediate research notes (ephemeral)
- outputs/{date}/output.md — your past outputs (one folder per run)
- outputs/{date}/manifest.json — metadata about each run

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
- Save working/{topic}.md with research notes (ephemeral — auto-cleaned after 24h)
- Append observations to memory/observations.md
- Save topic-scoped memory to memory/{topic}.md

Files in working/ are ephemeral scratch — they're auto-cleaned after 24h.
Everything else persists between runs. What you write now, you can read in future executions.""",
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

Searches across all your files: thesis, memory, outputs.
Ephemeral scratch files (working/) are excluded from search by default.
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
Much more targeted than receiving a full platform dump — query for what you need.

You can filter by the agent that produced the knowledge, by role type, or by content class.
Use DiscoverAgents first to find agent IDs if you want to query a specific agent's outputs.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (topic, person, keyword). Optional if filtering by agent_id or role."
            },
            "content_class": {
                "type": "string",
                "enum": ["digests", "analyses", "briefs", "research", "insights"],
                "description": "Optional: limit to a specific knowledge category"
            },
            "agent_id": {
                "type": "string",
                "description": "Optional: filter to knowledge produced by a specific agent (UUID)"
            },
            "role": {
                "type": "string",
                "enum": ["digest", "prepare", "monitor", "research", "synthesize"],
                "description": "Optional: filter by the role type that produced the knowledge"
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10, max 30)",
                "default": 10
            }
        },
        "required": []
    }
}


LIST_WORKSPACE_TOOL = {
    "name": "ListWorkspace",
    "description": """List files in your workspace.

See what's in your workspace: thesis, memory, working notes, outputs.
Call with no arguments to see top-level files, or pass a path to list a subdirectory.
Ephemeral (working/) and archived files are hidden by default.""",
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


async def _log_cross_agent_reference(auth: Any, referenced_agent_ids: list[str]):
    """ADR-116 Phase 5: Log cross-agent references for consumption tracking.

    When an agent reads knowledge or context from another agent, record the
    reference so Composer can build an agent dependency graph.
    Writes to the consuming agent's memory/references.json.
    Non-fatal — never blocks the calling primitive.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    calling_agent = getattr(auth, "agent", None)
    if not calling_agent or not referenced_agent_ids:
        return

    try:
        slug = get_agent_slug(calling_agent)
        ws = AgentWorkspace(auth.client, auth.user_id, slug)
        now = datetime.now(timezone.utc).isoformat()

        # Read existing references
        existing = await ws.read("memory/references.json")
        refs = {}
        if existing:
            try:
                refs = json.loads(existing)
            except json.JSONDecodeError:
                refs = {}

        # Update references (keyed by agent_id, latest timestamp wins)
        for aid in referenced_agent_ids:
            refs[aid] = {"last_read": now}

        await ws.write(
            "memory/references.json",
            json.dumps(refs, indent=2),
            summary="Cross-agent references (auto-tracked)",
        )
    except Exception as e:
        logger.debug(f"[WORKSPACE] Reference logging failed (non-fatal): {e}")


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
    """Handle QueryKnowledge primitive — searches /knowledge/ with optional metadata filters.

    ADR-116 Phase 1: When agent_id or role filters are provided, uses metadata-aware
    search (search_knowledge_by_metadata RPC). Otherwise falls back to existing
    full-text search. Always falls back to platform_content if /knowledge/ is empty.
    """
    from services.workspace import KnowledgeBase

    kb = KnowledgeBase(auth.client, auth.user_id)
    query = input.get("query") or None
    content_class = input.get("content_class")
    agent_id = input.get("agent_id")
    role = input.get("role")
    limit = min(input.get("limit", 10), 30)

    # ADR-116: Use metadata search when filters are provided
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

    if not results and query:
        # Fall back to searching platform_content for external data
        return await _fallback_platform_content_search(auth, query, None, limit)

    result_items = []
    for r in results:
        item = {"path": r.path, "summary": r.summary, "content_preview": r.content}
        # ADR-116: Include provenance metadata when available
        if r.metadata:
            item["produced_by"] = r.metadata.get("agent_id")
            item["role"] = r.metadata.get("role")
            item["scope"] = r.metadata.get("scope")
            item["version"] = r.metadata.get("version_number")
        result_items.append(item)

    # ADR-116 Phase 5: Log cross-agent references
    referenced_ids = set()
    for item in result_items:
        produced_by = item.get("produced_by")
        if produced_by:
            referenced_ids.add(produced_by)
    if referenced_ids:
        await _log_cross_agent_reference(auth, list(referenced_ids))

    return {
        "success": True,
        "query": query,
        "content_class": content_class,
        "agent_id": agent_id,
        "role": role,
        "count": len(result_items),
        "results": result_items,
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

        # ADR-073: Mark accessed content as retained
        content_ids = [i["id"] for i in items if i.get("id")]
        if content_ids:
            try:
                from services.platform_content import mark_content_retained
                await mark_content_retained(auth.client, content_ids, reason="tp_session")
            except Exception:
                pass  # Non-fatal

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


# =============================================================================
# ADR-116 Phase 2: DiscoverAgents
# =============================================================================

DISCOVER_AGENTS_TOOL = {
    "name": "DiscoverAgents",
    "description": """Discover other agents in this workspace.

Returns a list of agents with their identity, capabilities, and maturity.
Use this to understand what other agents exist and what knowledge they produce
before querying their outputs with QueryKnowledge.

Each result includes:
- Agent ID (use with QueryKnowledge's agent_id filter)
- Title, role, scope
- Thesis summary (what the agent understands about its domain)
- Sources it monitors
- Maturity signals (run count, approval rate)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": ["digest", "prepare", "monitor", "research", "synthesize"],
                "description": "Optional: filter by role type"
            },
            "scope": {
                "type": "string",
                "enum": ["platform", "cross_platform", "knowledge", "research", "autonomous"],
                "description": "Optional: filter by scope"
            },
            "status": {
                "type": "string",
                "enum": ["active", "paused"],
                "description": "Optional: filter by status. Default: active"
            }
        },
        "required": []
    }
}


async def handle_discover_agents(auth: Any, input: dict) -> dict:
    """Handle DiscoverAgents primitive — ADR-116 Phase 2.

    Returns agent cards with thesis summaries for inter-agent discovery.
    Excludes the calling agent itself from results.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    role_filter = input.get("role")
    scope_filter = input.get("scope")
    status_filter = input.get("status", "active")

    # Query agents table
    query = (
        auth.client.table("agents")
        .select("id, title, role, scope, status, created_at")
        .eq("user_id", auth.user_id)
        .eq("status", status_filter)
    )
    if role_filter:
        query = query.eq("role", role_filter)
    if scope_filter:
        query = query.eq("scope", scope_filter)

    result = query.order("created_at", desc=True).limit(20).execute()
    agents = result.data or []

    # Exclude the calling agent itself
    calling_agent = getattr(auth, "agent", None)
    calling_agent_id = calling_agent.get("id") if calling_agent else None
    if calling_agent_id:
        agents = [a for a in agents if a["id"] != calling_agent_id]

    # Load thesis summary for each agent (truncated for token budget)
    agent_cards = []
    for agent in agents:
        slug = get_agent_slug(agent)
        thesis_summary = None
        try:
            ws = AgentWorkspace(auth.client, auth.user_id, slug)
            thesis = await ws.read("thesis.md")
            if thesis:
                thesis_summary = thesis[:300]  # Truncate for token budget
        except Exception:
            pass

        # Compute basic maturity signals from available data
        run_count = 0
        try:
            run_result = (
                auth.client.table("agent_runs")
                .select("id", count="exact")
                .eq("agent_id", agent["id"])
                .execute()
            )
            run_count = run_result.count or 0
        except Exception:
            pass

        agent_cards.append({
            "agent_id": agent["id"],
            "title": agent["title"],
            "role": agent.get("role"),
            "scope": agent.get("scope"),
            "thesis_summary": thesis_summary,
            "maturity": {
                "runs": run_count,
            },
        })

    return {
        "success": True,
        "count": len(agent_cards),
        "agents": agent_cards,
    }


# =============================================================================
# ADR-116 Phase 3: ReadAgentContext
# =============================================================================

READ_AGENT_CONTEXT_TOOL = {
    "name": "ReadAgentContext",
    "description": """Read another agent's identity and domain understanding.

Use after DiscoverAgents to deeply understand a specific agent's perspective
before synthesizing or building on its work.

Available file sets:
- 'identity' (default): AGENT.md (behavioral instructions) + thesis.md (domain understanding)
- 'memory': memory/*.md files (observations, preferences, topic-scoped memory)
- 'all': identity + memory

Read-only. You cannot modify another agent's workspace.
Working notes (working/) and past runs (runs/) are excluded — those are process artifacts, not identity.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "UUID of the target agent (from DiscoverAgents results)"
            },
            "files": {
                "type": "string",
                "enum": ["identity", "memory", "all"],
                "description": "Which files to read. Default: 'identity' (AGENT.md + thesis.md)"
            }
        },
        "required": ["agent_id"]
    }
}


async def handle_read_agent_context(auth: Any, input: dict) -> dict:
    """Handle ReadAgentContext primitive — ADR-116 Phase 3.

    Read-only cross-agent workspace access for identity files.
    Restricted to synthesize, research roles (enforced by PRIMITIVE_MODES).
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    target_agent_id = input.get("agent_id", "")
    files_mode = input.get("files", "identity")

    # Look up the target agent (must belong to same user)
    try:
        result = (
            auth.client.table("agents")
            .select("id, title, role, scope, status")
            .eq("user_id", auth.user_id)
            .eq("id", target_agent_id)
            .limit(1)
            .execute()
        )
        agents = result.data or []
    except Exception as e:
        return {"success": False, "error": "query_failed", "message": str(e)}

    if not agents:
        return {
            "success": False,
            "error": "agent_not_found",
            "message": f"Agent {target_agent_id} not found or not owned by this user.",
        }

    target_agent = agents[0]
    slug = get_agent_slug(target_agent)
    ws = AgentWorkspace(auth.client, auth.user_id, slug)

    response = {
        "success": True,
        "agent_id": target_agent_id,
        "agent_title": target_agent.get("title"),
        "role": target_agent.get("role"),
        "scope": target_agent.get("scope"),
    }

    # Read identity files (AGENT.md + thesis.md)
    if files_mode in ("identity", "all"):
        agent_md = await ws.read("AGENT.md")
        thesis = await ws.read("thesis.md")
        response["agent_md"] = agent_md
        response["thesis"] = thesis

    # Read memory files
    if files_mode in ("memory", "all"):
        memory_files = {}
        try:
            files = await ws.list("memory/")
            for f in files:
                # f is a path string like "memory/observations.md"
                content = await ws.read(f)
                if content:
                    memory_files[f] = content[:1000]  # Truncate for token budget
        except Exception:
            pass
        response["memory_files"] = memory_files

    # ADR-116 Phase 5: Log cross-agent reference
    await _log_cross_agent_reference(auth, [target_agent_id])

    return response


# =============================================================================
# WriteAgentFeedback — ADR-143: TP writes feedback to an agent
# =============================================================================

WRITE_AGENT_FEEDBACK_TOOL = {
    "name": "WriteAgentFeedback",
    "description": """Write feedback to an agent about their work quality.

Use this when the user comments on an agent's output — positive or negative.
The feedback is persisted to the agent's memory and read on every future run.

Examples of when to use:
- User says "the research report was too long" → write to the research agent
- User says "great charts in the last update" → write positive feedback
- User says "stop including competitor pricing" → write specific guidance

Keep feedback concise (1-3 sentences). The agent reads this directly.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_slug": {
                "type": "string",
                "description": "The agent's slug (lowercase, hyphenated title). Use the agent's title to derive it."
            },
            "feedback": {
                "type": "string",
                "description": "The feedback to write. Be specific and actionable. 1-3 sentences."
            }
        },
        "required": ["agent_slug", "feedback"]
    }
}

async def handle_write_agent_feedback(auth: Any, input: dict) -> dict:
    """
    Write conversational feedback to an agent's memory/feedback.md.

    ADR-143: TP is the only entity that sees both agent output and user reaction.
    When the user gives feedback about an agent's work in conversation, TP calls
    this primitive to persist it.

    Input:
        agent_slug: str — the target agent's slug (from agent title)
        feedback: str — the feedback to write (human-readable, 1-3 sentences)

    Returns:
        {status: "ok", message: "Feedback written to {agent_slug}"}
    """
    client = auth["client"]
    user_id = auth["user_id"]
    agent_slug = input.get("agent_slug", "")
    feedback_text = input.get("feedback", "")

    if not agent_slug or not feedback_text:
        return {"error": "agent_slug and feedback are required"}

    # Look up the agent by slug (title-derived)
    try:
        result = client.table("agents").select("id, title, role").eq("user_id", user_id).execute()
        agents = result.data or []

        # Match by slug
        from services.workspace import get_agent_slug
        target = None
        for a in agents:
            if get_agent_slug(a) == agent_slug:
                target = a
                break

        if not target:
            return {"error": f"Agent '{agent_slug}' not found"}

        from services.feedback_distillation import write_feedback_entry
        success = await write_feedback_entry(
            client, user_id, target, feedback_text, source="conversation"
        )

        if success:
            return {"status": "ok", "message": f"Feedback written to {target.get('title', agent_slug)}"}
        else:
            return {"error": "Failed to write feedback"}

    except Exception as e:
        logger.warning(f"[WRITE_AGENT_FEEDBACK] Failed: {e}")
        return {"error": str(e)}


# =============================================================================
# WriteTaskFeedback — Task-specific feedback (focus, criteria, output spec)
# =============================================================================

WRITE_TASK_FEEDBACK_TOOL = {
    "name": "WriteTaskFeedback",
    "description": """Write task-specific feedback that only affects this task's future runs.

Use this when the user comments on what the task should produce differently:
- "Focus on pricing this week" → updates task criteria
- "Add a recommendations section" → updates output spec
- "The competitor section was thin" → records in run log for next run
- "Change delivery to Monday" → updates task config

This is different from WriteAgentFeedback:
- WriteAgentFeedback = changes the agent (style, tone, preferences — applies to ALL tasks)
- WriteTaskFeedback = changes the task definition (focus, criteria — applies to THIS task only)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task's slug (from the URL or task title)"
            },
            "feedback": {
                "type": "string",
                "description": "The feedback to apply. Be specific."
            },
            "target": {
                "type": "string",
                "enum": ["criteria", "objective", "output_spec", "run_log"],
                "description": "Where to apply the feedback: 'criteria' (success criteria), 'objective' (what to produce), 'output_spec' (format/structure), 'run_log' (observation for next run)"
            }
        },
        "required": ["task_slug", "feedback", "target"]
    }
}


async def handle_write_task_feedback(auth: Any, input: dict) -> dict:
    """
    Write task-specific feedback to TASK.md or memory/run_log.md.

    Routes feedback to the appropriate location based on target:
    - criteria/objective/output_spec → appends to TASK.md section
    - run_log → appends to memory/run_log.md
    """
    from services.task_workspace import TaskWorkspace
    from datetime import datetime, timezone

    client = auth["client"]
    user_id = auth["user_id"]
    task_slug = input.get("task_slug", "")
    feedback_text = input.get("feedback", "")
    target = input.get("target", "run_log")

    if not task_slug or not feedback_text:
        return {"error": "task_slug and feedback are required"}

    try:
        tw = TaskWorkspace(client, user_id, task_slug)
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M")

        if target == "run_log":
            # Append to memory/run_log.md
            entry = f"\n## Feedback ({date_str})\n- {feedback_text}\n"
            existing = await tw.read("memory/run_log.md") or ""
            await tw.write("memory/run_log.md", existing + entry,
                          summary=f"Task feedback: {feedback_text[:50]}")
            return {"status": "ok", "message": f"Feedback recorded in run log for {task_slug}"}

        else:
            # Read TASK.md, find the target section, append feedback
            task_md = await tw.read("TASK.md")
            if not task_md:
                return {"error": f"TASK.md not found for {task_slug}"}

            section_map = {
                "criteria": "## Success Criteria",
                "objective": "## Objective",
                "output_spec": "## Output Specification",
            }
            section_header = section_map.get(target, "## Success Criteria")

            # Append feedback as a new bullet under the section
            feedback_line = f"- {feedback_text} (updated {date_str})"

            if section_header in task_md:
                # Insert after the section header
                parts = task_md.split(section_header, 1)
                updated = parts[0] + section_header + "\n" + feedback_line + parts[1]
            else:
                # Section doesn't exist — append at end
                updated = task_md + f"\n\n{section_header}\n{feedback_line}\n"

            await tw.write("TASK.md", updated, summary=f"Updated {target}: {feedback_text[:50]}")
            return {"status": "ok", "message": f"Updated {target} in {task_slug}"}

    except Exception as e:
        logger.warning(f"[WRITE_TASK_FEEDBACK] Failed: {e}")
        return {"error": str(e)}
