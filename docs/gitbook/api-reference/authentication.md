# Authentication

YARNNN uses token-based authentication. All API requests require a valid token.

## Getting started

Authentication is handled through the YARNNN web app at [app.yarnnn.com](https://app.yarnnn.com). Sign up with email and password.

## Using the API

Include your token in the `Authorization` header of every request:

```
Authorization: Bearer <your-token>
```

## Token management

- Tokens are issued on login
- Expired tokens are automatically refreshed by the web app
- You can revoke tokens by logging out

## Data isolation

All API requests are scoped to your account. You can only access your own data — synced content, deliverables, preferences, and conversations.
