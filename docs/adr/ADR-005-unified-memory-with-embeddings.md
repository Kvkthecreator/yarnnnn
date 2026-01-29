# ADR-005: Unified Memory Architecture with Embeddings

**Status:** Accepted
**Date:** 2026-01-29
**Supersedes:** ADR-004 (Two-Layer Memory Architecture)
**Decision Makers:** Kevin Kim

## Context

ADR-004 implemented a two-layer memory architecture with rigid categorical taxonomies:
- **User context**: 7 predefined categories (preference, business_fact, work_pattern, etc.)
- **Project blocks**: 6 predefined semantic types (requirement, fact, guideline, etc.)

Upon analysis, we discovered these categories are **extracted and stored but not functionally used for retrieval**. They serve only as UI decoration for grouping display. The extraction prompts force classification into buckets, but retrieval ignores them entirely.

Research into industry benchmarks (Mem0, LangMem, Zep) and academic literature (H-MEM, MemTree, MemOS) reveals:

1. **Flat/rigid taxonomies fail at scale** - predefined categories can't capture emergent structure
2. **Vector embeddings are essential** - semantic retrieval beats categorical filtering
3. **Structure should emerge from data** - tags and entities extracted, not forced into enums
4. **Documents need a proper pipeline** - raw → chunks → derived memories

The current architecture also lacks document handling, which is the next priority feature.

## Decision

Replace the rigid two-table categorical model with a **unified memory architecture**:

1. **Single `memories` table** with embeddings for semantic retrieval
2. **Scope via nullable `project_id`** (NULL = user-scoped, non-NULL = project-scoped)
3. **Emergent structure** via extracted tags and entities (not forced categories)
4. **Documents pipeline**: documents → chunks → memories
5. **Immutable with soft-delete** for auditability

### Executive Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Embeddings** | Yes, first-class | Research consensus: vectors essential for retrieval at scale |
| **Categories** | Removed (replaced with tags) | Were decoration, not functional; emergent structure preferred |
| **User/Project scope** | Keep via nullable project_id | Solves real problem (portable vs task-specific knowledge) |
| **Immutability** | Soft-delete, append-preferred | Enables audit trail, versioning; simpler than update-in-place |
| **Chunks table** | Separate from memories | Documents need positional/structural metadata; memories are derived facts |
| **Graph layer** | Deferred (entities in JSONB) | Overkill for now; JSONB gives 80% of value without Neo4j |

## Schema

### Core Tables

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- MEMORIES: Unified memory storage (replaces user_context + blocks)
-- =============================================================================
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,  -- NULL = user-scoped

    -- Content
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 or equivalent

    -- Emergent structure (not forced categories)
    tags TEXT[] DEFAULT '{}',           -- LLM-extracted or user-added
    entities JSONB DEFAULT '{}',        -- {people: [], companies: [], concepts: []}

    -- Retrieval signals
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),

    -- Provenance
    source_type TEXT NOT NULL,          -- 'chat', 'document', 'manual', 'import'
    source_ref JSONB,                   -- {session_id, chunk_id, document_id, etc.}

    -- Lifecycle (soft-delete pattern)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for retrieval
CREATE INDEX idx_memories_user ON memories(user_id) WHERE is_active = true;
CREATE INDEX idx_memories_project ON memories(project_id) WHERE is_active = true;
CREATE INDEX idx_memories_importance ON memories(importance DESC) WHERE is_active = true;
CREATE INDEX idx_memories_tags ON memories USING gin(tags) WHERE is_active = true;
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100) WHERE is_active = true AND embedding IS NOT NULL;

-- RLS
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own memories"
    ON memories FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());


-- =============================================================================
-- DOCUMENTS: Raw file storage (existing table, extended)
-- =============================================================================
-- documents table already exists with: id, filename, file_url, file_type, file_size, project_id
-- Add processing status columns:
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending';
    -- pending, processing, completed, failed
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS word_count INTEGER;


-- =============================================================================
-- CHUNKS: Document segments for retrieval
-- =============================================================================
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    embedding vector(1536),

    -- Position in document
    chunk_index INTEGER NOT NULL,       -- 0-based order
    page_number INTEGER,                -- For PDFs

    -- Metadata
    metadata JSONB DEFAULT '{}',        -- {section_title, heading_level, etc.}
    token_count INTEGER,

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_order ON chunks(document_id, chunk_index);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100) WHERE embedding IS NOT NULL;

-- RLS (inherits from documents via project)
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access chunks from their documents"
    ON chunks FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            JOIN projects p ON d.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE d.id = chunks.document_id
            AND w.owner_id = auth.uid()
        )
    );
```

### Migration Strategy

Since there's no production data, we'll do a clean replacement:

```sql
-- Migration: 006_unified_memory.sql

-- 1. Drop old tables (no data to preserve)
DROP TABLE IF EXISTS user_context CASCADE;
DROP TABLE IF EXISTS blocks CASCADE;
DROP TABLE IF EXISTS block_relations CASCADE;
DROP TABLE IF EXISTS extraction_logs CASCADE;

-- 2. Create new schema (as above)
-- ... memories, chunks tables ...

-- 3. Clean up documents table columns if needed
-- ... ALTER statements ...
```

## Data Flow

### Memory Creation Pipeline

```
                    ┌─────────────────┐
                    │   Raw Input     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐        ┌───────────┐        ┌──────────┐
   │  Chat   │        │ Document  │        │  Manual  │
   └────┬────┘        └─────┬─────┘        └────┬─────┘
        │                   │                   │
        │                   ▼                   │
        │            ┌───────────┐              │
        │            │  Chunks   │              │
        │            │ (stored)  │              │
        │            └─────┬─────┘              │
        │                  │                    │
        ▼                  ▼                    ▼
   ┌─────────────────────────────────────────────────┐
   │              LLM Extraction                      │
   │  - Extract facts/insights                        │
   │  - Generate tags (emergent)                      │
   │  - Extract entities (people, companies, etc.)   │
   │  - Score importance                              │
   │  - Determine scope (user vs project)            │
   └─────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Memories     │
                    │ + embeddings    │
                    └─────────────────┘
```

### Memory Retrieval Pipeline

```python
async def get_relevant_memories(
    user_id: str,
    project_id: str | None,
    query: str,
    max_results: int = 20
) -> list[Memory]:
    """
    Hybrid retrieval: semantic similarity + importance weighting.

    1. Get query embedding
    2. Vector search for semantically similar memories
    3. Boost by importance score
    4. Include user-scoped memories + project-scoped (if project_id)
    """
    query_embedding = await get_embedding(query)

    # Scope: always user memories, optionally project memories
    scope_filter = "project_id IS NULL"  # user-scoped
    if project_id:
        scope_filter = f"(project_id IS NULL OR project_id = '{project_id}')"

    # Hybrid search: vector similarity + importance
    results = await db.execute(f"""
        SELECT *,
               (1 - (embedding <=> $1)) * 0.7 + importance * 0.3 AS relevance
        FROM memories
        WHERE user_id = $2
          AND is_active = true
          AND {scope_filter}
          AND embedding IS NOT NULL
        ORDER BY relevance DESC
        LIMIT $3
    """, query_embedding, user_id, max_results)

    return results
```

## Extraction Logic

### Emergent Structure Extraction

Replace the forced-category prompt with emergent extraction:

```python
EXTRACTION_PROMPT = """Analyze this content and extract distinct memories.

For each memory:
1. content: The specific fact, insight, preference, or information
2. scope: "user" (true across all projects) or "project" (specific to this work)
3. tags: 2-5 descriptive tags (lowercase, no spaces)
4. entities: People, companies, concepts mentioned
5. importance: 0.0-1.0 (how critical is this information?)

Examples of SCOPE classification:
- "Prefers bullet points" → user (style preference, applies everywhere)
- "Report due Tuesday" → project (specific deadline for this work)
- "Works at Acme Corp" → user (fact about the person)
- "Client wants 3 sections" → project (requirement for this deliverable)

Return JSON:
{
  "memories": [
    {
      "content": "...",
      "scope": "user" | "project",
      "tags": ["tag1", "tag2"],
      "entities": {"people": [], "companies": [], "concepts": []},
      "importance": 0.7
    }
  ]
}
"""
```

### Document Processing Pipeline

```python
async def process_document(document_id: str) -> None:
    """
    Document → Chunks → Memories pipeline.
    """
    # 1. Parse document
    doc = await get_document(document_id)
    text = await parse_document(doc.file_url, doc.file_type)  # PDF, DOCX, etc.

    # 2. Semantic chunking (~400 tokens, 10% overlap)
    chunks = semantic_chunk(text, target_tokens=400, overlap=0.1)

    # 3. Store chunks with embeddings
    for i, chunk_text in enumerate(chunks):
        embedding = await get_embedding(chunk_text)
        await create_chunk(
            document_id=document_id,
            content=chunk_text,
            embedding=embedding,
            chunk_index=i
        )

    # 4. Extract memories from chunks
    for chunk in chunks:
        memories = await extract_memories(chunk.content, source_type='document')
        for mem in memories:
            mem.source_ref = {'document_id': document_id, 'chunk_id': chunk.id}
            await create_memory(mem)

    # 5. Mark document complete
    await update_document(document_id, processing_status='completed')
```

## Scope Logic

The user/project scope distinction from ADR-004 is preserved, but simplified:

| project_id | Scope | Meaning |
|------------|-------|---------|
| NULL | User | Portable knowledge, applies across all projects |
| UUID | Project | Task-specific, isolated to this project |

**Retrieval behavior:**
- Global chat (no project): Only user-scoped memories
- Project chat: User-scoped + project-scoped memories
- Work agents: Primarily project-scoped, optionally user-scoped for style

## Consequences

### Positive
- **Semantic retrieval** actually works (vectors, not ignored categories)
- **Flexible structure** accommodates unexpected content types
- **Document pipeline** enables richer context
- **Simpler extraction** (no forced classification into 7+6 buckets)
- **Clean slate** (no migration complexity with zero users)
- **Future-proof** (embeddings enable similarity search, clustering, etc.)

### Negative
- **pgvector dependency** (requires Supabase pgvector extension)
- **Embedding costs** (API calls for each memory/chunk)
- **Index maintenance** (ivfflat indexes need occasional rebuilding)
- **More complex retrieval** (hybrid scoring vs simple SELECT)

### Risks
- **Embedding quality** affects retrieval quality
- **Tag extraction** may be inconsistent without constraints
- **Scope classification** may be less accurate without explicit categories

### Mitigations
- Use proven embedding model (OpenAI ada-002 or equivalent)
- Tune extraction prompt with examples for consistent tagging
- Allow user to manually adjust scope if misclassified
- Monitor retrieval quality and adjust scoring weights

## Migration Checklist

- [x] Enable pgvector extension in Supabase
- [x] Create migration `006_unified_memory.sql`
- [x] Drop old tables (user_context, blocks, block_relations)
- [x] Create new tables (memories, chunks)
- [x] Extend documents table
- [x] Update extraction service for emergent extraction
- [x] Add embedding generation service (`api/services/embeddings.py`)
- [x] Add semantic search RPC (`007_search_memories_rpc.sql`)
- [x] Update ThinkingPartner context assembly
- [x] Update chat routes for semantic retrieval
- [ ] Add document upload + processing endpoint (Phase 4)
- [ ] Update frontend components (partial - context panel needs refresh)

## References

- [ADR-004: Two-Layer Memory Architecture](ADR-004-two-layer-memory-architecture.md) (superseded)
- [Mem0 Architecture](https://docs.mem0.ai/platform/overview)
- [LangMem SDK](https://github.com/langchain-ai/langmem)
- [RAG Chunking Best Practices 2025](https://weaviate.io/blog/chunking-strategies-for-rag)
- [H-MEM: Hierarchical Memory](https://arxiv.org/pdf/2507.22925)
- [Serokell: Design Patterns for Long-Term Memory](https://serokell.io/blog/design-patterns-for-long-term-memory-in-llm-powered-architectures)
