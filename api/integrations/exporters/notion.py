"""
Notion Exporter - ADR-028, ADR-032, ADR-050

Delivers content to Notion pages via Direct API.

ADR-050: Uses NotionAPIClient (direct REST calls to api.notion.com) instead of spawning
the @notionhq/notion-mcp-server via npx — the Notion MCP server requires internal
integration tokens (ntn_...) and cannot use OAuth access tokens, making it incompatible
with YARNNN's existing auth model. Direct API works perfectly with OAuth tokens.

ADR-032 adds support for draft pages in a YARNNN Drafts database.

Destination Schema:
    {
        "platform": "notion",
        "target": "page-id-uuid",
        "format": "page" | "database_item" | "draft",
        "options": {
            "database_id": "db-uuid",  # For database items
            "properties": {},           # Database properties to set
            "target_name": "/ProductSpec",  # For drafts - human-readable target
            "target_url": "https://...",    # For drafts - link to target location
            "drafts_database_id": "...",    # For drafts - YARNNN Drafts DB
        }
    }
"""

import logging
from typing import Any, Optional

import httpx

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.notion_client import get_notion_client
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)

# Notion API version header
NOTION_VERSION = "2022-06-28"


def _markdown_to_notion_blocks(content: str) -> list[dict]:
    """
    Convert markdown content to Notion block objects.

    Notion's REST API accepts blocks when creating pages. This does a best-effort
    conversion from markdown to paragraph/heading blocks.

    For simplicity we create paragraph blocks from each non-empty line.
    Headings (# / ##) are converted to heading_1 / heading_2.
    """
    blocks = []
    for line in content.split("\n"):
        stripped = line.rstrip()
        if not stripped:
            continue

        if stripped.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[4:]}}]
                }
            })
        elif stripped.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[3:]}}]
                }
            })
        elif stripped.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:]}}]
                }
            })
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:]}}]
                }
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": stripped}}]
                }
            })

    return blocks


async def _create_notion_page(
    access_token: str,
    parent_id: str,
    parent_type: str,  # "page_id" or "database_id"
    title: str,
    content: str,
    properties: Optional[dict] = None,
) -> dict:
    """
    Create a Notion page via Direct API (POST /v1/pages).

    Args:
        parent_type: "page_id" for sub-pages, "database_id" for DB entries
        properties: Additional properties for database items (merged with title)

    Returns:
        Created page object from Notion API
    """
    # Build page title property (required for all pages)
    title_property = {
        "title": [{"type": "text", "text": {"content": title}}]
    }

    # Merge with any provided properties
    page_properties = {**title_property, **(properties or {})}

    # Convert content to blocks
    children = _markdown_to_notion_blocks(content)

    body: dict[str, Any] = {
        "parent": {parent_type: parent_id},
        "properties": page_properties,
        "children": children,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json=body,
        )

        if response.status_code not in (200, 201):
            error_data = response.json()
            raise RuntimeError(
                f"Notion API error ({response.status_code}): "
                f"{error_data.get('message', response.text)}"
            )

        return response.json()


class NotionExporter(DestinationExporter):
    """
    Exports content to Notion via Direct API.

    ADR-050: Uses NotionAPIClient / direct REST calls instead of MCP npx subprocess.
    This is required because:
    1. @notionhq/notion-mcp-server needs internal tokens (ntn_...), not OAuth
    2. Python API on Render has no Node.js runtime for npx
    3. Direct API works with our OAuth tokens and is simpler

    Supports:
    - Creating pages under a parent page
    - Creating database items
    - ADR-032: Creating draft pages in YARNNN Drafts database
    """

    @property
    def platform(self) -> str:
        return "notion"

    def get_supported_formats(self) -> list[str]:
        return ["page", "database_item", "draft"]

    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """Validate Notion destination config."""
        target = destination.get("target")
        if not target:
            return False

        fmt = destination.get("format", "page")
        if fmt not in self.get_supported_formats():
            return False

        if fmt == "database_item":
            options = destination.get("options", {})
            if not options.get("database_id"):
                return False

        # ADR-032: Drafts need drafts_database_id in options
        if fmt == "draft":
            options = destination.get("options", {})
            if not options.get("drafts_database_id"):
                return False

        return True

    async def deliver(
        self,
        destination: dict[str, Any],
        content: str,
        title: str,
        metadata: dict[str, Any],
        context: ExporterContext
    ) -> ExportResult:
        """Deliver content to Notion via Direct API."""
        target = destination.get("target")
        fmt = destination.get("format", "page")
        options = destination.get("options", {})

        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No target page specified"
            )

        access_token = context.access_token

        try:
            if fmt == "draft":
                return await self._create_draft_page(
                    access_token=access_token,
                    target=target,
                    title=title,
                    content=content,
                    options=options,
                    context=context,
                )

            if fmt == "page":
                # Create a child page under the parent page
                created = await _create_notion_page(
                    access_token=access_token,
                    parent_id=target,
                    parent_type="page_id",
                    title=title,
                    content=content,
                )

            elif fmt == "database_item":
                database_id = options.get("database_id")
                extra_properties = options.get("properties", {})

                created = await _create_notion_page(
                    access_token=access_token,
                    parent_id=database_id,
                    parent_type="database_id",
                    title=title,
                    content=content,
                    properties=extra_properties,
                )

            else:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message=f"Unsupported format: {fmt}"
                )

            page_id = created.get("id")
            page_url = created.get("url")

            logger.info(
                f"[NOTION_EXPORT] Delivered to {target} for user {context.user_id}, "
                f"page_id={page_id}"
            )

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=page_id,
                external_url=page_url,
                metadata={"parent_id": target, "format": fmt}
            )

        except Exception as e:
            logger.error(f"[NOTION_EXPORT] Failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def _create_draft_page(
        self,
        access_token: str,
        target: str,
        title: str,
        content: str,
        options: dict[str, Any],
        context: ExporterContext,
    ) -> ExportResult:
        """
        Create a draft page in the YARNNN Drafts database.

        ADR-032: Platform-centric drafts for Notion.

        Creates a database entry with:
        - Status: "Draft"
        - Target Name: human-readable destination
        - Target Location: URL to the intended destination page
        - Body: the deliverable content, ready to copy
        """
        drafts_database_id = options.get("drafts_database_id")
        target_name = options.get("target_name", target)
        target_url = options.get("target_url", "")

        if not drafts_database_id:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="draft format requires drafts_database_id in options"
            )

        # ADR-032: Draft content is clean — no attribution or instructions.
        # Database properties carry the context (Status, Target).
        properties: dict[str, Any] = {
            "Status": {
                "select": {"name": "Draft"}
            },
            "Target Name": {
                "rich_text": [{"type": "text", "text": {"content": target_name}}]
            },
        }

        if target_url:
            properties["Target Location"] = {"url": target_url}

        try:
            created = await _create_notion_page(
                access_token=access_token,
                parent_id=drafts_database_id,
                parent_type="database_id",
                title=title,
                content=content,
                properties=properties,
            )

            page_id = created.get("id")
            page_url = created.get("url")

            logger.info(
                f"[NOTION_EXPORT] Created draft in YARNNN Drafts for {target_name}, "
                f"page_id={page_id}"
            )

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=page_id,
                external_url=page_url,
                metadata={
                    "drafts_database_id": drafts_database_id,
                    "target": target,
                    "target_name": target_name,
                    "format": "draft"
                }
            )

        except Exception as e:
            logger.error(f"[NOTION_EXPORT] Draft creation failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def verify_destination_access(
        self,
        destination: dict[str, Any],
        context: ExporterContext
    ) -> tuple[bool, Optional[str]]:
        """Verify integration has access to the page via Direct API."""
        target = destination.get("target")
        fmt = destination.get("format", "page")

        # For drafts, verify access to the drafts database
        if fmt == "draft":
            options = destination.get("options", {})
            drafts_db_id = options.get("drafts_database_id")
            if not drafts_db_id:
                return (False, "Missing drafts_database_id for draft format")
            target = drafts_db_id

        if not target:
            return (False, "Missing target page ID")

        try:
            notion_client = get_notion_client()
            await notion_client.get_page(
                access_token=context.access_token,
                page_id=target,
            )
            return (True, None)

        except RuntimeError as e:
            error_msg = str(e)
            if "object_not_found" in error_msg.lower():
                return (False, f"Page '{target}' not found or not shared with integration")
            return (False, f"Cannot access page: {error_msg}")
        except Exception as e:
            return (False, f"Cannot access page: {e}")

    def infer_style_context(self) -> str:
        """Notion style: structured, headers, detailed."""
        return "notion"
