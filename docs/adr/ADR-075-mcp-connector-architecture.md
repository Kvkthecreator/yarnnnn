# ADR-075: MCP Connector — Technical Architecture

**Date**: 2026-02-25
**Status**: Implemented (Phase 1 — full tool surface + OAuth 2.1)
**Supersedes**: ADR-041 (MCP Server Exposure — deferred, scope replaced)
**Extends**: ADR-050 (MCP Gateway Architecture — now superseded by ADR-076)
**Related**: ADR-072 (Unified Content Layer), ADR-066 (Delivery-First Model)

---

## Context

### Current Platform Infrastructure (Outbound)

All platforms use Direct API clients from `api/integrations/core/` (ADR-076):

```
TP Agent (Python)
    │ Direct API calls
    ▼
api/integrations/core/
├── slack_client.py    (SlackAPIClient → Slack Web API)
├── notion_client.py   (NotionAPIClient → Notion REST API)
├── google_client.py   (GoogleAPIClient → Gmail/Calendar APIs)
```

The former MCP Gateway (ADR-050, Node.js) has been eliminated. See ADR-076.

### What This ADR Adds (Inbound)

This ADR introduces the **reverse direction** — YARNNN as MCP **server**, allowing Claude Desktop, Claude Code, and ChatGPT to call YARNNN tools.

For the product rationale and conceptual framework behind this decision, see [MCP-CONNECTORS.md](../integrations/MCP-CONNECTORS.md).

---

## Decision

Build a Python MCP server using the `mcp` SDK (`FastMCP`) that exposes YARNNN backend services as MCP tools. Deploy as a separate Render service (same codebase, separate process — matching the scheduler pattern). Dual transport: stdio (Claude Desktop/Code) and Streamable HTTP (ChatGPT, remote clients).

---

## Architecture

### System Placement

```
┌──────────────────────────────────────────────────────────────────┐
│                    YARNNN Codebase (api/)                         │
│                                                                  │
│  services/          routes/          jobs/         mcp_server/   │
│  ├─ supabase.py     ├─ chat.py      ├─ unified_   ├─ server.py  │
│  ├─ primitives/     ├─ deliver...   │  scheduler   ├─ auth.py   │
│  │  └─ system_      │               │              ├─ middleware │
│  │     state.py     │               │              └─ __main__  │
│  └─ ...             └─ ...          └─ ...                       │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Render Services (separate processes, same codebase):            │
│                                                                  │
│  yarnnn-api          uvicorn main:app                            │
│  yarnnn-scheduler    cd api && python -m jobs.unified_scheduler  │
│  yarnnn-sync         cd api && python -m jobs.platform_sync_scheduler │
│  yarnnn-mcp-server   cd api && python -m mcp_server http         │
└──────────────────────────────────────────────────────────────────┘
```

### MCP Server Module

```
api/mcp_server/
├── __init__.py          # Module docstring
├── __main__.py          # Entry point: transport selection, env loading
├── server.py            # FastMCP instance + tool registration + AuthSettings
├── auth.py              # Service key + MCP_USER_ID → AuthenticatedClient (data auth)
└── oauth_provider.py    # OAuthAuthorizationServerProvider (transport auth for 3rd-party clients)
```

**Why `mcp_server/` not `mcp/`:** The pip package is named `mcp`. A directory named `api/mcp/` would shadow it when Python resolves imports from the `api/` working directory. Underscore avoids the collision.

**Key design constraint:** Tool handlers call existing service functions directly. No new query logic. If `handle_get_system_state()` works for TP, it works for MCP.

### Transport Deployment

| Transport | Start Command | Deployment | Client |
|-----------|--------------|------------|--------|
| stdio | `cd api && python -m mcp_server` | User's machine (spawned by Claude) | Claude Desktop, Claude Code |
| Streamable HTTP | `cd api && python -m mcp_server http` | Render service (`yarnnn-mcp-server`) | ChatGPT, remote MCP clients |

Both transports share the same `FastMCP` server instance and tool handlers.

### Two-Layer Authentication Model

Authentication is split into two independent layers:

```
Request
  │
  ▼
Layer 1: Transport Auth (oauth_provider.py — load_access_token)
  "Is this request allowed to reach the server?"
  • OAuth 2.1 access token — validated against mcp_oauth_access_tokens table
  • Static bearer token fallback — MCP_BEARER_TOKEN env var (Claude Desktop/Code)
  • stdio: N/A (process-level access control)
  │
  ▼
Layer 2: Data Auth (auth.py)
  "Which user's data does this request access?"
  • Service key (SUPABASE_SERVICE_KEY) bypasses RLS
  • MCP_USER_ID scopes all queries via explicit .eq("user_id", user_id)
  • Matches worker/scheduler pattern — no token expiration
  │
  ▼
Tool Handler
  Uses AuthenticatedClient from lifespan context
```

**Layer 1 — Transport Auth** (`oauth_provider.py`):

The `mcp` SDK's built-in auth layer handles all transport auth when `auth_server_provider` is set on `FastMCP`. The SDK:
- Returns 401 on unauthenticated `/mcp` requests
- Serves `/.well-known/oauth-authorization-server` metadata (discovery)
- Handles `/register` (dynamic client registration, RFC 7591)
- Handles `/authorize` (authorization code grant with PKCE)
- Handles `/token` (code exchange + refresh)
- Calls `load_access_token()` on every authenticated request

`YarnnnOAuthProvider.load_access_token()` validates tokens in two ways:
1. **Static bearer token**: If token matches `MCP_BEARER_TOKEN` env var, returns an `AccessToken` scoped to `MCP_USER_ID`. Used by Claude Desktop and Claude Code.
2. **OAuth access token**: Looks up token in `mcp_oauth_access_tokens` table. Validates expiry. Returns `AccessToken` with the `user_id` stored at token issuance. Used by Claude.ai connectors and ChatGPT.

**Layer 2 — Data Auth** (`auth.py`):
- Uses `SUPABASE_SERVICE_KEY` via `get_service_client()` (bypasses RLS)
- `MCP_USER_ID` env var identifies the user — all queries filter by explicit `.eq("user_id", user_id)`
- Returns `AuthenticatedClient(client, user_id, email=None)` at lifespan startup
- Same pattern as `platform_worker.py` and `unified_scheduler.py`
- Currently single-user (lifespan auth). Multi-user would resolve per-request from OAuth token.

**Legacy note**: The original `BearerAuthMiddleware` (static token only) was superseded by the OAuth provider's `load_access_token()` method and has been deleted.

### Render Deployment

| Detail | Value |
|--------|-------|
| Service | `yarnnn-mcp-server` |
| Service ID | `srv-d6f4vg1drdic739nli4g` |
| URL | `https://yarnnn-mcp-server.onrender.com/mcp` |
| Plan | Starter ($7/mo) |
| Region | Singapore |
| Runtime | Python 3.11 |

**Env vars:**
- `PYTHON_VERSION` — `3.11.11`
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — Supabase anon key (unused by service key auth, but available)
- `SUPABASE_SERVICE_KEY` — Service key for RLS bypass
- `MCP_USER_ID` — User UUID for data scoping (auto-approve OAuth + static bearer fallback)
- `MCP_BEARER_TOKEN` — Static bearer token for Claude Desktop/Code (backward compat)
- `MCP_SERVER_URL` — OAuth issuer URL (defaults to `https://yarnnn-mcp-server.onrender.com`)

---

## Implementation: Phase 0 — Hello World Validation (Implemented)

### The Validation Tool: `get_status`

Single read-only tool that exercises the full auth chain (OAuth/bearer token → service key → user_id → Supabase query → structured response). No side effects. Wraps existing `handle_get_system_state()` from `services/primitives/system_state.py`.

### Files

| File | Purpose |
|------|---------|
| `api/mcp_server/__init__.py` | Module docstring |
| `api/mcp_server/auth.py` | Data auth: service key + MCP_USER_ID → AuthenticatedClient |
| `api/mcp_server/oauth_provider.py` | OAuth 2.1 provider: client registration, token issuance, validation |
| `api/mcp_server/server.py` | FastMCP instance + AuthSettings + 6 tool handlers |
| `api/mcp_server/__main__.py` | Entry point with transport selection |
| `supabase/migrations/082_mcp_oauth_tables.sql` | OAuth token storage: clients, codes, access/refresh tokens |

### Verification Status

- [x] All files parse as valid Python
- [x] Render deployment live (srv-d6f4vg1drdic739nli4g)
- [x] Service key auth working (queries return real data)
- [x] OAuth 2.1 flow: discovery → registration → authorize → token exchange
- [x] Static bearer token backward compatible (via `load_access_token` fallback)
- [x] `get_status` tool call returns full system state snapshot
- [x] Claude.ai connector integration (OAuth flow, tool discovery confirmed)
- [ ] ChatGPT developer mode integration test

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "yarnnn": {
      "type": "streamable-http",
      "url": "https://yarnnn-mcp-server.onrender.com/mcp",
      "headers": {
        "Authorization": "Bearer <MCP_BEARER_TOKEN>"
      }
    }
  }
}
```

### Claude Code Configuration

```bash
claude mcp add yarnnn \
  --transport http \
  --url https://yarnnn-mcp-server.onrender.com/mcp \
  --header "Authorization: Bearer <MCP_BEARER_TOKEN>"
```

### Local stdio Configuration (no bearer token needed)

```json
{
  "mcpServers": {
    "yarnnn": {
      "command": "python3",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/yarnnn/api",
      "env": {
        "SUPABASE_URL": "<url>",
        "SUPABASE_SERVICE_KEY": "<key>",
        "MCP_USER_ID": "<user-uuid>"
      }
    }
  }
}
```

### Claude.ai Connector

Claude.ai connectors use OAuth 2.1 (the MCP spec's standard auth). Add via Claude.ai Settings → Connectors → Add → enter URL:

```
https://yarnnn-mcp-server.onrender.com/mcp
```

Claude.ai handles the full OAuth flow automatically: discovery → client registration → authorize → token exchange. No manual token configuration needed.

### ChatGPT Developer Mode

ChatGPT supports remote MCP servers over Streamable HTTP with OAuth 2.1. The same OAuth flow used by Claude.ai should work — not yet integration-tested.

---

## Implementation: Phase 1 — Full Tool Surface (Implemented)

All 6 tools live in `server.py`. Tool handlers call service functions directly — same layer REST routes use.

| MCP Tool | Service Function / Pattern | File |
|----------|---------------------------|------|
| `get_status` | `handle_get_system_state()` | `services/primitives/system_state.py` |
| `list_deliverables` | Direct query on `deliverables` table | Direct (same as REST route) |
| `run_deliverable` | `execute_deliverable_generation()` | `services/deliverable_execution.py` |
| `get_deliverable_output` | Direct query on `deliverable_versions` | Direct (same as REST route) |
| `get_context` | `build_working_memory()` | `services/working_memory.py` |
| `search_content` | `search_platform_content()` | `services/platform_content.py` |

---

## Implementation: OAuth 2.1 (Implemented)

OAuth 2.1 is live, enabling Claude.ai connectors and ChatGPT developer mode.

### OAuth Flow

```
Claude.ai / ChatGPT
    │
    │ 1. POST /mcp → 401 Unauthorized
    │ 2. GET /.well-known/oauth-authorization-server → metadata
    │ 3. POST /register → client_id (dynamic registration, RFC 7591)
    │ 4. GET /authorize → auto-approve → redirect with auth code
    │ 5. POST /token → access_token + refresh_token (PKCE validated)
    │ 6. POST /mcp (Authorization: Bearer <token>) → tools work
    │
    ▼
MCP Server (FastMCP + YarnnnOAuthProvider)
    │
    │ load_access_token() validates token → resolves user_id
    │
    ▼
Supabase (service key, scoped by user_id)
```

### OAuth Provider (`oauth_provider.py`)

Implements `OAuthAuthorizationServerProvider` from `mcp.server.auth.provider` with 9 methods:

| Method | Purpose |
|--------|---------|
| `get_client` / `register_client` | Dynamic client registration (RFC 7591) |
| `authorize` | Auto-approve: issues auth code for `MCP_USER_ID` immediately |
| `load_authorization_code` / `exchange_authorization_code` | Auth code → access + refresh tokens |
| `load_refresh_token` / `exchange_refresh_token` | Token rotation (new access + refresh, old refresh deleted) |
| `load_access_token` | Validates token: static bearer fallback → OAuth table lookup |
| `revoke_token` | Deletes access or refresh token |

**Auto-approve mode**: The `authorize()` method skips login/consent and directly issues an auth code for `MCP_USER_ID`. Single-user mode — all OAuth tokens resolve to the same user. Multi-user mode would redirect to Supabase Auth login first.

**Token lifetimes**: Access token = 1 hour, refresh token = 30 days, auth code = 5 minutes.

**Custom token types**: `YarnnnAccessToken`, `YarnnnAuthCode`, `YarnnnRefreshToken` — each extends the SDK base with a `user_id` field for data scoping.

### OAuth Storage (Migration 082)

Four Supabase tables, service key access only (no RLS):

| Table | Purpose |
|-------|---------|
| `mcp_oauth_clients` | Registered OAuth clients (client_id, redirect_uris, etc.) |
| `mcp_oauth_codes` | Authorization codes (expires after 5 min, single-use) |
| `mcp_oauth_access_tokens` | Access tokens (expires after 1 hour) |
| `mcp_oauth_refresh_tokens` | Refresh tokens (30-day lifetime, rotated on use) |

### Future: Multi-User OAuth

Currently all OAuth tokens resolve to `MCP_USER_ID` (auto-approve). To support multiple users:

1. `authorize()` redirects to Supabase Auth login instead of auto-approving
2. Callback endpoint receives Supabase session, generates auth code with real `user_id`
3. Tool handlers resolve per-request `AuthenticatedClient` from OAuth token's `user_id`
4. Remove lifespan auth dependency — each request is independently scoped

---

## Consequences

### What Changes
- New `api/mcp_server/` directory (~500 lines: server, auth, OAuth provider)
- New Render service (`yarnnn-mcp-server`, Starter plan)
- `mcp` pip package already in `requirements.txt` (needs Python >= 3.10 runtime)
- 4 new Supabase tables for OAuth token storage (migration 082)

### What Does NOT Change
- All existing service code — untouched
- `execute_deliverable_generation()` — same pipeline, new `trigger_context` type (Phase 1)
- Existing tables — no schema changes to any existing table
- Scheduler, signal processing, platform sync — untouched
- TP agent — untouched
- Platform API clients (Slack, Notion, Gmail, Calendar) — untouched

---

## References

- [MCP Connectors Conceptual Framework](../integrations/MCP-CONNECTORS.md) — Product rationale, user flows, tool mapping decisions
- [ADR-041: MCP Server Exposure](./ADR-041-mcp-server-exposure.md) — Superseded by this ADR
- [ADR-050: MCP Gateway Architecture](./ADR-050-mcp-gateway-architecture.md) — Superseded by ADR-076
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — `FastMCP` server implementation
- [MCP Specification: Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [MCP Specification: Authorization](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization) — OAuth 2.1 with PKCE
- [RFC 7591: OAuth Dynamic Client Registration](https://tools.ietf.org/html/rfc7591)
