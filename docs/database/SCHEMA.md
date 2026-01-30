# Database Schema

**Supabase Project**: `noxgqcwynkzqabljjyon`
**Architecture**: ADR-005 Unified Memory, ADR-006 Sessions, ADR-008 Documents
**Extensions**: pgvector (for embeddings)

---

## Entity Relationship

```
user      1──n memories         (unified memory: user + project scoped)
user      1──n chat_sessions    (TP conversations)
user      1──n documents        (uploaded files)

project   1──n memories         (project-scoped memories)
project   1──n chat_sessions    (project-scoped conversations)
project   1──n documents        (project-scoped documents)
project   1──n work_tickets     (future: work orchestration)

document  1──n chunks           (semantic segments with embeddings)
chat_session 1──n session_messages (conversation turns)
work_ticket 1──n work_outputs   (agent deliverables)
```

---

## Core Tables

### 1. memories

Unified memory storage (ADR-005). Replaces the previous `user_context` and `blocks` tables.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, auto-generated |
| user_id | UUID | FK → auth.users, required |
| project_id | UUID | FK → projects, **NULL = user-scoped** |
| content | TEXT | The actual memory content |
| embedding | vector(1536) | For semantic retrieval |
| tags | TEXT[] | Emergent tags, LLM-extracted or user-added |
| entities | JSONB | `{people: [], companies: [], concepts: []}` |
| importance | FLOAT | 0-1, retrieval priority |
| source_type | TEXT | `chat`, `document`, `manual`, `import` |
| source_ref | JSONB | `{session_id, chunk_id, document_id, etc.}` |
| is_active | BOOLEAN | Soft-delete flag (default true) |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto |

**Scope Logic:**
- `project_id IS NULL` → User-scoped (portable across all projects)
- `project_id IS NOT NULL` → Project-scoped (isolated to specific work)

**RLS:** Users can only manage their own memories.

---

### 2. chat_sessions

Thinking Partner conversation containers (ADR-006).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users, direct ownership |
| project_id | UUID | FK → projects, **nullable** (NULL = global/orchestration chat) |
| session_type | TEXT | Default: `thinking_partner` |
| status | TEXT | `active`, `completed`, `archived` |
| started_at | TIMESTAMPTZ | Session start |
| ended_at | TIMESTAMPTZ | Session end |
| context_metadata | JSONB | `{memories_count, context_type, model}` |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto (trigger) |

**Session Reuse:** Daily scope - one active session per user/project/day.

**RLS:** Users own their chat sessions.

**RPCs:**
- `get_or_create_chat_session(user_id, project_id, session_type, scope)` - Daily reuse logic
- `append_session_message(session_id, role, content, metadata)` - Auto sequence numbers

---

### 3. session_messages

Individual conversation turns within a chat session (ADR-006).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| session_id | UUID | FK → chat_sessions |
| role | TEXT | `user`, `assistant`, `system` |
| content | TEXT | Message content |
| sequence_number | INTEGER | Order within session (unique per session) |
| metadata | JSONB | `{tokens, latency_ms, model}` |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can access messages in their sessions.

---

### 4. documents

Uploaded files (PDF, DOCX, etc). Parsed into chunks (ADR-008).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → auth.users, direct ownership |
| project_id | UUID | FK → projects, **nullable** (user-scoped if NULL) |
| filename | TEXT | Required |
| file_url | TEXT | Supabase Storage URL |
| storage_path | TEXT | Bucket path: `{user_id}/{doc_id}/original.{ext}` |
| file_type | TEXT | `pdf`, `docx`, `txt`, `md` |
| file_size | INTEGER | Bytes |
| processing_status | TEXT | `pending`, `processing`, `completed`, `failed` |
| processed_at | TIMESTAMPTZ | When processing completed |
| error_message | TEXT | On failure |
| page_count | INTEGER | For PDFs |
| word_count | INTEGER | Approximate |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can manage their own documents (via user_id).

**Storage:** `documents` bucket with user-folder RLS.

---

### 5. chunks

Document segments for retrieval. Intermediate layer between raw documents and derived memories.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK → documents |
| content | TEXT | Chunk text (~400 tokens) |
| embedding | vector(1536) | For semantic retrieval |
| chunk_index | INTEGER | 0-based order in document |
| page_number | INTEGER | For PDFs |
| metadata | JSONB | `{section_title, heading_level, etc.}` |
| token_count | INTEGER | Actual token count |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can access chunks from their documents (via `documents.user_id`).

---

### 6. workspaces

Multi-tenancy root. One per user/org.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | TEXT | Required |
| owner_id | UUID | FK → auth.users |
| owner_email | TEXT | For admin queries |
| subscription_status | TEXT | `free`, `pro` (default: free) |
| subscription_expires_at | TIMESTAMPTZ | Billing period end |
| lemonsqueezy_customer_id | TEXT | LS customer ID for portal |
| lemonsqueezy_subscription_id | TEXT | LS subscription ID |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto (trigger) |

**RLS:** Owner can manage own workspaces.

---

### 7. projects

User's work container.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | TEXT | Required |
| description | TEXT | Optional |
| workspace_id | UUID | FK → workspaces |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto (trigger) |

**RLS:** Users can manage projects in their workspaces.

---

### 8. work_tickets (Future - ADR-009)

Work request lifecycle. Currently exists but not actively used.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| task | TEXT | Work description |
| agent_type | TEXT | `research`, `content`, `reporting` |
| status | TEXT | `pending`, `running`, `completed`, `failed` |
| parameters | JSONB | Agent-specific params |
| error_message | TEXT | On failure |
| project_id | UUID | FK → projects |
| created_at | TIMESTAMPTZ | Auto |
| started_at | TIMESTAMPTZ | When agent started |
| completed_at | TIMESTAMPTZ | When agent finished |

**RLS:** Users can manage tickets in their projects.

---

### 9. work_outputs (Future - ADR-009)

Agent deliverables.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| title | TEXT | Output name |
| output_type | TEXT | `text`, `file` |
| content | TEXT | For text outputs |
| file_url | TEXT | For file outputs |
| file_format | TEXT | `pdf`, `pptx`, `docx`, etc |
| ticket_id | UUID | FK → work_tickets |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can view and create outputs for their tickets.

---

### 10. subscription_events

Audit log for Lemon Squeezy webhook events.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK → workspaces |
| event_type | TEXT | e.g., `subscription_created`, `subscription_updated` |
| event_source | TEXT | Default: `lemonsqueezy` |
| ls_subscription_id | TEXT | Lemon Squeezy subscription ID |
| ls_customer_id | TEXT | Lemon Squeezy customer ID |
| payload | JSONB | Full webhook payload |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can view their own subscription events.

---

### 11. scheduled_messages (Future - proactive features)

For scheduled/recurring message delivery.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| workspace_id | UUID | FK → workspaces |
| scheduled_for | TIMESTAMPTZ | When to send |
| message_type | TEXT | Type of message |
| subject | TEXT | Email subject |
| content | JSONB | Message content |
| recipient_email | TEXT | Delivery target |
| status | TEXT | `pending`, `sent`, `failed` |
| sent_at | TIMESTAMPTZ | When actually sent |
| failure_reason | TEXT | On failure |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can view their workspace messages.

---

### 12. email_delivery_log (Future - proactive features)

Audit log for email delivery.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| scheduled_message_id | UUID | FK → scheduled_messages |
| recipient | TEXT | Email address |
| subject | TEXT | Email subject |
| provider | TEXT | Default: `resend` |
| provider_message_id | TEXT | Provider's message ID |
| status | TEXT | Delivery status |
| status_updated_at | TIMESTAMPTZ | Last status update |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can view logs for their messages.

---

## Legacy Tables

### agent_sessions (Deprecated)

Originally for work ticket execution logs. Superseded by `chat_sessions` for TP conversations. May be repurposed for work agent execution logs when ADR-009 is implemented.

---

## Migrations

| File | Description | Status |
|------|-------------|--------|
| `001_initial_schema.sql` | Base tables | Applied |
| `002_fix_rls_policies.sql` | RLS fixes | Applied |
| `003_scheduling_tables.sql` | Scheduling tables (scheduled_messages, email_delivery_log) | Applied |
| `004_extend_blocks_for_extraction.sql` | Block extensions (superseded) | Applied |
| `005_user_context_layer.sql` | User context layer (superseded) | Applied |
| `006_unified_memory.sql` | ADR-005 unified memory | Applied |
| `007_search_memories_rpc.sql` | Semantic search RPCs | Applied |
| `008_chat_sessions.sql` | ADR-006 sessions | Applied |
| `009_document_pipeline.sql` | ADR-008 document storage | Applied |
| `010_subscription_fields.sql` | Lemon Squeezy subscription fields | Applied |
| `011_fix_chunks_rls.sql` | Fix chunks RLS for user-scoped docs | Applied |

---

## Key Design Decisions

### ADR-005: Unified Memory
1. Single `memories` table instead of separate user_context + blocks
2. Scope via nullable FK: `project_id IS NULL` = user-scoped, else project-scoped
3. Embeddings first-class: vector(1536) column with ivfflat index
4. Emergent structure: Tags and entities extracted by LLM, not enum categories
5. Soft-delete: `is_active` flag instead of hard delete

### ADR-006: Session Architecture
1. Normalized `chat_sessions` + `session_messages` tables
2. Direct `user_id` on sessions (not via project chain)
3. Daily session reuse via `get_or_create_chat_session` RPC
4. Global chat: `project_id IS NULL` on session

### ADR-008: Document Pipeline
1. Three-tier: documents → chunks → memories
2. Direct `user_id` on documents (RLS via ownership)
3. Processing status tracking for async pipeline

---

## Retrieval Patterns

### Semantic Search (Primary)

```sql
-- Find memories similar to a query
SELECT *,
       (1 - (embedding <=> $query_embedding)) * 0.7 + importance * 0.3 AS relevance
FROM memories
WHERE user_id = $user_id
  AND is_active = true
  AND (project_id IS NULL OR project_id = $project_id)
  AND embedding IS NOT NULL
ORDER BY relevance DESC
LIMIT 20;
```

### Session History

```sql
-- Get messages for a session
SELECT * FROM session_messages
WHERE session_id = $session_id
ORDER BY sequence_number;
```

### Document Chunk Retrieval

```sql
-- Find relevant chunks from a document
SELECT * FROM chunks
WHERE document_id = $document_id
ORDER BY (1 - (embedding <=> $query_embedding)) DESC
LIMIT 5;
```

---

## Extension Requirements

```sql
-- Required for embeddings
CREATE EXTENSION IF NOT EXISTS vector;
```
