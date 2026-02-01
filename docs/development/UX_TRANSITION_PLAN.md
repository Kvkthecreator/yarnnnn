# UX Transition Plan: Deliverables-First Experience

**ADR-018: Recurring Deliverables Product Pivot**
**Date:** February 1, 2026

---

## Current State Analysis

### Primary Interface
- **Chat-centric**: Dashboard is a full-height Chat component
- **Projects as context lenses**: ProjectSelector in top bar switches context
- **Surfaces for secondary access**: Context, Schedule, Outputs in side panel
- **Thinking Partner (TP)** is the primary interaction mode

### Navigation Model
```
TopBar: [Logo] [ProjectSelector] [WorkStatus] ... [Context] [Schedule] [Outputs] [User]
                    ↓
              Dashboard (Chat)
                    ↓
            Surfaces (side panel)
```

### Existing User Flows
1. **New user** → Cold start → WelcomePrompt → Upload/Paste/Chat
2. **Returning user** → Dashboard → Chat with TP → Work via conversation
3. **Work output** → TP triggers agent → WorkStatus shows progress → View in Outputs surface

### What Works
- Minimal chrome philosophy (ADR-014)
- Context-aware project switching
- Real-time work status
- Unified surface panel

### What Becomes Legacy
- Projects as primary organizing concept (becomes secondary)
- Chat as the only entry point (deliverables become first)
- Schedule surface showing generic "work" (becomes deliverables-focused)
- General-purpose onboarding (becomes deliverable-first)

---

## Target State: Deliverables-First UX

### New Mental Model
```
Before: User → Project → Chat with TP → TP creates work → Outputs
After:  User → Deliverable → [Automated pipeline] → Staged draft → Review/Approve
```

### New Primary Interface
The **Deliverables Dashboard** replaces the Chat as the primary landing experience.

```
┌─────────────────────────────────────────────────────────────────┐
│ TopBar: [Logo] [Deliverables ▾] [+New] ... [User]               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Client X Weekly │  │ Investor Update │  │ Comp Brief      │  │
│  │ ────────────────│  │ ────────────────│  │ ────────────────│  │
│  │ ⏰ Due Monday   │  │ 📝 Ready Review │  │ ⏸ Paused        │  │
│  │ v12 • 94% match │  │ v3 staged       │  │ v8 • 87% match  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
│  Quality Trend: ████████░░ 82% → Target 90%                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Navigation Restructure

**Option A: Replace Dashboard Route**
```
/dashboard → Deliverables Dashboard (new primary)
/dashboard/chat → Chat interface (accessible but secondary)
/dashboard/deliverable/:id → Deliverable detail/review
```

**Option B: New Route + Redirect**
```
/deliverables → Deliverables Dashboard (new primary)
/deliverables/new → Onboarding wizard
/deliverables/:id → Deliverable detail
/deliverables/:id/review/:versionId → Version review
/chat → Chat interface (legacy, still accessible)
```

**Recommendation: Option A** - Replace in place, preserving `/dashboard` as the entry point. Users expect `/dashboard` to be where they land. The Chat becomes a tool within the deliverable context.

---

## Component Architecture Changes

### New Components Needed

```
components/
├── deliverables/
│   ├── DeliverablesDashboard.tsx    # Primary view - card grid
│   ├── DeliverableCard.tsx          # Individual deliverable card
│   ├── DeliverableDetail.tsx        # Full deliverable view with versions
│   ├── VersionReview.tsx            # Draft review/edit interface
│   ├── VersionHistory.tsx           # Version timeline
│   ├── QualityTrend.tsx             # Edit distance visualization
│   ├── OnboardingWizard.tsx         # 6-step onboarding flow
│   │   ├── StepDeliverable.tsx      # "What do you deliver?"
│   │   ├── StepRecipient.tsx        # "Who receives it?"
│   │   ├── StepExamples.tsx         # "Show me examples"
│   │   ├── StepSources.tsx          # "What sources inform this?"
│   │   ├── StepSchedule.tsx         # "When is it due?"
│   │   └── StepFirstDraft.tsx       # Generate + review first draft
│   └── SchedulePicker.tsx           # Frequency/time selector
```

### Modified Components

```
components/
├── shell/
│   ├── TopBar.tsx                   # Update navigation buttons
│   │   - Replace: Context | Schedule | Outputs
│   │   - With:    Deliverables | Chat | Settings (or similar)
│   ├── ProjectSelector.tsx          # Repurpose or hide
│   │   - Projects become "contexts" for deliverables
│   │   - Or: Replace with DeliverableSelector
│   └── WorkStatus.tsx               # Update for pipeline status
│       - Show: "Generating v5..." instead of "Research running..."
│
├── surfaces/
│   ├── WorkspacePanel.tsx           # Update tabs
│   │   - Replace tabs with: Versions | Sources | Settings
│   │   - Or: Keep for deliverable detail view
│   └── SurfaceRouter.tsx            # Add deliverable surfaces
```

### Deprecated/Legacy Components

```
components/
├── Chat.tsx                         # Still used but secondary
├── WelcomePrompt.tsx                # Replace with deliverable onboarding
├── surfaces/
│   ├── ScheduleSurface.tsx          # Replace with deliverable-aware version
│   └── ContextSurface.tsx           # Keep but make accessible from deliverable
```

---

## User Flow Transitions

### New User Onboarding

**Current Flow:**
```
Login → Dashboard → WelcomePrompt → [Upload | Paste | Chat]
```

**New Flow:**
```
Login → Deliverables Dashboard (empty state)
         ↓
      "Create your first deliverable"
         ↓
      Onboarding Wizard (6 steps)
         ↓
      First draft generated
         ↓
      Review/approve interface
         ↓
      Deliverables Dashboard (1 card)
```

### Returning User Flow

**Current Flow:**
```
Login → Dashboard → Chat → (work happens via conversation)
```

**New Flow:**
```
Login → Deliverables Dashboard
         ↓
      [View staged draft requiring review]
         ↓
      Review → Edit → Approve
         ↓
      Copy/export for sending
         ↓
      Dashboard (next deliverable)
```

### Power User / Chat Access

Chat is not removed, but repositioned:
```
Deliverables Dashboard
         ↓
      Deliverable Card → "Refine" action
         ↓
      Chat interface scoped to deliverable
         ↓
      "For next week, emphasize budget more"
         ↓
      Feedback saved to deliverable context
```

---

## Top Bar Redesign

### Current
```
[yarnnn] [ProjectSelector] [WorkStatus] ... [Context] [Schedule] [Outputs] [UserMenu]
```

### Proposed
```
[yarnnn] [+ New Deliverable] [WorkStatus] ... [Deliverables] [Chat] [UserMenu]
```

Or with deliverable context:
```
[yarnnn] [DeliverableSelector] [WorkStatus] ... [Versions] [Sources] [Chat] [UserMenu]
```

**Key Changes:**
- **ProjectSelector → DeliverableSelector** (or hidden)
- **Surface buttons** reorient toward deliverable workflow
- **"+ New"** prominent CTA for creating deliverables
- **Chat** accessible but not primary

---

## Surface Panel Redesign

### Current Tabs
```
[ Context ] [ Work ] [ Outputs ]
```

### Proposed: Context-Dependent Tabs

**When on Deliverables Dashboard:**
```
[ Staged for Review ] [ Recent Deliveries ] [ All Versions ]
```

**When viewing a specific Deliverable:**
```
[ Versions ] [ Sources ] [ Settings ]
```

**When in Chat (legacy/power user):**
```
[ Context ] [ Work ] [ Outputs ]  ← Keep existing for chat mode
```

---

## Empty States & Onboarding Prompts

### Deliverables Dashboard Empty State
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    📋 No deliverables yet                       │
│                                                                 │
│     Set up your first recurring deliverable and YARNNN         │
│     will produce it on schedule, improving every cycle.         │
│                                                                 │
│              [ Create Your First Deliverable ]                  │
│                                                                 │
│     Examples:                                                   │
│     • Weekly client status report                               │
│     • Monthly investor update                                   │
│     • Bi-weekly competitive brief                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Staged Deliverable Prompt
```
┌─────────────────────────────────────────────────────────────────┐
│  🔔 1 deliverable ready for review                              │
│                                                                 │
│  Client X Weekly Status — v12 staged                            │
│  [ Review Now ]                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration Strategy

### Phase 1: Additive (Non-Breaking)
1. Add `/deliverables` route alongside existing `/dashboard`
2. Add DeliverablesDashboard component
3. Add OnboardingWizard
4. Keep all existing flows working
5. Add "Deliverables" to TopBar as optional navigation

### Phase 2: Soft Redirect
1. New users land on `/deliverables` by default
2. Existing users still land on `/dashboard`
3. Add migration prompt: "Try the new Deliverables experience"
4. Track adoption metrics

### Phase 3: Full Transition
1. `/dashboard` becomes `/deliverables` (redirect legacy URL)
2. Chat accessible via `/chat` or within deliverable context
3. Remove migration prompts
4. Update all documentation and marketing

**Recommendation for MVP:** Go directly to Phase 3 approach since this is a pivot, not an incremental feature. The old experience doesn't have significant user lock-in.

---

## Data Migration Considerations

### Existing Work → Deliverables
- Recurring work tickets could be migrated to deliverables
- Or: Keep them in legacy "Work" view, accessible but not primary

### Existing Projects → Deliverable Contexts
- Projects become the "project_id" on deliverables
- Or: Auto-create deliverable from active project's recurring work

### Existing Memories → Deliverable Sources
- User memories remain user-scoped (available to all deliverables)
- Project memories become deliverable-specific context

---

## Success Metrics

### Engagement Shift
- **Before:** Time in chat, messages sent
- **After:** Deliverables created, versions approved, edit distance trend

### Quality Metrics
- Edit distance decreasing over versions (learning is working)
- Time to approval decreasing
- Rejection rate decreasing

### Retention Metrics
- Weekly active deliverable reviews
- Deliverables with 4+ approved versions
- Users with multiple active deliverables

---

## Risk Mitigation

### Risk: Users confused by change
**Mitigation:** Clear empty state messaging, "How it works" inline help, video tutorial link

### Risk: Power users miss chat-first experience
**Mitigation:** Chat always accessible, keyboard shortcut (Cmd+K → Chat), deliverable-scoped chat for refinement

### Risk: Existing work/outputs orphaned
**Mitigation:** Keep "Legacy Work" accessible in settings or secondary nav, but don't promote

### Risk: First draft quality disappoints
**Mitigation:** Front-load example upload in onboarding (strongly encourage), collaborative refinement chat for cold start

---

## Implementation Checklist

### Frontend (Phase 2)
- [ ] Create DeliverablesDashboard component
- [ ] Create DeliverableCard component
- [ ] Create OnboardingWizard (6 steps)
- [ ] Create VersionReview component
- [ ] Update TopBar navigation
- [ ] Update SurfaceRouter for deliverable views
- [ ] Add empty state designs
- [ ] Update routing in app/(authenticated)/

### Backend (Already Done in Phase 1)
- [x] Deliverables API endpoints
- [x] Version management endpoints
- [x] Pipeline execution service
- [x] Feedback engine

### Integration
- [ ] Connect OnboardingWizard to API
- [ ] Connect DeliverablesDashboard to API
- [ ] Connect VersionReview to update endpoints
- [ ] Wire up "Run now" to pipeline trigger
- [ ] Email notifications for staged deliverables

---

## Appendix: Component Wireframes

### DeliverableCard
```
┌────────────────────────────────────────┐
│ Client X Weekly Status          [⋮]   │
│ ──────────────────────────────────────│
│ 📅 Weekly on Mondays                   │
│ 👤 Sarah (VP Marketing)                │
│                                        │
│ ┌──────────────────────────────────┐  │
│ │ v12 • Staged for review          │  │
│ │ Edit distance: 6% (improving!)   │  │
│ └──────────────────────────────────┘  │
│                                        │
│ [ Review Draft ]        [ ⏸ Pause ]   │
└────────────────────────────────────────┘
```

### OnboardingWizard Step Indicator
```
┌────────────────────────────────────────┐
│  ● ─ ○ ─ ○ ─ ○ ─ ○ ─ ○                │
│  1   2   3   4   5   6                │
│                                        │
│  Step 1: What do you deliver?          │
│  ─────────────────────────────────────│
│                                        │
│  Describe the recurring work you       │
│  owe to someone:                       │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ Weekly status report for...      │ │
│  └──────────────────────────────────┘ │
│                                        │
│                    [ Continue → ]      │
└────────────────────────────────────────┘
```

### VersionReview
```
┌────────────────────────────────────────────────────────────┐
│ Client X Weekly Status — Version 12                   [×]  │
│ ──────────────────────────────────────────────────────────│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ # Weekly Status Update                                 ││
│ │                                                        ││
│ │ Hi Sarah,                                              ││
│ │                                                        ││
│ │ Here's the weekly update for Project Alpha:            ││
│ │                                                        ││
│ │ ## Key Metrics                                         ││
│ │ - Sprint velocity: 42 points (↑ from 38)               ││
│ │ - Bug count: 12 open (↓ from 15)                       ││
│ │ ...                                                    ││
│ │                                                        ││
│ │ [Edit inline - changes tracked]                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ Add feedback for next time (optional):               │  │
│ │ ┌──────────────────────────────────────────────────┐ │  │
│ │ │ Include Q1 comparison numbers                    │ │  │
│ │ └──────────────────────────────────────────────────┘ │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
│ [ ✕ Reject ]    [ 💬 Refine with Chat ]    [ ✓ Approve ]  │
└────────────────────────────────────────────────────────────┘
```

---

*This document should be reviewed with the team before implementation begins. Key decisions to confirm: navigation model, routing approach, migration strategy.*
