# Authentication

## REST API

Every `/api/*` endpoint requires a bearer token.

```text
Authorization: Bearer <your-token>
```

Sign in through the YARNNN app; it manages session and token refresh. Use that access token for API calls.

### Scope

Requests resolve to a **principal** (who is calling) acting in a **workspace** (where). Both matter:

- The principal is the identity every write is attributed to
- The workspace is the boundary reads and writes are confined to

If you belong to more than one workspace, the target is selected per request. Everything you write lands attributed to you, in that workspace.

### Failures

| Code | Meaning |
|---|---|
| `401` | Missing or invalid token |
| `402` | A paid plan is required for this action |
| `403` | Authenticated, but this principal's grant doesn't reach here |
| `409` | Conflicting write — someone else changed the file first |
| `429` | Rate or budget limit |

A `403` usually means a grant has been narrowed rather than that something is broken — check the members roster.

## MCP

The MCP server has its own two paths:

**OAuth 2.1** with dynamic client registration — the path for ChatGPT and Claude.ai. You authorise once in the browser and the client holds a token.

**Bearer token** — the path for local clients like Claude Desktop and Claude Code, where one process serves one user. The token comes from your account settings.

Either way, the connection appears in **Workspace Settings → Access** as a named row, and revoking it there deletes its tokens.

See the [MCP connector guide](../integrations/mcp-connector.md).
