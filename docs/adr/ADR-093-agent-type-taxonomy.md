# ADR-093: Agent Type Taxonomy Revision

**Status:** Implemented
**Date:** 2026-03-04
**Supersedes:** ADR-082 (8-type consolidation), all prior type definitions

---

## Context

The agent type system accumulated 27 types across ADR phases 029–082, consolidated to 8 "active" types in ADR-082. Those 8 types (`slack_channel_digest`, `gmail_inbox_brief`, `notion_page_summary`, `weekly_calendar_preview`, `meeting_prep`, `status_report`, `research_brief`, `custom`) were named for **architectural origins** — which platform they read from, which ADR introduced them — not for user intent.

After ADR-092 (five execution modes), the type/mode separation is clean: **mode answers when/how a agent decides to act; type answers what the user is building**. The old type names violated this separation by encoding platform binding and temporal pattern into the type name itself (`slack_channel_digest` implies recurring + platform_bound + slack). With modes now handling execution character, types are free to be pure user vocabulary.

Additionally, a production bug existed: the creation wizard labeled `research_brief` as "Notion Changelog" — the wrong type showing under the wrong label.

All existing data is test data. No backwards-compat shims.

---

## Decision

Replace 8 legacy active types with 7 purpose-first types. Delete all deprecated type aliases. Types name user intent; mode + sources + instructions handle execution.

### The 7 types

| Type | User label | "What am I building?" | Natural modes | Context strategy |
|------|-----------|----------------------|--------------|-----------------|
| `digest` | Digest | A regular synthesis of what's happening in a specific place | recurring, reactive | platform_bound (inferred from sources) |
| `brief` | Brief | A situation-specific document before a key event | coordinator, proactive, goal | cross_platform |
| `status` | Status Update | A regular cross-platform summary for a person or audience | recurring, goal | cross_platform |
| `watch` | Watch | Standing-order intelligence on a domain I can't monitor full-time | proactive, reactive | cross_platform or research |
| `deep_research` | Deep Research | A bounded investigation into something specific, then done | goal | research or hybrid |
| `coordinator` | Coordinator | A meta-specialist that watches a domain and dispatches other work | coordinator | cross_platform |
| `custom` | Custom | I know what I want — define it myself | any | hybrid |

### Design principles

**Types are orthogonal to modes.** `digest` can be recurring (every Monday) or reactive (when threshold of channel events accumulates). `brief` can be coordinator-triggered (watch calendar, create when needed) or goal-driven (produce a brief for this event, then stop). The type names don't imply a mode.

**`digest` replaces four platform types.** `slack_channel_digest`, `gmail_inbox_brief`, `notion_page_summary`, `weekly_calendar_preview` were all the same intent — synthesize what happened in a specific place — with different platform labels. Platform is now a `sources` configuration detail, not a type. The `digest` prompt is parameterized by source platform.

**`brief` replaces `meeting_prep`.** Meeting prep was always a situation-specific brief; the name was too narrow. `brief` covers meeting prep, event prep, call prep, and any situation where a targeted document is needed before something happens.

**`watch` is new.** This is the standing-order intelligence use case that signal processing previously served via infrastructure. Now it's user-configured: "keep an eye on this domain and surface things when warranted." Natural home for proactive and reactive modes.

**`deep_research` replaces `research_brief`.** Renamed to match common LLM vocabulary (ChatGPT's "Deep Research" framing) and to clearly distinguish from `watch`. Deep Research = bounded investigation with a clear end (goal mode). Watch = ongoing monitoring with no end (proactive/reactive).

**`coordinator` as a type makes the mode discoverable.** The coordinator mode is architecturally real but invisible without a matching type. Users creating a "coordinator" agent understand they're configuring a meta-specialist, not a content producer.

### Backfill map (old → new)

| Old type | New type |
|----------|----------|
| `slack_channel_digest` | `digest` |
| `gmail_inbox_brief` | `digest` |
| `notion_page_summary` | `digest` |
| `weekly_calendar_preview` | `digest` |
| `meeting_prep` | `brief` |
| `status_report` | `status` |
| `stakeholder_update` | `status` |
| `board_update` | `status` |
| `weekly_status` | `status` |
| `project_brief` | `status` |
| `cross_platform_digest` | `status` |
| `activity_summary` | `status` |
| `daily_strategy_reflection` | `watch` |
| `intelligence_brief` | `watch` |
| `research_brief` | `deep_research` |
| `deep_research` | `deep_research` |
| `meeting_summary` | `brief` |
| `one_on_one_prep` | `brief` |
| `inbox_summary` | `digest` |
| `reply_draft` | `digest` |
| `follow_up_tracker` | `digest` |
| `thread_summary` | `digest` |
| `slack_standup` | `digest` |
| `client_proposal` | `custom` |
| `performance_self_assessment` | `custom` |
| `newsletter_section` | `custom` |
| `changelog` | `custom` |

---

## Consequences

### Positive
- Type names resonate with ICP vocabulary (consultants, founders, ops leads)
- Mode/type separation is clean and principled — matches primitive/capability separation in TP tools
- Creation wizard becomes intent-first ("what am I building?") not platform-first
- `watch` and `coordinator` types make advanced modes discoverable without documentation
- Dead code eliminated: `_TYPE_ALIASES`, 19 deprecated type entries, broken wizard label

### Negative
- Platform-specific prompt customization for `digest` must be inferred from sources (minor complexity)
- Existing test agents get backfilled — no content impact since all test data

### Neutral
- `custom` unchanged — still the safety valve for user-defined intent
- Execution strategy routing unchanged — still maps `type_classification.binding` to strategy class; only the classification function changes
