# Canary v4 — Substrate-Event Reactive Wake Closes Cleanly Post-Option-D

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").

**Captured**: 2026-05-21T04:50-04:52Z server-clock. N=1 substrate-event reactive wake (canary v4); cross-referenced against full Render Scheduler log for the wake window.

## Headline finding

**Canary v4 closes cleanly via the structured tool-use flow.** The Reviewer used 8 tool rounds (well within the post-Option-D 20-round budget), made 7 reads + 1 WriteFile, then closed via `ReturnVerdict`. Zero text-only-fallback warnings. The substantive output (`standing_intent.md` update) is high-quality: identifies the canary as a status re-transition, anchors against the prior 04:17Z addressed-turn audit, surfaces two concrete Clarify questions for the operator, and lays out forward-watch criteria for pieces 2-3.

**v3 → v4 pattern shift:**

| Metric | v3 (02:09Z) | v4 (04:51Z) |
|---|---|---|
| `execution_events` rows | 1 ✓ (dedup working) | 1 ✓ |
| `wake_dedup_key` populated | `2ae6dbdb`-class | `2ae6dbdb-675c-4b4e-99da-b1243bae66a2` |
| Tool rounds | 13 | 8 |
| Cost | $0.31 | $0.28 |
| `WriteFile` calls | **0** ✗ | **1** ✓ |
| Text-only fallback | **fired** ✗ | **not fired** ✓ |
| `judgment_log.md` write | 0 | 0 (correct — no new decision to log) |
| `standing_intent.md` write | 0 | 1 ✓ |
| Loop exit | text-only fallback → stand_down | ReturnVerdict (structured) |

The v3 text-only-fallback symptom did not reproduce in v4. The N=2 substrate-event reactive wakes post-Option-D characterize as: 1 fallback failure (v3), 1 structured success (v4). The pattern is **probabilistic**, not deterministic — the model on read-heavy hooks sometimes self-determines a text-only close, sometimes a tool-use close.

## Evidence trail

### Render Scheduler logs (crn-d604uqili9vc73ankvag, 04:50:30Z–04:52:30Z)

```
04:50:31.74Z  REVIEWER tool=ReadFile  trigger=reactive  user=0b7a852d  success=True
04:50:31.77Z  REVIEWER tool=ReadFile  trigger=reactive  user=0b7a852d  success=True
04:50:31.86Z  REVIEWER tool=GetSystemState  trigger=reactive  user=0b7a852d  success=True
04:50:35.19Z  REVIEWER tool=ReadFile  trigger=reactive  user=0b7a852d  success=True
04:50:35.22Z  REVIEWER tool=ListRevisions  trigger=reactive  user=0b7a852d  success=True
04:50:39.03Z  REVIEWER tool=ReadFile  trigger=reactive  user=0b7a852d  success=True
04:50:47.40Z  REVIEWER tool=ReadFile  trigger=reactive  user=0b7a852d  success=True
04:51:13.29Z  REVIEWER tool=WriteFile trigger=reactive  user=0b7a852d  success=True
04:51:18.95Z  TELEMETRY judgment/pre-ship-audit success cost=$0.2846
04:51:55.39Z  Scheduler tick: dedup gate consulted, dedup_key=2ae6dbdb-... → no re-submit ✓
04:52:23.26Z  Scheduler tick: dedup gate consulted, dedup_key=2ae6dbdb-... → no re-submit ✓
```

Critical absence: no `WARNING:agents.reviewer_agent:[REVIEWER] text-only response round N` warning (which appeared in v3's log at 02:09:26Z). The loop took the tool-use exit branch, not the fallback branch.

### Substrate writes (`workspace_file_versions`, 04:50:13Z–04:53:00Z, yarnnn-author)

| path | authored_by | created_at |
|---|---|---|
| `/workspace/context/authored/governance-as-trust/profile.md` | `operator-proxy:claude-opus-4-7:acting-as-yarnnn-author` | 04:50:13Z (Write 2 — canary transition) |
| `/workspace/review/standing_intent.md` | `reviewer:ai:reviewer-sonnet-v8` | 04:51:13Z |

(Write 1 at 04:50:13Z preceded Write 2 by ~0.4s; only Write 2 is in scope as the transition.)

### `execution_events` row

| field | value |
|---|---|
| `id` | `eb375ec3-...` |
| `slug` | `pre-ship-audit` |
| `wake_source` | `substrate_event` |
| `funnel_decision` | `escalate` |
| `mode` | `judgment` |
| `status` | `success` |
| `tool_rounds` | 8 |
| `cost_usd` | 0.2846 |
| `duration_ms` | 55812 |
| `wake_dedup_key` | `2ae6dbdb-675c-4b4e-99da-b1243bae66a2` (= Write 2's revision_id) ✓ |
| `created_at` | 2026-05-21T04:51:18.866Z |

### Reviewer substrate output quality

The new `standing_intent.md` body is substantively excellent (read in full at `/workspace/review/standing_intent.md`). Salient features:

- Correctly identifies the canary as a status re-transition ("just re-transitioned from draft state per substrate-event hook").
- Anchors against the prior 04:17Z audit ("governance-as-trust essay was approved for publication at 04:17 UTC on May 21 under autonomous delegation").
- Detects an open inconsistency: piece 1 was approved under autonomous delegation but `published_at` is unset. Surfaces this as a concrete Clarify question for the operator ("Is the publication hold deliberate, a system delay, or a test scenario?").
- Defines forward-watch criteria with specific thresholds (anti-pattern counts, Clarify triggers, defer thresholds).
- Acknowledges the cadence-planning gap (no formal piece-writing cadence in `_preferences.yaml`) as a second Clarify candidate.
- Reads as the Reviewer's own voice, not as boilerplate.

This is **the substrate-event reactive path doing exactly what it's designed for**: the Reviewer wakes on a substrate transition, audits the new state against prior corpus and canonical files, and updates its standing intent for the operator's situational awareness.

### Why no `judgment_log.md` entry on v4 (vs v3)

This is **correct parsimony**, not a bug. The judgment_log already carries the 04:17Z `pre-ship-audit` approve verdict for `governance-as-trust`. Write 2 was a status re-transition (`draft → ready_for_review`) on a piece with unchanged content — there is no new decision to log. The Reviewer correctly:

1. Read judgment_log.md (round 1).
2. Recognized the prior approval was still valid.
3. Updated standing_intent.md to reflect the re-transition + open publication question.
4. Closed via ReturnVerdict.

A new judgment_log entry would have been **incorrect substrate** — it would imply a new audit decision when one wasn't made.

## What this means for autonomy

The N=2 substrate-event reactive post-Option-D dataset characterizes as:

- **L1 walker dedup**: 2/2 working (one wake per transition; subsequent ticks short-circuit).
- **L2 round budget**: 2/2 sufficient (v3 used 13, v4 used 8 — both well below the 20-round cap).
- **L3 tool-use closure**: 1/2 closed via ReturnVerdict (v4); 1/2 fell through to text-only fallback (v3).
- **L4 substrate write**: 1/2 produced material substrate writes (v4); 1/2 produced zero writes (v3).

The substrate-event path is **structurally autonomous on the happy path**. The text-only-fallback failure mode is real but probabilistic — it occurred on v3's first read-heavy hook fire after Option D and did not reproduce on v4's identical canary shape ~2.5 hours later.

The probabilistic nature suggests this is **prompt-shape-sensitive**, not framework-broken. The Reviewer model (Sonnet) sometimes self-determines a text-only close on read-heavy hooks. The Hat-A direction recommended by the [prompt-strategy audit stub](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md) — tighten the `pre-ship-audit` hook prompt to structurally bind verdict-emission to `ReturnVerdict + WriteFile` — is the right fix shape. With N=2 evidence (1 success, 1 fallback) it's now justified.

## Recommendation

Open the prompt-strategy audit folder and execute candidate A from the stub: rewrite the `pre-ship-audit` hook prompt's "Decide and emit one of: APPROVE / DEFER / REJECT" line to structurally bind to `ReturnVerdict(verdict=...) + WriteFile(path=/workspace/review/judgment_log.md, ...)` as the close signal.

Until that fix lands, the substrate-event path on read-heavy hooks ships with **a probabilistic silent-failure rate of ~50% on this small sample**. The autonomy story is largely real but has a known calibration gap on this specific prompt class.

**The autonomy story everywhere else looks clean:**
- Walker dedup: 100% (2/2 canaries + 0 production complaints).
- Round budget: 100% (all wakes since Option D used 8-13 rounds, none hit ceiling).
- Chat addressed turns: 100% (04:17Z run wrote 3 substrate updates cleanly).
- Cron-tick judgment wakes: 100% (3 trader personas at 21:01-21:02Z yesterday all wrote substrate).
- Mechanical-mode trackers: 100% (every 30min, no complaints).

## Cross-references

- PLAYBOOK: [./PLAYBOOK.md](./PLAYBOOK.md)
- Round-budget audit + Option D: [`2026-05-21-014009-reviewer-round-budget-population-audit/findings.md`](../2026-05-21-014009-reviewer-round-budget-population-audit/findings.md)
- Prompt-strategy audit stub (now justified to open): [`2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md`](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md)
- Wake-duplication audit (Pattern 1 fix): [`2026-05-21-005856-wake-duplication-audit/findings.md`](../2026-05-21-005856-wake-duplication-audit/findings.md)
- Original substrate-event canary v1: [`2026-05-20-234300-yarnnn-author-substrate-event-canary/`](../2026-05-20-234300-yarnnn-author-substrate-event-canary/)
- Canary v4 harness: [`api/scripts/operator/canary_v4_substrate_event.py`](../../../api/scripts/operator/canary_v4_substrate_event.py)
- Reviewer text-only fallback location: [`api/agents/reviewer_agent.py:1391-1404`](../../../api/agents/reviewer_agent.py#L1391-L1404)
- Wake-dedup gate: [`api/services/wake_sources/substrate_event.py`](../../../api/services/wake_sources/substrate_event.py)
- Hook declaration: [`docs/programs/alpha-author/reference-workspace/_hooks.yaml`](../../programs/alpha-author/reference-workspace/_hooks.yaml)
