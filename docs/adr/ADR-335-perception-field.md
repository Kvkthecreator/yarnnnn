# ADR-335 — The Perception Field: Watches, the Observation Contract, and Transports-as-Drivers

**Status:** **Accepted (ratified 2026-06-11) — Crawl-A Implemented same-day.** Drafted 2026-06-10 under the Stage-C fence; operator ratified 2026-06-11 after the runtime audit (§3b). **Crawl-A landed**: D2 `substrate_abi.watches` slot (alpha-trader's `_universe.yaml` promoted to kernel-declared watch; `watch_declaration` joins the Reviewer wake envelope per ADR-281) + D3 observation contract (convention-first, ratified) + D8 FOUNDATIONS v9.3 (Axiom 1 eighth sub-clause + Derived Principle 27) + GLOSSARY v2.5 (perception field canonical; Watch + Observation entries) + D9 general four-flow conformance gate (`api/test_adr287_bundle_conformance.py`, 16/16; alpha-author declares `flows_na.perception`). **Crawl-B (D4 MCP client) demand-pulled; D6/D7 Walk gated empirically per §12.** This is arc 3 of the three-arc reality-in sequence (ADR-330 outcomes-in · ADR-331 doors/setup · this = senses). Its conceptual foundation was *fixed* by [ADR-332 D5](ADR-332-four-flow-completeness-model.md) so it cannot drift.
**Date:** 2026-06-10 (ratified + Crawl-A 2026-06-11)
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
| **D4** | **MCP client in the kernel — the one transport investment that earns kernel status.** One implementation makes every platform's MCP server a Mode-A read transport, capability-gated, usable by harvest (ADR-331) + recurrences. **No new bespoke tail connectors** (existing Direct API clients are retained head-platform drivers — see §7). Bindings stored on the `platform_connections` pattern (encrypted, existing OAuth). | Backend | Crawl |
| **D5** | **Watch-first, transport-second — the anti-capability-shopping bright line.** A transport enters the workspace **only because a declared watch needs it**. Never "browse the marketplace and add interesting perception." The declaration layer (judgment) stays sovereign over the transport layer (commodity). | Discipline (binding) | All |
| **D6** | **Perception-under-calibration: flow 4 judges attention.** The watch declaration is a *portfolio of attention*; calibration prunes it over tenure. Generalizes the trader's `by_signal` proof — the calibration mirror (ADR-327) gains a per-watch "earned its attention?" read. | Backend (light) + canon | Walk |
| **D7** | **One small generic transport for connectionless workspaces** (cadenced web/RSS read) so a no-platform workspace can watch *something* — and a `registry`-resolved binding (the marketplace move) at Walk. | Backend | Walk |
| **D8** | **FOUNDATIONS axiom-text for the four candidate clauses** lands here (ADR-332 D5 deferred the axiom-grade treatment to arc-3 ratification): *reality enters only as attributed observation · watches are declared, never crawled · transports are peripherals · attention is calibrated.* | Canon | Crawl (ratification) |
| **D9** | **The general four-flow conformance gate** (ADR-332 D4, deferred) lands here: every active program declares all four flows or marks one N/A with rationale, asserted in `api/test_adr287_bundle_conformance.py`. | Test gate | Crawl |

**Anti-goals (binding, stated so future sessions don't re-open them):**

- **No connector catalog, ever.** Transports are drivers consumed from the ecosystem; the kernel ships one MCP client + one generic web/RSS read, never a catalog of bespoke integrations. **Qualified (2026-06-11): "no bespoke connectors" means no *new* bespoke connectors *for tail perception*.** The existing Direct API clients (`slack_client.py`, `notion_client.py`, `alpaca_client.py`) are **retained drivers of the same driver class** — hand-authored where reliability is existential (head platforms a program's primary action or ground-truth depends on). A future program may still earn a hand-authored head driver; the catalog disease is building drivers for the *tail*.
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

## 3b. Pre-ratification runtime audit (2026-06-11) — five flags, five receipts

The ratification audit checked the watch model against the live runtime. All five flags resolved without new machinery; one draft claim was corrected:

1. **Mechanical wake path** — mechanical recurrences (the watch-read shape) dispatch deterministically via `services/wake.py::_dispatch_mechanical` (mode fork at `wake.py:359`; funnel decision `"mechanical"`), no Reviewer wake, no LLM. Watches with mechanical reads slot into this path unchanged.
2. **Feed weight** — mechanical successes emit **zero** narrative entries by design (ADR-277, `wake.py:1148-1173`); failures + capability transitions emit (material weight on transition). A 3×-daily watch produces no feed spam; binding failures surface as evidence. Nothing to build.
3. **Cost governance (draft claim corrected)** — the pace gate the draft's discourse cited was deleted by ADR-327; cost governance is the wake-funnel window budget, which meters judgment-mode LLM costs only (`wake.py:441-512`). Mechanical external reads (Alpaca in `TrackUniverse`) are zero-LLM and unmetered. §7's foreign-call-cost hard part updated accordingly; MCP-call metering is a Crawl-B item.
4. **Reviewer envelope** — per ADR-281, envelope additions are bundle-declared (`substrate_abi.reviewer_wake_envelope`), zero kernel edits. Crawl-A adds `watch_declaration` (→ `_universe.yaml`) to alpha-trader's envelope so the Reviewer perceives its portfolio of attention. **No persona-frame edit at Crawl-A** — watch-management posture is Run-stage; per Derived Principle 22 it will land in `principles.md`/substrate, not the frame, when Run arrives.
5. **Surface moment** — the perception field already surfaces through program home sections (`TraderRegime` renders `_regime.yaml`, `TraderPositions` merges per-ticker indicator substrate, per ADR-273/312). No perception dashboard; future programs declare their own home sections via SURFACES.yaml.

---

## 4. D1 — The three-layer cut

Perception is not data ingestion. The kernel question is never "how do we get data in" — it is **"what does this operation believe about the world, on what evidence, attested by whom, as of when."** Three layers, each with a distinct durability class:

| Layer | What it is | Where it lives | Durability |
|---|---|---|---|
| **1. Declaration** | The operation declares what it watches — judgment about which slice of infinite reality serves the mandate. | `substrate_abi.watches` (bundle) → operator-editable watch substrate (e.g. `_universe.yaml`) | **Cannot commoditize** — it is selection, not technology. The scarce thing. |
| **2. Observation contract** | Reality enters *only* as an observation: attributed, attested, source-referenced, dated, **distilled**. The perception twin of `OutcomeCandidate`. | Attributed signal substrate (`{entity}.yaml`, `_regime.yaml`, …) via Axiom 1 | Representation bet — outlives any protocol. |
| **3. Transport** | REST, RSS, CSV, MCP, whatever follows MCP. The kernel knows the **driver-class contract**, never the device. | `platform_connections` pattern (bindings) + the MCP client (D4) | Swappable by design; consumed from the ecosystem. |

OS framing pays rent: **transports are device drivers; MCP is USB; the registry is the driver repository.** Identity never lives in the transport layer.

**Context-in primacy (discourse-earned 2026-06-11 — answers "are connectors the first-class perception-in?"):** **No. The operator's own context is the universal first-class context-in; connectors are transports some mandates require.** Flow 1 has three cells (Derived Principle 26): self-past (harvest/uploads), self-present (live reads + operator push), world-present (watches) — connectors serve only part of the third. The primacy ladder: (1) **operator context** — uploads, chat, curated harvest (the ADR-331 doors arc, built + shipped; attestation `operator`); (2) **websearch** — the kernel's binding-free world read (attestation `agent`); (3) **head-platform connectors** — when the mandate's primary action or ground truth lives on a platform (attestation `platform`); (4) **standing tail watches** via web/RSS or MCP (Crawl-B/Walk). **The mandate determines which rungs an operation needs** — alpha-author is flow-complete on rungs 1–2 (`flows_na.perception`, gate-asserted); alpha-trader needs rung 3. A bare workspace's incompleteness is the absence of *declared flows* (no program, Direction A), never the absence of connectors — and canon has always ranked user-contributed/internal perception above raw external (FOUNDATIONS Principle 4, distill-don't-mirror). The operator-context loop is already wake-bearing without any connector: substrate writes from uploads/harvest fire substrate-event hooks (ADR-296) that wake the Reviewer — context as wake-ingredient is rung 1, not rung 4.

**The cadence dial (named principle, discourse-earned 2026-06-11):** a harvest (ADR-331 Mode-A) and a standing watch are **one move** — the same observation contract with a cadence ranging from `once` to `forever`. A harvest is a watch with `cadence: once`; a standing watch is a harvest with a standing Trigger. Graduation between them is the perception instance of the inline-action → task gradient (FOUNDATIONS Axiom 9 Clause C): attaching a cadence to a one-shot read is the same gradient-and-reversible move as attaching a nameplate + pulse to an inline action. This is why D2's `cadence` field is not metadata — it is the dial that determines whether a declared watch compiles to a recurrence (the existing `_recurrences.yaml` machinery, unchanged) or fires as a single invocation. Two acts stay distinct beneath the dial: **binding a transport** (one-time capability grant, Layer 3, `platform_connections` governance) and **declaring a watch** (Layer 1 judgment, cadence-bearing) — connecting a server is never itself perception.

---

## 5. D2 — The `substrate_abi.watches` kernel slot

The perception twin of `substrate_abi.ground_truth` (ADR-330 D4). A bundle declares its watches; the kernel reads the declaration the same way `bundle_reader.get_ground_truth_for_workspace` reads ground-truth.

**Landed shape (ratification refinement, 2026-06-11):**
```yaml
substrate_abi:
  ground_truth: operation/trading/_money_truth.md     # ADR-330
  watches:                                            # ADR-335 (this ADR)
    - id: universe
      shape: instrument_price_oracle                  # perception SHAPE, not a vendor
      declaration: operation/trading/_universe.yaml   # operator-editable watch substrate
      recurrence: track-universe                      # the Trigger pointer — cadence lives ON the recurrence
      distills_to: "operation/trading/{TICKER}.yaml"  # the attributed signal substrate
    - id: regime
      shape: market_regime
      declaration: operation/trading/_operator_profile.md
      recurrence: track-regime
      distills_to: operation/trading/_regime.yaml
```
Two refinements from the draft shape, both ratified 2026-06-11: (1) **`cadence` string replaced by a `recurrence` slug pointer** — the cadence already lives on the recurrence declaration in `_recurrences.yaml` (semantic schedules, authoritative); duplicating it in the MANIFEST would create dual-declaration drift (Singular Implementation). The conformance gate asserts the pointer resolves. (2) **static `attestation` field dropped** — attestation is a per-observation property (D3), resolved per binding at runtime, never a static declaration attribute.
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
- **Hard parts are non-protocol** (named, not solved here): per-server consent UX, tool-schema heterogeneity, community-server quality variance, injection surface (already disciplined — distill-only, Reviewer-gated), and **foreign-call cost metering** — corrected by the 2026-06-11 runtime audit (§3b): the wake-funnel window budget (ADR-327) meters *judgment-mode LLM* costs only; mechanical-mode external reads are zero-LLM and deliberately unmetered today (the Alpaca calls in `TrackUniverse` are unmetered precedent). MCP foreign-call metering for mechanical-mode watches is a named Crawl-B resolution item, not already-solved.
- **Binding is an epistemic + security act (D5 qualification 2):** every binding carries an attestation grade from registry provenance; foreign tool output is untrusted input.

**Transport trust posture — the funnel, ratified 2026-06-11.** The open MCP ecosystem is consumed through a deliberate funnel, never at large. Three structural biases (these qualify the "dynamic entries in capability-gated dispatch" line above):

- **B1 — The marketplace is never an operator surface.** Watch-first (D5) already commits this: operators declare watches; the *system* resolves transports against the registry. The registry is consulted by resolution logic — filtered, ranked, proposed — never rendered as a browseable catalog UI. The open market enters as a driver repository the kernel searches, not a store the operator shops.
- **B2 — Provenance funnel at Walk.** Registry resolution proposes only verified / official-provenance servers by default (first-party platform-published, OAuth 2.1-capable, registry-attested). Community and unverified servers remain **operator-pasted only** — the Crawl-stage manual-binding posture persists permanently for the low-trust tier; it never graduates to auto-proposal. Attestation grade derives from provenance (open question #3 resolves inside this bias).
- **B3 — Foreign calls only from mechanical executors.** MCP tools are invoked inside deterministic mechanical-mode primitives (the `TrackUniverse` shape): one call site per watch, bounded, every fire in `execution_events`, every observation carrying `source_ref`. Foreign tools are **never injected into the Reviewer's judgment-mode tool surface.** This is the debugging containment: what makes open-MCP integration hell elsewhere is foreign tools inside LLM tool loops (unbounded interaction surface + injection risk + non-reproducible traces); our model structurally excludes it. Debugging an MCP watch = debugging one deterministic function with one foreign call — the same shape as debugging the Alpaca client today, with the observation contract as the receipt trail.

**Transport trust is a DERIVED tier, not a platform class (the ADR-076 receipt, reframed — ratified 2026-06-19 via [the derived-trust-tier amendment](ADR-335-AMENDMENT-derived-trust-tier.md)).** YARNNN has retreated from MCP-as-transport once: [ADR-076](ADR-076-eliminate-mcp-gateway.md) (2026-02-25) deleted the MCP Gateway — a local Node subprocess proxying 3 Slack REST calls — for operational reasons (subprocess lifecycle, extra service, extra language), and its Mitigated section left the door open verbatim: *"If a future platform has an MCP server that genuinely adds value beyond REST, we can evaluate then."* This D4 is the evaluate-then moment, and the protocol shape changed underneath (remote streamable-HTTP, OAuth 2.1, `.well-known` discovery, official registry) — the specific things ADR-076 retreated from no longer exist. **Discharged by receipt 2026-06-18:** the GitHub remote MCP server (`api.githubcopilot.com/mcp/`) accepted a standard GitHub OAuth Bearer token through YARNNN's own in-kernel client (`api/integrations/core/mcp_client.py`) — `initialize` + `tools/list` (44 tools) + `call_tool('get_me')` = HTTP 200, the D3 observation contract round-tripped. February's token-format rejection did not recur. (Notion/Slack remote servers also now speak OAuth-2.1 RFC-9728 discovery — the Feb gateway-killer included.)

The decision the reopen forces is **NOT** "which platforms are head vs tail." By §6 (transport-blindness) the transport cannot carry that distinction — nothing above the observation contract can see the device. The distinction is **derived** from what the read is *for*:

1. **A read's role is declared by flow-participation (ADR-332), not by its platform.** A read either is, or is not, referenced by a program's `substrate_abi.ground_truth` or a primary-action flow. That reference — already authored, already canon — *is* the role.
2. **The required transport trust-tier is a pure function of role**, computed at bind-time and fire-time, **stored nowhere** (DP7):
   ```
   required_tier(read, program) = HIGH  if read ∈ (program.ground_truth ∪ program.primary_actions)
                                  OPEN  otherwise
   ```
3. **A binding is permitted iff its attestation grade meets the tier.** Grade reuses the ADR-330 D2 enum (`platform > operator > agent`, gold→weaker). HIGH requires `platform`-grade (a first-party API, or a registry-attested official server the platform itself published); OPEN accepts any grade (community MCP, generic web/RSS, operator-pasted CSV). The B1/B2/B3 funnel above *is* the grade-assignment mechanism.

**The "head/tail" category is retired.** It was never a property of a platform — it was the output of `required_tier`. Consequences, now *derived* rather than asserted:
- **Alpaca stays Direct API — by derivation.** Alpaca ∈ alpha-trader's `ground_truth` ⇒ `required_tier = HIGH` ⇒ only a `platform`-grade binding is admitted; today the hand-authored Direct API client is the only `platform`-grade transport for it. Money-truth never flowing through a community server is a *theorem*, not a special case.
- **"MCP = tail" is gone.** A sufficiently-attested official MCP server (platform-published, OAuth 2.1, registry-verified) carries `platform` grade and may serve a HIGH-tier read. A community server carries a weaker grade and is admissible only for OPEN-tier reads. The protocol is never the gate; the grade is.
- **The same read can be HIGH for one program and OPEN for another, simultaneously** — `required_tier` is evaluated per (read, program). This is the case the per-platform framing could not express and the reason the distinction must be derived, not stored.
- **The hedge is unchanged and strengthened.** "MCP failure is a driver swap, not a redesign" still holds (§6); additionally a HIGH-tier read can swap *within* the tier (Direct API ↔ attested-MCP) without touching judgment, because the gate reads a grade, not a wire.

**Connection vs watch (Open Question A, resolved 2026-06-18).** A *watch* is a declaration in the aperture (ADR-343 §31); a *connection* is a transport below the declaration/transport boundary (ADR-343 §47). A watch *consumes* a connection (D5: declare-watch → resolve-transport); it is not *made of* one. They are not unifiable — opposite sides of the boundary §6/ADR-307/ADR-320 enforce — and unify only compositionally (shared derived-tier gate + shared aperture roof). The two binding shapes (`watch_id` NULL = capability binding; `watch_id` set = watch binding) coexist permanently and correctly. Full reasoning: [amendment §E.A](ADR-335-AMENDMENT-derived-trust-tier.md).

---

## 8. D5 — Watch-first, transport-second (the bright line)

The failure mode is "browse the marketplace and add interesting perception" — the connector-catalog disease wearing the new protocol. **A transport only ever enters because a declared watch needs it.** Watch-first, transport-second, always. The flow (foundation §4):

1. Operator (or program) **declares a watch** ("watch these competitors' changelogs").
2. The system **resolves a transport**: first against already-connected transports, then by searching the MCP registry (Walk).
3. Candidates surface as a **proposal**; the operator **authorizes the binding** — a trust grant, same governance shape as `platform_connections`.
4. The watch goes live: a recurrence reads through the transport, **distills observations into attributed substrate**, narrative-traced.
5. **Calibration eventually prunes** (D6): which watches earned their attention.

The declaration layer (judgment) is sovereign over the transport layer (commodity). This is the discipline that keeps the perception field a representation bet, not a mechanism bet.

**Transport-blind for judgment, transport-legible for governance (discourse-earned 2026-06-11).** Transport-blindness (§6) is a claim about *judgment-read-time*, not a claim that nobody manages the transport. The management loop has two distinct seats, neither of which requires judgment to know the device:

- **Watch lifecycle is Layer 1 — Reviewer-authorable.** Declaring, re-cadencing, retiring a watch is a judgment act on substrate, with direct precedent: ADR-274/275 already give the Reviewer trigger-authoring authority over its own cadence via `Schedule`. Watch-authoring is the same Identity-layer responsibility one slot over (the Run stage formalizes it).
- **Binding health is Layer 3 — surfaced as evidence, never introspected.** A dead token, a down server, a renamed channel all manifest as *failed or absent observations*. Absence is perceivable from the substrate's own record (`observed_at` timestamps in signal substrate — the calibration mirror already reads exactly this shape for recurrences); failures land in `execution_events` + narrative like every invocation failure. Repair: operator re-authorizes the binding (governance, the connectors surface) or re-declares the watch (judgment). No source-freshness table — reading the record is not maintaining a tracker.

**Three drift classes, three answers** (the "outside reality changes continuously" case): (a) *binding drift* (token/scope revoked) → failure event → operator re-grant; (b) *container drift* (the watched channel/page renamed or archived) → declaration no longer resolves → failed observation → re-declaration, a Layer-1 act; (c) *world drift* (containers appear that *should* be watched) → handled by declaring watches at the right **altitude** — "what containers exist" is itself a watchable, distillable fact (a meta-altitude watch), feeding substrate the Reviewer reads to propose new leaf watches. World drift is answered by declaration altitude, never by transport awareness.

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
| **Crawl** | **Crawl-A ✅ SHIPPED 2026-06-11**: `substrate_abi.watches` slot (D2) + observation contract (D3, convention) + FOUNDATIONS axiom-text (D8) + conformance gate (D9) + `get_watches_for_workspace` reader + `watch_declaration` in the Reviewer wake envelope. alpha-trader's `_universe.yaml` migrated to a kernel-declared watch. **Crawl-B (pending, demand-pulled)**: kernel MCP client (D4) with operator-pasted server configs (manual binding). | Operator authorizes each binding explicitly. | Crawl-B: bundle #3, first non-trader watch need, or alpha-author post-330 deepening (ADR-332 D5) |
| **Walk** | Registry search resolves declared watches into **proposed** bindings (the marketplace move, D7) + one generic cadenced web/RSS transport for connectionless workspaces + per-watch calibration read (D6). | Proposal → operator authorization; attestation grade from registry provenance. | a watch needs a transport the workspace hasn't connected |
| **Run** | The Reviewer notices a perception gap against the mandate and itself **proposes** a new watch + transport — perception management under the same propose/approve loop as capital actions. | Fully inside the existing judgment loop; delegation-level gated. | the Reviewer demonstrably needs perception it doesn't have |

**Crawl decomposes — representation before driver (discourse-earned 2026-06-11).** D2 + D3 (the watches slot + observation contract) do **not** depend on D4 (the MCP client). The first kernel-declared watch is the trader's `_universe.yaml` migration, which runs on the existing hand-authored `TrackUniverse()` Alpaca primitive — zero MCP involved. So Crawl ships in two independently-landable halves: **Crawl-A** (representation: D2 + D3 + D8 axiom-text + D9 conformance gate — closes the canon gap entirely) and **Crawl-B** (the MCP client, D4 — demand-pulled by the first watch needing a transport no hand-authored driver serves; note the first such demand may equally pull D7's generic web/RSS read forward instead, and whichever the real watch needs is the one that gets built).

**Empirical Crawl→Walk gate (discourse-earned 2026-06-11):** registry resolution (the marketplace move) does not ship on protocol optimism — Walk is gated on Crawl evidence: **N real watches running through the MCP client against real servers for real tenure** before registry-resolved bindings surface as proposals. Precedent: ADR-169's QueryKnowledge ranking pre-ship validation gate. N set at the Walk commit.

**The dependency ordering (foundation §8, ratified):** ADR-330/331 implementation (✅ landed) → **this ADR's Crawl stage** (Crawl-A then Crawl-B, per above) → the **program-assembly ADR** (route i — inference drafts the four flow declarations; ADR-332 §5 ledger) → Walk (registry resolution inside setup, gated empirically). Each arc makes the previous more valuable.

---

## 13. What this ADR explicitly does NOT do

- Does not build a connector catalog (transports are drivers from the ecosystem; one MCP client + one web/RSS read, never a catalog).
- Does not add a "perception manager," source-freshness table, or `_perception_tracker.md` (dual-tracking bright line; the substrate is the record).
- Does not revive continuous sync or raw mirroring (ADR-153 stands permanently).
- Does not let foreign-tool output into substrate raw (distilled, attributed observations only; consequential actions Reviewer-gated).
- Does not add a new attestation taxonomy (reuses ADR-330 D2's enum).
- Does not store a head/tail/type/scope/tier field anywhere (derived-trust-tier amendment, ratified 2026-06-19). Transport trust-tier is **derived** from flow-participation (ADR-332) at evaluation time; the only stored facts are the flow declarations (already authored) and the binding's `attestation_grade`. Storing a tier would be the dual-tracking DP7 forbids.
- Does not add workspace-level watch declarations (Direction A / ADR-332 D3 — watches are program-declared; route-i assembly declares them *as a program*).
- Does not implement attention *weighting* in calibration (label-first; weighting deferred, mirroring ADR-330 D2).
- Does not build the program-assembly route-i door (separate ADR, ADR-332 §5 ledger, after this).
- **Does not land any code, FOUNDATIONS edit, GLOSSARY entry, or conformance-gate change until ratified** (Stage-C fence).

---

## 14. Render-service parity (at Crawl implementation, post-ratification)

- The MCP client (D4) runs inside the **API** (same SDK family as the FastMCP server — verified `mcp 1.28.0`, `streamablehttp_client` + `ClientSession`) and the **Unified Scheduler** (recurrences read through it). Bindings reuse the `platform_connections` table + existing OAuth machinery. **The binding row gains two facts, no policy column** (derived-trust-tier amendment §C, ratified 2026-06-19): `attestation_grade` (the ADR-330 enum value, derived from registry/first-party provenance per B2 — existing connections backfill to `platform`/gold, a superset gate that regresses nothing) and `watch_id` (nullable — NULL = capability binding per ADR-207; set = watch binding per D5). **No tier/type/head-tail column** — required tier is derived. No new secret beyond the existing `INTEGRATION_ENCRYPTION_KEY`. **Foreign-call metering is a Crawl-B precondition** (amendment §E.B): an unmetered mechanical executor calling arbitrary OPEN-grade servers scales the cost surface with the openness D4 sells — the meter lands with the client, not after.
- The generic web/RSS read (D7) is a read tool on the API + Scheduler — no new service.
- **No env-var changes that aren't already present on API + Scheduler.** MCP-server (the existing yarnnn-mcp-server, context-out) is untouched — the client is a *different* surface. Output gateway untouched.
- *Confirm at implementation:* the MCP client's per-server consent + cost metering route through the existing budget gate (foundation §8).

---

## 15. Open questions

1. **Observation contract form** — **RESOLVED at ratification (2026-06-11): convention-first.** The observation contract is a substrate convention (the trader's `{TICKER}.yaml` / `_regime.yaml` shape proves it); a typed `Observation` TypedDict is promoted only on second-program demand.
2. **Watch calibration metric** — what exactly "earned its attention" measures for non-trading watches without a clean `by_signal` analog. (Walk-stage; the trader's expectancy is the template, generalization TBD.)
3. **Registry provenance → attestation grade mapping** — ~~official vs community vs unverified server → which enum value. (Walk-stage, D7.)~~ **RESOLVED 2026-06-19 (derived-trust-tier amendment §C): the mapping IS the grade the gate reads.** First-party / platform-published / registry-attested-official ⇒ `platform`. Operator-vouched (operator pasted the config, server reputable but not platform-published) ⇒ `operator`. Agent-discovered / unverified ⇒ `agent`. Identical to ADR-330 D2's outcome-attestation mapping — perception reuses it without a parallel taxonomy. HIGH admits only `platform`; OPEN admits all three.
4. **Webhook / push ingestion** — pull + wake-on-event (existing wake sources) first; push deferred (foundation §7).
5. **`N/A`-flow rationale schema** — **RESOLVED at the conformance-gate commit (2026-06-11): `substrate_abi.flows_na.{perception|work_out|outcomes|loop}: <rationale string>`.** Derivation-first: the gate reads each flow's canonical slot (watches / capabilities / ground_truth / judgment-mode recurrences) so nothing is declared twice; `flows_na` is the explicit escape hatch, and an N/A without rationale fails the gate (silence is not a declaration). First instance: alpha-author's `flows_na.perception`.
6. **Foreign-call cost metering for mechanical-mode watches** (added by the §3b audit) — mechanical external reads are unmetered today (Alpaca precedent); resolve when the MCP client lands (Crawl-B).
