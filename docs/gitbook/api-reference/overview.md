# API Reference

YARNNN exposes a REST API for chat, integrations, and deliverable lifecycle management.

## Base URL

```text
https://api.yarnnn.com
```

## Core endpoint groups

| Group | Base path |
|---|---|
| Chat | `/api/chat` |
| Deliverables | `/api/deliverables` |
| Integrations | `/api/integrations` |
| Limits | `/api/user/limits` |
| System | `/api/system` |

## Health check

```text
GET /health
```

Response:

```json
{
  "status": "ok",
  "version": "5.0.0"
}
```

## Authentication

All `/api/*` endpoints require a Bearer token.

```text
Authorization: Bearer <token>
```

See [Authentication](authentication.md).

## Error format

Most errors return:

```json
{
  "detail": "Description of what went wrong"
}
```
