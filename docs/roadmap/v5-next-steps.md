# YARNNN v5 Roadmap

**Date:** 2026-01-29
**Current Phase:** Architecture Pivot (ADR-005)
**Status:** Phases 1-2 complete, pivoting to unified memory model

---

## Architecture Evolution

### What Changed

ADR-004 (Two-Layer Memory) implemented rigid categorical taxonomies:
- 7 user context categories (preference, business_fact, etc.)
- 6 project block types (requirement, fact, guideline, etc.)

**Problem discovered:** Categories were extracted and stored but **never used for retrieval**. They served only as UI decoration. Research showed this pattern fails at scale.

**ADR-005 (Unified Memory)** replaces this with:
- Single `memories` table with embeddings for semantic retrieval
- Scope via nullable `project_id` (NULL = user, non-NULL = project)
- Emergent structure via tags/entities (not forced categories)
- Document pipeline: documents → chunks → memories

---

## Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Dashboard transformation, global chat |
| Phase 2 | ✅ Complete | User context panel (will be rebuilt for new model) |
| **Phase 2.5** | 🔄 **Current** | **Architecture pivot: ADR-005 implementation** |
| Phase 3 | 🔲 Blocked | Work Agents (depends on new memory model) |
| Phase 4 | 🔲 Planned | Document upload + external imports |
| Phase 5 | 🔲 Future | Proactive features |

---

## Phase 2.5: Architecture Pivot (Current)

### Goal
Implement ADR-005 unified memory architecture with embeddings.

### Database Migration

- [ ] Enable pgvector extension in Supabase
- [ ] Write `006_unified_memory.sql` migration
  - [ ] Drop deprecated tables (user_context, blocks, block_relations)
  - [ ] Create `memories` table with embedding column
  - [ ] Create `chunks` table for document segments
  - [ ] Extend `documents` table with processing columns
  - [ ] Set up RLS policies
  - [ ] Create indexes (including ivfflat for vectors)

### Backend Changes

- [ ] Add embedding service (`api/services/embeddings.py`)
  - [ ] OpenAI ada-002 integration (or alternative)
  - [ ] Batch embedding for efficiency
- [ ] Rewrite extraction service (`api/services/extraction.py`)
  - [ ] Remove forced category extraction
  - [ ] Implement emergent tag/entity extraction
  - [ ] Scope classification (user vs project)
  - [ ] Generate embeddings on extraction
- [ ] Update memory retrieval (`api/services/memory.py`)
  - [ ] Semantic search with vector similarity
  - [ ] Hybrid scoring (similarity + importance)
  - [ ] Scope-aware retrieval
- [ ] Update ThinkingPartner context assembly
  - [ ] Query-based retrieval (not fetch-all)
  - [ ] Format memories for LLM consumption
- [ ] Update chat routes for new retrieval pattern

### Frontend Changes

- [ ] Update "About You" panel for new data model
  - [ ] Display tags instead of categories
  - [ ] Show entities
- [ ] Update project context view
- [ ] Memory management UI (edit, soft-delete)

### Document Pipeline (Foundation)

- [ ] Document upload endpoint
- [ ] Basic parsing (PDF, DOCX)
- [ ] Semantic chunking (~400 tokens)
- [ ] Chunk storage with embeddings
- [ ] Memory extraction from chunks

---

## Phase 3: Work Agents (Next)

**Blocked on:** Phase 2.5 completion

### Goal
Activate work agents that leverage the new memory architecture.

### Tasks

- [ ] Uncomment work/agents routes in main.py
- [ ] Update agents to use semantic memory retrieval
- [ ] Research agent: query memories for facts
- [ ] Content agent: query memories for style/guidelines
- [ ] Reporting agent: aggregate memories into outputs
- [ ] Work ticket UI in dashboard

---

## Phase 4: External Context

### Goal
Ingest context from external sources.

### Tasks

- [ ] Full document processing pipeline
  - [ ] PDF parsing with page tracking
  - [ ] DOCX/DOC parsing
  - [ ] Image OCR (optional)
- [ ] Conversation imports
  - [ ] Claude export format
  - [ ] ChatGPT export format
  - [ ] Parse → chunk → extract memories
- [ ] MCP integrations (future)
  - [ ] Notion connector
  - [ ] Linear connector

---

## Phase 5: Proactive Features

### Goal
YARNNN reaches out to users.

### Tasks

- [ ] Weekly digest emails (Render cron + Resend)
- [ ] Stale memory detection
- [ ] Memory consolidation/summarization

---

## Technical Architecture (Post-ADR-005)

### Data Flow

```
Input Sources                Processing              Storage
─────────────               ──────────              ───────

Chat ────────────┐
                 │
Document ────────┼──→ LLM Extraction ──→ Memories (+ embeddings)
                 │    - content
Manual ──────────┤    - tags (emergent)
                 │    - entities
Import ──────────┘    - importance
                      - scope (user/project)



Query ──→ Embedding ──→ Vector Search ──→ Relevant Memories
                        + importance weighting
```

### Retrieval Pattern

```python
# Semantic search with hybrid scoring
async def get_relevant_memories(user_id, project_id, query):
    query_embedding = await get_embedding(query)

    return await db.query("""
        SELECT *,
               (1 - (embedding <=> $1)) * 0.7 + importance * 0.3 AS relevance
        FROM memories
        WHERE user_id = $2
          AND is_active = true
          AND (project_id IS NULL OR project_id = $3)
        ORDER BY relevance DESC
        LIMIT 20
    """, query_embedding, user_id, project_id)
```

---

## Key Files to Modify

| File | Changes |
|------|---------|
| `supabase/migrations/006_unified_memory.sql` | New migration |
| `api/services/extraction.py` | Complete rewrite |
| `api/services/embeddings.py` | New file |
| `api/services/memory.py` | New file (retrieval) |
| `api/agents/thinking_partner.py` | Update context assembly |
| `api/routes/chat.py` | Update retrieval calls |
| `api/routes/context.py` | Update for memories table |
| `web/components/UserContextPanel.tsx` | Adapt for new model |

---

## References

- [ADR-005: Unified Memory with Embeddings](../adr/ADR-005-unified-memory-with-embeddings.md)
- [Database Schema](../database/SCHEMA.md)
- [ADR-004: Two-Layer Memory](../adr/ADR-004-two-layer-memory-architecture.md) (superseded)
