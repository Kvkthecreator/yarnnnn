"""
Destination Exporters - ADR-028

Platform-agnostic export infrastructure for destination-first deliverables.

The key insight: "The deliverable isn't the content. It's the commitment to
deliver something to a destination at the right time."

Each exporter implements:
- deliver(destination, content, title, metadata) → ExportResult
- validate_destination(destination) → bool
- infer_style_context() → str

Usage:
    from integrations.exporters import get_exporter_registry

    registry = get_exporter_registry()
    exporter = registry.get("slack")
    result = await exporter.deliver(destination, content, title, metadata)
"""

from .base import DestinationExporter, ExporterContext
from .registry import ExporterRegistry, get_exporter_registry
from .slack import SlackExporter
from .notion import NotionExporter
from .download import DownloadExporter
from .gmail import GmailExporter

__all__ = [
    "DestinationExporter",
    "ExporterContext",
    "ExporterRegistry",
    "get_exporter_registry",
    "SlackExporter",
    "NotionExporter",
    "DownloadExporter",
    "GmailExporter",
]
