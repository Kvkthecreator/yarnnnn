# ADR-071: Strategic Architecture Principles

**Status**: Accepted
**Date**: 2026-02-20
**Context**: Codification of architectural insights from Phase 1-3 implementation (Layer 4 integration, memory extraction, documentation hardening)

---

## Context

YARNNN's architecture has evolved through multiple ADRs (ADR-063 four-layer model, ADR-064 implicit memory extraction, ADR-068 signal-emergent deliverables, ADR-069 Layer 4 content integration). These decisions share underlying strategic principles that were implicit but not explicitly documented.

This ADR codifies those principles to:
1. Provide architectural guidance for future development
2. Ensure consistency across subsystems
3. Document the strategic vision behind the four-layer model

These principles emerged from implementation work, not from top-down design. They are descriptive (what we've built) and prescriptive (what future work should follow).

---

## Strategic Principles

### 1. Unidirectional Generation, Bidirectional Learning

**Principle**: Data flows downward (L1→L2→L3→L4) for generation. Learning flows upward (L4→L1, L2→L1) through feedback loops.

**Why**: Separating generation flow from learning flow enables predictable, deterministic output generation while allowing quality improvement over time through feedback loops.

**Generation flow** (downward):
```
Memory (L1) ───────┐
                   │
Activity (L2) ─────┤
                   ├──► Signal Processing ──► Work (L4)
Context (L3) ──────┘
```

**Learning flow** (upward):
```
Work (L4) ─────► Deliverable Feedback ──► Memory (L1)
               (process_feedback: ADR-064)

Work (L4) ─────► Content Quality Signal ──► Signal Processing (L4)
               (recent_content: ADR-069)

Activity (L2) ──► Pattern Detection ────► Memory (L1)
               (process_patterns: ADR-070)
```

**Implementation**:
- Generation never writes "backward" (Work doesn't modify Memory during execution)
- Learning happens at boundaries: session end, approval, daily cron
- This separation enables predictable generation while accumulating intelligence

---

### 2. Weighting Shift Over Time

**Principle**: Signal reasoning quality is a function of Layer 4 content depth. As user tenure increases, reliance shifts from Memory+Context to Work.

**New users (0-30 days)**:
- Rely heavily on **L1 (Memory) + L3 (Context)**
- Little Layer 4 history exists
- System uses stated preferences and live platform data
- Memory extraction from conversation carries the most weight

**Mature users (90+ days)**:
- Rely increasingly on **L4 (Work)**
- System learns what quality looks like from prior deliverable versions
- Layer 4 content becomes the strongest signal for what the user values
- Pattern detection from Activity and feedback from edits refine Memory

**Why**: Layer 4 accumulates intelligence over time. A mature user's deliverable history reveals preferences more accurately than stated facts. The system improves with usage.

**Implementation**:
- Signal processing prompts include recent deliverable content (ADR-069)
- Pattern detection analyzes 90 days of activity (ADR-070)
- Memory extraction confidence varies by source (user_stated=1.0, feedback=0.7, pattern=0.6)

---

### 3. Quality Flywheel Through Layer 4

**Principle**: Layer 4 serves dual purpose — output to users and training signal for future work. This creates a self-reinforcing quality loop.

**The flywheel**:
```
Better deliverables → More usage → More learning → Better deliverables
         ↑                                              ↓
         └──────────────────────────────────────────────┘
```

**Layer 4 as output**:
- Versioned work products delivered to users
- Scheduled digests, meeting briefs, intelligence reports
- User-facing value

**Layer 4 as input**:
- Training signal for what quality looks like
- Recent content informs signal processing (ADR-069)
- User edits trigger memory extraction (ADR-064)
- Deliverable runs populate Activity for pattern detection (ADR-070)

**Why**: The more deliverables a user runs, the more the system learns what they value. Each generation run both produces value and improves future quality.

**Implementation**:
- `deliverable_versions.final_content` included in signal reasoning prompts (400-char preview)
- Approval with edits triggers `process_feedback()` to extract length/format preferences
- `deliverable_run` activity events enable pattern detection (day-of-week, time-of-day, type preferences)

---

### 4. Explicit Writes at Boundaries

**Principle**: Every write to Memory, Activity, and Work happens at a known boundary. No scattered inference, no automatic promotion mid-operation.

**Defined boundaries**:
- **Memory writes**: Session end (nightly cron), deliverable approval (async), pattern detection (daily cron)
- **Activity writes**: After deliverable run, after platform sync, after chat turn, after memory write
- **Work writes**: At deliverable generation completion (version creation)

**Never happens**:
- Memory written mid-conversation by TP
- Activity written by user-facing clients
- Work modified after generation (content immutable; status progresses)

**Why**: Boundary-based writes are predictable, testable, and debuggable. Writes happen at observable lifecycle events, not scattered through execution paths.

**Implementation**:
- `process_conversation()` scheduled at midnight UTC, processes yesterday's sessions
- `process_feedback()` called from `routes/deliverables.py` approval endpoint via async task
- `process_patterns()` scheduled at midnight UTC, analyzes last 90 days
- `write_activity()` called immediately after primary operation completes

---

### 5. Separation of Freshness and Authority

**Principle**: The cache (`filesystem_items`) is fresh enough for conversation. Live APIs are authoritative for generation. Using the cache for deliverables would introduce silent staleness risk. Using live APIs for every conversational search would be prohibitively slow.

**Cache (`filesystem_items`)**:
- Used for: `Search(scope="platform_content")` during conversation
- Freshness: Tier-dependent (2–24h stale possible)
- Authority: No — convenience index, not source of truth
- Latency: Fast (local DB ILIKE query)
- Cross-platform: Single query across all platforms

**Live APIs**:
- Used for: Deliverable execution, TP platform tools
- Freshness: Always current
- Authority: Yes — direct from platform
- Latency: Slower (external API round trip)
- Cross-platform: Separate call per platform

**Why**: Different use cases require different trade-offs. Conversational search needs speed and composability. Generation needs authority and point-in-time accuracy.

**Implementation**:
- `deliverable_pipeline.py → fetch_integration_source_data()` never reads `filesystem_items`
- `platform_worker.py` populates cache on schedule with TTL expiry
- `primitives/search.py` hits cache for cross-platform ILIKE search

---

### 6. Immutability Where It Matters

**Principle**: Work versions are immutable records. Activity rows are immutable. Only Memory and deliverable metadata are mutable — and Memory mutability is boundary-controlled.

**Immutable**:
- `deliverable_versions.final_content` — never changes after generation
- `activity_log` rows — append-only, no updates
- `deliverable_versions.source_snapshots` — audit trail of what was read

**Mutable (controlled)**:
- `user_context` — upserted at boundaries (session end, approval, pattern detection)
- `deliverables` metadata (title, schedule, status) — user can edit configuration
- `deliverable_versions.status` — progresses forward (generating → staged → approved → published)

**Why**: Immutability enables audit, debugging, and learning. Layer 4 content is a historical record of what was produced. Activity is a provenance log. Only Memory needs mutability for learning.

**Implementation**:
- `final_content` written once, never updated
- `status` uses state machine transitions, never regresses
- Memory upserts happen via `_upsert_memory()` with confidence comparison

---

### 7. Non-Fatal Logging

**Principle**: Activity writes are wrapped in `try/except pass` everywhere. The provenance log is valuable but never mission-critical. A log failure is a missing entry, not a broken pipeline.

**Why**: Activity (Layer 2) exists to improve quality (recent activity in prompts, pattern detection), not to enable core functionality. If an activity write fails, the primary operation (deliverable run, platform sync, chat turn) must still succeed.

**Implementation**:
- All `write_activity()` calls wrapped in `try/except` with pass or warning log
- Service-role writes only (users cannot INSERT/UPDATE/DELETE)
- Activity reads are defensive (handle empty result sets)

**Example** (from `deliverable_execution.py`):
```python
try:
    write_activity(
        client=client,
        user_id=user_id,
        event_type="deliverable_run",
        summary=f"Generated {deliverable.get('title')}",
        metadata=metadata,
    )
except Exception:
    pass  # Non-fatal — a log failure doesn't fail the deliverable run
```

---

### 8. Headless Execution

**Principle**: Work is produced by a scheduler that runs without a user session. It depends only on credentials stored in `platform_connections`. The user does not need to be online.

**Why**: Deliverables are scheduled, automated outputs. The system must run reliably on cron without requiring an active user session.

**Implementation**:
- `unified_scheduler.py` runs every 5 minutes (Render Cron Job)
- Decrypts OAuth credentials from `platform_connections` at execution time
- Fetches live platform data via API clients (Google, Notion, Slack MCP)
- LLM call via `DeliverableAgent`
- Version creation, activity write, delivery all headless
- Email notification sent to user after generation (optional)

**User control**: Users configure deliverables (sources, schedule, destination) and review staged versions, but execution itself is fully automated.

---

## Consequences

### Positive

1. **Architectural clarity**: Future development can reference these principles to guide design decisions
2. **Consistency**: Subsystems built on these principles will interoperate predictably
3. **Quality improvement**: Bidirectional learning ensures the system gets better with usage
4. **Scalability**: Weighting shift enables new users to get value immediately while mature users benefit from accumulated intelligence
5. **Reliability**: Boundary-based writes and non-fatal logging prevent cascading failures

### Trade-offs

1. **Complexity**: Bidirectional flow (generation down, learning up) is harder to reason about than unidirectional flow
2. **Latency**: Boundary-based writes mean learning is not real-time (acceptable trade-off for predictability)
3. **Token cost**: Layer 4 content integration adds 2,500-3,500 tokens per signal processing cycle (acceptable for quality gain)

### Mitigations

- Documentation hardening (this ADR, four-layer-model.md updates) makes complexity navigable
- Batch jobs (midnight UTC cron) optimize latency vs freshness trade-off
- Token cost justified by measurable quality improvement in signal reasoning

---

## Design Guidance for Future Work

When building new features or modifying existing systems, ask:

1. **Does this respect the generation/learning flow separation?**
   - Generation should flow downward (L1→L2→L3→L4)
   - Learning should flow upward (L4→L1, L2→L1)

2. **Does this write at a defined boundary?**
   - Session end, approval, cron job — not mid-operation

3. **Does this contribute to the quality flywheel?**
   - Does Layer 4 content inform future work?
   - Does user behavior feed back into Memory?

4. **Does this respect immutability constraints?**
   - Work versions immutable after generation
   - Activity append-only
   - Memory mutable only at boundaries

5. **Does this handle weighting shift over time?**
   - New users: rely on L1+L3
   - Mature users: rely on L4
   - Does the feature improve with tenure?

6. **Does this maintain separation of freshness and authority?**
   - Cache for conversation
   - Live APIs for generation
   - No cross-contamination

---

## Related

- [ADR-063: Four-Layer Model](ADR-063-activity-log-four-layer-model.md) — Architectural foundation
- [ADR-064: Implicit Memory Extraction](ADR-064-unified-memory-service.md) — Learning from conversation, feedback, patterns
- [ADR-068: Signal-Emergent Deliverables](ADR-068-signal-emergent-deliverables.md) — Signal processing orchestration
- [ADR-069: Layer 4 Content Integration](ADR-069-layer-4-content-in-signal-reasoning.md) — Work as training signal
- [ADR-070: Enhanced Activity Pattern Detection](ADR-070-enhanced-activity-pattern-detection.md) — 5 pattern types from Activity
- [Four-Layer Model Architecture](../architecture/four-layer-model.md) — Comprehensive architectural overview with bidirectional learning diagrams

---

## Acceptance Criteria

✅ Strategic principles extracted from implementation work
✅ Principles are both descriptive (what exists) and prescriptive (what future work should follow)
✅ Design guidance provided for future development
✅ Consequences and trade-offs documented
✅ References to implementing ADRs included

This ADR serves as the strategic companion to ADR-063 (four-layer model structure) by documenting the architectural philosophy behind the structure.
