# Cognitive Dashboard Design — ADR-128 Phase 6

**Date:** 2026-03-21
**Status:** Active
**Related:**
- [ADR-128: Multi-Agent Coherence Protocol](../adr/ADR-128-multi-agent-coherence-protocol.md) — governing ADR, Phases 0-5
- [Agent Presentation Principles](AGENT-PRESENTATION-PRINCIPLES.md) — source-first mental model, card anatomy
- [Projects Product Direction](PROJECTS-PRODUCT-DIRECTION.md) — settled decision #8 (PM as coherence monitor)
- [Workspace Layout & Navigation](WORKSPACE-LAYOUT-NAVIGATION.md) — WorkspaceLayout, persistent panel
- [ADR-124: Project Meeting Room](../adr/ADR-124-project-meeting-room.md) — project surface architecture

---

## The Problem

ADR-128 Phases 0-4 built the **data substrate** — contributors self-assess, PM reads assessments, directives persist from chat, contributors read PM's project assessment. This intelligence exists in workspace files but is invisible to the user. The user can browse files in the Context tab, but there's no at-a-glance view of agent cognitive state.

The Workfloor currently shows **operational state** — what agents are doing (pulse decisions: generate/observe/wait/escalate). ADR-128 adds **cognitive state** — what agents are thinking (mandate fitness, confidence, domain coverage). These are different axes of the same entity.

## Decision: Evolve the Workfloor (Option B)

A separate "Cognition" tab (Option C) was considered and rejected. The whole point of ADR-128 is that intelligence substrates aren't silos — they flow into each other. A user looking at an agent's pulse state of "observe" wants to immediately know *why* — is it low confidence? stale context? mandate unclear? Separating operational and cognitive views forces tab-switching to answer the obvious follow-up.

**The Workfloor becomes the Situation Room** — one surface showing both what agents are doing and what they're thinking.

---

## Design: Workfloor Card Evolution

### Current State

Each agent card shows: avatar (with pulse ring for "generate") + name + role badge + pulse decision + reason + timestamp.

```
┌─────────────────────────────────────────────────────┐
│ [Avatar]  Slack Recap              DIGEST            │
│           ● Generating — fresh content available     │
│                                                3:15p │
└─────────────────────────────────────────────────────┘
```

### Evolved Contributor Card

Add a compact 4-bar cognitive assessment below the pulse state. Bars only appear after the agent's first run (not for "awaiting first run" initial state).

```
┌──────────────────────────────────────────────────────┐
│ [Avatar+ring]  Slack Recap              DIGEST       │
│                ● Generating — fresh content available │
│                                                      │
│    Mandate  ████████░░  high                         │
│    Fitness  ██████░░░░  medium — missing #eng thread │
│    Context  ████████░░  high                         │
│    Output   ██████░░░░  medium                       │
│                                              2:15 PM │
└──────────────────────────────────────────────────────┘
```

**Key design choices:**

- **Cognitive bars only appear after first assessment** — agents in "Initial (awaiting first run)" state show current "No activity yet" text. No false information.
- **3-level bar visualization** — high/medium/low map to filled segments (8/6/3 of 10). Not numeric. At a glance you see shape.
- **Low-confidence fields get annotation** — only medium/low show the "why" text (truncated). High is silent. Compress routine status (same principle as PM prompt).
- **Color-coded levels**: high = green-ish, medium = amber-ish, low = red-ish. Uses muted tones consistent with existing palette.
- **When all 4 dimensions are high** — collapse to single line: "✓ All dimensions healthy" to avoid visual noise on well-functioning agents.

### Evolved PM Card

PM uses its own cognitive model (5 prerequisite layers), not the contributor 4-bar. Show a horizontal layer progress indicator.

```
┌──────────────────────────────────────────────────────┐
│ [Avatar+ring]  Project Manager          PM           │
│                ● Generating — assembly ready          │
│                                                      │
│    ✓ Commitment  ✓ Structure  ✗ Context  · Quality   │
│    "Slack connected but objective needs financial     │
│     data — context-objective mismatch"               │
│                                              2:30 PM │
└──────────────────────────────────────────────────────┘
```

**Key design choices:**

- **5 layers as horizontal indicators** — ✓ (green, satisfied) / ✗ (red, broken) / · (grey, not yet evaluated). First broken layer gets the summary line.
- **Stop-at-first-broken principle** — mirrors PM's own reasoning. Layers after the broken one show as grey dots, not evaluated.
- **Summary line** — extracted from `project_assessment.md`, capped at ~120 chars. Only shown when there's a broken layer.
- **"No assessment yet" state** — shows "PM has not pulsed" text (from initial seed). No fake layers.

### Agents Without Cognitive Data

Agents that predate ADR-128 or haven't had their first run show the current card layout unchanged — pulse state only, no cognitive bars. Graceful degradation.

---

## Design: Pulse Timeline Evolution

The "Recent Pulse Activity" timeline below the cards currently shows only `agent_pulsed` and `pm_pulsed` events.

**New event types to surface** (derived, not stored — computed by comparing current vs previous state):

| Event | Source | Example |
|-------|--------|---------|
| Confidence change | Compare self_assessment entries | "Slack Recap confidence dropped: high → medium" |
| PM layer change | Compare project_assessment snapshots | "PM constraint moved: Structure → Context" |
| Directive persisted | `memory/directives.md` write events | "PM persisted decision: focus on action items" |

**Implementation note**: These are not new `activity_log` events. They're derived on the frontend by comparing the current cognitive state to what was shown previously, or by detecting WriteWorkspace calls in the activity log metadata.

---

## Design: InlineProfileCard Enrichment

The right-panel profile card (Team tab → click agent) currently shows: avatar, name, role badge, status, bio, runs/approval, thesis, last active, PM brief, contributions.

### New Section: Cognitive State

Insert between "runs/approval" and "thesis" sections:

```
┌─ Profile Card ──────────────────────────┐
│ [Avatar] Slack Recap                    │
│ DIGEST · ● Active                       │
│                                         │
│ "Monitors Slack channels for..."        │  ← bio (existing)
│                                         │
│ 12 runs · 83% approved                  │  ← run stats (existing)
│                                         │
│ ┌─ Self-Assessment (latest) ──────────┐ │  ← NEW
│ │ Mandate:  high                      │ │
│ │ Fitness:  medium — scope covers 3/4 │ │
│ │ Context:  high — 2h old             │ │
│ │ Output:   medium                    │ │
│ │                                     │ │
│ │ Trend: ■ ■ ■ □ ■  (last 5 runs)   │ │  ← confidence trajectory
│ └─────────────────────────────────────┘ │
│                                         │
│ "The team communicates primarily..."    │  ← thesis (existing)
│                                         │
│ Last active 2 hours ago                 │  ← existing
│                                         │
│ ┌─ PM Brief ─────────────────────────┐ │  ← existing
│ │ Focus on action items, not...      │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ 3 contributions                         │  ← existing
└─────────────────────────────────────────┘
```

**Confidence trajectory** — 5 squares (last 5 runs of overall output confidence): ■ filled = high, □ half = medium, ○ empty = low. Gives trajectory at a glance.

**PM profile card** — shows the current constraint layer summary instead of the 4-bar contributor view. Same data as the PM Workfloor card but with more detail (full assessment text, not truncated).

**No cognitive data** — section is simply absent. No empty state, no placeholder.

---

## Data Flow: Backend → Frontend

### Existing data path

`GET /api/projects/{slug}` → enriches contributors with agent table data + workspace identity (bio, thesis, seniority). Returns `ProjectDetail` with `contributors: ProjectMember[]`.

### New enrichment

In the same contributor enrichment loop (`api/routes/projects.py`, lines 163-206), add:

1. **Parse `memory/self_assessment.md`** — extract latest entry's 4 dimensions (mandate/fitness/currency/confidence) as `{level: "high"|"medium"|"low", reason?: string}`. Also extract up to 5 historical confidence levels for trajectory.
2. **Parse `memory/project_assessment.md`** (project-level, not per-contributor) — extract PM's constraint layer state. Return as top-level `project_cognitive_state` alongside `pm_intelligence`.

### New fields on `ProjectMember`

```typescript
interface CognitiveAssessment {
  mandate: { level: 'high' | 'medium' | 'low'; reason?: string };
  fitness: { level: 'high' | 'medium' | 'low'; reason?: string };
  currency: { level: 'high' | 'medium' | 'low'; reason?: string };
  confidence: { level: 'high' | 'medium' | 'low'; reason?: string };
  // Trajectory: most recent 5 output confidence levels (newest first)
  confidence_trajectory?: ('high' | 'medium' | 'low')[];
}

// Added to ProjectMember
cognitive_state?: CognitiveAssessment | null;
```

### New top-level field on project detail response

```typescript
interface PMCognitiveState {
  layers: {
    commitment: 'satisfied' | 'broken' | 'unknown';
    structure: 'satisfied' | 'broken' | 'unknown';
    context: 'satisfied' | 'broken' | 'unknown';
    quality: 'satisfied' | 'broken' | 'unknown';
    readiness: 'satisfied' | 'broken' | 'unknown';
  };
  constraint_summary?: string;  // First broken layer's summary
  raw_assessment?: string;      // Full text (for PM profile card)
}

// Added to project detail response
project_cognitive_state?: PMCognitiveState | null;
```

### Parsing strategy

**Contributor self_assessment.md** — already uses structured markdown:
```markdown
## Run 2026-03-21T14:00Z
- **Mandate**: Weekly Slack channel recap (high)
- **Domain Fitness**: Covers 3 of 4 assigned channels (medium — missing #eng-infra)
- **Context Currency**: Data is 2 hours old (high)
- **Output Confidence**: Good coverage but thin on action items (medium)
```

Regex: `\*\*(\w[\w ]+)\*\*:\s*(.+?)\s*\((high|medium|low)(?:\s*—\s*(.+?))?\)` per field.

**PM project_assessment.md** — is JSON (PM produces JSON, D3 decision). Parse the JSON, map layer states.

---

## What This Does NOT Include

- **Flow activity visualization** — when PM last read contributor X, when Y last read PM brief. Future.
- **Interactive cognitive drill-down** — clicking a bar to see full assessment history. Future.
- **Historical trajectory charts** — beyond the 5-square sparkline. Future.
- **Directive/decision management UI** — browsing/editing accumulated directives. Use Context tab file browser.
- **New activity_log event types** — derived events are computed, not stored.

---

## Implementation Sequence

1. **Backend**: Parse `self_assessment.md` → `cognitive_state` per contributor in `get_project()` enrichment loop
2. **Backend**: Parse `project_assessment.md` → `project_cognitive_state` in project detail response
3. **Types**: Add `CognitiveAssessment` and `PMCognitiveState` to `web/types/index.ts`
4. **WorkfloorView**: Evolve agent cards — 4-bar for contributors, 5-layer for PM
5. **InlineProfileCard**: Add cognitive state section + trajectory
6. **Pulse timeline**: Surface cognitive change events (stretch — can defer)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-21 | Initial design — Workfloor evolution, InlineProfileCard enrichment, data flow spec |
