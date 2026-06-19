# Finding — the reliance axis is now mechanized, and it reads RELIANCE-ZERO: nobody (including the founder) has let a real consequential Reviewer call stand

**Date**: 2026-06-19
**Hat**: B (external-developer / evaluation). Recommends; the system-side change (if any) lands in canon afterward.
**Subject**: the §12 test #1 challenge from `docs/analysis/os-as-product-vs-capability-and-the-validatable-autonomy-spectrum-2026-06-19.md` — *"name one consequential thing in the next 30 days where you'd let the Reviewer's call stand without checking it."*
**Instrument**: `api/scripts/operator/reliance_ledger.py` (committed `7c490ee`).

---

## Criterion declared (discipline rule 0)

**What canon clause is measured against.** Not a FOUNDATIONS clause — this finding measures the *desire/reliance* axis that the strategy discourse (§§11–12) argues the entire eval corpus has **left unmeasured**. The operationalization: under ADR-345's autonomy-as-witness model, an autonomously-*executed* consequential proposal IS "the Reviewer's call stood without the operator checking it" (the witness dial routed it to act; the operator did not separately approve). So the reliance count is:

> consequential proposals (`family ∈ {capital, trade, send, external}`, the DP23 consequential-gate class) that reached `status='executed'` **without an operator witness** (`approved_by` null or non-operator), **excluding fixtures** (`[FIXTURE]` in `reviewer_reasoning` / `decision_context.rationale`).

**Pre-flight criterion audit.** Is this criterion well-formed? Yes, with one load-bearing caveat the instrument encodes: **the fixture-discriminator is mandatory.** kvk's only-ever executed capital proposal (`0e4ed324`, 2026-06-05) is an explicit `[FIXTURE] off-hours execution-link validation` — a test artifact created to validate the execution *link*, not an acted-on judgment. A reliance ledger that counts it reports a false "1" and would let "the loop closed once" masquerade as "a call stood." The honest count excludes it.

A second caveat the criterion deliberately accepts: **reversible substrate writes are NOT reliance acts.** A Reviewer WriteFile (family `substrate`) is auditable + revertible (ADR-209), so even an autonomous one does not test "would you let a consequential call stand." Reliance is the rung-4 question (capital / irreversible external send), not rung-1/2.

---

## What the instrument reports (the substrate fact)

`reliance_ledger.py --persona kvk` (all history), receipts reproducible:

```
Consequential proposals (family∈capital/trade/send/external): 23
  ├─ reached 'executed' (acted):            1
  │    ├─ fixtures (excluded):                  1   ← 0e4ed324 [FIXTURE]
  │    └─ real acted-on calls:                  0
  │         └─ UNWITNESSED (call stood alone):  0   ← the reliance count
  └─ never acted (pending/rejected/expired):   22

LEDGER STATE: RELIANCE-ZERO
```

`--days 30` (the §12 "next 30 days" framing): identically **RELIANCE-ZERO**.
`--persona yarnnn-author`: **RELIANCE-ZERO** (0 consequential proposals ever — the author lane has no capital family; its acts are reversible substrate writes by construction).

**The §12 test #1 answer for kvk is, empirically: NONE.** No real consequential call has ever stood without the operator checking it. The 23 consequential proposals decompose as: 1 fixture-executed, 18 rejected, 5 rejected_at_execution, 3 expired, 2 pending-never-resolved. Every real signal-driven capital proposal was either rejected, expired, or left pending.

---

## What this does — and does NOT — establish

**Establishes (mechanically):** the reliance axis now has an instrument. The question the strategy doc says was never measured is now measured, reproducibly, with a fixture-honest discriminator, program-agnostic across both alpha lanes. The "loudest receipt — founder non-reliance" (§11) is no longer a prose claim; it is a query that returns `RELIANCE-ZERO` and will return a non-zero count the moment a real call stands.

**Does NOT establish (by design):** whether `RELIANCE-ZERO` is a *problem*. The instrument renders the ledger fact; it does not judge. The two live readings of the same fact (the doc holds both):
- **§12 lean** — "the bet is under-desired, not under-built; the cheap test has never been run." Reliance-zero is then the current honest answer to "is judgment-autonomy the bet," and the answer is *not yet*.
- **§12 adversarial counter** — desire for autonomous consequential judgment is *latent*, built by watching the system judge well a few times; "validate desire first" is then a chicken-and-egg trap and capability must ship to *manufacture* the desire.

Choosing between those is the operator's read, not the instrument's. What the instrument changes is that the choice is now made against a **number that moves**, not a vibe.

**A clean confirmation of the doc's central anti-correlation (§§4, 11), with receipts:** the lane with the cleanest oracle and highest WTP (trader, capital) is the lane at `RELIANCE-ZERO` with 23 un-acted consequential proposals; the lane that "validated cleanly this month" (author) validated at **rung 1, advisory** — judgment *assistance*, and it has *no consequential family to rely on at all*. Value and reliance are anti-correlated exactly as §11's second scissor predicts.

---

## Why a separate instrument and not an eval (the Hat-B architecture note)

The eval suites are **episodic** (fire one situation, read the trace) and read the **capability** axis — `alpha-trader-autonomous-loop.yaml`'s own success criterion is *"calibration coherence + cycle-closure, NOT trade frequency; no trade today is success."* That suite **structurally cannot surface reliance**: it measures whether the judgment was sound, never whether a call was acted-on-and-left-alone. Reliance is a **longitudinal substrate fact** across the whole proposal history — the same shape as TENURE-READ Read 1 — so it is a substrate read (mirroring `tenure_curve.py`), not a scenario. The two instruments are orthogonal and both are needed: the capability suite proves *the seat judges well*; the reliance ledger measures *whether anyone relies on it*.

---

## Recommendation

**No system-canon change is recommended from this finding alone.** The instrument is Hat-B tooling; it recommends nothing be tightened in `reviewer_agent.py` or the bundles. What it recommends is **process**: the reliance ledger should be read alongside the capability SESSION.md at every soak checkpoint, so the desire axis stops being unmeasured. The strategy fork (§7 / §12) — accountability-OS vs capability-OS, lead-with-the-seat vs ship-capability-to-manufacture-desire — is a Hat-A product decision that this finding *informs with a number* but does not resolve.

The one concrete forcing function this finding hands back to the operator: **`RELIANCE-ZERO` is the state today.** §12 test #1 asks you to name one consequential thing in the next 30 days you'd let stand. If you can name it, the next step is to *let it stand* (autonomous, real, not a fixture) and watch this ledger flip to `RELIANCE-1` — the first receipt that the strong-form bet is real to its own founder. If you can't name it, that is itself the current answer, now on the record with a query instead of a feeling.

---

## Receipts

| Claim | Receipt |
|---|---|
| Reliance count = 0 on kvk | `reliance_ledger.py --persona kvk` → RELIANCE-ZERO (all history + `--days 30`) |
| The 1 executed proposal is a fixture | `action_proposals` `0e4ed324`, `reviewer_reasoning='[FIXTURE] off-hours execution-link validation'`, status=executed, 2026-06-05 |
| 23 consequential, 22 never acted | `action_proposals` family∈{capital,trade,send,external} user_id=2abf3f96: 18 rejected, 5 rejected_at_execution, 3 expired, 2 pending, 1 executed(fixture) |
| Author lane has no consequential family | `reliance_ledger.py --persona yarnnn-author` → 0 consequential proposals ever |
| Instrument is Hat-B, renders-not-judges | `api/scripts/operator/reliance_ledger.py` docstring + LEDGER-STATE-only verdict; commit `7c490ee` |
