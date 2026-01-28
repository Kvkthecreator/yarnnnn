# Database Schema

**Supabase Project**: `noxgqcwynkzqabljjyon`
**Tables**: 8 core tables
**RLS**: Enabled on all tables

---

## Entity Relationship

```
workspace 1──n project
project   1──n block
project   1──n document
project   1──n work_ticket
project   1──n agent_session
block     n──n block (via block_relation)
work_ticket 1──n work_output
work_ticket 1──1 agent_session
```

---

## Tables

### 1. workspaces

Multi-tenancy root. One per user/org.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, auto-generated |
| name | TEXT | Required |
| owner_id | UUID | FK → auth.users |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto (trigger) |

**RLS Policies**: Owner can SELECT, INSERT, UPDATE, DELETE own workspaces.

---

### 2. projects

User's work container. Contains context and work tickets.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | TEXT | Required |
| description | TEXT | Optional |
| workspace_id | UUID | FK → workspaces |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto (trigger) |

**RLS Policies**: Users can manage projects in their workspaces.

---

### 3. blocks

Atomic knowledge units. The core of context.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| content | TEXT | Required |
| block_type | TEXT | `text`, `structured`, `extracted` |
| metadata | JSONB | Flexible attributes |
| project_id | UUID | FK → projects |
| created_at | TIMESTAMPTZ | Auto |
| updated_at | TIMESTAMPTZ | Auto (trigger) |

**RLS Policies**: Users can manage blocks in their projects.

**Indexes**:
- `idx_blocks_project` (project_id)
- `idx_blocks_type` (block_type)

---

### 4. documents

Uploaded files (PDF, DOCX, etc). Parsed into blocks.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| filename | TEXT | Required |
| file_url | TEXT | Supabase Storage URL |
| file_type | TEXT | `pdf`, `docx`, `xlsx`, etc |
| file_size | INTEGER | Bytes |
| project_id | UUID | FK → projects |
| created_at | TIMESTAMPTZ | Auto |

**RLS Policies**: Users can manage documents in their projects.

---

### 5. block_relations

Semantic links between blocks.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| source_id | UUID | FK → blocks |
| target_id | UUID | FK → blocks |
| relation_type | TEXT | `supports`, `contradicts`, `extends`, `references` |
| created_at | TIMESTAMPTZ | Auto |

**Constraints**: UNIQUE (source_id, target_id, relation_type)

**RLS Policies**: Users can manage relations for their blocks.

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

**RLS Policies**: Users can manage tickets in their projects.

**Indexes**:
- `idx_tickets_project` (project_id)
- `idx_tickets_status` (status)

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

**RLS Policies**: Users can view and create outputs for their tickets.

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
| project_id | UUID | FK → projects |
| created_at | TIMESTAMPTZ | Auto |
| completed_at | TIMESTAMPTZ | When session ended |

**RLS Policies**: Users can view and create sessions in their projects.

---

## Migrations

| File | Description | Applied |
|------|-------------|---------|
| `001_initial_schema.sql` | 8 tables, base RLS | Yes |
| `002_fix_rls_policies.sql` | Missing policies, GRANTs | Yes |

---

## Future Columns (When Needed)

As per [ADR-001](../adr/ADR-001-memory-simplicity.md), these may be added later:

```sql
-- blocks table
ALTER TABLE blocks ADD COLUMN importance_score FLOAT DEFAULT 0.5;
ALTER TABLE blocks ADD COLUMN expires_at TIMESTAMPTZ;
ALTER TABLE blocks ADD COLUMN embedding vector(1536);
```
