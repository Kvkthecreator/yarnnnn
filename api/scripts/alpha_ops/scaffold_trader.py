"""
Alpha-1 trader persona scaffolder.

Seeds the Simons-inspired `alpha-trader` workspace with the content
declared in ALPHA-1-PLAYBOOK.md §3A.1-3A.5. Idempotent: re-running
overwrites content to match the playbook (use when the playbook spec
evolves).

What this does:
  1. POST /api/memory/user/identity  — IDENTITY.md from §3A.1
  2. POST /api/memory/user/brand     — BRAND.md (no public brand framing)
  3. DB upsert review/principles.md  — §3A.4 Simons 6-check reviewer
  4. DB upsert context/trading/_operator_profile.md — §3A.2
  5. DB upsert context/trading/_risk.md at RISK_MD_PATH — §3A.3
  6. POST /api/tasks for 6 Simons-persona tasks (then PUT → paused)

What this doesn't do:
  - Signal state files under /signals/ (signal-evaluation first run)
  - Ticker entity files (track-universe first run)
  - _performance.md schema changes (reconciler's job; per-signal
    attribution gap is documented as observation material)

Usage:
    .venv/bin/python api/scripts/alpha_ops/scaffold_trader.py
    .venv/bin/python api/scripts/alpha_ops/scaffold_trader.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from _shared import ProdClient, load_registry, pg_connect  # noqa: E402


# =============================================================================
# Content (verbatim from ALPHA-1-PLAYBOOK.md §3A.1-3A.4)
# =============================================================================

IDENTITY_MD = """# Alpha Trader — systematic retail operator (Simons-inspired)

## Who I am
I'm a systematic retail trader. My edge is not intuition, speed,
or conviction — it's measurable. I operate a small book of
equity signals that I've defined, tested (loosely), and committed
to following. I don't override my signals based on narrative, news
sentiment, or gut. When a signal fires within its declared rules,
I take the trade. When it doesn't, I don't.

I measure everything I can. My performance record is the pattern
library I learn from — not because every trade should be a winner,
but because the distribution of outcomes tells me whether my
declared edge is real, decayed, or never existed.

I respect drawdown math. Position sizing is mechanical, derived
from volatility + signal expectancy. Concentration is capped.
Sector exposure is monitored. I will not deploy more than my
declared portfolio-level var budget even on "high-conviction"
setups — the word "conviction" is not in my vocabulary.

## My book
Starting capital: $25,000 (Alpaca paper). Universe: 12–15 liquid
US equities + index proxies. Typical hold: 1–20 trading days.
Expected trade count: 40–120 per year across all signals. Target
portfolio volatility: ≤1.5% daily standard deviation.

## What I want YARNNN to do
- Track each declared signal's real-time state across my universe.
  If a signal fires, generate a ProposeAction with full signal
  attribution (which signal, historical expectancy, current
  position sizing, stop-loss, target).
- Enforce signal-discipline strictly. The Reviewer's job is to
  confirm a proposed trade matches a declared signal's entry rules
  and that expected value given the signal's track record is
  positive. If either fails, reject.
- Pre-market brief daily: which signals are in "watch" state, which
  may fire intraday, current portfolio exposure against var budget,
  any signals that have decayed (last-20-trade expectancy turned
  negative).
- Weekly performance attribution: per-signal P&L, win rate,
  expectancy, Sharpe, max drawdown since signal-live date. Flag
  signals whose recent performance has diverged from historical
  baseline.
- Quarterly signal audit: which signals should be retired (decayed
  edge), which should be added (new research), which should have
  sizing changed.

## What I don't want
- Autonomous trade submission. Every trade passes through the
  cockpit Queue for human approval. Paper OR live.
- Proposals without signal attribution. If a trade idea doesn't
  map to a declared signal, it should not exist.
- Narrative suggestions, market commentary, FOMO-adjacent content.
  If it's not about my signals' state or my book's exposure, I
  don't need it.
- Optimizing for activity. Some weeks my signals fire rarely.
  That's data, not a problem.
- Character or conviction talk. Quantitative frame only.

## My operator hypothesis
A small set of declared signals with measured edge, followed
mechanically, will outperform discretionary trading at my capital
level. YARNNN's role is not to help me trade better — it's to
help me not drift from the systematic discipline when emotions
argue otherwise.
"""

BRAND_MD = """# Brand — Alpha Trader (no public brand)

This workspace does NOT have a public brand. The operator is a
private systematic retail trader; the "brand" is an internal
voice specification for YARNNN to respect, nothing more.

## Voice (internal only)
- Quantitative. Specific. Numeric.
- Every claim cites a signal, a threshold, or a measurement.
- No narrative framing. No "I think the market will…" No mood.
- Treat this like a risk committee memo, not a market commentary.

## Explicit non-goals
- No external audience. Nothing YARNNN produces here is meant
  to be shared, published, or seen by anyone outside the operator.
- No marketing materials. No "content" in the editorial sense.
- No persona-building, no thought-leadership posture.

## What YARNNN should NOT do
- Suggest headlines, captions, or social-style phrasings.
- Propose cross-posts, email digests styled for readers, or any
  publishing workflow.
- Offer "brand voice" adjustments in outputs. The voice is
  what's written above; it doesn't evolve with trends.

Operationally: if a task surface asks "what's the tone?", the
answer is always "risk-committee memo, numbers first."
"""

# Operator profile — playbook §3A.2
OPERATOR_PROFILE_MD = """# Operator profile — Alpha Trader (Simons, Option B)

## Declared strategy
Systematic equity trading across 5–8 measurable signals. Universe
limited to liquid, high-quality US equities + index proxies.
No options, no crypto, no leverage beyond 1.0x.

## Declared universe
Primary: AAPL, MSFT, GOOGL, NVDA, AMD, META, TSLA, AMZN,
         SMH, SOXX, QQQ, SPY, XLK, XLY, IWM
(Candidates to add/rotate via quarterly signal audit. Not a
trading wishlist — these are the instruments signals operate on.)

## Declared signals (initial set; evolves via quarterly audit)

### Signal 1: Momentum-breakout
- **Trigger:** 20-day high + price > 50-day SMA + RSI(14) between 55–75 + volume > 1.5x 20-day avg
- **Entry:** next-day open or on-trigger-day close (configurable)
- **Stop-loss:** 2× ATR(14) below entry
- **Target:** 3× ATR(14) above entry OR trailing stop at 1.5× ATR(14) after +2× ATR
- **Position sizing:** 1% portfolio risk (position_size = account_size × 0.01 / stop_distance)
- **Max hold:** 20 trading days; force-exit on day 21 regardless of state
- **Historical baseline (to establish):** target win rate ≥45%, avg win ≥1.5× avg loss, Sharpe ≥0.8

### Signal 2: Mean-reversion-oversold
- **Trigger:** RSI(14) < 25 + price within 5% of 200-day SMA (quality filter) + not in confirmed downtrend (20-day SMA above 50-day SMA)
- **Entry:** next-day open
- **Stop-loss:** 1.5× ATR(14) below entry
- **Target:** RSI returns to 50 OR 2× ATR(14) above entry, whichever first
- **Position sizing:** 0.75% portfolio risk (smaller — mean-reversion has lower expectancy than trend)
- **Max hold:** 10 trading days
- **Historical baseline (to establish):** target win rate ≥55%, avg win ~equal to avg loss, Sharpe ≥0.6

### Signal 3: Post-earnings drift (PEAD)
- **Trigger:** earnings surprise >5% + price gap >3% in surprise direction + hold universe match
- **Entry:** day+1 after earnings at open
- **Stop-loss:** 2× ATR(14) against entry direction
- **Target:** 10-day hold OR 3× ATR(14) profit, whichever first
- **Position sizing:** 1% portfolio risk
- **Max hold:** 10 trading days
- **Historical baseline (to establish):** target win rate ≥50%, asymmetric payoff (avg win ≥1.75× avg loss)

### Signal 4: Sector-rotation-momentum
- **Trigger:** ETF (SMH/XLK/XLY/XLF) relative-strength rank in top 2 of 9 sectors over 20-day window + sector ETF itself in momentum state per Signal 1 rules
- **Entry:** on ETF (not individual stock)
- **Stop-loss:** 2× ATR(14) below entry
- **Target:** trailing stop at 1.5× ATR after +2× ATR
- **Position sizing:** 1.5% portfolio risk (ETF = lower idiosyncratic; slightly larger sizing)
- **Max hold:** 30 trading days
- **Historical baseline:** Sharpe ≥0.7

### Signal 5: Volatility-regime filter (not a trade signal — a portfolio state)
- **Purpose:** reduce sizing across all signals when VIX > 25 AND VIX > 20-day VIX SMA
- **Action:** multiply all signal position_size by 0.5 while regime is active
- **Deactivation:** VIX < 20 for 5 consecutive days
- **Not a signal that generates trades — a global scalar applied in risk sizing.**

(Signals 6–8 reserved — added through quarterly audits as research identifies candidates. Do not add ad-hoc during Alpha-1.)

## Declared edge
Discipline in signal execution, position-sizing math, and signal
retirement. Not in prediction quality. My edge compounds through:
- Consistent sizing (never over-weighting a "high-conviction" trade)
- Diversification across uncorrelated signals
- Retiring signals that decay (don't hope them back to life)
- Never overriding the model

## Success criteria — year-over-year
- Net Sharpe ≥ 1.0 across portfolio
- Max drawdown ≤ 15%
- Per-signal Sharpe within 1.5x of declared baseline (signals
  performing roughly as expected in their regime)
- Zero trades without signal attribution
- At least one quarterly audit per quarter (operator discipline)

## What I'm NOT trying to do
- Not trying to match pro quants on return
- Not trying to beat the index on any single quarter
- Not trying to call market tops or bottoms
- Not trying to swing-trade narrative plays
- Not trying to hold long-term (this is not a buy-and-hold book)
"""

# Risk parameters — playbook §3A.3
RISK_MD = """# Risk parameters — Alpha Trader (Simons, Option B)

## Portfolio-level limits
max_portfolio_daily_var_usd: 375           # 1.5% of $25k starting capital
max_portfolio_weekly_drawdown_usd: 1250    # 5% weekly halt
max_simultaneous_open_positions: 6
max_total_gross_exposure_percent: 120      # cap stock allocation at 120% of book (small buffer above 1.0x, never above)
max_leverage: 1.0                          # no margin trades

## Per-position limits
max_position_percent_of_portfolio: 15
max_position_risk_percent: 2               # a single trade risking (entry→stop × size) can't exceed 2% of book
max_order_size_shares: 500
min_liquidity_filter_dollar_volume_20d: 50_000_000

## Per-signal capital allocation caps
max_capital_percent_per_signal: 25         # no single signal can hold >25% of deployed capital
max_open_positions_per_signal: 3

## Sector concentration
max_sector_percent_of_portfolio: 40        # across all open positions, any one sector
max_single_ticker_count_open_positions: 1  # no stacking same ticker

## Trade discipline
allowed_universe_only: true                # reject proposals outside declared universe (reference _operator_profile.md)
require_signal_attribution: true           # reject proposals without a named signal
require_stop_loss: true
require_position_sizing_formula: true      # the proposal must include the sizing calculation
trading_hours_only: true
max_day_trades: 0                          # no intraday in/out — positions open and hold minimum 1 day

## Volatility regime
apply_vix_regime_scalar: true              # Signal 5 is the regime filter; when active, sizing × 0.5

## Signal decay guardrails (auto-flag, not auto-halt)
flag_signal_for_review_if_recent_20_trade_expectancy_below: -0.5   # units: R-multiples; flag in weekly review
retire_signal_recommendation_after_recent_40_trade_sharpe_below: 0.3   # recommend retirement in quarterly audit
"""

# Reviewer principles — playbook §3A.4
PRINCIPLES_MD = """# Reviewer principles — Alpha Trader (Simons, Option B)

## Auto-approve policy
Auto-approve = NONE for Alpha-1. Every trade passes through human
operator review in cockpit Queue. (Paper OR live.) The AI Reviewer's
role is to EVALUATE each proposal and provide a clear recommendation
to the human — not to gate execution on its own.

## Always-escalate-to-human
- All trading.submit_* (bracket, trailing stop, market, limit)
- All trading.cancel_*
- All watchlist modifications
- All signal-definition edits (these touch _operator_profile.md, which
  is a persona-identity file per governance rules)
- All commerce.* (N/A for this account)

## Capital-EV evaluation framework (the Reviewer's structured reasoning)

For each proposal, the AI Reviewer executes these checks in order.
Each check produces a one-line verdict. The full chain is written
to decisions.md as the reviewer_reasoning field.

### Check 1: Signal attribution
- Does the proposal specify which signal generated it (Signal 1–5)?
- If no → reject with reason: "no signal attribution"
- If yes → continue

### Check 2: Signal rule compliance
- Read the signal's entry rules from _operator_profile.md
- Do the proposal's conditions match those rules at time of proposal?
  (price thresholds, indicator values, regime filters, universe
  membership, volume filters)
- If any rule condition fails → reject with reason: "signal rule X fails: <detail>"
- If all match → continue

### Check 3: Risk-limit compliance
- Read _risk.md and current portfolio state (open positions,
  exposures, sector concentration, var budget, VIX regime)
- Does the proposal, if executed, stay within every limit?
- If any limit violated → reject with reason: "risk limit X exceeded: <detail>"
- If all pass → continue

### Check 4: Signal expectancy
- Read the signal's last-20-trade and last-40-trade expectancy from
  _performance.md (ADR-195 substrate)
- Is recent-20-trade expectancy above the decay guardrail in _risk.md?
  - If below → flag as defer with reason: "signal decay — recent 20-trade expectancy is <value>; operator review required"
  - If above → continue
- Is recent-40-trade Sharpe above the retirement-recommendation threshold?
  - If below → flag as defer with reason: "signal approaching retirement criteria — Sharpe <value>; operator should review in next audit"
  - If above → continue

### Check 5: Position-sizing math
- Does the proposal's position_size match the signal's sizing formula
  applied to current account equity, adjusted by Signal 5 VIX scalar
  if active?
- If mismatch → reject with reason: "position sizing violates formula: expected <X>, proposed <Y>"
- If matches → continue

### Check 6: Portfolio-level diversification
- Does adding this position concentrate sector exposure above limit?
- Does it stack on existing open positions per signal?
- If either concerning → flag as defer with reason specifying the concentration
- If clean → continue

### Final verdict
- If all checks pass → recommend APPROVE with summary:
  "Signal <N> fired within rules. Expectancy <X>R. Sizing
  formula-compliant. Portfolio impact within limits."
- If any rejection reason → recommend REJECT with that reason
- If any defer reason → recommend DEFER with the specific flag

## Tone
Quantitative. Specific. Reviewer does not editorialize. Every
verdict references the check and the numeric threshold. If a
proposal is rejected because Signal 2's recent expectancy is -0.7R
(below -0.5R guardrail), the verdict says exactly that.

## Anti-override discipline
The Reviewer does NOT approve proposals that violate these checks
on "this-time-feels-different" grounds. There is no such thing as
a feeling here. If a signal's expectancy has turned negative, the
signal is off-limits until quarterly audit decides whether to retire
or adjust it.

## When the Reviewer disagrees with itself
If two checks conflict (e.g., signal rules pass but recent
expectancy is below guardrail), Check 4's defer takes precedence.
The operator makes the call.
"""


# =============================================================================
# Tasks — playbook §3A.5
# =============================================================================

TASKS = [
    {
        "title": "Track universe",
        "slug": "track-universe",
        "schedule": "0 8,11,15 * * 1-5",  # 08:00, 11:30, 15:45 ET approx (weekday-only)
        "objective": {
            "deliverable": "Per-ticker price + indicator state files under /workspace/context/trading/{ticker}.md",
            "audience": "signal-evaluation task (downstream) + operator (reference)",
            "purpose": "Accumulate current price, moving averages, ATR, RSI, volume state for each universe ticker",
            "format": "markdown with YAML frontmatter per ticker (price, sma_20, sma_50, sma_200, rsi_14, atr_14, volume_20d_avg, last_updated)",
        },
        "success_criteria": [
            "Every universe ticker in _operator_profile.md has a corresponding {ticker}.md updated within last 4 hours during market hours",
            "Indicator computations use closing prices; runs skipped on US market holidays",
        ],
    },
    {
        "title": "Signal evaluation",
        "slug": "signal-evaluation",
        "schedule": "5 8 * * 1-5",  # 08:05 ET weekdays
        "objective": {
            "deliverable": "Per-signal state files at /workspace/context/trading/signals/{signal-slug}.md",
            "audience": "trade-proposal task (emits on fire) + pre-market-brief (narrative summary)",
            "purpose": "Evaluate each declared signal across universe; identify watch/triggered tickers; compute expectancy-20/40; flag decay",
            "format": "markdown with YAML frontmatter: signal_slug, state (active|flagged|retirement-recommended), watch_tickers, triggered_today, expectancy_r_20, expectancy_r_40, sharpe_lifetime",
        },
        "success_criteria": [
            "All 5 declared signals in _operator_profile.md have state files updated daily by 08:10 ET",
            "If a signal triggers on any ticker, trade-proposal task is invoked with full signal attribution",
            "Decay guardrails from _risk.md are evaluated and flagged in the state file",
        ],
    },
    {
        "title": "Pre-market brief",
        "slug": "pre-market-brief",
        "schedule": "15 8 * * 1-5",  # 08:15 ET weekdays
        "objective": {
            "deliverable": "Daily HTML brief composed from signal-evaluation output + portfolio state",
            "audience": "Operator (cockpit Overview surface; email is expository pointer per ADR-202)",
            "purpose": "One-glance morning check: which signals may fire, current exposure vs var budget, decay flags, VIX regime state",
            "format": "HTML with sections: Signal State Summary, Portfolio Exposure, Decay Flags, Regime State, Pending Proposals",
        },
        "success_criteria": [
            "Published by 08:20 ET on weekdays",
            "Zero narrative content beyond declared signals + declared risk metrics",
            "Quantitative frame only — numbers, thresholds, named signals",
        ],
    },
    {
        "title": "Trade proposal",
        "slug": "trade-proposal",
        "schedule": None,  # reactive, event-triggered by signal-evaluation
        "objective": {
            "deliverable": "ProposeAction with full signal attribution, forwarded to AI Reviewer → cockpit Queue",
            "audience": "AI Reviewer (evaluates via principles.md 6-check framework) → human operator (final approval)",
            "purpose": "When signal-evaluation detects a fire condition, emit a trade proposal that passes the Reviewer's Check 1 (signal attribution) by construction",
            "format": "Structured ProposeAction: signal_id, ticker, direction, entry_price, stop_loss, target, position_size, sizing_formula_trace, entry_rule_trace",
        },
        "success_criteria": [
            "Every proposal includes a named signal (1-5)",
            "Every proposal includes sizing-formula trace matching the signal's declared formula",
            "Every proposal is gated through AI Reviewer before reaching the Queue",
            "Zero proposals generated outside declared universe",
        ],
    },
    {
        "title": "Weekly performance review",
        "slug": "weekly-performance-review",
        "schedule": "0 18 * * 0",  # Sunday 18:00 ET
        "objective": {
            "deliverable": "Weekly HTML performance report with per-signal attribution",
            "audience": "Operator (Sunday planning surface)",
            "purpose": "Read _performance.md money-truth substrate; compute per-signal P&L / win-rate / expectancy / Sharpe; flag divergence from declared baselines",
            "format": "HTML with sections: Portfolio Totals, Per-Signal Attribution, Decay Flags, Regime History, Quarterly-Audit Flags",
        },
        "success_criteria": [
            "Published Sunday 18:00 ET every week",
            "Per-signal expectancy-20, expectancy-40, Sharpe-lifetime surfaced for all active signals",
            "Signals flagged for decay (guardrail crossed) are explicitly listed with quantitative reasoning",
        ],
    },
    {
        "title": "Quarterly signal audit",
        "slug": "quarterly-signal-audit",
        "schedule": "0 18 31 3,6,9,12 *",  # Mar/Jun/Sep/Dec 31 (approx quarter-end)
        "objective": {
            "deliverable": "Quarterly audit document: signals to retire, retune, or add to Signals 6-8 slots",
            "audience": "Operator (ratifies final decisions; YARNNN prepares analysis)",
            "purpose": "Operator-discipline ritual — prevents letting decayed signals linger; surfaces research candidates for new signals; never auto-modifies _operator_profile.md",
            "format": "HTML with sections: Signal Performance Summary, Retirement Candidates (with evidence), Retune Proposals, New Signal Research Candidates, Operator Decision Block (empty — operator fills)",
        },
        "success_criteria": [
            "Published end of each quarter (Mar/Jun/Sep/Dec)",
            "Every signal's last-40-trade Sharpe + expectancy surfaced with comparison to declared baseline",
            "Retirement recommendations cite specific guardrail crossings from _risk.md",
            "Operator decision block is left empty — this task does NOT mutate _operator_profile.md autonomously",
        ],
    },
]


# =============================================================================
# Execution
# =============================================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_workspace_file(conn, user_id: str, path: str, content: str, summary: str) -> None:
    """Upsert a workspace_file row by (user_id, path). Idempotent."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO workspace_files (user_id, path, content, summary, content_type, updated_at)
            VALUES (%s, %s, %s, %s, 'text/markdown', now())
            ON CONFLICT (user_id, path) DO UPDATE
              SET content = EXCLUDED.content,
                  summary = EXCLUDED.summary,
                  updated_at = now()
            """,
            (user_id, path, content, summary),
        )
    conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Show plan without writing")
    ap.add_argument(
        "--slug",
        default="alpha-trader",
        help="Persona slug from personas.yaml (default: alpha-trader)",
    )
    args = ap.parse_args()

    reg = load_registry()
    persona = reg.require(args.slug)

    if persona.platform_kind != "trading":
        raise SystemExit(
            f"scaffold_trader.py is trading-specific; persona '{args.slug}' is {persona.platform_kind}"
        )

    print(f"Persona: {persona.slug}  ({persona.email})")
    print(f"  user_id:      {persona.user_id}")
    print(f"  workspace_id: {persona.workspace_id}")
    print()

    if args.dry_run:
        print("DRY RUN. No writes.")
        print("Would write:")
        print(f"  POST /api/memory/user/identity         ({len(IDENTITY_MD):,} chars)")
        print(f"  POST /api/memory/user/brand            ({len(BRAND_MD):,} chars)")
        print(f"  DB upsert /workspace/review/principles.md                ({len(PRINCIPLES_MD):,} chars)")
        print(f"  DB upsert /workspace/context/trading/_operator_profile.md ({len(OPERATOR_PROFILE_MD):,} chars)")
        print(f"  DB upsert workspace/context/trading/_risk.md [no leading slash per risk_gate.py:48] ({len(RISK_MD):,} chars)")
        print(f"  POST /api/tasks × {len(TASKS)}, then PUT status=paused on each")
        for t in TASKS:
            print(f"      - {t['slug']}  schedule={t['schedule']!r}")
        return 0

    errors: list[str] = []

    # ----- Step 1-2: IDENTITY + BRAND via prod API -----
    print("[1/6] POST /api/memory/user/identity")
    with ProdClient(persona, registry=reg) as pc:
        r = pc.post("/api/memory/user/identity", json={"content": IDENTITY_MD})
        if r.status_code >= 300:
            errors.append(f"identity: [{r.status_code}] {r.text[:200]}")
            print(f"  FAIL [{r.status_code}]: {r.text[:200]}")
        else:
            print(f"  OK  ({len(IDENTITY_MD):,} chars)")

        print("[2/6] POST /api/memory/user/brand")
        r = pc.post("/api/memory/user/brand", json={"content": BRAND_MD})
        if r.status_code >= 300:
            errors.append(f"brand: [{r.status_code}] {r.text[:200]}")
            print(f"  FAIL [{r.status_code}]: {r.text[:200]}")
        else:
            print(f"  OK  ({len(BRAND_MD):,} chars)")

        # ----- Step 6: Create 6 tasks (done via prod API while JWT is live) -----
        print(f"[6/6] POST /api/tasks × {len(TASKS)}  then PUT status=paused")
        for t in TASKS:
            payload = {k: v for k, v in t.items() if v is not None}
            r = pc.post("/api/tasks", json=payload)
            if r.status_code == 409:
                print(f"  SKIP {t['slug']}  (already exists)")
                continue
            if r.status_code >= 300:
                errors.append(f"task {t['slug']}: [{r.status_code}] {r.text[:200]}")
                print(f"  FAIL {t['slug']}  [{r.status_code}]: {r.text[:200]}")
                continue
            # Flip to paused
            r2 = pc.request(
                "PUT",
                f"/api/tasks/{t['slug']}",
                json={"status": "paused"},
            ) if hasattr(pc, "request") else pc._client.put(
                f"{pc.base}/api/tasks/{t['slug']}",
                json={"status": "paused"},
            )
            if r2.status_code >= 300:
                errors.append(f"task {t['slug']} pause: [{r2.status_code}] {r2.text[:200]}")
                print(f"  CREATED but pause FAIL {t['slug']}: [{r2.status_code}] {r2.text[:200]}")
            else:
                print(f"  OK   {t['slug']}  (created + paused)")

    # ----- Step 3-5: DB writes for gated paths -----
    print("[3/6] DB upsert /workspace/review/principles.md")
    conn = pg_connect()
    try:
        upsert_workspace_file(
            conn,
            persona.user_id,
            "/workspace/review/principles.md",
            PRINCIPLES_MD,
            "Reviewer principles — Simons Option B (playbook §3A.4)",
        )
        print(f"  OK  ({len(PRINCIPLES_MD):,} chars)")

        print("[4/6] DB upsert /workspace/context/trading/_operator_profile.md")
        upsert_workspace_file(
            conn,
            persona.user_id,
            "/workspace/context/trading/_operator_profile.md",
            OPERATOR_PROFILE_MD,
            "Operator profile — declared universe + 5 signals (playbook §3A.2)",
        )
        print(f"  OK  ({len(OPERATOR_PROFILE_MD):,} chars)")

        print("[5/6] DB upsert workspace/context/trading/_risk.md  (no leading slash per risk_gate.py:48)")
        upsert_workspace_file(
            conn,
            persona.user_id,
            "workspace/context/trading/_risk.md",
            RISK_MD,
            "Risk parameters — Simons Option B (playbook §3A.3)",
        )
        print(f"  OK  ({len(RISK_MD):,} chars)")
    finally:
        conn.close()

    print()
    if errors:
        print(f"FINISHED WITH {len(errors)} ERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SCAFFOLDING COMPLETE.")
    print("Run:  .venv/bin/python api/scripts/alpha_ops/verify.py alpha-trader")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
