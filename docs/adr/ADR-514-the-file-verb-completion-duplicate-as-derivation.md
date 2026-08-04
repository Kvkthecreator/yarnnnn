# ADR-514: The File-Verb Completion — Duplicate as Derivation

**Status**: **D1 Implemented** (2026-08-03, `b2d4224`; tree mount fixed `740f726` after the
click-pass) · **D2 Implemented except the override STORES** (2026-08-03 — the handler set,
the Finder grammar, Chat-as-reference-handler, and the D2.6 prop-wall removal are built and
gated, and the D2.3 cite delivery lands at the composer as of `fbf347d`; D2.4's per-FILE
store is the one remaining increment and its per-TYPE half is deliberately deferred —
see its status note).
D2 was re-cut on the LaunchServices model after the operator rejected the first
"intent-claim" draft: *"as close as technically and architecturally possible to existing
operating systems."* That draft is not preserved inline; its two surviving findings are
carried into D2.1 and D2.3.
**Date**: 2026-08-03
**Dimension**: Substrate (a new kernel verb) + Channel (which app opens a file, and how it is
delivered)

**Amends**: ADR-451 (the "Open with" picker deferral RESOLVES — the second handler for `.html`
has existed since ADR-451 shipped, hidden in an if/else fallthrough rather than a registry row) ·
ADR-436 (the renderer table and the surface-app table MERGE into one ordered handler set —
LaunchServices does not distinguish pane from window) · ADR-473 D2 (the runtime-learned kind→app
binding becomes a row in that one set; program rows append and may default only for
program-introduced types) · ADR-309 (the type layer is unchanged and remains the UTI analog) ·
ADR-448 (the reference edge gains its first operator-initiated producer)
**Preserves**: ADR-400 Amendment 1 (the optimistic model — the FE offers, the backend decides) ·
ADR-209 (`write_revision` stays the single write path) · ADR-452 D5 ("Learn from" is a creation
act homed on the Studio landing, not a file operation)

**Deferred to a separate lane** (operator ruling, 2026-08-03): the **boundary acts** — Share
wiring on Files, Copy AI reference, Copy link. They are held for full discourse *after* this
ADR's items stabilize and deploy. See §6.

---

## Context — what the audit found

A 2026-08-03 audit of the Files right-click menu against the kernel's verb surface (prompted by
the operator observing that recently-developed kernel actions were not reflected in the menu)
produced a full inventory. The result was better than feared in one direction and worse in
another.

**Healthy — genuinely singular implementations:**

- Rename / Move / Trash: `useFileOrganizeVerbs` is one hook, called by both the Files page and
  the Studio surface. The "SAME shared implementation" claim in its header was *tested*, not
  trusted, and it holds — a fix to the rename path reaches both surfaces.
- `FileContextMenu` + the `FileVerbs` bundle: one menu, four mount sites (left tree, RecentsView
  grid, ContentViewer listing, Studio recents).
- Properties: `PropertiesModal` wraps `NodeDetailsPanel`, which carries the ADR-512 D6 reach rows
  ("Who can reach this") and per-file share management. This DID land on Files.

**The pattern of failure:** verbs *born in Files* were properly shared. Verbs *born in Studio*
were authored as local callbacks inside `StudioSurface.tsx` and never lifted into the seam. Four
verbs sit in that class. Three of them (the boundary acts) are deferred by §6. The fourth —
**duplicate** — turns out not to have a kernel to be lifted *to*.

### The duplicate finding

`StudioSurface.tsx::duplicateArtifact` is a client-side re-implementation of a verb the kernel
does not have. There is no `DuplicateFile` primitive in `services/primitives/registry.py`; there
is no duplicate/copy route. The browser-side implementation:

1. Probes `getFile` up to five times looking for a free `-copy` suffix — a TOCTOU race (two
   duplicates in flight both see the same suffix free), and a hard cap at five copies.
2. Is `.html`-only by construction (`artifactPath.replace(/\.html$/, '')`), so it structurally
   cannot duplicate `_watch.yaml`, a `.md`, or an upload.
3. **Passes no `derived_from`** — so every duplicate made to date is an attribution orphan. The
   ADR-448 reference edge exists precisely to record "this content was made from that content,"
   and the one operator gesture that is *definitionally* a derivation does not use it.

Point 3 is the load-bearing one. Under FOUNDATIONS' attribution axiom, a file that came from
another file and does not say so is a hole in the record — not a missing convenience.

---

## D1 — `DuplicateFile` becomes a kernel primitive

A new primitive in the registry. **Duplicate, not copy** — the name is chosen against three
existing meanings of "copy" in this codebase (`copyLink`, `copyAiRef`, and the block-clipboard
`onCopy` in `StudioBlockMenu`), all of which mean *put a reference on the clipboard*. A fourth
"Copy" meaning *write a new attributed file* would collide. "Duplicate" also names the truth:
under ADR-209 a file is a revision chain, and the new file is a **derivation with an attributed
parent**, not a byte-identical clone with no lineage.

Contract:

- **Server-side suffix resolution.** The kernel picks the free name in one query against
  `workspace_files`, not an N-round client probe. No arbitrary cap.
- **Format-agnostic.** Operates on the path's extension generically, whatever it is. `_watch.yaml`
  duplicates to `_watch-copy.yaml`.
- **Writes `derived_from`.** The new revision records its parent path per ADR-448, so `trace` on
  the duplicate walks back to the original. This is the correctness fix, not a feature.
- **Goes through `write_revision`.** No second write door (ADR-209). The ADR-320 caller-class
  lock-set applies unchanged — a duplicate into a locked root is refused like any other write.
- **Attribution is the acting principal**, via the ADR-288 path — a duplicate is an authored act,
  not a system act.

`StudioSurface.tsx::duplicateArtifact` is **deleted**, not left alongside (Singular
Implementation). Studio's File card calls the shared verb like every other surface.

Open question for implementation (not blocking ratification): whether duplicating a *folder* is
in scope. Recommendation: **no** for v1 — a folder duplicate is a recursive multi-write with its
own failure semantics, and no observed demand. Files-only, stated as a limit.

## D2 — Open, Open With, and the handler set (the LaunchServices cut)

**Ratified framing (operator, 2026-08-03): "as close as technically and architecturally
possible to existing operating systems."** The first draft of D2 invented a claim taxonomy
(apps declare an `edit`/`reason`/`observe` *intent*). That was rejected as un-OS-like, and
rightly: **macOS has no such vocabulary.** Word, Pages and TextEdit do not declare intents
toward a `.docx` — each is *registered as a handler for the type*, the set is ordered, and one
is marked `(default)`. The concept is LaunchServices, and the vocabulary is: **type → handler
set → default binding.**

### D2.1 — The three layers already exist; only the middle one is degenerate

| LaunchServices | yarnnn today | State |
|---|---|---|
| **UTI** — what type is this? | `resolveViewerApplication` (path + content-type → 9 kinds, 3-tier fallback with a terminal) | Complete. Its own header already cites "macOS UTI + default-application binding." |
| **Handler set** — who can open it? | `resolveApps` returns an ordered list — but `APPS_BY_TYPE` is built so every type has exactly ONE row; and a SECOND, separate table (`resolveSurfaceApplication`) holds the surface-owning apps | **Degenerate.** The shape is right, the set is always a singleton, and it is split across two tables. |
| **Default binding** — which one wins? | `resolveApps[0]` / `DEFAULT_ARTIFACT_APP` | Implicit but correct — first wins. |

The gap is not a missing concept. It is that **the two registries are the same layer wearing
two coats**: `resolveApps` (in-frame renderers) and `resolveSurfaceApplication` (surface-owning
apps — Studio, Images, Radar). LaunchServices does not distinguish "opens in a pane" from
"opens in a window"; how a handler presents itself is the handler's business, not the
registry's.

Proof the split is already under strain: the Files open path
(`files/page.tsx::openPath`) asks `resolveSurfaceApplication` first and falls through to the
inline viewer when nothing claims the file. **That fallthrough IS a two-entry handler set,
hardcoded as an if/else.** An `.html` artifact genuinely has two handlers today — Studio (the
authoring surface) and the web viewer (the Quick Look render). ADR-451 D3 deferred the picker
"until a second app claims the same format"; that condition has been met since ADR-451 shipped.
It was invisible because the alternative lived in an else-branch instead of a registry row.

### D2.2 — One handler set, ordered, first is default

The two tables merge into ONE lookup:

```
resolveHandlers(path, contentType, kind?) -> Handler[]     // ordered; [0] is the default
```

A `Handler` row carries: `id`, the types it claims, an operator-readable `label`, how it opens
(in-frame renderer vs. surface navigation), and its rank. Merging the *table* does not merge
the *callers*: `FileBody` asks for the in-frame handler, Files asks for the default handler.
**One table, two queries** — no mount re-derives a type, which is ADR-309's standing rule.

- **`Open`** fires `handlers[0]`. Byte-identical to today for every single-handler file.
- **`Open With ›`** is a SUBMENU, rendered iff `handlers.length > 1`, listing every handler with
  `(default)` marked on the first — the Finder grammar exactly.

`Open` therefore keeps working with no picker in sight; `Open With` is pure secondary
optionality. This is the whole of the operator's instruction.

### D2.3 — Chat IS a handler; its HANDLING is reference, not render

Chat stays in Open With. The user-experience reading is decisive: **Chat is an app you pick to
open something with**, and demoting it to some separate "Send to…" verb would be a taxonomy the
OS does not have — the same mistake the rejected draft made, one layer down.

What differs is not whether Chat is a handler but **what opening means for it.** The registry
gains ONE axis, and it is mechanical, not semantic:

| Delivery | Meaning | Handlers |
|---|---|---|
| `document` | the handler takes custody of the file and opens it as its subject | Studio, Images, Radar, the in-frame viewers |
| `reference` | the handler receives the file as *cited material*, not as its subject | Chat |

This is a statement about **how the file is delivered to the app**, which is exactly what
LaunchServices itself encodes (open-document vs. open-in-place vs. the print/service verbs
sharing a registry). It is not a claim about the app's inner relationship to the content.

The distinction earns its keep by answering questions `document` cannot:

- **Multi-select.** `document` delivery is single-subject: opening five files in Studio means
  five documents. `reference` delivery is naturally plural — five files become five citations
  in one turn. Open With on a multi-selection therefore lists only handlers that accept the
  selection's cardinality.
- **Folders.** A folder has no `document` handler (nothing "opens" a directory as a subject
  except the Finder itself). It DOES have a `reference` handler: "Open with Chat" on a folder
  cites the folder — its listing, and its members as reachable context. This is the first
  coherent answer to what right-clicking a folder should offer beyond navigation.
- **No receiving contract needed.** `navigateToSurface('chat')` takes no file param, and the
  earlier draft treated that as a blocker. Under `reference` delivery it is not: the delivery
  mechanism is the ADR-512 D6 **bind** that already shipped (a chip referencing the existing
  path — no upload, no copy). Chat receives citations, and it already knows how.

So: one registry, one ordering, one `(default)`. `document` vs `reference` is a property of the
row that governs delivery and cardinality — never a taxonomy of relationships the operator has
to learn.

### D2.4 — The per-file default override

> **Status (2026-08-03), AMENDED — the per-TYPE scope is DEFERRED.** Operator ruling:
> *"deliberately defer implementing per workspace configuration and for now just focus
> on hardening and verifying the open with and thus file defaults."*
>
> So the override has exactly ONE scope: **per-file, stored on the file itself.** That
> is the more file-native shape regardless — a default that lives in workspace-wide
> config is a preferences system; a default that lives on the file travels with it, is
> visible in Get Info beside everything else about that file, and needs no reconciliation
> when the file moves.
>
> - **BUILT + GATED:** the resolution algebra (`applyDefaultOverride`, executed in
>   `__gate_adr514_d2.mjs` checks 1a–1f) including the stale-override fallthrough.
> - **DEFERRED (not "next increment"):** `/workspace/_launch.yaml` per-type config. It
>   stays specified below so the shape is on record, but nothing should build it until
>   a real case demands a default that spans files.
> - **OWED, the remaining increment:** the per-FILE store —
>   `workspace_files.metadata.launch.handler`, a metadata write endpoint (none exists
>   today; the metadata column is read-only from the FE), and the Get Info "Open with:"
>   affordance. Until then the algebra is a no-op awaiting input, and the registry rank
>   is the default for every file.
>
> Resolution order collapses accordingly to **per-file → registry rank**. The
> three-level form below is retained as the shape a future per-type scope would slot
> into without changing the contract.

macOS binds a default at two scopes: per-type (Get Info → "Change All…") and per-file (Get Info
→ "Open with:"). yarnnn should mirror both, and the storage follows the existing conventions
rather than inventing a table.

- **Per-file** override lives on the file's own metadata — the `workspace_files.metadata`
  jsonb, keyed `launch.handler`. It travels with the file through move/rename (metadata rides
  the row), it is per-workspace by construction, and it needs no migration.
- **Per-type** override is workspace configuration, so it belongs in the machine-parsed lane as
  `/workspace/_launch.yaml` (ADR-254: underscore prefix = machine-parsed, `yaml.safe_load`),
  a flat `type → handler_id` map. Operator/agent-editable like any other `_*.yaml`.
- **Resolution order** is the OS one, most-specific first: per-file override → per-type override
  → registry rank. A missing or unknown handler id **falls through silently** to the next level;
  a stale override must never make a file unopenable. This is the same terminal-fallback
  discipline ADR-309 already applies to types.
- **Surfacing** is Get Info, not a new panel — `NodeDetailsPanel` is already the Finder Get Info
  (ADR-329/400) and already carries reach and share rows.

**Deliberately deferred inside D2.4:** the "Change All…" bulk apply (write the per-type row from
a per-file choice) — the storage supports it; the affordance waits for demand.

### D2.5 — What programs may claim

`registerKindApps` (ADR-473 D2) already lets a program bind its document type to an app at
runtime, so program rows join the handler set for their type. The kernel boundary holds as:
**a program row APPENDS to the handler set and may take default only for a type the program
itself introduced.** A program cannot displace a kernel app as the default for a kernel type.
This keeps ADR-436's one-file ratchet meaningful — programs add rows, never re-rank the kernel.

### D2.6 — The prop-wall lesson (structural, and load-bearing)

The 2026-08-03 click-pass found Duplicate missing from the Files tree because `WorkspaceTree`
takes a **hand-listed prop subset** (`onGetInfo/onRename/onMove/onDelete`) rather than the
`FileVerbs` bundle — so a verb wired everywhere else silently skipped one mount, and the commit
message over-claimed the blast radius. `Share…` is STILL missing from the tree for the same
reason.

Open With makes this worse if left alone: it is not one verb but a *variable-length submenu*,
and a prop wall cannot carry it. **D2 therefore requires `WorkspaceTree` (and any other
hand-listing mount) to accept the `FileVerbs` bundle whole.** This is not scope creep — it is
the precondition that stops the next verb repeating the same defect.

> **Amendment (2026-08-04) — the spread was half the fix; the hook is the whole one.** The
> bundle-whole cut shipped as a raw `{...verbs}` spread into the menu component, and the third
> recurrence of the class arrived immediately: `FileVerbs` carries `handlersFor` (a function)
> while the menu takes `handlers` (the resolved array), and only `useFileContextMenu` performs
> that translation — so **Open With ▸ never rendered in the tree** while working in the grid and
> Recents (an audit finding, 2026-08-04). The corrected invariant: **every mount goes through
> the shared `useFileContextMenu` hook; nothing but the hook renders `<FileContextMenu>`
> directly.** The tree's local open-state machine is deleted; the gate now asserts hook-usage
> per mount, the singular JSX mount site by enumeration, and the translation line itself
> (`__gate_adr514_d2.mjs` 4b/4b2/4b3). The same pass made the open FILE a mount too (4b4):
> right-clicking the file you just opened offers its own verbs instead of bubbling to the
> canvas menu — previously the focused object was the only context on the surface with no menu
> at all, the inverse of the Finder. And the menu gained its first folder-scoped verb, **New
> Folder** (create inside the target — the Explorer "New > Folder" grammar; gate section 5),
> with the destination stated in the modal and the parent travelling verbatim in its own
> request field so existing path segments are never re-sanitized en route
> (`create_folder.parent`, ADR-424 lane).

### D2.7 — What is deliberately NOT built

- **No "App Store…" / "Other…" rows.** Both presuppose installable third-party apps; the
  one-file ratchet stays red until an App(principal) ADR flips it.
- **No new relationship vocabulary.** `document`/`reference` is a delivery axis, and it is
  closed at two values until a real third case appears.
- **No bulk "Change All…" affordance** (D2.4).
- **No folder `document` handler** — folders get `reference` handlers only.

## D3 — What is deliberately NOT built (ADR-wide)

Per-decision exclusions live with their decision (D1's folder-duplicate limit, D2.7's
Open-With exclusions). ADR-wide:

- **No third-party app rows.** The one-file ratchet (`apps.tsx` header) stays red until an
  App(principal) ADR flips it. D2 widens the row's *shape* and merges two tables; it does not
  change who may write rows.
- **The boundary acts** — see §6.

---

## §6 — The deferred lane: the boundary acts

Held by operator ruling (2026-08-03) for full discourse after this ADR's items stabilize and
deploy. Recorded here so the deferral is deliberate and the findings are not lost:

1. **Share wiring on Files.** The two-shape share sheet EXISTS and is correct
   (`StudioShareExport` — Full access / View-only, with honest per-mode consequence copy, landed
   at `d0a8b10`). The defect is that Files' right-click Share… does **not** route to it: it calls
   `createShare(path, name)` with no role, so it silently mints a **full-access member grant** and
   copies. ADR-465 D3's premise is that "just look at this" must never over-grant; the one surface
   reachable by right-click always over-grants. **This is a live over-grant defect, not a polish
   item** — it should be weighed accordingly when the lane opens.
   - Note for that discourse: the sheet currently lives in `StudioShareExport` beside Export
     (Print/PDF, PNG — Studio-specific). Lifting Share means extracting the sheet and leaving
     Export behind.
   - Note on gates: `test_adr465_share_as_view.py` check 5b ("client sends role on createShare")
     passes today because it inspects the *client function* and Studio's caller. It cannot see the
     Files caller. A per-site enumeration gate is owed —
     the counting-gate-cannot-defend-a-per-site-invariant class.
2. **Copy AI reference** (the `yarnnn://workspace/…` handle, ADR-512 D5) — exists only in Studio
   (`copyAiReference`). Files has no way to hand a file to an outside AI, which is the primary
   interop gesture.
3. **Copy link** (the in-app member deep-link) — same shape, Studio-only.

All three are *wiring* gaps over shipped, correct implementations. None needs a new kernel verb.

---

## Consequences

**D1 (done):**
- One new kernel primitive (`DuplicateFile`), two deleted client-side re-implementations.
- Every duplicate from ratification forward records its parent; **existing duplicates stay
  orphaned** (no backfill — the origin was never captured and cannot be inferred).

**D2 (accepted, unbuilt):**
- Two registries become one ordered handler set; `Open` fires `handlers[0]` — byte-identical for
  every single-handler file, which is most of them.
- `Open With ›` appears on `.html` immediately (Studio + web viewer), with no new app installed:
  ADR-451's deferral condition was already met, hidden in a fallthrough.
- Chat becomes a listed handler with `reference` delivery — which is also what makes Open With
  answerable for **multi-selections and folders**, neither of which has a `document` handler.
- Get Info gains the per-file "Open with:" binding; `/workspace/_launch.yaml` carries per-type.
- `WorkspaceTree` must take the `FileVerbs` bundle whole (D2.6) — the precondition, not an extra.

## Gates owed

**D1 — landed** (`test_adr514_duplicate_verb.py`, 21/21, falsified against a removed
`derived_from`): format-agnostic, edge written, server-side suffix, lock-set refusal, and no
surviving client-side implementation.

**D2 — owed, and they must EXECUTE, not count:**
- Resolution order, run as a table: per-file override → per-type override → registry rank, with
  an **unknown handler id falling through** rather than making a file unopenable.
- `handlers.length > 1` ⇒ the submenu renders with exactly one `(default)`; `== 1` ⇒ no submenu.
- Cardinality: a multi-selection offers only handlers that accept it; a folder offers `reference`
  handlers only and no `document` handler.
- **Per-mount, not per-count** (the D2.6 lesson): assert Open With is reachable from EVERY file
  mount — tree, grid, folder listing, Studio recents. A counting gate cannot see one mount
  missing a prop; that is precisely how Duplicate shipped absent from the tree
  (`feedback_counting_gate_cannot_defend_per_site`).
