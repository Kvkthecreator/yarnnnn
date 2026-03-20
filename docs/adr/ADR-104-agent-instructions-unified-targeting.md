# ADR-104: Agent Instructions as Unified Targeting Layer

**Date:** 2026-03-10
**Status:** Implemented (instructions migrated to workspace AGENT.md per ADR-106; dual-injected into system prompt + user message)
**Related:**
- [ADR-087: Agent Scoped Context](ADR-087-workspace-scoping-architecture.md) — introduced `agent_instructions`
- [ADR-093: Type Taxonomy](ADR-093-agent-type-taxonomy.md) — 7 type prompt templates
- [ADR-101: Agent Intelligence Model](ADR-101-agent-intelligence-model.md) — four-layer model (Skills / Directives / Memory / Feedback)

---

## Problem

Agent outputs are too broad and general. A Slack Recap covering #daily-work produces content that is "neither good nor bad — just not specific enough." The system knows *where* to look (sources) and *what format* to use (type prompts) but has no mechanism for users to say *what matters* within those sources.

Multiple targeting mechanisms were designed but never wired:

1. **`DataSource.scope`** — `IntegrationSourceScope` with `mode`, `fallback_days`, `recency_days`, `max_items`, `include_threads`, `include_sent`, `max_depth`. Stored in agent `sources[]` JSONB, never read by any execution code.

2. **`DataSource.filters`** — `IntegrationImportFilters` with `from`, `subject_contains`, `after`, `channel_id`, `page_id`. Stored, never read.

3. **`template_structure`** — `{sections, typical_length, tone, format_notes}`. Stored on agents, never consumed by `build_type_prompt()`.

4. **`platform_variant`** — Legacy field on agents. Not consumed.

5. **Dead `type_config` fields** — Many `TypeConfig` fields defined in TypeScript but never consumed by `build_type_prompt()`:
   - `DigestConfig.max_items`
   - `BriefConfig.*` (all four fields: `event_title`, `attendees`, `focus_areas`, `depth`)
   - `WatchConfig.threshold_notes`
   - `DeepResearchConfig.*` (all four fields: `focus_area`, `subjects`, `purpose`, `depth`)
   - `CustomConfig.example_content`

6. **`RecipientContext.notes`** — Defined in interface, stored, but `generate_draft_inline()` never reads `.notes`.

7. **`TypeClassification.platform_grounding`** — Array of `{platform, sources, instruction}`. Stored, never consumed by any strategy.

8. **`TypeClassification.freshness_requirement_hours`** — Defined, never read.

9. **`SECTION_TEMPLATES` + `build_sections_list()`** in `agent_pipeline.py` — Dead code. Never called by the execution pipeline.

Meanwhile, `agent_instructions` (ADR-087) already exists as a TEXT field on agents, is injected into the headless system prompt, is surfaced in TP working memory, can be edited via the Edit primitive and UI, and is seeded with type-appropriate defaults at creation time. It is the only targeting mechanism that is *actually wired end-to-end*.

The solution is not to add another targeting mechanism (per-source focus, structured filters) — that creates a dual approach. The solution is to make `agent_instructions` the *single* unified targeting layer and delete the dead infrastructure.

---

## Decision

### `agent_instructions` is the unified targeting layer

All user intent for "what this agent should focus on" flows through `agent_instructions`. No per-source scope, no structured filters, no template_structure. One field, fully wired.

### What instructions already do (no changes needed)

1. **Headless system prompt** — injected as `## Agent Instructions` in `_build_headless_system_prompt()` step 3
2. **TP working memory** — injected via `_extract_agent_scope()` as `scope["instructions"]`
3. **TP Edit primitive** — `Edit(ref="agent:{id}", changes={agent_instructions: "..."})` already works
4. **TP Create primitive** — `Write(ref="agent:new", ...)` seeds `DEFAULT_INSTRUCTIONS` by type
5. **UI editing** — Instructions panel in `AgentDrawerPanels.tsx` with debounced autosave

### What changes (this ADR)

#### Backend

1. **Delete dead infrastructure** — Remove all code and type definitions for: `DataSource.scope`, `DataSource.filters`, `template_structure`, `platform_variant`, `SECTION_TEMPLATES`, `build_sections_list()`, dead `type_config` fields, `RecipientContext.notes`, `TypeClassification.platform_grounding`, `TypeClassification.freshness_requirement_hours`.

2. **Inject instructions into content formatting** — `get_content_summary_for_generation()` currently returns a flat chronological dump with no awareness of what matters. Pass `agent_instructions` into the formatting function so it can include them as a preamble in the gathered context. This gives the headless agent both the raw content AND the user's stated priorities in the same user message — not just split across system prompt vs user message.

3. **Wire consumed type_config fields** — Fields that ARE consumed by `build_type_prompt()` remain. Dead ones are deleted from TypeScript interfaces. The consumed fields:
   - `DigestConfig`: `focus`, `reply_threshold`, `reaction_threshold`
   - `StatusConfig`: `subject`, `audience`, `detail_level`, `tone`
   - `WatchConfig`: `domain`, `signals`
   - `CoordinatorConfig`: `domain`, `dispatch_rules`
   - `CustomConfig`: `description`, `structure_notes`

#### Frontend (SEPARATE SCOPE — see note below)

4. **Instructions panel priority** — Move from tab #4 to tab #1 or make always-visible. Default drawer open. This is the primary user interaction surface for agent targeting.

5. **Remove dead UI fields** — Any UI that writes to `scope`, `filters`, `template_structure`, or dead `type_config` fields should be removed.

> **Frontend changes are out of scope for this ADR's implementation pass.** They require separate discourse on interaction design, drawer behavior, and create-flow UX. The backend changes are self-contained and do not break the existing frontend — dead fields simply stop being stored.

---

## Implementation

### Phase 1: Delete dead backend infrastructure

**`api/services/agent_pipeline.py`:**
- Delete `SECTION_TEMPLATES` dict (~lines 396-435)
- Delete `build_sections_list()` function (~line 463)
- Delete `LENGTH_GUIDANCE` entries only used by dead types

**`api/services/execution_strategies.py`:**
- No changes — strategies don't read scope/filters (confirming they're dead)

**`api/services/platform_content.py`:**
- No changes — `get_content_for_agent()` doesn't read scope/filters (confirming dead)

### Phase 2: Inject instructions into gathered context preamble

**`api/services/agent_execution.py`:**
- In `generate_draft_inline()`, pass `agent_instructions` to the type prompt assembly so instructions appear in the user message as well as the system prompt. This dual injection is intentional — instructions in the system prompt set behavioral constraints, instructions in the user message give the LLM a priority lens for the gathered content.

**`api/services/agent_pipeline.py`:**
- Add `{instructions}` slot to TYPE_PROMPTS templates and populate it in `build_type_prompt()`.

### Phase 3: Clean up TypeScript interfaces (frontend scope — deferred)

**`web/types/index.ts`:**
- Remove `IntegrationSourceScope` interface
- Remove `IntegrationImportFilters` interface
- Remove `scope` and `filters` from `DataSource`
- Remove `template_structure` from `Agent`, `AgentCreate`, `AgentUpdate`
- Remove `platform_variant` from `Agent`
- Remove dead fields from type config interfaces (`DigestConfig.max_items`, all `BriefConfig`, `WatchConfig.threshold_notes`, all `DeepResearchConfig`, `CustomConfig.example_content`)
- Remove `notes` from `RecipientContext`
- Remove `platform_grounding` and `freshness_requirement_hours` from `TypeClassification`

### Phase 4: Frontend UX (separate discourse)

- Instructions panel as default/primary tab
- Drawer default open on agent detail page
- Instructions prominent in create flow
- Dead UI fields removed

---

## What This Does NOT Change

- **`type_config` consumed fields** — `focus`, `reply_threshold`, `subject`, `audience`, etc. These are Skills layer (ADR-101) and stay on `type_config` JSONB.
- **`agent_memory`** — Observations, goals, review_log. This is Memory layer (ADR-101) and is orthogonal to targeting.
- **`recipient_context`** — `name`, `role`, `priorities` remain consumed. Only `notes` is dead.
- **Headless system prompt composition** — Still follows ADR-101 order. Instructions are now additionally present in the user message (dual injection).
- **Content fetching logic** — `get_content_for_agent()` continues to fetch by `(platform, resource_id)` with recency ordering. Instructions don't change *what* is fetched — they change *how the agent interprets* what was fetched.
- **Frontend functionality** — All frontend changes deferred. Current UI continues to work; dead fields are simply no longer consumed.

---

## Verification

1. **Dead code deletion** — All modified Python files compile cleanly
2. **Instruction dual injection** — Run a agent, inspect the assembled user message (type prompt). Instructions should appear both in system prompt and user message.
3. **TP cognizance** — In agent-scoped chat, TP should reference instructions from working memory. In generic chat, TP can read/edit instructions via primitives.
4. **No regression** — Existing agents with empty instructions continue to work (DEFAULT_INSTRUCTIONS seeded at creation, empty string handled gracefully)
