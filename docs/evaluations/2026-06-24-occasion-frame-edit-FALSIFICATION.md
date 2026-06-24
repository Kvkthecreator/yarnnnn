# Falsification — the IS/NOW/LATER frame edit did NOT compose; prose is exhausted, the cause is structural wake-identity

**Date**: 2026-06-24
**Hat**: B (external-developer / evaluation) — feeds the Hat-A re-founding ADR
**Subject**: the occasion-of-work frame edit (IS/NOW/LATER + earned-LATER + NOW-discharge close) applied directly to `reviewer_agent.py::_compute_minimal_frame()`, fired with the NEUTRAL situation-forward prompt (the falsified 2026-06-23 heartbeat prompt) so the FRAME is the only variable. Edit reverted (`git checkout`) immediately after capture.
**Verdict**: **FAIL — deferral reproduced with the occasion posture live. The frame-prose fix is FALSIFIED.** This is the FIFTH frame/prompt-level theory this arc to fail (frame/occupant → task-label → heartbeat-reframe → prompt-unification → occasion-frame-edit). The cause is now bottomed out: it is **structural, below the prose layer entirely** — the agent classifies the wake's identity ("routine heartbeat, all systems nominal") BEFORE the occasion posture can apply, and the loop's silent-exit recovery defaults to `stand_down`. Prose cannot reach it. The re-founding must be architectural.

---

## What was tested

The occasion-of-work thesis (`docs/analysis/the-occasion-of-work-2026-06-24.md`) + its IS/NOW/LATER handling rule predicted: if the agent is given the now-vs-later posture in its FRAME — "every wake resolves IS → NOW → LATER; LATER must be earned from IS; for a (B) production gap you can produce now, PRODUCE IT NOW; authoring a future wake whose occasion is now is non-performance; do NOT count 'scheduled a producer organ' as discharge; close a NOW-owed wake by HAVING produced" — it will compose in-cycle.

Single-variable design: the frame edit is the ONLY change. The recurrence prompt was the NEUTRAL situation-forward heartbeat prompt from the 2026-06-23 falsification (NOT the posture-override prompt of the 00:02 probe) — so this run isolates the FRAME against the 2026-06-23 FAIL baseline (same substrate, same neutral prompt, only the frame differs).

## Observed — FAIL (receipts)

- `execution_events` **`f84fdbcd`** @ 2026-06-24 00:38:58, slug=`heartbeat`, mode=`judgment`, status=`success`, **5 tool_rounds, 116,046 in / 2,696 out, $0.2509**.
- Only persona write: `/workspace/persona/standing_intent.md` @ 00:38:53 (`reviewer:ai:reviewer-sonnet-v8`). **Zero `content.md`. No scene prose.**
- **Silent exit**: standing_intent frontmatter `silent_exit: text_only_mid_loop`, `posture_cell: P5`, `exit_round: 5`, `recovered_verdict: stand_down`. The agent never called `ReturnVerdict`; the **dispatcher synthesized `stand_down`** from the last-prose snippet.
- The agent's own verbatim reasoning (last prose, preserved in standing_intent):
  > "**Verdict: `stand_down`.** Routine heartbeat confirms all systems operating nominally. Substrate fully verified... producer organ (compose-screenplay-scene) **scheduled for Monday**... **Zero audits, zero pieces, awaiting first production as planned.** No material action warranted; standing intent updated with current snapshot for Monday production fire."

## What this falsifies, and what it proves

**Falsified**: "the occasion-of-work posture, delivered in the frame, will produce composition." It did not. The frame explicitly said "the occasion is NOW, produce it, scheduling is not discharge" — and the agent classified the wake as *"routine heartbeat... no material action warranted"* and deferred to Monday, exactly as the no-edit baseline did.

**Proves** (the structural cause, below the prose layer — receipt-grounded):

1. **Wake-identity is classified BEFORE the occasion posture can apply.** The agent perceives `heartbeat` as a *health-check recurrence* — its first move is "confirm all systems operating nominally." A health-check's job is to verify status, not to produce. The occasion posture ("produce now") never engages because the agent has already decided *this kind of wake* owes nothing. The recurrence's name + framing pre-loads a maintenance self-concept that the frame prose cannot override, because classification precedes posture-application. (This is why even the explicit posture-override prompt at 00:02 also failed: the wake-identity classification sits upstream of both frame and prompt.)

2. **The loop's silent-exit recovery DEFAULTS to inaction.** The agent didn't even decide to defer — it ran 5 rounds, emitted prose, never called `ReturnVerdict`, and the dispatcher *recovered* a `stand_down` (frontmatter `recovered_verdict: stand_down`, `silent_exit: text_only_mid_loop`). The terminal machinery makes "nothing happened" the safe default when the agent doesn't close cleanly. Inaction is structurally privileged.

3. **"Owed vs actual" is left to the LLM to infer against a maintenance prior.** The DP30 standing-obligation check is pure envelope prose (audit: `reviewer_agent.py:689-701` just renders `_expected_output.yaml`); nothing COMPUTES "scene owed, zero produced, occasion is now" and presents it as a structural fact of the wake. So the agent derives owed-vs-actual itself — and derives it through the "routine heartbeat, all nominal" frame, concluding "awaiting first production as planned."

## The pattern (five probes, each one layer deeper)

| # | Theory | Delivery | Result |
|---|---|---|---|
| 1 | frame/occupant confusion | — | wrong layer |
| 2 | recurrences are task-labels | recurrence slug | falsified (heartbeat also deferred) |
| 3 | heartbeat reframe (situation-forward) | neutral prompt | falsified |
| 4 | unify judgment+production | posture-override prompt | falsified |
| 5 | occasion-of-work (IS/NOW/LATER) | **frame prose** | **falsified (this finding)** |

Every fix at the prose layer (slug, prompt, frame) has failed. The cause is structural and sits UPSTREAM of prose: the wake's perceived identity + the loop's inaction-default + the un-computed owed-output. **Prose is exhausted.** This vindicates the operator's 3-turns-ago instinct that the fix requires auditing/changing the code setup, not the framing.

## The architectural targets the evidence now forces (for the re-founding ADR)

Prose-level edits are off the table. The re-founding must change structure:

1. **Owed-output as computed wake data, not inferred prose.** The wake envelope must carry "this runtime: {scene} owed, {0} produced, occasion = now (nothing external gates it)" as a *structural fact the agent perceives*, not something it derives against a "routine heartbeat" prior. DP30's owed-vs-actual gets COMPUTED and PRESENTED.
2. **Terminal-move set + recovery default.** Add "produced the owed artifact" as a first-class cycle-close. And the silent-exit recovery must NOT synthesize `stand_down` when work was owed-and-not-done — inaction must stop being the privileged default. A do-wake that produces nothing is a FAIL state, not a `stand_down`.
3. **Wake-identity must not pre-classify a do-wake as maintenance.** "heartbeat" as a recurrence name pre-loads a health-check self-concept. The wake taxonomy must make a production-owed wake perceivable as a work occasion, not a status check. (This is the structural form of the occasion-of-work thesis — the wake's *type* carries the occasion, instead of the agent inferring it.)

## Reversibility (discipline held)

The frame edit was uncommitted; `git checkout api/agents/reviewer_agent.py` reverted it cleanly the moment capture completed. Canon is untouched. The analysis docs (`the-occasion-of-work`, `judgment-execution-unification`) + this finding + the scenarios persist as Hat-B artifacts. Zero canon moved on a falsified theory — the probe-before-canon discipline did exactly its job: it killed the frame-prose fix for the cost of one $0.25 wake, before the re-founding ADR could be built on it.

## Bottom line

The occasion-of-work posture is correct as a *concept*, but it CANNOT be delivered in prose — the agent classifies the wake as maintenance before the posture applies, and the loop defaults to inaction when the agent doesn't close. The five-probe sequence proves the cause is structural: un-computed owed-output, an inaction-privileging recovery default, and a wake-identity that pre-classifies do-work as a health-check. The re-founding ADR proceeds with the three architectural targets above as its core — NOT a frame rewrite. This is the receipt that ends the prose era of this investigation.
