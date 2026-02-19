# YARNNN v5 Roadmap

**Date:** 2026-01-30
**Current Phase:** Architecture Refinement + Work Agents
**Status:** Core complete, expanding TP architecture and work orchestration

---

## Architecture Summary

| ADR | Status | Description |
|-----|--------|-------------|
| ADR-005 | ✅ Implemented | Unified Memory with Embeddings |
| ADR-006 | ✅ Implemented | Session and Message Architecture |
| ADR-007 | ✅ Implemented | Thinking Partner Project Authority (Tools) |
| ADR-008 | ✅ Implemented | Document Pipeline Architecture |
| ADR-009 | 📝 Draft | Work and Agent Orchestration |
| ADR-010 | 📝 Draft | Thinking Partner as Primary Interface |
| ADR-011 | 📝 Draft | Frontend Navigation Architecture |

### What's Built

**Memory System (ADR-005):**
- Single `memories` table with pgvector embeddings
- Semantic search via `search_memories()` RPC
- Hybrid scoring (70% similarity + 30% importance)
- Emergent structure (tags/entities, not forced categories)
- Automatic extraction from chat conversations

**Session System (ADR-006):**
- Normalized `chat_sessions` + `session_messages` tables
- Daily session reuse (one session per project per day)
- Global chat support (no project required)
- RPC functions for session management

**Thinking Partner Tools (ADR-007):**
- `list_projects`, `create_project`, `rename_project`, `update_project`
- Streaming with inline tool use
- Frontend handles tool events, auto-refreshes sidebar

---

## Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Dashboard transformation, global chat |
| Phase 2 | ✅ Complete | User context panel |
| Phase 2.5 | ✅ Complete | Architecture pivot (ADR-005/006/007) |
| Phase 3 | ✅ Complete | Work Agents skeleton, deferred for Document Pipeline |
| **Phase 4** | ✅ **Complete** | **Document Pipeline (ADR-008)** |
| Phase 5 | 🔲 Planned | Frontend integration, onboarding UX |
| Phase 6 | 🔲 Future | Proactive features |

---

## Phase 3: Work Agents (Current)

### Goal
Activate work agents that leverage the semantic memory architecture.

### Tasks

- [ ] Enable work/agents routes in main.py
- [ ] Research Agent
  - [ ] Query memories semantically for facts
  - [ ] Produce research summaries
- [ ] Content Agent
  - [ ] Query memories for style/voice preferences
  - [ ] Generate content drafts
- [ ] Reporting Agent
  - [ ] Aggregate memories into structured outputs
  - [ ] Generate PPTX/PDF reports
- [ ] Work Ticket UI
  - [ ] Create work ticket from dashboard
  - [ ] View ticket status and outputs
  - [ ] Download generated files

### Key Files

| File | Status | Purpose |
|------|--------|---------|
| `api/routes/work.py` | Exists (commented) | Work ticket endpoints |
| `api/routes/agents.py` | Exists (commented) | Agent execution endpoints |
| `api/agents/research.py` | To implement | Research agent |
| `api/agents/content.py` | To implement | Content agent |
| `api/agents/reporting.py` | To implement | Reporting agent |

---

## Phase 4: Document Pipeline (ADR-008) ✅ Complete

### Goal
Ingest context from documents to avoid cold starts.

### Completed

- [x] Document processing pipeline
  - [x] Storage bucket with RLS (`documents` bucket)
  - [x] PDF parsing with `pypdf`
  - [x] DOCX parsing with `python-docx`
  - [x] Semantic chunking (~400 tokens)
  - [x] Chunk storage with embeddings
  - [x] Memory extraction from chunks
- [x] API endpoints (`api/routes/documents.py`)
  - [x] `POST /api/documents/upload` - Upload and process
  - [x] `GET /api/documents` - List documents
  - [x] `GET /api/documents/{id}` - Get with stats
  - [x] `GET /api/documents/{id}/download` - Signed URL
  - [x] `DELETE /api/documents/{id}` - Delete with cascade

### Pending (Future)
- [ ] Conversation imports (Claude, ChatGPT export formats)
- [ ] MCP integrations (Notion, Linear)

---

## Phase 5: Frontend Integration

### Goal
Surface document upload in the user experience.

### Tasks

- [ ] Upload integration (options to explore):
  - [ ] Chat interface ("drop a file")
  - [ ] Context panel
  - [ ] Dashboard for onboarding
- [ ] Document management UI
- [ ] Progress indicators for processing

---

## Phase 6: Proactive Features

### Goal
YARNNN reaches out to users.

### Tasks

- [ ] Weekly digest emails (Render cron + Resend)
- [ ] Stale memory detection
- [ ] Memory consolidation/summarization

---

## Technical Architecture

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

### Key Services

| Service | File | Purpose |
|---------|------|---------|
| Embeddings | `api/services/embeddings.py` | OpenAI text-embedding-3-small |
| Memory Service | `api/services/memory.py` | Implicit memory extraction at pipeline boundaries (ADR-064; replaced `extraction.py`) |
| Anthropic | `api/services/anthropic.py` | Streaming + tools |
| Project Tools | `api/services/project_tools.py` | TP project management |
| Documents | `api/services/documents.py` | PDF/DOCX parsing, chunking |

---

## References

- [ADR-005: Unified Memory with Embeddings](../adr/ADR-005-unified-memory-with-embeddings.md)
- [ADR-006: Session and Message Architecture](../adr/ADR-006-session-message-architecture.md)
- [ADR-007: Thinking Partner Project Authority](../adr/ADR-007-thinking-partner-project-authority.md)
- [ADR-008: Document Pipeline Architecture](../adr/ADR-008-document-pipeline.md)
- [ADR-009: Work and Agent Orchestration](../adr/ADR-009-work-agent-orchestration.md)
- [ADR-010: Thinking Partner Architecture](../adr/ADR-010-thinking-partner-architecture.md)
- [ADR-010: Stress Tests](../adr/ADR-010-stress-tests.md)
- [ADR-011: Frontend Navigation Architecture](../adr/ADR-011-frontend-navigation-architecture.md)
- [Database Schema](../database/SCHEMA.md)
