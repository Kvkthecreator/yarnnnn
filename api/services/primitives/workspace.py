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
  ReadFile(scope='workspace', path='constitution/MANDATE.md')
  ReadFile(scope='workspace', path='system/notes.md')
  ReadFile(scope='workspace', path='reports/market-weekly/_spec.yaml')

**scope='agent'** (headless default) — read from the calling agent's workspace
(/agents/{slug}/...). Requires agent context.
  ReadFile(scope='agent', path='AGENT.md')
  ReadFile(scope='agent', path='system/playbook-outputs.md')

Independent reads batch: when reading several known paths (sibling files, a
report's sections), issue the ReadFile calls together in a single turn rather
than one per turn.

For semantic search across accumulated context domains, use QueryKnowledge.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path. For scope='workspace': workspace-relative (e.g. 'constitution/MANDATE.md', 'system/notes.md'). For scope='agent': relative to the agent's workspace (e.g. 'AGENT.md')."
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
  WriteFile(scope='workspace', path='constitution/MANDATE.md', content='...')
  WriteFile(scope='workspace', path='system/notes.md', content='...', mode='append')
  WriteFile(scope='workspace', path='system/awareness.md', content='...')
  WriteFile(scope='workspace', path='reports/market-weekly/feedback.md', content='...', mode='append')

  Writes to recognized canonical paths emit activity log events automatically:
    'system/notes.md'   → 'memory_written'
    'agents/{slug}/memory/feedback.md' → 'agent_feedback'

  Accumulated domain context is path-native under operation/{domain}/ (ADR-321 —
  the path's root is the address; there is no separate 'context' scope):
  WriteFile(scope='workspace', path='operation/competitors/acme-corp/signals.md', content='...')

**scope='agent'** — write to the calling agent's workspace
(/agents/{slug}/...). Rarely needed — agent workspace is identity only.

For attribution semantics, every write lands a workspace_file_versions row
via the Authored Substrate (ADR-209) with attribution + revision chain.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path (the root IS the address — ADR-320/321). For scope='workspace': workspace-relative under one of the five roots (e.g., 'constitution/MANDATE.md', 'system/notes.md', 'reports/market-weekly/feedback.md', 'operation/competitors/acme-corp/signals.md' for accumulated domain context). For scope='agent': relative to the agent's workspace (e.g., 'AGENT.md').",
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
                "enum": ["workspace", "agent"],
                "description": "Write scope (address-space selector, ADR-321). 'workspace' (default for chat) reaches the five-root operator-shared filesystem via a workspace-relative path — the path's top-level root is the address (governance/constitution/persona/operation/system). 'agent' writes to the calling agent's private workspace.",
            },
            "authored_by": {
                "type": "string",
                "description": "ADR-209 attribution. Defaults to the caller identity from auth (typically 'operator' from operator-mediated chat, 'reviewer:...' from Reviewer wake, 'specialist:...' from sub-LLM dispatch, 'system:...' from mechanical recurrence, 'yarnnn:mcp' from MCP tool). Pass explicitly when overriding (e.g., a route handler asserting 'operator' on behalf of the user). Optional otherwise.",
            },
            "message": {
                "type": "string",
                "description": "ADR-209 commit-style message describing what changed (optional).",
            },
        },
        "required": ["path", "content"],
    },
}


EDIT_FILE_TOOL = {
    "name": "EditFile",
    "description": """Surgically replace a string within a workspace file (file layer, ADR-337 D1).

Prefer this over WriteFile for ANY change to an existing file — appending one
entry, fixing one threshold, updating one section. Regenerating a whole file
to change part of it is wasteful and truncation-prone.

Contract:
- old_string must match the file content EXACTLY (including whitespace) and,
  unless replace_all=true, must be UNIQUE in the file — include surrounding
  context to disambiguate.
- The edit lands as one attributed revision (ADR-209); prior content is
  retained in the revision chain.
- An edit may not empty the file — removing a file is DeleteFile, by intent.

  EditFile(path='persona/principles.md', old_string='threshold: 5', new_string='threshold: 8')""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path (same addressing as WriteFile — workspace-relative for scope='workspace', agent-relative for scope='agent').",
            },
            "old_string": {
                "type": "string",
                "description": "Exact text to replace. Must exist in the file; must be unique unless replace_all=true.",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement text (must differ from old_string).",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace every occurrence of old_string (default false).",
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent"],
                "description": "Address-space selector, same semantics as WriteFile.",
            },
            "authored_by": {
                "type": "string",
                "description": "ADR-209 attribution. Defaults to the caller identity from auth.",
            },
            "message": {
                "type": "string",
                "description": "ADR-209 commit-style message describing the change (optional).",
            },
        },
        "required": ["path", "old_string", "new_string"],
    },
}


DELETE_FILE_TOOL = {
    "name": "DeleteFile",
    "description": """Remove a file from the live workspace view; the revision chain retains everything (ADR-337 D2).

Deletion is a VIEW change, not information loss: an attributed tombstone
revision records who deleted, when, and the content at deletion; ListRevisions /
ReadRevision still work on the path afterward, and restore is ReadRevision +
WriteFile (ADR-209 D7 revert-as-write).

Use for substrate hygiene: superseded scratch files, dead duplicates after a
move, stale artifacts that mislead future reads. Governance-locked paths
cannot be deleted (same locks as WriteFile).

  DeleteFile(path='system/old-draft-notes.md', message='superseded by system/notes.md')""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to remove (same addressing as WriteFile).",
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent"],
                "description": "Address-space selector, same semantics as WriteFile.",
            },
            "authored_by": {
                "type": "string",
                "description": "ADR-209 attribution. Defaults to the caller identity from auth.",
            },
            "message": {
                "type": "string",
                "description": "Why this file is being removed (recorded on the tombstone revision; optional but encouraged).",
            },
        },
        "required": ["path"],
    },
}


MOVE_FILE_TOOL = {
    "name": "MoveFile",
    "description": """Move/rename a workspace file to a new path as one attributed operation (ADR-337 D3).

Writes the current content as a revision at new_path, then removes the old
live row with a tombstone revision pointing at the destination. Both paths
are checked against governance locks. Refuses to overwrite an existing
destination — if the destination must be replaced, DeleteFile it first
(explicit intent).

  MoveFile(path='operation/notes/draft.md', new_path='operation/competitors/acme/notes.md')""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Current path of the file (same addressing as WriteFile).",
            },
            "new_path": {
                "type": "string",
                "description": "Destination path (same addressing; must not already exist).",
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent"],
                "description": "Address-space selector, same semantics as WriteFile.",
            },
            "authored_by": {
                "type": "string",
                "description": "ADR-209 attribution. Defaults to the caller identity from auth.",
            },
            "message": {
                "type": "string",
                "description": "Why this file is moving (recorded on both revisions; optional).",
            },
        },
        "required": ["path", "new_path"],
    },
}


SEARCH_FILES_TOOL = {
    "name": "SearchFiles",
    "description": """Search the workspace filesystem for content (file layer).

This is a FILE LAYER primitive — it searches filesystem content. For semantic
search over accumulated context domains, use QueryKnowledge. For entity search
by database table, use SearchEntities.

Two match modes (ADR-337 D4):
- match='semantic' (default) — BM25 full-text relevance ranking.
- match='exact' — case-insensitive substring match over content and path
  (the grep shape). Use when hunting a literal string: a path fragment, a
  config key, an exact phrase.
  SearchFiles(query='operation/portfolio', match='exact')
  IMPORTANT: exact matches ONE literal substring — a multi-word query matches
  only that exact phrase, not the individual terms. To hunt several terms,
  issue one call per term (independent calls can be batched in a single turn).

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
                "description": "Search query (semantic terms, or the literal string when match='exact').",
            },
            "match": {
                "type": "string",
                "enum": ["semantic", "exact"],
                "description": "Match mode: 'semantic' (default, BM25 ranked) or 'exact' (case-insensitive literal substring over content + path).",
            },
            "scope": {
                "type": "string",
                "enum": ["workspace", "agent"],
                "description": "Search scope. 'workspace' (default for chat) searches operator-shared substrate. 'agent' (default for headless agents) searches the calling agent's workspace.",
            },
            "path_prefix": {
                "type": "string",
                "description": "Optional: limit search to a subdirectory (e.g., 'reports/', 'operation/', 'working/').",
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
Do not assume a fixed set of domains; use ListFiles on /workspace/operation/ to discover what exists.

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
    "description": """List the workspace filesystem as a tree with metadata (file layer, path-based).

ONE call returns the FULL subtree under `path` — every file recursively, each
with metadata:
  path        — relative path, directly usable as the `path` argument of
                ReadFile / EditFile / DeleteFile / MoveFile in the same scope
  bytes       — content size (0 = empty file; empty files are usually litter)
  updated_at  — last mutation time
  authored_by — head-revision author (operator / yarnnn:* / agent:* /
                reviewer:* / system:*)

Do NOT walk directories level by level — one ListFiles call per subtree is
enough. ListFiles(scope='workspace') with no path is the whole working tree
(the `git status`-shaped view: what exists, how big, who last touched it).

This is a FILE LAYER primitive — it enumerates paths in the workspace
filesystem. For entity listing by database table, use ListEntities.

Two scopes (ADR-235 Option A):

**scope='workspace'** (chat default) — operator-shared substrate.
  ListFiles(scope='workspace')                            # full working tree
  ListFiles(scope='workspace', path='operation/reports/') # one subtree

**scope='agent'** (headless default) — the calling agent's workspace.
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
                "description": "Optional: subdirectory to list. For scope='workspace' use workspace-relative (e.g. 'operation/', 'reports/', 'system/'). For scope='agent' relative to the agent's workspace.",
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
    Writes to the consuming agent's system/references.json.
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
        existing = await ws.read("system/references.json")
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
            "system/references.json",
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
        # Normalize path: UserMemory.read() expects a workspace-relative path
        # (e.g. "constitution/MANDATE.md") and prepends "/workspace/" itself.
        # The model sometimes passes the full absolute path ("/workspace/context/...")
        # or the path with a leading "workspace/" — strip both so we don't get
        # /workspace/workspace/... double-prefix.
        if path.startswith("/workspace/"):
            path = path[len("/workspace/"):]
        elif path.startswith("workspace/"):
            path = path[len("workspace/"):]

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


def _resolve_gate_paths(name: str, input: dict) -> list[str]:
    """ADR-337: every workspace-relative path a path-addressed verb targets.

    WriteFile / EditFile / DeleteFile address one path; MoveFile addresses
    two (source + destination) — a move into or out of a governance-locked
    subtree must DENY just like a write would.
    """
    keys = ("path", "new_path") if name == "MoveFile" else ("path",)
    paths: list[str] = []
    for key in keys:
        candidate = _resolve_workspace_path_for_gate({**input, "path": input.get(key, "")})
        if candidate:
            paths.append(candidate)
    return paths


def _resolve_workspace_path_for_gate(input: dict) -> Optional[str]:
    """ADR-307: normalize a WriteFile input to its workspace-relative path for
    the permission gate, or None when the write is not an operator-shared
    workspace-scope write (agent/context scope → not autonomy-gated here).

    Mirrors the scope + path normalization in handle_write_file so the gate
    (at execute_primitive) and the handler agree on the path. Single source of
    truth for "which path does this write target."
    """
    scope = input.get("scope")
    # Default scope inference needs the auth; the gate only owns workspace-scope
    # Reviewer writes, and the Reviewer always passes scope explicitly or
    # defaults to workspace (no agent attached). Treat absent scope as workspace.
    if scope not in (None, "workspace"):
        return None
    path = input.get("path", "") or ""
    if not path:
        return None
    if path.startswith("/workspace/"):
        path = path[len("/workspace/"):]
    elif path.startswith("workspace/"):
        path = path[len("workspace/"):]
    return path


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
      system/notes.md                       → memory_written
      agents/{slug}/memory/feedback.md      → agent_feedback (with agent_slug metadata)

    Other paths (governance declarations, task feedback, awareness, recurrence
    YAMLs, context domain files, agent workspace files) do NOT emit activity
    events — they are recorded only via the Authored Substrate revision chain.
    """
    if rel_path == "system/notes.md":
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

    Two scopes (ADR-321 — address-space selector; the path's root is the address):
      - 'workspace' (default for chat): writes workspace-relative paths via UserMemory
        across the five roots (governance/constitution/persona/operation/system).
        Accumulated domain context is path-native under operation/{domain}/ — there
        is no separate 'context' scope (ADR-321 deleted it). Recognized canonical
        paths (system/notes.md, agents/{slug}/memory/feedback.md) emit activity-log
        events automatically (ADR-235 D1.b).
      - 'agent' (default when agent context present): writes to the calling agent's workspace.

    ADR-321: embedding is no longer a write side-effect — it is the explicit Embed
    primitive (ADR-325). UserMemory.write → write_revision is content-hash-deduped
    (no-op writes create no revision per ADR-209).
    """
    path = input.get("path", "")
    content = input.get("content", "")
    mode = input.get("mode", "overwrite")
    scope = input.get("scope") or _default_file_scope(auth)
    authored_by = input.get("authored_by")
    message = input.get("message")

    # Empty-content guard (2026-06-11): a missing `content` key silently
    # defaulted to "" and overwrote real substrate with 0-byte files — the
    # observed failure mode when an LLM caller's tool input arrives truncated
    # (max_tokens cut mid-JSON drops `content`, keeps `path`). There is no
    # legitimate LLM write of an empty file: clearing a file is expressed by
    # writing a stub note, and placeholder seeding is system-side (UserMemory
    # direct). Defense-in-depth pair to the reviewer-loop truncation guard.
    if not content.strip():
        return {
            "success": False,
            "error": "empty_content_blocked",
            "message": (
                f"WriteFile requires non-empty content — refusing a 0-byte write to "
                f"'{path or '(missing path)'}'. If your previous attempt was truncated, "
                "re-issue the write in smaller parts using mode='append'."
            ),
        }

    if scope == "workspace":
        # ADR-235 Option A: workspace-relative paths via UserMemory. Reaches
        # operator-shared substrate (context/, memory/, review/, reports/, ...).
        # Recognized canonical paths emit activity-log events on write.
        from services.workspace import UserMemory

        if not path:
            return {"success": False, "error": "missing_path", "message": "path is required"}

        # Normalize path: strip absolute /workspace/ prefix if model passed
        # the absolute form (cockpit-awareness shows absolute paths so the
        # model echoes them). UserMemory.write() prepends /workspace/ itself.
        if path.startswith("/workspace/"):
            path = path[len("/workspace/"):]
        elif path.startswith("workspace/"):
            path = path[len("workspace/"):]

        # ADR-307: the permission gate moved UP to execute_primitive (the
        # single uniform chokepoint). A Reviewer substrate write under
        # bounded/manual is enqueued as a family='substrate' proposal by the
        # gate BEFORE this handler runs; a governance-locked path is DENY'd
        # there. By the time handle_write_file executes, the write is
        # authorized (autonomous, or operator-approved on proposal replay).
        # No inline gate here — the handler is the pure execution arm
        # (Claude-Code shape: tools don't gate themselves).
        um = UserMemory(auth.client, auth.user_id)

        if mode == "append":
            existing = await um.read(path) or ""
            new_content = existing + ("\n" if existing else "") + content
        else:
            new_content = content

        # ADR-288 D2: default authored_by from the auth's caller_identity.
        # Every auth-construction site (yarnnn.py operator-chat, reviewer_agent
        # wake, HeadlessAuth specialist dispatch, _MechanicalAuth recurrence,
        # MCP boundary) sets caller_identity per the ADR-209 taxonomy. LLM-
        # supplied authored_by still wins when explicitly passed. The
        # "system:unknown" fall-through is a telemetry tripwire — emitting it
        # means an auth-construction site forgot to set caller_identity.
        caller = getattr(auth, "caller_identity", None) or "system:unknown"
        if caller == "system:unknown":
            logger.warning(
                "[WRITEFILE] auth.caller_identity missing — attributing as 'system:unknown'. "
                "Auth construction site needs to set caller_identity per ADR-288 D1."
            )
        resolved_author = authored_by or caller
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

    # ADR-321: scope='context' DELETED. Domains live under operation/{domain}/
    # (re-rooted from context/ in directory_registry.py). Writes to a domain are
    # now path-native: WriteFile(scope='workspace', path='operation/{domain}/...').
    # The path's top-level root IS the address (the ADR-320 gate reads it); no
    # `domain` param, no get_domain_folder() indirection, no separate scope.
    # Embedding is no longer a write side-effect — it is the explicit Embed
    # primitive (ADR-325). The content-hash dedup is preserved in the
    # 'workspace' branch's UserMemory.write → write_revision path (no-op writes
    # don't create revisions per ADR-209).

    # scope == "agent"
    from services.workspace import AgentWorkspace, get_agent_slug

    agent = getattr(auth, "agent", None)
    if not agent:
        return {
            "success": False,
            "error": "no_agent_context",
            "message": "WriteFile scope='agent' requires agent context. Use scope='workspace' for operator-shared paths (including operation/{domain}/ for accumulated domain context).",
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


# =============================================================================
# ADR-337 — working-tree verbs (EditFile / DeleteFile / MoveFile)
# =============================================================================


def _exact_snippet(content: str, query: str, radius: int = 120) -> str:
    """Snippet around the first case-insensitive occurrence of query."""
    idx = content.lower().find(query.lower())
    if idx < 0:
        return content[:radius]
    start = max(0, idx - radius // 2)
    end = min(len(content), idx + len(query) + radius // 2)
    return ("…" if start > 0 else "") + content[start:end] + ("…" if end < len(content) else "")


def _exact_search(auth: Any, query: str, prefix: str) -> dict:
    """ADR-337 D4 — case-insensitive literal substring search (grep shape).

    Matches content OR path. Returns paths + a snippet around the first
    content occurrence. Read-only; no ranking — deterministic results.
    """
    if not query:
        return {"success": False, "error": "missing_query", "message": "query is required"}
    escaped = query.replace("%", r"\%").replace("_", r"\_")
    try:
        rows = (
            auth.client.table("workspace_files")
            .select("path, content")
            .eq("user_id", auth.user_id)
            .like("path", f"{prefix}/%")
            .or_(f"content.ilike.%{escaped}%,path.ilike.%{escaped}%")
            .limit(40)
            .execute()
        ).data or []
    except Exception as e:
        logger.warning(f"[SEARCH_FILES] exact search failed: {e}")
        rows = []
    out = {
        "success": True,
        "match": "exact",
        "semantics": "case-insensitive literal substring over content and path",
        "query": query,
        "path_prefix": prefix,
        "count": len(rows),
        "results": [
            {
                "path": r["path"],
                "snippet": _exact_snippet(r.get("content") or "", query),
            }
            for r in rows
        ],
    }
    # ADR-339 D2 — zero-yield legibility: a silent count:0 on a multi-word
    # query reads as "nothing exists" when the real cause is phrase-too-
    # specific (receipts: 3 live conflict-backup files hidden behind a
    # 5-word literal phrase, wake-round-economics-audit-2026-06-12).
    if not rows:
        out["message"] = (
            f"No matches for the LITERAL substring '{query}'. Multi-word "
            "queries only match as exact phrases — to hunt several terms, "
            "issue one call per term (independent calls can be batched in a "
            "single turn), or use match='semantic'."
        )
    return out


def _normalize_workspace_rel(path: str) -> str:
    """Strip absolute /workspace/ prefixes the model may echo from
    cockpit-awareness (same normalization as handle_write_file)."""
    if path.startswith("/workspace/"):
        return path[len("/workspace/"):]
    if path.startswith("workspace/"):
        return path[len("workspace/"):]
    return path


def _apply_edit(
    content: str, old_string: str, new_string: str, replace_all: bool
) -> tuple[Optional[str], Optional[dict]]:
    """Pure edit application (ADR-337 D1 — the Claude Code Edit contract).

    Returns (new_content, None) on success or (None, error_dict) on failure.
    Errors mirror the contract the model's trained prior expects:
    old_string_not_found / old_string_not_unique / no_change.
    """
    if not old_string:
        return None, {"success": False, "error": "missing_old_string",
                      "message": "old_string is required and must be non-empty."}
    if old_string == new_string:
        return None, {"success": False, "error": "no_change",
                      "message": "old_string and new_string are identical — nothing to do."}
    count = content.count(old_string)
    if count == 0:
        return None, {"success": False, "error": "old_string_not_found",
                      "message": "old_string was not found in the file. It must match the current content exactly, including whitespace."}
    if count > 1 and not replace_all:
        return None, {"success": False, "error": "old_string_not_unique",
                      "message": f"old_string appears {count} times. Include more surrounding context to make it unique, or pass replace_all=true."}
    if replace_all:
        return content.replace(old_string, new_string), None
    return content.replace(old_string, new_string, 1), None


def _resolved_author_and_message(auth: Any, input: dict, default_message: str) -> tuple[str, str]:
    """ADR-288 D2 attribution resolution shared by the ADR-337 verbs —
    identical semantics to handle_write_file."""
    caller = getattr(auth, "caller_identity", None) or "system:unknown"
    if caller == "system:unknown":
        logger.warning(
            "[FILE_VERBS] auth.caller_identity missing — attributing as 'system:unknown'. "
            "Auth construction site needs to set caller_identity per ADR-288 D1."
        )
    resolved_author = input.get("authored_by") or caller
    resolved_message = input.get("message") or default_message
    return resolved_author, resolved_message


async def handle_edit_file(auth: Any, input: dict) -> dict:
    """Handle EditFile primitive (ADR-337 D1) — surgical string replacement.

    The replacement contract is Claude Code's Edit shape (borrowed model
    prior); the write lands through the same Authored Substrate path as
    WriteFile (one attributed revision). An edit may not empty the file —
    that intent belongs to DeleteFile.
    """
    from services.workspace import AgentWorkspace, UserMemory, get_agent_slug

    path = input.get("path", "")
    old_string = input.get("old_string", "")
    new_string = input.get("new_string", "")
    replace_all = bool(input.get("replace_all", False))
    scope = input.get("scope") or _default_file_scope(auth)

    if not path:
        return {"success": False, "error": "missing_path", "message": "path is required"}

    if scope == "workspace":
        path = _normalize_workspace_rel(path)
        um = UserMemory(auth.client, auth.user_id)
        existing = await um.read(path)
        if existing is None:
            return {"success": False, "error": "file_not_found",
                    "message": f"No file at /workspace/{path}. EditFile requires an existing file — use WriteFile to create one."}

        new_content, err = _apply_edit(existing, old_string, new_string, replace_all)
        if err:
            return err
        if not new_content.strip():
            return {"success": False, "error": "empty_content_blocked",
                    "message": "This edit would empty the file. Removing a file is DeleteFile, by intent — not an edit side-effect."}

        resolved_author, resolved_message = _resolved_author_and_message(
            auth, input, f"EditFile workspace {path}"
        )
        ok = await um.write(
            path, new_content,
            summary=f"Workspace edit: {path}",
            authored_by=resolved_author, message=resolved_message,
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"Failed to write: /workspace/{path}"}
        await _emit_workspace_activity(auth, path, new_content)
        return {"success": True, "scope": "workspace", "path": f"/workspace/{path}",
                "replacements": (existing.count(old_string) if replace_all else 1)}

    # scope == "agent"
    agent = getattr(auth, "agent", None)
    if not agent:
        return {"success": False, "error": "no_agent_context",
                "message": "EditFile scope='agent' requires agent context. Use scope='workspace' for operator-shared paths."}
    ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(agent))
    existing = await ws.read(path)
    if existing is None:
        return {"success": False, "error": "file_not_found", "message": f"No file at {path}."}
    new_content, err = _apply_edit(existing, old_string, new_string, replace_all)
    if err:
        return err
    if not new_content.strip():
        return {"success": False, "error": "empty_content_blocked",
                "message": "This edit would empty the file. Removing a file is DeleteFile, by intent."}
    ok = await ws.write(path, new_content)
    if not ok:
        return {"success": False, "error": "write_failed", "message": f"Failed to write: {path}"}
    return {"success": True, "scope": "agent", "path": path,
            "replacements": (existing.count(old_string) if replace_all else 1)}


async def handle_delete_file(auth: Any, input: dict) -> dict:
    """Handle DeleteFile primitive (ADR-337 D2) — remove from the live view.

    Attributed tombstone revision + live-row removal via
    authored_substrate.delete_live_file. The revision chain (including the
    tombstone) is retained; restore is ReadRevision + WriteFile (ADR-209 D7).
    """
    from services.authored_substrate import delete_live_file
    from services.workspace import get_agent_slug

    path = input.get("path", "")
    scope = input.get("scope") or _default_file_scope(auth)
    if not path:
        return {"success": False, "error": "missing_path", "message": "path is required"}

    if scope == "workspace":
        rel = _normalize_workspace_rel(path)
        abs_path = f"/workspace/{rel}"
    else:
        agent = getattr(auth, "agent", None)
        if not agent:
            return {"success": False, "error": "no_agent_context",
                    "message": "DeleteFile scope='agent' requires agent context."}
        abs_path = f"/agents/{get_agent_slug(agent)}/{path}"

    resolved_author, resolved_message = _resolved_author_and_message(
        auth, input, f"DeleteFile {abs_path}"
    )
    if not resolved_message.startswith("DeleteFile"):
        resolved_message = f"DeleteFile: {resolved_message}"

    tombstone_id = delete_live_file(
        auth.client,
        user_id=auth.user_id,
        path=abs_path,
        authored_by=resolved_author,
        message=resolved_message,
    )
    if tombstone_id is None:
        return {"success": False, "error": "file_not_found",
                "message": f"No live file at {abs_path}."}
    return {"success": True, "scope": scope, "path": abs_path,
            "tombstone_revision_id": tombstone_id,
            "note": "Revision chain retained — restore via ReadRevision + WriteFile."}


async def handle_move_file(auth: Any, input: dict) -> dict:
    """Handle MoveFile primitive (ADR-337 D3) — relocation as one attributed op.

    Revision at new_path with current content, then tombstone + live-row
    removal at the old path. Refuses to overwrite an existing destination.
    """
    from services.authored_substrate import delete_live_file
    from services.workspace import UserMemory, get_agent_slug

    path = input.get("path", "")
    new_path = input.get("new_path", "")
    scope = input.get("scope") or _default_file_scope(auth)
    if not path or not new_path:
        return {"success": False, "error": "missing_path", "message": "path and new_path are required"}

    if scope == "workspace":
        rel_src = _normalize_workspace_rel(path)
        rel_dst = _normalize_workspace_rel(new_path)
        abs_src = f"/workspace/{rel_src}"
        abs_dst = f"/workspace/{rel_dst}"
    else:
        agent = getattr(auth, "agent", None)
        if not agent:
            return {"success": False, "error": "no_agent_context",
                    "message": "MoveFile scope='agent' requires agent context."}
        slug = get_agent_slug(agent)
        abs_src = f"/agents/{slug}/{path}"
        abs_dst = f"/agents/{slug}/{new_path}"

    if abs_src == abs_dst:
        return {"success": False, "error": "no_change", "message": "path and new_path are identical."}

    rows = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", auth.user_id)
        .in_("path", [abs_src, abs_dst])
        .execute()
    ).data or []
    by_path = {r["path"]: r for r in rows}
    if abs_src not in by_path:
        return {"success": False, "error": "file_not_found", "message": f"No live file at {abs_src}."}
    if abs_dst in by_path:
        return {"success": False, "error": "destination_exists",
                "message": f"{abs_dst} already exists. DeleteFile it first if replacement is intended."}

    content = by_path[abs_src].get("content") or ""
    resolved_author, base_message = _resolved_author_and_message(
        auth, input, f"move {abs_src} -> {abs_dst}"
    )

    # Step 1 — revision at destination. Route through UserMemory.write so
    # workspace-scope moves keep activity/lifecycle semantics; agent scope
    # writes through the same authored-substrate path via absolute write.
    from services.authored_substrate import write_revision
    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=abs_dst,
        content=content,
        authored_by=resolved_author,
        message=f"MoveFile: from {abs_src} — {base_message}",
        summary=f"Moved from {abs_src}",
    )

    # Step 2 — tombstone + live-row removal at the source.
    delete_live_file(
        auth.client,
        user_id=auth.user_id,
        path=abs_src,
        authored_by=resolved_author,
        message=f"MoveFile: to {abs_dst} — {base_message}",
    )

    return {"success": True, "scope": scope, "path": abs_src, "new_path": abs_dst}


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
    match = input.get("match") or "semantic"

    # ADR-337 D4 — exact mode: case-insensitive literal substring over
    # content + path (the grep shape). Read-only; works for both scopes by
    # prefix selection.
    if match == "exact":
        if scope == "workspace":
            prefix = "/workspace"
            if path_prefix:
                prefix = path_prefix if path_prefix.startswith("/") else f"/workspace/{path_prefix.lstrip('/')}"
        else:
            agent = getattr(auth, "agent", None)
            if not agent:
                return {"success": False, "error": "no_agent_context",
                        "message": "SearchFiles scope='agent' requires agent context."}
            prefix = f"/agents/{get_agent_slug(agent)}"
        return _exact_search(auth, query, prefix)

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
    """Handle QueryKnowledge primitive — searches /workspace/operation/ accumulated domains.

    ADR-151 + ADR-174 Phase 2: Semantic search as primary path, BM25 as fallback.
    - Primary: vector cosine similarity via search_workspace_semantic RPC (requires embedding)
    - Fallback: BM25 full-text via search_workspace RPC (always available)

    ADR-321: domain filter resolves to any path under /workspace/operation/{domain}/,
    including user-created domains not in the registry (re-rooted from context/).
    """
    query = input.get("query") or ""
    domain = input.get("content_class") or input.get("domain")  # content_class kept for backwards compat
    limit = min(input.get("limit", 10), 30)

    # Resolve path prefix — registry for known domains, direct path for unknown.
    # ADR-321: domains live under operation/{domain}/ (re-rooted from context/).
    prefix = "/workspace/operation/"
    if domain:
        from services.directory_registry import get_domain_folder
        domain_folder = get_domain_folder(domain) or f"operation/{domain}"
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


_LIST_FILES_MAX = 500


def _parse_iso_ts(value: str):
    """Parse an ISO-8601 timestamp tolerantly (Z suffix, missing tz)."""
    from datetime import datetime, timezone

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _list_tree(
    auth: Any,
    abs_prefix: str,
    rel_base: str,
    authored_by: str,
    since: str,
    until: str,
) -> tuple[list[dict], bool]:
    """ADR-339 D1 — one-call recursive listing with metadata.

    Returns (entries, truncated). Each entry carries `path` (relative to
    rel_base — directly usable as the `path` argument of ReadFile / EditFile /
    DeleteFile / MoveFile in the same scope), `bytes` (content size; 0 = empty
    file), `updated_at`, and `authored_by` (head revision author).

    The ADR-209 Phase 3 filters apply to the HEAD revision — the documented
    "most-recent revision" semantics (the pre-ADR-339 implementation matched
    ANY revision in the window; that drift dies here).
    """
    try:
        rows = (
            auth.client.table("workspace_files")
            .select(
                "path, content_bytes, updated_at, "
                "workspace_file_versions!head_version_id(authored_by, created_at)"
            )
            .eq("user_id", auth.user_id)
            .like("path", f"{abs_prefix}%")
            .in_("lifecycle", ["active", "delivered"])
            .order("path")
            .limit(_LIST_FILES_MAX + 1)
            .execute()
        ).data or []
    except Exception as e:
        logger.warning(f"[LIST_FILES] tree query failed: {e}")
        rows = []

    truncated = len(rows) > _LIST_FILES_MAX
    since_dt = _parse_iso_ts(since) if since else None
    until_dt = _parse_iso_ts(until) if until else None

    entries: list[dict] = []
    for r in rows[:_LIST_FILES_MAX]:
        head = r.get("workspace_file_versions") or {}
        head_author = head.get("authored_by") or ""
        head_at = head.get("created_at") or r.get("updated_at") or ""
        if authored_by and not head_author.startswith(authored_by):
            continue
        if since_dt or until_dt:
            head_dt = _parse_iso_ts(head_at) if head_at else None
            if head_dt is None:
                continue
            if since_dt and head_dt < since_dt:
                continue
            if until_dt and head_dt > until_dt:
                continue
        p = r["path"]
        entries.append({
            "path": p[len(rel_base):] if p.startswith(rel_base) else p,
            "bytes": r.get("content_bytes"),
            "updated_at": r.get("updated_at"),
            "authored_by": head_author or None,
        })
    return entries, truncated


async def handle_list_files(auth: Any, input: dict) -> dict:
    """Handle ListFiles primitive (ADR-168 rename; ADR-235 scopes; ADR-339 D1).

    ADR-339 D1: recursive listing with metadata — ONE call returns the full
    subtree under `path` with bytes / updated_at / head authored_by. The
    one-level names-only projection (and the drill-down walk it forced —
    receipts in docs/analysis/wake-round-economics-audit-2026-06-12.md) is
    deleted.

    Two scopes:
      - 'workspace' (default for chat): operator-shared substrate. Returned
        paths are workspace-relative from the root regardless of the `path`
        filter passed.
      - 'agent' (default when agent context present): the calling agent's
        workspace. Returned paths are relative to the agent root.

    ADR-209 Phase 3 filters (authored_by / since / until) apply to each
    file's head revision.
    """
    from services.workspace import get_agent_slug

    path = input.get("path", "")
    scope = input.get("scope") or _default_file_scope(auth)
    authored_by = (input.get("authored_by") or "").strip()
    since = (input.get("since") or "").strip()
    until = (input.get("until") or "").strip()

    if scope == "workspace":
        # Tolerate callers passing absolute paths (e.g. '/workspace/operation/').
        rel_base = "/workspace/"
        sub = (path or "").strip().lstrip("/")
        if sub.startswith("workspace/"):
            sub = sub[len("workspace/"):]
        if sub and not sub.endswith("/"):
            sub += "/"
        abs_prefix = f"/workspace/{sub}" if sub else "/workspace/"
    else:
        agent = getattr(auth, "agent", None)
        if not agent:
            return {
                "success": False,
                "error": "no_agent_context",
                "message": "ListFiles scope='agent' requires agent context. Use scope='workspace' for operator-shared paths.",
            }
        rel_base = f"/agents/{get_agent_slug(agent)}/"
        sub = (path or "").strip().lstrip("/")
        if sub and not sub.endswith("/"):
            sub += "/"
        abs_prefix = rel_base + sub

    entries, truncated = _list_tree(auth, abs_prefix, rel_base, authored_by, since, until)

    result = {
        "success": True,
        "scope": scope,
        "path": abs_prefix,
        "files": entries,
        "count": len(entries),
        "filters_applied": {
            "authored_by": authored_by or None,
            "since": since or None,
            "until": until or None,
        } if (authored_by or since or until) else None,
    }
    if truncated:
        result["truncated"] = True
        result["message"] = (
            f"Listing capped at {_LIST_FILES_MAX} entries — pass a narrower "
            "`path` prefix to see the rest."
        )
    return result


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
            files = await ws.list("system/")
            for f in files:
                # f is a path string like "system/observations.md"
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


# ---------------------------------------------------------------------------
# ADR-258 D3 + D9: operator-authored access policy enforcement
# ---------------------------------------------------------------------------

def _caller_class(auth: Any) -> str:
    """Resolve the caller-class key for the permission topology (ADR-320).

    Maps the auth's caller_identity / reviewer_caller flag to one of the
    CALLER_WRITE_POLICY keys: operator | reviewer | mcp | agent | system.
    """
    caller_identity = getattr(auth, "caller_identity", "") or ""
    if caller_identity == "yarnnn:mcp":
        return "mcp"
    if getattr(auth, "reviewer_caller", False) or caller_identity.startswith("reviewer:"):
        return "reviewer"
    if caller_identity == "operator" or caller_identity.startswith("operator"):
        return "operator"
    if caller_identity.startswith("agent:") or caller_identity.startswith("specialist:"):
        return "agent"
    if caller_identity.startswith("system:"):
        return "system"
    # Default: treat unknown LLM callers as agent-class (least-trust non-mcp).
    return "agent"


def _is_path_locked(caller_class: str, path: str) -> bool:
    """`access(2)` for the agent OS — the SINGULAR write-lock (ADR-320 D3).

    Topology IS the permission policy: a caller is locked from writing `path`
    iff `path`'s top-level root is in that caller-class's locked prefix set
    (CALLER_WRITE_POLICY). No filename appears — permission derives from
    (caller_class, root) alone. This replaces the pre-ADR-320 pair
    (_is_path_locked_for_reviewer flat-list + _is_path_locked_for_mcp prefix);
    one function, one source (workspace_paths.CALLER_WRITE_POLICY), one
    mechanism. The five roots: governance/ constitution/ persona/ operation/
    system/ (FOUNDATIONS Derived Principle 25).

    Note (ADR-364): persona/ has NO cross-class write. The pre-ADR-364
    exception — the reconciler (system:outcome-reconciliation) writing
    persona/calibration.md — is retired: calibration.md is superseded by
    persona/reflection.md, which is Reviewer-authored (from the envelope
    gap-fact), not system-written. So the prefix rule is exact for persona/:
    only the reviewer (+ operator) writes it; no named-path hole remains.
    """
    from services.workspace_paths import CALLER_WRITE_POLICY

    candidate = path.strip().lstrip("/")
    if candidate.startswith("workspace/"):
        candidate = candidate[len("workspace/"):]

    locked_prefixes = CALLER_WRITE_POLICY.get(caller_class, ())
    return any(candidate.startswith(prefix) for prefix in locked_prefixes)
