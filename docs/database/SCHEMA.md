# Database Schema

**Supabase Project**: `noxgqcwynkzqabljjyon`
**Architecture**: ADR-005 Unified Memory with Embeddings
**Extensions**: pgvector (for embeddings)

---

## Entity Relationship

```
user      1──n memories      (unified memory: user + project scoped)
project   1──n memories      (project-scoped memories)
project   1──n documents
document  1──n chunks        (semantic segments with embeddings)
project   1──n work_tickets
work_ticket 1──n work_outputs
project   1──n agent_sessions
```

---

## Core Tables

### 1. memories

Unified memory storage. Replaces the previous `user_context` and `blocks` tables.

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

**Indexes:**
- `idx_memories_user` (user_id) WHERE is_active
- `idx_memories_project` (project_id) WHERE is_active
- `idx_memories_importance` (importance DESC) WHERE is_active
- `idx_memories_tags` GIN(tags) WHERE is_active
- `idx_memories_embedding` ivfflat(embedding) WHERE is_active AND embedding IS NOT NULL

**RLS:** Users can only manage their own memories.

---

### 2. documents

Uploaded files (PDF, DOCX, etc). Parsed into chunks.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| filename | TEXT | Required |
| file_url | TEXT | Supabase Storage URL |
| file_type | TEXT | `pdf`, `docx`, `xlsx`, etc |
| file_size | INTEGER | Bytes |
| project_id | UUID | FK → projects |
| processing_status | TEXT | `pending`, `processing`, `completed`, `failed` |
| processed_at | TIMESTAMPTZ | When processing completed |
| error_message | TEXT | On failure |
| page_count | INTEGER | For PDFs |
| word_count | INTEGER | Approximate |
| created_at | TIMESTAMPTZ | Auto |

**RLS:** Users can manage documents in their projects.

---

### 3. chunks

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

**Indexes:**
- `idx_chunks_document` (document_id)
- `idx_chunks_order` (document_id, chunk_index)
- `idx_chunks_embedding` ivfflat(embedding) WHERE embedding IS NOT NULL

**RLS:** Inherits from documents via project ownership.

---

### 4. workspaces

Multi-tenancy root. One per user/org.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | TEXT | Required |
| owner_id | UUID | FK → auth.users |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto (trigger) |

**RLS:** Owner can manage own workspaces.

---

### 5. projects

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

### 6. work_tickets

Work request lifecycle.

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

**Indexes:**
- `idx_tickets_project` (project_id)
- `idx_tickets_status` (status)

**RLS:** Users can manage tickets in their projects.

---

### 7. work_outputs

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

### 8. agent_sessions

Execution logs for provenance.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| agent_type | TEXT | Which agent ran |
| messages | JSONB | Full conversation history |
| metadata | JSONB | Model, tokens, timing |
| ticket_id | UUID | FK → work_tickets (nullable) |
| project_id | UUID | FK → projects (nullable for global chat) |
| user_id | UUID | FK → auth.users |
| created_at | TIMESTAMPTZ | Auto |
| completed_at | TIMESTAMPTZ | When session ended |

**RLS:** Users can view and create sessions.

---

## Migrations

| File | Description | Status |
|------|-------------|--------|
| `001_initial_schema.sql` | Base tables | Applied |
| `002_fix_rls_policies.sql` | RLS fixes | Applied |
| `003_user_context.sql` | ADR-004 user_context (superseded) | Applied |
| `004_extend_blocks_for_extraction.sql` | Block extensions (superseded) | Applied |
| `005_user_context_layer.sql` | User context layer (superseded) | Applied |
| `006_unified_memory.sql` | ADR-005 unified memory | **Pending** |

---

## Deprecated Tables (Removed in 006)

These tables are removed by ADR-005:

- `user_context` → Replaced by `memories` with `project_id IS NULL`
- `blocks` → Replaced by `memories` with `project_id IS NOT NULL`
- `block_relations` → Deferred; entity relationships stored in `memories.entities`
- `extraction_logs` → Simplified; tracking via `memories.source_ref`

---

## Key Design Decisions (ADR-005)

1. **Unified table**: Single `memories` table instead of separate user_context + blocks
2. **Scope via nullable FK**: `project_id IS NULL` = user-scoped, else project-scoped
3. **Embeddings first-class**: vector(1536) column with ivfflat index for semantic search
4. **Emergent structure**: Tags and entities extracted by LLM, not forced into enum categories
5. **Soft-delete**: `is_active` flag instead of hard delete for auditability
6. **Document pipeline**: documents → chunks → memories (three-tier)

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

### Tag-Based Filtering

```sql
-- Find memories with specific tags
SELECT * FROM memories
WHERE user_id = $user_id
  AND is_active = true
  AND tags @> ARRAY['client', 'deadline']
ORDER BY importance DESC;
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
