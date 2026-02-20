# ADR-072: Unified Content Layer and TP Execution Pipeline

**Date**: 2026-02-20
**Status**: Accepted
**Supersedes**: ADR-049 (Context Freshness Model), ADR-062 (Platform Context Architecture)
**Extends**: ADR-063 (Four-Layer Model), ADR-068 (Signal-Emergent Deliverables), ADR-071 (Strategic Architecture Principles)
**Related**: ADR-064 (Unified Memory Service), ADR-069 (Layer 4 Content Integration)

---

## Context

### The Architectural Evolution

YARNNN's architecture evolved through incremental ADRs that made locally correct decisions but created systemic tensions:

**ADR-049** (2026-02-12) chose "freshness over accumulation" — treating platforms as the filesystem and sync as git pull. This was correct for the problem it solved (avoiding history compression complexity) but predated the flywheel moat thesis.

**ADR-062** (2026-02-18) defined `filesystem_items` as "conversational search cache only" and mandated that deliverable execution use live APIs. This created two parallel content access paths with different trust models.

**ADR-068** (2026-02-19) introduced signal processing, which reads live APIs for time-sensitive signals. This added a third content access path.

The result: three independent systems (`filesystem_items` cache, deliverable live fetches, signal processing live fetches) accessing the same upstream platforms with no shared representation, no accumulation, and no provenance tracking.

### The Axiomatic Foundation

The product thesis evolved: **accumulated data enables stronger inference**. The system that accumulates the richest local representation of a user's work world over time will produce the most intelligent outputs — independent of which LLM sits on top.

This is YARNNN's moat. It cannot be achieved with TTL-expiring caches or live-only fetches. It requires:
1. Content that proved significant is retained indefinitely
2. Content has provenance (what referenced it, when, why)
3. Accumulation compounds over time as the user's work history deepens

### Why Existing ADRs Are Superseded

**ADR-049's "freshness over accumulation"** was decided before:
- Signal processing existed
- The three strategic deliverable types were built
- The flywheel moat was articulated

**ADR-062's "cache stays cache"** created:
- A provenance gap (no link from deliverable output to source content)
- An audit gap (can't answer "what Slack messages informed this digest?")
- A quality gap (deliverable execution uses cruder fetches than TP primitives)

These decisions were made in a different context. The product thesis evolved. The architecture must evolve with it.

---

## Decision

### 1. Unified Content Layer: `platform_content`

Replace `filesystem_items` with a single, unified content table.

**Schema**:

```sql
CREATE TABLE platform_content (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Platform identification
    platform            TEXT NOT NULL,              -- slack, gmail, notion, calendar
    resource_id         TEXT NOT NULL,              -- channel_id, label, page_id, calendar_id
    resource_name       TEXT,                       -- human-readable (#engineering, Inbox, etc.)
    item_id             TEXT NOT NULL,              -- message_id, thread_id, event_id

    -- Content
    content             TEXT NOT NULL,              -- full text
    content_type        TEXT,                       -- message, email, page, event
    content_hash        TEXT,                       -- SHA-256 for deduplication on re-fetch
    content_embedding   vector(1536),               -- semantic search (pgvector)

    -- Versioning
    version_of          UUID REFERENCES platform_content(id), -- FK to previous version
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Retention policy
    retained            BOOLEAN NOT NULL DEFAULT false,
    retained_reason     TEXT,                       -- 'deliverable_execution', 'signal_processing', 'tp_session'
    retained_ref        UUID,                       -- FK to deliverable_version, signal_action, session
    expires_at          TIMESTAMPTZ,                -- NULL if retained=true

    -- Metadata
    author              TEXT,
    author_id           TEXT,
    is_user_authored    BOOLEAN DEFAULT false,
    source_timestamp    TIMESTAMPTZ,                -- when it happened at source
    metadata            JSONB DEFAULT '{}',         -- platform-specific fields

    -- Constraints
    UNIQUE(user_id, platform, resource_id, item_id, fetched_at)
);

-- Indexes
CREATE INDEX idx_platform_content_user_recent
    ON platform_content(user_id, fetched_at DESC);
CREATE INDEX idx_platform_content_retained
    ON platform_content(user_id, retained) WHERE retained = true;
CREATE INDEX idx_platform_content_expires
    ON platform_content(expires_at) WHERE expires_at IS NOT NULL AND retained = false;
CREATE INDEX idx_platform_content_embedding
    ON platform_content USING ivfflat (content_embedding vector_cosine_ops)
    WHERE content_embedding IS NOT NULL;
CREATE INDEX idx_platform_content_search
    ON platform_content USING gin (to_tsvector('english', content));

-- RLS
ALTER TABLE platform_content ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own content" ON platform_content
    FOR SELECT USING (auth.uid() = user_id);
```

**Retention Policy**:

| Condition | `retained` | `expires_at` | Outcome |
|---|---|---|---|
| Content never referenced | `false` | `NOW() + TTL` | Expires after TTL |
| Referenced by deliverable_version | `true` | `NULL` | Retained indefinitely |
| Referenced by signal_processing | `true` | `NULL` | Retained indefinitely |
| Accessed during TP session | `true` | `NULL` | Retained indefinitely |

**TTL by platform** (unchanged from current):
- Slack: 7 days
- Gmail: 14 days
- Notion: 30 days
- Calendar: 1 day

Content that has never been referenced by any downstream system expires after TTL. Content that has been referenced is retained indefinitely with provenance.

### 2. Dual-Writer Model

Two systems write to `platform_content`:

**Platform Sync** (`platform_worker.py`):
- Runs continuously on tier-appropriate frequency
- Fetches content from external platforms
- Writes with `retained=false`, `expires_at=NOW()+TTL`
- Knows nothing about significance — just syncs

**Signal Processing** (`signal_extraction.py`):
- Reads live platform APIs for time-sensitive signals
- When it identifies significant content, writes directly to `platform_content` with `retained=true`
- Sets `retained_reason='signal_processing'`, `retained_ref=signal_action_id`
- This is Option A from the implementation discussion

Additionally, **Deliverable Execution** and **TP Sessions** mark existing records as retained:
- After synthesis, execution marks source records `retained=true`, `retained_reason='deliverable_execution'`, `retained_ref=version_id`
- After semantic search hits during TP session, marks accessed records `retained=true`, `retained_reason='tp_session'`, `retained_ref=session_id`

### 3. TP as Execution Pipeline

Deliverable execution becomes a headless TP session.

**Current state** (being replaced):
- `DeliverableAgent` in `deliverable_pipeline.py` uses its own fetch pipeline
- Different primitives than TP
- Quality gap between interactive and scheduled outputs

**New state**:
- `DeliverableAgent` invokes the TP agent in execution mode
- Same primitives: `Search`, `FetchPlatformContent`, `CrossPlatformQuery`
- Same reasoning capability
- One codebase, not two

**Three behavioral differences from live mode**:

| Aspect | TP Live Mode | TP Execution Mode |
|---|---|---|
| **Streaming** | Streaming responses to user | Collect full output, write to `deliverable_version` |
| **Clarification** | Can ask "which version did you mean?" | Cannot ask — must complete with available context |
| **Tool rounds** | `max_tool_rounds=5` | May be higher for complex deliverables |

**Context injection differences**:

| Input | TP Live Mode | TP Execution Mode |
|---|---|---|
| User model | Full `user_context` (working memory) | Full `user_context` (working memory) |
| Task | User message | Deliverable configuration |
| Content | Fetched on demand via primitives | Pre-loaded relevant `platform_content` records |
| History | Recent deliverable versions (Layer 4 content) | Recent versions for same deliverable type |

**Deletion**: The parallel fetch pipeline in `deliverable_pipeline.py → fetch_integration_source_data()` is deleted entirely on cutover. No backwards compatibility shim.

### 4. Source Snapshots with Content References

`deliverable_versions.source_snapshots` now references specific `platform_content` record IDs:

```json
{
  "source_snapshots": [
    {
      "platform": "slack",
      "resource_id": "C01234567",
      "resource_name": "#engineering",
      "platform_content_ids": ["uuid-1", "uuid-2", "uuid-3"],
      "item_count": 47,
      "fetched_at": "2026-02-20T09:00:00Z"
    }
  ]
}
```

This closes the provenance gap: every deliverable version can answer "which specific content records were synthesized into this output?"

### 5. Memory Source Reference

`user_context` gains a `source_ref` field:

```sql
ALTER TABLE user_context
    ADD COLUMN source_ref UUID,           -- FK to source record
    ADD COLUMN source_type TEXT;          -- 'session_message', 'deliverable_version', 'platform_content', 'activity_log'
```

Every memory entry becomes traceable to its origin. This closes the memory audit gap.

---

## Cron Jobs Architecture

Four distinct cron jobs with distinct responsibilities:

| Job | Frequency | Responsibility | Writes To |
|---|---|---|---|
| **Platform Sync** | Tier-dependent (hourly Pro, less for lower) | Fetch content from external platforms | `platform_content` (retained=false) |
| **Signal Processing** | Hourly | Read live APIs, identify significance, create/trigger deliverables | `platform_content` (retained=true), `deliverables`, `signal_history` |
| **Memory Extraction** | Nightly (midnight UTC) | Extract patterns from sessions and feedback | `user_context` |
| **Deliverable Scheduler** | Every 5 minutes | Trigger due deliverables | `deliverable_versions` (via execution) |

These jobs are completely independent. None calls another. They share the data layer, not execution flow.

---

## Migration Plan

**Parallel-then-cutover approach** with time-bounded parallel phase.

**Hard cutover date**: 2 weeks after parallel phase begins (set before implementation starts).

**Phase 1: Schema** (Day 1-2)
- Create `platform_content` table alongside `filesystem_items`
- Verify pgvector extension (already enabled per migration 006)
- Add `source_ref` to `user_context`

**Phase 2: Platform Sync** (Day 3-5)
- Update `platform_worker.py` to write to both tables
- Implement retention policy logic
- Write tests for dual-write

**Phase 3: TP Primitives** (Day 6-8)
- Update `Search` primitive to read from `platform_content`
- Implement semantic search via pgvector
- Update other primitives (`FetchPlatformContent`, etc.)

**Phase 4: Signal Processing** (Day 9-10)
- Update `signal_extraction.py` to write significant content to `platform_content` with `retained=true`
- Update `source_snapshots` format to include `platform_content_ids`

**Phase 5: TP Execution Mode** (Day 11-14)
- Refactor `DeliverableAgent` to invoke TP agent in headless mode
- Implement no-streaming, no-clarification, bounded-tool-rounds behavior
- Delete `fetch_integration_source_data()` and related cruder fetches

**Phase 6: Memory Source Ref** (Day 15)
- Wire `process_feedback()` to record `source_ref`
- Wire `process_conversation()` to record `source_ref`
- Wire `process_patterns()` to record `source_ref`

**Phase 7: Cutover** (Day 16)
- Stop writing to `filesystem_items`
- Drop `filesystem_items` table
- Update all documentation

---

## What This Supersedes

### ADR-049 (Context Freshness Model)

**Original decision**: "Instead of history management, we need context freshness management... Each deliverable generation should work with current state, not accumulated history."

**New decision**: Accumulated history is the moat. Content that proved significant is retained indefinitely. The retention policy (referenced = retained) replaces the TTL-only model.

**Why**: ADR-049 was correct for avoiding history compression complexity. But it was decided before the flywheel thesis. Accumulation of significant content compounds value over time.

### ADR-062 (Platform Context Architecture)

**Original decision**: "`filesystem_items` is retained as the conversational search index... Do not expand the mirror's role... Deliverable execution remains on live reads."

**New decision**: `platform_content` is the unified content layer for both conversation and execution. TP primitives are the single content access path for all use cases. The parallel pipeline is deleted.

**Why**: ADR-062 created a quality gap between TP and deliverable execution. The unified model means improvements to TP primitives automatically improve deliverable quality.

---

## Consequences

### Positive

1. **Accumulation moat**: Significant content retained indefinitely, compounding intelligence over time
2. **Provenance closure**: Every deliverable links to specific source content; every memory links to its origin
3. **Quality unification**: TP primitives used for both conversation and execution; one codebase
4. **Semantic search**: pgvector enables semantic retrieval, not just ILIKE
5. **Audit trail**: "What content informed this output?" becomes answerable
6. **Simplified architecture**: One content layer, one execution agent, clear retention semantics

### Negative

1. **Migration complexity**: Parallel-then-cutover requires careful coordination
2. **Storage growth**: Retained content accumulates indefinitely (mitigated by selective retention)
3. **Embedding cost**: Content embedding generation adds API calls on write
4. **TP refactor risk**: Headless execution mode is non-trivial

### Mitigations

- Time-bounded parallel phase prevents drift
- Selective retention (only referenced content) controls storage growth
- Embedding generation can be async/batched
- TP refactor prioritized last, after content layer is stable

---

## Embedding Infrastructure Decision

**Decision**: Use pgvector (already enabled).

**Rationale**:
- Migration 006 already enables `CREATE EXTENSION IF NOT EXISTS vector`
- `memories` and `chunks` tables already use `vector(1536)` with ivfflat indexes
- No new infrastructure required
- Embedding dimension: 1536 (compatible with OpenAI ada-002, Anthropic embeddings)

**Embedding generation**:
- On write to `platform_content`, generate embedding via embedding API
- Async if latency-sensitive (platform sync batches)
- Sync if semantic search needed immediately

---

## Files Changed

| File | Change |
|---|---|
| `supabase/migrations/XXX_platform_content.sql` | New table, indexes, RLS |
| `api/services/filesystem.py` | Rename to `platform_content.py`, update all functions |
| `api/workers/platform_worker.py` | Write to `platform_content`, implement retention policy |
| `api/services/signal_extraction.py` | Write significant content with `retained=true` |
| `api/services/signal_processing.py` | Mark `platform_content_ids` in deliverable versions |
| `api/services/freshness.py` | Update to use `platform_content` |
| `api/services/primitives/search.py` | Read from `platform_content`, semantic search |
| `api/services/deliverable_pipeline.py` | Delete `fetch_integration_source_data()`, invoke TP in execution mode |
| `api/agents/thinking_partner.py` | Add execution mode flag, disable streaming/clarification |
| `api/services/memory.py` | Add `source_ref` to all writes |

---

## ADRs Updated

| ADR | Update |
|---|---|
| ADR-049 | Add "Superseded by ADR-072" header |
| ADR-062 | Add "Superseded by ADR-072" header |
| ADR-063 | Update Layer 3 (Context) description to reference `platform_content` |
| ADR-068 | Update signal processing to document dual-writer model |
| ADR-071 | Principle 5 (Separation of Freshness and Authority) partially superseded |

---

## Related

- [ADR-063: Four-Layer Model](ADR-063-activity-log-four-layer-model.md) — Extended by this ADR
- [ADR-068: Signal-Emergent Deliverables](ADR-068-signal-emergent-deliverables.md) — Signal processing now dual-role
- [ADR-071: Strategic Architecture Principles](ADR-071-strategic-architecture-principles.md) — Quality flywheel principle implemented
- [Four-Layer Model Architecture](../architecture/four-layer-model.md) — To be updated
- [Context Pipeline](../architecture/context-pipeline.md) — To be updated
- [Deliverables Architecture](../architecture/deliverables.md) — To be updated

---

## Acceptance Criteria

- [x] `platform_content` table created with retention policy
- [x] Platform sync writes to new table with TTL
- [ ] Signal processing writes significant content with `retained=true`
- [ ] TP primitives read from `platform_content` with semantic search
- [ ] Deliverable execution uses TP in headless mode
- [ ] `source_snapshots` includes `platform_content_ids`
- [x] `user_context.source_ref` populated by all extraction paths
- [ ] `filesystem_items` dropped
- [ ] ADR-049 and ADR-062 marked superseded
- [x] Architecture docs updated
- [x] Frontend surfacing completed (see below)

---

## Frontend Surfacing

**Status**: Completed (2026-02-20)

Frontend changes to surface ADR-072 concepts:

### Jobs Page (`/jobs`)
New operational visibility page showing:
- Platform sync status (per-platform last/next sync, source count)
- Background job status (signal processing, memory extraction, conversation analyst)

Distinct from Activity (audit trail) — Jobs shows operational state.
Deliverable schedules are shown on the dedicated Deliverables page, not duplicated here.

### Context Page Enhancements
- Retention badges on content items (`Retained` badge)
- `retained_count` in API response for accumulation visibility

### Memory Page Enhancements
- Provenance badges showing `source_type` ("from feedback", "from chat", "from patterns")
- `source_ref` available in frontend types

### Deliverables Page Enhancements
- Origin badges for `signal_emergent` and `analyst_suggested` deliverables
- Badges on list cards and detail page headers

### Activity Page Enhancements
- Added `integration_connected` to filterable event types
- Enhanced metadata display: version numbers, item counts, origin badges for signal-emergent deliverables

### Navigation
Added Jobs to navigation bar: Chat | Deliverables | Memory | Context | Activity | Jobs | Settings

### API Endpoints
- `GET /api/jobs/status` — Returns platform sync status, background job status
- `GET /api/integrations/{platform}/context` — Extended with `retained`, `retained_reason`, `retained_at`, `expires_at`, `retained_count`
- `GET /api/memory/context` — Extended with `source_ref`, `source_type`