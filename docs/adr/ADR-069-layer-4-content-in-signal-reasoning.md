# ADR-069: Layer 4 Content Integration in Signal Processing

**Date**: 2026-02-20
**Status**: Accepted
**Extends**: ADR-068 (Signal-Emergent Deliverables)
**Relates to**: ADR-063 (Four-Layer Model), ADR-061 (Two-Path Architecture)

---

## Context

### The Gap

Signal processing (ADR-068) currently reads Layer 4 (Work) **metadata only**:
- `id`, `title`, `deliverable_type`, `next_run_at`, `status`

It does NOT read:
- `deliverable_versions.draft_content` — LLM-generated output
- `deliverable_versions.final_content` — User-edited or final version
- Version creation timestamps
- Quality metrics

This means signal reasoning operates on deliverable **existence**, not deliverable **output**.

### Why This Matters

The signal processing LLM cannot:
1. **Assess staleness**: Is the existing meeting_prep deliverable configured for different attendees from 2 weeks ago?
2. **Determine coverage**: Did a recent deliverable already address this signal?
3. **Make quality-aware decisions**: Should we trigger_existing (reuse configuration) or create_signal_emergent (novel one-time work)?
4. **Reference accumulated intelligence**: What has the system already synthesized about this topic/person/context?

The decision to `trigger_existing` vs `create_signal_emergent` is currently based only on **type matching**, not **content relevance**.

### Strategic Principle

The four-layer model (ADR-063) establishes that **Layer 4 (Work) accumulates intelligence over time**. As user tenure increases, Layer 4 becomes the richest signal input:

- **New user (0-30 days)**: Layer 1 (Memory) + Layer 3 (Context) carry most reasoning load. Layer 4 is sparse.
- **Mature user (90+ days)**: Layer 4 (accumulated intelligence) is the richest signal. The system reasons over months of synthesized artifacts.

Signal processing must read Layer 4 content to implement this weighting shift.

---

## Decision

### What Changes

Signal processing now fetches and reasons over recent deliverable version content.

**Database Query** (unified_scheduler.py):
```python
existing_deliverables = (
    supabase.table("deliverables")
    .select("""
        id, title, deliverable_type, next_run_at, status,
        deliverable_versions!inner(
            final_content,
            draft_content,
            created_at,
            status
        )
    """)
    .eq("user_id", user_id)
    .in_("status", ["active", "paused"])
    .order("deliverable_versions(created_at)", desc=True)
    .execute()
)
```

**Content Extraction**:
- Most recent version per deliverable
- Prefer `final_content` (user-edited) over `draft_content`
- Include version creation timestamp for recency assessment

**Prompt Enhancement** (signal_processing.py):
- EXISTING DELIVERABLES section now includes:
  - First 400 characters of recent content
  - Days since last output ("today", "yesterday", "N days ago")
- System prompt updated with "LAYER 4 CONTENT USAGE" section instructing the model to:
  - Assess staleness
  - Check if recent work already covers the signal
  - Prefer create_signal_emergent over trigger_existing when content is stale

### Token Budget Impact

Each deliverable with recent content adds **~250-350 tokens** to the reasoning prompt:
- Content preview: 200-300 tokens (400 chars ≈ 100-150 tokens, formatted adds overhead)
- Metadata: 50 tokens

For a user with 10 active deliverables, this adds **~2,500-3,500 tokens** to the signal processing LLM call.

This is acceptable. The quality improvement from content-aware reasoning justifies the cost.

### Example Reasoning Flow

**Before (metadata only)**:
```
EXISTING DELIVERABLES:
- Weekly Team Update (meeting_prep, next run: 2026-02-27)

Signal: Meeting with Alice tomorrow (external attendee)
Decision: trigger_existing (type matches)
Problem: Weekly Team Update is for internal standup, not Alice meeting
```

**After (with content)**:
```
EXISTING DELIVERABLES:
- Weekly Team Update (meeting_prep, next run: 2026-02-27)
    Last output (14 days ago): Weekly standup agenda for internal team...

Signal: Meeting with Alice tomorrow (external attendee)
Decision: create_signal_emergent (existing deliverable is for different context)
Reasoning: The recurring meeting_prep is for weekly internal standup (last output confirms this).
           This signal warrants a one-time prep brief specific to Alice meeting.
```

---

## Architectural Principle

This implements a foundational strategic principle:

> **Signal processing reasoning quality is a function of Layer 4 content depth.**

As the user accumulates deliverable history:
- Signal processing can reference what the system has previously synthesized
- Decisions improve from type-based matching to content-based relevance
- The system builds on its own accumulated intelligence

This is the **learning loop** in action:
1. Signal processing creates deliverable
2. Deliverable execution produces Layer 4 content
3. Future signal processing cycles read that content
4. Reasoning improves

---

## Implementation

**Files Changed**:
1. `api/jobs/unified_scheduler.py` (~line 1023)
   - Updated deliverable query to join deliverable_versions
   - Extract most recent version content per deliverable

2. `api/services/signal_processing.py` (~line 379)
   - Enhanced prompt formatting to include content preview
   - Added recency calculation (days since last output)
   - Updated system prompt with Layer 4 usage guidance

**Backwards Compatibility**:
- If a deliverable has no versions, content fields are `None`
- Prompt gracefully handles missing content (no preview shown)
- No schema changes required

---

## Consequences

### Positive

1. **Quality-aware orchestration**: `trigger_existing` vs `create_signal_emergent` decisions based on content relevance, not just type matching
2. **Staleness detection**: System knows when recurring deliverable configuration has drifted from current signals
3. **Intelligence accumulation**: Signal processing builds on past synthesis, not just raw platform signals
4. **Mature user value**: As Layer 4 grows, signal reasoning improves automatically
5. **Deduplication improvement**: "Did recent work already cover this?" becomes answerable

### Negative

1. **Token cost**: +2,500-3,500 tokens per user per signal processing cycle (10 deliverables with content)
2. **Query complexity**: Join on deliverable_versions adds database overhead (mitigated by index on deliverable_id + created_at)
3. **Prompt length**: Longer prompts may approach context limits for users with 20+ active deliverables (rare)

### Mitigations

- Token cost is acceptable for the quality gain
- Database query uses existing indexes (deliverable_id, created_at already indexed)
- Prompt length capped at 10 deliverables max (reasonable limit)

---

## Alternatives Considered

### Option A: Metadata-only with version count

Add `version_count` and `last_version_date` to deliverable metadata without fetching content.

**Rejected**: Doesn't solve the staleness or coverage problem. We still can't assess what the deliverable produces.

### Option B: Full version history (last 5 versions)

Fetch last 5 versions per deliverable to show trend.

**Rejected**: Excessive token cost (~10,000+ tokens). Most recent version is sufficient for staleness assessment.

### Option C: Separate content summary table

Pre-compute 100-char summaries of deliverable outputs in a separate table, query that instead of raw content.

**Rejected**: Adds schema complexity. Content preview extraction is cheap and doesn't require pre-computation.

---

## Open Questions

1. **Content length limit**: 400 chars is a heuristic. Should this be tunable per deliverable type?
2. **Summarization**: For very long deliverables (5,000+ word research briefs), should we pre-summarize instead of truncating?
3. **Quality metrics**: Should we also pass `quality_score` (edit distance) to inform confidence?

These are deferred. Current implementation is sufficient for Phase 1.

---

## Related

- [ADR-068: Signal-Emergent Deliverables](ADR-068-signal-emergent-deliverables.md)
- [ADR-063: Four-Layer Model](ADR-063-activity-log-four-layer-model.md)
- [Four-Layer Model Architecture](../architecture/four-layer-model.md)
- [Signal Taxonomy](../architecture/signal-taxonomy.md)
