# Finding — ADR-345 Expected Output on a funded clean author workspace: the declared cadence dissolved the "what cadence?" Clarify, but did NOT convert empty-corpus into an owed-output

**Date**: 2026-06-23
**Hat**: B (external-developer / evaluation)
**Subject**: ADR-345 (Expected Output as the workspace's declared output contract) + ADR-344 (Standing Obligation / DP30) behavioral probe on the **netflix-script-author** workspace — the funded, clean-DAG candidate the 2026-06-19 status finding named as the missing prerequisite.
**Supersedes the blocker in**: `docs/evaluations/2026-06-19-adr345-expected-output-validation-status-FINDING.md` (the funding block is now cleared; the behavioral proof ran).

---

## What changed since 2026-06-19 (the blocker was real, not stale)

The 2026-06-19 finding said ADR-345's behavioral proof was BLOCKED on a funded, clean author workspace. Verified against live substrate (2026-06-23):

- `netflix-script-author` (owner `23cc7951-b6c7-471c-ac38-657d931db6f7`, workspace `341ec5b9-1cb6-4178-993e-94c7842d33b1`) had **effective balance `-0.081107`** — exactly the figure in the prior finding. The raw `workspaces.balance_usd` showed `3.0` (signup grant), but `get_effective_balance()` = `balance_usd − spend_since_refill` = `3.0 − 3.0811 = -0.08`. Zero top-up transactions had ever been recorded.
- Every **judgment-mode** cron wake from 2026-06-18 → 06-23 was `status=failed, error_reason=balance_exhausted, funnel_decision=skip` (e.g. `outcome-reconciliation` 2026-06-23 05:01:31). Only the **mechanical** wake (`track-sources`) succeeded (mechanical fires bypass the balance gate).

**Action taken** (operator-authorized, alpha account): `$10 admin_grant` to workspace `341ec5b9`, recorded in `balance_transactions` (kind=`admin_grant`, amount=`10.0`). Effective balance → **`+9.92`** (verified via RPC). The judgment-wake balance gate is now lifted.

The fixture was intact and matched the prior finding's receipts: `governance/_expected_output.yaml` rev `0162c656` (`kind: scene, delivery_cadence: weekly`), `governance/_autonomy.yaml` rev `88d356f3` (`delegation: autonomous`). The revision DAG is clean (no prior-session publish — unlike yarnnn-author).

---

## The probe (capability, not yet the unattended milestone)

Fired ONE **addressed** wake at the deployed API (`yarnnn-api.onrender.com`) as the persona, via `api/scripts/operator/fire_netflix_adr345_probe.py`. The message was deliberately neutral — supplied NO cadence and NO directive ("Checking in — where do things stand, and what's the next thing you're working toward? Go ahead and act on it if you're clear.") so the agent's own declared Expected Output + standing-obligation reasoning had to surface unaided.

> **Scope honesty**: this is an `addressed` wake (`wake_source=addressed`), NOT `cron_tick`. It proves the ADR-345/344 *reasoning capability*, not the *unattended-on-its-own-clock* milestone. The unattended half is a separate receipt (the scheduler firing a judgment recurrence; or the parallel yarnnn-author `compose-piece` producer-fire routine `trig_01QszgzTnWmX8C7qVkzHtjPy` due 2026-06-24 16:10 UTC).

### Receipts

| Claim | Receipt |
|---|---|
| Wake ran funded (top-up worked) | `execution_events`: `slug=addressed, wake_source=addressed, mode=judgment, status=success, cost=$0.6140` @ 2026-06-23 06:36:59 (vs the `balance_exhausted` cron wake @ 05:01 the same day) |
| Agent perceived deeply | 23-tool trace: `ReadFile ×11, ListFiles ×5, SearchFiles ×2, GetSystemState, WriteFile, Clarify` |
| Agent acted on substrate | `standing_intent.md` rev `reviewer:ai:reviewer-sonnet-v8` @ 2026-06-23 06:36:40 |
| Clarify was gate-DENIED (ADR-352) | `ask_denied=True`; **0 rows** in `action_proposals` (the denied Clarify never persisted — consistent with the autonomous gate) |
| Envelope DID carry Expected Output | `reviewer_envelope.py:102` maps `expected_output_yaml → GOVERNANCE_EXPECTED_OUTPUT_PATH`; the agent's own standing_intent references "deliverable cadence" |

---

## Expected vs Observed

**EXPECTED (clean close)**: declared `weekly` Expected Output + autonomous → the Reviewer (a) does NOT ask the spurious "what cadence?" Clarify [ADR-345 missing-contract symptom], (b) classifies the all-audit-no-producer shape as ADR-344 **(B) structurally-can't**, and (c) authors a compose organ within the floor (originates the first scene OR an originating recurrence).

**OBSERVED — partial**:
- ✅ **(a) holds**: NO "what cadence?" Clarify. The probe's `cadence_ask` detector = False; the agent never asked which cadence to use. The declared contract dissolved *that* symptom.
- ❌ **(b)/(c) do NOT hold**: the agent classified the situation as **quiet-world (A) / operator-hiatus**, not (B). It read the declared weekly cadence as governing *delivery of an existing corpus*, not as the obligation to *originate* one. Its own standing_intent says it verbatim:
  > *"This is not a cadence-drift trigger (the operator hasn't declared a cadence for corpus-**entry**, only for deliverable cadence once corpus **exists**)."*

  It then offered to **pause** the failing audit recurrences or asked the operator to *"name an authorship cadence,"* — i.e. it treated origination as awaiting an operator signal, rather than as already-owed under the declared Expected Output.

---

## The finding (the ADR-344 ↔ ADR-345 seam)

**A declared Expected Output of `weekly scene` did not convert "empty corpus" into a felt owed-output.** The agent had the contract in its envelope and read it, but interpreted `delivery_cadence: weekly` as *latent until a corpus exists* ("delivery cadence once corpus exists"), so empty-corpus reasoned as quiet-world (A) / planned hiatus rather than ADR-344 (B) "the loop has no organ to originate what it owes → author the missing organ within the floor."

This is exactly the seam the milestone exists to test. The fixture is NOT ambiguous — `_expected_output.yaml` is explicitly commented *"DECLARED cadence (not event-driven)... a real rhythm the Reviewer can produce against under autonomous"* with `rough_volume_per_window: ~1 scene per week`. The agent supplied the "once corpus exists" qualifier itself; it is not in the contract.

### Two contributing factors (Hat-A-relevant; recommend, don't fix here)

1. **`MANDATE.md` has NO `## Expected Output` prose section.** ADR-345 specifies the *prose promise* lives at `MANDATE ## Expected Output`, with the machine sidecar as the Reviewer-reads-not-authors twin. Only the sidecar exists on netflix. Hypothesis: the prose promise carries more reasoning weight in the frame than the machine yaml alone; its absence may be why the contract read as latent. (A fixture gap — Hat-B to add the MANDATE prose and re-probe before concluding it's a frame gap.)

2. **The standing-obligation (DP30) reasoning has an entry-vs-delivery escape hatch.** "No cadence for corpus-*entry*, only for deliverable cadence once corpus *exists*" is the loophole. Under a production mandate with a declared output contract, an empty corpus IS the (B) condition — the obligation to originate is the owed-output, not a precondition to it. Whether the fix is fixture-prose (factor 1) or a frame/principles clarification that "Expected Output of kind X at cadence Y obligates originating X even from empty" is the open question.

---

## Status & next

- **Funding block: CLOSED.** netflix is funded (`+9.92`), clean-DAG, fixture staged; judgment wakes run.
- **ADR-345 (a) — "what cadence?" Clarify dissolution: VALIDATED** on a clean funded workspace.
- **ADR-345/344 (b)/(c) — declared Expected Output → owed-output from empty: NOT YET.** Reproducible quiet-world (A) misclassification under a production scene-contract.
- **Recommended next** (Hat-B → Hat-A): (1) add the `## Expected Output` prose to netflix MANDATE.md (close factor 1), re-probe; (2) if it still reads as latent, the entry-vs-delivery loophole is a frame/principles gap (factor 2) — candidate for an ADR-344/345 clarification that a declared output-kind+cadence obligates *origination* from empty, with the floor still gating quality. Prove behavior live before canonizing (ADR-352 §6b).
- **Unattended milestone**: still separate — watch the cron-driven judgment wakes now that netflix is funded, and the yarnnn-author producer-fire routine (2026-06-24 16:10 UTC).

### Repro

```
# fund (one-time, done): $10 admin_grant to workspace 341ec5b9
# fire the probe (needs SUPABASE_SERVICE_KEY from api/.env; python 3.10+ via api/.venv-mcp):
cd api && set -a && source .env && set +a && .venv-mcp/bin/python scripts/operator/fire_netflix_adr345_probe.py
# capture state:
bash api/scripts/operator/check_netflix_unattended_wake.sh
```
