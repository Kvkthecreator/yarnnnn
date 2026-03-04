# Phase 3 Surface Layout (History)

**Date:** 2026-03-03
**Status:** Superseded by [Workspace Layout & Navigation](WORKSPACE-LAYOUT-NAVIGATION.md) (2026-03-04). Tab layout implemented as Phase 3 interim; full Cowork-style layout with scoped chat replaced this.
**References:**
- [ADR-087: Deliverable Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — Phase 3 spec
- [ADR-090: Work Tickets Consolidation](../adr/ADR-090-work-tickets-consolidation.md) — Phase 2 (surface redirects, combined here)
- [Workspace Architecture Analysis, Section 10.6](../analysis/workspace-architecture-analysis-2026-03-02.md) — Cowork UI benchmark
- [Workspace Architecture Analysis, Section 11.4](../analysis/workspace-architecture-analysis-2026-03-02.md) — Typed files → UI component mapping

---

## 1. Benchmark: Claude Cowork Layout

The Cowork sidebar organizes workspace state into four compact panels:

| Panel | What it shows | Interaction |
|-------|---------------|-------------|
| **Progress** | Task completion state (e.g., "5 of 5") | Read-only indicator |
| **Content** | Named files/artifacts in the workspace | Click to open in chat |
| **Context** | Uploads, Connectors (data sources) | View/manage sources |
| **Skills** | Workspace-specific agent instructions | View/manage |

Key design properties:
- **Sidebar, not main content** — the chat/content area stays dominant
- **Compact** — each panel is a collapsible section with a count badge
- **Declarative** — shows what the agent has access to, not detailed contents
- **Flat hierarchy** — no sub-pages, everything visible from one view

---

## 2. YARNNN Deliverable Data → Cowork Panel Mapping

| Cowork Panel | YARNNN Data | Field | Current UI Location |
|-------------|-------------|-------|-------------------|
| **Progress** | Schedule state + delivery status | `next_run_at`, `latest_version_status`, `version_count` | Header (schedule badge) + inline status |
| **Content** | Generated versions | `deliverable_versions` | Delivery History section (bottom of page) |
| **Context: Memory** | Agent's accumulated knowledge | `deliverable_memory` JSONB | **Not surfaced** (Phase 3 new) |
| **Context: Sources** | Data sources | `sources` JSONB array | Settings modal only |
| **Context: Sessions** | Scoped chat history | `chat_sessions` via `deliverable_id` FK | **Not surfaced** (Phase 3 new) |
| **Skills** | Behavioral instructions | `deliverable_instructions` TEXT | **Not surfaced** (Phase 3 new) |
| — | Mode selector | `mode` column | **Not surfaced** (Phase 3 new) |

---

## 3. Crowding Assessment

The current `/deliverables/[id]` page has 5 sections in a single-column layout (~538 lines):

```
┌─────────────────────────────────┐
│ 1. Header (title, schedule,     │
│    status, pause/settings)      │
├─────────────────────────────────┤
│ 2. Content Hero (markdown,      │
│    600px max-h, scrollable)     │
├─────────────────────────────────┤
│ 3. Execution Details (status,   │
│    timestamp, word count, src)  │
├─────────────────────────────────┤
│ 4. Schedule (next run, Run Now) │
├─────────────────────────────────┤
│ 5. Delivery History (version    │
│    list, click to switch hero)  │
└─────────────────────────────────┘
```

Phase 3 adds 4 new data surfaces:
- `deliverable_instructions` (editable text)
- `deliverable_memory` (read-only, observations + goal)
- `mode` selector (recurring vs goal)
- Scoped session history (read-only, recent summaries)

### Will it crowd?

**Yes, if all inline.** Adding 4 more sections to a 5-section page makes it 9 sections — too long, the content hero loses prominence.

**No, if we use the right surfacing patterns.** Three options considered:

---

## 4. Layout Options

### Option A: Sidebar (Cowork-style)

Split the detail page into main area + right sidebar:

```
┌──────────────────────┬─────────────────┐
│ Main (70%)           │ Sidebar (30%)   │
│                      │                 │
│ 1. Header            │ Instructions    │
│ 2. Content Hero      │ (collapsible)   │
│ 3. Execution Details │                 │
│ 4. Schedule          │ Memory          │
│ 5. Delivery History  │ (collapsible)   │
│                      │                 │
│                      │ Sessions        │
│                      │ (collapsible)   │
│                      │                 │
│                      │ Sources         │
│                      │ (collapsible)   │
└──────────────────────┴─────────────────┘
```

**Pros:** Most Cowork-aligned. Context always visible alongside content.
**Cons:** Breaks the current max-w-3xl single-column layout. On mobile, sidebar stacks below — losing the "alongside" benefit. Significant layout refactor.
**Verdict:** Right direction long-term (D2/D3 workspace evolution), but over-investment for Phase 3 validation.

### Option B: Tabbed sections below content (recommended)

Keep the single-column layout. Add a tab bar below the execution details that switches between context panels:

```
┌─────────────────────────────────┐
│ 1. Header (+ mode badge)       │
├─────────────────────────────────┤
│ 2. Content Hero (unchanged)    │
├─────────────────────────────────┤
│ 3. Execution Details            │
├─────────────────────────────────┤
│ 4. Schedule                     │
├─────────────────────────────────┤
│ [History] [Instructions] [Memory] [Sessions]  ← tab bar
│                                 │
│ (tab content — one panel at     │
│  a time, compact)               │
└─────────────────────────────────┘
```

**Pros:** No layout change to existing sections. Tabs contain complexity — each panel renders independently. Easy to add/remove tabs in future. Mobile-friendly. Low cognitive load — user focuses on one panel at a time.
**Cons:** Can't see Instructions while browsing History. Tab switching adds clicks.
**Verdict:** Best balance of simplicity, compactness, and extensibility. Matches "validate before committing" philosophy. If sidebar proves necessary later, the tab content components port directly into sidebar panels.

### Option C: Settings modal expansion

Keep the page unchanged. Add Instructions and Memory sections to the existing DeliverableSettingsModal:

```
Settings Modal (existing):
  1. Destination
  2. Title
  3. Schedule
  4. Data Sources
  5. Recipient Context (collapsed)
  + NEW: 6. Instructions (textarea)
  + NEW: 7. Memory (read-only viewer)
  + NEW: 8. Mode selector
```

**Pros:** Zero changes to the detail page. Quick to implement.
**Cons:** Instructions buried in settings — users won't discover or iterate on them. Memory hidden behind a modal — defeats the purpose of making the agent's knowledge visible. Settings modal already long (830 lines).
**Verdict:** Instructions belong on the detail page, not in settings. The modal is for configuration (destination, schedule, sources), not for context authoring.

---

## 5. Recommended Layout: Option B — Tabbed Sections

### Tab definitions

| Tab | Label | Data | Interaction | Default |
|-----|-------|------|-------------|---------|
| **History** | Delivery History | `deliverable_versions[]` | Click version → switch Content Hero | Selected (existing behavior) |
| **Instructions** | Instructions | `deliverable_instructions` TEXT | Inline edit (auto-save on blur) | — |
| **Memory** | Agent Memory | `deliverable_memory` JSONB | Read-only viewer with compact cards | — |
| **Sessions** | Chat History | `chat_sessions` via FK | Read-only list of scoped session summaries | — |

### Tab content specifications

#### History tab (existing, relocated)
- Moves current Delivery History section content into a tab panel
- No behavior change — version list, click to switch hero content
- Shows "X deliveries" count in tab badge

#### Instructions tab
- Plain textarea with monospace font (markdown-style editing)
- Auto-save: debounced PATCH to `api.deliverables.update(id, { deliverable_instructions })` on blur or after 2s idle
- Save indicator: subtle "Saved" / "Saving..." text
- Placeholder text: "Add instructions for how the agent should approach this deliverable. Examples: 'Use formal tone', 'Focus on trend analysis', 'The audience is the executive team.'"
- Empty state: placeholder only (no wrapper, no empty state graphic)

#### Memory tab
- Observations list: compact cards showing date + source + note
- Capped at 5 most recent (matching backend cap)
- Goal section (if present): description, status, milestones as checklist
- Read-only — system-accumulated, not user-editable
- Empty state: "No observations yet. The agent accumulates knowledge as it processes content for this deliverable."

#### Sessions tab
- List of scoped TP sessions with summary text
- Shows: session date, duration indicator, summary (first ~100 chars)
- Click to expand full summary
- Read-only — historical record
- Empty state: "No scoped conversations yet. Chat with the deliverable open to build session history."

### Mode indicator

Mode (`recurring` vs `goal`) surfaces as a **badge in the header**, not a separate section:

```
📊 Weekly Status Report [Recurring]     [Active] [⏸] [⚙]
   Weekly at 09:00 → kevin@yarnnn.com
```

For goal mode, the schedule section transforms:
- No "Next run" — goals don't have schedules
- Shows goal progress instead (from `deliverable_memory.goal`)
- "Run Now" becomes "Generate Update"

Mode switching happens in the **Settings modal** (since it fundamentally changes the deliverable's behavior), not inline.

---

## 6. ADR-090 Phase 2: Work Surface Redirects

Combined with Phase 3 since both are frontend changes.

### WorkListSurface → redirect to /deliverables

Current: `WorkListSurface` calls `api.work.listAll()` and shows work tickets.
After: Surface type `work-list` redirects to `/deliverables` route (same as `deliverable-list` already does in `SurfaceRouter.tsx`).

### WorkOutputSurface → redirect to /deliverables/[id]

Current: `WorkOutputSurface` calls `api.work.get(workId)` and shows work_ticket output.
After: Surface type `work-output` redirects to `/deliverables/{deliverableId}` if the work ticket has a `deliverable_id` (93/93 production tickets do). Falls back to showing a "Work item not found" message for any ticket without a deliverable_id (none exist in production).

### IdleSurface "Recent Work" section

Current: Shows recent work tickets from `api.work.listAll()`.
After: Shows recent deliverable versions from `api.deliverables.list()` (already shown elsewhere in IdleSurface as deliverable cards). Remove the "Recent Work" section entirely — it's redundant with the deliverable cards.

### API client cleanup

Remove `api.work.*` methods from `web/lib/api/client.ts`. Remove `Work`, `WorkOutput`, `WorkTicketDetail` types from `web/types/index.ts`. Remove `work-list` and `work-output` from desk surface type definitions.

---

## 7. Backend API Changes Required

### GET /deliverables/:id response

Already returns `deliverable_instructions` and `deliverable_memory` (Phase 1 wired these into the SELECT). Verify frontend types match.

### PATCH /deliverables/:id

Already accepts `deliverable_instructions` in update payload. Verify.

### GET /deliverables/:id/sessions (new endpoint)

Returns scoped chat sessions for this deliverable:
```json
{
  "sessions": [
    {
      "id": "uuid",
      "created_at": "2026-03-03T...",
      "summary": "Discussed shifting from quarterly to monthly...",
      "message_count": 12
    }
  ]
}
```

Query: `SELECT id, created_at, summary, (SELECT count(*) FROM session_messages WHERE session_id = cs.id) as message_count FROM chat_sessions cs WHERE deliverable_id = $1 ORDER BY created_at DESC LIMIT 10`

---

## 8. TypeScript Type Changes

```typescript
// Add to Deliverable type
interface Deliverable {
  // ... existing fields
  deliverable_instructions?: string;
  deliverable_memory?: {
    observations?: Array<{ date: string; source: string; note: string }>;
    goal?: { description: string; status: string; milestones?: string[] };
  };
  mode?: 'recurring' | 'goal';
}

// Add to DeliverableUpdate
interface DeliverableUpdate {
  // ... existing fields
  deliverable_instructions?: string;
  mode?: 'recurring' | 'goal';
}

// New type for scoped sessions
interface DeliverableSession {
  id: string;
  created_at: string;
  summary?: string;
  message_count: number;
}
```

---

## 9. Files Changed (Estimated)

| File | Change | Scope |
|------|--------|-------|
| `web/app/(authenticated)/deliverables/[id]/page.tsx` | Add tab bar + tab panels, mode badge in header | Major (primary change) |
| `web/types/index.ts` | Add instructions/memory/mode to Deliverable type, add DeliverableSession | Small |
| `web/types/desk.ts` | Remove `work-output`, `work-list` surface types | Small |
| `web/types/surfaces.ts` | Remove workId/outputId/ticketId from SurfaceData | Small |
| `web/lib/api/client.ts` | Remove `api.work.*`, add `api.deliverables.sessions()` | Small |
| `web/components/surfaces/WorkListSurface.tsx` | Delete file | Delete |
| `web/components/surfaces/WorkOutputSurface.tsx` | Delete file | Delete |
| `web/components/surfaces/IdleSurface.tsx` | Remove "Recent Work" section | Small |
| `web/components/desk/SurfaceRouter.tsx` | Remove work surface cases, redirect to routes | Small |
| `api/routes/deliverables.py` | Add GET /:id/sessions endpoint | Small |
| `web/components/modals/DeliverableSettingsModal.tsx` | Add mode selector | Small |

---

## 10. Implementation Sequence

1. **Types first** — Update TypeScript types (Deliverable, surfaces, desk)
2. **Backend endpoint** — Add GET /deliverables/:id/sessions
3. **Detail page tabs** — Refactor delivery history into tab, add Instructions/Memory/Sessions tabs
4. **Mode badge** — Add to header, mode selector in settings modal
5. **Work surface redirect** — Redirect work-list/work-output in SurfaceRouter, remove WorkListSurface/WorkOutputSurface
6. **IdleSurface cleanup** — Remove "Recent Work" section
7. **API client cleanup** — Remove api.work.*, remove Work types

---

## 11. What This Does NOT Include

- **Scoped TP chat panel on the detail page** — Future (requires embedding the chat widget, significant component work). Users chat with deliverable scope via the existing dashboard TP when navigating from a deliverable.
- **Goal mode UI** — Mode badge + mode selector included. Full goal UX (milestones, progress tracking, completion) deferred to separate design doc.
- **Memory compaction** — Backend concern, not UI.
- **Sidebar layout** — Validated via tabs first. If tabs prove insufficient, migrate tab panels into sidebar panels.
