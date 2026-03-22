"""
YARNNN Integration System

Platform integration layer for syncing context and delivering content.
See ADR-076 for architectural decisions.

All platforms use Direct API clients (ADR-131: Gmail/Calendar sunset):
- Slack: integrations/core/slack_client.py (SlackAPIClient)
- Notion: integrations/core/notion_client.py (NotionAPIClient)

Modules:
- core/: API clients, token encryption, types
- exporters/: Destination-specific delivery (Slack, Notion, Email)
- providers/: Provider-specific implementations
"""

from .core.tokens import TokenManager
from .core.types import (
    IntegrationProvider,
    IntegrationStatus,
    ExportResult,
    ExportStatus,
)

__all__ = [
    "TokenManager",
    "IntegrationProvider",
    "IntegrationStatus",
    "ExportResult",
    "ExportStatus",
]
