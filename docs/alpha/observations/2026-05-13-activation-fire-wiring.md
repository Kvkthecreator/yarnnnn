# 2026-05-13 — Activation-fire wiring — close the cold-start gap

> **Type**: Architectural-shift observation. Records the scheduler + bundle changes that make activation an active substrate-population moment instead of a passive scaffolding-then-silence one. Companion to the same-day regime wiring observation (2026-05-13-regime-wiring.md).
> **Trigger**: Multi-turn architectural discourse on 2026-05-13. Started as "should we have a research workspace / Researcher agent" question; first-principles stress test revealed the actual gap was that *recurrences are over-relied-on as the only first-class shape for substrate accumulation*, and the smallest fix was making activation a fire-trigger.
> **Persona**: bundle-wide change. Verification path against `seulkim88` (alpha-trader persona) workspace.

---

## Classification

- **Objective**: A-system (primary). Activation-fire is structural infrastructure that gates *whether the first cycle has substrate to reason against*.
- **Within-A scope**: systematic-workflow (new scheduler conditional + new bundle recurrence) + substrate-shape (new `/workspace/research/` convention).
- **FOUNDATIONS dimension**: Trigger (new deterministic fire-at-activation pattern within existing periodic umbrella) + Substrate (new research-substrate convention) + Mechanism (scheduler conditional, judgment recurrence).
- **Severity**: declarative-unenforced-by-experience (same trap class as iter-2 L3 + the regime wiring). System's claim of "accumulating, compounding intelligence" was structurally true post-fork but operator-experienced as "scaffolded inbox waiting for cron."
- **Resolution path**: bundle-level evolution + minimal kernel change (one conditional in `compute_next_run_at`). ADR-270 documents the kernel change; bundle changes follow ADR-270 §D6 (operator-authored at bundle layer).
- **Money impact**: indirect. Before this change, the Reviewer's first proposal post-activation had no substrate to reason against (`_money_truth.md` empty + no regime + no per-ticker bars + no historical findings). After: each of those substrate files exists within the first scheduler tick.

---

## What was wrong

The activation experience produced this sequence:

| T+ | What happened | Operator-experienced reality |
|---|---|---|
| 0 | Operator activates persona | Click; spinner; success message |
| seconds | Bundle fork writes files into `/workspace/` | Files exist on disk, invisible to operator surface |
| seconds | `materialize_scheduling_index` runs, populates `tasks` table | Scheduler now knows about the recurrences |
| minutes-to-hours | Wait for next periodic fire | Cockpit faces empty, feed silent, no progress visible |
| eventually | First periodic recurrence fires per its cron | Substrate starts populating |

For US-market-bound recurrences activated outside RTH (e.g., 22:00 KST on a weekday for an alpha-trader workspace), the eventually-window is **11.5 hours**. The operator's first lived YARNNN experience is *nothing happens visibly for 11.5 hours after I clicked activate*.

This is not a bug — every individual piece works correctly. It's a *gap between what canon claims about the architecture* (accumulating, compounding intelligence) *and what the operator's activation experience demonstrates* (dead-quiet substrate). Same trap class as iter-2's three-layer trade-execution gap: substrate declares intent, runtime doesn't enforce it at the moment it matters.

---

## What shipped

Two surfaces of change, both atomic in one commit:

### Kernel (one conditional)

`api/services/scheduling.py::compute_next_run_at` — one branch at the top of the function:

```python
if rec.options.get("fire_on_activation") and last_run_at is None:
    return now_utc
```

The change is structural: recurrences with `fire_on_activation: true` and no prior `last_run_at` return `now` from `compute_next_run_at`, so `materialize_scheduling_index` writes `next_run_at = now`, and the next scheduler tick picks the row up immediately. After the first fire records `last_run_at`, subsequent calls fall through to the regular schedule.

No new dataclass field — `rec.options` (the existing absorb-unknown-keys surface) carries the flag transparently. No new primitive. No new trigger sub-shape. The scheduler is still the single dispatch path; activation fires are just rows that happen to be due immediately.

### Bundle (operator-facing changes)

- **Three existing recurrences marked `fire_on_activation: true`**: `track-account` (broker account snapshot), `track-regime` (VIXY + SPY regime substrate per [ADR-269](../adr/ADR-269-capability-flow-wiring.md) flow + the 2026-05-13 regime-wiring change), `track-universe` (per-ticker bar snapshots feeding signal-evaluation).
- **One new recurrence**: `falsify-signals` — `schedule: null` (reactive) + `fire_on_activation: true`. Walks 90 days of historical bars through each operator-declared signal, writes per-signal findings to `/workspace/research/findings/{signal_id}.md`. Bootstrap-only — no periodic schedule, re-fires only on explicit `FireInvocation`.
- **New `/workspace/research/mandate.md`**: operator-facing standing intent for the research substrate. Names fidelity gaps honestly (no slippage model, survivorship bias, no regime conditioning).
- **New `/workspace/specs/falsify-signals.md`**: schema for findings files (frontmatter with sample_size, win_rate, avg_win_R, expectancy_R, source: replay, baseline_status).
- **`/workspace/review/principles.md` extended**: Capital-EV section now references `/workspace/research/findings/{signal_id}.md` alongside `_money_truth.md`. Rule: live data weighs more than replay findings; replay-only-below-baseline is a soft warning not an auto-reject.

### Net diff

~5 files changed, ~250 LOC added. One kernel conditional. Four bundle additions. Zero new primitives, zero new agent classes, zero registry changes.

---

## Why this shape (decision rationale traceable to discourse)

The discourse considered three richer shapes before settling on this one:

| Shape considered | Why rejected |
|---|---|
| Dedicated learning-playbook userspace ("Option A — separate workspace for operator + Claude learning") | Doesn't strongly serve money-truth objective; operator-mediated promotion between workspaces is friction without clear architectural payoff |
| Extended workspace with replay-as-platform-connection (Shape A/B/C from prior turn) | Over-architected for the actual gap; introduces a new platform-connection variant when the existing recurrence machinery can do the work |
| New Researcher Agent class as systemic peer of Reviewer | Stress-test against the primitives matrix showed *no judgment capability is structurally absent from the existing framework* — a Researcher seat would be a recurrence with attribution dressed as a persona |

The first-principled rest after stress-testing: **the framework already supports cold-start substrate population via the existing recurrence machinery; what's missing is a way for bundles to mark recurrences for activation-fire.** ADR-270 is that.

---

## What this does NOT do (deliberate non-actions per ADR-270 §3 "Earned escalation")

Three richer patterns were explicitly deferred:

1. **Chat-callable reactive recurrence invocation as first-class operator gesture.** Today `FireInvocation` exists in the primitive set but has no chat-surface convention for "operator says 'run X now'". Deferred until operator observation shows the verb is wanted often.
2. **Ad-hoc chat exploration writes substrate by default.** Convention discipline ("what counts as substantive enough to retain") wants operator input before shipping. Deferred.
3. **Periodic `falsify-signals` schedule.** Bundle ships it as one-shot. If observation shows ongoing falsification is load-bearing, a future bundle revision adds a periodic schedule. Earned by evidence per `research/mandate.md` §"Earned escalation".

The escalation pattern: ship the smallest version, observe lived experience, promote a deferred piece into shipped substrate when evidence justifies. Same discipline as AUTONOMY.md's Phase 0 → Phase 1 graduation.

---

## Verification path

Post-merge, verification runs against `seulkim88` persona (alpha-trader workspace, user_id `2be30ac5-...`):

1. **`reset.py --persona alpha-trader --confirm`** — purge workspace to cold state. Confirm `tasks` rows are dropped.
2. **`activate_persona.py --persona alpha-trader`** — fork bundle, materialize index. Expect logs to show:
   - `[FORK] materialized scheduling index for 2be30ac5: N rows` (N = total recurrences in bundle)
   - For activation-fired recurrences: `next_run_at` set to fork-time, not next cron tick
3. **`connect.py alpha-trader`** — wire Alpaca paper credentials.
4. **Wait one scheduler tick (60 seconds max).** Within the first minute post-connect:
   - `/workspace/context/portfolio/_account.yaml` exists with broker account snapshot
   - `/workspace/context/trading/_regime.yaml` exists with current VIXY + SPY regime (or `data_stale: true` if outside RTH)
   - `/workspace/context/trading/{ticker}.yaml` exists for each universe member
   - `/workspace/research/findings/{signal_id}.md` exists for each declared signal with `source: replay` frontmatter
5. **Feed surface check**: 4-7 system-attributed entries within the first minute (activation burst).
6. **`verify.py alpha-trader`** — invariant check should pass (existing invariants unchanged; new substrate doesn't break old assertions).

### What would falsify the change

If `/workspace/research/findings/` ends up empty post-activation (no findings files written), the L3 capability flow may still have a bug on the `falsify-signals` recurrence's specialist dispatch path. Per iter-2's observation, capability-flow wiring is still queued for full E2E validation. Falsify-signals exercises that path as a high-volume historical-bar fetch — a useful stress test.

If activation-fired recurrences fire but periodic recurrences don't subsequently follow their normal schedule, the `last_run_at` update path post-activation is broken. Should not happen — the scheduler's `record_task_run` path is unchanged.

---

## Friction (honest list)

1. **Activation outside RTH still produces stale-ish data.** `track-universe` activation-fires regardless of RTH state, fetching whatever bars Alpaca returns (which may be stale if activated on a weekend). The recurrence prompt handles stale data (`data_stale: true` flag in ticker.yaml) but the cockpit doesn't yet visually distinguish stale-from-activation vs stale-from-failure. Cosmetic, not load-bearing.

2. **`falsify-signals` is expensive on cold-start.** Walks 90 days × 1Hour bars × N tickers × N signals through the Reviewer's specialist dispatch path. First activation could consume meaningful tokens. Token budget pressure surfaces if `_autonomy.yaml::ceiling_cents` is low — but this is a one-shot cost, amortizable.

3. **Operator may re-reset and re-activate often during alpha.** Each cycle re-fires `falsify-signals` (intended per ADR-270 D3), which means re-paying the token cost each time. Acceptable during alpha when activation is intentional; would want a "skip falsify-signals on re-activation if findings are fresh" gate before scaling — but that's future scope.

4. **Bootstrap exception in `principles.md` is now layered.** Rule 7 has a bootstrap exception for missing `_regime.yaml`; rule on the new research-findings layer has its own "trade them anyway" disposition. Two bootstrap clauses with similar shape. Probably fine; watch for confusion when both fire in the same cycle.

---

## Links

- **ADR**: [ADR-270 Fire-on-Activation Recurrences](../adr/ADR-270-fire-on-activation-recurrences.md)
- **Kernel change**: `api/services/scheduling.py::compute_next_run_at` — one conditional at the top of the function
- **Bundle changes**: `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`, `review/principles.md`, new `research/mandate.md` + `specs/falsify-signals.md`
- **Companion observation (same day)**: [2026-05-13-regime-wiring.md](./2026-05-13-regime-wiring.md) — regime substrate wired, predates and motivates this change
- **Predecessor framing**: [2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md](./2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md) — iter-2 named the trap class this change addresses at a different layer
- **Discourse summary**: this observation doc + ADR-270 §7 (Discourse context for trace) — multi-turn architectural conversation that converged from "should we have a Researcher Agent" to "activation should be an active substrate-population moment"
- **Verification persona**: `seulkim88@gmail.com` → persona slug `alpha-trader` → user_id `2be30ac5-b3cf-46b1-aeb8-af39cd351af4` → workspace_id `b7e1b9bc-ffb3-478e-bd05-dcae01a8a6b1`

---

## Verification findings (2026-05-13, post-deploy 914086f)

Ran the verification chain against seulkim88 immediately after both API and Scheduler services went live on `914086f`. Findings in order:

### What confirmed working

1. **Reset + activation fork wrote bundle correctly.** `reset.py alpha-trader --confirm` returned success; reset endpoint inline-called `initialize_workspace(program_slug='alpha-trader')` which re-forked the bundle and re-materialized the scheduling index. 30 files in `workspace_files`, including both new bundle files:
   - `/workspace/research/mandate.md` (ADR-270 new)
   - `/workspace/specs/falsify-signals.md` (ADR-270 new)
   And the regime spec from the earlier commit:
   - `/workspace/specs/regime-state.md` (2026-05-13-regime-wiring.md)

2. **`fire_on_activation` conditional fires correctly in `compute_next_run_at`.** Direct psql verification of `tasks` table for seulkim88 user_id, immediately after reset:
   ```
   slug              | next_run_at                       | last_run_at
   falsify-signals   | 2026-05-13 05:57:39.406559+00     | NULL  ← reactive (schedule=null)
   track-account     | 2026-05-13 05:57:39.406559+00     | NULL  ← @every 5min
   track-regime      | 2026-05-13 05:57:39.406559+00     | NULL  ← @market_close+30min
   track-universe    | 2026-05-13 05:57:39.406559+00     | NULL  ← list-form schedule
   ```
   All four flagged recurrences have `next_run_at` = the activation moment (same timestamp across all four, confirming a single materialize-index call). Non-flagged recurrences in the same table have either future cron-resolved next-run-at (`morning-calibration`, `morning-reflection`, etc.) or NULL (semantic schedules requiring market-context resolution outside RTH — `pre-market-brief`, `signal-evaluation`, `track-positions`, etc.). The kernel conditional is doing exactly what ADR-270 D2 specifies, including for the list-form schedule on `track-universe`.

### What I could not verify (and why)

3. **End-to-end recurrence dispatch.** `connect.py alpha-trader` returned "Missing credentials. Set ALPHA_TRADER_ALPACA_KEY and ALPHA_TRADER_ALPACA_SECRET in env." — seulkim88's Alpaca paper credentials are commented out in `api/.env.alpha-ops` (only kvk's are uncommented). Without an active `platform_connections` row, the activation-fired recurrences cannot complete their bodies (every one needs `platform_trading_*` tool access). This is operator-private credential management, not a code issue.

### What the verification revealed about an existing scheduler interaction

4. **Re-fire-on-failure pattern surfaced.** Three minutes after reset, the four ADR-270 rows' `next_run_at` had advanced from `05:57:39` to `06:00:47`, but `last_run_at` was still NULL. Combined with zero entries in `activity_log` since reset, this means:
   - Scheduler tick **is** picking up the rows and calling `materialize_scheduling_index` (otherwise `next_run_at` wouldn't move).
   - Scheduler **is** attempting dispatch (the row was due).
   - Dispatch **is failing before `record_task_run` is called** (no `last_run_at` write, no activity event).
   - On the next tick, my conditional re-fires `now_utc` (because `last_run_at` is still NULL), and the cycle repeats.

   **This is an existing scheduler property, not an ADR-270 bug.** Any recurrence whose dispatch body fails before `record_task_run` would loop the same way regardless of `fire_on_activation`. ADR-270 surfaces it more visibly because activation-fired recurrences expect rapid first dispatch.

   The failure here is correctly localized to "no Alpaca connection," not to the scheduler/kernel path. Once `connect.py` lands credentials and creates a `platform_connections` row, the next tick should succeed and the cycle terminates.

   **Tolerable property for now** — activation-fired recurrences will loop quietly until they succeed (no LLM cost for the mechanical mirrors like `track-account` because they fail at the platform-tool call boundary). But it's a property worth knowing about: if a persistent failure mode existed in a judgment-mode activation-fired recurrence (which would consume LLM tokens on each tick), it could quietly burn budget. **Future scope** — a "max re-fire count for fire_on_activation" or "exponential backoff on consecutive failures with no last_run_at" gate. Not shipping now; flagged here for the record.

### Verification status summary

| Layer | Status |
|---|---|
| Kernel conditional in `compute_next_run_at` | ✅ verified working |
| Bundle YAML parsing (`fire_on_activation` absorbed into `rec.options`) | ✅ verified — flag round-trips through parser → dataclass → scheduler |
| `materialize_scheduling_index` writes `next_run_at = now` for flagged rows | ✅ verified |
| Bundle fork writes new `research/mandate.md` + `specs/falsify-signals.md` | ✅ verified |
| Scheduler tick picks up due rows | ✅ verified (indirect — `next_run_at` advances) |
| Dispatch completes successfully + writes substrate | ❌ blocked on Alpaca credentials (operator-private) |
| Falsify-signals produces `/workspace/research/findings/{signal_id}.md` | ❌ blocked on above |
| L3 capability-flow path (iter-4) exercised end-to-end | ❌ blocked on above |

### What unblocks full E2E

Operator uncomments `ALPHA_TRADER_ALPACA_KEY` and `ALPHA_TRADER_ALPACA_SECRET` in `api/.env.alpha-ops` (or sets them in env via the operator-side path documented in `docs/alpha/OPERATOR-HARNESS.md`), then `python api/scripts/alpha_ops/connect.py alpha-trader`. After the next scheduler tick, the four activation-fired rows should each execute their bodies once, set `last_run_at`, write substrate, and stop looping. Filesystem inspection at that point should show:
- `/workspace/context/portfolio/_account.yaml` populated
- `/workspace/context/trading/_regime.yaml` populated
- `/workspace/context/trading/{ticker}.yaml` populated per universe member
- `/workspace/research/findings/{signal_id}.md` populated per declared signal

`verify.py alpha-trader` should pass invariants.

---

## Full E2E findings (2026-05-13, post-credentials)

Operator added seulkim88's Alpaca paper credentials (account X4DJ) to `api/.env.alpha-ops`; `connect.py alpha-trader` succeeded; manually reset `last_run_at = NULL` on the four ADR-270 rows (because the pre-credentials run had marked them complete via failed dispatch — see §"What the verification revealed about an existing scheduler interaction" above). Scheduler tick post-credentials produced these outcomes:

| Recurrence | Dispatched | last_run_at | Substrate written | Verdict |
|---|---|---|---|---|
| `track-account` | ✓ | 06:13:25 | `/workspace/context/portfolio/_account.yaml` — real Alpaca data (PA3D05L0X4DJ, equity $100,028.14) | **PASS** — full E2E success |
| `track-regime` | ✓ | 06:14:00 | None observed (no `_regime.yaml` write) | Partial — dispatched but didn't write |
| `track-universe` | ✓ | 06:14:37 | `/workspace/context/trading/_run_log.md` — failure note: Reviewer couldn't resolve correct tool name, tried `platform_trading_get_bars` + `get_bars`; both rejected. Correct name is `platform_trading_get_market_data`. | **FAIL** — bundle prompt + tool resolution mismatch (iter-4 L3 surface issue) |
| `falsify-signals` | ✓ | 06:15:17 | `/workspace/review/decisions.md` — Reviewer correctly recognized "this is deterministic work, not judgment, attempting inline would hallucinate," attempted DispatchSpecialist(role=researcher) but received execution error; deferred per principles. | **Partial — exemplary failure** (Reviewer reasoning correct, infrastructure error blocked work) |

### What the full E2E validates

1. **ADR-270's kernel conditional is fully verified end-to-end.** `track-account` ran the complete fire-on-activation → SyncPlatformState → Alpaca API → substrate-write cycle in under 1 second after the scheduler tick that followed `materialize_scheduling_index`. The mechanical recurrence path works as designed.

2. **`verify.py alpha-trader` returns 32/32 invariants passing.** The activation chain is structurally sound; the failures are in *downstream specialist dispatch*, not in activation infrastructure.

3. **Reviewer reasoning quality is high even on failure.** The decisions.md entry for falsify-signals correctly identifies the work as deterministic (not judgment), attempts dispatch, recognizes the execution error, defers with structured options for the operator. This is the calibration-quality canon predicts at Phase 0; the persona-bearing-Agent thesis is doing its job.

### What the full E2E surfaces about downstream layers

1. **iter-4 L3 capability flow has a tool-name resolution issue in practice.** The Reviewer (or its dispatched specialist) didn't know the correct platform tool name (`platform_trading_get_market_data`) for fetching bars. The bundle's `track-universe` prompt says "fetch fresh 1Hour bars via the Alpaca platform tool" but doesn't name the tool explicitly. The Reviewer's tool-discovery path (or the specialist's) tried plausible names and failed.

   **Fix scope (NOT in this commit)**: either bundle prompts should name `platform_trading_get_market_data` explicitly, or the L3 specialist tool surface should make tool-name discovery cleaner. This is iter-4 follow-up work, not ADR-270.

2. **DispatchSpecialist returns execution errors on the falsify-signals path.** The Reviewer attempted `DispatchSpecialist(role=researcher, required_capabilities=['read_trading'])` and got an execution error. Whether this is the same root cause as `track-universe`'s tool-name issue or a different L3 path, the symptom blocks falsify-signals from producing any findings.

   **Fix scope (NOT in this commit)**: trace DispatchSpecialist execution in the Render logs for the relevant invocation; likely same iter-4 follow-up.

3. **The "no `last_run_at` on failed dispatch" interaction I noted earlier was wrong-shaped.** Re-reading: dispatcher DOES set `last_run_at` on failure (we saw it). My earlier note "dispatch failing before record_task_run" was incorrect — record_task_run runs regardless. The actual failure mode is *substrate-write-failure-recorded-as-success*. Once the dispatcher marks the row complete, fire_on_activation won't re-trigger it. **Operator has to manually FireInvocation or wait for periodic schedule.** This is more honest about the interaction than my earlier framing.

4. **`track-regime`'s silent failure** — dispatched, set last_run_at, but no `_regime.yaml` write. Could be same L3 issue (specialist couldn't fetch VIXY/SPY bars), or could be different. Worth investigating separately. Pattern: same shape as the `track-universe` and `falsify-signals` failures — Reviewer/specialist dispatched, attempted tool calls, failed at the tool surface, didn't write substrate.

### What this means for the alpha-1 trade-execution loop

The activation chain is now **fast** (under 60 seconds for the first fires), **structurally correct** (verify.py passes), and produces **partial substrate** (`_account.yaml`). The remaining gaps are in iter-4 L3 capability flow — specifically how the Reviewer's specialist sub-LLM resolves platform tool names. Those gaps existed before ADR-270; ADR-270 just exercises them faster + more visibly.

For the alpha-1 trade-execution path (signal-evaluation → trade-proposal → ProposeAction → execute):
- `signal-evaluation` is currently scheduled for next `@market_open + 15min` (08:14 UTC = 17:14 KST = 04:14 ET next morning, since current US market is closed).
- That fire will attempt to read `/workspace/context/trading/{ticker}.yaml` files which currently don't exist (track-universe failed).
- Without ticker substrate, signal-evaluation will likely stand down with "no data to evaluate."
- The trade-execution loop is structurally blocked until either L3 is fixed or operator manually populates ticker substrate.

### Verification status summary (updated)

| Layer | Status |
|---|---|
| Kernel conditional in `compute_next_run_at` | ✅ verified end-to-end |
| Bundle YAML parsing (`fire_on_activation` absorbed into `rec.options`) | ✅ verified |
| `materialize_scheduling_index` writes `next_run_at = now` for flagged rows | ✅ verified |
| Bundle fork writes new `research/mandate.md` + `specs/falsify-signals.md` | ✅ verified |
| Scheduler tick picks up due rows | ✅ verified |
| Dispatch completes successfully + writes substrate | ✅ verified for `track-account` (mechanical); ❌ failed for `track-universe`/`track-regime`/`falsify-signals` (judgment-mode L3 issues) |
| Falsify-signals produces `/workspace/research/findings/{signal_id}.md` | ❌ blocked on DispatchSpecialist execution error |
| L3 capability-flow path (iter-4) exercised end-to-end | ⚠️ exercised but tool-name resolution failure observed |
| `verify.py alpha-trader` invariants | ✅ 32/32 PASS |

### Commits associated with this observation

- `914086f` — ADR-270 implementation (kernel conditional + bundle + ADR + observation skeleton)
- `f9e79c9` — initial verification findings (pre-credentials, blocked on Alpaca)
- (this commit) — full E2E findings post-credentials, surfaced iter-4 L3 downstream issues

### What's NOT in scope for follow-up commits on ADR-270

- Track-universe/track-regime/falsify-signals downstream failures — these are iter-4 L3 specialist-tool-surface issues, separately owned. ADR-270 cleanly verified for its own scope.
- The "substrate-write-failure-recorded-as-success" pattern (corrected understanding of the dispatcher behavior). Worth a separate scheduler-discipline pass if it produces operator friction at scale; flagged for future scope, not blocking ADR-270.

---

## Structural-resolution path findings (2026-05-13, post-Phase 3)

After the failures above were noted as out-of-ADR-270-scope, the conversation committed to **Reading B (structural resolution)** of the underlying failure class. The discourse-aligned principle: not just fix alpha-trader symptoms, but resolve the underlying "specialist sub-call → tool-surface mismatch → silent substrate-write failure" pattern so future bundles inherit a working DispatchSpecialist by construction.

The diagnostic-then-fix cycle ran twice. Each gate exposed the next gate in series.

### Gate 1 — `tool_uses_raw` AttributeError (fixed in `16dcd5f`)

Render logs for the failed falsify-signals invocation:
> *"DispatchSpecialist failed with a platform error ('ChatResponse' object has no attribute 'tool_uses_raw')"*

`dispatch_specialist.py:326` accessed `response.tool_uses_raw` — a field that never existed on `ChatResponse` (anthropic.py:26). Python raised AttributeError before the `or` fallback could evaluate. Bug introduced in PR #9 squash commit `42725c6` (2026-05-10), never exercised end-to-end until today because iter-3's L2 fix + iter-4's L3 wiring + ADR-270's fire_on_activation all needed to land before the bug could surface.

Fix: replace with the canonical reconstruction loop over `response.content` from `reviewer_agent.py`. Same pattern, no new field, no `getattr` band-aid.

### Gate 2 — `ToolUseBlock.get()` AttributeError (fixed in `9d85d12`)

Phase 3 re-fire post-`16dcd5f` cleared Gate 1, but exposed:
> *"DispatchSpecialist is failing with a backend error ('ToolUseBlock' has no 'get' attribute)"*

`dispatch_specialist.py:357-359` iterated `response.tool_uses` and called `.get()` on each item. But `response.tool_uses` is `list[ToolUseBlock]` per anthropic.py:110-114 — `ToolUseBlock` is a `@dataclass` with `.id`, `.name`, `.input` attributes, not a dict.

Same root-cause class as Gate 1: dispatch_specialist code authored assuming dict shape; ChatResponse parser delivers typed dataclasses. Both bugs in the same commit (`42725c6`).

Fix: replace `.get()` with attribute access. Matches `reviewer_agent.py`'s iteration pattern exactly.

### Gate 3 — balance exhausted (NOT a code bug)

Phase 3 re-fire post-`9d85d12` produced:

- **`track-regime` SUCCEEDED end-to-end.** `/workspace/context/trading/_regime.yaml` populated with real VIXY + SPY computation from Alpaca 1Day bars. Regime correctly classified inactive (VIXY 26.77 > threshold 22.0 BUT < sma_20 27.81 — conjunctive predicate works). Trend regime uptrend (SPY sma_20 717.91 > sma_50 proxy 701.79; close 738.18 > sma_20). Specialist showed its math inline with `_source: Alpaca 1Day bars` attribution. **First end-to-end success of the Reviewer→DispatchSpecialist→Alpaca→substrate chain in alpha-1 history.**
- **`track-universe` and `falsify-signals` blocked on `[SCHED] ✗ balance exhausted`.** Per ADR-171 universal token ledger + ADR-172 balance-as-single-gate. token_usage shows $3.21 spent today against $3.00 free balance.

This is not a code bug — the budget gate is doing its job. Verifying `track-universe` and `falsify-signals` end-to-end requires either: topping up seulkim88's balance (operator action via Supabase update), verifying via kvk's workspace instead (separate balance), or accepting the partial verification.

### What this structural-resolution path verified

- **Both architectural bugs in DispatchSpecialist eliminated.** Regression gate `test_adr269_capability_flow.py` now 90/90 PASS (was 74/74), with two new tests pinning each fix and the bug class for future readers.
- **End-to-end specialist dispatch is operationally valid.** `track-regime` proves the full chain works: Reviewer → DispatchSpecialist → headless specialist with `read_trading` capability → Alpaca API → substrate write via `WriteFile` (with `source: ai:reviewer` attribution per ADR-209).
- **iter-4 L3 capability flow exercised end-to-end** for the first time. iter-2 → iter-3 → iter-4 → today's ADR-270 + two fixes form a four-step chain that finally produces working specialist-dispatched substrate.
- **Singular Implementation honored throughout.** Both fixes use the canonical `reviewer_agent.py` pattern — one shape across the codebase, no parallel approaches. The regression tests verify the bug class (not just the specific bug) so future similar mistakes get caught.

### What this surfaced about iter-4's regression gate

The pre-fix ADR-269 gate (74 assertions) verified the *wiring* — that `required_capabilities` flowed from YAML through to the specialist tool surface. It did NOT verify the specialist could complete a tool-use round trip. Both bugs were in the round-trip code path, not the wiring.

**Lesson for future iter regression gates: wiring tests verify shape; integration-shaped tests verify execution.** ADR-269 gate now extended with two tests that exercise the execution path with mock dataclasses.

### Commits associated with this path

- `914086f` — ADR-270 implementation (kernel conditional + bundle changes)
- `f9e79c9` — initial verification findings (pre-credentials)
- `8045238` — full E2E findings post-credentials (Gate 1 surfaced)
- `16dcd5f` — fix #1: tool_uses_raw → response.content reconstruction
- `9d85d12` — fix #2: ToolUseBlock attribute access
- (this commit) — Phase 3 outcome documentation
