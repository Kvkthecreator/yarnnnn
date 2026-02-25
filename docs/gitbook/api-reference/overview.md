# API Reference

YARNNN provides a REST API for programmatic access to the AI assistant and deliverable management.

## Base URL

```
https://api.yarnnn.com
```

## Authentication

All requests require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <your-token>
```

See [Authentication](authentication.md) for details on obtaining tokens.

## Available endpoints

| Section | Description |
|---|---|
| [Authentication](authentication.md) | Sign in and manage tokens |
| [Chat](chat.md) | Send messages to the AI assistant |
| [Deliverables](deliverables.md) | Create and manage deliverables |

## Response format

All responses are JSON. Errors return a structured message:

```json
{
  "detail": "Description of what went wrong"
}
```

## Rate limits

Usage limits are applied per account based on your plan. See [Plans](../plans/plans.md) for details.
