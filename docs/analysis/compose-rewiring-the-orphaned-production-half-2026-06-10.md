# The orphaned production half — rewiring compose into the reviewer-agent core

> **Status**: discourse + proposal, 2026-06-10 (v2 — axiomatic rewrite after the operator flagged cost-blindness in v1). Hat-A (system canon — real-operator-facing). Pre-ADR; produces the decisions an ADR-332 would ratify. Every load-bearing claim carries a file:line / ADR receipt (audited live 2026-06-10).
>
> **How we got here**: started as an eval-design question ("make a rich YARNNN blog piece"), corrected by the operator to "test the system at its corest form, not a constructed test." Tracing the *real ship path* — rather than designing a richness apparatus — surfaced an architectural gap, not a testing gap. v1 of this doc proposed a fix but priced compose as "cheap (~10ms cached)" — the operator correctly rejected that as cost-blind (the render service is a separate Docker instance; "cache hit" is a network round-trip, not a memory lookup; at scale the service-load + storage I/O + cold-starts are real). v2 derives the answer from **cost-grounded invariants**, not from anyone's trigger preference — the trigger shape *falls out* of the axiom.

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

## §2 The cost reality (grounded, not hand-waved)

v1 priced compose as "~10ms cached." Wrong. Audited against the actual service (`render/main.py`):

- **The render service is a separate Docker instance** (`yarnnn-render`), heavy image (pandoc + python-pptx + openpyxl + matplotlib + pillow + mermaid-cli). It has a `/health` endpoint but **no min-instances/keepalive config visible** → it can scale-to-zero → **cold starts on the latency tail.**
- **Every compose is a cross-service HTTP round-trip** (`compose_task_output_html` → POST render `/compose`), plus a **Supabase storage GET** to check the cache (`render/main.py:310`), plus on miss a render + a **storage PUT** (`render/main.py:330`). The cache is **storage, not in-process** — a "hit" is a network round-trip + storage egress (`render/main.py:374`), not a memory lookup.
- **Every asset** (chart/image/mermaid) is a **designer sub-LLM-call** + a render subprocess + a **storage PUT** (`render/main.py:257`).

So a rich artifact is, at scale: **N operators × M pieces × (designer sub-LLM-calls + subprocess spawns + multiple storage round-trips), against a service that may be cold.** The LLM cost dominates the dollar figure, but the **service-load, storage I/O, latency tails, and cold-start failure surface are real and independent** — they are the cost of the separate render instance *existing and being driven*, which "marginal cached request" pricing hides entirely. The operator was right to refuse the cheap/expensive binary.

**The discipline this forces:** an architecture that drives the render service eagerly — ahead of, or regardless of, consumption — pays this cost for artifacts no one reads. That is the failure mode to design out, not around.

---

## §3 The invariants (derive the axiom, not the preference)

Three invariants, true regardless of what anyone prefers:

**Invariant 1 — Compose is a *projection* of substrate, never a *source* of truth.** The substrate (`content.md`, `sections/*.md`, asset URLs) is canonical (FOUNDATIONS Axiom 1; ADR-209 authored substrate; ADR-213 "output HTML is a derivative artifact, not a primary output"). A projection's defining property: **it is reproducible from source at any time, so it never needs eager materialization — only production when consumed.** Same reason you don't materialize a DB view you never query.

**Invariant 2 — Cost is incurred at production; value is realized at consumption.** A rich artifact never read cost real service-load/LLM/I-O and returned zero value. The architecturally correct coupling is **produce-when-(and-only-when)-consumed.**

**Invariant 3 — There are two production costs with different economics, and conflating them is the original error.**
- **Rich-substrate production (expensive: LLM structure-judgment + designer sub-LLM + subprocess + storage)** — *changes rarely.* A piece's structure is decided once; its assets are stable once rendered.
- **HTML render (cheaper per call, but a cross-service hop + storage I/O) — re-incurred on every cache miss**, and misses happen on *every substrate change.*

**The derivation:** if compose is a projection (Inv 1) produced only when consumed (Inv 2), then **neither "default-on-write" nor "default-on-ship" is correct — both materialize eagerly.** Split by change-frequency (Inv 3):

> **AXIOM (proposed): Compose is a lazy projection pulled at the consumption boundary. The expensive half (structure + assets) is produced once, deliberately, idempotently, and persisted as *substrate* (sections + asset URLs) — never as HTML. The cheap half (HTML render) is pulled when a surface actually consumes the artifact. The render is pulled, never pushed.**

This is not a new idea — **it is exactly ADR-213's "surface-pull composition," stated as the axiom it always was.** The work is to apply it *uniformly*, which surfaces two gaps and one bug.

---

## §4 What the axiom reveals (two gaps + one bug — all the same violation)

Holding the system to the §3 axiom:

**Gap 1 — author pieces never produce the expensive half.** No rich-substrate production step writes `sections/` + assets for an authored piece. (The whole §1 orphaning.)

**Gap 2 — author pieces have no consumption-pull surface.** Even if sections existed, nothing pulls their render — the pull surfaces (`routes/recurrences.py:603`, `delivery.py:694`, `repurpose.py:142`) are all report-scoped.

**Bug — the report path itself violates the axiom (the bonus finding, verified).** `_maybe_auto_compose` (`wake.py:1373`) **eagerly calls `compose_task_output_html` at session-close** and persists `output.html` — *whether or not anyone consumes it.* The *same* artifact is then re-composed on consumption-pull (the three pull surfaces). The storage cache is the only thing preventing fully-duplicated render work. So the report path runs the separate Docker render service **on every cron fire, eagerly**, for daily reports most of which are never opened. This is precisely the §2 cost-blindness, *already shipped*, contradicting ADR-213's own surface-pull principle. The eager auto-compose is itself an era-fossil — it made sense under "render-at-fire so the artifact is ready," which ADR-213 superseded but never fully retired.

**The unification:** all three are the *same* violation — pushing the projection instead of pulling it. Fixing the author path by *copying* the eager auto-compose would propagate the bug to a second path. The axiomatic fix retires the push everywhere.

---

## §5 What the axiom dissolves (the two questions v1 asked were mis-framed)

- **"Trigger shape?" (operator-invoked / cadenced / ship-hooked)** — dissolved. There is **no production trigger for the render.** The render is pulled at consumption (Inv 2). The only deliberate act is **rich-substrate production** (structure-judgment + designer), which is a rare, idempotent authoring step keyed on *"this piece's structure was decided/changed,"* not on ship/cadence/clock. All three v1 trigger options were eager-projection variants of the §4 bug.
- **"Artifact relationship?" (HTML replaces vs sits beside content.md)** — dissolved by Inv 1. The HTML is **not a stored artifact at all** — it is a view, pulled on demand, the storage cache being a mere memoization. `content.md` + `sections/` + asset URLs are substrate (canonical); HTML is the projection. "Beside vs replaces" was a stored-artifact question; there is no stored artifact.

This is the payoff of deriving from invariants: the questions that felt like genuine forks were artifacts of a push-model assumption. Under the pull-model axiom they don't arise.

---

## §6 Proposal (ADR-332 decision sketch — axiomatic + uniform)

- **D1 — Ratify the projection axiom (§3).** Compose is a lazy projection pulled at the consumption boundary; the render is pulled, never pushed; rich-substrate production is a separate deliberate substrate-write. Formalize "deliverable" as *any* audience-facing artifact (published pieces, not only audit reports). This is the load-bearing decision; everything else is consequence.

- **D2 — Retire the eager push (the §4 bug), uniformly.** Delete/neuter `_maybe_auto_compose`'s session-close render (`wake.py:1373`). Session-close persists *substrate only* (sections + manifest already written by the Reviewer); it does **not** call the render service. The render happens on pull. (Singular Implementation: one shape — pull-on-consume — for reports AND pieces. This *removes* code; it doesn't add a parallel path.) **Cost win, immediate**: daily reports stop driving the Docker render service on every fire; they render only when opened/delivered/exported.

- **D3 — Give the authored deliverable a home in `conventions.py`** (`authored_deliverable_root()` or equiv), closing the missing-`authored_root()` gap (§1). The rich-substrate production output lands at a `sections/`-shaped folder under the authored topology.

- **D4 — A deliberate rich-substrate production step** (recurrence + spec): Reviewer reads the operator's approved draft + accumulated substrate → structure-judgment (which prose → which kind, gated by the "could this be a paragraph without loss?" anti-decoration rule) → `DispatchSpecialist(designer)` for assets → writes `sections/*.md` + `sys_manifest.json` to the D3 path. **Idempotent**: re-run only when the piece materially changes (Inv 3 — structure changes rarely). This is the only LLM/compute-heavy step and it is deliberate, not default.

- **D5 — A consumption-pull surface for authored deliverables** (the FE route / delivery / export that pulls `compose_task_output_html` for the authored path — mirrors the three existing report pull surfaces). The render fires here, lazily, cached.

- **D6 — content.md stays the operator's canonical authored source (ADR-283 preserved).** The rich deliverable is the *projection* of {content.md's prose + the produced sections/assets}; it is never a competing source of truth. (Dissolves v1's "beside vs replaces" — there is no stored HTML artifact, only the pull-rendered view.)

- **D7 — Author-first; generalize on demand.** The same axiom serves any non-report deliverable, but only the author program needs it now. Prove it there; generalize when a second program asks (demand-pull discipline, per ADR-327 D6.d).

**Net shape:** D1 (axiom) + D2 (retire the eager push — *removes* code, immediate cost win, fixes a live ADR-213 violation) + D3/D5 (give authored deliverables the same conventions-home + pull-surface reports have) + D4 (the one deliberate expensive step). No new program, no resurrected task pipeline, no default-on-write, **no eager render anywhere.** The crux the operator named — "compose set up but not streamlined into the core workflow because the architecture shifted" — is closed by making the *whole* system honor the projection axiom it already half-implements, rather than bolting the author path onto the half that's wrong.

---

## §7 Open questions for operator discourse

1. **Is the projection axiom (§3) the right invariant to canonize?** It's stricter than the current implementation (which eagerly renders reports). Ratifying it means committing that *no* artifact renders ahead of consumption — including reports. Agree, or is there a case for eager render (e.g., an artifact that MUST exist the instant it's produced for some downstream non-pull consumer — email is a pull at send-time, so that's covered; is there a genuine push consumer)?
2. **D2 retire-the-eager-push — any consumer that breaks?** Verify nothing downstream assumes `output.html` exists in substrate immediately at session-close (vs pulled on demand). The three pull surfaces already compose-on-demand, so they're fine; confirm no FE/delivery path reads a pre-existing `output.html` file directly without going through `compose_task_output_html`.
3. **D4 production trigger — operator-invoked or hook-on-approval?** The *render* has no trigger (it's pulled), but the *rich-substrate production* is a deliberate act — does it fire when the operator says "make this rich," or automatically when a draft reaches `approved`? (Narrower than v1's question — it's only about the expensive substrate step, not the render.)
4. **Relationship to ADR-330 (sibling).** ADR-330 = intake/flow-3 (world's verdict on acts). This = output/production. Complementary; both touch alpha-author; cross-reference + sequence, don't merge.
5. **Richness stays un-gameable** (per the design memo): D4's structure-judgment spec encodes argument-fidelity-gain (not asset count) as the gate, keeping this distinct from and non-contaminating to the alpha-author Goodhart probe.
