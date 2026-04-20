# Alpha-1 Playbook — Shared Operator Account + Omniscient Claude Presence

> **Status**: Canonical — single source of truth for Alpha-1 testing
> **Date**: 2026-04-20
> **Authors**: KVK, Claude
> **Grounded in**: ADR-191 (polymath ICP + conglomerate alpha), ADR-194 v2 (Reviewer seat interchangeability), ADR-198 v2 (cockpit service model), FOUNDATIONS v6.0 (Axiom 2 Identity, Axiom 6 Channel, Derived Principle 12)
> **Rule**: This doc is the sole governance artifact for Alpha-1 alpha testing. It is updated as we iterate, and archived when the alpha concludes (post-rollup into subsequent ADRs). Any alpha-testing artifact not captured here should either be merged in, or is not authoritative.

---

## What this playbook is

The **single source of truth** for Alpha-1 alpha testing. Covers:

1. **The thesis** — why we're doing this, why now, why this persona
2. **The governance model** — who fills which cognitive seat; shared-access discipline
3. **The persona spec** — full setup content for a Jim-Simons-inspired systematic retail trader (Option B scope: 5–8 declared signals with measured edge)
4. **The setup sequence** — exactly how the account is created and onboarded
5. **The operating protocol** — day-to-day rhythm, coordination between KVK and Claude
6. **Claude's rules of engagement** — what I can do autonomously, what I escalate, what I never touch
7. **The friction-capture loop** — how observations turn into ADR seeds
8. **Phase transitions** — scope expansion criteria (e-commerce, real trading, external operator)
9. **Ledger of active artifacts** — what belongs in `docs/alpha/` and why

If an artifact about Alpha-1 doesn't trace back to a section in this playbook, either it isn't authoritative or this playbook needs updating to name it.

---

## 1. Thesis

### Why we're doing this

The architecture (FOUNDATIONS v6.0 + 20+ ADRs since 189) has earned the right to be used. Every ADR after 189 was load-bearing-but-speculative — the cockpit framing, the authored-team moat, the Reviewer layer's capital-EV reasoning all bet on operator behavior we haven't observed. The next ADR built without alpha signal is probably half-right and half-wasted. The next ADR built *after* a real operator exercises the substrate is grounded.

### Why one account, not two

Original conglomerate-alpha plan called for e-commerce + trader simultaneously. Revised to **single-account scope** for Alpha-1 because:

- **Attention discipline produces sharper friction signals.** Two simultaneous personas dilute observation quality.
- **The trader is the harder stress test.** If Reviewer capital-EV reasoning + money-truth substrate + compose pipeline work for the trader, they very likely work for commerce. Reverse is less clearly true.
- **Circling back later is a reinforcement pattern.** When we add e-commerce as Alpha-1.5, we'll know which frictions are architecture-level (both personas feel them) vs. domain-specific (only one does). This is the anti-verticalization gate from ADR-191 operating correctly.

### Why a Simons-inspired systematic trader

Jim Simons — Renaissance Technologies, Medallion Fund — is the prototype of the **systematic quantitative operator**. The persona is:

- **Mathematician, not narrator.** Edge comes from measurable signals, not stories. Trades happen when signals fire, not when the operator feels strongly.
- **Empirically skeptical.** Discretionary overrides are treated as failure modes, not strengths. "We don't override the model" is the cultural spine.
- **Measures obsessively.** Every signal has performance history. Every trade attributes to a signal. Every drawdown gets post-mortemed. Unknown performance = signal doesn't exist yet.
- **Small edge × many trades = return.** Not holding-period plays; short-to-medium horizon systematic exposure. Many small wins, tightly-controlled losses.
- **Respects what it doesn't know.** Drawdown math isn't optional. Position sizing is mechanical.

This persona is the **hardest stress test** for three architectural commitments:

1. **AI Reviewer's capital-EV reasoning (ADR-194 §5).** A Simons-trader's Reviewer doesn't reason about character — it reasons about *signal alignment, expectancy, and drawdown contribution*. If the Reviewer can honor that frame (quote signal win rates, flag signal-incompatible trades, reason about position-level contribution to portfolio var), the architecture's claim of "capital-EV not rule-checking" is validated. If it can't, we learn that immediately.
2. **Money-truth substrate (`_performance.md` per ADR-195).** Simons-trader's `_performance.md` must carry *per-signal* attribution: which signals generated which trades, what each signal's expectancy looks like, how signals behave in different regimes. If the file schema + reconciler can honor this, money-truth is substrate-ready. If not, we learn the shape needs work.
3. **Cockpit-as-operator-surface (ADR-198 v2).** A Simons-trader doesn't live in the cockpit all day reacting. They check Overview in the morning to confirm systems ran correctly, review signal-level attribution weekly, intervene rarely. If the cockpit only rewards high-frequency operators, this persona surfaces that gap.

**Scope of "Simons-inspired" here = Option B (medium).** 5–8 declared signals with explicit entry/exit/sizing rules, per-signal performance tracking, quantitative Reviewer reasoning. Not light (rule-following discretion) — not heavy (mini-Medallion, beyond retail paper capability). The *honest* stress test.

### Why shared access matters structurally

The Reviewer layer was designed for seat interchangeability (ADR-194 v2). Shared-access alpha cashes that design in:

- **KVK** fills the primary Operator seat — strategy-level calls, signal roster curation, phase transitions
- **AI Reviewer** fills the automated Reviewer seat — per-proposal capital-EV checks via `review-proposal` task (ADR-194 Phase 3)
- **Claude** fills the secondary Operator + meta-observer seat — lands on cockpit, exercises the same surfaces a human uses, approves reversibles within tight discretion bounds, observes friction, writes ADR seeds

"Hand the keys to the AI" doesn't mean "give Claude backend access." It means Claude operates *via the exact interface human operators use*. If the cockpit fails for Claude, it fails for humans. If it works for Claude, human usability is the polish layer on a known-working substrate.

---

## 2. Governance model

### The account

| Account | Persona | Primary platform | Real/paper |
|---|---|---|---|
| `alpha-trader` | Simons-inspired systematic retail trader (Option B: 5–8 declared signals, measured edge) | Alpaca (paper throughout Alpha-1) | Paper throughout Alpha-1; live is Alpha-2 decision |

Real Supabase user + workspace, normal signup flow, OAuth to Alpaca paper, normal $3 signup grant. No special infrastructure.

### Three seats, one account

| Seat | Filled by | Scope | `decisions.md` tag |
|---|---|---|---|
| **Operator (primary)** | KVK | Strategy: signal roster, capital allocation across signals, phase transitions, principles + risk edits | `human:<user_id>` |
| **AI Reviewer** | AI Reviewer agent (ADR-194 Phase 3 — runs automatically via `review-proposal` reactive task) | Per-proposal: signal-alignment check, capital-EV evaluation, risk-rule enforcement. Approve / reject / defer. | `ai:reviewer-sonnet-v1` (or the version tag in use) |
| **Operator (secondary) + meta-observer** | Claude (authenticated operator session, same Supabase user or a second user sharing the workspace if multi-user support lands — see §open questions) | Reviews AI Reviewer calibration. Approves reversibles within tight bounds. Escalates irreversibles + signal-incompatible trades + ambiguous deferrals. Observes friction. Writes observation notes. | `human:<user_id>` (session auth limitation, §audit-trail-limitation) |

### What Claude can do as authenticated operator

- Read every cockpit surface (Overview, Team, Work, Context, Review, `/chat`)
- Read any substrate file via Context or `/api/workspace/file?path=`
- Approve / reject **reversible** proposals via cockpit Queue (within the tight Simons-persona discretion ladder, §6)
- Talk to YARNNN in the ambient rail — invoke primitives, query context, get second opinions
- Trigger tasks manually via `/work`
- Read `activity_log`, `token_usage`, `agent_runs` — any audit telemetry
- Propose edits to `principles.md`, `_risk.md`, `_operator_profile.md`, signal definitions — *to KVK for ratification*

### What Claude does NOT do

- **Approve `irreversible` proposals.** Always escalate. Structural safety fence, not trust.
- **Change persona identity files without KVK.** IDENTITY.md, BRAND.md, `_operator_profile.md`, `principles.md`, `_risk.md`, signal definitions — all joint decisions.
- **Override the AI Reviewer without explicit reasoning.** If AI Reviewer rejected, Claude does not approve unilaterally. Claude may dispute via observation note + escalation.
- **Dissolve, archive, or pause agents without KVK.**
- **Switch platform connection from paper to live.** Never. Phase transition with explicit ADR amendment.
- **Handle billing.** Alpha runs on KVK's card + $3 grant.
- **Act in ways incompatible with the Simons-persona's declared character** (e.g., approving a discretionary trade with no signal attribution, just because it seems like a good idea).

### Audit-trail limitation (open)

Session auth doesn't distinguish "KVK logged in" from "Claude logged in" — both get tagged `human:<user_id>`. For Alpha-1 this is acceptable because:
- Trust loop is joint (we're both supervising the same work)
- Post-hoc attribution is recoverable via cross-reference with observation notes (Claude logs every action to `docs/alpha/observations/`)
- Time-stamping + observation notes together form a working audit

If this becomes a real problem, we add session-metadata flagging or use separate Supabase users with workspace-sharing (ADR candidate if triggered). Not blocking for Alpha-1.

---

## 3. Persona spec — `alpha-trader`

### 3.1 Identity (`/workspace/IDENTITY.md`)

Seeded into the workspace during the first YARNNN conversation, pasted as rich input. YARNNN processes via `UpdateContext(target="identity")` per ADR-190 inference-driven scaffold.

```markdown
# Alpha Trader — systematic retail operator (Simons-inspired)

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
```

### 3.2 Operator profile (`/workspace/context/trading/_operator_profile.md`)

```markdown
# Operator profile — Alpha Trader (Simons, Option B)

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
```

### 3.3 Risk parameters (`/workspace/context/trading/_risk.md`)

```markdown
# Risk parameters — Alpha Trader (Simons, Option B)

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
```

### 3.4 Reviewer principles (`/workspace/review/principles.md`)

```markdown
# Reviewer principles — Alpha Trader (Simons, Option B)

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
```

### 3.5 Task scaffolding target

YARNNN composes via conversation during Phase 1 onboarding. Target set (iterate if YARNNN proposes a better fit for the persona):

| Task | Kind | Cadence | Purpose |
|---|---|---|---|
| `track-universe` | accumulates_context | 3× daily (8:00, 11:30, 15:45 ET) | Updates price/indicator state for each ticker in `_operator_profile.md` universe. Feeds `/workspace/context/trading/{ticker}.md`. |
| `signal-evaluation` | accumulates_context | Daily (8:05 ET, after track-universe morning run) | **NEW for Simons-persona.** For each declared signal in `_operator_profile.md`, evaluates current state across universe. Writes signal-state to `/workspace/context/trading/signals/{signal-slug}.md`: which tickers are in "watch" state, which triggered today, current expectancy-20/40, decay flags. |
| `pre-market-brief` | produces_deliverable | Daily 8:15 ET | Composed from signal-evaluation output. Human-readable morning brief: which signals may fire, portfolio exposure vs var budget, decay flags, regime state. Cockpit surface (per ADR-198 §6) — email is expository pointer. |
| `trade-proposal` | reactive (event-triggered by signal-evaluation) | On-demand | When signal-evaluation detects a fire condition, emits a ProposeAction with full signal attribution (see Reviewer Check 1). Runs through AI Reviewer → cockpit Queue for human approval. |
| `weekly-performance-review` | produces_deliverable | Sunday 18:00 ET | Reads `_performance.md` (ADR-195 substrate). Per-signal P&L, win rate, expectancy, Sharpe. Flags decay. Compares to declared baselines. |
| `quarterly-signal-audit` | goal (4-week bounded cycle, Sunday ending Mar/Jun/Sep/Dec 31) | Quarterly | Comprehensive review: which signals to retire, which to retune, candidates for Signals 6–8 slots. Operator drafts final decisions; YARNNN prepares the analysis. |

### 3.6 Money-truth substrate expectations (`_performance.md` shape)

ADR-195 v2 establishes `_performance.md` as filesystem-native money-truth per domain. For the trading domain under Simons-persona, the reconciler must populate **per-signal attribution**. Expected frontmatter shape:

```markdown
---
domain: trading
last_reconciled_at: <iso>
currency: USD
processed_event_keys:
  - alpaca_order_id:<id>
  - ...

totals:
  reconciled_event_count: <n>
  aggregate_pnl_cents: <n>
  wins: <n>
  losses: <n>
  realized_sharpe: <float>

by_signal:
  signal-1-momentum-breakout:
    trades_20: <n>
    trades_40: <n>
    trades_lifetime: <n>
    wins: <n>
    losses: <n>
    avg_win_r: <float>
    avg_loss_r: <float>
    expectancy_r_20: <float>        # recent 20-trade expectancy in R-multiples
    expectancy_r_40: <float>
    sharpe_lifetime: <float>
    max_drawdown_r: <float>
    state: "active" | "flagged" | "retirement-recommended"
  signal-2-mean-reversion-oversold:
    ...

rolling_windows:
  daily_var_7d: <cents>
  weekly_drawdown: <cents>
  vix_regime_days_active_30d: <n>
---

# Trading performance

Narrative body regenerated on each reconciler run. Highlights:
- Signal-level winners and losers in the past 7/30 days
- Regime state (VIX scalar active or not)
- Recent notable trades with attribution
- Signals flagged for quarterly review
```

**Key change from generic `_performance.md`:** the `by_signal` block. If the backend reconciler's current schema doesn't support per-signal attribution, that's an observation item (ADR candidate — schema extension for Simons-class operators). Does NOT block Alpha-1 start; the substrate degrades gracefully (reconciler writes overall totals; operator + Claude observe the gap).

---

## 4. Setup sequence

### Phase 0 — prerequisites

- [ ] Shared-credentials vault chosen (1Password / Bitwarden / team vault) — KVK picks, communicates location
- [ ] Persona email address (`alpha-trader@<domain>` or Gmail alias) — KVK creates
- [ ] Alpaca paper API key + secret provisioned — KVK provisions
- [ ] Inbox confirmed where daily-update expository-pointer emails will land — KVK confirms

### Phase 1 — account creation (KVK)

1. Sign up via normal YARNNN signup flow using the persona email. Note `user_id` from Supabase.
2. In the first YARNNN chat session, paste the IDENTITY.md content from §3.1 as rich input. YARNNN processes via inference-driven scaffold.
3. Confirm / refine YARNNN-proposed `/workspace/BRAND.md`. Low stakes; brand for a systematic-trader persona should be terse, quantitative, no hedging language.
4. Approve YARNNN-proposed task scaffolding. Goal: converge on the task set in §3.5. Iterate if YARNNN proposes tasks that fit the persona better — use judgment; the `signal-evaluation` task is the specifically-Simons piece and is non-negotiable.
5. Connect Alpaca paper via the integrations flow.
6. Seed the four identity-domain files via YARNNN rail:
   - `_operator_profile.md` (full content from §3.2)
   - `_risk.md` (full content from §3.3)
   - `principles.md` (full content from §3.4)
   - Initial signal state files at `/workspace/context/trading/signals/signal-N-<slug>.md` (can start empty — `signal-evaluation` populates on first run)
7. Store credentials in the shared vault.
8. Wait for first `track-universe` + `signal-evaluation` runs to populate substrate. First reconciler pass will establish `_performance.md` baseline (likely empty / near-empty — signals need trade history to build expectancy).
9. Confirm first daily-update email arrives tomorrow morning (baseline check).

### Phase 2 — Claude operator onboarding

Once Phase 1 is complete and credentials shared:

1. Claude logs in via authenticated web access.
2. Lands on `/overview`.
3. Opens YARNNN rail: *"I'm operating this account alongside KVK. Orient me: what does IDENTITY.md say about who this operator is? What signals are declared? What's scaffolded? What's pending?"*
4. Reads IDENTITY.md + `_operator_profile.md` + `principles.md` + `_risk.md` via Context.
5. Reviews Team — confirms scaffolded agent roster matches the persona's work.
6. Reviews Work — confirms `signal-evaluation` is running, `track-universe` cadence is sensible, `trade-proposal` reactive task is wired.
7. Visits `/workspace/context/trading/signals/` and skims each signal's state file. Baseline: "signals initialized, no trade history yet."
8. Writes the baseline observation: `docs/alpha/observations/{YYYY-MM-DD}-alpha-trader-first-session.md` — include: first impressions, anything surprising, anything missing, whether the `by_signal` block in `_performance.md` is populated or degraded gracefully.
9. Confirms to KVK: "baseline set, beginning alpha operation."

### Phase 3 — first signals, first decisions

- First ~2 weeks are warm-up. Signals need to fire, trades need to execute (on paper), `_performance.md` needs to accumulate per-signal history. During this period:
  - Expect no strong Reviewer calibration signal — too few trades per signal
  - Focus observation on: does the scaffolding work? Do proposals render correctly? Does the Reviewer's structured reasoning (§3.4 checks) actually execute the checks? Does `_performance.md` populate by-signal attribution?
- After ~20 trades across signals, preliminary calibration signal becomes available.
- After ~40 trades, quarterly-signal-audit task has enough substrate to run meaningfully.

---

## 5. Operating protocol

### 5.1 Daily rhythm (trading days)

**Pre-market (7:30–9:15 ET):**
- 8:00: `track-universe` morning run
- 8:05: `signal-evaluation` runs → state files updated
- 8:15: `pre-market-brief` fires → expository-pointer email arrives → Claude opens `/overview` from deep-link
- 8:15–8:45: Claude reviews Overview Since-last-look + any Queue items. Reads pre-market brief on Work task-detail. Notes any signal-state surprises (decay flags, regime-activation).
- 8:45–9:15: If any trade-proposals pending from overnight or pre-market signal fires, Claude + KVK coordinate out-of-band on approval.

**Market hours (9:30–16:00 ET):**
- Signals can fire intraday (track-universe runs at 11:30 and 15:45). Each fire → `trade-proposal` reactive task → AI Reviewer → cockpit Queue.
- Claude checks Overview Queue periodically (every 1–2 hours during market; not minute-by-minute — Simons-persona isn't a scalper).
- For each pending proposal:
  - Read the proposal card (action, signal attribution, Reviewer verdict + reasoning chain)
  - Apply the discretion ladder (§6)
  - Approve, escalate, or observe per the ladder

**Post-close (16:00–17:00 ET):**
- Claude reads day's `decisions.md` tail — AI Reviewer's verdicts + rationale. Were any rejections debatable? Any approvals that executed against declared signals correctly? Any concerning patterns?
- Reconciler runs in evening (backend cron) — updates `_performance.md` with any day's fills. Claude reads the update next morning.
- Observation note logged if anything friction-worthy surfaced.

### 5.2 Weekly rhythm

**Friday after close:**
- Optional mid-week pulse if week's observations are stacking.

**Sunday (performance-review day):**
- 18:00 ET: `weekly-performance-review` task fires → output at `/tasks/weekly-performance-review/outputs/{date}/`
- 18:30–19:30: Claude + KVK review output together (async OK). Per-signal stats, decay flags, regime history.
- KVK captures "what this surface SHOULD have shown" as observation notes.
- Joint weekly rollup report at `docs/alpha/reports/week-{N}-alpha-trader.md`:
  - What worked
  - What surfaced as friction
  - Per-signal performance vs. declared baseline
  - Whether Reviewer's quantitative reasoning honored the framework
  - ADR candidates
  - Phase-transition signal (are we tracking toward Alpha-1.5 readiness?)

### 5.3 Quarterly rhythm

- `quarterly-signal-audit` fires on last Sunday of each quarter
- Joint operator decision: which signals to retire, retune, or add (Signals 6–8)
- Signal-definition edits update `_operator_profile.md` — this is a persona-identity file, so it's a joint decision, captured in observation + commit

### 5.4 Coordination between KVK and Claude

- **Out-of-band updates** happen in this Claude Code session or an agreed channel — not inside the YARNNN account.
- **In-band in YARNNN**: both use the rail; session history is shared; no impersonation; each message attributes to whoever's authenticated.
- **Proposal approval race**: first authorized operator to act wins. OK for Alpha-1; revisit if it causes confusion.
- **ADR-triggering observations**: Claude drafts; KVK ratifies. Same PR pattern as architecture ADRs.

---

## 6. Claude's rules of engagement

### 6.1 The anti-discretion ladder (Simons-specific)

Under Simons-persona, Claude-as-operator's default is **DO NOT OVERRIDE THE SYSTEM**. The persona's declared character is mechanical signal execution. Claude's discretion ladder reflects this:

| Situation | Claude action |
|---|---|
| AI Reviewer approved (verdict: APPROVE), proposal pending human | **Approve in cockpit** if: (a) verdict reasoning references all six Reviewer checks, (b) signal attribution present, (c) position sizing matches formula, (d) risk limits clean, (e) proposal is `reversible` OR `soft-reversible`. All five required; any missing → escalate. |
| AI Reviewer approved, proposal is `irreversible` | **Always escalate to KVK.** Irreversibility overrides discretion even when verdict is clean. |
| AI Reviewer deferred (verdict: DEFER) | **Default: escalate to KVK.** Deferrals signal ambiguity (signal decay flag, concentration concern). Claude does not resolve ambiguity unilaterally. |
| AI Reviewer rejected (verdict: REJECT) | **Observe, do not override.** If Claude believes the rejection was wrong, write observation note + escalate the observation, not the approval. |
| No Reviewer verdict yet | **Wait.** Do not preempt. |
| Proposal has no signal attribution | **Escalate with rejection recommendation.** Signal attribution is required per §3.4 Check 1; a proposal missing attribution is a substrate bug or agent misbehavior — flag it. |
| Proposal for ticker outside declared universe | **Escalate.** Universe drift is identity drift. |
| Trade would open a position that would bring portfolio exposure above 100% gross | **Escalate.** Leverage cap is character-level. |
| Weekly-performance-review shows a signal flagged for review | **Observe.** No operator action on Claude's part — the flag is for quarterly audit. |

### 6.2 What I can do autonomously

- Approve reversibles that pass the five-condition test above
- Read any cockpit surface, any substrate, any audit telemetry
- Talk to YARNNN in the rail — including asking it to explain Reviewer reasoning, walk through signal state, summarize `_performance.md` for a specific signal
- Trigger `track-universe`, `signal-evaluation`, `pre-market-brief` manually if scheduled runs miss (e.g., if I'm debugging a missed fire)
- Write observation notes
- Propose ADR-level changes, principles edits, signal-definition edits to KVK

### 6.3 What I never do

- Override a Reviewer rejection
- Approve an irreversible
- Approve without signal attribution
- Approve outside the declared universe
- Modify `_operator_profile.md`, `_risk.md`, `principles.md`, IDENTITY.md, BRAND.md directly
- Add or retire a signal (quarterly audit only; joint decision)
- Dissolve / archive / pause agents
- Switch paper → live
- Handle billing
- Impersonate KVK (every action tagged to my authenticated identity)
- Speak in narrative or character language to YARNNN about this account (e.g., "I have a feeling about X" — not allowed; stay in the quantitative frame)

### 6.4 Escalation mechanics

Claude escalates → leaves proposal in `pending` → writes observation note naming `proposal_id` + reasoning → messages KVK out-of-band → KVK decides. Proposal TTL is the silent safety net.

---

## 7. Friction-capture loop

### 7.1 Observation note format

Pin at `docs/alpha/observations/{YYYY-MM-DD}-alpha-trader-{slug}.md`:

```markdown
# {YYYY-MM-DD} — alpha-trader — {one-line summary}

**Context:** what was I trying to do? (e.g., "approve proposal for NVDA Signal-1 trigger")
**What happened:** what the cockpit / Reviewer / agent did.
**Friction:** what was harder or more confusing than it should be.
**Hypothesis:** what change would resolve it? (prompt tweak / component patch / ADR amendment / new ADR)
**Dimensional classification:** which FOUNDATIONS v6.0 dimension(s) does this affect? (Substrate / Identity / Purpose / Trigger / Mechanism / Channel)
**Simons-persona specificity:** is this friction specific to the systematic-trader character, or would any operator hit it?
**Action:** what I did (approved / escalated / observed only / etc.).
**ADR candidate:** yes | no | maybe — and at what trigger (1x, 2x, only-if-e-commerce-corroborates).
```

### 7.2 Weekly rollup format

`docs/alpha/reports/week-{N}-alpha-trader.md`:

```markdown
# Week {N} — alpha-trader — {YYYY-MM-DD} to {YYYY-MM-DD}

## Operational summary
- Signals fired: {count} across {signal list}
- Trades executed: {approvals / rejections / TTL-expired}
- Reviewer verdict distribution: approve/reject/defer counts
- Portfolio state: start balance → end balance, drawdown, var utilization
- Any regime activations (Signal 5 VIX scalar)

## Signal-level performance (per-signal short table)
| Signal | Trades this week | Cumulative expectancy_r_20 | State (active/flagged/retirement) |

## Friction themes this week
- {Theme 1 with 2-3 linked observation notes}
- {Theme 2 ...}

## Reviewer calibration check
- Did the AI Reviewer's six-check framework honor itself?
- Any verdicts that looked wrong on reflection?
- Any missed checks?

## Cockpit usability check
- Did Overview surface the right stuff?
- Did Work task-detail help or hinder?
- Did Review chronicle give a clear audit picture?

## ADR candidates identified
- {Candidate 1 — specific observation links — dimension affected — phase-2 vs. phase-3 defer}

## Phase-transition signal
- Are we on track toward Alpha-1.5 readiness (2+ weeks clean, declining friction)?
```

### 7.3 Decision tree — observation → ADR

- **Same friction 2+ weeks in a row** → ADR candidate
- **Single friction, prompt-fixable** → update YARNNN prompt + `api/prompts/CHANGELOG.md`, no ADR
- **Single friction, component-fixable** → patch, no ADR
- **Structural gap (missing primitive / missing dimension behavior / missing substrate field)** → ADR immediately, regardless of frequency
- **Simons-persona-only friction** → defer ADR judgment until Alpha-1.5 e-commerce corroborates (anti-verticalization gate per ADR-191 DOMAIN-STRESS-MATRIX). Might still warrant a prompt tweak or task-type refinement in the interim.
- **Reviewer-calibration friction** → feeds ADR-194 Phase 4 (calibration tuning), which explicitly waits for alpha data. Log in weekly report Reviewer Calibration section.

---

## 8. Phase transitions

Never skip phases. Each phase's clean-operation period is the license for the next.

| Phase | Current? | Trigger to advance | Decision locus |
|---|---|---|---|
| **Alpha-1** | ✅ now | — | — |
| **Alpha-1.5** (add e-commerce persona as second shared account) | no | 2+ weeks of Alpha-1 clean operation; friction trend declining; e-commerce persona spec drafted | Joint decision captured in playbook update |
| **Alpha-2** (switch trader from paper to live, start small — $5k initial) | no | Alpha-1.5 clean for 4+ weeks; Reviewer calibration data sufficient (≥100 AI Reviewer verdicts with attribution to outcomes via `_performance.md`); per-signal Sharpe within declared baselines; KVK comfort | Joint decision; explicit ADR amendment to this playbook |
| **Alpha-3** (onboard first external friend as operator, could be trader or e-commerce) | no | Alpha-2 clean for 4+ weeks; ICP signal present; external-operator-onboarding scope doc drafted | Joint decision; dedicated scope doc |

### Why e-commerce is deferred, not cancelled

Adding e-commerce as a second simultaneous alpha was the original plan. Deferring is a deliberate scope choice:

- **Single-account attention produces sharper friction signals.** Two simultaneous personas dilute observation quality.
- **The trader is the harder stress test.** Reviewer capital-EV reasoning, money-truth substrate, signal-attribution — if these work for a systematic trader, they'll very likely work for commerce. Reverse is less clearly true.
- **Circling back later is a reinforcement pattern.** When we add e-commerce, we'll know which frictions are architecture-level (both personas feel them) vs. domain-specific (only one does). That's the anti-verticalization gate (ADR-191) operating correctly.

When we add e-commerce in Alpha-1.5, this playbook's §3 expands with a second persona spec (analogous structure, adapted to commerce domain). `DOMAIN-STRESS-MATRIX.md` gains two real columns of data.

---

## 9. Active-artifact ledger — what belongs in `docs/alpha/`

For this playbook to be the single source of truth, `docs/alpha/` structure is:

```
docs/alpha/
├── ALPHA-1-PLAYBOOK.md      ← this file; sole governance doc
├── observations/            ← observation notes, one per event
│   └── {YYYY-MM-DD}-alpha-trader-{slug}.md
├── reports/                 ← weekly and quarterly rollups
│   ├── week-{N}-alpha-trader.md
│   └── quarter-{Q}-alpha-trader.md
└── archive/                 ← after alpha concludes
    └── {previous playbook versions, rolled-up reports, etc.}
```

**What goes in `observations/`:** small, timestamped, friction-specific notes in the format from §7.1. Zero ceremony. One per friction event. A busy day may have 3–5; a quiet day zero.

**What goes in `reports/`:** consolidated rollups per §7.2. One per week per account. Quarterly rollups when we reach phase-transition decisions.

**What goes in this playbook:** governance, persona spec, operating protocol, rules of engagement, phase-transition criteria. Anything structural. Update in place; revision history at bottom tracks evolution.

**What does NOT go in `docs/alpha/`:**
- ADRs (those go in `docs/adr/` — observation notes *seed* ADRs but don't substitute for them)
- Prompt changes (those log to `api/prompts/CHANGELOG.md`)
- Component code (that's in `web/` and `api/`)
- Permanent architectural documentation (that's `docs/architecture/`)

---

## 10. Open questions deferred to Week-1 iteration

1. **Credentials-vault mechanics** — vault location, rotation policy, backup. KVK's operational decision.
2. **KVK time budget** — hours/week committed to alpha observation. Shapes Claude's autonomy tolerance.
3. **Communication cadence** — daily / weekly / ad-hoc. Start ad-hoc; formalize if needed.
4. **Observation-doc review rhythm** — batch at weekly rollup (default), or time-sensitive escalation if friction warrants.
5. **ADR-amendment protocol from alpha** — same PR pattern; observation subfolder is the input.
6. **Claude's authenticated session access** — how does Claude Code (this session) actually log in to the web app? Likely via credentials passed through a browser session KVK initiates; refined during Phase 2 onboarding.
7. **`_performance.md` per-signal schema** — backend's current reconciler shape may or may not support `by_signal` attribution. Verify during Phase 3 first-trades. If missing, log as structural-gap ADR candidate.
8. **Reviewer reasoning format** — does the AI Reviewer actually write its six-check chain to `decisions.md`, or does it produce a shorter summary? Verify against the first few AI verdicts; may require prompt adjustment.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial playbook (Rohn-inspired, later corrected). |
| 2026-04-20 | v2 — Full rewrite. Persona corrected to Jim Simons (systematic quantitative) — Option B scope: 5–8 declared signals, measured edge, quantitative Reviewer reasoning. IDENTITY.md, `_operator_profile.md` (with 5 initial signals + 3 reserved slots), `_risk.md` (statistical limits: portfolio var, per-signal caps, sector concentration, VIX regime scalar), and `principles.md` (six-check Reviewer evaluation framework) all rewritten end-to-end. New `signal-evaluation` task added to scaffolding. Anti-discretion ladder for Claude — default is DO NOT OVERRIDE. Friction-capture extended with Simons-persona-specificity field. Section 9 added (active-artifact ledger) to make the playbook the single documentation source for Alpha-1. Section 10 expanded open questions with `_performance.md` per-signal schema + Reviewer reasoning format. Singular implementation — v1 fully superseded. |
