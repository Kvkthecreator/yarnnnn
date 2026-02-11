# Changelog

All notable changes to YARNNN are documented here.

---

## [Unreleased]

### Agent Type Rename (ADR-045 Implementation)

**Date**: 2026-02-11

Renamed agent types to reflect their actual function:

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `research` | `synthesizer` | Synthesizes pre-fetched context into summaries |
| `content` | `deliverable` | Generates deliverable output (primary use case) |
| `reporting` | `report` | Generates standalone structured reports |

#### Breaking Changes

- Agent files renamed: `research.py` → `synthesizer.py`, `content.py` → `deliverable.py`, `reporting.py` → `report.py`
- New class names: `SynthesizerAgent`, `DeliverableAgent`, `ReportAgent`
- Database migration (038) updates existing `work_tickets.agent_type` values

#### Backwards Compatibility

- Factory (`agents/factory.py`) maps legacy names to new names
- API endpoints accept both old and new type names
- TypeScript types include both for compatibility

#### Files Changed

- `api/agents/synthesizer.py` — New (renamed from research.py)
- `api/agents/deliverable.py` — New (renamed from content.py)
- `api/agents/report.py` — New (renamed from reporting.py)
- `api/agents/factory.py` — Updated with legacy mapping
- `api/services/deliverable_execution.py` — Uses "deliverable" agent type
- `api/services/deliverable_pipeline.py` — Uses new agent types
- `api/routes/work.py` — Accepts both old and new types
- `web/types/index.ts` — Added `AgentType` with both old and new values
- `supabase/migrations/038_agent_type_rename.sql` — Data migration

---

### ADR-045: Deliverable Orchestration Redesign

**Date**: 2026-02-11

First-principles redesign of how deliverable types map to execution strategies and agent orchestration.

#### Key Insights

The current pipeline (SynthesizerAgent → DeliverableAgent) was designed for ADR-019's format-centric types before the platform-first shift (ADR-044). Types now have semantic meaning (binding, temporal pattern, freshness) that execution ignores.

#### What This ADR Proposes

| Binding | Orchestration Strategy |
|---------|----------------------|
| `platform_bound` | Single-platform gatherer → Platform-specific synthesizer |
| `cross_platform` | Parallel platform gatherers → Cross-platform synthesizer |
| `research` | Research agent with web search → Research synthesizer |
| `hybrid` | Research + Platform gatherers → Hybrid synthesizer |

#### New Primitives (Deferred)

- **WebSearch** — Search the web for external context
- **WebFetch** — Fetch and extract content from URLs

These are documented in `primitives.md` but not implemented until research-type deliverables require them.

#### New Deliverable Types (Deferred)

With web search capability, enables ADR-044's research types:
- `competitive_analysis`
- `market_landscape`
- `topic_deep_dive`
- `industry_brief`

#### Files

- `docs/adr/ADR-045-deliverable-orchestration-redesign.md` — Full ADR
- `docs/architecture/primitives.md` — Added "Deferred Primitives" section

---

### ADR-044: Deliverable Type Reconceptualization

**Date**: 2026-02-11

Reconceptualized deliverable types from format-centric (status_report, research_brief) to a two-dimensional classification model.

#### Type Classification Model

| Dimension | Values |
|-----------|--------|
| **Context Binding** | `platform_bound`, `cross_platform`, `research`, `hybrid` |
| **Temporal Pattern** | `reactive`, `scheduled`, `on_demand`, `emergent` |

#### New Platform-Bound Types

| Type | Platform | Description |
|------|----------|-------------|
| `slack_channel_digest` | Slack | What happened while you were away |
| `slack_standup` | Slack | Aggregate team standup updates |
| `gmail_inbox_brief` | Gmail | Prioritized inbox summary |
| `notion_page_summary` | Notion | What changed in your docs |

#### Emergent Deliverable Discovery

Database tables for TP to track user patterns and propose deliverables:
- `deliverable_proposals` — Tracks suggestions made by TP
- `user_interaction_patterns` — Tracks patterns that suggest deliverable value
- Helper functions: `increment_interaction_pattern()`, `should_propose_deliverable()`

#### Frontend Changes

- `TypeSelector.tsx` — Redesigned with binding-first flow (Platform Monitor → Cross-Platform → Research → Custom)
- `DeliverableCreateSurface.tsx` — Now passes `type_classification` when creating deliverables
- `DeliverableSettingsModal.tsx` — Added labels for new types

#### Schema Changes

```sql
-- Migration 037
ALTER TABLE deliverables ADD COLUMN type_classification JSONB;
CREATE TABLE deliverable_proposals (...);
CREATE TABLE user_interaction_patterns (...);
```

#### Files Changed

- `docs/adr/ADR-044-deliverable-type-reconceptualization.md` — New ADR
- `supabase/migrations/037_deliverable_type_classification.sql` — Schema changes
- `web/types/index.ts` — Added `TypeClassification`, `ContextBinding`, `TemporalPattern`
- `web/components/deliverables/TypeSelector.tsx` — Binding-first selector
- `web/components/surfaces/DeliverableCreateSurface.tsx` — Classification passthrough
- `web/components/modals/DeliverableSettingsModal.tsx` — New type labels

---

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
