# ADR-505 — The three-type cut: one medium per type, one insert grammar

> **⚠️ Amended by [ADR-518](ADR-518-docs-and-studio-the-writing-app-and-the-layout-app.md) (2026-08-04)**: the three types gain their housing column — `document` → **Docs** (the writing app); `deck` · `web` → **Studio** (the layout app). The type SET, D2's read-time aliasing, and D3's mode/frame seam are untouched; D1's table simply stopped being one app's table.

> **⚠️ Sharpened by [ADR-521](ADR-521-the-flow-benchmark-notions-scope-the-continuous-surfaces-mechanics.md) (2026-08-05)**: D1's medium-convention cell — "Notion, never Word" — binds **scope** (no pagination, no layout surface; its own parenthetical says so), never selection mechanics. The full benchmark is two-axis: Notion's scope, the continuous surface's (Google Docs / Word) mechanics — selection and formatting follow the range wherever it runs.

- **Status**: **Accepted + Implemented** (2026-07-30, operator-ratified through the
  studio-audit discourse — *"i'm underestimating just how far the ramifications of these
  modes go… ironically, in that light, i actually think we need to simplify"*). Each
  decision below was ratified individually in that exchange; D3 (`web` geometry) was
  explicitly delegated to the implementer and is decided here on first principles.
- **Date**: 2026-07-30
- **Dimension**: Channel (primary — what kinds of artifact exist, and how the member adds
  to one). No new substrate, no new write path, no schema, no migration.
- **Amends**:
  - **ADR-443 R5 / ADR-456 D4** — the Studio type set goes from four to **three**
    (`document` · `deck` · `web`). `article` + `page` merge; the W3 band family survives
    intact under the new name and gains two long-form bands.
  - **ADR-458 D4** — the hover gutter is **DELETED** on every mode. ADR-481 D2 had already
    removed it on `flow`; this removes the `paged` remainder. ADR-458 D3 (the Design tab as
    the one settings home) is untouched and is what that ADR is now remembered for.
  - **ADR-461 D2** — `bindGesture` survives losing its first caller (the `⋮⋮` reorder).
    The primitive is unchanged; the claim it proved is now proved by the divider + resize
    callers instead.
  - **ADR-466 D1** — the three per-mode interaction contracts stand, restated for three
    types: deck object-first, `web` band-first, document caret-first.
  - **STUDIO.md** — the type table, the object model's mode-conditional note, the
    interaction model's insert routes, and the refusals.
- **Preserves**: ADR-209 (the revision is the atom; one attributed write door — no legacy
  artifact is rewritten to satisfy a rename) · ADR-443 R1 (the DOM is the model) · ADR-480
  (the editing grain axiom, in full — this ADR is its type-level completion) · ADR-481 D1/D5
  (flow scaffolds flat; legacy renders, never migrates) · ADR-461 D4 (a slide has a frame, a
  page has a viewport — the refusal this ADR leans on) · ADR-472 D1/D7 (`canvas` left for
  IMAGES; nothing here re-claims it) · ADR-456 stop-lines (no second source format, no
  per-breakpoint editing, no pagination).

---

## 1. The question

ADR-480 established the axiom — **attribution binds to the file, addressing binds to
sub-file structure, editing binds to what the medium is** — and applied it to the *editing
grain*. ADR-481 rebuilt the chrome around it, ADR-482 closed the seam between them.

What none of the three did was apply the axiom one level up, to the **type set itself**. Four
types persisted (`document` · `deck` · `article` · `page`), and the operator named the
friction that produced:

> *"if the current document type, i'm confusing over a more text oriented, or notion like, or
> microsoft word like, and thus, there seems to be some confusion in what is the fundamental
> objective of the different document types… because the fundamental premise is vague, we're
> going back and forth on the key features and what they should be and how."*

The premise was not vague — it was **over-counted**. Four types implied four coordinate
systems where there were only ever three media.

## 2. What the evidence said

Measured at the cut (18 live `.html` artifacts, body-only `data-arrange` counts — kernel CSS
excluded, which is what made earlier counts look nonzero):

| Type | Artifacts | Body arrangements | Real authored content |
|---|---|---|---|
| `document` | 9 | **0 in all nine** | 2 (`prd-for-yarnnn` 24.8KB, `hello` 22KB) |
| `deck` | 3 | 11 · 6 · 5 | 1 (`ir-deck-yarnnn-march-2026-v5`) |
| `article` | 2 | 1 · 0 | **0 — both `test-*`** |
| `page` | 1 | 3 | **0 — `test-page`** |
| `canvas` | 1 | 1 | 0 — orphaned legacy (ADR-472 moved the type to IMAGES as `image`) |

Three findings, in the order they mattered:

1. **`document` is the centre of gravity and uses none of the region machinery.** Half the
   artifacts, both of the substantial ones, zero arrangements ever authored.
2. **Deck is the only type where the region machinery is load-bearing.** 11 arrangements, all
   in use, and the only type with a frame.
3. **`article` and `page` were never used for real work.** `article` was the tell — a
   *publishing* shape wearing an *internal-document* chrome (`mode: flow`, 0 arrangements,
   a narrower `max-width` as its entire distinction from `document`).

## 3. Decisions

### D1 — The Studio type set is THREE, one per medium

| Type | Job | Medium convention | Mode |
|---|---|---|---|
| **`document`** | **CAPTURE** — notes, drafts, working docs. Continuous, internal, revised forever. | Notion, never Word (no pagination — ADR-480 D6) | `flow` |
| **`deck`** | **PRESENT** — a framed stage, spoken over. | PowerPoint / Keynote | `paged` |
| **`web`** | **PUBLISH** — a banded page read by someone OUTSIDE the workspace. | Medium / Substack / Wix | `paged` |

`document`'s scope is the **markdown-grade essentials** (headings, prose, lists, quote,
callout, table, image, divider) — deliberately not a layout surface. Every region mechanism
is absent **by definition** now, not by measurement: a capture surface that asks *where on
the page* has stopped being a capture surface. This upgrades ADR-481 D1 from an empirical
finding (*"zero were member-authored"*, which could drift) to a type property.

`canvas` **is not a Studio type** and never re-becomes one. It left for the IMAGES app as
`image` (ADR-472 D1/D7). It is absent from `STUDIO_LAYOUTS`, absent from
`RETIRED_LAYOUT_SLUGS` (a Studio alias would re-claim it), and `app_for_kind("canvas")`
returns `None` on purpose — the one stale `canvas.html` opens in the generic viewer and
belongs to no app's recents. The reasoning is written at the registry, where someone would
try to add it back.

### D2 — `article` + `page` merge into `web`; the retired slugs resolve, never offer

Both answered one question — *HTML for someone outside the workspace* — and the split asked
the member to pre-classify an essay against a landing page **before writing a word**. The
band stack serves both: a `prose-header` band opens a blog post, `hero`/`cta` open a landing
page, and the difference is *which bands you stack* — a composition choice, not a type.

`web` ships **8 arrangements**: the six W3 bands (`hero` · `content` · `feature-grid` ·
`testimonial` · `cta` · `footer`) plus two new long-form bands carrying what `article` was —
`prose-header` (kicker · title · standfirst · byline) and `prose` (a 42rem reading column).

**Legacy resolves at READ time; the source is never rewritten.** A pre-cut artifact carries
`data-template="article"` in its own bytes, and ADR-209 forbids manufacturing a revision to
fix a naming decision. `RETIRED_LAYOUT_SLUGS` + `canonical_layout_slug()` map the two slugs
to `web` inside `resolve_layout` / `resolve_arrangements` / `artifact_kind` — one alias table,
one resolution point, **not a dual implementation** (there is exactly one `web` row and one
`web` roster). `all_layouts()` returns live types only, so a retired slug is *resolvable* but
never *offered*: the create picker shows three. The kind lift returns the **canonical** slug
because the FE keys its glyph and its app routing on it — returning the raw legacy value
would split one artifact's identity in two (`kind: article` wearing `label: Web`).

Nothing may be added to the alias table casually: a new retirement earns a row, and a slug
that never shipped is simply unknown.

### D3 — `web` is BAND-FIRST: mode is not the geometry seam

**`web` gets no coordinate space, ever.** Three reasons, in the order that decided it:

1. **The medium has no frame.** ADR-461 D4's refusal is a fact about the medium, not a
   convention: *a slide has a frame, a page has a viewport*. A deck slide is 16:9 always, so
   "40% from the left" is stable and meaningful. A web page is 390px on a phone and 2560px on
   a monitor; the same percentage means a different thing at every width, and pinning it is
   per-breakpoint editing — an ADR-456 stop-line.
2. **The reference class agrees.** Medium, Substack, Ghost — the richest long-form editors in
   wide use — ship **zero** positional control. The tools that do (Framer, Webflow) are
   building design tools and pay for it with a breakpoint editor we refuse.
3. **It keeps the types honest.** A `web` with free placement would become "the powerful one"
   and every long-form need would drift there, re-blurring the boundary D1 just drew.

**The seam this exposes, and the fix.** `paged` was doing two jobs — *has page units* and
*has a coordinate space*. Deck has both; `web` has only the first. Rather than add a third
mode, geometry keys on its own axis, **which the registry already had**: the `block-staged`
predicate tests `.slide` **ancestry**, not mode. A `web` band is not a `.slide`, so `x`/`y`/`z`
are structurally unreachable there — no gate, no flag, no suppression code.

> **`mode` answers *how it composes* (sequence vs page units). The FRAME answers *is there a
> coordinate space*. They were conflated under one word; naming them apart is what let `web`
> merge article+page without inheriting deck's object grammar.**

Two values of `mode` remain. This is the "mode we can fix" resolved: it was a conflation, not
a missing value.

### D4 — The hover gutter is DELETED on every mode; insert has one grammar

ADR-481 D2 deleted the gutter on `flow` (the caret IS the insertion point, so an affordance
pointing at a *place* answers a question a continuous surface never asks). What remained on
`paged` was a **third** insert route behind `/` and the New-‹page› gallery — and web-page
editors do not have one.

Deleted with it: the `⋮⋮` **drag-to-reorder** and its drop-line. Priced and accepted: on
`document`, reorder is now cut/paste in continuous prose (the browser's own, which is what a
capture medium's reorder actually is); on `deck`/`web` it is the menu's Move up/down.

**The resulting grammar — five mechanisms, zero mode-conditional cells within a route:**

| Act | `document` | `deck` / `web` |
|---|---|---|
| add a block | `/` at the caret | `/` at the caret |
| add a page / band | — (no page grain) | **New ‹slide|band›** (the gallery) |
| re-lay a page | — | **Re-arrange** |
| add a cited object | `/` → the file picker | `/` → the file picker |
| act on a thing | right-click | right-click |

`/` is deliberately **universal and ungated**. It is the conventional insert gesture
everywhere (Notion, Linear, Slack, Craft — and Figma Slides, Pitch and Gamma in the
deck class), it is the only route that works *while typing inside a slot*, and gating it
would mean **adding** a mode condition — the exact shape of the ADR-482 D3 race (chrome
conditioned on an async `mode` value). The invariant that keeps it honest: the slash runtime
rides `EDIT_SCRIPT`, injected on `opts.edit` alone, with no `paged`/`flow` branch.

**The gallery and Re-arrange stay distinct** (considered and declined: merging them, and
renaming the gallery "layout master"). They are two nouns — *add a page* (CREATE at page
grain) vs *re-lay this page* (TRANSFORM at page grain) — sharing only a chooser UI. Merging
them would leave a member picking a layout unsure whether a new slide appears or the current
one is overwritten, which is the ambiguity ADR-466 D5's amber `content → new ‹page›` warning
exists to resolve. "Layout master" was rejected because *master* already names the opposite
thing in this canon — the template a page inherits from, the scaffolding PowerPoint refuses
to make selectable (STUDIO.md §"A slot is CHROME only where it is a distinguishable region")
— and it is the term ADR-447 retired when `STUDIO_CONTAINERS` became `STUDIO_ARRANGEMENTS`.
The chrome keeps saying the act: **New ‹noun›** and **Re-arrange**.

### D5 — The flow-slot add-text duplicate is deleted; the media picker is not a duplicate

The Design tab's slot scope offered `+ Add text here`, calling the **same**
`insertProseInSlot` as the empty slot's own `+ Add` on the canvas — one act, two mounts, and
the canvas mount is the located one (DP29). Deleted; the panel now names the slot's role and
points at the located routes.

The **media** branch stays. It is not a second route: the canvas `+ Add` on a media slot
*routes into it* (`onAddHere`, `role === 'media'`), so it is that act's terminal step and its
documented home (STUDIO.md — *"this scope is the image picker's home"*).

### D6 — The object script is renamed for what it holds

`GUTTER_SCRIPT` was 1,167 lines of which the gutter bar was the first ~90. The rest: the
bounding box, eight resize handles, the border-band move, group resize (the Figma model), the
column divider, the selected block's keyboard, and undo/redo. **The name described its first
90 lines and hid the other thousand** — a reader following it to "delete the gutter" would
have deleted deck's entire object grammar and ADR-479's undo.

Renamed `OBJECT_SCRIPT`, and its injection comment now states the `paged`-only reason on its
own terms (*geometry needs a frame*) rather than inheriting the gutter's. This is the ADR-482
lesson generalized one turn further: **a stale name is a latent deletion hazard**, and the
gate now pins the rename so the hazard cannot return.

## 4. What this deleted (Singular Implementation)

Not disabled — deleted:

- `GUTTER_SCRIPT`'s bar: `build()`, the `+` button, the `⋮⋮` handle, `showFor`/`hide`
- the row band: `rowAt(x, y)`, `BAND_LEFT_REACH`/`BAND_RIGHT_REACH`, the mousemove/scroll
  re-anchor, the 150ms grace timer
- the reorder gesture: `bindDrag`, `ensureDropline`, `siblingBlocksOf`, the `yarnnn-reorder`
  message, `onReorder` (canvas prop + handler), `handleReorder` (surface)
- the `design: true` handshake end to end (runtime payload → `PointerEvent2.design` →
  `setRightTab('design')`) — orphaned the moment the `⋮⋮` click went
- CSS: `.yarnnn-gutter*`, `.yg-handle`, `.yarnnn-dragging`, `.yarnnn-dropline`
- four dead `.yarnnn-gutter` click/contextmenu/undo guards
- `moveBlockTo`'s export (now module-internal — its one caller is `moveBlock`, the menu verb)
- the Design tab's `+ Add text here` + its `onAddTextInSlot` prop and wiring
- `studioShapes`' `article` + `page` rows and the now-unused `Newspaper` import
- `api/test_studio_block_drag.py` — the gate for a deleted gesture

**Survived deliberately, and gated:** `bindGesture` (the shared pointer primitive), the
bounding box + handles + group resize, the column divider, undo/redo, the `hover: hover`
gate, `__yarnnnSelect`, and the empty-slot dashed `+ Add` placeholder (a slot affordance, not
a gutter).

## 5. Gates

`api/test_studio_gutter_and_arrows.py` → **`test_studio_no_gutter_and_arrows.py`**: its
gutter half **inverts** to a negative gate (the affordance has not come back) plus the
survival assertions (the deletion did not take `bindGesture` or the object chrome) and the
rename. Its F6 arrow-traversal half is unchanged. 16/16.

Updated: ADR-440 (3 seeded templates) · ADR-443 (3 layouts; `deck`/`web` scaffold slot
contract) · ADR-456 W3 (the band family survives the rename; +2 long-form; the measure gate
asserted a **slug** test the FE had already replaced with the mode seam) · ADR-458 (the
hover-layer half inverts; the one-settings-home half untouched) · ADR-461 (the divider is
`bindGesture`'s proof now; the frame gate has one consumer) · ADR-462 (the format bar is the
only injected chrome to exempt; the accent invariant survives its example) · ADR-466 · ADR-481
(`{deck, web}`; deck 11 + web 8) · ADR-482 (`OBJECT_SCRIPT`) · `test_studio_layout_mode`
(+4 checks: the three-type set, retired-resolves-never-offered, canvas-is-not-Studio, and
**mode-is-not-the-geometry-seam**).

Full studio sweep after: **25 gates green.** Four gates carry **pre-existing** failures,
verified against the clean tree by `git stash` and NOT caused by this change:
`test_adr480_flow_editing_grain` (3 — a `data-block` leak in
`scripts/oneshot/adr482_repair_flow_documents.py`, plus two mode-as-projection-input checks),
`test_studio_chrome_and_load` (2), `test_studio_name_is_one_fact` (1),
`test_studio_slash_anywhere` (1), `test_studio_split_merge` (2). They are named here rather
than absorbed silently; each deserves its own pass.

Runtime verified beyond the static gates: all three skeletons build (self-describing,
annotated, script-free), `document`'s body carries 0 arrangements + 0 slots, all 8 `web`
arrangements ship the slots they declare (the ADR-443 §2b invariant), `web`'s skin contains
no `.slide` so `block-staged` can never match, and both retired slugs round-trip to
`kind=web` / `mode=paged` / 8 arrangements. `next build` passes.

## 6. Consequences

**Positive.** One medium per type, each with a convention a member already knows. Insert is
one sentence per grain with no per-type subsetting — the 4×4 matrix with mode-conditional
cells that produced the ADR-482 hole is gone. `document`'s simplicity is now a *type
property* rather than a measurement that could drift. The geometry seam is named apart from
the composition seam, so a fourth type can be added without re-litigating either. A
1,167-line script is named for what it does.

**Costs, stated.** A long-form essay in a band stack is slightly worse than in continuous
flow — the honest remainder of merging `article` into a `paged` type; the answer is that
long-form drafting **is** `document`, and publishing it outward should be a *projection* of a
document rather than a separate authoring type (which makes `PROJECT`, today the thinnest of
the seven operations, the natural home for the follow-on). Drag-to-reorder is gone on every
type. Legacy `article`/`page` artifacts render through an alias — correct per ADR-209, and
they converge on `web` naturally when next edited (ADR-481 D5's migration-by-use).

**The follow-on this ADR makes visible, not taken here**: Studio is the *downstream* half of
ADR-457 D2's `think → settle → make` pipeline, and `settle` is ratified-but-unbuilt. A member
arriving at `document` today composes from nothing. That is the upstream gap the audit
surfaced, and it is fixed in chat, not in Studio.

## 7. Key files

`api/services/studio.py` (the three-type registry · `RETIRED_LAYOUT_SLUGS` +
`canonical_layout_slug` · the `web` layout + 8 arrangements · the canvas-is-not-Studio
declaration · the mode docstring re-cut) · `web/components/workspace/viewers/projection.ts`
(−284 lines: the gutter, the row band, the reorder gesture; `OBJECT_SCRIPT`) ·
`web/components/studio/{StudioSurface,StudioCanvas,StudioDesignTab,StudioToolbar,studioShapes,artifactOps}.tsx|ts`
· `api/test_studio_no_gutter_and_arrows.py` (renamed + inverted) · 10 updated gates ·
`docs/design/STUDIO.md` · `api/prompts/CHANGELOG.md`.
