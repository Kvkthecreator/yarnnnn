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

Via chat with YARNNN, paste in order (each is a separate turn or direct edit):

**a. MANDATE**: Paste contents of `docs/alpha/personas/alpha-trader/MANDATE.md` into YARNNN chat with framing like "Please store this as my workspace mandate." YARNNN should use `UpdateContext(target="mandate")` to write to `/workspace/context/_shared/MANDATE.md`. Verify via Context surface.

**b. Reviewer principles**: Paste contents of `docs/alpha/personas/alpha-trader/reviewer-principles.md` with framing "This is how I want the Reviewer to judge my proposals. Please overwrite `/workspace/review/principles.md`." YARNNN should use `UpdateContext(target="principles")` (or equivalent write to the review substrate). Verify via Context surface or `/review`.

**c. Operator profile (trading domain)**: Paste contents of `docs/alpha/personas/alpha-trader/operator-profile.md` with framing "These are my 5 declared trading signals. Please write them to `/workspace/context/trading/_operator_profile.md`." YARNNN should use `UpdateContext(target="context", domain="trading")`. Verify.

**d. Risk rules (trading domain)**: Paste contents of `docs/alpha/personas/alpha-trader/risk.md` with framing "These are my trading risk rules. Please write them to `/workspace/context/trading/_risk.md`." Verify.

**e. Verify all four pasted**:
- Context surface shows MANDATE.md, `/workspace/context/trading/_operator_profile.md`, `_risk.md`
- `/review` surface shows updated principles

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

If the operator needs to simulate a proposal for Scenario B, this is the shape it should take. The Reviewer should approve this proposal because it passes all six checks.

```yaml
# Example proposal — Signal 2 oversold bounce on a hypothetical universe stock
# Submitted via ProposeAction primitive to the action_proposals table

action_type: trading.submit_order_paper
action_class: external_action
reversibility: reversible
task_slug: trading-signal

inputs:
  ticker: NVDA
  side: buy
  qty: 4
  order_type: limit
  limit_price: 847.50
  time_in_force: day
  stop_loss_price: 829.20    # 1.5 × ATR(14) = 18.30 below entry
  take_profit_price: 865.80  # 1R target = entry + stop_distance

rationale: |
  Signal 2 (oversold bounce) fired on NVDA at 2026-04-23T14:32 EDT.

  Check 1 — Signal attribution: Signal 2 (oversold bounce, long-only)
  from _operator_profile.md.

  Check 2 — Mechanical rule evaluation:
    - RSI(14) = 23.4 (< 25: PASS)
    - Price = $847.50, 200-day SMA = $832.10, distance = 1.85% (< 5%: PASS)
    - Confirmed downtrend check: 50-day SMA > 200-day SMA, no 50/200 cross
      in last 10 trading days (not in downtrend: PASS)
    - Universe filter: NVDA in declared universe, mega-cap, S&P 500
      constituent since 2001 (PASS)

  Check 3 — Sizing formula:
    account_equity = $25,000
    risk_percent (Signal 2) = 0.75% = $187.50
    regime_scalar (VIX = 18.2, "normal" regime, no drawdown overlay) = 1.0
    stop_distance = 1.5 × ATR(14) = 1.5 × $12.20 = $18.30
    position_size_shares = ($25,000 × 0.0075 × 1.0) / $18.30
                         = $187.50 / $18.30
                         = 10.2 shares → rounded down to 4 shares
    (rounded further due to per-position ceiling — see Check 5)

  Check 4 — Expectancy decay guardrail:
    Signal 2 rolling 20-trade expectancy from _performance.md: +0.31R
    (above retire-flag threshold of -0.5R: PASS)

  Check 5 — Risk-layer enforcement:
    Current positions: 0 (fresh E2E workspace)
    This position size: 4 shares × $847.50 = $3,390 = 13.6% of equity
    Per-position ceiling (Check 5 risk.md): 15% = $3,750 (PASS, under)
    Cumulative Signal 2 ceiling: 15% = $3,750 (PASS, this is first position)
    Sector concentration (Tech): 13.6% (PASS, under 35%)
    Cash floor after: $21,610 = 86.4% (PASS, above 5%)

  Check 6 — Reversibility + action-class:
    Action: trading.submit_order_paper (reversible, not in never_auto_approve list)
    Paper account (not live trading, which is in never_auto_approve)
    Modes.md for trading domain: autonomy_level = manual for E2E
    → AI occupant may NOT auto-approve; routes to human occupant.

  Capital-EV:
    Signal 2's declared target is 1R profit = +$73.20 (4 × $18.30)
    Expected value at 55% hit rate = 0.55 × $73.20 + 0.45 × -$73.20
                                    = $40.26 - $32.94 = +$7.32
    At declared expectancy of +0.31R per trade: expected +$22.70 realized P&L
    Position sized within tolerance. Green-light for human review.

expected_effect: |
  Buy 4 NVDA at $847.50 limit (day order). Stop at $829.20 (-$73.20 max risk).
  Target $865.80 (+$73.20 profit). Time stop: exit in 5 trading days regardless
  if neither stop nor target hit.

expires_at: <+4 hours from now>
```

---

## Expected Reviewer verdict (what should happen)

Per the AI occupant defined in `reviewer_agent.py`, a well-formed proposal that passes all six checks and has `autonomy_level: manual` in modes.md should produce:

```yaml
decision: defer
reviewer_identity: ai:reviewer-sonnet-v1
confidence: high
reasoning: |
  Proposal passes all six mechanical checks against the declared
  operator-profile and risk floors. Signal 2 attribution correct.
  Rule evaluation shows RSI 23.4 < 25, price within 1.85% of 200-SMA,
  not in downtrend — all PASS with explicit numbers. Sizing formula
  matches: 0.75% risk × 1.0 regime × stop distance $18.30 = 10.2
  shares, correctly rounded down. Expectancy for Signal 2 at +0.31R
  is above the retire-flag threshold. Risk floors all satisfied.

  Capital-EV: expected +$22.70 realized at Signal 2's historical
  expectancy. Position size (13.6% of equity) within per-position
  ceiling with comfortable headroom.

  Autonomy_level for trading domain is 'manual' — AI occupant does
  not auto-approve. Deferring to human occupant for final approval
  and order submission.
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
