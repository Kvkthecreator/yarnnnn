# ADR-363 D3 — within-wake context-editing: probe INCONCLUSIVE on cost, clean on safety

**Date**: 2026-06-24
**Hat**: B (external-developer / evaluation). Funded yarnnn-author (U=0b7a852d).
**Concern**: 1 (context handling) — [ADR-363](../adr/ADR-363-wake-context-handling.md) D3.
**Verdict**: The cost claim is **untested, not falsified**. D3 demoted from "adopt-pending-measurement" to **wired-but-dormant pending a demonstrated need**. The mechanism ships off-by-default; revisit when a real long-wake cost problem surfaces in production.

---

## What was measured

A 3-arm keep-sweep on the real `corpus-coherence-check` prompt (a cross-corpus read-heavy judgment recurrence observed hitting `tool_rounds=20` on this workspace), fired back-to-back through the production path (`_invoke_recurrence_wake`):

| metric | control (edit off) | keep=6 | keep=3 |
|---|---:|---:|---:|
| status | success | success | success |
| verdict=None | **False** | **False** | **False** |
| tool_rounds | 5 | 14 | 11 |
| input (uncached) | 65,375 | 145,189 | 112,108 |
| cache_read | 113,935 | 454,600 | 357,202 |
| cache_create | 48,471 | 0 | 0 |

(trigger=24,000 on both treatment arms.)

## What it established (real)

1. **Safety: mid-loop pruning did NOT break judgment.** No arm flipped the verdict to None, at either `keep=3` or `keep=6`. The failure mode the discourse worried about — context-editing evaporating tool results the verdict still rests on — **did not fire** in this run. This is the one clean signal.
2. **The wiring works end-to-end.** Context-editing routes through `client.beta.messages.*` with the `context-management-2025-06-27` beta joined to prompt-caching; three funded wakes succeeded; the beta path co-exists with prompt-caching (`cache_read` populated on treatment arms — they read the cache control wrote moments earlier within the 5-min TTL).

## What it did NOT establish (the cost claim) — and why

The cost A/B is **confounded by wake-to-wake round-count variance**, which swamps any prune effect:

- The three arms hit **5 / 14 / 11 rounds on the identical prompt**. That spread is the wake doing different amounts of work run-to-run — not context-editing acting. Treatment cost *more* because it ran *longer*, not because editing failed.
- **The probe never captured `applied_edits`** (the response telemetry reporting `cleared_tool_uses` / `cleared_input_tokens`). So it could not even confirm the prune *fired* — at trigger=24k on a wake the control resolved in 5 rounds (~65k input), the trigger plausibly never crossed in the short arm. A token comparison across non-comparable wakes, with no confirmation the mechanism activated, cannot read on cost. *(Fixed post-hoc: `_parse_response` now logs `applied_edits` for any future run.)*

## Why demote rather than chase the win

The broader re-audit ([context-handling-reaudit-2026-06-24](../analysis/context-handling-reaudit-2026-06-24.md)) and the production-history scan already showed the premise is **thin**:

- **verdict=None is rare**: 1 occurrence in 30 days of judgment wakes on this workspace. The behavioral-rescue case D3 hoped for barely exists in production.
- **ceiling-hitting wakes are a small tail**: a handful at `tool_rounds=20` (concentrated in `outcome-reconciliation` / `pre-ship-audit` / `corpus-coherence-check`), each carrying large accumulated cache-read bloat — a *real* cost tail, but small in count.

So the measurable D3 win was always going to be a **marginal cost trim on a small tail**, not a behavioral fix. Spending more funded balance to isolate a marginal win against high wake-variance is poor return. The right posture: **ship the mechanism dormant, off by default, instrumented; let a demonstrated production cost problem (or a deliberate variance-controlled re-run) pull it on.**

## If/when the cost question is reopened — the corrected probe design

The instrument flaws are known and fixable:
1. **Control for wake length.** Fire a deterministically-long recurrence (`outcome-reconciliation` reliably hits 20 rounds), not a variable-length one; and fire ≥2× per arm to bound variance.
2. **Confirm the prune fired.** Read the `[CONTEXT-EDIT] applied …` log line (now emitted by `_parse_response`) — a cost comparison is only valid on wakes where `cleared_input_tokens > 0`.
3. **Lower the trigger** if needed so editing definitely activates on the test wake (12k forces it on most long wakes; 24k may not).
4. **Preserve the governance cache.** Watch `cache_create`/`cache_read`: the comma-joined beta header changes the request shape vs the non-beta cached path — verify caching still pays before crediting context-editing with any token cut.

## Receipts

- execution_events rows: `ctxedit-off-1782282117` (5 rounds), `ctxedit-on-1782282167` (keep=6, 14 rounds), `ctxedit-on-1782282242` (keep=3, 11 rounds), all `user_id=0b7a852d-4a67-447d-91d9-2ba1145a60d7`, 2026-06-24.
- Probe: `api/scripts/operator/probe_context_editing_local.py`.
