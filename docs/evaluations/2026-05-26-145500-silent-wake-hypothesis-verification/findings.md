# Silent-wake hypothesis verification — text-only-fallback CONFIRMED; recommended fix SUPERSEDED

> **STATUS BANNER (added 2026-05-26 ~12:25Z, same session):** The Hat-A fix
> recommended in §V4 + landed in commit `9e7c1c7` was REVERTED ~20 minutes
> after landing in commit (this commit, see git log). Operator review identified
> the fix as a workaround for an under-specified problem. The criterion that
> the predecessor population audit measured against ("every reactive recurrence
> cycle produces a standing_intent.md write") is suspect — several legitimate
> Reviewer postures (nothing-changed, substrate-already-answers, immaterial-
> trigger, no-op cell) could rationally exit without writing standing_intent.
> Before any code change, posture taxonomy must be canonized — define expected
> Reviewer behavior per (slug, wake_source, substrate-delta) cell, classify
> material vs immaterial wakes, declare what substrate side-effect each
> posture requires. See CHANGELOG `[2026.05.26.2]` for the revert rationale.
>
> **What survives from this folder:** §V1 Render-trace receipts (three target
> wakes with the `WARNING:agents.reviewer_agent:[REVIEWER] text-only response
> round N` log line) remain load-bearing evidence for the posture-taxonomy
> work. The model IS exiting via text-only-fallback on those wakes; what
> needs canonical work is whether that's a failure or a correct selectivity.
>
> **What is superseded:** §V4 "Hat-A fix shape" + §V5 "Verification protocol"
> (which assumed the fix would land). Adherence target framing was wrong-shaped.
>
> **Forward link:** posture-taxonomy ADR draft (forthcoming) +
> `docs/evaluations/` → `docs/evaluations/` rename + criterion-declaration
> discipline rewrite.

---

# Silent-wake hypothesis verification — text-only-fallback CONFIRMED, Hat-A fix landed in same commit (ORIGINAL TEXT BELOW, retained for trace continuity)

**Captured**: 2026-05-26T14:55Z. Hat-B observation.

**Shape**: targeted Render Scheduler trace pull against three specific silent wakes
identified in the predecessor population audit, plus same-session Hat-A fix landing
the substrate-honoring fallback. This folder records the verification half; the
canon-side fix lands at `api/agents/reviewer_agent.py` per CHANGELOG entry
`[2026.05.26.1]`.

**Predecessor**: `docs/evaluations/2026-05-25-053951-reviewer-behavior-population-audit/findings.md`
R1 ("Pull Render Scheduler trace logs for 2–3 specific silent wakes... Confirm
text-only-fallback hypothesis empirically — did the model emit prose without
wrapping in tool calls?").

---

## Headline

**The L4-F2 text-only-fallback hypothesis is confirmed.** Render Scheduler logs
captured the exact failure mode at three target wakes spanning two personas, two
slug types, and both wake_source classes (cron_tick + substrate_event). The code
itself logs the failure by name: `WARNING:agents.reviewer_agent:[REVIEWER]
text-only response round N trigger=reactive user=...`. Both fallback sites in
`invoke_reviewer` (text-only mid-loop at line ~1482; budget-exhausted at line
~1640) constructed `stand_down` verdicts without writing any reviewer-attributed
substrate, breaking the persona-frame contract on the silent-exit class.

Same-session Hat-A fix lands a substrate-honoring fallback that writes
`standing_intent.md` via the canonical primitive on either fallback path. See
CHANGELOG `[2026.05.26.1]`.

---

## V1 — Trace evidence per target wake

### Target 1: `c4f250f2-d26f-4c1b-9013-0c80854319f7` (yarnnn-author / pre-ship-audit / substrate_event)

**Wake metadata** (from `execution_events`):
- created_at: 2026-05-24T05:39:11.453931Z
- duration_ms: 43126
- output_tokens: 3013
- status: success

**Render Scheduler log** (`crn-d604uqili9vc73ankvag`, instance `xx8cv`):

```
2026-05-24T05:39:11.373006607Z WARNING:agents.reviewer_agent:[REVIEWER] text-only response round 7 trigger=reactive user=0b7a852d
2026-05-24T05:39:11.449918341Z INFO:services.telemetry:[TELEMETRY] judgment/pre-ship-audit success cost=$0.2573
```

**Interpretation**: model exited at round 7 with prose, fallback triggered,
telemetry recorded `success` 76ms later. Zero reviewer-attributed
`workspace_file_versions` rows in the ±15min window per the population-audit query.

### Target 2: `68534e54-9c39-4478-978e-cf810bc1516e` (kvk / signal-evaluation / cron_tick)

**Wake metadata**:
- created_at: 2026-05-22T13:46:17.33216Z
- duration_ms: 50824
- output_tokens: 4131
- status: success

**Render Scheduler log** (`crn-d604uqili9vc73ankvag`, instance `ns97m`):

The wake performed **18 tool actions** across rounds before silent exit:
- Multiple `ReadFile` + `ListFiles` (16 successful)
- 3 failed `ProposeAction` (likely schema rejection — line 13:46:46 / 13:46:48 /
  13:46:51)
- 1 successful `Clarify` (13:46:55)
- Then:

```
2026-05-22T13:46:17.233903653Z WARNING:agents.reviewer_agent:[REVIEWER] text-only response round 8 trigger=reactive user=2abf3f96
2026-05-22T13:46:17.313717375Z INFO:services.telemetry:[TELEMETRY] judgment/signal-evaluation success cost=$0.2491
2026-05-22T13:46:17.392322028Z INFO:services.wake:[DISPATCH] 2abf3f96/signal-evaluation done (50824ms) — actions=18 proposals=0 compose=—
```

**Interpretation**: kvk's signal-evaluation Reviewer worked the substrate
substantively (18 actions including failed ProposeAction attempts and a Clarify),
then exited text-only at round 8 of the 20-round Haiku budget. The "proposals=0"
in the DISPATCH line is the operator-facing consequence: no proposal flowed to
the cockpit Queue despite a full Reviewer reasoning cycle.

This is the case the predecessor audit §A4 flagged as needing Tuesday RTH to
disambiguate. The Render trace pre-empts that — at least one signal-evaluation
silent-exit was definitively text-only-fallback, not by-design selectivity.

### Target 3: `35ac5712-f01c-4bc1-a59c-6a2d8b05e898` (korea-shorts / outcome-reconciliation / cron_tick)

**Wake metadata**:
- created_at: 2026-05-22T05:03:50.164336Z
- duration_ms: 61916
- output_tokens: 4607
- status: success

**Render Scheduler log** (`crn-d604uqili9vc73ankvag`, instance `nx67d`):

```
2026-05-22T05:03:00.340Z INFO:agents.reviewer_agent:[REVIEWER] tool=ListFiles trigger=reactive user=ca478643 success=True
2026-05-22T05:03:00.369Z INFO:agents.reviewer_agent:[REVIEWER] tool=ListRevisions trigger=reactive user=ca478643 success=True
2026-05-22T05:03:29.231Z INFO:agents.reviewer_agent:[REVIEWER] tool=WriteFile trigger=reactive user=ca478643 success=False
2026-05-22T05:03:32.148Z INFO:agents.reviewer_agent:[REVIEWER] tool=ReadFile trigger=reactive user=ca478643 success=True
2026-05-22T05:03:50.143Z INFO:services.telemetry:[TELEMETRY] judgment/outcome-reconciliation success cost=$0.2465
2026-05-22T05:03:50.200Z INFO:services.wake:[DISPATCH] ca478643/outcome-reconciliation done (61916ms) — actions=18 proposals=0 compose=—
```

**Interpretation**: same pattern — substantive reasoning (18 actions including a
failed WriteFile attempt — interesting because the operator's `_locks.yaml` may
have refused the path), then silent exit without ReturnVerdict. The
WARNING:text-only line was outside our 2.5-minute capture window slice but the
substrate signature (zero reviewer writes despite 18 actions + success telemetry
+ 61s on Haiku) matches the population pattern exactly.

---

## V2 — Cross-target consistency

| target | persona | slug | wake_source | exit_round | budget | total_actions | failed_writes | final exit signal |
|---|---|---|---|---|---|---|---|---|
| c4f250f2 | yarnnn-author | pre-ship-audit | substrate_event | 7 | 20 | unknown (no per-tool logs captured) | unknown | WARNING text-only |
| 68534e54 | kvk | signal-evaluation | cron_tick | 8 | 20 | 18 | 3 ProposeAction | WARNING text-only |
| 35ac5712 | korea-shorts | outcome-reconciliation | cron_tick | n/a | 20 | 18 | 1 WriteFile | substrate match (warning outside window) |

The pattern is invariant across the three: substantive tool use earlier in the
loop, then the model decides it's "done thinking," emits prose without wrapping
in `ReturnVerdict`, and the existing fallback paths converted that to
`stand_down` with no substrate side-effect.

---

## V3 — Why the fallback was unguarded

Pre-fix `api/agents/reviewer_agent.py::invoke_reviewer` had two fallback sites:

1. **Line ~1482** (`if not tool_uses:`) — text-only response mid-loop. Constructed
   `verdict_raw = {"verdict": "stand_down", "reasoning": text_fallback[:1000],
   "confidence": "medium"}` and broke out of the loop.
2. **Line ~1640** (`if verdict_raw is None:`) — loop-exhaustion with no
   ReturnVerdict ever called. Constructed `verdict_raw = {"verdict":
   "stand_down", "reasoning": last_text, "confidence": "low"}`.

Both paths constructed a verdict that downstream `dispatcher` rendered into
`judgment_log.md` (verdict-of-record substrate per ADR-289 D4), but NEITHER
path produced a `standing_intent.md` write. Per the persona-frame contract
amended 2026-05-20 (ADR-294 Phase 2 warm-start observation), reactive
recurrence + addressed + heartbeat wakes MUST produce a standing_intent.md
write — "no action without an updated standing intent is not a real judgment,
it's drift."

The contract was held behaviorally at ~48% (population audit §A1) but
infrastructurally at 0% on the silent-exit class because the safety nets did
not honor the contract.

---

## V4 — Hat-A fix shape

Lands in same session at `api/agents/reviewer_agent.py`. See CHANGELOG
`[2026.05.26.1]` for the full rationale block.

Minimal-surface intervention:
- New helper `_write_silent_exit_standing_intent` writes `review/standing_intent.md`
  via `execute_primitive("WriteFile", ...)` with `caller_identity="reviewer:{REVIEWER_MODEL_IDENTITY}"`.
- Both fallback sites `await` the helper before constructing `verdict_raw`.
- Helper failures are logged but never raised — verdict construction always
  proceeds so the wake completes at the queue.
- Substrate entry carries: exit class, exit round, max rounds, trigger, slug,
  truncated last-prose snippet. Sufficient diagnostic content for operator to
  decide whether to re-fire or to re-shape the recurrence prompt.

What this fix does NOT do (deliberate):
- Does not constrain model behavior in-loop. No `tool_choice` forcing. No
  prompt nag to call ReturnVerdict. The model is free to decide as it would
  have; only the silent-exit path now writes substrate.
- Does not address audit R2 (persona-frame contract disambiguation across
  slug classes). Report-shape vs judgment-shape adherence asymmetry needs its
  own analysis — out of scope here.
- Does not address audit R5 (cross-trigger-class behavioral divergence). May
  resolve naturally if silent-wake rate drops symmetrically across triggers
  post-fix; hold this finding open until A1 re-run.

---

## V5 — Verification protocol post-deploy

The audit's §A1 query is the canonical re-run target. Re-run one week after the
fix deploys to Render:

```sql
WITH wakes AS (
  SELECT e.id, e.user_id, e.slug, e.wake_source, e.created_at, e.duration_ms, e.output_tokens
  FROM execution_events e
  WHERE e.mode = 'judgment'
    AND e.status = 'success'
    AND e.created_at >= '2026-06-02T00:00:00Z'  -- adjust to one week after deploy
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

**Target**: 95%+ adherence across all (slug, wake_source) combinations.

**Interpretation rules**:
- 95%+ → silent-exit substrate gap closed. Operator's "no information on feed
  and cockpit" experience should resolve in parallel. Folder moves to archive
  with RESOLUTION.md.
- 75–95% → fix is partial. Investigate which (slug, wake_source) combinations
  remain low; may need R2 (persona-frame disambiguation) to address residual
  class.
- <75% → fix is wrong-shaped. Re-investigate at trace level. The
  substrate-honoring fallback was the wrong primary lever; need to escalate to
  in-loop intervention (`tool_choice` forcing on terminal rounds, or per-round
  contract reminder injected mid-loop).

Distinct from the original audit, this re-run will ALSO surface a new diagnostic
signature: `standing_intent.md` revisions with `silent_exit:` frontmatter or
"silent-exit fallback" in the message field indicate the fix is firing. If we
see those at the same rate as the pre-fix silent-wake rate (~41%), we know the
silent-exit class is unchanged but now visible — the underlying model behavior
is the real problem and R2 work is needed next.

---

## Cross-references

- Predecessor population audit: `../2026-05-25-053951-reviewer-behavior-population-audit/findings.md`
- Hat-A fix landing site: `api/agents/reviewer_agent.py::_write_silent_exit_standing_intent` (new helper) + two call sites in `invoke_reviewer`
- Prompt CHANGELOG entry: `api/prompts/CHANGELOG.md` `[2026.05.26.1]`
- Operator session asking "is true autonomy realized?" — this is the substrate
  answer: it was being realized invisibly on ~41% of wakes pre-fix; post-fix it
  should be visible at 95%+ regardless of model decision shape.

## Status

**OPEN**. Re-run §V5 query one week after deploy to confirm or refute the fix.
If confirmed, archive both this folder and the predecessor population audit
with RESOLUTION.md cross-linked. If refuted, escalate to R2 + in-loop
intervention design.

## Last updated

2026-05-26T14:55Z — initial verification + same-session Hat-A fix landing.
