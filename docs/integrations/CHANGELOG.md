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
- No changes

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
