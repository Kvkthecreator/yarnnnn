# ADR-521: The flow benchmark — Notion's scope, the continuous surface's mechanics

> **Status**: **Accepted + Implemented** (2026-08-05). D1–D5 + D7 shipped `a99d1d9`·`5abb52a`;
> **D6 executed the same day** (§7) — the deferred audit found a real defect (unit verbs
> destroying prose blocks on flow) and landed its fix. The operator click-pass is the one
> open item: it is human-driven by necessity (the flow runtime lives in an opaque-origin
> iframe, so synthesized keys cannot drive it) — packet at
> [`docs/evaluations/OPERATOR-PACKET-adr521-flow-format-click-pass.md`](../evaluations/OPERATOR-PACKET-adr521-flow-format-click-pass.md).
> Operator-ratified in full ("proceed in the full
> streamlining: drafting ADR, updating existing docs scope, clean-up legacy code and docs,
> to full implementation scope") after a two-pass framing discourse: the operator named the
> seam from live use ("it's confusing the legacy studio apps approach with the notion like
> blocks approach — selecting across different blocks … is possible, but then the actual
> formatting isn't"), and the code receipts confirmed it exactly.
> **Date**: 2026-08-05
> **Dimension**: **Channel** (the interaction contract of the flow medium). Nothing at the
> Substrate dimension changes — one artifact format, one write door, one revision atom
> (ADR-518 D2 holds; every mechanism below is projection-runtime + FE op behavior).
> **Relates to**: ADR-480 (the editing grain — the axiom this ADR completes), ADR-456 W2
> (the format bar — the machinery this ADR re-derives), ADR-505 D1 ("Notion, never Word" —
> the cell this ADR sharpens), ADR-518 (Docs the writing app — the surface this contract
> governs), ADR-511 D3 (selection floor), ADR-509 (the gesture follows the medium),
> ADR-446 D2 (the sanitize contract — the second gate the paste carve rides).

---

## 1. Context — three grammars were live on one surface

Docs' flow medium was running three selection/formatting frameworks simultaneously, from
three eras:

1. **The selection grammar is continuous-surface class.** ADR-480 put `contenteditable`
   on the flow root; the browser owns selection, so a range from an h1 through prose into
   a bullet list is legal — *more* permissive than Notion, which converts any cross-block
   drag into whole-block selection.
2. **The formatting grammar was block-era.** The format bar shipped in ADR-456 Wave 2 —
   eight days *before* ADR-480 flipped the grain — designed for a caret inside one
   editable block. ADR-480 generalized it by swapping the host to the root (`editHost()`)
   but never re-derived the ops:
   - Bold/italic rode a bare `document.execCommand` toggle. Across a heterogeneous range
     its behavior is browser-defined: an h1 is already bold, so the toggle tries to
     *un*-bold it via style spans, which `sanitizeInner` strips at the commit — the
     formatting **silently reverts**. That is the operator's "the actual formatting isn't."
   - Code used `surroundContents`, which **throws on any range crossing a block
     boundary**; the fallback (`extractContents` + insert) structurally mangled the
     blocks it spanned.
3. **Residual object-grammar chrome from legacy Studio** — enclosure-era block verbs
   addressing flow as if blocks were walls.

Selection said "one continuous document," formatting said "one block at a time," chrome
said "objects." No debt-list fixes that without first deciding which grammar wins.

## 2. D1 — The two-axis benchmark (the framework commitment)

> **Docs' scope is Notion-class; Docs' mechanics are continuous-surface class.**

- **Scope — Notion** (ADR-505 D1, unchanged): the block vocabulary, slash, turn-into,
  markdown-grade essentials, no pagination, no layout surface. ADR-505's "Notion, never
  Word" binds **scope** — it says no pagination and no layout ambition; it never ruled
  selection mechanics (its own parenthetical scopes it to "no pagination — ADR-480 D6").
- **Mechanics — the continuous surface** (Google Docs / Word class): selection,
  formatting, keys, and paste follow the range wherever it runs, because the browser owns
  the flow surface (ADR-480's axiom, already ratified).

Notion supplies the *vocabulary*, never the selection grammar. Two facts make this a
derivation rather than a preference: (a) the block-first alternative was tried five times
and failed each time (ADR-462 → 466 P9-P12 → 477 — the false premise ADR-480 named);
(b) Notion's cross-block restriction is an artifact of its proprietary block-tree data
model — a model yarnnn refused (the DOM is the model; blocks are *annotations*). Adopting
the restriction would import Notion's limitation without Notion's reason.

## 3. D2 — The selection law (one law, two tiers)

> **On flow, text-tier affordances follow the SELECTION wherever it runs; structure-tier
> affordances address the BLOCKS the selection intersects.**

- **Text tier** — bold, italic, code, link, ⌘B/⌘I, paste: range-scoped, cross-block by
  definition.
- **Structure tier** — turn-into, block delete, list indent: derived from the range as a
  block *set* (the Notion affordance re-expressed over honest ranges).

## 4. D3 — The format tier, re-derived

The bare `execCommand` toggle and the destructive `wrapSelection` are **deleted** and
replaced by per-block-intersection machinery:

- **Segmentation**: the live range is intersected with every `[data-block]` it touches
  (top-level blocks only; citation islands excluded) — one sub-range per block.
- **Deterministic toggle** (the Word rule): if *any* eligible segment is unformatted, the
  intent is **apply everywhere**; only when every eligible segment is formatted does the
  op remove. Each segment is toggled only when its state differs from the intent — never
  a blind per-segment toggle (that is exactly the h1 un-bold trap).
- **Heading-aware**: heading blocks are exempt from the bold op (a heading is already
  bold; "bolding" it must be a no-op, never an un-bold). Italic applies everywhere.
- **Code**: per-segment semantic wrap/unwrap. The wrap's fallback now operates within a
  single block segment — the cross-block mangle is structurally unreachable.
- **Link**: unchanged — `createLink` on a multi-block range natively splits into one
  anchor per block, which is the correct continuous-surface behavior.
- The b/i → strong/em normalization at the commit (ADR-446 D2 / ADR-456 W2) is unchanged;
  the source still speaks semantic tags only.

## 5. D4 — Keyboard entrances (one implementation, N entrances)

- **⌘B / ⌘I on a selection** route to the same D3 op — the ADR-511 D5 shape: the bar and
  the keys are two entrances to one implementation. A **collapsed caret** stays
  browser-native (type-ahead formatting state is the browser's own; at a caret there is
  no heterogeneous range, so the trap cannot fire).
- **Tab in a list indents; ⇧Tab outdents** (native `ul > li` nesting — the nesting
  ADR-456 D2 already sanctions). This **supersedes the written refusal** in the flow
  runtime ("deliberately NOT a list-indent gesture"): a keyboard entrance to a structural
  op has exactly slash's legitimacy — the key is not the op, it is a door to it. Tab in
  prose keeps the literal tab character; Tab still never ends the writing session.

## 6. D5 — text/html paste, behind the allowlist (the declared carve, executed)

The security carve STUDIO.md declared ("`text/html` paste — allow-list sanitizer first")
ships as the **first gate** of two:

- **Gate 1 (paste-time allowlist, new)**: allowed tags only (inline semantics + the
  block-level basics the grammar speaks); *every* attribute stripped except `href`, which
  is rejected when it carries a `javascript:` scheme; executable elements dropped
  outright; **media dropped** — a pasted `<img>` lands as nothing, because media enters
  as *cited figures* (ADR-427/448 provenance), never as anonymous pasted bytes.
  Plain-text fallback when no HTML flavor exists.
- **Gate 2 (commit-time, existing, unchanged)**: `sanitizeInner` (ADR-446 D2) strips
  script/iframe/object/embed, `on*` handlers, and `javascript:` URLs from every
  member-typed commit — pasted or typed.

Pasted structure (headings, lists, quotes) is legal because the write seam already
promises it: `normalizeStructure` promotes bare elements into the grammar at every write
(STUDIO.md, "unannotated HTML is editable by definition").

## 7. D6 — The legacy residue audit (deferred at ratification; **executed 2026-08-05**)

The third grammar's residue — enclosure-era block-verb keys in the pointer runtime
addressing flow prose — was **deferred, not dropped**: that exact region of
`POINTER_SCRIPT` was under active concurrent edit by the ADR-520 lane at ratification
time, and two lanes in one region is the refused shape. The audit lands as a follow-on
against D2's two tiers: object *kinds* (figure, table) rightly keep unit selection;
prose-range verbs that assume enclosure are retired from flow.

**Executed the same day the ADR-520 lane landed. It found a defect, not just residue.**

The verb keys (⌫ delete · ⌘C/⌘V/⌘D) asked two questions — *is a block selected* and
*does the caret have a claim on it* — and never the third one this ADR makes decisive:
**is the subject prose or an object.** That was survivable under the enclosure grain the
keys were written for (ADR-482 D2, eight days before ADR-480 flipped it), but not after:
the flow click handler sets the selection on **every** block including prose, withholding
only the visual *cue* (ADR-484). A paragraph was therefore a live verb subject while
looking like nothing was selected, and `⌫` reached the parent's `deleteBlock` in two
reachable windows:

1. **An emptied paragraph.** The caret guard requires non-empty text, so clearing a
   paragraph and pressing Backspace again to merge up **deleted the block** instead.
2. **A cross-block range** — the subject D2 had just made first-class. The range's
   `startContainer` sits in its *first* block, so the in-block test fails for the
   selected one, and Backspace over an h1→prose→li selection **deleted a whole block**
   instead of the selected range.

Both commit a revision through `applyOp`: real content loss, recoverable only by ⌘Z or
the revision chain. The fix is one gate at `selectedBlock()` — the single chokepoint
every verb reads — so on flow the verb tier is an **object tier**, and prose hands the
keys back to the platform, where Backspace means "delete the selection or merge": the
continuous-surface mechanic D1 committed to. Paged is untouched; there the block *is* an
enclosure and the unit verb is the correct grain (ADR-480's per-mode axiom).

This is the D2 law reaching one rung further than the format tier: **the text tier
follows the selection, the structure tier addresses intersected blocks, and the object
tier addresses only what has no caret to speak for it.**

## 8. D7 — Refusals (the benchmark is mechanics, not chrome mimicry)

- **No block-set selection mode** (Notion's blue whole-block highlight) — the browser
  range IS flow's selection; a second selection mode would rebuild the deleted editor.
- **No drag handles / positional anything on flow** (ADR-481/509 unchanged).
- **Pagination stays refused** (ADR-480 D6) — "never Word" still binds where it always
  did: scope.
- **Caret-state formatting pipeline** (custom collapsed-⌘B state machinery) — not owed;
  browser-native suffices at a caret.

## 9. What this amends

| Canon | Change |
|---|---|
| STUDIO.md | Normative rule 10 (the two-axis benchmark + the selection law) · the Inline format matrix row · keyboard owed cells cleared for document · forward roster re-cut (⌘B/⌘I and `text/html` paste leave the owed lists; the D6 audit enters) · standing refusals gain the block-set selection mode. |
| ADR-505 D1 | The medium-convention cell sharpened by banner: "Notion, never Word" binds scope (pagination/layout), not selection mechanics. |
| ADR-456 W2 | The format bar's *mechanism* re-derived for the flow grain (banner); the bar, slash, and turn-into affordances stand. |
| ADR-480 | The flow Tab ruling ("never a list-indent gesture") superseded by D4 (banner); the axiom, the grain, and every other ruling stand untouched. |
| ADR-482 D2 | The keyboard-verb guard sharpened by D6 (2026-08-05): the caret question it introduced is necessary but not sufficient on flow — the verb tier must also ask the block KIND. Its caret-vs-session correction stands; the text keys still ask `__yarnnnCaretLive`. |
| STUDIO.md (verbs row) | The `document` cell rewritten from "same, caret-guarded" — which D6 falsified for prose — to **objects only**; the roster's residue-audit follow-on moves to shipped. |

Preserved untouched: ADR-443 R1 (DOM is the model) · ADR-446 D2 (sanitize contract —
now two gates deep on paste) · ADR-480 D1/D6 · ADR-505 type set · ADR-509 · ADR-511 ·
ADR-518 D2 (no new op, no second write path, no forked machinery).

## 10. The one-line statement

**Notion tells Docs what a document holds; the continuous surface tells Docs how hands
work on it — the selection is the browser's, wherever it runs, and every text affordance
follows it, while structure keeps addressing the blocks it crosses.**
