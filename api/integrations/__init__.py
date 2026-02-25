"""
YARNNN Integration System

Platform integration layer for syncing context and delivering content.
See ADR-076 for architectural decisions.

All platforms use Direct API clients:
- Slack: integrations/core/slack_client.py (SlackAPIClient)
- Notion: integrations/core/notion_client.py (NotionAPIClient)
- Gmail/Calendar: integrations/core/google_client.py (GoogleAPIClient)

Modules:
- core/: API clients, token encryption, types
- exporters/: Destination-specific delivery (Slack, Notion, Gmail, Email)
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
