# Surface Display Map

**Date:** 2026-04-15
**Status:** Active — ground-truth from code, not narrative docs
**Sources:** `WorkDetail.tsx`, `WorkListSurface.tsx`, `details/*Middle.tsx`, `context/page.tsx`, `WorkspaceTree.tsx`, `ContentViewer.tsx`, `InferenceContentView.tsx`

---

## Purpose

This document is the single reference for what each surface actually renders, organized by page → mode → task type → component. It is ground-truth from code, not aspirational design. Use this as the foundation for deriving what actions are needed and where (a separate discourse).

---

## The Three-Surface User Journey

```
/work  (setup + operational health)
  ↓
  [ judgment gap — what should I do about this? ]
  ↓
/context  (results + accumulated intelligence)
```

**Work** answers: "Is this running correctly? What is it configured to do?"
**Context** answers: "What has it produced? What does my workspace know?"

The judgment gap between them is currently handled by TP chat (present on both surfaces). Whether additional affordances belong in this gap is a separate discourse.

---

## Surface 1: Work (`/work`)

### Mode A: List View (no `?task=` in URL)

**Functional role:** Inventory of all work units. Orient, filter, and navigate to task detail.

**Chrome:**
- `SurfaceIdentityHeader`: "Work" H1, subtitle "Your active tasks and scheduled work"
- Toolbar: Mode chips (`Recurring` / `One-time`), title search input, Group-by toggle (`Output kind` / `Agent`), overflow `···` (include archived, include system)
- Plus-menu (bottom-right): "Start new work" → `TaskSetupModal`

**Body:** Grouped rows. Default group-by is Output kind → five groups:

| Group label | Included output_kinds / task types |
|-------------|-----------------------------------|
| **Reports** | `produces_deliverable` (non-digest) |
| **Tracking** | `accumulates_context` (non-digest) |
| **Connected** | slack-digest, notion-digest, github-digest |
| **Actions** | `external_action` |
| **System** | `system_maintenance` |

Each row: kind icon + status dot · title · sub-label (agent name or kind) · schedule string · time signal (Next run or Last run, relative).

**Empty state:** "No tasks yet. Use the plus button to start new work."

**Navigation out:** Click any row → `/work?task={slug}` (detail mode)

---

### Mode B: Task Detail (`?task={slug}`)

**Functional role:** Operational health of a single task. One question per kind (see below). NOT the knowledge surface — accumulated results live in `/context`.

**Chrome:**
- `PageHeader` breadcrumb: `Work › {task.title}` — last segment = task title
- Subtitle strip: mode badge (`Recurring` / `One-time`) · status · schedule string · next/last run times
- Actions slot: Run / Pause-Resume / Edit-via-chat (prompt relay to task-scoped TP chat)
- Right panel: TP chat (`ThreePanelLayout`, `defaultOpen: true`), `chatSurfaceOverride: { type: 'task-detail', taskSlug }`

**`ObjectiveBlock`** (rendered for all output_kinds except `system_maintenance`):
- `task.objective.deliverable` (what it produces)
- `task.objective.audience` (who it's for)
- `task.objective.purpose` (why it matters)

---

#### Kind: `produces_deliverable`

**Functional question:** "Is the output right?"

**`DeliverableMiddle`** renders:

| Section | Content | Data source |
|---------|---------|-------------|
| Tab strip | Output · History | — |
| **Output tab** | | |
| Latest output label | "Latest output · {relative date}" | `useTaskOutputs` → `latest.date` |
| `SectionProvenanceStrip` | Freshness pills per section (only if `sys_manifest` present) | `latest.manifest.sections[]` |
| `QualityContractPanel` (collapsible) | expected_output · quality_criteria · audience · user_preferences | `task.deliverable_spec` (parsed DELIVERABLE.md) |
| Output body | Rendered HTML in nested-card iframe, or markdown fallback | `latest.html_content` or `latest.md_content` |
| **History tab** | | |
| Run list | Date + relative time per past run | `useTaskOutputs` → `history[]` |

**Empty state:** "No output yet. Run this task to generate the first version."

**Context pointer:** `OutputsLinkBlock` (bottom of detail) — links to `/context?path=/tasks/{slug}/outputs` so user can view the same output in the knowledge surface.

---

#### Kind: `accumulates_context`

**Functional question:** "Is it tracking the right things?"

**`TrackingMiddle`** renders:

| Section | Content | Data source |
|---------|---------|-------------|
| `PlatformSourcesSection` | Source picker (only for platform digest tasks with `sources` field) | `task.sources` + platform connection |
| Run receipts | Compact list: date + one-line summary extracted from run log | `useTaskOutputs` → `history[]`, `extractReceiptLine()` |
| Last-run log | Expandable full markdown of most recent run | `latest.content` |
| `DataContractPanel` (collapsible) | Context structure (paths, format) + data quality criteria | `task.deliverable_spec` |

**Empty state:** "No runs yet. This task will accumulate context on its next scheduled run."

**Context pointer:** `OutputsLinkBlock` links to `/context?domain={domain}` — the domain folder is the result, not the run log.

---

#### Kind: `external_action`

**Functional question:** "Did it fire correctly? What did it send?"

**`ActionMiddle`** renders:

| Section | Content | Data source |
|---------|---------|-------------|
| `PlatformSourcesSection` | Source picker (which channel/page to read from) | `task.sources` |
| Action Target block | Delivery target (channel/page name) | `task.delivery` or `task.objective.audience` |
| Latest payload | Markdown render of last sent message | `latest.content` or `latest.md_content` |
| Action history | List: date + status + optional external platform link | `useTaskOutputs` → `history[]`, `manifest.delivery_external_url` |

**No iframe.** No workspace file — artifact lives on external platform.

**No context pointer.** `external_action` produces no workspace output.

---

#### Kind: `system_maintenance`

**Functional question:** "Is the housekeeping healthy?"

**`MaintenanceMiddle`** renders:

| Section | Content | Data source |
|---------|---------|-------------|
| Hygiene log | Markdown of last run summary | `latest.content` |
| Run history | Compact date + status list | `useTaskOutputs` → `history[]` |

**`ObjectiveBlock` suppressed** for `system_maintenance` (ADR-167 spec — though current code still renders it for all kinds).

**No context pointer.** System maintenance produces no user-facing workspace output.

---

## Surface 2: Context / Files (`/context`)

### Navigation model

**Left panel (always visible):** `WorkspaceTree` — four synthetic roots:

| Root | Maps to workspace path | Contents |
|------|----------------------|---------|
| **Context** | `/workspace/context/` | Domain folders (competitors, market, relationships, etc.) |
| **Reports** | tasks with `produces_deliverable` + `last_run_at` | One entry per deliverable task with a completed run |
| **Uploads** | `/workspace/uploads/` | User-contributed files |
| **Settings** | `/workspace/` (identity/brand/awareness) | IDENTITY.md, BRAND.md, AWARENESS.md |

Clicking a tree node sets `selectedNode` → drives center panel content.

**Right panel:** TP chat (global session). Surface context: `type: "context"`, includes navigation path. Plus-menu: Start new work → `TaskSetupModal` · Update my info → prompt relay · Web search · Upload file.

---

### Center panel dispatch

The center panel renders differently depending on what tree node is selected:

#### A. Domain folder (root: Context)

**Node type:** folder at `/workspace/context/{domain}/`

**`ContentViewer` → `DirectoryView`:**
- Header: domain name + entity count
- Directory listing grid: entity subfolders + synthesis files (`_`-prefixed)
- Each row: name · kind (folder/file) · last modified

**No task-type mapping** at folder level — domain folders are shared across all tasks that write to them. The folder is the result of one or more `accumulates_context` tasks.

**Navigate deeper:** Click entity subfolder → entity files (profile.md, summary.md, etc.)

---

#### B. Task output entry (root: Reports)

**Node type:** task output entry (synthetic, maps to `/tasks/{slug}/outputs/latest/`)

**`DeliverableMiddle`** — same component as Work detail, same render logic:
- Tab strip: Output · History
- Output tab: provenance strip + quality contract + HTML iframe
- History tab: past runs

**This is the primary place to read a deliverable.** Work shows operational health; Context shows the knowledge artifact. Same component, different navigational context and intent.

**Clicking from Context means the user is in knowledge-consumption mode**, not operational-health mode. The distinction is navigational intent, not rendered content.

---

#### C. Upload file (root: Uploads)

**Node type:** file at `/workspace/uploads/{filename}`

**`ContentViewer` → `FileView`:**
- Header: file icon + name + metadata (size, type, uploaded date) + Open/Download buttons
- Body: type-aware viewer
  - `.md`: `MarkdownRenderer`
  - `.html`: `<iframe>`
  - `.png/.jpg`: `<img>`
  - `.pdf`: `<iframe>`
  - `.csv`: `CsvPreview` (first 20 rows as table)
  - other: `<pre>` syntax-highlighted

---

#### D. Settings files (root: Settings)

Three files with specialized renderers:

| File | Component | Sections |
|------|-----------|---------|
| `IDENTITY.md` | `InferenceContentView` (target="identity") | Source caption · markdown body · gap banner |
| `BRAND.md` | `InferenceContentView` (target="brand") | Source caption · markdown body · gap banner |
| `AWARENESS.md` | `ContentViewer → FileView → MarkdownRenderer` | Plain markdown (no inference metadata) |

**`InferenceContentView`** shows:
1. Source provenance caption: "Last updated from: {source}" + relative age
2. Markdown body (inference result)
3. Gap banner (if missing fields): named gaps + suggested fill question + "Chat to fill this in" link → `CHAT_ROUTE?prompt=...`

---

### Task type → Context surface mapping

This table answers: "If a task of type X runs, where does its output appear in Context?"

| Task type | output_kind | Appears in Context as |
|-----------|-------------|----------------------|
| `daily-update` | `produces_deliverable` | Outputs root → DeliverableMiddle |
| `market-report`, `executive-brief`, `competitive-report`, etc. | `produces_deliverable` | Outputs root → DeliverableMiddle |
| `track-competitors`, `track-market`, `track-relationships`, etc. | `accumulates_context` | Context root → domain folder (e.g., `/workspace/context/competitors/`) |
| `slack-digest`, `notion-digest`, `github-digest` | `accumulates_context` | Context root → platform temporal folder (e.g., `/workspace/context/slack/`) |
| `slack-respond`, `notion-update` | `external_action` | Does NOT appear in Context — artifact is on external platform |
| `back-office-agent-hygiene`, `back-office-workspace-cleanup` | `system_maintenance` | Does NOT appear in Context — no user-facing output |

**The Reports root is a curated view**: only tasks with `produces_deliverable` AND at least one completed run appear. It is not a raw file dump — it is the rendered artifact layer. "Reports" names the intent (something to read and act on) rather than the mechanism ("outputs" sounds like a filesystem concept).

**The Context root is the knowledge layer**: domain folders accumulate over time from multiple task runs. Each tracking task writes to its assigned domain(s). The folder outlives any single task run.

---

## Cross-Surface Correspondence

| Work detail shows | Context shows | Same data? |
|-------------------|---------------|-----------|
| `DeliverableMiddle` (Output tab) | `DeliverableMiddle` (Output tab via Reports root) | Yes — same component, same API call |
| `TrackingMiddle` (run receipts + log) | Domain folder in Context root | No — Work shows run health; Context shows accumulated entities |
| `ActionMiddle` (delivery history) | Nothing | Action tasks have no Context representation |
| `MaintenanceMiddle` (hygiene log) | Nothing | System tasks have no Context representation |

The only kind with a direct Work↔Context equivalence is `produces_deliverable`. For `accumulates_context`, Work and Context show fundamentally different views of the same task's work product.

---

## Component Inventory

### Work surface components

| Component | File | Role |
|-----------|------|------|
| `WorkListSurface` | `work/WorkListSurface.tsx` | List mode — grouped rows, toolbar, TaskSetupModal |
| `WorkDetail` | `work/WorkDetail.tsx` | Detail shell — ObjectiveBlock + KindMiddle dispatch |
| `DeliverableMiddle` | `work/details/DeliverableMiddle.tsx` | Output/History tabs, HTML iframe, QualityContractPanel |
| `TrackingMiddle` | `work/details/TrackingMiddle.tsx` | Run receipts, last-run log, DataContractPanel |
| `ActionMiddle` | `work/details/ActionMiddle.tsx` | Action target, latest payload, fire history |
| `MaintenanceMiddle` | `work/details/MaintenanceMiddle.tsx` | Hygiene log, run history |
| `PlatformSourcesSection` | `work/details/PlatformSourcesSection.tsx` | Source picker for platform-backed tasks (used in Tracking + Action) |
| `QualityContractPanel` | inside `DeliverableMiddle` | Collapsible spec panel (expected_output, quality_criteria) |
| `DataContractPanel` | inside `TrackingMiddle` | Collapsible spec panel (context structure, quality criteria) |
| `SectionProvenanceStrip` | `work/details/SectionProvenanceStrip.tsx` | Freshness pills per output section |

### Context surface components

| Component | File | Role |
|-----------|------|------|
| `WorkspaceTree` | `workspace/WorkspaceTree.tsx` | Left panel — four synthetic roots, recursive tree |
| `ContentViewer` | `workspace/ContentViewer.tsx` | Center panel — DirectoryView or FileView dispatch |
| `DeliverableMiddle` | `work/details/DeliverableMiddle.tsx` | Reused — renders task outputs when Outputs root node selected |
| `InferenceContentView` | `context/InferenceContentView.tsx` | IDENTITY.md / BRAND.md with provenance + gap banner |
| `ResourceList` | `context/ResourceList.tsx` | Platform source selection (used in Settings > platform connections) |
| `ResourceRow` | `context/ResourceRow.tsx` | Individual resource item with sync state |
| `StatusBadge` | `context/StatusBadge.tsx` | Active/Paused/Other color badge |

---

## Known Gaps and Divergences

| Gap | Location | Notes |
|-----|----------|-------|
| No `FeedbackStrip` in `WorkDetail` | `WorkDetail.tsx` | Proposed in `FEEDBACK-LOOP.md`. Not yet implemented. |
| `OutputsLinkBlock` ("See in Context" pointer) | `WorkDetail.tsx` | Mentioned in ADR-180 intent; verify whether it exists in code. The cross-reference from Work→Context for `accumulates_context` tasks is currently implicit (user must navigate manually). |
| `accumulates_context` tasks: no entity-level navigation from Work | `TrackingMiddle.tsx` | Only links to domain folder root. Entity drill-down requires navigating to Context first. |
| Empty workspace state on `/context` | `context/page.tsx` | Renders empty tree roots with CTAs. Not explicitly specified in design docs. |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-15 | Initial — ground-truth matrix from code. Work list/detail per kind, Context tree/center/settings, cross-surface correspondence table. |
