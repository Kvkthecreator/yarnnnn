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

### Reconnection Required

Users must reconnect Slack when:
1. New OAuth scopes are added (e.g., `im:write` for DMs)
2. `authed_user_id` needs to be captured (for `"self"` resolution)
3. Token has expired or been revoked

The reconnection flow captures all required metadata fresh from Slack's OAuth response.

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing required arguments: channel_id` | Used `channel` param | Use `channel_id` |
| `channel_not_found` | Invalid channel format | Use `list_platform_resources` first |
| `not_in_channel` | Bot not added to channel | Invite bot or use public channel |
| `missing_scope` | Bot lacks required OAuth scope | User must reconnect Slack with new scopes |
| `Cannot resolve 'self'` | `authed_user_id` not in metadata | User must reconnect Slack (captures ID during OAuth) |

### Required OAuth Scopes

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages to channels |
| `channels:read` | List public channels |
| `channels:history` | Read channel history |
| `channels:join` | Join public channels |
| `groups:read` | List private channels |
| `groups:history` | Read private channel history |
| `users:read` | List workspace users |
| `im:write` | Open and send DMs (required for `"self"` and user ID targets) |

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
- Package: `@notionhq/notion-mcp-server` (via Claude AI integration)
- Transport: stdio

### Parameter Quirks

| What you might expect | What actually works | Notes |
|-----------------------|---------------------|-------|
| `{page_id: "abc123", text: "Hi"}` | ❌ Does not work | Use structured `parent` and `rich_text` |
| `{parent: {page_id: "..."}, rich_text: [...]}` | ✅ Works | Required structure for comments |
| `page_id: "abc-123-def"` | ✅ Works | UUID with dashes |
| `page_id: "abc123def"` | ✅ Works | UUID without dashes |
| `page_id: "https://notion.so/..."` | ✅ Works | Full URL supported |

### Page ID Formats

```
✅ a1b2c3d4-e5f6-7890-abcd-ef1234567890  (UUID with dashes)
✅ a1b2c3d4e5f67890abcdef1234567890      (UUID without dashes)
✅ https://notion.so/workspace/Page-abc123  (Full URL)
✅ https://myspace.notion.site/Page-abc123  (Notion Sites URL)
❌ @page-name                              (Not valid)
❌ page-name                               (Not valid - use UUID or URL)
```

### Adding Comments (platform.send)

**Correct MCP structure for `notion-create-comment`:**

```json
{
  "parent": {
    "page_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  },
  "rich_text": [
    {
      "type": "text",
      "text": {
        "content": "Your comment text here"
      }
    }
  ]
}
```

**TP usage:**
```
Execute(action="platform.send", target="platform:notion", params={page_id: "abc123...", content: "Note added"})
```

The system automatically transforms this into the correct MCP structure.

### Creating Pages

Use `notion-create-pages` with proper parent:

```json
{
  "parent": {"page_id": "parent-page-uuid"},
  "pages": [{
    "properties": {"title": "New Page Title"},
    "content": "# Section 1\nContent here"
  }]
}
```

### Fetching Pages First

**Best practice:** Always use `notion-fetch` before updating to understand page structure:

```
notion-fetch with {id: "page-uuid-or-url"}
```

Returns Notion-flavored Markdown with the page content.

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `object_not_found` | Page doesn't exist or no access | Ensure page is shared with the integration |
| `validation_error` | Malformed page ID or wrong structure | Use UUID format or full URL |
| `Could not find...` | Page not shared with integration | User must share page with Notion integration |
| `unauthorized` | Token expired or invalid | User must reconnect Notion |
| `restricted_resource` | Commenting disabled on page | Enable comments on the Notion page |

### Required Permissions

The Notion integration must have access to:
- The specific page (user must share it with the integration)
- Comment permission (if adding comments)
- Edit permission (if updating page content)

### Searching for Pages

Use `notion-search` to find pages before operating on them:

```json
{
  "query": "meeting notes",
  "query_type": "internal"
}
```

Returns page IDs and URLs that can be used with other operations.

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
