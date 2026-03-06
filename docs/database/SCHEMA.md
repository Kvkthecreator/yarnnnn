# Database Schema

**Supabase Project**: `noxgqcwynkzqabljjyon`
**Architecture**: ADR-063 Four-Layer Model (Memory / Activity / Context / Work)
**Extensions**: pgvector (for embeddings on platform_content, filesystem_chunks)
**Last Updated**: 2026-03-03
**Key ADRs**: ADR-072 (Unified Content Layer), ADR-087 (Deliverable Scoped Context — proposed)

---

## Entity Relationship (ADR-063)

```
user      1──n platform_connections    (OAuth connections to platforms)
user      1──n platform_content        (unified content layer — synced content with retention)
user      1──n filesystem_documents    (uploaded files)
user      1──n user_memory             (Memory — what TP knows about the user)
user      1──n activity_log            (Activity — what YARNNN has done)
user      1──n chat_sessions           (TP conversations)
user      1──n deliverables            (scheduled outputs)

platform_content    n──1 platform_content   (version chain via version_of)
filesystem_documents 1──n filesystem_chunks  (document segments)
chat_sessions 1──n session_messages          (conversation turns)
deliverables 1──n deliverable_versions       (generated outputs)
```

---

## Four-Layer Model

### Layer 1: Memory (user_memory)

What TP knows *about the user* — stable, explicit, user-owned. Injected into every TP session.

| Table | Purpose |
|-------|---------|
| `user_memory` | Single flat Memory store (renamed from `user_context` in ADR-087 migration window) |

### Layer 2: Activity (activity_log)

What YARNNN has done — system provenance log. Append-only. Recent events injected into every TP session.

| Table | Purpose |
|-------|---------|
| `activity_log` | Timestamped event log across all pipelines (deliverable runs, syncs, memory writes, chat sessions) |

### Layer 3: Context (Platform Content)

The current working material — what's in their platforms right now. ADR-072 unified content layer with retention-based accumulation.

| Table | Purpose |
|-------|---------|
| `platform_connections` | OAuth connections to external platforms |
| `platform_content` | Unified content layer with retention (replaces filesystem_items) |
| `filesystem_documents` | Uploaded PDF, DOCX, TXT, MD files |
| `filesystem_chunks` | Document segments with embeddings (for Search) |
| `sync_registry` | Per-resource sync state tracking |

### Layer 4: Work

What TP produces.

| Table | Purpose |
|-------|---------|
| `deliverables` | Scheduled output configurations |
| `deliverable_versions` | Generated outputs |

---

## Memory Table

### 1. user_memory

Single flat key-value Memory store. Renamed from `user_context` in ADR-087 migration window. Replaces `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries` (all dropped in migration 057).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| key | TEXT | Namespaced key (see below) |
| value | TEXT | The stored value |
| source | TEXT | `user_stated`, `tp_extracted`, `document`, `feedback`, `pattern` |
| confidence | FLOAT | 0.0–1.0. user_stated = 1.0, feedback = 0.7, pattern = 0.6 |
| source_ref | UUID | ADR-072: FK to source record (session_id, version_id, etc.) |
| source_type | TEXT | ADR-072: Type of source: `session_message`, `deliverable_version`, `platform_content`, `activity_log` |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

**Unique constraint**: `(user_id, key)`

**Key patterns**:

| Key | Meaning | Example |
|-----|---------|---------|
| `name` | User's name | `"Kevin"` |
| `role` | Job title / role | `"Head of Growth"` |
| `company` | Company name | `"YARNNN"` |
| `timezone` | User timezone | `"Asia/Singapore"` |
| `summary` | Brief bio | `"Solo founder building..."` |
| `tone_{platform}` | Communication style | `tone_slack = "casual"` |
| `verbosity_{platform}` | Verbosity preference | `verbosity_gmail = "detailed"` |
| `fact:...` | Noted fact | `fact:prefers bullet points` |
| `instruction:...` | Standing instruction | `instruction:always include TL;DR` |
| `preference:...` | Stated preference | `preference:no jargon in reports` |

**Written by**: User directly (Context page), TP during conversation (`create_memory` / `update_memory` tools)
**Never written by**: background inference — all inference pipelines removed in ADR-059
**Read by**: `working_memory.py → build_working_memory()` at session start

---

## Activity Table

### 2. activity_log

Append-only system provenance log. Records what YARNNN has done across all pipelines.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| event_type | TEXT | `deliverable_run`, `memory_written`, `platform_synced`, `chat_session` |
| event_ref | UUID | FK reference to related record (version_id, session_id, etc.) |
| summary | TEXT | Human-readable one-liner for working memory injection |
| metadata | JSONB | Event-specific structured detail |
| created_at | TIMESTAMPTZ | Auto |

**Append-only**: no UPDATE or DELETE policies. Written by service role only.

**event_type values**:

| event_type | Written by | summary example |
|---|---|---|
| `deliverable_run` | `deliverable_execution.py` | `"Weekly Digest v3 generated (staged)"` |
| `memory_written` | TP memory tools | `"Noted: prefers bullet points"` |
| `platform_synced` | `platform_worker.py` | `"Synced gmail/INBOX: 12 items"` |
| `chat_session` | `chat.py` | `"Chat session (8 turns)"` |

**Read by**: `working_memory.py → build_working_memory()` — last 10 events (7-day window) injected as "Recent activity" block in TP system prompt (~300 tokens)

---

## Context Tables

### 3. platform_connections

OAuth connections to external platforms.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| platform | TEXT | `slack`, `gmail`, `notion`, `calendar` |
| status | TEXT | `active`, `disconnected`, `error` |
| credentials_encrypted | TEXT | Encrypted OAuth access token |
| refresh_token_encrypted | TEXT | Encrypted refresh token (Google only) |
| metadata | JSONB | Workspace name, user info |
| settings | JSONB | User preferences for this connection |
| landscape | JSONB | Available resources + selected sources |
| last_synced_at | TIMESTAMPTZ | Last successful sync |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

**Unique constraint**: `(user_id, platform)`

---

### 4. platform_content

ADR-072: Unified content layer with retention-based accumulation. Replaces `filesystem_items`.

Content that proves significant (referenced by deliverables, signals, or TP) is retained indefinitely.
Unreferenced content expires after TTL.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| platform | TEXT | Source platform (`slack`, `gmail`, `notion`, `calendar`) |
| resource_id | TEXT | Channel ID, label, page ID, calendar ID |
| resource_name | TEXT | Human-readable resource name |
| item_id | TEXT | Unique item identifier from platform |
| content | TEXT | Full text content |
| content_type | TEXT | `message`, `email`, `page`, `event` |
| content_hash | TEXT | SHA-256 for deduplication on re-fetch |
| title | TEXT | Subject line, page title, event title |
| content_embedding | vector(1536) | Semantic search via pgvector |
| version_of | UUID | FK → platform_content (version chain) |
| fetched_at | TIMESTAMPTZ | When fetched from platform |
| retained | BOOLEAN | When true, content never expires |
| retained_reason | TEXT | `deliverable_execution`, `tp_session` |
| retained_ref | UUID | FK to the record that marked this retained |
| retained_at | TIMESTAMPTZ | When marked retained |
| expires_at | TIMESTAMPTZ | NULL if retained=true, otherwise TTL |
| author | TEXT | Who authored this content |
| author_id | TEXT | Platform-specific author ID |
| is_user_authored | BOOLEAN | True if user wrote this |
| source_timestamp | TIMESTAMPTZ | When created on platform |
| metadata | JSONB | Platform-specific metadata |
| sync_batch_id | UUID | Batch identifier |
| created_at | TIMESTAMPTZ | Auto |

**Unique constraint**: `(user_id, platform, resource_id, item_id, content_hash)`

**Retention policy**:
| Condition | `retained` | `expires_at` | Outcome |
|---|---|---|---|
| Content never referenced | `false` | `NOW() + TTL` | Expires after TTL |
| Referenced by deliverable_version | `true` | `NULL` | Retained indefinitely |
| Accessed during TP session | `true` | `NULL` | Retained indefinitely |

**TTL by platform** (ADR-077, extended from original values):
- Slack: 14 days
- Gmail: 30 days
- Notion: 90 days
- Calendar: 2 days

---

### 5. filesystem_documents

Uploaded files.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| filename | TEXT | Original filename |
| file_type | TEXT | `pdf`, `docx`, `txt`, `md` |
| file_size | INTEGER | Bytes |
| storage_path | TEXT | Supabase Storage path |
| processing_status | TEXT | `pending`, `processing`, `completed`, `failed` |
| page_count | INTEGER | For PDFs |
| word_count | INTEGER | Approximate |
| error_message | TEXT | On failure |
| uploaded_at | TIMESTAMPTZ | Auto |
| processed_at | TIMESTAMPTZ | When processing completed |

---

### 6. filesystem_chunks

Document segments for retrieval.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK → filesystem_documents |
| content | TEXT | Chunk text (~400 tokens) |
| chunk_index | INTEGER | 0-based order |
| page_number | INTEGER | For PDFs |
| embedding | vector(1536) | For semantic search |
| token_count | INTEGER | Actual token count |
| metadata | JSONB | Section title, heading level |
| created_at | TIMESTAMPTZ | Auto |

---

### 7. sync_registry

Per-resource sync state tracking.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| platform | TEXT | Platform name |
| resource_id | TEXT | Channel/label/page ID |
| resource_name | TEXT | Human-readable name |
| last_synced_at | TIMESTAMPTZ | Last sync time |
| platform_cursor | TEXT | Platform-specific pagination cursor |
| item_count | INTEGER | Items synced for this resource |

**Unique constraint**: `(user_id, platform, resource_id)`

---

## Session Tables

### 8. chat_sessions

TP conversation containers. Inactivity-based session boundary (ADR-067).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| project_id | UUID | FK → projects (nullable, currently unused — all values NULL) |
| session_type | TEXT | `thinking_partner` (default) |
| status | TEXT | `active`, `completed`, `archived` |
| started_at | TIMESTAMPTZ | Session start |
| ended_at | TIMESTAMPTZ | Session end (nullable) |
| context_metadata | JSONB | Session context `{}` |
| summary | TEXT | Prose summary written by nightly cron (ADR-067 Phase 1) |
| compaction_summary | TEXT | In-session compaction summary (ADR-067 Phase 3) |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Bumped on every message append — doubles as last_message_at |
| deliverable_id | UUID | ADR-087: FK → deliverables (nullable, ON DELETE SET NULL). Routes session to a specific deliverable for scoped memory accumulation. |

**Session boundary**: `get_or_create_chat_session()` reuses sessions active within 4h inactivity window (ADR-067 Phase 2).

---

### 9. session_messages

Conversation turns within a session.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| session_id | UUID | FK → chat_sessions |
| role | TEXT | `user`, `assistant`, `system` |
| content | TEXT | Message content |
| sequence_number | INTEGER | Order within session |
| metadata | JSONB | `{tokens, latency_ms, model}` |
| created_at | TIMESTAMPTZ | Auto |

Note: `knowledge_extracted` and `knowledge_extracted_at` columns were dropped in migration 059 (ADR-059 — extraction pipeline removed).

---

## Work Tables

### 10. deliverables

Scheduled output configurations. The unit of work in YARNNN — each deliverable is a self-contained specialist (see [Agent Model Comparison](../architecture/agent-model-comparison.md)).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| project_id | UUID | FK → projects (nullable, currently unused — all values NULL) |
| title | TEXT | Deliverable name |
| description | TEXT | Optional description |
| deliverable_type | TEXT | Type identifier (8 active types — ADR-082) |
| type_config | JSONB | Type-specific settings `{}` |
| type_classification | JSONB | `{binding, temporal_pattern}` (ADR-044) |
| status | TEXT | `active`, `paused`, `archived` |
| sources | JSONB | `[{platform, resource_id, resource_name}]` |
| schedule | JSONB | `{frequency, time, timezone}` |
| recipient_context | JSONB | Audience/delivery configuration |
| template_structure | JSONB | Output format/structure settings `{}` |
| destination | JSONB | Primary delivery destination (ADR-028) |
| destinations | JSONB | Multiple delivery destinations `[]` |
| platform_variant | TEXT | Platform-specific variant (nullable) |
| trigger_type | TEXT | `schedule` (default), `event`, `manual` |
| trigger_config | JSONB | Event trigger configuration (nullable) |
| origin | TEXT | `user_configured`, `analyst_suggested`, `signal_emergent` (ADR-068) |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |
| last_run_at | TIMESTAMPTZ | Last execution |
| next_run_at | TIMESTAMPTZ | Next scheduled run |
| last_triggered_at | TIMESTAMPTZ | Last event trigger |
| deliverable_instructions | TEXT | ADR-087: User-authored behavioral directives (default `''`) |
| deliverable_memory | JSONB | ADR-087: System-accumulated knowledge `{}` |
| mode | TEXT | ADR-087: `recurring` (default) or `goal` |

---

### 11. deliverable_versions

Generated outputs. Each version captures the draft, the user's final edit, and structured feedback.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| deliverable_id | UUID | FK → deliverables |
| version_number | INTEGER | Sequence number (unique per deliverable) |
| status | TEXT | `generating`, `staged`, `reviewing`, `approved`, `rejected`, `suggested` |
| draft_content | TEXT | What YARNNN produced |
| final_content | TEXT | What the user approved/sent (after edits) |
| edit_diff | JSONB | Structured diff between draft and final |
| edit_categories | JSONB | `{additions, deletions, restructures, rewrites}` |
| edit_distance_score | FLOAT | 0.0 = no edits, 1.0 = complete rewrite |
| feedback_notes | TEXT | Explicit user feedback |
| source_snapshots | JSONB | Context used at generation `[]` |
| delivery_mode | TEXT | `draft`, `direct`, NULL (ADR-032) |
| analyst_metadata | JSONB | For `suggested` status — confidence, detected pattern (ADR-060) |
| context_snapshot_id | UUID | Future: reference to context state |
| pipeline_run_id | UUID | Reference to gather work ticket |
| created_at | TIMESTAMPTZ | Auto |
| staged_at | TIMESTAMPTZ | When staged for review |
| approved_at | TIMESTAMPTZ | When approved |

---

## Working Memory

Built at session start from **Memory + Activity** layers. Raw platform content is not pre-injected.

```
### About you
{name, role, company, timezone, summary}

### Your preferences
{tone_*, verbosity_*, preference:*}

### What you've told me
{fact:*, instruction:*}

### Active deliverables
{title, destination, sources, schedule — max 5}

### Connected platforms
{name, status, last_synced, freshness}

### Recent activity
{last 10 events from activity_log, last 7 days}
### Current deliverable: {title} ({type})   ← ADR-087, only when session is scoped
{instructions, session_summaries (queried via deliverable_id FK), observations, goal}
```

Injected into TP's system prompt (~2,000 token budget + ~500 for deliverable scope). During a session, TP accesses platform content via `Search(scope="platform_content")` (hits `platform_content` table with semantic search) or direct platform tools (live API calls).

**ADR-087:** When a session is in deliverable scope (via `surface_context.deliverableId`), the scoped deliverable's instructions and memory are injected into the working memory prompt. Session summaries are queried from `chat_sessions` by `deliverable_id` FK (not duplicated in JSONB). The headless generation prompt also receives the same context.

---

## Migrations

| Migration | Description | Status |
|-----------|-------------|--------|
| 001-042 | Legacy migrations | Applied |
| 043-045 | ADR-058: Terminology rename + knowledge_* tables created | Applied (knowledge_* dropped in 057) |
| 046 | Restore integration_import_jobs | Applied |
| 047-050 | Fix RPCs for ADR-058 schema | Applied |
| 051-054 | ADR-060: Background Conversation Analyst + suggested status | Applied |
| 055 | ADR-059: Create user_context table | Applied |
| 056 | ADR-059: Migrate stated data from knowledge_* → user_context | Applied |
| 057 | ADR-059: Drop knowledge_profile/styles/domains/entries | Applied |
| 058 | Fix SECURITY DEFINER view | Applied |
| 059 | ADR-059: Drop dead columns from session_messages | Applied |
| 060 | ADR-063: Create activity_log table | Applied |
| 061 | ADR-067: Session compaction — summary, compaction_summary, inactivity-based boundary | Applied |
| 064 | Deliverable type constraint expansion | Applied |
| 070 | ADR-068: Deliverable origin column (signal_emergent) | Applied |
| 071 | ADR-068: Signal history table | Applied |
| 073 | ADR-066: Drop governance/governance_ceiling columns | Applied |
| 075 | Phase 2 strategic types — type constraint update | Applied |
| 077 | ADR-072: Create platform_content, migrate filesystem_items, drop legacy | Applied |
| 078 | ADR-072: Add source_ref/source_type to user_context | Applied |
| 079 | Daily token usage function | Applied |
| 080 | Activity log granular events | Applied |
| 081 | Signal history RLS | Applied |
| 082 | MCP OAuth tables (ADR-075) | Applied |
| 083 | Sync registry error columns | Applied |
| 084 | ADR-087: Rename user_context → user_memory | Pending |
| 085 | ADR-087: Deliverable scoped context (instructions, memory, mode, deliverable_id) | Pending |

---

## Removed Tables (do not reference in new code)

Per ADR-072 (migration 077):
- `filesystem_items` — replaced by `platform_content` with retention-based accumulation

Per ADR-059 (migration 057):
- `knowledge_profile` — replaced by `user_memory` keys: `name`, `role`, `company`, `timezone`, `summary`
- `knowledge_styles` — replaced by `user_memory` keys: `tone_{platform}`, `verbosity_{platform}`
- `knowledge_domains` — removed entirely (deliverable.sources carries source context directly)
- `knowledge_entries` — replaced by `user_memory` with key pattern `{type}:{content}`

Per ADR-058 (migration 045):
- `user_integrations`, `ephemeral_context`, `documents`, `chunks`, `context_domains`, `memories`

---

## Extension Requirements

```sql
-- Required for embeddings (filesystem_chunks only)
CREATE EXTENSION IF NOT EXISTS vector;
```
