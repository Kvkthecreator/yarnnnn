# MCP Integration System Architecture

> **Status**: Implemented
> **Created**: 2026-02-06
> **Updated**: 2026-02-12
> **Related**: ADR-026 (Integration Architecture), ADR-050 (MCP Gateway Architecture)

---

## Architecture Overview

**CRITICAL DISTINCTION**: YARNNN uses TWO different backends for platform integrations:

| Platform | Backend | Client Class | Transport | Status |
|----------|---------|--------------|-----------|--------|
| **Slack** | MCP Gateway | `MCPManager` | Local (stdio) | ✅ Working |
| **Notion** | Direct API | `NotionAPIClient` | REST API | ✅ Working |
| **Gmail** | Direct API | `GoogleAPIClient` | REST API | ✅ Working |
| **Calendar** | Direct API | `GoogleAPIClient` | REST API | ✅ Working |

### Why Two Backends?

- **Slack**: Uses `@modelcontextprotocol/server-slack` via local stdio transport (subprocess). Only platform where MCP works with OAuth tokens.
- **Notion/Gmail/Calendar**: Use platform REST APIs directly from Python. See "MCP OAuth Compatibility" below.

### MCP OAuth Compatibility (Learned 2026-02-12)

**Key Learning**: MCP servers have varying auth models. Not all support OAuth tokens.

| Platform | MCP Options Tested | Result | Our Solution |
|----------|-------------------|--------|--------------|
| **Slack** | `@modelcontextprotocol/server-slack` | ✅ Works with OAuth | MCP Gateway |
| **Notion** | `@notionhq/notion-mcp-server` | ❌ Requires `ntn_...` internal tokens | Direct API |
| **Notion** | `mcp.notion.com` (hosted) | ❌ Manages own OAuth sessions | Direct API |
| **Gmail** | No suitable MCP server | N/A | Direct API |
| **Calendar** | No suitable MCP server | N/A | Direct API |

**Why Notion MCP Failed (both options):**

1. **Open-source MCP** (`@notionhq/notion-mcp-server`):
   - Requires internal integration tokens (`ntn_...`)
   - These are created in Notion Developer Portal for private workspace integrations
   - YARNNN uses OAuth (public integration) = incompatible

2. **Hosted MCP** (`mcp.notion.com/mcp`):
   - Designed for direct user-to-server auth (Claude Desktop, Cursor)
   - Manages its own OAuth sessions internally
   - Cannot accept tokens passed from intermediary platforms
   - Error: `{"error":"invalid_token","error_description":"Invalid token format"}`

**Architecture Principle: Single Implementation Path**

Each platform has ONE integration path. No fallbacks or dual approaches:

```
✅ Good: Slack → MCP Gateway (only)
✅ Good: Notion → Direct API (only)
✅ Good: Gmail → Direct API (only)
❌ Bad: Platform → try MCP, fallback to Direct API
```

See [ADR-050](../adr/ADR-050-mcp-gateway-architecture.md) for the full architectural decision and learnings.

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Database schema | ✅ Complete | Migration 023_integrations.sql |
| `MCPManager` | ✅ Complete | `api/integrations/core/client.py` (Slack ONLY via gateway) |
| `NotionAPIClient` | ✅ Complete | `api/integrations/core/notion_client.py` (Notion Direct API) |
| `GoogleAPIClient` | ✅ Complete | `api/integrations/core/google_client.py` (Gmail/Calendar) |
| `TokenManager` | ✅ Complete | `api/integrations/core/tokens.py` |
| Types/Models | ✅ Complete | `api/integrations/core/types.py` |
| API routes | ✅ Complete | `api/routes/integrations.py` |
| MCP Gateway | ✅ Complete | `mcp-gateway/` - Slack only (stdio transport) |
| OAuth flows | ✅ Complete | All four platforms |
| Platform tools | ✅ Complete | All platforms working |

### Client Separation (Clean Architecture)

Each platform has ONE client. No dual-path code.

```
api/integrations/core/
├── client.py          # MCPManager - Slack ONLY (MCP protocol via Gateway)
├── notion_client.py   # NotionAPIClient - Notion (Direct API to api.notion.com)
├── google_client.py   # GoogleAPIClient - Gmail/Calendar (Direct API)
├── tokens.py          # TokenManager - OAuth token management
└── types.py           # Shared types/interfaces
```

### MCP Gateway (Node.js Service)

The MCP Gateway runs as a separate Render service and handles MCP protocol communication:
- URL: `yarnnn-mcp-gateway.onrender.com`
- **Slack ONLY**: `@modelcontextprotocol/server-slack` via stdio subprocess
- **Why Slack only**: Only MCP server that works with OAuth tokens (see ADR-050)

### Required Environment Variables

| Provider | Variables | Backend |
|----------|-----------|---------|
| Slack | `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` | MCP Gateway |
| Notion | `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET` | Direct API (yarnnn-api) |
| Gmail/Calendar | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Direct API |

> **Note**: Google and Notion credentials needed on `yarnnn-api`. Slack credentials needed on `yarnnn-mcp-gateway`.

---

## Default Landing Zones

Each platform has a default output destination so user owns the output:

| Platform | Default Destination | Metadata Key | Backend |
|----------|---------------------|--------------|---------|
| Slack | User's DM to self | `authed_user_id` | MCP Gateway |
| Notion | User's designated page | `designated_page_id` | Direct API |
| Gmail | Draft to user's email | `user_email` | Direct API |
| Calendar | User's designated calendar | `designated_calendar_id` | Direct API |

**Designated Settings UI**:
- Notion: Users set output page at `/context/notion`
- Calendar: Users set default calendar at `/context/calendar`

---

## Implemented Architecture

> The sections below reflect the **actual implemented state** as of 2026-02-19.
> The original draft (2026-02-06) contained placeholder code and abstract patterns that were superseded during implementation.

---

## Folder Structure

```
api/
├── integrations/
│   ├── core/
│   │   ├── client.py          # MCPClientManager — Slack ONLY (MCP protocol via Gateway)
│   │   ├── notion_client.py   # NotionAPIClient — Notion Direct API (api.notion.com)
│   │   ├── google_client.py   # GoogleAPIClient — Gmail/Calendar Direct API
│   │   ├── tokens.py          # TokenManager — OAuth token encryption/storage
│   │   └── types.py           # ExportResult, ExportStatus, IntegrationProvider
│   │
│   └── exporters/             # Deliverable destination exporters (ADR-028)
│       ├── base.py            # DestinationExporter ABC, ExporterContext
│       ├── slack.py           # SlackExporter → MCP Gateway (HTTP)
│       ├── notion.py          # NotionExporter → Direct API (POST /v1/pages)
│       ├── gmail.py           # GmailExporter → Direct API (GoogleAPIClient)
│       ├── download.py        # DownloadExporter (no auth needed)
│       └── registry.py        # ExporterRegistry singleton
│
├── services/
│   ├── platform_tools.py      # TP platform tool definitions + handlers
│   ├── mcp_gateway.py         # HTTP client for MCP Gateway (Slack calls)
│   └── delivery.py            # Governance-aware delivery orchestration
│
└── routes/
    └── integrations.py        # OAuth flows + platform_connections CRUD

mcp-gateway/                   # Node.js service on Render
├── src/
│   ├── mcp/client-manager.ts  # MCP session management (Slack npx subprocess)
│   └── routes/tools.ts        # POST /api/mcp/tools/:provider/:tool
└── package.json
```

---

## Data Flow: TP Platform Tools (Conversational)

```
User: "what's in #daily-work?"
         │
         ▼
Thinking Partner (TP)
  calls: platform_slack_list_channels()
  calls: platform_slack_get_channel_history(channel_id="C...")
         │
         ▼
api/services/platform_tools.py
  _handle_mcp_tool() → Slack
  _handle_notion_tool() → Notion
  _handle_google_tool() → Gmail/Calendar
         │
    ┌────┴──────────────────────────────────┐
    │ Slack                                  │ Notion / Gmail / Calendar
    ▼                                        ▼
services/mcp_gateway.py             NotionAPIClient / GoogleAPIClient
  POST https://yarnnn-mcp-gateway     Direct REST API calls
    .onrender.com/api/mcp/tools/      (no Node.js, no subprocess)
    slack/{tool}
         │
         ▼
mcp-gateway/ (Node.js on Render)
  @modelcontextprotocol/server-slack
  (npx subprocess, stdio transport)
```

---

## Data Flow: Deliverable Export (Scheduled / Approval)

```
Deliverable approved (governance=semi_auto) or scheduled run
         │
         ▼
services/delivery.py: deliver_version()
  → get ExporterContext (decrypt tokens from platform_connections)
  → get exporter from ExporterRegistry
         │
    ┌────┴─────────────────────────────────┐
    │ Slack                │ Notion         │ Gmail
    ▼                      ▼               ▼
SlackExporter          NotionExporter   GmailExporter
  call_platform_tool()   POST /v1/pages   GoogleAPIClient
  (MCP Gateway HTTP)     (Direct API)     .create_gmail_draft()
                                          .send_gmail_message()
```

---

## Adding New Integrations

Follow the established pattern based on whether the platform has a compatible MCP server:

**Decision tree** → see [ADR-050](../adr/ADR-050-mcp-gateway-architecture.md#decision-tree-mcp-vs-direct-api)

**Direct API pattern** (for platforms without OAuth-compatible MCP servers):

1. Add `api/integrations/core/{platform}_client.py` — Direct API client
2. Add tool definitions to `PLATFORM_TOOLS_BY_PROVIDER` in `platform_tools.py`
3. Add handler `_handle_{platform}_tool()` in `platform_tools.py`
4. Add exporter `api/integrations/exporters/{platform}.py` — implements `DestinationExporter`
5. Register exporter in `registry.py`

**MCP Gateway pattern** (only for platforms with OAuth-compatible MCP servers — currently Slack only):

1. Add provider config to `mcp-gateway/src/mcp/client-manager.ts`
2. Use `call_platform_tool(provider="{platform}", ...)` in `platform_tools.py` and exporter

---

## Security: Token Flow

```
OAuth callback
  → TokenManager.encrypt(token) → platform_connections.credentials_encrypted
  → TokenManager.encrypt(refresh_token) → platform_connections.refresh_token_encrypted

TP tool call / Deliverable delivery
  → TokenManager.decrypt(credentials_encrypted) → access_token
  → TokenManager.decrypt(refresh_token_encrypted) → refresh_token (Gmail/Calendar)
  → Pass to client: MCP Gateway auth.token / DirectAPIClient access_token
```

---

## Scope Minimization

| Provider | Key Scopes | Backend |
|----------|-----------|---------|
| Slack | `chat:write`, `channels:read`, `groups:read` | MCP Gateway |
| Notion | `read_content`, `insert_content` | Direct API |
| Gmail | `gmail.modify`, `gmail.send` | Direct API |
| Calendar | `calendar.events`, `calendar.readonly` | Direct API |

---

## Changelog

### 2026-02-19: Exporter rewrites + platform_notion_get_page

- All three deliverable exporters (Slack, Notion, Gmail) rewritten to use production-compatible backends.
  Previously all called `get_mcp_manager()` from `client.py` which either spawned npx (fails on Render's Python service) or called methods that don't exist on `MCPClientManager`.
  - `SlackExporter`: now calls `services.mcp_gateway.call_platform_tool()` (HTTP to MCP Gateway)
  - `NotionExporter`: now calls Notion REST API directly via `POST /v1/pages`; added `_markdown_to_notion_blocks()` converter
  - `GmailExporter`: now calls `GoogleAPIClient.create_gmail_draft()` / `send_gmail_message()`; reads `context.refresh_token` (not metadata)
- Added `platform_notion_get_page` TP tool: search → get_page workflow; normalizes Notion block API to `{type, text}` via `_normalize_notion_blocks()`

### 2026-02-12: Notion MCP → Direct API Migration

**Key Discovery**: MCP server OAuth compatibility is NOT guaranteed.

- Tested both Notion MCP options - both incompatible with OAuth:
  - `@notionhq/notion-mcp-server`: Requires `ntn_...` internal tokens
  - `mcp.notion.com` (hosted): Manages own OAuth sessions
- **Decision**: Notion uses Direct API (same pattern as Gmail/Calendar)
- Created `NotionAPIClient` in `api/integrations/core/notion_client.py`
- MCP Gateway now handles Slack ONLY
- Added comprehensive learnings section to ADR-050
- **Architecture Principle**: Single implementation path per platform (no fallbacks)

### 2026-02-06: Initial Architecture

- Defined folder structure for scalable integration system
- Core components: Registry, BaseProvider, MCPClientManager, ExportService
- Slack provider implementation example
- API routes for integrations management
- Frontend context and components
- Database schema with encryption
- Guide for adding new integrations
