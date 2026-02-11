# ADR-042: Deliverable Execution Simplification

**Status**: Proposed
**Date**: 2026-02-11
**Supersedes**: Portions of ADR-018 (pipeline complexity), ADR-019 (feedback engine timing)
**Related**: ADR-036 (Two-Layer), ADR-039 (Background Work Agents)

---

## Context

ADR-018 introduced a 3-step chained pipeline for deliverable execution:

```
Gather (research agent) → Synthesize (content agent) → Stage (format/notify)
```

Each step created a separate `work_ticket` with dependency chaining (`depends_on_work_id`, `pipeline_step`, `chain_output_as_memory`). The `deliverable_versions` table captured detailed feedback metrics (`edit_diff`, `edit_categories`, `edit_distance_score`, `context_snapshot_id`).

This architecture anticipated:
1. Multi-minute pipeline stages requiring intermediate caching
2. Immediate need for sophisticated edit-distance learning
3. Full context snapshot capture for reproducibility

**Reality check**: None of these requirements have materialized. The pipeline runs in seconds, not minutes. Users aren't editing drafts yet (no training data for feedback loop). Context snapshot debugging is premature optimization.

The schema columns aren't the problem—they sit empty with zero runtime cost. The problem is **implementation complexity**: multiple work_tickets per generation, chained dependencies, feedback computation on every approval, context snapshot infrastructure.

### Guiding Principle

**"Grow into the schema, don't tear it down."**

The schema is an asset. The columns exist via migrations 019/020/030/036. Empty columns don't confuse the model or slow anything down. Dropping them would be pointless churn.

The simplification is about **handler implementation**, not schema changes.

---

## Decision

### 1. Single Execute Call per Generation

Replace the 3-step pipeline with a single `deliverable.generate` Execute call:

```
User: "Generate my weekly update"
    ↓
TP: Execute(action="deliverable.generate", target="deliverable:uuid-123")
    ↓
Execute handler:
  1. Read deliverable config (sources, recipient_context, template_structure)
  2. Gather source content (already in context, or Read from platforms)
  3. Generate draft via LLM
  4. Create deliverable_version row (status=staged, draft_content=output)
  5. Create work_ticket row (single row, action=deliverable.generate)
  6. Return draft to TP
    ↓
TP: "Here's your weekly update draft. [shows content] Want me to publish it?"
```

One Execute call. One work_ticket. One version row.

### 2. Minimal Version Population

When creating `deliverable_versions`, populate only:

| Column | Populate | Notes |
|--------|----------|-------|
| `deliverable_id` | ✓ | Required FK |
| `version_number` | ✓ | Sequential, cheap ordering |
| `status` | ✓ | `generating` → `staged` → `approved/rejected` |
| `draft_content` | ✓ | LLM output |
| `final_content` | ✓ | Copy of draft if approved without edits, or edited version |
| `created_at` | ✓ | Auto |
| `staged_at` | ✓ | When generation completes |
| `approved_at` | ✓ | When user approves |
| `edit_diff` | NULL | v2 |
| `edit_categories` | NULL | v2 |
| `edit_distance_score` | NULL | v2 |
| `context_snapshot_id` | NULL | Defer |
| `pipeline_run_id` | NULL | No longer relevant |
| `feedback_notes` | ✓ | If user provides explicit feedback |

### 3. Single Work Ticket per Execution

When logging execution, create one `work_ticket`:

| Column | Value |
|--------|-------|
| `action` | `deliverable.generate` |
| `status` | `pending` → `running` → `completed/failed` |
| `deliverable_id` | FK to deliverable |
| `deliverable_version_id` | FK to version being generated |
| `result` | Generation result summary |
| `depends_on_work_id` | NULL (no chaining) |
| `pipeline_step` | NULL (no pipeline) |
| `chain_output_as_memory` | FALSE |

### 4. Defer Feedback Engine

The feedback engine requires a training set that doesn't exist. Defer edit-distance computation until:
- Users are consistently editing drafts before approval
- There's enough data (10+ versions per deliverable) to learn patterns

**For now**: When user approves with edits (`final_content` differs from `draft_content`), save both. That's data hygiene. Don't compute diffs or categorize edits.

### 5. Input Logging Instead of Context Snapshots

Instead of full context snapshots, log key inputs in `work_execution_log`:

```json
{
  "stage": "started",
  "message": "Generating version 3",
  "metadata": {
    "sources_used": ["platform:slack:#engineering", "document:uuid-456"],
    "source_staleness_hours": {"slack": 2, "document": null},
    "active_memories_count": 12,
    "deliverable_type": "status_report"
  }
}
```

This provides 80% of debugging value at 5% of complexity.

---

## Implementation

### Phase 1: Simplify Execute Handler

Modify `api/services/primitives/execute.py`:

```python
async def _handle_deliverable_generate(auth, entity, ref, via, params):
    """Generate deliverable content - simplified single-call flow."""
    deliverable_id = entity.get("id")

    # 1. Get next version number
    next_version = await get_next_version_number(auth.client, deliverable_id)

    # 2. Create version record (status=generating)
    version = await create_version(auth.client, deliverable_id, next_version)

    # 3. Create single work_ticket
    ticket = await create_work_ticket(
        auth.client,
        action="deliverable.generate",
        deliverable_id=deliverable_id,
        deliverable_version_id=version.id,
    )

    # 4. Log inputs for debugging
    await log_execution(ticket.id, "started", {
        "sources": entity.get("sources", []),
        "type": entity.get("deliverable_type"),
    })

    # 5. Gather context (inline, not separate step)
    context = await gather_context(auth, entity)

    # 6. Generate draft
    draft = await generate_draft(auth, entity, context)

    # 7. Update version and ticket
    await update_version(auth.client, version.id,
        status="staged",
        draft_content=draft,
        staged_at=now()
    )
    await complete_ticket(auth.client, ticket.id, result={"draft_length": len(draft)})

    return {
        "status": "staged",
        "version_id": str(version.id),
        "version_number": next_version,
        "draft": draft,  # Return to TP for display
        "message": f"Version {next_version} ready for review",
    }
```

### Phase 2: Simplify Pipeline Service

Collapse `api/services/deliverable_pipeline.py`:
- Remove `execute_pipeline()` (3-step orchestration)
- Keep source fetching utilities (`fetch_integration_source_data`, etc.)
- Keep type-specific prompts (`TYPE_PROMPTS`)
- New: `gather_context()` - single function that gathers all sources
- New: `generate_draft()` - single LLM call with gathered context

### Phase 3: Approval Flow

```python
async def _handle_deliverable_approve(auth, entity, ref, via, params):
    version_id = params.get("version_id")
    edited_content = params.get("final_content")  # Optional: if user edited

    version = await get_version(auth.client, version_id)

    final = edited_content or version.draft_content

    await update_version(auth.client, version_id,
        status="approved",
        final_content=final,
        approved_at=now(),
        # Note: NOT computing edit_diff or edit_distance_score
    )

    return {"status": "approved", "version_id": version_id}
```

---

## Migration Path

1. **No schema changes** - All columns remain, just populated minimally
2. **Feature flag optional** - Could add `SIMPLE_PIPELINE=true` env var during transition
3. **Backwards compatible** - Old versions with populated columns remain valid

---

## Consequences

### Positive

1. **Reduced complexity** - One code path instead of three
2. **Faster iteration** - Less indirection when debugging
3. **Better model performance** - Fewer concepts for TP to understand
4. **Schema preserved** - No migrations, columns ready when needed

### Negative

1. **No intermediate caching** - If generation becomes slow, we'd need to add it back
   - Mitigation: This is the npm analogy - cache when builds take 20 minutes, not 20 seconds
2. **No feedback learning initially** - First 10 versions won't improve from edits
   - Mitigation: Type-specific prompts and rich context provide baseline quality

### Neutral

1. **Existing data unchanged** - Versions with populated columns keep their data
2. **Future expansion path clear** - When feedback loop is needed, columns are waiting

---

## Entity Type Alignment

Per discussion, TP-facing entity types should be 6:

| Entity | Table | TP-Facing | Notes |
|--------|-------|-----------|-------|
| `deliverable` | `deliverables` | ✓ | Primary |
| `platform` | `user_integrations` | ✓ | By provider name |
| `document` | `documents` | ✓ | Uploaded files |
| `work` | `work_tickets` | ✓ | Execution records |
| `session` | `chat_sessions` | ✓ | Chat history |
| `action` | (virtual) | ✓ | Available actions |
| `memory` | `memories` | Background | Cache, not TP-facing |
| `domain` | `context_domains` | Deferred | Future |
| `platform_content` | `ephemeral_context` | Background | Implicit in context |

Update `primitives.md` to reflect this hierarchy.

---

## What This Resolves

From the original discussion:

| Question | Resolution |
|----------|------------|
| deliverable_versions usage | Use as-is, populate minimally |
| Pipeline chaining | Skip for v1, single ticket per execution |
| Feedback engine | v2, just save draft + final for now |
| Context snapshots | Defer, log inputs as JSON in work_ticket |

---

## Open Questions

1. **Terminology**: Keep "deliverable" or rename to "task"/"job"?
   - Recommendation: Keep "deliverable" - semantically precise (delivered to someone, on schedule)

2. **Source freshness logging**: How detailed should input logging be?
   - Start with source list + staleness, expand if debugging needs it

---

## References

- [ADR-018: Recurring Deliverables](./ADR-018-recurring-deliverables.md) - Original pipeline design
- [ADR-019: Deliverable Types](./ADR-019-deliverable-types.md) - Type system
- [ADR-036: Two-Layer Architecture](./ADR-036-two-layer-architecture.md) - Primitives foundation
- [ADR-039: Background Work Agents](./ADR-039-background-work-agents.md) - work_execution_log
- [primitives.md](../architecture/primitives.md) - Execute primitive specification
- [deliverable_pipeline.py](../../api/services/deliverable_pipeline.py) - Current implementation
