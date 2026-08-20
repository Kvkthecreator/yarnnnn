# ADR-586 one-door insert click-pass — run 1 (2026-08-19)

**Instrument**: chrome-devtools MCP, one isolated context (`owner`); substrate
half by `psql` against the live DB (the authoritative reading — the API is a
separate origin from the web app, so page-context authed reads were not the
instrument this run).
**Principal**: owner `kvkthecreator@yarnnn.com` (`67c5c637…`), sole member of
rig workspace `bf5b25a9…` — identity asserted from the app's own Workspace
Settings pane AND the `auth.users`/`workspaces` join, not from the login step.
**Subject commits**: `af92564` (ADR-586 build) · `d476dc2` (583) · `4d630b0`
(581 D4). In-run fix: `d10c092`.
**Baseline (pre-mutation)**: deck `deck.html` 17651 B @ 2026-08-04; flow
`untitled-document-3/document.html` 26497 B @ 2026-08-10; `*.component.html`
count = **0**; workspace images = **0**.

## Verdict: PASS with ONE defect found and fixed in-run (`d10c092`)

Every category of the door was driven on a real deck and a real flow doc, both
halves observed per step. One real defect surfaced — an ungrammatical composed
header on every block-selected open — fixed, gated, falsified, pushed.

## Scope — what this run does NOT cover

- **The in-frame right-click gesture itself.** `projection.ts:1069` handles
  `contextmenu` INSIDE the `sandbox="allow-scripts"` opaque-origin canvas. A
  real right-click cannot be synthesized into it (playbook §2 ceiling). The
  parent-side half — positioning, tier expansion, re-measure — WAS driven, by
  posting the runtime's own `yarnnn-context-menu` contract with bottom-edge
  coordinates. The frame's own hit-testing/grain-walk is **inferred from source**.
- **Logo-row height preset**: unreachable on this rig — 0 images in the
  workspace, so the multi-pick has nothing to pick. The picker's empty state WAS
  driven (it teaches correctly). The preset itself is **not run**.
- Single principal only; no member/grant dimension (the door is owner-scoped
  chrome — no permission fork under test).
- Deck medium tested at 1470px and 560px; flow medium at 1470px only.

## Step verdicts

| # | Step | DOM half | Substrate half | Verdict |
|---|---|---|---|---|
| 1 | Deck → `[+ Add]` opens the rail | rail = New slide · Components · Text · Media · Data; **New slide leads** (medium ordering); header "ADD — INTO SLIDE 1"; `[Update]` disabled with a reason | — | **PASS** |
| 2 | Gallery scrolls | `overflow-y-auto`, 729px content in 386px box (clipping is scroll, not truncation) | — | **PASS** |
| 3 | Components gallery | Divider · Button · Component · Metrics · **Stat · Comparison · Timeline · Person** (581 D4) + library empty state | `*.component.html` = 0 (matches the empty state) | **PASS** |
| 4 | Insert a Stat | renders "42% / label / ▲ 8% vs last quarter"; delta themed green (527 palette marks); lands in **Slide 1** as the header promised; strip thumb updates | `deck.html` 17651 → **35293 B**, `updated_at` 12:07:20, `data-kind="stat"` present | **PASS** |
| 5 | Right-click near the bottom edge | posted at page y=**751** (vh 780); menu drew at top=647/bottom=772 — **flipped up**, on-screen | — | **PASS** (parent half; see scope) |
| 6 | Tier expands at the edge | Components tier opened INLINE: 8 kinds, 8 schematic thumbs; box 125→**352px**, repositioned 647→**421** top; `overflowsBottom:false`, `offTop:false` | — | **PASS** — the re-measure-on-open claim |
| 7 | Block selected → `[Update]` | `[Update]` enables, description flips to "Update the selected block…"; the ONE block-acts menu opens with **Update tier pre-expanded** (Move up/down/Rewrite visible), Ask collapsed; `Rewrite…` badged **• AI**, mechanical rows unbadged | — | **PASS** |
| 8 | Properties for a composed block | breadcrumb `Slide 1 › Area › Stat` (Stat terminal); pane offers WIDTH/ALIGN/**TONE**, no delta control | — | **PASS** (see withdrawn finding) |
| 9 | Narrow window (560px) | toolbar collapses to icons (titles retained); door renders as `fixed inset-x-0 bottom-0 max-h-[70vh] rounded-t-lg` — full-width, bottom-pinned, **same category list**, 3-up thumb grid, tone-aware (section-header thumb dark) | — | **PASS** — one component, class fork |
| 10 | Flow doc medium ordering | rail leads **Text**, no Slide category at all; Add title adapts ("a component, text, media, or data") | — | **PASS** |
| 11 | Logo row | picker mounts and teaches: "No images in the workspace yet — drop one into Files, or ask the chat for an SVG." | images = 0 | **PASS** (empty state only — preset NOT run) |
| 12 | 583: lane composes a component | "Designer is working…" (562: the app's resident is the engine) | `operation/components/pricing-tier.component.html` **absent → present**, 5056 B, ~40s. Contract: 0 `<script>`, 1 `<style>` scoped under the single root, 0 `data-block-id`; every hex/rgba is a `var(--…, fallback)` — the two bare `rgba()` are box-shadow (geometry, freed by D1) | **PASS** |
| 13 | 583: appears as "shared" | gallery row `pricing-tier` + **shared** marker, titled with its path; empty state gone | — | **PASS** |
| 14 | 583: insert cites directly | no picker hop (`anyPicker:false`); component renders live in the artifact with its own scoped CSS + workspace accent | `document.html` → 33855 B; `data-ref="operation/components/pricing-tier.component.html"`, `data-ref-kind="component"`, `data-ref-rev="c8adce97…"` — pin **matches the head revision**; attribution `member:67c5c637… via anthropic/claude-sonnet-4-6` (the WHO seam) | **PASS** |
| 15 | 583: edit source → citation follows | after reload the artifact renders **GROWTH / $79** | source head → `4296cd1b…` (`pt-plan">GROWTH`, `pt-price">79`); artifact's stored pin **still `c8adce97…`** | **PASS** — D4's "reference, never copy": the pin is the dangling-citation FALLBACK, not a freeze |

## Finding 1 — the named target did not compose: "ADD — INTO AFTER THE SELECTED BLOCK" (fixed `d10c092`)

**Observed** on the bottom sheet with a block selected, then reproduced
independently on the **flow** medium ("Add — into after the heading") — one
header serves both housings and both media, so this was every block-selected
open everywhere.

**Mechanism**: `StudioBlockInsertMenu.tsx` hard-coded the preposition
(`Add — into {targetLabel}`) while `resolveInsertTarget` returned MIXED
grammar — three branches yield a noun phrase that reads correctly after "into"
("slide 2", "this slide", a slot), but the block branch yields a PREPOSITIONAL
phrase (`after the ${blockKind}`). Prefixing that composed "into after the stat".

**Fix**: each resolver branch carries its own preposition; the header states the
label verbatim. Notably, the resolver's own comment block already recorded that
a label naming a place different from the landing is the failure it exists to
prevent — this is the same class one layer up: the label was RIGHT, the
composition was not.

**Gate**: `test_adr586_one_door.py` 27→**31**. Two new checks, both falsified
against real breaks: restoring the prefix (the actual shipped defect) → red;
stripping one branch's preposition → red. The resolver body is brace-bounded,
not window-sliced.

**Collateral**: `test_adr509_insert_route.py` pinned the literal
`"— into {targetLabel}"` and so read this CORRECTION as a violation — the
stale-spelling-anchor trap this repo keeps paying for. Re-anchored on the wired
`{targetLabel}` interpolation; falsified by deleting the destination outright.

## Withdrawn finding — "the Properties pane shows the container, not the selection"

Suspected at step 8: with the Stat selected, the pane header read
`slide 1 › Area` and offered LAYOUT/WIDTH/ALIGN. **Withdrawn.** `pathChain` is
the ANCESTOR path (the selection excluded by construction), so `slide 1 › Area`
is the correct path TO the Stat, and the bottom breadcrumb carries the terminal
(`Stat`, styled `font-medium text-foreground`). The offered controls are
ADR-581 D4's stated ruling for composed kinds — "the existing tier + tone
token", with no delta control because delta is what content decides. Conforming
behavior; recorded so the next session does not re-derive the suspicion.

## Baseline restoration

**Not restored — deliberate.** This is a disposable rig; the mutations are the
receipts (a stat on `deck.html`, a component file + its citation). Guardrail
re-asserted: the live workspace `d5b9029b…` (`kvkthecreator@gmail.com`) was
never touched — every query and every gesture was scoped to `bf5b25a9…`.

## Deltas not caused by this pass

`next build` reports **172/172** pages against a 171/171 baseline. Not mine —
this run touched no routes; a concurrent lane added a page. Named rather than
silently absorbed.

---

## Addendum — run 2 (2026-08-20): the FLYOUT recut, probed live

The operator refused the inline-tier feel and supplied the reference shape
(Figma's `Move to page ▸`). D4 had ALREADY specified flyouts; the build had
substituted inline tiers behind a positioning note, now withdrawn in the ADR.
Shipped `671f6da` (+ `cd18845` anchor hardening) and **probed on production**
after the deploy landed — the probe was the running page reading its OWN loaded
chunk for the flyout class, not a guess at timing (two earlier watchers measured
nothing: one polled for a bot-challenge string, one grepped a URL that 308s).

| # | Step | Measured | Verdict |
|---|---|---|---|
| 16 | Bottom-right right-click, open a tier | parent HELD at top=647/left=1029/h=125 (was 647→421, h 125→352). Flyout at left=802–1032 — **flipped left**; top=551–772 — **shifted up**; all four overflow flags false | **PASS** — the jump is gone |
| 17 | Gallery contents in the flyout | all 8 component kinds + 8 thumbs (`BlockThumb` draws DIV schematics, so an SVG count of 0 is correct — the first probe looked for the wrong element and was withdrawn) | **PASS** |
| 18 | Two-level nesting (menu → Update → Turn into) | Update panel left=724–922; Turn-into left=919–1087, cascading right; both fully on-screen; `• AI` badge intact on Rewrite | **PASS** |
| 19 | Narrow (560px) keeps INLINE tiers | 0 flyout panels; box grew 125→340px and re-clamped 647→437 — the pre-existing behaviour, deliberately preserved | **PASS** |

**Geometry harness** (`/tmp/flyout_geom.mjs`, asserts the four math lines are
present in source, then exercises them): centre · right edge · bottom ·
bottom-right (flips AND shifts) · panel taller than the viewport (clamps, scrolls
internally) — all five fit the viewport.

**Gates**: 586 31→36, all five new checks falsified one at a time against real
breaks — including restoring the old dep list, which reproduces the exact jump.
579 re-anchored (its Rewrite-before-Ask ORDER claim is unchanged; only the
landmark `{askOpen && (` moved) — the pinned-spelling trap, 4th firing this week.

**Still owed**: the hover-open behaviour is unjudged by the operator — hover
never CLOSES a tier (leaving toward the panel would dismiss what you are
reaching for), so moving down the menu opens each tier passed over. Figma
behaves this way; if it reads busy the fix is an open-delay, not structure.
`cd18845` (button anchor) was not yet in the deploy probed here — same geometry,
so the verdicts above stand for both.
