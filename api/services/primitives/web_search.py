"""
WebSearch Primitive

ADR-045 + TP Enhancement: Web search capability for Thinking Partner.

This primitive provides web search functionality using Anthropic's native
web_search tool. Unlike other primitives that operate on YARNNN entities,
this reaches out to the internet for current information.

Usage:
  WebSearch(query="latest React 19 features")
  WebSearch(query="competitor pricing", context="enterprise SaaS")
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass

from services.anthropic import get_anthropic_client

logger = logging.getLogger(__name__)


# Anthropic's native web_search tool definition (server-side)
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}


WEB_SEARCH_PRIMITIVE = {
    "name": "WebSearch",
    "description": """Search the web for current information.

Use when you need:
- Current events or news
- Latest documentation or release notes
- Market research or competitor info
- Technical information not in user's data
- Anything requiring up-to-date external information

Returns search results with titles, URLs, and snippets.

Examples:
- WebSearch(query="OpenAI GPT-5 release date")
- WebSearch(query="best practices kubernetes autoscaling 2026")
- WebSearch(query="Acme Corp funding news", context="competitor research")

Note: For user's own data (Slack, Gmail, documents), use Search() instead.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "context": {
                "type": "string",
                "description": "Optional context to help focus the search (e.g., 'competitor research', 'technical documentation')"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return. Default: 5",
                "default": 5
            }
        },
        "required": ["query"]
    }
}


@dataclass
class WebSearchResult:
    """Result from web search."""
    query: str
    results: list[dict]  # [{title, url, snippet}]
    success: bool
    error: Optional[str] = None


async def _execute_web_search(
    query: str,
    context: Optional[str] = None,
    max_results: int = 5,
) -> WebSearchResult:
    """
    Execute web search using Anthropic's native tool.

    This creates a minimal Claude call with web_search enabled,
    asking it to search and summarize results.
    """
    client = get_anthropic_client()

    # Build the search prompt
    user_prompt = f"Search the web for: {query}"
    if context:
        user_prompt += f"\n\nContext: {context}"
    user_prompt += f"""

Please search for this and return the top {max_results} most relevant results.
For each result, provide:
1. Title
2. URL
3. Brief snippet/summary

Format your response as a structured list of findings."""

    system_prompt = """You are a web search assistant. Use web_search to find relevant information.
After searching, provide a clear summary of findings with source URLs.
Be factual and cite your sources."""

    try:
        messages = [{"role": "user", "content": user_prompt}]
        sources = []
        search_results = []
        content_parts = []

        # Initial API call with web_search tool
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )

        # Process response - track searches and results
        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "server_tool_use":
                if block.name == "web_search":
                    logger.info(f"[WEB_SEARCH] Query: {block.input.get('query', '')}")
            elif block.type == "web_search_tool_result":
                # Extract search results
                if hasattr(block, 'content') and isinstance(block.content, list):
                    for result in block.content:
                        if hasattr(result, 'type') and result.type == "web_search_result":
                            search_results.append({
                                "title": getattr(result, 'title', ''),
                                "url": getattr(result, 'url', ''),
                                "snippet": getattr(result, 'snippet', getattr(result, 'content', ''))[:500],
                            })

        # Handle continuation if needed
        while response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                tools=[WEB_SEARCH_TOOL],
                messages=messages,
            )

            for block in response.content:
                if block.type == "text":
                    content_parts.append(block.text)
                elif block.type == "web_search_tool_result":
                    if hasattr(block, 'content') and isinstance(block.content, list):
                        for result in block.content:
                            if hasattr(result, 'type') and result.type == "web_search_result":
                                search_results.append({
                                    "title": getattr(result, 'title', ''),
                                    "url": getattr(result, 'url', ''),
                                    "snippet": getattr(result, 'snippet', getattr(result, 'content', ''))[:500],
                                })

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in search_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)

        logger.info(f"[WEB_SEARCH] Complete: {len(unique_results)} results for '{query}'")

        return WebSearchResult(
            query=query,
            results=unique_results[:max_results],
            success=True,
        )

    except Exception as e:
        logger.error(f"[WEB_SEARCH] Failed: {e}", exc_info=True)
        return WebSearchResult(
            query=query,
            results=[],
            success=False,
            error=str(e),
        )


async def handle_web_search(auth: Any, input: dict) -> dict:
    """
    Handle WebSearch primitive.

    Args:
        auth: Auth context with user_id and client (not used for web search)
        input: {"query": "...", "context": "...", "max_results": N}

    Returns:
        {"success": True, "results": [...], "query": "..."}
        or {"success": False, "error": "...", "message": "..."}
    """
    query = input.get("query", "").strip()
    context = input.get("context")
    max_results = input.get("max_results", 5)

    if not query:
        return {
            "success": False,
            "error": "missing_query",
            "message": "Search query is required",
        }

    # Execute the web search
    result = await _execute_web_search(query, context, max_results)

    if not result.success:
        return {
            "success": False,
            "error": "web_search_failed",
            "message": result.error or "Web search failed",
            "query": query,
        }

    return {
        "success": True,
        "results": result.results,
        "count": len(result.results),
        "query": query,
        "message": f"Found {len(result.results)} result(s) for '{query}'",
    }
