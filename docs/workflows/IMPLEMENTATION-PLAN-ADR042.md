# Implementation Plan: ADR-042 Deliverable Execution Simplification

> **Status**: Ready for Discourse
> **Date**: 2026-02-11
> **Related**: [ADR-042](../adr/ADR-042-deliverable-execution-simplification.md)

---

## Summary

Simplify deliverable execution from a 3-step chained pipeline to a single Execute call. No schema changes—grow into existing columns when needed.

---

## Current vs. Target State

### Current Flow (ADR-018)

```
Scheduler / TP Request
    ↓
execute_deliverable_pipeline()
    ├─ execute_gather_step()    → work_ticket #1 (pipeline_step=gather)
    │      └─ Fetch sources, MCP calls, Haiku extraction
    ├─ execute_synthesize_step() → work_ticket #2 (depends_on=#1, pipeline_step=synthesize)
    │      └─ Build prompt, LLM call, generate draft
    └─ execute_stage_step()      → work_ticket #3 (pipeline_step=stage)
           └─ Validate, update version, notify

3 work_tickets, chained dependencies, ~1800 lines of pipeline code
```

### Target Flow (ADR-042)

```
TP: Execute(action="deliverable.generate", target="deliverable:uuid")
    ↓
_handle_deliverable_generate()
    1. Read deliverable config
    2. Gather context (inline)
    3. Generate draft (single LLM call)
    4. Create deliverable_version (status=staged)
    5. Create work_ticket (single, action=deliverable.generate)
    6. Log inputs to work_execution_log
    7. Return draft to TP

1 work_ticket, no dependencies, simplified flow
```

---

## Files to Modify

### 1. `api/services/primitives/execute.py`

**Changes**:
- Rewrite `_handle_deliverable_generate()` to inline the simplified flow
- Add input logging via `work_execution_log`

**Current** (lines 286-326): Delegates to job queue

**Target**:
```python
async def _handle_deliverable_generate(auth, entity, ref, via, params):
    """Generate deliverable - simplified single-call flow (ADR-042)."""
    from services.deliverable_pipeline import (
        gather_context_inline,
        generate_draft_inline,
        get_next_version_number,
    )

    deliverable_id = entity.get("id")

    # 1. Get next version
    next_version = await get_next_version_number(auth.client, deliverable_id)

    # 2. Create version (generating)
    version = await create_version_record(auth.client, deliverable_id, next_version)

    # 3. Create single work_ticket
    ticket = await create_work_ticket(
        auth.client,
        user_id=auth.user_id,
        action="deliverable.generate",
        deliverable_id=deliverable_id,
        deliverable_version_id=version["id"],
        # NULL: depends_on_work_id, pipeline_step, chain_output_as_memory
    )

    # 4. Log inputs for debugging (ADR-042)
    await log_execution_inputs(ticket["id"], entity)

    # 5. Gather + Generate (inline, not separate steps)
    context = await gather_context_inline(auth, entity)
    draft = await generate_draft_inline(auth, entity, context)

    # 6. Update version → staged
    await update_version_staged(auth.client, version["id"], draft)

    # 7. Complete ticket
    await complete_work_ticket(auth.client, ticket["id"], {"draft_length": len(draft)})

    return {
        "status": "staged",
        "version_id": str(version["id"]),
        "version_number": next_version,
        "draft": draft,
        "message": f"Version {next_version} ready for review",
    }
```

### 2. `api/services/deliverable_pipeline.py`

**Keep**:
- `fetch_integration_source_data()` - Source fetching utilities
- `extract_with_haiku()` - Cost-effective extraction
- `TYPE_PROMPTS` - Type-specific prompts
- `SECTION_TEMPLATES` - Section definitions
- `build_type_prompt()` - Prompt builder
- `validate_output()` - Output validation
- `get_past_versions_context()` - Historical context

**Add**:
```python
async def gather_context_inline(auth, deliverable: dict) -> str:
    """
    ADR-042: Inline context gathering.

    Combines what execute_gather_step did without creating work_tickets.
    Returns gathered context as string.
    """
    sources = deliverable.get("sources", [])
    context_parts = []

    for source in sources:
        source_type = source.get("type")
        if source_type == "integration_import":
            result = await fetch_integration_source_data(
                auth.client,
                auth.user_id,
                source,
                last_run_at=deliverable.get("last_run_at"),
                deliverable_id=deliverable.get("id"),
            )
            if result.content:
                context_parts.append(result.content)
        elif source_type == "url":
            # Existing URL fetch logic
            pass
        elif source_type == "document":
            # Existing document fetch logic
            pass

    # Add user memories
    memories = await get_relevant_memories(auth.client, auth.user_id, deliverable)
    if memories:
        context_parts.append(format_memories(memories))

    return "\n\n---\n\n".join(context_parts)


async def generate_draft_inline(auth, deliverable: dict, context: str) -> str:
    """
    ADR-042: Inline draft generation.

    Single LLM call with gathered context.
    Returns generated draft.
    """
    from services.anthropic import chat_completion

    deliverable_type = deliverable.get("deliverable_type", "custom")
    type_config = deliverable.get("type_config", {})

    prompt = build_type_prompt(
        deliverable_type=deliverable_type,
        config=type_config,
        gathered_context=context,
        deliverable=deliverable,
    )

    draft = await chat_completion(
        messages=[{"role": "user", "content": prompt}],
        system="You are generating a deliverable. Follow the format and instructions exactly.",
        model=SONNET_MODEL,
        max_tokens=4000,
    )

    return draft.strip()
```

**Deprecate** (mark with `# ADR-042: Deprecated, kept for backwards compatibility`):
- `execute_deliverable_pipeline()` - Full 3-step orchestrator
- `execute_gather_step()` - Separate gather work_ticket
- `execute_synthesize_step()` - Separate synthesize work_ticket
- `execute_stage_step()` - Separate stage step
- `save_as_memory()` - Output-to-memory conversion (defer to v2)

### 3. `api/routes/deliverables.py`

**Changes** to `POST /deliverables/:id/run`:
- Currently calls `execute_deliverable_pipeline()`
- Change to call Execute primitive directly or use simplified inline function

```python
@router.post("/{deliverable_id}/run")
async def run_deliverable(
    deliverable_id: UUID,
    auth: UserClient = Depends(get_user_client),
):
    """Trigger ad-hoc deliverable run."""
    # Get deliverable
    deliverable = await get_deliverable(auth.client, str(deliverable_id))
    if not deliverable:
        raise HTTPException(404, "Deliverable not found")

    # Use simplified inline generation (ADR-042)
    from services.deliverable_pipeline import (
        gather_context_inline,
        generate_draft_inline,
        get_next_version_number,
    )

    next_version = await get_next_version_number(auth.client, str(deliverable_id))
    version = await create_version(auth.client, str(deliverable_id), next_version)

    # Single ticket, no chaining
    ticket = await create_work_ticket(...)

    context = await gather_context_inline(auth, deliverable)
    draft = await generate_draft_inline(auth, deliverable, context)

    await update_version_staged(auth.client, version["id"], draft)
    await complete_ticket(auth.client, ticket["id"])

    return {"version_id": version["id"], "status": "staged"}
```

### 4. Scheduler Changes

**File**: `api/services/scheduler.py` (if exists) or background worker

**Current**: Calls `execute_deliverable_pipeline()`

**Target**: Call simplified inline functions or Execute primitive

---

## Non-Changes (Schema Preserved)

| Table | Columns | Status |
|-------|---------|--------|
| `deliverable_versions` | `edit_diff`, `edit_categories`, `edit_distance_score`, `context_snapshot_id`, `pipeline_run_id` | Remain NULL |
| `work_tickets` | `depends_on_work_id`, `pipeline_step`, `chain_output_as_memory` | Remain NULL |
| `work_execution_log` | All columns | Used for input logging |

---

## Testing Strategy

### Unit Tests

1. **`test_execute_deliverable_generate_simplified`**
   - Verify single work_ticket created
   - Verify version status transitions: generating → staged
   - Verify no `depends_on_work_id` populated

2. **`test_gather_context_inline`**
   - Verify source fetching works
   - Verify Haiku extraction still applies
   - Verify memories included

3. **`test_approval_without_feedback_engine`**
   - Approve with edits → both `draft_content` and `final_content` saved
   - Verify `edit_distance_score` remains NULL

### Integration Tests

1. **Full flow**: Create deliverable → Generate → Review → Approve
2. **Verify governance**: `full_auto` still works (auto-approve, deliver)
3. **Verify type prompts**: Different types produce correct output

---

## Migration Path

1. **Phase 1**: Add new inline functions alongside existing pipeline
2. **Phase 2**: Switch Execute handler to use inline functions
3. **Phase 3**: Switch `/run` endpoint to use inline functions
4. **Phase 4**: Mark old pipeline functions as deprecated
5. **Phase 5**: Remove deprecated functions after validation period

Feature flag: `SIMPLE_PIPELINE=true` (optional, for gradual rollout)

---

## Rollback Plan

If issues arise:
1. Revert Execute handler to call job queue
2. Old `execute_deliverable_pipeline()` still works
3. Schema unchanged, data preserved

---

## Open Questions for Discourse

1. **Scheduler integration**: Does scheduler need to change, or does it already go through Execute?

2. **Event triggers (ADR-031)**: Event-triggered generations currently call `execute_deliverable_pipeline()`. Should they use Execute primitive instead?

3. **Background execution**: For long-running generations, should we keep foreground or switch to background? Current implementation is synchronous.

4. **Validation step**: `execute_stage_step()` runs `validate_output()`. Keep validation inline or make it optional?

---

## Estimated Effort

| Phase | Work | Time |
|-------|------|------|
| Add inline functions | New code in deliverable_pipeline.py | 2-3 hours |
| Modify Execute handler | Update execute.py | 1-2 hours |
| Update routes | Modify /run endpoint | 1 hour |
| Testing | Unit + integration | 2-3 hours |
| Documentation | Update workflow docs | 1 hour |
| **Total** | | **~1 day** |

---

## Success Criteria

- [ ] Single work_ticket per generation
- [ ] No `depends_on_work_id` populated
- [ ] Version fields `edit_diff`, `edit_distance_score` remain NULL
- [ ] Input logging via `work_execution_log`
- [ ] All existing tests pass
- [ ] Type-specific prompts still work
- [ ] Governance (manual/semi_auto/full_auto) still works
