# Deliverable Workflow Design

> **Status**: Core Implementation Complete
> **Last Updated**: 2026-02-04
> **Related**: ADR-018, ADR-019, ADR-023, ADR-005 (Memory), ADR-015 (Unified Context)

## Quick Reference

### What's Implemented
- [x] TP Bar state indicators (below input, Claude Code style) - `web/components/tp/TPBar.tsx`
- [x] State indicator utilities - `web/lib/tp-chips.ts`
- [x] Handoff message pattern for TP navigation - `web/contexts/DeskContext.tsx`
- [x] Data model for context scopes (user vs deliverable) - `memories.project_id`
- [x] Basic surfaces: IdleSurface, DeliverableListSurface, DeliverableDetailSurface, DeliverableReviewSurface
- [x] **TP system prompt: context clarification** - `api/agents/thinking_partner.py`
- [x] **Setup Confirmation modal** - `web/components/modals/SetupConfirmModal.tsx`, `api/services/project_tools.py`
- [x] **Dynamic TP bar labels** - `web/lib/entity-cache.ts`, `web/components/tp/TPBar.tsx`
- [x] **Context surface streamlining** - Deliverable scope enabled in `web/components/surfaces/ContextBrowserSurface.tsx`

### What's Pending
1. [ ] Export nudge post-approval flow
2. [ ] Make TP bar indicators clickable (context → open context browser)
3. [ ] Add tentative state indicator (e.g., "Q4 Planning?" when inferred)

### Decisions Made (2026-02-04)
- **Setup Confirmation**: Modal within deliverable flow, shown per deliverable
- **Context clarification**: Always state it (not just when ambiguous)
- **Review context panel**: Skip - use existing context surfaces instead
- **Modal context verbosity**: Detailed (counts, sample memories)
- **Context basket selection**: Not in scope - TP uses `clarify()` upstream if ambiguous

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
| **Conversational Assurance** | During key decisions | TP explicitly states what it's doing | ✅ Implemented |

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

- [x] Show actual deliverable/project names instead of generic labels - via entity-cache.ts
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

**Status:** ✅ Implemented in `api/agents/thinking_partner.py`

#### 1C. Setup Confirmation (Modal)

After TP creates deliverable, show **Setup Confirmation** modal (see Implementation Details below):

- Shows what will be created (title, schedule)
- Shows context that will be used (detailed: memory counts, document counts, sample memories)
- Actions: "Run First Draft Now" or "Just Add to Schedule"
- Edit button to modify context before first run

**Status:** ✅ Implemented - `web/components/modals/SetupConfirmModal.tsx`

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

**Decision:** Skip dedicated context panel - use existing context surfaces instead. User can navigate to ContextBrowserSurface if they need to see/edit context.

**Status:** ✅ Review surface complete as-is

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
| SetupConfirmModal | Post-creation setup review | `web/components/modals/SetupConfirmModal.tsx` | ✅ |

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
| Setup Flow | Conversational → Context stated → Setup Confirmation Modal |
| Context terminology | "Your context" + "Deliverable context" (hide "project") |
| Context visibility | Always show what context will be used before first run |
| Clarification | TP always states context explicitly before creating |
| Review info | Output only (use existing context surfaces if needed) |
| Post-approval | Export nudge with "next run" info |
| TP Bar indicators | 3 visual cues below input: Surface, Context, Deliverable |
| Two-layer assurance | Visual cues (ambient) + Conversational (explicit) |
| TP Bar position | Below input field (Claude Code style) |

---

## Implementation Details

### 1. TP System Prompt: Context Clarification

**Goal**: TP always explicitly states what context will be used when creating a deliverable.

**Files**: `api/agents/thinking_partner.py`, `api/services/project_tools.py`

#### Addition to SYSTEM_PROMPT_WITH_TOOLS

Add after "## Response Patterns (IMPORTANT)":

```markdown
---

## Deliverable Creation: Context Assurance Pattern

When creating a deliverable, you MUST explicitly state what context will be used. This is non-negotiable - users need to verify you understood correctly.

**The Pattern:**

1. **Infer the context** - Based on conversation, existing projects, or user's current surface
2. **State it explicitly** - "I'll use your [X] context for this"
3. **Allow correction** - Give user opportunity to adjust before creating

**Examples:**

User: "I need a weekly report for the board"

GOOD (state context explicitly):
→ `respond("I'll set up a weekly board report. I'll use your TechStart Board context - that includes your investor updates and quarterly metrics. Sound right, or should I use different context?")`
→ Wait for confirmation
→ Then `create_deliverable(...)`

BAD (create without stating context):
→ `create_deliverable(...)` immediately
→ `respond("Done! I created your board report.")`

**When context is ambiguous:**

If user has multiple relevant contexts or you're unsure which applies:
→ `clarify("Which context should I use for this deliverable?", ["TechStart Board (investor updates, metrics)", "General context (your preferences only)", "Create new context for this"])`

**When context is new:**

If this is clearly a new topic with no existing context:
→ `respond("I'll create a new context basket for your board reports. As you refine this deliverable, I'll learn what's specific to this work. Ready to set it up?")`

**After creation - always state what was used:**

→ `respond("Done! I've created 'Weekly Board Update'. It will use your TechStart Board context (12 memories + 2 documents) plus your general preferences. First draft will be ready Monday at 9am. Want me to generate a preview now?")`
```

#### Update to CREATE_DELIVERABLE_TOOL Description

```python
CREATE_DELIVERABLE_TOOL = {
    "name": "create_deliverable",
    "description": """Create a new recurring deliverable for the user.

IMPORTANT: Before calling this tool, you MUST have:
1. Stated what context you'll use ("I'll use your [X] context")
2. Given user opportunity to confirm or correct

Never create a deliverable without first confirming context with the user.

ADR-020: TP can scaffold deliverables on behalf of users.

Use this when the user describes something they need to produce regularly:
- "I need to send weekly updates to my manager"
- "Can you help me create a monthly investor report?"
- "I want to track my competitors weekly"

After stating context and getting confirmation, create the deliverable.
Then follow up with respond() to confirm what was created and what context
will be used for generation.

TYPES:
- status_report: Regular progress/status updates
- stakeholder_update: Updates for clients, investors, partners
- research_brief: Competitive intel, market research, trends
- meeting_summary: Recap of recurring meetings
- custom: Anything else

Returns the created deliverable. Always follow with respond() to:
1. Confirm creation
2. State what context will be used
3. Offer to generate first draft""",
    ...
}
```

---

### 2. Setup Confirmation Modal

**Goal**: After TP creates a deliverable, show a modal with detailed context info before first run.

**Files**: `api/services/project_tools.py`, `web/contexts/TPContext.tsx`, `web/components/modals/SetupConfirmModal.tsx` (new)

#### Backend: New ui_action Type

In `handle_create_deliverable()`:

```python
return {
    "success": True,
    "deliverable": {...},
    "message": f"Created '{title}'",
    "ui_action": {
        "type": "SHOW_SETUP_CONFIRM",
        "data": {
            "deliverableId": deliverable["id"],
            "title": title,
            "schedule": schedule_desc,
            "context": {
                "user_memory_count": user_memory_count,
                "deliverable_memory_count": deliverable_memory_count,
                "document_count": document_count,
                "sample_memories": [...],  # First 3 for preview
            }
        }
    }
}
```

#### Frontend: Handle in TPContext.tsx

```typescript
if (action.type === 'SHOW_SETUP_CONFIRM') {
  setSetupConfirmModal({
    open: true,
    data: action.data
  });
}
```

#### Modal Component

```tsx
// web/components/modals/SetupConfirmModal.tsx

interface SetupConfirmModalProps {
  open: boolean;
  onClose: () => void;
  data: {
    deliverableId: string;
    title: string;
    schedule: string;
    context: {
      user_memory_count: number;
      deliverable_memory_count: number;
      document_count: number;
      sample_memories: string[];
    };
  };
  onConfirm: (runNow: boolean) => void;
}

export function SetupConfirmModal({ open, onClose, data, onConfirm }: SetupConfirmModalProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-500" />
            {data.title}
          </DialogTitle>
          <DialogDescription>
            Ready to generate your first draft
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* What I'll Create */}
          <section className="p-3 rounded-lg bg-muted">
            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              What I'll Create
            </h4>
            <p className="text-sm text-muted-foreground">
              {data.title} • {data.schedule}
            </p>
          </section>

          {/* Context I'll Use - Detailed */}
          <section className="p-3 rounded-lg bg-muted">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <Brain className="w-4 h-4" />
                Context I'll Use
              </h4>
              <Button variant="ghost" size="sm" onClick={() => {/* open context browser */}}>
                Edit
              </Button>
            </div>

            <div className="space-y-2 text-sm text-muted-foreground">
              <div>
                <span className="font-medium">Your context:</span>{' '}
                {data.context.user_memory_count} memories
              </div>
              {data.context.deliverable_memory_count > 0 && (
                <div>
                  <span className="font-medium">Deliverable context:</span>{' '}
                  {data.context.deliverable_memory_count} memories
                </div>
              )}
              {data.context.document_count > 0 && (
                <div>
                  <span className="font-medium">Documents:</span>{' '}
                  {data.context.document_count} attached
                </div>
              )}

              {/* Sample memories preview */}
              {data.context.sample_memories.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border">
                  <p className="text-xs text-muted-foreground mb-1">Preview:</p>
                  <ul className="text-xs space-y-1">
                    {data.context.sample_memories.map((mem, i) => (
                      <li key={i} className="truncate">• {mem}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="flex gap-2 mt-3">
              <Button variant="outline" size="sm">
                <Plus className="w-3 h-3 mr-1" />
                Add context
              </Button>
              <Button variant="outline" size="sm">
                <FileUp className="w-3 h-3 mr-1" />
                Add document
              </Button>
            </div>
          </section>
        </div>

        <DialogFooter className="flex gap-2">
          <Button variant="outline" onClick={() => onConfirm(false)}>
            Just Add to Schedule
          </Button>
          <Button onClick={() => onConfirm(true)}>
            Run First Draft Now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

#### Flow After Modal

| User Action | Result |
|-------------|--------|
| "Run First Draft Now" | Close modal → call `run_deliverable` → navigate to DeliverableDetailSurface |
| "Just Add to Schedule" | Close modal → navigate to DeliverableDetailSurface |
| "Edit" context | Open ContextBrowserSurface for deliverable scope |

#### Future Enhancement

Downstream, consider adding approval mode settings (per-deliverable or user-level) to bypass certain workflow steps. This should be addressed after the core workflow is hardened.

---

### 3. Dynamic TP Bar Labels

**Goal**: Show actual deliverable/project names instead of generic labels.

**Files**: `web/lib/entity-cache.ts` (new), `web/components/tp/TPBar.tsx`, surface components

#### Entity Cache

```typescript
// web/lib/entity-cache.ts
const entityCache = new Map<string, { name: string; type: string }>();

export function cacheEntity(id: string, name: string, type: 'deliverable' | 'project') {
  entityCache.set(id, { name, type });
}

export function getEntityName(id: string): string | undefined {
  return entityCache.get(id)?.name;
}
```

#### Surface Integration

Surfaces populate cache when loading:

```typescript
// In DeliverableDetailSurface
useEffect(() => {
  if (deliverable) {
    cacheEntity(deliverable.id, deliverable.title, 'deliverable');
  }
}, [deliverable]);
```

#### TPBar Integration

```typescript
// In TPBar
import { getEntityName } from '@/lib/entity-cache';

const entityName = surface.type === 'deliverable-detail'
  ? getEntityName(surface.deliverableId)
  : undefined;

// Use in indicator
<span>{entityName || indicators.surface.label}</span>
```

---

### 4. Context Surface Streamlining

**Goal**: Enable deliverable scope in existing context surfaces.

**Files**: `web/components/surfaces/ContextBrowserSurface.tsx`

#### Enable Deliverable Scope

```typescript
// Currently only supports 'user' | 'project'
// Update to include 'deliverable'
scope: 'user' | 'project' | 'deliverable';
```

The deliverable scope maps to the project_id linked to the deliverable (each deliverable has an associated project for context isolation).

---

### 5. Export Nudge Flow (Deferred)

Lower priority - doesn't affect core assurance loop. Address after items 1-4 are complete.

---

## Open Questions

### Resolved (2026-02-04)
1. ~~How explicit should context inference be?~~ → **Always state it**
2. ~~Is Setup Confirmation a new surface type?~~ → **Modal within deliverable flow**
3. ~~Review context panel: Two-panel or collapsible?~~ → **Skip - use existing context surfaces**
4. ~~Setup Confirm modal: When to show?~~ → **Always, per deliverable**
5. ~~Context clarification verbosity in modal?~~ → **Detailed (counts, sample memories)**
6. ~~Existing context baskets as options during creation?~~ → **Not in scope - TP uses `clarify()` upstream if ambiguous**

### Still Open
1. **Post-approval flow:** Modal, toast, or inline surface change?
2. **Approval mode settings:** Per-deliverable or user-level bypass for workflow steps? (Address after core workflow hardened)
