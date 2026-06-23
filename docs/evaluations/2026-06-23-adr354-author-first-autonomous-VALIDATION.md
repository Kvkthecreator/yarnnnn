# Validation — author-first-under-autonomous: the agent AUTHORS the producer organ, no permission-seeking Clarify

**Date**: 2026-06-23
**Hat**: B (external-developer / evaluation)
**Subject**: the Hat-A fix (alpha-author `principles.md` §2 (B) precedence rewrite + ADR-354 §8) validated against the controlled `author-expected-output-origination` scenario.
**Closes**: the operator's question — *"in full autonomy why is it asking for authorization?"* — and the residual passivity the prior validation (`2026-06-23-adr354-author-collapse-VALIDATION.md`) surfaced.

---

## The question this answers

The §7 collapse made the standing obligation *reachable*, and the prior validation showed the Reviewer correctly classify ADR-344 (B) — but it **surfaced a permission-seeking Clarify** (`outcome_kind: clarify` — *"authorize me to compose scenes on weekly cadence... or commit to authoring drafts yourself"*). Under `autonomous` (autonomy-as-witness, ADR-345), asking permission to do what is already your standing authority is autonomy-in-costume.

**Diagnosis (substrate-receipted)**: the cause was the `principles.md` §2 (B) text — it presented "Do ONE of: **author** … **or surface**" as *unordered* options AND shipped a copy-paste *surface* script (*"authorize me to compose on cadence, or feed drafts"*) with no author script. The agent reached (B), saw two equal options, and copied the more concrete one. The frame's (B) line had the same parallel "X, or Y" with no precedence — but the persona-frame is at its char ceiling (pre-existing `test_adr323` over-ceiling at 11,809 on HEAD), so per §3.2.1 the precedence was instanced in `principles.md`.

**Fix**: `principles.md` §2 (B) rewritten — *the default move is to AUTHOR the missing organ; under `autonomous` you author it, you do not ask permission*; the witness dial means the operator *witnesses* the authored organ. The structural-gap Clarify narrowed to genuine operator-needs (a missing capability, a floor change, a mandate reinterpretation). The "authorize me to compose" script deleted. (alpha-trader's (B) was already correctly ordered — *"Authoring is your authority; commissioning is not"* — so this is parity, not novelty.)

## Expected vs Observed

**EXPECTED (PASS)**: on (B) under `autonomous`, the Reviewer AUTHORS the compose organ (a Reviewer-authored `Schedule` routed through the existing floor) on its own initiative — `outcome_kind: schedule_create`, no permission-seeking Clarify.

**OBSERVED — PASS.** The validation wake (`corpus-coherence-check`, `fire_cron` → `wake_source=cron_tick`, `mode=judgment`, `status=success`, $0.2470, @ 2026-06-23 07:49:42) **authored the producer organ itself**:
- New recurrence **`compose-screenplay-scene`** now exists — `active`, `schedule: 0 10 * * 1` (Monday weekly), `mode: judgment`. Authored @ 07:49:03 (`created recurrence compose-screenplay-scene`). Its prompt is a real, mandate-grounded compose instruction (the Korea Thomas-Crown-Joker thriller, Jaewon protagonist, `_voice.md` floor, entity continuity) — not a stub.
- judgment_log `outcome_kind: schedule_create` (NOT clarify), verbatim:

  > *"The standing obligation rule in principles.md identifies a structural production gap: an operation that owes ~1 scene per week from an empty corpus, with judgment recurrences that can only audit existing material. I **authored a missing producer organ** (`compose-screenplay-scene` recurrence, weekly, judgment mode) **within my standing authority per ADR-275 D1**. No framework changes warranted; **no proposals necessary**. The operation transitions from waiting to producing Monday 2026-06-24."*

- `action_proposals` since 07:47 = **0 rows**. No Clarify, no permission ask.

## The before/after — single variable

| Run | principles.md §2 (B) | Behavior |
|---|---|---|
| `072622` (prior validation) | unordered "Do ONE of" + scripted surface example | `outcome_kind: clarify` — *"authorize me to compose, or author yourself"* (permission-seeking) |
| `074723` (this) | **author-first-under-autonomous (rewritten)** | `outcome_kind: schedule_create` — *"I authored a missing producer organ within my standing authority. No proposals necessary."* |

The only variable changed was the (B) precedence rewrite. The behavior flipped from asking-permission to authoring-on-initiative. **The principles §2 (B) text was steering toward the ask; the precedence fix retired the passivity.**

This is the answer to the operator's question: under full autonomy the agent should NOT ask for authorization to author a producer organ that is within its standing authority (ADR-275 D1) + floor — and now it doesn't. Autonomy-as-witness (ADR-345) operating correctly: the agent authored the organ; the operator witnesses it (it is `active` and fires Monday 2026-06-24 10:00 UTC).

## Receipts

| Claim | Receipt |
|---|---|
| Validation wake (cron_tick, faithful unattended path) | execution_event @ `2026-06-23 07:49:42.347512+00`, slug=`corpus-coherence-check`, wake_source=`cron_tick`, mode=`judgment`, status=`success`, cost=$0.2470 |
| AUTHORED the producer organ | `tasks`: `compose-screenplay-scene` active, schedule `0 10 * * 1`, judgment; `_recurrences.yaml` rev @ 07:49:03 (`created recurrence compose-screenplay-scene`) |
| schedule_create, not clarify | judgment_log `outcome_kind: schedule_create` @ 07:49:42 (quoted above) |
| No permission-seeking | `action_proposals` since 07:47 = 0 rows |
| Fix is live on netflix | principles.md force-push rev `03e3dfd3` (29,364 chars); old "authorize me to compose" script grep = 0 matches |
| Conformance | test_adr287 18/18 |

## Notes & follow-ons

- **Capture caveat (honest)**: the runner's completion gate timed out before the deployed scheduler drained the wake (slower scheduler tick this run), so `2026-06-23-074723-...-session/SESSION.md` rendered "0 wakes." The wake fired + succeeded + authored the organ — confirmed in the DB (receipts above, disconnect-independent). This FINDING is the authoritative read; the SESSION.md auto-render is stale.
- **The loop now closes end-to-end under full autonomy**: empty corpus → (B) classified → producer organ authored → `compose-screenplay-scene` fires Monday → first scene drafted → routes through the existing pre-ship-audit floor. No operator permission step. The operator witnesses (the organ is `active` in the index).
- **Pre-existing separate finding**: `test_adr323_frame_collapse_finished.py::test_system_prompt_under_ceiling` is failing on HEAD (frame 11,809 > 11,500) — a rebloat from a prior session, NOT this change (the frame is byte-identical to HEAD here). When resolved, the bare author-first precedence stance belongs in the frame (kernel-general per ADR-345), with principles.md instancing the program specifics (§3.2.1). Recorded in ADR-354 §8.
