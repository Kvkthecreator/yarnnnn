# Integration Changelog

Track changes to platform integrations, MCP servers, and discovered quirks.

---

## 2026-02-11

### Slack

**New Features**:
- **Auto-open DM for user IDs**: `platform.send` with `channel: "U0123ABC456"` now automatically opens a DM channel and sends the message there
- Platform registry for structured validation and param mapping

**Breaking Changes**:
- `platform.send` action now requires valid channel format
- MCP server (`@modelcontextprotocol/server-slack`) expects `channel_id` parameter, not `channel`

**Known Issues**:
- `@username` / `@me` / `@self` formats are NOT valid for Slack API - use user ID (U...) instead

**Valid Formats**:
- `C0123ABC456` - Channel ID (posts to channel)
- `#general` - Channel name (posts to channel)
- `U0123ABC456` - User ID (auto-opens DM, then posts)

**Implementation**:
- Added auto-open DM logic in `_send_slack_message` for U... prefixed targets
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
