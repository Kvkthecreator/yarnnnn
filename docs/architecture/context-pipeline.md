# Context Pipeline Architecture

How platform data flows from OAuth connection through to the TP system prompt and deliverable execution.

> **Last updated**: 2026-02-25 (ADR-077 — platform sync overhaul, ADR-076 — direct API clients)

---

## Conceptual Model: Four Layers

Yarnnn operates on four distinct layers. The terminology is intentional and should be used consistently across code, docs, and conversation.

```
┌─────────────────────────────────────────────────────────────┐
│  MEMORY  (user_context)                                      │
│  What TP knows about you — stable, explicit, auditable      │
│  Injected into every TP session (working memory block)      │
│  source_ref tracks provenance of each entry                  │
└─────────────────────────────────────────────────────────────┘
         Written by: user directly (Context page); Memory Service nightly cron

┌─────────────────────────────────────────────────────────────┐
│  ACTIVITY  (activity_log)                                    │
│  What YARNNN has done — system provenance, append-only      │
│  Recent events injected into every TP session               │
└─────────────────────────────────────────────────────────────┘
         Written by: deliverable pipeline, platform sync,
                     signal processing, memory service

┌─────────────────────────────────────────────────────────────┐
│  CONTEXT  (platform_content) — ADR-072                       │
│  Unified content layer with retention-based accumulation     │
│  Versioned · Semantically indexed · Provenance-tracked      │
└─────────────────────────────────────────────────────────────┘
         Written by: platform sync (ephemeral content)
                     signal processing (retained content)
         Marked retained by: deliverable execution, TP sessions

┌─────────────────────────────────────────────────────────────┐
│  WORK  (deliverables + deliverable_versions)                 │
│  What TP produces — structured, versioned, exported         │
│  source_snapshots includes platform_content_ids             │
└─────────────────────────────────────────────────────────────┘
         Written by: TP in execution mode (headless)
```

### Reference models

| | Claude Code | Clawdbot | Yarnnn |
|---|---|---|---|
| **Memory** | CLAUDE.md | SOUL.md / USER.md | `user_context` |
| **Activity** | Git commit log | Script execution log | `activity_log` |
| **Context** | Source files (read on demand) | Local filesystem | `platform_content` |
| **Work** | Build output | Script output | `deliverable_versions` |
| **Execution** | Shell / Bash | Skills | TP (headless mode) |

---

## Unified Content Layer (ADR-072)

> **Note**: This section replaces the previous "Two Independent Data Paths" section. ADR-072 unifies content access.

### The `platform_content` table

All platform content flows through a single table with retention semantics:

```
platform_content
├── Ephemeral content (retained=false, expires_at set)
│   └── Written by platform sync, expires after TTL
│
└── Retained content (retained=true, expires_at NULL)
    └── Marked significant by deliverable execution, signal processing, or TP sessions
```

### Two writers

**Platform Sync** (`platform_worker.py`):
- Runs continuously on tier-appropriate frequency
- Writes with `retained=false`, `expires_at=NOW()+TTL`
- Knows nothing about significance — just syncs

**Signal Processing** (`signal_extraction.py`):
- Reads live APIs for time-sensitive signals
- Writes significant content with `retained=true`
- Sets `retained_reason='signal_processing'`

### Retention marking

When content is consumed by a downstream system, it's marked retained:

| Consumer | When | Sets |
|---|---|---|
| Deliverable execution | After synthesis | `retained=true`, `retained_reason='deliverable_execution'`, `retained_ref=version_id` |
| TP session | After semantic search hit | `retained=true`, `retained_reason='tp_session'`, `retained_ref=session_id` |
| Signal processing | When identified as significant | `retained=true`, `retained_reason='signal_processing'` |

### The accumulation moat

Content that proves significant accumulates indefinitely. Over time, `platform_content` contains:
- Recent ephemeral content (TTL-bounded, most expires unused)
- Accumulated significant content (never expires, the compounding moat)

This is how YARNNN builds intelligence over time. A user with 6 months of deliverable history has a rich archive of content that mattered.

---

## Memory Layer: user_context

**Table**: `user_context`
**ADR**: ADR-059

A single flat key-value store for everything TP knows *about the user*. Replaces the prior four-table inference pipeline (`knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`).

| Key pattern | Meaning | Example |
|---|---|---|
| `name`, `role`, `company`, `timezone` | Profile fields | `role = "Head of Growth"` |
| `tone_{platform}`, `verbosity_{platform}` | Style preferences | `tone_slack = "casual"` |
| `fact:...` | Noted facts | `fact:prefers bullet points` |
| `instruction:...` | Standing instructions | `instruction:always include TL;DR` |
| `preference:...` | Stated preferences | `preference:no jargon in reports` |

**Written by**:
- User directly via the Context page (Profile, Styles, Entries sections)
- Backend Memory Service via nightly cron and pipeline hooks (ADR-064):
  - `process_conversation()` — nightly cron (midnight UTC), processes prior day's sessions in batch
  - `process_feedback()` — triggered when user approves an edited deliverable version
  - `process_patterns()` — daily background job (activity_log analysis)

**Never written by**: TP directly during conversation. The explicit `create_memory` / `update_memory` tools were removed in ADR-064. Conversation memory extraction is a **batch nightly job**, not a real-time session-end hook. A preference stated today is available in working memory the next morning.

**Read by**: `working_memory.py → build_working_memory()` — assembled into the system prompt block injected at the start of every TP session (~2,000 token budget).

### Working memory format

```
### About you
{name, role, company, timezone}

### Your preferences
{tone_*, verbosity_*, preference:*}

### What you've told me
{fact:*, instruction:*}

### Active deliverables
{title, destination, sources, schedule — max 5}

### Connected platforms
{name, status, last_synced, freshness}
```

---

## Sync Frequency (ADR-053)

| Tier | Frequency | Min interval |
|---|---|---|
| Free | 1x/day | 24 hours |
| Starter | 4x/day | 4 hours |
| Pro | Hourly | 45 minutes |

Triggered by `platform_sync_scheduler.py` → `platform_worker.py` every 5 minutes.

### What each platform extracts (ADR-077)

All platforms use Direct API clients from `api/integrations/core/` — no MCP, no gateway (ADR-076).

| Platform | Method | What is stored |
|---|---|---|
| Slack | `SlackAPIClient` direct REST | Paginated history (1000 initial/500 incremental), thread replies, user-resolved authors. System messages filtered. |
| Gmail | `GoogleAPIClient` direct REST | Paginated messages (200/label), concurrent fetch, 30-day initial window |
| Notion | `NotionAPIClient` direct REST | Recursive block content (depth=3, 500 blocks), database row querying |
| Calendar | `GoogleAPIClient` direct REST | Events -7d to +14d, paginated (200 max) |

### Source limits (ADR-077)

| Platform | Free | Starter | Pro |
|---|---|---|---|
| Slack channels | 5 | 15 | ∞ |
| Gmail labels | 5 | 10 | ∞ |
| Notion pages | 10 | 25 | ∞ |
| Calendars | ∞ | ∞ | ∞ |

### TTL by platform (for unreferenced content, ADR-077)

| Platform | Expiry |
|---|---|
| Slack | 14 days |
| Gmail | 30 days |
| Notion | 90 days |
| Calendar | 2 days |

---

## Deliverable Execution (ADR-072)

> **Note**: Deliverable execution now uses TP in headless mode with unified primitives. The previous parallel fetch pipeline is deleted.

When a deliverable runs (scheduled, event-triggered, or manual):

1. `unified_scheduler.py` fetches deliverable configuration
2. TP invoked in **execution mode** (headless, no streaming, no clarification)
3. TP uses primitives (`Search`, `FetchPlatformContent`) to gather content from `platform_content`
4. LLM synthesis produces output
5. `deliverable_version` created with `platform_content_ids` in `source_snapshots`
6. Source content marked `retained=true`, `retained_reason='deliverable_execution'`
7. Content delivered to configured destination(s)
8. `activity_log` event written

**Why unified execution?** Improvements to TP primitives automatically improve deliverable quality. One codebase, not two.

---

## Work Layer: Deliverables

**Tables**: `deliverables`, `deliverable_versions`

The output of TP's execution pipeline. Every generation run produces a new `deliverable_version`. Versions are reviewed by the user and exported to the platform destination (Slack channel, Gmail draft, Notion page, etc.).

Deliverables carry their own source configuration — which channels, labels, pages, or calendars to read from. Source references live on the deliverable, not on any domain or grouping abstraction (knowledge_domains was removed in ADR-059 for this reason).

---

## Live Platform Tools (Conversational)

TP has platform tools for direct, action-oriented platform operations during conversation. These are distinct from both the sync cache and deliverable execution:

| Tool | Platform | Method |
|---|---|---|
| `platform_slack_send_message` | Slack | SlackAPIClient direct REST |
| `platform_slack_list_channels` | Slack | SlackAPIClient direct REST |
| `platform_notion_search` | Notion | Direct NotionAPIClient |
| `platform_notion_create_comment` | Notion | Direct NotionAPIClient |
| `platform_gmail_search` | Gmail | GoogleAPIClient |
| `platform_gmail_create_draft` | Gmail | GoogleAPIClient |
| `platform_calendar_list_events` | Calendar | GoogleAPIClient |
| `platform_calendar_create_event` | Calendar | GoogleAPIClient |

These are action calls TP makes on behalf of the user during a chat turn. They are **not** how context flows into TP — that is the working memory block and Search.

---

## What TP Has at Session Start

At the start of every TP session, the working memory block is assembled from **Memory only** (user_context + active deliverables + platform connection status). Raw platform content is **not** pre-injected.

TP accesses platform content during a session in two ways, with a defined priority order (ADR-065):

1. **Primary: Live platform tools** — `platform_gmail_search`, `platform_slack_list_channels`, `platform_notion_search`, etc. Direct API calls. Always current. Used first.
2. **Fallback: `Search(scope="platform_content")`** — hits `platform_content` table (ILIKE text search). Used when live tools can't serve the query (cross-platform aggregation, live tool unavailable). When used, TP **must disclose the cache age** to the user.

**If the cache is needed but empty**: TP triggers `Execute(action="platform.sync")`, informs the user ("takes ~30–60 seconds, ask again once done"), then stops. There is no in-conversation polling tool available — sync is async. The user re-engages after the job completes; the cache will be populated by then.

---

## Document Uploads

Uploaded documents are processed into `filesystem_chunks` (chunked, embedded, indexed). They are searchable via `Search(scope="document")`. Documents do **not** automatically extract into Memory (`user_context`).

**Intentional oversight**: there is a legitimate future use case for "promote document to Memory" — where a user wants a style guide, brief, or set of standing instructions to always be present in working memory rather than just searchable. This should be implemented as an explicit user action, not automatic extraction. It is deferred pending architectural hardening.

---

## Connection Mechanisms (ADR-076)

All platforms use Direct API clients — no MCP gateway, no subprocess management:

| Client | Location | Used for |
|---|---|---|
| **SlackAPIClient** | `api/integrations/core/slack_client.py` | Slack sync, landscape discovery, TP live tools |
| **NotionAPIClient** | `api/integrations/core/notion_client.py` | Notion sync, landscape discovery, TP live tools |
| **GoogleAPIClient** | `api/integrations/core/google_client.py` | Gmail/Calendar sync, landscape discovery, TP live tools |

---

## Known Gaps (as of 2026-02-20)

1. **Document-to-Memory extraction removed** — Documents populate filesystem_chunks only. Intentional for now; "promote to Memory" is a deferred feature.

2. **Unified content layer (ADR-072)** — `platform_content` is now the single content table. The previous `filesystem_items` table was dropped in migration 077. All content access goes through unified primitives.
