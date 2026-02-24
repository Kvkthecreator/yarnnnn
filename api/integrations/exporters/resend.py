"""
Resend Exporter - ADR-066 Email-First Delivery

Delivers deliverable content via Resend API (server-side, no user OAuth required).

This is the default email delivery channel. Unlike GmailExporter (which requires
the user's Google OAuth refresh_token), ResendExporter works for all users
regardless of their platform connections.

GmailExporter remains available for explicit Gmail draft/send operations that
require appearing as the user's own email. ResendExporter handles the common
case: delivering formatted content to the user's inbox from noreply@yarnnn.com.

Destination Schema:
    {
        "platform": "email",
        "target": "user@example.com",
        "format": "html" | "send",
        "options": {
            "subject": "Custom subject"
        }
    }
"""

import logging
from typing import Any, Optional

from integrations.core.types import ExportResult, ExportStatus
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)


class ResendExporter(DestinationExporter):
    """
    Delivers content via Resend API — no user OAuth required.

    Advantages over GmailExporter for default delivery:
    - Works for all users (no Google connection needed)
    - Server-side only (no token refresh issues)
    - Consistent sender: noreply@yarnnn.com
    - Free tier: 3,000 emails/month; Pro: $20/mo for 50k

    GmailExporter remains for:
    - Creating Gmail drafts (requires OAuth)
    - Sending as the user's own address (requires OAuth)
    """

    @property
    def platform(self) -> str:
        return "email"

    @property
    def requires_auth(self) -> bool:
        """Resend uses server-side API key, not user OAuth."""
        return False

    def get_supported_formats(self) -> list[str]:
        return ["html", "send"]

    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """Validate email destination config."""
        target = destination.get("target")
        return bool(target and "@" in target)

    async def deliver(
        self,
        destination: dict[str, Any],
        content: str,
        title: str,
        metadata: dict[str, Any],
        context: ExporterContext,
    ) -> ExportResult:
        """Deliver content via Resend API."""
        from jobs.email import send_email
        from services.platform_output import generate_gmail_html

        target = destination.get("target")
        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No recipient email specified",
            )

        options = destination.get("options", {})
        subject = options.get("subject", title)

        # Generate HTML from markdown content
        platform_variant = metadata.get("platform_variant")
        deliverable_id = metadata.get("deliverable_id", "")
        try:
            html_body = generate_gmail_html(
                content=content,
                variant=platform_variant or "default",
                metadata={
                    "title": subject,
                    "recipient": target,
                    "deliverable_id": deliverable_id,
                    "date": options.get("date", ""),
                    "email_count": options.get("email_count", ""),
                    "is_draft": False,
                },
            )
        except Exception as e:
            logger.warning(f"[RESEND_EXPORT] HTML generation failed, using plain: {e}")
            html_body = f"<html><body><pre style='white-space:pre-wrap;font-family:sans-serif;'>{content}</pre></body></html>"

        try:
            result = await send_email(
                to=target,
                subject=subject,
                html=html_body,
                text=content,  # Plain text fallback = raw markdown
            )

            if result.success:
                logger.info(f"[RESEND_EXPORT] Delivered to {target}, message_id={result.message_id}")
                return ExportResult(
                    status=ExportStatus.SUCCESS,
                    external_id=result.message_id,
                    metadata={
                        "format": "html",
                        "recipient": target,
                        "channel": "resend",
                    },
                )
            else:
                logger.error(f"[RESEND_EXPORT] Failed to deliver to {target}: {result.error}")
                return ExportResult(
                    status=ExportStatus.FAILED,
                    error_message=result.error or "Resend delivery failed",
                )

        except Exception as e:
            logger.error(f"[RESEND_EXPORT] Exception delivering to {target}: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e),
            )

    async def verify_destination_access(
        self,
        destination: dict[str, Any],
        context: ExporterContext,
    ) -> tuple[bool, Optional[str]]:
        """Verify Resend is configured."""
        import os

        if not os.environ.get("RESEND_API_KEY"):
            return (False, "RESEND_API_KEY not configured")
        return (True, None)

    def infer_style_context(self) -> str:
        """Email style: professional, clear."""
        return "email"
