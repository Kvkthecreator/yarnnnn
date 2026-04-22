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
- Task bodies (TASK.md, DELIVERABLE.md) — these are workspace files. Use ReadFile with path /tasks/{slug}/TASK.md instead. The compact index already lists every task by slug; pick the slug, read the file directly.
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
    """
    Search uploaded documents by their content.

    ADR-058: Documents are stored in filesystem_documents, but their
    actual content is chunked and stored in filesystem_chunks for retrieval.
    We search chunks and return the parent document info.
    """
    import logging

    try:
        # First, get user's documents to scope the search
        user_docs_result = auth.client.table("filesystem_documents").select(
            "id"
        ).eq(
            "user_id", auth.user_id
        ).eq(
            "processing_status", "completed"
        ).execute()

        if not user_docs_result.data:
            # No documents, try filename fallback
            return await _search_entity(auth, query, "document", limit)

        user_doc_ids = [doc["id"] for doc in user_docs_result.data]

        # Search document chunks for the query, filtered to user's documents
        chunk_result = auth.client.table("filesystem_chunks").select(
            "id, document_id, content, chunk_index, page_number"
        ).in_(
            "document_id", user_doc_ids
        ).ilike(
            "content", f"%{query}%"
        ).limit(limit * 2).execute()  # Get more chunks to dedupe by document

        if not chunk_result.data:
            # Fallback: search document filenames as well
            return await _search_entity(auth, query, "document", limit)

        # Get unique document IDs from chunks
        matched_doc_ids = list(set(chunk["document_id"] for chunk in chunk_result.data))

        # Fetch the full document info
        doc_result = auth.client.table("filesystem_documents").select(
            "id, filename, file_type, file_size, page_count, word_count, "
            "processing_status, uploaded_at"
        ).eq(
            "user_id", auth.user_id
        ).in_(
            "id", matched_doc_ids
        ).execute()

        if not doc_result.data:
            return []

        # Build results with matched content snippets
        doc_map = {doc["id"]: doc for doc in doc_result.data}
        results = []
        seen_docs = set()

        for chunk in chunk_result.data:
            doc_id = chunk["document_id"]
            if doc_id in seen_docs or doc_id not in doc_map:
                continue
            seen_docs.add(doc_id)

            doc = doc_map[doc_id]
            content_snippet = chunk["content"][:500] + "..." if len(chunk.get("content", "")) > 500 else chunk.get("content", "")

            results.append({
                "entity_type": "document",
                "ref": f"document:{doc_id}",
                "data": {
                    "filename": doc.get("filename"),
                    "file_type": doc.get("file_type"),
                    "page_count": doc.get("page_count"),
                    "word_count": doc.get("word_count"),
                    "matched_content": content_snippet,
                    "matched_page": chunk.get("page_number"),
                },
                "score": 0.5,
            })

            if len(results) >= limit:
                break

        return results

    except Exception as e:
        logging.warning(f"[SEARCH] Document content search failed: {e}")
        # Fallback to filename search
        return await _search_entity(auth, query, "document", limit)


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
