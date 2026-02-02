# ADR-021: Review-First Supervision UX

**Status:** Accepted
**Date:** 2026-02-02
**Builds On:** ADR-018 (Recurring Deliverables), ADR-020 (Deliverable-Centric Chat)
**Supersedes:** docs/development/UX_TRANSITION_PLAN.md (delete)

## Context

We established two axiomatic principles:

1. **Deliverables are first-class data entities** - the objects users supervise
2. **TP is the first-class interaction surface** - the method of supervision

The current implementation separates these across multiple screens:
- Dashboard: Shows deliverables (objects) but no TP
- Detail: Shows content but TP is just a button
- Review: Finally has both, but user had to navigate there

This navigation-centric model is a legacy web paradigm. A supervisor doesn't "navigate to where they can supervise" - they respond to what's in front of them.

## Decision

### The Review-First Principle

**When a user logs in with something needing attention, they land directly on the review screen - not a list.**

The primary view unites both first-class entities:
- The **deliverable content** (object of supervision) is visible and editable
- **TP interaction** (method of supervision) is embedded, not hidden behind navigation

### Screen Architecture

#### Primary: Review View (When Something Needs Attention)

```
┌─────────────────────────────────────────────────────────────────┐
│ Weekly Status Report                         [All Deliverables] │
│ Ready for your review • Due tomorrow                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                                                             │ │
│ │  Hi Sarah,                                                  │ │
│ │                                                             │ │
│ │  Here's this week's update for Project Alpha...             │ │
│ │  [Directly editable - no "click to edit"]                   │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ [Shorter] [More detail] [More formal] [____________] [Send]     │
│                                                                 │
│ ✨ YARNNN is learning: You prefer bullet points, concise style  │
│                                                                 │
│                               [Skip for now]    [Approve]       │
└─────────────────────────────────────────────────────────────────┘
```

Key elements:
- **Content is immediately editable** - not read-only requiring another click
- **TP refinement chips are visible** - not hidden behind "Refine with AI" button
- **Custom TP input is visible** - user can type instructions without opening anything
- **Feedback summary is visible** - shows what YARNNN has learned
- **[All Deliverables]** provides escape to list view
- **[Skip for now]** moves to next item or dashboard

#### Secondary: Dashboard View (When Nothing Needs Attention)

```
┌─────────────────────────────────────────────────────────────────┐
│ All caught up                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✓ Weekly Status Report         Next: Monday                    │
│  ✓ Client Update                Next: Feb 15                    │
│  ✓ Monthly Investor Brief       Next: Mar 1                     │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│  Need something?                                                │
│  [Set up new deliverable]                                       │
│                                                                 │
│  Or ask me anything:                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ _                                                           ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Key elements:
- **Status at a glance** - what's done, when's next
- **TP input is visible** - user can always talk to TP
- **Create action is visible** - not hidden in a menu
- **No card grid** - compact list is sufficient when nothing needs action

#### Tertiary: Browse View (When User Explicitly Wants to Browse)

Accessible via [All Deliverables] or clicking a specific deliverable from the dashboard list.

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back                    Weekly Status Report                  │
├─────────────────────────────────────────────────────────────────┤
│ Weekly on Mondays • For Sarah                    [Run Now]      │
│                                                                 │
│ ✨ YARNNN is learning your preferences                          │
│    87% quality across 4 versions                                │
│                                                                 │
│ Latest: Week of Jan 27                                          │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Content preview...                                          │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Previous outputs (3)                                            │
│ ▶ Week of Jan 20 - 92% match                                    │
│ ▶ Week of Jan 13 - 85% match                                    │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│ Ask about this deliverable:                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ _                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

Key elements:
- **TP input at bottom** - can ask questions about this deliverable
- **History accessible** - expandable previous versions
- **[Run Now]** for manual trigger - but not prominent

### TP Presence Rule

**TP must be visible and interactive on every screen.**

| Screen | TP Manifestation |
|--------|------------------|
| Review (primary) | Refinement chips + custom input inline |
| Dashboard (idle) | Text input for conversation |
| Browse (detail) | Text input scoped to deliverable |
| Onboarding | Conversational flow (TP guides setup) |

There is no screen where the user cannot interact with TP without navigation.

### Navigation Model

```
Login
  │
  ├─→ [Has staged version?] ─→ Review View (with that version)
  │                              │
  │                              ├─→ [Approve] ─→ Next staged OR Dashboard
  │                              ├─→ [Skip] ─→ Next staged OR Dashboard
  │                              └─→ [All Deliverables] ─→ Dashboard
  │
  └─→ [Nothing staged?] ─→ Dashboard View
                              │
                              ├─→ [Click deliverable] ─→ Browse View
                              ├─→ [Set up new] ─→ Onboarding
                              └─→ [Type in TP input] ─→ Conversation
```

### Onboarding Alignment

Onboarding is TP-guided conversation that ends with the first review:

```
TP: What recurring work do you owe someone?
User: I send a weekly status report to my manager Sarah

TP: Got it. What day should I have it ready for review?
[Monday] [Tuesday] [Wednesday] [Custom]

User: [Monday]

TP: Perfect. I'll draft your Weekly Status Report every Monday.
    Let me create your first draft now...

    [Generating...]

    Here's your first draft. Make any changes and I'll learn
    from your edits.

    [Shows Review View with first draft]
```

The onboarding **ends in the review view**, not a dashboard. User's first action is supervision.

## Consequences

### Positive

- **Unified first-class entities**: Every screen shows both deliverable (object) AND TP (method)
- **Supervision-native**: User lands on what needs attention, not a list
- **Reduced navigation**: One less click to supervise
- **TP always available**: No need to find/open chat
- **Consistent mental model**: "Open YARNNN → do supervision → done"

### Negative

- **Significant refactor**: Current 3-screen model (Dashboard → Detail → Review) collapses
- **Mobile complexity**: Review-first on small screens needs careful design
- **Edge cases**: Multiple staged versions need queue/navigation UX

### Migration

1. Keep existing components but reorganize routing
2. `/dashboard` checks for staged versions, redirects to review if found
3. Review view becomes the primary component, not a modal
4. Dashboard becomes the "nothing to do" state
5. Detail/Browse view is secondary, accessible via explicit navigation

## Implementation Priority

1. **Update routing logic** - Check staged versions on login, redirect appropriately
2. **Embed TP in all views** - Add input field to Dashboard and Browse views
3. **Make Review the primary** - Full-page review, not modal over detail
4. **Onboarding ends in review** - After setup, show first draft in review view
5. **Remove floating chat** - TP is embedded everywhere, floating is redundant

## References

- [ESSENCE.md](../ESSENCE.md) - Core principles
- [Design Principle: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md)
- [ADR-018: Recurring Deliverables](ADR-018-recurring-deliverables.md)
- [ADR-020: Deliverable-Centric Chat](ADR-020-deliverable-centric-chat.md)
