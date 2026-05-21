# Canary v4 — Substrate-Event Reactive Wake Revalidation Post-Option-D

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").

**Created**: 2026-05-21T04:45Z server-clock.

**Trigger**: Resolution addendum on [round-budget audit](../2026-05-21-014009-reviewer-round-budget-population-audit/findings.md) reported canary v3 produced text-only response at round 13 instead of `ReturnVerdict + WriteFile`. N=1 evidence is insufficient to distinguish "one-off dice roll" from "prompt-shape-specific gap on `pre-ship-audit`". Operator chose canary v4 to drive N=2 evidence before opening the broader [prompt-strategy audit stub](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md).

## What this canary tests

Same shape as canary v2 + v3 — a two-flip transition of `status` frontmatter on `governance-as-trust/profile.md`. The fourth layer of the test is the only open question; the first three are confirmed working from prior runs.

| Layer | What's tested | Pre-Option-D | Post-Option-D (v3) | This run (v4) |
|---|---|---|---|---|
| L1 walker dedup | One transition → one wake | 6 wakes | 1 wake ✓ | confirm 1 wake |
| L2 round budget | Reviewer can use 7+ rounds on read-heavy hook | 70% silent @ round 6 | 13 rounds ✓ | confirm 7+ rounds |
| L3 tool-use closure | Reviewer calls `ReturnVerdict + WriteFile` to close | counter-nudge coached it | **text-only fallback** ✗ | **open question** |
| L4 substrate write | `judgment_log.md` + `standing_intent.md` written | sometimes | **NOT written** ✗ | **open question** |

L3/L4 are the bits canary v4 disambiguates. Two outcomes:

- **L4 writes happen** → v3 was a one-off, the substrate-event path is good, autonomy ships on this path.
- **L4 writes don't happen again** → text-only fallback is the dominant exit pattern for read-heavy reactive wakes. Prompt-strategy audit opens with N=2 evidence; Hat-A direction is to tighten the `pre-ship-audit` hook prompt to structurally bind verdict-emission to `ReturnVerdict + WriteFile`.

## Baseline (T0 — 2026-05-21T04:45Z server-clock)

### Workspace state

- `governance-as-trust/profile.md` currently at `status: ready_for_review` (from the prior canary v3 flip).
- Last Reviewer write: 2026-05-21T04:18:35Z on `/workspace/review/judgment_log.md` (addressed-turn, not reactive — different code path).
- Last reactive substrate-event wake: 2026-05-21T02:09:26Z (canary v3, the one that produced text-only fallback).
- Zero `execution_events` rows since canary v3.

### Hook declaration

`docs/programs/alpha-author/reference-workspace/_hooks.yaml` declares `pre-ship-audit` to fire on `field_change: { status: ready_for_review }` matching path glob `/workspace/context/authored/*/profile.md`.

### Code state under test

- `wake_dedup_key` on `execution_events` (commit `fa22788`, live since 2026-05-21T01:08Z on Scheduler). Validates L1.
- Counter-nudge `_round >= 4` deleted, `max_rounds` raised 12 → 20 (commit `e8017d3`, live 2026-05-21T02:01-02:02Z on Scheduler). Validates L2.
- No fix yet for L3/L4. This canary characterizes the gap.

## Trigger plan

Two writes, both authored as `operator-proxy:claude-opus-4-7:acting-as-yarnnn-author` per ADR-294 D2:

1. **Write 1** (status: `ready_for_review` → `draft`): edit `governance-as-trust/profile.md` frontmatter `status` field.
2. **Write 2** (status: `draft` → `ready_for_review`): flip back. **The second write is the transition the walker fires on.**

Both writes happen back-to-back. The walker has a 30-minute lookback (per `services/wake_sources/substrate_event.py::walk_hooks`); the scheduler tick cadence is `*/1 * * * *` (every minute on the Scheduler cron). Expected first wake within ~1-2 minutes of Write 2.

## Expected behavior

Within ~2 minutes of Write 2:

1. `walk_hooks(client, user_id)` runs at next scheduler tick.
2. Walker queries `workspace_file_versions` since (now - 30min), finds Write 2.
3. `_matches_hook` checks: path glob ✓, `status` transitioned `draft` → `ready_for_review` ✓.
4. Dedup check on `wake_dedup_key=<revision_id>` — first sight, no prior row → proceeds.
5. `submit_wake_proposal(source="substrate_event", payload={hook, path, field_change, revision_id})`.
6. Funnel evaluates → `escalate`.
7. Reviewer wakes with hook prompt as envelope.
8. Reviewer reads declared files (8+ files: draft, content, voice, editorial, corpus, recurrences, standing_intent, judgment_log).
9. Reviewer calls `ReturnVerdict(verdict=approve|defer|reject) + WriteFile(/workspace/review/judgment_log.md) + WriteFile(/workspace/review/standing_intent.md)`.
10. `execution_events` row appears with `slug='pre-ship-audit'`, `wake_source='substrate_event'`, `funnel_decision='escalate'`, `mode='judgment'`, `status='success'`.

L4 success = both substrate writes present in `workspace_file_versions` with `authored_by='reviewer:ai:reviewer-sonnet-v8'` within ~5 minutes of the wake's `created_at`.

L4 failure (matching v3 pattern) = wake row present, status='success', but ZERO substrate writes between wake start and wake end.

## What this folder does NOT do

- No system canon edits. Any L3/L4 fix surfaces in `findings.md` for a separate Hat-A commit per the three-commit cross-hat discipline (CLAUDE.md §"The Two Hats").
- No chat messages to YARNNN (chat path was tested separately at 04:17Z and works — different code path).
- No edits to anything beyond `profile.md` frontmatter (just the two status flips).
- No touch to alpha-trader workspaces.

## Cross-references

- Prior canary v3 + Option D resolution: [`2026-05-21-014009-reviewer-round-budget-population-audit/findings.md`](../2026-05-21-014009-reviewer-round-budget-population-audit/findings.md) §"Resolution addendum 2026-05-21T02:11Z"
- Prompt-strategy audit stub (motivated by v3): [`2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md`](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md)
- Wake-duplication audit (Pattern 1 fix, validated by canary v2): [`2026-05-21-005856-wake-duplication-audit/findings.md`](../2026-05-21-005856-wake-duplication-audit/findings.md)
- Original substrate-event canary (canary v1): [`2026-05-20-234300-yarnnn-author-substrate-event-canary/PLAYBOOK.md`](../2026-05-20-234300-yarnnn-author-substrate-event-canary/PLAYBOOK.md)
- Walker code: [`api/services/wake_sources/substrate_event.py`](../../../api/services/wake_sources/substrate_event.py)
- Reviewer loop with Option D fix: [`api/agents/reviewer_agent.py`](../../../api/agents/reviewer_agent.py)
- Hook declaration: [`docs/programs/alpha-author/reference-workspace/_hooks.yaml`](../../programs/alpha-author/reference-workspace/_hooks.yaml)
- Three-commit cross-hat discipline: CLAUDE.md §"The Two Hats", commit `3ba880b`
