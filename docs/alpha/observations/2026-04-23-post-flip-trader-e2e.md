# alpha-trader E2E Observation Log — 2026-04-23 post-LAYER-MAPPING-flip

> **Run date**: to be filled by operator on actual run
> **Commit SHA**: the LAYER-MAPPING flip shipped across 14afd72's lineage (14afd72 is the persona seeds; the orchestration flip landed at c4194a1 + 455fec3 + 2922c81; the prompt alignment at 310ac27; backend at f21737d; frontend at f90f3b4; CLAUDE.md at 1740da3)
> **Prior observations**: `observations/2026-04-22-adr206-trader-e2e-*.md` (pre-flip run); this is the post-flip re-run
> **Purpose**: capture what actually happens end-to-end when the alpha-trader workspace runs one cycle against the post-flip codebase
> **Status**: TEMPLATE — operator fills in during the run

---

## Pre-run checklist (operator follows before each E2E cycle)

### 1. Verify canonical state

```bash
cd /Users/macbook/yarnnn
git log --oneline -5                                  # confirm HEAD includes LAYER-MAPPING commits
git status                                            # expect clean
```

Expected: HEAD should be at or past commit `14afd72` (persona seeds). Earlier LAYER-MAPPING flip commits listed in handoff doc.

### 2. Purge workspace for clean cold-start

```bash
cd /Users/macbook/yarnnn/api
python scripts/purge_user_data.py kvkthecreator@gmail.com --dry-run
# review what would delete
python scripts/purge_user_data.py kvkthecreator@gmail.com
# type 'yes' at confirmation
```

Expected output: 11 table-level deletions across workspace_file_versions, workspace_files, action_proposals, tasks, agent_runs, agents, chat_sessions, platform_connections, token_usage, notifications, filesystem_documents, filesystem_chunks, activity_log. auth.users + workspaces + balance_transactions preserved.

### 3. Fresh login + workspace_init smoke test

- Visit `https://yarnnn.com` (or local dev server) → log in
- Landing page should be `/chat` (HOME_ROUTE per ADR-163)
- Expected initial state: OnboardingModal opens (workspace_state signals empty identity)
- Scroll through OnboardingModal — confirm vocabulary uses "Agents" in sharp sense + no mentions of "Specialists" or "Platform Bots" as entity terms

**If OnboardingModal still uses retired vocabulary**: first observation. Log in §Observations below, continue but note drift.

### 4. Verify systemic-Agent scaffold (two Agents at signup)

- Visit `/agents` surface. Expected: **no user-authored Agents listed** (operator hasn't created any). If there's a filter for infrastructure agents, YARNNN may or may not be visible there depending on ADR-189's `origin != 'system_bootstrap'` filter.
- Via chat or Context surface, verify `/workspace/review/` has all seven canonical files scaffolded:
  - `IDENTITY.md`
  - `OCCUPANT.md` (should declare `human:<user_id>`)
  - `principles.md` (generic default)
  - `modes.md` (commented-out defaults)
  - `decisions.md` (likely empty, created on first write)
  - `handoffs.md` (should have signup-scaffold entry for `human:<user_id>`)
  - `calibration.md` (empty initial state)

**If any of seven missing**: workspace_init Phase 4 scaffolding has a gap. Log observation and fix before proceeding.

### 5. 4-surface smoke test

Visit each in order; confirm loads without error + structure is right:
- `/chat` — YARNNN chat surface loads; send one "hello" message; verify response comes back through `YarnnnAgent`
- `/work` — task list surface loads; empty state expected (no tasks yet)
- `/agents` — Agent roster surface loads; empty state expected (no user-authored Agents yet)
- `/review` — Reviewer decisions stream pane loads; empty state expected (no decisions yet)

Record any crashes, vocabulary drift, or structural surprises in the Observations section.

### 6. Paste persona seeds (operator-authored intent)

**Canonical source: `docs/alpha/ALPHA-1-PLAYBOOK.md` §3A (alpha-trader).** The playbook is the single source of truth for the four seed files' content; it has been the canonical spec since before today and was not duplicated here.

Via chat with YARNNN, paste in order (each is a separate turn or direct edit):

**a. MANDATE**: Paste contents of `docs/alpha/personas/alpha-trader/MANDATE.md` into YARNNN chat with framing like "Please store this as my workspace mandate." YARNNN should use `UpdateContext(target="mandate")` to write to `/workspace/context/_shared/MANDATE.md`. Verify via Context surface.

**b. Reviewer principles**: Copy the code block from ALPHA-1-PLAYBOOK.md §3A.4 (Reviewer principles — Alpha Trader, Simons, Option B) into YARNNN chat with framing "This is how I want the Reviewer to judge my proposals. Please overwrite `/workspace/review/principles.md`." YARNNN should use `UpdateContext(target="principles")` (or equivalent write to the review substrate). Verify via Context surface or `/review`.

**c. Operator profile (trading domain)**: Copy the code block from ALPHA-1-PLAYBOOK.md §3A.2 (Operator profile — Alpha Trader, Simons, Option B) with framing "These are my declared trading signals. Please write them to `/workspace/context/trading/_operator_profile.md`." YARNNN should use `UpdateContext(target="context", domain="trading")`. Verify.

**d. Risk rules (trading domain)**: Copy the code block from ALPHA-1-PLAYBOOK.md §3A.3 (Risk parameters — Alpha Trader, Simons, Option B) with framing "These are my trading risk rules. Please write them to `/workspace/context/trading/_risk.md`." Verify.

**e. Verify all four pasted**:
- Context surface shows MANDATE.md, `/workspace/context/trading/_operator_profile.md`, `_risk.md`
- `/review` surface shows updated principles

**Note**: ALPHA-1-PLAYBOOK.md §3A signals are: Momentum-breakout, Mean-reversion-oversold, Post-earnings drift (PEAD), Sector-rotation-momentum, Volatility-regime filter. The PEAD signal is real and important — YARNNN asks about earnings calendars during the evaluation — and was missing from earlier drafts of E2E materials.

### 7. Connect Alpaca paper account

- Go to integrations / settings → connect Alpaca
- Use paper-trading API keys (Alpaca paper endpoint is https://paper-api.alpaca.markets)
- Confirm `platform_connections` row created with `platform='trading'` `provider='alpaca'` `status='active'`
- Verify `capability_available(user_id, 'read_trading', client)` returns True

### 8. Create one trading task via chat

Operator asks YARNNN: "Create a daily trading-signal task. It should evaluate my five signals against current market data and propose trades that pass every rule."

Expected YARNNN behavior:
- Reads MANDATE (mandate gate passes — mandate is non-empty)
- Reads operator-profile.md + risk.md for context
- Drafts a TASK.md with `**Agent:** tracker` or `**Agent:** researcher` (a production role fit for signal evaluation) and `**Required Capabilities:** read_trading, produce_markdown, investigate`
- Calls `ManageTask(action="create")` which passes the mandate-gate check
- Task appears on `/work` list

Verify:
- Task scaffolded at `/tasks/{slug}/TASK.md`
- Task has `** Required Capabilities:**` including trading platform access
- `/work` list shows the new task with correct output_kind, schedule, assigned role

### 9. Trigger first task run

- If task is schedule-recurring, wait for the cron tick OR manually trigger via "Run now" button OR via chat "Run the task now."
- Task pipeline dispatches: `ensure_infrastructure_agent` should lazy-create a `tracker` or `researcher` row in agents table (class="specialist" per enum exception)
- Production role reads operator-profile + risk, fetches current market data via Alpaca `read_trading` capability, evaluates the 5 signals against current state

### 10. Await first proposal

Two scenarios:

**Scenario A (realistic, market-dependent)**: if any signal fires for a universe stock, a `ProposeAction` fires → Reviewer dispatches reactively → verdict renders.

**Scenario B (no signals firing at this moment)**: fall back to simulated proposal. Operator manually drafts a proposal representing "Signal 2 fired on AAPL" (or whichever signal + ticker is realistic for current market), submits via chat request to YARNNN or via direct `ProposeAction` call. This exercises the proposal → review flow even without a real signal trigger.

The dry-run proposal in the next section shows exactly what a proposal must look like to pass Reviewer's Six Checks.

---

## Dry-run proposal (reference — what a passing proposal looks like)

If the operator needs to simulate a proposal for Scenario B, this is the shape it should take. Signals + risk rules cited are from **ALPHA-1-PLAYBOOK.md §3A.2 / §3A.3** (authoritative). The Reviewer should approve this proposal because it passes all Six Checks per §3A.4.

```yaml
# Example proposal — Signal 2 (Mean-reversion-oversold) on NVDA
# Submitted via ProposeAction primitive to the action_proposals table
# Signal rules per ALPHA-1-PLAYBOOK §3A.2:
#   Trigger: RSI(14) < 25 + price within 5% of 200-day SMA (quality
#            filter) + not in confirmed downtrend (20-day SMA above
#            50-day SMA)
#   Entry: next-day open
#   Stop-loss: 1.5× ATR(14) below entry
#   Target: RSI returns to 50 OR 2× ATR(14) above entry, whichever first
#   Sizing: 0.75% portfolio risk
#   Max hold: 10 trading days

action_type: trading.submit_order_paper
action_class: external_action
reversibility: reversible
task_slug: trading-signal

inputs:
  ticker: NVDA
  side: buy
  qty: 10
  order_type: limit
  limit_price: 847.50                # next-day open-approximation (Signal 2 says "next-day open")
  time_in_force: day
  stop_loss_price: 829.20            # 1.5 × ATR(14) = 18.30 below entry
  # target management: exit on RSI(14) back to 50 OR price reaches
  # 847.50 + 2 × 12.20 = 871.90 — whichever first. Time stop: day 10.

rationale: |
  Signal 2 (Mean-reversion-oversold) fired on NVDA at 2026-04-23T14:32 EDT.

  Check 1 — Signal attribution: Signal 2 per ALPHA-1-PLAYBOOK §3A.2.

  Check 2 — Signal rule compliance:
    - RSI(14) = 23.4 (< 25: PASS)
    - Price = $847.50, 200-day SMA = $832.10, distance = 1.85% (< 5%: PASS)
    - Not in confirmed downtrend: 20-day SMA ($849.10) > 50-day SMA
      ($846.80) — PASS
    - Universe filter: NVDA is in declared universe (§3A.2) — PASS
    - Not a day-trade (hold minimum 1 day per §3A.3) — PASS

  Check 3 — Risk-limit compliance (vs §3A.3):
    Starting capital: $25,000, current equity: $25,000 (fresh workspace)
    Position size: 10 × $847.50 = $8,475 = 33.9% of book
    max_position_percent_of_portfolio: 15 → 33.9% EXCEEDS the 15% limit.
    FAIL CHECK 3. (See note below — this proposal needs recalibrated
    sizing for the smaller $25K book. Pasting this dry-run verbatim
    produces a Reviewer REJECT on Check 3, which is also useful E2E
    signal — proves the risk-layer check actually fires. Adjust qty
    downward to pass, or keep as-is to exercise the rejection path.)

    For the approve variant: qty = 4 (4 × $847.50 = $3,390 = 13.6% of book)
    Check max_position_risk_percent (2%): 4 × $18.30 = $73.20 stop-distance
      = 0.29% of book → PASS
    Check sector concentration (40% max any one sector): 13.6% Tech → PASS
    Check max_open_positions_per_signal (3): 1 → PASS
    Check allowed_universe_only: PASS (NVDA in list)
    Check require_signal_attribution: PASS
    Check require_stop_loss: PASS ($829.20)
    Check require_position_sizing_formula: PASS (shown in Check 5)

  Check 4 — Signal expectancy (vs §3A.3 guardrails):
    Signal 2 recent-20-trade expectancy from _performance.md: +0.31R
      (above -0.5R decay guardrail: PASS)
    Signal 2 recent-40-trade Sharpe: +0.68
      (above 0.3 retirement-recommendation threshold: PASS)

  Check 5 — Position-sizing math (vs §3A.2 Signal 2 sizing rule):
    account_equity = $25,000
    risk_percent (Signal 2) = 0.75% = $187.50
    regime_scalar (VIX = 18.2, below 25 threshold in Signal 5): 1.0
    stop_distance = 1.5 × ATR(14) = 1.5 × $12.20 = $18.30
    position_size_shares = ($25,000 × 0.0075 × 1.0) / $18.30
                         = 10.2 shares → rounded down to 4 shares
    (further constrained by per-position ceiling — Check 3 forced reduction)

  Check 6 — Portfolio-level diversification:
    Current open positions: 0 (fresh workspace)
    Sector concentration (Tech after add): 13.6% → PASS (under 40%)
    No stacking (no existing NVDA position) → PASS

  Final Reviewer verdict (per §3A.4 framework):
    Recommend DEFER.
    Reasoning: proposal passes all six checks at qty=4 variant. Autonomy
    policy for Alpha-1 is "Auto-approve = NONE" — every trade routes to
    human operator for Queue approval per §3A.4 Auto-approve policy.

expected_effect: |
  Buy 4 NVDA at $847.50 limit (day order). Stop at $829.20 (-$73.20 max risk).
  Target: RSI(14) back to 50 OR $871.90 (2× ATR above entry), whichever
  first. Time stop: exit on day 10 regardless.

expires_at: <+4 hours from now>
```

---

## Expected Reviewer verdict (what should happen)

Per ALPHA-1-PLAYBOOK §3A.4 Auto-approve policy ("Auto-approve = NONE for Alpha-1 — every trade passes through human operator review in cockpit Queue; AI Reviewer's role is to EVALUATE and recommend, not to gate execution"), a well-formed proposal that passes all Six Checks should produce:

```yaml
decision: defer                           # per §3A.4 always defer — human approves in Queue
reviewer_identity: ai:reviewer-sonnet-v1
confidence: high
reasoning: |
  Recommend APPROVE (deferred to human per §3A.4 policy).

  Signal 2 (Mean-reversion-oversold) fired within rules per §3A.2:
    - RSI(14) = 23.4 < 25 ✓
    - Price within 1.85% of 200-SMA (< 5% quality filter) ✓
    - Not in confirmed downtrend (20-SMA > 50-SMA) ✓
    - NVDA in declared universe ✓

  Expectancy +0.31R (above -0.5R decay guardrail, above 0.3 Sharpe retire
  recommendation threshold) per §3A.3.

  Sizing formula-compliant: 0.75% risk × 1.0 regime × $18.30 stop =
  10.2 shares, rounded down to 4 per per-position 15% ceiling.

  Portfolio impact: 13.6% position size, 13.6% Tech sector, zero
  existing positions. All §3A.3 limits satisfied.

  Autonomy policy for Alpha-1: Auto-approve = NONE. Every trade
  defers to human occupant in Queue regardless of check outcome.
  Recommendation is APPROVE; execution gates on operator's click.
```

Operator then clicks Approve in the cockpit Queue → ExecuteProposal runs → Alpaca paper order submits → outcome eventually reconciles (next trading day or when stop/target/time-stop hits) → _performance.md updates → calibration.md rebuilds at next back-office cycle.

---

## Observations (operator fills during run)

### Setup phase observations

| # | What was observed | Expected? | Impact (none / minor / blocking) | Action |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

### Workspace init / smoke test observations

| # | Surface | What was observed | Expected? | Impact | Action |
|---|---|---|---|---|---|
| 1 | /chat | | | | |
| 2 | /work | | | | |
| 3 | /agents | | | | |
| 4 | /review | | | | |

### Persona-seed application observations

| # | Step | What was observed | Expected? | Impact | Action |
|---|---|---|---|---|---|
| 1 | MANDATE paste | | | | |
| 2 | principles paste | | | | |
| 3 | operator-profile paste | | | | |
| 4 | risk paste | | | | |

### Task creation + dispatch observations

| # | What was observed | Expected? | Impact | Action |
|---|---|---|---|---|
| 1 | Task scaffolded correctly | | | |
| 2 | Production role lazy-created on dispatch | | | |
| 3 | Capability gate (read_trading) enforced | | | |

### Proposal + Reviewer observations

| # | What was observed | Expected? | Impact | Action |
|---|---|---|---|---|
| 1 | Proposal shape matches Six Checks structure | | | |
| 2 | Reviewer dispatch fired reactively | | | |
| 3 | Verdict rendered with reasoning | | | |
| 4 | current_occupant displayed correctly (I1/I2) | | | |
| 5 | decisions.md append worked (with authored_by attribution) | | | |

### Execution + reconciliation observations

| # | What was observed | Expected? | Impact | Action |
|---|---|---|---|---|
| 1 | Approval flow ran end-to-end | | | |
| 2 | Alpaca paper order submitted | | | |
| 3 | outcome reconciliation triggered (daily back-office) | | | |
| 4 | _performance.md updated | | | |
| 5 | calibration.md rebuild worked | | | |

### Vocabulary / UI drift observations

| # | Surface | Retired vocabulary seen? | Where | Action |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

---

## Summary (operator fills post-run)

### What worked

-

### What didn't work

-

### What's blocking autonomous operation

-

### What canon or code needs to change

-

### Thesis-prediction progress

Per THESIS.md predictions:

1. Did the YARNNN-structured cycle produce a measurable outcome? __________
2. Did the Reviewer accumulate any calibration data? __________
3. Did the authored substrate show stickiness (operator spent time authoring persona seeds, valuable)? __________
4. Was the AI-occupant verdict reasonable vs what the operator would have judged retrospectively? __________

---

## Next-cycle setup (if this cycle worked)

If the first cycle produced a reasonable verdict and outcome, next-cycle setup is incremental:

- Tune `modes.md` for bounded_autonomous on paper trades below $2,000 threshold
- Let the system run 2–3 weeks of cycles
- Review calibration.md for per-signal aggregates
- At 2 weeks: first quarterly-style audit (condensed) to decide which signals are performing at expectancy

If this cycle didn't work: DON'T escalate. Fix the blocker. Re-run one cycle. Observation-first.
