# Changelog

All notable changes to YARNNN are documented here.

---

## [Unreleased]

### ADR-042: Deliverable Execution Simplification

**Date**: 2026-02-11

A significant architectural simplification of the deliverable execution model, moving from a 3-step chained pipeline to a single Execute call.

#### Breaking Changes

- **Pipeline replacement**: `execute_deliverable_pipeline()` is deprecated. All entry points now use `execute_deliverable_generation()` from `services/deliverable_execution.py`.

#### What Changed

| Before (ADR-018) | After (ADR-042) |
|------------------|-----------------|
| 3-step pipeline (gather → synthesize → stage) | Single `execute_deliverable_generation()` call |
| 3 work_tickets per generation with chaining | 1 work_ticket per generation, no chaining |
| Feedback engine computed on every approval | Deferred - just saves draft + final |
| Context snapshots via separate table | Input logging via `work_execution_log` |

#### Files Changed

**New**:
- `api/services/deliverable_execution.py` - Simplified execution module

**Modified**:
- `api/services/primitives/execute.py` - `_handle_deliverable_generate()` uses new flow
- `api/jobs/unified_scheduler.py` - `process_deliverable()` uses new flow
- `api/services/event_triggers.py` - `execute_matched_deliverables()` uses new flow
- `api/routes/deliverables.py` - `/run` endpoint uses new flow
- `api/services/project_tools.py` - `handle_run_deliverable()` uses new flow
- `api/workers/deliverable_worker.py` - Marked deprecated, forwards to new flow

**Preserved** (in `deliverable_pipeline.py`):
- `fetch_integration_source_data()` - Source fetching utilities
- `extract_with_haiku()` - Cost-effective extraction
- `TYPE_PROMPTS`, `build_type_prompt()` - Type-specific prompts
- `validate_output()` - Output validation
- `get_past_versions_context()` - Historical context

**Deprecated** (in `deliverable_pipeline.py`):
- `execute_deliverable_pipeline()` - 3-step orchestrator
- `execute_gather_step()` - Separate gather work_ticket
- `execute_synthesize_step()` - Separate synthesize work_ticket
- `execute_stage_step()` - Validation/staging step

#### Schema Impact

**No migrations required**. The existing schema supports both flows:

| Column | Before | After |
|--------|--------|-------|
| `work_tickets.depends_on_work_id` | Populated for chaining | NULL |
| `work_tickets.pipeline_step` | 'gather'/'synthesize'/'stage' | NULL |
| `work_tickets.chain_output_as_memory` | TRUE for gather step | FALSE |
| `deliverable_versions.edit_diff` | Computed on approval | NULL (deferred) |
| `deliverable_versions.edit_distance_score` | Computed on approval | NULL (deferred) |
| `deliverable_versions.context_snapshot_id` | Populated | NULL (deferred) |

#### Entity Type Clarification

Updated `primitives.md` to clarify entity tiers:

**TP-Facing (6)**:
- `deliverable`, `platform`, `document`, `work`, `session`, `action`

**Background (3)**:
- `memory`, `platform_content`, `domain`

#### Rationale

The 3-step pipeline was designed for:
1. Multi-minute stages requiring intermediate caching
2. Immediate need for sophisticated edit-distance learning
3. Full context snapshot capture for reproducibility

None of these requirements materialized. The simplification:
- Reduces complexity (one code path instead of three)
- Improves debuggability (less indirection)
- Preserves optionality (schema columns remain for future use)

See [ADR-042](docs/adr/ADR-042-deliverable-execution-simplification.md) for full details.

---

## Previous Versions

### ADR-039: Unified Context Surface
**Date**: 2026-02-11

Frontend integration for unified context visualization.

### ADR-038: Claude Code Architecture Mapping
**Date**: 2026-02-10 - 2026-02-11

- Phase 1: Filesystem-as-context implementation
- Phase 2: Single storage layer (memories table unification)
- Manual context as first-class citizen

### ADR-035: Platform-First Type System
**Date**: 2026-02-09

Wave 1 platform-native types:
- `slack_channel_digest`
- `slack_standup`
- `gmail_inbox_brief`
- `notion_page_summary`

### ADR-034: Projects Removed
**Date**: 2026-02-08

Deliverables are now user-scoped, not project-scoped. Domain-based context scoping replaces project hierarchy.

### ADR-028: Destination-First Deliverables
**Date**: 2026-02-05

Governance model (manual/semi_auto/full_auto) tied to destination type.

### ADR-018: Recurring Deliverables Product Pivot
**Date**: 2026-02-01

Original deliverable architecture with 3-step pipeline. Superseded by ADR-042 for execution model.
