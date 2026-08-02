# ADR-511 Phases 1+2 — Studio click-pass, run 2 (the automatable half)

- **Date**: 2026-08-02 · **Session**: parallel lane, carry-over from the ADR-511 Phase-2 session
- **Principal**: `kvkthecreator@yarnnn.com` (OWNER, rig ws `bf5b25a9` — disposable, mutations real)
- **Environment**: LOCAL (`next dev` + local API on :8000 against live Supabase) — main @ 27b93dd
  (Phase 2 unpushed at run time; prod carries Phase 1 only). One isolated browser context.
- **Constraint honored**: synthesized input does not reach the sandboxed opaque-origin canvas
  iframe (fd705c0). This run covers the PARENT-DOM lanes only; the in-canvas half is the
  human checklist below.
- **Artifact**: `/workspace/operation/untitled-deck/deck.html`, created fresh via New → Deck,
  then Re-arrange → Two column on slide 2 (reproduces the shipped bare-`<p>` template case).

## Results (each with its receipt)

| # | Lane | Verdict | Receipt |
|---|------|---------|---------|
| A1 | Left rail: selected slide's card shows the structure tree — operator words, containers green, never "div" | **PASS** | DOM read of tree rows: `heading` (emerald container row) on slide 1; `heading · columns · main · prose · side · prose` on slide 2. Labels sourced from the file's own names (D8). Cosmetic note: the title template's slot is *named* `heading` (`data-slot="heading"`), so its container row reads "heading" — colliding visually with the block kind. Template naming, not a label-map defect. |
| A2 | Container row click → Design tab container scope | **PASS** | Scope header `HEADING` (resp. `COLUMNS`) + LAYOUT rows Padding/Gap/Align/Justify (bounded presets, no raw CSS pane — D7). |
| A3 | Layout preset click → ONE revision + canvas re-render | **PASS with finding** | One `POST /api/studio/artifacts/write` → head `bebfad15-02e1-4f78-8479-53756710f880`, message `Studio: layout ba9n1 container`, parent-pointered to the create revision. **FINDING-1 (fixed this session, 8b87379)**: the write pushed bare `display: flex` — axis flipped to ROW, title slide re-flowed horizontally (screenshot + head bytes both). |
| A4 | Block row → block scope, Position row | **PASS** | `POSITION` row with `In flow \| Positioned` chips (disabled while in flow, with the drag hint — enablement is drag-gated; drag itself is human-lane). |
| A5 | Normalize-on-load corrupts nothing; first write carries container ids | **PASS** | Create revision `08d54012` has bare slot divs (no ids); first write (`bebfad15`) persisted `ba9n1`/`b0net` — the declared D5 migration-by-use ride-along, receipted at both revisions. Render pre/post identical apart from FINDING-1. |
| A6 | The bare-`<p>` regression (two-column "Second column.") | **PASS** | After the arrangement write (head `fddcaeb6`), the formerly dead `<p>Second column.</p>` carries `data-block="prose" data-block-id="biuul"`; `.cols`/`.col`s stamped `bqbhy`/`bvl7q`/`bfptv`. |

## Finding-1 — fixed and re-verified live (commit 8b87379)

`setContainerLayout` needed a flex context for gap/align/justify and pushed bare
`display: flex` (row default) — every block-flow container flipped horizontal on its first
layout preset. Fix: push `flex-direction: column` with the flex context for non-row
containers; row containers recognized structurally (`.col` children); a container carrying
the pre-fix residue (`display: flex`, no direction) heals on its next layout write.

Live re-verify receipts: damaged `ba9n1` healed → head `c01f3c26`
(`display: flex; gap: 0.5rem; flex-direction: column`), slide 1 vertical again (screenshot);
`.cols` `bqbhy` → head `9f35690b` (`gap: 1rem; display: flex`, NO direction), columns still
side-by-side (screenshot). Gate: `test_adr466_mode_native.py` grew the axis assertion,
proven RED against the pre-fix source, then 73/73.

**Prod note**: Phase 1 (a08c876) is deployed, so the axis bug is live in prod until this
fix ships. Damage requires a member to have clicked a container layout preset; any damaged
artifact heals on its next layout write once the fix deploys.

## Pre-existing observations (not ADR-511 regressions, not fixed)

- Re-arrange replaces the heading and its id (`carriedBlocksOf` excludes
  `data-block="heading"` by design — slide 2's "First point" became the template's
  "Slide title", id `t2` → `blw6e`). Designed pre-511; whether heading text should carry
  is a product question for KVK.
- The deck template authors kicker + subtitle as `data-block="heading"` — three "heading"
  rows on the title slide's tree. Template authoring choice.

## Gate + build state at close

`next build` GREEN (full tree, clean run — earlier failures were a three-way `.next`
collision between this session's dev server/build and a parallel session's build, all
environmental). Studio gates GREEN: adr453/461/462/466/482/484/485/509 (py) + all 7 `.mjs`
gates from repo root. `test_adr480_flow_editing_grain.py` RED with the SAME three
pre-existing stale pins as the receipted baseline (F3 oneshot leak + 2 D1) — untouched.

## Scope of sign-off

- **web lane marked validated**: `next build` green over the whole tree + this click-pass
  over the STUDIO surface's parent-DOM lanes. NOT covered: in-canvas gestures (below),
  other sessions' UI work since 902c592 (landing mocks etc.).
- api / migrations / evals / claude-md lanes: NOT marked — other lanes' work, criteria not
  exercised here.

## Human checklist (KVK, one screen — the sandboxed-iframe half)

On any deck in Studio (prod after the fix deploys, or local):
1. Single click on text → caret (flow); first click on a deck block → box + 8 handles + frame label.
2. Click on column padding → green container selection + Design tab container scope.
3. Esc walks up: block → column → slide → clear.
4. Hover labels on containers use operator words (never "div").
5. Drag a block → "positioned" corner tag appears; Design tab "In flow" chip returns it.
6. "+ Add" in an empty region inserts prose / opens the media picker.
