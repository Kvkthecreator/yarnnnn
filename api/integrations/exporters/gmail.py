"""
Gmail Exporter - ADR-029

Delivers content to Gmail via MCP (send or draft).

Destination Schema:
    {
        "platform": "gmail",
        "target": "recipient@example.com",
        "format": "send" | "draft" | "reply",
        "options": {
            "cc": "other@example.com",
            "subject": "Custom subject",
            "thread_id": "abc123"  # For replies
        }
    }
"""

import os
import logging
from typing import Any, Optional

from integrations.core.types import ExportResult, ExportStatus
from integrations.core.client import get_mcp_manager, MCP_AVAILABLE
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)


class GmailExporter(DestinationExporter):
    """
    Exports content to Gmail via MCP.

    Supports:
    - Sending emails directly
    - Creating drafts for user review
    - Replying to existing threads
    """

    @property
    def platform(self) -> str:
        return "gmail"

    def get_supported_formats(self) -> list[str]:
        return ["send", "draft", "reply"]

    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """Validate Gmail destination config."""
        # Must have a target (recipient email)
        target = destination.get("target")
        if not target or "@" not in target:
            return False

        # Format must be supported
        fmt = destination.get("format", "send")
        if fmt not in self.get_supported_formats():
            return False

        # Reply format requires thread_id
        if fmt == "reply":
            options = destination.get("options", {})
            if not options.get("thread_id"):
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
        """Deliver content to Gmail."""
        if not MCP_AVAILABLE:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="MCP not available. Install: pip install mcp"
            )

        target = destination.get("target")
        fmt = destination.get("format", "send")
        options = destination.get("options", {})

        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No recipient email specified"
            )

        # Get Gmail credentials from context
        # Note: Gmail uses refresh_token, not access_token
        refresh_token = context.metadata.get("refresh_token")
        if not refresh_token:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Missing refresh_token in integration metadata"
            )

        # Get Google OAuth credentials from environment
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Google OAuth credentials not configured"
            )

        # Build subject - use title or custom from options
        subject = options.get("subject", title)
        cc = options.get("cc")
        thread_id = options.get("thread_id")

        try:
            mcp = get_mcp_manager()

            if fmt == "draft":
                # Create draft for user review
                result = await mcp.create_gmail_draft(
                    user_id=context.user_id,
                    to=target,
                    subject=subject,
                    body=content,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    cc=cc,
                    thread_id=thread_id
                )

                if result.status == ExportStatus.SUCCESS:
                    logger.info(
                        f"[GMAIL_EXPORT] Created draft for {target}, "
                        f"draft_id={result.external_id}"
                    )
                    result.metadata["format"] = "draft"
                    result.metadata["recipient"] = target

                return result

            else:
                # Send directly (both "send" and "reply" formats)
                result = await mcp.send_gmail_message(
                    user_id=context.user_id,
                    to=target,
                    subject=subject,
                    body=content,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    cc=cc,
                    thread_id=thread_id if fmt == "reply" else None
                )

                if result.status == ExportStatus.SUCCESS:
                    logger.info(
                        f"[GMAIL_EXPORT] Sent to {target}, "
                        f"message_id={result.external_id}"
                    )
                    result.metadata["format"] = fmt
                    result.metadata["recipient"] = target

                return result

        except Exception as e:
            logger.error(f"[GMAIL_EXPORT] Failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def verify_destination_access(
        self,
        destination: dict[str, Any],
        context: ExporterContext
    ) -> tuple[bool, Optional[str]]:
        """Verify Gmail integration is valid."""
        if not MCP_AVAILABLE:
            return (False, "MCP not available")

        # Check refresh token exists
        refresh_token = context.metadata.get("refresh_token")
        if not refresh_token:
            return (False, "Missing refresh token - reconnect Gmail")

        # Check OAuth credentials
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            return (False, "Google OAuth not configured")

        # Try to list messages as a connectivity test
        try:
            mcp = get_mcp_manager()
            await mcp.list_gmail_messages(
                user_id=context.user_id,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                max_results=1
            )
            return (True, None)

        except Exception as e:
            error_msg = str(e)
            if "invalid_grant" in error_msg.lower():
                return (False, "Gmail access expired - please reconnect")
            if "insufficient_scope" in error_msg.lower():
                return (False, "Missing Gmail permissions - please reconnect")
            return (False, f"Cannot access Gmail: {error_msg}")

    def infer_style_context(self) -> str:
        """Email style: professional, clear, appropriate greeting/sign-off."""
        return "email"
