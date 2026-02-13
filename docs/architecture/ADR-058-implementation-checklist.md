# ADR-058 Implementation Checklist

> **Status**: Planning
> **Created**: 2026-02-13
> **ADR**: [ADR-058-knowledge-base-architecture.md](../adr/ADR-058-knowledge-base-architecture.md)

---

## Overview

This checklist tracks implementation of the Knowledge Base Architecture (ADR-058).

**Key Changes**:
1. Terminology alignment (ephemeral_context → filesystem_items, etc.)
2. New Knowledge tables (profile, styles, domains, entries)
3. Inference engine for populating Knowledge from Filesystem
4. Updated TP prompt injection (build_working_memory)
5. Updated Context page UI

---

## Phase 1: Schema Migration

### Database
- [ ] Review migration 043_knowledge_base_architecture.sql
- [ ] Review migration 044_knowledge_base_data_migration.sql
- [ ] Review migration 045_knowledge_base_cleanup.sql
- [ ] Run migrations on local database
- [ ] Verify data migration with verification queries
- [ ] Run cleanup migration
- [ ] Test RLS policies

### Files
- `supabase/migrations/043_knowledge_base_architecture.sql`
- `supabase/migrations/044_knowledge_base_data_migration.sql`
- `supabase/migrations/045_knowledge_base_cleanup.sql`

---

## Phase 2: API Layer Updates

### Rename/Refactor Services

| Old File | New File | Status |
|----------|----------|--------|
| `api/integrations/core/client.py` | Rename references to `platform_connections` | [ ] |
| `api/services/ephemeral_context.py` | `api/services/filesystem.py` | [ ] |
| `api/services/context.py` | `api/services/working_memory.py` | [ ] |
| `api/services/extraction.py` | Update to use new tables | [ ] |
| `api/services/domain_inference.py` | Update to use `knowledge_domains` | [ ] |

### New Services

| File | Purpose | Status |
|------|---------|--------|
| `api/services/knowledge/profile.py` | Profile inference + CRUD | [ ] |
| `api/services/knowledge/styles.py` | Style inference + CRUD | [ ] |
| `api/services/knowledge/domains.py` | Domain management | [ ] |
| `api/services/knowledge/entries.py` | Entry management | [ ] |
| `api/services/knowledge/inference.py` | Inference engine orchestration | [ ] |

### API Routes

| Old Route | New Route | Status |
|-----------|-----------|--------|
| `GET /api/integrations/connected` | `GET /api/platforms` | [ ] |
| `GET /api/integrations/{provider}/context` | `GET /api/filesystem/{platform}` | [ ] |
| `GET /api/context/user/memories` | `GET /api/knowledge/entries` | [ ] |
| `POST /api/context/user/memories` | `POST /api/knowledge/entries` | [ ] |
| `GET /api/domains` | `GET /api/knowledge/domains` | [ ] |
| N/A | `GET /api/knowledge/profile` | [ ] |
| N/A | `PUT /api/knowledge/profile` | [ ] |
| N/A | `GET /api/knowledge/styles` | [ ] |
| N/A | `POST /api/knowledge/refresh` | [ ] |

---

## Phase 3: TP Integration

### Working Memory Builder
- [ ] Create `api/services/working_memory.py`
- [ ] Implement `build_working_memory(user_id, client)`
- [ ] Format output for prompt injection
- [ ] Update `thinking_partner.py` to use new builder

### Prompt Updates
- [ ] Update system prompt template in `thinking_partner.py`
- [ ] Add Knowledge section formatting
- [ ] Update primitive descriptions (grep Knowledge first)

### Files
- `api/services/working_memory.py` (new)
- `api/agents/thinking_partner.py`
- `api/services/primitives/search.py`

---

## Phase 4: Inference Engine

### Style Inference
- [ ] Implement `infer_platform_style(user_id, platform, client)`
- [ ] Analyze user-authored messages from `filesystem_items`
- [ ] Extract tone, verbosity, formatting patterns
- [ ] Store sample excerpts
- [ ] Trigger after platform sync

### Profile Inference
- [ ] Implement `infer_user_profile(user_id, client)`
- [ ] Extract name from email signatures
- [ ] Extract role/company from platform metadata
- [ ] Infer timezone from calendar/message patterns

### Domain Inference
- [ ] Migrate existing `domain_inference.py` to new schema
- [ ] Update source mapping to `knowledge_domains.sources`
- [ ] Add domain summary generation

### Conversation Extraction
- [ ] Implement `extract_knowledge_from_conversation(session_id, client)`
- [ ] Identify preferences, facts, decisions in user messages
- [ ] Create `knowledge_entries` with source tracking
- [ ] Mark messages as processed

### Scheduled Jobs
- [ ] Create `api/jobs/inference_jobs.py`
- [ ] Daily profile refresh job
- [ ] Post-sync style inference job
- [ ] Conversation extraction job

---

## Phase 5: Frontend Updates

### API Client
- [ ] Update `web/lib/api/client.ts` with new routes
- [ ] Add `api.knowledge.profile`, `api.knowledge.styles`, etc.
- [ ] Add `api.filesystem.*` methods
- [ ] Add `api.platforms.*` methods

### Context Page Rewrite
- [ ] Create new `web/app/(authenticated)/context/page.tsx`
- [ ] Implement Knowledge section (Profile, Styles, Domains, Entries)
- [ ] Implement Filesystem section (Platforms, Documents)
- [ ] Add "Add Knowledge" entry form
- [ ] Add user override editing
- [ ] Show inference sources/confidence

### Components

| Component | Purpose | Status |
|-----------|---------|--------|
| `KnowledgeProfileCard.tsx` | Display/edit profile | [ ] |
| `KnowledgeStyleCard.tsx` | Display/edit platform style | [ ] |
| `KnowledgeDomainCard.tsx` | Display/edit domain | [ ] |
| `KnowledgeEntryList.tsx` | List/manage entries | [ ] |
| `FilesystemPlatformCard.tsx` | Platform sync status | [ ] |
| `FilesystemDocumentCard.tsx` | Document display | [ ] |
| `AddKnowledgeModal.tsx` | Add new entry | [ ] |

### Empty State
- [ ] Update empty state with three paths (Platforms, Documents, Knowledge)
- [ ] Update copy ("Add Knowledge" not "Tell TP")

---

## Phase 6: Deliverable Updates

### Service Updates
- [ ] Update `api/services/deliverable_execution.py`
- [ ] Read from `filesystem_items` instead of `ephemeral_context`
- [ ] Apply `knowledge_styles` to generation
- [ ] Use `knowledge_domains` for context scoping

### Frontend Updates
- [ ] Update deliverable detail to show domain
- [ ] Update source selector to use new tables

---

## Phase 7: Testing

### Unit Tests
- [ ] Test knowledge profile CRUD
- [ ] Test knowledge styles CRUD
- [ ] Test knowledge entries CRUD
- [ ] Test working memory builder
- [ ] Test inference functions

### Integration Tests
- [ ] Test platform sync → filesystem_items
- [ ] Test sync → style inference trigger
- [ ] Test conversation → knowledge extraction
- [ ] Test TP prompt includes knowledge

### E2E Tests
- [ ] Test Context page with knowledge display
- [ ] Test adding knowledge entry
- [ ] Test editing profile override
- [ ] Test "Refresh" inference

---

## Phase 8: Cleanup

### Remove Old Code
- [ ] Remove old `ephemeral_context.py` (after new `filesystem.py` works)
- [ ] Remove old routes
- [ ] Remove old components
- [ ] Remove old types

### Documentation
- [ ] Update API documentation
- [ ] Update architecture docs
- [ ] Update README if needed

---

## Terminology Reference

| Old Term | New Term | Notes |
|----------|----------|-------|
| `ephemeral_context` | `filesystem_items` | Platform synced content |
| `documents` | `filesystem_documents` | Uploaded files |
| `chunks` | `filesystem_chunks` | Document chunks |
| `user_integrations` | `platform_connections` | OAuth connections |
| `context_domains` | `knowledge_domains` | Work domains |
| `memories` | `knowledge_entries` | User facts (subset) |
| `build_session_context()` | `build_working_memory()` | Prompt injection |
| "Tell TP" | "Add Knowledge" | UI label |

---

## Risk Mitigation

### Data Loss Prevention
- [ ] Backup database before migration
- [ ] Run verification queries after 044 migration
- [ ] Only run 045 cleanup after verification passes

### Rollback Plan
- Keep old table backups for 7 days post-migration
- Document manual rollback steps if needed

### Testing Strategy
- Local testing with full data migration
- Staging deployment before production
- Canary rollout if user data exists

---

## Timeline Estimate

| Phase | Scope | Notes |
|-------|-------|-------|
| Phase 1 | Schema | 1 session |
| Phase 2 | API Layer | 2-3 sessions |
| Phase 3 | TP Integration | 1 session |
| Phase 4 | Inference Engine | 2-3 sessions |
| Phase 5 | Frontend | 2-3 sessions |
| Phase 6 | Deliverables | 1 session |
| Phase 7 | Testing | 1-2 sessions |
| Phase 8 | Cleanup | 1 session |

**Total**: ~12-15 sessions

---

## Notes

- Pre-launch, no user data at risk
- Clean-slate approach preferred over incremental
- Inference engine is the most complex piece
- Style inference can be MVP (simple heuristics) then improved
