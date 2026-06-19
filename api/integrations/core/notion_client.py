"""
Notion API Client.

ADR-050: Direct API client for Notion operations.

Why Direct API instead of MCP?
1. @notionhq/notion-mcp-server requires internal integration tokens (ntn_...)
2. Notion's hosted MCP (mcp.notion.com) manages its own OAuth sessions
3. Neither option works with YARNNN's existing OAuth access tokens
4. Direct API calls to api.notion.com work perfectly with OAuth tokens

Direct API is the standard pattern for all YARNNN platform clients.
"""

import logging
from typing import Optional, Any

import httpx

logger = logging.getLogger(__name__)

# Notion API version - required header
NOTION_VERSION = "2022-06-28"


class NotionAPIClient:
    """
    Direct API client for Notion operations.

    NOT MCP - uses Notion's REST API directly with OAuth access tokens.

    Usage:
        client = NotionAPIClient()

        # Search pages
        results = await client.search(
            access_token="...",
            query="project notes"
        )

        # Add comment to page
        result = await client.create_comment(
            access_token="...",
            page_id="...",
            content="Hello from YARNNN!"
        )
    """

    async def search(
        self,
        access_token: str,
        query: str,
        filter_type: Optional[str] = None,
        page_size: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search for pages and databases in Notion.

        Args:
            access_token: OAuth access token
            query: Search query text
            filter_type: Optional filter - "page" or "database"
            page_size: Max results (default 10, max 100)

        Returns:
            List of search result objects
        """
        body: dict[str, Any] = {
            "query": query,
            "page_size": min(page_size, 100),
        }

        if filter_type in ("page", "database"):
            body["filter"] = {"value": filter_type, "property": "object"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise RuntimeError(
                    f"Notion API error: {error_data.get('message', response.text)}"
                )

            data = response.json()
            return data.get("results", [])

    async def get_page(
        self,
        access_token: str,
        page_id: str
    ) -> dict[str, Any]:
        """
        Get a Notion page by ID.

        Args:
            access_token: OAuth access token
            page_id: Page UUID

        Returns:
            Page object with properties
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise RuntimeError(
                    f"Notion API error: {error_data.get('message', response.text)}"
                )

            return response.json()

    async def get_page_content(
        self,
        access_token: str,
        page_id: str,
        page_size: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get block children (content) of a page.

        Args:
            access_token: OAuth access token
            page_id: Page UUID
            page_size: Max blocks to return

        Returns:
            List of block objects
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                },
                params={"page_size": min(page_size, 100)},
                timeout=30.0,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise RuntimeError(
                    f"Notion API error: {error_data.get('message', response.text)}"
                )

            data = response.json()
            return data.get("results", [])

    async def create_comment(
        self,
        access_token: str,
        page_id: str,
        content: str
    ) -> dict[str, Any]:
        """
        Add a comment to a Notion page.

        Args:
            access_token: OAuth access token
            page_id: Page UUID to comment on
            content: Comment text (supports basic markdown)

        Returns:
            Created comment object
        """
        # Notion comments use rich text blocks
        rich_text = self._text_to_rich_text(content)

        body = {
            "parent": {"page_id": page_id},
            "rich_text": rich_text,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/comments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )

            if response.status_code not in (200, 201):
                error_data = response.json()
                raise RuntimeError(
                    f"Notion API error: {error_data.get('message', response.text)}"
                )

            return response.json()

    async def get_comments(
        self,
        access_token: str,
        page_id: str,
        page_size: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get comments on a Notion page.

        Args:
            access_token: OAuth access token
            page_id: Page UUID
            page_size: Max comments to return

        Returns:
            List of comment objects
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.notion.com/v1/comments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                },
                params={
                    "block_id": page_id,
                    "page_size": min(page_size, 100),
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise RuntimeError(
                    f"Notion API error: {error_data.get('message', response.text)}"
                )

            data = response.json()
            return data.get("results", [])

    async def list_databases(
        self,
        access_token: str,
        page_size: int = 50
    ) -> list[dict[str, Any]]:
        """
        List databases the integration has access to.

        Args:
            access_token: OAuth access token
            page_size: Max results

        Returns:
            List of database objects
        """
        # Use search with database filter
        return await self.search(
            access_token=access_token,
            query="",
            filter_type="database",
            page_size=page_size,
        )

    async def search_paginated(
        self,
        access_token: str,
        query: str = "",
        filter_type: Optional[str] = None,
        max_results: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Paginated search through Notion workspace.

        ADR-077: Full paginated discovery for landscape (replaces capped search).
        """
        all_results: list[dict[str, Any]] = []
        start_cursor: Optional[str] = None

        while len(all_results) < max_results:
            body: dict[str, Any] = {
                "query": query,
                "page_size": min(100, max_results - len(all_results)),
            }
            if filter_type in ("page", "database"):
                body["filter"] = {"value": filter_type, "property": "object"}
            if start_cursor:
                body["start_cursor"] = start_cursor

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.notion.com/v1/search",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": NOTION_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=30.0,
                )
                if response.status_code != 200:
                    break
                data = response.json()

            all_results.extend(data.get("results", []))
            if not data.get("has_more") or not data.get("next_cursor"):
                break
            start_cursor = data["next_cursor"]

        return all_results

    async def check_recent_changes(
        self,
        access_token: str,
        since_iso: str,
    ) -> bool:
        """Check if any Notion pages were edited since a given timestamp (ADR-112).

        One lightweight API call: search with sort by last_edited_time, page_size=1.
        Returns True if at least one page was edited after `since_iso`.
        """
        body: dict[str, Any] = {
            "query": "",
            "page_size": 1,
            "sort": {
                "direction": "descending",
                "timestamp": "last_edited_time",
            },
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.notion.com/v1/search",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": NOTION_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=15.0,
                )
                if response.status_code != 200:
                    return True  # On error, assume changes exist (safe fallback)
                data = response.json()
                results = data.get("results", [])
                if not results:
                    return False
                # Compare most recently edited page's timestamp with our cursor
                latest = results[0].get("last_edited_time", "")
                return latest > since_iso
        except Exception:
            return True  # On error, assume changes exist

    async def get_page_content_full(
        self,
        access_token: str,
        page_id: str,
        max_blocks: int = 500,
        max_depth: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Recursively fetch all blocks including nested children with pagination.

        ADR-077: Replaces single-page get_page_content for deeper content capture.
        """
        blocks: list[dict[str, Any]] = []
        await self._fetch_blocks_recursive(
            access_token, page_id, blocks, max_blocks, max_depth, depth=0
        )
        return blocks

    async def _fetch_blocks_recursive(
        self,
        access_token: str,
        block_id: str,
        blocks: list[dict[str, Any]],
        max_blocks: int,
        max_depth: int,
        depth: int,
    ) -> None:
        """Recursively fetch block children with pagination."""
        import asyncio

        if len(blocks) >= max_blocks or depth > max_depth:
            return

        start_cursor: Optional[str] = None
        while len(blocks) < max_blocks:
            params: dict[str, Any] = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.notion.com/v1/blocks/{block_id}/children",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": NOTION_VERSION,
                    },
                    params=params,
                    timeout=30.0,
                )
                if response.status_code != 200:
                    break
                data = response.json()

            results = data.get("results", [])
            for block in results:
                if len(blocks) >= max_blocks:
                    break
                blocks.append(block)
                # Recurse into children (toggles, columns, synced blocks, etc.)
                if block.get("has_children") and depth < max_depth:
                    # ADR-077: Notion rate limit ~3 req/sec
                    await asyncio.sleep(0.35)
                    await self._fetch_blocks_recursive(
                        access_token, block["id"], blocks,
                        max_blocks, max_depth, depth + 1,
                    )

            start_cursor = data.get("next_cursor")
            if not start_cursor or not data.get("has_more"):
                break

    async def query_database(
        self,
        access_token: str,
        database_id: str,
        page_size: int = 100,
        max_pages: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Query a Notion database to get its rows (pages).

        ADR-077: Database content support for richer Notion sync.
        Returns list of page objects that are rows of the database.
        """
        all_results: list[dict[str, Any]] = []
        start_cursor: Optional[str] = None

        for _ in range(max_pages):
            body: dict[str, Any] = {"page_size": min(page_size, 100)}
            if start_cursor:
                body["start_cursor"] = start_cursor

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.notion.com/v1/databases/{database_id}/query",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": NOTION_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=30.0,
                )
                if response.status_code != 200:
                    break
                data = response.json()

            all_results.extend(data.get("results", []))
            start_cursor = data.get("next_cursor")
            if not start_cursor or not data.get("has_more"):
                break

        return all_results

    async def create_page(
        self,
        access_token: str,
        parent_page_id: str,
        title: str,
        content: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a child page under a parent page (ADR-304 amendment audience-
        write). Creates a page titled `title` under `parent_page_id`; if
        `content` is provided, seeds it as paragraph blocks.

        Args:
            access_token: OAuth access token (operator's Notion integration).
            parent_page_id: UUID of the parent page the new page nests under.
            title: The new page's title.
            content: Optional initial body (plain text / basic markdown), split
                into paragraph blocks.

        Returns:
            The created page object (carries `id`, `url`).
        """
        body: dict[str, Any] = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {"title": self._text_to_rich_text(title or "Untitled")},
            },
        }
        if content:
            body["children"] = self._text_to_paragraph_blocks(content)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )
            if response.status_code not in (200, 201):
                error_data = response.json()
                raise RuntimeError(
                    f"Notion API error: {error_data.get('message', response.text)}"
                )
            return response.json()

    async def append_block(
        self,
        access_token: str,
        block_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Append paragraph block(s) to an existing page or block (ADR-304
        amendment audience-write). Uses PATCH /blocks/{id}/children.

        Args:
            access_token: OAuth access token.
            block_id: UUID of the page or block to append children to (a page
                is a block in Notion's model).
            content: Text to append, split into paragraph blocks.

        Returns:
            The append response (carries the created `results` blocks).
        """
        body = {"children": self._text_to_paragraph_blocks(content)}

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.notion.com/v1/blocks/{block_id}/children",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30.0,
            )
            if response.status_code not in (200, 201):
                error_data = response.json()
                raise RuntimeError(
                    f"Notion API error: {error_data.get('message', response.text)}"
                )
            return response.json()

    def _text_to_rich_text(self, text: str) -> list[dict[str, Any]]:
        """
        Convert plain text to Notion rich text format.

        For simplicity, we create a single text block.
        More complex formatting could be added later.
        """
        return [
            {
                "type": "text",
                "text": {"content": text},
            }
        ]

    def _text_to_paragraph_blocks(self, text: str) -> list[dict[str, Any]]:
        """Split plain text / basic markdown into Notion paragraph blocks.

        One block per non-empty line; each block's text chunked at Notion's
        2000-char-per-rich-text-object limit so long lines don't 400. Blank
        lines become empty paragraph spacers (preserving visual structure).
        """
        NOTION_RICH_TEXT_LIMIT = 2000
        blocks: list[dict[str, Any]] = []
        for line in (text or "").split("\n"):
            if not line.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": []},
                })
                continue
            # Chunk long lines into ≤2000-char rich-text objects (same block).
            chunks = [
                line[i:i + NOTION_RICH_TEXT_LIMIT]
                for i in range(0, len(line), NOTION_RICH_TEXT_LIMIT)
            ]
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": c}} for c in chunks
                    ]
                },
            })
        # Notion caps children at 100 per request; cap defensively.
        return blocks[:100] if blocks else [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": []},
        }]


# Singleton instance
_notion_client: Optional[NotionAPIClient] = None


def get_notion_client() -> NotionAPIClient:
    """Get or create the Notion API client singleton."""
    global _notion_client
    if _notion_client is None:
        _notion_client = NotionAPIClient()
    return _notion_client
