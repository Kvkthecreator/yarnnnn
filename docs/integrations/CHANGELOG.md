# Integration Changelog

Track changes to platform integrations and platform perception infrastructure.

---

## 2026-03-29

### GitHub Platform Integration (ADR-147)

**New Platform**:
- GitHub added as third content platform (Slack + Notion + GitHub)
- Framing: **perception source for work artifacts** — issues and PRs as knowledge, not code editing
- OAuth App model with `repo` + `read:user` scopes
- Token refresh support (GitHub tokens can expire, unlike Slack/Notion)

**Sync**:
- Issues: open + recently updated, with top 5 comments for context
- Pull Requests: open + merged, with branch/state metadata
- Incremental cursor via `updated_at` per repo, 6-month lookback on first sync
- Heartbeat check via GitHub events API (skip full sync when nothing changed)
- 14-day TTL (same as Slack — re-fetchable content)

**TP Tools** (read-only — context exploration, not platform action):
- `platform_github_list_repos` — see connected repos
- `platform_github_get_issues` — read issues/PRs from a repo

**Tier Limits**: Free 3 repos, Pro unlimited. `total_platforms` bumped to 3.

**Frontend**: GitHub card in Settings → Connected Platforms. Icon, types, onboarding prompt.

**Documentation**: PLATFORM-INTEGRATIONS.md rewritten with "platforms are perception" framing. Removed stale Gmail/Calendar/MCP Gateway/Starter tier references.

**Intentionally excluded**: source code, diffs, CI/CD, releases, commits — operational noise, not compounding knowledge.

**Files**: `github_client.py`, `oauth.py`, `platform_worker.py`, `landscape.py`, `platform_tools.py`, `platform_limits.py`, `types.py`, `ConnectedIntegrationsSection.tsx`, `PlatformIcons.tsx`, `PlatformCard.tsx`, `PlatformFilter.tsx`, `types/index.ts`, `client.ts`.

---

## 2026-03-05

### Context Page Sync-State Alignment

**Fixes**:
- **Slack error visibility gap**: Slack channel API failures (`not_in_channel`, permission failures, etc.) now write `sync_registry.last_error` per channel instead of silently skipping rows as "not synced."
- **False-success sync runs**: Slack worker now returns provider-level `error` when all selected channels fail, so activity/status no longer imply a healthy run with zero effective syncs.
- **Context pagination contract mismatch**: `GET /api/integrations/{provider}/context` now honors `offset` (range-based pagination) to match frontend `Load more` calls.
- **Sync status derivation**: Context page status now treats any `last_extracted_at` as synced (not just `items_extracted > 0`), avoiding "awaiting first sync" for sources that synced but had no new items.

### Context UX Clarification (All Platform Pages)

**Changes**:
- Added selected-source filtering in Context tab (default: selected sources only, with toggle to show all retained/synced platform context).
- Added scheduled post-sync refresh polling after `Run sync` to reduce stale UI after background sync trigger.
- Fixed Slack metadata key mismatch (`num_members` vs `member_count`) so channel metadata consistently renders.
- Prioritized sync errors over "awaiting first sync" in compact status so failed first sync attempts are visible immediately.
- Resource metadata now shows sync recency even when zero new items were extracted (`0 new items · synced X ago`), removing false "never synced" impressions.
- Reworked source selection information architecture for Slack/Gmail/Notion: workflow-first header, selected/synced/attention stat cards, source search, and explicit view filters (`Selected`, `Recommended`, `All`, `Issues`).
- Updated tab semantics: second tab now surfaces as **Synced content** by default; calendar keeps platform-specific wording (`Calendar setup` / `Context`).
- Tightened `Attention` logic: now includes selected-but-never-synced and selected-stale sources (not only explicit sync errors), with breakdown copy for triage.

### Sync Feedback + Cross-Platform ID Alignment

**Fixes**:
- `Run sync` UX now uses explicit progress polling (`sync-status`) instead of fixed timed reload bursts, so users see "in progress" vs "complete/error" messaging without repeated full-page refresh behavior.
- Sync metrics now scope to selected sources (synced/error/last-synced), preventing non-selected resources from distorting top-bar health state.
- Gmail landscape coverage now matches both `label:ID` and plain `ID` sync registry keys, eliminating false "not synced" labels after successful Gmail label sync.
- Notion database selections now write a database-level `sync_registry` marker after child-page sync, so selected databases no longer stay stuck at "not synced."

### Context Pages Visual Polish (All Platform Subpages)

**Changes**:
- Simplified sync header to neutral-by-default styling; warning/error colors now appear only for degraded states.
- Reduced visual/action overload in source selection: removed stat cards + progress bar, replaced with one compact summary line.
- Streamlined controls: `Save`/`Reset` surface only when there are unsaved source edits.
- Reduced filter complexity to three views (`Selected`, `All`, `Attention`) and kept search as the single discovery input.
- Quieted row-level status surfacing: neutral “Synced/Not synced” badges by default, color reserved for stale/error states.
- Unified tab switcher look across platform pages with a lower-contrast segmented control.

### Context Layout Sequencing Pass

**Changes**:
- Reordered top controls across all context pages to follow one sequence: tab selection -> sync status -> active panel.
- Reduced vertical fragmentation by tightening top-level spacing on Slack/Gmail/Notion/Calendar context pages.
- Consolidated Sources layout into one contiguous card (summary, filters, alerts, and resource list together) to reduce scattered blocks.

---

## 2026-02-28

### RefreshPlatformContent Primitive (ADR-085)

- Added `RefreshPlatformContent` primitive for synchronous platform sync in chat mode
- Replaces fire-and-forget `Execute(action="platform.sync")` — TP can now answer real-time platform questions within a single chat turn
- Uses the same `_sync_platform_async()` worker pipeline as the scheduler
- 30-minute staleness threshold prevents redundant syncs
- Supports all 4 platforms: slack, gmail, notion, calendar

### Google/Gmail/Calendar Domain Separation

- Fixed calendar sync never running from scheduler (dead code in worker)
- Unified gmail/calendar/google into single split-sync branch in `platform_worker.py`
- TP now sees calendar as connected, calendar tools load correctly
- Landscape endpoint wrapped in error handling (502 on token failure, not CORS error)
- Landscape resources filtered by requested domain (gmail vs calendar)

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
- Execute is for YARNNN orchestration only (agent.generate, platform.sync, etc.)
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
