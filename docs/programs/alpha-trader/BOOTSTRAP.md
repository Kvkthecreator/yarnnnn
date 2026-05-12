---
title: Alpha-Trader Bootstrap Playbook
audience: operator (alpha)
scope: signup → fork → Phase 0 observation → ceiling tuning → live autonomy
status: Canonical
last_updated: 2026-05-12
counterpart_docs:
  - docs/architecture/WORKSPACE.md     # substrate + autonomy loop + failure modes
  - docs/programs/alpha-trader/README.md  # bundle architecture
  - docs/programs/alpha-trader/MANIFEST.yaml  # machine-readable contract
---

# Alpha-Trader — Bootstrap Playbook

This is the operator-facing walkthrough for activating alpha-trader and running it to first auto-executed trade. The bundle ships substantial pre-authored substrate — most cold-start failure modes (per [WORKSPACE.md §5](../../architecture/WORKSPACE.md#5-cold-start-failure-modes)) are resolved by the bundle. The operator's decision points are concentrated at one editing checkpoint.

**Read this once before activating.** It's short.

---

## What you're activating

Alpha-trader is a systematic equity trading program running on YARNNN. The bundle ships:

- A pre-authored MANDATE (one-sentence Primary Action + Success Criteria + Boundary Conditions)
- A pre-authored Reviewer (Simons-style persona + 5 hard rejection rules + hard exit triggers)
- An operator profile with 5 measurable signals (momentum-breakout, mean-reversion, etc.) — full rules, sizing formulas, baselines
- A pre-authored risk envelope (`_risk.md` — portfolio limits, position constraints, signal allocation caps)
- 14 recurrences (3 mechanical substrate sensors at minute granularity; 11 judgment recurrences for signal evaluation, proposal generation, calibration, reporting)
- 5 output specs (ticker-snapshot, pre-market-brief, weekly-performance-review, quarterly-signal-audit, performance-rollup)

The bundle is **operator-grade out-of-box**. You can run the workspace end-to-end on shipped defaults. You will probably want to tune some numbers — that's covered below.

---

## The four-stage sequence

```
Stage 0 — Activate              (1 click + acknowledgment)
   ↓
Stage 1 — Observe Phase 0       (1–2 weeks; recurrences fire, proposals queue)
   ↓
Stage 2 — Calibrate              (raise ceiling; optionally tune signals)
   ↓
Stage 3 — Live autonomous       (auto-execution within new ceiling)
```

---

## Stage 0 — Activate

**What you do:** From `/workspace?first_run=1` (or any time later from Settings → Workspace), click **Activate alpha-trader**.

**What happens on the backend** (per [WORKSPACE.md §2 Phase 5](../../architecture/WORKSPACE.md#phase-5--reference-workspace-fork-optional)):

1. `POST /api/programs/activate` runs.
2. `services.programs.fork_reference_workspace()` walks the bundle's `reference-workspace/` directory.
3. For each file:
   - `tier: canon` files copied verbatim (alpha-trader: `_autonomy.yaml`)
   - `tier: authored` files copied to skeleton-state (alpha-trader: `_universe.yaml`, `_principles.yaml`) — operator may overwrite
   - All other files copied as initial content (the bundle's pre-authored MANDATE, IDENTITY, principles, Reviewer IDENTITY, etc.)
4. Scheduling index materialized — `tasks` table populated with `next_run_at` for every recurrence.
5. Workspace lands at `activation_state = "operational"` immediately. MANDATE is non-skeleton (the bundle's pre-authored content satisfies `is_skeleton_content() == False`).

**What you'll see:**
- Cockpit tabs populate (Chat / Work / Agents / Files).
- The Mandate face on the Work cockpit shows the bundle's authored Primary Action.
- The Money truth face shows zero P&L (no trades yet).
- The Performance face shows empty calibration (no decisions yet).
- The Tracking face shows pending recurrence schedules but no fires yet.

**Time:** Under 30 seconds.

---

## Stage 1 — Observe Phase 0

**Duration:** 1–2 weeks, your call. Until you've built confidence in the Reviewer's calibration.

**Default Phase 0 posture** (shipped in `_autonomy.yaml`):
```yaml
default:
  delegation: bounded
  ceiling_cents: 20000        # $200 ceiling — paper-seed default
  never_auto:
    - close_position_market
    - cancel_other_orders
```

**What this means:** `delegation: bounded` + `ceiling_cents: 20000` together gate every Reviewer approve verdict. A signal-sized trade entry is roughly $12k–$15k notional, so **every entry exceeds the $200 ceiling and queues for your click**. The Reviewer runs end-to-end, judges every proposal, and you see its full reasoning — but execution waits for you.

**What you observe during Phase 0:**

| Time | What fires | What you see |
|---|---|---|
| Every minute, market hours | `track-positions`, `track-orders` (mechanical) | Position + order substrate refreshes silently. No proposals. |
| Every 5 min, market hours | `track-account` (mechanical) | Account state refreshes. No proposals. |
| 8:00am ET (daily) | `track-universe` (judgment) | Per-ticker snapshots regenerate against the universe in `_universe.yaml`. Visible in narrative. |
| 8:05am ET (daily) | `signal-evaluation` (judgment) | Reviewer evaluates all 5 signals. If entry/exit conditions match for any signal, fires `trade-proposal`. |
| Reactive | `trade-proposal` (judgment) | Reviewer emits ProposeAction with sizing math; lands in operator-approval queue. |
| 8:15am ET (daily) | `pre-market-brief` (judgment) | Daily report: signal state, exposure, decay flags, regime. Composed HTML in `/workspace/reports/pre-market-brief/{date}/`. |
| 6:00am ET (daily) | `morning-calibration` (judgment) | Reviewer compares realized vs declared expectancy; flags divergence in `decisions.md`. |
| 7:00am ET (daily) | `morning-reflection` (judgment) | Reviewer reflects on prior verdicts; may propose principle edits. |
| 5:00am ET (daily) | `outcome-reconciliation` (judgment) | Reconciles fills against proposal projections; updates `_performance.md` rolling windows. |
| Sunday 6:00pm ET | `weekly-performance-review` (judgment) | Per-signal P&L, Sharpe, expectancy. |

**What you should track during Phase 0:**

1. **Reviewer verdict quality.** Read `/workspace/review/decisions.md` regularly. Are the approve verdicts ones you would have approved? Are the reject verdicts catching real risk?
2. **Signal expectancy stability.** Watch `weekly-performance-review`. Are signals tracking their declared baselines?
3. **Calibration trajectory.** Watch `morning-calibration`. Is realized P&L close to declared expectancy?

**Optional during Phase 0 — tune for your actual capital:**

| File | What to tune | Why |
|---|---|---|
| `/workspace/context/_shared/IDENTITY.md` | Author your operator persona (2–3 sentences on decision posture + risk relationship) | Reviewer reads it for judgment voice; empty defaults to neutral baseline. Non-blocking but improves verdict quality. |
| `/workspace/context/trading/_risk.md` | Adjust portfolio limits if your seed capital differs from $25k | Shipped at $25k seed / 1.5% daily VAR / 5% weekly drawdown. If you have $100k, scale up. |
| `/workspace/context/trading/_universe.yaml` | Edit the ticker list | Shipped with AAPL, MSFT, NVDA, SPY, TSLA. Add/remove per your actual interest. |
| `/workspace/review/IDENTITY.md` | Customize Reviewer persona if not Simons-style | Shipped Simons-style. Swap to Buffett, Deming, or operator-original if your judgment character differs. |
| `/workspace/review/principles.md` | Tune hard rejection rules if your edge differs | Shipped with 5 rules + hard exit triggers. Most operators leave defaults. |

None of these tunes are blocking. They make the system more accurate to your specifics.

**What NOT to do in Phase 0:**

- Don't raise `ceiling_cents` yet. The ceiling is the brake during the calibration period.
- Don't archive recurrences out of impatience. They're firing on operator-decided cadence.
- Don't hand-edit `_performance.md`. The reconciler owns it.

---

## Stage 2 — Calibrate

**When you're ready** (you decide — typical: 1–2 weeks of Phase 0):

**Make one edit.** Raise `_autonomy.yaml` `ceiling_cents` to the notional that lets entry-sized trades auto-execute.

Open `/workspace/context/_shared/_autonomy.yaml` in the Files surface (or via chat):

```yaml
default:
  delegation: bounded
  ceiling_cents: 1500000      # $15,000 — covers signal-sized entries per _operator_profile.md
  never_auto:
    - close_position_market
    - cancel_other_orders
```

**Why $15,000:** Per `_operator_profile.md` line 23 (`max_capital_percent_per_signal: 25`), entries are sized to ~25% of book per signal. At $25k seed that's $6,250; with breathing room for larger signal weights, $15k covers most legitimate entries while still queueing anything anomalously large.

**Alternative postures:**

| Posture | Setting | When |
|---|---|---|
| Phase 0 (default) | `delegation: bounded`, `ceiling_cents: 20000` ($200) | Initial observation. Every entry queues. |
| Phase 1 (bounded autonomous) | `delegation: bounded`, `ceiling_cents: 1500000` ($15k) | Post-Phase-0. Signal entries auto-execute; outsized trades queue. |
| Phase 2 (full autonomous) | `delegation: autonomous` | After many Phase-1 weeks. Reviewer approval is execution. Operator sees outcomes in narrative. Highest trust. |
| Circuit breaker | Add `paused_until: <ISO8601>` + `pause_reason: <text>` to `_autonomy.yaml` | Anytime you want a time-bounded autonomy halt (e.g., during a high-volatility regime). |

**That's the one critical edit.** Everything else is optional tuning.

---

## Stage 3 — Live autonomous

**What happens after the ceiling raise:**

1. Next `signal-evaluation` fire generates entry proposals as before.
2. `trade-proposal` recurrence emits ProposeAction.
3. Reviewer wakes (reactive trigger), reads substrate, judges proposal.
4. Reviewer returns `approve`.
5. `should_auto_execute_verdict()` reads `_autonomy.yaml`:
   - `delegation: bounded` ✓
   - `proposal.estimated_cents` ($12,500 for typical entry) < `ceiling_cents` ($15,000) ✓
   - Action type not in `never_auto` ✓
6. **Executes**: `handle_execute_proposal` fires the platform tool (Alpaca order submission).
7. Audit: `append_decision(decision="approve", reviewer_identity="ai:reviewer-{occupant}")` to `/workspace/review/decisions.md`.
8. Next minute: `track-positions` mechanical recurrence mirrors the new position into substrate.
9. Next 5am: `outcome-reconciliation` reconciles when the trade closes (stop / target / max-hold).
10. Next 6am: `morning-calibration` compares realized vs declared expectancy.
11. Loop closes.

**What stays queued even in Phase 1:**
- `close_position_market` — closing positions at market always requires operator click (per `never_auto`)
- `cancel_other_orders` — cancellations require operator click
- Any proposal whose `estimated_cents` exceeds your ceiling
- Any proposal that Reviewer `reject`s (Reject is binding, never gated by autonomy)

**What you monitor in Phase 1:**

- `morning-calibration` flags divergence between predicted and realized expectancy. If divergence persists, the Reviewer may propose principle edits via `morning-reflection`.
- `weekly-performance-review` confirms signals are tracking baselines.
- `quarterly-signal-audit` (quarter-end) surfaces decay candidates — signals to retire or rebuild.

---

## Troubleshooting

**"I activated the bundle but recurrences aren't firing."**
- Check `tasks` scheduling index: `SELECT slug, next_run_at, paused FROM tasks WHERE user_id='<your-uuid>'`. Each recurrence should have `next_run_at` set.
- If empty: `services.scheduling.materialize_scheduling_index()` didn't run. Re-trigger via `POST /api/programs/activate` (idempotent — won't overwrite operator content).
- Check unified-scheduler health on Render. Cron service must be up.

**"Reviewer is approving proposals but nothing executes."**
- Default Phase 0 posture. Check `_autonomy.yaml` `ceiling_cents` — likely $200. Either you're in observation phase (expected) or you forgot to raise the ceiling after calibration.
- If `paused_until` is set in `_autonomy.yaml` with a future date, autonomy is in circuit-breaker mode.

**"Reviewer keeps deferring instead of approving or rejecting."**
- Check `/workspace/context/trading/_performance.md` — is it empty or stale? Reviewer defers when it has insufficient evidence.
- Check the proposal's reasoning. If it doesn't name a signal from `_operator_profile.md`, Reviewer should reject (hard rule 2), not defer.
- Inspect `decisions.md` for the deferral reasoning. The Reviewer narrates why.

**"`_risk.md` ceiling check is failing."**
- This shouldn't happen with the bundle as-shipped — `_risk.md` ships full. If you cleared it, restore from `docs/programs/alpha-trader/reference-workspace/context/trading/_risk.md` or re-fork the bundle.

**"I want to start over."**
- L2 reset: `DELETE /api/account/workspace` purges workspace, preserves user account. Workspace re-initializes on next `GET /api/workspace/state`. Re-activate the bundle from `/workspace?first_run=1`.
- L4 reset: `DELETE /api/account/reset` purges everything including user account.
- See [WORKSPACE.md §2](../../architecture/WORKSPACE.md#2-temporal-bootstrap--what-gets-seeded-when) for reset semantics.

**For any cold-start failure mode not covered here**, see [WORKSPACE.md §5 — Cold-Start Failure Modes](../../architecture/WORKSPACE.md#5-cold-start-failure-modes). That catalog covers every prerequisite × what specifically breaks × code line that fails.

---

## What this playbook is not

- **Not a trading strategy guide.** The bundle's signals are starting points. Your edge is your responsibility.
- **Not legal or financial advice.** Paper-trade first. Live trading at your own risk.
- **Not a substitute for reading `_operator_profile.md`.** Before raising the ceiling, you should understand the 5 shipped signals and decide which match your conviction.

## Related

- [WORKSPACE.md](../../architecture/WORKSPACE.md) — substrate architecture + autonomy loop + cold-start failure modes
- [alpha-trader/README.md](README.md) — bundle architecture + position relative to the kernel
- [alpha-trader/MANIFEST.yaml](MANIFEST.yaml) — machine-readable bundle contract
- [ADR-187](../../adr/ADR-187-trading-integration-alpaca.md) — Alpaca integration architecture
- [ADR-260 / ADR-261 / ADR-262](../../adr/ADR-260-real-time-reviewer-loop.md) — real-time Reviewer loop + recurrences as prompts
