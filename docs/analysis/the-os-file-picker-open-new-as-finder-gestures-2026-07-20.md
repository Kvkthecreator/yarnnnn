# The OS File Picker — Open & New as Finder Gestures

**Date**: 2026-07-20
**Status**: Design consideration, doc-first (operator-requested). Implementation gated on sign-off.
**Dimension**: Channel (which chrome a file operation opens in) — one shared picker across surfaces.
**Origin**: Operator observation on the Studio Open / New modals — "shouldn't our Open/Find modals
actually be a Finder-like consideration, identical across scenarios? And New shouldn't ask for a
name + typed path — it should follow the OS metaphor: name it, then navigate to a destination the
way Finder's Save dialog does."

---

## 1. The observation, restated

The operator screenshotted three things side by side:

1. **Studio → New document** — a modal with a name field **and a `operation/…/artifact.html`
   font-mono path field** the operator types into.
2. **Studio → Open…** — a modal with a **tree picker** ("Pick something you've made").
3. **macOS Finder Open dialog** — the reference: a sidebar of locations + a navigable file list;
   you never type a path.

The claim: (a) our Open/Find modals should be **one Finder-like picker reused everywhere** for
cross-scenario familiarity, and (b) New should stop asking for a typed path and instead follow the
OS metaphor — name it, pick a destination folder in the same picker, optionally treat it as a
temporary file until saved.

Both are correct against our own canon. The codebase already half-agrees with itself — it just
hasn't finished the thought.

## 2. What exists today (receipts)

| Modal | File | Role | Grammar |
|---|---|---|---|
| `OpenArtifactModal` | `web/components/studio/OpenArtifactModal.tsx` | **pick a FILE** to open | portal + `Z_CONFIRM_*` + recursive `PickerRow`, lazy tree fetch, prune-empty-branches, `resolveSurfaceApplication` filter |
| `MoveToFolderModal` | `web/components/workspace/MoveToFolderModal.tsx` | **pick a FOLDER** to move into | portal + `Z_CONFIRM_*` + recursive `FolderRow`, `canOrganize` predicate, disable-current-parent |
| `NewArtifactModal` | `web/components/studio/NewArtifactModal.tsx` | name + **typed path** | plain inputs; path defaults to `operation/{slug}/{template}.html`, operator can edit the raw string |
| `FileOpenModal` | `web/components/chat-surface/FileOpenModal.tsx` | **render** one known file in a chat frame | NOT a picker — a renderer overlay (ADR-436 §7). Out of scope. |

Two observations fall straight out of this:

**(a) The two tree-pickers are the same component wearing two hats.** `OpenArtifactModal`'s own
header comment already argues this out loud:

> "the member picks their work from a tree, the way an OS Open dialog works … a sibling of
> `MoveToFolderModal`, deliberately mirroring its portal + z-tier + row structure rather than
> inventing a second modal grammar. The inversion vs. Move: Move picks a FOLDER and hides files;
> Open picks a FILE and shows folders only as the path to one."

So the model is already ratified — Open and Move are the **same picker, one axis of variation**
(what's selectable: a file vs. a folder; what's filtered: Studio-openable vs. organize-into-able).
But they are **two hand-rolled copies**, not one component. That is the Singular-Implementation
smell CLAUDE.md §2 exists to catch: `createPortal` + z-tiers + the recursive row + the lazy fetch
+ prune-empty-branches logic is written twice, and will be written a third time the next time a
surface needs "pick a file/folder."

**(b) New still asks for a typed path — the exact gesture we already banned.** ADR-400 Q2 killed
raw-path typing for Move ("move to shouldn't be a URL path input; users will find that
confusing") and `MoveToFolderModal` is the *fix* for it. Yet `NewArtifactModal` re-introduces the
same font-mono `operation/…/artifact.html` input one ADR later. New is inconsistent with its own
sibling Open, and with the ruling that produced Move's picker.

## 3. The macOS truth the operator is invoking

In Finder there are exactly two file-location gestures, and both are the **same navigable view**:

- **Open** — navigate to a file, select it, open. (Our `OpenArtifactModal`.)
- **Save As / New** — type a *name*, navigate to a *destination folder*, save. You **never type a
  path**; the path is composed from `{picked folder}/{name}`.

We already have the Open half and the folder-navigation half (Move). We are missing only the
**composition**: New = `[name] + [folder picked in the same tree]`, path assembled for the
operator, never typed.

This is the DP29 "mirror once, compose few" model (ADR-340) applied to a widget instead of a
surface: **one picker primitive, composed into three operator acts** (open a file, move into a
folder, place a new file), rather than three bespoke modals.

## 4. The proposal — two moves, both pure-FE

### Move A — Extract one `<WorkspacePicker>` primitive

A single component both existing pickers configure, rather than two copies:

```
<WorkspacePicker
  mode="file" | "folder"          // what a leaf row IS — selectable file, or navigate-only
  selectable={(node) => boolean}  // Open: isOpenable (resolveSurfaceApplication==studio)
                                  // Move: canOrganize + not-current-parent
  emptyState={string}            // "Nothing to open yet" | "Pick a destination folder"
  onPick={(path) => void}
/>
```

The variation between Open and Move is **data, not grammar** — the selectable predicate, the leaf
mode, the empty copy. Everything structural (portal, z-tier, recursive rows, lazy `getRoots` +
`getTree`, prune-empty-branches, chevron expand/collapse, ADR-459 meaning-folder naming) is written
**once**. `OpenArtifactModal` and `MoveToFolderModal` become thin configurations of it.

Precedent for "same shell, configured": the two modals *already* deliberately mirror each other by
hand — this move just makes the mirror a symlink.

**This is a collapse, not an addition (operator directive, 2026-07-20).** The duplicated grammar is
DELETED, not left beside the new component. Concretely, when Move A lands there must be exactly
**one** recursive tree-row component and **one** picker shell in the tree; `PickerRow` (in
`OpenArtifactModal`) and `FolderRow` (in `MoveToFolderModal`) both cease to exist as independent
implementations — their bodies move into `WorkspacePicker` and the old copies are removed in the
same commit. Per CLAUDE.md §2 (Singular Implementation): no parallel implementations, no
"OpenArtifactModal keeps its own row for now" shim. If a caller still imports a deleted symbol after
the collapse, that is the defect the collapse exists to prevent. The success test is a `grep`: after
the change, `createPortal` + a hand-rolled recursive folder row appears in the workspace-picker
component and **nowhere else** for these three acts.

### Deletion ledger (what gets removed, not just refactored)

| Removed | From | Replaced by |
|---|---|---|
| `PickerRow` fn + its portal/shell | `studio/OpenArtifactModal.tsx` | `WorkspacePicker` (file-mode) |
| `FolderRow` fn + its portal/shell | `workspace/MoveToFolderModal.tsx` | `WorkspacePicker` (folder-mode) |
| the font-mono path `<input>` + `pathEdited` state | `studio/NewArtifactModal.tsx` | folder-picker destination (Move B) |

`OpenArtifactModal` / `MoveToFolderModal` remain as **named entry points** (they carry the
act-specific copy, the `onOpen`/`onMove` callback shape, and the surface each lives on) but shrink
to a header + a `<WorkspacePicker …/>` + a footer — no tree logic of their own. If either shrinks to
literally nothing but a pass-through, collapse it into the call site rather than keeping an empty
wrapper.

### Move B — New names, then picks a destination folder

`NewArtifactModal` loses the font-mono path field. It becomes:

```
New {type}
  [ Name it (e.g. IR deck v3) ]
  Destination:  [ operation/…  ▸ ]   ← opens WorkspacePicker in folder-mode
  ────────────────────────────────
  Cancel   + Create
```

- The **default destination** stays `operation/` (ADR-440 D6 — the Studio never invents an
  app-named root; work lives under `operation/`), pre-selected so the fast path is still one field
  + Enter.
- The **path is composed server-visibly** as `{picked folder}/{slug(name)}/{template}.html` — the
  operator sees a meaning-placed *destination*, never edits a raw string.
- The advanced escape hatch (type the exact path) can survive as a collapsed "advanced" affordance
  if we want it, but it is no longer the primary gesture.

Both moves are frontend-only. No substrate change: New still calls `api.studio.createArtifact(path,
templateSlug)` exactly as today — it just assembles `path` from a picked folder instead of a typed
string.

## 5. What this deliberately does NOT build — the temp-file lifecycle

The operator floated a deeper version: an **untitled scratch file that lives nowhere until you
Save-As** into the Finder — the true macOS "unsaved document" state.

This is a **substrate decision, not a modal decision**, and it collides with the moat floor:

- Every file today is a real attributed `write_revision` from the moment it exists (ADR-209
  authored substrate; ADR-286 single-writer-per-path). There is **no orphan / draft / unsaved
  state** in the filesystem — by design, because "every mutation is attributed and retained" is the
  moat's floor.
- A true untitled-until-saved lifecycle introduces a draft object that exists outside the
  attributed ledger, then gets "committed" on Save-As. That is a new lifecycle the substrate does
  not model, and it would need its own ADR weighing it against Axiom 1 (everything reconstructable
  from attributed state).

**Recommendation:** ship Move A + Move B first. The folder-picker gives ~90% of the OS feel (you
name it, you navigate to where it goes) **without** the draft-state cost. If, after living with the
folder-picker, the true untitled-until-saved model is still wanted, it gets its own ADR — because
the question it raises ("can a file exist un-attributed, even briefly?") is a kernel question, not
a Studio one.

## 6. Scope & sequencing

One commit (A1–A3 are a single collapse — extracting the primitive and deleting the two copies must
land together, or there is a window with three implementations):

| Step | Change | Files | Risk |
|---|---|---|---|
| A1 | Add `WorkspacePicker` primitive (the merged shell + recursive row) | new `web/components/workspace/WorkspacePicker.tsx` | low |
| A2 | Collapse `OpenArtifactModal` onto it, **delete `PickerRow`** | `studio/OpenArtifactModal.tsx` | low |
| A3 | Collapse `MoveToFolderModal` onto it, **delete `FolderRow`** | `workspace/MoveToFolderModal.tsx` | low — verify drag-and-drop path untouched (Move's modal is the a11y/deliberate path; drag stays direct, it does not go through this modal) |
| B1 | New = name + folder-picker, **delete the typed-path input** | `studio/NewArtifactModal.tsx` | low |
| — | (deferred) temp-file lifecycle | ADR + substrate | high — separate discourse |

**Post-collapse grep gate** (the singular-implementation check, run as verification):
- `grep -rn "createPortal" web/components/{studio,workspace}` for these picker acts → the shell
  appears only in `WorkspacePicker`.
- No dangling import of a deleted `PickerRow`/`FolderRow`.
- `NewArtifactModal` contains no `font-mono` path `<input>`.

Verify: `next build` (not just `tsc` — a dirty tree hides splits, per the standing FE-verify
lesson), then drive Open / Move / New end-to-end in the running app.

## 7. Canon touchpoints

- **Aligns with** ADR-400 Q2 (no raw-path typing — extends the Move ruling to New), ADR-451
  (`resolveSurfaceApplication` stays the openable filter — the picker asks the OS which app owns the
  type), ADR-340 DP29 (mirror once, compose few — one picker, three acts), ADR-459 (rows named by
  meaning, not `.html` storage).
- **Preserves** ADR-297 D15 (window = surface; the picker is a modal primitive, not a new window in
  the window manager — same stance `FileOpenModal` took), ADR-209/286 (no new orphan file state in
  the cheap version).
- **Does not touch** the substrate, the app registry, or the open contract's branching (ADR-438) —
  this is a widget-consolidation + one gesture correction, entirely within the Channel dimension.
