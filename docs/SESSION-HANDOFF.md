# Session handoff — 2026-08-12 (the arrival + organisation arc, ADR-549 · 552 · 553 · 554 · 555)

`origin/main`. Five ADRs shipped across two arcs in one session, and the
operator's click-pass PASSED — the arc has no unverified claim left.

> **Renumbered at close.** This arc first landed as ADR-550/551; a concurrent
> lane had claimed both numbers ~2h earlier, so **mine moved to 554/555** (they
> arrived first). Two file renames + 40 citations, with the split verified per
> file: theirs live in `WorkspaceMembersCard` / `workspace-settings` /
> `review_policy`, mine in the files + authoring surface. The lesson is the
> one already in canon — *verify the ADR number AT COMMIT TIME*, not at draft
> time; I checked when drafting, before theirs existed, and never re-checked.

## 1. What landed

**Arc A — creation (ADR-549 + amendments).** Operator's receipt was
`operation/asdfadsf/document.html`: a keyboard-mash folder, permanent and
attributed. Two `+ New` rows named **one thing and a toll**.

| Commit | What |
|---|---|
| `2f516f1` | the create door offers what the server accepts; both doors disambiguate |
| `70b16f3` | the `u`-flag regex the build refused; two gates that could not go red |
| `7cbc8ec` | **ADR-549** — one door, name required, derived work lands beside its source |
| `e7746c5` | the shape-choice check was presence, not behaviour |
| `11c084c` | **D5.1** — on a paged layout the KICKER is the name-bearer |

**Arc B — arrival + organisation (ADR-554…553).** Operator asked whether Files
needs a "New" verb. The audit said **no** — Finder has none, Explorer's
`ShellNew` is a legacy wart — and that the real gap was getting things IN.

| Commit | ADR | What |
|---|---|---|
| `51a7394` | 554 | the projection follows its raw; hiding on the derive EDGE, not the lane |
| `27aea5d` | 555 | arrival gets a "here"; ONE placement law for every create/receive verb |
| `00600d3` | 552 | the grid + details list drag (closes ADR-400's named deferral) |
| `70fd2e7` | 553 | the file set — and four independent ways out |

## 2. The three findings worth carrying

1. **`upload_documents` authorized nothing.** No `operator_can_organize` at all
   — a hardcoded destination had nothing to authorize. The moment a caller can
   name one it needs a check, or ADR-549's F1 defect ships twice.
2. **Moving an upload silently detached its searchable text.** The `.extracted.md`
   projection stayed behind, still hidden, citing a dead path — in the workflow
   the system tells members to use. Two rules each correct alone (ADR-422 D2 +
   ADR-395's lane anchor) made a broken pair.
3. **An arrival is badged on the LEDGER, not by its path.** ADR-448 already said
   so verbatim in the code. That is what made `inbound/uploads/` a default
   rather than a law.

## 3. Corrections made mid-implementation (both against my own proposal)

- *"the listing already selects `content`"* — true of the uploads listing,
  **false** of the tree and recents. Switched to the path-pair form rather than
  pulling file bodies into a tree query for a cosmetic rule.
- The **de-emphasis item was dropped**: executed `fileLegibilityState` and
  `inbound/uploads/` already classifies `operator`. The audit claim was wrong,
  so nothing was changed.

## 4. OWED — nothing

The click-passes were **run by the operator and passed** (2026-08-12), covering
the drop-on-folder-row gesture, the cross-pane drag, the four multi-select
exits, the relaxed fence, Learn-from placement and the folder-name preview.
Every commit is gate-verified, build-verified **and** browser-verified.

## 5. Landmarks

- **`test_adr209` is red at HEAD** (2 banned-pattern hits: `_archive_to_history`,
  `list_history`). Pre-existing, confirmed by stash — another lane's.
- **One placement law now**: `operator_can_organize`, asked by `create_folder`,
  `create_artifact` and `upload_documents` alike. `STUDIO_ARTIFACT_REGION`
  survives as the DEFAULT home, not a gate. If you re-fence one of them, the
  other two are wrong.
- **The drag MIME is declared ONCE** (`TILE_DRAG_MIME`, in `FileTile.tsx`) and
  imported by the tree and list. Re-declaring it breaks cross-pane drags while
  every per-module test stays green.
- **A file set is state beside the selection**, never a scope (ADR-519 D4.1).
  Every `FileVerbs` signature is still single-target.

## 6. The authoring width ladder (`edf9508` · `d047580`) — a THIRD lane, closed

Re-added after a handoff rewrite dropped it (same concurrent-lane collision that
renumbered 550/551 → 554/555; this lane held the responsive work). Code is
untouched on `main` and its gate is green at HEAD.

Docs and Studio are one component, and it was the only major surface doing
responsive purely in raw Tailwind classes. Two thresholds disagreed about what a
tablet is: the shell collapses at `MOBILE_BREAKPOINT_PX` (640); the workbench
switched at `md:` (768), spelled in class strings where nothing reconciled them.

Measured on prod before: at **820px** the toolbar row held `clientW 16` against
`scrollW 274` and painted **260px over the Properties column**; at 768 the canvas
iframe was **177px**; at 500 the row still overflowed 210px *with* the tab bar up,
and 27 controls sat below the 44px touch floor.

The row cannot be made to scroll — its galleries are `absolute top-full`, and the
root's own comment said so while doing nothing about it. Fix: **need less width**.
Four rungs (`full · condensed · two-pane · single-pane`), thresholds declared once
beside the shell's own, read through `useWorkbenchWidth`, which measures the
workbench's **own container**. Ordering principle: **the canvas never yields** —
it was the sole `flex-1` among `shrink-0` siblings, so it absorbed every deficit.

**`d047580` is the one worth reading.** `edf9508` shipped tsc 0, build 0, 33/33
gate green — and the tablet layout was byte-identical to the defect. The hook took
a `RefObject` and observed it in `useEffect([ref])`; the surface returns its START
state before the workbench, so the effect's only run saw a null node, bailed, and
never re-ran. Measurement right (819px), derivation right (819 → two-pane), nothing
connecting them. Now a **callback ref**. Every gate assertion tested the
DERIVATION, which was never broken — three added for the WIRING.
**Found by driving the doorway, not by a gate.**

Click-passed on prod at three rungs, both apps, incl. emulated iPad-portrait touch:

| rung | before → after |
|---|---|
| 1440 desktop | unchanged — labels, Properties as a column, overflow 0 |
| 820 + touch | overflow 258 → **0**; every verb **44×44**; canvas 177 → **819** |
| 500 phone | tab bar 34 → **44px**; overflow 210 → **0** |

Docs on the same tablet: overflow 0, 44px targets, and correctly **no** page-grain
verbs — the mode distinction holds while the ladder lands on both by construction.

Canon: AUTHORING.md **rule 15**; compositor.md notes the shell's 640 is its own.
Gate: `web/scripts/gates/authoring_width_ladder.mjs` (36 assertions, executes the
derivation at each boundary; all falsifiers fire).

**OWED: one pass on real hardware** — emulation covers pointer-coarse and the box
model, not thumb reach.
