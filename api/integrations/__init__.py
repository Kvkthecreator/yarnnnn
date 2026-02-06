"""
YARNNN Integration System

MCP-based integration layer for exporting deliverables to third-party services.
See ADR-026 for architectural decisions.

Modules:
- core/: MCP client management, token encryption, types
- providers/: Provider-specific implementations (Slack, Notion, etc.)
"""

from .core.client import MCPClientManager
from .core.tokens import TokenManager
from .core.types import (
    IntegrationProvider,
    IntegrationStatus,
    ExportResult,
    ExportStatus,
)

__all__ = [
    "MCPClientManager",
    "TokenManager",
    "IntegrationProvider",
    "IntegrationStatus",
    "ExportResult",
    "ExportStatus",
]
