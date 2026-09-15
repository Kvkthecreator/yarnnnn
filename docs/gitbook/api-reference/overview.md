# API Overview

Most integrations should use the [MCP connector](../integrations/mcp-connector.md) — it's the supported, stable, intent-shaped way in, and it works from any MCP-capable client without writing code.

The REST API below is what the YARNNN app itself uses. It's available, but it tracks the product closely and changes with it.

## Base URL

```text
https://api.yarnnn.com
```

## Machine-readable spec

The authoritative, always-current surface is the OpenAPI 3.1 document:

```text
https://yarnnn.com/openapi.json
```

Generate a client from that rather than transcribing endpoints from documentation. The developer hub at [yarnnn.com/developers](https://yarnnn.com/developers) covers the same ground with worked examples.

## Endpoint groups

| Group | Base path | What it covers |
|---|---|---|
| Workspace | `/api/workspace` | Files, revisions, members, shares |
| Lanes | `/api/lanes` | Chat lanes and turns |
| Studio | `/api/studio` | Artifacts, layouts, blocks (the route kept its original name after the app became Slides) |
| Documents | `/api/documents` | Uploads |
| Agents | `/api/agents` | The roster |
| Integrations | `/api/integrations` | Platform connections |
| Subscription | `/api/subscription` | Plan, balance, top-ups |
| Budget | `/api/budget` | Spend envelope |
| Standing work | `/api/standing` | Files declared to stay current on a schedule |
| Account | `/api/account` | Account-level state |

## Errors

Structured JSON, never HTML:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "hint": "..."
  }
}
```

## Health

```text
GET /health
```

## Authentication

Every `/api/*` endpoint requires a bearer token — see [Authentication](authentication.md).
