# Integration Changelog

Track changes to platform integrations, MCP servers, and discovered quirks.

---

## 2026-02-23

### All Platforms — Sync Pipeline Fixes

**Fixes**:
- **Worker env var parity**: `INTEGRATION_ENCRYPTION_KEY`, Google/Notion OAuth creds, and `MCP_GATEWAY_URL` were missing from Worker and Scheduler Render services. Worker silently reported `success=True` while syncing 0 items because it couldn't decrypt OAuth tokens.
- **Worker failure reporting**: Worker now checks for error key + 0 items before reporting success. Only updates `last_synced_at` on actual success.
- **Scheduler heartbeat FK**: Was writing to `activity_log` with dummy UUID `00000000-...` → FK violation. Now writes per-user heartbeats for users with active `platform_connections`.
- **getSources field name mismatch**: Backend returned `{ selected_sources, provider, count }` but frontend expected `{ sources, limit, can_add_more }`. Context page showed "0 of 1 selected" despite 2 sources being synced.

### Context Page UX

**Changes**:
- `CoverageBadge`: Shows "Synced 2h ago" with relative time instead of static "Synced"/"Not synced"
- `SyncStatusBanner`: Shows last sync time in green state ("Syncing N sources · 2x daily · Last synced X ago")
- Count text: "2 selected · 1 included on free plan" for over-limit instead of confusing "2 of 1 selected"

### System Page

**Changes**:
- Signal Processing now writes `activity_log` even on early return (no signals found) so system page shows "last run" instead of "Never Run"
- Platform Sync aggregates all `platform_synced` events in 30-min window instead of showing only the last platform

---

## 2026-02-12

### All Platforms - ADR-048: Direct MCP Access

**Breaking Changes**:
- **`platform.send` removed** from Execute primitive
- **`platform.search` removed** from Execute primitive
- TP now uses MCP tools directly (like Claude Code uses tools)

**Migration**:
| Old Pattern | New Pattern |
|-------------|-------------|
| `Execute(action="platform.send", target="platform:slack", params={...})` | `mcp__claude_ai_Slack__slack_send_message(channel_id=..., text=...)` |
| `Execute(action="platform.search", target="platform:notion", params={query: "..."})` | `mcp__claude_ai_Notion__notion-search(query="...")` |

**Architecture**:
- TP has 7 primitives: Read, Write, Edit, Search, List, Execute, Clarify
- Execute is for YARNNN orchestration only (deliverable.generate, platform.sync, etc.)
- MCP tools exposed directly to TP as first-class tools
- `Search` primitive searches synced content (ephemeral_context)
- MCP tools search/interact with platforms directly

**Files Changed**:
- `api/services/primitives/execute.py` - Removed ~300 lines of wrapper handlers
- `api/services/primitives/refs.py` - Removed live search functions
- `api/agents/thinking_partner.py` - Updated system prompt for direct MCP usage
- `api/integrations/platform_registry.py` - Updated to reference MCP tools

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
