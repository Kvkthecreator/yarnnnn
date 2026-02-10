"""
Search Primitive

Find entities by content (semantic search).

Usage:
  Search(query="database migration", scope="memory")
  Search(query="weekly report", scope="deliverable")
"""

from typing import Any

from .refs import TABLE_MAP


SEARCH_TOOL = {
    "name": "Search",
    "description": """Find entities by content using semantic search.

Examples:
- Search(query="database migration decisions", scope="memory") - search memories
- Search(query="weekly status", scope="deliverable") - search deliverables
- Search(query="competitor analysis") - search all entity types

Uses embeddings for semantic matching.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (natural language)"
            },
            "scope": {
                "type": "string",
                "enum": ["memory", "deliverable", "document", "work", "all"],
                "description": "Entity type to search. Default: 'all'"
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
    "memory": ["content"],
    "deliverable": ["title", "description"],
    "document": ["name", "content"],
    "work": ["task"],
}


async def handle_search(auth: Any, input: dict) -> dict:
    """
    Handle Search primitive.

    Args:
        auth: Auth context with user_id and client
        input: {"query": "...", "scope": "...", "limit": N}

    Returns:
        {"success": True, "results": [...], "count": N}
        or {"success": False, "error": "...", "message": "..."}
    """
    query = input.get("query", "").strip()
    scope = input.get("scope", "all")
    limit = input.get("limit", 10)

    if not query:
        return {
            "success": False,
            "error": "missing_query",
            "message": "Search query is required",
        }

    try:
        # Get embedding for query
        from services.embeddings import get_embedding

        query_embedding = await get_embedding(query)

        if query_embedding is None:
            # Fallback to text search if embedding fails
            return await _text_search(auth, query, scope, limit)

        # Determine scopes to search
        if scope == "all":
            scopes = ["memory", "deliverable", "document", "work"]
        else:
            scopes = [scope]

        all_results = []

        for entity_scope in scopes:
            results = await _vector_search(
                auth, query_embedding, entity_scope, limit
            )
            all_results.extend(results)

        # Sort by similarity score and limit
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
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


async def _vector_search(
    auth: Any,
    embedding: list[float],
    entity_type: str,
    limit: int,
) -> list[dict]:
    """Perform vector similarity search."""
    # Only memories have embeddings currently
    if entity_type != "memory":
        return []

    try:
        # Use the match_memories RPC function
        result = await auth.client.rpc(
            "match_memories",
            {
                "query_embedding": embedding,
                "match_threshold": 0.7,
                "match_count": limit,
                "filter_user_id": auth.user_id,
            }
        ).execute()

        if not result.data:
            return []

        return [
            {
                "entity_type": "memory",
                "ref": f"memory:{m['id']}",
                "data": m,
                "score": m.get("similarity", 0),
            }
            for m in result.data
        ]

    except Exception:
        return []


async def _text_search(
    auth: Any,
    query: str,
    scope: str,
    limit: int,
) -> dict:
    """Fallback text search when embeddings unavailable."""
    if scope == "all":
        scopes = ["memory", "deliverable"]
    else:
        scopes = [scope]

    all_results = []

    for entity_scope in scopes:
        table = TABLE_MAP.get(entity_scope)
        if not table:
            continue

        fields = SEARCH_FIELDS.get(entity_scope, [])
        if not fields:
            continue

        try:
            # Simple ilike search on first searchable field
            field = fields[0]
            result = await auth.client.table(table).select("*").eq(
                "user_id", auth.user_id
            ).ilike(field, f"%{query}%").limit(limit).execute()

            if result.data:
                for item in result.data:
                    all_results.append({
                        "entity_type": entity_scope,
                        "ref": f"{entity_scope}:{item['id']}",
                        "data": item,
                        "score": 0.5,  # No score for text search
                    })

        except Exception:
            continue

    return {
        "success": True,
        "results": all_results[:limit],
        "count": len(all_results[:limit]),
        "query": query,
        "scope": scope,
        "message": f"Found {len(all_results[:limit])} result(s) for '{query}'",
    }
