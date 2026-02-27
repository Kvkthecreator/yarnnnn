# ADR-082: Deliverable Type Consolidation

**Status:** Accepted (Implemented 2026-02-27)
**Date:** 2026-02-27
**Amends:** ADR-044 (Type Reconceptualization) — reduces type surface from 27 to 8
**Supersedes:** ADR-019 (Deliverable Types System) — original type definitions
**Related:**
- [ADR-035: Platform-First Deliverable Type System](ADR-035-platform-first-deliverable-type-system.md)
- [ADR-044: Deliverable Type Reconceptualization](ADR-044-deliverable-type-reconceptualization.md)
- [ADR-045: Deliverable Orchestration Redesign](ADR-045-deliverable-orchestration-redesign.md)
- [ADR-081: Execution Path Consolidation](ADR-081-execution-path-consolidation.md)

---

## Context

### The accumulation problem

The deliverable type system grew additively across 7 ADRs over 4 weeks:

| ADR | Types Added | Rationale |
|-----|-------------|-----------|
| ADR-019 | 11 | Original format-centric types (status_report, research_brief, etc.) |
| ADR-029 | 4 | Email-specific types (inbox_summary, reply_draft, follow_up_tracker, thread_summary) |
| ADR-031 | 4 | Cross-platform synthesizers (weekly_status, project_brief, cross_platform_digest, activity_summary) |
| ADR-035 | 4 | Platform-first wave 1 (slack_channel_digest, slack_standup, gmail_inbox_brief, notion_page_summary) |
| ADR-046 | 2 | Calendar types (meeting_prep, weekly_calendar_preview) |
| Phase 2 | 3 | Strategic intelligence (deep_research, daily_strategy_reflection, intelligence_brief) |
| — | 1 | Custom catch-all (always existed) |

**Result: 27 registered types, 5 ever used in production.** The 22 unused types have prompts, classifications, DB constraints, frontend definitions, and documentation — all maintained for zero user value.

### Documentation drift

The type system is defined in 6+ locations with inconsistencies:

| Location | Claims | Reality |
|----------|--------|---------|
| `docs/architecture/deliverables.md` | "31 types across three tiers" | 27 types in code, 28 in DB constraint |
| Same doc | Lists `competitive_analysis`, `digest`, `newsletter` | These don't exist in code |
| Same doc | `meeting_summary` under Platform-Bound | Code classifies it as `cross_platform` |
| Same doc | `client_proposal` under Research/Hybrid | Code classifies it as `cross_platform` |
| ADR-035 TYPE_WAVES | `meeting_prep` as Wave 2 (cross-platform) | Code classifies it as `platform_bound` (calendar) |
| `is_synthesizer` flag | 4 types marked as synthesizers | Overlaps with `binding=cross_platform`; redundant dimension |
| TYPE_GOVERNANCE_CEILINGS | 9 types mapped | Governance deprecated per ADR-066 |

### Naming fragmentation

The same concept has 3+ names depending on which ADR you read:

| Concept | ADR-031 | ADR-035 | ADR-044 | Code |
|---------|---------|---------|---------|------|
| "single platform deliverable" | Platform-Native | Platform-First | Platform-Bound | `platform_bound` |
| "multi-platform deliverable" | Synthesizer | Wave 2 | Cross-Platform | `cross_platform` + `is_synthesizer` |
| "maturity level" | — | Wave (1/2/3) | — | Tier (stable/beta/experimental) |

### The deeper question

The type system was designed to showcase breadth — "look at all the types of content YARNNN can generate." But breadth without depth is a menu, not a product. The question isn't "what can we generate?" but **"what set of deliverables makes YARNNN indispensable?"**

---

## Decision

### Consolidate to 8 types anchored in the user's work rhythm

A deliverable is valuable when it has three properties:

1. **Temporal urgency** — there's a "when" that makes it timely (before a meeting, start of day, end of week)
2. **Context advantage** — YARNNN knows something the user would have to manually assemble
3. **Actionability** — the output changes what the user does next

The strongest deliverable suite covers the user's rhythm without gaps or overlaps:

```
Morning:     What happened overnight? What's today?     → platform-bound (per-platform)
Pre-meeting: What do I need to know for this meeting?   → meeting_prep (reactive)
End of week: What's the big picture?                    → status_report (cross-platform)
On-demand:   I need to understand X                     → research_brief (web research)
Flexible:    Something else entirely                    → custom (hybrid)
```

### The 8 types

| Type | Binding | Rhythm | What it replaces |
|------|---------|--------|-----------------|
| `slack_channel_digest` | platform_bound | daily | + absorbs `slack_standup` |
| `gmail_inbox_brief` | platform_bound | daily | + absorbs `inbox_summary`, `follow_up_tracker`, `thread_summary`, `reply_draft` |
| `notion_page_summary` | platform_bound | daily | unchanged |
| `weekly_calendar_preview` | platform_bound | weekly | unchanged |
| `meeting_prep` | platform_bound | reactive | + absorbs `meeting_summary`, `one_on_one_prep` |
| `status_report` | cross_platform | weekly | + absorbs `stakeholder_update`, `board_update`, `weekly_status`, `cross_platform_digest`, `activity_summary`, `project_brief`, `daily_strategy_reflection` |
| `research_brief` | research | on-demand | + absorbs `deep_research`, `intelligence_brief` |
| `custom` | hybrid | on-demand | + absorbs `client_proposal`, `performance_self_assessment`, `newsletter_section`, `changelog` |

### Why each type is axiomatic

**`slack_channel_digest`** — The canonical "what happened while I was away" deliverable. Platform-bound to Slack. Absorbs `slack_standup` because standup synthesis is a Slack digest with a filter — achievable via `type_config` (e.g., `focus: "standup"`).

**`gmail_inbox_brief`** — The canonical "what's in my inbox" deliverable. Absorbs 4 email types that are all slices of the same inbox view: `inbox_summary` (near-duplicate), `follow_up_tracker` (a section within the brief), `thread_summary` (per-thread view, better as TP chat), `reply_draft` (action, not digest — better as TP chat).

**`notion_page_summary`** — The canonical "what changed in my docs" deliverable. No overlap.

**`weekly_calendar_preview`** — The canonical "what's my week ahead" deliverable. No overlap.

**`meeting_prep`** — The canonical "prepare me for this meeting" deliverable. Reactive (triggered by calendar event). Absorbs `meeting_summary` (pre/post are config variants) and `one_on_one_prep` (a meeting prep with relationship context — achievable via type_config).

**`status_report`** — The canonical "synthesize my week" deliverable. Cross-platform. Absorbs all the cross-platform synthesis types that differ only in audience, tone, or scope — these are all configurations of "summarize what happened across my platforms": `stakeholder_update` (tone=executive), `board_update` (tone=formal), `weekly_status` (scope=weekly), `cross_platform_digest` (scope=recent), `activity_summary` (scope=activity), `project_brief` (scope=project), `daily_strategy_reflection` (scope=daily).

**`research_brief`** — The canonical "investigate this topic" deliverable. Web research binding. Absorbs `deep_research` (research_brief with more rounds — achieved via binding-aware round limits in ADR-081) and `intelligence_brief` (research with platform grounding — the hybrid binding handles this automatically).

**`custom`** — The catch-all. Hybrid binding (can use both web research and platform context). Absorbs all speculative types with zero usage: `client_proposal`, `performance_self_assessment`, `newsletter_section`, `changelog`. Users who need these formats can configure them via `custom` with a description.

### What absorbed types become

Absorbed types are not deleted from the DB constraint (existing data must remain valid). They are:

1. **Removed from the frontend TypeSelector** — users can no longer create new deliverables of absorbed types
2. **Removed from the prompt registry** — new executions use the parent type's prompt
3. **Aliased in `get_type_classification()`** — absorbed types route to their parent's binding and strategy
4. **Retained in the DeliverableType Literal** — for backwards compatibility with existing data
5. **Marked as `tier: "deprecated"` in TYPE_TIERS** — clear signal in code

### Naming standardization

With this ADR, establish canonical terminology:

| Term | Definition | Replaces |
|------|-----------|----------|
| **Binding** | How context is gathered: `platform_bound`, `cross_platform`, `research`, `hybrid` | "Platform-Native" (ADR-031), "Platform-First" (ADR-035), "Wave" (ADR-035) |
| **Tier** | Maturity level for UI/code: `stable`, `deprecated` | "Beta", "Experimental", "Wave 1/2/3" |
| **Rhythm** | When the deliverable is valuable: `daily`, `weekly`, `reactive`, `on-demand` | "Temporal pattern" (ADR-044), "Scheduled/Reactive/On-demand/Emergent" |
| **Origin** | How the deliverable was created: `user_configured`, `analyst_suggested`, `signal_emergent` | Unchanged (ADR-068) |

**Retired terminology:**
- `is_synthesizer` flag — replaced by `binding=cross_platform`
- `TYPE_WAVES` dict — replaced by binding
- `TYPE_GOVERNANCE_CEILINGS` dict — governance deprecated per ADR-066
- `TYPE_EXTRACTION_SIGNALS` dict — extraction logic belongs in the prompt, not a separate dict

---

## What changes

### Code changes

| File | Change |
|------|--------|
| `api/routes/deliverables.py` | TYPE_TIERS: mark 19 absorbed types as `deprecated`. Remove TYPE_WAVES, TYPE_GOVERNANCE_CEILINGS, TYPE_EXTRACTION_SIGNALS dicts. Update `get_type_classification()` to alias absorbed types to parent bindings. |
| `api/services/deliverable_pipeline.py` | Remove TYPE_PROMPTS entries for 19 deprecated types. Ensure fallback to parent type prompt. Simplify VARIANT_PROMPTS to match 8 active types. |
| `web/components/deliverables/TypeSelector.tsx` | Reduce to 8 types across 4 binding categories. Remove LegacyTypeSelector. |
| `web/types/index.ts` | DeliverableType union remains full (backwards compat) but add `ActiveDeliverableType` subset for UI. |

### Documentation changes

| File | Change |
|------|--------|
| `docs/architecture/deliverables.md` | Rewrite Type System section: 8 active types, correct bindings, remove ghost types |
| `docs/architecture/agent-execution-model.md` | No structural changes needed — execution model is binding-based, not type-based |
| `docs/architecture/backend-orchestration.md` | Minor: F3 type reference update |

### Database changes

**No migration needed.** The DB CHECK constraint keeps all 27+ types valid. Existing deliverables of deprecated types continue to work — they route to the parent type's strategy and prompt. New deliverables of deprecated types cannot be created from the UI.

---

## What does NOT change

| Component | Status | Rationale |
|-----------|--------|-----------|
| DB CHECK constraint | Unchanged | Existing data must remain valid |
| Execution strategies | Unchanged | Strategies are binding-based, not type-based |
| DeliverableType Literal (backend) | Unchanged | API backwards compat |
| Delivery pipeline | Unchanged | Independent of type |
| Signal processing | Unchanged | Creates by type, but types it creates (meeting_prep, status_report) are in the active set |
| Conversation analysis | Unchanged | Creates suggestions; may need type mapping update |

---

## Consequences

### Positive

1. **Clarity.** 8 types that each serve a distinct purpose. No overlap, no "which status report type do I pick?"
2. **Reduced maintenance.** 19 fewer prompts to maintain. One prompt per user-facing need.
3. **Better TypeSelector UX.** Users see 8 focused options instead of 16+ ambiguous choices.
4. **Documentation parity.** One source of truth for types that matches code, schema, and frontend.
5. **Foundation for depth.** Instead of building 27 shallow types, invest in making 8 types excellent — better prompts, better type_config options, better research integration.

### Negative

1. **Reduced type specificity.** A `board_update` user now gets `status_report` with tone configuration. The dedicated prompt was more opinionated. Mitigated by: type_config can carry audience/tone preferences.
2. **Migration complexity for existing data.** Any deliverables of deprecated types still work but may get a different prompt on next execution. Mitigated by: 5 types have production data, all 5 are in the active set.

### Risk

**Signal processing creates deliverables by type.** If signal processing creates a deprecated type (e.g., `meeting_summary`), it will still work via aliasing. But we should update signal processing to use only active types. Low risk — signal processing currently creates `meeting_prep` and custom types, both active.

---

## Future: Daily Brief as cross-platform morning synthesis

The 8-type model keeps platform-bound morning deliverables separate (`slack_channel_digest`, `gmail_inbox_brief`, `notion_page_summary`). A user who wants all three gets 3 emails.

The natural evolution is a **Daily Brief** — a single cross-platform deliverable that synthesizes the morning view across all connected platforms. This would:
- Replace 3 platform-bound types with 1 cross-platform type
- Reduce to 6 types total (Daily Brief, Meeting Prep, Weekly Calendar Preview, Status Report, Research Brief, Custom)
- Require a new cross-platform morning synthesis prompt

This is deferred because:
1. The platform-bound types work now and are production-tested
2. A good Daily Brief requires better cross-platform synthesis (ranking, deduplication, priority)
3. Users may prefer granular control over per-platform digests
4. Let usage data inform whether users actually configure all 3 morning types

---

## Implementation status

All phases completed 2026-02-27.

### Phase 1 — Documentation update ✅

- `docs/architecture/deliverables.md` rewritten: 8 active types, correct bindings, canonical terminology
- ADR-044 marked "Amended by ADR-082", ADR-019 marked "Superseded by ADR-082"

### Phase 2 — Backend type consolidation ✅

- TYPE_TIERS: 8 stable, 19 deprecated
- Removed TYPE_WAVES, TYPE_GOVERNANCE_CEILINGS, TYPE_EXTRACTION_SIGNALS dicts
- `get_type_classification()`: alias map routes deprecated types to parent bindings
- TYPE_PROMPTS: reduced to 8 active entries (deprecated prompts deleted, not shimmed)
- SECTION_TEMPLATES: reduced to 7 active entries (custom has no sections)
- VARIANT_PROMPTS: removed all deprecated variants (email, cross-platform synthesizer, notion_page)
- Validation functions: removed 16 deprecated validators, `validate_output()` routes to 6 active validators
- Config models: removed 19 deprecated Pydantic configs, TypeConfig union reduced to 6 active types
- `get_default_config()`: reduced to 6 active type defaults
- `build_type_prompt()`: uses `_TYPE_PROMPT_ALIASES` to resolve deprecated types to parent prompt

### Phase 3 — Frontend consolidation ✅

- TypeSelector: 8 types across 4 binding categories, LegacyTypeSelector removed
- `ActiveDeliverableType` union added to `types/index.ts`
- `DeliverableTier` changed from `"stable" | "beta" | "experimental"` to `"stable" | "deprecated"`
- Removed 24 deprecated TypeScript interfaces (Section + Config for each deprecated type)
- `SynthesizerType` removed
- TypeConfig union reduced to 6 active types + `Record<string, unknown>` fallback
- DELIVERABLE_TYPE_LABELS in DeliverableSettingsModal and IdleSurface reduced to 8 active types

### Phase 4 — Signal processing alignment ✅

- `_REASONING_SYSTEM_PROMPT`: references only active types (status_report, research_brief, custom)
- `SUGGESTABLE_TYPES` in conversation_analysis: removed `weekly_status`
- `get_type_classification()` used instead of hardcoded meeting_prep classification

---

## Open questions (identified, not yet solved)

### 1. Scope management per deliverable

The system currently dumps chronological content from `platform_content` into the prompt without defined time windows, depth limits, or priority filtering per source. The `scope_config` field exists in the source schema (`mode`, `fallback_days`, `max_items`) but is not implemented — all fetches use chronological recency with hardcoded caps (20 items/source, 500 chars/item).

This means:
- A digest of 1 quiet channel vs 5 active channels gets the same treatment
- "What happened overnight" vs "what happened this week" isn't distinguished
- High-volume sources get truncated without priority filtering

**The question:** Should scope rules be encoded in Python (pre-agent filtering, per-type scope defaults) or should the headless agent receive richer context and reason about relevance itself? The TP/Claude Code pattern suggests the latter — give the agent better primitives and let it reason — but this requires more tool rounds and higher cost. May also be a hybrid: coarse pre-filtering (time window, item cap) as orchestration, fine filtering (relevance, priority) as agent reasoning.

Deferred until production usage reveals where output quality degrades.

### 2. Content vs action boundary

The current type system conflates format with intent. Some deprecated types were really actions (`reply_draft` = draft an email), some were summaries (`slack_channel_digest` = what happened), some were synthesis (`status_report` = cross-platform themes). The 8-type consolidation focuses on content deliverables — text artifacts the user reads.

The architecture already supports action-capable primitives in chat mode (Write, Edit, Execute). Headless mode is deliberately read-only. But the boundary between "generate a report" and "draft a reply" and "handle this thread" will become increasingly relevant as the system matures.

**The question:** When the use case arrives for action deliverables (draft replies, create calendar events, post Slack messages), should they be:
- New deliverable types with write-mode primitives?
- An extension of headless mode (`mode="headless_action"`) with scoped write primitives?
- Delegated to TP chat via a sub-agent pattern (ADR-080 extensibility note)?

The Claude Code analogy suggests: don't pre-build a taxonomy. Provide tools (primitives) and let the agent reason about what to do. The type system defines *what the user configured*, not *how the agent operates*. The agent's primitive access (read-only vs read-write) is the actual boundary.

Deferred until user demand for action-oriented deliverables emerges.
