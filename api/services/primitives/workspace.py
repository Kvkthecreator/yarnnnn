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
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

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
        # ADR-209 permitted exception: metadata-only updates (no content
        # mutation) bypass the revision chain. Embedding is a derived index
        # over content that was already recorded by write_revision, not a
        # new authored change — so we update workspace_files.embedding
        # directly. See authored_substrate.py docstring "NOT routed through
        # write_revision".
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
    "description": """Read a file from the workspace filesystem (file layer, path-based).

This is a FILE LAYER primitive — it reads a path within the workspace filesystem.
For entity lookups by typed ref (agent:uuid, document:uuid), use LookupEntity.

Two scopes (ADR-235 Option A):

**scope='workspace'** (chat default) — read workspace-relative paths via the
operator-shared substrate. Use for shared context, governance, working memory,
task substrate, etc.
  ReadFile(scope='workspace', path='context/_shared/MANDATE.md')
  ReadFile(scope='workspace', path='memory/notes.md')
  ReadFile(scope='workspace', path='reports/market-weekly/_spec.yaml')

**scope='agent'** (headless default) — read from the calling agent's workspace
(/agents/{slug}/...). Requires agent context.
  ReadFile(scope='agent', path='AGENT.md')
  ReadFile(scope='agent', path='memory/playbook-outputs.md')

For semantic search across accumulated context domains, use QueryKnowledge.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path. For scope='workspace': workspace-relative (e.g. 'context/_shared/MANDATE.md', 'memory/notes.md'). For scope='agent': relative to the agent's workspace (e.g. 'AGENT.md')."
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent"],
                "description": "Read scope. 'workspace' (default for chat) reaches operator-shared substrate. 'agent' (default for headless agents) reaches the calling agent's workspace.",
            },
        },
        "required": ["path"]
    }
}


WRITE_FILE_TOOL = {
    "name": "WriteFile",
    "description": """Write a file to the workspace filesystem (file layer, path-based).

This is a FILE LAYER primitive — it writes to a path within the workspace filesystem.
For entity mutations by typed ref, use EditEntity.

Three scopes (ADR-235 Option A):

**scope='workspace'** (chat default) — write to operator-shared substrate via
workspace-relative path. Use for governance declarations, working memory,
task feedback, awareness handoff, etc.
  WriteFile(scope='workspace', path='context/_shared/MANDATE.md', content='...')
  WriteFile(scope='workspace', path='memory/notes.md', content='...', mode='append')
  WriteFile(scope='workspace', path='memory/awareness.md', content='...')
  WriteFile(scope='workspace', path='reports/market-weekly/feedback.md', content='...', mode='append')

  Writes to recognized canonical paths emit activity log events automatically:
    'memory/notes.md'   → 'memory_written'
    'agents/{slug}/memory/feedback.md' → 'agent_feedback'

**scope='context'** — write to a shared context domain at
/workspace/context/{domain}/. Use during "update-context" steps to persist
research findings.
  WriteFile(scope='context', domain='competitors', path='acme-corp/signals.md', content='...')

**scope='agent'** — write to the calling agent's workspace
(/agents/{slug}/...). Rarely needed — agent workspace is identity only.

For attribution semantics, every write lands a workspace_file_versions row
via the Authored Substrate (ADR-209) with attribution + revision chain.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path. For scope='workspace': workspace-relative (e.g., 'context/_shared/MANDATE.md', 'memory/notes.md', 'reports/market-weekly/feedback.md'). For scope='context': within the domain folder (e.g., 'acme-corp/signals.md'). For scope='agent': relative to the agent's workspace (e.g., 'AGENT.md').",
            },
            "content": {
                "type": "string",
                "description": "Content to write.",
            },
            "mode": {
                "type": "string",
                "enum": ["overwrite", "append"],
                "description": "Write mode: 'overwrite' replaces the file, 'append' adds to end. Default: overwrite.",
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent", "context"],
                "description": "Write scope. 'workspace' (default for chat) reaches operator-shared substrate via workspace-relative path. 'context' writes to /workspace/context/{domain}/. 'agent' writes to the calling agent's workspace.",
            },
            "domain": {
                "type": "string",
                "description": "For scope='context': the context domain (e.g., 'competitors', 'market', 'relationships').",
            },
            "authored_by": {
                "type": "string",
                "description": "ADR-209 attribution. For scope='workspace' writes from chat, defaults to 'yarnnn:chat' if omitted; for explicit operator-authored writes pass 'operator'. Optional otherwise.",
            },
            "message": {
                "type": "string",
                "description": "ADR-209 commit-style message describing what changed (optional).",
            },
        },
        "required": ["path", "content"],
    },
}


SEARCH_FILES_TOOL = {
    "name": "SearchFiles",
    "description": """Search the workspace filesystem for content (file layer).

This is a FILE LAYER primitive — it searches filesystem content via BM25
full-text. For semantic search over accumulated context domains, use
QueryKnowledge. For entity search by database table, use SearchEntities.

Two scopes (ADR-235 Option A):

**scope='workspace'** (chat default) — search across the entire operator-shared
filesystem. Optional path_prefix narrows the search.
  SearchFiles(scope='workspace', query='mandate workspace declaration')
  SearchFiles(scope='workspace', query='paper trades closed', path_prefix='reports/')

**scope='agent'** (headless default) — search within the calling agent's workspace.
Ephemeral scratch files (working/) are excluded from search by default.
  SearchFiles(scope='agent', query='thesis')""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query.",
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent"],
                "description": "Search scope. 'workspace' (default for chat) searches operator-shared substrate. 'agent' (default for headless agents) searches the calling agent's workspace.",
            },
            "path_prefix": {
                "type": "string",
                "description": "Optional: limit search to a subdirectory (e.g., 'reports/', 'context/', 'working/').",
            },
        },
        "required": ["query"],
    },
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
    "description": """List files in the workspace filesystem (file layer, path-based).

This is a FILE LAYER primitive — it enumerates paths in the workspace
filesystem. For entity listing by database table, use ListEntities.

Two scopes (ADR-235 Option A):

**scope='workspace'** (chat default) — list operator-shared substrate.
Pass `path` to scope a subdirectory (e.g. 'context/', 'reports/', 'memory/').
  ListFiles(scope='workspace')                        # top-level workspace folders
  ListFiles(scope='workspace', path='context/')       # context domains
  ListFiles(scope='workspace', path='reports/')       # task report folders

**scope='agent'** (headless default) — list within the calling agent's workspace.
Ephemeral (working/) and archived files are hidden by default.

ADR-209 Phase 3 filters (all optional, both scopes):
- authored_by: filter to files whose most-recent revision was authored by a
  specific identity (e.g., 'operator', 'yarnnn:claude-sonnet-4-7',
  'agent:alpha-research', 'reviewer:ai-sonnet-v1',
  'system:outcome-reconciliation'). Supports prefix match — 'agent:' returns
  every file most-recently authored by any agent.
- since: ISO 8601 timestamp — only include files whose most-recent revision
  is at or after this time.
- until: ISO 8601 timestamp — only include files whose most-recent revision
  is at or before this time.

Operator-facing examples:
  ListFiles(scope='workspace', authored_by='operator', since='2026-04-22T00:00:00Z')
  ListFiles(scope='workspace', authored_by='yarnnn:', since='2026-04-28T20:00:00Z')""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Optional: subdirectory to list. For scope='workspace' use workspace-relative (e.g. 'context/', 'reports/', 'memory/'). For scope='agent' relative to the agent's workspace.",
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent"],
                "description": "List scope. 'workspace' (default for chat) lists operator-shared substrate. 'agent' (default for headless agents) lists within the calling agent's workspace.",
            },
            "authored_by": {
                "type": "string",
                "description": "Optional: filter to files whose most-recent revision matches this authored_by prefix (e.g., 'operator', 'agent:', 'yarnnn:').",
            },
            "since": {
                "type": "string",
                "description": "Optional: ISO 8601 timestamp. Only files with most-recent revision at or after this time.",
            },
            "until": {
                "type": "string",
                "description": "Optional: ISO 8601 timestamp. Only files with most-recent revision at or before this time.",
            },
        },
        "required": [],
    },
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
    """Handle ReadFile primitive (ADR-168: renamed from ReadWorkspace; ADR-235 Option A: scope='workspace').

    Two scopes:
      - 'workspace' (default for chat): reads workspace-relative paths via UserMemory.
        Reaches operator-shared substrate (context/, memory/, review/, reports/, etc.).
      - 'agent' (default when agent context present): reads from the calling agent's workspace.
    """
    from services.workspace import AgentWorkspace, UserMemory, get_agent_slug

    path = input.get("path", "")
    scope = input.get("scope") or _default_file_scope(auth)

    if scope == "workspace":
        um = UserMemory(auth.client, auth.user_id)
        content = await um.read(path)
        if content is None:
            return {
                "success": True,
                "found": False,
                "scope": "workspace",
                "path": path,
                "message": f"File not found: {path}. Use ListFiles to see available files.",
            }
        return {
            "success": True,
            "found": True,
            "scope": "workspace",
            "path": path,
            "content": content,
        }

    agent = getattr(auth, "agent", None)
    if not agent:
        return {
            "success": False,
            "error": "no_agent_context",
            "message": "ReadFile scope='agent' requires agent context. Use scope='workspace' for operator-shared paths.",
        }

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    content = await ws.read(path)
    if content is None:
        return {
            "success": True,
            "found": False,
            "scope": "agent",
            "path": path,
            "message": f"File not found: {path}. Use ListFiles to see available files.",
        }

    return {
        "success": True,
        "found": True,
        "scope": "agent",
        "path": path,
        "content": content,
    }


def _default_file_scope(auth: Any) -> str:
    """Pick a default scope based on caller shape.

    Chat callers (no agent context) default to 'workspace'. Headless agent
    callers (agent attached to auth) default to 'agent' to preserve the
    pre-ADR-235 behavior. Either caller can override explicitly.
    """
    return "agent" if getattr(auth, "agent", None) else "workspace"


# ---------------------------------------------------------------------------
# Activity-log path recognition (ADR-235 D1.b)
# ---------------------------------------------------------------------------
#
# A subset of canonical workspace paths emit activity-log events on write.
# This is a deliberate path-coupling inside WriteFile rather than per-target
# bloat in the primitive's input schema. The recognition table is small;
# unknown paths emit no event (silent default).

import re as _re

_AGENT_FEEDBACK_PATH_RE = _re.compile(r"^agents/([^/]+)/memory/feedback\.md$")


def _classify_workspace_path_for_activity(rel_path: str) -> Optional[dict]:
    """Return an activity-log event dict for a recognized canonical path, else None.

    Recognized paths:
      memory/notes.md                       → memory_written
      agents/{slug}/memory/feedback.md      → agent_feedback (with agent_slug metadata)

    Other paths (governance declarations, task feedback, awareness, recurrence
    YAMLs, context domain files, agent workspace files) do NOT emit activity
    events — they are recorded only via the Authored Substrate revision chain.
    """
    if rel_path == "memory/notes.md":
        return {"event_type": "memory_written", "metadata": {}}

    m = _AGENT_FEEDBACK_PATH_RE.match(rel_path)
    if m:
        agent_slug = m.group(1)
        return {
            "event_type": "agent_feedback",
            "metadata": {"agent_slug": agent_slug, "source": "conversation"},
        }

    return None


async def _emit_workspace_activity(
    auth: Any,
    rel_path: str,
    content: str,
) -> None:
    """Emit an activity-log event when a recognized path is written. Best-effort."""
    classification = _classify_workspace_path_for_activity(rel_path)
    if classification is None:
        return

    try:
        from services.activity_log import write_activity

        preview = content[:60] + "..." if len(content) > 60 else content
        summary = (
            f"Noted: {preview}"
            if classification["event_type"] == "memory_written"
            else f"Feedback for {classification['metadata'].get('agent_slug', '?')}: {preview}"
        )

        await write_activity(
            client=auth.client,
            user_id=auth.user_id,
            event_type=classification["event_type"],
            summary=summary,
            metadata=classification["metadata"],
        )
    except Exception as e:
        logger.debug(f"[WORKSPACE] activity emission failed (non-fatal): {e}")


async def handle_write_file(auth: Any, input: dict) -> dict:
    """Handle WriteFile primitive (ADR-168: renamed from WriteWorkspace; ADR-235 Option A: scope='workspace').

    Three scopes:
      - 'workspace' (default for chat): writes workspace-relative paths via UserMemory.
        Reaches operator-shared substrate (context/, memory/, review/, reports/, ...).
        Recognized canonical paths (memory/notes.md, agents/{slug}/memory/feedback.md)
        emit activity-log events automatically (ADR-235 D1.b).
      - 'context': writes a shared context domain at /workspace/context/{domain}/.
      - 'agent' (default when agent context present): writes to the calling agent's workspace.

    ADR-174 Phase 2: Registry gate removed for scope='context'. Unknown domains
    allowed — TP can create new context domains freely. Async embedding generation
    fires after successful context file writes. Non-blocking; failure does not
    fail the write.
    """
    path = input.get("path", "")
    content = input.get("content", "")
    mode = input.get("mode", "overwrite")
    scope = input.get("scope") or _default_file_scope(auth)
    domain = input.get("domain", "")
    authored_by = input.get("authored_by")
    message = input.get("message")

    if scope == "workspace":
        # ADR-235 Option A: workspace-relative paths via UserMemory. Reaches
        # operator-shared substrate (context/, memory/, review/, reports/, ...).
        # Recognized canonical paths emit activity-log events on write.
        from services.workspace import UserMemory

        if not path:
            return {"success": False, "error": "missing_path", "message": "path is required"}

        um = UserMemory(auth.client, auth.user_id)

        if mode == "append":
            existing = await um.read(path) or ""
            new_content = existing + ("\n" if existing else "") + content
        else:
            new_content = content

        # Default authored_by for chat-driven writes is yarnnn:chat unless the
        # caller explicitly asserts operator authorship. Headless writes via
        # scope='workspace' should pass authored_by explicitly.
        resolved_author = authored_by or "yarnnn:chat"
        resolved_message = message or f"WriteFile workspace {path}"

        ok = await um.write(
            path,
            new_content,
            summary=f"Workspace write: {path}",
            authored_by=resolved_author,
            message=resolved_message,
        )

        abs_path = f"/workspace/{path}"
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"Failed to write: {abs_path}"}

        # ADR-235 D1.b: emit activity log for recognized canonical paths.
        await _emit_workspace_activity(auth, path, content)

        return {"success": True, "scope": "workspace", "path": abs_path, "mode": mode}

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
            new_content = existing + "\n" + content
            success = await um.write(full_path, new_content,
                                     summary=f"Context update: {domain}/{path}")
        else:
            # ADR-176 Phase 4: Content hash dedup — skip write if content unchanged.
            # Cheap SHA-256 comparison avoids unnecessary DB writes and embedding calls.
            filename = path.rsplit("/", 1)[-1] if "/" in path else path
            # ADR-209: versioning is substrate-native — every write to the
            # Authored Substrate (via um.write → write_revision) lands a new
            # revision with authored_by + message attribution and preserves
            # prior content in the revision chain. The explicit dedup check
            # below remains a short-circuit optimization (avoids creating a
            # no-op revision for idempotent writes).
            existing_content = await um.read(full_path)
            if existing_content is not None:
                existing_hash = hashlib.sha256(existing_content.encode()).hexdigest()
                new_hash = hashlib.sha256(content.encode()).hexdigest()
                if existing_hash == new_hash:
                    return {"success": True, "path": abs_path, "domain": domain,
                            "scope": "context", "skipped": True, "reason": "content_unchanged"}

            new_content = content
            # authored_by derives from the invoking caller identity:
            # context writes typically come through WriteFile primitive invoked by
            # an agent or by YARNNN. We pass the agent slug when known
            # (via write_context_ref) or fall back to "yarnnn:<model>" for
            # YARNNN-authored context. UserMemory.write's default
            # ("system:user-memory") is the safety net.
            success = await um.write(
                full_path, new_content,
                summary=f"Context write: {domain}/{path}",
                message=f"WriteFile context {domain}/{path}",
            )

        if success:
            # ADR-174 Phase 2: embed context files async (fire-and-forget).
            # Scoped to /workspace/context/ only. Failure is non-fatal.
            asyncio.ensure_future(
                _embed_workspace_file(auth.client, auth.user_id, abs_path, new_content)
            )
            return {"success": True, "path": abs_path, "domain": domain, "scope": "context"}
        return {"success": False, "error": "write_failed", "message": f"Failed to write: {full_path}"}

    # scope == "agent"
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {
            "success": False,
            "error": "no_agent_context",
            "message": "WriteFile scope='agent' requires agent context. Use scope='workspace' for operator-shared paths or scope='context' for context domains.",
        }

    agent_slug = get_agent_slug(agent)
    ws = AgentWorkspace(auth.client, auth.user_id, agent_slug)

    if mode == "append":
        success = await ws.append(path, content)
    else:
        success = await ws.write(path, content)

    if not success:
        return {"success": False, "error": "write_failed", "message": f"Failed to write: {path}"}

    # ADR-235 D1.b: emit activity log for recognized canonical paths.
    # Compose the workspace-relative path so the classifier's regex matches.
    rel_in_workspace = f"agents/{agent_slug}/{path}"
    await _emit_workspace_activity(auth, rel_in_workspace, content)

    return {"success": True, "path": path, "mode": mode, "scope": "agent"}


async def handle_search_files(auth: Any, input: dict) -> dict:
    """Handle SearchFiles primitive (ADR-168: renamed from SearchWorkspace; ADR-235 Option A: scope='workspace').

    Two scopes:
      - 'workspace' (default for chat): BM25 search across the entire operator
        workspace. Optional path_prefix narrows the search.
      - 'agent' (default when agent context present): scoped search within the
        calling agent's workspace.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    query = input.get("query", "")
    scope = input.get("scope") or _default_file_scope(auth)
    path_prefix = input.get("path_prefix")

    if scope == "workspace":
        # Direct RPC call with workspace-wide prefix (or sub-prefix if requested).
        prefix = "/workspace"
        if path_prefix:
            normalized = path_prefix if path_prefix.startswith("/") else f"/workspace/{path_prefix.lstrip('/')}"
            prefix = normalized

        try:
            result = auth.client.rpc("search_workspace", {
                "p_user_id": auth.user_id,
                "p_query": query,
                "p_path_prefix": prefix,
                "p_limit": 20,
            }).execute()
            rows = result.data or []
        except Exception as e:
            logger.warning(f"[SEARCH_FILES] workspace search failed: {e}")
            rows = []

        return {
            "success": True,
            "scope": "workspace",
            "query": query,
            "path_prefix": prefix,
            "count": len(rows),
            "results": [
                {
                    "path": r["path"],
                    "summary": r.get("summary"),
                    "content_preview": (r.get("content") or "")[:500],
                }
                for r in rows
            ],
        }

    agent = getattr(auth, "agent", None)
    if not agent:
        return {
            "success": False,
            "error": "no_agent_context",
            "message": "SearchFiles scope='agent' requires agent context. Use scope='workspace' for operator-shared paths.",
        }

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    results = await ws.search(query, path_prefix=path_prefix)

    return {
        "success": True,
        "scope": "agent",
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
    """Handle ListFiles primitive (ADR-168: renamed from ListWorkspace; ADR-235 Option A: scope='workspace').

    Two scopes:
      - 'workspace' (default for chat): direct DB enumeration under /workspace/{path}.
        Returns direct children (folders + files); pass `path` to scope.
      - 'agent' (default when agent context present): scoped list within the
        calling agent's workspace.

    ADR-209 Phase 3: supports authored_by / since / until filters in both scopes
    via a join against workspace_file_versions.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    path = input.get("path", "")
    scope = input.get("scope") or _default_file_scope(auth)
    authored_by = (input.get("authored_by") or "").strip()
    since = (input.get("since") or "").strip()
    until = (input.get("until") or "").strip()

    if scope == "workspace":
        # Direct DB query — list under /workspace/{path or ''}
        prefix = "/workspace/"
        if path:
            sub = path.lstrip("/")
            if not sub.endswith("/"):
                sub += "/"
            prefix = f"/workspace/{sub}"

        try:
            q = (
                auth.client.table("workspace_files")
                .select("path")
                .eq("user_id", auth.user_id)
                .like("path", f"{prefix}%")
                .in_("lifecycle", ["active", "delivered"])
            )
            result = q.order("path").execute()
            abs_paths = [r["path"] for r in (result.data or [])]
        except Exception as e:
            logger.warning(f"[LIST_FILES] workspace list failed: {e}")
            abs_paths = []

        # Apply ADR-209 filters if any provided.
        if authored_by or since or until:
            try:
                fq = (
                    auth.client.table("workspace_file_versions")
                    .select("path")
                    .eq("user_id", auth.user_id)
                    .like("path", f"{prefix}%")
                )
                if authored_by:
                    fq = fq.like("authored_by", f"{authored_by}%")
                if since:
                    fq = fq.gte("created_at", since)
                if until:
                    fq = fq.lte("created_at", until)
                fq = fq.order("created_at", desc=True)
                fres = fq.execute()
                matched_abs = {row.get("path") for row in (fres.data or []) if row.get("path")}
            except Exception as e:
                logger.warning(f"[LIST_FILES] workspace filter query failed: {e}")
                matched_abs = set()
            abs_paths = [p for p in abs_paths if p in matched_abs]

        # Project to direct children of prefix.
        direct = set()
        for p in abs_paths:
            remainder = p[len(prefix):] if p.startswith(prefix) else p
            if not remainder:
                continue
            if "/" in remainder:
                direct.add(remainder.split("/", 1)[0] + "/")
            else:
                direct.add(remainder)

        files = sorted(direct)
        return {
            "success": True,
            "scope": "workspace",
            "path": prefix,
            "files": files,
            "count": len(files),
            "filters_applied": {
                "authored_by": authored_by or None,
                "since": since or None,
                "until": until or None,
            } if (authored_by or since or until) else None,
        }

    agent = getattr(auth, "agent", None)
    if not agent:
        return {
            "success": False,
            "error": "no_agent_context",
            "message": "ListFiles scope='agent' requires agent context. Use scope='workspace' for operator-shared paths.",
        }

    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    files = await ws.list(path)

    # ADR-209 Phase 3 filters: authored_by (prefix match) + since/until
    # (timestamp window on most-recent revision). If any filter present,
    # intersect `files` with the set of paths whose head revision matches.
    if authored_by or since or until:
        # Resolve the requested list to absolute paths so we can match against
        # workspace_file_versions rows. ws.list() returns paths relative to the
        # `prefix` passed in (or relative to /agents/{slug}/ when path="").
        from services.workspace import AgentWorkspace as _AW  # for _full_path access
        if path and not path.endswith("/"):
            path_for_prefix = path + "/"
        else:
            path_for_prefix = path
        full_prefix = ws._full_path(path_for_prefix) if path_for_prefix else ws._base + "/"

        q = (
            auth.client.table("workspace_file_versions")
            .select("path, authored_by, created_at")
            .eq("user_id", auth.user_id)
            .like("path", f"{full_prefix}%")
        )
        if authored_by:
            # Prefix match — 'agent:' or 'operator' or 'system:outcome-reconciliation'
            q = q.like("authored_by", f"{authored_by}%")
        if since:
            q = q.gte("created_at", since)
        if until:
            q = q.lte("created_at", until)

        # Order by created_at DESC and take first occurrence per path
        # (approximates "most-recent revision matches"). PostgREST doesn't
        # expose DISTINCT ON, so we post-process in Python.
        q = q.order("created_at", desc=True)

        try:
            result = q.execute()
        except Exception as e:
            logger.warning(f"[LIST_FILES] ADR-209 filter query failed: {e}")
            result = type("X", (), {"data": []})()

        matched_abs_paths = set()
        for row in (result.data or []):
            p = row.get("path")
            if p and p not in matched_abs_paths:
                matched_abs_paths.add(p)

        # Filter `files` (relative paths) to those whose absolute path is in matched
        prefix_strip = full_prefix
        filtered = []
        for rel in files:
            candidate = prefix_strip + rel if not rel.endswith("/") else None
            if candidate and candidate in matched_abs_paths:
                filtered.append(rel)
        files = filtered

    return {
        "success": True,
        "scope": "agent",
        "path": path or "/",
        "files": files,
        "count": len(files),
        "filters_applied": {
            "authored_by": authored_by or None,
            "since": since or None,
            "until": until or None,
        } if (authored_by or since or until) else None,
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
# ADR-235: Their successor (UpdateContext target='agent'|'task') is also
# deleted. Feedback writes now go through WriteFile(scope="workspace", ...)
# at the canonical path (agents/{slug}/memory/feedback.md or task natural-
# home feedback.md). The activity-log emission previously inside the
# UpdateContext handlers is now a path-prefix recognition step inside the
# WriteFile dispatch (ADR-235 D1.b).
