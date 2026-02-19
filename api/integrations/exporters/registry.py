"""
Exporter Registry - ADR-028

Central registry for all destination exporters.
Provides a unified way to get an exporter by platform name.
"""

import logging
from typing import Optional

from .base import DestinationExporter

logger = logging.getLogger(__name__)


class ExporterRegistry:
    """
    Registry of all available destination exporters.

    Usage:
        registry = ExporterRegistry()
        registry.register(SlackExporter())
        registry.register(NotionExporter())

        exporter = registry.get("slack")
        if exporter:
            result = await exporter.deliver(...)
    """

    def __init__(self):
        self._exporters: dict[str, DestinationExporter] = {}

    def register(self, exporter: DestinationExporter) -> None:
        """
        Register an exporter.

        Args:
            exporter: The exporter instance to register
        """
        platform = exporter.platform
        if platform in self._exporters:
            logger.warning(f"[EXPORTERS] Overwriting existing exporter for {platform}")
        self._exporters[platform] = exporter
        logger.debug(f"[EXPORTERS] Registered exporter for {platform}")

    def get(self, platform: str) -> Optional[DestinationExporter]:
        """
        Get an exporter by platform name.

        Args:
            platform: The platform identifier (e.g., "slack", "notion")

        Returns:
            The exporter instance, or None if not found
        """
        return self._exporters.get(platform)

    def get_or_raise(self, platform: str) -> DestinationExporter:
        """
        Get an exporter by platform name, raising if not found.

        Args:
            platform: The platform identifier

        Returns:
            The exporter instance

        Raises:
            ValueError: If no exporter is registered for the platform
        """
        exporter = self.get(platform)
        if not exporter:
            available = list(self._exporters.keys())
            raise ValueError(
                f"No exporter registered for platform '{platform}'. "
                f"Available: {available}"
            )
        return exporter

    def list_platforms(self) -> list[str]:
        """
        List all registered platform names.

        Returns:
            List of platform identifiers
        """
        return list(self._exporters.keys())

    def list_exporters(self) -> list[DestinationExporter]:
        """
        List all registered exporters.

        Returns:
            List of exporter instances
        """
        return list(self._exporters.values())


# Global registry instance
_registry: Optional[ExporterRegistry] = None


def get_exporter_registry() -> ExporterRegistry:
    """
    Get the global exporter registry.

    The registry is lazily initialized with all available exporters.

    Returns:
        The global ExporterRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ExporterRegistry()
        _initialize_default_exporters(_registry)
    return _registry


def _initialize_default_exporters(registry: ExporterRegistry) -> None:
    """
    Initialize the registry with default exporters.

    Called once when the registry is first accessed.
    """
    # Import here to avoid circular imports
    from .slack import SlackExporter
    from .notion import NotionExporter
    from .download import DownloadExporter
    from .gmail import GmailExporter  # ADR-029

    registry.register(SlackExporter())
    registry.register(NotionExporter())
    registry.register(DownloadExporter())
    registry.register(GmailExporter())  # ADR-029

    # Alias "email" to "gmail" for email-first delivery
    # Frontend uses "email" platform, backend has "gmail" exporter
    gmail_exporter = registry.get("gmail")
    if gmail_exporter:
        registry._exporters["email"] = gmail_exporter
        logger.debug("[EXPORTERS] Added 'email' alias for 'gmail' exporter")

    logger.info(f"[EXPORTERS] Initialized registry with: {registry.list_platforms()}")
