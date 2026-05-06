"""
SearchEntities Primitive (ADR-168 Commit 4: renamed from Search)

Find entities by content using text search. Entity layer — operates on the
relational abstraction, NOT on filesystem content.

Distinct from SearchFiles (file layer, workspace-scoped, agent filesystem).
Distinct from QueryKnowledge (semantic-query layer, accumulated context domains).

Usage:
  SearchEntities(query="weekly report", scope="agent")
  SearchEntities(query="competitor analysis", scope="document")

scope="memory" is NOT a valid search scope. Memory is injected into the
TP system prompt at session start via working memory. TP already has it.
"""

from typing import Any, Optional

from .refs import TABLE_MAP


SEARCH_ENTITIES_TOOL = {
    "name": "SearchEntities",
    "description": """Find database-backed entities by content (entity layer). Returns refs for LookupEntity.

Scopes: document (uploaded files), agent, version, all. Memory is not a scope — already in working memory.

DOES NOT SEARCH:
- Work declarations — these are recurrence YAML files at natural-home paths. The compact index lists every recurrence by slug; use ReadFile with the YAML path directly (/workspace/reports/{slug}/_spec.yaml, /workspace/context/{domain}/_recurring.yaml, /workspace/operations/{slug}/_action.yaml, /workspace/_shared/back-office.yaml).
- Context domain files (/workspace/context/**) — use QueryKnowledge for semantic search or ReadFile for a known path.
- AGENT.md, IDENTITY.md, BRAND.md — these are workspace files. Use ReadFile with the known path.

Use SearchEntities ONLY when you need database rows (agent records, uploaded document metadata, agent run history).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (natural language)"
            },
            "scope": {
                "type": "string",
                "enum": ["document", "agent", "version", "all"],
                "description": "What to search. Default: 'all'. Note: memory is not a scope — it is already in your working memory context."
            },
            "agent_id": {
                "type": "string",
                "description": "Filter versions by agent ID (only used with scope='version')"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results. Default: 10"
            }
        },
        "required": ["query"]
    }
}


# Searchable fields per entity type
SEARCH_FIELDS = {
    "agent": ["title", "description"],
    "version": ["content"],  # Agent version content
    "document": ["filename"],  # documents table uses 'filename' not 'name'
}


async def handle_search_entities(auth: Any, input: dict) -> dict:
    """
    Handle SearchEntities primitive (ADR-168: renamed from handle_search).

    Args:
        auth: Auth context with user_id and client
        input: {"query": "...", "scope": "...", "limit": N}

    Returns:
        {"success": True, "results": [...], "count": N}
        or {"success": False, "error": "...", "message": "..."}
    """
    query = input.get("query", "").strip()
    scope = input.get("scope", "all")
    agent_id = input.get("agent_id")
    limit = input.get("limit", 10)

    if not query:
        return {
            "success": False,
            "error": "missing_query",
            "message": "Search query is required",
        }

    # ADR-065: scope="memory" is not a valid search scope.
    # Memory is injected into the TP system prompt at session start (working memory).
    # TP already has this context — searching it mid-conversation is redundant.
    if scope == "memory":
        return {
            "success": False,
            "error": "invalid_scope",
            "message": (
                "scope='memory' is not searchable — memory is already in your working memory "
                "context at session start. Check the 'What you've told me' section of your context. "
                "Use scope='document' for uploaded documents, scope='agent' for agents, "
                "or scope='all' to search everything."
            ),
        }

    try:
        # Determine scopes to search
        # ADR-065: 'all' excludes memory (already in working memory prompt)
        if scope == "all":
            scopes = ["document", "agent"]
        else:
            scopes = [scope]

        all_results = []

        for entity_scope in scopes:
            if entity_scope == "document":
                # Documents need special handling - search chunks for content
                results = await _search_document_content(auth, query, limit)
            elif entity_scope == "version":
                results = await _search_versions(auth, query, agent_id, limit)
            else:
                results = await _search_entity(auth, query, entity_scope, limit)
            all_results.extend(results)

        all_results = all_results[:limit]

        return {
            "success": True,
            "results": all_results,
            "count": len(all_results),
            "query": query,
            "scope": scope,
            "message": f"Found {len(all_results)} result(s) for '{query}'",
        }

    except Exception as e:
        return {
            "success": False,
            "error": "search_failed",
            "message": str(e),
        }


async def _search_document_content(
    auth: Any,
    query: str,
    limit: int,
) -> list[dict]:
    """Search uploaded documents by content (ADR-249).

    Reads /workspace/uploads/*.md workspace files via ilike full-text match
    on content. The file body IS the document — no chunk table needed.
    """
    import logging

    try:
        result = auth.client.table("workspace_files").select(
            "path, content, updated_at"
        ).eq(
            "user_id", auth.user_id
        ).like(
            "path", "/workspace/uploads/%.md"
        ).ilike(
            "content", f"%{query}%"
        ).limit(limit).execute()

        rows = result.data or []
        results = []
        for row in rows:
            path = row["path"]
            raw = row.get("content", "") or ""

            # Parse frontmatter fields
            original_filename = path.rsplit("/", 1)[-1].removesuffix(".md")
            word_count = 0
            for line in raw.split("\n"):
                if line.startswith("original_filename:"):
                    original_filename = line.split(":", 1)[1].strip()
                elif line.startswith("word_count:"):
                    try:
                        word_count = int(line.split(":", 1)[1].strip())
                    except (ValueError, IndexError):
                        pass

            # Extract body snippet (skip frontmatter)
            if raw.startswith("---"):
                parts = raw.split("---", 2)
                body = parts[2].strip() if len(parts) >= 3 else raw
            else:
                body = raw

            # Find query position for a relevant snippet
            idx = body.lower().find(query.lower())
            start = max(0, idx - 100)
            snippet = body[start:start + 400]
            if start > 0:
                snippet = "..." + snippet
            if start + 400 < len(body):
                snippet += "..."

            results.append({
                "entity_type": "document",
                "ref": f"document:{path}",
                "data": {
                    "path": path,
                    "filename": original_filename,
                    "word_count": word_count,
                    "matched_content": snippet,
                    "uploaded_at": (row.get("updated_at") or "")[:10],
                },
                "score": 0.5,
            })

        return results

    except Exception as e:
        logging.warning(f"[SEARCH] Document content search failed: {e}")
        return []


async def _search_versions(
    auth: Any,
    query: str,
    agent_id: Optional[str],
    limit: int,
) -> list[dict]:
    """
    Search agent_runs by content. Scoped through user's agents.
    """
    try:
        # Get user's agent IDs for scoping
        if agent_id:
            check = auth.client.table("agents").select("id").eq(
                "id", agent_id
            ).eq("user_id", auth.user_id).execute()
            if not check.data:
                return []
            agent_ids = [agent_id]
        else:
            user_agents = auth.client.table("agents").select("id").eq(
                "user_id", auth.user_id
            ).execute()
            agent_ids = [d["id"] for d in (user_agents.data or [])]
            if not agent_ids:
                return []

        # Search both draft_content and final_content for matches
        q = auth.client.table("agent_runs").select(
            "id, agent_id, version_number, status, "
            "draft_content, final_content, "
            "created_at, delivery_status"
        ).in_("agent_id", agent_ids).or_(
            f"draft_content.ilike.%{query}%,final_content.ilike.%{query}%"
        ).order("created_at", desc=True).limit(limit)

        result = q.execute()
        if not result.data:
            return []

        items = []
        for item in result.data:
            content = item.get("final_content") or item.get("draft_content") or ""
            items.append({
                "entity_type": "version",
                "ref": f"version:{item['id']}",
                "data": {
                    "agent_id": item["agent_id"],
                    "version_number": item["version_number"],
                    "status": item["status"],
                    "content": content[:500] + "..." if len(content) > 500 else content,
                    "created_at": item["created_at"],
                    "delivery_status": item.get("delivery_status"),
                },
                "score": 0.5,
            })
        return items

    except Exception as e:
        import logging
        logging.warning(f"[SEARCH] Version search failed: {e}")
        return []


async def _search_entity(
    auth: Any,
    query: str,
    entity_type: str,
    limit: int,
) -> list[dict]:
    """Search standard entity tables (agent, document)."""
    table = TABLE_MAP.get(entity_type)
    if not table:
        return []

    fields = SEARCH_FIELDS.get(entity_type, [])
    if not fields:
        return []

    try:
        # Simple ilike search on first searchable field
        field = fields[0]
        result = auth.client.table(table).select("*").eq(
            "user_id", auth.user_id
        ).ilike(field, f"%{query}%").limit(limit).execute()

        if not result.data:
            return []

        return [
            {
                "entity_type": entity_type,
                "ref": f"{entity_type}:{item['id']}",
                "data": item,
                "score": 0.5,  # No score for text search
            }
            for item in result.data
        ]

    except Exception:
        return []
