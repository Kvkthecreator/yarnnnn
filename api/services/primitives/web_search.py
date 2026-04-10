"""
WebSearch Primitive

ADR-045 + TP Enhancement: Web search and URL fetch capability for Thinking Partner.

This primitive provides two modes:
1. Web search: Uses Anthropic's native web_search tool to find information
2. URL fetch: Directly fetches and extracts text content from a specific URL

Usage:
  WebSearch(query="latest React 19 features")
  WebSearch(query="competitor pricing", context="enterprise SaaS")
  WebSearch(url="https://example.com/about")
"""

import logging
import re
from html.parser import HTMLParser
from typing import Any, Optional
from dataclasses import dataclass

import httpx

from services.anthropic import get_anthropic_client

logger = logging.getLogger(__name__)


# Anthropic's native web_search tool definition (server-side)
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}


WEB_SEARCH_PRIMITIVE = {
    "name": "WebSearch",
    "description": """Search the web or fetch a specific URL.

Two modes:
1. **Search** (pass `query`): Search the web for information
2. **Fetch** (pass `url`): Read the content of a specific webpage

Use search when you need:
- Current events or news
- Latest documentation or release notes
- Market research or competitor info
- Technical information not in user's data

Use fetch when:
- User shares a URL and wants you to read it
- You need the full content of a specific page
- A search result looks relevant and you want the details

Examples:
- WebSearch(query="OpenAI GPT-5 release date")
- WebSearch(query="Acme Corp funding news", context="competitor research")
- WebSearch(url="https://example.com/about")

Note: For user's own data (Slack, documents), use Search() instead.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (for web search mode)"
            },
            "url": {
                "type": "string",
                "description": "URL to fetch and extract content from (for fetch mode)"
            },
            "context": {
                "type": "string",
                "description": "Optional context to help focus the search (e.g., 'competitor research')"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum search results to return. Default: 5",
                "default": 5
            }
        },
        "required": []
    }
}


@dataclass
class WebSearchResult:
    """Result from web search."""
    query: str
    results: list[dict]  # [{title, url, snippet}]
    success: bool
    error: Optional[str] = None
    input_tokens: int = 0   # ADR-171: accumulated across all rounds
    output_tokens: int = 0


@dataclass
class URLFetchResult:
    """Result from URL fetch."""
    url: str
    title: str
    content: str
    success: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# HTML text extraction (stdlib only — no beautifulsoup dependency)
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Extract visible text from HTML, skipping scripts/styles."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0
        self._title: str = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str):
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        # Add whitespace after block-level tags
        if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
                    "li", "tr", "td", "th", "blockquote", "section", "article",
                    "header", "footer", "nav", "main"}:
            self._pieces.append("\n")

    def handle_data(self, data: str):
        if self._in_title:
            self._title = data.strip()
        if self._skip_depth == 0:
            self._pieces.append(data)

    def get_text(self) -> str:
        raw = "".join(self._pieces)
        # Collapse whitespace: multiple spaces → single, multiple newlines → double
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    def get_title(self) -> str:
        return self._title


def _extract_text_from_html(html: str) -> tuple[str, str]:
    """Return (title, visible_text) from raw HTML."""
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass
    return extractor.get_title(), extractor.get_text()


# ---------------------------------------------------------------------------
# URL fetch
# ---------------------------------------------------------------------------

_MAX_CONTENT_LENGTH = 12_000  # ~3K tokens — enough to extract key facts from a page
_FETCH_TIMEOUT = 15  # seconds

async def _fetch_url(url: str) -> URLFetchResult:
    """Fetch a URL and extract its text content."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(_FETCH_TIMEOUT),
        ) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; YARNNN/1.0; +https://yarnnn.com)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type or "application/xhtml" in content_type:
                html = response.text
                title, text = _extract_text_from_html(html)
                # Truncate if extremely long
                if len(text) > _MAX_CONTENT_LENGTH:
                    text = text[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated]"
                return URLFetchResult(
                    url=url,
                    title=title or url,
                    content=text,
                    success=True,
                )
            elif "text/plain" in content_type or "application/json" in content_type:
                text = response.text[:_MAX_CONTENT_LENGTH]
                return URLFetchResult(
                    url=url,
                    title=url,
                    content=text,
                    success=True,
                )
            else:
                return URLFetchResult(
                    url=url,
                    title="",
                    content="",
                    success=False,
                    error=f"Unsupported content type: {content_type}",
                )

    except httpx.HTTPStatusError as e:
        return URLFetchResult(
            url=url, title="", content="", success=False,
            error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
        )
    except httpx.TimeoutException:
        return URLFetchResult(
            url=url, title="", content="", success=False,
            error=f"Request timed out after {_FETCH_TIMEOUT}s",
        )
    except Exception as e:
        return URLFetchResult(
            url=url, title="", content="", success=False,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Web search (Anthropic native tool)
# ---------------------------------------------------------------------------

async def _execute_web_search(
    query: str,
    context: Optional[str] = None,
    max_results: int = 5,
) -> WebSearchResult:
    """
    Execute web search using Anthropic's native tool.

    Makes a minimal Claude call solely to trigger the web_search_20250305
    server-side tool. We extract search result blocks directly from the
    response — no summarization prompt, no prose generation. The calling
    agent (TP or headless) synthesizes results in context, not here.

    max_tokens=50: We only want the server tool to fire. The model doesn't
    need to generate meaningful text — just enough to complete the tool call.
    Output tokens beyond tool execution are waste.
    """
    client = get_anthropic_client()

    # Minimal prompt — just enough to trigger a search. No "please summarize"
    # instruction that wastes output tokens on prose nobody reads.
    user_prompt = f"Search: {query}"
    if context:
        user_prompt += f" ({context})"

    try:
        messages = [{"role": "user", "content": user_prompt}]
        search_results = []
        # ADR-171: accumulate tokens across all rounds
        total_input_tokens = 0
        total_output_tokens = 0

        def _extract_results(content_blocks):
            """Pull web_search_tool_result blocks from a response content list."""
            for block in content_blocks:
                if block.type == "web_search_tool_result":
                    if hasattr(block, 'content') and isinstance(block.content, list):
                        for result in block.content:
                            if hasattr(result, 'type') and result.type == "web_search_result":
                                search_results.append({
                                    "title": getattr(result, 'title', ''),
                                    "url": getattr(result, 'url', ''),
                                    "snippet": getattr(result, 'snippet', getattr(result, 'content', ''))[:500],
                                })
                elif getattr(block, 'type', '') == "server_tool_use" and block.name == "web_search":
                    logger.info(f"[WEB_SEARCH] Query: {block.input.get('query', '')}")

        # Initial call — max_tokens=50 because we only need the tool to execute,
        # not generate a prose summary. Server-side tool result arrives in the
        # response content regardless of text output length.
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            system="Search the web and return results.",
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )
        if response.usage:
            total_input_tokens += getattr(response.usage, "input_tokens", 0)
            total_output_tokens += getattr(response.usage, "output_tokens", 0)

        _extract_results(response.content)

        # Continue only if the tool is still running (shouldn't happen with simple queries)
        while response.stop_reason == "tool_use" and not search_results:
            messages.append({"role": "assistant", "content": response.content})
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                system="Search the web and return results.",
                tools=[WEB_SEARCH_TOOL],
                messages=messages,
            )
            if response.usage:
                total_input_tokens += getattr(response.usage, "input_tokens", 0)
                total_output_tokens += getattr(response.usage, "output_tokens", 0)
            _extract_results(response.content)

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
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )

    except Exception as e:
        logger.error(f"[WEB_SEARCH] Failed: {e}", exc_info=True)
        return WebSearchResult(
            query=query,
            results=[],
            success=False,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def _looks_like_url(text: str) -> bool:
    """Check if text looks like a URL."""
    return bool(re.match(r'^https?://', text.strip()))


async def handle_web_search(auth: Any, input: dict) -> dict:
    """
    Handle WebSearch primitive.

    Two modes:
    - URL fetch: if `url` is provided, fetch and extract page content
    - Web search: if `query` is provided, search the web

    If `query` looks like a URL (starts with http), auto-routes to fetch mode.
    """
    url = input.get("url", "").strip()
    query = input.get("query", "").strip()
    context = input.get("context")
    max_results = input.get("max_results", 5)

    # Auto-detect: if query looks like a URL, treat as fetch
    if not url and query and _looks_like_url(query):
        url = query
        query = ""

    # URL fetch mode
    if url:
        logger.info(f"[WEB_FETCH] Fetching URL: {url}")
        result = await _fetch_url(url)

        if not result.success:
            return {
                "success": False,
                "error": "fetch_failed",
                "message": result.error or "Failed to fetch URL",
                "url": url,
            }

        return {
            "success": True,
            "mode": "fetch",
            "url": url,
            "title": result.title,
            "content": result.content,
            "content_length": len(result.content),
            "message": f"Fetched content from {url} ({len(result.content)} chars)",
        }

    # Web search mode
    if not query:
        return {
            "success": False,
            "error": "missing_input",
            "message": "Provide either 'query' (to search) or 'url' (to fetch a page)",
        }

    result = await _execute_web_search(query, context, max_results)

    # ADR-171: Record token spend for this search
    if result.input_tokens or result.output_tokens:
        try:
            from services.platform_limits import record_token_usage
            from services.supabase import get_service_client
            record_token_usage(
                get_service_client(),
                user_id=auth.user_id,
                caller="web_search",
                model="claude-sonnet-4-20250514",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                metadata={"query": query[:200]},
            )
        except Exception as _e:
            logger.warning(f"[TOKEN_USAGE] web_search record failed: {_e}")

    if not result.success:
        return {
            "success": False,
            "error": "web_search_failed",
            "message": result.error or "Web search failed",
            "query": query,
        }

    return {
        "success": True,
        "mode": "search",
        "results": result.results,
        "count": len(result.results),
        "query": query,
        "message": f"Found {len(result.results)} result(s) for '{query}'",
    }
