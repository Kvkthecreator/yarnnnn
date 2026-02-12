"""
Notion API Client.

ADR-050: Direct API client for Notion operations.

Why Direct API instead of MCP?
1. @notionhq/notion-mcp-server requires internal integration tokens (ntn_...)
2. Notion's hosted MCP (mcp.notion.com) manages its own OAuth sessions
3. Neither option works with YARNNN's existing OAuth access tokens
4. Direct API calls to api.notion.com work perfectly with OAuth tokens

This follows the same pattern as GoogleAPIClient for Gmail/Calendar.
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


# Singleton instance
_notion_client: Optional[NotionAPIClient] = None


def get_notion_client() -> NotionAPIClient:
    """Get or create the Notion API client singleton."""
    global _notion_client
    if _notion_client is None:
        _notion_client = NotionAPIClient()
    return _notion_client
