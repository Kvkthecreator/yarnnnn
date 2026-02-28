"""
Search Primitive (ADR-072 Unified Content Layer)

Find entities by content using text or semantic search.

Usage:
  Search(query="database migration", scope="platform_content")
  Search(query="weekly report", scope="deliverable")

ADR-072: scope="platform_content" searches the unified content layer with
semantic search (pgvector) when available, falling back to full-text search.
Supports both retained (permanent) and ephemeral (TTL) content.

scope="memory" is NOT a valid search scope. Memory is injected into the
TP system prompt at session start via working memory. TP already has it.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from .refs import TABLE_MAP


SEARCH_TOOL = {
    "name": "Search",
    "description": """Find entities by content using text search. Returns refs for use with Read.

IMPORTANT — platform content access (ADR-085):
1. Search(scope="platform_content") is the primary way to query synced platform data
2. If results are stale or empty, use RefreshPlatformContent(platform="...") to sync latest (~10-30s)
3. Then re-query with Search — content will be fresh
4. When using results, disclose the synced_at age to the user

Examples:
- Search(query="Q2 planning discussion", scope="platform_content") - search synced Slack/Gmail/Notion/Calendar
- Search(query="weekly status", scope="deliverable") - search deliverables
- Search(query="competitor analysis", scope="document") - search uploaded documents
- Search(query="competitor analysis") - search all scopes (excludes memory — already in working memory)

Results include a `ref` field (e.g., "document:abc123-uuid"). Use this ref with Read() to get full content.

Workflow for documents:
1. Search(query="topic", scope="document") → returns matches with `ref` and snippet
2. Read(ref="document:<UUID>") → returns full document content

Scopes:
- platform_content: Synced platform data (Slack, Gmail, Notion, Calendar). May be hours old — disclose age. Use RefreshPlatformContent to get latest.
- document: Uploaded documents (PDF, DOCX, TXT, MD) - searches actual content, not just filenames
- deliverable: Your recurring deliverables
- work: Work tickets
- all: Search everything (platform_content + document + deliverable + work)

Note: Memory is NOT a search scope — it is already in your working memory context at session start.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (natural language)"
            },
            "scope": {
                "type": "string",
                "enum": ["platform_content", "document", "deliverable", "work", "all"],
                "description": "What to search. Default: 'all'. Note: memory is not a scope — it is already in your working memory context."
            },
            "platform": {
                "type": "string",
                "enum": ["slack", "gmail", "notion", "calendar"],
                "description": "Filter platform_content by platform (optional)"
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
    "platform_content": ["content"],
    "deliverable": ["title", "description"],
    "document": ["filename"],  # documents table uses 'filename' not 'name'
    "work": ["task"],
    "memory": ["content"],  # ADR-038: User-stated facts only
}


async def handle_search(auth: Any, input: dict) -> dict:
    """
    Handle Search primitive.

    Args:
        auth: Auth context with user_id and client
        input: {"query": "...", "scope": "...", "platform": "...", "limit": N}

    Returns:
        {"success": True, "results": [...], "count": N}
        or {"success": False, "error": "...", "message": "..."}
    """
    query = input.get("query", "").strip()
    scope = input.get("scope", "all")
    platform_filter = input.get("platform")
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
                "To search platform content use scope='platform_content' (cache fallback) or "
                "use live platform tools (platform_slack_*, platform_gmail_*, etc.) for current data."
            ),
        }

    try:
        # Determine scopes to search
        # ADR-065: 'all' excludes memory (already in working memory prompt)
        if scope == "all":
            scopes = ["platform_content", "document", "deliverable", "work"]
        else:
            scopes = [scope]

        all_results = []

        for entity_scope in scopes:
            if entity_scope == "platform_content":
                results = await _search_platform_content(
                    auth, query, platform_filter, limit
                )
            elif entity_scope == "memory":
                results = await _search_user_memories(auth, query, limit)
            elif entity_scope == "document":
                # Documents need special handling - search chunks for content
                results = await _search_document_content(auth, query, limit)
            else:
                results = await _search_entity(auth, query, entity_scope, limit)
            all_results.extend(results)

        # Sort by recency for platform_content, then others
        # Platform content has source_timestamp; entities have created_at
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


async def _search_platform_content(
    auth: Any,
    query: str,
    platform_filter: Optional[str],
    limit: int,
) -> list[dict]:
    """
    Search platform_content table for platform content.

    ADR-072: Unified content layer with retention. Searches both retained
    (permanent) and ephemeral (TTL) content that hasn't expired.
    """
    try:
        # Build query on platform_content (ADR-072 unified content layer)
        now = datetime.now(timezone.utc).isoformat()
        q = auth.client.table("platform_content").select(
            "id, platform, resource_id, resource_name, content, content_type, "
            "metadata, source_timestamp, fetched_at, retained, expires_at"
        ).eq(
            "user_id", auth.user_id
        ).or_(
            f"retained.eq.true,expires_at.gt.{now}"  # Include retained OR non-expired
        ).ilike(
            "content", f"%{query}%"
        )

        # Optional platform filter
        if platform_filter:
            q = q.eq("platform", platform_filter)

        # Order by recency and limit
        result = q.order("fetched_at", desc=True).limit(limit).execute()

        if not result.data:
            return []

        return [
            {
                "entity_type": "platform_content",
                "ref": f"platform_content:{item['id']}",
                "platform": item["platform"],
                "resource_name": item.get("resource_name"),
                "content_type": item.get("content_type"),
                # ADR-072: fetched_at exposed for freshness awareness
                "fetched_at": item.get("fetched_at"),
                "retained": item.get("retained", False),
                "data": {
                    "content": item["content"][:500] + "..." if len(item.get("content", "")) > 500 else item.get("content", ""),
                    "source_timestamp": item.get("source_timestamp"),
                    "metadata": item.get("metadata", {}),
                },
                "score": 0.5,  # Text search doesn't have similarity score
            }
            for item in result.data
        ]

    except Exception as e:
        # Log but don't fail the search
        import logging
        logging.warning(f"[SEARCH] Platform content search failed: {e}")
        return []


async def _search_user_memories(
    auth: Any,
    query: str,
    limit: int,
) -> list[dict]:
    """
    ADR-059: Search user_context table for user knowledge (fact:/instruction:/preference: keys).
    """
    try:
        result = auth.client.table("user_context").select(
            "id, key, value, source, confidence, created_at"
        ).eq(
            "user_id", auth.user_id
        ).or_(
            "key.like.fact:%,key.like.instruction:%,key.like.preference:%"
        ).ilike(
            "value", f"%{query}%"
        ).order(
            "created_at", desc=True
        ).limit(limit).execute()

        if not result.data:
            return []

        return [
            {
                "entity_type": "memory",
                "ref": f"memory:{item['id']}",
                "data": {
                    "content": item["value"],
                    "source": item.get("source"),
                    "entry_type": item["key"].split(":")[0],
                    "importance": item.get("confidence", 1.0),
                },
                "score": 0.5,
            }
            for item in result.data
        ]

    except Exception as e:
        import logging
        logging.warning(f"[SEARCH] Memory search failed: {e}")
        return []


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


async def _search_entity(
    auth: Any,
    query: str,
    entity_type: str,
    limit: int,
) -> list[dict]:
    """Search standard entity tables (deliverable, document, work)."""
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
