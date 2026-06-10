# The orphaned production half — rewiring compose into the reviewer-agent core

> **Status**: discourse + proposal, 2026-06-10. Hat-A (system canon — real-operator-facing). Pre-ADR; produces the decisions an ADR-332 would ratify. Every load-bearing claim carries a file:line / ADR receipt (audited live 2026-06-10).
>
> **How we got here**: started as an eval-design question ("make a rich YARNNN blog piece"), corrected by the operator to "test the system at its corest form, not a constructed test." Tracing the *real ship path* — rather than designing a richness apparatus — surfaced an architectural gap, not a testing gap. This doc is the reshift: from "how do we test richness" to "the compose pipeline is orphaned from the core agent workflow, and that is the crux."

---

## §1 The crux, stated plainly

YARNNN ships a complete multi-modal compose pipeline — `render/compose.py` (section-kind rendering: comparison-table, mermaid, trend-chart, metric-cards, status-matrix, entity-grid, timeline) + the designer specialist (`DispatchSpecialist(role="designer")` → `RuntimeDispatch` chart/image/mermaid assets) + content-addressed caching (ADR-213). It is live, test-covered, and **GREEN**.

It produces rich HTML for exactly one thing: **audit reports** (`/workspace/operation/reports/{slug}/{date}/`).

It produces nothing for the thing operators actually publish: **author pieces** (`/workspace/operation/authored/{slug}/content.md`) **ship as flat markdown.** They never touch compose.

This is why YARNNN's own blog corpus is 102 posts of flat prose, zero images/tables/diagrams — and it would be true for any real author operator. **The richness machinery and the published artifact are on opposite sides of an architectural seam.**

### Why the seam exists (the archaeology — operator's hypothesis confirmed)

Compose was **task-pipeline-wired** in the prior era. ADR-177 D1: `_compose_and_persist()` lived *in* `task_pipeline.py`, firing on every `produces_deliverable` task's output. The task pipeline was the universal execution shape; compose was a post-step on it.

Then the architecture shifted in full:
- **ADR-231** deleted `task_pipeline.py` (4,204 LOC) + the task abstraction.
- **ADR-260/261/262** replaced it with the reviewer-agent loop + recurrences-as-prompts. "The biggest collapse since ADR-138."

Compose got **re-wired, but only halfway.** ADR-262 D4 re-attached it as "an opt-out structural default — auto-run at session-close when section partials matching the deliverable convention (presence of `sections/*.md` in `/workspace/operation/reports/{slug}/{date}/`) are present." (`api/services/wake.py::_maybe_auto_compose`, substrate query `.like("path", f"{report_root}/%/sections/%.md")`.)

That trigger is **path-and-shape scoped to reports.** Author pieces:
- live at `operation/authored/`, not `operation/reports/` → `report_root()` never matches them;
- are a flat `content.md`, not a `sections/*.md` folder → the shape never matches.

So the orphaning is **implicit, not explicit** — there's no "don't compose author pieces" rule; it's that the reviewer-agent author workflow never writes the `sections/` substrate that the trigger keys on, and the path convention for authored output isn't even in `conventions.py` (it has `report_root()` etc. but **no `authored_root()`** — the authored path is hardcoded in operator-proxy scenarios, evidence the production half was never given a home in the new conventions module). The compose pipeline is an **era-fossil**: re-wired for the report path that the reviewer-agent inherited, never given a production path for the artifact operators publish.

### The ship_piece confirmation

When an author piece "ships," nothing reshapes the artifact. `ProposeAction` has **no `ship_piece` action type** in its mapping (`api/services/primitives/propose_action.py`); shipping is a `status: published` flip on `profile.md`. **The raw `content.md` IS the published artifact.** No compose, no HTML, no assets, ever.

---

## §2 The cost is mislocated (the key reframe for the design)

The operator's instinct: *"compose takes its own compute and LLM-intensive workflow; a dedicated workflow may be the right approach; I'm skeptical of making it first-class default-to-ALL-writes."*

That instinct is **right in conclusion but the cost is in a different place than it sounds.** Audited precisely:

- **Compose-the-render is cheap and mechanical.** `compose_task_output_html` → POST render-service `/compose` → python-markdown + matplotlib + component HTML. **Zero LLM.** ~200–1500ms, content-addressed cached (ADR-213) so a re-compose of unchanged substrate is ~10ms. Composing liberally costs almost nothing.

- **The expense lives UPSTREAM of compose, in two production steps:**
  1. **Structure-judgment** — the Reviewer deciding *which prose becomes which kind* (this A-vs-B contrast → comparison-table, this pipeline → mermaid) and writing the `sections/*.md` + `sys_manifest.json` shape. This is LLM (part of the Reviewer's loop).
  2. **Asset production** — `DispatchSpecialist(role="designer")`, a bounded sub-LLM-call that calls `RuntimeDispatch` to render charts/images. This is LLM + render-service compute.

**So the design rule sharpens:** the thing that must NOT be default-on-every-write is **rich-substrate *production*** (structure-judgment + designer dispatch), not **compose-the-*render***. Compose itself could safely run on every shipped artifact. This dissolves the apparent tension — "don't make compose first-class" and "compose the published artifact" are not in conflict, because the costly part isn't compose.

---

## §3 What "default to all writes" would wrongly catch (why the operator's skepticism is correct)

Making compose-on-write a first-class default for *all* substrate writes is wrong, decisively. The reviewer-agent writes constantly, and almost all of it is **flat-by-nature machine substrate that must never be rich HTML:**
- `/workspace/persona/judgment_log.md`, `standing_intent.md`, `_signal.md`, `_money_truth.md`, `_calibration.md` — append-only ledgers + machine-parsed state. Composing these to rich HTML is nonsensical (they're read by the Reviewer + mechanical mirrors, not published).
- domain `context/` accumulation files (`_voice.md`, `entities/{slug}.md`) — operator-authored canon, read as prose, never "published artifacts."
- `.yaml` config/state (`_budget.yaml`, `_recurrences.yaml`) — machine-parsed; rich rendering is a category error.

The set of substrate that *wants* compose is narrow: **the deliverable artifact the operation produces for an audience** (a report, a published piece). Everything else is working substrate. So "compose belongs to the *deliverable*, not the *write*" is the correct scoping — and the report path already honors it. The gap is that the **author-piece deliverable** isn't recognized as a deliverable by the compose trigger.

---

## §4 The design space — where does a rich-production workflow attach?

Given (§2) the costly part is production-of-rich-substrate and (§3) it belongs to deliverables not writes, the real question is the operator's: **what is the trigger shape for the production workflow in a reviewer-agent world?** Four candidate shapes, mapped against the current architecture:

### Option A — Ship-time compose hook (minimal: render the approved draft)
On `ship_piece` (the status→published transition), route the approved `content.md` through compose. **But** `content.md` is flat prose with no `sections/` shape and no kind metadata — so compose would just markdown-render it (callout + narrative). **This gets HTML, not richness.** It closes the "flat markdown ships" gap at the *render* level but not the *structure* level. Cheap, mechanical, no new LLM. Honest framing: this is "compose the published artifact" (a real fix) but NOT "rich" (no structure-judgment, no assets).

### Option B — A dedicated rich-production recurrence (the operator's "dedicated workflow")
A recurrence (or one-off invocation — schedules can be null/reactive per `recurrence.py:206`) whose prompt directs the Reviewer to: read the operator's approved draft + accumulated substrate → decide structure (which prose → which kind) → `DispatchSpecialist(designer)` for assets → write `sections/*.md` + `sys_manifest.json` to a deliverable folder → session-close auto-compose (ADR-262 D4) fires. **This is the full rich pipeline, and it reuses the EXISTING report-path trigger** — if the rich-production output lands at a `sections/`-shaped deliverable folder, ADR-262 D4 already composes it. The only new thing is the *production recurrence* + giving authored deliverables a `sections/`-shaped home. LLM-intensive by design (structure-judgment + designer), which is correct — it's a deliberate, operator-or-cadence-triggered act, not an every-write default.

### Option C — Extend the auto-compose trigger to the authored path
Broaden `_maybe_auto_compose`'s substrate query from `report_root/%/sections/%.md` to also match `authored/%/sections/%.md`. **But this does nothing unless author pieces actually write `sections/`** — which they don't (Option A's problem). So C is necessary-but-insufficient; it only matters if paired with B (something must produce the `sections/` shape for authored deliverables). On its own, C is a no-op.

### Option D — Make rich-production a property of the Reviewer's draft-writing itself
When the Reviewer (or the audit loop) handles a piece, have it natively write `sections/`+kinds instead of flat `content.md`. **This conflicts with ADR-283 (operator authors, not YARNNN)** — the operator wrote `content.md` as prose; YARNNN restructuring it into kinds at draft-write time would be YARNNN-authoring-the-structure on every piece. Too aggressive; collapses the operator-authors thesis.

### The shape that fits: B (+ C as its enabling plumbing)

**A dedicated rich-production workflow that the operator invokes (or cadences) on an approved draft**, which produces the `sections/`+kind deliverable shape, lands it at an authored-deliverable path, and lets the existing ADR-262 D4 auto-compose render it. This:
- keeps compose-the-render exactly where it is (no first-class default-on-write — §3 honored);
- locates the LLM/compute cost in a *deliberate, dedicated workflow* (the operator's instinct — §2 honored);
- reuses the existing trigger + render engine (Singular Implementation — no parallel compose path);
- preserves ADR-283 (the operator authored the *prose*; the rich-production step is editorial enrichment of an *approved* draft — structure + assets — analogous to a publication's art/layout desk, not authorship);
- needs C (extend the trigger's path-match) only as the plumbing that lets the authored deliverable reach the existing auto-compose.

**Singular-Implementation note**: this must NOT become a second compose path. The rich-production recurrence writes the *same* `sections/*.md` + `sys_manifest.json` substrate the report path writes; the *same* `_maybe_auto_compose` + `compose_task_output_html` + render `/compose` render it. The only additions are (1) a production recurrence/spec, (2) an authored-deliverable path in `conventions.py` (closing the missing-`authored_root()` gap), (3) the trigger path-match extension. Everything downstream is the existing pipeline.

---

## §5 The honest open questions for operator discourse

1. **Is the rich artifact a *new deliverable* or a *transformed draft*?** Option B produces a rich deliverable *from* the approved `content.md`. Does the rich HTML *replace* `content.md` as the published artifact, or sit *beside* it (content.md = canonical prose source, rich HTML = rendered publication)? Leaning beside (content.md stays the operator's authored source-of-truth per ADR-283; rich HTML is the derivative — same relation as report `sections/*.md` → `output.html`). Confirm.

2. **Trigger: operator-invoked, cadenced, or ship-hooked?** Option B can fire (a) on operator request ("make this rich"), (b) on a cadence, or (c) automatically at `ship_piece`. Given the cost is deliberate, (a) or (c) fit better than (b). Ship-hooked (c) is the most "core workflow" — every shipped piece gets enriched — but commits the LLM cost on every ship. Operator-invoked (a) is the most controlled. **This is the real trigger-shape decision.**

3. **Does this generalize beyond author, or is it author-first?** The same gap exists for any program whose deliverable isn't report-shaped. The fix (authored-deliverable path + production recurrence) could be author-specific or kernel-general (any deliverable that wants richness). Leaning author-first (demand-pull — prove it on the one program that needs it), generalize when a second program asks. Same discipline as ADR-327 D6.d.

4. **Relationship to ADR-330 (sibling, concurrent lane).** ADR-330 is the *intake* side (flow 3 — the world's verdict on the operation's acts). This proposal is the *output/production* side (the operation produces a rich artifact). Complementary, not colliding — but both touch alpha-author, so they should be sequenced/cross-referenced, not merged.

5. **Does richness stay un-gameable?** Per the prior design memo: richness = argument-structure-made-visible, measured by argument-fidelity-gain, never asset count. The production recurrence's spec must encode the "could this be a paragraph without loss?" gate so the structure-judgment doesn't degenerate into decoration. This keeps it distinct from (and non-contaminating to) the alpha-author Goodhart probe.

---

## §6 Recommendation

**Ratify the gap as an architectural finding and fix it via Option B + C, author-first, content.md-stays-canonical, trigger TBD by Q2.** Concretely, an ADR-332 would decide:

- **D1**: The compose pipeline is canon for *deliverables*, not *writes* (§3) — formalize that "deliverable" includes audience-facing published pieces, not only audit reports. Names the orphaning as the era-fossil it is (ADR-177→231→262 chain).
- **D2**: Add the authored-deliverable path to `conventions.py` (`authored_deliverable_root()` or equivalent) — close the missing-home gap; the production output lands at a `sections/`-shaped folder under the authored topology.
- **D3**: A dedicated rich-production workflow (recurrence + spec) — Reviewer reads approved draft + substrate → structure-judgment → designer dispatch → writes `sections/`+manifest. Reuses ADR-262 D4 auto-compose downstream (Singular Implementation — no parallel render path).
- **D4**: Extend `_maybe_auto_compose`'s path-match to the authored-deliverable path (the C plumbing — no-op without D3).
- **D5**: content.md stays the operator's canonical authored source (ADR-283 preserved); rich HTML is the derivative deliverable (same relation as report sections→output.html).
- **D6**: Trigger shape (Q2) + generalize-or-not (Q3) decided in the ADR after this discourse.

This is a **small, core, canon-aligned change** — not a new program, not a resurrected task pipeline, not default-on-all-writes. It rewires the orphaned production half back into the reviewer-agent core by giving the authored deliverable a home and a dedicated production workflow, then letting the existing (cheap, mechanical, cached) compose render it. The crux the operator named — "compose set up but not streamlined into the core agent workflow because the architecture shifted" — is closed at its root.
