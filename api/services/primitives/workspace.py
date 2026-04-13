"""
Workspace & Inter-Agent Primitives — ADR-106 / ADR-107 / ADR-116 / ADR-168

Headless-only primitives that let reasoning agents interact with their
workspace, the shared knowledge base, and other agents.

ADR-168 Commit 4: Workspace-prefixed names renamed to File-suffixed names
to make the file-layer substrate explicit. No behavior change — the file
layer was always distinct from the entity layer, the names now reflect it.

- ReadFile (was ReadWorkspace): read from agent's workspace
- WriteFile (was WriteWorkspace): write to agent's workspace or shared context domain
- SearchFiles (was SearchWorkspace): full-text search within agent's workspace
- ListFiles (was ListWorkspace): list files in agent's workspace
- QueryKnowledge: semantic query over accumulated context domains (name preserved — distinct mental model)
- ReadAgentFile (was ReadAgentContext): read a file from another agent's workspace
- DiscoverAgents: find other agents by role/scope/status (ADR-116 Phase 2)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def _embed_workspace_file(client: Any, user_id: str, abs_path: str, content: str) -> None:
    """Fire-and-forget: generate embedding for a context file and update the row.

    ADR-174 Phase 2 — scoped to /workspace/context/ paths only. Non-blocking;
    called after successful WriteFile for context scope. Failure is logged but
    does not surface to the caller.
    """
    try:
        from services.embeddings import get_embedding
        embedding = await get_embedding(content)
        client.table("workspace_files").update(
            {"embedding": embedding}
        ).eq("user_id", user_id).eq("path", abs_path).execute()
        logger.debug(f"[WORKSPACE] Embedded context file: {abs_path}")
    except Exception as e:
        logger.warning(f"[WORKSPACE] Embedding failed (non-fatal) for {abs_path}: {e}")


# =============================================================================
# Tool Definitions
# =============================================================================

READ_FILE_TOOL = {
    "name": "ReadFile",
    "description": """Read a file from your workspace (file layer, path-based).

This is a FILE LAYER primitive — it reads a path within your workspace filesystem.
For entity lookups by typed ref (agent:uuid, document:uuid), use LookupEntity.

Your workspace contains your identity and methodology:
- AGENT.md — your identity and behavioral instructions
- memory/playbook-*.md — your methodology files

Use this to review your identity. For domain context, use QueryKnowledge or read from context domains via scope='context'.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path within your workspace (e.g., 'AGENT.md', 'memory/playbook-outputs.md')"
            }
        },
        "required": ["path"]
    }
}


WRITE_FILE_TOOL = {
    "name": "WriteFile",
    "description": """Write a file to shared context domains or your agent workspace (file layer, path-based).

This is a FILE LAYER primitive — it writes to a path within the workspace filesystem.
For entity mutations by typed ref, use EditEntity.

**Shared context** (scope="context") — PRIMARY USE:
- Write to /workspace/context/{domain}/ — accumulated intelligence shared across all tasks
- Use during "update-context" steps to persist research findings
- Example: WriteFile(path="acme-corp/signals.md", content="...", scope="context", domain="competitors")
- Entity files: {entity-slug}/profile.md, signals.md, product.md, strategy.md
- Synthesis files: landscape.md, overview.md, portfolio.md

**Agent workspace** (default scope):
- Rarely needed — agent workspace is identity only (AGENT.md, playbooks)

What you write to context domains persists between runs and is readable by all tasks that declare this domain in context_reads.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path. For scope='context': path within the domain folder, e.g., 'acme-corp/signals.md'. For scope='agent': e.g., 'AGENT.md'"
            },
            "content": {
                "type": "string",
                "description": "Content to write"
            },
            "mode": {
                "type": "string",
                "enum": ["overwrite", "append"],
                "description": "Write mode: 'overwrite' replaces the file, 'append' adds to end. Default: overwrite"
            },
            "scope": {
                "type": "string",
                "enum": ["agent", "context"],
                "description": "Write scope: 'agent' (default) writes to agent workspace, 'context' writes to /workspace/context/{domain}/"
            },
            "domain": {
                "type": "string",
                "description": "For scope='context': the context domain to write to (e.g., 'competitors', 'market', 'relationships')"
            }
        },
        "required": ["path", "content"]
    }
}


SEARCH_FILES_TOOL = {
    "name": "SearchFiles",
    "description": """Search your workspace filesystem for relevant content (file layer).

This is a FILE LAYER primitive — it searches filesystem content in your workspace.
For entity search by database table, use SearchEntities. For semantic search over
accumulated context domains, use QueryKnowledge.

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
    "description": """Search accumulated workspace context (ADR-151, ADR-174).

Context domains contain accumulated intelligence shared across all tasks.
Search by topic, entity, or keyword. Optionally filter by domain name to narrow results.

Domains are filesystem-discovered — any domain that has files appears here,
including user-created domains (customers/, investors/, campaigns/, etc.).
Do not assume a fixed set of domains; use ListFiles on /workspace/context/ to discover what exists.

Uses semantic search (vector similarity) as the primary path, with keyword
search as fallback. Best for conceptual queries: "what do we know about X?"
For path-based browsing, use ListFiles instead.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (topic, entity, keyword). Leave empty to list recent files."
            },
            "domain": {
                "type": "string",
                "description": "Optional: limit search to a specific context domain (e.g., 'competitors', 'market', or any custom domain)"
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


LIST_FILES_TOOL = {
    "name": "ListFiles",
    "description": """List files in your workspace (file layer, path-based).

This is a FILE LAYER primitive — it enumerates paths in your workspace filesystem.
For entity listing by database table, use ListEntities.

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


async def handle_read_file(auth: Any, input: dict) -> dict:
    """Handle ReadFile primitive (ADR-168: renamed from ReadWorkspace)."""
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context", "message": "ReadFile requires agent context"}

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    path = input.get("path", "")

    content = await ws.read(path)
    if content is None:
        return {
            "success": True,
            "found": False,
            "message": f"File not found: {path}. Use ListFiles to see available files.",
        }

    return {
        "success": True,
        "found": True,
        "path": path,
        "content": content,
    }


async def handle_write_file(auth: Any, input: dict) -> dict:
    """Handle WriteFile primitive (ADR-168: renamed from WriteWorkspace) — agent workspace or shared context domains.

    ADR-174 Phase 2: Two changes from prior implementation:
    1. Registry gate removed for scope='context'. Unknown domains are now allowed —
       TP can create new context domains freely. The registry is vocabulary, not enforcement.
       Domain folder derives to context/{domain}/ for any domain name.
    2. Async embedding generation fires after successful context file writes. Non-blocking
       fire-and-forget — embedding failure does not fail the write.
    """
    path = input.get("path", "")
    content = input.get("content", "")
    mode = input.get("mode", "overwrite")
    scope = input.get("scope", "agent")
    domain = input.get("domain", "")

    if scope == "context":
        # ADR-151 + ADR-174: Write to shared context domain /workspace/context/{domain}/
        # ADR-174: domain need not be in the registry — any domain name is valid.
        if not domain:
            return {"success": False, "error": "missing_domain", "message": "domain is required for scope='context'"}

        from services.workspace import UserMemory

        # ADR-174: derive folder directly — registry is vocabulary, not gate.
        # Known domains resolve to their declared path; unknown domains default to context/{domain}.
        from services.directory_registry import get_domain_folder
        domain_folder = get_domain_folder(domain) or f"context/{domain}"

        full_path = f"{domain_folder}/{path}"
        abs_path = f"/workspace/{full_path}"

        um = UserMemory(auth.client, auth.user_id)
        if mode == "append":
            existing = await um.read(full_path) or ""
            success = await um.write(full_path, existing + "\n" + content,
                                     summary=f"Context update: {domain}/{path}")
        else:
            success = await um.write(full_path, content,
                                     summary=f"Context write: {domain}/{path}")

        if success:
            # ADR-174 Phase 2: embed context files async (fire-and-forget).
            # Scoped to /workspace/context/ only. Failure is non-fatal.
            asyncio.ensure_future(
                _embed_workspace_file(auth.client, auth.user_id, abs_path, content)
            )
            return {"success": True, "path": abs_path, "domain": domain, "scope": "context"}
        return {"success": False, "error": "write_failed", "message": f"Failed to write: {full_path}"}

    else:
        # Default: write to agent workspace
        from services.workspace import AgentWorkspace, get_agent_slug

        agent = getattr(auth, "agent", None)
        if not agent:
            return {"success": False, "error": "no_agent_context", "message": "WriteFile requires agent context"}

        ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))

        if mode == "append":
            success = await ws.append(path, content)
        else:
            success = await ws.write(path, content)

        if success:
            return {"success": True, "path": path, "mode": mode, "scope": "agent"}
        return {"success": False, "error": "write_failed", "message": f"Failed to write: {path}"}


async def handle_search_files(auth: Any, input: dict) -> dict:
    """Handle SearchFiles primitive (ADR-168: renamed from SearchWorkspace)."""
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context", "message": "SearchFiles requires agent context"}

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
    """Handle QueryKnowledge primitive — searches /workspace/context/ accumulated domains.

    ADR-151 + ADR-174 Phase 2: Semantic search as primary path, BM25 as fallback.
    - Primary: vector cosine similarity via search_workspace_semantic RPC (requires embedding)
    - Fallback: BM25 full-text via search_workspace RPC (always available)

    ADR-174: domain filter resolves to any path under /workspace/context/{domain}/,
    including user-created domains not in the registry.
    """
    query = input.get("query") or ""
    domain = input.get("content_class") or input.get("domain")  # content_class kept for backwards compat
    limit = min(input.get("limit", 10), 30)

    # Resolve path prefix — registry for known domains, direct path for unknown.
    prefix = "/workspace/context/"
    if domain:
        from services.directory_registry import get_domain_folder
        domain_folder = get_domain_folder(domain) or f"context/{domain}"
        prefix = f"/workspace/{domain_folder}/"

    rows = []
    search_method = "none"

    if query:
        # --- Primary: semantic search via vector embedding ---
        semantic_ok = False
        try:
            from services.embeddings import get_embedding
            query_embedding = await get_embedding(query)
            result = auth.client.rpc("search_workspace_semantic", {
                "p_user_id": auth.user_id,
                "p_query_embedding": query_embedding,
                "p_path_prefix": prefix,
                "p_limit": limit,
            }).execute()
            sem_rows = result.data or []
            # Only use semantic results if we got meaningful similarity scores
            if sem_rows and sem_rows[0].get("similarity", 0) > 0.3:
                rows = sem_rows
                search_method = "semantic"
                semantic_ok = True
        except Exception as e:
            logger.warning(f"[QUERY_KNOWLEDGE] Semantic search failed, falling back to BM25: {e}")

        # --- Fallback: BM25 full-text search ---
        if not semantic_ok:
            try:
                result = auth.client.rpc("search_workspace", {
                    "p_user_id": auth.user_id,
                    "p_query": query,
                    "p_path_prefix": prefix,
                    "p_limit": limit,
                }).execute()
                rows = result.data or []
                search_method = "bm25"
            except Exception as e:
                logger.warning(f"[QUERY_KNOWLEDGE] BM25 fallback also failed: {e}")

    else:
        # No query — list recent files in the domain
        try:
            result = (
                auth.client.table("workspace_files")
                .select("path, content, summary, updated_at, metadata")
                .eq("user_id", auth.user_id)
                .like("path", f"{prefix}%")
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            rows = result.data or []
            search_method = "list"
        except Exception as e:
            logger.warning(f"[QUERY_KNOWLEDGE] List failed: {e}")

    result_items = []
    for r in rows:
        path = r.get("path", "")
        content = r.get("content", "")
        summary = r.get("summary", "")
        item = {
            "path": path,
            "summary": summary or path.split("/")[-1],
            "content_preview": content[:500] if content else "",
            "updated_at": r.get("updated_at", ""),
        }
        if "similarity" in r:
            item["similarity"] = round(r["similarity"], 3)
        result_items.append(item)

    return {
        "success": True,
        "query": query,
        "domain": domain,
        "search_method": search_method,
        "count": len(result_items),
        "results": result_items,
    }


async def handle_list_files(auth: Any, input: dict) -> dict:
    """Handle ListFiles primitive (ADR-168: renamed from ListWorkspace)."""
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context", "message": "ListFiles requires agent context"}

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    path = input.get("path", "")

    files = await ws.list(path)

    return {
        "success": True,
        "path": path or "/",
        "files": files,
        "count": len(files),
    }


# ADR-153: _fallback_platform_content_search DELETED — platform_content sunset.
# Context domains are the sole data source. No fallback to raw platform data.


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
# ADR-116 Phase 3 + ADR-168 Commit 4: ReadAgentFile (renamed from ReadAgentContext)
# =============================================================================

READ_AGENT_FILE_TOOL = {
    "name": "ReadAgentFile",
    "description": """Read files from another agent's workspace — identity and domain understanding.

This is a FILE LAYER primitive, cross-agent variant. Distinct from ReadFile
(own workspace) and LookupEntity (entity layer).

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


async def handle_read_agent_file(auth: Any, input: dict) -> dict:
    """Handle ReadAgentFile primitive — ADR-116 Phase 3 + ADR-168 Commit 4.

    Read-only cross-agent workspace access for identity files.
    Restricted to synthesize, research roles (enforced by headless registry).
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

# ADR-146: WriteAgentFeedback and WriteTaskFeedback deleted.
# Absorbed into UpdateContext(target="agent"|"task") in update_context.py.
