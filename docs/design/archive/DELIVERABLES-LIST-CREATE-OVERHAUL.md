# Deliverables List & Create Flow — Overhaul

**Date:** 2026-03-05
**Status:** Implemented
**Related:**
- [ADR-092: Mode Taxonomy](../adr/ADR-092-deliverable-intelligence-mode-taxonomy.md)
- [ADR-093: Type Taxonomy](../adr/ADR-093-deliverable-types-overhaul.md)
- [Workspace Layout](WORKSPACE-LAYOUT-NAVIGATION.md)
- [Deliverable Modes](../features/deliverable-modes.md)

---

## Problem

The deliverables list page grouped cards by destination platform (Slack / Email / Notion / Synthesis). This made sense when deliverables were mostly platform-bound digests. With ADR-092 adding 5 modes and ADR-093 adding 7 purpose-first types, the platform is now a secondary detail — the primary question for a user is *"how does this deliverable behave?"* (mode), not *"where does it send output?"* (destination).

The create flow had a similar mismatch: "Platform Monitors vs Synthesis Work" categories organized by data binding, not by user intent. Mode was invisible — only `deep_research` got `goal` mode, everything else defaulted to `recurring`. The `coordinator` type was missing entirely. A misleading "Draft mode" notice referenced removed governance.

---

## Decision

### List page: flat, mode-anchored

Drop platform grouping. Render a flat list where **mode** is the primary visual signal.

**Card layout:**
```
┌──────────────────────────────────────────────┐
│ [ModeIcon]  Title                    → email │
│             Digest · Mon 9:00am              │
│             Last: 2h ago  ✓Delivered  ▶Active│
└──────────────────────────────────────────────┘
```

- **Left icon**: Mode icon (Repeat/Target/Zap/Eye/Bot) with mode-specific color
- **Title row**: Title + optional origin badge ("Auto" for coordinator-created) + destination pill
- **Subtitle**: Type label + mode-aware status line
- **Bottom**: Last delivery time + delivery status + active/paused badge

**Mode-aware status line** (`getModeStatusLine`):

| Mode | Shows |
|------|-------|
| recurring | Schedule: "Mon 9:00am", "Daily 9:00am" |
| goal | "Goal: {status}" from `deliverable_memory.goal.status` |
| reactive | "{n} observations" from `deliverable_memory.observations.length` |
| proactive | "Next review {time}" from `proactive_next_review_at` |
| coordinator | Same as proactive |

### Create flow: intent-based sections + implicit mode

Replace "Platform Monitors / Synthesis Work" with three intent-based sections:

**"Keep me informed"** — ongoing monitoring:
- Digest (→ recurring)
- Status Update (→ recurring)
- Watch (→ proactive)

**"Get something done"** — produce specific output:
- Brief (→ recurring)
- Deep Research (→ goal)
- Custom (→ recurring)

**"Advanced"** — autonomous agents:
- Coordinator (→ coordinator)

Mode is set **implicitly** from the type selection — no manual mode picker. Schedule section is hidden for proactive/coordinator modes (they use review cadence, not fixed schedules).

---

## What was deleted

| Item | Reason |
|------|--------|
| `PlatformGroup` type, `GroupedDeliverables` interface | Platform grouping removed |
| `groupDeliverables()` function | Platform grouping removed |
| `PLATFORM_CONFIG` constant | Platform grouping removed |
| `getPlatformEmoji()` function | Replaced by `DeliverableModeBadge` |
| `DeliverableGroup` component | Replaced by flat list |
| `formatScheduleShort()` | Replaced by `getModeStatusLine()` |
| `TypeSelector.tsx` | Unused component, never imported |
| "Draft mode" notice in create flow | ADR-066 removed governance |

## What was created

| Item | Location |
|------|----------|
| `DeliverableModeBadge` component | `web/components/deliverables/DeliverableModeBadge.tsx` |
| `getModeStatusLine()` helper | `web/app/(authenticated)/deliverables/page.tsx` |
| `TYPE_LABELS` map | `web/app/(authenticated)/deliverables/page.tsx` |
| Coordinator type definition | `web/components/surfaces/DeliverableCreateSurface.tsx` |

## Files changed

| File | Change |
|------|--------|
| `web/components/deliverables/DeliverableModeBadge.tsx` | Created — shared mode badge (pill + icon variants) |
| `web/app/(authenticated)/deliverables/[id]/page.tsx` | Uses shared badge, removed inline mode switch |
| `web/app/(authenticated)/deliverables/page.tsx` | Full rewrite — flat mode-anchored list |
| `web/components/surfaces/DeliverableCreateSurface.tsx` | Intent sections, implicit mode, schedule gating |
| `web/components/deliverables/TypeSelector.tsx` | Deleted — unused |

---

## Type → implicit mode mapping

| Type | Mode | Schedule? |
|------|------|-----------|
| digest | recurring | Yes |
| status | recurring | Yes |
| watch | proactive | No |
| brief | recurring | Yes |
| deep_research | goal | Yes |
| custom | recurring | Yes |
| coordinator | coordinator | No |
