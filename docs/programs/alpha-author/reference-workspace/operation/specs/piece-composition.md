# Piece Composition Spec

Spec for composing a **published piece** — the alpha-author program's first *production* (non-audit) deliverable. Every other spec in this directory is an audit spec (the Reviewer evaluating substrate); this one governs the Reviewer **producing** the artifact an operator publishes.

The Reviewer reads this spec when authoring or revising a piece at `/workspace/operation/authored/{piece-slug}/`. It is the discipline for *where structure lives in a piece* — when a passage carries its argument better as a section-kind (table, flow, callout) than as prose, and when it does not.

> **There is no "rich" mode and no "enrich" step.** Structure is native to authoring. The Reviewer does not write flat prose and then separately decorate it. It writes the piece, and the judgment "this contrast is a comparison-table; this pipeline is a flow" is part of the *same* authoring act. This spec teaches that judgment; it does not introduce a second pass. (Derived: compose-rewiring discourse 2026-06-10 §3 projection axiom; design-memo `richness-soak-yarnnn-author/DESIGN-MEMO-rich-piece.md`.)

## The thesis: structure made visible, measured by argument-fidelity

A composed piece is one where **the structure the author is already reasoning in is rendered in the form that carries it** — a table for a comparison, a flow for a pipeline, a matrix for a status set, a callout for the plain-language gloss. The failure mode to author against is "add assets to make it look produced." That is the gameable proxy (more assets ≠ better) and this spec rejects it by construction.

**The gate — applied per candidate section, inside the authoring act:**

> *Could this be a paragraph without loss?* If there is no clear **no**, it stays prose.

A section-kind earns its place only when it carries the argument *better than prose would*. A piece with one well-placed diagram is composed better than one with five decorative charts. The measure is **argument-fidelity-gain**, never asset count. A loop optimizing asset count fails this gate by construction — which is the point.

## When does this fire

Structure is decided as the piece is authored or materially revised. This is **not** keyed to ship, cadence, or a clock — it is keyed to *the piece's structure being decided or changed*. The expensive judgment (which prose → which kind, which sections warrant a designer-rendered asset) happens once, deliberately, and is **idempotent**: re-run only when the piece materially changes, because a piece's structure changes rarely.

The HTML render is **never** produced here. It is a projection pulled at the consumption boundary (a surface opening the piece, an export, an email send). This spec produces *substrate* — `sections/*.md` + `sys_manifest.json` + asset URLs — never HTML. (Projection axiom: compose-rewiring discourse §3; ADR-213.)

## The palette, ranked by argument-fit for this voice

The corpus voice (per `_voice.md`) is **claim-first, architecture-grounded, em-dash-fluent, contrast-heavy**. Some kinds fit that voice; some fight it. The ranking *is* the anti-gaming structure:

### Tier 1 — earns its place often (the voice is built on these)
- **`comparison-table`** — the voice lives on A-vs-B contrasts (dashboard vs file, capability vs context, episodic vs accumulative). The single highest-fit kind. When a passage contrasts two things point by point, it is a table.
- **`mermaid`** (flow / system diagram) — pipelines, loops, data-flow described in prose where *the flow is the argument*. When the prose narrates "step 1 → step 2 → step 3" or "A reads X, B does not," it is a diagram.
- **`callout`** — the "what this answers (plain language)" gloss. When a passage is the plain-language restatement of a dense claim, it is a callout.

### Tier 2 — earns its place sometimes (only with REAL substrate data)
- **`metric-cards`** — only when there are *real* headline numbers the piece reports on. **Never for invented stats.** Every card's number must trace to a **Source** (the `source_ref` of the observation that grounded it — a repo path, a URL, the ground-truth file's reconciled value; ADR-357 / DP31), cited so a reader can verify it. A number that cannot be traced to a resolvable Source does not ship. (Trace to the Source — where the number came from in the world — NOT to the internal workspace file the distilled copy happens to live in.)
- **`status-matrix`** — for named-pattern sets (e.g. "3 failure modes," "4 flows"). Good fit, used sparingly.
- **`trend-chart`** — only when there is a *real* series to plot (e.g. a piece visualizing the workspace's own accumulation curve — genuinely novel and honest because the data is real substrate). **Never decorative trend lines.**

### Tier 3 — rarely earns its place in this voice
- **`image`** (generated text→image) — the voice's argument is architectural, not evocative. A generated hero image is the *most* likely to be decoration-not-argument and the **highest Goodhart risk in the palette**. At most **one** optional hero per piece, and only when it carries a concept no diagram-kind can (rare). When in doubt: no image.
- **`entity-grid` / `data-table` / `timeline`** — fit specific content (entity rosters, dense tabular data, chronologies) that argument-essays rarely have. Available, not default.

**The default spine is Tier 1 (comparison-table + mermaid + callout).** Reach for Tier 2 only with real data. Treat Tier 3 — especially generated images — as exceptional.

## How a piece gets composed (the authoring procedure)

1. **The Reviewer authors / revises the piece** from substrate — `_voice.md`, `_editorial.md`, `_entities.md` + the operator's declared piece intent in `profile.md`. The prose is written in voice.
2. **As it authors, the Reviewer decides structure** — per passage, applies the gate ("could this be a paragraph without loss?"). Where a kind carries the argument better, that passage becomes a section with a `kind:`. Where prose carries it, it stays a `narrative` section. This is the judgment that cannot be mechanized.
3. **For any asset-bearing section** (a `mermaid` diagram, a `trend-chart`, the rare `image`), the Reviewer dispatches the designer:
   `DispatchSpecialist(role="designer", brief="render a mermaid flowchart of the 4-step money-truth pipeline: fetch → compute → write → idempotency-check")`.
   The designer calls `RuntimeDispatch`, the asset lands, the designer returns markdown + asset URL.
4. **The Reviewer writes the substrate** to the authored piece's dated folder:
   - `sections/{n}-{slug}.md` — one partial per section, in order, prose written in voice.
   - `sys_manifest.json` — the section → kind map (`{title, sections: {slug: {kind, title}}, surface_type}`), plus `surface_type: "article"`.
   - asset URLs recorded in `manifest.json` (`files[]` with `content_url` + `role`).
5. **Compose is pulled when the piece is consumed** (a surface opens it, an export, an email) — section-kind dispatch renders each section in its form; the result is the composed article. The render is never produced here.

## Output target

The authored piece's dated composition folder (mirrors the report topology, under the **authored** root — not the reports root):

- Prose source (canonical, ADR-283): `/workspace/operation/authored/{piece-slug}/content.md`
- Composition substrate: `/workspace/operation/authored/{piece-slug}/{date}/sections/{n}-{slug}.md`
- Section map: `/workspace/operation/authored/{piece-slug}/{date}/sys_manifest.json`
- Asset manifest: `/workspace/operation/authored/{piece-slug}/{date}/manifest.json`

`content.md` stays the canonical prose source — authored by the agent as the operator's installed judgment (FOUNDATIONS:240; ADR-355), or by the operator when they choose to author/co-author as principal. Either way it is canonical and attributed via the revision chain (ADR-209). The composed piece is the **projection** of `{content.md's prose + the produced sections/assets}` — it is never a competing source of truth. (ADR-283 preserved — only the author of content.md is clarified, not its canonical status; projection axiom §6 D6.)

## The `sys_manifest.json` shape (canonical — match it exactly)

The composer (ADR-170 + ADR-213) reads `sections` as a **JSON object keyed by section slug** — NOT a list. Each section partial file is `{n}-{slug}.md` and its slug key in the manifest is `{slug}` (without the numeric prefix). The composer renders sections in the order they appear in the object. Required shape:

```json
{
  "surface_type": "article",
  "title": "Money-Truth As A File, Not A Dashboard",
  "sections": {
    "architectures-comparison": { "kind": "comparison-table", "title": "The Two Architectures" },
    "dashboard-failure-modes":  { "kind": "narrative",        "title": "Why The Dashboard Architecture Breaks Autonomy" },
    "money-truth-computation":  { "kind": "mermaid",          "title": "How Money-Truth Gets Computed" }
  }
}
```

The section partial for `architectures-comparison` lives at `{date}/sections/01-architectures-comparison.md`; its key in `sections` is `architectures-comparison`. **Do not write `sections` as a list/array** — a list shape (`[{slug, kind, ...}]`) is non-canonical and the composer cannot read it. Object-keyed-by-slug, rendered in declaration order, is the contract.

## Format: composed HTML *article*, not slides

The output form is a composed HTML **article** (`surface_type: "article"`) — sections stack vertically, each rendered in its kind, with the em-dash-fluent connective prose between the diagrams carrying the argument. The voice's strength is exactly that connective prose; slides would fragment it into bullet-shards and discard the connective tissue. Slides remain a legitimate *separate* derivative (via `repurpose`) if a piece ever needs a deck — never the default form.

## Quality criteria

- **Argument-fidelity per section**: every non-prose section passes the gate — it carries an argument the prose could not carry as well. A section that fails the gate is rewritten as prose, not kept for coverage.
- **Voice integrity**: the connective prose between sections is still the corpus voice (claim-first, em-dash-fluent per `_voice.md`). Structure must not fragment voice into bullet-shards. A composed piece that reads as voiceless scaffolding fails this criterion even if every section is individually justified.
- **Real data only for Tier 2, traced to Source**: every `metric-cards` number and `trend-chart` series traces to a resolvable **Source** (the observation's `source_ref` — where it came from in the world; ADR-357 / DP31), not merely to the internal workspace file the distilled copy lives in. No invented statistics. A claim or number with no resolvable Source does not ship.
- **Images are exceptional**: at most one generated `image` per piece, only when it carries a concept the diagram-kinds cannot. Default to none.
- **Idempotent**: the composition substrate is rewritten only when the piece materially changes. Re-running on unchanged prose produces the same sections.
- **Substrate, not HTML**: this step writes `sections/` + manifests + asset URLs. It does not call the render service. (Projection axiom — the render is pulled at consumption.)

## How a composed piece is judged (the eval criterion — anti-gaming built in)

For the richness-soak thesis read (does the author workspace produce composed pieces that beat the flat corpus, improving over tenure?), the criterion is **never** asset count:

- **Argument-fidelity vs the flat baseline**: take a strong existing flat post (control: `money-truth-as-a-file-not-a-dashboard`), have the author workspace produce its composed analog, and judge whether the composed version is *more legible / faster to grasp* without losing the argument. The flat corpus is the control; the comparison is direct and A/B.
- **Voice integrity**: is the connective prose still the corpus voice, or did structure fragment it? Richness must not cost voice.
- **Over tenure**: does the author's *structural judgment* improve — does it learn which kinds carry which arguments, place fewer decorative assets over time? This is the genuine self-improvement claim for the composition domain, and the honest, hard-to-game version.

**The gameable failure to watch for** (named so it can be designed against): a loop that maximizes asset-count or "coverage" while argument-fidelity drops. The criterion above measures the opposite of that by construction — which is *also* why this track stays separate from and non-contaminating to the alpha-author Goodhart probe (that probe tests loop alignment under a gameable signal; this track is designed so its signal is *not* gameable, by making argument-fidelity the measure).
