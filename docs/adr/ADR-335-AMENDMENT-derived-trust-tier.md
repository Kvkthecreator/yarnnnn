# ADR-335 AMENDMENT (draft) — Retire the head/tail category; transport trust is a derived tier, not a platform class

**Date:** 2026-06-18
**Status:** **Draft amendment — awaiting operator ratification.** Does not land in ADR-335 or FOUNDATIONS until ratified (the ADR-335 Stage-C fence still applies to Crawl-B; this amendment is a *framing correction* to the ratified Crawl-A canon, scoped to the not-yet-built D4 client).
**Hat:** A (System Editor) — this edits canon. Authored from the Hat-B finding [`2026-06-18-head-tail-split-consequence-radius-FINDING.md`](../evaluations/2026-06-18-head-tail-split-consequence-radius-FINDING.md) (Discipline rule 5: an evaluation that contradicts an ADR's claim is followed by an amendment).
**Amends:** ADR-335 §7 (D4 head/tail split) + §13/§14 (binding storage) + §15 (open question #3) + a new §7b (existing connections).
**Does NOT change:** the Crawl-A implementation already shipped (D2 watches slot, D3 observation contract, D8 axiom-text, D9 conformance gate). Those are untouched. This amends only the *not-yet-built* D4 client's framing + storage model.

---

## Why this amendment exists (one paragraph)

ADR-335 §7 framed the MCP-client decision as **head platforms (Direct API) vs tail platforms (MCP)**. Interrogation against first principles (FOUNDATIONS Axiom 1 / DP7 no-dual-tracking; ADR-335 §6 transport-blindness; ADR-332 programs-are-flows) shows that framing is mis-leveled: it makes a *transport* class carry a distinction that, by transport-blindness, the transport cannot carry — and it has no coherent home for the case where the **same read is constitutive for one program and ambient for another**. The architecturally-stable model **retires the head/tail category entirely** and replaces it with a *derived* trust-tier: a read's role is already declared by its participation in a program's four flows (ADR-332); the required transport trust-tier is a pure function of that role; a binding is permitted iff its attestation grade meets the tier. "Direct API" and "MCP" become two transports each carrying a grade — the gate reads the grade, not the protocol. This is strictly stronger: every guarantee §7 asserted (Alpaca stays Direct API; money-truth never via a community server; the B1/B2/B3 funnel) is *preserved by derivation* rather than special-cased.

---

## A. The model (normative)

Three levels, two declared, one derived-never-stored:

| Level | What | Where it lives | Mutability |
|---|---|---|---|
| **Role** | what the read is *for* (feeds ground-truth / an action / only context) | the program's four-flow declarations (ADR-332) — **already authored** | declared by operator/program |
| **Required tier** | how much trust the transport must carry | **nowhere — computed** | pure function of Role |
| **Binding** | the transport + its trust grade | `platform_connections` (the binding row) | authorized by operator |

**The function:**
```
required_tier(read, program) =
    HIGH   if read ∈ (program.substrate_abi.ground_truth ∪ program.primary_actions)
    OPEN   otherwise
```

**The gate** (replaces the `platform`-enum match at `api/services/orchestration.py:1363-1364`):
```
binding permitted for (read, program)  ⇔  attestation_grade(binding) ≥ required_tier(read, program)
```
where the trust order reuses the **existing ADR-330 D2 attestation enum verbatim** (`api/services/outcomes/base.py:59-67`):
```
platform  >  operator  >  agent          (gold → weaker)
HIGH tier requires grade == platform
OPEN tier accepts any grade
```

**No head/tail/type/scope/tier field is ever stored.** Severity is *which* flow the read feeds; scope is *how many* flows/programs reference it — both are queries over the flow graph, not authored facts. Storing them would be the dual-tracking DP7 forbids (the `sync_registry` / `_perception_tracker.md` disease §13 already refuses).

---

## B. Replacement text for §7 (D4)

> **Replace the two "head/tail split" consequences (current §7, the passage beginning "The head/tail split + the ADR-076 receipt") with:**

**Transport trust is a derived tier, not a platform class (the ADR-076 receipt, reframed).** YARNNN retreated from MCP-as-transport once — [ADR-076](ADR-076-eliminate-mcp-gateway.md) deleted the MCP Gateway for operational reasons, leaving the door open: *"If a future platform has an MCP server that genuinely adds value beyond REST, we can evaluate then."* This is the evaluate-then moment, and the protocol shape changed underneath (remote streamable-HTTP, OAuth 2.1, `.well-known`, official registry). But the decision the reopen forces is **not** "which platforms are head vs tail." By §6 (transport-blindness), the transport cannot carry that distinction — nothing above the observation contract can see the device. The distinction is therefore not a property of the transport at all. It is **derived** from what the read is *for*:

1. **A read's role is declared by flow-participation (ADR-332), not by its platform.** A read either is, or is not, referenced by a program's `substrate_abi.ground_truth` or a primary-action flow. That reference — already authored, already canon — *is* the role.
2. **The required transport trust-tier is a pure function of role.** `required_tier = HIGH` for reads that feed ground-truth or a primary action; `OPEN` otherwise. Computed at bind-time and fire-time; **stored nowhere** (DP7).
3. **A binding is permitted iff its attestation grade meets the tier.** Grade uses the ADR-330 D2 enum (`platform > operator > agent`). HIGH requires `platform`-grade (a first-party API, or a registry-attested official server published by the platform itself); OPEN accepts any grade (community MCP, generic web/RSS, operator-pasted CSV).

**Consequences, now derived rather than asserted:**

- **Alpaca stays Direct API — by derivation.** Alpaca ∈ alpha-trader's `ground_truth` ⇒ `required_tier = HIGH` ⇒ only a `platform`-grade binding is admitted; today the hand-authored Direct API client is the only `platform`-grade transport for it. Money-truth never flowing through a community server is now a *theorem*, not a special case.
- **"MCP = tail" is gone.** A sufficiently-attested official MCP server (platform-published, OAuth 2.1, registry-verified) carries `platform` grade and may serve a HIGH-tier read. A community server carries a weaker grade and is admissible only for OPEN-tier reads. The protocol is never the gate; the grade is.
- **The same read can be HIGH for one program and OPEN for another, simultaneously** — because `required_tier` is evaluated per (read, program) against that program's flows. This is the case the per-platform framing could not express and is the reason the distinction must be derived, not stored.
- **The hedge is unchanged and strengthened.** "MCP failure is a driver swap, not a redesign" still holds (§6); additionally, a HIGH-tier read can swap *within* the tier (Direct API ↔ attested-MCP) without touching judgment, because the gate reads a grade, not a wire.

**The B1/B2/B3 transport-trust funnel (unchanged) governs the OPEN tier and the grade assignment:** B2's provenance funnel is precisely *how a binding earns `platform` vs weaker grade* — first-party/official/registry-attested ⇒ `platform`; community/unverified ⇒ weaker, operator-pasted only. The funnel was always the grade-assignment mechanism; this amendment names what it assigns *to*.

---

## C. Replacement text for §13/§14 (binding storage)

> **§13 "What this ADR does NOT do" — replace the bullet:**
> ~~Does not add a new attestation taxonomy (reuses ADR-330 D2's enum).~~
> **Keep**, and **add:**
> - Does not store a head/tail/type/scope/tier field anywhere. Transport trust-tier is **derived** from flow-participation (ADR-332) at evaluation time; the only stored facts are the flow declarations (already authored) and the binding's attestation grade. Storing a tier would be the dual-tracking DP7 forbids.

> **§14 "Render-service parity" — replace the binding-storage sentence:**
> ~~Bindings reuse the `platform_connections` table + existing OAuth machinery — **no new storage, no new secret** beyond per-binding encrypted tokens.~~
> **With:**
> Bindings reuse the `platform_connections` table + existing OAuth machinery. **The binding row gains two facts, no policy column:** `attestation_grade` (the ADR-330 enum value, derived from registry/first-party provenance per B2) and `watch_id` (which declared watch this binding serves). **No tier/type/head-tail column** — the required tier is derived from flow-participation at evaluation time. Storage decision (typed columns vs. `metadata` JSONB) resolved in the Crawl-B implementation commit; the *shape* is fixed here (two facts on the binding; tier derived). No new secret beyond the existing `INTEGRATION_ENCRYPTION_KEY`.

> **§15 Open question #3 — RESOLVE:**
> 3. ~~Registry provenance → attestation grade mapping — official vs community vs unverified server → which enum value. (Walk-stage, D7.)~~
> **RESOLVED (this amendment): the mapping IS the grade the gate reads.** First-party / platform-published / registry-attested-official ⇒ `platform`. Operator-vouched (operator pasted the config and the server is reputable but not platform-published) ⇒ `operator`. Agent-discovered / unverified ⇒ `agent`. This is identical to the ADR-330 D2 outcome-attestation mapping (external-API = `platform` gold; operator-import = `operator`; agent-asserted = `agent`); perception reuses it without a parallel taxonomy. The HIGH tier admits only `platform`; OPEN admits all three.

---

## §7b — Existing platform connections (NEW — the further-consideration the finding underplayed)

The model must account for the connections that exist **today** — Slack, Notion, GitHub, plus program-scoped Alpaca (trading) and Lemon Squeezy (commerce) — because they are live, gate real capabilities, and have neither `attestation_grade` nor `watch_id`. There are five questions; each resolves *by derivation*, which is itself evidence the model is right.

### 1. What grade do existing connections get?

**`platform` (gold), automatically, with zero per-row authoring.** Every existing connection is a first-party Direct API integration against the platform's own API with the operator's own OAuth token — that is the *definition* of `attestation = platform` in ADR-330 D2 (`base.py:59`: "external API independent of operator AND agent"). The migration is a **backfill default**, not a decision: `attestation_grade = 'platform'` for every existing `platform_connections` row. No row needs inspection.

### 2. Do existing connections break under the new gate?

**No — they pass strictly more often than before, never less.** Today's gate is `platform == req.platform AND status == active`. The new gate is `attestation_grade ≥ required_tier`. Since every existing connection backfills to `platform` (the max grade), it satisfies **both** HIGH and OPEN tiers — i.e. every read it serves is admissible regardless of role. The set of admitted (read, connection) pairs under the new gate is a **superset** of today's. **No capability that fires today stops firing.** This is the property that makes the migration safe: the reframe cannot regress an existing connection, by construction.

### 3. What happens to the `platform` enum string / capability names (`read_slack`, etc.)?

**Unchanged — and this is deliberate.** The existing capabilities (`read_slack`, `read_notion`, `read_github`, program-scoped `read_trading`/`read_commerce`) remain exactly as declared in `CAPABILITIES` / `PLATFORM_TOOLS_BY_CAPABILITY`. The amendment does **not** dissolve hand-authored Direct API drivers — it reframes *why* they're trusted (they're `platform`-grade), not *whether* they exist. The `platform`-enum match at `orchestration.py:1363` is **generalized, not deleted**: the existing capability check becomes one path (a named first-party driver is a `platform`-grade binding); the MCP path is the *second* path through the *same* derived gate. **Singular implementation:** one gate (`grade ≥ required_tier`), two transport families feeding it, not two parallel gating systems. The legacy `platform_connection_requirement` dict becomes a thin adapter that resolves a first-party connection to a `platform`-grade binding — or is absorbed entirely when the gate reads grade directly. (Which of the two — adapter vs. absorption — is a Crawl-B implementation call; the *direction* is absorption, per Singular Implementation.)

### 4. Does an existing connection need a `watch_id`?

**No, and this exposes a real asymmetry worth stating.** Existing connections are **capability bindings** (ADR-205/207: a connection makes a capability *available*; recurrences declare `required_capabilities`). MCP bindings under D5 are **watch bindings** (watch-first: a transport enters *because a declared watch needs it*). These are two binding shapes:
   - **Capability binding** — `(user_id, platform, grade=platform)`, no `watch_id`; serves any recurrence declaring the matching capability. The pre-existing model.
   - **Watch binding** — `(user_id, server/url, grade, watch_id)`; serves exactly the watch it was authorized for. The D5 model.

`watch_id` is therefore **nullable** on the binding row: NULL = capability binding (legacy + first-party), set = watch binding (MCP/tail). This is not a wart — it reflects that YARNNN has **two legitimate ways a transport enters**: *operator connects a platform → capabilities unlock* (ADR-207, broad) and *operator/program declares a watch → transport resolves* (ADR-335 D5, narrow). The derived-tier gate is identical for both; only the binding's *scope of service* differs (any-matching-capability vs. one-watch).

> **Consideration flagged for the operator:** this means the existing `platform_connections` rows are *not* migrated into the watch-first discipline — they stay capability-broad. That is correct for now (don't churn working connections into watch declarations), but it means **two binding shapes coexist permanently** unless a future ADR unifies "connecting a platform" into "declaring a watch over that platform." That unification is *plausible* (it would make ADR-207's capability-unlock a special case of ADR-335's watch-declaration) but is **explicitly out of scope here** — naming it so a later ADR can decide it deliberately rather than discovering the fork by accident. See Open Question A below.

### 5. Migration shape (Crawl-B implementation, post-ratification)

One additive migration, no data reshaping, no downtime:
- `ALTER TABLE platform_connections ADD COLUMN attestation_grade TEXT NOT NULL DEFAULT 'platform'` (backfills every existing row to gold — see Q1).
- `ALTER TABLE platform_connections ADD COLUMN watch_id UUID NULL` (NULL for all existing rows = capability bindings — see Q4).
- No change to existing rows' `platform`, `status`, `credentials_encrypted`, `metadata`. No RLS change. No new secret.
- The gate generalization at `orchestration.py:1363` ships in the *same* commit (Singular Implementation: the new column and the gate that reads it land together, never a column without its reader).

---

## D. What this amendment preserves (regression checklist)

- ✅ Crawl-A (D2/D3/D8/D9) — untouched.
- ✅ Alpaca / money-truth high-trust guarantee — preserved by derivation (Q1 + §B).
- ✅ B1/B2/B3 funnel — preserved; named as the grade-assignment mechanism.
- ✅ Watch-first discipline (D5) — preserved; clarified to coexist with legacy capability bindings (Q4).
- ✅ Every capability firing today — still fires (Q2, superset property).
- ✅ Transport-blindness (§6) — *strengthened* (the gate provably reads a grade, never a protocol).
- ✅ No dual-tracking (DP7) — *enforced* (tier derived, never stored; §C §13 bullet).
- ✅ Singular implementation — one gate, two transport families, legacy `platform_connection_requirement` absorbed not paralleled (Q3).

---

## E. Open questions this amendment leaves (deliberately)

- **A. Unify "connect a platform" into "declare a watch"?** (from Q4) Should ADR-207 capability-unlock become a special case of ADR-335 D5 watch-declaration, collapsing the two binding shapes into one? Plausible, attractive for conceptual unity, but a real ADR with real migration weight (every existing connection would re-home into a watch). **Out of scope; named for a deliberate later decision.**
- **B. Foreign-call metering as a Crawl-B precondition** (from the finding §8.3) — an unmetered mechanical executor calling arbitrary `OPEN`-grade servers scales the cost surface with the openness D4 sells. The grade does not bound *cost*, only *trust*. Metering must land with the client, not after. **Restated here as binding on the Crawl-B commit.**
- **C. The ADR-076 server-auth-shape ghost** (finding §7) — the premise "the things ADR-076 retreated from no longer exist" is reasoned from protocol maturity, not a real server bound end-to-end. **Crawl-B increment 1 (bind one real OAuth-2.1 server, GitHub-via-MCP recommended) is the receipt that discharges it.** The empirical gate ADR-335 §12 places on Walk should be pulled forward to *also* gate Crawl-B's first binding.

---

## F. Cross-cascade (what else changes if ratified — same-commit discipline)

Per CLAUDE.md prompt/primitive-rename protocol and ADR same-commit discipline, ratifying this amendment cascades to:
- **FOUNDATIONS** — Axiom 1 perception sub-clause (D8, already landed) gains one sentence: *transport trust is a derived tier of the read's flow-role, never a stored property of the transport.* (DP27 unaffected.)
- **GLOSSARY** — "Watch" / "Observation" entries (already canonical) gain a cross-ref to *attestation grade* on the binding; add **no** "head/tail" entry (the term is retired, not defined).
- **`docs/architecture/primitives-matrix.md`** — when the MCP-read primitive lands (Crawl-B), it declares the derived-tier gate, not a `platform` requirement.
- **The finding** [`2026-06-18-head-tail-split-consequence-radius-FINDING.md`](../evaluations/2026-06-18-head-tail-split-consequence-radius-FINDING.md) — status flips Open → Resolved-by-amendment on ratification.
- **No code lands until Crawl-B is demand-pulled and built** — this amendment is framing + storage-shape + migration-shape only. The Stage-C fence on D4 stands.
