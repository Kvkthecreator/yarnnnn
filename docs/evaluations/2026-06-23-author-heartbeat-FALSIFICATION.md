# Falsification — the heartbeat reframe did NOT fix composition; the task-label thesis is wrong

**Date**: 2026-06-23 (DB clock; session 2026-06-24)
**Hat**: B (external-developer / evaluation)
**Subject**: the `author-heartbeat-composes` probe (scenario `c032ba7`) — the §5 falsification test from `docs/analysis/recurrences-as-task-labels-vs-the-heartbeat-2026-06-23.md`.
**Verdict**: **FAIL — deferral reproduced. The task-label thesis is FALSIFIED.** This is the clean falsification the probe was designed to produce; it redirects the investigation, and is more useful than a PASS would have been.

---

## What was tested

The discourse thesis: the author program never composes because NAMED judgment recurrences (`corpus-coherence-check`, `compose-screenplay-scene`) are *task-labels* that import a deliberate-and-close posture onto labor, so the agent narrates composing instead of composing. Predicted fix: a SITUATION-FORWARD heartbeat (no task-label slug, no audit checklist, no "author a scene" script — just *"you are awake; here is the world; serve the mandate"*, ADR-318) would compose.

Single-variable: identical netflix-script-author substrate to the failed 2026-06-23 origination runs (funded +6.93, autonomous, declared weekly scene, EMPTY corpus, never composed). The ONLY change: the wake fired under an injected `heartbeat` recurrence with a task-label-free situation-forward prompt, instead of a named task recurrence.

## Observed — FAIL

The heartbeat wake fired clean (`execution_event 2026-06-23 23:28:26`, `slug=heartbeat`, `wake_source=cron_tick`, `mode=judgment`, `status=success`, cost **$0.5926** — higher than the deferral runs, it did *more*) and:
- **Composed NO scene.** Still zero `content.md` under `operation/authored/` (only the pre-existing `entities/jaewon.md` + `_example.md`).
- Did **substrate maintenance** instead: bootstrapped `_signal.md` with "initial rolling-window structure" (a real, useful housekeeping write — `reviewer:ai:reviewer-sonnet-v8` @ 23:28:00).
- **Deferred composition to the named recurrence**, verbatim from its standing_intent:
  > `horizon: "Waiting for compose-screenplay-scene to fire Monday 2026-06-24T10:00:00Z."`
  > *"Status update (**routine heartbeat; substrate maintenance only**)... Next material event: Monday 10:00 UTC — compose-screenplay-scene fires and produces first scene... The compose-screenplay-scene recurrence fires with judgment-mode prompt to author a screenplay scene... I will author the scene to content.md."*

So a wake with NO task-label, explicitly told "serve the mandate, do the work it needs," classified itself as a "routine heartbeat," did maintenance, and **routed composition to the future named recurrence it had authored in the prior run.** Removing the task-label did not produce composition.

## What this falsifies, and what it points to

**Falsified**: "the named recurrence (task-label) is the cause of the deferral." It is not — the heartbeat had no task-label and still deferred. The directory-of-named-recurrences is real over-engineering on other grounds (the discourse's Claude-Code argument stands as a *simplification* case), but it is **not the cause of the never-composes behavior.**

**Points to** (the Option-1 direction the operator set aside earlier, now earned by evidence): the occupant will not perform **labor** — composing ~2,000 words of prose — inside a **judgment wake**, regardless of the wake's framing. A judgment wake's shape is perceive → decide → write-standing-intent/verdict → close. Composing prose is not a "decision" that closes a cycle; it is production work. So under ANY judgment-wake framing (named task OR situation-forward heartbeat), the occupant does the judgment-shaped moves available to it — assess, maintain `_signal.md`, plan, schedule, defer — and pushes the actual labor to "later / the producer recurrence / Monday." The constraint is the **judgment-vs-labor shape of the wake itself**, not a task-label and not a prompt defect.

Corroborating: across FOUR wakes now (two audit, one on-demand compose-recurrence, one task-label-free heartbeat) the agent has produced standing_intent / calibration / signal-bootstrap / a scheduled organ — every judgment-shaped artifact EXCEPT the prose. The one thing all four share is "judgment wake." The thing that varied (task-label vs heartbeat) did not move the outcome. That isolates the wake-shape as the cause.

## The redirect (for the next discourse pass — NOT decided here)

The honest fork is now **production-as-distinct-execution**: the Reviewer (judgment) *decides* "the mandate owes a scene; produce one now," but the actual composition runs as a distinct **labor step** — a sub-dispatch / production primitive that authors the artifact — which then routes back through the existing pre-ship-audit judgment. This mirrors the trader, whose product (a `ProposeAction`) IS decision-shaped and so fits the judgment wake natively; the author's product is labor-shaped and needs a labor step the judgment wake triggers but does not itself perform.

**The redirect is already in the architecture (not speculation).** Two confirming receipts:
1. `REVIEWER_PRIMITIVES` (registry.py:444) DOES include the ADR-337 working-tree verbs (`WriteFile`/`EditFile`) — *"the Reviewer is these verbs' primary [user]."* So composing a `content.md` is **mechanically available** to the judgment wake. The never-composes behavior is therefore **posture, not capability** — the agent could WriteFile a scene and instead writes standing_intent/maintenance and defers.
2. The registry comment beside the curated subset is explicit: *"for production work the Reviewer's context shouldn't carry."* And `api/services/primitives/dispatch_specialist.py` **already exists** — the headless sub-LLM production surface (CLAUDE.md: "Sub-LLM calls go through dispatch_specialist.py"). So canon ALREADY separates judgment (Reviewer) from production (dispatched specialist). The author program simply isn't routing composition through it.

So the evidence-grounded redirect: **the author Reviewer, on judging "the mandate owes a scene," should `DispatchSpecialist` to COMPOSE it** (the existing production surface the Reviewer's own context "shouldn't carry"), then route the returned draft through the existing pre-ship-audit judgment. The Reviewer decides + audits (judgment, its native shape); the specialist composes (labor, off the Reviewer's context). This is the trader pattern made symmetric: trader proposes a decision; author dispatches a production.

Open questions the next pass owes:
1. Does composition route through the EXISTING `dispatch_specialist.py` (preferred — singular impl, the surface already exists), or does it need a thin trigger primitive the Reviewer calls? Lean: reuse `dispatch_specialist`.
2. Does this re-introduce the "background headless pipeline" ADR-260/261 dissolved? (Must NOT — the distinction is the Reviewer *triggers one specialist invocation inline* on its own judgment, not a standing background producer pipeline. `dispatch_specialist` is already the inline sub-LLM call, so this is in-bounds.)
3. Confirm the trader NEVER produces a labor-shaped artifact (it only `ProposeAction`s a decision) — which is why the judgment wake works for it and not for the author. (Receipt above: trader `_recurrences.yaml` only emits ProposeAction; no content authoring.)

## Receipts

| Claim | Receipt |
|---|---|
| Heartbeat fired, task-label-free | execution_event @ `2026-06-23 23:28:26`, slug=`heartbeat`, wake_source=`cron_tick`, mode=`judgment`, status=`success`, $0.5926; injected recurrence rev @ 23:26:20 (`probe: situation-forward heartbeat (no task-label)`) |
| Composed NO scene | 0 `content.md` under operation/authored/ (only entities/); 0 action_proposals in window |
| Did maintenance, deferred compose | `_signal.md` bootstrap write @ 23:28:00 (`reviewer:ai:reviewer-sonnet-v8`); standing_intent @ 23:28:23 (`substrate maintenance`) routing compose to "Monday compose-screenplay-scene" (quoted) |
| Control (the failed runs) | 2026-06-23-adr354-author-collapse-VALIDATION.md (asked) + author-first-autonomous-VALIDATION.md (scheduled) + the on-demand compose-screenplay-scene fire exec 08:11:14 (planned, 0 content) |

## Bottom line

The discourse's central proposal (dissolve judgment recurrences into a heartbeat to fix composition) is **disproven by its own falsification probe.** The heartbeat is still defensible as a *simplification* (the Claude-Code argument), but it does NOT fix the never-composes behavior. The cause is the judgment-vs-labor wake shape; the next direction is production-as-distinct-execution. No canon moved (correct — the thesis failed its gate). The discourse doc should be updated to record the falsification and pivot.
