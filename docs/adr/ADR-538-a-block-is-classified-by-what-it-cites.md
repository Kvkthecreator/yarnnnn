# ADR-538: A block is classified by what it cites — and the motion ceiling is declarative

> **Status**: **Accepted** (2026-08-09) — operator-ratified through the docs/studio service-model discourse; implementation delegated in full.
> **Date**: 2026-08-09
> **Dimension**: **Substrate** (Axiom 0 — what a block IS and what renders it) primary; a **Channel** consequence (which mounts can draw it). No Identity, Trigger, or Purpose change.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**: ADR-443 R4 (one component vocabulary), ADR-440 D5 (the reference projection), ADR-448 (the reference edge), ADR-511 (the conventional substrate), ADR-513 D3 (the locked share sandbox), ADR-417 (generation is rented, not owned), ADR-487 (the design system reaches the grammar), ADR-536 (the precedent: a kind the runtime could draw but the vocabulary could not name), FOUNDATIONS DP33 (collapse the category into data), DP31 (a citation binds a claim to its Source).

---

## 1. Context — the operator's question, and what the audit found

The operator, comparing yarnnn's authored deck against a Claude Design artifact
(2026-08-09): *"right now, they are mostly flat, or images, or svgs… I notice
that there are dynamic and animated. I'm thinking how we should fundamentally
approach this."*

The audit that followed produced three facts, two of them defects.

**(a) `chart` is mis-wired, and it is the actual "flatness."** `STUDIO_BLOCKS["chart"]`
is filed `group: "data"` and describes itself as *"An authored SVG chart in
./assets/, cited by reference"* — it cites a **rendered picture**, not the data.
It also sits in `MEDIA_BLOCK_KINDS` beside `figure` and `gallery`, which is the
structural confession: the registry already classifies it as media while the
group label calls it data. The consequence is exact — when the underlying
numbers change, **nothing happens**. The chart is a photograph of data.

The live substrate confirms it (query at `main`, 2026-08-09):

| Probe | Count |
|---|---|
| Artifacts holding `data-block="chart"` | 15 |
| Artifacts holding `data-block="metrics"` | 15 |
| Artifacts holding `data-block="table"` | 1 |
| **Artifacts holding `data-ref-kind="table"` (a cited table)** | **0** |
| **Artifacts mentioning a `.csv`** | **0** |

And the two real chart blocks (`operation/prd-for-yarnnn/document.html`) cite
`./assets/philosophy-chart.svg` and `./assets/philosophy-donut.svg` with
**`data-ref-rev=""`** — unpinned. Their data exists only as prose in the `alt`
attribute (*"Attribution & Versioning (100%), Substrate-First Architecture (85%)…"*).
A number that lives only in alt text is not a claim the workspace can defend,
which is DP31's concern precisely.

**(b) The cited-table edge is shipped and correct — and unused.** `projection.ts`
resolves `data-ref-kind="table"` (or any `.csv` ref) through `csvToTableHtml`,
with a pinned-revision fallback when the living path dangles, a visible broken
marker when both fail, and **no pin write-back** (reads must not write). It runs
in every mount. It is the reference implementation of everything this ADR wants —
and zero artifacts use it. The mechanism is not missing; the *vocabulary pointed
the wrong way*.

**(c) The motion ceiling was never measured.** The working assumption in the
discourse was "no motion." That was wrong, and the correction came from the
operator: the Claude components are *"dynamic, much like components of a web
landing page style html."* Measured rather than assumed (§2), the true ceiling
is **no JavaScript**, which is a very different line — and a much higher one.

## 2. The receipt — what actually survives `sandbox=""`

Every mount that a reader sees runs a bare `sandbox=""` iframe: the Web Viewer
(`viewers/index.tsx`), the paged navigator's thumbnails, and — decisively — the
**public share link** (`app/s/[token]/page.tsx`), whose own comment states the
constraint: *"There is no server-side sanitizer, so the sandbox IS the boundary."*
Only the Studio canvas runs `allow-scripts`, and deliberately without
`allow-same-origin` (its runtime speaks only by `postMessage`).

Driven in a real browser against that exact grammar (2026-08-09):

| Probe | Result |
|---|---|
| `<script>` mutating the DOM | **blocked** — the marker never changed (`no-js`) |
| `@keyframes` opacity/transform on an element | **ran** — sampled at two instants, visibly different |
| SVG `stroke-dashoffset` draw-in | **ran to completion** |
| Parent `contentDocument` access | **null** — same-origin denied |

**The ceiling is therefore: CSS-declarative motion is fully alive in every mount;
JavaScript is dead in three of the four.** A script-driven component would work
while its author edits it and be inert everywhere the work is *seen* — including
the share link, which is the mount that carries the product's value outward.

## 3. Decisions

### D1 — A block is classified by what it CITES and what RENDERS it, never by how it looks

The group label becomes a rule with a test, rather than a topic:

| Group | The rule | Members |
|---|---|---|
| **`data`** | cites a **source**; a projection renders it | `table` · `chart` (D2) |
| **`content`** | styled HTML, authored inline; the kernel renders it | prose · heading · list · numbered · checklist · quote · callout · toggle · divider · button · `metrics` · **`component` (D3)** |
| **`media`** | cites a **picture**; the projection resolves it to a URL | `figure` · `gallery` |

The diagnostic, for any future kind: **what does it cite, and what draws it?**
A kind that cites a source belongs to `data` and must be projected. A kind that
cites a picture is `media`. A kind that cites nothing is `content`. A kind whose
group and citation disagree is mis-wired — which is what `chart` was.

**`metrics` is re-filed `data` → `content` by this ADR.** Writing the rule
surfaced a second instance of the same mis-filing the gate then caught: `metrics`
was grouped `data` while citing nothing (its numbers are typed into the markup,
`<strong>42%</strong>`). It fails D1's test exactly as `chart` did, so it is
corrected in the same motion. The group is a served display label with no code
branching on it, so this moves a palette heading and nothing else.

What is **not** delivered here is the valuable version: a metric that *cites a
cell* — a headline number that is a defensible, attributed claim. That needs
sub-file addressing, which the substrate does not have (the ADR-528 finding —
the substrate has no relationship to sub-file identity). Named as the honest
open question, not smuggled in.

### D2 — `chart` is re-cut to cite its data source (a sibling of `table`, not of `figure`)

`chart` cites a **`.csv`**, carries its visual intent as block attributes, and is
drawn by a projection function beside `csvToTableHtml`. It leaves
`MEDIA_BLOCK_KINDS` — it is no longer a picture, so the media-grain tokens
(`height`/`fit`) no longer apply to it; `size` continues to reach it as a
`block-staged` object.

**This is not an ADR-417 reversal.** ADR-417 retired *generation* — an owned
engine that manufactured pictures (matplotlib, image, video), on the principle
that generation is rented, not owned. Projecting the workspace's own cited
substrate into a visual is a different act, and it is one the system **already
performs**: `csvToTableHtml` has shipped in the surviving projection module
since ADR-440 D5. A chart renderer beside it is the same class of act as the
table renderer, not a new engine, and it rents nothing.

**Migration is by-use, not by sweep** (the ADR-536 precedent). The two live
SVG-citing charts continue to render exactly as they do today: they are
`<figure>` elements with an `<img data-ref>`, and the projection's media path
resolves that markup regardless of the block's declared kind. They are
`figure`-shaped content wearing a `chart` name, and they become honest on their
next authored write. No sweep, no dual-run write path, no compatibility alias.

### D3 — A `component` kind: composite, declarative, motion-capable

The Claude-artifact components the operator pointed at (a bordered card with a
label row, icon/name/phrase/pill rows, a footer line) are **styled HTML**. They
need no new architecture — they need vocabulary. `component` is one row: a
container with typed child rows, drawn by kernel CSS and themed by the design
system's tokens (ADR-487), exactly as `metrics` and `checklist` already are.

It is `content`: it cites nothing. It is `apps: ("studio",)` — a composed
landing-page/deck object, the same reasoning ADR-528 D5 applied to `callout` and
`toggle`, and for the same reason (Docs is the flow/caret medium; Google Docs
has no equivalent).

### D4 — Motion enters the kernel as DECLARATIVE ONLY, and is refused as script

The kernel CSS gains motion for the first time (it holds no `animation`,
`transition`, or `@keyframes` rule today), bounded to what §2 proved survives
every mount:

- **Permitted**: `@keyframes`, `animation`, `transition`, `:hover`/`:focus-within`,
  and SVG-internal animation on a cited `.svg`.
- **Refused**: `<script>` in substrate, and any component whose *legibility*
  depends on one. Not a taste judgment — it renders in one mount of four, and
  the three it fails are the ones a reader uses.
- **Mandatory**: every kernel motion rule sits under a
  `@media (prefers-reduced-motion: reduce)` guard that disables it. Motion that
  cannot be turned off is an accessibility defect, and the kernel is the only
  place this can be guaranteed once for every artifact.

The refusal is recorded as a **falsifier**, not a permanent law: if a mount ever
gains a server-side sanitizer, the script question may be reopened on that
evidence. Until then the sandbox is the boundary, and the boundary is the answer.

## 4. What this amends

| Canon | Change |
|---|---|
| ADR-443 R4 | The one component vocabulary gains a classification *rule* (D1). The vocabulary stays singular and stays one home. |
| ADR-448 | The reference edge gains its second `data` consumer (`chart`). Mechanism untouched. |
| ADR-511 | `component` is a conventional-substrate kind like any other — annotation, not schema. Untouched otherwise. |
| ADR-513 D3 | Re-affirmed and now load-bearing in the block vocabulary: the locked sandbox is why D4 refuses script. |
| ADR-417 | Explicitly NOT reversed — §D2 states the generation/projection line. |
| `STUDIO_KERNEL_CSS_VERSION` | 15 → 16 (motion primitives + the `component` rules + the reduced-motion guard). Additive; the retrofit cannot alter an artifact holding neither kind. |
| `MEDIA_BLOCK_KINDS` | `chart` leaves the set (D2). |
| STUDIO.md · GLOSSARY | The three-group rule (D1) documented with this ADR. |

## 5. Consequences

**Positive.** The registry's groups become a rule with a diagnostic rather than a
topic label, so the next kind resolves without a debate. The system's flattest
block becomes its clearest moat expression: a chart that stays true to an
attributed, versioned, walkable source is a thing a workspace without a commons
structurally cannot draw. Composite components arrive as vocabulary rather than
as an engine, and the motion ceiling is set by measurement instead of assumption.

**Costs, stated.** `chart`'s re-cut leaves two live artifacts holding the old
SVG-citing shape; they render correctly but their declared kind is provisional
until their next write (accepted — migration-by-use, the ADR-536 precedent).
`metrics` remains uncited, so the most viscerally valuable case (a KPI that is a
defensible claim) is **not** delivered here and waits on sub-file addressing.
The `component` row is the first kernel motion, so the reduced-motion guard is
now a permanent maintenance obligation on every future motion rule.

## 6. Falsifiers

1. **The motion ceiling.** If a `@keyframes` rule in the kernel is ever observed
   NOT running inside a `sandbox=""` mount, D4's premise is wrong and the
   component vocabulary must degrade to static. *(Read before any widening.)*
2. **The chart re-cut's value.** If, one quarter on, no artifact cites a `.csv`
   through `chart`, then the data-projection thesis is unproven by use and
   `chart` should be honestly re-merged into `media` rather than kept as an
   aspirational row. The current reading is the honest baseline: **0 cited
   tables, 0 CSVs** — this ADR is a bet that the vocabulary was the blocker, and
   that bet is falsifiable.
3. **Script refusal.** If a mount gains a server-side sanitizer, D4's refusal is
   re-arguable on that evidence and should be re-opened rather than inherited.

## 7. The one-line statement

**A block is classified by what it cites and what draws it — so `chart` cites its
data, components are declarative HTML with motion the kernel guards, and script
is refused because three of the four mounts a reader uses cannot run it.**
