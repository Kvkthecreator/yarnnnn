# ADR-089: Agent Autonomy & Context-Aware Triggers

**Status:** Proposed (Parked — parking condition now met; un-parking is a deliberate product decision)

**Parking condition update:** The original condition was "ADR-087 Phase 2 complete: `deliverable_memory` write paths are wired and demonstrably improve headless generation quality." ADR-087 Phase 2 is now complete and all three phases are implemented. The technical prerequisite is satisfied.

**Note on ADR-091:** `deliverable.acknowledge` is a *user-initiated* supervision action — the user asks TP to acknowledge a version, TP writes an observation. This is the opposite of autonomous: the agent acts because the user asked. It does not un-park this ADR. This ADR is about the agent noticing something and acting without being prompted.

**When to un-park:** Product decision — the technical gate is cleared. Un-park when the cost of context staleness between generations (Problem 2) or over-reactive full generations from event triggers (Problem 1) becomes felt in practice.
**Date:** 2026-03-03
**Authors:** Kevin Kim, Claude (analysis)
**References:**
- [ADR-087: Deliverable Scoped Context](ADR-087-workspace-scoping-architecture.md) — the `deliverable_memory` field this ADR writes to
- [ADR-088: Unified Input Processing](ADR-088-input-gateway-work-serialization.md) — the routing function this ADR's actions flow through
- [ADR-068: Signal-Emergent Deliverables](ADR-068-signal-emergent-deliverables.md) — existing signal detection + deliverable creation
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — headless execution mode used for autonomous actions
- [Pre-ADR Analysis](../analysis/workspace-architecture-analysis-2026-03-02.md) — Section 12.6 (Learning 6: Heartbeats), Section 13.6 (existing event-driven paths)
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — Step 3

---

## Context

YARNNN's agent currently acts only when explicitly triggered: by a user message (TP chat) or by a schedule/event (headless generation). Between triggers, the agent is dormant. All trigger actions produce the same outcome — a full deliverable version generation.

With `deliverable_memory` (ADR-087), a lighter action becomes possible: the agent notices new context relevant to a deliverable and updates the deliverable's accumulated knowledge without generating a full version. This is the difference between "the agent produces output when asked" and "the agent stays informed about its work."

### What already exists

YARNNN has three event-driven paths that are already implemented:

1. **Slack/Gmail webhooks** (`POST /webhooks/slack/events`, `POST /webhooks/gmail/push`) → match to deliverables via `event_triggers.py` → execute generation. A platform event triggering a full version.

2. **Signal processing** (hourly via `unified_scheduler.py`) → reads `platform_content`, runs Haiku reasoning → can create new deliverables with `origin=signal_emergent`. The most autonomous existing feature.

3. **Event trigger system** (`event_triggers.py`) → per-deliverable matching with cooldown tracking (`event_trigger_log`) → per-thread, per-channel, per-sender, and global cooldowns. Prevents duplicate triggering.

All three paths end in the same action: `execute_deliverable_generation()`. There is no lighter action available.

### What OpenClaw does differently

OpenClaw's HEARTBEAT.md defines periodic check-in tasks at the workspace level — the agent periodically reviews workspace state and takes lightweight actions (update notes, reorganize memory, flag attention-needed items). This is separate from producing output; it's the agent maintaining its own context.

OpenClaw also performs "memory flush" before session compaction — promoting durable information from conversation into memory files before older turns are summarized away. This prevents context loss during compaction.

---

## Problem Statement

The current trigger → action model is binary: something happens → generate a full version. This has two limitations:

1. **Over-reaction:** A minor Slack mention in a monitored channel triggers full deliverable generation (with cooldowns, but still heavy). Sometimes the right action is "note this for next time," not "produce a new version."

2. **Context staleness:** Between generations, the deliverable's context doesn't update. If 10 relevant Slack messages arrive between scheduled generations, the agent only sees them at generation time. With `deliverable_memory`, observations could accumulate continuously, making the next generation better-informed.

3. **No inter-session learning:** When a TP session ends, the conversation's insights are trapped in session messages until the nightly cron extracts them. With `deliverable_memory`, end-of-session summaries could be written immediately, making the deliverable's context current for the next interaction (TP or headless).

---

## Decision

**Park this ADR.** The concept is sound but depends on ADR-087 Phase 2 validating that `deliverable_memory` accumulation improves output quality. If accumulation doesn't help, autonomous context updates are wasted work.

### When to un-park

- ADR-087 Phase 2 complete: `deliverable_memory` write paths (feedback patterns, session summaries) are wired and demonstrably improve headless generation quality
- The need for "lighter than full generation" trigger actions becomes felt (e.g., too many unnecessary full generations from event triggers)

---

## Proposed Expansion (for when un-parked)

### New action type: update_context

Alongside the existing `execute_deliverable_generation()` action, add `update_deliverable_context()`:

| Aspect | generate (existing) | update_context (new) |
|--------|--------------------|--------------------|
| Model | Opus-level (full generation) | Haiku-level (lightweight observation) |
| Tool access | Read-only primitives (2-6 rounds) | Minimal (read platform_content, write deliverable_memory) |
| Output | New deliverable_version | Append to deliverable_memory sections |
| Cost | ~$0.05-0.50 per generation | ~$0.001-0.01 per update |
| Frequency | Per schedule (hourly/daily) | Per relevant event (with cooldown) |

### Trigger → action routing

The event trigger system (`event_triggers.py`) would route events to the appropriate action based on signal strength:

| Signal strength | Action | Example |
|----------------|--------|---------|
| High (direct mention, urgent keyword) | `execute_deliverable_generation()` | "@bot update the digest now" |
| Medium (relevant content in monitored source) | `update_deliverable_context()` | New messages in a monitored Slack channel |
| Low (tangentially related) | No action (log only) | Activity in an unmonitored channel |

This routing could be rule-based (trigger_config on the deliverable) or model-assessed (Haiku classifies signal strength).

### Specific autonomous actions

1. **Platform content observation:** New `platform_content` arrives for a deliverable's `sources`. Run Haiku to extract relevant observations → append to `deliverable_memory.observations`.

2. **End-of-session context flush:** When a TP session in deliverable scope ends (4h inactivity boundary), immediately append a session summary to `deliverable_memory.session_summaries` rather than waiting for the nightly cron.

3. **Signal accumulation:** When the signal processing system (hourly) detects a signal relevant to an existing deliverable (not creating a new one), append the signal to `deliverable_memory.signals` for the next generation to consider.

4. **Periodic workspace review (heartbeat):** Configurable per-deliverable: "every Monday, review accumulated context and update instructions if patterns have changed." This is OpenClaw's HEARTBEAT.md equivalent — the agent reviewing its own workspace.

---

## Consequences of Parking

### Positive
- No premature complexity in the trigger system
- Validates `deliverable_memory` value before expanding the write surface
- Keeps ADR-087 implementation focused on the core TP↔headless bridge

### Negative
- Context staleness continues between generations until un-parked
- Event triggers continue to only produce full generations (over-reaction persists)

### Neutral
- The signal processing system and event triggers continue working as-is
- Nightly cron continues as the only session summary writer

---

## Implementation Sketch (for when un-parked)

### Phase 1: End-of-session context flush

Simplest autonomous action. When a TP session in deliverable scope hits the 4h inactivity boundary, immediately append a summary to `deliverable_memory.session_summaries`. No new triggers — just a write path on session expiry.

- Change: `get_or_create_session()` detects expired scoped session → calls `append_session_summary_to_deliverable_memory()`
- Dependency: ADR-087 Phase 2 (deliverable_memory write paths exist)

### Phase 2: Lightweight context updates from events

Add `update_deliverable_context()` as a new action in `event_triggers.py`. Route medium-strength signals to context update instead of full generation.

- Change: `event_triggers.py` gains action routing logic. New function in `deliverable_execution.py` for lightweight context updates.
- Dependency: ADR-087 Phase 2 + Phase 1 of this ADR validated

### Phase 3: Periodic workspace review (heartbeat)

Add optional heartbeat configuration to deliverables (via `trigger_config` or a dedicated field). Periodic Haiku-level review of accumulated `deliverable_memory` — summarize, prune, update instructions if patterns changed.

- Change: New trigger type in `unified_scheduler.py`. Compaction logic for `deliverable_memory`.
- Dependency: Phase 2 of this ADR + sufficient `deliverable_memory` accumulation to warrant compaction

---

## Alternatives Considered

| Option | Pros | Cons | Why Not (for now) |
|--------|------|------|-------------------|
| Always generate on every event | Simple — one action type | Expensive, over-reactive, unnecessary generations | Current approach, acceptable but not ideal long-term |
| Pure rule-based context accumulation (no LLM) | Cheap, deterministic | Can't assess relevance — would accumulate noise | Insufficient for meaningful context updates |
| Real-time streaming context updates | Most current context | Engineering complexity, token cost, diminishes with scale | Overkill — batch/event-driven is sufficient |

---

## References

- [OpenClaw Memory Architecture](https://docs.openclaw.ai/concepts/agent-workspace) — HEARTBEAT.md, memory flush pattern
- [OpenClaw Memory Explained](https://lumadock.com/tutorials/openclaw-memory-explained) — daily logs, compaction, memory promotion
- [ADR-068 implementation](../adr/ADR-068-signal-emergent-deliverables.md) — the signal system this builds on
- [event_triggers.py](../../api/services/event_triggers.py) — existing event matching and cooldown infrastructure
