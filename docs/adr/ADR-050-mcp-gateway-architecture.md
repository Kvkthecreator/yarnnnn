# ADR-050: MCP Gateway Architecture

> **Status**: Implemented
> **Created**: 2026-02-12
> **Updated**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-048 (Direct MCP Access), ADR-041 (MCP Server Exposure), ADR-046 (Google Calendar Integration)

---

## Implementation Status

**Phase 1: Complete** ✅
- MCP Gateway deployed at `yarnnn-mcp-gateway.onrender.com`
- Slack tools working via `@modelcontextprotocol/server-slack`
- Platform tools dynamically added to TP based on user integrations

**Phase 2: Complete** ✅
- Gmail Direct API tools: `search`, `get_thread`, `send`, `create_draft`
- Calendar Direct API tools: `list_events`, `get_event`, `create_event`
- Routing: MCP Gateway for Slack, Direct API for Gmail/Calendar

**Notion Status: Resolved** ✅
- The open-source `@notionhq/notion-mcp-server` requires internal tokens (`ntn_...`)
- **Solution**: Use Notion's Hosted MCP at `mcp.notion.com/mcp` instead
- Hosted MCP supports OAuth bearer token authentication
- Gateway now supports both local (stdio) and remote (HTTP) transports
- See "Notion MCP Incompatibility" section below for full details

**Prompt Versioning**: Added in `api/services/platform_tools.py:PROMPT_VERSIONS`

**Default Landing Zones** (user owns the output):

| Platform | Default Destination | Metadata Key | Backend |
|----------|---------------------|--------------|---------|
| Slack | User's DM to self | `authed_user_id` | MCP Gateway |
| Notion | User's designated page | `designated_page_id` | MCP Gateway |
| Gmail | Draft to user's email | `user_email` | Direct API |
| Calendar | User's designated calendar | `designated_calendar_id` | Direct API |

**Designated Settings UI**:
- Notion: Users set output page at `/context/notion`
- Calendar: Users set default calendar at `/context/calendar`

**Client Separation** (clean architecture):
```
api/integrations/core/
├── client.py          # MCPManager - Slack ONLY (MCP protocol via Gateway)
├── google_client.py   # GoogleAPIClient - Gmail/Calendar (Direct API)
└── tokens.py          # TokenManager - OAuth token management
```

The client classes are intentionally separated to avoid confusion:
- `MCPManager` handles ONLY MCP protocol (Slack only - Notion blocked, see below)
- `GoogleAPIClient` handles ONLY Google Direct API (Gmail, Calendar)
- No dual-path code - each platform has ONE implementation path

---

## Notion MCP Incompatibility

**Discovery Date:** 2026-02-12

### The Problem

The official `@notionhq/notion-mcp-server` (npm package) requires **internal integration tokens** that start with `ntn_`. These are different from OAuth access tokens:

| Auth Type | Token Format | Source | Use Case |
|-----------|--------------|--------|----------|
| Internal Integration | `ntn_...` | Notion Developer Portal | Private integrations within a workspace |
| OAuth Access Token | `secret_...` or opaque | OAuth flow | Public apps that users authorize |

YARNNN uses OAuth for user authorization (public integration), but the MCP server expects internal integration tokens. This is a fundamental incompatibility.

### Evidence

From the Notion MCP documentation:
> "NOTION_TOKEN": "ntn_****" - Your integration secret token from your integration's Configuration tab

The server initialization fails silently or returns "Method not found" errors when given OAuth tokens because it cannot authenticate with the Notion API.

### Options Evaluated

1. **Switch Notion to Direct API**
   - Like Gmail/Calendar, call Notion REST API directly from Python
   - OAuth tokens work with Notion REST API
   - Downside: Loses MCP abstraction, more code to maintain

2. **Use Notion's Hosted MCP** (`mcp.notion.com`) ✅ **CHOSEN**
   - Supports OAuth authentication via bearer token
   - Actively maintained by Notion
   - Keeps MCP abstraction for future ecosystem benefits
   - Uses `StreamableHTTPClientTransport` instead of `StdioClientTransport`

3. **Require Internal Integration Tokens**
   - Users create internal integration and paste token
   - Breaks OAuth flow UX
   - **Rejected**: Poor user experience

### Decision: Remote MCP via Hosted Server

**Implemented 2026-02-12**: Use Notion's hosted MCP at `https://mcp.notion.com/mcp` with OAuth bearer token authentication.

This approach:
- Maintains the MCP abstraction (strategic investment in MCP ecosystem)
- Uses existing OAuth tokens (no UX change for users)
- Leverages Notion's actively maintained server
- Requires gateway to support both local (stdio) and remote (HTTP) transports

**Implementation:**
```typescript
// MCP Gateway now supports two transport types:
const PROVIDERS = {
  slack: {
    type: 'local',  // StdioClientTransport - subprocess
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-slack'],
  },
  notion: {
    type: 'remote',  // StreamableHTTPClientTransport - HTTP
    url: 'https://mcp.notion.com/mcp',
  },
};
```

**Updated Platform Routing:**

| Platform | Backend | Transport | Reason |
|----------|---------|-----------|--------|
| Slack | MCP Gateway | Local (stdio) | MCP server supports OAuth |
| Notion | MCP Gateway | Remote (HTTP) | Hosted MCP supports OAuth |
| Gmail | Direct API | N/A | No suitable MCP server |
| Calendar | Direct API | N/A | No suitable MCP server |

---

## Context

### The Problem

ADR-048 established that TP should have direct access to MCP tools for platform operations (Slack, Notion, etc.). However, the implementation hit a blocker:

1. **MCP requires Node.js** - MCP servers are npm packages spawned as subprocesses
2. **Render Python runtime can't spawn Node** - No `npx` available in Python service
3. **Current state is broken** - TP's system prompt describes MCP tools, but they're not actually callable

### Strategic Consideration

MCP is becoming the standard protocol for LLM-to-service integration:
- Growing ecosystem of pre-built MCP servers
- Anthropic, OpenAI, and others adopting it
- Each new integration becomes trivial once infrastructure exists

Building MCP infrastructure now is an investment in future integration velocity.

### Two Directions of MCP

1. **Outbound (MCP Client)**: YARNNN calls external services
   - TP → Slack, Notion, Gmail, Calendar
   - YARNNN initiates, external service responds

2. **Inbound (MCP Server)**: External tools call YARNNN
   - Claude Desktop/Code → YARNNN memories, deliverables
   - External tool initiates, YARNNN responds

Both are valuable. A unified gateway can serve both.

---

## Decision

**Create a dedicated Node.js MCP Gateway service** that handles both inbound and outbound MCP communication.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   yarnnn-mcp-gateway                         │
│                      (Node.js)                               │
│                                                              │
│  ┌────────────────────┐     ┌─────────────────────────────┐ │
│  │ MCP Server         │     │ MCP Client Manager          │ │
│  │ (stdio transport)  │     │ (subprocess management)     │ │
│  │                    │     │                             │ │
│  │ Exposes:           │     │ Manages:                    │ │
│  │ - get_memories     │     │ - @mcp/server-slack         │ │
│  │ - list_deliverables│     │ - @notionhq/notion-mcp      │ │
│  │ - search_context   │     │ - (future integrations)     │ │
│  └────────────────────┘     └─────────────────────────────┘ │
│           ↑                            ↑                     │
│           │                            │                     │
│           │      HTTP REST API         │                     │
│           │   ┌────────────────────┐   │                     │
│           └───┤ /api/mcp/*         ├───┘                     │
│               │                    │                         │
│               │ POST /tools/:provider/:tool                  │
│               │ GET  /tools/:provider                        │
│               │ POST /auth/:provider                         │
│               └────────────────────┘                         │
│                         ↑                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │ HTTPS
                          │
┌─────────────────────────┼────────────────────────────────────┐
│                   yarnnn-api                                  │
│                    (Python)                                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Thinking Partner                                      │   │
│  │                                                       │   │
│  │ tools = PRIMITIVES + get_platform_tools(user)        │   │
│  │                                                       │   │
│  │ tool_executor:                                        │   │
│  │   if tool.startswith("platform_"):                   │   │
│  │     → HTTP call to mcp-gateway                       │   │
│  │   else:                                               │   │
│  │     → execute_primitive()                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Gateway Responsibilities

**Outbound (Client) - For TP platform operations:**
- Spawn and manage MCP server subprocesses
- Route tool calls from Python API to appropriate MCP server
- Handle authentication (tokens passed per-request)
- Parse MCP results and return JSON

**Inbound (Server) - For Claude Desktop/Code:**
- Expose YARNNN as an MCP server
- Authenticate via JWT token
- Proxy requests to yarnnn-api for actual operations
- Return results in MCP format

### API Design

**Outbound Tool Calls:**
```
POST /api/mcp/tools/slack/send_message
Authorization: Bearer <user-jwt>
Content-Type: application/json

{
  "channel_id": "C0123ABC",
  "text": "Hello from YARNNN!"
}

Response:
{
  "success": true,
  "result": { "ts": "1234567890.123456", "channel": "C0123ABC" }
}
```

**List Available Tools:**
```
GET /api/mcp/tools/slack
Authorization: Bearer <user-jwt>

Response:
{
  "tools": [
    { "name": "send_message", "description": "...", "input_schema": {...} },
    { "name": "list_channels", "description": "...", "input_schema": {...} }
  ]
}
```

### Tool Naming Convention

For TP tools, use underscore-prefixed platform tools:
- `platform_slack_send_message`
- `platform_slack_list_channels`
- `platform_notion_search`
- `platform_notion_create_comment`
- `platform_gmail_send`
- `platform_calendar_create_event`

This makes it clear these route through the gateway, distinct from YARNNN primitives.

---

## Implementation Plan

### Phase 1: Gateway Foundation (Priority - Fixes Current Bug)

1. **Create gateway service** in `mcp-gateway/` directory
2. **Implement outbound client manager** for Slack and Notion
3. **REST API** for tool calls
4. **Deploy to Render** (unsuspend/reconfigure existing service)
5. **Wire TP** to call gateway for platform tools

### Phase 2: Full Platform Coverage

1. Add Gmail direct API handler (not MCP)
2. Add Google Calendar direct API handler
3. Dynamic tool discovery from gateway

### Phase 3: Inbound Server (ADR-041)

1. Implement MCP server for YARNNN exposure
2. Claude Desktop configuration
3. Authentication flow for external clients

---

## Consequences

### Positive

1. **MCP ecosystem access** - Future integrations are npm install away
2. **Clean separation** - Node.js handles MCP, Python handles AI/business logic
3. **Both directions** - TP can call out, Claude Code can call in
4. **Future-proof** - Aligned with market direction

### Negative

1. **Additional service** - $7/month, operational overhead
2. **Network hop** - Python → HTTP → Node.js → MCP → Platform
3. **Two codebases** - Node.js gateway + Python API

### Mitigations

- Gateway is stateless, simple to operate
- Network latency is minimal for tool calls
- Clear API boundary means independent deployment

---

## Alternatives Considered

### A. Direct API Calls (No MCP)

Skip MCP entirely, use httpx to call platform APIs directly from Python.

**Rejected because:**
- Loses MCP ecosystem benefits
- Each integration requires learning platform API
- Not aligned with market direction

### B. MCP in Python Only

Use Python MCP SDK to spawn Node subprocesses.

**Rejected because:**
- Doesn't work on Render (no Node.js in Python runtime)
- Complex subprocess management in Python
- Still need Node.js somehow

### C. Docker with Node + Python

Single Docker container with both runtimes.

**Rejected because:**
- More complex build/deploy
- Harder to debug
- Overkill for the problem

---

## Render Configuration

**Service:** `yarnnn-mcp-gateway`
**Runtime:** Node.js
**Plan:** Starter ($7/month)
**Region:** Singapore (same as yarnnn-api)

**Environment Variables:**
- `YARNNN_API_URL` - Internal URL to yarnnn-api
- `SLACK_*`, `NOTION_*` - OAuth credentials (same as yarnnn-api)

**Build Command:** `npm install`
**Start Command:** `npm start`

---

## See Also

- [ADR-048: Direct MCP Access](ADR-048-direct-mcp-access.md)
- [ADR-041: MCP Server Exposure](ADR-041-mcp-server-exposure.md)
- [MCP Specification](https://modelcontextprotocol.io/)
