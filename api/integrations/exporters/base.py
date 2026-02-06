"""
Base classes for Destination Exporters - ADR-028

Defines the DestinationExporter abstract interface and supporting types.
All platform-specific exporters implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

from integrations.core.types import ExportResult, ExportStatus


@dataclass
class ExporterContext:
    """
    Context passed to exporters for a delivery operation.

    Contains user-specific auth info and metadata needed to authenticate
    with the destination platform.
    """
    user_id: str

    # Decrypted access token for the platform
    access_token: str

    # Platform-specific metadata (e.g., team_id for Slack)
    metadata: dict[str, Any]

    # Optional: refresh token for platforms that support it
    refresh_token: Optional[str] = None


class DestinationExporter(ABC):
    """
    Abstract base class for all destination exporters.

    Each exporter handles delivery to a specific platform (Slack, Notion, etc.).
    Exporters are stateless - authentication is passed via ExporterContext.

    Destination Schema:
        {
            "platform": "slack" | "notion" | "email" | "download",
            "target": str,         # Channel ID, page ID, email, or None for download
            "format": str,         # "message", "page", "html", "markdown"
            "options": dict        # Platform-specific options
        }
    """

    @property
    @abstractmethod
    def platform(self) -> str:
        """
        The platform identifier this exporter handles.

        Must match destination.platform in the deliverable schema.
        """
        pass

    @property
    def requires_auth(self) -> bool:
        """
        Whether this exporter requires OAuth authentication.

        Most exporters (Slack, Notion) require auth.
        Download exporter does not.
        """
        return True

    @abstractmethod
    async def deliver(
        self,
        destination: dict[str, Any],
        content: str,
        title: str,
        metadata: dict[str, Any],
        context: ExporterContext
    ) -> ExportResult:
        """
        Deliver content to the destination.

        Args:
            destination: The destination config from deliverable.destination
                {
                    "platform": "slack",
                    "target": "#team-updates" or "C123ABC",
                    "format": "message",
                    "options": {}
                }
            content: The content to deliver (markdown)
            title: Title of the deliverable
            metadata: Additional metadata (deliverable_id, version_id, etc.)
            context: Auth context with user tokens

        Returns:
            ExportResult with status, external_id, external_url
        """
        pass

    @abstractmethod
    def validate_destination(self, destination: dict[str, Any]) -> bool:
        """
        Validate that a destination config is valid for this exporter.

        Called during deliverable setup to verify destination config
        before saving.

        Args:
            destination: The destination config to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def infer_style_context(self) -> str:
        """
        Infer the style context for content generation.

        When a deliverable has a destination, the platform informs
        what style of content to generate:
        - Slack → casual, brief, emoji-friendly
        - Notion → structured, headers, detailed
        - Email → formal, professional

        Returns:
            Style context string that matches existing style profiles
        """
        return self.platform

    def get_supported_formats(self) -> list[str]:
        """
        Get the formats this exporter supports.

        Returns:
            List of format strings (e.g., ["message", "thread"])
        """
        return ["default"]

    async def verify_destination_access(
        self,
        destination: dict[str, Any],
        context: ExporterContext
    ) -> tuple[bool, Optional[str]]:
        """
        Verify the user has access to deliver to this destination.

        Called during deliverable setup to verify the bot/integration
        can access the target channel/page.

        Args:
            destination: The destination config
            context: Auth context

        Returns:
            (success, error_message) tuple
        """
        # Default: assume accessible if we have tokens
        return (True, None)
