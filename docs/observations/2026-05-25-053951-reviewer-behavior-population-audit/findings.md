# Reviewer behavior population audit — persona-frame contract holds at ~48%, not architecture-claimed 100%

**Captured**: 2026-05-25T05:39Z. Hat-B observation.

**Shape**: substrate-population audit, not capture-window observation. No PLAYBOOK because there's
no captured-window narrative — this is N=27 wakes characterized by SQL against `execution_events` +
`workspace_file_versions` + `wake_queue` + `action_proposals` directly. Re-runnable; every load-bearing
claim has its query inline.

**Why now**: a session-start brief carried two architecturally-tense claims forward — (a) "behavioral
closure confirmed" post-ADR-301, (b) "canary-RED was a one-shot anomaly." Verification queries against
substrate contradicted both. Drilling broader to find the population-level pattern: the canary-RED is
representative, not anomalous. The earlier reviewer-prompt-strategy-audit-stub (archived at
`archive/2026-05-21-021204-reviewer-prompt-strategy-audit-stub/`) deferred this characterization
pending more data; the data is now here.

**Baseline window**: 2026-05-22T00:00Z onward (post-ADR-298 cutover). Any wakes earlier ran on
pre-cutover plumbing and are excluded.

---

## Headline

**The Reviewer's persona-frame contract — "every judgment cycle produces a `standing_intent.md`
write" — holds at ~48% on judgment-shape recurrences (N=27, range 33%–67% by slug class). 41% of
judgment-shape wakes produced ZERO Reviewer substrate writes at all, despite running 50–110 seconds
on Sonnet with `status='success'`. The canary-RED pattern from 2026-05-24T05:38Z (zero writes, 43s,
3K output_tokens) is one row in a population of 11 similar silent wakes, not an outlier.**

The architecture layer is fully GREEN (1984 wakes through wake_queue, 1 failed, ~0.05%). The plumbing
works. The behavior on top of the plumbing does not consistently fulfill the persona-frame contract.

The most parsimonious hypothesis (L4-F2 text-only-fallback) is supported by output-token correlation:
silent wakes cluster at low output_tokens (1.1K, 1.6K, 3.0K) vs. clean wakes (4.6K+ typical). The
model is plausibly emitting prose responses without wrapping in `ReturnVerdict` + `WriteFile` tool
calls, then closing without substrate side-effects.

---

## A1 — Persona-frame contract adherence: 48% on judgment-shape recurrences

The persona-frame at `api/agents/reviewer_agent.py::_PERSONA_FRAME` mandates: *"Reactive recurrence
fires + addressed turns + heartbeats: every cycle produces a standing_intent.md write."* This is the
universal cycle-artifact contract.

**Query:**
```sql
WITH wakes AS (
  SELECT e.id, e.user_id, e.slug, e.wake_source, e.created_at, e.duration_ms, e.output_tokens
  FROM execution_events e
  WHERE e.mode = 'judgment'
    AND e.status = 'success'
    AND e.created_at >= '2026-05-22T00:00:00Z'
    AND e.slug IN ('pre-ship-audit', 'signal-evaluation', 'outcome-reconciliation', 'revision-audit')
)
SELECT
  w.slug,
  w.wake_source,
  count(*) AS total,
  count(*) FILTER (WHERE EXISTS (
    SELECT 1 FROM workspace_file_versions v
    WHERE v.user_id = w.user_id
      AND v.path = '/workspace/review/standing_intent.md'
      AND v.authored_by LIKE 'reviewer:%'
      AND v.created_at BETWEEN w.created_at - interval '15 minutes' AND w.created_at + interval '1 minute'
  )) AS si_clean,
  round(100.0 * count(*) FILTER (WHERE EXISTS (
    SELECT 1 FROM workspace_file_versions v
    WHERE v.user_id = w.user_id
      AND v.path = '/workspace/review/standing_intent.md'
      AND v.authored_by LIKE 'reviewer:%'
      AND v.created_at BETWEEN w.created_at - interval '15 minutes' AND w.created_at + interval '1 minute'
  )) / count(*), 1) AS pct_clean
FROM wakes w
GROUP BY w.slug, w.wake_source
ORDER BY w.slug, w.wake_source;
```

**Result (2026-05-25T05:39Z):**

| slug | wake_source | total | si_clean | pct_clean |
|---|---|---|---|---|
| outcome-reconciliation | cron_tick | 15 | 7 | 46.7% |
| pre-ship-audit | substrate_event | 6 | 4 | 66.7% |
| revision-audit | cron_tick | 3 | 1 | 33.3% |
| signal-evaluation | cron_tick | 3 | 1 | 33.3% |
| **TOTAL** | | **27** | **13** | **48.1%** |

**Interpretation:** the persona-frame contract is treated as a doctrine at architecture-claim level
but is fulfilled approximately half the time at substrate level. This is not a one-shot failure
mode; it's a class-level discipline gap.

---

## A2 — Silent-wake pattern reproduces across N=11

A silent wake = `execution_events.status='success'` + zero `workspace_file_versions` rows with
`authored_by LIKE 'reviewer:%'` in the ±15min window around the wake.

**Query** (the 11 fully-silent rows):
```sql
SELECT e.id, e.user_id, e.slug, e.wake_source, e.created_at, e.duration_ms, e.output_tokens
FROM execution_events e
WHERE e.mode='judgment' AND e.status='success' AND e.created_at >= '2026-05-22'
  AND e.slug IN ('pre-ship-audit', 'signal-evaluation', 'outcome-reconciliation', 'revision-audit')
  AND NOT EXISTS (
    SELECT 1 FROM workspace_file_versions v
    WHERE v.user_id = e.user_id
      AND v.authored_by LIKE 'reviewer:%'
      AND v.created_at BETWEEN e.created_at - interval '15 minutes' AND e.created_at + interval '1 minute'
  )
ORDER BY e.created_at;
```

**Receipts (the 11):**

| execution_event_id | persona | slug | duration | output_tokens |
|---|---|---|---|---|
| `c4f250f2-d26f-4c1b-9013-0c80854319f7` | yarnnn-author | pre-ship-audit | 43s | **3,013** |
| (cross-ref the canary-RED predecessor finding `2026-05-24-054214-adr299-phase4-canary-red/findings.md`) | | | | |
| (full list available via the query above; 11 rows total across 4 personas, 4 slug-types, 2 wake_sources) | | | | |

**Cross-trigger breakdown:**

| wake_source | total | silent | pct_silent |
|---|---|---|---|
| cron_tick | 21 | 9 | 42.9% |
| substrate_event | 6 | 2 | 33.3% |

**Interpretation:** the 2026-05-24T05:38Z canary-RED is ONE row in this population, not an outlier.
The earlier predecessor finding treated it as a one-shot anomaly worth investigating only if it
reproduced. The substrate says it has reproduced 11 times across the broader judgment surface,
spanning 4 personas, 4 slug types, and 2 wake sources.

---

## A3 — Cross-trigger-class variance: cron_tick 43% vs substrate_event 67%

ADR-276 closed plumbing-symmetry across trigger types (reactive + addressed envelope shape) by
introducing the `load_reviewer_governance_envelope` helper called from both code paths. But the
behavioral output diverges: substrate_event wakes produce standing_intent.md 67% of the time;
cron_tick wakes 43%.

**This is a structural finding worth naming.** ADR-276 said: "Reviewer perceives full governance
substrate at every wake regardless of trigger shape." That holds at the envelope-content level
(both paths now call the same helper). It does NOT hold at the behavioral-output level (the
Reviewer reasons differently with the same envelope when invocation context shifts).

The seulkim88 framework-contradiction documented at
`2026-05-25-042647-cross-session-substrate-verification/findings.md` is a different manifestation of
this same phenomenon — addressed-turn vs cron_tick produced opposite verdicts on identical data.

---

## A4 — Zero `action_proposals` since cutover

Across 4 days × 3 trader personas, the substrate produced ZERO capital action proposals.

**Query:**
```sql
SELECT count(*) FROM action_proposals WHERE created_at >= '2026-05-22T00:00:00Z';
-- 0
```

**Two possible explanations:**

1. **By-design selectivity** — entry rules in `_operator_profile.md` are deliberately tight; on most
   RTH days no ticker matches any signal; signal-evaluation correctly stands down. Plausible per the
   alpha-trader session guide's "signal frequency is naturally low" framing.
2. **Behavioral silent stand-down** — the 1-of-1 silent kvk signal-evaluation wake at
   2026-05-22T13:46 (51s on Sonnet, 4.1K output_tokens, zero substrate writes) supports the
   alternative that signal-evaluation Reviewer reasoning is sometimes producing silent
   stand-downs rather than evaluating to proposals.

**Cannot distinguish from substrate alone.** Tuesday 2026-05-26T13:45Z signal-evaluation will
inform — if it produces substrate writes (even a stand-down note to standing_intent.md), the
selectivity explanation strengthens; if it joins the silent-wake population, explanation #2
strengthens.

---

## A5 — Author-program outcome-reconciliation: 7-of-12 silent

Author programs (yarnnn-author, netflix-author, korea-shorts) have no platform fills to fold —
outcome-reconciliation may be a legitimate no-op there. But the wakes still run 50–75s on Sonnet
at $0.10–$0.30 per wake.

**Per-persona breakdown:**

| persona | outcome-reconciliation wakes | produced substrate | silent |
|---|---|---|---|
| yarnnn-author | 4 | 4 | 0 |
| netflix-author | 4 | 0 | 4 |
| korea-shorts | 4 | 1 | 3 |

**Asymmetric in a way that demands explanation.** yarnnn-author's Reviewer writes substrate on
every outcome-reconciliation; netflix-author's writes none. Same recurrence, same trigger context,
same balance state, ~similar bundle. The asymmetry suggests either (a) yarnnn-author Reviewer has
material to fold and netflix-author doesn't (then outcome-reconciliation should be opt-out at
bundle-level for personas without platform connections), or (b) author Reviewers are silent-stand-
down at variable rates per A2.

**Either resolution is Hat-A:** filter the recurrence at bundle-level, OR sharpen the prompt to
force a stand-down note. Substrate cost: ~$1.20/persona/month for unnecessary judgment cycles if
explanation (a) holds.

---

## A6 — Architecture layer: GREEN

Plumbing health since 2026-05-22T00:00Z cutover:

**Query:**
```sql
SELECT status, count(*) FROM wake_queue WHERE enqueued_at >= '2026-05-22' GROUP BY status;
```

**Result:**
| status | count |
|---|---|
| completed | 1984 |
| failed | 1 |

**The one failure** (`5320fe47-30f3-4939-8831-93eaa7496a36`) was the pre-stable canary v5 on
2026-05-22T02:02Z when the workspace had negative balance — gated correctly at the architecture
layer, not a current concern.

**ADR-298 + ADR-301 + ADR-276 closed the wake-architecture arc.** The behavior gap in A1–A5 is
NOT a plumbing gap. The wakes fire reliably, the substrate accumulates attribution reliably, the
telemetry pairs reliably. What the Reviewer does INSIDE those wakes is the gap.

---

## A7 — Operator-addressing email channel: structurally broken

**Query:**
```sql
SELECT count(*) FROM notifications WHERE status='sent';
-- 0
SELECT count(*) FROM notifications;
-- 2 (in_app rows from 2026-03-20, no channel='email' rows ever)
```

**Receipt:** zero successful email sends in 90 days across all users. ADR-040 (notifications base),
ADR-202 (daily-update email pointer model), ADR-299 (operator-addressing capability) wires all
empirically unproven at the delivery layer.

This morning's clean phase4-canary-v3 cycle on yarnnn-author (`252e75f6-44bc-47db-9403-9fdbf74416ae`,
74s, $0.32, 6.1K output_tokens, produced judgment_log + standing_intent) — a textbook-quality
Reviewer reject_publication with substantive citation of 5 voice-anti-patterns — also produced
ZERO notifications. The architecture is correct; delivery is unverified.

**Likely cause** (operator-side verifiable): `RESEND_API_KEY` env var status on Render services
(API + Scheduler). If unset, ADR-040 + ADR-202 + ADR-299 all unblock simultaneously when set.

---

## A8 — Persona-frame contract scope ambiguity

The persona-frame says "every cycle produces standing_intent.md." But the substrate suggests this
contract may not have been intended for report-shape recurrences:

**Report-shape recurrences** (slug-class):

| slug | wakes | standing_intent rate | other writes per wake (avg) |
|---|---|---|---|
| weekly-corpus-review | 3 | 0% | 5.3 (sections + output.md) |
| weekly-performance-review | 3 | 33% | 4.7 (sections + output.md) |
| pre-market-brief | 3 | 100% | 3.3 |

`weekly-corpus-review` writes the report sections + composed output.md but NOT standing_intent.md
— and this may be slug-appropriate. The persona-frame contract may need disambiguation:
"judgment-shape recurrences produce standing_intent.md; report-shape recurrences produce the
declared output." `pre-market-brief` is interestingly both — it produces brief content AND
standing_intent.md every time.

**Either:**
- The persona-frame needs slug-class disambiguation (Hat-A: persona-frame edit).
- OR the persona-frame is correct as-stated and report-shape Reviewers are silently violating it
  (Hat-A: prompt strategy to enforce).

This is the same shape as the prompt-strategy audit-stub's deferred concern: the prompt surface
has accumulated coaching mechanisms across ~20+ ADRs and may be incoherent at the cross-slug-class
level.

---

## What is NOT a finding (sanity checks that passed)

- Wake-architecture L1–L8: GREEN across all wakes (A6).
- ADR-301 substrate mirrors: firing reliably (system:mirror-* writes on every scheduler tick).
- Substrate attribution: 100% of writes carry `authored_by` per ADR-209.
- This morning's phase4-canary-v3 Reviewer cycle: textbook-quality REJECT with substantive
  citation of 5 voice anti-patterns. The Reviewer can produce excellent behavior; it just doesn't
  always produce excellent behavior.
- Memorial Day scheduler skip: working correctly (signal-evaluation `next_run_at` advanced from
  Friday to Tuesday without firing on Monday).

---

## Recommendations (Hat-A engagement set)

This audit is the substrate evidence the deferred prompt-strategy-audit-stub at
`archive/2026-05-21-021204-reviewer-prompt-strategy-audit-stub/` was waiting for. Operator decides
which threads to engage.

### R1 — Reopen the reviewer-prompt-strategy work

The substrate now shows 11 reproducing silent wakes spanning 4 personas, 4 slug types, 2 wake
sources. The stub explicitly waited for "more data before recommending"; the data is here. Pre-flight
work warranted:

- Pull Render Scheduler trace logs for 2–3 specific silent wakes (e.g., `c4f250f2` canary-RED + one
  netflix-author outcome-reconciliation + the kvk signal-evaluation silent fire). Confirm
  text-only-fallback hypothesis empirically — did the model emit prose without wrapping in tool
  calls?
- If confirmed: persona-frame amendment (Hat-A) to either (a) force-tool-choice on ReturnVerdict
  at API level, OR (b) restructure the prompt to make tool-call wrapping more robust.
- If not confirmed: the failure mode is somewhere else and needs different investigation.

### R2 — Persona-frame contract disambiguation

Sharpen the contract per A8:

- "Every judgment-shape cycle produces standing_intent.md" (preserved canon).
- "Every report-shape cycle produces the declared deliverable substrate" (new clarification).
- "Every reactive substrate-event wake produces at minimum a stand-down note IF the trigger does
  not warrant material judgment" (closes the silent-wake gap structurally).

ADR amendment territory. Persona-frame edit in `api/agents/reviewer_agent.py`. Prompt CHANGELOG entry
required.

### R3 — Bundle-level recurrence scope re-evaluation

Per A5, author-program outcome-reconciliation may be a misconfigured recurrence costing ~$1.20/
persona/month for no-op cycles. Two paths:

- Filter `outcome-reconciliation` at bundle-level for author programs (alpha-author bundle's
  `_recurrences.yaml` may need conditional `active: false` for personas without platform
  connections).
- OR add early-return discipline at the executor: if `account_state.fills_count == 0`, emit
  stand-down narrative without spending Sonnet cycles.

### R4 — Operator-addressing channel: empirical viability check

Per A7, check `RESEND_API_KEY` on Render services (operator-side: dashboard inspection). If unset,
setting it unblocks three ADR threads simultaneously. ~10 minute fix.

### R5 — Cross-trigger-class envelope-behavior gap

Per A3, ADR-276 closed plumbing-symmetry but the behavioral output diverges across trigger types.
This may resolve naturally if R1 + R2 land (text-only-fallback being trigger-class-sensitive would
explain the asymmetry). Hold this finding open until R1 prompt-strategy work surfaces evidence on
whether trigger-class is causally relevant to silent-wake rate.

---

## What this audit does NOT claim

- This is NOT a claim that the system is broken. The architecture is GREEN; the Reviewer produces
  high-quality work when it produces work at all (this morning's canary-v3 reject_publication is
  textbook-quality). The claim is that **behavioral consistency** has not yet been achieved at
  architecture-claimed rates, and the gap is class-level, not anomalous.
- This is NOT a Hat-A fix. No code changes recommended in this folder. R1–R5 are recommendations
  the operator considers; the fixes (whichever land) ship as separate commits in system canon.
- This is NOT exhaustive. N=27 judgment-shape wakes is a population, not the full universe.
  Re-running the queries weekly would deepen the characterization; the recommendation set above is
  what the current N=27 substrate justifies.

---

## Re-runnable verification

Every query above can be re-run by any future session to re-characterize the population. The
substrate is the evaluation framework. No ledger maintenance, no folder ceremony, no register
discipline — just the queries.

If after R1–R5 land, re-running the A1 query produces 95%+ adherence, the discipline gap closes.
If it stays at ~48%, the engagement is wrong-shaped and needs different intervention.

---

## Cross-references

- Predecessor canary-RED (now archived): `archive/2026-05-24-054214-adr299-phase4-canary-red/findings.md`
- Predecessor cross-session verification: `2026-05-25-042647-cross-session-substrate-verification/findings.md`
- Deferred prompt-strategy audit-stub: `archive/2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md`
- Tuesday signal-evaluation observation staging: `2026-05-26-134500-signal-evaluation-tuesday-rth/PLAYBOOK.md`
- ADR-276 (envelope governance pre-load): `docs/adr/ADR-276-reactive-trigger-envelope-governance-preload.md`
- ADR-298 (wake_queue): `docs/adr/ADR-298-wake-queue.md`
- ADR-301 (substrate mirrors): `docs/adr/ADR-301-substrate-mirrors.md`
- Persona-frame: `api/agents/reviewer_agent.py::_PERSONA_FRAME`

## Status

**OPEN.** Recommendations queue for operator engagement. This folder remains active as
the load-bearing characterization until R1–R5 land or until a follow-up population
audit (~weekly re-run of the queries) supersedes it.

## Last updated

2026-05-25T05:39Z — initial population characterization. N=27 judgment-shape wakes, N=11 silent
wakes, 1984 total wakes through queue since cutover.
