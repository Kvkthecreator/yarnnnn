# ADR-075: MCP Connector — Technical Architecture

**Date**: 2026-02-25
**Status**: Implemented (Phase 0 + HTTP transport live)
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
│  yarnnn-worker       python -m jobs.worker                       │
│  yarnnn-scheduler    cd api && python -m jobs.unified_scheduler  │
│  yarnnn-mcp-server   cd api && python -m mcp_server http         │
└──────────────────────────────────────────────────────────────────┘
```

### MCP Server Module

```
api/mcp_server/
├── __init__.py          # Module docstring
├── __main__.py          # Entry point: transport selection, env loading
├── server.py            # FastMCP instance + tool registration
├── auth.py              # Service key + MCP_USER_ID → AuthenticatedClient
└── middleware.py         # Bearer token transport auth (HTTP only)
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
Layer 1: Transport Auth (middleware.py)
  "Is this request allowed to reach the server?"
  • HTTP: Bearer token from Authorization header vs MCP_BEARER_TOKEN env var
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

**Layer 1 — Transport Auth** (`middleware.py`):
- HTTP requests must include `Authorization: Bearer <token>` matching `MCP_BEARER_TOKEN`
- Returns 401 if missing/invalid, 503 if env var not configured (fail closed)
- `/health` path bypasses auth (Render health checks)
- Uses `hmac.compare_digest()` for constant-time token comparison
- stdio transport has no middleware — access is process-level

**Layer 2 — Data Auth** (`auth.py`):
- Uses `SUPABASE_SERVICE_KEY` via `get_service_client()` (bypasses RLS)
- `MCP_USER_ID` env var identifies the user — all queries filter by explicit `.eq("user_id", user_id)`
- Returns `AuthenticatedClient(client, user_id, email=None)` at lifespan startup
- Same pattern as `platform_worker.py` and `unified_scheduler.py`

**Future: 3rd-party OAuth (Layer 1 extension)**:
- ChatGPT developer mode sends `Authorization: Bearer <oauth-token>` per MCP spec
- Layer 1 will validate JWT signature + audience for 3rd-party tokens
- Layer 2 will resolve user from OAuth token instead of env var
- This is additive — internal bearer token continues to work alongside

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
- `MCP_USER_ID` — User UUID for data scoping
- `MCP_BEARER_TOKEN` — Static bearer token for transport auth

---

## Implementation: Phase 0 — Hello World Validation (Implemented)

### The Validation Tool: `get_status`

Single read-only tool that exercises the full auth chain (bearer token → service key → user_id → Supabase query → structured response). No side effects. Wraps existing `handle_get_system_state()` from `services/primitives/system_state.py`.

### Files

| File | Purpose |
|------|---------|
| `api/mcp_server/__init__.py` | Module docstring |
| `api/mcp_server/auth.py` | Data auth: service key + MCP_USER_ID → AuthenticatedClient |
| `api/mcp_server/middleware.py` | Transport auth: bearer token validation |
| `api/mcp_server/server.py` | FastMCP instance + `get_status` tool |
| `api/mcp_server/__main__.py` | Entry point with transport selection + middleware wiring |

### Verification Status

- [x] All files parse as valid Python
- [x] Render deployment live (srv-d6f4vg1drdic739nli4g)
- [x] Service key auth working (queries return real data)
- [x] Bearer token middleware active (401 without token)
- [x] `get_status` tool call returns full system state snapshot
- [ ] Claude Desktop integration test
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

### ChatGPT Developer Mode (Future)

ChatGPT developer mode supports remote MCP servers over Streamable HTTP with OAuth 2.1. When OAuth is implemented (Layer 1 extension), ChatGPT will authenticate per the MCP spec and send bearer tokens with each request.

---

## Implementation: Phase 1 — Full Tool Surface

After Phase 0 validates the wiring, add 5 more tools in `server.py`:

| MCP Tool | Service Function | File |
|----------|-----------------|------|
| `get_status` | `handle_get_system_state()` | `services/primitives/system_state.py` |
| `list_deliverables` | Supabase query on `deliverables` | `routes/deliverables.py` (reuse query logic) |
| `run_deliverable` | `execute_deliverable_generation()` | `services/deliverable_execution.py` |
| `get_deliverable_output` | Supabase query on `deliverable_versions` | `routes/deliverables.py` (reuse query logic) |
| `get_context` | Supabase query on `user_context` | `services/working_memory.py` (reuse fetch logic) |
| `search_content` | Supabase query on `platform_content` | `services/platform_content.py` |

---

## Implementation: Phase 2 — 3rd-Party OAuth

1. Implement OAuth 2.1 token validation in Layer 1 middleware (alongside static bearer token)
2. Resolve user identity from OAuth token (replace MCP_USER_ID for 3rd-party requests)
3. Register as ChatGPT developer mode connector
4. Multi-tenant support: per-request user resolution instead of per-process

---

## Consequences

### What Changes
- New `api/mcp_server/` directory (~200 lines for Phase 0)
- New Render service (`yarnnn-mcp-server`, Starter plan)
- `mcp` pip package already in `requirements.txt` (needs Python >= 3.10 runtime)

### What Does NOT Change
- All existing service code — untouched
- `execute_deliverable_generation()` — same pipeline, new `trigger_context` type (Phase 1)
- All existing tables — no schema changes
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
