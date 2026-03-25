# ADR-123: Project Objective & Ownership Model

> **Status**: Phases 1-4 Implemented (Complete)
> **Superseded by**: [ADR-138](ADR-138-agents-as-work-units.md) — Project layer collapsed. PM dissolved. Tasks replace projects.
> **Date**: 2026-03-19
> **Authors**: KVK, Claude
> **Extends**: ADR-120 (Project Execution), ADR-121 (PM Intelligence Director), ADR-122 (Project Type Registry)
> **Implements**: FOUNDATIONS.md Axiom 1 (project north star), Axiom 3 (agents develop inward)

---

## Context

ADR-120 Phase 4 introduced two concepts into PROJECT.md:

1. **`intent`** (singular) — a 4-field dict (`deliverable`, `audience`, `format`, `purpose`) describing what the project produces and why. Set at creation, treated as immutable.
2. **`intentions`** (plural) — a list of operational execution specs (`recurring`/`goal`/`reactive`) with triggers, delivery, budgets, deadlines. Mutable by PM via `UpdateProjectIntent`.

**The problems:**

1. **Naming collision**: "Intent" and "intentions" look like singular/plural of the same word. They are fundamentally different concerns — identity vs. operations — but the names suggest they're the same thing.

2. **Dual operational substrate**: PM has `## Intentions` in PROJECT.md AND `memory/work_plan.md` for operational planning. Two places for "how PM plans to execute." The `UpdateProjectIntent` primitive updates `intentions` in PROJECT.md, while PM's `update_work_plan` action writes to `memory/work_plan.md`. This violates singular implementation discipline.

3. **Misnamed primitive**: `UpdateProjectIntent` updates operational execution specs (`intentions`), not the project's identity (`intent`). The name lies about what it does.

4. **No user-facing configuration**: The user never directly shapes the project's purpose. It's either template-generated (bootstrap) or LLM-generated (Composer/TP). The user can't see or edit it. PM assesses quality against a north star the user never set.

5. **False immutability**: `intent` is treated as immutable in code (PM can't change it), but there's no principled reason why. A project's north star should evolve — "Weekly Slack Recap" can become "Weekly Communication Intelligence" as the user's needs sharpen. Immutability was an implementation default, not a design decision.

## Decision

### Terminology

| Current | New | What It Is |
|---------|-----|------------|
| `intent` (dict) | `objective` | Project north star — what, for whom, why, in what form |
| `intentions` (list in PROJECT.md) | Deleted — absorbed into PM's `memory/work_plan.md` | Operational execution specs |
| `UpdateProjectIntent` primitive | `UpdateWorkPlan` | PM updates its own operational plan |

### Ownership Model

**PROJECT.md is the charter** — owned by User, Composer, and TP:
- `## Objective` (was `## Intent`) — mutable north star
- `## Contributors` — who participates
- `## Assembly Spec` — how to combine contributions
- `## Delivery` — where output goes
- `## Status` — project lifecycle state

**PM memory/ is the operational plan** — owned by PM:
- `memory/work_plan.md` — absorbs former `## Intentions` content (recurring/goal/reactive specs, budget allocation, focus areas, timeline)
- `memory/quality_assessment.md` — contribution quality scoring (ADR-121)

**The principle**: The charter says WHAT and WHY. The PM decides HOW and WHEN. The user sets the north star; PM plans execution toward it.

### Objective Structure

The 4-field structure is retained but renamed:

```markdown
## Objective
- **Deliverable**: Weekly cross-platform insights report
- **Audience**: You (solo founder)
- **Format**: pdf
- **Purpose**: See patterns across platforms that individual digests miss
```

Fields are unchanged (`deliverable`, `audience`, `format`, `purpose`) — the container is renamed from `intent` to `objective`.

### Objective Mutability

| Actor | Can Read | Can Write |
|-------|----------|-----------|
| User (frontend/API) | Yes | Yes — edit from project detail page |
| TP (Orchestrator) | Yes | Yes — via UpdateObjective or CreateProject |
| Composer | Yes | Yes — at creation, or propose changes via escalation |
| PM | Yes — reads as quality reference | **No** — PM judges against objective, doesn't change it |
| Contributing Agents | Yes — via load_context() project injection | No |

### Intentions Consolidation

`## Intentions` section is removed from PROJECT.md. The information moves to PM's `memory/work_plan.md`:

**Before** (two places):
```
PROJECT.md:
  ## Intentions
  - recurring: Produce weekly deck
    - format: pptx
    - delivery: email → ceo@example.com
    - budget: 8 units/cycle

PM workspace:
  memory/work_plan.md:
    ## Focus Areas
    - analyst: revenue trends
    - writer: narrative framing
```

**After** (one place):
```
PROJECT.md:
  ## Objective
  (north star only, no operational specs)

PM workspace:
  memory/work_plan.md:
    ## Execution Plan
    - recurring: Produce weekly deck (pptx, email → ceo@example.com, 8 units/cycle)

    ## Focus Areas
    - analyst: revenue trends
    - writer: narrative framing

    ## Budget
    8 units/cycle, 15 units total for Q2 goal
```

PM seeds `memory/work_plan.md` from the objective + delivery on first run if no work plan exists. After that, PM evolves it independently.

### Backward Compatibility

**None.** Per hooks discipline (singular implementation, no dual approaches):
- All existing PROJECT.md files rewritten on read — `read_project()` accepts both `## Intent` and `## Objective`, writes back as `## Objective`
- `## Intentions` section parsed on read, migrated to PM's work_plan on next PM run, then deleted from PROJECT.md on next write
- No shim code persists after migration phase completes

## Relationship to Existing Architecture

| Component | Change |
|-----------|--------|
| `workspace.py` `read_project()` | Parse `## Objective` (accept `## Intent` for migration), drop `## Intentions` parsing after migration |
| `workspace.py` `write_project()` | Write `## Objective` (not `## Intent`), stop writing `## Intentions` |
| `project_registry.py` | Rename `intent` → `objective` in all registry entries and `scaffold_project()` |
| `agent_pipeline.py` ROLE_PROMPTS["pm"] | Template field `{intentions}` → removed; PM reads work_plan from memory instead |
| `agent_pipeline.py` ASSEMBLY_COMPOSITION_PROMPT | Template field `{intent}` → `{objective}` |
| `agent_execution.py` `_load_pm_project_context()` | Build `objective` field (not `intent`); stop building `intentions` field; PM gets work_plan from memory |
| `primitives/project_execution.py` | Rename `UpdateProjectIntent` → `UpdateWorkPlan`; scope to PM's memory/work_plan.md only |
| `routes/projects.py` | Rename `ProjectIntent` → `ProjectObjective`; update create/update handlers |
| `web/types/index.ts` | Rename `ProjectIntent` → `ProjectObjective` interface |
| `web/app/.../projects/[slug]/page.tsx` | Render objective prominently; add edit capability |
| `FOUNDATIONS.md` | Rewrite "Intentions at Project Scope" section |
| `ADR-120` | Update Phase 8 "Project-Level Intentions" section |
| `PROJECTS-PRODUCT-DIRECTION.md` | Update PROJECT.md schema examples and Intent tab |
| `ADR-122` | Update registry examples |
| `CLAUDE.md` | Update ADR-120/121/122 entries |
| `api/prompts/CHANGELOG.md` | PM prompt version bump, assembly prompt version bump |

## Implementation Phases

### Phase 1: Terminology Rename — `intent` → `objective`
- Rename field in `read_project()` / `write_project()` (accept both on read, write new)
- Rename in `project_registry.py` (all entries + scaffold function)
- Rename in `agent_execution.py` (PM context loading, assembly composition)
- Rename in `agent_pipeline.py` (ASSEMBLY_COMPOSITION_PROMPT template field)
- Rename in `routes/projects.py` (Pydantic models, handlers)
- Rename in `web/types/index.ts`
- Rename in frontend project detail page
- CHANGELOG entry for prompt changes

### Phase 2: Consolidate `intentions` → PM `memory/work_plan.md`
- Remove `## Intentions` from `write_project()` output
- `read_project()`: if `## Intentions` found, return them as `legacy_intentions` for migration
- PM first-run logic: if `legacy_intentions` exist and `memory/work_plan.md` is empty, seed work_plan from legacy_intentions + objective + delivery
- Rename `UpdateProjectIntent` → `UpdateWorkPlan`; change target from PROJECT.md to `memory/work_plan.md`
- Update PM prompt: remove `{intentions}` template field; PM reads work_plan from memory (already loaded)
- Delete backward-compat derivation code (workspace.py lines 1871-1878)
- CHANGELOG entry for PM prompt changes

### Phase 3: Frontend Objective Editing + PM Intelligence Surfacing
- Project detail page: editable objective section (PATCH `/api/projects/{slug}`)
- PM quality assessment panel (read from workspace API)
- PM brief display per contributor
- Activity timeline: quality assessment and steer events

### Phase 4: Documentation
- Update FOUNDATIONS.md, ADR-120, ADR-122, PROJECTS-PRODUCT-DIRECTION.md, CLAUDE.md
- All updated alongside code in their respective phase commits (not batched)

## What This Does NOT Change

- Project creation flows (bootstrap, Composer, TP) — same paths, new field name
- PM's intelligence capabilities (ADR-121) — assess, steer, assemble unchanged
- Work budget mechanics (ADR-120 P3) — unchanged
- Assembly composition pipeline — same flow, new template field name
- Workspace filesystem conventions (ADR-119) — folder structure unchanged
- Agent execution strategies — unchanged
- Contributing agent context injection — sees `objective` instead of `intent`, same mechanism
