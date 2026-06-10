# ADR-335 — The Perception Field: Watches, the Observation Contract, and Transports-as-Drivers

**Status:** **Proposed (draft — ratification pause)** (2026-06-10) — drafted for operator ratification per the Stage-C fence. **No code lands on this ADR until ratified.** This is arc 3 of the three-arc reality-in sequence (ADR-330 outcomes-in · ADR-331 doors/setup · this = senses). Its conceptual foundation was *fixed* by [ADR-332 D5](ADR-332-four-flow-completeness-model.md) so it cannot drift; this ADR turns that fixed foundation into a buildable shape.
**Date:** 2026-06-10
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon — real-operator-facing) — but **drafted under the Hat-B fence**: ratification gates the Hat-A landing.

> **Discourse base:** [`perception-under-calibration-arc3-foundation-2026-06-10.md`](../analysis/perception-under-calibration-arc3-foundation-2026-06-10.md) (the fixed foundation — §2 three-layer cut, §3 perception-under-calibration, §4 watch-first discipline, §5 MCP-client posture, §6 crawl/walk/run staging, §8 feasibility + dependency ordering), succeeding [`four-flow-completeness-and-program-floor-2026-06-10.md`](../analysis/four-flow-completeness-and-program-floor-2026-06-10.md) §2 (the perception-field correction: *reading is commodity, the declared/distilled/tenured field is not*). Receipts re-verified against live `api/` + the alpha-trader bundle on 2026-06-10 (§3 below).

**Amends (on ratification):**
- [ADR-332](ADR-332-four-flow-completeness-model.md) — enacts D5 (the perception field, foundation-fixed) + D4 (the *general* four-flow conformance gate lands here, extending the ADR-330 D4 first-instance). FOUNDATIONS axiom-text for D5's candidate clauses lands here, not at ADR-332 (which was framing-only).
- [ADR-280](ADR-280-substrate-abi.md) — adds a `substrate_abi.watches` declaration block, the perception twin of ADR-330's `substrate_abi.ground_truth`.
- [ADR-287](ADR-287-bundle-conformance-discipline.md) — the four-flow conformance assertion extends the bundle-conformance gate (same-commit discipline).
- [ADR-169](ADR-169-mcp-context-hub.md) — YARNNN is already an MCP *server* (context out); this adds the symmetric **MCP client** (perception in). The two faces share no code path beyond the SDK family.
- [ADR-331](ADR-331-setup-as-rendering.md) — the harvest read-tool surface (Mode-A) gains MCP-client-resolved transports; a watch can graduate a harvest into a recurrence via the existing ADR-205 path.

**Preserves:** FOUNDATIONS Axioms 0–9 (D-A below is a derived-principle + Axiom-4/Axiom-1 clause addition, not an axiom replacement) · [ADR-153](ADR-153-platform-content-sunset.md) (no continuous-sync-into-unattributed-shadow-table — observations are *distilled*, attributed, bounded; the opposite shape) · [ADR-209](ADR-209-authored-substrate.md) (every observation is an attributed revision) · ADR-330's `OutcomeCandidate` attestation enum (reused verbatim — no new taxonomy) · ADR-222 no-workspace-types · the dual-tracking bright line (no "perception manager" / no source-freshness state table — the substrate is the record).

---

## 1. Problem statement

The four-flow model (ADR-332) names flow 1's **world-present** cell — *the perception field*: what the operation watches, independent of itself. It is the last underbuilt flow. Three facts set the problem:

**Fact A — the pattern is proven, but program-private.** alpha-trader runs the perception field end-to-end today (receipts §3): `_universe.yaml` (the operator's declared watch) → `track-regime` / `track-universe` recurrences (cadenced reads) → `_regime.yaml` + per-ticker `{TICKER}.yaml` (distilled signal substrate) → `signal-evaluation` (wakes on threshold) → `by_signal` expectancy attribution in `_money_truth.md` (flow 4 judging *which watches earned their attention*). Every piece is post-collapse kernel machinery (recurrences, wake sources, mechanical mirrors, attributed writes) — **except the watch-declaration vocabulary, which is trader-private.** No generic workspace can declare a watch.

**Fact B — the conventional answer is a trap.** "Add a connector catalog; value = coverage" commoditizes twice: Zapier/Composio industrialized it, and MCP is now commoditizing *them* (every platform ships its own MCP server). A connector catalog is a mechanism bet on a layer being turned into a public utility. The durable move is a **representation bet** — axiomatize the *form perception takes*, leave transports swappable (the same move filesystem-native substrate made for persistence, and ADR-330 made for outcomes).

**Fact C — perception is calibratable, and that is the moat.** No integration platform has a concept of *whether a feed deserved the attention*. The trader's `by_signal` attribution already proves flow 4 judges attention, not just actions. **Reading the world is commodity; the declared, distilled, tenured perception field — pruned by calibration over tenure — is not.** It is the substrate's world-facing half (ESSENCE v14.1).

The gap: promote the trader-private watch pattern to a **kernel slot** (the third arc of the same move — ADR-330 did it for ground-truth, ADR-331 for doors), with a transport posture that consumes the commodity layer from the ecosystem rather than building it.

---

## 2. Decision summary

| # | Decision | Shape | Build stage |
|---|---|---|---|
| **D1** | **The three-layer cut** (foundation-fixed by ADR-332 D5, ratified here): **Declaration** (kernel, axiomatic — what the operation watches) · **Observation contract** (kernel, axiomatic — reality enters *only* as attributed, distilled observation) · **Transport** (deliberately commodity — REST/RSS/CSV/MCP, a driver class the kernel knows by contract, never by device). | Canon + (Crawl) | — |
| **D2** | **`substrate_abi.watches` kernel slot** — the perception twin of ADR-330's `substrate_abi.ground_truth`. A bundle declares its watches (shape, cadence, target signal-substrate path); the trader's `_universe.yaml` becomes the first instance of a kernel-declared watch, not a program-private file. | Bundle + backend | Crawl |
| **D3** | **The observation contract reuses ADR-330's attestation enum verbatim.** An observation is `{watch_id, source_ref, attestation (platform\|operator\|agent), observed_at, distilled_content}` written to attributed signal substrate. No new taxonomy — the perception twin of `OutcomeCandidate`. | Backend + canon | Crawl |
| **D4** | **MCP client in the kernel — the one transport investment that earns kernel status.** One implementation makes every platform's MCP server a Mode-A read transport, capability-gated, usable by harvest (ADR-331) + recurrences. **Zero bespoke connectors, ever.** Bindings stored on the `platform_connections` pattern (encrypted, existing OAuth). | Backend | Crawl |
| **D5** | **Watch-first, transport-second — the anti-capability-shopping bright line.** A transport enters the workspace **only because a declared watch needs it**. Never "browse the marketplace and add interesting perception." The declaration layer (judgment) stays sovereign over the transport layer (commodity). | Discipline (binding) | All |
| **D6** | **Perception-under-calibration: flow 4 judges attention.** The watch declaration is a *portfolio of attention*; calibration prunes it over tenure. Generalizes the trader's `by_signal` proof — the calibration mirror (ADR-327) gains a per-watch "earned its attention?" read. | Backend (light) + canon | Walk |
| **D7** | **One small generic transport for connectionless workspaces** (cadenced web/RSS read) so a no-platform workspace can watch *something* — and a `registry`-resolved binding (the marketplace move) at Walk. | Backend | Walk |
| **D8** | **FOUNDATIONS axiom-text for the four candidate clauses** lands here (ADR-332 D5 deferred the axiom-grade treatment to arc-3 ratification): *reality enters only as attributed observation · watches are declared, never crawled · transports are peripherals · attention is calibrated.* | Canon | Crawl (ratification) |
| **D9** | **The general four-flow conformance gate** (ADR-332 D4, deferred) lands here: every active program declares all four flows or marks one N/A with rationale, asserted in `api/test_adr287_bundle_conformance.py`. | Test gate | Crawl |

**Anti-goals (binding, stated so future sessions don't re-open them):**

- **No connector catalog, ever.** Transports are drivers consumed from the ecosystem; the kernel ships one MCP client + one generic web/RSS read, never a catalog of bespoke integrations.
- **No "perception manager" subsystem.** No source-freshness table, no `_perception_tracker.md`, no `sync_registry` rebirth — the dual-tracking disease (Derived Principle 7). What's been observed = the attributed observations that exist in signal substrate.
- **No continuous sync / no mirroring** (ADR-153 stands permanently). Reality enters *distilled*, never raw-crawled into a shadow table.
- **No raw foreign-tool output into substrate.** A bound MCP server is untrusted input: its output enters only as distilled, attributed observations; consequential actions stay Reviewer-gated.
- **No workspace-level watch declarations** (Direction A / ADR-332 D3). Watches are declared by *programs*; a freehand workspace-level watch path would revive the shapeless-generic-workspace route Direction A closed. Operator-assembled programs (the route-i horizon) declare watches *as a program*, never freehand.

---

## 3. Receipts — the perception field is real, today (program-private)

Live, 2026-06-10, alpha-trader bundle:

- **Watch declaration:** `docs/programs/alpha-trader/reference-workspace/operation/trading/_universe.yaml` — `tickers: [AAPL, MSFT, NVDA, SPY, TSLA]`, `tier: authored`, operator-editable, machine-parsed by `trading_universe_tracker.py`. *This is a watch — but program-private vocabulary; no kernel slot declares it.*
- **Cadenced reads:** `_recurrences.yaml` — `track-universe` (three RTH snapshots, `mode: mechanical`, `@primitive: TrackUniverse()`) + `track-regime`. The reads happen on a Trigger (Axiom 4), not a crawl.
- **Distilled signal substrate:** per-ticker `{TICKER}.yaml` + `_regime.yaml` (declared in `substrate_abi.path_zones[*].accumulating_files`). Distilled, not mirrored — the ADR-153 line, already honored.
- **Wake on threshold:** `signal-evaluation` (`mode: judgment`) reads the distilled snapshots and emits `ProposeAction` inline when conditions warrant.
- **Flow-4 calibration of attention:** `by_signal` per-signal expectancy in `_money_truth.md` (`api/services/outcomes/ledger.py` — `by_signal` totals + rolling windows). *This is the loop reporting which watched signals earned their keep* — perception-under-calibration, proven end-to-end.

**The generalization (this ADR):** every one of those is kernel machinery except the watch-declaration vocabulary. Promote it to `substrate_abi.watches` — the third trader-private pattern raised to kernel slot, after `substrate_abi.ground_truth` (ADR-330) and the `/setup` flow-walk (ADR-331).

---

## 4. D1 — The three-layer cut

Perception is not data ingestion. The kernel question is never "how do we get data in" — it is **"what does this operation believe about the world, on what evidence, attested by whom, as of when."** Three layers, each with a distinct durability class:

| Layer | What it is | Where it lives | Durability |
|---|---|---|---|
| **1. Declaration** | The operation declares what it watches — judgment about which slice of infinite reality serves the mandate. | `substrate_abi.watches` (bundle) → operator-editable watch substrate (e.g. `_universe.yaml`) | **Cannot commoditize** — it is selection, not technology. The scarce thing. |
| **2. Observation contract** | Reality enters *only* as an observation: attributed, attested, source-referenced, dated, **distilled**. The perception twin of `OutcomeCandidate`. | Attributed signal substrate (`{entity}.yaml`, `_regime.yaml`, …) via Axiom 1 | Representation bet — outlives any protocol. |
| **3. Transport** | REST, RSS, CSV, MCP, whatever follows MCP. The kernel knows the **driver-class contract**, never the device. | `platform_connections` pattern (bindings) + the MCP client (D4) | Swappable by design; consumed from the ecosystem. |

OS framing pays rent: **transports are device drivers; MCP is USB; the registry is the driver repository.** Identity never lives in the transport layer.

**The cadence dial (named principle, discourse-earned 2026-06-11):** a harvest (ADR-331 Mode-A) and a standing watch are **one move** — the same observation contract with a cadence ranging from `once` to `forever`. A harvest is a watch with `cadence: once`; a standing watch is a harvest with a standing Trigger. Graduation between them is the perception instance of the inline-action → task gradient (FOUNDATIONS Axiom 9 Clause C): attaching a cadence to a one-shot read is the same gradient-and-reversible move as attaching a nameplate + pulse to an inline action. This is why D2's `cadence` field is not metadata — it is the dial that determines whether a declared watch compiles to a recurrence (the existing `_recurrences.yaml` machinery, unchanged) or fires as a single invocation. Two acts stay distinct beneath the dial: **binding a transport** (one-time capability grant, Layer 3, `platform_connections` governance) and **declaring a watch** (Layer 1 judgment, cadence-bearing) — connecting a server is never itself perception.

---

## 5. D2 — The `substrate_abi.watches` kernel slot

The perception twin of `substrate_abi.ground_truth` (ADR-330 D4). A bundle declares its watches; the kernel reads the declaration the same way `bundle_reader.get_ground_truth_for_workspace` reads ground-truth.

**Draft shape (to refine at ratification):**
```yaml
substrate_abi:
  ground_truth: operation/trading/_money_truth.md     # ADR-330
  watches:                                            # ADR-335 (this ADR)
    - id: universe
      shape: instrument_price_oracle                  # perception SHAPE, not a vendor
      declaration: operation/trading/_universe.yaml   # operator-editable watch substrate
      cadence: "@market_open + 15min; @market_open + 3h; @market_close - 1h"
      distills_to: operation/trading/{TICKER}.yaml    # the attributed signal substrate
      attestation: platform                           # ADR-330 enum (resolved per binding at runtime)
    - id: regime
      shape: market_regime
      declaration: operation/trading/_operator_profile.md
      cadence: "@market_open"
      distills_to: operation/trading/_regime.yaml
```
- **Shape, not vendor** (the durability dividend, foundation §6): a bundle declares a perception *shape* ("continuous price oracle"); the vendor binding (Alpaca, an MCP server) is **late-bound at setup-time** — exactly where ADR-331's sequence lives. Bundles get *more* durable.
- **`new bundle_reader.get_watches_for_workspace(user_id, client)`** mirrors `get_ground_truth_for_workspace` (iterates active-for-workspace bundles). No new loader pattern.
- **The trader's `_universe.yaml` is the first instance** — it stops being trader-private and becomes a kernel-declared watch. (Migration: add the `watches:` block to alpha-trader's MANIFEST; the file + recurrences are unchanged.)

---

## 6. D3 — The observation contract (reuse the attestation enum)

Reality enters only as an **observation** — the perception twin of `OutcomeCandidate`, reusing ADR-330 D2's attestation enum verbatim (no new taxonomy):

| Field | Meaning |
|---|---|
| `watch_id` | which declared watch produced it |
| `source_ref` | the transport + container it came from (URL, MCP server + tool, channel id) |
| `attestation` | `platform` \| `operator` \| `agent` — **same enum as ground-truth** (an official-platform MCP server ≈ `platform`; a community server ≈ weaker; an agent-asserted read ≈ `agent`) |
| `observed_at` | when reality was read (dated) |
| `distilled_content` | the *distilled* signal — never the raw payload (ADR-153) |

- **Written to attributed signal substrate** via the Authored Substrate (`agent:` or `system:` attribution per ADR-209), same revision chain as everything else. Subject to the same distill-don't-mirror rule.
- **Attestation is load-bearing for the same reason it is in ground-truth:** an operator-imported observation or an agent-scraped read must never be weighted like an independent platform read. Label-first (the ADR-330 D2 posture); weighting deferred.
- **Substrate-aware, transport-blind (binding, discourse-earned 2026-06-11):** judgment never knows the device. The Reviewer — and any judgment recurrence — reads only the distilled signal substrate; whether an observation arrived via REST, CSV, or an MCP server is invisible above this contract. The *only* thing that crosses the layer boundary upward is `attestation`, and it crosses as a **property of the observation** (a trust grade), never as device-awareness. This is what licenses Layer 3 to stay commodity (D1/D5): nothing above the observation contract can develop a dependency on a transport, so transports remain swappable forever.
- **Open at ratification:** whether the observation is a typed Python shape (an `Observation` TypedDict alongside `OutcomeCandidate`) or stays a per-bundle substrate convention. Foundation §7 leaves the contract schema to this ADR; lean is **convention-first** (the trader proves it works as substrate convention without a typed shape), promote to a typed contract only if a second program needs it.

---

## 7. D4 — The MCP client (the one transport that earns kernel status)

YARNNN is already an MCP *server* (ADR-169 — context out). The symmetric move: **one MCP-client implementation in the kernel.** This is the architecturally-scalable form of "integration-maxxing" — and the only transport-layer investment that earns kernel status, because one implementation makes the ecosystem build the driver catalog for free, forever.

- **Feasibility (verified, foundation §8):** the official registry is live with a queryable API (`registry.modelcontextprotocol.io`); remote servers standardized on OAuth 2.1 + `.well-known` discovery; the protocol is moving to a stateless HTTP core (a structural fit for stateless-computation-over-substrate). Crawl-stage build is small: MCP client in the API (same SDK family as the existing FastMCP server), bindings on the `platform_connections` pattern, foreign tools surfacing as dynamic entries in the existing capability-gated dispatch.
- **Hard parts are non-protocol** (named, not solved here): per-server consent UX, tool-schema heterogeneity, community-server quality variance, injection surface (already disciplined — distill-only, Reviewer-gated), foreign-call cost (the budget gate already meters).
- **Binding is an epistemic + security act (D5 qualification 2):** every binding carries an attestation grade from registry provenance; foreign tool output is untrusted input.

---

## 8. D5 — Watch-first, transport-second (the bright line)

The failure mode is "browse the marketplace and add interesting perception" — the connector-catalog disease wearing the new protocol. **A transport only ever enters because a declared watch needs it.** Watch-first, transport-second, always. The flow (foundation §4):

1. Operator (or program) **declares a watch** ("watch these competitors' changelogs").
2. The system **resolves a transport**: first against already-connected transports, then by searching the MCP registry (Walk).
3. Candidates surface as a **proposal**; the operator **authorizes the binding** — a trust grant, same governance shape as `platform_connections`.
4. The watch goes live: a recurrence reads through the transport, **distills observations into attributed substrate**, narrative-traced.
5. **Calibration eventually prunes** (D6): which watches earned their attention.

The declaration layer (judgment) is sovereign over the transport layer (commodity). This is the discipline that keeps the perception field a representation bet, not a mechanism bet.

---

## 9. D6 — Perception-under-calibration (flow 4 judges attention)

The watch declaration is a **portfolio of attention**. The trader proves the loop already judges it: `by_signal` expectancy in `_money_truth.md` reports which watched signals earned their keep. Generalized:

- The calibration mirror (ADR-327 `mirror_calibration.py`) gains a per-watch read: for each declared watch, *did the observations it produced contribute to outcomes / proposals / verdicts?* — the perception analog of the per-recurrence "fired but produced no value" line it already writes.
- **Calibration prunes over tenure** — a watch that never feeds a consequential decision is surfaced as a pruning candidate (the operator decides; the mirror states evidence, never verdicts — same posture as today).
- This is the layer beyond MCP-maxxing: no integration platform knows whether a feed deserved the attention. The cut: **declared + distilled + tenured + calibrated** perception.

---

## 10. D8 — FOUNDATIONS axiom-text (draft — lands at ratification)

ADR-332 D5 fixed the four candidate clauses but deferred axiom-grade treatment to here. **Draft text for operator ratification** (final wording set at ratification; no FOUNDATIONS edit lands until then):

> **Axiom 1 (Substrate) clause addition / Axiom 4 (Trigger) relation:**
> *Reality enters the substrate only as attributed observation — distilled, source-referenced, attested, dated; never raw-mirrored (Axiom 1 + ADR-153). Watches are declared, never crawled: the operation authors which slice of infinite reality it perceives (Declaration), and a Trigger reads it on cadence (Axiom 4) — the cadence dial spans once-to-forever, so a one-shot harvest and a standing watch are one observation contract distinguished only by Trigger shape. Transports are peripherals — a driver class the kernel knows by contract, never by device; judgment is substrate-aware and transport-blind, with attestation the only property that crosses the boundary. Attention is calibrated: the watch declaration is a portfolio of attention, and the loop (flow 4) judges which watches earn their keep, the same way it judges acts.*

Plus a new **Derived Principle 27** (draft): *Perception is the operation's epistemics under calibration — the world-facing half of the cumulative substrate. Reading the world is commodity; the declared/distilled/tenured/calibrated perception field is the asset.*

GLOSSARY: promote the reserved "perception field" row to canonical + add **watch** and **observation** full entries (currently reserved by ADR-332 / GLOSSARY v2.4 for arc-3).

---

## 11. D9 — The general four-flow conformance gate (lands here)

ADR-332 D4 deferred the *general* conformance assertion to arc-3; ADR-330 D4 was the first instance (ground-truth). This ADR adds the full assertion to `api/test_adr287_bundle_conformance.py` (per ADR-287 same-commit discipline): **every active program declares all four flows — context-in (watches OR uploads OR websearch), work-out (deliverable specs / capabilities), outcomes-in (`substrate_abi.ground_truth`), the loop (a judgment recurrence) — or explicitly marks a flow `N/A` with rationale.** alpha-author's lean shape (uploads + websearch, no platform watch) stays valid — perception is a flow, never a gate (ADR-332 §2 guard).

---

## 12. Staging (crawl / walk / run) — foundation §6, ratified here

| Stage | What ships | Trust shape | Demand-pull trigger |
|---|---|---|---|
| **Crawl** | `substrate_abi.watches` slot (D2) + observation contract (D3) + kernel MCP client (D4) with operator-pasted server configs (manual binding) + FOUNDATIONS axiom-text (D8) + conformance gate (D9). alpha-trader's `_universe.yaml` migrated to a kernel-declared watch. | Operator authorizes each binding explicitly. | bundle #3, first non-trader watch need, or alpha-author post-330 deepening (ADR-332 D5) |
| **Walk** | Registry search resolves declared watches into **proposed** bindings (the marketplace move, D7) + one generic cadenced web/RSS transport for connectionless workspaces + per-watch calibration read (D6). | Proposal → operator authorization; attestation grade from registry provenance. | a watch needs a transport the workspace hasn't connected |
| **Run** | The Reviewer notices a perception gap against the mandate and itself **proposes** a new watch + transport — perception management under the same propose/approve loop as capital actions. | Fully inside the existing judgment loop; delegation-level gated. | the Reviewer demonstrably needs perception it doesn't have |

**The dependency ordering (foundation §8, ratified):** ADR-330/331 implementation (✅ landed) → **this ADR's Crawl stage** → the **program-assembly ADR** (route i — inference drafts the four flow declarations; ADR-332 §5 ledger) → Walk (registry resolution inside setup). Each arc makes the previous more valuable.

---

## 13. What this ADR explicitly does NOT do

- Does not build a connector catalog (transports are drivers from the ecosystem; one MCP client + one web/RSS read, never a catalog).
- Does not add a "perception manager," source-freshness table, or `_perception_tracker.md` (dual-tracking bright line; the substrate is the record).
- Does not revive continuous sync or raw mirroring (ADR-153 stands permanently).
- Does not let foreign-tool output into substrate raw (distilled, attributed observations only; consequential actions Reviewer-gated).
- Does not add a new attestation taxonomy (reuses ADR-330 D2's enum).
- Does not add workspace-level watch declarations (Direction A / ADR-332 D3 — watches are program-declared; route-i assembly declares them *as a program*).
- Does not implement attention *weighting* in calibration (label-first; weighting deferred, mirroring ADR-330 D2).
- Does not build the program-assembly route-i door (separate ADR, ADR-332 §5 ledger, after this).
- **Does not land any code, FOUNDATIONS edit, GLOSSARY entry, or conformance-gate change until ratified** (Stage-C fence).

---

## 14. Render-service parity (at Crawl implementation, post-ratification)

- The MCP client (D4) runs inside the **API** (same SDK family as the FastMCP server) and the **Unified Scheduler** (recurrences read through it). Bindings reuse the `platform_connections` table + existing OAuth machinery — **no new storage, no new secret** beyond per-binding encrypted tokens (the existing `INTEGRATION_ENCRYPTION_KEY`).
- The generic web/RSS read (D7) is a read tool on the API + Scheduler — no new service.
- **No env-var changes that aren't already present on API + Scheduler.** MCP-server (the existing yarnnn-mcp-server, context-out) is untouched — the client is a *different* surface. Output gateway untouched.
- *Confirm at implementation:* the MCP client's per-server consent + cost metering route through the existing budget gate (foundation §8).

---

## 15. Open questions (carried, not resolved — resolved at ratification or later)

1. **Observation contract form** — typed `Observation` TypedDict vs substrate convention. (Lean: convention-first; promote on second-program demand — §6.)
2. **Watch calibration metric** — what exactly "earned its attention" measures for non-trading watches without a clean `by_signal` analog. (Walk-stage; the trader's expectancy is the template, generalization TBD.)
3. **Registry provenance → attestation grade mapping** — official vs community vs unverified server → which enum value. (Walk-stage, D7.)
4. **Webhook / push ingestion** — pull + wake-on-event (existing wake sources) first; push deferred (foundation §7).
5. **`N/A`-flow rationale schema** — how a bundle marks a flow N/A in MANIFEST for the D9 gate. (Resolve at the conformance-gate commit.)
