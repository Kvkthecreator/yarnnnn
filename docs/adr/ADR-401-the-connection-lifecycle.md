# ADR-401 — The Connection Lifecycle: the peripheral as a first-class mechanical object

> **Status**: **Accepted** (2026-07-02) — ratified by the operator with the D2 clarification that the lifecycle is a **descriptive map (indicative), not an enforced state machine** — representative, amendable, never a code artifact. Implementation lands in the §8 phase sequence. Decides the connection's ontology (peripheral, not principal), canonizes its full nine-stage lifecycle with an owner per stage, takes ownership of the two previously unowned stages (disconnect/teardown, health-state semantics), resolves the ADR-392/ADR-394 retention-polarity contradiction, and adopts the derive attention-routing fix. Implementation lands in the §8 phase sequence after sign-off.
> **Date**: 2026-07-02
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the connections-first-class scoping session (2026-07-02). The bottom-up design ([connection-manager.md](../design/connection-manager.md), one drill-in screen) is reconciled against the top-down question — *what IS a connection, what is its full lifecycle, where does it live in the kernel model?* Every lifecycle claim below carries a file:line receipt from that session's substrate audit.
> **Builds on / ratified framing**: [ADR-335](ADR-335-perception-field.md) (transports are peripherals — driver-class, transport-blind judgment) + [ADR-378](ADR-378-the-workspace-as-the-outermost-unit.md) §3.4 (the connection/inflow split: "the *connection* is a driver/config…its *inflow* is work — holds (with a split)") + [ADR-392](ADR-392-the-connector-lane.md) (the four-phase connector lane) + [ADR-393](ADR-393-the-perception-capture-pipeline.md) (the mechanical capture lane) + [ADR-394](ADR-394-connector-capture-the-reader.md) (`CaptureConnector`, seed-at-select, derive-by-reference, GC wiring) + [ADR-338](ADR-338-management-plane.md) (DP28, the consent line) + [ADR-340](ADR-340-operator-experience-model.md) (DP29, mirror-once-compose-few).
> **Preserves**: [ADR-394 D3](ADR-394-connector-capture-the-reader.md) (derive is the seat's on-engagement judgment act — NOT a cadence; D5 here routes attention to it, it does not mechanize it), [ADR-288] (peripheral writes are `system:`-attributed — the mechanism, not a principal), [ADR-385](ADR-385-channels-the-perception-and-principal-surface.md)/[ADR-386](ADR-386-workspace-members-the-grant-lifecycle.md) (the two-roster separation on the Channels surface — `platform_connections` vs `principal_grants` — ratified here as correct, not accidental), [ADR-396](ADR-396-the-pricing-model.md) (retention as a tier gate — D4 makes the gate actually enforce).
> **Amends**: [ADR-392](ADR-392-the-connector-lane.md) D8 (its retention wording is self-contradictory — "raw is GC'd only after it has been derived-and-cited" vs "never GC a raw a derived act still needs"; D4 here fixes the polarity to ADR-394 D4's and the ADR-392 text gets a clarifying banner in the Phase-0 commit).
> **Defers**: platform-as-principal (ADR-378 §7: "the one implementation move that makes the intake model and the actor model consistent in code…Highest-leverage single change; not decided here") — named as a seam in D1, explicitly not taken.
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — the connection is a Where: a transport peripheral on the in-side, a destination on the out-side) + **Substrate** (Axiom 1 §8/§9 — what lifecycle state persists where, and the raw-lane retention contract) + **Trigger** (Axiom 4 — capture cadence, GC cadence, and the D5 wake route).

---

## 1. Why this ADR — connections are first-class, but their lifecycle has no owner

Connections (Slack/Notion/GitHub today) are now first-class to the service: they are the operation's perception intake and — on the out-side — its addressed-write destinations. The connector arc (ADR-392→394) built the lane; ADR-385 gave connections a surface; [connection-manager.md](../design/connection-manager.md) designed the per-connection Manage screen. But nothing owns the *object* end-to-end:

- **"Connection" is never a lifecycle-bearing noun in canon.** ADR-392 deliberately dissolved it into four phases ("no new primitive, no new class"); ADR-353 §15's "connection lifecycle" covers only discovery + mapping. The one full lifecycle that exists (ADR-386 ensure/narrow/evict) governs `principal_grants` — foreign LLMs, not platform connections.
- **Two stages have no canonical owner and are broken or orphaning in code** (§3): disconnect (deletes credentials, orphans `_watch.yaml` + the `_captures.yaml` entry + all `inbound/` raw) and health-state (a `status` column that is theatre — only ever written `'active'`).
- **Two ratified contracts are contradicted or inert in code** (§3): the retention GC's polarity is the *inverse* of ADR-394 D4's, and — because derive has never fired — the GC prunes nothing, the retention dial is a no-op, and the ADR-396 tier retention gate (7/30/90d) enforces nothing.

This ADR gives the connection its ontology (D1), its canonical lifecycle with an owner per stage (D2), and decisions for the broken stages (D3–D6). It changes no judgment-layer contract: the connection stays mechanical.

## 2. The ontology, resolved (D1)

### D1 — A connection is a first-class **mechanical peripheral**, not a principal

The operator's ratification, from first principles and consistent with existing canon:

1. **The connection is a transport/peripheral** — driver-class, intent-free, below the declaration/transport boundary (ADR-335 Layer 3; FOUNDATIONS Axiom 1 §8 "transports are peripherals"). It is a **non-actor**: it gets neither a home nor attribution (ADR-378 Law 2). On the out-side it is a Channel destination (Axiom 6). It is **not intelligence-layer**: it carries no judgment, holds no standing intent, and never becomes a persona.
2. **"First-class" means the peripheral itself is first-class** — a fully owned lifecycle (D2), an honest management surface (D7), and every stage either surfaced above the consent line, legibly mechanical below it, or explicitly deferred. First-class ≠ promoted into the principal model. Separation of concerns is the architecture: the mechanical perception machinery and the attributed judgment commons are different layers, and the connection lives wholly in the first.
3. **Attribution stays `system:*`.** Capture writes are authored by the mechanism (`system:capture-{platform}` / `system:sync-platform-state`, per ADR-288) — the peripheral is machinery, not a contributor. The **source-as-data** is carried where DP32 puts it: in the raw-lane path (`inbound/{platform}/{selector}/…`) and revision metadata, not in the author field.
4. **The DP32 gloss.** DP32's sentence "every transport is a principal writing a raw observation" is read as the *intake-shape* claim (one intake model; the source is data), not as a mandate to provision connector principals. The ledger move that would literalize it — `platform:slack` `authored_by` revisions + a provisioned `platform`-role grant — is **platform-as-principal**, which ADR-378 §7 names and defers, and which this ADR **explicitly does not take**. The seam is preserved: the `platform` role in `principal_grants` stays a name-only schema slot (migration `189_adr373_…​.sql:64`; zero write path — confirmed: the OAuth callback never calls `ensure_principal_grant`), the eviction branch that anticipates it (`principal_grants.py:337`) stays dormant, and the AI-Connections pane's `platform` filter stays empty. If platform-as-principal is ever taken, it slots into ADR-386's existing lifecycle without disturbing this ADR — that is what "naming the seam" buys.
5. **Consequently the two rosters are two concepts, correctly separate.** `platform_connections` (peripherals — what the operation *perceives through*) and `principal_grants` (principals — who may *write the commons*) co-habit the Channels surface by design (ADR-385 §2: "different facts about different objects"). This ADR ratifies that co-habitation as the intended architecture, not an accident awaiting unification.

## 3. Ground truth — the audited lifecycle (receipts)

The nine stages as they exist in code today (audit 2026-07-02):

| # | Stage | State | Receipts |
|---|-------|-------|----------|
| 1 | **Connect** (OAuth) | Surfaced, works | `routes/integrations.py:1381` (authorize), `:1423` (callback); `oauth.py:283`. `status` hardcoded `'active'` in every branch (`oauth.py:347,387,438,498`) |
| 2 | **Grant** (scopes) | Below-line fact, unsurfaced | Granted scopes stored `metadata.scope`, comma-joined (Slack `oauth.py:345`, GitHub `:436`; Notion stores none). Never mirrored anywhere; not in any response model |
| 3 | **Declare scope** (the aperture) | Surfaced, built | `connector_watch.py::write_selection`; seed-at-select capture entry `@every 15min` hardcoded (`connector_watch.py:181`); deselect-all → `paused` (`:284`). **Slack only** — Notion/GitHub have no capture binding (`:173`) |
| 4 | **Capture** | Below-line mechanical, works; freshness surfaced | `services/capture/`; `drain_due_captures` (`unified_scheduler.py:354`) gated on `AGENT_ENABLED` (`:331`); raw → `inbound/{platform}/{selector}/{observed_at}.md` attributed `system:*` (`lane.py:259`); health → `_capture_signal.yaml` keyed by capture slug (`declarations.py:293`) |
| 5 | **Derive** | **Broken in effect — never fired** | No code path derives `inbound/{platform}` → `operation/`; the only `derived_from`-citing pairing exists in test fixtures (`test_adr394_capture_connector.py:375`). The seat perceives only the one-line peripheral field (`freddie_envelope.py:800`); nothing routes its attention to accumulating raw |
| 6 | **Embed** | **Works** (prior "embeddings dead" claim corrected) | `_embed_workspace_file` has four live callers — post-wake sweep `wake.py:1110`, uploads `documents.py:117`, blob extraction `extract_text_from_blob.py:220`, the Embed primitive `embed.py:229`. `inbound/{platform}` is correctly embed-ineligible (`embed.py:53` — raw is reached by deterministic key, not ranked). The connector→recall chain is broken at the **derive** link, not embed: once derive writes `operation/` files, the existing wake sweep embeds them. **No embed work is needed** |
| 7 | **Retention / GC** | **Broken — polarity inverted, and inert** | `prune_raw_lane` prunes iff old **AND cited** (`connector_retention.py:231-234`) — the inverse of ADR-394 D4 ("a cited raw is **evidence** and is never pruned; only un-cited raw past the…window is dropped"). Since derive never fires, `cited_paths = ∅` → nothing is ever pruned → the retention dial (`RetentionDial.tsx`, `/integrations/retention`) and the ADR-396 tier gate (`retention_max_days_for_user`) are no-ops; `inbound/` grows unbounded |
| 8 | **Disconnect** | **No canonical owner; orphans state** | `integrations.py:742` deletes the `platform_connections` row (credentials go with it) but KEEPS `_watch.yaml`, the `capture-{platform}` entry in `_captures.yaml` (skips thereafter via the capability gate, `lane.py:132`), and all `inbound/` raw. ADR-386's revoke-as-eviction is foreign-llm only |
| 9 | **Health** | Probe honest; stored status is theatre | Real liveness only via `GET /integrations/{provider}/health?validate=true` (`validation.py:74` — Slack actually reads). The `status` column is only ever written `'active'`; `expired`/`revoked`/`error` (`types.py:24-29`) are dead enum values — no demotion path exists, no expiry column, no refresh routine; "Reconnect" = re-running authorize→callback (upsert `integrations.py:1457-1487`) |

## 4. The canonical lifecycle (D2)

### D2 — Nine stages, each with an owner and a consent-line class

The table in §3 becomes canon as the **connection lifecycle**. **Canon here means a descriptive map, not an enforced state machine** (operator ratification, 2026-07-02): there is no `ConnectionLifecycle` object, no stage enum, no sequencing constraint in code, and none is to be built — the stages are not even strictly sequential in reality (derive is on-engagement, health is continuous, retention is cyclic). What the map fixes is **ownership and consent-line placement** — every concern a connection raises has a named owner and a named side of the line, so no stage is ever unowned again. The stage set is representative and amendable: a new concern (e.g. a token-refresh stage, if token expiry becomes real) is added by amending this table, not by refactoring machinery. The only code this ADR schedules is the four targeted fixes (D3–D6); none introduces lifecycle enforcement.

Ownership and placement:

| Stage | Consent line (ADR-338 D3) | Canonical owner |
|---|---|---|
| Connect | **Above** (binding a driver is a consent moment) | ADR-392 D1 phase 1 (mechanism) · ADR-353 (creation/discovery) |
| Grant (scopes) | Above (the consent fact, read-back) | **This ADR** (surfacing contract → D7/Phase 1); the scopes themselves are OAuth's |
| Declare scope | **Above** (declaring the aperture) | ADR-392 D3/D7 + ADR-394 D2 (seed-at-select) |
| Capture | Below (mechanical enactment) | ADR-393 (lane) + ADR-394 D1 (primitive) |
| Derive | Below (the seat's judgment act) | ADR-376/ADR-394 D3; **attention route → this ADR D5** |
| Embed | Below (mechanical sweep post-derive) | ADR-325 + the wake sweep (`wake.py:1110`); nothing new |
| Retention / GC | Dial **above**; sweep below | ADR-392 D8 (dial) + ADR-394 D4 (wiring); **polarity → this ADR D4** |
| Disconnect | **Above** (changes what the operation may perceive) | **This ADR D3** (previously unowned) |
| Health | Derived read-back (D6) | **This ADR D6** (previously unowned) |

The one-line summary: **connect, scope, cadence, retention and disconnect are the operator's; capture, derive, embed and GC are the machine's; health is derived, never stored.**

## 5. The broken-stage decisions

### D3 — The disconnect teardown contract

Disconnect is a consent-line act (it changes what the operation may perceive) and gets a deterministic teardown:

1. **Delete** the `platform_connections` row (credentials) — unchanged.
2. **Remove** the connector's `capture-{platform}` entry from `_captures.yaml` (machine state; seed-at-select recreates it on reconnect+select). Today's behavior — a permanently skipping entry — is an orphan, not a pause.
3. **Keep** `operation/_connectors/{platform}/_watch.yaml` — it is the *operator's authored declaration* (consent substrate, `authored_by="operator"`). Reconnecting restores perception without re-declaring the aperture. An orphaned declaration with no connection is legible ("declared, not connected"), not drift.
4. **Keep** `inbound/{platform}/` raw — it ages out mechanically under D4 (un-cited raw past the window is pruned; cited raw is evidence and survives). No special-case deletion: the GC is the single raw-disposal path.

### D4 — Retention polarity: fix code to ADR-394 D4; the noise framing is the rationale

The code's polarity (`prune iff cited`) is **wrong**, twice over: it deletes exactly the raw that a `derived_from` chain still points at (breaking `trace`, the moat's distinguishing capability) and keeps forever exactly the raw nobody engaged. Under the operator's ratified framing — **connector raw is mostly noise** (a busy Slack channel is largely un-context chatter) — the correct GC is:

- **Prune**: un-cited raw older than `retention_days` (noise, presumed un-engaged — ages out mechanically at the dial's window).
- **Never prune**: cited raw (a judgment engaged it; it is evidence in a provenance chain, immortal).

This matches ADR-394 D4 verbatim and makes the retention dial and the ADR-396 tier gate (7/30/90d) *actually enforce*. The fail-safe stays: `cited_paths=None` (unknown) prunes nothing. ADR-392 D8's self-contradictory sentence ("raw is GC'd only after it has been derived-and-cited") is amended to this polarity in the Phase-0 commit. The `test_adr392`/`test_adr394` gates flip with the code.

### D5 — Derive attention-routing: the wake-path fix

Derive stays exactly what ADR-394 D3 ratified — the seat's derive-and-cite judgment act, on engagement, never a cadence, never a mechanical summarizer. What is missing is not a derive step but **attention routing**: nothing tells the seat that raw is accumulating, so the act never has an occasion. The fix stays inside ADR-296 wake canon:

- **Inbound accumulation becomes a wake occasion** — via the existing substrate-event hook mechanism (`_hooks.yaml`, walked by the scheduler against recent `workspace_file_versions`) or an equivalent threshold-shaped wake proposal from the capture lane (N new un-derived raw files / M hours since last engagement → one `substrate_event` proposal into the funnel). The funnel still decides; pace still caps; the seat still exercises judgment on arrival — including the judgment *not* to derive noise.
- The exact mechanism (declared hook vs lane-emitted proposal) is resolved at Phase-3 implementation against `wake_sources/substrate_event.py`; the contract decided *here* is: **capture volume must be able to reach the funnel; derive must never run outside judgment.**
- ~~**Mechanism RESOLVED (Phase 3, 2026-07-03): the lane-emitted proposal**, mirroring the existing MCP `remember` adapter (`mcp_composition`'s wake seam — the same derive-and-cite route MCP raw already had and connector raw lacked). A declared glob-hook was rejected because the walker fires one proposal per matching *revision* (a 40-channel capture run would flood the funnel with 40 proposals) and a path-only hook is not expressible (`_field_change_matches` requires a frontmatter transition). The capture lane's `_propose_derive_wake` (`services/capture/lane.py`) submits ONE `substrate_event` proposal per capture run that wrote ≥1 new file — the run is the natural batch; the dedup key is the run stamp (`{slug}:{observed_at}`); diff-aware capture means an unchanged world proposes nothing. The adapter is the lane's single wake-contract site, best-effort, and a proposal failure never fails the capture.~~
- **AMENDED — the lane-emitted proposal is RETIRED (2026-07-03, operator decision, after one production night).** The adapter's premise ("an unchanged world proposes nothing") failed immediately in production: the diff baseline called a phantom `UserMemory.list()` that never existed on the real class (the AttributeError was swallowed fail-open; the test fake modeled the missing method — mock drift), so *every* 15-min capture rewrote byte-identical raw (md5 receipt `46f3105a…`) and fired a ~$0.60 judgment wake — **~$60/day per connector on an unchanged world** — plus per-wake re-proposal spam (22 duplicate pending `EditFile standing_intent` in 3 h). The operator's ruling generalizes past the bug: **capture accumulation must have ZERO correlation with wake / LLM-invocation count** — even a correctly-suppressed adapter ties judgment spend to connector chatter rather than to declared cadence, inverting the ADR-327 budget posture and ADR-393 D1's own invariant ("a capture wakes no one"). The adapter is deleted, not gated. The phantom `list()` is fixed regardless (real `UserMemory.list` + loud fail-open in `_latest_snapshot_content`) so identical raw stops duplicating. Receipts: `docs/evaluations/2026-07-03-rung4-model-stabilization-FINDING.md` §production flags.
- **The standing attention route (post-amendment)**: the seat perceives accumulated un-derived inbound at its **own** wake cadence — the envelope's peripheral field (`freddie_envelope._peripheral_field_fact`) carries per-capture freshness at every wake, and a workspace that wants inbound engaged on a rhythm declares a recurrence for it (Freddie-authored per ADR-275 D1, or operator-asked), governed by `_budget.yaml`/pace like any other judgment work. Wake count is set by declared cadence + operator address, never by capture volume. The one-night production run proved the derive act itself (approvals produced real derived files under `operation/yarnnn-product/`); the occasion no longer needs manufacturing per capture run.
- Embed follows for free: derived `operation/` files are swept by `wake.py:1110`. The yield/recall chain (capture → derive → embed → recall) is unchanged; only derive's *trigger* moved from capture-volume to declared-cadence.

### D6 — Health honesty: derived, never stored

Health follows the DP29/DP28 derivation discipline (attention-routing is derived, never stored):

- **UI health = the validate probe** (`?validate=true`, on demand) **+ the capture signal** (`_capture_signal.yaml` freshness/`last_error`). Both are real observations.
- The stored `status` column is a **connect-time fact** (credentials present), nothing more. No code presents it as liveness. The dead enum values (`expired`/`revoked`/`error`) are documented as unused; removal is optional cleanup, not required.
- **No token-expiry sweep is built now** — Slack bot tokens don't expire; building the display without the detection is fabrication (connection-manager.md §5 discipline). If token expiry becomes a real failure mode (GitHub/Reddit), a health sweep that writes real `status` transitions is the deferred backend workstream, and the ACCESS section absorbs it then.

## 6. Surface placement (D7)

### D7 — The Connections pane is the mirror; the Manage drill-in is the lifecycle's UI

- Under DP29 the Connections pane is the **mirror** of `platform_connections` (one surface ↔ one substrate concern). There is no "Connect" act in the standing loop (ADR-340 D3), so no new composition is created — connections are managed from the Channels surface (ADR-385) as today.
- The per-connection Manage drill-in adopts the **4-section design of [connection-manager.md](../design/connection-manager.md) unchanged** — ACCESS · SCOPE · CADENCE · YIELD, consent-line ordered. That document is this ADR's Phase-1 UI spec; its grain decision (connector = unit of perception, channels = the aperture; per-channel health deliberately unmodeled) and its no-fabrication discipline are ratified as-is.
- The AI-Connections pane (principals) is untouched — the D1(5) two-roster separation.

## 7. Cross-compare: what the bottom-up design got right, and where it was too narrow

**Survives intact** (ratified by this ADR): the connector-grain decision; the 4-section Manage UI; the no-fake-token-health discipline; build-order items 1–4 (they become Phase 1/2/4 below).

**Too narrow** (what the macro frame adds): the design treated the derive gap as a UI explainer ("retained now, understood when the agent engages") — true copy, but the stage itself was broken with no occasion for engagement (D5); it did not touch disconnect orphaning (D3), the retention polarity/inertness (D4), or the peripheral-vs-principal seam (D1). None of that is a fault of the document — it was scoped to one screen against current substrate; this ADR is the altitude it lacked.

**Corrected en route**: the working memory's "embeddings dead (`_embed_workspace_file` no write-path caller, 642/642 NULL)" claim is stale — four live callers exist (§3 stage 6); the chain is broken at derive, not embed.

## 8. Phased implementation plan (each phase independently shippable, after sign-off)

| Phase | Scope | Notes |
|---|---|---|
| **0 — Retention polarity fix** (bug-grade) | Flip the cited-check in `prune_raw_lane` (`connector_retention.py:231-234`) to prune-uncited-past-window / keep-cited; flip the `test_adr392`/`test_adr394` gate assertions; amend ADR-392 D8 wording; verify the tier clamp (`retention_max_days_for_user`) end-to-end | Makes the dial + ADR-396 gate real. Ships independent of everything else |
| **1 — Manage drill-in 4-section UI** | connection-manager.md build order 1–3: ACCESS (surface `metadata.scope`, validate-probe button, Reconnect link) · CADENCE display (honest paused/`AGENT_ENABLED` states) · YIELD (Files deep-link to `inbound/{platform}/` + derive-truth explainer) | Pure legibility, no lane changes |
| **2 — Disconnect teardown + derived health** | D3 (remove capture entry on disconnect; keep `_watch.yaml` + raw) + D6 (pane health = probe + capture signal; no stored-status theatre) | Closes the unowned stages |
| **3 — Derive attention-routing** (the value unlock) | D5: inbound-accumulation wake route; **Hat-B eval** proving the seat derives-and-cites live connector raw when woken; recall over connector content becomes real via the existing embed sweep | Can be pulled ahead of 1–2 if recall value is the priority |
| **4 — Breadth** | CADENCE edit (small enum, pace-gated per ADR-298) + Notion/GitHub capture bindings (`CONNECTOR_CAPTURE_BINDINGS`) | Completes the connector surface |

**Deferred, named**: platform-as-principal (D1(4) — the seam); per-channel health (connection-manager.md §2 — a consumer-less second grain); token-expiry sweep (D6).

**Verification**: Phase 0 — gates green post-flip + a live `prune_raw_lane(dry_run=True)` reporting `pruned>0` with cited kept. Phase 3 — eval under `docs/evaluations/`: wake with fresh inbound raw present → assert a derived `operation/` file whose `derived_from` cites the raw → assert `recall` *finds* the derived content (not merely "returns a bundle").
