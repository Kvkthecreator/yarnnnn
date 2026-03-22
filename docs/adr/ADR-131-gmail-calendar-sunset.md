# ADR-131: Gmail & Calendar Sunset — Platform Hierarchy Realignment

**Status**: Proposed → Implementing
**Supersedes**: ADR-046 (Google Calendar Integration), ADR-029 (Email Integration Platform), ADR-055 (Gmail Label-Based Sync)
**Extends**: ADR-122 (Project Type Registry), ADR-100 (Simplified Monetization), ADR-077 (Platform Sync Overhaul)
**Date**: 2026-03-22

## Context

YARNNN's service model has evolved from "connect your tools, get context-aware chat" to "autonomous agents collaborate inside projects to produce recurring work products." Under this model, the value of a platform connection is proportional to the **unstructured knowledge** it provides for agents to reason over, summarize, and compound across cycles.

Evaluating the four current platforms against this standard:

| Platform | Content type | Agent reasoning depth | Standalone project value | Compounding moat |
|----------|-------------|----------------------|-------------------------|-----------------|
| **Slack** | Unstructured, high-volume, collaborative | High — threads, decisions, context | Strong (Slack Recap) | Deep — team knowledge accumulates |
| **Notion** | Knowledge-dense, structured docs | High — cross-references, state tracking | Strong (Notion Summary) | Deep — institutional knowledge |
| **Gmail** | Transactional, personal, ephemeral | Medium — action-oriented, not knowledge-oriented | Weak — competes with Gmail's own AI | Thin — email is ephemeral by nature |
| **Calendar** | Structured metadata (time, attendees, title) | Low — no content to reason over | None — acknowledged in docs as "context enrichment only" | None — switching cost is zero |

Gmail and Calendar are not core to YARNNN's value proposition. Maintaining them creates:
- **Engineering burden**: Google OAuth complexity (shared connection model, scope management, token refresh), two separate sync pipelines, calendar live-query tools, Gmail-specific exporters
- **Product confusion**: Four "equal" platform cards in onboarding dilute the message. Calendar has no standalone project type. Gmail digest competes with commoditized inbox AI.
- **Surface area**: ~2,500 lines of Google client code, dedicated context pages, TP prompt sections, tier limit fields — all for platforms that don't compound

## Decision

**Full sunset of Gmail and Calendar integrations.** Not deprecation, not repositioning — deletion.

YARNNN's platform story becomes: **Slack and Notion** — where your team's knowledge lives. Two platforms, deep integration, clear value.

### What gets deleted

**Backend:**
1. `api/integrations/core/google_client.py` — entire file (Gmail + Calendar API client)
2. `api/workers/platform_worker.py` — `_sync_gmail()` and `_sync_calendar()` functions
3. `api/services/landscape.py` — Google calendar/Gmail discovery, `fetch_google_calendars()`, Gmail label discovery
4. `api/integrations/core/oauth.py` — `"gmail"` and `"google"` OAuth configs, Google-specific token exchange, capability detection
5. `api/routes/integrations.py` — Google calendar routes (`/google/calendars`, `/google/events`, `/google/designated`), Gmail import route
6. `api/services/project_registry.py` — `gmail_digest` project type
7. `api/services/onboarding_bootstrap.py` — Gmail bootstrap path
8. `api/services/platform_limits.py` — `gmail_labels` and `calendars` limit fields
9. `api/integrations/platform_registry.py` — Gmail platform entry and tools
10. `api/integrations/exporters/gmail.py` — Gmail exporter
11. `api/agents/tp_prompts/platforms.py` — Gmail/Calendar operation guides
12. `api/agents/tp_prompts/tools.py` — Gmail/Calendar tool definitions
13. `api/jobs/platform_sync_scheduler.py` — `"gmail"` from PROVIDERS list
14. `api/mcp_server/` — Gmail/Calendar references in tool docs

**Frontend:**
1. `web/app/(authenticated)/context/gmail/page.tsx` — entire page
2. `web/app/(authenticated)/context/calendar/page.tsx` — entire page
3. `web/components/calendar/CalendarView.tsx` — entire component
4. `web/types/index.ts` — remove `"gmail" | "calendar"` from provider unions, remove `gmail_labels` and `calendars` limit fields
5. `web/lib/api/client.ts` — Google calendar/designated methods, Gmail sync trigger
6. `web/components/ui/PlatformIcons.tsx` — `GmailIcon`, `GoogleCalendarIcon`
7. `web/components/ui/PlatformCard.tsx` — Gmail/Calendar card configs
8. `web/components/context/` — Gmail/Calendar-specific rendering
9. Dashboard, settings — remove Gmail/Calendar connection cards

**Documentation:**
1. Archive ADR-046, ADR-029, ADR-055 (already in `docs/adr/archive/`)
2. Update all active ADRs that reference Gmail/Calendar as current platforms
3. Update Gitbook docs — integrations overview, quickstart, FAQ
4. Update CLAUDE.md — remove Google env vars from critical lists, update tier limits, update platform count

**Infrastructure:**
1. Remove `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from all Render services
2. Database migration: clean up `platform_connections` where platform in ('gmail', 'google', 'calendar'), remove Gmail/Calendar `platform_content`, remove `gmail_labels`/`calendars` from tier logic

### What stays

- **Supabase/Postgres schema**: `platform_connections`, `platform_content` tables unchanged structurally. Gmail/Calendar rows become orphaned and can be cleaned up in migration.
- **Sync infrastructure**: `platform_worker.py`, `platform_sync_scheduler.py` remain for Slack and Notion — only Google-specific code removed.
- **OAuth framework**: `oauth.py` keeps Slack and Notion configs. Google OAuth config deleted entirely.

### Resolved Decisions

**R1: Why full deletion, not deprecation?**
YARNNN's discipline (ADR-103, CLAUDE.md) is singular implementation — no legacy shims, no dual approaches. A deprecated-but-present integration creates confusion in code, docs, and product. If the model says it's not core, remove it.

**R2: What about existing users with Gmail/Calendar connections?**
Pre-revenue, test data only. Migration deletes Gmail/Calendar `platform_connections` and associated `platform_content`. No user notification needed.

**R3: What about cross-platform synthesis value?**
The thesis was that Gmail + Slack + Notion together > sum of parts. In practice, Slack + Notion alone provide the collaborative knowledge substrate. Gmail adds transactional signal that doesn't compound. Calendar adds metadata. Neither is load-bearing for the synthesis thesis.

**R4: Google OAuth env vars — remove from Render?**
Yes. After code deletion and migration, `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` serve no purpose. Remove from all 3 services (API, Unified Scheduler, Platform Sync).

**R5: Total platforms count?**
Changes from 4 to 2. `total_platforms` in tier limits updated. Marketing, invest page, docs updated.

## Implementation Phases

### Phase 1: Backend core deletion
- Delete `google_client.py`
- Remove `_sync_gmail()` and `_sync_calendar()` from `platform_worker.py`
- Remove Google from `landscape.py`
- Remove Google OAuth configs from `oauth.py`
- Remove `"gmail"` from `PROVIDERS` in `platform_sync_scheduler.py`

### Phase 2: Routes, registry, limits
- Remove Google routes from `integrations.py`
- Delete `gmail_digest` from `PROJECT_TYPE_REGISTRY`
- Remove Gmail from `onboarding_bootstrap.py`
- Remove `gmail_labels`/`calendars` from `PlatformLimits`, `TIER_LIMITS`, `PROVIDER_LIMIT_MAP`
- Delete `gmail.py` exporter
- Remove Gmail from `platform_registry.py`

### Phase 3: TP prompts, primitives, MCP
- Remove Gmail/Calendar sections from `tp_prompts/platforms.py` and `tp_prompts/tools.py`
- Remove Gmail/Calendar from MCP tool docs
- Update prompt CHANGELOG

### Phase 4: Frontend deletion
- Delete context pages (`gmail/page.tsx`, `calendar/page.tsx`)
- Delete `CalendarView.tsx`
- Update type unions
- Update API client
- Remove platform icons, cards, configs
- Update dashboard, settings, onboarding UI

### Phase 5: Documentation
- Update Gitbook (integrations, quickstart, FAQ, plans)
- Update active ADRs (ADR-100, ADR-077, ADR-122)
- Update CLAUDE.md

### Phase 6: Infrastructure
- Database migration: soft-delete Gmail/Calendar platform_connections, clean platform_content
- Remove `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` from Render services
- Update `render.yaml`

## Consequences

**Positive:**
- Cleaner product narrative — "Slack and Notion" is a sharper wedge than "four platforms"
- ~3,000+ lines of backend code deleted, ~500+ lines of frontend deleted
- Reduced OAuth complexity (no more shared Google connection model)
- Two fewer sync pipelines to maintain
- Onboarding becomes simpler and more focused
- No more explaining why Calendar doesn't have a project type

**Negative:**
- Lose Gmail as a delivery destination (email delivery via SMTP/SendGrid unaffected — that's separate from Gmail integration)
- Lose calendar context enrichment for meeting prep
- Narrower platform story for investors (mitigated: depth > breadth at pre-seed)

**Neutral:**
- Can re-add Google integrations later if market demands it — the sync infrastructure is platform-agnostic
- Gmail/Calendar ADRs already archived; design knowledge preserved
