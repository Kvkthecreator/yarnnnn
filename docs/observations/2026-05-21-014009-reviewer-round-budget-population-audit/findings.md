# Reviewer Round-Budget Population Audit — Nudge-Threshold Mis-Calibration

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats"). One-document folder — population audit, no canary needed; the data was already sitting in `execution_events` + `workspace_file_versions`.

**Trigger**: Operator pushback against the prior session's stub recommendation that we "wait for 2-3 more wakes before deciding." Operator correctly observed that **we already have a population dataset in the DB** — `execution_events` carries every judgment-mode wake ever fired, `workspace_file_versions` carries every Reviewer-authored write. Joining the two characterizes the pattern empirically.

**Captured**: 2026-05-21T01:40Z server-clock. N=28 judgment-mode wakes across 4 workspaces (2abf3f96 / 2be30ac5 / 29a74c63 / 0b7a852d). Population spans 2026-05-18T05:01Z (oldest reflective wake) through 2026-05-21T01:20Z (canary v2 wake).

## Headline finding

**The Reviewer's tool-use loop ships with a "round 5+ nudge" that pushes the Reviewer toward `stand_down` BEFORE read-heavy hook prompts have completed their read-then-write cycle.** This is a **prompt-nudge mis-calibration**, not a round-budget exhaustion. The configured budget is 12 (Haiku) / 3 (Sonnet); the *effective* budget for productive wakes is bounded below by the nudge at round 5+ (`_round >= 4` in code, 0-indexed).

Population evidence: at `tool_rounds = 6`, 70% of wakes are silent (no substrate written). At `tool_rounds ≥ 7`, only 11% are silent. The threshold is sharp and lives at the nudge boundary, not the budget cap.

## The data

### Histogram: round-count distribution vs whether wake wrote substrate

| `tool_rounds` | Total wakes | Productive (wrote) | Silent (no write) | Silent % |
|---|---|---|---|---|
| 6 | 10 | 3 | **7** | **70%** |
| 7 | 9 | 8 | 1 | 11% |
| 8 | 3 | 2 | 1 | 33% |
| 9 | 4 | 4 | 0 | 0% |
| 10 | 2 | 2 | 0 | 0% |

The discontinuity at round 6 → 7 is the nudge boundary. Wakes that get past round 6 almost always produce useful output; wakes that stop at round 6 almost always stand_down silently.

### Per-slug + wake_source breakdown

| Slug | Wake source | Total | Silent | Silent % | Silent avg rounds | Productive avg rounds | Silent avg dur | Productive avg dur |
|---|---|---|---|---|---|---|---|---|
| `pre-ship-audit` | substrate_event | 7 | **5** | **71.4%** | **6.0** | 8.5 | 27.1s | 69.4s |
| `outcome-reconciliation` | (null pre-ADR-296) | 9 | 3 | 33.3% | 6.7 | 7.7 | 47.3s | 57.2s |
| `outcome-reconciliation` | cron_tick | 3 | 0 | 0% | — | 6.7 | — | 38.2s |
| `signal-evaluation` | (null pre-ADR-296) | 3 | 1 | 33.3% | 7.0 | 8.5 | 47.6s | 64.5s |
| `signal-evaluation` | cron_tick | 3 | 0 | 0% | — | 7.7 | — | 52.7s |
| `corpus-coherence-check` | (null pre-ADR-296) | 3 | 0 | 0% | — | 7.7 | — | 66.4s |

**`pre-ship-audit` is the most affected**: 71% silent rate, average 6.0 rounds on silent wakes (perfectly aligned to the nudge boundary). The slug has a known read-heavy prompt (8+ files in the hook declaration: draft + content + voice + editorial + corpus + recurrences + standing_intent + judgment_log).

### Path-level evidence

Productive wakes consistently write to one of: `review/judgment_log.md`, `review/standing_intent.md`, `_recurrences.yaml`. Silent wakes write to none. There is no "wrote-but-to-an-unexpected-path" intermediate class — wakes either reach the verdict-write step or they don't.

## Root cause — the nudge

`api/agents/reviewer_agent.py` line 1506:

```python
elif _round >= 4:
    nudge = (
        f"You are on round {_round + 1} of {max_rounds}. You must call "
        "ReturnVerdict next to close this turn. Synthesize what you've "
        "learned from substrate above into a verdict + reasoning. Even "
        "if conditions are unclear, ReturnVerdict(stand_down) with your "
        "honest assessment is correct."
    )
```

The nudge fires starting round 5 (0-indexed `_round >= 4`). The text explicitly tells the Reviewer that `stand_down` is "correct" even when conditions are unclear — an invitation, not a constraint. Reviewers on read-heavy hooks are still mid-read at round 5 and the nudge lets them gracefully exit before completing the audit they were woken for.

The nudge's design intent (per the inline comment `# Loop-shape nudges to prevent runaway tool use`) is sound for short hooks where the Reviewer would otherwise spin on cognition reads forever. It's mis-calibrated for read-heavy hooks where 5-6 reads are legitimately required before the write step.

### Why the budget itself (12) doesn't help

The configured budget is 12 rounds for Haiku-driven recurrence/substrate wakes. Population data shows ZERO wakes hitting rounds 11 or 12. The nudge converts the budget from "12 rounds" to "effectively 6-7 rounds" because the Reviewer obeys the nudge's invitation.

The previous "fix this by raising the budget" framing the prior session's resolution addendum surfaced is **wrong**. Raising `max_rounds` from 12 to 20 wouldn't help — the nudge would still fire at round 5 and the Reviewer would still stand_down.

## Why the prior session canary "looked" inconsistent

Same canary, two outcomes:
- **Parent session run (2026-05-21T00:11-00:17Z)**: 6 redundant wakes (Pattern 1 pre-fix). Of those 6, two managed to write standing_intent (at rounds 8 and 9). Most stand_downed at round 6.
- **This session canary v2 (2026-05-21T01:20Z)**: 1 wake (Pattern 1 fix engaged). It stand_downed at round 6.

The "intermittent productive" outcome of the prior session was a 2-out-of-6 dice roll — wakes #1 and #5 happened to choose more rounds before stand_down (rounds 8 and 9 respectively, both ≥ 7). Pattern 1's bug masked this — the redundancy increased the odds that AT LEAST ONE of the 6 wakes would reach round 7+. Fixing Pattern 1 to one-wake-per-transition exposes the underlying nudge mis-calibration.

**This is the "Pattern 1 fix surfaces a downstream gap" finding the prior addendum hinted at, now characterized in full.**

## Cross-workspace blast radius

The pattern is workspace-agnostic. Affected workspaces in the population:

| user_id | Affected slugs (silent / total) |
|---|---|
| `0b7a852d` (yarnnn-author) | pre-ship-audit (5/7), outcome-reconciliation (1/3) |
| `2abf3f96` (alpha-trader / kvk) | outcome-reconciliation (3/6), signal-evaluation (1/3) |
| `2be30ac5` (alpha-trader-2) | signal-evaluation (1/3), outcome-reconciliation (1/3) |
| `29a74c63` (other alpha-trader persona) | (mostly productive) |

Every program with read-heavy hooks/recurrences will hit this. As more operators activate programs and the corpus of hooks grows, the silent-wake fraction scales with average read-burden-per-prompt.

## Fix shape recommendations (Hat-A action)

The nudge needs to be **read-burden-aware**, not round-count-aware. Three candidate shapes:

### Option A — Raise the nudge threshold

Change `_round >= 4` to `_round >= 8` (nudge fires at round 9 of 12 instead of round 5). Smallest change. Population data suggests round 9 + would still leave 3-4 rounds of head room before the budget cap.

**Risk**: read-heavy hooks could spin to round 8 on cognition-only without writing. The nudge was added (per the inline comment) to PREVENT runaway loops on prompts that drift into cognition-only modes. If we raise the threshold too high, we risk re-introducing the runaway-loop class of failure the nudge was designed to prevent.

### Option B — Make the nudge conditional on the wake's prompt shape

A prompt that declares "read N files then write" should get a different nudge threshold than a prompt that's discrete-decision-shaped. The wake's hook declaration / recurrence YAML could carry a hint (`expected_round_budget: 10`) that the loop reads to defer the nudge.

**Risk**: requires every hook author to think about round-budget, which couples hook prompts to a runtime concern. Adds vocabulary the system shouldn't need.

### Option C — Soften the nudge's invitation to stand_down

The nudge currently says *"Even if conditions are unclear, ReturnVerdict(stand_down) with your honest assessment is correct."* This is an explicit invitation to stop. The more disciplined framing: *"You are on round 5 of 12 — synthesize toward verdict in next 1-2 rounds, OR continue reading if you haven't yet read the required substrate."* Let the Reviewer judge whether it has enough; don't pre-decide that stand_down is acceptable at round 5.

**Risk**: looser nudge → more cost on legitimate runaway-loop edge cases. But population data shows zero existing wakes hit round 10+, so the runaway-loop risk seems already low in production.

### Recommended sequence

The Hat-A discipline says "don't pre-fix what observation hasn't validated." The population audit IS the observation — N=28 across all workspaces shows the pattern is empirical, not anecdotal. The fix is justified now.

Between A / B / C, I'd recommend **Option C (soften the nudge) + Option A (raise threshold to round >= 7)** combined as a single commit:

1. Move `_round >= 4` → `_round >= 6` (nudge fires at round 7 of 12 — past the empirical threshold where productive wakes consistently complete).
2. Soften the nudge text to remove the "stand_down is correct" invitation; replace with "continue reading or synthesize toward verdict — your judgment."

Both changes target the same artifact (the nudge), can be tested with the same regression mechanism (re-fire the canary, observe whether the wake reaches verdict-write step), and don't require schema changes or new vocabulary.

**Singular implementation discipline**: one nudge edit, one commit, one regression observation.

## What this folder does NOT do

- No system canon edits. The fix is a Hat-A commit referencing this folder by path per the three-commit-shape discipline (CLAUDE.md §"The Two Hats", commit `3ba880b`).
- No new audit dimensions. The pattern is well-characterized by the existing population; further data would add resolution but not change the conclusion.
- No Hat-A commits batched with this finding because the fix shape is the open question — operator chooses between Option A / B / C / combined before Hat-A executes.

## Cross-references

- Nudge code: [`api/agents/reviewer_agent.py:1506-1513`](../../../api/agents/reviewer_agent.py#L1506-L1513)
- Round-budget config: [`api/agents/reviewer_agent.py:1306`](../../../api/agents/reviewer_agent.py#L1306) (`max_rounds = 3 if use_sonnet else 12`)
- ReturnVerdict tool definition: [`api/agents/reviewer_agent.py:204-225`](../../../api/agents/reviewer_agent.py#L204-L225)
- Prior session's wake-duplication audit (which surfaced the round-budget concern as deferred follow-on): [`2026-05-21-005856-wake-duplication-audit/findings.md`](../2026-05-21-005856-wake-duplication-audit/findings.md) §"New surface: Reviewer round-budget exhaustion on read-heavy hooks"
- Substrate-event canary that exposed the pattern: [`2026-05-20-234300-yarnnn-author-substrate-event-canary/findings.md`](../2026-05-20-234300-yarnnn-author-substrate-event-canary/findings.md)
- alpha-author hook prompt that's most affected: [`docs/programs/alpha-author/reference-workspace/_hooks.yaml`](../../programs/alpha-author/reference-workspace/_hooks.yaml) (pre-ship-audit)
- ADR-260 round-bound rationale: ADR-260 D8 + ADR-263 (referenced in the code comment at line 1301-1305)

## Capture method (reproducibility)

All findings derived from two SQL aggregates against Supabase prod:

1. Per-wake join: `execution_events` (mode='judgment', status='success', tool_rounds NOT NULL) LEFT JOIN `workspace_file_versions` (authored_by LIKE 'reviewer:%', created_at within [`wake_start, wake_end`]) where `wake_start = created_at - duration_ms`. Yields one row per wake with substrate-write count.

2. Histogram aggregate of the join: `GROUP BY tool_rounds, COUNT(*) FILTER (WHERE wrote)`.

Plus code reads against `api/agents/reviewer_agent.py` to locate the nudge mechanism + Render log inspection to confirm the canary v2 wake's tool-call sequence (14 reads, no writes, exit at round 6).

No operator-proxy writes, no chat messages issued. Hat-B observation-only discipline preserved.
