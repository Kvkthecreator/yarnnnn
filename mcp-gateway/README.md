# YARNNN MCP Gateway

Node.js service that handles MCP (Model Context Protocol) communication for YARNNN.

## Architecture (ADR-050)

```
┌─────────────────────────────────────────┐
│         yarnnn-mcp-gateway              │
│                                         │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ MCP Server  │  │ MCP Client Mgr   │  │
│  │ (inbound)   │  │ (outbound)       │  │
│  │             │  │                  │  │
│  │ Claude Code │  │ → Slack MCP      │  │
│  │ calls in    │  │ → Notion MCP     │  │
│  └─────────────┘  └──────────────────┘  │
│          ↑              ↑               │
│          └──── HTTP ────┘               │
└─────────────────────────────────────────┘
                  ↑
            yarnnn-api
```

## API

### Health Check

```
GET /health

Response: { status: "healthy", service: "yarnnn-mcp-gateway" }
```

### List Provider Tools

```
GET /api/mcp/tools/:provider

Response: {
  success: true,
  provider: "slack",
  tools: [
    { name: "slack_post_message", description: "..." },
    ...
  ]
}
```

### Call Tool

```
POST /api/mcp/tools/:provider/:tool
Content-Type: application/json

{
  "args": { "channel_id": "C0123", "text": "Hello!" },
  "auth": {
    "token": "xoxb-...",
    "metadata": { "team_id": "T0123" }
  }
}

Response: {
  success: true,
  provider: "slack",
  tool: "slack_post_message",
  result: { "ts": "1234567890.123456", "channel": "C0123" }
}
```

## Development

```bash
npm install
npm run dev
```

## Deployment (Render)

- **Runtime**: Node.js
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`
- **Environment**: `PORT` (auto-set by Render)

## Supported Providers

| Provider | MCP Server | Status |
|----------|-----------|--------|
| Slack | @modelcontextprotocol/server-slack | ✅ |
| Notion | @notionhq/notion-mcp-server | ✅ |
| Gmail | Direct API (not MCP) | Planned |
| Calendar | Direct API (not MCP) | Planned |
