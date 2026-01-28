# Memory & Context Patterns Analysis

**Date**: 2026-01-28
**Purpose**: Document learnings from sibling repos for future reference

---

## Overview

Analysis of two sibling projects to inform YARNNN v5's approach to memory/context management.

| Repo | Focus | Memory Approach |
|------|-------|-----------------|
| `yarnnn-app-fullstack` | Work platform | Block state machine with governance |
| `chat_companion` | AI companion | LLM extraction with temporal tiers |

---

## yarnnn-app-fullstack: Block State Machine

### Schema (Substrate V3)

```sql
blocks:
  - id, basket_id, workspace_id
  - semantic_type, title, content
  - state (PROPOSED|ACCEPTED|LOCKED|CONSTANT|REJECTED|SUPERSEDED)
  - version, parent_block_id
  - scope (for workspace-scoped cross-basket memory)
  - anchor_role, anchor_status, anchor_confidence
  - last_validated_at
```

### State Transitions

```
PROPOSED → ACCEPTED → LOCKED → CONSTANT
    ↓          ↓
REJECTED   SUPERSEDED (new version created)
```

### Key Patterns

**1. Agent vs User Permissions**
```python
# lifecycle.py
USER_ONLY_STATES = {ACCEPTED, LOCKED, CONSTANT, REJECTED}
AGENT_PROPOSABLE_STATES = {PROPOSED, SUPERSEDED}
```
- Agents propose, users approve
- Users control what becomes permanent

**2. Immutability**
- LOCKED/CONSTANT blocks cannot have content modified
- Changes create new versions (parent_block_id reference)

**3. Scope Levels**
- `basket_id` - Working memory (single work container)
- `workspace_id` + `scope` - Cross-basket memory (shared across projects)
- CONSTANT state required for cross-basket visibility

**4. Indexing Strategy**
```sql
idx_blocks_basket_state_time   -- Primary queries
idx_blocks_workspace_scope      -- Cross-basket memory
idx_blocks_anchor_vocabulary    -- Semantic discovery
idx_blocks_recent_validated     -- Short-term (7 days)
idx_blocks_constants            -- Long-term
```

### Lessons Learned

**Positive:**
- Clear ownership model (agent proposes, user decides)
- Versioning enables evolution without data loss
- Cross-basket memory useful for persistent facts

**Negative:**
- Approval workflow added friction
- State machine complexity wasn't justified by user value
- Over-indexed on governance before product-market fit

---

## chat_companion: Temporal Memory Tiers

### Schema

**user_context** (fact-based):
```sql
user_context:
  - id, user_id
  - category (fact|preference|event|goal|relationship|emotion|situation)
  - key, value
  - importance_score (0.0-1.0)
  - emotional_valence
  - source (extracted|user_provided)
  - expires_at
```

**memory_events** (episode-based):
```sql
memory_events:
  - id, user_id, character_id, episode_id, series_id
  - type, content, summary
  - importance_score, emotional_valence
  - embedding vector(1536)
  - last_referenced_at, reference_count
  - expires_at
```

### Three-Tier Architecture (ADR-001)

| Tier | Storage | Lifespan | Contents |
|------|---------|----------|----------|
| Working | In-memory | Current conversation | Recent messages, mood |
| Active | `user_context` | Days-weeks | Ongoing events, goals |
| Core | `user_context` | Permanent | Facts, preferences |

### Key Patterns

**1. Extraction Pipeline**
```python
# context.py
async def extract_context():
    # 1. Get last 10 messages
    # 2. Compare against existing context (dedup)
    # 3. LLM extracts only new items
    # 4. Return ExtractedContext objects
```

**2. Deduplication**
```python
# Before insert, check existing
existing = await get_user_context(user_id, category)
# LLM prompt includes existing context
# "Only extract if NOT already in: {existing}"
```

**3. Temporal Expiry**
```python
# Time-bound context
if context.temporal_hint:
    expires_at = parse_temporal(context.temporal_hint)
    # "meeting tomorrow" → expires_at = tomorrow + 1 day
```

**4. Retrieval Ranking**
```python
.order("importance_score", desc=True)
.order("last_referenced_at", desc=True)
.order("updated_at", desc=True)
.filter("expires_at", "is", None)  # OR > NOW()
.limit(15)
```

**5. Semantic Search**
```sql
-- pgvector for similarity
CREATE INDEX idx_memory_embedding
ON memory_events USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Lessons Learned

**Positive:**
- Importance scoring enables smart retrieval
- Temporal expiry prevents stale context
- Background extraction doesn't block conversation
- Deduplication keeps context clean

**Negative:**
- Two tables (user_context + memory_events) created confusion
- Character-scoped memory added complexity
- pgvector requires maintenance (reindexing)

---

## Comparison Matrix

| Feature | yarnnn-fullstack | chat_companion | YARNNN v5 |
|---------|-----------------|----------------|-----------|
| **Unit** | Block | Context item | Block |
| **Scope** | Basket/Workspace | User/Character | Project |
| **Governance** | State machine | Auto-extract | None (direct) |
| **Validation** | User approval | LLM dedup | None |
| **Importance** | Implicit (state) | Explicit (score) | None |
| **Temporal** | last_validated_at | expires_at | None |
| **Semantic** | Anchor vocab | pgvector | None |
| **Versioning** | parent_block_id | None | None |

---

## Future Enhancements (When Needed)

### Tier 1: Low-Effort Additions
```sql
ALTER TABLE blocks ADD COLUMN importance_score FLOAT DEFAULT 0.5;
ALTER TABLE blocks ADD COLUMN expires_at TIMESTAMPTZ;
```
- Enable ranking during retrieval
- Support time-bound context

### Tier 2: Medium-Effort Additions
```sql
ALTER TABLE blocks ADD COLUMN embedding vector(1536);
CREATE INDEX idx_blocks_embedding ON blocks
USING ivfflat (embedding vector_cosine_ops);
```
- Requires pgvector extension
- Enable semantic search

### Tier 3: High-Effort Additions
- Block state machine (PROPOSED→ACCEPTED)
- User approval UI
- Versioning with parent_block_id
- Cross-project (workspace-scoped) blocks

---

## Decision

See [ADR-001-memory-simplicity.md](../adr/ADR-001-memory-simplicity.md)

**Summary**: Keep simple for MVP. Add complexity only when users report specific problems.

---

## File References

### yarnnn-app-fullstack
- Schema: `supabase/migrations/20250115_substrate_v3_purge_and_rebuild.sql`
- Lifecycle: `work-platform/api/src/app/memory/blocks/lifecycle.py`
- Models: `work-platform/api/src/app/models/block.py`

### chat_companion
- Schema: `supabase/migrations/005_memory_hooks.sql`
- Schema: `supabase/migrations/100_companion_schema.sql`
- Context: `api/api/src/app/services/context.py`
- Memory: `api/api/src/app/services/memory.py`
- ADR: `docs/adr/ADR-001-memory-architecture.md`
