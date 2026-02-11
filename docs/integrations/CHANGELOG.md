# Integration Changelog

Track changes to platform integrations, MCP servers, and discovered quirks.

---

## 2026-02-11

### Slack

**New Features**:
- **`"self"` channel target**: Use `channel: "self"` to DM the user directly - resolves to their Slack ID automatically
- **Auto-open DM for user IDs**: `platform.send` with `channel: "U0123ABC456"` automatically opens a DM channel
- **Store authed_user_id**: OAuth now captures the authorizing user's Slack ID for "self" resolution
- Platform registry for structured validation and param mapping

**Breaking Changes**:
- `platform.send` action now requires valid channel format
- MCP server (`@modelcontextprotocol/server-slack`) expects `channel_id` parameter, not `channel`

**Known Issues**:
- `@username` / `@me` / `@self` formats are NOT valid - use `"self"` or user ID (U...) instead
- Existing Slack integrations need to reconnect to:
  - Capture `authed_user_id` for "self" resolution
  - Get `im:write` scope for DM access

**Discovered Quirks** (via production debugging):
- `missing_scope` error when calling `conversations.open` without `im:write` scope
- OAuth must store `authed_user.id` from Slack response (not just team info)
- MCP parameter is `channel_id` not `channel`, `text` not `message`

**Valid Formats**:
- `self` - DM to the user (recommended!)
- `C0123ABC456` - Channel ID (posts to channel)
- `#general` - Channel name (posts to channel)
- `U0123ABC456` - User ID (auto-opens DM, then posts)

**Implementation**:
- Added `authed_user_id` capture in Slack OAuth callback
- Added "self" resolution in `_send_slack_message`
- Added auto-open DM logic for U... prefixed targets
- Added `im:write` scope to Slack OAuth for DM channel access
- Added platform registry (`integrations/platform_registry.py`) for validation
- Added health check endpoint (`/integrations/{provider}/health`)
- Updated TP documentation to clarify valid formats

### Gmail
- No changes (uses direct API, not MCP)

### Notion

**New Features**:
- `platform.send` support for adding comments to Notion pages
- Automatic transformation of simple params to MCP-expected structure
- Page ID validation (UUID with/without dashes, full URLs)

**Breaking Changes**:
- `notion-create-comment` requires specific structure: `{parent: {page_id: ...}, rich_text: [...]}`

**Known Issues**:
- Page must be explicitly shared with the Notion integration
- Comments require commenting permission on the page

**Valid Formats**:
- `a1b2c3d4-e5f6-7890-abcd-ef1234567890` - UUID with dashes
- `a1b2c3d4e5f67890abcdef1234567890` - UUID without dashes
- `https://notion.so/workspace/Page-abc123` - Full Notion URL
- `https://myspace.notion.site/Page-abc123` - Notion Sites URL

**Implementation**:
- Updated `_send_notion_content` to use correct MCP structure
- Added page_id validation in platform_registry.py
- Added `notion-search` as resolution tool for finding pages
- Added `notion-get-comments` capability for reading comments

**Tested**: Successfully added comment to Notion page via MCP (2026-02-11)

---

## Template for Future Entries

```markdown
## YYYY-MM-DD

### Platform Name

**Breaking Changes**:
- Description of breaking change

**New Features**:
- Description of new capability

**Known Issues**:
- Issue description and impact

**Workarounds**:
- How to work around the issue

**Implementation**:
- Code changes made
```
