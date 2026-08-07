# ADR-536 — The list is a kind, and align comes home

**Status**: Implemented (2026-08-07)
**Supersedes**: nothing. **Amends**: ADR-443 D4 (the block vocabulary — two rows),
ADR-527 D3 (align/indent — the mount it specified, finally built).
**Relates to**: ADR-528 D2 (the range/object re-cut this ADR repairs the collateral of),
ADR-521 D4 (Tab/⇧Tab list nesting — shipped against a container that did not exist),
ADR-511 D8 (inert names), ADR-456 W1 (`divider` — the rows-not-mechanisms precedent).

> **Operator report (2026-08-07)**, on a Docs document holding a numbered list:
> *"i'm still noticing the existing docs app, despite our recent commits i thought we
> were suppose to readily show align bullets like considerations or the prior decided
> scope but i don't see it on our properties."*

## 1. Two defects, one shape

Both are a control the canon **promised** and the pane could not reach. Neither is a
missing feature; both are a seam between a thing that exists and a door that never opened
onto it. That is why they are one ADR and one commit.

| | promised by | the pane showed | why |
|---|---|---|---|
| D1 | ADR-521 D4 (`Tab/⇧Tab in a list`) | Quote · Checklist | no list kind existed to nest |
| D2 | ADR-527 D3 (`align returns … in a new Text section`) | B/I/U/S · Colour · Highlight | the mount was never built |

## 2. D1 — the vocabulary had no ordinary list

`STUDIO_BLOCKS` carried 13 kinds and **not one plain list**. `checklist` was the only list
row, and it is a *checkbox* list — `list-style: none` plus a `☐` pseudo-element. A member
who wanted a bullet or a numbered list had nothing to insert and nothing to Turn into.

Three things had already been built **on top of** that absence:

- **The paste allowlist admits `UL`/`OL`** ([projection.ts:2255](../../web/components/workspace/viewers/projection.ts#L2255)) — so lists
  entered documents freely.
- **ADR-521 D4 shipped `Tab`/`⇧Tab` nesting "in a list"** and AUTHORING.md records it as ✅
  for the document column — nesting, for a container the member could not create.
- **The recognizer said the quiet part out loud.** `PROMOTE_KIND` mapped `UL: 'prose',
  OL: 'prose'` ([artifactOps.ts:324](../../web/components/studio/artifactOps.ts#L324)) —
  because there was no list kind to promote to. **This is why the operator's numbered list
  reported as `prose` in the pane** and was offered the prose roster: the registry gap
  surfacing at the recognizer, one layer down from where it was felt.

**D1 (the decision).** Two registry rows — `list` (bulleted) and `numbered` (ordered) —
**unscoped**, so every app offers them (ADR-528 D5's default). No new mechanism: rows, not
machinery, exactly the ADR-456 W1 `divider` precedent.

- **Kernel CSS, not skin CSS** — the kernel is the layer that retrofits. `padding-inline-start`
  is declared explicitly because `_SHARED_CSS`'s reset zeroes every margin and padding, which
  would collapse a bare `<ul>` onto its markers; `checklist` next door already had to escape
  the same reset. Nesting steps the marker down (disc → circle → square, decimal → alpha →
  roman), which is what ADR-521 D4's Tab was nesting *into*.
- **`STUDIO_KERNEL_CSS_VERSION` 14 → 15.** The CSS alone retrofits nothing.
- **`PROMOTE_KIND` re-points at the new kinds.** Migration-by-use, the standing pattern: a
  list already in a document is re-named on the artifact's next write, never by a sweep.
  **`checklist` stays unreachable from promotion on purpose** — promotion guesses from a
  TAG, and the checkbox list is the marked special case. Guessing plain is the honest
  default; the member reaches checklist through Turn into, deliberately.
- **`convertBlock` routes both through the `<li>` branch.** The `else` fallback builds `<p>`
  children; inside a `<ul>`/`<ol>` shell that is invalid markup rendering as unmarked text —
  a Turn into that visibly does nothing.
- **`TEXT_BLOCK_KINDS` carries both** — prose lives inside the items, so a click enters
  edit-at-caret. Omitting them would make a list select-only: a container you can point at
  but not type in.

## 3. D2 — align/indent were lost in a re-cut, not withdrawn

ADR-527 D3 is unambiguous. It restored `align` on flow, added `indent`, and said where they
go: *"a new **Text** section, not a resurrected Layout section — the section name matters:
this is arrangement of text."* It amended the grain to `["block-staged","media","block-flow"]`
and noted `block-flow` was *"the grain ADR-525 D4 added to the vocabulary and, until now,
nothing used."*

**The grain was consumed. The mount never was.** The only place a block-grain token could
render was the **Layout** section — which lives in `object` scope. So when ADR-528 D2 turned
flow's `block` scope into `range`, align and indent had no reachable home and silently
disappeared. `TextSection` shipped with B/I/U/S/code/Clear + Colour + Highlight and no
token rows at all.

The tell that this was collateral and not a decision: **the code still claims they render.**
[StudioDesignTab.tsx:1455-1458](../../web/components/studio/StudioDesignTab.tsx#L1455-L1458)
says a range *"still reaches tone + align/indent (meaning and arrangement in the measure,
ADR-527 D3), it is the BOX tokens it never had."* `applicable` computes them at range scope
to this day. Nothing consumed the result.

> **A token computed and never mounted is the green-gates-test-the-room shape.** The grain
> existed, the scope existed, the filter ran — and the control was unreachable. Every gate
> stayed green because each tested its own layer.

**D2 (the decision).** The `block-flow` rows mount in `TextSection`, where D3 put them.

- **Derived from the served grain** (`applies.includes('block-flow')`), never a hardcoded
  `['align','indent']` — a token declaring the grain tomorrow joins with no edit, the rule
  `colorTokens` already follows one line up.
- **Rendered through the shared `TokenControl`** — one presentation for "pick among
  enumerated values", never a second shape for the same idea (the ADR-487 D9 drift).
- **Block grain (`onSetToken('block', …)`) beside range ops, deliberately.** `data-align` is
  `text-align`: arrangement of prose inside its own measure. It addresses the block the caret
  is in — the STRUCTURE tier, exactly like the typography ramp and Turn into, which already
  sit at this scope on identical reasoning.
- **Withdrawn over a multi-block range**, and the notice now *names* align/indent among what
  withdrew. The op is single-subject; answering for the clicked block while six are selected
  is the `d878242` defect.

## 4. Refused, with reasons recorded

- **A list-style picker** (disc/circle/square as a member control). The marker is the design
  system's (ADR-449, and ADR-528 D6 restates it for exactly this pressure). Nesting depth
  selects the marker; the member never picks one.
- **Making `checklist` a variant of `list`.** Tempting — same tag, one row less — but the
  checkbox list is what ADR-443 shipped, it carries its own kernel rule, and re-parenting it
  would rename a kind in every document that holds one. Two ordinary siblings is the smaller
  change.
- **Reviving the Layout section on flow to host align.** ADR-528 D4 deleted its guard as dead
  code and ADR-521 D1 stands: Docs has no layout surface. D3 already refused this by name.

## 5. Implementation

| # | File | Change |
|---|---|---|
| 1 | `services/studio.py` | `list` + `numbered` rows; kernel CSS; version 14 → 15 |
| 2 | `artifactOps.ts` | `PROMOTE_KIND` UL/OL → the new kinds; `convertBlock` `<li>` branch |
| 3 | `projection.ts` | `TEXT_BLOCK_KINDS` += both |
| 4 | `StudioDesignTab.tsx` | `TURN_INTO_KINDS` += both; `flowTokens`; `TextSection` mount; multi-block notice |
| 5 | `test_adr536_lists_and_align.py` | 31 checks incl. 5 falsifiers |
| 6 | `test_adr443_studio_model.py`, `test_adr456_studio_wave2.py` | the roster set + a spelling-pinned assertion re-cut to membership |

**Gate note.** `test_adr456_studio_wave2.py` pinned the turn-into roster as a literal
substring (`"'prose', 'heading', …"`), so re-formatting the array across lines broke a gate
that had no opinion about formatting. Re-cut to parse the array and compare the SET — never
pin a spelling.

**Retrofit note.** The version-generic backfill script landed alongside (`da322d4`'s lane)
carries v15 to existing artifacts, so lists already in members' documents get both the kernel
rules and — on their next write — the promotion to a named kind.

## 6. Owed

- **A click-pass** on the Docs properties pane: insert a bulleted list, Tab to nest, Turn
  into numbered, then align a paragraph. Green gates prove the room, not the doorway.
