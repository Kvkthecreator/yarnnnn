# ADR-541: The selection algebra — a range's subjects are its covered blocks, and every verb entrance reads one answer

> **Status**: **Accepted** (2026-08-09) — operator-ratified through the
> hierarchy/docs-app audit + the benchmark re-challenge ("the proposed
> discipline, scope, and approach is actually right"; implementation delegated
> in full). Numbering note: ADR-540 is reserved by the concurrent flow-retire
> lane whose code comments already claim it.
> **Date**: 2026-08-09
> **Dimension**: **Channel** (how a gesture reaches an op) primary; a
> **Substrate** consequence only in that N-block ops land as ONE revision.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**: ADR-519 D4.1 (the set is state, not a scope — upheld and
> finished), ADR-520 (pane spine), ADR-521 D7 (flow's selection is the browser
> range), ADR-525 (the selection carries its tier — extended to the whole
> answer), ADR-526 (its "no block-set selection mode" refusal narrowed to
> chrome), ADR-527 D2 (range emphasis), ADR-528 (range/object scopes; D7's
> two-axis benchmark — two corollaries amended), the `d878242` single-subject
> rule (re-cut), ADR-536 (align/indent's mount).

---

## 1. Context — six derivation sites, two set representations, two blind verb entrances

The 2026-08-09 audit mapped the selection layer: **nine** distinct
selection-state representations across the runtime/parent boundary, **five**
incompatible scope/grain enumerations, and **six** independent sites deriving
"what can I do to this selection" — of which two (`StudioToolbar`,
`SurfaceFocus`) never read the tier ADR-525 told everyone to read. The
multi-selection exists **twice** (`rangeBlockIds` for flow ranges, `groupIds`
for ⇧-click object sets), the single-subject rule is enforced through five
mechanisms across ~14 pane guard sites with two different notice strings, and
two whole verb entrances are set-blind:

- **The right-click menu** reads one block: during a six-block range it
  offers Turn into and Delete against whatever sat under the cursor.
- **The runtime keyboard** gates on `cur` alone: **⌫ over a five-object set
  deletes one object, silently** — a data-loss-shaped defect.

The benchmark re-challenge found the deeper fault: the `d878242`
single-subject rule ("align/indent/ramp/turn-into withdraw over any
multi-block selection") **contradicts both halves of ADR-528 D7's own
benchmark**. Google Docs applies a paragraph style across every paragraph a
range covers; Notion turns-into across a selected set. The withdrawal was an
implementation constraint (`handleFormat`'s structure ops address a single
`selectedEl`) dressed as a design position — ADR-528 itself listed
"span-aware structure ops" as OWED. The current state delivers *neither*
benchmark at the multi-block seam.

## 2. Decisions

### D1 — The selection payload is the WHOLE answer, declared once by the runtime

ADR-525 put `tier` on the payload and consumers still re-derived everything
else. The payload becomes complete:

```
{ tier: 'text' | 'object' | 'structure',
  subject: { blockId, kind } | null,     // the primary — ADR-519 D4.1's `cur`
  set: string[],                          // [] or the covered/collected ids
  setKind: 'range' | 'objects' | null,    // HOW the set was made (gesture fact)
  headingId, headingText,                 // the ADR-522/526 crumb (unchanged)
  slideIndex, pageIndex, slot, arrange }  // the paged grains (unchanged)
```

`rangeBlockIds` and `groupIds` **unify into `set`**. ADR-519 D4.1 stands
whole: the set is state, never a scope — `setKind` records the gesture, and
no section ever takes the set as its identity subject. The parent keeps ONE
piece of state for it.

### D2 — `scopeOf` and `arityOf` are the only derivation sites

Two exported pure functions, defined once beside the payload type:

- **`scopeOf(sel, mode)`** → `document | range | object | container | page`
  — the ADR-528 D2.1 ladder, extracted from the pane into the one shared
  home. Consumed by the pane, the right-click menu, the toolbar,
  `SurfaceFocus`, and the navigator reach. The two consumers that today
  ignore tier get it by construction.
- **`arityOf(sel)`** → `none | one | many` — the single-subject question
  answered once. Every verb entrance (pane section guards, menu rows, runtime
  keyboard dispatch on the parent side) consults it. The pane's ~14 ad-hoc
  guards collapse onto it; the two multi-notice strings become one derivation.

### D3 — Structure ops are SPAN-AWARE: a range's subjects are its covered blocks

Amends the `d878242` rule and pays ADR-528's OWED item. The heading ramp,
Turn into, and align/indent, invoked while `arityOf === 'many'` with
`setKind === 'range'`, apply **per covered block, in document order, as ONE
revision** (`convertBlocks` / token-set-many beside the existing
`setGeometryMany` precedent — a list in, one write out). Rules:

- Per-block legality is per-block: a citation island inside the range is
  skipped (convertBlock's refusal per block, not a whole-range veto), and the
  revision message says how many blocks the op touched.
- The ramp across a range makes every covered convertible block that rung —
  the Google Docs contract, verbatim.
- Formatting (`onFormat`) already spans; it is untouched.

### D4 — Every verb entrance is set-aware, or refuses with the one notice

- **⌫ / duplicate over an object set**: the whole set, one revision, count in
  the revision message ("delete 5 blocks"). The runtime keyboard stops
  consulting `cur` alone; the parent dispatches by `arityOf`.
- **The right-click menu during a live set**: rows that take a set
  (Delete, Duplicate, Turn into per D3) act on the set and SAY the count;
  rows that are single-subject (Copy link, History, Move up/down) withdraw
  with the same one-sentence notice the pane shows. One notice, one source.

### D5 — ADR-526's set-mode refusal narrows to CHROME

Flow keeps the character-highlight presentation — no blue block cards, no
set-selection mode, no drag handles (ADR-521 D7 stands). What the refusal no
longer covers is *semantics*: the covered blocks ARE the op's subjects (D3).
The data model already said so (`rangeBlockIds` has existed since ADR-527);
this makes the interaction model agree with it.

### D6 — Not done here

No per-block attribution (whole-file facts, ADR-528 D0). No `<section>`
wrapper. No new tier, no new scope, no sixth pane section. The
`StudioContextTarget` parallel payload type dissolves into the D1 payload +
a coordinate — the menu reads what everything else reads.

## 3. What this amends

| Canon | Change |
|---|---|
| `d878242` rule | Single-subject narrows to genuinely single-subject verbs (identity/position/history). Structure ops span (D3). |
| ADR-528 D7 | The benchmark's corollaries corrected: both references apply block-grain transforms across a selection; now so do we. |
| ADR-528 §7 OWED | "Span-aware structure ops" delivered. |
| ADR-526 §4 | "No block-set selection mode" narrowed to presentation (D5). |
| ADR-519 D4.1 | Upheld; `setKind` is the gesture fact it called for; align/distribute keep being the set's only identity-free sections. |
| ADR-525 | Extended: the payload carries the whole answer, not only the tier. |
| AUTHORING.md | The interaction contract gains the (tier × arity) table; rules 10/11 re-point at `scopeOf`/`arityOf`. |

## 4. Consequences

**Positive.** One derivation, N mounts: the pane, menu, toolbar, focus line
and keyboard structurally cannot disagree about a selection again — the
ADR-525-class defect ("three surfaces, three answers") becomes
unrepresentable rather than re-patched. The ⌫-deletes-one-of-five defect
closes. Docs finally honors both its benchmarks at the multi-block seam.

**Costs, stated.** The runtime payload grows (every consumer re-reads it —
one shape change, coordinated across projection.ts, StudioCanvas,
StudioSurface, pane, menu). Span ops mean a bad gesture can restructure N
blocks at once — mitigated by ONE revision (one ⌘Z undoes the whole op) and
the count in the revision message. The menu's set-aware rows need the set to
survive a right-click (the click must not collapse the range/set before the
menu reads it) — an ordering constraint the implementation must gate.

## 5. Falsifiers

1. If any consumer is found deriving scope or arity outside `scopeOf`/
   `arityOf` after this ships, D2 failed as a chokepoint — move the
   derivation, never add a second. The gate enumerates consumers.
2. If span ops produce N revisions instead of one, D3's substrate contract is
   broken (attribution noise + N-step undo) — that is a defect, not a
   variant.
3. If members are observed losing work to span ops (support signal, not
   speculation), D3 adds a confirm affordance at the gesture — not a
   withdrawal back to single-subject.

## 6. The one-line statement

**The runtime declares the whole selection once; `scopeOf` and `arityOf` are
the only readers; a range's subjects are its covered blocks — so every door
offers the same verbs, and a verb over many lands as one revision.**
