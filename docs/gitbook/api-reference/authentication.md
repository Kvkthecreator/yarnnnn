# Authentication

YARNNN API endpoints are user-scoped and require an authenticated bearer token.

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
- agents and runs
- integration sources and synced content
- profile, memory, and knowledge records

## Common auth failures

- `401`: missing/invalid token
- `403`: token valid but resource access is not allowed
