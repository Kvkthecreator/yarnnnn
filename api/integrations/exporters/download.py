"""
Download Exporter - ADR-028

Provides local download capability (no external delivery).

This is the fallback when no destination is configured or when
user explicitly wants to download content locally.

Destination Schema:
    {
        "platform": "download",
        "target": null,
        "format": "markdown" | "html" | "pdf",
        "options": {}
    }
"""

import logging
from typing import Any, Optional

from integrations.core.types import ExportResult, ExportStatus
from .base import DestinationExporter, ExporterContext

logger = logging.getLogger(__name__)


class DownloadExporter(DestinationExporter):
    """
    Download exporter - enables local content download.

    Unlike other exporters, this doesn't send content anywhere.
    It returns the content in a format suitable for download.

    The frontend handles the actual download (creating blob, triggering download).
    """

    @property
    def platform(self) -> str:
        return "download"

    @property
    def requires_auth(self) -> bool:
        """Download doesn't require OAuth."""
        return False

    def get_supported_formats(self) -> list[str]:
        return ["markdown", "html", "pdf"]

    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """Validate download destination config."""
        # Format must be supported
        fmt = destination.get("format", "markdown")
        return fmt in self.get_supported_formats()

    async def deliver(
        self,
        destination: dict[str, Any],
        content: str,
        title: str,
        metadata: dict[str, Any],
        context: ExporterContext
    ) -> ExportResult:
        """
        Prepare content for download.

        For download, we don't actually "deliver" anywhere.
        We just return success with the content available for frontend download.
        """
        fmt = destination.get("format", "markdown")

        if fmt == "html":
            # Convert markdown to HTML
            try:
                import markdown
                html_content = markdown.markdown(content)
                processed_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 16px; border-radius: 6px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {html_content}
</body>
</html>"""
            except ImportError:
                # Fallback: wrap content in basic HTML
                processed_content = f"<html><head><title>{title}</title></head><body><pre>{content}</pre></body></html>"

        elif fmt == "pdf":
            # PDF generation would require additional library (weasyprint, etc.)
            # For now, return markdown with a note
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message="PDF export not yet implemented. Use markdown or HTML."
            )

        else:  # markdown
            processed_content = content

        logger.info(
            f"[DOWNLOAD_EXPORT] Prepared {fmt} download for user {context.user_id}, "
            f"title='{title}'"
        )

        return ExportResult(
            status=ExportStatus.SUCCESS,
            external_id=None,  # No external reference for downloads
            external_url=None,
            metadata={
                "format": fmt,
                "content": processed_content,  # Frontend uses this for download
                "filename": f"{self._sanitize_filename(title)}.{self._get_extension(fmt)}"
            }
        )

    def infer_style_context(self) -> str:
        """Download: general markdown style."""
        return "general"

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename."""
        # Remove or replace problematic characters
        import re
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        sanitized = sanitized.strip()
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized or "deliverable"

    def _get_extension(self, fmt: str) -> str:
        """Get file extension for format."""
        extensions = {
            "markdown": "md",
            "html": "html",
            "pdf": "pdf"
        }
        return extensions.get(fmt, "txt")
