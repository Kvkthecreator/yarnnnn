# ADR-147: GitHub Platform Integration

**Status:** In Progress (Phase 1)
**Date:** 2026-03-29
**Supersedes:** None
**Extends:** ADR-077 (Platform Sync), ADR-079 (Smart Auto-Selection), ADR-056 (Per-Source Sync), ADR-112 (Sync Concurrency)

## Context

YARNNN serves solo founders with two perception platforms: Slack (communication) and Notion (documentation). The third pillar of a solo founder's work environment is **code** — GitHub issues, PRs, and project boards represent decision-dense, time-stamped knowledge that compounds over time.

ADR-131 (Gmail/Calendar Sunset) established the bar: platforms must compound knowledge, not just relay ephemeral data. GitHub issues and PRs meet this bar — they are persistent, accumulate context, and contain decision rationale.

Adding GitHub closes the perception triangle (communication + documentation + code) and unlocks cross-platform synthesis that is impossible with 2/3 coverage:
- "What shipped this week?" — PR summaries as changelog fodder
- "What's blocking me?" — cross-repo issue triage
- Slack discussion + GitHub issue correlation

## Decision

Add GitHub as the third content platform using the established Direct API pattern (ADR-076). GitHub OAuth App (not GitHub App) for simplicity — solo founder use case doesn't need org-level installs.

### Key Design Decisions

**D.1: OAuth App, not GitHub App**
GitHub Apps require installation flows and webhook servers. OAuth Apps are simpler: redirect → code → token. Solo founders authorize their personal account, we read their repos. GitHub Apps are a future upgrade if org support becomes needed.

**D.2: Token refresh required**
Unlike Slack (eternal bot tokens) and Notion (non-expiring), GitHub OAuth tokens expire. We implement token refresh using `refresh_token_encrypted` column (already exists on `platform_connections` — currently NULL for Slack/Notion). Refresh happens transparently on 401 responses.

**D.3: MVP sync scope — Issues + PRs only**
Sync open + recently-updated issues and PRs from selected repos. Skip: commits (too granular, captured in PR descriptions), Actions/workflows (CI noise), Releases (auto-generated), Discussions (low adoption among solo founders). Add more sources in later phases if demand emerges.

**D.4: Repos as resources (not orgs)**
Landscape discovery lists personal repos (owned + collaborator). Repos map to "sources" in the existing per-source sync model (ADR-056). Org-level access deferred.

**D.5: Read-only TP tools for MVP**
Two read tools: `platform_github_list_repos` and `platform_github_get_issues`. Write tools (create issue, create PR comment) deferred — read perception is higher leverage than write action at this stage.

**D.6: GitHub exporter for delivery**
Create issue as delivery target — agents can deliver task output as a GitHub issue (e.g., weekly engineering recap posted as issue in a meta repo).

**D.7: 6-month lookback, 14-day retention**
Issues/PRs synced from last 6 months on first sync, then incremental via `updated_at` cursor. Retention TTL: 14 days (same as Slack), since issues are re-fetchable.

### Scope per Phase

**Phase 1 (this ADR): Backend Core**
- GitHub API client (`github_client.py`)
- OAuth config + token refresh
- Sync worker (`_sync_github()`)
- Landscape discovery
- Platform limits + types
- TP read tools

**Phase 2: Delivery + Frontend**
- GitHub exporter (create issue)
- Frontend platform card + context page
- Settings integration

**Phase 3: Enrichment**
- Project board sync
- Cross-platform correlation (Slack message → GitHub issue linking)
- GitHub-aware agent types in task registry

## Architecture

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `api/integrations/core/github_client.py` | Create | REST API client with rate limiting + token refresh |
| `api/integrations/core/oauth.py` | Modify | Add GitHub OAuth config |
| `api/integrations/core/types.py` | Modify | Add GITHUB provider enum |
| `api/workers/platform_worker.py` | Modify | Add `_sync_github()` + heartbeat |
| `api/services/landscape.py` | Modify | Add `discover_github()` |
| `api/services/platform_limits.py` | Modify | Add `github_repos` limit |
| `api/services/platform_tools.py` | Modify | Add GitHub read tools |
| `api/routes/integrations.py` | Modify | Add GitHub OAuth branch |
| `api/integrations/exporters/github.py` | Create (Phase 2) | Issue creation exporter |
| `web/components/ui/PlatformIcons.tsx` | Modify (Phase 2) | GitHub icon |
| `web/components/ui/PlatformCard.tsx` | Modify (Phase 2) | GitHub config entry |

### OAuth Flow

```
User clicks "Connect GitHub"
  → GET /integrations/github/authorize
    → Redirect to github.com/login/oauth/authorize
      → User authorizes
        → GitHub redirects to /integrations/github/callback
          → Exchange code for token (+ refresh_token)
            → Store encrypted tokens in platform_connections
              → Discover landscape (list repos)
                → Auto-select repos via smart defaults
                  → Kick off first sync
                    → Redirect to /workfloor?provider=github&status=connected
```

### Token Refresh Flow (D.2)

```python
# In github_client.py — transparent refresh on 401
async def _request(self, method, url, token, refresh_token, connection_id):
    response = await self.client.request(method, url, headers={"Authorization": f"token {token}"})
    if response.status_code == 401 and refresh_token:
        new_tokens = await self._refresh_token(refresh_token)
        # Update platform_connections with new tokens
        # Retry original request
    return response
```

### Sync Content Model

GitHub content maps to `platform_content` rows:

| GitHub Entity | `resource_type` | `resource_name` | `content` |
|---------------|----------------|-----------------|-----------|
| Issue | `issue` | `owner/repo#123` | Title + body + top comments |
| Pull Request | `pull_request` | `owner/repo#456` | Title + description + review summary |

### Tier Limits

| Tier | Repos | Sync Frequency |
|------|-------|----------------|
| Free | 3 | 1x/day |
| Pro | Unlimited (-1) | Hourly |

### Environment Variables (D.2 — all services that need them)

| Env Var | Services | Purpose |
|---------|----------|---------|
| `GITHUB_CLIENT_ID` | API | OAuth client ID |
| `GITHUB_CLIENT_SECRET` | API | OAuth client secret |
| (no additional env for schedulers) | — | Schedulers use encrypted tokens from DB, same as Slack/Notion |

Note: Unlike Slack (SLACK_CLIENT_ID needed by Platform Sync cron for Slack API calls), GitHub API calls only need the user's OAuth token (stored encrypted in DB). Schedulers already have `INTEGRATION_ENCRYPTION_KEY` to decrypt. No new env vars needed on schedulers.

### Rate Limiting

GitHub API: 5,000 requests/hour per authenticated user. Mitigation:
- Incremental sync (only fetch `since` last cursor)
- Batch user resolution (GitHub includes author in issue/PR responses)
- Respect `X-RateLimit-Remaining` header, back off at <100 remaining
- Per-repo sync is independent (cursor per resource, same as Slack channels)

## Consequences

### Positive
- Closes perception triangle for solo founders (communication + docs + code)
- Enables cross-platform synthesis (e.g., "What shipped this sprint?" combining PRs + Slack discussions)
- Follows established patterns — zero new architectural concepts
- Token refresh pattern benefits future platforms with expiring tokens

### Negative
- Third platform increases sync scheduler load
- GitHub rate limits (5k/hr) are tighter than Slack/Notion — need careful batching
- Token refresh adds complexity to credential management

### Risks
- Solo founders may not have significant GitHub activity (mitigate: make it optional, not part of onboarding)
- Rate limit exhaustion for users with many repos (mitigate: enforce tier limits, incremental sync)

## Implementation Notes

Follow the Render service parity checklist from CLAUDE.md:
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` only on API service (OAuth initiation)
- No new env vars needed on Scheduler/Platform Sync (tokens in DB)
- Update `total_platforms` in TIER_LIMITS from 2 → 3 for Pro tier
