# Findings — author-compose-money-truth-remake

**Hat:** B (external-developer / evaluation surface). **Date:** 2026-06-10.
**Run:** `2026-06-10-105720` (third of three; the prior two are recorded under
"The arc" below). **Workspace:** alpha-author persona `yarnnn-author`
(`0b7a852d-…`), live. **Subject:** ADR-333 composition thesis — can the Reviewer
author a piece with *structure native to the authoring act*?

---

## The criterion (declared before adherence, per README discipline)

Measured against three canon clauses:

1. **ADR-333 D5** — structure is native to authoring (the Reviewer emits
   `kind:`-tagged sections as part of the single authoring act; no separate
   enrich step, no trigger).
2. **`piece-composition.md` §1 gate** — a section-kind earns its place only when
   it carries the argument *better than prose would* ("could this be a paragraph
   without loss?"). Richness = argument-fidelity-gain, **never** asset count.
3. **`piece-composition.md` §2 palette ranking** — comparison-table + mermaid +
   callout spine; metric-cards/status-matrix/trend-chart only with real
   substrate data; generated images Tier-3/exceptional.

**Pass-bar (substrate-receipt-backed):** real `workspace_file_versions`
revisions, attributed `reviewer:ai:*`, at `content.md` + `{date}/sections/*.md`
(≥1 kind-tagged partial) + `{date}/sys_manifest.json`; then the ADR-333 D6
consumption-pull surface must render composed HTML.

---

## Verdict: PASS (the thesis), with three integration gaps the soak surfaced + closed

### What the Reviewer did (substrate receipts)

The Reviewer, under autonomous delegation, authored the money-truth re-make
end-to-end. Receipts (live `workspace_files`, run 3):

| Artifact | Receipt |
|---|---|
| Prose | `…/money-truth-remake/content.md` (7.6 KB, `reviewer:ai:*`) |
| Profile | `…/money-truth-remake/profile.md` (status: draft) |
| Section partials | 5 × `…/2026-06-10/sections/{1..5}-{slug}.md` (real prose each) |
| Section map | `…/2026-06-10/sys_manifest.json` (6 declared sections) |
| Composed HTML | `composed-output.html` (16 KB, this folder) — the D6 pull render |

### The structural judgment (the criterion's heart) — STRONGLY MET

The Reviewer's section→kind map, run 3:

| Section | Kind chosen | Gate verdict |
|---|---|---|
| opener (plain-language gloss) | **callout** | ✓ Tier-1 spine |
| The Two Architectures (A vs B) | **comparison-table** | ✓ highest-fit kind — the contrast IS a table |
| Why the dashboard breaks autonomy | **narrative** | ✓ prose carries the argument — left as prose on purpose |
| How money-truth gets computed (4-step pipeline) | **mermaid** | ✓ the flow IS the argument |
| What the substrate enables | **narrative** | ✓ prose |
| Closing | **narrative** | ✓ prose |

This is the **full Tier-1 spine** (callout + comparison-table + mermaid) with
**3 narrative sections left as prose** — exactly the §1 gate applied *in both
directions*. Two structural kinds, not five decorative ones. **The
anti-Goodhart outcome the criterion was designed to measure: achieved by the
Reviewer's own judgment** (the message named the latent structure but the
Reviewer chose what earned its place). Run 3 was *better* than run 2 (which
omitted the callout) — the structural judgment was not fragile across runs.

### What surprised us (the value of running it live)

Three integration gaps that **no unit test would have caught** — only an E2E
soak driving the real Reviewer surfaced them. Each was closed in the same
session (Hat-A fixes):

1. **The Reviewer reliably writes `sections` as a LIST, not the report-path
   dict** — twice, even after the spec was amended with the dict schema + an
   explicit "do not write a list" warning. **The prompt-layer fix did not
   hold.** Finding: the LLM's natural manifest shape is an ordered list; the
   composer's dict-only contract (ADR-170) was too rigid. **Fix:** normalize
   both shapes at the composer's input boundary (one tolerant boundary, not a
   dual render path — same discipline as ADR-166's legacy remap). This is the
   load-bearing finding: *meet the model where it reliably is, don't fight the
   format.*

2. **Partials are `{N}-{slug}.md` (numeric-ordered) but the manifest slug is
   bare** — the composer's slug→file resolution needed to strip the numeric
   prefix. Single-digit (`1-`) tripped a two-digit assumption first; fixed with
   a regex prefix strip.

3. **The render engine has no `article` surface type** — its vocabulary is
   `(report, deck, dashboard, digest, workbook, preview, video)`. The article
   form IS its `report` surface (vertically-stacked section-kind dispatch). The
   composer now maps `article → report` at the boundary rather than registering
   a new render-side type on a separate Docker deploy.

After the three fixes, the **D6 pull rendered 16 KB of styled HTML** — the
`comparison-table` as a real 7-row `<table>`, the `mermaid` block present,
section headings, full content. The flat baseline's hidden structure, made
visible. (Receipt: `composed-output.html`.)

### Also validated: the citation-verifiability discipline (run 1)

The **first** run had no source seeded. The Reviewer **refused to fabricate** —
it deferred with a Clarify asking where the source lived (web / paste /
workspace path), and even attempted a web-search. This is *correct* behavior,
not a failure: the Reviewer reasons from substrate (Axiom 1) and will not author
"about content it can't read." Seeding the flat post as input substrate (run 2)
unblocked it. **Two distinct disciplines validated in one soak: it won't
fabricate AND it composes well when given real input.**

---

## The arc (three runs, honest record)

| Run | Source seeded? | Spec schema? | Outcome |
|---|---|---|---|
| `104606` | no | no | Reviewer deferred (refused to fabricate) — citation-verifiability working |
| `104831` | flat post | prose-only | Composed substrate written (comparison-table + mermaid); manifest list-shaped → D6 pull crashed on `.items()` |
| `105720` | flat post | dict schema added | **Best structure** (callout + comparison-table + mermaid); still list-shaped (prompt fix didn't hold) → composer normalized → **D6 pull rendered 16 KB HTML** |

Total live cost across runs: ~$1 (3 × ~$0.35 Reviewer turns). Cheap for a
full E2E validation of the production half of system autonomy.

---

## What this validates / contradicts in the canon

- **VALIDATES ADR-333 D5** — structure is genuinely native to the authoring
  act. The Reviewer did not write flat prose then enrich; it composed kinds as
  it authored, applying the §1 gate without a second pass. The orphaned
  production half is wired: an author piece now becomes a composed article.
- **VALIDATES the anti-Goodhart §1 criterion** — the Reviewer placed kinds
  where they carry argument and left prose as prose; it did not maximize asset
  count. The criterion measured the right thing and the behavior met it.
- **REFINES ADR-333's manifest contract** — the canonical `sys_manifest.sections`
  shape (ADR-170 dict) is NOT what the Reviewer reliably produces. The composer
  must tolerate the list shape. *This is a system-side change (landed), not a
  prompt the operator should keep escalating.* Candidate follow-up: make the
  list shape the documented-canonical authored-piece shape (the LLM's reliable
  shape, with explicit order), and let the report path keep its dict — both
  normalized at the one composer boundary.
- **SURFACES a pre-existing env gap** (out of ADR-333 scope, noted): the local
  `.env` `RENDER_SERVICE_URL` points at `yarnnn-output-gateway` (404/dead);
  the live service is `yarnnn-render`. The composer's hardcoded default
  (`yarnnn-render`) is correct; the stale env override masked it. Worth a
  Render-parity check on which URL is canonical.

## Open follow-ups (for a future session, not blockers)

1. **Canonicalize the list shape** for authored pieces in `piece-composition.md`
   (stop telling the Reviewer to write a dict it won't write; document the list
   shape it reliably produces) + drop the now-redundant "do not write a list"
   warning.
2. **The 6th declared section (`opener` callout) had no partial file** — the
   Reviewer declared it in the manifest but folded the gloss into content.md's
   open. The composer correctly skips contentless sections; worth a spec note
   that every declared section needs a partial.
3. **Pre-activated workspace gap** — this workspace (forked 2026-05-18) lacked
   the ADR-333 spec; the soak seeded it. Real operators activated before a
   bundle update have the same gap (ADR-244 deactivation/re-fork territory).
