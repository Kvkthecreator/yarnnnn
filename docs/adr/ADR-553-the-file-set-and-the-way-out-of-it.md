# ADR-553 — The file set, and the way out of it

> **Status**: Implemented (2026-08-12). Phase 4 of the arrival/move proposal.
> **Inherits**: [ADR-519](ADR-519-the-object-hierarchy-and-the-pane-grammar.md) D4.1 — *"the set is STATE, not a scope"* — applied to files rather than blocks
> **Preserves**: every `FileVerbs` signature (single-target, unchanged) · ADR-337 D3 (MoveFile is one attributed op per file) · ADR-550 (the projection travels, per move) · ADR-552 (one drag grammar)
> **Derivation**: the 2026-08-12 arrival/move audit

---

## 1. The defect

Selection was a single `selectedPath: string | null`, and every verb took one
`{path, name}`. **Moving ten uploaded files was ten right-click → modal → pick
sequences.** No `shiftKey`/`metaKey` handling existed anywhere in
`web/components/workspace/`.

## 2. The risk this phase inherited, and why it shapes the design

**ADR-519 shipped an inescapable multi-selection to production once.** That is
the named trap this phase carries, and it changes what the work *is*: the
feature is not "select many files", it is **"select many files and reliably stop
selecting many files."**

The trap was never in the entering. It was in the leaving — which is why the
gate for this ADR weights four escape assertions against one existence
assertion, and falsifies each exit **independently**: three surviving exits
still read as "fine" while the fourth corner traps someone.

## 3. Decisions

### D1 — Entered only deliberately, never by accident

A ⌘/Ctrl-click toggles membership. A plain click replaces the selection
entirely. There is **no drag-rectangle, no shift-range, no "select all"** — one
deliberate gesture in, so a member cannot arrive in a multi-selection without
having asked for one.

A folder is never a set member (there is no bulk folder verb), and an additive
click does **not** also toggle a folder's disclosure — the set gesture and the
navigate gesture must not fight over one click.

### D2 — The set is STATE beside the selection, never a scope

ADR-519 D4.1's rule, inherited verbatim: `selectedPath` stays the primary, and
the set is *additional members*. Every existing reader still gets exactly one
path; only the N-taking gesture consults the set. The primary is **first** in
the derived set, so a `[0]` reader gets the same file the subject names, and the
primary can never leave the set (no orphan state).

The bulk move is a **loop over the single mover**, deliberately: the substrate
has no bulk move, and inventing one would need partial-failure semantics the
single mover already has. Two consequences are handled rather than hidden:

- **Sequential, not parallel.** N concurrent writes into one folder race on
  `destination_exists`, and the loser's 409 would read as a random failure.
- **Partial results are SAID.** Moves are non-transactional per file, so a set
  can half-land: *"Moved 7 of 10. 3 could not be moved."* Reporting a flat
  success over a partial move is the failure this guards.

It reuses the **same picker** a single Move uses, and names the set honestly
(*"3 files"*) rather than borrowing one member's name — the stale-label failure
ADR-519 D4.1 names.

### D3 — Four independent ways out

Each exists because losing any one re-creates the trap in a different corner:

1. **Escape** — the universal exit.
2. **A visible Clear** beside the count. A keyboard-only exit is not an exit for
   someone who never learns the key.
3. **A plain click** clears the set before selecting.
4. **Any single-target verb** ends the set. Without this, a set built before a
   rename/move/trash outlives it and points at paths that no longer exist — the
   *stale* half of the trap, arriving by a door Escape does not guard.

And the set **says itself**: a mounted count, because a set with no visible
count is a set the member cannot see they are in.

## 4. What is deliberately not built

- **No shift-range, no marquee, no Select All.** One way in is the point.
- **No bulk delete, rename, share, or duplicate.** Move is the verb the audit
  found a member actually repeating. Each additional bulk verb is its own
  partial-failure story and earns its own decision.
- **No folders in the set** — no bulk folder verb exists to take them.
- **No cross-surface set.** The set lives on Files; Studio and Docs are
  single-artifact surfaces.

## 5. Falsifiers

1. ⌘-click three files → the count reads "3 selected".
2. Escape → the count disappears.
3. Clear → same.
4. A plain click on a fourth file → selection is just that file.
5. Rename one file while a set is live → the set ends.
6. Move a set into a folder → all land, one toast.
7. Move a set where one file's name is taken → *"Moved N of M"*, naming the
   failure.
8. A ⌘-click on a folder does not add it, and does not collapse it.

## 6. The one-line statement

**A file set is state carried beside the selection, entered only on purpose and
leaveable four ways — because the hard part of multi-select is not selecting
many things, it is reliably stopping.**
