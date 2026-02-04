# Deliverable Workflow Design

> **Status**: Draft - Active Discussion
> **Last Updated**: 2026-02-04
> **Related**: ADR-018, ADR-019, ADR-023, ADR-005 (Memory), ADR-015 (Unified Context)

## Overview

This document defines the user-facing workflow for deliverables from creation through ongoing supervision. The mental model is a **factory supervisor** who:
1. Sets up recurring work (deliverable definition)
2. Reviews output quality (version review)
3. Maintains oversight of all active work (dashboard)

---

## Context Architecture (Foundation)

Before diving into workflow, it's important to understand how context flows AND how users gain assurance about what context is being used.

### The Core Problem: User Assurance & Authority

When a user says "create a weekly status report", they need to know:
1. **What context will this draw from?** (assurance)
2. **Is YARNNN understanding my intent correctly?** (clarification)
3. **Can I adjust if it's wrong?** (authority)

This is similar to how Claude Code infers the "topic" of a session - but users need visibility and control.

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

### The Assurance & Clarification Pattern

**Scenario 1: Clear intent**
```
User: "I need a weekly status report for Sarah"
TP: [creates deliverable]
    → Shows: "I'll set up a weekly status report for Sarah using your
              work context. First draft Monday 9am."
    → User sees confirmation, can adjust
```

**Scenario 2: Ambiguous intent - needs clarification**
```
User: "Create a report"
TP: [clarify] "What kind of report?"
    → Options: Status update, Research brief, Board update, Something else
User: "Board update"
TP: [clarify] "Is this for the TechStart board or a different context?"
    → Shows existing relevant context if any
    → User confirms or provides new context
```

**Scenario 3: Wrong context inferred**
```
User: "Weekly update for the marketing team"
TP: [creates deliverable, infers wrong project]
    → Shows: "I'll use your Product Launch context for this"
User: "No, this is for a different project - the rebrand"
TP: [adjusts] "Got it, I'll create a new context basket for the rebrand
              marketing updates. What should I know about it?"
```

### Key Principle: Show What We're Using

At every stage, the user should be able to see:
- **What context basket** this deliverable draws from
- **What's in that basket** (memories, docs, feedback)
- **How to adjust it** if wrong

This is NOT about exposing "projects" as an organizational concept - it's about giving users **visibility into YARNNN's understanding**.

### Data Model (Already Implemented)

| Layer | Schema | User Sees As |
|-------|--------|--------------|
| User context | `memories` where `project_id IS NULL` | "Your context" |
| Deliverable context | `memories` where `project_id = X` | "This deliverable's context" |
| Topic/basket | `projects` table | Hidden - just powers isolation |

**Current Implementation:** ✅ Data model fully supports this
- `memories` table has nullable `project_id`
- `load_context_for_work()` combines both scopes
- Each deliverable creates/links to a project for context isolation

**Gap:** ⚠️ UI doesn't surface this clearly to users yet

---

## Workflow Phases

### Phase 1: Creation & Setup

**Entry Points:**
- TP conversation: "I need a weekly status report"
- Dashboard "+" button → triggers TP
- Empty state CTA → triggers TP

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

**Behind the scenes:**
- TP calls `create_deliverable` tool
- Backend creates deliverable + associated project (for context isolation)
- Returns deliverable ID for navigation

**Open Questions:**
- [x] Should TP show a "type picker" UI or stay fully conversational? → Conversational with clarify()
- [ ] How explicit should context inference be? Always state it, or only when ambiguous?
- [ ] Should existing "context baskets" be shown as options?

#### 1C. Setup Confirmation (Surface)

After TP creates deliverable, show **Setup Confirmation** - this gives the user visual assurance:

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

**Key Assurance Elements:**
- **"Context I'll Use"** - Shows exactly what YARNNN will draw from
- **Two-layer display** - "Your context" (portable) + "Board-specific" (isolated)
- **Edit affordance** - User can adjust before first run
- **Add actions** - Attach docs or add memories right here

**Open Questions:**
- [ ] Is this a new surface type or part of DeliverableDetailSurface?
- [ ] Should "Run First Draft Now" be the primary CTA? (Probably yes - get to value fast)
- [ ] How much context detail to show? (Summary vs. expandable list)

**Resolved:**
- ✅ User sees "this deliverable's context", not "project"
- ✅ Document attachment is prominent and in-flow
- ✅ Two-layer context display (your context + deliverable-specific)

---

### Phase 2: Generation (Background)

**Trigger:** Scheduler runs or user clicks "Run Now"

**3-Step Pipeline:**
1. **Gather**: Research agent pulls from configured sources
2. **Synthesize**: Content agent generates draft using type-specific prompt
3. **Stage**: Validate output, create version, notify user

**User sees:**
- Work ticket created (visible in Recent Work?)
- Notification when complete (how? badge? toast? email?)

**Open Questions:**
- [ ] Should generation progress be visible in UI?
- [ ] How to handle generation failures gracefully?
- [ ] Push notification vs. pull (user checks dashboard)?

---

### Phase 3: Output Review

When a version is staged, user reviews the generated content.

#### 3A. Attention Queue
Dashboard shows "Needs Attention" section with staged items.

#### 3B. Review Surface

**Current Implementation:**
- Shows draft content in editor
- Approve / Reject & Refine / Discard buttons
- Optional feedback notes

**Proposed Enhancement - Two-Panel Review:**

```
┌─────────────────────────────────────────────────────┐
│ Review: Weekly Status Report (v3)                   │
├───────────────────────┬─────────────────────────────┤
│                       │                             │
│ GENERATED OUTPUT      │ CONTEXT PANEL               │
│                       │                             │
│ [Draft content here]  │ ┌─────────────────────────┐ │
│                       │ │ Sources Used            │ │
│                       │ │ • 12 memories           │ │
│                       │ │ • 2 documents           │ │
│                       │ │ • Previous feedback     │ │
│                       │ └─────────────────────────┘ │
│                       │                             │
│                       │ ┌─────────────────────────┐ │
│                       │ │ Quality Trend           │ │
│                       │ │ v1: 0.45 → v2: 0.28 ↓  │ │
│                       │ │ (less editing needed)   │ │
│                       │ └─────────────────────────┘ │
│                       │                             │
│                       │ ┌─────────────────────────┐ │
│                       │ │ Compare to Previous     │ │
│                       │ │ [Show Diff]             │ │
│                       │ └─────────────────────────┘ │
│                       │                             │
├───────────────────────┴─────────────────────────────┤
│ [Approve] [Edit & Approve] [Reject] [Skip for Now]  │
└─────────────────────────────────────────────────────┘
```

**Context Panel Shows:**
- What sources were used for this generation
- Quality trend (edit distance over versions)
- Comparison to previous version
- Feedback history summary

**Open Questions:**
- [ ] Two-panel always or collapsible?
- [ ] What's the minimum context to show?
- [ ] Should "Skip for Now" exist? (defer review)
- [ ] Inline editing vs. open in editor mode?

---

### Phase 4: Post-Approval Actions

After approving, what happens next?

**Current:** Version saved with final_content, feedback captured.

**Proposed - Export Nudge:**

```
┌─────────────────────────────────────────────────────┐
│ ✓ Approved                                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Your Weekly Status Report is ready.                 │
│                                                     │
│ [Copy to Clipboard]  [Download PDF]  [Send Email]   │
│                                                     │
│ ─────────────────────────────────────────────────── │
│                                                     │
│ Next version: Monday, Feb 10 at 9:00 AM             │
│ [View in Deliverables]  [Dismiss]                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Open Questions:**
- [ ] Is this a modal, toast, or inline surface change?
- [ ] PDF generation - build or defer?
- [ ] Email sending - to whom? (recipient vs. self)
- [ ] Should this be skippable via preference?

---

### Phase 5: Ongoing Supervision

User returns to dashboard and sees their deliverables.

**Dashboard View:**
- Active deliverables with next run time
- Attention items (staged versions)
- Quality indicators (trend arrows?)

**Deliverable List Surface:**
- All deliverables with status
- Quick actions: Run Now, Pause, Settings
- Filter by status

**Deliverable Detail Surface:**
- Version history with quality trend
- Settings (schedule, sources, recipient)
- Feedback summary ("YARNNN has learned...")

---

## Surface Inventory

| Surface | Purpose | Status |
|---------|---------|--------|
| IdleSurface (Dashboard) | Overview, attention queue | ✅ Exists |
| DeliverableListSurface | List all deliverables | ✅ Exists |
| DeliverableDetailSurface | Single deliverable + versions | ✅ Exists |
| DeliverableReviewSurface | Review staged version | ✅ Exists |
| **DeliverableSetupSurface** | Post-creation setup review | ❓ New? |

---

## Key Decision Points

### 1. Setup Flow
**Option A:** Fully conversational (current)
- TP gathers everything through chat
- Pros: Natural, low friction
- Cons: User doesn't see full config until later

**Option B:** Conversational + Setup Surface
- TP creates basic deliverable
- Setup surface shows full config for review/adjustment
- Pros: Clear confirmation, easy to adjust
- Cons: Extra step

**Option C:** Hybrid based on completeness
- If TP gathered enough info → show setup surface
- If minimal info → continue conversation
- Pros: Adaptive
- Cons: Inconsistent UX

### 2. Review Information Density
**Option A:** Output only (current)
- Just the draft content
- User focuses on output quality

**Option B:** Output + Context panel
- Shows what went into generation
- Helps user understand and trust output

**Option C:** Output + Collapsible context
- Context available but not prominent
- Best of both worlds?

### 3. Post-Approval Flow
**Option A:** Silent success
- Approve → back to dashboard
- User exports manually later

**Option B:** Export nudge
- Approve → export options shown
- Encourages action on approved content

**Option C:** Configurable per deliverable
- Some deliverables auto-send, others manual
- Future feature

---

## Open Items for Discussion

1. **Attachment/Files**: Where in the flow should users attach documents as context sources?
   - During creation?
   - In setup surface?
   - Anytime via settings?

2. **Type Selection**: Should type selection be:
   - Inferred from conversation?
   - Explicit picker UI?
   - Suggested by TP with confirmation?

3. **Scheduling UX**: When/how to set schedule:
   - During creation conversation?
   - In setup surface?
   - Default schedule with easy override?

4. **Learning Feedback**: How to show "YARNNN is learning from your edits"?
   - Quality trend in review surface?
   - Summary in detail surface?
   - Explicit "what I learned" message?

---

## TP Bar: Visual State Indicators

### The Gap in Current UX

Looking at the TP interface, the user has **no visibility** into what TP "sees" or "knows" during conversation. The screenshot shows:
- User creating a deliverable
- No indicator of what surface TP is looking at
- No indicator of what context TP is working under
- No indicator of whether this connects to existing work

This is different from the conversational assurance pattern (which happens DURING interaction). These are **ambient indicators** that show TP's current state at all times.

### Two Layers of Assurance

| Layer | When | How |
|-------|------|-----|
| **Visual Cues (TP Bar)** | Always visible | Ambient indicators in UI |
| **Conversational Assurance** | During key decisions | TP explicitly states what it's doing |

Both are needed - they're complementary:
- Visual cues = "Here's what I'm looking at right now"
- Conversational = "Here's what I understood and will do"

### Proposed TP Bar State Indicators

```
┌─────────────────────────────────────────────────────────────┐
│  TP                                                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 📍 Dashboard │ 🧠 Your context │ 📋 No deliverable      ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  [Chat history...]                                           │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Ask anything...                                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Three indicators:**

1. **📍 Surface** - What TP is currently "seeing"
   - `Dashboard` - Idle/overview
   - `Weekly Report` - Specific deliverable detail
   - `Review: v3` - Reviewing a staged version
   - Changes when user navigates surfaces

2. **🧠 Context** - What context basket TP is working under
   - `Your context` - General user context only
   - `Board Updates` - Specific deliverable/topic context
   - `New topic` - When TP has inferred a new context
   - Clickable to show what's in the basket?

3. **📋 Deliverable** - Whether TP is focused on a specific deliverable
   - `No deliverable` - General conversation
   - `Weekly Report` - Working on specific deliverable
   - `Creating new` - In creation flow

### State Transitions

**Scenario: User opens dashboard and starts chatting**
```
Initial state:
📍 Dashboard │ 🧠 Your context │ 📋 No deliverable

User: "I need a weekly report for the board"

During creation:
📍 Dashboard │ 🧠 Board context │ 📋 Creating: Weekly Report

After creation complete:
📍 Setup: Weekly Report │ 🧠 Board context │ 📋 Weekly Report
```

**Scenario: User navigates to existing deliverable, then asks TP**
```
User clicks "Weekly Status Report" in list

State updates:
📍 Weekly Status Report │ 🧠 Status context │ 📋 Weekly Status Report

User: "Can you make this more concise?"

TP knows it's about THIS deliverable, not asking generally
```

**Scenario: User on dashboard asks about something new**
```
State:
📍 Dashboard │ 🧠 Your context │ 📋 No deliverable

User: "What about the Q4 planning doc?"

TP: "I see you have a Q4 Planning context with 12 memories.
     Want me to work on something related to that?"

State could update to:
📍 Dashboard │ 🧠 Q4 Planning? │ 📋 No deliverable
                    ↑ tentative, indicated with "?"
```

### Open Design Questions

1. **Where do indicators live?**
   - Top of TP panel (as shown above)?
   - Bottom of TP panel near input?
   - Integrated into input placeholder?

2. **How prominent?**
   - Always visible vs. collapsed/expandable
   - Subtle text vs. chips/badges

3. **Interaction on click?**
   - Context indicator → opens context browser?
   - Deliverable indicator → navigates to deliverable?
   - Surface indicator → just informational?

4. **Mobile/narrow view?**
   - Show all three? Collapse to icons?
   - Priority order if space constrained?

### Relationship to Conversational Assurance

The visual cues DON'T replace the conversational pattern - they augment it:

| What | Visual Cue Shows | TP Says Explicitly |
|------|------------------|-------------------|
| Context | `🧠 Board context` | "I'll use your Board context for this" |
| Intent | - | "I'll create a weekly board update" |
| Schedule | - | "Set for every Monday at 9am" |
| Confirmation | Surface updates | "Done! Here's the setup review" |

Visual = ambient awareness
Conversational = explicit confirmation for decisions

---

## Core Concept: Assurance & Authority

### The Problem We're Solving

Users need confidence that YARNNN:
1. **Understands their intent** - "Yes, this is what I meant"
2. **Uses the right context** - "Yes, draw from these sources"
3. **Can be corrected** - "No, I meant something different"

This is similar to Claude Code's topic inference - but we make it explicit because:
- Deliverables are recurring (mistakes compound)
- Context directly affects output quality
- Users are "supervisors" who need oversight

### The Assurance Pattern

**At every decision point, show what we understood and allow correction:**

| Stage | What User Sees | How They Correct |
|-------|---------------|------------------|
| **Intent** | "I'll create a board update" | "No, status report" |
| **Context** | "Using your TechStart Board context" | "No, different board" |
| **Schedule** | "Every Monday at 9am" | "Make it Fridays" |
| **Output** | Draft content | Edit before approve |

### Clarification vs. Confirmation

**Clarification** (TP asks before acting):
- Ambiguous request
- Multiple possible contexts
- Missing critical info

**Confirmation** (TP shows after acting):
- Setup confirmation surface
- "Here's what I set up, adjust if needed"
- Visual assurance before first run

### Context Architecture Decisions

**Resolved:**
- ✅ Schema supports project-scoped memories (nullable project_id)
- ✅ API has separate endpoints for scopes
- ✅ Each deliverable gets isolated context automatically
- ✅ UI terminology: "Your context" + "This deliverable's context" (not "project")
- ✅ TP states context inference explicitly
- ✅ Setup confirmation shows context before first run

**Implementation approach:**
- Keep `project_id` in schema (powers isolation)
- UI never shows "project" - shows "deliverable context"
- TP verbalizes: "I'll use your [X] context for this"
- Setup surface shows what context will be used

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
| **TP Bar indicators** | 3 visual cues: Surface, Context, Deliverable |
| **Two-layer assurance** | Visual cues (ambient) + Conversational (explicit) |

## Next Steps

1. [x] ~~Decide: "Project" vs "Deliverable context" terminology~~ → Deliverable context
2. [x] ~~Decide on Setup Flow~~ → Three-stage with clarification
3. [x] ~~Two-layer assurance model~~ → Visual cues (ambient) + Conversational (explicit)
4. [ ] **TP Bar design decisions**: Where to place indicators, interaction on click
5. [ ] Decide on Review Information Density details (how much to show)
6. [ ] Decide on Post-Approval Flow details (modal vs inline)
7. [ ] Update TP system prompt for context clarification pattern
8. [ ] Create/update Setup Confirmation surface
9. [ ] Update Review surface with context panel
10. [ ] Implement TP Bar state indicators
11. [ ] Implementation plan for remaining gaps
