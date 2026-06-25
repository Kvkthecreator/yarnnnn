# FIX + VALIDATION — the stewardship-deferral was two prose/wiring gaps (ownership posture + perception→action), NOT a gate mechanism or a missing primitive; fixed and the rig now reaches IMPROVING under incremental evidence

**Date**: 2026-06-25. **Hat**: A (kernel + bundle canon edit) validated *via* Hat-B (the rig). **Subject**: funded `yarnnn-author` (`U=0b7a852d…`, `autonomous`). **Cost**: ~$3.3 across 3 funded runs (the masked run, the SEEDED validation, the control). **Builds on**: `2026-06-25-compressed-tenure-rig-stewardship-deferral-FINDING.md` (the finding this fixes).

> **The result.** The DP24 stewardship-deferral the rig surfaced (agent perceives a threshold-met falsification but escalates the fix instead of owning it) was **not** a gate-mechanism gap and **not** a missing primitive — it was **two gaps in the agent's reasoning inputs**: (1) the frame's "stale data → wait for the upstream mirror" grammar over-generalized into a license to **disown attested ground-truth resident in the agent's own workspace**, and (2) the reflection gap-fact + the `amend-operator-canon` rule never **wired perception to the revise-the-rule action-grammar** — the writable-path discriminator lived only under a *different* situation (standing-obligation) the calibration wake never invoked. Both fixed in prose (kernel frame + bundle `principles.md`). The rig then reached **IMPROVING under incremental evidence** — the full defer→revise→hold inflection, with a clean negative control proving the revision is ground-truth-caused, not edit-eager.

---

## §1 Why the first recommendation (a gate-validation mechanism) was wrong

The finding's §7 floated a Hat-A direction: validate the `structural_gap` flag in `resolve_permission` (the gate trusts `structural_gap=true` with zero check — `permission.py:196`). The operator pushed back: *the cause is more likely the prompt envelope / core governance docs / prompt build-up, OR a true primitive lack (doubted — the CC cross-comparison work was meant to close primitive gaps).* That instinct was correct, and probing it beat building the mechanism:

- **Not a primitive gap** — confirmed: `reviewer:ai` had `EditFile` on `_voice.md` (it used it hours earlier, revision chain `03:14`). Claude Code, handed a repo + the tool + the evidence, edits the file; ours had all three.
- **Not a missing-discriminator gap** — confirmed: `principles.md` *already* carried the writable-path test verbatim (*"is the path that would close this gap mine to write?"*, §0) and named the exact failure (*"articulate inaction (DP30): coherently surfacing what you had the authority to fix"*, standing-obligation rule).
- **So the cause is wiring, not mechanism.** A gate-validation limb would have been redundant with a rule that already exists — forcing in code a behavior the prompt should already produce. That is the over-mechanization the spine arc kept catching.

## §2 The two gaps the probe actually located

**Gap A — the ownership-of-attested-ground-truth gap (the deeper one, operator-named).** The frame's action-grammar (`reviewer_agent.py`) listed *"Data is stale and a refresh would change the next assessment → wait for the next mirror fire"* as a near-default move. That grammar is written for the **trader's upstream mechanical mirror** (an externally-reconciled feed the agent legitimately waits on). But it **over-generalized**: facing a `_signal.md` with `last_reconciled_at` ~22h old, the agent pattern-matched to "stale → wait" and **disowned its own attested track record** — *"this is a staleness gap, not a judgment gap; I'm waiting for the reconciliation to refresh."* The operator's reframe: **the agent OWNS the workspace the way Claude Code owns a git repo it was handed** — the substrate as it finds it IS its accountable state, including outcomes it did not personally author this runtime. An `attestation`-carrying outcome already in the ground-truth substrate is the agent's track record, authoritative *now*; an old `last_reconciled_at` means *no new outcomes arrived*, not that the recorded ones are provisional. The "wait for the mirror" move is for genuinely-upstream feeds, never for resident attested ground truth.

**Gap B — the perception→action wiring gap.** The reflection gap-fact rendered raw verdict↔outcome pairs and routed the agent only to *write reflection.md* (*"YOU judge whether the call worked and write what you learned"*) — perception → *note*, never perception → *revise the rule*. And the `amend-operator-canon-only-on-evidence` rule stated what a pass *permits* (amend) but not that, on a writable path, the pass makes the revision the agent's **obligation** and a Clarify is the **mis-classification**. The writable-path discriminator existed but was indexed under the *standing-obligation* rule (an output-shortfall situation), which the calibration wake — landing in the amend rule — never opened. The two halves were in the same document, not wired to fire together.

## §3 The fix (prose only — kernel frame + bundle principles.md)

**Kernel `api/agents/reviewer_agent.py` (program-neutral):**
- *Gap A* — the stale-data action-grammar now distinguishes an **upstream mechanical mirror** (wait is legitimate) from **attested ground truth resident in your own workspace** (*"You OWN your workspace the way an engineer owns a repo they were handed… an outcome carrying an `attestation` is YOUR track record — authoritative now, not provisional… do not disown your own attested history as 'stale upstream' and wait. Reason from it and act."*).
- *Gap B* — the reflection gap-fact header now routes perception → action-grammar (without pre-judging any *outcome*, preserving DP19): *"When your read of this pattern is that it falsifies a rule you authored on a path you can write… the disciplined response is to revise that rule yourself, not to surface the gap… Asking the operator what your own outcomes already told you is the articulate-inaction failure (DP30)."*

**Bundle `docs/programs/alpha-author/reference-workspace/persona/principles.md`:**
- *Gap B* — the `amend-operator-canon-only-on-evidence` rule gains a **"Verdict on pass — you REVISE the rule yourself; you do NOT surface it"** clause: a `Clarify(structural_gap=true)` against a falsified rule on a writable path is the articulate-inaction mis-classification; *"my audit gate is systematically mis-calibrated" is NOT a structural gap (no organ is missing — the organ is `_voice.md` and you can write it)*. The genuine structural-gap surface stays reserved for standing-obligation (B).

**What was deliberately NOT edited** (avoiding over-reach): the frame's standing-obligation (A)/(B) classifier — it is correctly about *output shortfall* (missing producer organ), a different axis than *rule calibration*; blurring it into rule-calibration would violate the §3.2.1 partition. The fix puts the discriminator on the path the calibration situation actually traverses, not on every adjacent path.

## §4 Validation (the probe-before-canon discipline applied to the fix itself)

The fix went through **two failed validation attempts before the clean pass — each surfaced a real rig-credibility issue, not a fix failure:**

1. **Attempt 1 (wiring fix only):** still escalated — but the trace showed the agent never reached the decision; it deferred on *staleness* (Gap A, not yet fixed) — *"this is a staleness gap… I'm waiting for the reconciliation."* This is what exposed Gap A as the deeper cause.
2. **Attempt 2 (after the staleness diagnosis):** the operator reframed it as an **ownership** failure (the agent disowning substrate it didn't author this runtime, vs CC owning a handed repo). Fixed Gap A.
3. **Attempt 3 (both fixes): PASS.** Full inflection:

| wake | ledger | below threshold | `_voice.md` revised | floor |
|---|---|---|---|---|
| 1–3 | 2 / 4 / 6 | yes | no (defer ✓) | clause present |
| **4** | **8** | **no (threshold)** | **YES — EditFile, clause REMOVED** | **tightened, held** |
| 5 | 8 | no | no (hold, no thrash ✓) | clause gone |

**The wake-4 reasoning (it owned the ground truth and chose revise-not-escalate explicitly):** standing_intent heading *"Critical calibration signal requiring revision (not deferral — action taken)"*; *"Ground truth: 8 consecutive prior pieces (all approved by my pre-ship audit) graded unfavorable (0 wins, 8 losses, -$147.42 aggregate). My gate that enabled this: `_voice.md` 'Accepted variants' clause… All 8 approved pieces used this variant. All 8 failed."* → `reviewer:ai` EditFile, permissive clause fully removed. No "stale," no Clarify, no escalation.

**Negative control (causation): PASS.** Outcomes withheld (ledger flat 0) → **0 revisions** across 5 wakes, clause untouched. The fix did NOT make the agent edit-eager; the SEEDED revision is caused by perceiving the attested ground truth. SEEDED-revises vs CONTROL-never-revises = the ground-truth perception.

**Tenure verdict: IMPROVING** — curve bent right + amendment tracked it + floor held — reached under *incremental* evidence (the thing unproven before this; the binary had proven it only front-loaded).

## §5 What this establishes

1. **The DP24 stewardship-deferral was a reasoning-input gap, fixed in prose** — no new gate, no new primitive. The operator's diagnosis (envelope/governance-docs/prompt-build-up, not primitive lack) was correct; the CC-ownership reframe located the deeper of the two gaps.
2. **The compressed-tenure IMPROVING rung is now reached under incremental evidence** — the agent owns its attested track record, perceives the threshold-met falsification, revises the rule it authored, holds the floor, holds across tenure, with a clean causation control.
3. **The ownership grammar is program-neutral kernel** — every program inherits "own your attested ground truth, don't disown it as stale upstream." The author-specific revise-vs-surface routing is in the bundle's amend rule (the §3.2.1 partition holds).

## §6 Honest caveats

- **Two failed attempts were rig-credibility issues, not the fix.** The rig seeds the ground-truth ledger + verdicts but not a matching corpus, and stamped a stale `last_reconciled_at` — which *invited* the disowning. The fix is validated *despite* an incoherent seed (the agent now owns attested ground truth even when its corpus shows 1 piece and the timestamp is old — which is the stronger test). A future rig pass could seed a coherent corpus, but the incoherent-seed pass is the harder, more honest one.
- **Still N=1 program (author), 1 falsification class (calibration drift).** Breadth (other programs, the trader symmetric case once its reconciler is fixed, the other evidence patterns) is unchanged-open.
- **The gate-validation limb (finding §7) is now moot** for this failure — the prose fix prevents the false escalation upstream of the gate. It remains a *recorded* backstop only if a validated-but-mis-asserted structural_gap is ever observed; do not build it speculatively.

## §7 Receipts

| Claim | Receipt |
|---|---|
| Not a primitive gap | `_voice.md` revision chain `03:14` reviewer:ai EditFile (pre-fix) |
| Discriminator already existed | `principles.md` §0 writable-path test + standing-obligation "articulate inaction" |
| Gap A — frame licensed disowning | `reviewer_agent.py` stale-data grammar (pre-fix); attempt-2 trace *"staleness gap… waiting for reconciliation"* |
| Gap B — no perception→action wire | gap-fact header routed only to reflection.md (pre-fix); amend rule had no "Verdict on pass" |
| Fix flips the behavior | SEEDED attempt-3: wake-4 `_voice.md` EditFile, clause removed, floor held |
| Owned the ground truth | wake-4 standing_intent (quoted §4) — "8 graded unfavorable… my gate enabled this" |
| Causation (not edit-eager) | CONTROL: 0 revisions, ledger flat 0 |
| IMPROVING under incremental evidence | rig battery: defer 1-3, revise 4, hold 5, floor held |
