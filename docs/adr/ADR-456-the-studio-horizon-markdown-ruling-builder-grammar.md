# ADR-456 — The Studio horizon: the markdown ruling, the Notion/builder gap carve, and the wave plan

> **Status**: **Accepted** (2026-07-14, operator-ratified via the 2026-07-13→14 horizon discourse:
> "aligned in full … as you propose on the sequencing let's proceed"). The umbrella ADR for the
> Studio's next horizon across its three formats; **Wave 1 ships with this ADR**, later waves land
> as their own commits against the plan recorded here.
>
> **Wave 2 shipped** (2026-07-14, same-day): the Notion core — the inline format bar (B/I/code/link
> on a selection, in-frame chrome, `b`/`i`→`strong`/`em` normalized at the write door), slash-insert
> (`/` in an empty context → commit-exit → a filterable palette; empty block converts in place,
> non-empty inserts after; picker-backed kinds stay in Insert ▾), and turn-into (`convertBlock` —
> id + tokens survive, citations refuse to flatten, text kinds only). FE-only: the registries and
> the posture are untouched. Gate `api/test_adr456_studio_wave2.py`. *Post-ship operator note: the
> slash-insert interaction wants polish/refactor — named fast-follow, post-stabilization.*
>
> **Wave 3 shipped** (2026-07-14, same-day): the builder look. (1) **Cited backgrounds** —
> `data-ref` + `data-ref-kind="background"` on the page element; the projection materializes
> `background-image` (inline style never enters the source); `data-scrim`/`data-bg-pos` tokens
> (new `page-bg` applies value); set/removed from the Design tab's page scope. (2) **The `page`
> layout** (D4) + its band family (hero · content · feature-grid · testimonial · cta · footer).
> (3) **The theme contract** — five kernel-consumed variables (`--ink`/`--paper`/`--muted`/
> `--accent`/`--radius`), named in the derive recipe; a read-only theme panel in the Design tab.
> The **mechanical var-editor is deferred by decision**: it requires widening the
> `PATCH /workspace/file` editable-prefix allow-list to design-system folders — a permission-
> surface change that gets its own discourse, not a wave rider. Kernel CSS **v4** also fixes two
> pre-existing defects found in recon: the **skin-stomp** (the projection resolved INTO the marked
> `<style data-skin data-ref>` element, replacing an applied design system's CSS with the
> manifest's escaped text — latent since ADR-449) and the **phantom `.cols`** (document/article
> two-column arrangements referenced a class only the deck skin defined — the generic non-slide
> `.cols` now lives in the kernel element). Gate `api/test_adr456_studio_wave3.py`.

**Date**: 2026-07-14
**Dimension**: Substrate (Axiom 1 — one canonical source format, projections at the boundary) +
Channel (the palette/gallery/Design-tab growth) + Mechanism (registry growth vs new capability vs
refusal — the carve is the decision)

**Extends**: ADR-443 (the axiomatic model — R1/R5 are the rulers used here), ADR-447 (arrangement
registry growth), ADR-449 (design systems as the theme layer), ADR-450 (recipe registry growth),
ADR-453 (token families + kernel-CSS retrofit), ADR-455 (document-grain tokens).
**Preserves**: ADR-417 (no owned generation/rendering engine), ADR-406/286 (no CRDT — the revision
is the atom), ADR-444/446 (one mechanical door), ADR-222 (kernel names categories, never instances).

---

## 1. Context — the three-format horizon question

The operator set the next-horizon vision: **documents** should become much more Notion-like in
full (including the question whether documents should be markdown-AND-html native); **deck +
article** should stay html-native but move toward Squarespace/Wix builder capability; and the
work should be divided honestly across the filesystem-native substrate, the AI (bound lane +
derive recipes + design systems), and the kernel registries. The assessment ran against the
shipped stack (ADR-440→455) and was ratified in full.

## 2. Decisions

### D1 — The markdown ruling: one source, projections at the boundary

**HTML stays the sole canonical source for Studio artifacts. Markdown is an interchange
projection, never a second source format.** A dual-native source violates ADR-443 R1 not in
letter but in structure: every layer shipped since (block ids, citation pins, arrangements,
tokens, the two marked style elements, the direct-edit runtime that joins projection→source by
block id) is annotation-on-DOM machinery markdown cannot carry — an extension syntax would be a
shadow model in a costume. Notion itself is the precedent: its internal model is a proprietary
block tree; markdown is only its import/export currency. Therefore:

- **Import (md→html)**: a creation-time up-projection ("New document from this .md" — a Studio
  landing path beside Learn-from). The kernel already owns the parser (`compose/engine.py`,
  python-markdown): heading-led runs → `prose` blocks, blockquote → `quote`, task lists →
  `checklist`, tables → `table`. Mechanical where deterministic; a lane turn where judgment is
  needed. **Wave 4.**
- **Export (html→md)**: a down-projection at the boundary, sibling of publish/exports (already
  PROJECT territory, ADR-443 D2). The block grammar maps to md constructs deliberately;
  lossiness (tokens, arrangements, skins) is what interchange means. **Wave 4.**
- **The OS division stands**: `.md` is the substrate's prose currency (mandates, briefs, memory,
  derive outputs); `.html` is the Studio's authored-artifact currency. The bridge is projection
  both ways; Studio is never bimodal.
- **Named-deferred**: a `markdown.editor` app claiming the `markdown` type beside
  `markdown.viewer` (the ADR-436 Open-With moment — textarea/CodeMirror-grade, never
  block-grade; Studio's machinery must not leak into it). This is the honest answer to the
  coming "why can't I edit MANDATE.md with this nice editor?" — an app decision, not a Studio
  format decision.

### D2 — Documents: the Notion decomposition and the stop-lines

**Build** (grain-ordered): `toggle` block on native `<details>/<summary>` (Wave 1 — the platform
already ships Notion's toggle, script-free) · **inline format bar** (bold/italic/code/link on a
text selection inside the edit runtime — *semantic* wrapping in `strong/em/code/a`, no collision
with the raw-color refusal; workspace-path links keep the living-reference thesis) · **slash-
insert** (`/` in an editing block → caret-anchored palette over the existing postMessage bridge →
the same mechanical insert op) · **turn-into** (`convertBlock(id, kind)` — registry-driven
content mapping, id preserved) — all Wave 2, all through the one door.

**Stop-lines (refusals)**: no block-as-page recursion and no arbitrary block trees (the shadow-
model gravity well; native `ul>li` nesting and toggle content are the allowed nesting) · no
databases/linked views (the `table` block citing workspace CSVs is the stronger primitive) · no
synced-block *mechanism* — Notion's synced block IS the `data-ref` thesis at block grain; when
demanded it arrives as a block-level citation, never a second mechanism (named-deferred) · no
keystroke CRDT (standing) · comments belong to the ADR-454 regroup (the `data-block-id` substrate
is what makes them possible; not this arc).

### D3 — Deck + Article: the builder-class carve

- **Registry-content** (rows + fragments + kernel CSS — Wave 1): more arrangements (deck
  `agenda · big-number · full-bleed · closing`; document `checklist-section · metrics-band`),
  `button`/`gallery`/`toggle`/`divider` blocks, `pad` page token, deck slide numbers (CSS
  counters, opt-in root token `pagenum`), responsive stacking for document/article multi-column
  bands (a deck slide is a fixed 16:9 stage — exempt).
- **Mechanism** (bounded, Wave 3): **background-image citation** — authored form is `data-ref` on
  a *section* plus scrim/position *tokens*; the **projection** materializes `background-image`
  with the signed blob URL exactly as it swaps `img src` today; inline style never enters the
  source; export/publish reuses the same resolution. **Theme editing** — never an artifact-side
  second styling path: (a) harden the custom-property contract the kernel CSS understands
  (palette / type scale / spacing / radius — the shape the design-system recipe already emits),
  (b) the Design tab's document scope edits the **design-system files themselves** through the
  existing verbs, so every artifact wearing the system re-renders (the living-reference thesis
  where Wix has per-site settings).
- **Refusals engaged**: JS carousels (CSS scroll-snap is the offer), forms, scroll animations,
  per-breakpoint editing (intrinsically responsive arrangements are the answer), web-font CDNs
  (self-contained artifacts; system stacks + design-system `font-family` declarations;
  workspace-asset `@font-face` is named-deferred, not refused forever).

### D4 — The fourth layout: `page`

The Wix/Squarespace ambition gets its own layout rather than stretching `article` (editorial
prose) or `deck` (a spoken-over stage): **`page`** — landing/one-pager (hero → feature grid →
testimonial → CTA → footer), one registry row plus its arrangement family. It lands **with the
background mechanism (Wave 3)** — a page layout without heroes is not credible. This is where
the philosophy's own word "pages" (the six-axiom manifesto) lands.

### D5 — The division of labor + two boundaries

**Kernel ships grammar** (kinds, arrangements, tokens, kernel CSS, citation-resolution rules,
the md↔html projections, the one door — categories, never instances of taste). **AI authors
instances** (design systems, imports needing judgment, drafts, section fills — and anything the
registries don't cover *yet*: the bound lane can already write bespoke builder-class sections on
a metered turn; registry growth converts recurring taste into free mechanical acts, it never
gates capability; `landing-page` is the natural next derive recipe). **The member composes
mechanically, free** (a structural act never needs a metered turn).

Named-deferred boundaries (both mirror ADR-450 D1): **workspace-authored arrangements/snippets**
(the "save this section for reuse" act — user-territory substrate, not kernel rows) and the
**markdown editor app** (D1).

### D6 — The wave plan

- **Wave 1 — registry + kernel CSS** (ships with this ADR): the D3 registry list + the `toggle`
  block + responsive stacking + slide numbers. Detail in §3.
- **Wave 2 — the Notion core**: inline format bar → slash-insert → turn-into (D2).
- **Wave 3 — the builder look**: background-image citation + scrim/position tokens → the `page`
  layout + hero/CTA/feature arrangements → theme-contract hardening + Design-tab theme editing
  (D3/D4).
- **Wave 4 — interchange** (demand-gated): md import at creation/learn-from · md export at the
  boundary, sequenced with the publish arc it belongs to (D1).
- **Deferred ledger** (additions to the standing one): markdown editor app · block-level
  citations (synced-block analog) · workspace-authored arrangements/snippets · workspace-asset
  web fonts · multi-block select. (In-frame drag · snap handles · Undo/History · navigator slide
  context-menu stand unchanged from ADR-453 D7.)

Waves 1 and 2 are independent; Wave 3 has the internal dependency (mechanism before heroes);
Wave 4 floats.

### D7 — One reconciliation line for ADR-443

The "format-agnostic" axiom and ADR-447 D7.5 (type fixed at creation) are reconciled as already
implicitly shipped: **the axiom survives as block portability** — the posture still teaches the
lane-performed layout change (every block and id preserved); what D7.5 deleted was the
*mechanical* type toggle. Type change is a judgment act, not a view switch.

## 3. Wave 1 — the shipped scope

- **Blocks** (+4, `STUDIO_BLOCKS`): `divider` (`<hr>`) · `toggle` (`<details>/<summary>` —
  script-free, native) · `button` (a styled `<a>` CTA, themed via the palette variables) ·
  `gallery` (a grid of **cited** figures — media group).
- **Arrangements**: deck `agenda · big-number · full-bleed · closing` (closing reuses
  `data-tone="inverse"`; full-bleed's media slot fills the stage); document
  `checklist-section · metrics-band`.
- **Tokens** (+2, `STUDIO_TOKENS`): `pad` (page grain — Tight/Airy; absence = the layout
  default) · `pagenum` (new `document-deck` applies value — the artifact root, deck only;
  slide numbers via CSS counters).
- **Kernel CSS v3** with a **mechanism ruling recorded**: *arrangement- and block-kind CSS lives
  in the versioned kernel element, not the layout skin* — the kernel element is the only style
  that retrofits into existing artifacts (ADR-453 D2), so new kinds/arrangements light up in old
  artifacts on first touch. Order discipline inside the sheet: block/arrangement rules first,
  token rules last (a token wins at equal specificity). Responsive stacking scoped
  `[data-arrange]:not(.slide) .cols`.
- **FE**: the Insert palette routes `gallery` → a multi-select image picker (N cited figures in
  one block, one revision); the Design tab gains the `document-deck` gate; the pointer runtime
  lets a **selected** toggle's `<summary>` click through so the native open/close works on the
  canvas (first click selects, second click acts); `button` hrefs stay navigation-safe (the
  pointer runtime already `preventDefault`s canvas clicks).
- **Gates**: `api/test_adr456_studio_wave1.py` (new) + the exact-set/version pins in
  `test_adr443` / `test_adr455` updated.

## 4. Cascade

`docs/design/STUDIO.md` (blocks/arrangements/tokens tables + the md ruling + the wave plan
pointer) · ADR-443 (amendment banner: D7 reconciliation + Wave-1 vocabulary growth) ·
`api/prompts/CHANGELOG.md` (the posture derives from the registries — new kinds/arrangements/
token families reach the lane).

## 5. The one-line statement

**One source format with projections at the boundary, one grammar grown by rows not mechanisms,
three bounded new capabilities (backgrounds, inline formatting, slash-insert) and a fourth
layout — everything else is either free registry growth, AI-authored taste, or a refusal we
already ratified.**
