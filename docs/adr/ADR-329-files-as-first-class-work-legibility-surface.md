# ADR-329 — Files as the Operator's Substrate Surface: Five File Verbs, Two Operator / Two System / One Shared

> **Status**: IMPLEMENTED (2026-06-08). **Amended 2026-06-10** (D2 reshape — see Amendment 1). **Amended 2026-06-19** (D2 re-ratified in its Finder shape — see Amendment 2). Drafted + implemented by KVK + Claude. Frontend re-composition + one read-only route + one route-behavior change; no schema change.
> **Date**: 2026-06-08
> **Authors**: KVK, Claude
> **Hat**: A (System Editor) — reshapes the operator-facing Files surface real operators inherit.
> **Dimensional classification**: **Channel** (Axiom 6 — how the operator perceives + acts on authored work) primary; **Substrate** (Axiom 1 — Layer 1 made legible) + **Mechanism** (Axiom 5 — the file-verb permission carve) secondary.
> **Upstream discourse**: [substrate-portability-swap-test-2026-06-08.md](../analysis/substrate-portability-swap-test-2026-06-08.md) ("the OS metaphor's frontend payoff is the two things only Layer 1 can show that a Finder cannot: attribution/provenance, and the permission topology made legible") + [ADR-328](ADR-328-substrate-portability-invariant.md) (Layer 1 is the authored, attributed, portable substrate; Layer 2 is reconstructable cache).

---

## Amendment 2 (2026-06-19) — the workspace-wide recency view is canon, in its Finder **Recents** shape (center pane, not sidebar feed)

**Status correction first.** Amendment 1 deleted `RecentlyAuthored.tsx` + the `recent-revisions` route. A later commit (`ba22d0b`) re-added them as a sidebar feed leading the Files surface — **without amending this ADR**. So for a window the code ran a shape the canon had retired, and the sidebar feed sat *next to* the `NodeDetailsPanel` that replaced it. Operator-observed (KVK 2026-06-19, against the live Files window vs macOS Finder Recents): the sidebar feed truncates filenames to illegibility (`judgment_…`, `OCCUPANT.…`) in the 280px rail, while the wide center pane sits empty (`Select a file or folder`). The Finder analog is the inverse — Recents *fills the main pane* with readable, columnar rows.

**What changed:** the workspace-wide recency view is **re-ratified** as canon, **as a Finder-faithful `Recents` view in the center pane** (the empty-state of the surface), **not** as the sidebar feed Amendment 1 rightly killed. The component is `RecentRevisions` (renamed from `RecentlyAuthored`); it renders a columnar table (**Name · Where · Author · When**, full filenames, full-width) when no node is selected. The OS-native label is **"Recents"** (Finder's word), not "Recently authored."

**Why this is NOT a revival of what Amendment 1 killed** — Amendment 1 raised three objections; the Finder shape answers each rather than re-incurring it:
1. *"Two stacked recency views"* — the center Recents table renders **only when nothing is selected**; the per-node revision view (NodeDetailsPanel) renders **only when something is selected**. They are **mutually exclusive by construction** — they can never co-render, so there is no stacking. (Amendment 1's failure was a *sidebar feed* that co-rendered with the body revision panel; that specific shape stays dead.)
2. *"'authored' reads as jargon"* — fixed: the view is labeled **"Recents"** (OS-native), and rows show **plain who/where/when**, not "authored substrate delta."
3. *"The data is fundamentally per-node"* — half-true, and Finder itself draws the line we now draw: **per-node history is Get Info/Details** (this file's chain), **workspace-wide "what changed while I was away" is the Recents view** (a different question, not a per-node property). Amendment 1 conflated "the feed *shape* was wrong in the sidebar" with "a workspace-wide view is wrong." Amendment 2 separates them: the *shape* (sidebar feed) stays retired; the *workspace-wide question* gets its honest Finder home (center pane).

**Net effect on the five verbs:** unchanged (same as Amendment 1). `read`-includes-provenance now has **two complementary surfaces**, matching Finder: the **Recents** view (workspace-wide glance, center pane, empty-state) + **Get Info/Details** (per-node history, on selection). `add`/`delete`/`edit`/`index` untouched.

**Implementation (shipped 2026-06-19):**
- **RESTORED + RESHAPED:** `web/components/workspace/RecentRevisions.tsx` (renamed from the re-added `RecentlyAuthored.tsx`) — a Finder-style **Recents table** for the center pane: columns **Name · Where · Author · When**, full filenames (no truncation), `Where` derived from the path's section, `When` Finder-relative. Rows deep-link into the file (`onSelectPath`). The cramped sidebar mount is **deleted** — Singular Implementation: one recency view, in the center pane.
- **CENTER-PANE EMPTY STATE:** `files/page.tsx` renders `<RecentRevisions>` in the center pane when `selectedNode` is null (replacing the bare `Select a file or folder` placeholder). Selecting a row (or any tree node) swaps the center pane to the node view; deselecting returns to Recents — exactly Finder's Recents↔file behavior.
- **SIDEBAR NAV ITEM:** a **"Recents"** item sits at the top of the explorer tree pane (above `WorkspaceTree`), the Finder-sidebar Recents analog. Clicking it deselects the current node (`setSelectedPath(null)`), which returns the center pane to the Recents view — the navigational way *back* to Recents once a file is open. It is the active/highlighted item when nothing is selected (`aria-current`). This is what makes Recents a destination, not just a transient empty-state: Finder's Recents lives in the sidebar Favorites and is always one click away.
- **ROUTE:** `GET /api/workspace/recent-revisions` (re-added by `ba22d0b`) is **kept** — it is the right data source for the workspace-wide view. (Amendment 1 deleted it only because the feed shape was wrong; the data question is valid.)
- **GET INFO/DETAILS:** `NodeDetailsPanel` (Amendment 1) is **retained unchanged** — it answers the per-node question, complementary to Recents.

**Preserves:** D1 (read-includes-provenance — now via Recents + Details + the header glance), D3–D6 (verbs), ADR-209 (revision chain is the data), ADR-328 D6 (Layer-1-only). **Supersedes:** Amendment 1's deletion of the workspace-wide view *as a concept* (the sidebar-feed *shape* it killed stays dead; the center-pane Finder shape is the re-ratified form). **Amends:** the `ba22d0b` re-add (which was unratified) is now ratified in corrected form.

---

## Amendment 1 (2026-06-10) — provenance is a per-node Details property, not a standing feed

**What changed:** D2's "workspace-wide *feed*" (`RecentlyAuthored` left-rail) is replaced by **per-node Details** ("Get Info"), the OS Properties/Get-Info convention. The `read`-includes-provenance principle (D1) is **preserved and generalized**: provenance is now a property of the *selected node* (file **or** folder), surfaced on demand via right-click "Get Info" or a header **Details** (ⓘ) toggle — not a permanent rail competing with the tree.

**Why:** the standing feed had three operator-observed problems, all traceable to the feed *shape* (not the data):
1. **Two stacked recency views** — the left-rail workspace feed *and* the center-pane revision history rendered together, with no visible distinction between "workspace-wide substrate delta" and "this file's chain." Confusing by construction.
2. **"authored" reads as jargon** — the operator wanted OS-native vocabulary. "Get Info" / "Details" is the universal convention; the *content* still shows who-touched-what, but the container is named like every other OS.
3. **The data is fundamentally per-node** — provenance/history is a property of a thing, not a workspace-level stream. Treating it as a Details inspector (scoped to whatever is selected — file, folder, or domain) is the honest shape and strictly more capable: the deleted feed could only point at *files*; Details describes *folders/domains* too (subtree recent changes).

**Net effect on the five verbs:** unchanged. `read`-includes-provenance (verbs 1–2) is now delivered through one Details surface scoped to the node, replacing the feed + the body-level revision panel. `add`/`delete`/`edit`/`index` (verbs 3–6) untouched.

**Implementation (shipped 2026-06-10):**
- **DELETED:** `web/components/workspace/RecentlyAuthored.tsx` + `api.workspace.recentRevisions` client method + `GET /api/workspace/recent-revisions` route + `RecentRevision`/`RecentRevisionsResponse` models (single-caller, no other consumers). Singular Implementation — no parallel feed survives.
- **NEW:** `web/components/workspace/NodeDetailsPanel.tsx` — the Details panel. **File node** → embeds `RevisionHistoryPanel` (the existing ADR-209 Phase 4 chain with revert/diff). **Folder node** → read-only subtree recent-changes list (each row = the file that changed + author + age, deep-linking into the file). Reverting an aggregate is meaningless; revert stays on file Details.
- **ROUTE EXTENDED:** `GET /api/workspace/revisions` now accepts *either* `path` (file Details — exact chain) *or* `path_prefix` (folder Details — subtree scan, newest first, each row carrying `path`). One route, two scopes. `RevisionSummary.path` is populated only in the subtree case.
- **MOVED:** the full revision chain (`RevisionHistoryPanel`) folded out of `ContentViewer`'s file body and into Details. The **always-visible** "Last edited by …" header glance (ADR-236 Cluster B) **stays** on the file view — that 1-line attribution is D1's promoted-provenance glance; only the heavy panel moved.
- **INVOCATION:** right-click any tree node → "Get Info" (custom fixed-position context menu — the project has no radix/shadcn menu primitive; mirrors `shell/chrome/TopBarSurface`) + a **Details** (ⓘ) toggle in `SurfaceIdentityHeader`'s `actions` slot when a node is selected. Collapsible section above the content; tied to the current selection.

**Carried-over second-order finding (NOT fixed here):** the explorer tree hides `_`-prefixed substrate, yet most deep-links (Home cockpit faces, folder-Details rows) target exactly those hidden files — so the tree can't "follow you" to the most-navigated nodes. This Amendment makes the hidden file *reachable + inspectable* (Get-Info on a folder-Details row deep-links into it; `syntheticNodeForPath` resolves the viewer), but the tree-honesty question (stop hiding `_*` vs. de-emphasize them) is left to a follow-on. The "doesn't follow me like Finder" complaint is *reduced* (Details now describes any node, hidden or not), not fully resolved.

**Preserves:** D1 (read-includes-provenance — now via Details + the header glance), D3–D6 (add/delete/edit/index verbs), ADR-209 (revision chain is the data; revert = new revision), ADR-328 D6 (Layer-1-only — no embeddings/search internals in Details). **Supersedes:** D2 as originally written (the *feed* shape; the underlying intent — "the operator can see what the system authored, and by whom" — survives as the Details property).

---

## The one-sentence thesis

**The Files surface is not first-class because the file *browser* is rich — that instinct is the reinvent-Claude-Code trap (ADR-328). Files is first-class because it is the operator's substrate surface: where they *see* the work the system authored (who wrote each claim, how it evolved, what changed while they were away) and *act* on their own material (add, delete) — under a permission carve that is OS-neutral and traces directly to ADR-320 topology. There are exactly five verbs over the substrate: `add` and `delete` are operator verbs; `edit` and `index` are system verbs; `read` is shared (and reading includes provenance). This carve dictates the whole file UX, and its second-order effect on Home is small: Home stays the decision glance and grows no file affordance.**

---

## Why this does NOT contradict the swap-test

The swap-test concluded the Files *surface* is "the least fundamental layer" and warned against a "richer file explorer / Finder clone." This ADR is not that — it answers a different question:

- **Swap-test question:** "Is a richer file *browser* the moat?" → No. Don't reinvent Finder.
- **This ADR's question:** "Does the operator have a first-class way to *see and trust* the work the system did, and *act on their own* material?" → That's not browser chrome. It's provenance legibility + a clean file-verb permission model.

The swap-test names the resolution itself: *"the frontend payoff is the two things only Layer 1 can show that a Finder cannot — (1) attribution/provenance … `git log` surfaced as L3, the moat made visible; (2) the permission topology made legible."* This ADR delivers (1) directly and grounds (2) in the file-verb carve.

---

## The model — five file verbs (the whole permission story in one table)

Every OS exposes the same handful of verbs over a filesystem. Naming the file operations *is* the OS-neutral vocabulary — no bespoke decision-point numbers, the verbs are the canon.

| Verb | Who acts | How | Substrate effect |
|---|---|---|---|
| **read** | operator + system | operator views; system calls `ReadFile` | none — and reading *includes* provenance (authored-by + revision history; the moat made visible) |
| **add** | **operator** | upload affordance on Files | `write_revision` to `uploads/`, attributed `operator`, auto-indexed (ADR-325 D6) |
| **delete** | **operator** | "Delete" on Files (uploads only) | **archive, not erase** — `write_revision` sets `lifecycle=archived`; ADR-209-retained, reversible |
| **edit** | **system only** | operator routes intent through chat → `WriteFile` | attributed revision — the operator never edits files directly |
| **index** (embed) | **system only** | `Embed` primitive, autonomy-gated (+ upload auto-index) | derived Layer-2 index; never an operator button |

**The one-line UX law:** *the operator adds and deletes their own material; the system edits and indexes; everyone reads — and reading includes seeing who authored what.*

This maps 1:1 to ADR-320's caller×root topology: the operator owns `uploads/`; the system owns everything it authors. The carve is the topology made visible (swap-test payoff #2).

---

## Decisions

### 1. read — provenance is promoted to first-class on the file view.

> **Amended 2026-06-10 (Amendment 1):** preserved + generalized. The full `RevisionHistoryPanel` moved from the file *body* into the per-node **Details** panel ("Get Info"); the always-visible "Last edited by …" header glance stays on the file view. Provenance now scopes to any node (file or folder), not just text files.

When a file is selected, its authored-by + revision history is a first-class element of the file view, not a buried panel. The `RevisionHistoryPanel` (ADR-209 Phase 4) — which previously rendered on Brand/Task/Agent views but **never on the Files surface itself** — now renders on every text-shaped file (markdown/text/csv/html). This is `git log`/`blame` as the file view's substrate-trust layer: who authored this claim, how it evolved, whether it's been judged. Promotion of existing components, not new build.

### 2. read — "Recently authored" is a first-class view (the work-legibility surface).

> **SUPERSEDED 2026-06-10 (Amendment 1):** the standing workspace-wide *feed* (`RecentlyAuthored`) is replaced by **per-node Details** ("Get Info") — the OS Properties convention. The intent below ("the operator can see what the system authored, and by whom") survives as a per-node property; the *feed shape + the "Recently authored" name* do not. Read Amendment 1 (top of file) for the current design. The text below is preserved as the original decision.

Files leads with a reverse-chronological feed of authored substrate changes: *what the system authored in the workspace, and by whom*, grouped by author-class with relative time, each row deep-linking to the file. Reads a new read-only route `GET /api/workspace/recent-revisions` over `workspace_file_versions` (ADR-209). This is the literal "supplement the work done in the system" surface — it makes accumulation watchable.

Distinct from the three existing recency-ish surfaces, must not duplicate:
- **Home `KernelRecentArtifacts`** = delivered *outputs* (reports). This = authored *substrate changes*. Different substrate.
- **Home `KernelJudgmentTrail`** = Reviewer *decisions*. This = the *file mutations* those decisions (+ agents + operator) produced.
- **The Feed (ADR-259)** = the multi-actor *invocation narrative*. This = the *substrate delta*, not the narrative.

### 3. add — upload is an operator verb, homed on Files.

The single "add a file" affordance lives on Files (where uploads live, where "add a file" is the natural thought). Routes through the existing `POST /api/documents/upload` → text extraction → `/workspace/uploads/{slug}.md` via the Authored Substrate (ADR-209, attributed `operator`) → auto-index (ADR-325 D6). Singular Implementation: there is no parallel upload UI (Settings shows a document *count*, not an uploader).

### 4. delete — an operator verb with trash-semantics, scoped to operator-owned roots.

The operator-facing label is **"Delete"**, but the behavior is **archive, not erase** (Trash, not `rm`):
- **Retention (ADR-209):** delete writes a *new revision* with `lifecycle='archived'`, attributed `operator`. The row + revision chain + storage binary stay. Reversible. The one operation that previously violated retention (a hard `table.delete()`) is replaced — Singular Implementation, the hard-delete route is gone.
- **Scope (ADR-320):** the operator may delete only operator-authored material under `/workspace/uploads/`. The button is gated on that prefix in the UI **and** the backend returns 403 for any other path. The operator does not delete what the system authored on their behalf — deleting a Reviewer principle or agent context from a file browser would break the persistent-judgment-seat promise (THESIS Commitment 2). Operator-authored *constitution* files (MANDATE/IDENTITY/…) are *edited via chat*, never deleted from the browser.
- Archived files self-filter from the explorer tree + uploads list (`lifecycle.is.null OR lifecycle.neq.archived`).

### 5. edit — system-only; stays in chat. (No change; ratified here.)

Direct inline editing was deleted (ADR-236); the operator routes edit intent through chat → `WriteFile(scope='workspace')` (ADR-235). The file view shows `EditInChatButton`, never a text field. This ADR ratifies it as the canonical `edit` verb and forbids re-introducing an inline editor.

### 6. index (embed) — system-only; never an operator button. (No change; ratified here.)

Per ADR-325, `Embed` is an LLM primitive, autonomy-gated (`GATE_QUEUEABLE` — the autonomy mode *is* the embed policy), with one operator-initiated trigger: upload auto-index (D6). There is no standalone operator "Embed" button and **the Files surface must never grow one**. Embedding is a derived Layer-2 index over Layer-1 content (ADR-328); exposing it as an operator action would surface cache machinery the operator should never manage.

### 7. Second-order Home effect is small — Home stays the decision glance.

`add`/`delete` are operator file verbs surfaced **on Files**; Home grows no file-management affordance. Home keeps its decision-shaped glance (decision queue + judgment trail + ground-truth). Its recent-artifacts slot thins to a glance (limit 3) labeled "Recently delivered" (outputs — distinct from Files' "Recently authored" substrate-change feed) with a "View in Files" pointer (also fixing a stale `/workspace/reports` deep-link → the substrate is at `/workspace/operation/reports`, ADR-231 D2). Discipline: file ops live on Files; glances live on Home.

---

## What this is NOT

- **NOT a richer file browser / Finder clone.** The tree is unchanged; the *file view* + *recency view* gain legibility, and operator file verbs (add/delete) get clean affordances.
- **NOT inline / Notion-style editing.** Edit stays in chat (verb 5). Re-introducing an inline editor is forbidden.
- **NOT an operator embed button.** Index stays system-only (verb 6).
- **NOT hard delete.** Delete is archive (retained, reversible). No operation erases authored substrate.
- **NOT Files-as-cockpit.** Home stays the cockpit (ADR-312); Files is the substrate + escape-hatch surface (ADR-245).
- **NOT a Layer-2 surface.** No embeddings/search-internals/RLS exposed (ADR-328 D6).
- **NOT new substrate, no new primitive.** One read-only route (recent-revisions), one route-behavior change (delete→archive), the rest frontend re-composition over served data. `lifecycle` already exists on `workspace_files`.

---

## Claim tiering (forced vs chosen)

- **FORCED (by receipts + canon):** the provenance/recency data is fully present in Layer 1 and served, yet not legible (composition gap, not infra gap). The five-verb carve is forced by ADR-320 topology (who-owns-which-root) + ADR-209 retention (delete cannot erase) + ADR-325 (index is system-gated) + ADR-236 (edit is chat-only) — the model *reads off* existing canon rather than inventing.
- **Commitment-4 / DP16-GROUNDED:** Files-as-Layer-1's-operator-face; legibility as the frontend complement to ADR-328's export-as-proof.
- **DESIGN CHOICE (open to pushback):** the visual shape of the provenance promotion + recency feed; the "Delete" label vs "Archive"/"Remove" (chose "Delete" with trash-semantics — most familiar word, honest reversible behavior); delete scope set at `uploads/` only for now (operator-authored constitution edits are chat-managed, not browser-deletable).
- **EXPLICITLY OUT OF SCOPE:** richer file browser; inline editing; operator embed; Layer-2 exposure; the full permission-topology matrix as a visible surface (ADR-320 payoff #2 — a minimal author label rides along; the full matrix is its own ADR).

---

## Relationship to other ADRs / canon

- **Realizes** the swap-test's "frontend payoff = provenance + topology legibility" — payoff #1 (verbs 1+2), payoff #2 grounded (the five-verb carve = ADR-320 made visible).
- **Complements** ADR-328 — 328 proves portability by *export*; 329 proves authored-accumulation by *legibility*. Both surface Layer 1; neither touches Layer 2.
- **Builds on** ADR-209 (revision chain + `authored_by` + `lifecycle` are the data this surfaces; delete=archive honors retention), ADR-320 (topology = the file-verb permission carve), ADR-325 (index/embed system-gated), ADR-236 (edit chat-only), ADR-249 (upload → uploads/ substrate).
- **Preserves** ADR-245 (Files = L1 escape hatch + now the substrate surface), ADR-312 (Home stays cockpit), ADR-259 (Feed = invocation narrative; recency = substrate delta).

---

## Implementation (shipped 2026-06-08)

**Backend:**
- `GET /api/workspace/recent-revisions` — read-only, workspace-scoped, Layer-1-only (path/authored_by/message/created_at; no embeddings/search internals). [routes/workspace.py](../../api/routes/workspace.py).
- `DELETE /api/documents/{path}` — replaced hard-delete with archive (`write_revision`, `lifecycle='archived'`, `authored_by='operator'`) + 403 scope guard outside `/workspace/uploads/`. [routes/documents.py](../../api/routes/documents.py).
- Tree + uploads-list queries filter `lifecycle.is.null OR lifecycle.neq.archived`.

**Frontend:**
- `read` verb 1: `RevisionHistoryPanel` rendered on the Files file view for text-shaped files. [ContentViewer.tsx](../../web/components/workspace/ContentViewer.tsx).
- `read` verb 2: `RecentlyAuthored` section leads the Files explorer. [RecentlyAuthored.tsx](../../web/components/workspace/RecentlyAuthored.tsx).
- `add` verb: `UploadButton` in the Files explorer header. [UploadButton.tsx](../../web/components/workspace/UploadButton.tsx).
- `delete` verb: "Delete" (trash-semantics) on the file view, gated to `/workspace/uploads/`. [ContentViewer.tsx](../../web/components/workspace/ContentViewer.tsx).
- Home: `KernelRecentArtifacts` thinned to a 3-row glance + "View in Files" pointer (stale reports deep-link fixed). [KernelRecentArtifacts.tsx](../../web/components/library/kernel-home/KernelRecentArtifacts.tsx).
- `api.documents.delete` comment updated; `api.workspace.recentRevisions` added. [client.ts](../../web/lib/api/client.ts).

No schema change. No Render-service env-var change. No primitive rename. No new substrate.
