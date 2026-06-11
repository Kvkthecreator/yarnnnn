# ADR-336 — The Web/RSS Standing Watch: TrackWebSources, Prediction-Graded Attention, and the Path to the Interest-Scout Program

**Status:** **Accepted (2026-06-11)** — P2 Implemented same-day (TrackWebSources primitive + alpha-author bundle watch + live binding contract test on the anr-scout soak); P3 ratified as convention (prediction grading — first instance lands with the soak's reconciliation cycles); P4 (interest-scout bundle) scoped, next bundle cycle.
**Date:** 2026-06-11
**Deciders:** KVK (operator: "the leverage and phasing is correct… proceed") + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [`perception-rungs-2-4-psychographic-consumer-2026-06-11.md`](../analysis/perception-rungs-2-4-psychographic-consumer-2026-06-11.md) (the investment ladder; sequencing ≠ importance — P3+P2 are the product). Enacts **ADR-335 D7** (the generic transport for connectionless workspaces), pulled forward from Walk per the R3 staging refinement ("the first such demand may equally pull D7 forward") — the psychographic ICP is that demand. P1 (rung-2 websearch) validated 2026-06-11 (`2026-06-11-051153`, honest-null trap held).

**Enacts:** ADR-335 D7 (generic cadenced web/RSS read) against the Crawl-A kernel slots (watches declaration + observation contract + Check 7, all landed).
**Preserves:** every ADR-335 anti-goal — no connector catalog, no perception manager, no raw mirroring (ADR-153: feed entries are already summaries; we distill further and cap), no new attestation taxonomy, transports-as-peripherals (this executor is a driver; an MCP binding can replace it under the same watch with zero redesign).

---

## D1 — `TrackWebSources`: one mechanical primitive, program-agnostic

`api/services/primitives/track_web_sources.py::handle_track_web_sources` — the web-transport sibling of `TrackUniverse` (same shape: deterministic, zero-LLM, dispatcher-only, `HANDLERS`-registered, never in an LLM tool surface).

- **Directive** (paths from args — the kernel hardcodes no program's topology):
  `@primitive: TrackWebSources(declaration="<path>/_sources.yaml", distills_to="<path>/_watch_signal.yaml")`
- **Declaration substrate** (`_sources.yaml`, operator-editable — the web analog of `_universe.yaml`): `sources: [{id, url, kind: rss|atom (auto-detected), attestation?: platform|agent (default platform — a first-party publisher feed attests its own publication facts), max_entries?: int}]`. Source count capped (12) — a portfolio of attention, not a crawler.
- **Fetch**: httpx, 15s timeout, honest UA, no auth (authenticated sources are rung-3/4b territory). Per-source failure isolates (one dead feed ≠ dead watch); failures land in the result's `errors` + the signal file's per-source `status` — absence/error is perceivable from the record (ADR-335 D5-governance), no freshness table.
- **Parse**: stdlib `xml.etree` for RSS 2.0 + Atom (title / link / published / summary). **No new dependency** — render-parity across all 4 services is untouched.
- **Distill** (deterministic — keeps mechanical zero-LLM): per source keep the newest `max_entries` (default 8) entries, summaries truncated ≤ 280 chars, HTML stripped. Semantic reading happens at judgment wakes, never here.
- **Observation contract** (ADR-335 D3, convention-first): the signal file carries per-source blocks `{source_ref: url, attestation, observed_at, status, entries: [...]}` — `watch_id` is the file's frontmatter-level `watch:` key. Written via `write_revision(authored_by="system:track-web-sources")`.

## D2 — alpha-author gains its standing watch (the lean shape graduates)

The bundle's `flows_na.perception` rationale said audience watches activate "at which point a `watches:` block replaces this rationale." That point is now:

- MANIFEST `substrate_abi.watches`: `{id: interest-sources, shape: web_press_feed, declaration: operation/authored/_sources.yaml, recurrence: track-sources, distills_to: operation/authored/_watch_signal.yaml}`; `flows_na.perception` REMOVED (Singular — the flow is now declared, not excused).
- `_recurrences.yaml`: `track-sources` (mechanical, daily 11:30 UTC — 30min before the corpus-coherence judgment wake, so the watch is fresh when judgment reads it).
- `reference-workspace/operation/authored/_sources.yaml`: authored-tier template, empty sources (empty = no-op; the lean pre-audience shape stays valid — perception is a flow, never a gate).
- `reviewer_wake_envelope` += `{key: watch_signal, path: operation/authored/_watch_signal.yaml, optional: true}` — judgment perceives the watch per ADR-281, zero kernel edits.

## D3 — Prediction-graded attention (P3, ratified as convention)

The consumer analog of `by_signal` expectancy: **a watch-call with a named trigger is a falsifiable prediction**. Convention (no new kernel): every brief's `call:` carries its trigger (already the editorial standard — mara-voss: "upgrade trigger = retention holds while geo diversifies"); the reconciliation/coherence cycles grade open calls against subsequent observations (including `_watch_signal.yaml` entries) into the program's ground-truth file (`_signal.md`) as `{call, trigger, graded: confirmed|refuted|open, evidence}` entries. Flow 4 then judges both the calls AND the watch that fed them (Check 7 + calibration mirror). First instance accumulates on the anr-scout soak; promote to typed shape only on second-program demand (the ADR-335 §6 rule).

## D4 — The interest-scout bundle (P4, scoped — next bundle cycle)

Generalizes the anr-scout judgment shape into the consumer's activatable program: declared interest set → `_sources.yaml` watches → periodic briefs with triggered calls → prediction-graded ground truth. Direction A compliant. Ships as `docs/programs/interest-scout/` after the soak validates D1–D3 over real tenure. NOT built in this ADR.

## Validation (the e2e ADR-335 couldn't run)

1. **Gates**: `test_adr336_web_watch.py` (parser fixtures + distillation + registration) + ADR-287/335 conformance (alpha-author now passes via `watches`, pointer resolves).
2. **Binding contract test** (the per-binding test the canon prescribed): direct invocation against the live anr-scout workspace with real music-press feeds — receipts: `_watch_signal.yaml` revision + entry counts.
3. **Judgment leg**: addressed wake reads the watch signal into corpus judgment.
4. **Standing**: `track-sources` daily on the soak clock; Check 7 (transport-blind) covers it unchanged; tenure reads grade D3 from read #2.
