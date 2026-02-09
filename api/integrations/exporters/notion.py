"""
Notion Exporter - ADR-028, ADR-032

Delivers content to Notion pages via MCP.

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

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.client import get_mcp_manager, MCP_AVAILABLE
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)


class NotionExporter(DestinationExporter):
    """
    Exports content to Notion via MCP.

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
        # Must have a target (page ID)
        target = destination.get("target")
        if not target:
            return False

        # Format must be supported
        fmt = destination.get("format", "page")
        if fmt not in self.get_supported_formats():
            return False

        # Database items need database_id in options
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
        """Deliver content to Notion."""
        if not MCP_AVAILABLE:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="MCP not available. Install: pip install mcp"
            )

        target = destination.get("target")
        fmt = destination.get("format", "page")
        options = destination.get("options", {})

        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No target page specified"
            )

        try:
            mcp = get_mcp_manager()

            # ADR-032: Handle draft format (platform-centric drafts)
            if fmt == "draft":
                return await self._create_draft_page(
                    mcp=mcp,
                    context=context,
                    target=target,
                    title=title,
                    content=content,
                    options=options
                )

            if fmt == "page":
                # Create a new page under the parent
                # @notionhq/notion-mcp-server uses notion-create-pages
                result = await mcp.call_tool(
                    user_id=context.user_id,
                    provider="notion",
                    tool_name="notion-create-pages",
                    arguments={
                        "pages": [{
                            "parent_id": target,
                            "title": title,
                            "content_markdown": content
                        }]
                    },
                    env={"NOTION_TOKEN": context.access_token}
                )
            elif fmt == "database_item":
                # Create a database item
                database_id = options.get("database_id")
                properties = options.get("properties", {})

                result = await mcp.call_tool(
                    user_id=context.user_id,
                    provider="notion",
                    tool_name="notion-create-pages",
                    arguments={
                        "pages": [{
                            "parent_id": database_id,  # Database ID as parent
                            "title": title,
                            "content_markdown": content,
                            "properties": properties
                        }]
                    },
                    env={"NOTION_TOKEN": context.access_token}
                )
            else:
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message=f"Unsupported format: {fmt}"
                )

            # Extract page ID and URL from result
            page_id = None
            page_url = None

            if isinstance(result, dict):
                page_id = result.get("id")
                page_url = result.get("url")
            # MCP returns CallToolResult with content
            elif hasattr(result, "content"):
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        import json
                        try:
                            parsed = json.loads(content_item.text)
                            page_id = parsed.get("id")
                            page_url = parsed.get("url")
                        except (json.JSONDecodeError, TypeError):
                            pass

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
        mcp: Any,
        context: ExporterContext,
        target: str,
        title: str,
        content: str,
        options: dict[str, Any]
    ) -> ExportResult:
        """
        Create a draft page in the YARNNN Drafts database.

        ADR-032: Platform-centric drafts for Notion.

        The draft page includes:
        - Status property: "Draft"
        - Target Location property: URL to destination page
        - Target Name property: Human-readable destination
        - Body: Content with destination context callout
        """
        import json

        drafts_database_id = options.get("drafts_database_id")
        target_name = options.get("target_name", target)
        target_url = options.get("target_url", "")

        if not drafts_database_id:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="draft format requires drafts_database_id in options"
            )

        # ADR-032: Draft content should be clean - no attribution or instructions
        # that users might forget to remove before sending.
        # The database properties (Status, Target) provide the context.
        # The content itself is ready to copy/move.
        draft_content = content

        # Build properties for the database item
        properties = {
            "Status": {
                "select": {"name": "Draft"}
            },
            "Target Name": {
                "rich_text": [{"text": {"content": target_name}}]
            },
        }

        if target_url:
            properties["Target Location"] = {
                "url": target_url
            }

        try:
            result = await mcp.call_tool(
                user_id=context.user_id,
                provider="notion",
                tool_name="notion-create-pages",
                arguments={
                    "pages": [{
                        "parent_id": drafts_database_id,
                        "title": title,
                        "content_markdown": draft_content,
                        "properties": properties
                    }]
                },
                env={"NOTION_TOKEN": context.access_token}
            )

            # Extract page ID and URL from result
            page_id = None
            page_url = None

            if isinstance(result, dict):
                page_id = result.get("id")
                page_url = result.get("url")
            elif hasattr(result, "content"):
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        try:
                            parsed = json.loads(content_item.text)
                            page_id = parsed.get("id")
                            page_url = parsed.get("url")
                        except (json.JSONDecodeError, TypeError):
                            pass

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
        """Verify integration has access to the page."""
        if not MCP_AVAILABLE:
            return (False, "MCP not available")

        target = destination.get("target")
        fmt = destination.get("format", "page")

        # For drafts, verify access to the drafts database instead
        if fmt == "draft":
            options = destination.get("options", {})
            drafts_db_id = options.get("drafts_database_id")
            if not drafts_db_id:
                return (False, "Missing drafts_database_id for draft format")
            target = drafts_db_id

        if not target:
            return (False, "Missing target page ID")

        try:
            mcp = get_mcp_manager()

            # Try to get page info to verify access
            # @notionhq/notion-mcp-server uses notion-fetch
            result = await mcp.call_tool(
                user_id=context.user_id,
                provider="notion",
                tool_name="notion-fetch",
                arguments={"resource_uri": f"notion://page/{target}"},
                env={"NOTION_TOKEN": context.access_token}
            )

            # If we get here without error, we have access
            return (True, None)

        except Exception as e:
            error_msg = str(e)
            if "object_not_found" in error_msg.lower():
                return (False, f"Page '{target}' not found or not shared with integration")
            return (False, f"Cannot access page: {error_msg}")

    def infer_style_context(self) -> str:
        """Notion style: structured, headers, detailed."""
        return "notion"
