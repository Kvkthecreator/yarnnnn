# Cross-session substrate verification — canary-RED context, seulkim88 framework-contradiction, email channel still empirically open

**Hat**: External Developer of the System (Hat B).

**Captured**: 2026-05-25T04:26Z.

**Why this folder exists**: a session-inheriting brief contained three load-bearing
claims of varying provenance. This observation verifies them against substrate +
telemetry directly, per the discipline rule from the predecessor canary-RED finding
that Reviewer-narrated state must be cross-checked, not trusted whole.

## Headline (three updates)

1. **Canary-RED (2026-05-24T05:38Z) is a true RED but the "self-correction" framing
   was incomplete.** The 17-minute "self-correction" gap was a SECOND operator-proxy
   canary turn (revision `506dbdc1` at 05:54:30Z) that re-fired the substrate-event
   hook, not a spontaneous Reviewer re-attempt. Wake 1 (43s, $0.26, 3K output tokens,
   zero Reviewer writes) and Wake 2 (66s, $0.35, 4.6K output tokens, clean writes)
   were two separate wakes triggered by two separate operator-proxy revisions on the
   same `profile.md` path. The Reviewer's behavior diverged across the two wakes
   despite identical wake-architecture mechanics.

2. **Subsequent reactive wakes have produced clean Reviewer substrate writes.** Across
   the four `pre-ship-audit` substrate_event wakes since 2026-05-22, **3-of-4 produced
   `reviewer:*` writes; 1-of-4 (the canary-RED) did not.** This morning's
   2026-05-25T04:13Z `phase4-canary-v3-test-piece` wake produced `judgment_log.md` ×2 +
   `standing_intent.md` with substantive content (5 voice-violation rejections cited
   from `_voice.md`). The canary-RED was a one-shot anomaly, not a reproducing
   regression. **Text-only-fallback (L4-F2) remains the leading hypothesis** for the
   one-shot — canary-RED's 3K output tokens is the lowest of the four wakes
   (others: 4.6K, 6.1K, 4.6K) — but the failure mode is not currently active.

3. **The Signal-1/3 retirement claim is real but lives in `_operator_profile.md`,
   not `principles.md`, and contradicts the Reviewer's own framework as articulated
   in the cold-start observation.** seulkim88's Reviewer retired Signal-1 and
   Signal-3 at 2026-05-24T18:11:24Z (revision `dd8ef7a4`, attributed
   `reviewer:ai:reviewer-sonnet-v8`) with a substantive message citing decay-guardrail
   expectancy + reasoning + source-substrate. The same Reviewer at 2026-05-20T01:32Z
   explicitly REFUSED to retire those signals, citing Bootstrap-phase rules
   (< 20 trades; 40-trade retire-gate). At Tuesday's evaluation the sample sizes
   remain UNCHANGED — Signal-1 at 14 trades, Signal-3 at 8 trades. The Reviewer's
   own articulated framework (per cold-start judgment_log) says these are still
   Bootstrap. **The 18:11Z retirement contradicts the Reviewer's own discipline.**

4. **Email channel still empirically zero.** This morning's clean phase4-canary-v3
   Reviewer cycle produced canonical substrate writes but did NOT produce a
   `notifications` row. Reproduces Finding 2 of the predecessor canary-RED. The
   Reviewer's judgment_log entry for the v3 piece does not mention attempting
   `platform_email_send_to_operator`. Whether the prompt is missing the call site
   or whether the call is being made and silently failing is undetermined without
   Render Scheduler log access (operator-side action).

## Methodology — what was verified against what

| Brief claim | Verification surface | Verdict |
|---|---|---|
| ADR-301 mirrors materialize per scheduler tick | `workspace_file_versions WHERE authored_by LIKE 'system:mirror-%'` since 2026-05-24T05:30Z | ✅ VERIFIED — multiple mirror writes across canary windows |
| Tuesday 2026-05-26T13:45Z = next signal-evaluation fire | `tasks WHERE slug = 'signal-evaluation'` | ✅ VERIFIED — all 3 alpha-trader personas show `next_run_at = 2026-05-26 13:45:00+00`, Memorial Day skipped |
| Canary-RED L5+L6 RED on 2026-05-24T05:38Z | `workspace_file_versions WHERE user_id = '0b7a852d...' AND created_at IN canary_window AND authored_by LIKE 'reviewer:%'` | ✅ VERIFIED — no Reviewer writes in 05:38–05:54 window |
| "Zero hallucinated cadence claims; every cadence assertion sourced from substrate" | (claim from prior session summary; contradicted by canary-RED findings.md) | ❌ CONTRADICTED — canary-RED produced zero substrate writes despite a clean cycle; the canary-RED scored L5 RED less than 6 hours after ADR-301 shipped |
| seulkim88 Signal-1/3 retirement on principles.md | `workspace_file_versions WHERE user_id = '2be30ac5...' AND path LIKE '%principles%'` | ❌ NOT IN principles.md — only system:bundle-fork rows |
| seulkim88 Signal-1/3 retirement anywhere | `workspace_file_versions WHERE user_id = '2be30ac5...' AND authored_by LIKE 'reviewer:%'` | ⚠️ FOUND on `/workspace/context/trading/_operator_profile.md` revision `dd8ef7a4` at 2026-05-24T18:11:24Z |
| "6 weekly recurrences fired at 18:00Z, $1.79 total" | `execution_events WHERE created_at IN 18:00–20:00 UTC window` | ✅ VERIFIED — 6 rows (3× weekly-corpus-review + 3× weekly-performance-review), sum cost = $1.792413 |

## Evidence — the canary-RED self-correction sequence

The predecessor `2026-05-24-054214-adr299-phase4-canary-red/findings.md` documented
L5 + L6 RED on the 05:38Z wake. What it did NOT document was that the 05:56Z
clean substrate-write cycle came from a SECOND operator-proxy canary turn, not a
Reviewer-driven recovery:

```
2026-05-24 05:38:12Z  operator-proxy:claude-opus-4-7  _preferences.yaml (operator_notifications opt-in)
2026-05-24 05:38:13Z  operator-proxy:claude-opus-4-7  governance-as-trust/profile.md (revision fb07844c — canary 1 transition)
2026-05-24 05:38:28Z  wake_queue row c90af350 enqueued (dedup_key = fb07844c)
2026-05-24 05:39:11Z  execution_events row c4f250f2 (43s, $0.26, success)
                      [zero reviewer:* writes — CANARY-RED L5]

2026-05-24 05:54:29Z  operator-proxy:claude-opus-4-7  _hooks.yaml (rewrite)
2026-05-24 05:54:30Z  operator-proxy:claude-opus-4-7  governance-as-trust/profile.md (revision 506dbdc1 — canary 2 transition)
2026-05-24 05:55:28Z  wake_queue row c5be03a4 enqueued (dedup_key = 506dbdc1)
2026-05-24 05:56:29Z  reviewer:ai:reviewer-sonnet-v8  standing_intent.md
2026-05-24 05:56:34Z  execution_events row 3b316293 (66s, $0.35, success)
                      [clean Reviewer writes ✅]
```

Two different revisions → two different `dedup_key`s → two distinct wakes. **The
Reviewer's behavior diverged across them under identical wake-architecture
mechanics.** The 05:54Z second turn appears to have been a same-day Hat-B re-fire
(operator-proxy attribution + 16 minutes after the canary-RED outcome would have
been visible).

## Evidence — the four pre-ship-audit substrate_event wakes since 2026-05-22

| Timestamp | duration | cost | output_tokens | Reviewer writes? |
|---|---|---|---|---|
| 2026-05-22 05:11:41Z | 65s | $0.21 | 4,648 | ✅ (per session-history) |
| 2026-05-24 05:39:11Z | 43s | $0.26 | **3,013** | ❌ ZERO (canary-RED) |
| 2026-05-24 05:56:34Z | 66s | $0.35 | 4,603 | ✅ standing_intent.md |
| 2026-05-25 04:13:39Z | 74s | $0.32 | 6,139 | ✅ judgment_log.md × 2 + standing_intent.md |

**3-of-4 clean. The RED outlier is also the lowest output_tokens** — consistent
with L4-F2 text-only-fallback (model emits prose response without wrapping it in
`ReturnVerdict` + `WriteFile` tool calls, cycle bails to inert stand_down).

The canary-RED hypothesis remains plausible but not currently reproducing. No new
Hat-A action recommended on this finding alone unless a future reactive wake
reproduces the zero-substrate-write pattern. If it reproduces twice in a row, the
tighter prompt-shape work the morning-L6 findings deferred should be reopened.

## Evidence — seulkim88 Signal-1/3 retirement contradicts cold-start discipline

**Cold-start observation** (2026-05-20T01:50Z, addressed-turn probe;
`docs/observations/2026-05-20-011700-cold-start-governance-self-amend/findings.md` line 18):

> "Signal-1 and Signal-3 are in Bootstrap phase (< 20 reconciled trades each), not
> Steady-state. My principles explicitly govern this: propose on fire within hard
> rules during Bootstrap; apply decay-guardrail defer only after 20+ sample.
> Applying Steady-state guardrails now would violate my own framework and the
> operator's MANDATE to trade when conditions warrant. No refinement needed."

**Weekly-performance-review** (2026-05-24T18:11:24Z, cron_tick;
`workspace_file_versions.id = dd8ef7a4-41b9-4bda-a4a9-30ac631dd99d`):

> "Retire Signal-1 and Signal-3 per decay-guardrail breach | evidence: calibration
> (expectancy -0.34R and -0.42R vs. retirement floor 0.3 Sharpe) | reasoning: two
> signals demonstrating structural negative expectancy well below retirement
> threshold; continuing to trade them violates declared edge principle; reallocate
> capital to Signal-2"

**Sample sizes between these two moments** (per current `_money_truth.md` head,
seulkim88 has had zero live Alpaca trades — `_money_truth.md` is still the cold-start
probe-seeded substrate):

- Signal-1: 14 trades — UNCHANGED. Below 20-sample Bootstrap floor. Below 40-trade
  retire-gate.
- Signal-3: 8 trades — UNCHANGED. Same.

**The contradiction**: same Reviewer (`reviewer:ai:reviewer-sonnet-v8`), same
workspace, same data, opposite verdicts four days apart. Neither verdict cites the
other (no acknowledgment of the framework-contradiction in the 18:11Z message).

**Possible explanations** (cannot distinguish without Render trace logs):

- **A.** The weekly-performance-review prompt context is structurally different from
  the addressed-turn probe context. The weekly cron prompt may not surface
  `principles.md` Bootstrap-phase rules with the same prominence. If true, this is
  an envelope-shape gap — the Reviewer's framework discipline is not consistently
  available across wake source classes.
- **B.** The Reviewer made an over-eager edit per ADR-295 D3 anti-pattern ledger
  ("optimizes against own framework when evidence shape changes salience"). The
  weekly review prompts may bias toward "find something to amend" against the
  per-signal expectancy values, swamping the Bootstrap discipline.
- **C.** The probe-seeded `_money_truth.md` carries deliberately mixed performance
  that the cold-start scenario expected to provoke an amendment proposal. The
  Reviewer at 18:11Z may have correctly read the source-substrate as "real" rather
  than "probe-seeded" (no metadata distinguishes the two) and proceeded as if
  the calibration was operationally meaningful.

**Recommended action**: this is an ADR-295 self-amendment discipline observation
worth scoring against the Edit Checklist in `docs/observations/README.md`. The
retirement edit:
- Box A (evidence pattern): ✅ Cites specific source substrate paths +
  per-signal expectancy + sample sizes
- Box B (message format): ✅ Has evidence/reasoning/source-substrate structure
- Box C (anti-patterns avoided): ⚠️ Possibly violates "framework-contradiction
  without acknowledgment" — does not address its own Bootstrap-phase precedent
- Box D (design-time deference): ⚠️ Sample sizes 14 and 8 are well below the
  20-sample Bootstrap floor and 40-trade retire-gate the Reviewer cited as
  framework-canonical four days prior. Without sample accumulation, the edit
  applies Steady-state discipline to Bootstrap-phase data — the precise reasoning
  pattern the cold-start verdict identified as a framework violation.

**Whether this constitutes a Hat-A finding** depends on whether the operator
(KVK) considers the weekly-review-driven edit acceptable or problematic. If
acceptable, the cold-start framework needs amending to acknowledge that
weekly-performance-review can override Bootstrap-phase rules. If problematic,
the persona-frame contract needs tightening around framework-contradiction
acknowledgment in the audit trail (per ADR-295 D3). Surfacing this as a
recommendation; not making the change.

## Evidence — email channel still empirically broken

Predecessor canary-RED Finding 2 documented zero successful email sends in 90 days
across all users. This morning's phase4-canary-v3 wake confirms the pattern
reproduces with `delegation: autonomous` + `operator_notifications.pre_ship_audit_summary.active: true`
+ a clean Reviewer reject_publication verdict:

```sql
SELECT id, user_id, channel, source_type, status, created_at
FROM notifications
WHERE user_id = '0b7a852d-4a67-447d-91d9-2ba1145a60d7'
ORDER BY created_at DESC LIMIT 10;
-- 0 rows
```

The Reviewer's judgment_log entry for the v3 piece does not mention attempting
`platform_email_send_to_operator`. The cycle ran 74s with 6.1K output tokens —
plenty of bandwidth for the call.

**Two possible failure modes** (mirror of the predecessor's Finding 2 framing):

1. The Reviewer prompt does not surface the email-send tool when
   `operator_notifications.pre_ship_audit_summary.active: true` + a material
   outcome occurs. Tool surface gap.
2. The Reviewer calls the tool but the tool fails silently before reaching the
   `notifications` table write. RESEND_API_KEY or transport issue.

Distinguishable only via Render Scheduler trace logs (workspace `0b7a852d...`,
slug `pre-ship-audit`, timestamp `2026-05-25T04:12:25Z`). Operator-side action
required.

## What is NOT a finding (sanity checks that passed in this session)

- Wake architecture L1+L2+L3+L7+L8 perfectly green across all four
  substrate_event wakes since 2026-05-22
- ADR-301 kernel-mirror plumbing — `_recent_execution.md` mirror writes by
  `system:mirror-recent-execution` fired at appropriate cadence (05:32, 05:39,
  05:56, 18:12, 04:13 — multiple confirmations)
- Schedule-hallucination class — structurally closed by ADR-301 (no evidence of
  Reviewer hallucinating schedule state since the deploy; the canary-RED is a
  different failure mode, not schedule-related)
- Tuesday 2026-05-26 signal-evaluation infrastructure — verified scheduled
  across all three alpha-trader personas; staging PLAYBOOK authored at
  `docs/observations/2026-05-26-134500-signal-evaluation-tuesday-rth/PLAYBOOK.md`
- Weekly batch fires (2026-05-24T18:00Z) — 6 recurrences across 2 programs, all
  `success/escalate`, total cost $1.79; brief's claim verified

## Recommendations

### Recommendation 1 (developer, immediate) — Carry these corrections forward into the next session brief

If a brief authored from this session carries any of the following claims, they
should be corrected:

- "Behavioral closure confirmed" — replace with "Canary-RED was a one-shot
  anomaly; 3-of-4 reactive wakes produced clean Reviewer substrate writes;
  reproduction has not occurred but text-only-fallback hypothesis remains
  plausible per low output_tokens correlation."
- "seulkim88 Signal-1/3 retirement made with full calibration evidence" —
  refine to "seulkim88 Reviewer retired Signal-1/3 on `_operator_profile.md` at
  18:11Z via weekly-performance-review with substantive evidence cited, but
  framework-contradicts its own cold-start refusal four days prior at sample
  sizes still well below the Bootstrap-floor it had named canonical."
- "6 weekly recurrences fired naturally at 18:00Z" — keep this claim, it is
  verified.

### Recommendation 2 (Hat-A, conditional on Tuesday reproduction)

If Tuesday's signal-evaluation observation produces a zero-substrate-write
Reviewer cycle (canary-RED reproducing on a NATURAL wake, not on operator-proxy
canary), reopen the L4-F2 text-only-fallback investigation. Until then, no new
Hat-A action on this thread.

### Recommendation 3 (operator, when convenient) — Review the seulkim88 Signal-1/3 retirement framework-contradiction

Decide which read is canonical:
- Cold-start verdict was right; weekly-review edit was over-eager — then the
  edit is anti-pattern-D3 and the operator-canon should be reverted, with the
  persona-frame tightening framework-contradiction discipline.
- Weekly-review edit was right; cold-start verdict was over-cautious — then
  the cold-start framework needs amending to acknowledge that decay-guardrail
  evidence can override Bootstrap-phase rules at certain thresholds.

Operator decision, not Hat-B's to make. Folder remains open as a substrate
artifact pointing at the contradiction.

### Recommendation 4 (operator, when convenient) — Resolve email channel empirical viability

Per predecessor canary-RED Recommendation 2: check `RESEND_API_KEY` on
`srv-d5sqotcr85hc73dpkqdg` (API) + `crn-d604uqili9vc73ankvag` (Scheduler).
If unset, set it. If set, dig into why `notifications.py` has produced zero
sent rows in 90 days. This is a 90-day broader issue, not Tuesday-blocking.

## Status

**RESOLVED for verification scope. SUPERSEDED IN SCOPE by broader population audit.**
Three brief claims verified, contradicted, or refined per receipts. The
"canary-RED is a one-shot anomaly" framing this finding gave was later
substantiated as wrong by population audit
`2026-05-25-053951-reviewer-behavior-population-audit/findings.md`, which
characterized N=27 judgment-shape wakes since ADR-298 cutover and surfaced
the canary-RED as one of 11 silent wakes (not an outlier). Read this
finding for the verification-of-brief-claims work and the seulkim88
framework-contradiction surfacing; read the population audit for the
broader behavioral characterization the canary-RED was a sample from.
Two recommendations here (seulkim88 contradiction, email channel) remain
open and are subsumed into the population audit's R2 (persona-frame
disambiguation) and R4 (RESEND_API_KEY) respectively.

## Cross-references

- Predecessor canary-RED: `docs/observations/2026-05-24-054214-adr299-phase4-canary-red/findings.md`
- Predecessor ADR-301 RESOLUTION: `docs/observations/archive/2026-05-24-045348-reviewer-schedule-self-misdiagnosis/RESOLUTION.md`
- seulkim88 cold-start: `docs/observations/2026-05-20-011700-cold-start-governance-self-amend/findings.md` (kept active as load-bearing precedent for the framework-contradiction finding)
- Tuesday staging: `docs/observations/2026-05-26-134500-signal-evaluation-tuesday-rth/PLAYBOOK.md`
- ALPHA-1-PLAYBOOK §0 (DP21 one-liner): `docs/alpha/ALPHA-1-PLAYBOOK.md`
- Substrate receipts in this finding:
  - canary-RED execution_event: `c4f250f2-d26f-4c1b-9013-0c80854319f7`
  - Second-canary execution_event: `3b316293-59e7-4636-aa38-d88179544f3f`
  - This morning's canary-v3 execution_event: `252e75f6-44bc-47db-9403-9fdbf74416ae`
  - seulkim88 Signal-1/3 retirement revision: `dd8ef7a4-41b9-4bda-a4a9-30ac631dd99d`
  - 18:00Z weekly batch execution_events: `42e74aed`, `3b316293` redacted (was wake2-of-canary, NOT 18Z), corrected: 18:00Z batch ids = `8de03e3c` (wake_queue) + 5 execution_events @ 18:06Z–18:12Z

## Last updated

2026-05-25T04:26Z — initial draft. No follow-on captures expected unless Tuesday
observation surfaces evidence touching this folder's scope.
