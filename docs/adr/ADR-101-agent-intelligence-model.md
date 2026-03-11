# ADR-101: Agent Intelligence Model

**Date:** 2026-03-09
**Status:** Implemented
**Related:**
- [ADR-087: Agent Scoped Context](ADR-087-workspace-scoping-architecture.md)
- [ADR-092: Mode Taxonomy](ADR-092-agent-intelligence-mode-taxonomy.md)
- [ADR-093: Type Taxonomy](ADR-093-agent-types-overhaul.md)

---

## Problem

A agent accumulates several kinds of knowledge across its lifetime — behavioral directives from the user, format-specific configuration, observations from triggers, edit patterns from user feedback. These were named inconsistently across schema, code, and docs, leading to confusion about what each field represents and how they interact.

Specific issues:
1. `agent_instructions` called "instructions" but acts as user directives, not skills
2. `agent_memory` conflates event observations with operational state (review_log)
3. Edit feedback (`edit_distance_score`, `edit_categories`) computed but never fed back into generation — the learning loop was broken because `get_past_versions_context()` queried `status='approved'` while the delivery-first model (ADR-066) sets versions to `status='delivered'`
4. `create_feedback_memory()` in `feedback_engine.py` was dead code — exported but never called
5. No documentation of how these layers compose into the agent's prompt

---

## Decision

### Four-layer intelligence model

Every agent has four distinct layers of knowledge:

| Layer | What it is | Who writes | Who reads | Schema field(s) |
|-------|-----------|-----------|----------|-----------------|
| **Skills** | How to do the job — type-specific format, structure, tool budget | System (hardcoded per type) | Headless agent (type prompt) | `type_config` JSONB + `DEFAULT_INSTRUCTIONS` dict + type prompt templates in `agent_pipeline.py` |
| **Directives** | User's behavioral constraints — tone, priorities, audience | User (UI, chat, API) | Headless agent (system prompt) + proactive review | `agent_instructions` TEXT + `recipient_context` JSONB |
| **Memory** | What happened — observations, review decisions, goals | System (triggers, review passes) + user (chat) | Headless agent (system prompt) + proactive review | `agent_memory` JSONB: `{observations, goal, review_log, created_agents}` |
| **Feedback** | How well it's doing — edit patterns from user corrections | System (on version approval/edit) | Headless agent (type prompt, as "learned preferences") | `edit_distance_score` FLOAT + `edit_categories` JSONB + `feedback_notes` TEXT on `agent_runs` |

### Prompt composition order

The headless agent sees these layers assembled in this order:

```
SYSTEM PROMPT (_build_headless_system_prompt):
  1. Output Rules (generic)
  2. User Context (from user_memory — profile, preferences)
  3. Directives (agent_instructions)
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

**Change:** Learned preferences move from user message (type prompt) to system prompt, where they sit alongside other persistent agent knowledge. This ensures feedback is always visible to the agent regardless of type prompt structure.

### Feedback loop fix

`get_past_versions_context()` query changed from `status='approved'` to `status IN ('approved', 'delivered')`. This unbreaks the learning loop for delivery-first (ADR-066) versions that skip the approval gate.

---

## What this is NOT

This ADR does **not** introduce:
- A sub-agent framework — agents remain execution targets, not autonomous agents
- Self-modifying instructions — the agent cannot change its own directives
- Adaptive scheduling — review cadence remains fixed per proactive review decision
- Per-agent token budgets (enforcement) — tokens are tracked but not gated per agent

These are scoped out for separate consideration if needed.

---

## Changes

| File | Change |
|------|--------|
| `api/services/agent_pipeline.py` | Fix `get_past_versions_context()` status filter: `approved` → `approved, delivered` |
| `api/services/agent_execution.py` | Inject learned preferences into `_build_headless_system_prompt()` instead of only type prompt |
| `api/services/agent_execution.py` | Token accumulation across headless agentic loop; return `(draft, usage)` tuple |
| `api/services/agent_execution.py` | `update_version_for_delivery()` accepts `metadata` param; stores tokens on version |
| `api/services/anthropic.py` | `ChatResponse.usage` field; `_parse_response()` extracts `response.usage` |
| `api/services/feedback_engine.py` | Delete dead `create_feedback_memory()` function |
| `supabase/migrations/096_version_metadata.sql` | Add `metadata` JSONB column to `agent_runs` |
| `web/types/index.ts` | Complete `AgentMemory` type (add `review_log`, `created_agents`); add `metadata` to `AgentVersion` |
| `web/components/agents/AgentDrawerPanels.tsx` | MemoryPanel: display `review_log`; prompt preview: include review history |
| `web/components/agents/AgentVersionDisplay.tsx` | Token count display on version cards |
| `docs/adr/ADR-101-agent-intelligence-model.md` | This document |

---

## Per-Agent Token Tracking

Token usage is accumulated across all tool rounds in the headless agentic loop (`generate_draft_inline`) and stored as execution metadata on each version:

```json
// agent_runs.metadata
{
  "input_tokens": 12345,
  "output_tokens": 2345,
  "model": "claude-sonnet-4-20250514"
}
```

Token counts are also written to `activity_log.metadata` for each `agent_run` event, enabling aggregate cost analysis across agents.

The frontend displays total tokens on version cards (hover for input/output breakdown). This provides cost visibility without enforcement — per-agent token budgets are a separate future consideration.

---

## Frontend visibility

The structured Instructions panel (ADR-087 Phase 3) provides user visibility into the Directives layer. The Prompt Preview section shows the composed prompt including instructions, memory, and audience — giving users inspectability over what the agent receives.

Feedback (learned preferences) is visible in the existing quality indicators on the agents list page (`quality_trend`, `avg_edit_distance`). The prompt preview does not yet show feedback — this could be added as a future enhancement.
