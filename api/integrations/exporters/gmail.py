"""
Gmail Exporter - ADR-029, ADR-031, ADR-050

Delivers content to Gmail via Direct API (GoogleAPIClient).

ADR-050: Uses GoogleAPIClient (direct REST calls to Gmail API) instead of MCPClientManager.
The old code called get_mcp_manager() but then called methods (create_gmail_draft,
send_gmail_message, list_gmail_messages) that only exist on GoogleAPIClient — not on
MCPClientManager. This was silently broken.

ADR-031 adds support for platform variants with HTML formatting:
- email_summary: Inbox digest with sections
- email_draft_reply: Reply drafts
- email_weekly_digest: Weekly overview
- email_triage: Email categorization

Destination Schema:
    {
        "platform": "gmail",
        "target": "recipient@example.com",
        "format": "send" | "draft" | "reply" | "html",
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
from integrations.core.google_client import get_google_client
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)


class GmailExporter(DestinationExporter):
    """
    Exports content to Gmail via Direct API.

    ADR-050: Uses GoogleAPIClient instead of MCPClientManager.
    Gmail/Calendar use direct Google REST APIs — no MCP or Node.js required.

    Auth: Uses refresh_token from ExporterContext.refresh_token (decrypted by
    delivery.py from platform_connections.refresh_token_encrypted).

    Supports:
    - Sending emails directly
    - Creating drafts for user review
    - Replying to existing threads
    - HTML-formatted emails (platform variants)
    """

    @property
    def platform(self) -> str:
        return "gmail"

    def get_supported_formats(self) -> list[str]:
        return ["send", "draft", "reply", "html"]

    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """Validate Gmail destination config."""
        target = destination.get("target")
        if not target or "@" not in target:
            return False

        fmt = destination.get("format", "send")
        if fmt not in self.get_supported_formats():
            return False

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
        """Deliver content to Gmail via Direct API."""
        target = destination.get("target")
        fmt = destination.get("format", "send")
        options = destination.get("options", {})

        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No recipient email specified"
            )

        # Gmail uses the refresh_token (not access_token) — decrypted by delivery.py
        refresh_token = context.refresh_token
        if not refresh_token:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Missing refresh_token — reconnect Gmail in Settings"
            )

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="Google OAuth credentials not configured"
            )

        subject = options.get("subject", title)
        cc = options.get("cc")
        thread_id = options.get("thread_id")

        try:
            google_client = get_google_client()

            # ADR-031 Phase 5: HTML formatting for email platform variants
            platform_variant = metadata.get("platform_variant")
            use_html = fmt == "html" or platform_variant in (
                "email_summary", "email_draft_reply", "email_follow_up",
                "email_weekly_digest", "email_triage"
            )

            email_body = content
            if use_html:
                from services.platform_output import generate_gmail_html

                is_draft_mode = fmt == "draft"
                email_body = generate_gmail_html(
                    content=content,
                    variant=platform_variant or "default",
                    metadata={
                        "title": subject,
                        "recipient": target,
                        "date": options.get("date", ""),
                        "email_count": options.get("email_count", ""),
                        "is_draft": is_draft_mode,
                    }
                )
                logger.info(f"[GMAIL_EXPORT] Using HTML format for variant={platform_variant}, is_draft={is_draft_mode}")

            if fmt == "draft":
                result = await google_client.create_gmail_draft(
                    to=target,
                    subject=subject,
                    body=email_body,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    cc=cc,
                    thread_id=thread_id,
                    is_html=use_html,
                )

                if result.status == ExportStatus.SUCCESS:
                    logger.info(f"[GMAIL_EXPORT] Created draft for {target}, draft_id={result.external_id}")
                    result.metadata["format"] = "draft"
                    result.metadata["recipient"] = target

                return result

            else:
                # "send", "reply", "html"
                result = await google_client.send_gmail_message(
                    to=target,
                    subject=subject,
                    body=email_body,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    cc=cc,
                    thread_id=thread_id if fmt == "reply" else None,
                    is_html=use_html,
                )

                if result.status == ExportStatus.SUCCESS:
                    logger.info(f"[GMAIL_EXPORT] Sent to {target}, message_id={result.external_id}")
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
        """Verify Gmail integration is valid via Direct API."""
        refresh_token = context.refresh_token
        if not refresh_token:
            return (False, "Missing refresh token — reconnect Gmail")

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            return (False, "Google OAuth not configured")

        try:
            google_client = get_google_client()
            await google_client.list_gmail_messages(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                max_results=1,
            )
            return (True, None)

        except Exception as e:
            error_msg = str(e)
            if "invalid_grant" in error_msg.lower():
                return (False, "Gmail access expired — please reconnect")
            if "insufficient_scope" in error_msg.lower():
                return (False, "Missing Gmail permissions — please reconnect")
            return (False, f"Cannot access Gmail: {error_msg}")

    def infer_style_context(self) -> str:
        """Email style: professional, clear, appropriate greeting/sign-off."""
        return "email"
