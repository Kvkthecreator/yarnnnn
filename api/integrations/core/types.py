"""
Integration type definitions.

Shared types for the integration system.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime


class IntegrationProvider(str, Enum):
    """Supported integration providers."""
    SLACK = "slack"
    NOTION = "notion"
    GOOGLE = "google"
    EMAIL = "email"  # Native, not MCP
    DOWNLOAD = "download"  # Native, not MCP


class IntegrationStatus(str, Enum):
    """Status of a user's integration connection."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class ExportStatus(str, Enum):
    """Status of an export operation."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class ExportResult(BaseModel):
    """Result of an export operation."""
    status: ExportStatus
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: dict[str, Any] = {}


class IntegrationInfo(BaseModel):
    """User-facing integration information (no tokens)."""
    id: str
    provider: IntegrationProvider
    status: IntegrationStatus
    workspace_name: Optional[str] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


class ExportDestination(BaseModel):
    """Export destination configuration."""
    provider: IntegrationProvider
    # Provider-specific destination details
    # Slack: { channel_id, channel_name }
    # Notion: { page_id, page_title }
    destination: dict[str, Any]


class SlackDestination(BaseModel):
    """Slack-specific destination."""
    channel_id: str
    channel_name: Optional[str] = None


class NotionDestination(BaseModel):
    """Notion-specific destination."""
    page_id: str
    page_title: Optional[str] = None
    database_id: Optional[str] = None
