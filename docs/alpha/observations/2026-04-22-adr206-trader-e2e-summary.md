# E2E Run Summary — alpha-trader post-ADR-206 validation

**Date**: 2026-04-22
**Duration**: ~40 minutes (substrate checks + 2 chat turns + DB inspection)
**Result**: Architectural validation succeeded with 4 real bugs surfaced + 1 unresolved decision flagged

## What the E2E proved

ADR-205 + ADR-206 are directionally sound:

- **Workspace_init is clean post-purge.** Fresh login produces exactly the
  ADR-206 substrate shape: 1 YARNNN agent + `_shared/*` + `memory/*` +
  `review/*` skeletons. 0 tasks. Zero pre-scaffolded domain content.
- **YARNNN's first-turn posture is operation-first** in prod. The Phase 2
  prompt rewrite propagated. YARNNN greets with "What operation do you
  want to run?" not "Tell me about yourself." (Obs 02)
- **Task scaffolding works.** ManageTask primitive + the full ADR-149 +
  ADR-181 task substrate (TASK, DELIVERABLE, awareness, feedback,
  memory/steering) materializes correctly. (Obs 05)
- **Authored-team moat is working.** YARNNN authored a user Agent
  (`trading-operator`, role=analyst, origin=user_configured) through
  conversation. Exactly what ADR-189 predicted. (Implicit in Obs 03)
- **Compact index post-ADR-206 was useful to YARNNN.** YARNNN cited
  "trading platform connected" and "one agent set up" verbatim in the
  first turn, pulling from the rewritten three-section compact index.

## What the E2E broke

- **Obs 01**: verify.py invariants in personas.yaml are pre-ADR-206.
  4/23 checks pass. Harness and substrate drifted apart.
- **Obs 03**: ADR-206 specifies domain-scoped Intent artifacts
  (`_operator_profile.md`, `_risk.md`) but **no primitive writes them**.
  YARNNN falls back to AGENT.md.
- **Obs 04**: `review/principles.md` not customized from declared
  capital-EV framework. Same primitive-gap root cause as Obs 03.
- **Obs 05 Bug 1**: Duplicate task created (`track-universe-2`).
  Idempotence gap in ManageTask.
- **Obs 05 Bug 2**: YARNNN made a hallucinated WebSearch call to
  `https://raw.githubusercontent.com/`. Prompt calibration issue.
- **Obs 05 Bug 3**: `SearchEntities(scope="agent")` returned 0 for an
  agent that exists. Search index freshness bug.
- **Obs 06**: YARNNN delegated domain-Intent authorship via task
  `trigger_context.md` instead of writing directly. Unresolved
  architectural question — who authors Intent files, in what cases?

## Proposed next actions

Priority-ordered:

1. **Fix the substrate-harness coupling** (Obs 01). Update
   `personas.yaml` `expected` blocks to ADR-206 invariants. Add to
   CLAUDE.md: every ADR that mutates `workspace_init` also mutates
   `personas.yaml` in the same commit.
2. **Draft ADR-207** — Intent-layer authorship chain. Resolve Obs 03 + 04
   + 06 together. Propose:
   - Add `UpdateContext` targets for `operator_profile`, `risk`,
     `review_principles`.
   - Specify authorship chain per file (operator-direct vs. YARNNN-inferred
     vs. agent-delegated).
   - Update `ManageContextModal` to cover `_risk.md` + `principles.md`.
3. **Fix Obs 05 Bug 1** (idempotent ManageTask create). Small patch;
   check for existing by title+agent_slug before creating.
4. **Fix Obs 05 Bug 3** (SearchEntities freshness). Add sync index rebuild
   on ManageAgent(create), or fallback-to-ListEntities on zero results.
5. **Obs 05 Bug 2** (WebSearch hallucination). Prompt-level guidance
   tightening.
6. Run a second E2E once (1)-(4) land to validate fixes.

## Cost signals

Two chat turns consumed:
- Turn 1 ("hi"): 28,344 cache_creation + 583 fresh input + 78 output.
- Turn 2 (operation declaration): ~3000 input + ~900 output + 5 tool rounds
  (UpdateContext × 2, ManageAgent, platform_trading_get_account,
  list_integrations × 2).
- Turn 3 (finish scaffold): 10+ tool rounds. Context caching kept input
  cost down; output tokens dominated.

No runaway spend. Pipeline is cost-healthy even across heavy scaffold turns.

## Simons discipline compliance

YARNNN's voice stayed in Simons register throughout. No "feel", "conviction",
"breakout setup" language. Responses cited signal names, sizing math, ATR
stops, VIX scalars. Excellent prompt calibration on that front. The persona
voice contract held.

## Not exercised this run (for next E2E)

- First task actual dispatch + output generation (track-universe's run
  is stuck in `generating` — need to investigate separately).
- Reviewer evaluation of a real proposal (no proposal fired yet).
- Cockpit Queue + approve/reject flow (no proposal).
- Money-truth reconciliation (no trades yet).
- CreateTaskModal UI exercise (only backend path via chat).
- ManageContextModal UI exercise (only endpoints via chat).
- `/settings/system` diagnostic view (no back-office tasks materialized
  yet — they materialize on trigger per ADR-206).

## E2E verdict

**ADR-205 + ADR-206 architecture is directionally correct. Substrate
collapse worked cleanly. Operation-first prompt landed. Authored-team
moat is operative. But three primitive-layer gaps (Intent-file writes,
search-index freshness, idempotence) need follow-up commits before
a second E2E. ADR-207 (Intent authorship chain) is the most important
of the three.**

## Update (scheduled wakeup fired 5.5 min after trigger) — Obs 07 added

The `track-universe` task trigger hung silently. `agent_runs` row sits
at `status="generating"` with 0 bytes of draft content, no activity_log
entry, no error propagation. **This is the most severe finding of the
whole E2E** — the operation loop can't close because the pipeline fails
on first real dispatch and doesn't surface the failure.

Revised priority (replaces earlier action list):

1. **Debug Obs 07 task-pipeline silent hang.** Check Render logs,
   inspect TASK.md consistency, read `task_pipeline.py execute_task()`
   for missing-context and unhandled-error paths. Add a watchdog
   that auto-fails `generating` runs older than 5 minutes.
2. **Fix `personas.yaml` invariants** (Obs 01) — small patch, unblocks
   harness-based validation.
3. **Draft ADR-207** — Intent-layer authorship chain (Obs 03+04+06).
4. **Fix ManageTask idempotence** (Obs 05-1) + SearchEntities freshness
   (Obs 05-3) + WebSearch prompt calibration (Obs 05-2).
5. Re-run E2E once (1) is resolved.

**Without Obs 07 fixed, no operator can run the loop. This is the
blocker.**
