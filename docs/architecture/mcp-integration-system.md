# MCP Integration System Architecture

> **Status**: Implementation Started
> **Created**: 2026-02-06
> **Updated**: 2026-02-06
> **Related**: ADR-026 (Integration Architecture)

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Database schema | ✅ Complete | Migration 023_integrations.sql |
| `MCPClientManager` | ✅ Complete | `api/integrations/core/client.py` |
| `TokenManager` | ✅ Complete | `api/integrations/core/tokens.py` |
| Types/Models | ✅ Complete | `api/integrations/core/types.py` |
| API routes | ✅ Complete | `api/routes/integrations.py` |
| OAuth flows | ⏳ Pending | Need Slack/Notion app setup |
| Provider implementations | ⏳ Pending | Slack, Notion providers |
| Frontend components | ⏳ Pending | Settings tab, export bar |

### Validated Technical Details

- **MCP SDK**: Official `mcp` package (v1.x, PyPI)
- **Transport**: Stdio subprocess (standard pattern)
- **Server commands**:
  - Slack: `npx @modelcontextprotocol/server-slack`
  - Notion: `npx @notionhq/notion-mcp-server --transport stdio`
  - Gmail: `npx @shinzolabs/gmail-mcp` (ADR-029)
- **Render**: Node.js/npx confirmed available

### Required Environment Variables

| Provider | Variables |
|----------|-----------|
| Slack | `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` |
| Notion | `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET` |
| Gmail | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |

> **Note**: These must be set on both `yarnnn-api` and `unified-scheduler` services in Render.

---

## Overview

This document defines the technical architecture for YARNNN's integration system, using MCP (Model Context Protocol) as the primary implementation stack. The design emphasizes:

1. **Scalability** - Easy to add new integrations
2. **Consistency** - Unified patterns across all integrations
3. **Separation of concerns** - Clean boundaries between layers
4. **Future-proof** - Designed for both managed and user-configured MCP

---

## Folder Structure

```
api/
├── integrations/                    # 🆕 Integration system root
│   ├── __init__.py
│   ├── core/                        # Core infrastructure
│   │   ├── __init__.py
│   │   ├── client.py               # MCPClientManager
│   │   ├── registry.py             # IntegrationRegistry
│   │   ├── auth.py                 # OAuth flow management
│   │   ├── tokens.py               # Token encryption/storage
│   │   └── types.py                # Shared types/interfaces
│   │
│   ├── providers/                   # Provider-specific implementations
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseIntegrationProvider
│   │   ├── slack/
│   │   │   ├── __init__.py
│   │   │   ├── provider.py         # SlackProvider(BaseIntegrationProvider)
│   │   │   ├── oauth.py            # Slack-specific OAuth
│   │   │   ├── formatters.py       # Content formatting for Slack
│   │   │   └── config.py           # MCP server config, scopes, etc.
│   │   ├── notion/
│   │   │   ├── __init__.py
│   │   │   ├── provider.py
│   │   │   ├── oauth.py
│   │   │   ├── formatters.py
│   │   │   └── config.py
│   │   └── google/                  # Future
│   │       └── ...
│   │
│   ├── export/                      # Export orchestration
│   │   ├── __init__.py
│   │   ├── service.py              # ExportService - main entry point
│   │   ├── formatters.py           # Non-MCP format conversions (email, PDF)
│   │   └── validators.py           # Pre-export validation
│   │
│   └── mcp_server/                  # YARNNN as MCP server (Phase 2)
│       ├── __init__.py
│       ├── server.py               # YarnnnMCPServer
│       ├── tools.py                # Tool definitions
│       └── handlers.py             # Tool handlers
│
├── routes/
│   ├── integrations.py             # 🆕 /api/integrations/* endpoints
│   └── ...
│
├── services/
│   └── ...                          # Existing services unchanged
│
└── jobs/
    ├── email.py                     # Existing email (non-MCP)
    └── ...

web/
├── lib/
│   ├── integrations/               # 🆕 Frontend integration utilities
│   │   ├── index.ts
│   │   ├── types.ts                # TypeScript types
│   │   ├── oauth.ts                # OAuth popup handling
│   │   └── api.ts                  # Integration API client
│   └── ...
│
├── components/
│   ├── integrations/               # 🆕 Integration UI components
│   │   ├── IntegrationCard.tsx     # Single integration display
│   │   ├── IntegrationList.tsx     # List of connected integrations
│   │   ├── ConnectButton.tsx       # OAuth initiation button
│   │   ├── DestinationPicker.tsx   # Channel/page selector
│   │   └── ExportActionBar.tsx     # Export buttons row
│   └── ...
│
├── app/(authenticated)/
│   ├── settings/
│   │   └── page.tsx                # Add "Integrations" tab
│   └── ...
│
└── contexts/
    └── IntegrationsContext.tsx     # 🆕 Global integration state
```

---

## Core Components

### 1. Integration Registry

Central registry of all available integrations. Single source of truth for what's available.

```python
# api/integrations/core/registry.py

from typing import Dict, Type
from .types import IntegrationConfig
from ..providers.base import BaseIntegrationProvider

class IntegrationRegistry:
    """
    Singleton registry of all available integrations.
    New integrations register here to become available.
    """

    _providers: Dict[str, Type[BaseIntegrationProvider]] = {}
    _configs: Dict[str, IntegrationConfig] = {}

    @classmethod
    def register(
        cls,
        provider_id: str,
        provider_class: Type[BaseIntegrationProvider],
        config: IntegrationConfig
    ):
        """Register a new integration provider."""
        cls._providers[provider_id] = provider_class
        cls._configs[provider_id] = config

    @classmethod
    def get_provider(cls, provider_id: str) -> Type[BaseIntegrationProvider]:
        """Get provider class by ID."""
        if provider_id not in cls._providers:
            raise ValueError(f"Unknown integration: {provider_id}")
        return cls._providers[provider_id]

    @classmethod
    def get_config(cls, provider_id: str) -> IntegrationConfig:
        """Get provider config by ID."""
        return cls._configs[provider_id]

    @classmethod
    def list_available(cls) -> list[IntegrationConfig]:
        """List all available integrations."""
        return list(cls._configs.values())

# Registration happens at module load
# api/integrations/providers/slack/__init__.py
from ..registry import IntegrationRegistry
from .provider import SlackProvider
from .config import SLACK_CONFIG

IntegrationRegistry.register("slack", SlackProvider, SLACK_CONFIG)
```

### 2. Base Integration Provider

Abstract base class that all providers implement. Enforces consistent interface.

```python
# api/integrations/providers/base.py

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass

@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    external_id: Optional[str] = None  # Slack message ts, Notion page id
    external_url: Optional[str] = None  # Link to view in external service
    error: Optional[str] = None

@dataclass
class Destination:
    """A target destination within a provider."""
    id: str              # channel_id, page_id, etc.
    name: str            # #team-updates, "Engineering Wiki"
    type: str            # channel, page, database, etc.
    metadata: dict = None

class BaseIntegrationProvider(ABC):
    """
    Base class for all integration providers.
    Each provider implements MCP client + provider-specific logic.
    """

    provider_id: str  # "slack", "notion", etc.

    def __init__(self, user_id: str, access_token: str, metadata: dict = None):
        self.user_id = user_id
        self.access_token = access_token
        self.metadata = metadata or {}

    @abstractmethod
    async def connect_mcp(self) -> None:
        """Initialize MCP client connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up MCP connection."""
        pass

    @abstractmethod
    async def list_destinations(self) -> list[Destination]:
        """List available destinations (channels, pages, etc.)."""
        pass

    @abstractmethod
    async def export(
        self,
        content: str,
        destination: Destination,
        title: Optional[str] = None,
        metadata: dict = None
    ) -> ExportResult:
        """Export content to a destination."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Check if the connection is still valid."""
        pass

    # Optional: Provider-specific formatting
    def format_content(self, markdown: str) -> Any:
        """Convert markdown to provider-specific format. Override if needed."""
        return markdown
```

### 3. MCP Client Manager

Manages MCP client connections, handles lifecycle and pooling.

```python
# api/integrations/core/client.py

from typing import Dict, Optional
from mcp import Client, ServerConfig
import asyncio

class MCPClientManager:
    """
    Manages MCP client connections to external servers.
    Handles connection pooling, lifecycle, and cleanup.
    """

    def __init__(self):
        self._clients: Dict[str, Client] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def get_client(
        self,
        user_id: str,
        provider_id: str,
        server_config: ServerConfig
    ) -> Client:
        """
        Get or create MCP client for user+provider.
        Thread-safe with connection pooling.
        """
        key = f"{user_id}:{provider_id}"

        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            if key not in self._clients:
                client = await Client.connect(server_config)
                self._clients[key] = client

            return self._clients[key]

    async def disconnect(self, user_id: str, provider_id: str) -> None:
        """Disconnect and remove a client."""
        key = f"{user_id}:{provider_id}"
        if key in self._clients:
            await self._clients[key].close()
            del self._clients[key]

    async def disconnect_user(self, user_id: str) -> None:
        """Disconnect all clients for a user."""
        keys_to_remove = [k for k in self._clients if k.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            await self._clients[key].close()
            del self._clients[key]

    async def cleanup(self) -> None:
        """Close all connections (for shutdown)."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()

# Global instance
mcp_client_manager = MCPClientManager()
```

### 4. Export Service

Main entry point for exporting content. Orchestrates provider selection and execution.

```python
# api/integrations/export/service.py

from typing import Optional
from ..core.registry import IntegrationRegistry
from ..core.tokens import TokenManager
from ..providers.base import ExportResult, Destination
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExportRequest:
    """Request to export content."""
    user_id: str
    provider_id: str            # "slack", "notion"
    destination_id: str         # channel_id, page_id
    content: str                # Markdown content
    title: Optional[str] = None
    deliverable_version_id: Optional[str] = None
    metadata: dict = None

class ExportService:
    """
    Orchestrates content export to external services.
    Main entry point for all export operations.
    """

    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager

    async def export(self, request: ExportRequest) -> ExportResult:
        """
        Export content to an external service.

        1. Load user's integration credentials
        2. Instantiate provider
        3. Connect MCP
        4. Execute export
        5. Log result
        """
        try:
            # Get credentials
            credentials = await self.token_manager.get_credentials(
                request.user_id,
                request.provider_id
            )
            if not credentials:
                return ExportResult(
                    success=False,
                    error=f"Not connected to {request.provider_id}"
                )

            # Get provider class
            provider_class = IntegrationRegistry.get_provider(request.provider_id)

            # Instantiate and connect
            provider = provider_class(
                user_id=request.user_id,
                access_token=credentials.access_token,
                metadata=credentials.metadata
            )
            await provider.connect_mcp()

            try:
                # Build destination
                destination = Destination(
                    id=request.destination_id,
                    name="",  # Will be looked up by provider if needed
                    type="unknown"
                )

                # Execute export
                result = await provider.export(
                    content=request.content,
                    destination=destination,
                    title=request.title,
                    metadata=request.metadata
                )

                # Log success/failure
                await self._log_export(request, result)

                return result

            finally:
                await provider.disconnect()

        except Exception as e:
            logger.exception(f"Export failed: {e}")
            return ExportResult(success=False, error=str(e))

    async def _log_export(
        self,
        request: ExportRequest,
        result: ExportResult
    ) -> None:
        """Log export attempt to database."""
        # TODO: Insert into export_log table
        pass

    async def list_destinations(
        self,
        user_id: str,
        provider_id: str
    ) -> list[Destination]:
        """List available destinations for a provider."""
        credentials = await self.token_manager.get_credentials(user_id, provider_id)
        if not credentials:
            return []

        provider_class = IntegrationRegistry.get_provider(provider_id)
        provider = provider_class(
            user_id=user_id,
            access_token=credentials.access_token,
            metadata=credentials.metadata
        )

        await provider.connect_mcp()
        try:
            return await provider.list_destinations()
        finally:
            await provider.disconnect()
```

---

## Provider Implementation Example: Slack

```python
# api/integrations/providers/slack/config.py

from ...core.types import IntegrationConfig

SLACK_CONFIG = IntegrationConfig(
    provider_id="slack",
    name="Slack",
    description="Send deliverables to Slack channels",
    icon="slack",  # Used by frontend
    oauth_url="https://slack.com/oauth/v2/authorize",
    scopes=["chat:write", "channels:read", "groups:read"],
    mcp_server="@modelcontextprotocol/server-slack",
    supports_destinations=True,
    destination_types=["channel", "dm"],
)
```

```python
# api/integrations/providers/slack/provider.py

from typing import Optional
from mcp import Client, ServerConfig
from ..base import BaseIntegrationProvider, ExportResult, Destination
from ...core.client import mcp_client_manager
from .formatters import markdown_to_slack_blocks

class SlackProvider(BaseIntegrationProvider):
    """Slack integration via MCP."""

    provider_id = "slack"

    def __init__(self, user_id: str, access_token: str, metadata: dict = None):
        super().__init__(user_id, access_token, metadata)
        self._client: Optional[Client] = None

    async def connect_mcp(self) -> None:
        """Initialize MCP connection to Slack server."""
        config = ServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-slack"],
            env={
                "SLACK_BOT_TOKEN": self.access_token,
                "SLACK_TEAM_ID": self.metadata.get("team_id", ""),
            }
        )
        self._client = await mcp_client_manager.get_client(
            self.user_id,
            self.provider_id,
            config
        )

    async def disconnect(self) -> None:
        """Disconnect MCP client."""
        # Connection pooling means we don't actually disconnect here
        self._client = None

    async def list_destinations(self) -> list[Destination]:
        """List Slack channels user can post to."""
        if not self._client:
            raise RuntimeError("Not connected")

        # Call MCP tool to list channels
        result = await self._client.call_tool(
            "list_channels",
            {"types": "public_channel,private_channel"}
        )

        destinations = []
        for channel in result.get("channels", []):
            destinations.append(Destination(
                id=channel["id"],
                name=f"#{channel['name']}",
                type="channel",
                metadata={"is_private": channel.get("is_private", False)}
            ))

        return destinations

    async def export(
        self,
        content: str,
        destination: Destination,
        title: Optional[str] = None,
        metadata: dict = None
    ) -> ExportResult:
        """Post message to Slack channel."""
        if not self._client:
            raise RuntimeError("Not connected")

        # Format content for Slack
        blocks = markdown_to_slack_blocks(content, title)

        # Call MCP tool
        result = await self._client.call_tool(
            "post_message",
            {
                "channel": destination.id,
                "blocks": blocks,
                "text": title or "New deliverable from YARNNN",  # Fallback
            }
        )

        if result.get("ok"):
            return ExportResult(
                success=True,
                external_id=result.get("ts"),
                external_url=f"https://slack.com/archives/{destination.id}/p{result.get('ts', '').replace('.', '')}"
            )
        else:
            return ExportResult(
                success=False,
                error=result.get("error", "Unknown Slack error")
            )

    async def validate_connection(self) -> bool:
        """Check if Slack connection is valid."""
        if not self._client:
            return False
        try:
            result = await self._client.call_tool("auth_test", {})
            return result.get("ok", False)
        except Exception:
            return False
```

```python
# api/integrations/providers/slack/formatters.py

def markdown_to_slack_blocks(markdown: str, title: str = None) -> list:
    """
    Convert markdown to Slack Block Kit format.

    Slack uses its own mrkdwn format which is similar but not identical
    to standard markdown. The MCP server may handle some of this,
    but we can pre-process for better control.
    """
    blocks = []

    # Header block if title provided
    if title:
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": title}
        })

    # Main content as section blocks
    # Split on double newlines to create multiple sections
    sections = markdown.split("\n\n")

    for section in sections:
        if section.strip():
            # Convert markdown syntax to mrkdwn
            mrkdwn = _markdown_to_mrkdwn(section)
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": mrkdwn}
            })

    # Context block with YARNNN attribution
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "Sent via <https://yarnnn.com|YARNNN>"
        }]
    })

    return blocks


def _markdown_to_mrkdwn(text: str) -> str:
    """Convert standard markdown to Slack mrkdwn."""
    import re

    # Bold: **text** or __text__ -> *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    text = re.sub(r'__(.+?)__', r'*\1*', text)

    # Italic: *text* or _text_ -> _text_
    # (Slack uses _ for italic, but we already converted ** to *)
    # This is tricky - skip for now, Slack will interpret

    # Links: [text](url) -> <url|text>
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<\2|\1>', text)

    # Code: `code` -> `code` (same)

    # Lists: - item -> • item
    text = re.sub(r'^- ', '• ', text, flags=re.MULTILINE)

    return text
```

---

## API Routes

```python
# api/routes/integrations.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.supabase import UserClient
from integrations.core.registry import IntegrationRegistry
from integrations.export.service import ExportService, ExportRequest

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ============================================================================
# List & Status
# ============================================================================

@router.get("/available")
async def list_available_integrations():
    """List all available integrations."""
    configs = IntegrationRegistry.list_available()
    return {
        "integrations": [
            {
                "id": c.provider_id,
                "name": c.name,
                "description": c.description,
                "icon": c.icon,
            }
            for c in configs
        ]
    }


@router.get("/connected")
async def list_connected_integrations(auth: UserClient):
    """List user's connected integrations."""
    # Query user_integrations table
    result = auth.client.table("user_integrations") \
        .select("provider, metadata, created_at") \
        .eq("user_id", auth.user_id) \
        .execute()

    return {
        "integrations": [
            {
                "provider": row["provider"],
                "connected_at": row["created_at"],
                "metadata": row.get("metadata", {}),
            }
            for row in result.data or []
        ]
    }


@router.delete("/{provider_id}")
async def disconnect_integration(provider_id: str, auth: UserClient):
    """Disconnect an integration."""
    auth.client.table("user_integrations") \
        .delete() \
        .eq("user_id", auth.user_id) \
        .eq("provider", provider_id) \
        .execute()

    return {"success": True}


# ============================================================================
# OAuth
# ============================================================================

class OAuthStartResponse(BaseModel):
    auth_url: str
    state: str


@router.get("/{provider_id}/oauth/start")
async def start_oauth(provider_id: str, auth: UserClient) -> OAuthStartResponse:
    """
    Start OAuth flow for an integration.
    Returns URL to redirect user to.
    """
    config = IntegrationRegistry.get_config(provider_id)
    # TODO: Build OAuth URL with state, scopes, redirect_uri
    # Store state in session/cache for callback verification
    pass


@router.get("/{provider_id}/oauth/callback")
async def oauth_callback(
    provider_id: str,
    code: str,
    state: str,
    auth: UserClient
):
    """
    OAuth callback handler.
    Exchange code for tokens and store.
    """
    # TODO: Verify state, exchange code, encrypt and store tokens
    pass


# ============================================================================
# Destinations
# ============================================================================

@router.get("/{provider_id}/destinations")
async def list_destinations(provider_id: str, auth: UserClient):
    """List available destinations for an integration."""
    export_service = ExportService(...)  # DI
    destinations = await export_service.list_destinations(
        auth.user_id,
        provider_id
    )

    return {
        "destinations": [
            {
                "id": d.id,
                "name": d.name,
                "type": d.type,
            }
            for d in destinations
        ]
    }


# ============================================================================
# Export
# ============================================================================

class ExportRequestBody(BaseModel):
    provider_id: str
    destination_id: str
    content: str
    title: Optional[str] = None
    deliverable_version_id: Optional[str] = None


@router.post("/export")
async def export_content(body: ExportRequestBody, auth: UserClient):
    """Export content to an external service."""
    export_service = ExportService(...)  # DI

    result = await export_service.export(ExportRequest(
        user_id=auth.user_id,
        provider_id=body.provider_id,
        destination_id=body.destination_id,
        content=body.content,
        title=body.title,
        deliverable_version_id=body.deliverable_version_id,
    ))

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "external_id": result.external_id,
        "external_url": result.external_url,
    }
```

---

## Frontend Components

### Integration Context

```typescript
// web/contexts/IntegrationsContext.tsx

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '@/lib/api/client';

interface Integration {
  provider: string;
  connectedAt: string;
  metadata: Record<string, unknown>;
}

interface Destination {
  id: string;
  name: string;
  type: string;
}

interface IntegrationsContextValue {
  integrations: Integration[];
  isLoading: boolean;
  refresh: () => Promise<void>;
  isConnected: (provider: string) => boolean;
  getDestinations: (provider: string) => Promise<Destination[]>;
  export: (provider: string, destinationId: string, content: string, title?: string) => Promise<{
    success: boolean;
    externalUrl?: string;
    error?: string;
  }>;
}

const IntegrationsContext = createContext<IntegrationsContextValue | null>(null);

export function IntegrationsProvider({ children }: { children: ReactNode }) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = async () => {
    try {
      const result = await api.integrations.listConnected();
      setIntegrations(result.integrations);
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const isConnected = (provider: string) =>
    integrations.some(i => i.provider === provider);

  const getDestinations = async (provider: string) => {
    const result = await api.integrations.listDestinations(provider);
    return result.destinations;
  };

  const exportContent = async (
    provider: string,
    destinationId: string,
    content: string,
    title?: string
  ) => {
    return api.integrations.export({
      provider_id: provider,
      destination_id: destinationId,
      content,
      title,
    });
  };

  return (
    <IntegrationsContext.Provider
      value={{
        integrations,
        isLoading,
        refresh,
        isConnected,
        getDestinations,
        export: exportContent,
      }}
    >
      {children}
    </IntegrationsContext.Provider>
  );
}

export function useIntegrations() {
  const context = useContext(IntegrationsContext);
  if (!context) {
    throw new Error('useIntegrations must be used within IntegrationsProvider');
  }
  return context;
}
```

### Export Action Bar

```typescript
// web/components/integrations/ExportActionBar.tsx

import { useState } from 'react';
import { Copy, Send, FileDown, Check, Loader2 } from 'lucide-react';
import { useIntegrations } from '@/contexts/IntegrationsContext';
import { DestinationPicker } from './DestinationPicker';
import { cn } from '@/lib/utils';

interface ExportActionBarProps {
  content: string;
  title?: string;
  onExportComplete?: (provider: string, url?: string) => void;
}

export function ExportActionBar({
  content,
  title,
  onExportComplete,
}: ExportActionBarProps) {
  const { isConnected, export: exportContent } = useIntegrations();
  const [copied, setCopied] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState<string | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = async (provider: string, destinationId: string) => {
    setExporting(provider);
    setShowPicker(null);

    try {
      const result = await exportContent(provider, destinationId, content, title);
      if (result.success) {
        onExportComplete?.(provider, result.externalUrl);
      }
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {/* Copy */}
      <button
        onClick={handleCopy}
        className="px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted flex items-center gap-1.5"
      >
        {copied ? (
          <>
            <Check className="w-4 h-4 text-green-600" />
            Copied
          </>
        ) : (
          <>
            <Copy className="w-4 h-4" />
            Copy
          </>
        )}
      </button>

      {/* Slack */}
      <div className="relative">
        <button
          onClick={() => isConnected('slack')
            ? setShowPicker(showPicker === 'slack' ? null : 'slack')
            : window.location.href = '/settings?tab=integrations'
          }
          disabled={exporting === 'slack'}
          className={cn(
            "px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted flex items-center gap-1.5",
            !isConnected('slack') && "opacity-60"
          )}
        >
          {exporting === 'slack' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          Slack
        </button>
        {showPicker === 'slack' && (
          <DestinationPicker
            provider="slack"
            onSelect={(dest) => handleExport('slack', dest.id)}
            onClose={() => setShowPicker(null)}
          />
        )}
      </div>

      {/* Notion */}
      <div className="relative">
        <button
          onClick={() => isConnected('notion')
            ? setShowPicker(showPicker === 'notion' ? null : 'notion')
            : window.location.href = '/settings?tab=integrations'
          }
          disabled={exporting === 'notion'}
          className={cn(
            "px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted flex items-center gap-1.5",
            !isConnected('notion') && "opacity-60"
          )}
        >
          {exporting === 'notion' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileDown className="w-4 h-4" />
          )}
          Notion
        </button>
        {showPicker === 'notion' && (
          <DestinationPicker
            provider="notion"
            onSelect={(dest) => handleExport('notion', dest.id)}
            onClose={() => setShowPicker(null)}
          />
        )}
      </div>

      {/* Download */}
      <button
        onClick={() => {/* TODO: Download as PDF/MD */}}
        className="px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted flex items-center gap-1.5"
      >
        <FileDown className="w-4 h-4" />
        Download
      </button>
    </div>
  );
}
```

---

## Database Schema

```sql
-- migrations/xxx_user_integrations.sql

-- User's connected integrations
CREATE TABLE user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- 'slack', 'notion', etc.

    -- Encrypted OAuth tokens
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,

    -- Provider-specific metadata
    metadata JSONB DEFAULT '{}',  -- { team_id, workspace_name, etc. }

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,  -- Token expiry if applicable

    UNIQUE(user_id, provider)
);

-- RLS: Users can only see their own integrations
ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own integrations"
    ON user_integrations
    FOR ALL
    USING (auth.uid() = user_id);


-- Deliverable export preferences
CREATE TABLE deliverable_export_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,

    -- Destination config
    destination_id TEXT NOT NULL,      -- channel_id, page_id
    destination_name TEXT,             -- #team-updates, "Wiki Page"
    destination_metadata JSONB DEFAULT '{}',

    -- Auto-export on approval
    auto_export BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(deliverable_id, provider)
);

-- RLS via deliverable ownership
ALTER TABLE deliverable_export_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own deliverable export prefs"
    ON deliverable_export_preferences
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM deliverables d
            WHERE d.id = deliverable_id AND d.user_id = auth.uid()
        )
    );


-- Export history log
CREATE TABLE export_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    deliverable_version_id UUID REFERENCES deliverable_versions(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,

    -- Destination
    destination_id TEXT,
    destination_name TEXT,

    -- Result
    status TEXT NOT NULL,  -- 'success', 'failed', 'pending'
    error_message TEXT,
    external_id TEXT,      -- Slack ts, Notion page id
    external_url TEXT,     -- Link to view

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for querying user's export history
CREATE INDEX idx_export_log_user ON export_log(user_id, created_at DESC);
CREATE INDEX idx_export_log_deliverable ON export_log(deliverable_version_id);
```

---

## Adding New Integrations

To add a new integration (e.g., Google Docs):

### 1. Create Provider Directory

```
api/integrations/providers/google/
├── __init__.py       # Register with IntegrationRegistry
├── provider.py       # GoogleDocsProvider(BaseIntegrationProvider)
├── oauth.py          # Google-specific OAuth
├── formatters.py     # Markdown → Google Docs format
└── config.py         # GOOGLE_CONFIG
```

### 2. Implement Provider

```python
# api/integrations/providers/google/provider.py

from ..base import BaseIntegrationProvider, ExportResult, Destination

class GoogleDocsProvider(BaseIntegrationProvider):
    provider_id = "google"

    async def connect_mcp(self) -> None:
        # Connect to Google Drive MCP server
        pass

    async def list_destinations(self) -> list[Destination]:
        # List folders/recent docs
        pass

    async def export(self, content, destination, title, metadata) -> ExportResult:
        # Create Google Doc via MCP
        pass

    async def disconnect(self) -> None:
        pass

    async def validate_connection(self) -> bool:
        pass
```

### 3. Register

```python
# api/integrations/providers/google/__init__.py

from ...core.registry import IntegrationRegistry
from .provider import GoogleDocsProvider
from .config import GOOGLE_CONFIG

IntegrationRegistry.register("google", GoogleDocsProvider, GOOGLE_CONFIG)
```

### 4. Import in Main

```python
# api/integrations/__init__.py

# Import all providers to trigger registration
from .providers import slack, notion, google  # noqa
```

That's it - the integration is now available throughout the system.

---

## Security Considerations

### Token Encryption

```python
# api/integrations/core/tokens.py

from cryptography.fernet import Fernet
import os

class TokenManager:
    """Manages encrypted storage of OAuth tokens."""

    def __init__(self):
        key = os.environ.get("INTEGRATION_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("INTEGRATION_ENCRYPTION_KEY not set")
        self.fernet = Fernet(key.encode())

    def encrypt(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()

    async def store_credentials(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str = None,
        metadata: dict = None,
        client: Any = None  # Supabase client
    ) -> None:
        """Encrypt and store credentials."""
        data = {
            "user_id": user_id,
            "provider": provider,
            "access_token_encrypted": self.encrypt(access_token),
            "metadata": metadata or {},
        }
        if refresh_token:
            data["refresh_token_encrypted"] = self.encrypt(refresh_token)

        await client.table("user_integrations").upsert(data).execute()

    async def get_credentials(
        self,
        user_id: str,
        provider: str,
        client: Any = None
    ) -> Optional[Credentials]:
        """Retrieve and decrypt credentials."""
        result = await client.table("user_integrations") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("provider", provider) \
            .single() \
            .execute()

        if not result.data:
            return None

        return Credentials(
            access_token=self.decrypt(result.data["access_token_encrypted"]),
            refresh_token=self.decrypt(result.data["refresh_token_encrypted"])
                if result.data.get("refresh_token_encrypted") else None,
            metadata=result.data.get("metadata", {}),
        )
```

### Scope Minimization

Each provider requests minimum necessary scopes:

| Provider | Scopes | Justification |
|----------|--------|---------------|
| Slack | `chat:write`, `channels:read` | Post messages, list channels |
| Notion | `read_content`, `insert_content` | Create pages, query databases |
| Google | `drive.file` | Only files created by app |

---

## Testing Strategy

### Unit Tests

```python
# api/integrations/tests/test_slack_provider.py

import pytest
from unittest.mock import AsyncMock, patch
from integrations.providers.slack.provider import SlackProvider

@pytest.fixture
def slack_provider():
    return SlackProvider(
        user_id="test-user",
        access_token="xoxb-test-token",
        metadata={"team_id": "T12345"}
    )

async def test_list_destinations(slack_provider):
    with patch.object(slack_provider, '_client') as mock_client:
        mock_client.call_tool = AsyncMock(return_value={
            "channels": [
                {"id": "C123", "name": "general", "is_private": False},
                {"id": "C456", "name": "team", "is_private": True},
            ]
        })

        await slack_provider.connect_mcp()
        destinations = await slack_provider.list_destinations()

        assert len(destinations) == 2
        assert destinations[0].name == "#general"
        assert destinations[1].metadata["is_private"] == True
```

### Integration Tests

```python
# api/integrations/tests/test_export_service.py

async def test_export_to_slack_success():
    """Full export flow with mocked MCP."""
    # Test the complete flow from ExportService through provider
    pass

async def test_export_without_connection():
    """Should return error if not connected."""
    pass

async def test_export_logs_result():
    """Should log to export_log table."""
    pass
```

---

## Changelog

### 2026-02-06: Initial Architecture

- Defined folder structure for scalable integration system
- Core components: Registry, BaseProvider, MCPClientManager, ExportService
- Slack provider implementation example
- API routes for integrations management
- Frontend context and components
- Database schema with encryption
- Guide for adding new integrations
