# ADR-101: Deliverable Intelligence Model

**Date:** 2026-03-09
**Status:** Implemented
**Related:**
- [ADR-087: Deliverable Scoped Context](ADR-087-workspace-scoping-architecture.md)
- [ADR-092: Mode Taxonomy](ADR-092-deliverable-intelligence-mode-taxonomy.md)
- [ADR-093: Type Taxonomy](ADR-093-deliverable-types-overhaul.md)

---

## Problem

A deliverable accumulates several kinds of knowledge across its lifetime — behavioral directives from the user, format-specific configuration, observations from triggers, edit patterns from user feedback. These were named inconsistently across schema, code, and docs, leading to confusion about what each field represents and how they interact.

Specific issues:
1. `deliverable_instructions` called "instructions" but acts as user directives, not skills
2. `deliverable_memory` conflates event observations with operational state (review_log)
3. Edit feedback (`edit_distance_score`, `edit_categories`) computed but never fed back into generation — the learning loop was broken because `get_past_versions_context()` queried `status='approved'` while the delivery-first model (ADR-066) sets versions to `status='delivered'`
4. `create_feedback_memory()` in `feedback_engine.py` was dead code — exported but never called
5. No documentation of how these layers compose into the agent's prompt

---

## Decision

### Four-layer intelligence model

Every deliverable has four distinct layers of knowledge:

| Layer | What it is | Who writes | Who reads | Schema field(s) |
|-------|-----------|-----------|----------|-----------------|
| **Skills** | How to do the job — type-specific format, structure, tool budget | System (hardcoded per type) | Headless agent (type prompt) | `type_config` JSONB + `DEFAULT_INSTRUCTIONS` dict + type prompt templates in `deliverable_pipeline.py` |
| **Directives** | User's behavioral constraints — tone, priorities, audience | User (UI, chat, API) | Headless agent (system prompt) + proactive review | `deliverable_instructions` TEXT + `recipient_context` JSONB |
| **Memory** | What happened — observations, review decisions, goals | System (triggers, review passes) + user (chat) | Headless agent (system prompt) + proactive review | `deliverable_memory` JSONB: `{observations, goal, review_log, created_deliverables}` |
| **Feedback** | How well it's doing — edit patterns from user corrections | System (on version approval/edit) | Headless agent (type prompt, as "learned preferences") | `edit_distance_score` FLOAT + `edit_categories` JSONB + `feedback_notes` TEXT on `deliverable_versions` |

### Prompt composition order

The headless agent sees these layers assembled in this order:

```
SYSTEM PROMPT (_build_headless_system_prompt):
  1. Output Rules (generic)
  2. User Context (from user_memory — profile, preferences)
  3. Directives (deliverable_instructions)
  4. Memory (observations, goal, review_log)
  5. Feedback (learned preferences from past version edits)  ← NEW
  6. Tool Usage guidance
  7. Trigger Context (if signal/proactive)

USER MESSAGE (build_type_prompt):
  1. Skills (type-specific template with config values)
  2. Gathered Context (platform content)
  3. Recipient Context (audience personalization)
  4. Past Versions feedback (learned preferences)  ← MOVED from here
```

**Change:** Learned preferences move from user message (type prompt) to system prompt, where they sit alongside other persistent deliverable knowledge. This ensures feedback is always visible to the agent regardless of type prompt structure.

### Feedback loop fix

`get_past_versions_context()` query changed from `status='approved'` to `status IN ('approved', 'delivered')`. This unbreaks the learning loop for delivery-first (ADR-066) versions that skip the approval gate.

---

## What this is NOT

This ADR does **not** introduce:
- A sub-agent framework — deliverables remain execution targets, not autonomous agents
- Self-modifying instructions — the agent cannot change its own directives
- Adaptive scheduling — review cadence remains fixed per proactive review decision
- Per-deliverable token budgets

These are scoped out for separate consideration if needed.

---

## Changes

| File | Change |
|------|--------|
| `api/services/deliverable_pipeline.py` | Fix `get_past_versions_context()` status filter: `approved` → `approved, delivered` |
| `api/services/deliverable_execution.py` | Inject learned preferences into `_build_headless_system_prompt()` instead of only type prompt |
| `api/services/feedback_engine.py` | Delete dead `create_feedback_memory()` function |
| `docs/adr/ADR-101-deliverable-intelligence-model.md` | This document |

---

## Frontend visibility

The structured Instructions panel (ADR-087 Phase 3) provides user visibility into the Directives layer. The Prompt Preview section shows the composed prompt including instructions, memory, and audience — giving users inspectability over what the agent receives.

Feedback (learned preferences) is visible in the existing quality indicators on the deliverables list page (`quality_trend`, `avg_edit_distance`). The prompt preview does not yet show feedback — this could be added as a future enhancement.
