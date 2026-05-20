# Playbook — yarnnn-author Autonomy Demonstration (T0 baseline)

> **The first long-running autonomy demonstration under ADR-294 observation discipline.** Marks the structural shift from operator-proxy-driven scenarios to *operator-absent observation* of natural system behavior.

## North Star

YARNNN is becoming a fully autonomous Agent OS. The two-workspace north star (per the 2026-05-20 reframe):

- Demonstrate the Reviewer + System Agent + Orchestration substrate running end-to-end **without operator-on-behalf interjection** for an extended period
- Capture what the system did on its own — substrate writes, judgment_log entries, recurrence fires, principled refusals, principled amendments
- Use the captures to verify canon-behavior alignment (or surface drift)

This T0 observation is the **before-snapshot** of yarnnn-author's first autonomy demonstration window. Subsequent observations (T+24h, T+48h, T+7d) will capture what the system did between.

## Why yarnnn-author (and not alpha-trader)

The capital-lane (alpha-trader, kvk) end-to-end demonstration is structurally expensive in a single session: US market hours, real signal match required, Alpaca submission infrastructure with multiple validation cascades, real outcome reconciliation. Days to weeks of real time.

The substrate-continuity archetype (alpha-author, yarnnn-author) is structurally tractable:
- No platform dependency (alpha-author bundle ships `platform_kind: none` per ADR-283 D7)
- Outcome timeline operator-driven, not market-driven
- Reviewer wakes are triggered by substrate state (draft `ready_for_review` reactive trigger) + judgment-mode recurrences (corpus-coherence-check Mon/Thu, revision-audit Fri, outcome-reconciliation daily)
- End-to-end loop: operator drafts → marks ready_for_review → Reviewer audits → verdict lands in judgment_log + standing_intent → outcome-reconciliation rolls up

**Same architectural thesis, faster-feedback archetype.** Validating autonomy on yarnnn-author is validating the autonomy story; the capital-lane variant becomes second-pass once the substrate-continuity story holds.

## T0 substrate state

- Persona: yarnnn-author (`user_id=0b7a852d-...`, program=alpha-author)
- Activation: re-activated via `activate_persona.py` at 2026-05-20T03:08Z (post-ADR-295 Phase A canon ship)
- Bundle update: applied via `apply_substrate_update(scope="bundle")` per ADR-292 — propagated 20 file updates
- Principles hardening: `review/principles.md` force-pushed via `_force_push_principles.py` to install the ADR-295 D6 Self-Improvement Posture content (18,575 chars). ADR-292 gap workaround noted; ADR-292 gap finding lives at `docs/observations/2026-05-20-034317-adr-292-gap-finding.md` (sibling observation).
- AUTONOMY: flipped from bundle-default `manual` to `autonomous` at 2026-05-20T03:30Z. Reviewer approve verdicts on pre-ship-audits now bind (or are the substrate-of-record, since alpha-author has no actual external publication step).
- First piece seeded: `/workspace/context/authored/governance-as-trust/{profile.md,content.md}` with `status: ready_for_review`. Real founder-voice essay (~700 words) on the lock-set discipline. Substrate seeded so `pre-ship-audit` (reactive trigger) has something to fire on.
- Reviewer state at T0: workspace has prior Reviewer-authored substrate (`review/standing_intent.md`, `review/judgment_log.md`, `review/calibration.md`) from 2026-05-18 first-activation. T0 captures what the Reviewer left behind.

## What we're watching for (during the elapsed window)

**Reactive wake on the seeded piece:**
- Bundle's `pre-ship-audit` recurrence is reactive (`schedule: null`). Trigger condition: "operator marks a draft `ready_for_review`."
- Does the system detect the seeded `status: ready_for_review` and fire pre-ship-audit?
  - If yes: Reviewer reads `_voice.md` + `_editorial.md` + the seeded draft, produces verdict (approve/defer/reject), writes judgment_log + standing_intent.
  - If no: surfaces a system bug — the reactive trigger isn't detecting substrate-state changes for this seeded path. Hat-A fix.

**Scheduled recurrence fires (without operator-proxy interjection):**
- `corpus-coherence-check` at Mon + Thu 12:00 UTC — periodic cross-corpus pass
- `revision-audit` at Fri 22:00 UTC — long-arc draft revision audit
- `outcome-reconciliation` daily at 05:00 UTC — folds the day's events into `_signal.md`

Today is 2026-05-20 (Wednesday UTC). Next scheduled fires within 48h:
- Thu 2026-05-21 05:00 UTC — outcome-reconciliation
- Thu 2026-05-21 12:00 UTC — corpus-coherence-check
- Fri 2026-05-22 05:00 UTC — outcome-reconciliation
- Fri 2026-05-22 22:00 UTC — revision-audit

That's **3-4 natural recurrence fires** plus the pre-ship-audit reactive fire (if it triggers correctly).

**Self-amendment behavior under autonomous (per ADR-295 D1):**
- Will the Reviewer trigger any operator-canon edits on its own initiative based on accumulated evidence?
- Likely no — yarnnn-author has minimal accumulated audit history. ADR-295 D1 alpha-author thresholds (20 published pieces with audience-response data, 8 distinct audits / 2 weeks persistence) are not yet reachable. Expected behavior: defer + write standing_intent.md naming what's being watched for.
- A self-amendment IF it occurs would be highly informative — evaluated against ADR-295 D1-D4 Edit Checklist.

**Substrate-write attribution:**
- All Reviewer writes should land with `authored_by: reviewer:ai:reviewer-sonnet-v8`.
- No `operator-proxy:*` writes during the window — this IS the discipline test for "operator-absent observation."

## Capture cadence

- T0 (now, 2026-05-20T03:43Z): full baseline snapshot. 8 canonical artifacts produced.
- T+24h (2026-05-21 ~03:43 UTC): mid-window snapshot. Diff against T0.
- T+48h (2026-05-22 ~03:43 UTC): end-window snapshot. Final diff. Findings authored.
- Optional T+7d (2026-05-27 ~03:43 UTC): extended observation if the 48h window surfaced incomplete behavior.

The developer (KVK or Claude) **does NOT engage with the workspace between snapshots** other than to capture. No chat messages. No proxy turns. No nudges.

## What success looks like

A clean autonomy demonstration produces (at minimum):
1. The Reviewer fires at least one wake during the window (reactive or scheduled).
2. At least one judgment-mode wake produces a verdict + standing_intent write.
3. Revision chain shows `reviewer:*` attribution on relevant substrate paths.
4. No discipline failures (no anti-pattern hits per ADR-295 D3 Edit Checklist).
5. No system errors blocking the autonomous loop (scheduler runs, dispatcher routes, Reviewer wakes complete in budget).

## What partial / interesting findings would look like

- Reviewer fires pre-ship-audit but defers — surfaces what the Reviewer flagged (anti-slop hits, voice mismatch, continuity gaps) on a real founder-prose draft.
- Reviewer fires pre-ship-audit and approves — validates that the bundle's audit logic produces production-readiness verdicts under autonomous.
- Reviewer self-amends operator-canon (low likelihood given thresholds aren't met) — examined against ADR-295 D1-D4 Edit Checklist.
- Scheduled recurrence fires (corpus-coherence-check, revision-audit, outcome-reconciliation) — captures what the multi-recurrence loop produces.
- Wake fails (round-budget exhausted, infrastructure error, missing substrate) — surfaces real-world bugs analogous to what the Phase D probe of ADR-295 surfaced.

## Findings

`findings.md` is left as a stub in this T0 folder per ADR-294 D7. The actual findings live in the T+24h / T+48h follow-up observations after substantive elapsed time has passed.

## Cross-reference

- ADR-283 — alpha-author bundle (the program this persona runs)
- ADR-294 — operator-proxy + observation discipline (the framework this observation runs under)
- ADR-295 — Reviewer self-amendment discipline (the canon the demonstration tests)
- FOUNDATIONS v8.6 §Scope — the system-vs-developer-surface boundary (the discipline that makes "operator-absent observation" meaningful)
- 2026-05-20-022520-post-refusal-self-amendment-probe — the discipline-failure observation that motivated the shift to autonomy-demonstration over operator-proxy-driven probing
