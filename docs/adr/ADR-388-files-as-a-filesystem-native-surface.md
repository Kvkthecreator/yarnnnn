# ADR-388 — Files as a filesystem-native surface: derived tree, one design language, attribution-first details

> **Status**: **Accepted** (2026-06-29) — implementation in progress (the derive-from-FS spine + D1 land first as the bug fix; D2–D5 coherence pass follows). Doc-first. **Channel-dimension (Axiom 6)** — a surface/IA reshape of the Files surface. The load-bearing change (D1) is a **bug fix with a systemic cure**: the left explorer is rebuilt to *derive its tree from the actual filesystem roots* instead of a hardcoded 5-root array, so every directory shows (including the ADR-320 `governance/` + `constitution/` roots and the ADR-376 `inbound/` lane that are invisible today) and no future root can ever go missing. The rest (D2–D5) is a coherence pass toward a Finder/Explorer-native experience: one shared file-row design language, surface-wide view-mode, attribution made legible (no new data — the ADR-209 `authored_by` chain rendered properly), and details via right-click → a Get-Info modal carrying the revision history. One new lightweight read endpoint (`GET /workspace/roots`); no schema, no primitive, no write-path or gate change.
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: live screenshot-walk of the Files surface (2026-06-29). Operator findings: (1) a deep-linked file 404s (`/workspace/inbound/mcp/chatgpt/yarnnn-memory-test.md`); (2) **the explorer doesn't show all directories** — "this isn't about a specific directory, but warrants suspicion why all directories simply aren't visible"; (3) the recents/icons should be more macOS-elegant and the unlabeled dots are confusing; (4) Details should be right-click → a modal showing attribution (who wrote it), filesystem-native, "no new data, just better display of existing information"; (5) the grid/list view toggle should be Files-surface-wide, not Recents-only; (6) "a lack of coherent, consistent design implementation (think Windows Explorer, macOS Finder)."
> **Builds on**: [ADR-320](ADR-320-constitution-region-topological-cut.md) (the five semantic-class roots the tree must show) + [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (the `inbound/` intake lane) + [ADR-209](ADR-209-authored-substrate.md) (the `authored_by` / `workspace_file_versions` revision chain the attribution surfaces) + [ADR-329](ADR-329-files-as-first-class-work-legibility-surface.md) (Files as first-class work-legibility) + [ADR-337/339](ADR-337-file-layer-verb-completion.md) (the file verbs / git-status-shape metadata).
> **Preserves**: ADR-320 topology + lock model (read-only surface, no write/gate change), ADR-209 attribution taxonomy (rendered, not changed), ADR-286 single-writer-per-path, the re-founding direction (D1's derive-from-FS *immunizes* the surface against the re-founding re-homing roots — see §6).
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6) — what the operator sees and how, over the substrate the other axioms own.

---

## 1. The problem (grounded in the walk)

### 1a. The systemic bug: the explorer is hardcoded, so directories go missing

The left explorer does NOT list all workspace directories. The operator's instinct — *"why aren't ALL directories visible?"* — is the correct diagnosis: it is not a per-directory gap, it is a **hardcoded root list**.

- [`files/page.tsx:420-436`](../../web/app/(authenticated)/files/page.tsx#L420-L436) fetches a **literal list of 5 roots** (`operation`, `uploads`, `system`, `persona`, `agents`).
- [`buildContextNodes()`](../../web/app/(authenticated)/files/page.tsx#L157-L272) assembles a **literal array of 7 groups** (Identity · Context · Reports · Persona · System · Agents · Uploads).
- The backend `GET /workspace/tree` ([`workspace.py:446-508`](../../api/routes/workspace.py#L446-L508)) returns *everything* under any root — **no server-side filter**. The exclusion is purely the frontend's hardcoded list.

Live DB receipts (distinct top-level paths under `/workspace/`):

| root | files | in the explorer today? |
|---|---|---|
| `persona/` | 18 | ✅ |
| `system/` | 10 | ✅ |
| `constitution/` | 6 | ❌ **invisible** (MANDATE, PRECEDENT) |
| `governance/` | 3 | ❌ **invisible** (AUTONOMY, _budget, _autonomy) |
| `operation/` | 3 | ✅ (as "Context") |
| `inbound/` | 2 | ❌ **invisible** (the ADR-376 MCP intake lane) |
| `agents/`, `uploads/` | 0 | (empty) |

Three roots are unreachable from the UI. The group labels (Identity/Context/Reports) are a **synthetic curation** that doesn't even map 1:1 to the real ADR-320 roots — "Identity" is 5 hand-picked files scattered across `persona/`+`operation/`+`system/`.

### 1b. The 404 is a *consequence* of 1a, not a separate bug

`/desktop?files.path=/workspace/inbound/mcp/chatgpt/yarnnn-memory-test.md` → 404. The file-load endpoint ([`workspace.py:515-585`](../../api/routes/workspace.py#L515-L585)) normalizes and queries correctly; the 404 means no row exists at that *exact* path (the slug typed ≠ the slug written). The operator only hit it by hand-typing a deep-link **because `inbound/` has no tree node to click** — the synthetic-node-for-typed-path fallback let an arbitrary path through to a load that missed. **Fixing the tree (D1) dissolves this**: `inbound/`'s real files become clickable and resolve; nobody hand-types a path that wasn't written.

### 1c. Five fragmented display surfaces, no shared design language

The surface has five file-display components, each rolling its own icon set, attribution rendering, and metadata:

| Surface | Component | View | Attribution shown |
|---|---|---|---|
| Recents | `RecentsView` | icon grid + list (toggle, Recents-only) | color dot + label |
| Folder listing | `DirectoryView` (in `ContentViewer`) | fixed details table | **none** |
| File viewer | `FileView` (in `ContentViewer`) | prose | head author in header |
| Tree | `WorkspaceTree`/`TreeItem` | outline | author shorthand on edge |
| Details | `NodeDetailsPanel` | inline collapsible | dot + label + message (folders only) |

The "confusing dots" are **author-identity glyphs** (ADR-209: primary=You, rose=Reviewer, sky=YARNNN, muted=system) — unlabeled color, which is the *right data rendered illegibly*. The grid/list toggle is `RecentsView`-local by design. Folder listings show **no author at all**.

### 1d. The interop-wedge story is invisible where it matters most

YARNNN's moat is **durable attributed memory** — *who wrote each version, traceably* (ADR-209 + the `trace` MCP verb). The Files surface is exactly where an operator should *see* that: open a file, see its revision chain — operator wrote v1, ChatGPT-via-MCP appended v2, the seat reconciled v3. That data is fully available (`GET /workspace/revisions?path=`) but is **not surfaced in the file viewer's details** (it renders for folders only; for files it's behind a side panel that only appears when Details is open). The operator's "no new data, just better display" is precisely correct.

## 2. Decisions

### D1 — The explorer tree is DERIVED from the filesystem (filesystem-literal)

The tree mirrors the real FS 1:1 — no synthetic cross-root groups. The explorer lists **whatever roots actually exist** under `/workspace/`, each with a friendly label/icon, children lazy-loaded per root.

- **New endpoint** `GET /workspace/roots` — one `SELECT DISTINCT split_part(...)` query returning `[{name, path, file_count, exists}]` for every depth-1 directory (plus the canonical-but-empty roots so `agents/`/`uploads/` show as creatable). Cheap; no 500-row subtree burden.
- **New source of truth** `WORKSPACE_ROOTS` (extends [`workspace_paths.py`](../../api/services/workspace_paths.py)) — maps each root → `{display_name, semantic_class, description, icon}`. Backend (already owns the `*_ROOT` constants) and frontend share it; no duplication. Known roots get friendly names (`constitution/`→"Constitution", `inbound/`→"Intake", etc.); an **unknown/new root still renders** with its raw name.
- `buildContextNodes`'s literal 7-group array is **deleted**. The tree is `roots.map(buildGroup)`.
- The `operation/` domains (the old "Context" group) + `reports/` (recurrence outputs) remain as *children* under the `operation/` root node, derived as today — but nested under the real root, not lifted into top-level synthetic groups.

**This is the root-cause kill**: a derived tree cannot go stale. The ADR-320 roots, the ADR-376 `inbound/` lane, and any future root (the re-founding will add/rename some — §6) all appear with zero code change.

### D2 — One file-row design language (Finder/Explorer-native)

Extract a single shared presentational component — `FileRow` (list) + `FileTile` (grid) — consumed by Recents, folder listings (`DirectoryView`), and the details modal's revision list. One icon set (file-type-aware, macOS-Finder-faithful), one attribution rendering, one metadata shape. Kills the five-surface fragmentation. The tree keeps its compact outline form but draws icons/attribution from the same primitives.

### D3 — Attribution made legible (no new data)

The bare color dots become a proper author affordance: **glyph + readable label** ("You", "Reviewer", "ChatGPT via MCP", "System") sourced from the existing ADR-209 `authored_by` taxonomy. Every file-row (including folder listings, which show none today) carries author + when. This is the interop-wedge made visible at a glance.

### D4 — View mode is Files-surface-wide

The grid/list toggle moves from `RecentsView`-local state to a **Files-surface preference** (one localStorage key, the Finder model). Folder listings honor it (currently a fixed table). Recents, folder listings, and search results all respond to one toggle.

### D5 — Details via right-click → a Get-Info modal with the revision chain

- The inline "Details" button is replaced by a **context menu** (right-click on any file/folder row or tile) → "Get Info".
- Get Info opens a **modal** (not the current inline collapsible) — the macOS Get-Info / Explorer-Properties idiom — carrying: path, type, size/when, and the **full revision chain** for files (`GET /workspace/revisions?path=` — each revision's author + timestamp + message + parent pointer). The ADR-209 attribution story lives here, first-class, for files (today it's folders-only).
- Revert/diff (the existing `RevisionHistoryPanel` affordances) fold into the modal.

### D6 — The 404 resolves via D1

No separate fix. Once `inbound/` is a real tree node, its files are reachable by click and resolve correctly; the synthetic-node fallback stops being load-bearing. (If a genuinely-missing path is deep-linked, the viewer shows an honest "this file no longer exists at this path" empty state rather than a raw "API Error: 404".)

## 3. What this does NOT do

- **No write-path / gate / lock change.** Files stays a read+navigate surface; the ADR-320 lock model is untouched. (Showing `governance/`/`constitution/` does not make them operator-writable from here — that's the gate's job, unchanged.)
- **No schema, no primitive.** One new *read* endpoint (`GET /workspace/roots`); revisions/tree/file endpoints already exist.
- **No new attribution data.** D3/D5 render the ADR-209 chain that's already stored and already fetchable.
- **Does not pre-empt the re-founding.** D1 is forward-compatible by construction (§6); it does not encode any specific root set.

## 4. Rejected / deferred

- **"Add the 3 missing fetches" (minimal patch).** Rejected — fixes today, re-breaks on the next new root (the re-founding will add some). Derive-from-FS is the systemic cure (operator's explicit choice).
- **Keep the synthetic Identity/Context/Reports curation.** Rejected — filesystem-literal is more coherent and aligns with the re-founding's meaning-folders thesis (what the substrate *is* = what the operator *sees*). Operator decision.
- **`getTree('/workspace')` for the spine.** Rejected for the root list — heavy (500-row cap, full subtree). A dedicated cheap `GET /workspace/roots` is the right shape; subtrees lazy-load per root.
- **Backfilling `SETTINGS_FILES` to include constitution/governance.** Not needed — those roots get their own top-level nodes under D1; the curated "settings" list is retired with the synthetic groups.

## 5. Cascade / blast radius

- **Backend**: `api/services/workspace_paths.py` (new `WORKSPACE_ROOTS` map); `api/routes/workspace.py` (new `GET /workspace/roots`). `_build_tree` / `getTree` unchanged (still used for per-root subtrees).
- **Frontend**: `web/app/(authenticated)/files/page.tsx` (delete hardcoded fetch list + `buildContextNodes` literal array → derive from `roots`); new shared `FileRow`/`FileTile` (D2); `RecentsView` (toggle → surface pref, consume shared rows); `DirectoryView` in `ContentViewer` (consume shared rows + honor view-mode + show attribution); `WorkspaceTree`/`TreeItem` (draw from shared icon/attribution primitives); `NodeDetailsPanel` → Get-Info **modal** + right-click context menu (D5); an author-label helper (glyph + readable label) shared by all rows (D3); a Files-surface view-mode store (D4).
- **Canon**: GLOSSARY (Files surface entry if it names the synthetic groups); CLAUDE.md only if a reference names the old group labels.
- **Gate**: `api/test_adr388_files_surface.py` — assert the tree derives from roots (no hardcoded root array), all live roots present (constitution/governance/inbound), shared file-row used across surfaces, view-mode surface-wide, revision chain in the details modal. `tsc --noEmit`.

## 6. Why this is forward-compatible with the re-founding

The re-founding (filesystem-by-meaning; `docs/analysis/the-re-founding-meaning-folders-and-permission-as-metadata-2026-06-29.md`) may **re-home or rename roots** (it reconsiders the six semantic-class roots + the `inbound/` lane). A *hardcoded* tree would have to be re-edited every time that lands. A **derived** tree (D1) simply renders whatever roots exist after each re-founding phase — the explorer follows the substrate automatically. The `WORKSPACE_ROOTS` label map is the only thing to touch when a root is renamed, and an un-mapped root still shows (raw name). So this ADR is not racing the re-founding; it makes the Files surface *correct by construction* across it. This is the deep reason filesystem-literal (D1) is the right call now rather than after the re-founding settles.

## 7. Sequencing (doc-first)

1. This ADR (sign-off).
2. `WORKSPACE_ROOTS` map + `GET /workspace/roots` endpoint (the spine).
3. Derive the explorer tree (D1) — directories visible, 404 dissolves (D6). *This alone fixes the broken surface; independently shippable.*
4. The coherence pass: shared `FileRow`/`FileTile` (D2) + legible attribution (D3) + surface-wide view-mode (D4) + right-click Get-Info modal with revision chain (D5).
5. Gate (`api/test_adr388_files_surface.py`) + `tsc --noEmit` + operator browser walk.
