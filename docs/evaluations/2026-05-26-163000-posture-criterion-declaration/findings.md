# Posture-Criterion Declaration + Pre-Implementation Baseline (first evaluation under criterion-declaration discipline)

**Captured**: 2026-05-26T16:30Z. Hat-B evaluation.

**Shape**: criterion-declaration + pre-implementation baseline measurement. **First evaluation under the criterion-declaration discipline codified by the 2026-05-26 rename** (`docs/observations/` → `docs/evaluations/`, commit `4f1f128`). No new wake population has been captured since the predecessor population audit; what changes here is what we're measuring against.

**Why this folder, why now**: per the criterion-declaration discipline (`docs/evaluations/README.md` §"The criterion-declaration discipline"), every load-bearing evaluation must declare the canon clause it measures against BEFORE reporting adherence. The predecessor population audit (`2026-05-25-053951`) reported ~48% adherence against a criterion that was over-broad. ADR-302 + ADR-303 (commit `23b59e7`, refined in `6a3161d`) decompose the criterion into per-cell contracts. This evaluation captures the new criterion + a pre-implementation baseline measurement under it, so the post-implementation re-run has a clean anchor to delta against.

---

## §1 Criterion declaration

### §1.1 Canon clause being measured against

Primary: **ADR-303 D1 — Five posture cells, axiomatically derived.** The Reviewer's possible exit shapes from a judgment cycle, exhaustively enumerated as P1 fired-correctly / P2 decided-nothing-material / P3 tried-was-gated / P4 budget-exhausted / P5 confused.

Secondary: **ADR-303 D2 — Per-cell substrate side-effect contract.** Each cell MUST produce at minimum one operator-readable substrate artifact, slot-filled differently per cell, with attribution discipline distinguishing model-authored (`reviewer:...`) from dispatcher-synthesized (`dispatcher:silent_exit_fallback`, `dispatcher:reviewer_action_blocked`).

Predecessor canon being **superseded** by this criterion: persona-frame `_PERSONA_FRAME` §392-§411 standing_intent contract — "Reactive recurrence fires + addressed turns + heartbeats: every cycle produces a standing_intent.md write." This was the criterion the predecessor audit measured against and is what ADR-303 D1 ("the persona-frame's standing_intent contract is one-size-fits-all across what are actually distinct cognitive postures") explicitly amends.

### §1.2 Operationalization — how each cell maps to substrate signals

| Cell | Detection rule | Substrate query target |
|---|---|---|
| **P1 (fired-correctly)** | `workspace_file_versions` row with `path='/workspace/review/judgment_log.md'` and `authored_by LIKE 'reviewer:%'` within ±15min of `execution_events` row. | judgment_log.md — model authored verdict-of-record |
| **P2 (decided-nothing-material)** | `workspace_file_versions` row with `path='/workspace/review/standing_intent.md'` and `authored_by LIKE 'reviewer:%'` AND NO P1 detection. | standing_intent.md — model authored intent without verdict |
| **P3 (tried-was-gated)** | (Post-ADR-303 implementation) narrative entry with event-kind `reviewer_action_blocked` AND `authored_by LIKE 'dispatcher:%'`. Render log proxy: `WARNING:agents.reviewer_agent:[REVIEWER] tool=... success=False` cluster preceding silent exit. | session_messages event-kind narrative + Render log SURFACE_FAILURE_REASONS pattern |
| **P4 (budget-exhausted)** | (Post-ADR-303 implementation) `workspace_file_versions` row with `path='/workspace/review/standing_intent.md'` AND `authored_by='dispatcher:silent_exit_fallback'` AND exit_class metadata = `budget_exhausted`. Render log proxy: `WARNING:agents.reviewer_agent:[REVIEWER] no ReturnVerdict after N rounds`. | standing_intent.md authored_by dispatcher with exit metadata |
| **P5 (confused)** | (Post-ADR-303 implementation) `authored_by='dispatcher:silent_exit_fallback'` AND exit_class = `text_only_mid_loop` (not budget-exhausted). Render log proxy: `WARNING:agents.reviewer_agent:[REVIEWER] text-only response round N` where N < max_rounds. | standing_intent.md authored_by dispatcher with mid-loop exit metadata |

**Key shape**: pre-implementation, cells P3/P4/P5 collapse into a single observable class — "no reviewer-attributed substrate" — because the dispatcher-write contracts ADR-303 D2 specifies do not yet exist. The pre-implementation baseline (§3) measures that collapsed class. The post-implementation re-run will be able to distinguish P3/P4/P5 because the dispatcher will author the substrate that disambiguates them.

### §1.3 Expected posture per cell

Per ADR-303 D2 + ADR-302 (which addresses the canon contradiction driving P3 frequency):

| Cell | Expected frequency post-implementation | Expected substrate side-effect |
|---|---|---|
| **P1** | The "happy path" — exact fraction depends on substrate-change frequency per slug. No specific target. | judgment_log.md entry + per-action narrative |
| **P2** | Material fraction expected — selective Reviewer correctly identifies "nothing warrants action" on many wakes. No specific target. | standing_intent.md revision (`reviewer:` authored) recording the looked-and-decided reasoning |
| **P3** | **Should approach zero post-ADR-302** because the canon contradiction driving attempted-locked-writes is resolved at the source. Residual P3 = genuine schema mismatches or capability gaps the operator should see, not canon confusion. | New `reviewer_action_blocked` narrative entry (`dispatcher:` authored) |
| **P4** | Low but non-zero — genuinely hard reasoning sometimes hits budget. Should be rare per slug class. | standing_intent.md revision (`dispatcher:silent_exit_fallback` authored, exit_class=budget_exhausted) |
| **P5** | Low — confusion is a real-but-rare class. Persistent P5 on a specific slug = persona-frame disambiguation needed (separate Hat-A work). | standing_intent.md revision (`dispatcher:silent_exit_fallback` authored, exit_class=text_only_mid_loop) |

**Aggregate operator-visibility ratio target**: 100% of judgment-shape wakes produce SOME operator-visible substrate (any cell's substrate side-effect). Currently ~52% (P1 + explicit-P2 only). The structural target per ADR-303 §3 acceptance criteria is 95%+.

**Adherence target**: NOT a single percentage. Per-cell contract honored, where "honored" means the substrate matching the cell's detection rule appears within ±15min of the wake. This is the discipline shift: from "did the model do X" to "did the wake produce ONE OF the legitimate cell-shaped substrate artifacts."

### §1.4 Pre-flight criterion audit

Before reporting adherence, the discipline requires asking whether the criterion itself is well-formed.

**Q1**: Does the criterion cover all legitimate behaviors?

Yes — ADR-303 D1 is explicitly exhaustive over `invoke_reviewer` execution paths. The five cells partition the exit space without overlap.

**Q2**: Does it over-broadly conflate distinct postures?

Pre-implementation: NO — the per-cell decomposition is the entire point. Post-implementation: TBD — re-evaluate after first wake population accumulates.

**Q3**: Are there cases where canon doesn't yet have a clear expected behavior?

YES, three cases worth naming:
- **P5 differentiation from P4**: ADR-303 D1 itself acknowledges P5 is "indistinguishable from P4 in current code." The criterion currently treats them as one observable class. Whether they NEED to be distinguished is a forward question — if P5 patterns surface at the persona-frame level, differentiation becomes load-bearing. Today it's not.
- **Per-slug expected frequency**: ADR-303 D2 declines to specify per-cell frequency targets per slug. The criterion as-stated says "P2 should be a material fraction" without saying what fraction. This is appropriate (slug-context dictates) but means cross-slug comparison needs slug-specific baselines.
- **What counts as "operator-relevant" failure for P3 surfacing**: ADR-303 D3's `SILENCE_FAILURE_REASONS` starts with three entries (rate_limited / transient_network / retried_successfully_in_cycle). The denylist may need to evolve through observation. Criterion handles this via the explicit "denylist evolves through observation; operator-relevant reasons NEVER enter denylist" rule.

**Q4**: Are the criterion's load-bearing claims grounded in canon citations rather than vibes?

Yes — every cell + every contract cites ADR-303 D1/D2/D3 + ADR-302 D5/D6 + FOUNDATIONS Derived Principle 21 + the persona-frame `_PERSONA_FRAME` §392-§411 it supersedes. Substrate-receipts (revision_id, execution_event id, ±15min window query) per the discipline.

**Verdict on criterion well-formedness**: Sound enough to measure against. Three open questions tracked for forward evolution but not blocking.

---

## §2 What this evaluation does NOT do

Three explicit non-claims:

1. **Does NOT report a delta against the new criterion** — because no new wake population has been captured since the predecessor audit. Same N=27 wakes, same substrate, same DB state. The substrate doesn't change just because we changed what we measure against; new substrate accumulates from future wakes.

2. **Does NOT replace the predecessor population audit** (`2026-05-25-053951-...`) — that captured a real-world adherence number against the criterion that was operative at the time. Its lesson stands. This evaluation supersedes the *criterion* the predecessor used, not the *audit itself*.

3. **Does NOT validate that ADR-303 will achieve the 95% target** — that's the post-implementation re-run's question. This folder establishes the measurement framework + pre-implementation baseline so the post-implementation re-run has clean anchors. Validation comes later, against fresh substrate.

---

## §3 Pre-implementation baseline — per-cell breakdown of the existing N=27 population

Same N=27 judgment-shape wakes as the predecessor audit. Same DB state. New per-cell partition under the ADR-303 D1 criterion.

### §3.1 Cell distribution today

**Query** (substrate-receipts: re-runnable verbatim):

```sql
WITH wakes AS (
  SELECT
    e.id AS wake_id,
    e.user_id,
    e.slug,
    e.wake_source,
    e.created_at,
    e.duration_ms,
    e.output_tokens,
    EXISTS (
      SELECT 1 FROM workspace_file_versions v
      WHERE v.user_id = e.user_id
        AND v.path = '/workspace/review/judgment_log.md'
        AND v.authored_by LIKE 'reviewer:%'
        AND v.created_at BETWEEN e.created_at - interval '15 minutes' AND e.created_at + interval '1 minute'
    ) AS has_judgment_log,
    EXISTS (
      SELECT 1 FROM workspace_file_versions v
      WHERE v.user_id = e.user_id
        AND v.path = '/workspace/review/standing_intent.md'
        AND v.authored_by LIKE 'reviewer:%'
        AND v.created_at BETWEEN e.created_at - interval '15 minutes' AND e.created_at + interval '1 minute'
    ) AS has_standing_intent,
    EXISTS (
      SELECT 1 FROM workspace_file_versions v
      WHERE v.user_id = e.user_id
        AND v.authored_by LIKE 'reviewer:%'
        AND v.created_at BETWEEN e.created_at - interval '15 minutes' AND e.created_at + interval '1 minute'
    ) AS has_any_reviewer_write
  FROM execution_events e
  WHERE e.mode = 'judgment'
    AND e.status = 'success'
    AND e.created_at >= '2026-05-22T00:00:00Z'
    AND e.slug IN ('pre-ship-audit', 'signal-evaluation', 'outcome-reconciliation', 'revision-audit')
)
SELECT
  CASE
    WHEN has_judgment_log THEN 'P1 (fired-correctly)'
    WHEN has_standing_intent AND NOT has_judgment_log THEN 'P2-explicit (stand-down with intent write)'
    WHEN has_any_reviewer_write AND NOT has_judgment_log AND NOT has_standing_intent THEN 'P? (other reviewer writes only)'
    ELSE 'P3/P4/P5 (silent — no reviewer substrate)'
  END AS cell_today,
  count(*) AS wakes,
  round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
FROM wakes
GROUP BY cell_today
ORDER BY 2 DESC;
```

**Result (2026-05-26T16:30Z)**:

| cell_today | wakes | pct |
|---|---|---|
| P3/P4/P5 (silent — no reviewer substrate) | 12 | 44.4% |
| P2-explicit (stand-down with intent write) | 10 | 37.0% |
| P1 (fired-correctly) | 5 | 18.5% |

### §3.2 Interpretation — what this baseline tells us

**(a) Operator-visibility ratio today is 55.5% (P1 + P2-explicit = 5+10 of 27).** Not 52% as the predecessor finding §finding-3 summary stated — the predecessor framing computed visibility from a different denominator. The corrected figure under the new criterion: 55.5% of wakes produce operator-readable reviewer-attributed substrate today.

**(b) The 44.4% silent class collapses, by ADR-303 design, into one of three cells post-implementation:**
- P3 (tried-was-gated) — the failed-WriteFile pattern. Concentrated on author-class personas per `2026-05-26-152500-failed-action-substrate-blindspot/findings.md` §Finding-3. ADR-302's canon-contradiction fix should reduce P3 frequency at the source.
- P4 (budget-exhausted) — wakes where the model hit `max_rounds` without ReturnVerdict.
- P5 (confused) — wakes where the model emitted text-only mid-loop without justified reason.

The pre-implementation baseline cannot distinguish these three. The post-implementation re-run will be able to.

**(c) P2-explicit (37%) is the surprise positive finding.** Under the predecessor criterion, this class was conflated with P1 in the "did the wake write standing_intent.md" check — counting toward the ~48% adherence as a single "yes." Under the new criterion, P2-explicit is recognized as its own legitimate cell (model decided no action warranted, authored standing_intent without verdict). It's not a failure mode — it's optimal selectivity working as designed. **The new criterion correctly distinguishes "good silence" (P2 with substrate) from "blind silence" (P3/P4/P5).**

### §3.3 Silent-wake distribution by slug × wake_source

For posture-cell forecasting — which cells the 12 silent wakes are likely to collapse to post-implementation:

```sql
WITH silent_wakes AS (
  SELECT e.id, e.user_id, e.slug, e.wake_source, e.duration_ms, e.output_tokens
  FROM execution_events e
  WHERE e.mode = 'judgment' AND e.status = 'success'
    AND e.created_at >= '2026-05-22T00:00:00Z'
    AND e.slug IN ('pre-ship-audit', 'signal-evaluation', 'outcome-reconciliation', 'revision-audit')
    AND NOT EXISTS (
      SELECT 1 FROM workspace_file_versions v
      WHERE v.user_id = e.user_id
        AND v.authored_by LIKE 'reviewer:%'
        AND v.created_at BETWEEN e.created_at - interval '15 minutes' AND e.created_at + interval '1 minute'
    )
)
SELECT slug, wake_source, count(*) AS silent_wakes,
       round(avg(duration_ms) / 1000.0, 1) AS avg_duration_s,
       round(avg(output_tokens)) AS avg_output_tokens
FROM silent_wakes
GROUP BY slug, wake_source
ORDER BY 3 DESC;
```

**Result (2026-05-26T16:30Z)**:

| slug | wake_source | silent_wakes | avg_duration_s | avg_output_tokens |
|---|---|---|---|---|
| outcome-reconciliation | cron_tick | 7 | 57.6 | 4206 |
| pre-ship-audit | substrate_event | 2 | 33.9 | 2295 |
| revision-audit | cron_tick | 2 | 64.6 | 4816 |
| signal-evaluation | cron_tick | 1 | 50.8 | 4131 |

**Forecast per cell post-implementation** (substrate-anchored hypotheses; the post-implementation re-run confirms or refutes):

- **outcome-reconciliation cron_tick × 7**: spread across author-class personas (netflix-author + korea-shorts + yarnnn-author). Predicted breakdown: likely **majority P2 post-fix** (operator-relevant outcome-reconciliation on author-class workspaces with no platform fills correctly stands down — substrate already says "no outcomes to fold"). Per `2026-05-26-152500-...` §Finding-3, korea-shorts shows the failed-WriteFile-to-`_autonomy.yaml` pattern — those convert to **P3** post-fix. Tuesday signal-evaluation Render trace + the audit's §A5 author-program outcome-reconciliation asymmetry support the P2/P3 split hypothesis.
- **pre-ship-audit substrate_event × 2** (both yarnnn-author): the canary-RED + a sibling. Render trace at `2026-05-26-145500-...` §V1 Target-1 confirmed text-only-exit at round 7. Predicted: **P3 today** (the model attempted writes that were refused) becomes **P2 post-ADR-302 fix** because the canon contradiction is resolved and the same model on the same substrate has a clean recovery path.
- **revision-audit cron_tick × 2** (split netflix + korea): Render trace at the active session showed failed `_autonomy.yaml` write + Clarify on korea revision-audit. Predicted: **P3 today** → **P2 or P5 post-fix** depending on whether the persona-frame remediation also resolves the model's confusion about what to do next.
- **signal-evaluation cron_tick × 1** (kvk): Render trace at `2026-05-26-145500-...` §V1 Target-2 showed 18 tool actions + 3 failed ProposeActions + Clarify + text-only exit. Predicted: **P3 today** → **P2 or P5 post-fix**, with ProposeAction schema friction possibly persisting as a separate finding.

**No claim**: these forecasts are hypotheses for the post-implementation re-run to test. They are NOT predictions of fact. The substrate decides.

---

## §4 What the post-implementation re-run will measure

After ADR-302 + ADR-303 implementation phases land (estimated multi-commit work in `api/agents/reviewer_agent.py` + `api/services/reviewer_chat_surfacing.py` + new `api/agents/reviewer_agent_sections.py` per ADR-302 D5 + D6, plus dispatcher-write contracts per ADR-303 D2), a fresh wake population will accumulate under the new criterion. The re-run measures:

**Adherence metric**: per-cell contract-honored rate. For each cell, fraction of wakes assignable to that cell where the cell's substrate side-effect contract is satisfied. Per ADR-303 §3 acceptance criteria: 95%+ per cell.

**Operator-visibility ratio**: fraction of judgment-shape wakes producing ANY operator-visible substrate. Pre-implementation baseline: 55.5%. Target: 95%+.

**Cell-distribution delta**: how the 44.4% silent class breaks down post-fix. Expected: most collapse to P2 (correct selectivity); residual P3 = real constraint hits worth operator attention; P4 + P5 small.

**Failure-reason taxonomy evolution**: D3's `SILENCE_FAILURE_REASONS` denylist may need to grow if new natural-noise classes surface. The post-implementation re-run is where this gets discovered.

**Re-run timing**: at least 1 week of substrate accumulation post-deploy, mirroring the predecessor audit's window. Earlier re-runs are noise; the cell-distribution stabilizes only after material wake count.

---

## §5 Discipline notes — what this evaluation is for

This folder establishes three things at once:

1. **The canonical criterion** future re-runs measure against. Cite this folder, not the predecessor audit, when running the §3.1 query against new wake populations.

2. **The pre-implementation baseline** (55.5% operator-visibility / per-cell partition). Without this anchor, post-implementation deltas are unmeasurable.

3. **The first evaluation under the criterion-declaration discipline** (`docs/evaluations/README.md` rule 0). Future evaluations can copy this folder's shape: §1 declares criterion + operationalization + expected posture + pre-flight audit; §2 names non-claims; §3 reports measurement with substrate-receipts; §4 forecasts what re-runs will measure.

The discipline isn't "more ceremony per evaluation." The discipline is "don't measure against an under-specified criterion." This evaluation took a single session to draft because the criterion was already substantively defined by ADR-302 + ADR-303 — Hat-B work composed cleanly atop Hat-A canon.

---

## §6 Cross-references

- Predecessor population audit: `../2026-05-25-053951-reviewer-behavior-population-audit/findings.md` — measured ~48% adherence against the over-broad criterion this evaluation supersedes.
- Driving structural finding: `../2026-05-26-152500-failed-action-substrate-blindspot/findings.md` — named the two structural blindspots ADR-303 D2 + D3 address.
- Render-trace verification: `../2026-05-26-145500-silent-wake-hypothesis-verification/findings.md` — confirmed text-only-fallback failure mode at code-log level.
- Criterion canon: `docs/adr/ADR-303-reviewer-posture-taxonomy.md` D1 + D2 + D3.
- Discipline that motivated this evaluation's shape: `docs/adr/ADR-302-prompt-envelope-discipline.md` + `docs/evaluations/README.md` §"The criterion-declaration discipline" (rule 0).
- Rename commit that codified the discipline: `4f1f128` (docs/observations → docs/evaluations + README rewrite).

---

## Status

**OPEN** as the canonical pre-implementation baseline against the new criterion. Lock at "Implemented" only after the post-implementation re-run lands a fresh wake-population measurement (estimated ≥1 week post-deploy of ADR-302/303 implementation commits).

## Last updated

2026-05-26T16:30Z — initial criterion declaration + baseline measurement against the existing N=27 wake population.
