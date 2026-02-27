# Signal Processing Taxonomy — Conceptual Framework

**Date**: 2026-02-20
**Context**: ADR-068 Signal-Emergent Deliverables Phase 3+4 Implementation

This document clarifies the conceptual framework for signal processing, deliverable types, and how they relate to the existing UI categorization system.

---

## The Confusion

Signal processing introduced new terminology (`meeting_prep`, `silence_alert`, `contact_drift`) that doesn't map cleanly to the existing deliverable type system. This creates several points of confusion:

1. **Are signal types the same as deliverable types?** No, but they can create them.
2. **Where do signal-emergent deliverables appear in the UI?** In the "SYNTHESIS" group.
3. **What's the relationship between signals and platforms?** Signals observe platforms, deliverables synthesize across them.

---

## Conceptual Layers

### Layer 1: Deliverable **Origins** (How it came to exist)

All deliverables have an `origin` field (ADR-068):

| Origin | Created By | Signal Source | Example |
|---|---|---|---|
| `user_configured` | User or TP (on explicit request) | User intent | "Create a weekly Slack digest for #engineering" |
| `analyst_suggested` | Conversation Analyst (ADR-060) | TP session mining | User keeps asking for status updates → suggests recurring deliverable |
| `signal_emergent` | Signal Processing (ADR-068) | Live platform APIs | Meeting tomorrow with external attendees → creates meeting prep brief |

**Key distinction**: Origin records **provenance** (how it was born), not **what it is**. A `signal_emergent` deliverable can be promoted to recurring and still retain `origin=signal_emergent`.

---

### Layer 2: Deliverable **Types** (What content it produces)

The `deliverable_type` field determines:
- What prompt template is used (deliverable_pipeline.py)
- What execution strategy is used (execution_strategies.py via type_classification)
- What fields are available in type_config

**Active types** (ADR-082 — 8 types, defined in [routes/deliverables.py](../../api/routes/deliverables.py)):

```python
# Platform-bound types (single platform focus)
"slack_channel_digest",        # Slack
"gmail_inbox_brief",           # Gmail
"notion_page_summary",         # Notion
"meeting_prep",                # Calendar (reactive)
"weekly_calendar_preview",     # Calendar (scheduled)

# Cross-platform types (multi-source synthesis)
"status_report",               # Weekly cross-platform synthesis

# Research types (web search)
"research_brief",

# Custom (hybrid)
"custom"
```

19 deprecated types remain in the DB constraint for backwards compatibility but are not selectable in the UI. See [ADR-082](../adr/ADR-082-deliverable-type-consolidation.md) for what each deprecated type was absorbed into.

**Signal-emergent types** that signal processing creates:
- `meeting_prep` — Active type, signal creates it for upcoming calendar events
- `status_report`, `research_brief`, `custom` — Active types referenced by signal reasoning

---

### Layer 3: Type **Classification** (How it's executed)

The `type_classification` field determines execution strategy (ADR-045):

```python
{
  "binding": "platform_bound" | "cross_platform" | "research" | "hybrid",
  "temporal_pattern": "scheduled" | "reactive" | "on_demand",
  "primary_platform": "slack" | "gmail" | "notion" | "calendar",  # if platform_bound
  "freshness_requirement_hours": int
}
```

**Execution strategies**:
- `platform_bound` → PlatformBoundStrategy (single platform gatherer)
- `cross_platform` → CrossPlatformStrategy (parallel platform gatherers)
- `research` → ResearchStrategy (web search via Anthropic)
- `hybrid` → HybridStrategy (research + platform)

---

### Layer 4: UI **Grouping** (Where it appears in the frontend)

The deliverables list page ([deliverables/page.tsx](../../web/app/(authenticated)/deliverables/page.tsx:43-106)) groups deliverables into 4 visual categories:

| UI Group | Rule | Examples | Icon |
|---|---|---|---|
| **SLACK** | `primary_platform=slack` OR `destination.platform=slack` | slack_channel_digest | 💬 |
| **EMAIL** | `primary_platform=gmail` OR `destination.platform=email/gmail` | gmail_inbox_brief | 📧 |
| **NOTION** | `primary_platform=notion` OR `destination.platform=notion` | notion_page_summary | 📝 |
| **SYNTHESIS** | `binding=cross_platform/hybrid/research` OR no clear platform | status_report, research_brief, custom, **meeting_prep** | 📊 |

**Key insight**: "SYNTHESIS" is the UI catch-all for **cross-platform work**. It includes:
- Deliverables that pull from multiple platforms (status_report)
- Deliverables with no specific platform binding (research_brief)
- **Signal-emergent deliverables** (even if they're technically platform_bound)

The frontend **intentionally** groups signal-emergent deliverables as "SYNTHESIS" because they represent **proactive, system-generated work** rather than platform monitoring.

---

## Signal Processing Flow

### What Signals Are

Signals are **behavioral events extracted from live platform APIs**:

```
SIGNAL TYPES (conceptual, not schema):
- Calendar Signal: "Meeting in 6h with [contact] (last emailed 11d ago)"
- Silence Signal: "Gmail thread '[subject]' with [sender] quiet for 7d"
- Drift Signal: "No contact with [client] in 12d (avg cadence: 4d)"
- Mention Signal: "Tagged in Slack #channel, no response in 3h"
- Ownership Signal: "Notion page you own edited by [colleague]"
```

Signals are **not stored** in the database. They're ephemeral observations extracted during the signal processing cron run.

---

### What Signal Processing Does

**Input**: Live platform APIs (Google Calendar, Gmail, Slack, Notion)
**Output**: Zero or more `signal_emergent` deliverables

**Process** (unified_scheduler.py Phase 1):
1. **Extract signals** (deterministic, no LLM)
   - Query live Google Calendar API for upcoming events
   - Query live Gmail API for thread silence patterns
   - Query live Slack API for unanswered mentions (future)
   - Produce structured SignalSummary object

2. **Reason over signals** (single LLM call)
   - Input: SignalSummary + user_context + recent_activity + existing_deliverables
   - Output: List of actions (create_signal_emergent | trigger_existing | no_action)
   - Constraints: confidence ≥ 0.60, deduplication, type deduplication

3. **Execute actions** (create deliverables)
   - Create `deliverable` row with `origin=signal_emergent`
   - Immediately queue execution (one-time, `trigger_type=manual`)
   - Record in `signal_history` for deduplication

---

### Signal-to-Deliverable Mapping

Signal processing **creates deliverables of existing types**:

| Signal Type | Creates Deliverable Type | Type Classification | UI Group |
|---|---|---|---|
| **Calendar signal** (meeting soon) | `meeting_prep` | `platform_bound` (calendar) | **SYNTHESIS** ⚠️ |
| **Silence signal** (thread quiet) | `silence_alert` (NEW) | `platform_bound` (gmail) | EMAIL |
| **Drift signal** (no contact) | `contact_drift` (NEW) | `cross_platform` | SYNTHESIS |

⚠️ **Why meeting_prep goes to SYNTHESIS**: Even though it's `platform_bound` to Calendar, signal-emergent deliverables are intentionally grouped as SYNTHESIS because they're **proactive, system-generated work** rather than recurring platform monitors.

---

## Orchestration vs. Artifacts — The Core Distinction

### First-Principles Answer (2026-02-20)

**Question:** Are signals orchestration (triggering existing deliverables) or artifacts (creating new deliverable rows)?

**Answer:** Both, at different phases.

Signal processing implements a **two-phase model**:

**Phase 1: Pure Orchestration (Ephemeral)**
- Extract behavioral signals from live platform APIs
- Reason with LLM over signals + context + existing deliverables
- Produce action recommendations (ephemeral `SignalAction` objects):
  - `create_signal_emergent` — For novel work not covered by existing deliverables
  - `trigger_existing` — For work already handled by recurring deliverables (advance next_run_at)
  - `no_action` — Signal doesn't meet confidence threshold or is redundant

**Phase 2: Selective Artifact Creation (Persistent)**
- For `create_signal_emergent`: Create new deliverable row (`origin=signal_emergent`) + execute immediately
- For `trigger_existing`: Update existing deliverable's next_run_at (pure orchestration, no new row)
- For `no_action`: Nothing
- Record all actions in `signal_history` for deduplication

**This is analogous to GitHub Actions:**
- **Trigger event** (push, PR) → **Ephemeral signal** (calendar event, thread silence)
- **Workflow definition** (YAML file persists) → **Deliverable row** (config persists)
- **Workflow run** (execution instance) → **Deliverable version** (execution result)

The key insight: **Signals observe platforms, deliverables synthesize across them.** Signal processing creates deliverable artifacts when it detects novel work that isn't covered by the user's existing configurations.

---

## The Naming Problem

### Current Confusion

The signal processing code uses signal type names (`meeting_prep`, `silence_alert`, `contact_drift`) in three different contexts:

1. **Signal type** (conceptual) — "There's a meeting coming up"
2. **Deliverable type** (schema) — `deliverable_type = "meeting_prep"`
3. **Deduplication key** (signal_history) — `signal_type = "meeting_prep"`

This conflates **what we observed** with **what we created**.

However, after first-principles analysis, this conflation is **acceptable** because:
- Signal processing creates deliverables using existing types (`meeting_prep` already exists)
- The `signal_history.signal_type` matches `deliverable_type` by design (tracks which type of deliverable was created)
- Alternative (separate signal taxonomy) adds complexity without clear benefit

---

### Proposed Clarification

#### Signal Types (Behavioral Observations)

These are **conceptual categories** of behavioral patterns we detect:

```python
# Not a database enum — just conceptual taxonomy
SIGNAL_TYPES = {
    "upcoming_meeting": "Calendar event with external attendees in next 48h",
    "thread_silence": "Gmail thread with no reply in 5+ days",
    "contact_gap": "No communication with key contact in N days",
    "mention_pending": "Slack mention with no response in N hours",
    "ownership_alert": "Notion page you own was edited by someone else",
}
```

#### Deliverable Types Created

Signal processing creates deliverables using **existing or new deliverable types**:

```python
# Deliverable types (database values)
SIGNAL_CREATES = {
    "upcoming_meeting" -> deliverable_type="meeting_prep",      # Already exists
    "thread_silence" -> deliverable_type="silence_alert",       # NEW, needs prompt template
    "contact_gap" -> deliverable_type="contact_drift",          # NEW, needs prompt template
    "mention_pending" -> deliverable_type="mention_followup",   # Future
    "ownership_alert" -> deliverable_type="ownership_brief",    # Future
}
```

#### Deduplication Keys

The `signal_history` table tracks which signals have already triggered deliverables:

```sql
CREATE TABLE signal_history (
  signal_type TEXT,      -- "meeting_prep", "silence_alert", etc. (matches deliverable_type)
  signal_ref TEXT,       -- event_id, thread_id, contact_email
  ...
);
```

**Current approach**: Uses `deliverable_type` as `signal_type` (conflated).
**Better approach**: Separate signal taxonomy from deliverable taxonomy (not worth refactoring now).

---

## Implementation Gaps

### What Exists (Phase 3+4 Complete)

✅ `meeting_prep` deliverable type — fully implemented
✅ Signal extraction for calendar events — queries live Google Calendar API
✅ Signal extraction for Gmail silence — queries live Gmail API
✅ Deduplication via `signal_history` table
✅ User preferences via `user_notification_preferences` extension
✅ Split cron: hourly (calendar) + daily 7 AM (silence)

---

### What's Missing

#### 1. New Deliverable Types Need Prompt Templates

`silence_alert` and `contact_drift` are referenced in signal_processing.py but **not defined** in deliverable_pipeline.py:

```python
# api/services/deliverable_pipeline.py

TYPE_PROMPTS = {
    # ... existing types ...

    # MISSING: Need to add
    "silence_alert": """You are drafting a follow-up message for a Gmail thread that has gone silent.

The thread involves an external contact who hasn't replied in several days. Your task is to:
1. Summarize the thread context
2. Draft a gentle, contextual nudge
3. Respect the relationship tone (formal vs casual)
4. Avoid being pushy — offer value or a question

{sections_list}
""",

    "contact_drift": """You are identifying a relationship gap and suggesting action.

This contact hasn't been reached out to in longer than their typical cadence. Your task is to:
1. Note the relationship context (client, colleague, mentor, etc.)
2. Suggest why reconnecting might be valuable
3. Draft a natural, non-awkward opening message
4. Reference recent shared context if available

{sections_list}
""",
}

SECTION_TEMPLATES = {
    # ... existing types ...

    "silence_alert": {
        "thread_context": "Thread Context",
        "draft_message": "Suggested Follow-Up",
        "tone_notes": "Relationship & Tone Notes",
    },

    "contact_drift": {
        "relationship_context": "Relationship Context",
        "reconnection_rationale": "Why Reconnect Now",
        "draft_opening": "Suggested Opening",
        "recent_context": "Recent Shared Context",
    },
}
```

**Also need** in routes/deliverables.py:

```python
# Add to DELIVERABLE_TYPES list
"silence_alert",
"contact_drift",

# Add to DELIVERABLE_TYPE_STATUS
"silence_alert": "beta",
"contact_drift": "beta",

# Add to get_type_classification()
if deliverable_type == "silence_alert":
    return {
        "binding": "platform_bound",
        "temporal_pattern": "reactive",
        "primary_platform": "gmail",
        "freshness_requirement_hours": 1,
    }

if deliverable_type == "contact_drift":
    return {
        "binding": "cross_platform",  # Needs Gmail + Calendar + Slack to detect gaps
        "temporal_pattern": "reactive",
        "freshness_requirement_hours": 4,
    }
```

---

#### 2. Frontend Type Selector

The TypeSelector component doesn't include signal-emergent types because users can't manually create them. But if a user **promotes** a signal-emergent deliverable to recurring, they might want to edit it.

**Decision**: Don't add `silence_alert`/`contact_drift` to the type selector. Signal-emergent deliverables are system-created. If promoted, they keep their type and become recurring without needing UI selection.

---

#### 3. Contact Drift Signal Extraction

Currently only `calendar_signals` and `silence_signals` are extracted. Need to implement `contact_drift` extraction:

```python
# api/services/signal_extraction.py

@dataclass
class ContactDriftSignal:
    contact_email: str
    contact_name: str
    days_since_contact: float
    average_cadence_days: float
    last_interaction_platform: str  # "gmail" | "slack" | "calendar"
    relationship_context: str       # "client" | "colleague" | "vendor" | etc.

async def _extract_contact_drift_signals(client, user_id: str, now: datetime) -> list[ContactDriftSignal]:
    """
    Detect contacts where communication cadence has lapsed.

    This requires analyzing:
    - Gmail sent messages (who have we emailed?)
    - Calendar events (who have we met with?)
    - Slack DMs (who have we messaged?)

    Then computing per-contact:
    - Average cadence (time between contacts)
    - Time since last contact
    - Flag if gap > 2x average cadence
    """
    # Complex logic — deferred to future phase
    return []
```

This is **expensive** (requires analyzing full communication history) and deferred to future phases.

---

## Recommended Naming Conventions

Going forward, to reduce confusion:

### In Code Comments

```python
# GOOD: Be explicit
"Extract calendar signals (upcoming events with external attendees)"
"Create meeting_prep deliverable for calendar signal"

# BAD: Ambiguous
"Process meeting_prep signals"
```

### In Variable Names

```python
# GOOD: Clear context
signal_summary: SignalSummary          # The extracted behavioral observations
deliverable_type: str = "meeting_prep" # The content type we'll produce
signal_type: str = "meeting_prep"      # The deduplication key (conflated with type)

# BAD: Reused terms
signal: str  # Is this a signal observation or a deliverable type?
```

---

## Summary

### Hardened Conceptual Framework (2026-02-20)

**Signal processing is orchestration that creates artifacts.**

**Three-Layer Model:**

1. **Signals** (behavioral observations) — Extracted from live APIs, ephemeral
2. **Deliverables** (content artifacts) — Created in database, versioned, delivered
3. **UI Grouping** (visual organization) — Platform vs Synthesis

**Key Principles:**

- **Two-phase execution**: Orchestration (signal reasoning) → Selective artifact creation (deliverable rows)
- **Hybrid action model**: `trigger_existing` (pure orchestration) + `create_signal_emergent` (artifact creation)
- **Signals observe platforms, deliverables synthesize across them**
- **SYNTHESIS = cross-platform work** (including all signal-emergent deliverables)
- **Origin records provenance**, not current state (`signal_emergent` is immutable)
- **Type classification drives execution**, not UI grouping
- **Schema evidence**: `signal_history.deliverable_id` FK proves artifact creation pattern

**Implementation Status:**

- ✅ `meeting_prep` fully implemented (reuses existing type)
- ✅ Two-phase model implemented (create + trigger actions)
- ✅ Infrastructure complete (signal_history, preferences, split cron)
- ⚠️ `silence_alert` needs prompt template + type classification
- ⚠️ `contact_drift` needs prompt template + type classification + extraction logic
- ⚠️ LLM prompt currently favors `create_signal_emergent` over `trigger_existing`

**Architectural Alignment:**

- All three deliverable origins (user/analyst/signal) create deliverable rows
- Signal-emergent deliverables are **not special cases** — they're normal deliverables with different provenance
- Promotion preserves `origin=signal_emergent` (provenance tracking)
- Fits cleanly into Path B Phase 1 (orchestrator, not TP)

---

## Next Steps

If we want to **complete signal processing taxonomy**:

1. Add `silence_alert` and `contact_drift` prompt templates to deliverable_pipeline.py
2. Add type classifications to routes/deliverables.py
3. Implement `_extract_contact_drift_signals()` in signal_extraction.py
4. Update frontend to handle these types if promoted to recurring

**Or** we can ship with just `meeting_prep` and add silence/drift types when we have real user demand for them.
