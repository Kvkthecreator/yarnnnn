# ADR-134: Output-First Project Surface

> **Status**: Proposed
> **Date**: 2026-03-23
> **Authors**: KVK, Claude
> **Evolves**: ADR-124 (Meeting Room → output-first layout), ADR-133 (phase state surfacing)
> **Extends**: ADR-130 (composed HTML rendering), ADR-128 (cognitive state visualization)

---

## Context

ADR-124 established a 5-tab project page (Meeting Room, Participants, Context, Outputs, Settings) with chat as the default surface. This was designed before ADR-133 (PM-coordinated phase dispatch) changed the execution model.

The current layout puts **conversation first, work second**. But a solo founder opening their project wants to know:

1. **What is this project producing?** — objective + latest output
2. **What's happening right now?** — which agents are working, what phase
3. **Is there anything I need to do?** — approvals, edits, steering

Chat is for intervention, not observation. Outputs are the point.

### What's wrong with 5 tabs

- **Meeting Room as default**: forces the user into a chat interface when they may just want to see results
- **Outputs buried in tab 4**: the most important surface (what agents produced) requires 4 clicks to reach
- **Participants separate from work state**: team cards disconnected from phase progression
- **Context tab (file browser)**: useful for power users, not primary navigation
- **No phase indicator anywhere**: ADR-133's phase coordination is invisible

---

## Decision

### Two-panel layout, output-first

Replace the 5-tab structure with a continuous two-panel layout where the left panel leads with output and the right panel shows team + coordination state.

```
┌──────────────────────────────────────────────────────────┐
│ PROJECT HEADER (always visible)                          │
│                                                          │
│ Title                                    [⚙ Settings]    │
│ Objective: {deliverable} for {audience} — {purpose}      │
│                                                          │
│ Phase: [Research ✓] → [Synthesis ●] → [Assembly ○]       │
│ Last delivered: Mar 23 · Next delivery: in 2 days        │
└──────────────────────────────────────────────────────────┘

┌───────────────────────────┐  ┌───────────────────────────┐
│ LEFT PANEL                │  │ RIGHT PANEL               │
│                           │  │                           │
│ [Output] [Chat]  toggle   │  │ Team                      │
│                           │  │ ┌────┐ ┌────┐ ┌────┐     │
│ ┌───────────────────────┐ │  │ │ PM │ │Res │ │Wrt │     │
│ │                       │ │  │ └────┘ └────┘ └────┘     │
│ │ Latest Output         │ │  │ pulse + cognitive state   │
│ │ (composed HTML or md) │ │  │                           │
│ │                       │ │  │ ─────────────────────     │
│ │                       │ │  │                           │
│ └───────────────────────┘ │  │ PM Coordination           │
│                           │  │ "Dispatched researcher    │
│ Previous: v2 · v1        │  │  and analyst for Phase 1"  │
│                           │  │                           │
│ ── or when Chat mode ──  │  │ ─────────────────────     │
│                           │  │                           │
│ Meeting room chat         │  │ Work Plan                 │
│ (existing ADR-124)        │  │ ☑ Phase 1: Research       │
│                           │  │ ● Phase 2: Synthesis      │
│                           │  │ ○ Phase 3: Assembly       │
│                           │  │                           │
└───────────────────────────┘  └───────────────────────────┘
```

### Design principles

1. **Output is the hero** — latest composed HTML output rendered inline, prominently. This is what the user cares about.
2. **Phase progression always visible** — header shows current phase as a horizontal stepper.
3. **Team cards show coordination state** — compact workfloor cards in right panel (not a separate tab). Shows who's running, who's waiting, cognitive state bars.
4. **PM coordination surfaced** — PM's latest decision (dispatch, advance, steer) shown as a status card. Not buried in activity timeline.
5. **Work plan as checklist** — structured phases rendered as a checklist in right panel. Collapsible.
6. **Chat is a mode, not the default** — toggle between Output view (default) and Chat view (for intervention). Chat preserves full ADR-124 meeting room functionality.
7. **Settings via gear icon** — not a tab. Opens drawer or modal.
8. **Context (file browser) accessible via link** — drill-down, not primary surface. Accessible from right panel or settings.

### What stays from ADR-124

- Chat functionality (meeting room, @-mentions, agent attribution) — preserved as toggle mode
- Agent participation model (routing, ChatAgent class) — unchanged
- Data scopes (group/agent/project) — unchanged
- Activity events in timeline — preserved within chat mode

### What changes from ADR-124

- **Default surface**: chat → output preview
- **Tab structure**: 5 tabs → 2-panel continuous layout
- **Participants**: separate tab → compact cards in right panel
- **Outputs**: separate tab → hero position in left panel
- **Settings**: tab → gear icon drawer
- **Context**: tab → link in right panel (or gear drawer)

---

## Left Panel: Output / Chat Toggle

### Output Mode (default)

Shows the latest agent output:
1. **Hero output**: composed HTML via iframe (ADR-130 Phase 2), or markdown fallback
2. **Output history**: clickable version list (v3, v2, v1) with status badges
3. **Delivery status**: when it was last delivered, next scheduled delivery
4. **Actions**: approve, edit, request re-run

### Chat Mode

Full ADR-124 meeting room:
- Merged timeline (activity events + chat messages)
- @-mention agent picker
- Share file form
- PM as default interlocutor

Toggle is a simple button pair at the top of the left panel. State preserved when switching.

---

## Right Panel: Team + Coordination

### Team Section (top)

Compact workfloor cards — same data as current Workfloor view but:
- **Grouped by phase**: Phase 1 agents | Phase 2 agents | Unassigned
- **Dispatch status badge**: dispatched (green pulse), running, waiting
- **Click to expand**: shows profile card inline (existing ADR-128 cognitive state)
- **PM card prominent**: shows current coordination decision + constraint layers

### PM Coordination Card (middle)

Always visible:
- **Latest PM decision**: "Dispatched researcher + analyst for Phase 1" or "Waiting — Phase 2 blocked"
- **Quality assessment snippet**: if PM has assessed, show verdict
- **Active briefs count**: "2 briefs written for Phase 2 contributors"

### Work Plan Section (bottom)

Rendered from `memory/work_plan.md` + `phase_state.json`:
- Phase checklist with status icons (✓ complete, ● in progress, ○ blocked/pending)
- Per-phase: contributor assignments + completion status
- Collapsible sections

---

## API Changes

### Existing endpoints (no changes needed)

- `GET /projects/{slug}` — already returns contributors, PM intelligence, cognitive state
- `GET /projects/{slug}/activity` — already returns all event types
- `GET /projects/{slug}/outputs` — already returns output manifests

### New data in existing endpoints

- `GET /projects/{slug}` response gains:
  - `phase_state`: parsed from `memory/phase_state.json` (or null)
  - `work_plan`: raw content from `memory/work_plan.md` (or null)
  - `latest_output`: most recent output manifest + composed_html flag

---

## Phases

### Phase 1: Layout restructure

- Replace 5-tab structure with 2-panel layout
- Project header with objective + phase indicator
- Left panel: output/chat toggle (output default)
- Right panel: compact team cards + PM coordination card + work plan checklist
- Settings → gear icon drawer

### Phase 2: Data wiring

- API: add phase_state + work_plan to project detail response
- Phase indicator: parse phase_state.json for stepper
- Work plan: render structured markdown as checklist
- PM coordination card: latest pm_pulsed event + quality assessment

### Phase 3: Output enhancement

- Hero output: render composed HTML inline (iframe or dangerouslySetInnerHTML)
- Output history: version picker with preview
- Approve/edit/re-run actions on output

---

## Trade-offs

### Accepted

1. **Chat demoted from default** — Chat is still fully functional but requires one click to access. Accepted because output is the primary user concern.
2. **5 tabs → continuous layout** — More information density, less navigation. Accepted because tabs were click-expensive for the most common flow.
3. **Context tab removed from primary nav** — File browser is a power-user feature. Accessible via settings or link.

### Rejected

1. **Removing chat entirely** — Chat is essential for user steering and @-mention interaction. Just not the default.
2. **Separate workfloor page** — Workfloor cards work well in a compact right panel. No need for a dedicated route.
3. **Phase indicator as modal/drawer** — Phase state is critical context. Must be always visible in header.
