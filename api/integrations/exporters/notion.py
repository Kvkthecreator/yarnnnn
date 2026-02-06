"""
Notion Exporter - ADR-028

Delivers content to Notion pages via MCP.

Destination Schema:
    {
        "platform": "notion",
        "target": "page-id-uuid",
        "format": "page" | "database_item",
        "options": {
            "database_id": "db-uuid",  # For database items
            "properties": {}            # Database properties to set
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
    - Creating database items (future)
    """

    @property
    def platform(self) -> str:
        return "notion"

    def get_supported_formats(self) -> list[str]:
        return ["page", "database_item"]

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

        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No target page specified"
            )

        try:
            mcp = get_mcp_manager()

            if fmt == "page":
                # Create a new page under the parent
                result = await mcp.call_tool(
                    user_id=context.user_id,
                    provider="notion",
                    tool_name="notion_create_page",
                    arguments={
                        "parent_id": target,
                        "title": title,
                        "content": content
                    },
                    env={"AUTH_TOKEN": context.access_token}
                )
            elif fmt == "database_item":
                # Create a database item (future enhancement)
                options = destination.get("options", {})
                database_id = options.get("database_id")
                properties = options.get("properties", {})

                result = await mcp.call_tool(
                    user_id=context.user_id,
                    provider="notion",
                    tool_name="notion_create_database_item",
                    arguments={
                        "database_id": database_id,
                        "title": title,
                        "content": content,
                        "properties": properties
                    },
                    env={"AUTH_TOKEN": context.access_token}
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

    async def verify_destination_access(
        self,
        destination: dict[str, Any],
        context: ExporterContext
    ) -> tuple[bool, Optional[str]]:
        """Verify integration has access to the page."""
        if not MCP_AVAILABLE:
            return (False, "MCP not available")

        target = destination.get("target")
        if not target:
            return (False, "Missing target page ID")

        try:
            mcp = get_mcp_manager()

            # Try to get page info to verify access
            result = await mcp.call_tool(
                user_id=context.user_id,
                provider="notion",
                tool_name="notion_get_page",
                arguments={"page_id": target},
                env={"AUTH_TOKEN": context.access_token}
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
