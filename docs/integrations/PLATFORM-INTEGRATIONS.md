# Platform Integrations Architecture

> How YARNNN perceives the outside world. Updated 2026-03-29 per ADR-147 (GitHub).

## First Principle: Platforms Are Perception, Not Action

YARNNN is not a Slack client, not a Notion editor, not a code editor. Platforms are **how agents sense the world** — the perception layer that feeds context into the generation pipeline. The primary flow is always:

```
External platform → sync → platform_content → agent context → generated output
```

This means:
- **Read/sync is the core contract.** Every platform must write to `platform_content` via the sync pipeline.
- **Write-back is secondary and scoped.** Where write tools exist (Slack DM, Notion comment), they serve delivery — getting agent output back to the user in their existing workflow. They are not general-purpose platform manipulation.
- **TP tools are for context, not creation.** TP's platform tools help the user explore what agents can see ("show me my Slack channels", "what issues are open?"), not replace platform-native workflows.

## Connected Platforms

Three platforms, each representing a distinct knowledge domain:

| Platform | Domain | What Agents See | Primary Value |
|----------|--------|----------------|---------------|
| **Slack** | Communication | Messages, threads, reactions | Who said what, decisions made, team sentiment |
| **Notion** | Documentation | Pages, databases, structured content | Knowledge base, specs, plans, reference material |
| **GitHub** | Code & Work | Issues, pull requests, project activity | What's being built, what's blocked, what shipped |

ADR-131 (Gmail/Calendar Sunset) established the bar: platforms must **compound knowledge** — persistent, accumulating, decision-dense content. All three current platforms pass this test. GitHub issues and PRs are especially knowledge-dense: they contain decision rationale, cross-references, and evolve over time.

### Platform Classification

| Aspect | Slack | Notion | GitHub |
|--------|-------|--------|--------|
| Content type | Stream (temporal) | Document (persistent) | Hybrid (issues evolve, PRs have lifecycle) |
| Sync model | Incremental (message `ts` cursor) | Change detection (`last_edited_time`) | Incremental (`updated_at` cursor) |
| Source unit | Channel | Page / Database | Repository |
| TTL | 14 days | 90 days | 14 days |
| Token expiry | Never (bot token) | Never | Can expire (refresh supported) |
| TP read tools | list_channels, get_channel_history | search, get_page | list_repos, get_issues |
| TP write tools | send_message (DM to self) | create_comment (designated page) | None (read-only MVP) |
| Delivery export | Channel post, thread, Block Kit, DM | Child page, database item, draft | Issue creation (Phase 2) |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ PERCEPTION LAYER (only subsystem calling external APIs)             │
│                                                                     │
│ platform_sync_scheduler.py (cron, tier-gated)                       │
│   └─ platform_worker.py                                             │
│        ├─ _sync_slack()     → SlackAPIClient   → Slack Web API      │
│        ├─ _sync_notion()    → NotionAPIClient  → Notion REST API    │
│        └─ _sync_github()    → GitHubAPIClient  → GitHub REST API v3 │
│                                                                     │
│ All content → platform_content table (single source of truth).      │
│ Content starts ephemeral (retained=false, TTL set).                 │
│ ADR-112: Atomic sync lock prevents overlapping syncs.               │
│ ADR-112: Heartbeat fast-path skips full sync when nothing changed.  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ writes to
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CONTENT LAYER (platform_content — perception substrate)             │
│                                                                     │
│ Storage:   _store_content() in platform_worker.py                   │
│ Search:    search_platform_content() (pgvector semantic search)     │
│ Freshness: has_fresh_content_since() for scheduling decisions       │
│ Retention: mark_content_retained() when consumed by agent           │
│ Cleanup:   cleanup_expired_content() removes TTL-expired rows       │
└──────────┬──────────────────┬────────────────────────────────────────┘
           │                  │
           ▼                  ▼
   TP Chat (context)    Task Pipeline (generation)
   (user explores        (agents consume context
    what agents see)      to produce output)
```

### TP Tools: Context Exploration, Not Platform Action

TP's platform tools let users explore what the perception layer sees. They are **not** replacements for native platform UIs.

| Tool | Purpose | Category |
|------|---------|----------|
| `platform_slack_list_channels` | See what Slack channels are visible | Context exploration |
| `platform_slack_get_channel_history` | Read recent messages from a channel | Context exploration |
| `platform_slack_send_message` | Send DM to self (output delivery) | Delivery |
| `platform_notion_search` | Find pages in connected workspace | Context exploration |
| `platform_notion_get_page` | Read page content | Context exploration |
| `platform_notion_create_comment` | Comment on designated page (output delivery) | Delivery |
| `platform_github_list_repos` | See connected repositories | Context exploration |
| `platform_github_get_issues` | Read issues and PRs from a repo | Context exploration |

**Delivery tools** (Slack DM, Notion comment) are the exception — they exist to push agent output back to where the user already works. They are scoped to "self" destinations by default (your DM, your designated page).

## Per-Platform Specifications

### Slack

**Transport**: Direct API (`SlackAPIClient`)
**OAuth Scopes**: `chat:write`, `channels:read`, `channels:history`, `channels:join`, `groups:read`, `groups:history`, `users:read`, `im:write`
**Token**: Bot token (`xoxb-...`), never expires
**Storage**: `credentials_encrypted`

**Sync Spec**:

| Aspect | Value |
|--------|-------|
| Source unit | Channel (public + private the bot can see) |
| Content synced | Messages, threads (reply_count >= 2), reactions |
| Content types | `message`, `thread_parent`, `thread_reply` |
| Cursor | `oldest` ts per channel in `sync_registry` |
| TTL | 14 days |
| Auto-selection | Score by: work-signal name patterns, member count, purpose text (ADR-079) |

### Notion

**Transport**: Direct API (`NotionAPIClient`)
**OAuth**: Notion's built-in OAuth (no scope parameter — capabilities set on dev dashboard)
**Token**: OAuth access token, never expires
**Storage**: `credentials_encrypted`

**Why Direct API**: Notion MCP servers require internal `ntn_...` tokens, not OAuth tokens. Direct API works with our OAuth flow.

**Sync Spec**:

| Aspect | Value |
|--------|-------|
| Source unit | Page or Database |
| Content synced | Full page text (recursive block extraction), database items |
| Content types | `page`, `database_item` |
| Cursor | `last_edited_time` comparison — skip unchanged pages |
| TTL | 90 days |
| Auto-selection | Score by: databases > pages, workspace-level > nested, recent > stale (ADR-079) |

### GitHub (ADR-147)

**Transport**: Direct API (`GitHubAPIClient`)
**OAuth**: GitHub OAuth App, scopes `repo` + `read:user`
**Token**: OAuth access token, **can expire** — transparent refresh via `refresh_token_encrypted`
**Storage**: `credentials_encrypted` + `refresh_token_encrypted`

**Conceptual framing**: GitHub is a **work-artifact perception source**, not a code editing interface. YARNNN reads issues and PRs as knowledge artifacts — decisions, blockers, progress, and context — the same way it reads Slack messages or Notion pages. The value is in understanding *what work is happening*, not in manipulating code.

**What agents see from GitHub**:
- Open/closed issues with labels, assignees, and comment threads → *what's being worked on, what's blocked*
- Pull requests with state, branches, and descriptions → *what shipped, what's in review*
- Comment threads → *decision rationale, technical context*

**What agents do NOT see** (intentionally):
- Source code / diffs — too granular, already in PRs as descriptions
- CI/CD workflows — operational noise, not knowledge
- Releases — often auto-generated, low signal
- Commits — summarized in PR descriptions

**Sync Spec**:

| Aspect | Value |
|--------|-------|
| Source unit | Repository (`owner/repo`) |
| Content synced | Issues (open + recently updated) + top 5 comments; PRs (open + merged) |
| Content types | `issue`, `pull_request` |
| Cursor | `updated_at` per repo, 6-month lookback on first sync |
| TTL | 14 days (re-fetchable from API) |
| Rate limiting | 5,000 req/hr per token; back off at <100 remaining |
| Auto-selection | Score by: user-owned > forks, active > stale, open issues > empty repos (ADR-079) |
| Token refresh | Automatic on 401 — exchange refresh_token for new access_token, update DB |

**Token Refresh** (new pattern for GitHub, not needed by Slack/Notion):
```
API call → 401 response
  → Decrypt refresh_token_encrypted
    → POST github.com/login/oauth/access_token (grant_type=refresh_token)
      → Encrypt new tokens → Update platform_connections
        → Retry original request
```

## Tier Limits (ADR-100)

| Gate | Free | Pro ($19/mo) |
|------|------|-------------|
| Platform connections | All 3 | All 3 |
| Slack channels | 5 | Unlimited |
| Notion pages | 10 | Unlimited |
| GitHub repos | 3 | Unlimited |
| Sync frequency | 1x/day | Hourly |
| Monthly messages | 150 | Unlimited |
| Active tasks | 2 | 10 |
| Monthly work credits | 20 | 500 |

**Enforcement**: `api/services/platform_limits.py` — `TIER_LIMITS`, `PROVIDER_LIMIT_MAP`, source limit checks.

## Token Management

| Platform | Storage Column | Token Type | Expiry | Refresh |
|----------|---------------|------------|--------|---------|
| Slack | `credentials_encrypted` | Bot token | Never | N/A |
| Notion | `credentials_encrypted` | OAuth access token | Never | N/A |
| GitHub | `credentials_encrypted` | OAuth access token | Can expire | `refresh_token_encrypted` → auto-refresh on 401 |

## Environment Variables

```bash
# Slack (API service + schedulers decrypt from DB)
SLACK_CLIENT_ID=       # API only (OAuth initiation)
SLACK_CLIENT_SECRET=   # API only (OAuth initiation)

# Notion (schedulers need these for Notion API calls)
NOTION_CLIENT_ID=      # API + Unified Scheduler + Platform Sync
NOTION_CLIENT_SECRET=  # API + Unified Scheduler + Platform Sync

# GitHub (API only — schedulers use encrypted tokens from DB)
GITHUB_CLIENT_ID=      # API only (OAuth initiation)
GITHUB_CLIENT_SECRET=  # API only (OAuth initiation)

# Encryption (all services that decrypt tokens)
INTEGRATION_ENCRYPTION_KEY=  # API + Unified Scheduler + Platform Sync
```

## Key Files

| Concern | File |
|---------|------|
| Sync scheduler | `api/jobs/platform_sync_scheduler.py` |
| Sync worker | `api/workers/platform_worker.py` |
| Slack API client | `api/integrations/core/slack_client.py` |
| Notion API client | `api/integrations/core/notion_client.py` |
| GitHub API client | `api/integrations/core/github_client.py` |
| Token management | `api/integrations/core/tokens.py` |
| OAuth flows | `api/integrations/core/oauth.py` |
| TP platform tools | `api/services/platform_tools.py` |
| Landscape discovery | `api/services/landscape.py` |
| Tier limits | `api/services/platform_limits.py` |
| Freshness tracking | `api/services/freshness.py` |

## Adding New Platforms

1. **Start with the question**: What persistent, compounding knowledge does this platform hold? If the answer is "ephemeral data" or "operational noise," don't add it (ADR-131 lesson).
2. **OAuth**: Add provider config to `oauth.py`
3. **API Client**: Create `integrations/core/{platform}_client.py` (Direct API pattern — no MCP)
4. **Sync Worker**: Add `_sync_{platform}()` to `platform_worker.py` with cursor strategy
5. **Landscape**: Add discovery + scoring to `landscape.py`
6. **Limits**: Add source limit field to `PlatformLimits` + `PROVIDER_LIMIT_MAP`
7. **TP Tools** (read-only): Add context exploration tools to `platform_tools.py`
8. **Delivery** (optional, later): Add exporter for write-back if the platform is a natural delivery destination

All read operations by TP and agents automatically work via `platform_content` — no per-platform integration needed for downstream consumers.

## Related Documentation

- [ADR-147: GitHub Platform Integration](../adr/ADR-147-github-platform-integration.md)
- [ADR-131: Gmail & Calendar Sunset](../adr/ADR-131-gmail-calendar-sunset.md)
- [ADR-077: Platform Sync Overhaul](../adr/ADR-077-platform-sync-overhaul.md)
- [ADR-112: Sync Efficiency & Concurrency Control](../adr/ADR-112-sync-efficiency-concurrency-control.md)
- [ADR-079: Smart Auto-Selection](../adr/archive/ADR-079-smart-auto-selection-heuristic.md)
- [ADR-056: Per-Source Sync](../adr/ADR-056-per-source-sync-implementation.md)
