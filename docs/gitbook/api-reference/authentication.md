# Authentication

YARNNN API endpoints are protected and require an authenticated user token.

## Header format

```text
Authorization: Bearer <your-token>
```

## How tokens are issued

- Sign in through the YARNNN app.
- The app manages session/token refresh.
- Use that access token for API calls.

## Scope model

Requests are user-scoped. Data is isolated by authenticated user identity, including:

- chat sessions
- deliverables and versions
- integration sources and synced content
- memory/profile records

## Common auth failures

- `401`: missing/invalid token
- `403`: token valid but resource access is not allowed
