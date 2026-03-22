"""
Resend Exporter - ADR-066 Email-First Delivery

Delivers agent content via Resend API (server-side, no user OAuth required).
ADR-131: This is now the sole email delivery channel (GmailExporter removed).

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
    ADR-131: Sole email delivery channel (GmailExporter removed with Gmail sunset).
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
        from services.platform_output import generate_email_html

        target = destination.get("target")
        if not target:
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="No recipient email specified",
            )

        options = destination.get("options", {})
        # Include version/timestamp by default so each run is visibly distinct in inbox threads.
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        timestamp_str = now_utc.strftime("%b %-d %H:%M UTC")
        version_number = metadata.get("version_number")
        if version_number:
            default_subject = f"{title} v{version_number} — {timestamp_str}"
        else:
            default_subject = f"{title} — {timestamp_str}"
        subject = options.get("subject", default_subject)

        # Generate HTML from markdown content
        platform_variant = metadata.get("platform_variant")
        agent_id = metadata.get("agent_id", "")
        try:
            html_body = generate_email_html(
                content=content,
                variant=platform_variant or "default",
                metadata={
                    "title": title,
                    "recipient": target,
                    "agent_id": agent_id,
                    "version_number": metadata.get("version_number"),
                    "mode": metadata.get("mode"),
                    "date": options.get("date", ""),
                    "email_count": options.get("email_count", ""),
                    "is_draft": False,
                },
            )
        except Exception as e:
            logger.warning(f"[RESEND_EXPORT] HTML generation failed, using plain: {e}")
            html_body = f"<html><body><pre style='white-space:pre-wrap;font-family:sans-serif;'>{content}</pre></body></html>"

        # ADR-118: Query for rendered artifacts and include download links
        try:
            agent_id = metadata.get("agent_id", "")
            if agent_id:
                from services.supabase import get_service_client
                svc = get_service_client()
                rendered = (
                    svc.table("workspace_files")
                    .select("path, content_url, content_type, metadata")
                    .eq("user_id", context.user_id)
                    .like("path", "/agents/%/outputs/%")
                    .not_.is_("content_url", "null")
                    .order("updated_at", desc=True)
                    .limit(5)
                    .execute()
                )
                if rendered.data:
                    links = []
                    for f in rendered.data:
                        fname = f["path"].rsplit("/", 1)[-1]
                        url = f["content_url"]
                        size = (f.get("metadata") or {}).get("size_bytes", 0)
                        size_str = f" ({size // 1024}KB)" if size > 0 else ""
                        links.append(
                            f'<li><a href="{url}" style="color:#6366f1;text-decoration:underline;">'
                            f'{fname}</a>{size_str}</li>'
                        )
                    if links:
                        attachment_html = (
                            '<div style="margin-top:24px;padding:16px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">'
                            '<p style="margin:0 0 8px 0;font-weight:600;font-size:14px;">Attachments</p>'
                            f'<ul style="margin:0;padding-left:20px;">{"".join(links)}</ul>'
                            '</div>'
                        )
                        html_body = html_body.replace("</body>", f"{attachment_html}</body>")
        except Exception as e:
            logger.debug(f"[RESEND_EXPORT] Rendered artifact query failed (non-fatal): {e}")

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
