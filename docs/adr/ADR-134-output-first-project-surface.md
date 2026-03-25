# ADR-134: Workfloor-First Project Surface

> **Status**: Phase 1 Implementation
> **Superseded by**: [ADR-138](ADR-138-agents-as-work-units.md) — Project layer collapsed. PM dissolved. Tasks replace projects.
> **Date**: 2026-03-23 (revised)
> **Authors**: KVK, Claude
> **Evolves**: ADR-124 (Meeting Room → workfloor-first), ADR-133 (phase state surfacing)
> **Extends**: ADR-130 (composed HTML rendering), ADR-128 (cognitive state visualization)

---

## Context

ADR-124 established a 5-tab project page with chat as the default surface. This was designed before ADR-133 changed the execution model to PM-coordinated phases.

The current layout treats conversation as the primary interface. But the user's mental model is **watching a team work** — seeing agents at their desks, seeing what they've produced, intervening when needed.

### The Sims/Tamagotchi principle

The project page should feel like looking into a workspace. You see your team. They're alive — generating, thinking, observing, waiting. You see their latest output. You can walk over to talk to any of them. You don't navigate tabs — you observe a scene.

---

## Decision

### Single-surface workfloor with chat drawer

One page. No tabs. No view toggles. The workfloor IS the project.

```
┌──────────────────────────────────────────────────────────┐
│ PROJECT HEADER                                    [⚙]   │
│ Title · purpose                                          │
│ [Research ✓] → [Analysis ●] → [Narrative ○] → [Deliver] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  WORKFLOOR — your team at work                           │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐    │
│  │ 🟢       │  │ 🔵       │  │ ⚪       │  │ 🟣   │    │
│  │ Market   │  │ Data     │  │ Board    │  │ PM   │    │
│  │Researcher│  │ Analyst  │  │ Writer   │  │      │    │
│  │          │  │          │  │          │  │"Looks│    │
│  │"Found 3  │  │"Analyzing│  │ Waiting  │  │ good │    │
│  │ entrants"│  │ Q2 data" │  │ for P2   │  │ so   │    │
│  │          │  │          │  │          │  │ far" │    │
│  │ ✓ Done   │  │ ● Active │  │ ○ Queued │  │      │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────┘    │
│                                                          │
│  ────────────────────────────────────────────────────    │
│                                                          │
│  LATEST OUTPUT                          v2 · Mar 23      │
│  ┌────────────────────────────────────────────────┐      │
│  │ Composed HTML or markdown preview              │      │
│  └────────────────────────────────────────────────┘      │
│  Previous: v1 Mar 16                                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Chat as drawer overlay

Chat doesn't replace the workfloor. It slides in from the right when triggered.

**Trigger 1**: Click an agent card → opens chat drawer scoped to that agent.
**Trigger 2**: Click chat icon in header → opens group chat (meeting room).
**Dismiss**: Close drawer → back to full workfloor.

```
┌──────────────────────────────┬───────────────────────────┐
│ Workfloor (compressed)       │ Chat with Researcher    × │
│                              │                           │
│ ┌──┐ ┌──┐ ┌──┐ ┌──┐        │ Profile: Market Researcher │
│ │  │ │  │ │  │ │  │        │ Briefer · 12 runs · 94%   │
│ └──┘ └──┘ └──┘ └──┘        │                           │
│                              │ You: Focus on enterprise  │
│ Latest Output                │ Agent: I'll adjust my     │
│ ┌──────────────────────┐     │ next run to emphasize...  │
│ │ Composed HTML         │     │                           │
│ └──────────────────────┘     │ [Type message...]         │
└──────────────────────────────┴───────────────────────────┘
```

The workfloor stays visible — cards compress but remain. You're talking to one agent while seeing the whole team.

### Settings as gear icon modal

No settings tab. Gear icon in header opens a modal/drawer with:
- Objective editing
- Delivery configuration
- Archive action
- File browser (Context) accessible here for power users

---

## Agent Card Design

Each card is a personified character:

### Visual state
- **Green ring (pulsing animation)** = actively generating
- **Blue ring (breathing animation)** = observing, sensing domain
- **Gray (static)** = waiting for phase dispatch
- **Amber (attention)** = escalated, needs user input

### Content
- **Avatar** with role-colored ring
- **Display name** (from agent title)
- **Role badge** (Researcher, Analyst, Writer, etc.)
- **Thought bubble** — what the agent is doing/thinking (from pulse reason or latest assessment)
- **Phase badge** — ✓ done / ● active / ○ queued for current phase
- **Cognitive bars** (hover or always-minimal) — mandate/fitness/context/confidence

### PM Card (special)
- Purple-themed
- Shows coordination decision ("Dispatched Phase 1 contributors")
- Constraint layer indicators (5 layers: commitment/structure/context/quality/readiness)

### Interaction
- **Click** → opens chat drawer scoped to this agent
- **Hover** → shows expanded cognitive state + last assessment
- Active card has subtle highlight when chat drawer is open for it

---

## What stays from ADR-124

- Chat functionality (meeting room, @-mentions, agent attribution) — preserved in drawer
- ChatAgent class and agent_chat mode — unchanged
- Data scopes (group/agent/project) — unchanged
- All activity events — available in chat timeline

## What changes

| Before | After |
|--------|-------|
| 5 tabs | Single surface |
| Chat as default view | Chat as drawer overlay |
| Workfloor as alternate view | Workfloor IS the page |
| Output buried in tab 4 | Output below workfloor |
| Participants as tab | Agent cards on workfloor |
| Settings as tab | Gear icon modal |
| Context as tab | Accessible via settings modal |
