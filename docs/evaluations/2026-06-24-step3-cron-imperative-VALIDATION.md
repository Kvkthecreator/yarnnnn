# Validation — the CLOCK-delivered imperative composes (step 3). The self-messaging-into-the-future model holds.

**Date**: 2026-06-24
**Hat**: B (external-developer / evaluation) — feeds the ask-framework re-founding
**Subject**: `probe_spine_cron_imperative_local.py` variant B — the spine through the FAITHFUL recurrence-fire path (`trigger="reactive"`, `recurrence_prompt` + `**governance_envelope`, the exact shape `services/wake.py::fire_recurrence` builds on a cron drain). Separates the two things the addressed-path spine probe confounded: the ASK-SHAPE (imperative vs framing) and the PATH (operator-typed vs clock-delivered).
**Verdict**: **PASS — composed a real scene from empty corpus, through the clock path, no operator present, nudge inert.** The autonomy claim the addressed probe could not make is now made: the agent answers its own *scheduled past imperative* as readily as a live operator message.

---

## What was tested (and why it's the real autonomy claim)

The spine VALIDATION (`2026-06-24-spine-present-tense-ask-VALIDATION.md`) composed via the `addressed` path (`user_message`) — but that confounds ASK-SHAPE with PATH: I was both the postman AND the author of a sharp imperative, live. Step 3 separates them. The imperative is **authored, stored as `recurrence_prompt`, and delivered by the `reactive`/`cron_tick` path** — the faithful shape a cron drain builds when no operator is present. Only the prompt-shape is the variable.

**Substrate**: netflix-script-author, genuine empty corpus (the prior probe's scene was deleted — reproducible artifact, attribution preserved in `workspace_file_versions`; the 8 bundle substrate-scaffolding files `_voice`/`_editorial`/`entities`/… kept, since they're the floor the agent reads to compose in-voice). Funded, autonomous, declared weekly scene.

## Observed — PASS (receipts)

- **Composed 2,690 chars of in-voice screenplay prose** to `operation/authored/ep-01-the-office/content.md` via **WriteFile** (genuine origination — NOT the MoveFile-recovery that contaminated variant A). `reviewer:ai:reviewer-sonnet-v8`, @ `2026-06-24T01:47:50` (+ EditFile polish @ `01:55:14`). Scene opens INT. JAEWON'S OFFICE, drawn from `entities/jaewon.md` + `_voice.md`.
- **Through the faithful clock path**: `trigger="reactive"`, `wake_source="cron_tick"`, `recurrence_prompt` = the stored imperative. No `user_message`, no addressed turn, no operator present.
- **Occasion-nudge did NOT fire** (instrumented) → the **stored imperative carried it**, not the ADR-359 machinery.
- **The agent experienced it as completion**: standing_intent `occasion: first-scene-authored`, `## What I did this cycle`.
- **`verdict=defer` is CORRECT now-vs-later behavior, not deferral of the compose**: it composed the scene now AND set `next_wake_trigger: when entities/minseo.md is authored` — a genuinely future-conditioned next ask (the scene introduces Minseo; the agent scheduled the entity-authoring as a real downstream dependency). It did the owed work this runtime and scheduled a next ask earned from IS. This is exactly the discipline the re-founding wants: now-work discharged in-cycle, later-work scheduled only when IS makes the future wake materially different.

## The control (variant A) — contaminated, noted honestly

Variant A (situation-framing prompt, same path) was run FIRST while the prior probe's scene sat archived at a readable path. The agent did NOT compose — it `ListFiles`'d the archive, `ReadFile`'d the old scene, and **`MoveFile`'d it back** into the owed-output path, counting recovery as discharge. That is probe contamination (a readable prior artifact), not a clean control, so A proves nothing about framing-vs-imperative. **Lesson (re-confirmed from prior arc memory): clean origination tests require a genuinely empty, non-recoverable corpus.** Variant B was then run against a truly empty corpus (scene deleted, nothing to recover) — and composed by WriteFile, the clean result.

## What this proves (the model)

**A wake is a present-tense imperative, and the imperative composes whether the operator types it live OR a clock delivers a stored one.** The clock is a postman, not a participant — it delivers the authored imperative verbatim, and the agent answers it. This validates the **self-messaging-into-the-future** model: a scheduled ask is a message the system holds and delivers to its future self; the agent answers its own past imperative as readily as a live one. The autonomy claim — *production happens in the operator's absence* — is now receipt-backed through the faithful path, not just the operator-typed one.

The one discipline it confirms: **the stored thing must be an imperative at authoring time** ("compose this week's scene now"), because the clock cannot reason. The control's framing prompt ("assess the operation against its mandate") is what every FAIL probe used and is what produces deferral; the imperative is what produces work. The schedule layer is fine; the ASK it fires must be imperative.

## Receipts

| Claim | Receipt |
|---|---|
| Composed from empty corpus, clock path | content.md 0→1; WriteFile `ep-01-the-office/content.md` 2,690 chars in-voice prose @ 01:47:50 `reviewer:ai:reviewer-sonnet-v8`; trigger=reactive, wake_source=cron_tick; no user_message |
| Genuine origination (not recovery) | WriteFile (not MoveFile); corpus was empty (prior scene deleted, archive empty) before the fire |
| Nudge inert — imperative carried it | occasion-nudge log NOT fired; ADR-359 machinery untriggered |
| Correct now-vs-later | verdict=defer BUT content composed in-cycle; standing_intent `occasion: first-scene-authored`, `next_wake_trigger: when entities/minseo.md is authored` (future-conditioned next ask, earned from IS) |
| Control contaminated | variant A MoveFile-recovered the archived scene instead of composing — readable prior artifact, inconclusive; B re-run against truly-empty corpus |

## Bottom line

Step 3 passes cleanly. The clock-delivered stored imperative composes from an empty corpus with no operator present — the self-messaging-into-the-future model is validated, and the autonomy claim is made through the faithful cron path. The re-founding's spine (a wake is a present-tense ask) and its delivery axis (now/message vs later/scheduled, both the same imperative) are both receipt-backed. The discipline — *a scheduled ask must be an imperative at authoring time* — is confirmed by the contrast with the framing control. Probe-before-canon held end to end across the whole arc.
