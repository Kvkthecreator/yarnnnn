"""
Search Primitive (ADR-038 Phase 2)

Find entities by content using text search.

Usage:
  Search(query="database migration", scope="platform_content")
  Search(query="weekly report", scope="deliverable")

NOTE: 'memory' scope removed per ADR-038. Platform content now lives in
ephemeral_context table. Use scope="platform_content" to search imported
Slack/Gmail/Notion content.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from .refs import TABLE_MAP


SEARCH_TOOL = {
    "name": "Search",
    "description": """Find entities by content using text search.

Examples:
- Search(query="Q2 planning discussion", scope="platform_content") - search imported Slack/Gmail/Notion
- Search(query="weekly status", scope="deliverable") - search deliverables
- Search(query="competitor analysis") - search all scopes

Scopes:
- platform_content: Imported platform data (Slack messages, Gmail emails, Notion pages)
- deliverable: Your recurring deliverables
- document: Uploaded documents
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
                "enum": ["platform_content", "deliverable", "document", "work", "all"],
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
    "document": ["name", "content"],
    "work": ["task"],
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
            scopes = ["platform_content", "deliverable", "document", "work"]
        else:
            scopes = [scope]

        all_results = []

        for entity_scope in scopes:
            if entity_scope == "platform_content":
                results = await _search_platform_content(
                    auth, query, platform_filter, limit
                )
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
    Search ephemeral_context table for platform content.

    ADR-038: This replaces the old memory scope. Platform content
    (Slack messages, Gmail emails, Notion pages) lives in ephemeral_context.
    """
    try:
        # Build query on ephemeral_context
        q = auth.client.table("ephemeral_context").select(
            "id, platform, resource_id, resource_name, content, content_type, "
            "platform_metadata, source_timestamp, created_at, expires_at"
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
                "ref": f"platform:{item['platform']}:{item['id']}",
                "platform": item["platform"],
                "resource_name": item.get("resource_name"),
                "content_type": item.get("content_type"),
                "data": {
                    "content": item["content"][:500] + "..." if len(item.get("content", "")) > 500 else item.get("content", ""),
                    "source_timestamp": item.get("source_timestamp"),
                    "metadata": item.get("platform_metadata", {}),
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
