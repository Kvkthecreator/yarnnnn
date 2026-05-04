# Workfloor Liveness — Dynamic Agent Office

**Date:** 2026-03-25
**Status:** Archived — never shipped. SURFACE-ARCHITECTURE.md v2 superseded through v9.1 (ADR-163/167/214/241). ADR-139 (workfloor surface) dissolved into ADR-163/167. ADR-140 (agent workforce) superseded by ADR-176 then ADR-188/205. "Workfloor" as a surface name retired; /chat is now HOME_ROUTE. Retained as design-intent record for future liveness/presence features.
**Depends on:** [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md) v2 (archived), [ADR-139](../adr/ADR-139-workfloor-task-surface-architecture.md), [ADR-140](../adr/ADR-140-agent-workforce-model.md)
**Related:** [AGENT-PRESENTATION-PRINCIPLES.md](AGENT-PRESENTATION-PRINCIPLES.md) (source-first mental model → extended with liveness)

---

## Problem

The workfloor has the right structure (agent rooms, live tasks, TP card, resizable panels, chat drawer) but feels static. Cards are styled boxes with text — not a living office where you can tell at a glance who's working, who's idle, and what's happening.

The reference inspirations (OpenClaw, tamagotchi, factory dashboards) all share one trait: **ambient state communication** — the interface tells you what's happening without you reading labels.

## Principle: Singular Animation Language

One cohesive visual system across all agent states. Not a different trick per card — a consistent vocabulary of motion and light that scales from 1 agent to 20.

| Signal | Communicates | Perceived as |
|--------|-------------|--------------|
| Pulse/glow | Active work happening now | "Alive, busy" |
| Steady light | Ready, healthy | "Calm, available" |
| Dimmed | Paused or empty | "Sleeping, waiting" |
| Attention ring | Error or needs action | "Look at me" |
| Breathing | Idle but present | "There, not urgent" |

---

## Agent States × Visual Treatment

### Working (generating output now)

The agent is actively producing. This should be the most visually prominent state.

```
Visual:
- Desk icon has a soft pulsing glow ring (type-color, 50% opacity)
- Task section highlighted with type-color background
- Subtle shimmer gradient sweep across the card (left-to-right, slow)
- Status dot: pulsing (existing, keep)
- "Working: {task title}" text in type-color

CSS:
@keyframes desk-glow {
  0%, 100% { box-shadow: 0 0 0 0 var(--agent-color-20); }
  50% { box-shadow: 0 0 12px 4px var(--agent-color-15); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

### Ready (has tasks, waiting for next run)

Calm, present. The agent is there and healthy.

```
Visual:
- Desk icon has a steady, subtle inner glow (no animation)
- Card border slightly more visible than paused
- Status dot: steady green
- Gentle breathing effect on the entire card (scale 1.0 → 1.005, very subtle)

CSS:
@keyframes breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.003); }
}
/* Applied at card level, duration: 4s, ease-in-out */
```

### Paused (deliberately paused by user)

Deliberately sleeping. Still visible, just muted.

```
Visual:
- Card opacity reduced to ~60%
- Desk icon desaturated (grayscale filter or muted color)
- No animation
- Status dot: amber, steady
- Task section shows but dimmed
```

### Empty (no tasks assigned)

An empty desk. Inviting, not sad.

```
Visual:
- Dashed border (existing)
- Desk icon is a placeholder (outline only, no fill)
- "No task assigned" in light italic
- Card has a subtle dashed-border pulse (every 6s, barely visible) suggesting "fill me"
```

### Error (last run failed)

Needs attention without being alarming.

```
Visual:
- Card border changes to red/attention color
- Desk icon gets a small attention badge (red dot, similar to notification)
- No aggressive animation — just color shift
- Status dot: red, steady (not pulsing — pulsing = working)
```

---

## TP Card (Orchestrator)

TP is always on — it's not a worker, it's the manager's office. Distinct treatment:

```
Visual:
- Primary color gradient (already done)
- Persistent subtle pulse on the chat icon (not the card — just the icon)
- "Online" indicator with slow fade-in-out pulse
- On hover: card lifts + icon brightens (invite to chat)
- No "desk" metaphor — TP doesn't have a task, it has conversations
```

---

## Polling (Ambient Refresh)

The workfloor should feel real-time without WebSockets.

```
Interval: 30 seconds
What refreshes:
- Agent list (status, latest_version_status, last_run_at)
- Task list (status, last_run_at)

Implementation:
- useEffect with setInterval in the main page
- On focus: immediate refresh (visibilitychange event)
- During chat drawer open: pause polling (avoid flickering)
- Stale indicator: if last poll > 60s, show subtle "last updated Xs ago"
```

---

## Implementation Approach

### Phase 1: CSS Animations (no libraries)

Pure CSS keyframes. No Framer Motion, no react-spring, no GSAP.

1. Define CSS custom properties per agent type color (--agent-color)
2. Working: `desk-glow` keyframe + `shimmer` gradient on card
3. Ready: `breathe` keyframe on card
4. Paused: opacity + grayscale filter
5. Error: border-color transition
6. TP: icon pulse

### Phase 2: Polling

1. 30-second interval for agent + task refresh
2. visibilitychange handler for immediate refresh on tab focus
3. Last-updated timestamp (optional, subtle)

### Phase 3: Transitions

1. State change transitions (ready → working should animate smoothly)
2. Card enter/exit animations when agents are created/archived
3. Task assignment animation (task "appears" on desk)

---

## What This Is NOT

- Not pixel art or sprites (we're not building a game)
- Not per-agent custom illustrations
- Not a real-time multiplayer canvas
- Not dependent on new backend APIs (uses existing list endpoints)
- Not a WebSocket implementation

This is **ambient CSS liveness** — the minimum visual treatment that makes static cards feel alive. The data model and layout are already correct.

---

## Success Criteria

A user opening the workfloor should be able to tell, without reading any text:
1. Which agents are working right now (glow + shimmer)
2. Which agents are ready (calm, steady)
3. Which agents need attention (red accent)
4. That the TP is available to chat (pulse on icon)
5. That the page is fresh (no stale data)

---

## Files to Modify

| File | Changes |
|------|---------|
| `web/app/(authenticated)/workfloor/page.tsx` | Add CSS classes for states, polling hook |
| `web/app/globals.css` (or new CSS module) | Keyframe definitions |
| `web/components/desk/ChatDrawer.tsx` | Accept pause-polling signal |

No new components. No new dependencies. CSS + a polling hook.
