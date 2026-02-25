# ADR-050: MCP Gateway Architecture

> **Status**: Superseded by [ADR-076](ADR-076-eliminate-mcp-gateway.md)
> **Created**: 2026-02-12
> **Updated**: 2026-02-25
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-048 (Direct MCP Access), ADR-041 (MCP Server Exposure), ADR-046 (Google Calendar Integration)

**⚠️ SUPERSEDED**: This ADR is historical. The MCP Gateway has been eliminated (ADR-076). All platforms — including Slack — now use Direct API clients from `api/integrations/core/`. The gateway service (`yarnnn-mcp-gateway`) and `MCPClientManager` have been deleted. The "Learnings for Future Integrations" section below remains valuable as context.

---

## Implementation Status

**Phase 1: Complete** ✅
- MCP Gateway deployed at `yarnnn-mcp-gateway.onrender.com`
- Slack tools working via `@modelcontextprotocol/server-slack`
- Platform tools dynamically added to TP based on user integrations

**Phase 2: Complete** ✅
- Gmail Direct API tools: `search`, `get_thread`, `send`, `create_draft`
- Calendar Direct API tools: `list_events`, `get_event`, `create_event`
- Routing: MCP Gateway for Slack ONLY, Direct API for everything else

**Notion Status: Resolved via Direct API** ✅
- Both MCP options failed (see "Notion MCP Incompatibility" section)
- **Final Solution**: Direct API calls to `api.notion.com`
- New `NotionAPIClient` in `api/integrations/core/notion_client.py`
- OAuth tokens work perfectly with Notion REST API

**Prompt Versioning**: Added in `api/services/platform_tools.py:PROMPT_VERSIONS`

**Exporter Alignment** (2026-02-19): All deliverable exporters now use the same backends as TP platform tools:
- `integrations/exporters/slack.py` → MCP Gateway (`call_platform_tool()`)
- `integrations/exporters/notion.py` → Direct API (`POST /v1/pages`)
- `integrations/exporters/gmail.py` → Direct API (`GoogleAPIClient`)

Previously all three exporters incorrectly called `MCPClientManager` from `client.py`, which either failed at runtime (npx unavailable on Render) or called methods that don't exist on that class.

**Default Landing Zones** (user owns the output):

| Platform | Default Destination | Metadata Key | Backend |
|----------|---------------------|--------------|---------|
| Slack | User's DM to self | `authed_user_id` | MCP Gateway |
| Notion | User's designated page | `designated_page_id` | Direct API |
| Gmail | Draft to user's email | `user_email` | Direct API |
| Calendar | User's designated calendar | `designated_calendar_id` | Direct API |

**Designated Settings UI**:
- Notion: Users set output page at `/context/notion`
- Calendar: Users set default calendar at `/context/calendar`

**Client Separation** (clean architecture):
```
api/integrations/core/
├── client.py          # MCPManager - Slack ONLY (MCP protocol via Gateway)
├── notion_client.py   # NotionAPIClient - Notion (Direct API)
├── google_client.py   # GoogleAPIClient - Gmail/Calendar (Direct API)
└── tokens.py          # TokenManager - OAuth token management
```

The client classes are intentionally separated to avoid confusion:
- `MCPManager` handles ONLY MCP protocol (Slack only - the only platform where MCP works with OAuth)
- `NotionAPIClient` handles Notion Direct API (MCP incompatible with OAuth)
- `GoogleAPIClient` handles Google Direct API (Gmail, Calendar)
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

1. **Open-source MCP server** (`@notionhq/notion-mcp-server`)
   - ❌ **Failed**: Requires internal integration tokens (`ntn_...`), not OAuth
   - Error: "Method not found" when passing OAuth tokens

2. **Notion's Hosted MCP** (`mcp.notion.com/mcp`)
   - ❌ **Failed**: Manages its own OAuth sessions
   - Error: `{"error":"invalid_token","error_description":"Invalid token format"}`
   - The hosted MCP is designed for direct user-to-server auth flows (Claude Desktop, Cursor)
   - Not designed for intermediary platforms passing OAuth tokens through

3. **Direct API** (`api.notion.com`) ✅ **CHOSEN**
   - OAuth tokens work perfectly with Notion REST API
   - Same pattern as Gmail/Calendar
   - Full control over API calls
   - No MCP abstraction overhead

4. **Require Internal Integration Tokens**
   - ❌ **Rejected**: Poor user experience
   - Users would need to create integration and paste token

### Decision: Direct API (Final)

**Implemented 2026-02-12**: Call Notion REST API directly from Python using OAuth access tokens.

```python
# api/integrations/core/notion_client.py
class NotionAPIClient:
    async def search(self, access_token: str, query: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": "2022-06-28",
                },
                json={"query": query},
            )
            return response.json().get("results", [])
```

**Final Platform Routing:**

| Platform | Backend | Reason |
|----------|---------|--------|
| Slack | MCP Gateway | Only MCP server that works with OAuth |
| Notion | Direct API | MCP options incompatible with OAuth |
| Gmail | Direct API | No suitable MCP server |
| Calendar | Direct API | No suitable MCP server |

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
│  │ - get_memories     │     │ - @mcp/server-slack (ONLY)  │ │
│  │ - list_deliverables│     │                             │ │
│  │ - search_context   │     │ (Notion/Gmail/Calendar use  │ │
│  │                    │     │  Direct API - see ADR-050)  │ │
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

## Learnings for Future Integrations

**Date Documented**: 2026-02-12

These learnings will pay off for downstream platform integrations. When adding a new platform, evaluate using this decision tree.

### Decision Tree: MCP vs Direct API

```
New Platform Integration
         │
         ▼
┌────────────────────────────┐
│ Does an MCP server exist?  │
└────────────────────────────┘
         │
    ┌────┴────┐
    No        Yes
    │         │
    ▼         ▼
Direct    ┌──────────────────────────────┐
 API      │ What auth does it require?   │
          └──────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
    OAuth tokens  API keys    Internal tokens
    (our model)   (simple)    (ntn_..., etc.)
         │            │            │
         ▼            ▼            ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │ Test it │   │   MCP   │   │ Direct  │
    │  first! │   │ Gateway │   │   API   │
    └─────────┘   └─────────┘   └─────────┘
         │
         ▼
┌───────────────────────────────────┐
│ Does passing OAuth token work?    │
│ (Test with actual token, not key) │
└───────────────────────────────────┘
         │
    ┌────┴────┐
   Yes        No
    │         │
    ▼         ▼
   MCP     Direct
 Gateway     API
```

### Key Insight: MCP OAuth Compatibility is NOT Guaranteed

**What We Learned:**

1. **MCP servers have varying auth models** - Even official MCP servers may not support OAuth tokens
2. **"OAuth app" ≠ "OAuth token compatible"** - A platform may support OAuth apps for authorization but their MCP server may expect different credential types
3. **Hosted MCP services manage their own sessions** - Services like `mcp.notion.com` expect to handle OAuth flows themselves, not receive tokens from intermediaries

**Platform-Specific Findings:**

| Platform | MCP Server | OAuth Token Support | Our Solution |
|----------|------------|---------------------|--------------|
| **Slack** | `@modelcontextprotocol/server-slack` | ✅ Yes - works with `SLACK_BOT_TOKEN` | MCP Gateway |
| **Notion** | `@notionhq/notion-mcp-server` | ❌ No - requires `ntn_...` internal tokens | Direct API |
| **Notion** | `mcp.notion.com` (hosted) | ❌ No - manages own OAuth sessions | N/A |
| **Gmail** | None suitable | N/A | Direct API |
| **Calendar** | None suitable | N/A | Direct API |

### Testing Protocol for New MCP Servers

Before committing to MCP for a new platform:

1. **Check the docs first** - Look for authentication requirements
   - `ntn_...`, `sk_...`, `xoxb-...` patterns indicate specific token types
   - "Internal integration" or "workspace token" = likely incompatible

2. **Test with actual OAuth token** - Don't assume it works
   ```bash
   # Set env var with your OAuth token
   PLATFORM_TOKEN="oauth_token_here" npx @platform/mcp-server
   # Try listing tools
   ```

3. **Check error messages** - Common failure patterns:
   - `"invalid_token"` - Wrong token format expected
   - `"Method not found"` - Server not initializing properly
   - Silent failure - Auth rejected before tool discovery

4. **Evaluate hosted MCP endpoints** - If they exist:
   - Are they designed for direct user auth (Claude Desktop)?
   - Do they accept tokens passed from intermediaries?
   - Most hosted MCPs manage their own sessions

### When to Choose Direct API

**Choose Direct API when:**
- ✅ No MCP server exists
- ✅ MCP server requires non-OAuth credentials
- ✅ MCP server is for direct-to-user auth only
- ✅ Platform has a simple, well-documented REST API
- ✅ You need fine-grained control over requests/responses

**Benefits of Direct API:**
- Full control over error handling
- No subprocess management overhead
- Simpler debugging (just HTTP calls)
- No dependency on third-party MCP server maintenance

### Code Pattern: Adding a New Direct API Platform

Follow the established pattern in `api/integrations/core/`:

```python
# api/integrations/core/{platform}_client.py
class PlatformAPIClient:
    """
    Direct API client for {Platform} operations.

    NOT MCP - uses {Platform}'s REST API directly with OAuth access tokens.
    """

    async def operation_name(
        self,
        access_token: str,
        # platform-specific params
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.{platform}.com/v1/endpoint",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    # platform-specific headers
                },
                json=body,
                timeout=30.0,
            )
            # error handling
            return response.json()
```

Then wire into `platform_tools.py`:
```python
async def _handle_{platform}_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """ADR-050: Handle {Platform} tools via Direct API."""
    from integrations.core.{platform}_client import get_{platform}_client
    # implementation
```

### Architecture Principle: Single Implementation Path

**Avoid dual-path implementations.** Each platform should have ONE integration path:

```
✅ Good: Slack → MCP Gateway (only)
✅ Good: Notion → Direct API (only)
✅ Good: Gmail → Direct API (only)

❌ Bad: Platform → try MCP, fallback to Direct API
❌ Bad: Platform → MCP for some tools, Direct for others
```

Single paths are:
- Easier to debug
- Easier to maintain
- Clearer mental model
- No "which path did it take?" confusion

---

## See Also

- [ADR-048: Direct MCP Access](ADR-048-direct-mcp-access.md)
- [ADR-041: MCP Server Exposure](ADR-041-mcp-server-exposure.md)
- [MCP Specification](https://modelcontextprotocol.io/)
