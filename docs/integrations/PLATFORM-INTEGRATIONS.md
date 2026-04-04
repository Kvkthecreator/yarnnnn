# Platform Integrations Architecture

> How YARNNN connects to external work platforms today. Updated 2026-04-03 after ADR-153 and ADR-156 cleanup.

## First Principle

Platforms are access surfaces, not a mirrored knowledge base.

YARNNN keeps backend-managed platform connections for:
- OAuth credentials and connection status
- source discovery and user selection
- direct platform tool access
- task-first recurring observation workflows

YARNNN does **not** maintain a generic synced platform cache anymore. The old
`platform_content` table, sync worker, sync scheduler, and refresh primitive are
sunset.

## Current Platform Set

| Platform | Primary role | Typical value |
|---|---|---|
| Slack | Communication surface | Decisions, action items, team activity, momentum |
| Notion | Document/reference surface | Specs, plans, knowledge pages, change tracking |
| GitHub | Work artifact surface | Issues, pull requests, repository activity |

## Active Runtime Pieces

### Stays active

| Component | Purpose |
|---|---|
| `platform_connections` | OAuth tokens, platform metadata, landscape snapshot, selected sources |
| `sync_registry` | Resource coverage / last-observed bookkeeping still used by parts of the product |
| `landscape.py` | Provider discovery and smart source defaults |
| Direct API clients | Slack, Notion, GitHub REST access |
| `platform_tools.py` | TP-facing live platform tools |
| Integration routes | Connect, disconnect, inspect landscape, choose sources |

### Removed

| Removed component | Status |
|---|---|
| `platform_content` | Sunset |
| `platform_worker.py` | Deleted |
| `platform_sync_scheduler.py` | Deleted |
| `RefreshPlatformContent` | Deleted |
| Generic sync-driven downstream reads | Removed |

## Access Model

There are two supported access patterns in the current codebase:

1. **Direct platform tools in TP**
   - Connected integrations expose `platform_*` tools.
   - These are live reads and scoped write/delivery actions where supported.

2. **Task-first recurring observation (ADR-158)**
   - Platform bots own temporal context directories: Slack Bot → `/workspace/context/slack/`, Notion Bot → `/workspace/context/notion/`.
   - Digest task types (`slack-digest`, `notion-digest`) write per-source observations.
   - Per-source subfolders (channel/page) with `_tracker.md` for freshness.
   - These are temporal awareness for TP — not canonical context for domain stewards.
   - Cross-pollination into canonical domains is explicitly out of scope.

The important architectural shift is that a platform connection no longer implies
"keep a cached copy of this platform in YARNNN."

## Data Model

### `platform_connections`

Stores:
- encrypted credentials
- provider status
- provider metadata such as workspace/team information
- landscape snapshots
- `selected_sources`

This is the control plane for integrations.

### `sync_registry`

Still present, but no longer represents a generic sync pipeline.

Today it is used for:
- per-resource coverage state
- exclusion flags
- last-observed timestamps and error reporting
- some status/freshness surfaces that have not yet been fully renamed

It should be read as legacy bookkeeping, not as proof of a background sync
architecture.

## Source Selection

Source boundaries are user-controlled.

Landscape discovery provides available resources per platform:
- Slack channels
- Notion pages / databases
- GitHub repositories

Users then choose which sources are in scope. Smart defaults may preselect likely
relevant sources, but the selected set is stored explicitly in
`platform_connections.landscape.selected_sources`.

## Tooling Surface

### TP platform tools

Examples:
- `platform_slack_list_channels`
- `platform_slack_get_channel_history`
- `platform_notion_search`
- `platform_notion_get_page`
- `platform_github_list_repos`
- `platform_github_get_issues`

These are live platform operations, not queries against a local cache.

### Delivery / write-back

Write-back remains narrow and intentional.

Examples:
- Slack send message
- Notion comment / designated-page workflows

These are delivery affordances, not a general "edit the user's tools for them"
subsystem.

## Key Files

| Concern | File |
|---|---|
| Integration routes | `api/routes/integrations.py` |
| Slack client | `api/integrations/core/slack_client.py` |
| Notion client | `api/integrations/core/notion_client.py` |
| GitHub client | `api/integrations/core/github_client.py` |
| Token helpers | `api/integrations/core/tokens.py` |
| OAuth flows | `api/integrations/core/oauth.py` |
| Platform tools | `api/services/platform_tools.py` |
| Landscape discovery | `api/services/landscape.py` |
| Limits | `api/services/platform_limits.py` |
| Freshness / coverage helpers | `api/services/freshness.py` |

## Adding New Platforms

1. Start with the source question: is this platform actually a useful work or reference surface?
2. Add OAuth support in `oauth.py`
3. Add a direct API client in `api/integrations/core/`
4. Add landscape discovery and source scoring in `landscape.py`
5. Add integration routes and source-selection support
6. Add live TP tools only where the platform is a good conversational surface

Do **not** add a new generic sync/cache pipeline.

## Related

- [ADR-158: External Context Access — Platform Bot Ownership](../adr/ADR-158-external-context-access-authority-model.md)
- [ADR-153: Platform Content Sunset](../adr/ADR-153-platform-content-sunset.md)
- [ADR-147: GitHub Platform Integration](../adr/ADR-147-github-platform-integration.md)
- [ADR-131: Gmail & Calendar Sunset](../adr/ADR-131-gmail-calendar-sunset.md)
