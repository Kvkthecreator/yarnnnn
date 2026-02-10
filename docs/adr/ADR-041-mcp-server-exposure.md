# ADR-041: MCP Server Exposure

> **Status**: Proposed
> **Created**: 2026-02-10
> **Priority**: P3 (Strategic, longer timeline)
> **Related**: ADR-026 (Integration Architecture), ADR-038 (Claude Code Architecture Mapping)
> **Effort**: 2 months development
> **Prerequisite**: ADR-026 Section 3.3 provides initial blueprint

---

## Context

ADR-038 identified exposing YARNNN as an MCP server as an enhancement opportunity. This would enable Claude Code and other MCP clients to access YARNNN's context, deliverables, and execution capabilities.

### Current State

**YARNNN consumes MCP** — We already act as an MCP client:
```python
# integrations/core/client.py
class MCPClientManager:
    # Connects to Slack MCP server, Notion MCP server
    # Calls their tools, processes results
```

**YARNNN is not exposed** — No MCP server interface exists.

### Why This Matters

**Interoperability**: Claude Code users could access YARNNN context while coding:
```
Claude Code: "What does the user prefer for error handling?"
    → calls yarnnn://get_memories(tags=["preference"])
    → returns user's coding preferences from YARNNN context
```

**Ecosystem**: As MCP becomes standard, YARNNN should participate bidirectionally.

**Composability**: Other AI tools could orchestrate YARNNN capabilities.

---

## Decision

Expose YARNNN as an **MCP server** using stdio transport, enabling Claude Desktop and other MCP clients to access YARNNN's tools.

### Architecture

```
Claude Desktop (MCP Client)
    ↓ stdio
YARNNN MCP Server
    ├── Tool definitions (subset of TP tools)
    ├── Authentication bridge (JWT → UserClient)
    └── Handler adapters
        ↓ internal calls
    YARNNN Services
        ├── project_tools.py handlers
        ├── Supabase (RLS enforced)
        └── LLMs
```

### Scope: Three Tiers

| Tier | Tools | Purpose | Priority |
|------|-------|---------|----------|
| **Tier 1** | 8 tools | Core value (context + deliverables) | MVP |
| **Tier 2** | 7 tools | Extended (work execution, domains) | Phase 2 |
| **Tier 3** | 5+ tools | Advanced (sessions, integrations) | Future |

---

## Specification

### 1. MCP Server Structure

```python
# mcp/server.py

from mcp import Server, Tool, Resource
from mcp.transports import StdioTransport

class YarnnnMCPServer(Server):
    """YARNNN MCP Server exposing context and deliverable tools."""

    def __init__(self):
        super().__init__(
            name="yarnnn",
            version="1.0.0",
            description="Access YARNNN context, memories, and deliverables"
        )
        self._register_tools()

    def _register_tools(self):
        """Register Tier 1 tools."""
        # Context tools
        self.register_tool(Tool(
            name="get_memories",
            description="Retrieve user's context memories with optional filtering",
            parameters={
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["user", "domain"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "search": {"type": "string"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ))

        self.register_tool(Tool(
            name="add_memory",
            description="Store a new context memory",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "domain_id": {"type": "string"}
                },
                "required": ["content"]
            }
        ))

        self.register_tool(Tool(
            name="search_memories",
            description="Semantic search across memories",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ))

        # Deliverable tools
        self.register_tool(Tool(
            name="list_deliverables",
            description="List user's recurring deliverables",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "paused", "all"]},
                    "type": {"type": "string"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ))

        self.register_tool(Tool(
            name="get_deliverable",
            description="Get deliverable details with version history",
            parameters={
                "type": "object",
                "properties": {
                    "deliverable_id": {"type": "string"}
                },
                "required": ["deliverable_id"]
            }
        ))

        self.register_tool(Tool(
            name="get_latest_version",
            description="Get the latest generated version of a deliverable",
            parameters={
                "type": "object",
                "properties": {
                    "deliverable_id": {"type": "string"}
                },
                "required": ["deliverable_id"]
            }
        ))

        self.register_tool(Tool(
            name="run_deliverable",
            description="Trigger ad-hoc deliverable generation",
            parameters={
                "type": "object",
                "properties": {
                    "deliverable_id": {"type": "string"}
                },
                "required": ["deliverable_id"]
            }
        ))

        # Domain tools
        self.register_tool(Tool(
            name="list_domains",
            description="List available context domains",
            parameters={"type": "object", "properties": {}}
        ))

    async def handle_tool(self, name: str, arguments: dict) -> dict:
        """Route tool calls to handlers."""
        handler = self._tool_handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}

        return await handler(self._auth, arguments)
```

### 2. Authentication Bridge

```python
# mcp/auth.py

import os
from services.supabase import get_user_client_from_token, AuthenticatedClient

def get_auth_from_env() -> AuthenticatedClient:
    """
    Get authenticated client from environment.

    Expects YARNNN_TOKEN environment variable containing JWT.
    """
    token = os.environ.get("YARNNN_TOKEN")
    if not token:
        raise ValueError("YARNNN_TOKEN environment variable required")

    return get_user_client_from_token(token)

# Alternative: OAuth flow through Claude Desktop (future)
```

### 3. Tool Handler Adapters

```python
# mcp/handlers.py

from services.project_tools import (
    handle_list_memories,
    handle_create_memory,
    handle_list_deliverables,
    handle_get_deliverable,
    handle_run_deliverable,
)

class ToolHandlers:
    """Adapters between MCP tools and existing TP tool handlers."""

    def __init__(self, auth: AuthenticatedClient):
        self.auth = auth

    async def get_memories(self, arguments: dict) -> dict:
        """Adapter for list_memories."""
        result = await handle_list_memories(self.auth, {
            "scope": arguments.get("scope", "user"),
            "tag": arguments.get("tags", []),
            "search": arguments.get("search"),
            "limit": arguments.get("limit", 20),
        })
        # Strip ui_action (not relevant for MCP)
        result.pop("ui_action", None)
        return result

    async def add_memory(self, arguments: dict) -> dict:
        """Adapter for create_memory."""
        result = await handle_create_memory(self.auth, {
            "content": arguments["content"],
            "tags": arguments.get("tags", []),
            "domain_id": arguments.get("domain_id"),
        })
        result.pop("ui_action", None)
        return result

    async def list_deliverables(self, arguments: dict) -> dict:
        """Adapter for list_deliverables."""
        result = await handle_list_deliverables(self.auth, {
            "status": arguments.get("status", "active"),
            "type": arguments.get("type"),
            "limit": arguments.get("limit", 20),
        })
        result.pop("ui_action", None)
        return result

    async def get_deliverable(self, arguments: dict) -> dict:
        """Adapter for get_deliverable."""
        result = await handle_get_deliverable(self.auth, {
            "deliverable_id": arguments["deliverable_id"],
        })
        result.pop("ui_action", None)
        return result

    async def run_deliverable(self, arguments: dict) -> dict:
        """Adapter for run_deliverable."""
        result = await handle_run_deliverable(self.auth, {
            "deliverable_id": arguments["deliverable_id"],
        })
        result.pop("ui_action", None)
        return result
```

### 4. Entry Point

```python
# mcp/__main__.py

import asyncio
from mcp.transports import StdioTransport
from mcp.server import YarnnnMCPServer
from mcp.auth import get_auth_from_env

async def main():
    """MCP server entry point."""
    # Initialize auth from environment
    auth = get_auth_from_env()

    # Create server
    server = YarnnnMCPServer()
    server.set_auth(auth)

    # Run with stdio transport
    transport = StdioTransport()
    await server.run(transport)

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Claude Desktop Configuration

```json
// Claude Desktop config
{
  "mcpServers": {
    "yarnnn": {
      "command": "python",
      "args": ["-m", "api.mcp"],
      "env": {
        "YARNNN_TOKEN": "<user-jwt-token>"
      }
    }
  }
}
```

---

## Tool Tiers

### Tier 1: Core Value (MVP)

| Tool | Maps to Handler | Purpose |
|------|-----------------|---------|
| `get_memories` | handle_list_memories | Retrieve context |
| `add_memory` | handle_create_memory | Store context |
| `search_memories` | handle_list_memories + search | Semantic search |
| `list_deliverables` | handle_list_deliverables | Discover deliverables |
| `get_deliverable` | handle_get_deliverable | Full deliverable info |
| `get_latest_version` | handle_get_deliverable | Latest output content |
| `run_deliverable` | handle_run_deliverable | Trigger generation |
| `list_domains` | domains.list_domains | Context scopes |

### Tier 2: Extended Capabilities

| Tool | Purpose |
|------|---------|
| `create_work` | Trigger work agents |
| `get_work_status` | Check work progress |
| `get_work_output` | Retrieve work results |
| `create_deliverable` | Set up new recurring deliverable |
| `update_deliverable` | Modify deliverable settings |
| `get_domain_context` | Domain-specific memories |
| `update_memory` | Modify existing memory |

### Tier 3: Advanced

| Tool | Purpose |
|------|---------|
| `start_chat_session` | Begin TP conversation |
| `send_chat_message` | Multi-turn chat |
| `list_integrations` | Connected platforms |
| `get_integration_destinations` | Available export targets |
| `bulk_import_memories` | Batch context import |

---

## Implementation Plan

### Phase 1: Foundation (2 weeks)

1. Create `/api/mcp/` directory structure
2. Implement MCP server with stdio transport
3. Implement authentication bridge
4. Add 3 tools for POC: get_memories, list_deliverables, run_deliverable
5. Test with Claude Desktop manually

### Phase 2: Tier 1 Tools (2 weeks)

1. Add remaining Tier 1 tools (8 total)
2. Implement all handler adapters
3. Add error handling and validation
4. Write integration tests
5. Document Claude Desktop configuration

### Phase 3: Hardening (2 weeks)

1. Rate limiting for MCP calls
2. Audit logging
3. Token refresh handling
4. Error response standardization
5. Performance testing

### Phase 4: Tier 2 (2 weeks)

1. Add Tier 2 tools (7 more)
2. Add work execution tools
3. Add deliverable creation
4. Extended testing

---

## Deployment Options

### Option A: Bundled with API (Recommended)

```
yarnnn-api/
├── api/
│   ├── routes/
│   └── services/
└── mcp/
    ├── __main__.py
    ├── server.py
    ├── auth.py
    └── handlers.py
```

MCP server is part of the same codebase, shares service layer.

Claude Desktop spawns: `python -m api.mcp`

### Option B: Separate Package

Publish `yarnnn-mcp` to PyPI, users install separately.

**Rejected**: Adds maintenance burden, version sync issues.

---

## Authentication Considerations

### Current Approach: JWT in Environment

Pros:
- Simple to implement
- Works with existing auth
- No additional OAuth flow

Cons:
- Token in environment (security concern)
- Token expiry handling unclear
- User must manually set token

### Future Enhancement: OAuth Device Flow

Claude Desktop could authenticate via OAuth:
1. User clicks "Connect YARNNN"
2. Claude Desktop initiates device flow
3. User approves in browser
4. Token stored securely by Claude Desktop

**Deferred**: Start with env token, add OAuth later.

---

## Consequences

### Positive

1. **Interoperability** — Claude Code can access YARNNN context
2. **Ecosystem participation** — YARNNN as first-class MCP citizen
3. **Composability** — Other tools can orchestrate YARNNN
4. **Minimal new code** — Reuses existing tool handlers

### Negative

1. **Security surface** — New attack vector via MCP
2. **Maintenance** — Another interface to support
3. **Auth complexity** — Token management for external clients

### Risks

1. **Token security** — JWT in process environment
   - Mitigation: Clear documentation, future OAuth

2. **API changes** — Internal tool changes break MCP
   - Mitigation: Adapter layer insulates

3. **Rate abuse** — External clients overwhelming API
   - Mitigation: MCP-level rate limiting

---

## Open Questions

1. **Token lifecycle** — How to handle refresh for long-running sessions?
   - Defer: Start with long-lived tokens, add refresh later

2. **Multi-user** — Can one MCP server serve multiple users?
   - No: Each user needs own server instance with own token

3. **Tool versioning** — How to handle breaking changes?
   - Defer: Version in server metadata, document migration

4. **Resources** — Should we expose MCP resources (not just tools)?
   - Defer: Tools only for MVP, add resources in Phase 4

---

## References

- [ADR-026: Integration Architecture](./ADR-026-integration-architecture.md) — Section 3.3 MCP server blueprint
- [ADR-038: Claude Code Architecture Mapping](./ADR-038-claude-code-architecture-mapping.md) — Tool equivalence
- [MCP Specification](https://modelcontextprotocol.io/) — Protocol docs
- `integrations/core/client.py` — Existing MCP client implementation

---

*This ADR proposes exposing YARNNN as an MCP server to enable interoperability with Claude Code and other MCP clients.*
