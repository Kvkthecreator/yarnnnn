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

## Memory Layer

**Store**: `workspace_files` under `/memory/` (ADR-108, migrating from `user_memory` table)
**ADR**: ADR-059 (original), ADR-108 (filesystem migration)

Everything TP knows *about the user* — identity, preferences, standing instructions. Three files:

| File | Contains | Primary writer |
|---|---|---|
| `MEMORY.md` | Name, role, company, timezone, bio | User directly |
| `preferences.md` | Tone, verbosity, format preferences (per-platform) | System (extraction), user (overrides) |
| `notes.md` | Standing instructions, observed facts | Both (extraction appends, user edits) |

> **ADR-108 (proposed):** Migrates from `user_memory` key-value table (ADR-059) to `/memory/` filesystem in `workspace_files`. Fixes duplication, enables document-level coherence, unifies storage with `/agents/` and `/knowledge/`. See [ADR-108](../adr/ADR-108-user-memory-filesystem-migration.md).

**Written by**:
- User directly via Memory page (file editing)
- User Memory Service (`api/services/memory.py`) via nightly cron (ADR-064):
  - `process_conversation()` — reads existing files, merges new observations, writes back deduplicated content

**Never written by**: TP directly during conversation. Conversation memory extraction is a **batch nightly job**, not a real-time session-end hook. A preference stated today is available in working memory the next morning.

**Read by**: `working_memory.py → build_working_memory()` — reads `/memory/` files, concatenates into the system prompt block injected at the start of every TP session (~2,000 token budget).

### Working memory format

```
## Working Memory

### About you                    ← from /memory/MEMORY.md
{name, role, company, timezone}

### Preferences                  ← from /memory/preferences.md
{tone, verbosity, format prefs}

### Notes                        ← from /memory/notes.md
{standing instructions, facts}

### Active agents                ← from agents table
{title, destination, schedule — max 5}

### Connected platforms           ← from platform_connections + sync_registry
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
### Four Storage Domains (ADR-106 + ADR-107 + ADR-108)

The platform distinguishes four storage domains with distinct lifecycle and access models:

```
┌─────────────────────────────────────────────────────────────┐
│  USER MEMORY  (workspace_files: /memory/)                    │
│  MEMORY.md, preferences.md, notes.md  (ADR-108)             │
│  Global user identity, preferences, standing instructions    │
│  Injected into every TP session as working memory            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  EXTERNAL CONTEXT  (platform_content)                        │
│  Raw platform data — Slack, Gmail, Notion, Calendar          │
│  TTL-managed (14-90d), flat rows, sync-pipeline-written      │
│  External platforms only — no agent outputs here             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  AGENT INTELLIGENCE  (workspace_files: /agents/{slug}/)      │
│  AGENT.md, memory/*.md, thesis.md, working/, runs/           │
│  Singular source of truth — DB columns deprecated (ADR-106)  │
│  Per-agent, private, persistent                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ACCUMULATED KNOWLEDGE  (workspace_files: /knowledge/)       │
│  Agent-produced knowledge artifacts (ADR-107)                │
│  digests/, research/, analyses/, briefs/, insights/           │
│  Per-user, shared across agents, version-aware, persistent   │
└─────────────────────────────────────────────────────────────┘
```

**OS analogy:** `/memory/` = `/etc/` (system config), `/agents/` = `/home/` (per-process private state), `/knowledge/` = `/var/shared/` (shared knowledge filesystem), `platform_content` = `/dev/` (device drivers — raw external I/O).

> **ADR-107 (implemented):** Agent-produced outputs write to `/knowledge/` filesystem in `workspace_files` — organized by content class (digests, analyses, briefs, research, insights) with structured metadata. Outputs enter `/knowledge/` at delivery time. The previous `platform="yarnnn"` rows in `platform_content` (ADR-102) have been superseded and deleted. See [ADR-107](../adr/ADR-107-knowledge-filesystem-architecture.md).

> **ADR-108 (proposed):** User memory migrates from `user_memory` key-value table to `/memory/` filesystem in `workspace_files`. Three files (MEMORY.md, preferences.md, notes.md) replace ~30 key-value rows. Extraction cron shifts to read-merge-write pattern, eliminating duplication. See [ADR-108](../adr/ADR-108-user-memory-filesystem-migration.md).

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
