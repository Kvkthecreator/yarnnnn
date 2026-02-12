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
- Notion tools working via `@notionhq/notion-mcp-server` v2
- Platform tools dynamically added to TP based on user integrations

**Phase 2: Complete** ✅
- Gmail Direct API tools: `search`, `get_thread`, `send`, `create_draft`
- Calendar Direct API tools: `list_events`, `get_event`, `create_event`
- Routing: MCP Gateway for Slack/Notion, Direct API for Gmail/Calendar

**Prompt Versioning**: Added in `api/services/platform_tools.py:PROMPT_VERSIONS`

**Streamlined Patterns**:
- Slack: Send to user's own DM via `authed_user_id` (personal ownership)
- Notion: Write to user's designated page via `designated_page_id` (personal ownership)
- Calendar: Create events on user's designated calendar via `designated_calendar_id`
- Gmail: Prefer `create_draft` for deliverable outputs

**Designated Settings UI**:
- Notion: Users set output page at `/context/notion`
- Calendar: Users set default calendar at `/context/calendar`

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
