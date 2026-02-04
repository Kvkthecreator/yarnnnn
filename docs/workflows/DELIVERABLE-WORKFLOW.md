# Deliverable Workflow Design

> **Status**: In Progress
> **Last Updated**: 2026-02-04
> **Related**: ADR-018, ADR-019, ADR-023, ADR-005 (Memory), ADR-015 (Unified Context)

## Quick Reference

### What's Implemented
- [x] TP Bar state indicators (below input, Claude Code style) - `web/components/tp/TPBar.tsx`
- [x] State indicator utilities - `web/lib/tp-chips.ts`
- [x] Handoff message pattern for TP navigation - `web/contexts/DeskContext.tsx`
- [x] Data model for context scopes (user vs deliverable) - `memories.project_id`
- [x] Basic surfaces: IdleSurface, DeliverableListSurface, DeliverableDetailSurface, DeliverableReviewSurface

### What's Pending
- [ ] Setup Confirmation surface (post-creation review)
- [ ] Context panel in Review surface
- [ ] TP system prompt updates for context clarification pattern
- [ ] Export nudge post-approval flow
- [ ] Dynamic context/deliverable names in TP bar indicators

---

## Overview

This document defines the user-facing workflow for deliverables from creation through ongoing supervision. The mental model is a **factory supervisor** who:
1. Sets up recurring work (deliverable definition)
2. Reviews output quality (version review)
3. Maintains oversight of all active work (dashboard)

---

## Core Concept: Assurance & Authority

### The Problem We're Solving

Users need confidence that YARNNN:
1. **Understands their intent** - "Yes, this is what I meant"
2. **Uses the right context** - "Yes, draw from these sources"
3. **Can be corrected** - "No, I meant something different"

This is similar to how Claude Code infers the "topic" of a session - but users need visibility and control because:
- Deliverables are recurring (mistakes compound)
- Context directly affects output quality
- Users are "supervisors" who need oversight

### Two Layers of Assurance

| Layer | When | How | Status |
|-------|------|-----|--------|
| **Visual Cues (TP Bar)** | Always visible | Ambient indicators below input | ✅ Implemented |
| **Conversational Assurance** | During key decisions | TP explicitly states what it's doing | ⚠️ Needs prompt update |

Both are complementary:
- Visual cues = "Here's what I'm looking at right now"
- Conversational = "Here's what I understood and will do"

### The Assurance Pattern

**At every decision point, show what we understood and allow correction:**

| Stage | What User Sees | How They Correct |
|-------|---------------|------------------|
| **Intent** | "I'll create a board update" | "No, status report" |
| **Context** | "Using your TechStart Board context" | "No, different board" |
| **Schedule** | "Every Monday at 9am" | "Make it Fridays" |
| **Output** | Draft content | Edit before approve |

---

## TP Bar: Visual State Indicators

### Implementation Details

**Location**: `web/components/tp/TPBar.tsx`
**Utilities**: `web/lib/tp-chips.ts`

### Current Layout (Claude Code Style)

```
┌───────────────────────────────────────────────────┐
│ Ask anything...                            [→]    │
└───────────────────────────────────────────────────┘
 📍 Dashboard · 🧠 Your context · 📅 Deliverable
```

The indicators are positioned **below** the input field, matching Claude Code's status line pattern.

### Three Indicators

1. **📍 Surface** - What TP is currently "seeing"
   - `Dashboard` - Idle/overview
   - `Deliverable` - Specific deliverable detail
   - `Review` - Reviewing a staged version
   - Updates automatically when user navigates

2. **🧠 Context** - What context basket TP is working under
   - `Your context` - General user context only (default)
   - `Deliverable context` - When on a specific deliverable
   - `Project context` - When on a specific project

3. **📅 Deliverable** - Whether TP is focused on a specific deliverable
   - Hidden when not on a deliverable surface
   - Shows "Deliverable" badge when viewing/editing one

### How It Works

```typescript
// web/lib/tp-chips.ts
export function getTPStateIndicators(surface: DeskSurface): TPStateIndicators {
  // Derives all three indicators from the current surface
  // - Surface label: getSurfaceLabel(surface)
  // - Context scope: getContextScope(surface)
  // - Deliverable focus: based on surface.type
}
```

The indicators update automatically when the user navigates between surfaces via `useDesk().surface`.

### Pending Enhancements

- [ ] Show actual deliverable/project names instead of generic labels
- [ ] Make indicators clickable (context → open context browser)
- [ ] Add tentative state indicator (e.g., "Q4 Planning?" when inferred)

---

## Context Architecture

### Mental Model: Context Baskets

```
┌─────────────────────────────────────────────────────┐
│ YOUR CONTEXT (always available)                     │
│ "Things YARNNN knows about you"                     │
│ • Preferences: "I prefer bullet points"             │
│ • Identity: "I'm a PM at a fintech startup"         │
│ • Habits: "Weekly reports to Sarah on Mondays"      │
└─────────────────────────────────────────────────────┘
         │
         │ Always included in every deliverable
         ▼
┌─────────────────────────────────────────────────────┐
│ DELIVERABLE-SPECIFIC CONTEXT                        │
│ "Things specific to THIS recurring work"            │
│ • Recipient details: "Board is conservative"        │
│ • Previous outputs: Learning from v1, v2 edits      │
│ • Attached documents: "Q3 financials.pdf"           │
│ • Topic inference: "This is about board reporting"  │
└─────────────────────────────────────────────────────┘
```

### Data Model (Implemented)

| Layer | Schema | User Sees As |
|-------|--------|--------------|
| User context | `memories` where `project_id IS NULL` | "Your context" |
| Deliverable context | `memories` where `project_id = X` | "This deliverable's context" |
| Topic/basket | `projects` table | Hidden - just powers isolation |

**Key Implementation Details:**
- `memories` table has nullable `project_id`
- `load_context_for_work()` in backend combines both scopes
- Each deliverable creates/links to a project for context isolation
- UI terminology: "Your context" + "Deliverable context" (never expose "project")

---

## Workflow Phases

### Phase 1: Creation & Setup

**Entry Points:**
- TP conversation: "I need a weekly status report"
- Dashboard "+" button → triggers TP message
- Empty state CTA → triggers TP message

**Three Sub-stages:**

#### 1A. Intent Capture (Conversational)

TP gathers info through natural conversation:
- What type of output? (status report, research brief, etc.)
- Who receives it? (manager, client, team)
- How often? (weekly on Mondays, monthly, etc.)

#### 1B. Context Clarification (If Needed)

**This is the key assurance step.** TP must:

1. **Infer the context basket** - What topic/project is this about?
2. **State the inference explicitly** - "I'll use your [X] context for this"
3. **Allow correction** - If user says "no, different context", adjust

**Clarification triggers:**
- Ambiguous request ("create a report")
- Multiple possible contexts ("you have 3 client projects - which one?")
- New topic that doesn't match existing context

**Example flow:**
```
User: "I need a weekly report for the board"

TP infers: User has "TechStart Board" context from previous work

TP responds: "I'll set up a weekly board report using your TechStart
             Board context - that includes your investor updates and
             quarterly metrics. Sound right?"

[Yes] → Proceed to creation
[No, different context] → "Tell me about this board context"
```

**Status:** ⚠️ TP system prompt needs update to implement this pattern

#### 1C. Setup Confirmation (Surface)

After TP creates deliverable, show **Setup Confirmation** surface:

```
┌─────────────────────────────────────────────────────┐
│ ✓ Weekly Board Update                               │
│   Ready to generate your first draft                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📋 WHAT I'LL CREATE                             │ │
│ │ Type: Board Update                              │ │
│ │ For: TechStart Board                            │ │
│ │ Tone: Professional, data-driven                 │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🧠 CONTEXT I'LL USE                     [Edit]  │ │
│ │                                                 │ │
│ │ Your context (always included):                 │ │
│ │ • 143 memories about you and your work          │ │
│ │                                                 │ │
│ │ Board-specific context:                         │ │
│ │ • "Board prefers executive summaries"           │ │
│ │ • "5 members, quarterly meetings"               │ │
│ │ • Q3_financials.pdf                             │ │
│ │                                                 │ │
│ │ [+ Add document] [+ Add context]                │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📅 SCHEDULE                                     │ │
│ │ Every Monday at 9:00 AM                         │ │
│ │ First draft: Feb 10, 2026                       │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ [Run First Draft Now]        [Just Add to Schedule] │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Status:** ❌ Not implemented - needs new surface or extension of DeliverableDetailSurface

---

### Phase 2: Generation (Background)

**Trigger:** Scheduler runs or user clicks "Run Now"

**3-Step Pipeline:**
1. **Gather**: Research agent pulls from configured sources
2. **Synthesize**: Content agent generates draft using type-specific prompt
3. **Stage**: Validate output, create version, notify user

**Status:** ✅ Backend implemented, ⚠️ UI notification needs work

---

### Phase 3: Output Review

When a version is staged, user reviews the generated content.

#### 3A. Attention Queue
Dashboard shows "Needs Attention" section with staged items.

**Status:** ✅ Implemented in IdleSurface

#### 3B. Review Surface

**Current Implementation:** `web/components/surfaces/DeliverableReviewSurface.tsx`
- Shows draft content in editor
- Approve / Reject & Refine / Discard buttons
- Optional feedback notes

**Proposed Enhancement - Add Context Panel:**

```
┌─────────────────────────────────────────────────────┐
│ Review: Weekly Status Report (v3)                   │
├───────────────────────┬─────────────────────────────┤
│                       │                             │
│ GENERATED OUTPUT      │ CONTEXT PANEL (collapsible) │
│                       │                             │
│ [Draft content here]  │ Sources Used:               │
│                       │ • 12 memories               │
│                       │ • 2 documents               │
│                       │ • Previous feedback         │
│                       │                             │
│                       │ Quality Trend:              │
│                       │ v1: 0.45 → v2: 0.28 ↓      │
│                       │ (less editing needed)       │
│                       │                             │
├───────────────────────┴─────────────────────────────┤
│ [Approve] [Edit & Approve] [Reject] [Skip for Now]  │
└─────────────────────────────────────────────────────┘
```

**Status:** ⚠️ Context panel not implemented

---

### Phase 4: Post-Approval Actions

After approving, show export options:

```
┌─────────────────────────────────────────────────────┐
│ ✓ Approved                                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Your Weekly Status Report is ready.                 │
│                                                     │
│ [Copy to Clipboard]  [Download PDF]  [Send Email]   │
│                                                     │
│ Next version: Monday, Feb 10 at 9:00 AM             │
│ [View in Deliverables]  [Dismiss]                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Status:** ❌ Not implemented

---

### Phase 5: Ongoing Supervision

User returns to dashboard and sees their deliverables.

**Dashboard View (IdleSurface):**
- Active deliverables with next run time
- Attention items (staged versions)
- Quick links to Context and Documents

**Status:** ✅ Implemented

---

## Surface Inventory

| Surface | Purpose | File | Status |
|---------|---------|------|--------|
| IdleSurface | Dashboard, attention queue | `web/components/surfaces/IdleSurface.tsx` | ✅ |
| DeliverableListSurface | List all deliverables | `web/components/surfaces/DeliverableListSurface.tsx` | ✅ |
| DeliverableDetailSurface | Single deliverable + versions | `web/components/surfaces/DeliverableDetailSurface.tsx` | ✅ |
| DeliverableReviewSurface | Review staged version | `web/components/surfaces/DeliverableReviewSurface.tsx` | ✅ |
| **DeliverableSetupSurface** | Post-creation setup review | - | ❌ Needed |

---

## Key Files

### TP Bar & State Indicators
- `web/components/tp/TPBar.tsx` - Main TP input bar with state indicators
- `web/lib/tp-chips.ts` - Utilities for deriving state from surface

### Context Management
- `web/contexts/DeskContext.tsx` - Desk state, surface navigation, handoff messages
- `web/contexts/TPContext.tsx` - TP conversation state, message streaming
- `web/types/desk.ts` - Type definitions for surfaces, actions, state

### Surfaces
- `web/components/desk/SurfaceRouter.tsx` - Routes to appropriate surface component
- `web/components/desk/HandoffBanner.tsx` - Shows TP message after navigation
- `web/components/surfaces/*.tsx` - Individual surface implementations

---

## Summary of Decisions

| Decision | Resolution |
|----------|------------|
| Setup Flow | Conversational → Clarify (if needed) → Setup Confirmation Surface |
| Context terminology | "Your context" + "Deliverable context" (hide "project") |
| Context visibility | Always show what context will be used before first run |
| Clarification | TP states inference explicitly, asks when ambiguous |
| Review info | Output + collapsible context panel (what was used) |
| Post-approval | Export nudge with "next run" info |
| TP Bar indicators | 3 visual cues below input: Surface, Context, Deliverable |
| Two-layer assurance | Visual cues (ambient) + Conversational (explicit) |
| TP Bar position | Below input field (Claude Code style) |

---

## Next Steps (Priority Order)

1. **TP System Prompt Updates**
   - Add context clarification pattern
   - Explicit statement of inferred context
   - File: `api/agents/thinking_partner.py`

2. **Setup Confirmation Surface**
   - New surface or extend DeliverableDetailSurface
   - Show "Context I'll Use" section
   - Add document/context attachment

3. **Review Surface Context Panel**
   - Add collapsible panel showing sources used
   - Quality trend indicator

4. **Dynamic TP Bar Labels**
   - Fetch actual deliverable/project names
   - Show in indicators instead of generic labels

5. **Export Nudge Flow**
   - Post-approval options modal/inline
   - Copy, PDF, Email actions

---

## Open Questions

1. **How explicit should context inference be?** Always state it, or only when ambiguous?
2. **Should existing context baskets be shown as options** when creating new deliverable?
3. **Is Setup Confirmation a new surface type** or part of DeliverableDetailSurface?
4. **Review context panel:** Two-panel always or collapsible?
5. **Post-approval flow:** Modal, toast, or inline surface change?
