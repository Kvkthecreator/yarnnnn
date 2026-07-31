# ADR-509 — The insert route follows the medium: the slash is flow's, the mouse is paged's

- **Status**: **Accepted + Implemented** (2026-07-31, operator-ratified — *"despite our prior
  commits and decisions, should we make the slash command action still relevant in non
  flow-mode (document) type surface commands? … i think due to that, we have confusion."*
  The operator named PowerPoint and Squarespace as the reference class and delegated the
  mount decision; the removal was ratified explicitly against the option of narrowing.)
- **Date**: 2026-07-31
- **Dimension**: Channel — how a member adds a block, per medium. No new substrate, no new
  write path, no schema, no migration.
- **Amends**:
  - **ADR-505 D4** — `/` is **no longer universal**. It is `flow`'s gesture. The *"insert has
    one grammar"* claim is corrected to *"insert has one grammar per medium"*, and D4's
    empirical justification is **falsified in part** (see §2 — this is the load-bearing half
    of this ADR).
  - **ADR-506 D1** — the toolbar's Insert is a **door onto the slash on `flow` only**. On
    `paged` it opens a native menu, because there is no longer a slash there to be a door
    onto. The *"exactly one sender of `yarnnn-slash-open`"* invariant **survives intact** and
    is still gate-pinned; what changes is that the button does not call it on paged.
  - **ADR-506 D3** — *"the button's contents do NOT differ per type"* holds **within a
    medium** and is now false **across** the flow/paged seam, by construction rather than by
    subsetting: the two mounts render the SAME list from the SAME registry (`blockRows.tsx`),
    so no per-type filter, no `applies` column on blocks, no `mode` prop on the palette. The
    ADR-482 D3 race stays closed — see D4 below.
  - **ADR-482 D9** — the "no acts = no menu" rule stands; what counts as an act on `paged`
    grew by one (Insert), so a right-click on bare canvas now serves a menu there.
- **Preserves**: ADR-443 D2 (never an eighth operation — all three doors land through the
  existing ops) · ADR-209 (the revision is the atom; one attributed write door) · ADR-480
  (the editing-grain axiom — this is its insert-route corollary) · ADR-505 D1/D2/D3 (three
  types; the geometry seam) · ADR-466 D4 (insert is located, with no exceptions).

---

## 1. The question

ADR-505 D4 deleted the hover gutter on every mode and left `/` as the **sole block-insert
route on every type**. ADR-506 added a toolbar button, but as a *door* onto that same slash
rather than a route of its own. The operator, using the result:

> *"me using powerpoint and other web editor tools like squarespace, they didnt have the slash
> command and rather just relied on mouse selects, multi selects, right clicks and buttons? i
> think due to that, we have confusion."*

## 2. What the evidence said — and what it falsified

ADR-505 D4 justified the universal slash with a claim about the reference class:

> *"It is the conventional insert gesture everywhere (Notion, Linear, Slack, Craft — and
> **Figma Slides, Pitch and Gamma in the deck class**)."*

**Two of the three deck-class citations are false**, verified against the vendors' own docs:

| Cited | Actual behavior |
|---|---|
| **Figma Slides** | `/` is bound to **cursor chat**. Insert is `Shift+I` / the toolbar. Figma spent the key on something else *on a spatial canvas* — a direct conflict signal. |
| **Pitch** | The quick menu is **Cmd/Ctrl+K**, and Pitch's help explicitly says it is not slash. |
| **Gamma** | True — but Gamma is a card/document hybrid, not a spatial canvas, and its own docs list the **insert bar as "Option 1"** and slash as "Option 2". |

Surveyed properly (5 document editors, 7 slide editors, 5 page builders):

- **Slide editors: 1 of 7** ship a block-insert slash (Gamma alone). PowerPoint, Google
  Slides, Keynote, Figma Slides, Pitch, Canva — none. (Canva's `/` is a global command
  palette, not a caret block menu.)
- **Page builders: 1 of 5** canvas-wide (Gutenberg — itself a *block document* editor).
  **Webflow and Framer both shipped a slash and both scoped it to rich-text contexts only,
  deliberately not the canvas.** That is the same line this ADR draws.
- **Document editors: 3 of 5** (Notion, Craft, Coda). The two that decline are the
  incumbents — Google Docs chose `@`; Word has none.

**The predictor is not document-vs-slide. It is: is there a TEXT CARET IN A LINEAR FLOW?**
The slash needs a caret to anchor to and an unambiguous "here, next" to insert at. Spatial
insertion has neither — you must choose *where*, and no caret names it.

**And the universal finding, with zero counterexamples: no surveyed tool ships slash as the
sole or primary insert route.** A visible mouse affordance always exists, and where the docs
reveal an ordering they present it first (Notion's `+`, Gamma's insert bar, Gutenberg's `+`).

**Studio had this exactly inverted on `paged`.** Measured at the cut: the only mouse insert
route was the empty-slot `+ Add`, which inserts **prose only**; right-click had thirteen rows
and **no insert**; New ‹slide› / Re-arrange are page grain. Of **13 registry block kinds, 10
were mouse-unreachable on a deck** — callout, quote, checklist, divider, toggle, button,
table, metrics, chart, gallery.

## 3. Decisions

### D1 — `/` is FLOW's gesture; `paged` loses it

Gated at the single keypress that opens it, on `FLOW_MODE` — a fact stamped on the served
projection (ADR-480 D1), read from the DOM at keypress time. **Not** an async React value, so
this cannot re-open the ADR-482 D3 race: the gate is correct on the first frame.

`slashFromToolbar`'s paged branch (which entered the last block to manufacture an anchor) is
**deleted, not left unreachable**. A surviving branch would be a second insert path waiting
to be called, and a latent route is precisely how the ADR-482 hole stayed invisible.

### D2 — The mouse insert route on `paged` is TWO MOUNTS, ONE MENU

| Mount | Role | Why it alone is insufficient |
|---|---|---|
| **Toolbar Insert** | **Discovery** — visible without knowing it exists | Not located: it inserts relative to the selection, not to where you are pointing (PowerPoint's ribbon has the same limit) |
| **Right-click → Insert block…** | **Located** — fast, at the thing you clicked | Invisible until you already know; shipping only this repeats the slash's own failure in another costume |

They are **one menu with two mounts**, not two mechanisms — the shape ADR-462 D1 already
ratified for the block menu (*every row is a second entrance to an op that exists, never a
second write path*). One rendered list lives in `blockRows.tsx` and serves the flow palette
too, so a kind added to the served vocabulary appears in all three doors with no second edit.

### D3 — The target is RESOLVED and NAMED, never guessed

Most specific first: a selected **block** → after it · a selected **slot** → into it ·
otherwise → **append to the current page**. Never "nowhere": a member who presses Insert
having selected nothing gets the block on the page they are looking at.

The menu **states the destination** (*"Insert into slide 3"*). On a spatial surface an insert
with an unstated target is the ambiguity that makes members undo and retry — the same reason
ADR-466 D5 forewarns an arrangement that would move content to a new page.

### D4 — Per-MEDIUM is not per-TYPE subsetting

ADR-506 D3 refused per-type kinds because it would rebuild the mode-conditional matrix that
produced the ADR-482 hole. That refusal is intact. The distinction:

- **Refused (and still refused)**: the same door offering *different kinds* per type — which
  needs an `applies` column on blocks and a `mode` prop on the palette, making a menu's
  CONTENTS depend on an async value.
- **Decided here**: *which door exists* per medium. Both doors offer **every kind**, from one
  list. `StudioSlashPalette` still takes no `mode` prop. Nothing filters.

The seam moved from *what is in the menu* to *which menu opens* — and the latter is a
property of the medium, resolved before any content renders.

## 4. What this deleted

- `slashFromToolbar`'s paged anchor branch (the `enter()`-the-last-block ladder)
- the palette's private icon map + row markup (moved to `blockRows.tsx`, one renderer)
- the paged path through `invokeSlash` from the toolbar

## 5. Cost, accepted

**`/` no longer works while typing inside a slot on a deck.** That was the one thing the
slash did on paged that the mouse could not, and ADR-505 D4 named it as a reason to keep it.
Priced and accepted: the member selects and uses the toolbar or right-click, which is what
PowerPoint, Google Slides, Keynote and Squarespace all require. The trade buys back ten kinds
that had no mouse route at all.

## 6. Falsifiers

1. On a `deck`, typing `/` in a block inserts a literal `/` and opens **no** palette.
2. On a `document`, typing `/` still opens the palette at the caret.
3. On a `deck` with nothing selected, toolbar Insert → the menu says *"this slide"* (or
   *"slide N"*), and picking Callout lands a callout on that slide.
4. On a `deck`, right-clicking a block offers **Insert block…** first; on a `document` that
   row is absent.
5. Right-clicking bare deck canvas yields a menu (Insert), where it previously yielded none.
6. `grep -c "type: 'yarnnn-slash-open'"` over `projection.ts` still returns **1**.
7. Every one of the 13 registry kinds is reachable by mouse on a deck.
8. A `web` artifact behaves as `deck` does, not as `document` does.

**Falsifiers 1–5 and 7 need a browser.** The gate proves the routes exist and that the flow
gate is present; it cannot press a key. The click-pass is owed (VERIFICATION.md, E2E lane).

## 7. Key files

- `web/components/workspace/viewers/projection.ts` — the `FLOW_MODE` gate on the `/` keydown
  and on `slashFromToolbar`
- `web/components/studio/StudioBlockInsertMenu.tsx` — the native paged menu (new)
- `web/components/studio/blockRows.tsx` — the one rendered list, three doors (new)
- `web/components/studio/StudioSurface.tsx` — `resolveInsertTarget`, `onInsertPressed`
  (the one fork by medium), `onInsertMenuPick`
- `web/components/studio/StudioBlockMenu.tsx` — the located mount
- `api/test_adr509_insert_route.py` — the gate
