# Platform Integration Quirks

> **Purpose**: Document platform-specific behaviors, gotchas, and workarounds
> **Updated**: 2026-02-11
> **Related**: [ADR-047: Platform Integration Validation](../adr/ADR-047-platform-integration-validation.md)

---

## Overview

Each platform (Slack, Gmail, Notion) has unique requirements that differ from what might seem intuitive. This guide documents known quirks to prevent debugging in production.

---

## Slack

### MCP Server
- Package: `@modelcontextprotocol/server-slack`
- Transport: stdio subprocess

### Parameter Quirks

| What you might expect | What actually works | Notes |
|-----------------------|---------------------|-------|
| `channel: "#general"` | `channel_id: "#general"` | MCP param is `channel_id` |
| `channel: "@username"` | ❌ Does not work | @mentions are not API identifiers |
| `channel: "@me"` | ❌ Does not work | Use DM channel lookup |
| `channel: "general"` | ❌ May not work | Include `#` prefix or use ID |

### Valid Channel Formats

```
✅ self            (DM to the user - recommended!)
✅ C0123ABC456     (Channel ID - posts to channel)
✅ #general        (Channel name - posts to channel)
✅ #team-updates   (Channel name - posts to channel)
✅ U0123ABC456     (User ID - auto-opens DM, then posts)
❌ @username       (Not valid - use "self" or user ID)
❌ @me             (Not valid - use "self")
❌ general         (Missing # prefix)
```

### Sending DMs

**Use `"self"` to DM the user:**

```
Execute(action="platform.send", target="platform:slack", params={channel: "self", message: "Hey!"})
```

This resolves to the user's Slack ID (stored during OAuth) and auto-opens a DM.

**Or use a specific user ID** (starts with `U`):

```
Execute(action="platform.send", target="platform:slack", params={channel: "U0123ABC456", message: "Hey!"})
```

The system automatically:
1. Resolves `"self"` to the authed user's Slack ID (if used)
2. Opens a DM channel with the user (`conversations.open`)
3. Sends the message to that DM channel

**How to get other users' IDs**:
- Use `list_platform_resources(platform="slack")` - returns users with their IDs

**Alternative**: For simple notifications, use `send_notification` (sends email).

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing required arguments: channel_id` | Used `channel` param | Use `channel_id` |
| `channel_not_found` | Invalid channel format | Use `list_platform_resources` first |
| `not_in_channel` | Bot not added to channel | Invite bot or use public channel |

---

## Gmail

### Integration Method
- Direct API (not MCP)
- Uses OAuth refresh token flow

### Parameter Quirks

| What you might expect | What actually works | Notes |
|-----------------------|---------------------|-------|
| `access_token` | `refresh_token` | Gmail uses refresh flow |
| Send immediately | Works | But prefer drafts for review |

### Authentication

Gmail requires:
- `refresh_token` (stored encrypted in `user_integrations.metadata`)
- `client_id` (from environment)
- `client_secret` (from environment)

Access token is refreshed automatically on each call.

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `invalid_grant` | Refresh token expired | User must reconnect Gmail |
| `insufficient_scope` | Missing permissions | Re-auth with correct scopes |
| `Missing refresh_token` | OAuth didn't return refresh | Ensure `access_type=offline` |

---

## Notion

### MCP Server
- Package: `@notionhq/notion-mcp-server`
- Transport: stdio with `--transport stdio` flag

### Parameter Quirks

| What you might expect | What actually works | Notes |
|-----------------------|---------------------|-------|
| `page_id: "abc123"` | Works | UUID format |
| `page_id: "https://notion.so/..."` | May work | URL format supported |

### Page ID Formats

```
✅ abc123def456...  (UUID)
✅ https://notion.so/workspace/Page-abc123  (URL)
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `object_not_found` | Page doesn't exist or no access | Check integration has page access |
| `validation_error` | Malformed page ID | Use `search_notion_pages` to find valid IDs |

---

## Adding New Platforms

When integrating a new platform:

1. **Document immediately**: Add to this file before shipping
2. **Test in isolation**: Validate MCP parameter names match documentation
3. **Capture errors**: Log actual error messages for this guide
4. **Update TP docs**: Add platform guidance to `thinking_partner.py`

### Checklist for New Platform

- [ ] MCP server package name documented
- [ ] Parameter name mapping verified (what TP sends vs what MCP expects)
- [ ] Valid/invalid formats documented with examples
- [ ] Authentication flow documented
- [ ] Common errors and fixes listed
- [ ] TP system prompt updated
- [ ] Added to CHANGELOG.md

---

## See Also

- [CHANGELOG.md](CHANGELOG.md) - Version history of integration changes
- [ADR-026: Integration Architecture](../adr/ADR-026-integration-architecture.md)
- [ADR-047: Platform Integration Validation](../adr/ADR-047-platform-integration-validation.md)
- [Testing Environment Guide](../testing/TESTING-ENVIRONMENT.md)
