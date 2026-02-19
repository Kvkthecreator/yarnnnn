# ADR-008: Document Pipeline Architecture

**Status:** Accepted (Implemented)
**Date:** 2026-01-29
**Authors:** [AI-assisted]

## Context

YARNNN's memory system (ADR-005) supports semantic retrieval but currently only ingests context from chat conversations. Users need to load context from existing documents (PDFs, DOCX files) to avoid "cold starts" where the Thinking Partner has no knowledge of their work.

The document pipeline must:
1. Accept file uploads and store them securely
2. Parse documents into text
3. Chunk text into semantic segments for retrieval
4. Extract memories (facts, insights) from chunks
5. Support future work outputs (agents generating files)

### Existing Infrastructure

| Component | Status | Notes |
|-----------|--------|-------|
| `documents` table | ✅ Extended | Added `user_id`, `storage_path`, nullable `project_id` |
| `chunks` table | ✅ Exists | With embeddings, pgvector index |
| `match_chunks()` RPC | ✅ Exists | Semantic search on chunks |
| `memories` table | ✅ Exists | ADR-005, with `source_type='document'` |
| Storage bucket | ✅ Created | `documents` bucket with RLS |
| Document routes | ✅ Created | `api/routes/documents.py` |
| Parsing service | ✅ Exists | `api/services/documents.py` |

## Decision

### 1. Storage Architecture

**Supabase Storage bucket:** `documents`

```
documents/
├── {user_id}/
│   └── {document_id}/
│       └── original.{ext}    # Raw uploaded file
```

**Bucket policies:**
- Private bucket (not public)
- RLS: Users can only access files in their `{user_id}/` prefix
- Max file size: 25MB (covers most business documents)
- Allowed MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`, `text/markdown`

### 2. Schema Changes

**Extend `documents` table:**

```sql
ALTER TABLE documents ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE documents ADD COLUMN storage_path TEXT;  -- Bucket path
ALTER TABLE documents ALTER COLUMN project_id DROP NOT NULL;  -- Allow user-scoped docs
```

**Rationale:**
- `user_id`: Direct ownership for RLS (currently only via project → workspace chain)
- `storage_path`: Explicit bucket path instead of full URL
- Nullable `project_id`: Documents can be user-scoped (available to all projects) or project-scoped

### 3. Processing Pipeline

```
Upload → Store → Parse → Chunk → Embed → Extract Memories
```

**Stage 1: Upload & Store**
- Accept multipart file upload
- Validate file type and size
- Generate `document_id`
- Store in bucket at `{user_id}/{document_id}/original.{ext}`
- Create `documents` row with `processing_status='pending'`

**Stage 2: Parse**
- PDF: `pypdf` or `pdfplumber` (extract text, preserve page numbers)
- DOCX: `python-docx` (extract text, preserve structure)
- TXT/MD: Direct read
- Update `documents.page_count`, `documents.word_count`

**Stage 3: Chunk**
- Target: ~400 tokens per chunk (semantic boundaries)
- Overlap: 50 tokens between chunks (context preservation)
- Track: `chunk_index`, `page_number`, `metadata.section_title`
- Insert into `chunks` table

**Stage 4: Embed**
- Use existing `embeddings.py` service (`text-embedding-3-small`)
- Batch embed chunks (max 20 per batch for rate limits)
- Update `chunks.embedding`

**Stage 5: Extract Memories**
- ~~Use existing `extraction.py` service~~ → `extraction.py` deleted (ADR-064). Memory Service (`api/services/memory.py`) handles extraction at session end.
- Process chunks in groups (3-5 chunks for context)
- Extract memories with `source_type='document'`, `source_ref={document_id, chunk_ids}`
- Embed and store memories

**Stage 6: Complete**
- Update `documents.processing_status='completed'`
- Update `documents.processed_at`

### 4. API Endpoints

```
POST   /api/documents/upload
       - Multipart file upload
       - Optional: project_id (null = user-scoped)
       - Returns: document_id, status

GET    /api/documents
       - List user's documents
       - Filter: project_id, status

GET    /api/documents/{id}
       - Document details + chunk count + memory count

GET    /api/documents/{id}/download
       - Signed URL for original file

DELETE /api/documents/{id}
       - Soft delete (cascade to chunks, memories)
```

### 5. Processing Strategy

**Synchronous (MVP):**
- Process immediately after upload
- Simple, no queue infrastructure
- Risk: Timeout on large documents

**Background (Future):**
- Return immediately after upload
- Process via Render cron job or background task
- Poll status or use webhooks

**Decision: Start synchronous**, with 60-second timeout. Move to background processing if needed.

### 6. Work Outputs Integration

Work outputs (from agents) use same storage pattern:

```
outputs/
├── {user_id}/
│   └── {output_id}/
│       └── {filename}.{ext}
```

Reuse `work_outputs` table with `storage_path` column (needs migration).

### 7. Frontend Integration (Deferred)

This ADR intentionally defers frontend decisions. Options to explore:

- **Upload in chat**: "Drop a file here" in TP chat
- **Context panel**: Dedicated upload area in user context panel
- **Project view**: Document list per project
- **Dashboard**: Global upload for onboarding

The backend supports all patterns via the API.

## Consequences

### Positive

- Users can load context from existing work (avoid cold start)
- Semantic search across documents via `match_chunks()`
- Extracted memories persist and improve TP responses over time
- Foundation for work outputs (agents generating files)
- User-scoped documents available across projects

### Negative

- Storage costs (Supabase Storage pricing)
- Processing time for large documents (may need background jobs)
- Embedding costs (OpenAI API calls)
- Complexity: three-tier pipeline (doc → chunks → memories)

### Neutral

- Documents always project-scoped OR user-scoped (not both)
- Chunks are intermediate (not directly exposed to users)
- Memory extraction is best-effort (LLM may miss things)

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Store text only (no files) | Simpler, no storage | Lose original, no re-processing | Users expect to download originals |
| External storage (S3) | More control | Extra infra, cross-service auth | Supabase Storage is sufficient for MVP |
| Real-time streaming parse | Faster feedback | Complex, partial failures | YAGNI for MVP |
| Per-chunk memory extraction | More granular | More LLM calls, noise | Group chunks for better context |

## Implementation Checklist

### Phase 1: Storage & Schema
- [x] Create `documents` Supabase Storage bucket
- [x] Configure bucket RLS policies
- [x] Migration: Add `user_id`, `storage_path` to `documents`
- [x] Migration: Add `storage_path` to `work_outputs`

### Phase 2: Upload & Parse
- [x] Create `api/services/documents.py` service
- [x] Implement PDF parsing (`pypdf`)
- [x] Implement DOCX parsing (`python-docx`)
- [x] Create `api/routes/documents.py` endpoints

### Phase 3: Chunk & Embed
- [x] Implement semantic chunking (~400 tokens)
- [x] Batch embedding with existing service
- [x] Insert chunks with embeddings

### Phase 4: Memory Extraction
- [x] Group chunks for extraction context
- [x] ~~Use existing `extraction.py` service~~ → deleted (ADR-064); memory.py handles extraction
- [x] Link memories to document via `source_ref`

### Phase 5: Polish
- [x] Error handling and retry logic
- [x] Processing status updates
- [x] Download endpoint with signed URLs
- [x] Delete cascade (chunks, memories)

### Implementation Files
- `supabase/migrations/009_document_pipeline.sql` - Schema + bucket + RLS
- `api/services/documents.py` - Processing pipeline (text extraction, chunking, embedding)
- `api/routes/documents.py` - API endpoints (upload, list, get, download, delete)
- `api/main.py` - Router registration

## References

- [ADR-005: Unified Memory with Embeddings](ADR-005-unified-memory-with-embeddings.md)
- [Database Schema](../database/SCHEMA.md)
- [Supabase Storage Docs](https://supabase.com/docs/guides/storage)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
