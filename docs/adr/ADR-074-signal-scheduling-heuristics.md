# ADR-074: Signal Scheduling Heuristics

**Status**: Proposed
**Date**: 2026-02-23
**Depends on**: ADR-072 (Unified Content Layer), ADR-073 (Unified Fetch Architecture)

## Context

The current signal processing pipeline runs hourly (per `unified_scheduler.py`, when `now.minute < 5`) and makes a **Haiku LLM call per user per cycle** to decide whether platform content warrants action. At production scale (N users × 2 filters × 24 hours = 48N LLM calls/day), this becomes a significant cost driver for what is fundamentally a scheduling/triage decision.

### Current Flow

```
unified_scheduler (hourly, minute < 5)
  └─ For each user with active platforms:
       └─ For each filter (calendar_only, non_calendar):
            1. extract_signal_summary() → reads platform_content (ADR-073)
            2. process_signal() → Haiku LLM call ($0.25/MTok in, $1.25/MTok out)
               - System prompt: ~1,200 tokens
               - User prompt (signals + context): ~2,000-5,000 tokens
               - Response: ~200-500 tokens
            3. execute_signal_actions() → trigger_existing or create_signal_emergent
```

**Cost estimate** (100 users):
- 100 users × 2 filters × 24 hours = 4,800 Haiku calls/day
- ~3,500 input tokens × $0.25/MTok = ~$4.20/day input
- ~350 output tokens × $1.25/MTok = ~$2.10/day output
- **~$190/month** just for signal triage (before any actual content generation)

### What the LLM Actually Decides

The Haiku call (`signal_processing.py:78`) reasons over the `SignalSummary` and returns one of three actions:

1. **`trigger_existing`** — an active deliverable should regenerate based on fresh content
2. **`create_signal_emergent`** — new content warrants creating a new deliverable (e.g., meeting_prep)
3. **`no_action`** — nothing significant, skip

The decision inputs are:
- Platform content summaries (email subjects, calendar events, Slack messages)
- User context (memory entries)
- Active deliverables (titles, types, last generated)
- Recent activity log

## Proposal: Deterministic Heuristics

Replace the Haiku LLM call with rule-based heuristics that use the same data but evaluate deterministically. The key insight: **most signal triage decisions follow predictable patterns** that don't require natural language reasoning.

### Heuristic Rules

#### Rule 1: Freshness-Based Deliverable Triggering (`trigger_existing`)

**Already partially implemented** in `unified_scheduler.py:should_skip_deliverable()` via `has_fresh_content_since()`.

Extend to fully replace `trigger_existing`:
```
For each active deliverable:
  1. Get deliverable's source list (platforms + resource_ids)
  2. Check has_fresh_content_since(last_generated_at) for those sources
  3. If fresh content exists AND enough time has passed since last generation:
     → trigger regeneration
```

This replaces the LLM's judgment of "is this content significant enough to trigger?" with "is there new content for this deliverable's sources?"

#### Rule 2: Schedule-Based Meeting Prep (`create_signal_emergent`)

The primary emergent signal type is `meeting_prep`:
```
For each calendar event in next 24 hours:
  1. Has ≥2 external attendees
  2. No existing meeting_prep deliverable for this event
  3. User has relevant platform content (emails from attendees, Slack threads)
  → create meeting_prep deliverable
```

#### Rule 3: Volume Spike Detection (future)

```
If message_count(last_2h) > 3× average(last_7d) for a source:
  → flag for user attention (notification, not deliverable)
```

### What We Lose

The LLM can reason about content **semantics** — e.g., "this email from the CEO about Q3 results is more important than routine HR updates." Heuristics cannot make this judgment.

**Mitigation**: The content itself still goes through a full LLM generation pass when a deliverable is triggered. The heuristic only decides *whether* to trigger — the *quality* of the output is unchanged.

### Implementation Approach

#### Phase 1: Replace `trigger_existing` with Freshness Check

- Move `should_skip_deliverable()` logic from scheduler into a dedicated `signal_heuristics.py` service
- Add source-aware freshness checking (per-deliverable, not per-user)
- Remove the `process_signal()` → Haiku call for `trigger_existing` actions
- Keep `extract_signal_summary()` as-is (it already reads from platform_content)

#### Phase 2: Add Meeting Prep Heuristic

- Calendar event scanner: check events in next 24h window
- Attendee cross-reference: check for related platform content
- Auto-create `meeting_prep` deliverables when criteria match

#### Phase 3: Remove Signal Processing LLM Path

- Delete `signal_processing.py` (the Haiku LLM call)
- Simplify `unified_scheduler.py` signal section to call heuristics directly
- Keep `signal_extraction.py` (reads platform_content, useful for other consumers)

### File Impact

| File | Change |
|------|--------|
| `api/services/signal_heuristics.py` | **New** — deterministic rule engine |
| `api/services/signal_processing.py` | **Delete** (Phase 3) |
| `api/services/signal_extraction.py` | **Keep** — platform_content reader |
| `api/jobs/unified_scheduler.py` | Update signal section to call heuristics |
| `api/routes/signal_processing.py` | Update to use heuristics (or keep for manual trigger) |

### Existing Infrastructure

These already exist and support the heuristic approach:

- `platform_content.has_fresh_content_since()` — freshness check per user/platform/resource
- `sync_registry` — tracks last sync time and cursor per source
- `should_skip_deliverable()` — partial freshness gate already in scheduler
- `extract_signal_summary()` — reads platform_content (ADR-073 compliant)

## Decision

**Proposed** — awaiting implementation approval.

Recommended phased approach: Phase 1 first (eliminate majority of Haiku calls), measure impact, then Phase 2-3.

## Consequences

### Positive
- **~$190/month savings** at 100 users (scales linearly)
- **Lower latency** — heuristic evaluation is <10ms vs ~500ms for Haiku call
- **Deterministic behavior** — same inputs always produce same scheduling decisions
- **Debuggable** — can trace exactly why a deliverable was/wasn't triggered

### Negative
- **Loss of semantic reasoning** at triage level — may miss nuanced signals
- **More rules to maintain** — each new signal type needs explicit logic
- **Testing overhead** — need to validate heuristic coverage matches LLM decisions

### Neutral
- Content generation quality unchanged (still uses full Claude model)
- Signal extraction unchanged (still reads platform_content)
- User-visible behavior should be similar (most LLM triage decisions are predictable)
