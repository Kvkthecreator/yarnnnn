# ADR-389 — Principal vs Peripheral, and the steward-shaped wake envelope

> **Status**: **Accepted + Implemented** (2026-06-30). Doc + code landed same session (gate `api/test_perception_envelope.py` 27/27; siblings `test_attribution_fact` 16/16, `test_reviewer_context_contract` 16/16, `test_adr276_reactive_envelope` 9/9 all green). **Substrate/Identity dimension** (Axiom 1 §8 + Axiom 2) — it adds two *perception facts* to the steward's wake envelope (DP19-clean read-and-present); it changes no substrate paths, no write gate, no schema, no primitive surface.
> **Date**: 2026-06-30
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the operator's read of the attribution-fact confirmation FAIL ([2026-06-30-attribution-fact-confirmation-FINDING.md](../evaluations/2026-06-30-attribution-fact-confirmation-FINDING.md)) — *"check if [Freddie's] overall prompt envelope accommodates the full perception scope: connection, sources, external agents… most likely the envelope + primitives need revisiting from first principles because the current setup still assumes the prior pre-Freddie reviewer posture… and I'm not sure how Sources/Connections are fundamentally different from an MCP-AI writing documents into the substrate. If that nuance needs its own scoping, now is the time."*
> **Builds on**: [ADR-381](ADR-381-freddie-the-rung-1-substrate-steward.md) (Freddie = the Rung-1 substrate steward whose duties include keeping attributions + connections coherent) + [ADR-383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) (the steward self-model that names those duties) + [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (the `principal_grants` roster this ADR makes the steward perceive) + [ADR-335](ADR-335-perception-field.md) (peripherals as driver-class transports — the half this ADR contrasts with principals) + [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (the ledger-intake floor where all three transports converge) + [ADR-387](ADR-387-agent-governance-on-the-agent-pane.md) follow-on (the attribution fact this ADR gives a referent) + [ADR-364](ADR-364-reflection-loop.md) (the reflection gap-fact, the DP19 read-and-present shape both new facts copy).
> **Analysis base**: [docs/analysis/perception-and-the-principal-commons-first-principles-2026-06-30.md](../analysis/perception-and-the-principal-commons-first-principles-2026-06-30.md) (the first-principles pass; this ADR ratifies its taxonomy and ships the envelope it scoped).
> **Preserves**: DP19 (kernel presents, the agent's rule judges — both new facts are read-and-present, no labeling); the write gate (ADR-307/320/366 — unchanged; this is perception, not authorization); Singular Implementation (the roster logic is shared between this envelope and the Workspace Members route via `services/principals.py`); the bundle/kernel boundary (the facts are kernel-universal perception, program-neutral).
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 §8 — what the steward perceives) + **Identity** (Axiom 2 — the steward's perception of the commons it tends).

---

## 1. The problem

The attribution-fact arc (ADR-387 follow-on) added one perception slice to Freddie's wake envelope — recent revisions + their `authored_by` — to close the bare-Freddie eval's attribution miss. Across three confirmation wakes the fact *fired* (Freddie investigated attribution where it never had) but **never closed the catch**: it kept accepting `authored_by: operator` on overtly AI-voiced content. The [confirmation FINDING](../evaluations/2026-06-30-attribution-fact-confirmation-FINDING.md) diagnosed a rule-trigger gap. The operator's read went deeper: **the envelope carries one slice of the perception field, not the field.** The persona-frame (ADR-383) names the steward's duties — "keeping the files, context, **attributions, intake, and connections** coherent" — but the envelope surfaces substrate for only *attribution*. Connections-health, Sources-health, and **the principal roster** (who is even authorized to write into the commons) are absent. The [perception-envelope-completeness FINDING](../evaluations/2026-06-30-perception-envelope-completeness-FINDING.md) confirmed it with receipts.

The deepest miss: **the attribution check has no referent.** `authored_by: operator` is a bare string. To judge "is this stamp honest?" the steward must know *who the workspace's principals are* — that the `operator` principal is a specific human whose voice differs from an AI's. The envelope never told it.

## 2. The decision — name the taxonomy, then ship the steward-shaped envelope

### D1 — Principal vs Peripheral (the conceptual cut)

The three "Channels" the operator sees (Connections, Sources, External Agents) **converge at the ledger floor** — all are ADR-376 context-in transports that *retain + attribute + cite* into `inbound/{transport}/`. The operator's instinct that they're "not fundamentally different" is correct *there*. They **diverge at the principal layer**:

- **A PRINCIPAL** is an intent-bearing, grant-backed identity that attributes *as itself*: the owner, members, own-agents, foreign LLMs (MCP), A2A callers — the rows of `principal_grants` (ADR-373). It reasons; it can be honest, careless, or adversarial about *who it is*. The steward judges its **HONESTY** (does the stamp match the content + the roster?). This needs a **roster**.
- **A PERIPHERAL** is a driver-class transport with no intent: a web/RSS feed (ADR-335/336, `system:track-web-sources`), a platform API (ADR-264 `SyncPlatformState`, `system:sync-platform-state`). It has no "who" to lie — its `system:` attribution is honest by construction. The steward judges its **HEALTH** (is it live? current?). This needs a **status surface**.

This is the scoping the operator asked whether we need. It is half-canonized already (ADR-335 "peripherals, driver-class" + ADR-373 principals); D1 names them as **one taxonomy** so the steward's two perception duties (honesty over principals, health over peripherals) are distinct by construction. A connection or source is **never** an attribution-integrity violation; only a principal can mis-attribute.

### D2 — The principal-commons fact (the missing referent)

The envelope gains `principal_commons_fact`: the roster (each active `principal_grants` row — principal · role · write-regions) + recent authorship GROUP-BY (per `authored_by`, revisions in the window). It renders **before** the attribution fact and names the owner as *"the human operator (writes as `operator`)"* and each foreign LLM as *"… (foreign LLM, writes as `yarnnn:mcp:…`)"* — so the attribution check has a concrete referent. The attribution-fact header now routes the check *through* the roster ("check each stamp against the principal commons above"). Forward-compatible with the re-founding (provenance-as-metadata): the recent-authorship half *is* a `GROUP BY principal` over the ledger.

### D3 — The peripheral-field fact (the connection-hygiene substrate)

The envelope gains `peripheral_field_fact`: connection health (`platform_connections`: platform · status) + declared-source count (ADR-335 watches). It gives the persona-frame's `connection-hygiene` duty perceptible state, framed as health-not-honesty.

### D4 — Singular roster home

The class-default-write-region + roster logic moves from `routes/workspace.py` into `services/principals.py`, so the steward envelope and the Workspace Members route read the **same** roster (a service shared by both, not a route helper copied into a service).

### D5 — DP19 preserved; refold, don't bolt-on

Both facts are read-and-present (kernel presents, the steward's `attribution-integrity`/`connection-hygiene` rules judge). The attribution fact is **refolded** as the per-path detail layer *within* the principal-commons view, not a fifth standalone bolt-on — the steward reads roster → recent authorship → per-path attribution as one coherent commons view. This is the steward-shaped-envelope direction (perceive the workspace as a commons-with-a-perimeter), not another one-fact-per-eval accretion.

## 3. What this is NOT

- **Not a new write gate.** Perception only. Who-may-write is unchanged (ADR-307/320/366); the steward now *sees* the grant scopes it always ran under.
- **Not making Connections/Sources principals.** The opposite — D1 fixes them as peripherals, correctly `system:`-attributed.
- **Not the rule-trigger lever.** The confirmation FINDING named a sharper `attribution-integrity` trigger as the next lever. This ADR ships the *referent* the rule needs first (the more first-principles fix). Whether the roster alone closes the catch is the validation wake (§5); if it still misses, the rule-trigger lever follows, now with the roster ruled in.
- **Not the full re-architecture.** This is the steward-shaped envelope's first coherent pass (principal commons + peripheral field + refolded attribution). Deeper unification (e.g. a single "what needs tending" fact) and re-founding coordination remain open.

## 4. Implementation (landed this session)

- `api/services/principals.py` (new) — `load_principal_roster` + `class_default_write_regions` (relocated from the route, D4).
- `api/services/freddie_envelope.py` — `_principal_commons_fact`, `_peripheral_field_fact`; both wired into `load_freddie_governance_envelope`.
- `api/agents/occupant_contract.py` — `FreddieContext` gains `principal_commons_fact` + `peripheral_field_fact`.
- `api/agents/freddie_agent.py::_build_user_message` — render blocks for both facts; attribution-fact header routes the check through the roster.
- `api/routes/workspace.py` — imports the shared helper (D4).
- Gate: `api/test_perception_envelope.py` (27/27).

## 5. Validation (done — FAIL on the catch, roster ruled IN-but-insufficient)

Fired the bare-steward wake (2026-06-30, $0.087, [validation FINDING](../evaluations/2026-06-30-principal-commons-validation-FINDING.md)). The principal commons rendered correctly (owner named "the human operator (writes as `operator`)" + the foreign-LLM principal) — the referent the attribution check lacked is now present. **But the steward still did not catch the mis-attribution.** It read the file, placed the honest dump well, and took zero action on the `authored_by=operator` lie (one improvement: it stopped *propagating* the false stamp, which the prior run did).

This is the **FAIL branch**, reached cleanly. The arc has now eliminated every perception hypothesis (presence → salience → referent), and none closed the catch. **The roster is ruled IN — built, correct, necessary, but insufficient on its own.** The confirmed remaining gap is the **rule trigger**: the steward does not RUN the `attribution-integrity` check unprompted even with the referent in hand. The next lever (§6) is now singular and unambiguous: sharpen the `attribution-integrity` trigger in the steward-default `persona/principles.md` to an imperative per-file voice-vs-stamp-vs-roster check. Probe before building it (re-fire this same wake). This ADR's build is not wasted — the principal commons is the referent the eventual catch needs, and serves connection-hygiene + multi-principal reasoning + the re-founding's provenance projection independent of this one catch.

## 6. Open follow-ons (deferred, NOT in this ADR)

- The rule-trigger sharpening (only if §5 still misses).
- The "what needs tending" unification (intake + revisions + commons as one fact).
- Re-founding coordination (provenance-as-metadata makes the principal commons a ledger projection — when that lands, re-source the recent-authorship half from revision metadata rather than a parallel query).
- Surface naming: the Channels panes could honor principal-vs-peripheral (External Agents = principal; Connections/Sources = peripheral) — cosmetic, deferred.
