# Context Pipeline Architecture

How platform data flows from OAuth connection through to the TP system prompt and agent execution.

> **Last updated**: 2026-02-27 (consistency sweep — sync frequency fix, stale gaps removed)

---

## Conceptual Model: Four Layers

Yarnnn operates on four distinct layers. The terminology is intentional and should be used consistently across code, docs, and conversation.

```
┌─────────────────────────────────────────────────────────────┐
│  MEMORY  (user_memory)                                      │
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
         Written by: agent pipeline, platform sync,
                     memory service

┌─────────────────────────────────────────────────────────────┐
│  CONTEXT  (platform_content) — ADR-072                       │
│  Unified content layer with retention-based accumulation     │
│  Versioned · Semantically indexed · Provenance-tracked      │
└─────────────────────────────────────────────────────────────┘
         Written by: platform sync (ephemeral content)
         Marked retained by: agent execution, TP sessions

┌─────────────────────────────────────────────────────────────┐
│  WORK  (agents + agent_runs)                 │
│  What TP produces — structured, versioned, exported         │
│  source_snapshots includes platform_content_ids             │
└─────────────────────────────────────────────────────────────┘
         Written by: TP in execution mode (headless)
```

### Reference models

| | Claude Code | Clawdbot | Yarnnn |
|---|---|---|---|
| **Memory** | CLAUDE.md | SOUL.md / USER.md | `user_memory` |
| **Activity** | Git commit log | Script execution log | `activity_log` |
| **Context** | Source files (read on demand) | Local filesystem | `platform_content` |
| **Work** | Build output | Script output | `agent_runs` |
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
    └── Marked significant by agent execution or TP sessions
```

### Two writers

**Platform Sync** (`platform_worker.py`):
- Runs continuously on tier-appropriate frequency
- Writes with `retained=false`, `expires_at=NOW()+TTL`
- Knows nothing about significance — just syncs

### Retention marking

When content is consumed by a downstream system, it's marked retained:

| Consumer | When | Sets |
|---|---|---|
| Agent execution | After synthesis | `retained=true`, `retained_reason='agent_execution'`, `retained_ref=version_id` |
| TP session | After semantic search hit | `retained=true`, `retained_reason='tp_session'`, `retained_ref=session_id` |

### The accumulation moat

Content that proves significant accumulates indefinitely. Over time, `platform_content` contains:
- Recent ephemeral content (TTL-bounded, most expires unused)
- Accumulated significant content (never expires, the compounding moat)

This is how YARNNN builds intelligence over time. A user with 6 months of agent history has a rich archive of content that mattered.

---

## Memory Layer: user_memory

**Table**: `user_memory`
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
- User Memory Service (`api/services/memory.py`) via nightly cron (ADR-064, ADR-087 Phase 2):
  - `process_conversation()` — nightly cron (midnight UTC), processes prior day's sessions in batch

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

### Active agents
{title, destination, sources, schedule — max 5}

### Connected platforms
{name, status, last_synced, freshness}
```

---

## Sync Frequency (ADR-053)

| Tier | Frequency | Min interval | Schedule |
|---|---|---|---|
| Free | 2x/day | 6 hours | 8am + 6pm user timezone |
| Starter | 4x/day | 4 hours | Every 6 hours |
| Pro | Hourly | 45 minutes | Top of each hour |

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
| yarnnn | Always retained (ADR-102) |

> **ADR-102**: Agent outputs are written to `platform_content` with `platform="yarnnn"` after successful delivery. These are always retained (`retained=true`, `retained_reason="yarnnn_output"`) — generated artifacts don't expire. This closes the accumulation loop: agent outputs become searchable context for TP and other agents.

---

## Agent Execution (ADR-072)

> **Note**: Agent execution now uses TP in headless mode with unified primitives. The previous parallel fetch pipeline is deleted.

When a agent runs (scheduled, event-triggered, or manual):

1. `unified_scheduler.py` fetches agent configuration
2. TP invoked in **execution mode** (headless, no streaming, no clarification)
3. Strategy gathers content from `platform_content` filtered by agent sources
4. `build_type_prompt()` assembles type-specific user message with `agent_instructions` as priority lens (ADR-104: dual injection)
5. Headless system prompt includes instructions as behavioral constraints + user memories + learned preferences
6. LLM synthesis produces output
7. `agent_version` created with `platform_content_ids` in `source_snapshots`
8. Source content marked `retained=true`, `retained_reason='agent_execution'`
9. Content delivered to configured destination(s)
10. `activity_log` event written

**Why unified execution?** Improvements to TP primitives automatically improve agent quality. One codebase, not two.

---

## Work Layer: Agents

**Tables**: `agents`, `agent_runs`

The output of TP's execution pipeline. Every generation run produces a new `agent_version`. Versions are reviewed by the user and exported to the platform destination (Slack channel, Gmail draft, Notion page, etc.).

Agents carry their own source configuration — which channels, labels, pages, or calendars to read from. Source references live on the agent, not on any domain or grouping abstraction (knowledge_domains was removed in ADR-059 for this reason).

---

## Live Platform Tools (Conversational)

TP has platform tools for direct, action-oriented platform operations during conversation. These are distinct from both the sync cache and agent execution:

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

At the start of every TP session, the working memory block is assembled from **Memory only** (user_memory + active agents + platform connection status). Raw platform content is **not** pre-injected.

TP accesses platform content during a session in three steps (ADR-085):

1. **Primary: `Search(scope="platform_content")`** — hits `platform_content` table (ILIKE text search). When used, TP **must disclose the cache age** to the user.
2. **If stale/empty: `RefreshPlatformContent(platform="...")`** — synchronous cache refresh (~10-30s). Calls the same worker pipeline as the scheduler, awaited within the chat turn. 30-minute staleness threshold prevents redundant syncs.
3. **Re-query: `Search(scope="platform_content")`** — now has fresh data. Answer the user.

Live platform tools (`platform_slack_*`, `platform_gmail_*`, etc.) are used for write operations, CRUD, and interactive lookups — not as the primary read path.

---

## Document Uploads

Uploaded documents are processed into `filesystem_chunks` (chunked, embedded, indexed). They are searchable via `Search(scope="document")`. Documents do **not** automatically extract into Memory (`user_memory`).

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

## Known Gaps

1. **Document-to-Memory extraction removed** — Documents populate filesystem_chunks only. Intentional for now; "promote to Memory" is a deferred feature.
