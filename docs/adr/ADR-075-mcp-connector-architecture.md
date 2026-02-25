# ADR-075: MCP Connector — Technical Architecture

**Date**: 2026-02-25
**Status**: Draft (Phase 0 implemented)
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
│  │  └─ system_      │               │              └─ __main__  │
│  │     state.py     │               │                            │
│  └─ ...             └─ ...          └─ ...                       │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Render Services (separate processes, same codebase):            │
│                                                                  │
│  yarnnn-api          uvicorn main:app                            │
│  yarnnn-worker       python -m jobs.worker                       │
│  yarnnn-scheduler    cd api && python -m jobs.unified_scheduler  │
│  yarnnn-mcp-server   cd api && python -m mcp_server  ◄── NEW    │
└──────────────────────────────────────────────────────────────────┘
```

### MCP Server Module

```
api/mcp_server/
├── __init__.py          # Module docstring
├── __main__.py          # Entry point: transport selection, env loading
├── server.py            # FastMCP instance + tool registration
└── auth.py              # YARNNN_TOKEN → user-scoped Supabase client
```

**Why `mcp_server/` not `mcp/`:** The pip package is named `mcp`. A directory named `api/mcp/` would shadow it when Python resolves imports from the `api/` working directory. Underscore avoids the collision.

**Key design constraint:** Tool handlers call existing service functions directly. No new query logic. If `handle_get_system_state()` works for TP, it works for MCP.

### Transport Deployment

| Transport | Start Command | Deployment | Client |
|-----------|--------------|------------|--------|
| stdio | `cd api && python -m mcp_server` | User's machine (spawned by Claude) | Claude Desktop, Claude Code |
| Streamable HTTP | `cd api && python -m mcp_server http` | Render service (`yarnnn-mcp-server`) | ChatGPT, remote MCP clients |

Both transports share the same `FastMCP` server instance and tool handlers.

### Authentication Bridge

The auth bridge (`mcp_server/auth.py`) reads `YARNNN_TOKEN` from environment and creates a user-scoped Supabase client using the same pattern as `services/supabase.get_user_client()`:

1. `decode_jwt_payload(token)` → extract `sub` (user_id) and `email`
2. `create_client(SUPABASE_URL, SUPABASE_ANON_KEY)` → create Supabase client
3. `client.postgrest.auth(token)` → scope client to user (RLS enforced)
4. Return `AuthenticatedClient(client, user_id, email)`

**RLS preserved:** All tool handlers operate through the user-scoped client. No service-role bypass.

**For stdio transport:** One process = one user. Auth runs once at lifespan startup.

**For HTTP transport (Phase 2):** Auth will need to move to per-request (token in Authorization header).

### Render Deployment (Phase 2)

New Render service: `yarnnn-mcp-server` (Python, Starter plan)

**Note:** The MCP Gateway has been eliminated (ADR-076). This is now the only MCP-related Render service.

**Env var parity** (see CLAUDE.md § Render Service Parity):
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`
- `ANTHROPIC_API_KEY` (for deliverable generation in Phase 1)
- `INTEGRATION_ENCRYPTION_KEY` (for token decryption during delivery)

**Python version requirement:** `mcp` package requires Python >= 3.10. Render default Python runtime satisfies this. Local dev requires Python 3.10+.

---

## Implementation: Phase 0 — Hello World Validation (Implemented)

### The Validation Tool: `get_status`

Single read-only tool that exercises the full auth chain (token → user_id → Supabase query → structured response). No side effects. Wraps existing `handle_get_system_state()` from `services/primitives/system_state.py`.

### Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `api/mcp_server/__init__.py` | Module docstring | 7 |
| `api/mcp_server/auth.py` | Auth bridge: YARNNN_TOKEN → AuthenticatedClient | 60 |
| `api/mcp_server/server.py` | FastMCP instance + `get_status` tool | 68 |
| `api/mcp_server/__main__.py` | Entry point with transport selection | 25 |

### Verification Status

- [x] All files parse as valid Python
- [x] `mcp_server.auth` imports resolve (`services.supabase` dependencies OK)
- [x] `services.primitives.system_state` imports resolve
- [ ] Runtime test requires Python >= 3.10 + `mcp` pip package installed
- [ ] Claude Desktop integration test pending

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "yarnnn": {
      "command": "python3",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/yarnnn/api",
      "env": {
        "YARNNN_TOKEN": "<supabase-jwt>",
        "SUPABASE_URL": "<url>",
        "SUPABASE_ANON_KEY": "<key>"
      }
    }
  }
}
```

### Claude Code Configuration

```bash
claude mcp add --transport stdio yarnnn -- \
  bash -c "cd /path/to/yarnnn/api && python3 -m mcp_server"
```

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

## Implementation: Phase 2 — Streamable HTTP + ChatGPT

1. Deploy `yarnnn-mcp-server` on Render with start command: `cd api && python -m mcp_server http`
2. Add health check endpoint
3. Move auth to per-request (Authorization header) for multi-user support
4. Document ChatGPT Developer Mode configuration
5. Test with ChatGPT

---

## Consequences

### What Changes
- New `api/mcp_server/` directory (~160 lines for Phase 0)
- New Render service for HTTP transport (Phase 2)
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
- [ADR-050: MCP Gateway Architecture](./ADR-050-mcp-gateway-architecture.md) — Existing outbound MCP infrastructure
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — `FastMCP` server implementation
- [MCP Specification: Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
