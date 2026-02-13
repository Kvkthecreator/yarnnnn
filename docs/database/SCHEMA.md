# Database Schema

**Supabase Project**: `noxgqcwynkzqabljjyon`
**Architecture**: ADR-058 Knowledge Base Architecture (Filesystem + Knowledge)
**Extensions**: pgvector (for embeddings)
**Last Updated**: 2026-02-13

---

## Entity Relationship (ADR-058)

```
user      1──n platform_connections    (OAuth connections to platforms)
user      1──n filesystem_items        (synced platform content)
user      1──n filesystem_documents    (uploaded files)
user      1──1 knowledge_profile       (inferred + stated profile)
user      1──n knowledge_styles        (per-platform communication styles)
user      1──n knowledge_domains       (work context groupings)
user      1──n knowledge_entries       (facts, preferences, decisions)
user      1──n chat_sessions           (TP conversations)
user      1──n deliverables            (scheduled outputs)

filesystem_documents 1──n filesystem_chunks  (document segments)
chat_sessions 1──n session_messages          (conversation turns)
deliverables 1──n deliverable_versions       (generated outputs)
```

---

## ADR-058 Two-Layer Model

### Layer 1: Filesystem (Raw Data)

The source of truth — synced platform content and uploaded documents.

| Table | Purpose |
|-------|---------|
| `platform_connections` | OAuth connections to external platforms |
| `filesystem_items` | Synced messages, emails, pages, events |
| `filesystem_documents` | Uploaded PDF, DOCX, TXT, MD files |
| `filesystem_chunks` | Document segments with embeddings |
| `sync_registry` | Per-resource sync state tracking |

### Layer 2: Knowledge (Inferred Narrative)

Derived from filesystem — what TP knows about the user.

| Table | Purpose |
|-------|---------|
| `knowledge_profile` | Who the user is (name, role, company, timezone) |
| `knowledge_styles` | How they communicate per platform |
| `knowledge_domains` | What they're working on (work contexts) |
| `knowledge_entries` | Facts, preferences, decisions, instructions |

---

## Filesystem Tables

### 1. platform_connections

OAuth connections to external platforms (replaces `user_integrations`).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| platform | TEXT | 'slack', 'gmail', 'notion', 'calendar' |
| status | TEXT | 'active', 'disconnected', 'error' |
| credentials_encrypted | TEXT | Encrypted OAuth tokens |
| metadata | JSONB | Workspace name, user info |
| settings | JSONB | User preferences for this connection |
| landscape | JSONB | Available resources + selected sources |
| last_synced_at | TIMESTAMPTZ | Last successful sync |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

**Unique constraint**: `(user_id, platform)`

---

### 2. filesystem_items

Synced platform content — the "filesystem" (replaces `ephemeral_context`).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| platform | TEXT | Source platform |
| resource_id | TEXT | Channel ID, label, page ID |
| resource_name | TEXT | Human-readable resource name |
| item_id | TEXT | Unique item identifier from platform |
| content | TEXT | Message/email/page content |
| content_type | TEXT | 'message', 'email', 'page', 'event' |
| author | TEXT | Who authored this content |
| is_user_authored | BOOLEAN | True if user wrote this (for style inference) |
| source_timestamp | TIMESTAMPTZ | When created on platform |
| metadata | JSONB | Platform-specific metadata |
| sync_batch_id | UUID | Batch identifier |
| synced_at | TIMESTAMPTZ | When synced |
| expires_at | TIMESTAMPTZ | TTL for cleanup |

**Unique constraint**: `(user_id, platform, resource_id, item_id)`

---

### 3. filesystem_documents

Uploaded files (replaces `documents`).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| filename | TEXT | Original filename |
| file_type | TEXT | 'pdf', 'docx', 'txt', 'md' |
| file_size | INTEGER | Bytes |
| storage_path | TEXT | Supabase Storage path |
| processing_status | TEXT | 'pending', 'processing', 'completed', 'failed' |
| page_count | INTEGER | For PDFs |
| word_count | INTEGER | Approximate |
| error_message | TEXT | On failure |
| uploaded_at | TIMESTAMPTZ | Auto |
| processed_at | TIMESTAMPTZ | When processing completed |

---

### 4. filesystem_chunks

Document segments for retrieval (replaces `chunks`).

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

### 5. sync_registry

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

## Knowledge Tables

### 6. knowledge_profile

User profile with inferred + stated fields.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users, UNIQUE |
| inferred_name | TEXT | From email signatures, etc. |
| inferred_role | TEXT | Job title/role |
| inferred_company | TEXT | Company name |
| inferred_timezone | TEXT | From calendar patterns |
| inferred_summary | TEXT | Brief bio/description |
| stated_name | TEXT | User override (takes precedence) |
| stated_role | TEXT | User override |
| stated_company | TEXT | User override |
| stated_timezone | TEXT | User override |
| stated_summary | TEXT | User override |
| last_inferred_at | TIMESTAMPTZ | Last inference run |
| inference_sources | JSONB | What was used for inference |
| inference_confidence | FLOAT | Confidence score |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

**Key pattern**: `get_name() = stated_name OR inferred_name`

---

### 7. knowledge_styles

Platform-specific communication styles.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| platform | TEXT | 'slack', 'email', 'notion' |
| tone | TEXT | 'casual', 'formal', 'mixed' |
| verbosity | TEXT | 'minimal', 'moderate', 'detailed' |
| formatting | JSONB | {uses_emoji, uses_bullets, avg_length} |
| vocabulary_notes | TEXT | "Uses technical jargon" |
| sample_excerpts | TEXT[] | Actual examples of user's writing |
| stated_preferences | JSONB | User overrides |
| sample_count | INTEGER | Messages analyzed |
| last_inferred_at | TIMESTAMPTZ | Last inference run |
| inference_sources | JSONB | Source tracking |

**Unique constraint**: `(user_id, platform)`

---

### 8. knowledge_domains

Work context groupings (replaces `context_domains`).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| name | TEXT | Domain name |
| name_source | TEXT | 'inferred' or 'user' |
| summary | TEXT | Inferred narrative |
| key_facts | TEXT[] | Important facts |
| key_people | JSONB | [{name, role, notes}] |
| key_decisions | TEXT[] | Important decisions |
| sources | JSONB | [{platform, resource_id, resource_name}] |
| is_default | BOOLEAN | Default domain flag |
| is_active | BOOLEAN | Active flag |
| last_inferred_at | TIMESTAMPTZ | Last inference run |
| inference_confidence | FLOAT | Confidence score |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

---

### 9. knowledge_entries

Facts, preferences, decisions, instructions (replaces `memories`).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| domain_id | UUID | FK → knowledge_domains (nullable) |
| content | TEXT | The knowledge content |
| entry_type | TEXT | 'preference', 'fact', 'decision', 'instruction' |
| source | TEXT | 'inferred', 'user_stated', 'document', 'conversation' |
| source_ref | JSONB | {table, id} for traceability |
| confidence | FLOAT | For inferred entries |
| inference_sources | JSONB | Source tracking |
| tags | TEXT[] | Emergent tags |
| importance | FLOAT | 0-1, retrieval priority |
| embedding | vector(1536) | For semantic search |
| is_active | BOOLEAN | Soft-delete flag |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

---

## Session Tables

### 10. chat_sessions

TP conversation containers (minimal changes).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| domain_id | UUID | FK → knowledge_domains (nullable) |
| status | TEXT | 'active', 'completed', 'archived' |
| summary | TEXT | Optional session summary |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

---

### 11. session_messages

Conversation turns within a session.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| session_id | UUID | FK → chat_sessions |
| role | TEXT | 'user', 'assistant', 'system' |
| content | TEXT | Message content |
| sequence_number | INTEGER | Order within session |
| metadata | JSONB | {tokens, latency_ms, model} |
| knowledge_extracted | BOOLEAN | Extraction tracking |
| knowledge_extracted_at | TIMESTAMPTZ | When extracted |
| created_at | TIMESTAMPTZ | Auto |

---

## Deliverable Tables

### 12. deliverables

Scheduled outputs.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users |
| domain_id | UUID | FK → knowledge_domains (nullable) |
| title | TEXT | Deliverable name |
| deliverable_type | TEXT | Type identifier |
| status | TEXT | 'active', 'paused', 'archived' |
| sources | JSONB | [{platform, resource_id, resource_name}] |
| schedule | JSONB | {frequency, time, timezone} |
| recipient_context | JSONB | Delivery configuration |
| template | JSONB | Template settings |
| type_classification | JSONB | {binding, temporal_pattern} |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |
| next_run_at | TIMESTAMPTZ | Next scheduled run |

---

### 13. deliverable_versions

Generated outputs.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| deliverable_id | UUID | FK → deliverables |
| content | TEXT | Generated content |
| version_number | INTEGER | Sequence number |
| status | TEXT | 'draft', 'approved', 'published' |
| source_snapshots | JSONB | Context used at generation |
| generated_at | TIMESTAMPTZ | Auto |
| approved_at | TIMESTAMPTZ | When approved |
| published_at | TIMESTAMPTZ | When published |

---

## Working Memory

The Working Memory is built at request time from Knowledge tables:

```python
working_memory = {
    "profile": knowledge_profile,      # WHO
    "styles": knowledge_styles[],      # HOW
    "domains": knowledge_domains[],    # WHAT
    "entries": knowledge_entries[],    # KNOWN
    "platforms": platform_connections[], # STATUS
    "deliverables": deliverables[],    # WORK
    "recent_sessions": chat_sessions[], # HISTORY
}
```

This is injected into TP's system prompt (~2,500 tokens).

---

## Migrations

| Migration | Description | Status |
|-----------|-------------|--------|
| 001-042 | Legacy migrations | Applied |
| 043 | ADR-058: Create new schema tables | Applied |
| 044 | ADR-058: Data migration from old tables | Applied |
| 045 | ADR-058: Drop old tables, cleanup | Applied |
| 046 | Restore integration_import_jobs | Applied |
| 047 | Fix memory RPCs for knowledge_entries | Applied |
| 048 | Fix domain RPCs for knowledge_domains.sources | Applied |

---

## Key Design Decisions

### ADR-058: Knowledge Base Architecture

1. **Two-layer model**: Filesystem (source of truth) + Knowledge (derived narrative)
2. **Inference-driven**: Knowledge is inferred from filesystem, not manually curated
3. **User overrides**: `stated_*` fields take precedence over `inferred_*`
4. **Working memory**: Compact knowledge injected into TP prompt (~2,500 tokens)
5. **Transparent**: Users can see and edit what TP knows

### Terminology Alignment

| Old Term | New Term |
|----------|----------|
| `ephemeral_context` | `filesystem_items` |
| `memories` | `knowledge_entries` |
| `user_integrations` | `platform_connections` |
| `context_domains` | `knowledge_domains` |
| `documents` | `filesystem_documents` |
| `chunks` | `filesystem_chunks` |

---

## Extension Requirements

```sql
-- Required for embeddings
CREATE EXTENSION IF NOT EXISTS vector;
```
