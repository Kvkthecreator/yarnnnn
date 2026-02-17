"""
Search Primitive (ADR-038 Phase 2)

Find entities by content using text search.

Usage:
  Search(query="database migration", scope="platform_content")
  Search(query="weekly report", scope="deliverable")

NOTE: 'memory' scope removed per ADR-038. Platform content now lives in
filesystem_items table. Use scope="platform_content" to search imported
Slack/Gmail/Notion content.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from .refs import TABLE_MAP


SEARCH_TOOL = {
    "name": "Search",
    "description": """Find entities by content using text search. Returns refs for use with Read.

Examples:
- Search(query="Q2 planning discussion", scope="platform_content") - search imported Slack/Gmail/Notion
- Search(query="weekly status", scope="deliverable") - search deliverables
- Search(query="prefers bullet points", scope="memory") - search user-stated facts
- Search(query="competitor analysis", scope="document") - search uploaded documents
- Search(query="competitor analysis") - search all scopes

Results include a `ref` field (e.g., "document:abc123-uuid"). Use this ref with Read() to get full content.

Workflow for documents:
1. Search(query="topic", scope="document") → returns matches with `ref` and snippet
2. Read(ref="document:<UUID>") → returns full document content

Scopes:
- platform_content: Imported platform data (Slack messages, Gmail emails, Notion pages)
- memory: User-stated facts and preferences (what the user has told you)
- document: Uploaded documents (PDF, DOCX, TXT, MD) - searches actual content, not just filenames
- deliverable: Your recurring deliverables
- work: Work tickets
- all: Search everything""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (natural language)"
            },
            "scope": {
                "type": "string",
                "enum": ["platform_content", "memory", "document", "deliverable", "work", "all"],
                "description": "What to search. Default: 'all'"
            },
            "platform": {
                "type": "string",
                "enum": ["slack", "gmail", "notion"],
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

    # Handle legacy 'memory' scope - redirect to platform_content
    if scope == "memory":
        scope = "platform_content"

    try:
        # Determine scopes to search
        if scope == "all":
            scopes = ["platform_content", "memory", "document", "deliverable", "work"]
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
    Search filesystem_items table for platform content.

    ADR-038: This replaces the old memory scope. Platform content
    (Slack messages, Gmail emails, Notion pages) lives in filesystem_items.
    """
    try:
        # Build query on filesystem_items
        q = auth.client.table("filesystem_items").select(
            "id, platform, resource_id, resource_name, content, content_type, "
            "metadata, source_timestamp, synced_at, expires_at"
        ).eq(
            "user_id", auth.user_id
        ).gt(
            "expires_at", datetime.now(timezone.utc).isoformat()
        ).ilike(
            "content", f"%{query}%"
        )

        # Optional platform filter
        if platform_filter:
            q = q.eq("platform", platform_filter)

        # Order by recency and limit
        result = q.order("source_timestamp", desc=True).limit(limit).execute()

        if not result.data:
            return []

        return [
            {
                "entity_type": "platform_content",
                "ref": f"platform_content:{item['id']}",  # Use platform_content:uuid format
                "platform": item["platform"],
                "resource_name": item.get("resource_name"),
                "content_type": item.get("content_type"),
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
    Search knowledge_entries table for user knowledge.

    ADR-058: Knowledge entries are user-stated facts, preferences, decisions.
    source IN ('user_stated', 'conversation', 'document', 'inferred')
    """
    try:
        result = auth.client.table("knowledge_entries").select(
            "id, content, tags, importance, source, entry_type, created_at"
        ).eq(
            "user_id", auth.user_id
        ).eq(
            "is_active", True
        ).ilike(
            "content", f"%{query}%"
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
                    "content": item["content"],
                    "tags": item.get("tags", []),
                    "importance": item.get("importance", 0.5),
                    "source": item.get("source"),
                    "entry_type": item.get("entry_type"),
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
