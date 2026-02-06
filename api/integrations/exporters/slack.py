"""
Slack Exporter - ADR-028

Delivers content to Slack channels via MCP.

Destination Schema:
    {
        "platform": "slack",
        "target": "#team-updates" or "C123ABC456",
        "format": "message" | "thread",
        "options": {
            "thread_ts": "1234.5678"  # For replies
        }
    }
"""

import logging
from typing import Any, Optional

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.client import get_mcp_manager, MCP_AVAILABLE
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)


class SlackExporter(DestinationExporter):
    """
    Exports content to Slack via MCP.

    Supports:
    - Posting to channels (public and private)
    - Threading (reply to existing messages)
    """

    @property
    def platform(self) -> str:
        return "slack"

    def get_supported_formats(self) -> list[str]:
        return ["message", "thread"]

    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """Validate Slack destination config."""
        # Must have a target (channel ID or name)
        target = destination.get("target")
        if not target:
            return False

        # Format must be supported
        fmt = destination.get("format", "message")
        if fmt not in self.get_supported_formats():
            return False

        # If threading, must have thread_ts in options
        if fmt == "thread":
            options = destination.get("options", {})
            if not options.get("thread_ts"):
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
        """Deliver content to Slack."""
        if not MCP_AVAILABLE:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="MCP not available. Install: pip install mcp"
            )

        target = destination.get("target")
        fmt = destination.get("format", "message")
        options = destination.get("options", {})

        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No target channel specified"
            )

        # Get team_id from context metadata
        team_id = context.metadata.get("team_id")
        if not team_id:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Missing team_id in integration metadata"
            )

        try:
            mcp = get_mcp_manager()

            # Build message arguments
            arguments = {
                "channel": target,
                "text": content,
            }

            # Add thread_ts for threaded replies
            if fmt == "thread" and options.get("thread_ts"):
                arguments["thread_ts"] = options["thread_ts"]

            result = await mcp.call_tool(
                user_id=context.user_id,
                provider="slack",
                tool_name="slack_post_message",
                arguments=arguments,
                env={
                    "SLACK_BOT_TOKEN": context.access_token,
                    "SLACK_TEAM_ID": team_id
                }
            )

            # Extract message ts and permalink from result
            message_ts = None
            permalink = None

            if isinstance(result, dict):
                message_ts = result.get("ts")
                permalink = result.get("permalink")
            # MCP returns CallToolResult with content
            elif hasattr(result, "content"):
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        import json
                        try:
                            parsed = json.loads(content_item.text)
                            message_ts = parsed.get("ts")
                            permalink = parsed.get("permalink")
                        except (json.JSONDecodeError, TypeError):
                            pass

            logger.info(
                f"[SLACK_EXPORT] Delivered to {target} for user {context.user_id}, "
                f"ts={message_ts}"
            )

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=message_ts,
                external_url=permalink,
                metadata={"channel": target, "format": fmt}
            )

        except Exception as e:
            logger.error(f"[SLACK_EXPORT] Failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def verify_destination_access(
        self,
        destination: dict[str, Any],
        context: ExporterContext
    ) -> tuple[bool, Optional[str]]:
        """Verify bot has access to the channel."""
        if not MCP_AVAILABLE:
            return (False, "MCP not available")

        target = destination.get("target")
        team_id = context.metadata.get("team_id")

        if not target or not team_id:
            return (False, "Missing target or team_id")

        try:
            mcp = get_mcp_manager()

            # Try to get channel info to verify access
            result = await mcp.call_tool(
                user_id=context.user_id,
                provider="slack",
                tool_name="slack_get_channel_info",
                arguments={"channel": target},
                env={
                    "SLACK_BOT_TOKEN": context.access_token,
                    "SLACK_TEAM_ID": team_id
                }
            )

            # If we get here without error, bot has access
            return (True, None)

        except Exception as e:
            error_msg = str(e)
            if "channel_not_found" in error_msg.lower():
                return (False, f"Channel '{target}' not found or bot not added")
            if "not_in_channel" in error_msg.lower():
                return (False, f"Bot is not a member of '{target}'")
            return (False, f"Cannot access channel: {error_msg}")

    def infer_style_context(self) -> str:
        """Slack style: casual, brief, emoji-friendly."""
        return "slack"
