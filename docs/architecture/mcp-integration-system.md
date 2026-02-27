# MCP Integration System Architecture

> **Status**: Archived (2026-02-27)
> **Superseded by**: ADR-076 (Direct API for all platforms)
> **Previous version**: [previous_versions/mcp-integration-system.md](previous_versions/mcp-integration-system.md)

---

## Current State

The MCP Gateway was deleted in ADR-076 (2026-02-25). All four platforms now use Direct API clients:

| Platform | Client | Location |
|----------|--------|----------|
| Slack | `SlackAPIClient` | `api/integrations/core/slack_client.py` |
| Notion | `NotionAPIClient` | `api/integrations/core/notion_client.py` |
| Gmail/Calendar | `GoogleAPIClient` | `api/integrations/core/google_client.py` |

There is no MCP gateway, no subprocess management, no Node.js service.

The only MCP component in YARNNN is the **MCP Server** (`api/mcp_server/`, ADR-075) — which exposes YARNNN's data to external clients (Claude.ai, Claude Desktop), not the other way around.

## References

- [Context Pipeline](./context-pipeline.md) — how platform data flows through the system
- [Backend Orchestration](./backend-orchestration.md) — F1 (Platform Sync) section
- [ADR-076](../adr/ADR-076-direct-api-consolidation.md) — decision to delete MCP Gateway
- [ADR-075](../adr/ADR-075-mcp-server.md) — MCP Server (outbound, unrelated to platform integration)