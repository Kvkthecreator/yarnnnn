# Design memo — what is a *rich* YARNNN piece?

> **Status**: design memo, 2026-06-10. Pre-spec discourse for the author-richness track (operator chose "design memo first, then author the spec"). Hat-B (developer-surface reasoning that will produce a Hat-A bundle spec). **Not a spec — a memo to react to.** The spec it informs lands at `docs/programs/alpha-author/reference-workspace/operation/specs/` after sign-off.
>
> **The premise** (operator, 2026-06-10): YARNNN's blog corpus is 102 posts, all flat prose, *none made by YARNNN* — externally AI-generated under operator direction. The text is strong; it is also "text-heavy and flat." YARNNN ships a multi-modal asset + compose pipeline (audit-confirmed GREEN: chart/image/mermaid producers + section-kind rendering + designer-dispatch, all live) that the corpus never touches. The richness dogfood: make an alpha-author workspace produce *rich* pieces using YARNNN's own substrate, and prove (over tenure) they beat the flat hand-made corpus.

---

## §1 The thesis: richness is *argument structure made visible*, not decoration

The failure mode to design against is "add charts to make it look produced." That is the gameable-proxy version of richness (more assets ≠ better — your own Goodhart hazard). The memo rejects it.

The real opportunity, grounded in the actual corpus: **YARNNN's strong posts already have visual structure latent in the argument — the flat prose is hiding it.** Take `money-truth-as-a-file-not-a-dashboard.md` (a strong, representative post):

| What the prose does | What it *is*, structurally | Native YARNNN section-kind |
|---|---|---|
| "The Two Architectures" — A (dashboard) vs B (substrate file), contrasted point by point | a **comparison** | `comparison-table` |
| "predictable failure modes" — 3 named patterns (same-mistake repetition / drift unnoticed / operator-mediated calibration) | a **status set** | `status-matrix` or `metric-cards` |
| "How Money-Truth Gets Computed" — a 4-step deterministic pipeline | a **flow** | `mermaid` flowchart |
| Architecture A vs B *data-flow* ("the AI doesn't read the dashboard") | a **system diagram** | `mermaid` (AI-reads vs AI-doesn't-read split) |

Every one of those is an argument the prose *flattens into a paragraph* and a section-kind would *sharpen into a glance*. **A rich YARNNN piece is one where the structure the author is already reasoning in is rendered in the form that carries it** — table for a comparison, flow for a pipeline, matrix for a status set, chart for a trend, image only where an image genuinely earns its place.

**Corollary — the anti-gaming rule (built into the definition, not bolted on):** a section-kind is only justified when it carries the argument *better than prose would*. "Could this be a paragraph without loss?" → if no clear yes, it stays prose. Richness is measured by *argument-fidelity gain*, never by asset count. (This is the design-level guard against the Goodhart hazard the operator flagged: a loop optimizing "asset count" would fail this test by construction.)

---

## §2 The section-kind palette, ranked by argument-fit for YARNNN's voice

YARNNN's voice is **claim-first, architecture-grounded, em-dash-fluent, contrast-heavy** (per VOICE_AND_BRAND + the corpus). Some kinds fit that voice; some fight it. Ranked:

**Tier 1 — earns its place often (the voice is built on these):**
- **`comparison-table`** — YARNNN posts live on A-vs-B contrasts (dashboard vs file, capability vs context, episodic vs accumulative). This is the single highest-fit kind.
- **`mermaid`** (flow / system diagram) — pipelines, loops, data-flow ("the loop closes") are described constantly in prose; the flow IS the argument.
- **`callout`** (the "What this answers (plain language)" blockquote already in every post) — already used; formalize as a kind.

**Tier 2 — earns its place sometimes (when the data is real):**
- **`metric-cards`** — only when there are *real* headline numbers (a richness piece that reports on something measurable). NOT for invented stats. Risk: fabrication. Guard: cards must cite substrate.
- **`status-matrix`** — for named-pattern sets (the "3 failure modes" shape). Good fit, used sparingly.
- **`trend-chart`** — only when there's a *real* series to plot (e.g., a piece that visualizes the author workspace's OWN accumulation curve — which would be genuinely novel + honest, since the data is real substrate). NOT for decorative trend lines.

**Tier 3 — rarely earns its place in this voice:**
- **`image`** (Gemini text→image) — YARNNN's argument is architectural, not evocative. A generated hero image is the *most* likely to be decoration-not-argument. Allow ONE optional hero per piece at most, and only when it carries a concept the diagram-kinds can't (rare). This is where the Goodhart hazard is highest — flag it as the kind most likely to be gamed.
- **`entity-grid` / `data-table` / `timeline`** — fit specific content (entity rosters, dense tabular data, chronologies) that YARNNN essays rarely have. Available, not default.

**The design call this implies:** a rich YARNNN piece defaults to **comparison-table + mermaid + callout** (Tier 1) as its richness spine, reaches for Tier 2 only with real data, and treats Tier 3 (especially generated images) as exceptional. That ranking is itself the anti-gaming structure.

---

## §3 Format: HTML-composed article, NOT slides

The operator floated "in slides (html based which is our default)." Recommendation: **the rich piece is a composed HTML *article*, not a slide deck.**

- YARNNN's argument-dense voice is a *reading* experience — the reader follows a claim through contrasts and pipelines. Slides fragment that into bullet-shards and lose the connective tissue (the em-dash-fluent prose between the diagrams is the argument). The corpus's strength is exactly the connective prose; slides would discard it.
- The compose engine's section-kind rendering produces a *flowing article* (sections stack vertically, each rendered in its kind) — that IS the right output for a blog piece. It's the `surface_type` already used for deliverables.
- "HTML-based default" is right at the *rendering* level (compose → self-contained HTML); "slides" is wrong at the *form* level. A rich article in composed HTML — prose + inline diagrams + tables + an optional hero — is the target. (Slides remain a legitimate *separate* derivative if a piece ever needs a deck; not the default rich form.)

---

## §4 The production flow (how a rich piece gets made — grounds the spec)

The pipeline is all live (audit-confirmed); the spec wires it:

1. **Author recurrence fires** (e.g. `rich-essay`, operator-cadenced). The Reviewer (alpha-author's seat) reasons about the piece from substrate — the author workspace's accumulated `_voice.md`, `_editorial.md`, corpus, and the operator's declared piece intent.
2. **Reviewer drafts the prose + decides the structure** — which sections, which kinds. This is the judgment that can't be mechanized: *where does a diagram carry the argument?*
3. **Reviewer dispatches the designer** for any asset-bearing sections: `DispatchSpecialist(role="designer", brief="render a mermaid flowchart of the 4-step money-truth pipeline: fetch → compute → write → idempotency-check")`. Designer calls `RuntimeDispatch`, assets land, returns markdown + URLs.
4. **Reviewer writes `kind:`-tagged section partials** + `sys_manifest.json` (the section→kind map) to `/workspace/operation/reports/{slug}/{date}/sections/`.
5. **Compose pulls it to HTML** (surface-pull, ADR-213) — section-kind dispatch renders each section in its form; the result is the rich article.

**The spec's job** is to declare: the section structure with kinds, the quality criteria (the §1 anti-gaming "earns-its-place" rule as an explicit gate), the designer-brief expectations, and the output target. **It is NOT an audit spec** (unlike every existing author spec) — it's the author program's first *production* deliverable.

---

## §5 How "richness" is judged (the eval criterion — anti-gaming built in)

For the soak's thesis read (does YARNNN produce rich pieces that beat the flat corpus, improving over tenure?), the criterion must NOT be "asset count." Proposed criterion, by the §1 thesis:

- **Argument-fidelity**: does each non-prose section carry an argument the prose couldn't carry as well? (The "could this be a paragraph without loss?" test, applied per-section.) A piece with 1 well-placed diagram scores higher than one with 5 decorative charts.
- **Voice integrity**: is the connective prose still YARNNN's voice (claim-first, em-dash-fluent), or did the structure fragment it into bullet-shards? Richness must not cost voice.
- **vs the flat baseline**: pick a strong existing post (e.g. money-truth), have the author workspace produce its rich analog, and judge whether the rich version is *more legible / faster to grasp* without losing the argument. The flat corpus is the control.
- **Over tenure**: does the author's *structural judgment* improve — does it learn which kinds carry which arguments, place fewer decorative assets over time? (This is the genuine self-improvement claim for the richness domain, and it's the honest, hard-to-game version.)

**The gameable failure to watch for** (the operator's own hazard, named): a loop that maximizes asset-count or "coverage" while argument-fidelity drops. The criterion above measures the opposite of that by construction — which is *also* why this track stays SEPARATE from the Goodhart probe (the probe tests the loop's alignment under a gameable signal; this track is designed so its signal is *not* gameable, by making argument-fidelity the measure).

---

## §6 Open questions for operator reaction (the discourse)

Before I author the spec, react to these:

1. **The §1 thesis** — is "richness = argument structure made visible, measured by argument-fidelity-gain, not asset count" the right framing? Or do you want a different definition of rich?
2. **The §2 palette ranking** — agree that comparison-table + mermaid + callout is the richness spine, with generated images as exceptional/Tier-3? Or do you want images to play a bigger role (and accept the higher decoration-risk)?
3. **§3 article-not-slides** — agree the default rich form is a composed HTML *article*, with slides as a separate derivative only? Or do you specifically want the slide-deck form as the default?
4. **§4 the deliverable's nature** — comfortable that this is the author program's first *production* (not audit) deliverable, and that it's authored as a new recurrence spec? Any concern about it coexisting with the audit recurrences?
5. **§5 the eval criterion** — is argument-fidelity-vs-flat-baseline the right way to judge "did it beat the corpus," or do you have a different success bar (e.g., would-I-actually-publish-this)?
6. **First subject** — should the first rich piece be a *new* topic, or a *rich re-make of an existing strong flat post* (e.g. money-truth) so the flat-vs-rich comparison is direct and controlled? (I lean re-make: cleanest A/B.)
