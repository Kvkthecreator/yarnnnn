# ADR-076: Eliminate MCP Gateway — All Platforms Use Direct API

**Date**: 2026-02-25
**Status**: Implemented
**Supersedes**: ADR-050 (MCP Gateway Architecture)
**Related**: ADR-075 (MCP Connector Architecture — inbound, unaffected)

---

## Context

The MCP Gateway (`mcp-gateway/`, Node.js, Render `srv-d66jir15pdvs73aqsmk0`, Starter $7/mo) existed to proxy Slack API calls through an MCP subprocess (`@modelcontextprotocol/server-slack`). It spawned a Node.js MCP server as a child process and forwarded 3 REST calls to it.

Meanwhile, 3 out of 4 platforms already used Direct API clients:

| Platform | Before ADR-076 | Client |
|----------|---------------|--------|
| Slack | MCP Gateway (Node.js subprocess) | `MCPClientManager` / `mcp_gateway.py` |
| Notion | Direct API | `NotionAPIClient` |
| Gmail | Direct API | `GoogleAPIClient` |
| Calendar | Direct API | `GoogleAPIClient` |

The gateway added:
- A $7/mo Render service
- A network hop (Python → HTTP → Node.js → MCP stdio → Slack REST API)
- A separate Node.js codebase to maintain
- Subprocess management complexity (sessions, locks, env vars)

The Slack exporter already made direct Slack REST calls for DM delivery, proving the direct approach works.

---

## Decision

**Eliminate the MCP Gateway entirely.** Replace it with a `SlackAPIClient` that calls Slack's Web API directly from Python, matching the `NotionAPIClient` and `GoogleAPIClient` pattern.

The inbound MCP server (`api/mcp_server/`, ADR-075) is NOT affected — it stays as-is.

---

## Implementation

### New: `api/integrations/core/slack_client.py`

`SlackAPIClient` class following the established Direct API pattern:

- `_request_with_retry()` — 3 retries, Slack 429 + `Retry-After` header handling
- `list_channels(bot_token)` → normalized channel list
- `get_channel_history(bot_token, channel_id)` → message list
- `get_channel_history_with_error(bot_token, channel_id)` → `(messages, error_code)` for auto-join flow
- `post_message(bot_token, channel_id, text, blocks, thread_ts)` → Slack response
- `get_channel_info(bot_token, channel_id)` → channel info
- `join_channel(bot_token, channel_id)` → bool
- `get_slack_client()` singleton factory

No token refresh needed — Slack bot tokens don't expire.

### Migrated consumers (8 files)

| File | Change |
|------|--------|
| `api/services/platform_tools.py` | `_handle_mcp_tool()` → `_handle_slack_tool()` |
| `api/integrations/exporters/slack.py` | `call_platform_tool()` → `slack_client.post_message()` |
| `api/workers/platform_worker.py` | `MCPClientManager` → `get_slack_client()` |
| `api/jobs/import_jobs.py` | `get_mcp_manager()` → `get_slack_client()` + `get_notion_client()` |
| `api/services/landscape.py` | `mcp_manager.list_slack_channels()` → `slack_client.list_channels()` |
| `api/services/project_tools.py` | Both Slack and Notion paths updated |
| `api/routes/integrations.py` | Removed `MCP_AVAILABLE` check, session invalidation |
| `api/integrations/validation.py` | All 3 test functions updated (also fixed broken Gmail test) |

### Deleted

| Item | Description |
|------|-------------|
| `api/services/mcp_gateway.py` | Gateway HTTP client |
| `api/integrations/core/client.py` | `MCPClientManager`, `get_mcp_manager()`, MCP SDK imports |
| `mcp-gateway/` | Entire Node.js service directory |

### Configuration

- `render.yaml`: Removed `yarnnn-mcp-gateway` service + `MCP_GATEWAY_URL` env vars
- `CLAUDE.md`: Removed gateway from service table and env var list

---

## Final Architecture

```
api/integrations/core/
├── slack_client.py     SlackAPIClient    → Slack Web API (conversations.*, chat.*)
├── notion_client.py    NotionAPIClient   → Notion REST API (v1/*)
├── google_client.py    GoogleAPIClient   → Google APIs (Gmail, Calendar)
└── tokens.py           TokenManager      → OAuth token encryption/decryption
```

All four platforms: same pattern, same language, no subprocess management, no gateway service.

---

## Consequences

### Positive
- Eliminates $7/mo Render service
- Removes network hop (Python → HTTP → Node → MCP → Slack becomes Python → Slack)
- Single codebase (Python only)
- Unified pattern for all 4 platforms
- No subprocess management or MCP session lifecycle

### Negative
- Loses MCP ecosystem "plug-and-play" for future Slack-like integrations
- Must implement retry/rate-limit logic per platform (already done for all 4)

### Mitigated
- The MCP ecosystem benefit was theoretical — in practice, 3/4 platforms couldn't use MCP anyway (ADR-050 documents this). The gateway only wrapped 3 REST calls.
- ADR-050's "Learnings for Future Integrations" section remains valid. If a future platform has an MCP server that genuinely adds value beyond REST, we can evaluate then.

---

## See Also

- [ADR-050: MCP Gateway Architecture](ADR-050-mcp-gateway-architecture.md) — Superseded (historical context + learnings)
- [ADR-075: MCP Connector Architecture](ADR-075-mcp-connector-architecture.md) — Inbound MCP server (unaffected)
