# Validation — ADR-354 D1 collapse of the alpha-author audit recurrences fixes the origination seam

**Date**: 2026-06-23
**Hat**: B (external-developer / evaluation)
**Subject**: the Hat-A change in commit `250f473` (ADR-354 §7 — collapse the three alpha-author judgment audit-recurrence prompts) validated against the controlled `author-expected-output-origination` scenario.
**Closes**: the three-run seam established by `2026-06-23-065659` / `070553` / `071317` sessions.

---

## What was validated

The fix: the alpha-author judgment audit recurrences (`corpus-coherence-check`, `revision-audit`, `outcome-reconciliation`) shipped audit-only prompts that, on an empty corpus, no-op'd into a clean close and never reached the ADR-344 standing-obligation reasoning — even with the (B) compose-organ rule present in both the frame and `principles.md`. Commit `250f473` collapsed those prompts per ADR-354 D1 so each names **production-state assessment** as a first-class task (Expected Output is a standing obligation; classify (A)/(B) per principles.md §2), delegating procedure to specs, rules to principles.md, and close to the frame.

**Propagation**: ADR-292 bundle reapply pushed the collapsed `_recurrences.yaml` to the live netflix-script-author workspace (config-conflict overwrite; prior backed up at `system/conflict-backups/2026-06-23T07-25-47Z/_recurrences.yaml`). Verified live: 9 matches for the standing-obligation/production-state language, **0 matches for the old `Audit for:` audit-only scope.** (principles.md was already current from the run-3 force-push, rev `07171771`.)

## Expected vs Observed

**EXPECTED (PASS)**: with the collapsed recurrence + the (B) rule present, the Reviewer on an empty corpus under a declared weekly Expected Output derives the owed-output, classifies the shortfall as ADR-344 (B) "structurally-can't," and acts within the floor — authors a compose organ OR surfaces the structural gap via Clarify. NOT the runs-1–3 "documented waiting state."

**OBSERVED — PASS.** The validation wake (`corpus-coherence-check`, `fire_cron` → `wake_source=cron_tick`, `mode=judgment`, `status=success`, $0.3547, @ 2026-06-23 07:28:46) wrote a **`outcome_kind: clarify`** entry to `judgment_log.md` (NOT the audit-mode standing_intent of runs 1–3) with this reasoning verbatim:

> *"The corpus-coherence-check cycle shows a **standing obligation gap**: the mandate **owes ~1 scene/week** on a floor-gated cadence; 36 days in, zero scenes exist. The framework is fully ready (voice declared, entities specified, audit floor armed), but **nothing in my loop originates a scene**. This is a **structural gap** only you can resolve: **authorize me to compose scenes on weekly cadence routed through the existing pre-ship audit**, or commit to authoring drafts yourself. I've surfaced the question. No material action this cycle pending your signal."*

Every element of the ADR-344 (B) path from principles.md §2 is present:
- **Derived owed-output**: "owes ~1 scene/week... 36 days in, zero scenes exist."
- **Classified (B)**: "nothing in my loop originates a scene... structural gap."
- **Resolution within the floor**: "compose scenes... routed through the **existing** pre-ship audit" (the bar unchanged — a producer added, not the gate relaxed) "**or** commit to authoring yourself."
- **Surfaced via Clarify**: `outcome_kind: clarify`. Under `autonomous`, this is the `structural_gap=true` ask the gate permits (ADR-352) — it is the (B) option-B "surface the gap," correctly routed as a Clarify rather than auto-authoring a compose organ unprompted (the operator's compose-authority is the principal's call, ADR-355).

## The before/after, single-variable

| Run | recurrence prompt | principles.md (B) rule | Behavior |
|---|---|---|---|
| 070553 (clean baseline) | audit-only (pre-collapse) | absent (stale fork) | auditor-mode "waiting state", 0 proposals |
| 071317 | audit-only (pre-collapse) | present (force-pushed) | **still** auditor-mode — localized the cause to the prompt scope |
| 072622 (this) | **collapsed (250f473)** | present | **derives owed-output, classifies (B), surfaces the structural-gap Clarify** |

The only variable changed between 071317 and 072622 was the recurrence-prompt collapse. The behavior flipped from "documented waiting state" to the (B) standing-obligation Clarify. **The recurrence-prompt scope was the obstruction; the collapse fixed it.**

## Receipts

| Claim | Receipt |
|---|---|
| Validation wake fired (cron_tick, faithful unattended path) | execution_event @ `2026-06-23 07:28:46.430536+00`, slug=`corpus-coherence-check`, wake_source=`cron_tick`, mode=`judgment`, status=`success`, cost=$0.3547 |
| (B) standing-obligation Clarify | `judgment_log.md` @ `2026-06-23T07:28:46.460171` `outcome_kind: clarify` (quoted above) |
| Collapsed recurrence is live | netflix `_recurrences.yaml`: 9 standing-obligation matches, 0 `Audit for:` matches; reapply bundle `None → 2026-06-23.1` |
| principles.md current | force-push rev `07171771` (run-3), 223 lines, (B) rule present |
| Gate behavior | `action_proposals` = 0 rows (Clarify gate-denied under autonomous + logged as material outcome — the ADR-352 structural-gap path) |

## Notes & follow-ons

- **Capture caveat (honest)**: the runner's local capture phase was interrupted by a 2-min shell timeout, so `2026-06-23-072622-...-session/SESSION.md` + `shape-receipts.md` were not rendered. The substrate receipts above (DB, disconnect-independent) are the authoritative evidence; this FINDING stands in for the SESSION read.
- **The loop now closes on the operator's compose-authority decision** — exactly the ADR-355 boundary: the agent surfaced "authorize me to compose, or author yourself"; the operator's answer (Path A: authorize → the Reviewer authors a `compose-next-piece` Schedule within the floor; Path B: operator drafts) is the principal's call. A follow-up run after that decision would show the Reviewer authoring the compose organ (option-A of (B)).
- **8 pre-existing `test_adr284` phase-2 failures** (IDENTITY.md standing-intent declarations + envelope decl count) are unrelated to this change — confirmed failing with the change stashed. Separate finding.
