# ADR-417: Retire the Render Service — Generation Is Rented, Not Owned

**Status**: Accepted (2026-07-08, operator-ratified — "yes, I'd like the render cut, and even the PDF/XLSX I don't think we need the dedicated render service; I want to shut that down now"; compose-in-library ruling same day). Doc-first; the code teardown is this ADR's own scope (a single subtractive-plus-port pass, pushed to main separately from the models/platforms axis).
**Date**: 2026-07-08
**Dimension**: Mechanism (Axiom 5 — which intelligence runs where, and what the platform owns vs rents) + Channel (Axiom 6 — the derivative-artifact surface) + Substrate (Axiom 1 — the deployed-service footprint)
**Supersedes**: ADR-118/130/148/157/170/177 *asset-production machinery only* — the compose substrate and section-kind rendering survive (ported in-API); the **in-house render service** (`yarnnn-render`) that hosted them is retired. ADR-172's `render_usage` metering ledger retires (already a fossil under ADR-396's one-meter).
**Amends**: ADR-413 (the render-service-preservation convenience clause in D5.1/§8 retires; the *falsifiable* anti-goal — "never force an async-job engine through the tool-loop protocol" — stands, unchanged, and is now trivially satisfied because yarnnn runs no async-job engine at all), CLAUDE.md "Render Service Parity" (4 services → 3), the FOUNDATIONS four-permitted-DB-row-kinds gloss (`render_usage` leaves the audit-ledger set).
**Relates to**: ADR-396 (one meter — `render_usage` was a parallel usage table; its removal tightens the invariant), ADR-408 D4 / ADR-413 (buy-not-build — this ADR extends that logic from *chat engines* to *generation engines*), ADR-185/202 (external-channel distribution — the Slack/Notion *sharing* exporters are untouched; only file-download PDF is cut), ADR-213 (compose-on-read — its engine moves in-API, the surface is preserved)

---

## 1. Context — the render service is the last thing yarnnn builds that it should rent

`yarnnn-render` is a standing Docker web service (ADR-118) doing three unrelated jobs bundled into one deployment:

1. **Asset generation** — `chart`, `mermaid`, `image`, `video` skills. Called by `RuntimeDispatch` (chat/specialist designer path) and `render_assets.py` (post-generation inline extraction). This is the platform *owning generation engines*.
2. **Deterministic export** — `pdf`, `xlsx` skills. Turning authored HTML/markdown substrate into a downloadable file artifact.
3. **Compose** — the `/compose` endpoint (ADR-130/213): section-partials + markdown → styled HTML, for email/report delivery and the on-demand composed-report surface.

All three are re-examined against a single constraint the operator named: **a solo founder cannot build the multi-AI-cowork-filesystem platform AND the generation/rendering layer.** The two are different businesses, and one of them is the least defensible layer in the entire stack.

The strategic frame is ESSENCE v15's own: *"the engines are fungible precisely because the memory is not… every new frontier engine deepens the commons it works through while remaining swappable."* **Generation engines are the most fungible engines that exist** — image/video/chart models leapfrog monthly, and none of them is a moat. Owning them in-house is pouring the scarcest solo-founder resource (integration + maintenance time) into the layer with the *lowest* defensibility. The correct posture is the one ADR-408 D4 already ratified for chat engines — **buy, not build** — extended one altitude out to generation.

This ADR is the decisive decouple: yarnnn stops hosting a generation/rendering service entirely. The **deployment** dies; the one job in it that carries product value (compose) moves in-API as a library.

## 2. The three jobs, decided separately

### 2a. Asset generation — retired outright

`chart`, `mermaid`, `image`, `video` generation leave the platform. yarnnn does not host, maintain, or meter generation. When generative capability returns to the product, it returns **rented** — a member-attached connector (the ADR-413 catalog / the models-vs-platforms axis under separate discourse), never an in-house engine. The `RuntimeDispatch` primitive and its skill library are deleted, not shrunk.

Why this is safe: `RuntimeDispatch` is a relic of the pre-coworking headless task-pipeline / production-role ("designer") era (ADR-118/130), an era ADR-260/261 already largely dissolved. It is **not on the lane path** (ADR-411 helpers get exactly five file verbs — no `RuntimeDispatch`) and **not on the steward path** (Freddie is Anthropic-only, no generation — ADR-402). Its only live callers are the orchestration/specialist designer prompts, which are themselves vestigial. The `designer` production role — whose entire purpose was RuntimeDispatch asset generation — collapses to a compose-only shell (keeps `read_workspace`/`search_knowledge`/`compose_html`); `has_asset_capabilities()` returns `False` universally. `DispatchSpecialist(role="designer")` is thereby near-inert; collapsing or removing `DispatchSpecialist` is a **named follow-on** (the specialist-dispatch architecture cleanup), deliberately out of this pass's scope so the three-actor execution model is revisited on its own.

### 2b. Deterministic export (PDF/XLSX) — retired, zero export capability at launch

The operator's ruling: **the ability to *share* is the priority; file export is not — zero export capability is fine for launch.** This is canon-coherent, not a gap:

- **Sharing already lives in the commons.** A workspace is a shared, attributed, versioned filesystem (ADR-407/408). "Share this" = a peer reads it in the commons, or it crosses a boundary via the Slack/Notion *external-channel* exporters (ADR-185/202) — **both untouched by this ADR.** What retires is the `download` exporter's `pdf` format (a never-implemented stub that returned `FAILED`); its `markdown`/`html` formats are pure text (the `markdown` lib, no render service) and stay.
- **Artifacts-as-dividends does not require a downloadable file.** ESSENCE's "artifacts are the dividends" is satisfied by the composed, attributed artifact *in the workspace*; a PDF is one derivative Channel, not the artifact itself (SERVICE-MODEL Frame 3: external distribution is derivative).
- **No frontier vendor will make your PDF** — true, and precisely why keeping a whole Docker service alive for it is the wrong trade for a solo founder at launch. If downloadable export returns, it returns as an in-API library call, **never as a standing deployed service** — a demand-gated follow-on, not launch scope.

### 2c. Compose (section→styled-HTML) — moves in-API as a library, NOT retired

Compose is **deterministic templating, not generation** — the operator's ruling (2026-07-08): move it in-API as a library rather than let the report/email surface degrade to markdown. The port is clean because `render/compose.py`'s section-kind dispatch is pure `markdown`→HTML for ~10 of its 12 kinds (`narrative`/`callout`/`checklist`/`metric-cards`/`entity-grid`/`comparison-table`/`status-matrix`/`data-table`/`timeline`, plus mermaid rendered client-side as JS). **The two matplotlib-backed kinds (`trend-chart`/`distribution-chart`) do NOT port** — they are inline chart *generation*, exactly what §2a retires; those sections degrade to native `data-table` HTML (the data survives as a table; no image is generated). **No matplotlib/numpy enters the API.**

The new home is `api/services/compose/engine.py` — a pure-Python `compose_html(sections, markdown, surface_type, assets)` returning an HTML string, ported from `render/compose.py` minus the matplotlib chart kinds. The two callers (`delivery.py::_compose_email_html`, `compose/task_html.py::compose_task_output_html`) switch from an HTTP POST to a direct in-process call. The content-addressed cache (ADR-213) is preserved as an in-process / `workspace_blobs`-keyed memoization, or dropped if in-process compose is fast enough (decided at port time by measurement). This is "compose shrinks to a library, never a standing service" — the export principle applied to the one compose path that carries product value.

## 3. Decision

**D1 — The `yarnnn-render` Render deployment is decommissioned.** Service parity goes 4 → 3 (yarnnn-api · yarnnn-unified-scheduler · yarnnn-mcp-server). The `RENDER_SERVICE_URL` / `RENDER_SERVICE_SECRET` env vars retire from every service.

**D2 — `RuntimeDispatch` is deleted** (primitive + tool def + registry entry + permission-taxonomy row + the `chart`/`mermaid`/`image`/`video` skill dirs). The orchestration/specialist designer prompts that instruct its use are stripped; the `designer` role collapses to compose-only; `has_asset_capabilities()` returns `False` universally.

**D3 — `render_assets.py` (inline post-generation asset extraction) is deleted** — it had no live caller.

**D4 — The `download` exporter's `pdf` format retires** (the never-implemented FAILED stub); `markdown`/`html` stay; the `slack` and `notion` external-channel **sharing** exporters are untouched.

**D5 — Compose ports in-API** (`api/services/compose/engine.py`), matplotlib chart kinds dropped; the two HTTP callers switch to direct calls; the composed-report + email-HTML surfaces are preserved (no degrade).

**D6 — The `render_usage` table + `get_monthly_render_count` RPC retire.** A parallel usage ledger fossilized by ADR-172/396 (billing collapsed to `balance_usd` + the one `execution_events` meter); no live billing reads it. A migration drops the table.

**D7 — `render/` (the service source tree) is deleted from the repo** — after the compose port. `render/skills/`, `render/main.py`, the Docker/compose config — all gone.

**D8 — Historical ADRs and analyses are NOT rewritten.** The ~80 doc references across `docs/adr/*` and `docs/analysis/*` are lineage. Only the *live* canonical docs update (§5).

## 4. What this ADR does NOT do

- **Does not touch the lane tool surface** (ADR-411 D3's five file verbs stand). The render cut and the models-vs-platforms axis are deliberately separate passes.
- **Does not decide how generation returns** (raw model vs member-attached MCP connector) — the separate ADR-413-descendant discourse ("engine breadth vs connector breadth"), demand-gated.
- **Does not remove external-channel sharing** (Slack/Notion exporters, ADR-185/202).
- **Does not remove the compose substrate or the composed-report surface** — compose moves in-API (§2c); only the two matplotlib chart *kinds* degrade to tables.
- **Does not collapse `DispatchSpecialist`** — named follow-on (§2a), the specialist-dispatch architecture cleanup on its own.
- **Does not add a new deployed service or dependency.** Net footprint strictly shrinks; the API gains a pure-Python module, no new pip deps (matplotlib is deliberately NOT ported).

## 5. Doc cascade (lands with the code commit)

- **CLAUDE.md** — "Render Service Parity" table 4 → 3; env-var matrix strips `RENDER_SERVICE_*`; the `RuntimeDispatch` / output-gateway rows in "File Locations" retire; the yarnnn-render impact-trigger row goes.
- **SERVICE-MODEL.md** — "Deployed Services" 4 → 3; the "How Output Gets Displayed and Delivered" section drops the render-service export/asset lines (retains in-API compose-to-HTML + Slack/Notion sharing).
- **FOUNDATIONS.md** — the Axiom-1 audit-ledger gloss drops `render_usage`.
- **primitives-matrix.md** — `RuntimeDispatch` moves to the deleted-primitives ledger.
- **docs/integrations/RENDER-SERVICES.md** + **docs/features/{image,video}-generation.md** — marked retired (banner pointing here), not deleted, so lineage reads.
- **api/prompts/CHANGELOG.md** — entry per the Prompt Change Protocol (RuntimeDispatch tool-def + designer prompts removed).

## 6. Sequencing

One commit to main, subtraction + the compose port, landed independently of the models/platforms axis:

1. Delete `RuntimeDispatch` (primitive, registry, permission row, skill-def) + strip `orchestration.py` designer prompts + collapse `designer` to compose-only. *(done)*
2. Delete `render_assets.py`. *(done — no live caller)*
3. Retire the `download`/`pdf` stub; keep Slack/Notion + markdown/html. *(done)*
4. **Port compose in-API** (`compose/engine.py`, matplotlib kinds dropped) + switch the two callers to direct calls.
5. Migration: drop `render_usage` + `get_monthly_render_count`.
6. Delete `render/`; remove `RENDER_SERVICE_*` env vars (Render MCP across all services); decommission the `yarnnn-render` deployment.
7. Doc cascade (§5).
8. Gate: a regression test asserting no live import of `runtime_dispatch` / `render_assets` / `RENDER_SERVICE_URL`, no `render_usage` reference outside migrations + historical docs, and that `compose_html` resolves in-API (no HTTP).

Verify: the API boots with the primitive gone; a delivery on substrate-with-sections produces styled HTML via the in-API engine (chart kinds → tables); `tsc --noEmit` clean on any FE touch.
