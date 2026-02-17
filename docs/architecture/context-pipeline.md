# Context Pipeline Architecture

How platform data flows from OAuth connection → extracted content → working knowledge → TP system prompt.

---

## Overview

There are four distinct layers:

```
1. platform_connections   OAuth credentials + landscape (what sources exist)
         ↓
2. filesystem_items       Raw extracted platform content, short TTL
         ↓
3. knowledge_* tables     Inferred + stated knowledge, permanent
         ↓
4. working_memory         ~2,500-token system prompt injected per TP session
```

TP operates from layer 4. It never reads `filesystem_items` directly unless it explicitly calls the Search primitive during a chat.

---

## Layer 1: platform_connections

**Table:** `platform_connections`
**Written by:** OAuth callback (`api/routes/integrations.py`)

Stores per-user, per-platform:
- Encrypted OAuth credentials + refresh token
- `metadata` — workspace name, email, team ID
- `landscape` — JSON snapshot of available resources (channels, labels, pages)
- `landscape_discovered_at` — timestamp of last discovery
- `status` — connected / disconnected / error

Landscape is cleared to NULL on each re-auth and lazily re-discovered when the `/integrations/{provider}/landscape` endpoint is first called after connect.

---

## Layer 2: filesystem_items

**Table:** `filesystem_items`
**Written by:** `api/workers/platform_worker.py`
**Triggered by:** Render cron job every 5 minutes → `api/jobs/platform_sync_scheduler.py`

### Sync frequency (ADR-053)

| Tier     | Frequency | Min interval |
|----------|-----------|--------------|
| Free     | 2x/day    | 6 hours      |
| Starter  | 4x/day    | 4 hours      |
| Pro      | Hourly    | 45 minutes   |

The scheduler checks every 5 minutes whether each user is due. It only syncs sources the user has explicitly selected (stored in `landscape.selected_sources`).

### What each platform extracts

| Platform | Method | What is stored |
|----------|--------|----------------|
| Slack | `MCPClientManager` → `@modelcontextprotocol/server-slack` subprocess | Last 50 messages per selected channel (text, user, timestamp, reactions) |
| Notion | `MCPClientManager` → `@notionhq/notion-mcp-server` subprocess | **Full page content** (title + all text blocks) per selected page |
| Gmail | `GoogleAPIClient` direct REST | Last 50 emails per selected label, 7-day window (subject, from, snippet) |
| Calendar | `GoogleAPIClient` direct REST | Next 7 days of events (summary, description, location, attendees) |

> **Known issue:** `_sync_notion()` uses `MCPClientManager` which spawns `@notionhq/notion-mcp-server` via `npx`. This server requires internal integration tokens (`ntn_...`), not OAuth tokens. This sync path may be silently failing — Notion content may not be landing in `filesystem_items`. The landscape discovery fix (switching to direct `NotionAPIClient`) has not yet been applied to the sync worker.

### TTL

| Platform | Expiry |
|----------|--------|
| Slack    | 72 hours (3 days) |
| Notion   | 168 hours (7 days) |
| Gmail    | 168 hours (7 days) |
| Calendar | 168 hours (7 days) |

Expired rows are cleaned up hourly by `unified_scheduler.py → cleanup_expired_items()`.

### Upsert key

`(user_id, platform, resource_id)` — each source+resource combination is one row, refreshed on each sync.

---

## Layer 3: knowledge_* tables

These are the permanent, per-user knowledge store. They are written by inference jobs that run after sync, not by sync itself. Once written, they persist until explicitly updated or deleted.

### knowledge_profile

**Written by:** `api/services/profile_inference.py → infer_profile_from_filesystem()`
**Triggered by:** After every successful platform sync (`platform_worker.py` line ~142)
**Model:** Claude 3 Haiku

Reads `filesystem_items` (Gmail signatures, Slack profile content, Calendar work hour patterns) and calls Claude Haiku to extract:
- `inferred_name`, `inferred_role`, `inferred_company`, `inferred_timezone`, `inferred_summary`

User can override any field with `stated_*` equivalents. Stated values always win in prompt formatting.

### knowledge_styles

**Written by:** `api/agents/integration/style_learning.py`
**Triggered by:** Slack import jobs when `learn_style=true` config flag is set
**Model:** Claude Sonnet 4

Analyzes user-authored content from `filesystem_items` (Slack messages where `is_user_authored=true`, Notion pages, Gmail sent emails) and extracts per-platform style profile:
- Tone (casual/formal/professional)
- Verbosity (minimal/moderate/detailed)
- Structure, vocabulary, sentence style, emoji usage, formatting preferences

Stored as `knowledge_entries` rows with tags `["style", "{platform}"]`, not in a separate table.
User can state overrides via `stated_preferences` on the style entry.

### knowledge_domains

**Written by:** `api/services/domain_inference.py → recompute_user_domains()`
**Triggered by:** Deliverable create/update (not by platform sync)
**Model:** None — pure heuristic/graph algorithm

Domains are **not derived from filesystem_items**. They are derived from deliverable sources using a graph algorithm:
1. Extracts sources from all user deliverables (e.g., `#client-acme` channel, `acme@company.com` label)
2. Builds adjacency graph — sources that appear together in a deliverable are connected
3. Finds connected components (BFS) — each component becomes a domain
4. Names the domain by pattern-matching source identifiers for client/project names

Each domain has a `sources` JSONB array: `[{platform, resource_id, resource_name}]`

### knowledge_entries

**Written by multiple paths:**

| Source | Writer | Entry type |
|--------|--------|------------|
| Platform sync (style) | `import_jobs.py` | `preference` |
| Background extraction | `services/extraction.py` | `fact`, `decision`, `instruction` |
| TP conversation | Agent during chat | `fact`, `preference` |
| Document upload | `api/routes/documents.py` | `fact` |

Each entry has:
- `content` — the actual fact/preference/decision text
- `entry_type` — preference, fact, decision, instruction
- `source` — inferred, user_stated, document, conversation
- `source_ref JSONB` — `{table, id}` traceability pointer back to origin
- `domain_id` — optional scope to a work domain
- `importance` — 0.0–1.0 float
- `tags TEXT[]`

---

## Layer 4: working_memory (TP system prompt)

**Built by:** `api/services/working_memory.py → build_working_memory()`
**Called at:** Start of every TP streaming response (`thinking_partner.py` line ~466)
**Budget:** ~2,500 tokens

Assembles from knowledge tables (not `filesystem_items`):

| Section | Source table | Cap |
|---------|-------------|-----|
| Profile | `knowledge_profile` | 1 row |
| Styles | `knowledge_styles` | 3 platforms |
| Domains | `knowledge_domains` | all active |
| Entries | `knowledge_entries` | 15 most important |
| Deliverables | `deliverables` | 5 active |
| Platform status | `platform_connections` | all connected, with freshness |
| Recent sessions | `chat_sessions` | 3 sessions, 7-day window, 300-char summaries |

Formatted as readable markdown sections and injected as the system prompt context block.

---

## What TP does NOT have at session start

- Raw Slack messages, Gmail bodies, Notion page content — these stay in `filesystem_items`
- Real-time platform state
- More than 15 knowledge entries

TP only accesses `filesystem_items` if it explicitly calls the `Search(scope="platform_content")` primitive during a chat turn (text search on the `content` column, filtered by `expires_at > now`).

---

## Live platform queries during chat

TP has platform tools available when connected integrations exist. These make live API calls:

| Tool | Platform | Method |
|------|----------|--------|
| `platform_slack_send_message` | Slack | MCP Gateway (Node.js HTTP service) → Slack API |
| `platform_slack_list_channels` | Slack | MCP Gateway → Slack API |
| `platform_notion_search` | Notion | Direct `NotionAPIClient` → Notion REST API |
| `platform_notion_create_comment` | Notion | Direct `NotionAPIClient` → Notion REST API |
| `platform_gmail_search` | Gmail | `GoogleAPIClient` → Gmail API |
| `platform_gmail_create_draft` | Gmail | `GoogleAPIClient` → Gmail API |
| `platform_calendar_list_events` | Calendar | `GoogleAPIClient` → Calendar API |
| `platform_calendar_create_event` | Calendar | `GoogleAPIClient` → Calendar API |

These are action-oriented (TP doing something on a platform), not passive context loading.

---

## MCP Gateway vs MCPClientManager vs Direct API

Three different connection mechanisms exist in the codebase — understanding the distinction prevents confusion:

| Mechanism | Location | Used for | Notes |
|-----------|----------|----------|-------|
| **MCP Gateway** | `mcp-gateway/` (Node.js HTTP service) + `api/services/mcp_gateway.py` (Python client) | TP live Slack tool calls during chat | HTTP-based, only Slack supported |
| **MCPClientManager** | `api/integrations/core/client.py` | Background Slack + Notion sync in `platform_worker.py` | Spawns `npx` subprocess per session, stdio transport |
| **Direct API clients** | `api/integrations/core/notion_client.py`, `api/integrations/core/google_client.py` | Notion landscape discovery, Gmail/Calendar sync and TP tools | Standard REST over httpx |

---

## Known gaps as of 2026-02-17

1. **Notion sync uses wrong method** — `_sync_notion()` in `platform_worker.py` calls `MCPClientManager` which uses `@notionhq/notion-mcp-server`. This server requires internal `ntn_...` tokens, not OAuth tokens. Notion page content is likely not being synced to `filesystem_items`. Fix: replace with direct `NotionAPIClient.get_page_content()` calls, same as the landscape discovery fix applied today.

2. **Style learning is gated** — `knowledge_styles` is only populated during Slack import jobs when `learn_style=true`. It is not triggered by the regular scheduled sync.

3. **Domains depend on deliverables** — If a user has no deliverables yet, `knowledge_domains` is empty regardless of how many platforms are connected.
