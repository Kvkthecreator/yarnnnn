# ADR-345 — Expected Output: the workspace's declared output contract (+ the autonomy-as-witness reframe)

**Status:** **Accepted (2026-06-19)** — canon + schema + bundle worked-instances; fresh-workspace validation gates ratification of the wake-time read. See §8.
**Date:** 2026-06-19
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [`operation-heartbeat-and-autonomy-as-witness-2026-06-19.md`](../analysis/operation-heartbeat-and-autonomy-as-witness-2026-06-19.md). The operator's arc: "where does the standing obligation / expected output reside? … shouldn't full autonomy mean zero operator intervention? … yes it's a heartbeat and rhythm, but **equally important is the expected output, which I believe are fundamentally different things we need to explicitly capture for each workspace.**"

**Companion naming**: GLOSSARY v2.8 (the *Operation Rate, Output Contract & Witnessing* section — Rhythm · Expected Output · Witness dial).
**Extends:** ADR-344 / Derived Principle 30 (the standing-obligation self-check derived an owed-output at wake-time; this gives it a *declared* referent, sharpening the (A)/(B) classifier), ADR-327 (Rhythm = spend-as-tempo — Expected Output is named as its orthogonal sibling, not a third budget facet).
**Reframes (prose only, no code change):** ADR-249 / ADR-307 — autonomy is the **witness dial** (which consequential beats the operator witnesses before they bind), not a "trust ceiling / approval degree." The mechanism (`permission.py`) is already exactly this; only the framing flips.
**Preserves:** the aperture/floor split (ADR-342/343 — Expected Output is a floor-gated delivery-cadence, NOT a quota that pressures the floor), ADR-320 five-root topology (prose in constitution, machine sidecar in governance — no new root), ADR-254 file-format discipline (`.md` prose / `_.yaml` machine), "operator authors what serves them" (Expected Output is **optional**; undeclared → the ADR-344 derivation is the fallback, so no existing workspace requires a migration).

---

## 1. Problem statement — two orthogonal concepts were collapsed into one

The standing-obligation work (ADR-344) made the Reviewer *derive* its owed-output at wake-time from budget × mandate × bar. Derivation is a correct floor, but a derived-only referent is **unstable and unshared** — the operator and the agent have no declared contract they both point at. That is the direct cause of the alpha-author Reviewer's repeated *"what's the production cadence?"* Clarify (2026-06-18): it was reaching for a referent that was never declared.

The deeper error (the operator's correction): an earlier synthesis folded **expected-output into the operation's rate** ("budget × pace × expected-output are three facets of one fact"). That is a category error. **Rhythm and Expected Output are orthogonal:**

- **Rhythm** (the heartbeat) — the *rate of attention*: how often the operation wakes/reasons/spends. A *rate*. Already canon (ADR-327: budget IS pace; `_pace.yaml` deleted).
- **Expected Output** — the *output contract*: what the operation owes (kind + delivery-cadence + bar). A *deliverable*, not a rate.

**The orthogonality proof:** a trader can wake every minute (fast rhythm) and correctly produce zero trades for weeks (no output owed — and that's correct); an author can wake weekly (slow rhythm) and owe two essays a month (definite output). Neither derives from the other. Expected Output therefore needs its own explicit home — it was homeless precisely because it was being wedged into `_budget.yaml`, where it does not belong.

## 2. Decision: Expected Output is a first-class, explicitly-declared workspace property

Every workspace may declare an **Expected Output** — the operator's promise of what the operation owes. It is the *measurable half of the MANDATE* (*why we exist*, made concrete). Two faces (the AUTONOMY.md + `_autonomy.yaml` pattern):

- **Prose (the promise) → `constitution/MANDATE.md` → `## Expected Output`.** Operator-authored intent, survives occupant rotation, human + LLM readable. ADR-344 already opened this optional section; ADR-345 makes it the canonical prose home.
- **Machine sidecar → `governance/_expected_output.yaml`.** The parseable referent the standing-obligation check (DP30) + any conformance gate read. Governance root because it is operator-declared and **Reviewer-reads-not-authors** (the same cut as `_budget.yaml` / `_autonomy.yaml`) — the operator owns the contract; the agent honors it.

The MANDATE prose is authoritative for humans; the sidecar is authoritative for machines; they must agree (same discipline as AUTONOMY.md ↔ `_autonomy.yaml`).

## 3. The schema — `governance/_expected_output.yaml` (cadence-not-quota)

```yaml
# _expected_output.yaml — the operation's output contract (ADR-345).
# Operator declares; the Reviewer reads + holds itself accountable (DP30);
# the Reviewer never authors this (governance, like _budget.yaml).
# The prose companion is MANDATE.md ## Expected Output.

expected_output:
  # KIND — the artifact the operation produces (program-natural noun).
  kind: essay                      # e.g. essay | trade | campaign | report
  # DELIVERY-CADENCE — the rhythm of delivery, NOT a hard quota.
  # A cadence the floor still gates: if nothing clears the bar this period,
  # the slot slips. The Reviewer measures "am I keeping rhythm", never
  # "have I hit a number no matter what".
  delivery_cadence: biweekly       # e.g. biweekly | weekly | per-signal | quarterly
  # BAR — the quality floor each unit must clear (pointer to where it lives;
  # the floor itself is principles.md / _voice.md / _risk.md, NOT duplicated here).
  bar: "principles.md voice + anti-slop + continuity audit (six rules)"
  # Optional shape hint — order-of-magnitude, never a hard target.
  # Present ONLY when the operator wants a rough volume sense; omittable.
  rough_volume_per_window: "~2 per month"   # advisory, floor-gated, never enforced as a quota
```

**The cadence-not-quota invariant (load-bearing):** `delivery_cadence` is a *rhythm the floor regulates*, and `rough_volume_per_window` is *advisory order-of-magnitude*. Neither is a number the agent must hit. A hard quota creates internal pressure to ship marginal work — the exact Goodhart hazard the aperture/floor split forbids *externally* (don't lower the bar to trade), now arising *internally* from a self-imposed target. The contract is a pulse the floor gates, not a body count. MANDATE's own alpha-author editorial principle already states this: *"Cadence is a floor, not a ceiling. If I have nothing on-thesis to ship in a given week, the slot goes empty or slips."*

## 4. The autonomy-as-witness reframe (prose, no code change)

The operator's framing — *"autonomy is almost a given/expected default; the modes are just the permission gate"* — is **literally how the code works.** `permission.py::resolve_permission` runs *after* the Reviewer has reasoned and decided to call a primitive; it returns APPLY (run now) / QUEUE (route to `action_proposals`, operator approves later) / DENY (governance-locked). **QUEUE has never meant "the agent was blocked" — it means "the agent decided, and this beat surfaces to the operator before it binds."**

So ADR-345 flips the *prose* (ADR-249/307 framing + the AUTONOMY.md bundle templates) from "trust ceiling / approval degree" to:

> **Autonomy is the witness dial.** The agent always works the full job (a judgment seat acting in absence). The dial decides *which consequential beats the operator witnesses before they bind* — not *whether* the agent works. `autonomous` = the whole operation runs subconsciously; `bounded`/`manual` = chosen beats surface first.

This canonically resolves *"does full autonomy mean zero operator intervention?"* → **yes: the agent works the whole job; the dial only routes attention.** And it reclassifies the alpha-author Path-A/B Clarify (2026-06-18) as a **missing-contract symptom**, not correct consent-seeking: with a declared Expected Output + `autonomous`, the agent authors its own production organ and produces at the declared cadence — nothing to ask.

## 5. Wiring the standing-obligation check (declared-then-derive)

DP30's standing-obligation check (ADR-344) gains a *declared* referent:
- **Declared path**: read `_expected_output.yaml` (+ the MANDATE prose) → compare actual output against the declared contract. "Behind on the contract" is now unambiguous.
- **Derive fallback**: when `_expected_output.yaml` is absent, the ADR-344 derivation (budget × mandate × bar) remains the floor — no workspace is forced to declare.

The sidecar joins the reviewer wake envelope (`reviewer_envelope.py::_UNIVERSAL_ENVELOPE_DECLS`) as `expected_output_yaml`, a new `ReviewerContext` field — same shape as `budget_yaml` (empty string when absent, so the key is always present).

## 6. Where it lands (separation of concerns)

A workspace is fully specified by four orthogonal operator declarations + the kernel frame:
- **MANDATE** (constitution) — *why we exist* + primary action + **`## Expected Output`** (what we owe).
- **`_budget.yaml`** (governance) — **Rhythm** (rate of attention).
- **`_autonomy.yaml`** (governance) — **Witness dial** (which beats surface).
- **IDENTITY + principles** (persona) — **Persona** (how we reason + the bar).
- **`_expected_output.yaml`** (governance) — the machine face of the Expected Output promise.

Rhythm, Expected Output, and the Witness dial are three different questions (*how often* · *what we owe* · *what surfaces*); none derives from the others. The GLOSSARY v2.8 section is the naming home.

## 7. Scope boundary

- No new primitive. The sidecar is read like `_budget.yaml`; the contract is honored by the existing DP30 check + the existing Schedule/file primitives (the agent authors its production organ within the floor, ADR-275 D1).
- No forced migration — Expected Output is optional; absent → ADR-344 derivation.
- No code change to the permission gate — the witness reframe is prose only.
- Not a quota — `delivery_cadence` + optional advisory `rough_volume`, floor-gated (§3).

## 8. Implementation status (2026-06-19)

- **Naming (companion)**: GLOSSARY v2.8 *Operation Rate, Output Contract & Witnessing* section (Rhythm · Expected Output · Witness dial).
- **Autonomy prose reframe**: both bundles' `AUTONOMY.md` "What autonomy controls" flipped ceiling → witness-dial.
- **Schema + path**: `governance/_expected_output.yaml` + `GOVERNANCE_EXPECTED_OUTPUT_PATH` in `workspace_paths.py`; envelope wiring (`expected_output_yaml` in `_UNIVERSAL_ENVELOPE_DECLS` + `ReviewerContext`).
- **Bundle worked instances**: both bundles ship `MANDATE.md ## Expected Output` + `_expected_output.yaml` (trader: kind=trade, delivery_cadence=per-signal-when-fires; author: kind=piece, delivery_cadence=operator-declared) + `_workspace_guide.md` note.
- **DP30 wiring**: the standing-obligation read consults the declared contract first, derivation as fallback.

**Validation (gates ratification of the wake-time behavior):** a **fresh** author workspace with a declared Expected Output (delivery-cadence R, `autonomous`), left to run — does the agent author its own compose organ and produce at R *without the spurious Clarify*? (The current yarnnn-author can't be the test bed — its revision DAG is contaminated and the Reviewer reads history, per the 2026-06-18 finding.) Recorded in `docs/evaluations/`.

---

## 9. Receipts

| Claim | Receipt |
|---|---|
| Rhythm = spend-as-tempo already canon | ADR-327 "pace was always a budget wearing a frequency costume"; `_pace.yaml` deleted |
| Rhythm ⟂ Expected Output | trader fast-wake/zero-output (correct) vs author slow-wake/definite-output — neither derives the other |
| Autonomy already = witness-selector in code | `permission.py:162-256` (gate runs after the Reviewer decides; QUEUE = "operator approves later", not blocked) |
| Expected Output was derived, not declared | ADR-344 §2; MANDATE `## Expected Output` optional, no machine sidecar pre-ADR-345 |
| Cadence-not-quota already in MANDATE | alpha-author MANDATE editorial: "Cadence is a floor, not a ceiling… the slot goes empty or slips" |
| Sidecar is governance (operator-declared, Reviewer-reads-not-authors) | ADR-320 cut; sibling to `_budget.yaml`/`_autonomy.yaml` |
