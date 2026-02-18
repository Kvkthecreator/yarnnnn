# Database Schema

**Supabase Project**: `noxgqcwynkzqabljjyon`
**Architecture**: ADR-059 Simplified Context Model (Three-Layer: Memory / Context / Work)
**Extensions**: pgvector (for embeddings on filesystem_chunks)
**Last Updated**: 2026-02-18

---

## Entity Relationship (ADR-059)

```
user      1──n platform_connections    (OAuth connections to platforms)
user      1──n filesystem_items        (synced platform content — conversational search cache)
user      1──n filesystem_documents    (uploaded files)
user      1──n user_context            (Memory — what TP knows about the user)
user      1──n chat_sessions           (TP conversations)
user      1──n deliverables            (scheduled outputs)

filesystem_documents 1──n filesystem_chunks  (document segments)
chat_sessions 1──n session_messages          (conversation turns)
deliverables 1──n deliverable_versions       (generated outputs)
```

---

## Three-Layer Model

### Layer 1: Memory (user_context)

What TP knows *about the user* — stable, explicit, user-owned. Injected into every TP session.

| Table | Purpose |
|-------|---------|
| `user_context` | Single flat Memory store (replaces the four knowledge_* tables from ADR-058) |

### Layer 2: Context (Filesystem)

The current working material — what's in their platforms right now.

| Table | Purpose |
|-------|---------|
| `platform_connections` | OAuth connections to external platforms |
| `filesystem_items` | Synced content cache for conversational Search |
| `filesystem_documents` | Uploaded PDF, DOCX, TXT, MD files |
| `filesystem_chunks` | Document segments with embeddings (for Search) |
| `sync_registry` | Per-resource sync state tracking |

### Layer 3: Work

What TP produces.

| Table | Purpose |
|-------|---------|
| `deliverables` | Scheduled output configurations |
| `deliverable_versions` | Generated outputs |

---

## Memory Table

### 1. user_context

Single flat key-value Memory store. Replaces `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries` (all dropped in migration 057).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| key | TEXT | Namespaced key (see below) |
| value | TEXT | The stored value |
| source | TEXT | `user_stated`, `tp_extracted`, `document` |
| confidence | FLOAT | 0.0–1.0. user_stated = 1.0 |
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

## Context Tables

### 2. platform_connections

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

### 3. filesystem_items

Synced platform content — conversational search cache. Not used by deliverable execution.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| platform | TEXT | Source platform |
| resource_id | TEXT | Channel ID, label, page ID |
| resource_name | TEXT | Human-readable resource name |
| item_id | TEXT | Unique item identifier from platform |
| content | TEXT | Message/email/page content |
| content_type | TEXT | `message`, `email`, `page`, `event` |
| author | TEXT | Who authored this content |
| is_user_authored | BOOLEAN | True if user wrote this |
| source_timestamp | TIMESTAMPTZ | When created on platform |
| metadata | JSONB | Platform-specific metadata |
| sync_batch_id | UUID | Batch identifier |
| synced_at | TIMESTAMPTZ | When synced |
| expires_at | TIMESTAMPTZ | TTL for cleanup |

**Unique constraint**: `(user_id, platform, resource_id, item_id)`

---

### 4. filesystem_documents

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

### 5. filesystem_chunks

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

### 6. sync_registry

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

### 7. chat_sessions

TP conversation containers.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| status | TEXT | `active`, `completed`, `archived` |
| summary | TEXT | Optional session summary |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

---

### 8. session_messages

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

---

## Work Tables

### 9. deliverables

Scheduled output configurations.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| title | TEXT | Deliverable name |
| deliverable_type | TEXT | Type identifier |
| status | TEXT | `active`, `paused`, `archived` |
| sources | JSONB | `[{platform, resource_id, resource_name}]` |
| schedule | JSONB | `{frequency, time, timezone}` |
| recipient_context | JSONB | Delivery configuration |
| template | JSONB | Template settings |
| type_classification | JSONB | `{binding, temporal_pattern}` |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |
| next_run_at | TIMESTAMPTZ | Next scheduled run |

---

### 10. deliverable_versions

Generated outputs.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| deliverable_id | UUID | FK → deliverables |
| content | TEXT | Generated content |
| version_number | INTEGER | Sequence number |
| status | TEXT | `draft`, `approved`, `published`, `suggested` |
| source_snapshots | JSONB | Context used at generation |
| generated_at | TIMESTAMPTZ | Auto |
| approved_at | TIMESTAMPTZ | When approved |
| published_at | TIMESTAMPTZ | When published |

---

## Working Memory

Built at session start from **user_context only** (Memory layer). Raw platform content is not pre-injected.

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
```

Injected into TP's system prompt (~2,000 token budget). During a session, TP accesses live platform content via `Search(scope="platform_content")` (hits `filesystem_items`) or direct platform tools (live API calls).

---

## Migrations

| Migration | Description | Status |
|-----------|-------------|--------|
| 001-042 | Legacy migrations | Applied |
| 043-045 | ADR-058: Terminology rename + knowledge_* tables created | Applied (knowledge_* dropped in 057) |
| 046 | Restore integration_import_jobs | Applied |
| 047-050 | Fix RPCs for ADR-058 schema | Applied |
| 051-054 | ADR-060: Background Conversation Analyst | Applied |
| 055 | ADR-059: Create user_context table | Applied |
| 056 | ADR-059: Migrate stated data from knowledge_* → user_context | Applied |
| 057 | ADR-059: Drop knowledge_profile/styles/domains/entries | Applied |

---

## Removed Tables (do not reference in new code)

Per ADR-059 (migration 057):
- `knowledge_profile` — replaced by `user_context` keys: `name`, `role`, `company`, `timezone`, `summary`
- `knowledge_styles` — replaced by `user_context` keys: `tone_{platform}`, `verbosity_{platform}`
- `knowledge_domains` — removed entirely (deliverable.sources carries source context directly)
- `knowledge_entries` — replaced by `user_context` with key pattern `{type}:{content}`

Per ADR-058 (migration 045):
- `user_integrations`, `ephemeral_context`, `documents`, `chunks`, `context_domains`, `memories`

---

## Extension Requirements

```sql
-- Required for embeddings (filesystem_chunks only)
CREATE EXTENSION IF NOT EXISTS vector;
```
