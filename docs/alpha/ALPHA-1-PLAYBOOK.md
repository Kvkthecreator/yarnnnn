# Alpha-1 Playbook — Shared Operator Account + Omniscient Claude Presence

> **Status**: Canonical — single source of truth for Alpha-1 testing
> **Date**: 2026-04-20 (last vocabulary-sweep refresh: 2026-04-29)
> **Authors**: KVK, Claude
> **Grounded in**: ADR-191 (polymath ICP + conglomerate alpha), ADR-194 v2 (Reviewer seat interchangeability), ADR-228 (cockpit-as-operation), FOUNDATIONS v6.0 (Axiom 2 Identity, Axiom 6 Channel, Derived Principle 12)
> **Rule**: This doc is the sole governance artifact for Alpha-1 alpha testing. It is updated as we iterate, and archived when the alpha concludes (post-rollup into subsequent ADRs). Any alpha-testing artifact not captured here should either be merged in, or is not authoritative.
>
> **Refactor-wave note (2026-04-29, Pass 4 complete)**: This doc was realigned across the late-April substrate-dissolution wave (ADR-227/228/230/231/233/235/237/238/239). §3A.5 reframes "tasks" as **recurrence declarations** with natural-home YAML substrate paths (ADR-231 D2). §3A.5b documents the back-office recurrences scaffolded automatically per ADR-164. §5.1 daily rhythm describes the four cockpit faces (ADR-228) instead of the pre-228 BriefingStrip framing. The four-pass refresh log lives in commits `9c071d1` (Pass 1 vocabulary), `89738a3` (Pass 2 invariants), `77d654f` (Pass 3 observation), and the current commit (Pass 4 playbook §3A.5/§5/§6).
>
> **Read first**: [SCOPE.md](./SCOPE.md) — locks in trading-only commitment + money-truth + cost-truth as the alpha-1 success contract. This playbook is scoped by SCOPE.md; if a request conflicts with that scope, defer it.
>
> **Companion docs to read alongside**: [E2E-EXECUTION-CONTRACT.md v3](./E2E-EXECUTION-CONTRACT.md) for current primitive call shapes, [observations/2026-04-29-post-refactor-wave-e2e.md](./observations/2026-04-29-post-refactor-wave-e2e.md) for ground-truth E2E findings.

---

## What this playbook is

The **single source of truth** for Alpha-1 alpha testing. Covers:

1. **The thesis** — why we're doing this, why now, why these two personas
2. **The governance model** — who fills which cognitive seat; shared-access discipline (applies identically to both accounts)
3. **The persona specs** — full setup content for two operator personas:
   - §3A — Jim-Simons-inspired systematic retail trader (Option B scope: 5–8 declared signals with measured edge)
   - §3B — Korea↔USA international commerce operator (KVK's voice; dual-directional physical/digital arbitrage)
4. **The setup sequence** — exactly how each account is created and onboarded
5. **The operating protocol** — day-to-day rhythm, coordination between KVK and Claude
6. **Claude's rules of engagement** — what I can do autonomously, what I escalate, what I never touch (with persona-specific discretion adjustments)
7. **The friction-capture loop** — how observations turn into ADR seeds
8. **Phase transitions** — scope expansion criteria (real trading, real commerce, external operator)
9. **Ledger of active artifacts** — what belongs in `docs/alpha/` and why

If an artifact about Alpha-1 doesn't trace back to a section in this playbook, either it isn't authoritative or this playbook needs updating to name it.

---

## 1. Thesis

### Why we're doing this

The architecture (FOUNDATIONS v6.0 + 20+ ADRs since 189) has earned the right to be used. Every ADR after 189 was load-bearing-but-speculative — the cockpit framing, the authored-team moat, the Reviewer layer's capital-EV reasoning all bet on operator behavior we haven't observed. The next ADR built without alpha signal is probably half-right and half-wasted. The next ADR built *after* a real operator exercises the substrate is grounded.

### Why two accounts (the conglomerate-alpha test)

ADR-191's conglomerate-alpha commitment was that YARNNN should be validated across structurally-different domains simultaneously — not sequenced, because sequencing hides which frictions are architecture-level vs. domain-specific. Alpha-1 runs **two accounts in parallel:**

- **`alpha-trader`** — Simons-inspired systematic retail trader (Option B: 5–8 declared signals with measured edge)
- **`alpha-commerce`** — Korea↔USA international commerce operator (KVK's actual voice, testing whether the two-city dual-life can be economically self-funding)

**Why these two specifically:**

- **Maximum structural separation, shared architecture.** Trading and international commerce have almost nothing in common at the domain layer — different platforms, different time horizons, different units of account (shares × prices vs. SKUs × margins × FX), different risk shapes (var-budget vs. inventory-tied-up + currency swing). But they share *every architecture layer* — cockpit surfaces, Reviewer layer, money-truth substrate, primitive matrix, Axiom-1 filesystem. If the architecture is genuinely domain-agnostic, both should work. If a friction only hits one, it's a domain issue, not an architecture issue. If a friction hits both, it's an architecture issue that needs an ADR.

- **Both are quantitatively reasonable.** Both are systematic operators with declared rules, measurable performance, and anti-discretion cultures. The trader declares signals and holds the discipline to honor them; the commerce operator declares sourcing/pricing/stocking rules and holds the discipline to honor them. The Reviewer's capital-EV framework (ADR-194 §5) speaks the same language to both — expected-value reasoning against a declared rule system with real money-truth to reconcile against.

- **KVK can operate both authentically.** The commerce persona is literally KVK's voice — a dual-life Seoul/LA operator running arbitrage to fund the two-city lifestyle. This isn't a fictional friend; it's a real operator hypothesis you'd want to test either way. The trader persona is KVK-as-systematic-trader — not your actual trading style today, but a structured experiment in *whether systematic discipline produces real edge at retail capital level* using a paper account so the research question doesn't cost real money.

**Why not sequenced (first trader, then commerce):**
Previous playbook draft (v2) sequenced trader first, commerce as Alpha-1.5. Reversed here because **sequencing defeats the anti-verticalization gate.** If we ship the trader alone and build up a pile of ADRs from its friction, we can't tell which ADRs are architecture-level until commerce lands three months later. Running both from the start means every observation immediately categorizes as "trader-only / commerce-only / both." That's the signal quality we actually need.

### Why a Simons-inspired systematic trader

Jim Simons — Renaissance Technologies, Medallion Fund — is the prototype of the **systematic quantitative operator**. The persona is:

- **Mathematician, not narrator.** Edge comes from measurable signals, not stories. Trades happen when signals fire, not when the operator feels strongly.
- **Empirically skeptical.** Discretionary overrides are treated as failure modes, not strengths. "We don't override the model" is the cultural spine.
- **Measures obsessively.** Every signal has performance history. Every trade attributes to a signal. Every drawdown gets post-mortemed. Unknown performance = signal doesn't exist yet.
- **Small edge × many trades = return.** Not holding-period plays; short-to-medium horizon systematic exposure. Many small wins, tightly-controlled losses.
- **Respects what it doesn't know.** Drawdown math isn't optional. Position sizing is mechanical.

This persona is the **hardest stress test** for three architectural commitments:

1. **AI Reviewer's capital-EV reasoning (ADR-194 §5).** A Simons-trader's Reviewer doesn't reason about character — it reasons about *signal alignment, expectancy, and drawdown contribution*. If the Reviewer can honor that frame (quote signal win rates, flag signal-incompatible trades, reason about position-level contribution to portfolio var), the architecture's claim of "capital-EV not rule-checking" is validated. If it can't, we learn that immediately.
2. **Money-truth substrate (`_money_truth.md` per ADR-195).** Simons-trader's `_money_truth.md` must carry *per-signal* attribution: which signals generated which trades, what each signal's expectancy looks like, how signals behave in different regimes. If the file schema + reconciler can honor this, money-truth is substrate-ready. If not, we learn the shape needs work.
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

### The accounts

| Account | Persona | Primary platform | Real/sandbox |
|---|---|---|---|
| `alpha-trader` | Simons-inspired systematic retail trader (Option B: 5–8 declared signals, measured edge) | Alpaca (paper throughout Alpha-1) | Paper throughout Alpha-1; live is Alpha-2 decision |
| `alpha-commerce` | Korea↔USA international commerce operator (KVK voice) | TBD based on product choice (§3B): Shopify for physical, Lemon Squeezy for digital, Stripe + own storefront for maximum flexibility | Sandbox/test-mode throughout Alpha-1; real transactions are Alpha-2 decision |

Both accounts = real Supabase user + workspace, normal signup flow, normal $3 signup grant. No special infrastructure.

Both accounts run concurrently under the same governance model (§3-seat structure below) — they are *structurally identical at the architecture layer*, differing only in domain-specific substrate (signals vs. sourcing-rules; universe vs. SKU-catalog; var-budget vs. inventory-budget).

### Three seats, per account (both accounts identical)

| Seat | Filled by | Scope | `judgment_log.md` tag |
|---|---|---|---|
| **Operator (primary)** | KVK | Strategy: signal/rule roster, capital allocation, phase transitions, principles + risk edits, persona-identity edits | `human:<user_id>` |
| **AI Reviewer** | AI Reviewer agent (ADR-194 Phase 3 — runs automatically via `review-proposal` reactive task) | Per-proposal: attribution check, capital-EV evaluation, rule/signal-rule compliance, risk-limit enforcement. Approve / reject / defer. | `ai:reviewer-sonnet-v1` (or version tag in use) |
| **Operator (secondary) + meta-observer** | Claude (authenticated operator session, same Supabase user or separate user if multi-user support lands — see §open questions) | Reviews AI Reviewer calibration. Approves reversibles within tight bounds per the anti-discretion ladder (§6). Escalates irreversibles + attribution-missing + ambiguous deferrals. Observes friction. Writes observation notes. | `human:<user_id>` (session auth limitation, see below) |

**Same seat-structure for both accounts, distinct substrate.** KVK primary-operates in both; Claude secondary-operates in both; AI Reviewer runs per workspace autonomously. No seat bleeds across workspaces — each account has its own three seats operating on its own substrate.

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

## 3. Persona specs

Two accounts, symmetric architecture, different domain substrate. §3A covers the trader (systematic quantitative); §3B covers the commerce operator (international arbitrage between Korea and LA, in KVK's voice).

---

## 3A. `alpha-trader` — Simons-inspired systematic retail trader

### 3A.1 Identity (`/workspace/IDENTITY.md`)

Seeded into the workspace during the first YARNNN conversation, pasted as rich input. Post-ADR-235, YARNNN routes identity inference through `InferContext(target="identity")` (per ADR-235 D1.a — the `UpdateContext` primitive was dissolved); the bundle's `authored` tier IDENTITY.md template arrives at fork time per ADR-226.

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

### 3A.2 Operator profile (`/workspace/context/trading/_operator_profile.md`)

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

### 3A.3 Risk parameters (`/workspace/context/trading/_risk.md`)

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

### 3A.4 Reviewer principles (`/workspace/review/principles.md`)

> **ADR-217 amendment (2026-04-24)**: The "Auto-approve policy" + "Always-
> escalate-to-human" blocks below are the playbook's *default* operator
> posture. Under ADR-217 these operational clauses moved to
> `/workspace/context/_shared/AUTONOMY.md` as workspace-scoped delegation
> (operator-authored, dispatcher-read). principles.md retains the six-check
> framework + tone + anti-override discipline. The scaffold in
> `api/scripts/alpha_ops/scaffold_trader.py` writes the split accordingly:
> framework → principles.md, delegation → AUTONOMY.md. The playbook block
> below is preserved for the historical default; live workspaces derive
> from the scaffold.

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
to judgment_log.md as the reviewer_reasoning field of a `--- decision ---` entry (ADR-281 §3 single-writer; proposal-arrival = decision entries, material outcomes = material-outcome entries).

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
  _money_truth.md (ADR-195 substrate)
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

### 3A.5 Recurrence set

Post-ADR-261/262, the bundle ships a single canonical recurrence declaration substrate at `/workspace/_recurrences.yaml`. Per-shape natural-home YAML files (`_spec.yaml`, `_action.yaml`, `_recurring.yaml`, `back-office.yaml`) and the `output_kind` enum dissolved per ADR-261 D2. Every recurrence is `{slug, schedule, mode, prompt}` — one shape, one execution path.

The bundle's `_recurrences.yaml` (at [docs/programs/alpha-trader/reference-workspace/_recurrences.yaml](../programs/alpha-trader/reference-workspace/_recurrences.yaml)) ships **14 recurrences** that fork into every alpha-trader-program workspace at activation. The 14 are not operator-composed via chat at onboarding — they're pre-declared by the bundle and inherited at fork time per ADR-226. YARNNN may help the operator tune cadence or pause individual recurrences via `Schedule(action="pause"|"update")`, but the set itself is the program's authored opinion.

**Modes** (ADR-261 D7): `judgment` = focused Sonnet sub-LLM call dispatched via the Reviewer's loop (uses `DispatchSpecialist` for production-role specialists per ADR-176); `mechanical` = deterministic Python executor at `@primitive: SyncPlatformState`, zero LLM cost (per ADR-264).

| Slug | Mode | Cadence | Purpose |
|---|---|---|---|
| `narrative-digest` | judgment | Daily 03:00 UTC | Aggregates execution narrative entries (per ADR-219 substrate-as-the-bus) into a compact "recent" rollup at `/workspace/memory/recent.md` for the working-memory compact index. |
| `proposal-cleanup` | judgment | Daily 04:00 UTC | Archives stale `action_proposals` rows + dead-letters anything past Reviewer-defer timeout. |
| `outcome-reconciliation` | judgment | Daily 05:00 UTC | Reads platform events (Alpaca trade fills, etc.), folds into `/workspace/context/trading/_money_truth.md` per ADR-195 v2. The money-truth refresh. |
| `morning-calibration` | judgment | Daily 06:00 UTC | Aggregates `judgment_log.md` decision + material-outcome entries into rolling 7d/30d/90d windows + cross-domain `_money_truth_summary.md`. Drives the cockpit Performance face. |
| `morning-reflection` | judgment | Daily 07:00 UTC | Reviewer reads its own decisions trajectory and writes pattern observations to `/workspace/review/handoffs.md` (per ADR-218 → ADR-256 unified Reviewer invocation, reflection trigger). |
| `pre-market-brief` | judgment | 15 8 * * 1-5 (8:15 UTC weekdays) | Composed deliverable from signal-evaluation output. Which signals may fire, portfolio exposure vs var budget, decay flags, regime state. Output at `/workspace/reports/pre-market-brief/{date}/output.md` per CONVENTIONS.md slug-templated path. Cockpit surfaces it; daily-update email is expository pointer per ADR-202. |
| `signal-evaluation` | judgment | 5 8 * * 1-5 (8:05 UTC weekdays) | For each declared signal in `_operator_profile.md`, evaluates current state across the universe. When fire conditions hit, calls `FireInvocation(slug="trade-proposal")` (per ADR-253 D4 — signal evaluator can fire the reactive trade-proposal recurrence directly). Writes signal-state under `/workspace/context/trading/signals/`. |
| `track-universe` | judgment | 0 8,11,15 * * 1-5 (3× weekdays UTC) | Reads `/workspace/context/trading/_universe.yaml` (operator-declared tickers per ADR-254 D4), pulls fresh price/indicator state, writes per-ticker `.yaml` under `/workspace/context/trading/` per ADR-254 D5. |
| `track-account` | mechanical | `*/5 * 9-16 * 1-5` (every 5min, market hours) | Deterministic Python mirror of Alpaca account state (cash, equity, buying power) into `/workspace/context/portfolio/account.yaml`. Zero LLM cost. |
| `track-orders` | mechanical | `* * 9-16 * 1-5` (every minute, market hours) | Deterministic mirror of open + recently-filled Alpaca orders into `/workspace/context/portfolio/orders.yaml`. |
| `track-positions` | mechanical | `* * 9-16 * 1-5` (every minute, market hours) | Deterministic mirror of current Alpaca positions + unrealized P&L into `/workspace/context/portfolio/positions.yaml`. |
| `trade-proposal` | judgment | reactive (no schedule) | Fires via `FireInvocation` when `signal-evaluation` detects a fire condition. Emits a ProposeAction with full signal attribution (see Reviewer Check 1). Runs through AI Reviewer reactive dispatch (ADR-194 v2 Phase 3 + ADR-256 unified invocation) → cockpit Tracking face Queue for human approval if Reviewer defers. |
| `weekly-performance-review` | judgment | `0 18 * * 0` (Sunday 18:00 UTC) | Reads `_money_truth.md`. Per-signal P&L, win rate, expectancy, Sharpe. Flags decay. Compares to declared baselines. Output at `/workspace/reports/weekly-performance-review/{date}/output.md`. |
| `quarterly-signal-audit` | judgment | `0 18 31 3,6,9,12 *` (quarter-end 18:00 UTC) | Comprehensive review: which signals to retire, which to retune, candidates for new signal slots. Operator drafts final decisions; the recurrence prepares the analysis. |

**Three composition groups** for the reader's mental model:

- **Operator-facing deliverables** (4): `pre-market-brief`, `weekly-performance-review`, `quarterly-signal-audit`, `narrative-digest`. Composed outputs the operator reads.
- **Reasoning engine** (3): `signal-evaluation` (fires proposals), `trade-proposal` (the proposal), `track-universe` (universe state the signals evaluate against).
- **System hygiene** (7): `outcome-reconciliation`, `morning-calibration`, `morning-reflection`, `proposal-cleanup` (judgment); `track-account`, `track-orders`, `track-positions` (mechanical, deterministic Alpaca mirrors per ADR-264).

The operator does not "scaffold" these recurrences — they ship with the bundle and fork at activation. Operator authoring lives in `_operator_profile.md` (universe + signal definitions), `_risk.md` (risk parameters), `principles.md` (Reviewer rules), and `AUTONOMY.md` (delegation ceiling). The recurrences are the program's standing engine; the authored substrate is what the engine reasons against.

Bundle template improvements to any of these 14 recurrences (or to the `specs/*.md` capability library) propagate to activated workspaces via the continuous re-apply mechanism (ADR-292) where the operator has not customized the file. Operator-customized files (HEAD `authored_by` ≠ `system:*`) are never touched. The mechanism runs daily as `back-office-substrate-reapply`; audit at `/workspace/_shared/substrate-reapply-log.md`.

### 3A.6 Money-truth substrate expectations (`_money_truth.md` shape)

**SHIPPED 2026-05-12 via ADR-267 (P&L unification).** Canonical money-truth file renamed `_money_truth.md` → `_money_truth.md`; `_money_truth_summary.md` → `_money_truth_summary.md`. The reconciler now populates per-signal attribution natively via Alpaca's `client_order_id` round-trip — ExecuteProposal stamps `proposal.id` on submit, reconciler reads it back to recover `signal_id` from `proposal.inputs`.

Actual frontmatter shape (JSON, per `api/services/outcomes/ledger.py::_init_money_truth`):

```json
{
  "domain": "trading",
  "last_reconciled_at": "<iso>",
  "processed_event_keys": ["alpaca_order_id:<id>", "..."],
  "totals": {
    "reconciled_event_count": <n>,
    "aggregate_value_cents": <n>,
    "currency": "USD"
  },
  "by_action_type": {
    "trading.submit_order": {"count": <n>, "value_cents": <n>, "wins": <n>, "losses": <n>}
  },
  "by_signal": {
    "momentum-breakout": {
      "count": <n>,
      "value_cents": <n>,
      "wins": <n>,
      "losses": <n>,
      "rolling_7d":  {"count": <n>, "value_cents": <n>, "wins": <n>, "losses": <n>},
      "rolling_30d": {"count": <n>, "value_cents": <n>, "wins": <n>, "losses": <n>},
      "rolling_90d": {"count": <n>, "value_cents": <n>, "wins": <n>, "losses": <n>}
    }
  },
  "rolling_7d":  {"count": <n>, "value_cents": <n>, "wins": <n>, "losses": <n>},
  "rolling_30d": {"count": <n>, "value_cents": <n>, "wins": <n>, "losses": <n>},
  "rolling_90d": {"count": <n>, "value_cents": <n>, "wins": <n>, "losses": <n>},
  "events": [<append-only per-event time-series>],
  "recent_wins": [<top-10 narrative entries>],
  "recent_losses": [<top-10 narrative entries>]
}
```

Body: markdown narrative regenerated on each reconciliation. Includes "## Rolling windows", "## By action type", "## Per-signal attribution" (new section per ADR-267), "## Recent wins", "## Recent losses".

**Differences from the original 3A.6 spec written pre-unification:**
- Lifetime Sharpe + expectancy_R fields are *not* in frontmatter directly. The Reviewer computes them at prompt time from the `events` array filtered by `signal_id` (per ADR-267 prompts in Commit 3). Less duplication; one canonical event log drives all derived metrics.
- "state" field per signal (active/flagged/retirement-recommended) is not in frontmatter. The Reviewer's morning-calibration recurrence writes calibration concerns to `judgment_log.md` (per ADR-281 §3 single-writer); quarterly-signal-audit surfaces retirement candidates in its output report. Substrate stays factual (counts + windows); judgment stays in agent narrative.
- `daily_var_7d`, `weekly_drawdown`, `vix_regime_days_active_30d` belong to a separate `_risk.md` reading layer; they're not duplicated in `_money_truth.md` frontmatter.

---

### 3A.7 Content quality audit — Reviewer apparatus (2026-05-12)

> **Status**: First applied instance of the operator-substrate quality framework in [persona-reflection.md §1.5](../architecture/persona-reflection.md#15-operator-substrate-quality-framework). Findings dated against the alpha-trader bundle as of commit `25c00df`. Surface here for operator visibility; track each finding's resolution in a follow-on commit.

The Cluster 2 audit (Reviewer apparatus — IDENTITY + principles.md + `_principles.yaml` + AUTONOMY.md + `_autonomy.yaml` read as one system) surfaced 8 concrete findings. Two are critical drifts between operator-facing prose and code-supported config; three are material inconsistencies the Reviewer must arbitrate per cycle; three are polish for next-iteration.

**🔴 Critical (operator-facing prose drifts from machine-parsed truth)**

| # | Finding | Where it lives | Action |
|---|---|---|---|
| **A1** | AUTONOMY.md `## Levels` enumerates 4 delegation values (`manual | assisted | bounded_autonomous | autonomous`). ADR-261 D5 collapsed to 3 (`manual | bounded | autonomous`). `_autonomy.yaml` ships `delegation: bounded` matching the new enum; operator-facing prose still cites the old enum. Operator who sets `delegation: bounded_autonomous` per AUTONOMY.md will have `load_autonomy()` silently fall back to `manual` (the autonomy-disabled state per [WORKSPACE.md §5 row 6](../architecture/WORKSPACE.md#5-cold-start-failure-modes)). | `docs/programs/alpha-trader/reference-workspace/context/_shared/AUTONOMY.md` | Rewrite §"Levels" to canonical 3-value enum; remove `assisted` and `bounded_autonomous` references throughout the file. |
| **A2** | `_principles.yaml` ships `auto_approve_below_cents: 20000`. principles.md §"Capital-EV thresholds" + Bootstrap clause describe this field as binding Reviewer approve verdicts. Per ADR-261 D5, `auto_approve_below_cents` was folded into `ceiling_cents` (in `_autonomy.yaml`); the principles-side field is dead config. Operator who tunes it observes zero behavioral effect. | `docs/programs/alpha-trader/reference-workspace/review/_principles.yaml` + `principles.md` | Delete `auto_approve_below_cents` from `_principles.yaml`. Rewrite principles.md §"Capital-EV thresholds" to reference `ceiling_cents` from `_autonomy.yaml` instead. |

**🟡 Material (structural weaknesses in the apparatus)**

| # | Finding | Where it lives | Action |
|---|---|---|---|
| **A3** | `_principles.yaml` has 2 trading thresholds (`high_impact_threshold_cents`, the dead `auto_approve_below_cents`). principles.md cites several more unquantified: 20-occurrence defer threshold, decay retire-flag, approve-incorrect-rate calibration trigger, false-negatives loosen trigger. Reviewer self-quantifies per cycle. Two runs may verdict differently on identical evidence. | `_principles.yaml` + `principles.md` | Add machine thresholds: `retire_flag_recent_20_trade_expectancy_below_R`, `defer_sample_size_floor`, `calibration_approve_incorrect_rate_threshold`. Surface them in principles.md. |
| **A4** | principles.md §"Capital-EV thresholds" says "defer when sample size < 20." §"Bootstrap clause" says "propose when sample < 20 if conditions unambiguous." Internal conflict that Reviewer arbitrates per cycle. | `principles.md` | Resolve explicitly: bootstrap supersedes defer when sample < 20 AND no hard rule fails AND no overlap with other open signal positions. Define "unambiguous" concretely. |
| **A6** | IDENTITY.md + principles.md both say exit-proposals are mandatory and frame the Reviewer as binding execution. `_autonomy.yaml` `never_auto: [close_position_market, cancel_other_orders]` overrides this — stops route to operator queue even in `autonomous` mode. Operator-facing prose doesn't acknowledge the override. | `principles.md` §"Hard exit triggers" | Add note: `never_auto` may route exit proposals to queue even in autonomous mode; intentional for paper-mode safety; tune `_autonomy.yaml::never_auto` to remove `close_position_market` once Phase 2 confidence achieved. |

**🟢 Polish (next-iteration improvements)**

| # | Finding | Action |
|---|---|---|
| **A5** | Persona's "principles tighten/loosen" calibration loop is overstated — Reviewer can't rewrite operator-authored principles.md. Reflection emits `narrow`/`relax`/`character_note` verdicts; operator must approve to mutate. | Restate honestly: "If approve-incorrect rate climbs, Reviewer's reflection emits a `narrow` verdict proposing tightening; operator reviews and applies." |
| **A7** | `_principles.yaml` thresholds are static; no parallel guidance for how they evolve alongside `_autonomy.yaml` Phase progression. | Add §"Threshold progression" to `_principles.yaml` frontmatter or AUTONOMY.md, parallel to ceiling-tuning guidance. |
| **A8** | No fixture-library regression test for Reviewer verdict quality. The apparatus's behavior is emergent from LLM reasoning; no scripted test for "given proposal X + substrate Y, verdict should be Z." | Schedule a follow-on: 10-15 proposal scenarios with declared expected-verdict annotations. Detect drift between releases of principles.md, Reviewer system prompt, model version. |

**Inter-cluster dependencies surfaced:**

- C2→C1 hard coupling: principles.md hard rule #2 makes Reviewer logic structurally dependent on `_operator_profile.md` quality. Weak signal declarations → false rejects or ambiguous attribution.
- C2→C4 latent: AUTONOMY.md `paused_until` write requires Reviewer to have WriteFile authority over `_autonomy.yaml`. Verify against `DEFAULT_REVIEWER_WRITE_LOCKS` and operator's `_locks.yaml` (per ADR-258).
- C2 self-coupling: Bootstrap vs Capital-EV (A4) is internal contradiction Reviewer arbitrates each cycle. A4 fix resolves.

**What the audit validated:**

- Mechanically the apparatus runs the loop end-to-end. The smoke test (commit `25c00df`) proved fork → connect → operational.
- C1 minimum holds — all 5 signals have concrete trigger / entry / stop / target / sizing fields.
- C3+C4 prompt-primitive coherence holds — every Reviewer-prompted action is in `REVIEWER_PRIMITIVES`.
- The persona character itself is well-conceived (Simons-style numbers-first, correlation-paranoid, vocabulary-blocked). The drift is in framework consistency, not in persona vision.

**Verdict:** the alpha-trader Reviewer apparatus is **structurally sound but carries content defects that degrade operator trust without preventing operation**. Fix A1 + A2 unlock honest delegation behavior. A3–A6 sharpen the apparatus to Simons-grade rigor. A7–A8 are next-iteration improvements.

---

## 3B. `alpha-commerce` — Korea↔USA international commerce operator (PARKED)

> **Per [SCOPE.md](./SCOPE.md), alpha-commerce is deferred for Alpha-1.** The 430-line persona spec that previously lived here (mandate, rule set, six-check Reviewer adaptation, money-truth shape) is preserved verbatim at [docs/alpha/parked/alpha-commerce-persona-spec.md](./parked/alpha-commerce-persona-spec.md).
>
> When alpha-commerce graduates from `deferred`, rewrite a fresh §3B here against current canon — do not unpark the historical content (it carries pre-ADR-261/262 substrate vocabulary).

---

## 4. Setup sequence

> **Operational machinery:** the day-to-day connect/verify/reset commands
> that both KVK and Claude run are documented in
> [OPERATOR-HARNESS.md](./OPERATOR-HARNESS.md). The persona registry
> (slug → email → user_id → workspace_id → expected invariants) lives in
> [personas.yaml](./personas.yaml). If you are repeating a setup ritual
> by hand, check the harness first.
>
> **Access model:** how a given Claude session actually operates on behalf
> of KVK — which of three access modes applies, what Claude can and cannot
> do in each, and how future connection paths (MCP, Playwright,
> impersonation chrome) will slot in — is documented in
> [CLAUDE-OPERATOR-ACCESS.md](./CLAUDE-OPERATOR-ACCESS.md). Read that
> once; it pins the operational contract between KVK and any Claude
> session without re-derivation each time.

### 4.0 Ownership split (what KVK does vs. what Claude does)

**This is an honest delineation of Phase 0 and Phase 1 work** — the playbook earlier implied Claude could handle "prerequisites + Phase 0-1 fully," which isn't accurate once we audit what each step requires.

**KVK-only** (requires your identity, your payment method, your decisions):
- Shared-credentials vault creation and population
- External platform account signup (Alpaca paper, Shopify/LS/Stripe)
- Email inbox provisioning (Gmail aliases simplest)
- YARNNN account signup (requires real email confirmation from your inbox)
- Payment / billing setup for commerce platforms
- Phase-transition decisions (paper→live, sandbox→real)

**Claude-can-handle autonomously** (given prerequisites):
- Render environment-variable updates (once you select the workspace via `mcp__render__select_workspace` — I can read and update env vars after)
- Drafting and persisting persona-file content to this playbook
- Writing observation notes + weekly reports
- Recommending ADR changes

**Claude-can-handle with-credentials** (after KVK completes signup):
- Logging into YARNNN web app as authenticated operator
- First-session onboarding inside YARNNN: pasting IDENTITY.md, confirming BRAND.md, approving task scaffolding, seeding `_operator_profile.md` / `principles.md` / `_risk.md` via rail
- Connecting platform OAuth (for platforms that allow session-based OAuth completion — may require KVK to complete the OAuth grant if 2FA or device-confirmation is enforced)

**Neither can skip** (hard external dependencies):
- Alpaca dashboard key generation (requires Alpaca signup flow)
- Shopify store creation (requires paid plan for Shopify or commercial decision about platform)
- Gmail account creation (if we need new inbox; aliases on existing Gmail work)
- Resend API key (for YARNNN outbound email — if not already configured in Render)

### Phase 0 — prerequisites (locked decisions + task split)

All three KVK-delegated decisions resolved during v4 iteration. Locked values:

- **Credentials home:** `api/.env.alpha-ops` (gitignored; canonical pattern per [OPERATOR-HARNESS.md §"Where secrets live"](./OPERATOR-HARNESS.md#where-secrets-live))
- **Render workspace:** `tea-cspsq5ogph6c73f4m8t0` (KVKtheCreator's Workspace — only one exists; auto-selected by the MCP tool when Claude queried)
- **Commerce platform:** Shopify (Option B per §3B.0) — dev store for Alpha-1, production upgrade at Alpha-2
- **Persona emails:** Gmail aliases (`you+alpha-trader@gmail.com`, `you+alpha-commerce@gmail.com`) off KVK's existing Gmail. Resend outbound already configured; inbound-parse deferred to post-alpha ADR if friction warrants (see "Email architecture note" below).

#### Pre-existing infrastructure (already on Render; Claude audited)

Already-configured env vars that support the alpha without additional setup:

| Env var | Purpose | Status |
|---|---|---|
| `ANTHROPIC_API_KEY` | LLM calls throughout YARNNN | Configured |
| `INTEGRATION_ENCRYPTION_KEY` | Fernet key encrypting `platform_connections` (per-user OAuth tokens + API keys) | Configured on API + Scheduler |
| `LEMONSQUEEZY_API_KEY` + variant/store/webhook secret | Platform billing (KVK's YARNNN account billing, not alpha commerce) | Configured |
| `RESEND_API_KEY` + `RESEND_WEBHOOK_SECRET` | Outbound email + delivery-event webhooks | Configured |
| Supabase + `SUPABASE_SERVICE_KEY` | Database + filesystem substrate | Configured |

**Alpaca and Shopify API keys are NOT env vars** — they live per-user in the `platform_connections` table (encrypted via `INTEGRATION_ENCRYPTION_KEY`), populated when the operator connects the integration via YARNNN's integrations UI. This is the same pattern Slack/Notion/GitHub OAuth uses.

No Render env var changes are required for Alpha-1. The infrastructure is alpha-ready.

#### Email architecture note (why Resend-inbound is deferred)

KVK requested agent-first email provisioning via Resend. Claude audited: Resend is an **outbound-sending service** + **delivery-event webhook receiver**, not an inbox provider. Resend *can* parse inbound email via webhook if we provision a receiving domain and a new API endpoint, but that's net-new infrastructure (new route, new substrate convention for `/workspace/uploads/inbox/`, new parser service) — an ADR candidate, not an alpha-provisioning shortcut.

**Alpha-1 uses Gmail aliases.** They land in KVK's existing Gmail with `+` filter, are human-readable, and cover the critical email workflows (signup verification, platform confirmations, login/reset, daily-update briefings). Zero new accounts required.

**Email-as-substrate** (Resend inbound-parse writing received email to `/workspace/uploads/inbox/{date}-{subject}.md` for YARNNN to reason over) is a genuine architectural direction. It becomes **ADR-204 candidate** if alpha friction shows operators actually need email-content to participate in substrate reasoning (beyond the expository-pointer emails YARNNN already sends outbound). Drafted only if observed, not pre-drafted.

#### Phase 0 task split

**KVK-owned (external signup + account provisioning):**
- [ ] Create `api/.env.alpha-ops` (gitignored). Populate the env vars
      named in [docs/alpha/personas.yaml](./personas.yaml) under each
      persona's `credentials_env` block, plus `SUPABASE_SERVICE_KEY` from
      [docs/database/ACCESS.md](../database/ACCESS.md). See
      [OPERATOR-HARNESS.md §"Where secrets live"](./OPERATOR-HARNESS.md#where-secrets-live)
      for the file shape.
- [ ] Create Gmail aliases (no separate Gmail accounts needed):
  - `{your-gmail}+alpha-trader@gmail.com`
  - `{your-gmail}+alpha-commerce@gmail.com`
  - Optional: add Gmail filters routing messages with these `+` tags into dedicated labels
- [ ] **Alpaca paper credentials.** *Already exists — reuse, do not re-signup.* An active Alpaca paper connection exists in YARNNN production under `kvkthecreator@gmail.com` (verified 2026-04-20 via `platform_connections` DB query; account ends AI0V, created 2026-04-16 during ADR-187 shipping). Options:
  - **(Recommended) Option 2 — Reuse the key in a fresh `alpha-trader` workspace.** Log into alpaca.markets → paper dashboard → API keys. Copy the existing key ID (starts `PK...`). If you have the secret saved (password manager / keychain / shell history), reuse it. If you've lost the secret, regenerate — but know this invalidates the key your main YARNNN account is using and you'll need to reconnect both. Paste both into `api/.env.alpha-ops` under the appropriate persona's `credentials_env` names; `connect.py` reads them from env when invoked during Phase 1.
  - **(Alternative) Option 1 — Use `kvkthecreator@gmail.com` YARNNN workspace as `alpha-trader`.** No second Alpaca step. Seed Simons-persona files into the existing workspace. Downside: mixed workspace (personal + persona artifacts).
  - Claude recommends Option 2 for persona-separation discipline even at the cost of one copy-paste step.
- [ ] Sign up for Shopify dev store (free) → partners.shopify.com → create development store → admin panel → apps → create custom app → generate Admin API token with scopes `read_products, write_products, read_inventory, write_inventory, read_orders, write_orders, read_customers, read_price_rules, write_price_rules` → store token in `api/.env.alpha-ops`
- [ ] Sign up for 2 YARNNN workspaces using the Gmail aliases:
  - Workspace 1: email = `{your-gmail}+alpha-trader@gmail.com`, workspace name `alpha-trader`
  - Workspace 2: email = `{your-gmail}+alpha-commerce@gmail.com`, workspace name `alpha-commerce`
  - KVK keeps web-login passwords wherever KVK prefers (password manager,
    notes); they're Mode-2 cockpit creds, not harness creds.

**Claude-owned (after KVK completes the above):**
- [ ] Verify Render env var inventory (done during v4 audit — nothing alpha-blocking)
- [ ] Send a test outbound email via Resend to both Gmail aliases to confirm deliverability (sanity check; can do from a small API script or the admin dashboard once alpha workspaces exist)
- [ ] Phase 1 onboarding (paste IDENTITY.md, confirm task scaffolding, connect platforms, seed persona files — §Phase-1 below)
- [ ] Phase 2 baseline observations

### 3B.0 Commerce-platform decision — **Option B (Shopify) committed**

KVK delegated the commerce-platform decision to Claude during v4 playbook iteration. **Decision: Option B — Shopify (physical products).**

#### Options considered

| Option | Product type | Platform | Pros | Cons |
|---|---|---|---|---|
| A. Digital products | Info products, guides, software, digital content | Lemon Squeezy (sandbox) | Matches existing ADR-183 integration; lowest friction; no shipping/customs | Doesn't test the *real* operator hypothesis (physical arbitrage is the actual thesis, not info products); low monetary upside |
| **B. Physical products (committed)** | Korean/US consumer goods with real shipping + customs + FX exposure | Shopify (starts on dev store — free; production upgrade when going to real transactions in Alpha-2) | Matches the persona hypothesis exactly; real unit economics; real FX exposure; real inventory discipline; high monetary upside | Requires Shopify signup; YARNNN lacks native Shopify integration (platform-bot gap → ADR-203 candidate surfaced in first weeks of Alpha-1); shipping logistics complexity is real |
| C. Hybrid | Info products now, physical later | LS first; add Shopify at Alpha-1.5 | Ships Alpha-1 without integration work | Defers the real hypothesis test; commerce persona stays partially artificial |

#### Why Option B (committed rationale)

KVK framed the tradeoff honestly: *"digital / LS seems more plausible from an implementation standpoint yet lower chance of monetary success; Shopify feels more difficult but with more upside monetary chance."*

The alpha is not about minimizing implementation friction — it's about testing whether the operator hypothesis (Korea↔USA physical arbitrage as dual-life funding mechanism) is real. Digital-info-products test a different, weaker hypothesis (can KVK productize dual-life expertise). If Alpha-1 doesn't test the real thing, it doesn't earn the right to inform Alpha-2 live-commitment or Alpha-3 external-operator onboarding.

**Secondary reasons:**
- The platform-integration gap (no native Shopify) is *exactly the kind of architecture-level finding alpha is supposed to surface*. Catching "Shopify bot needs ADR" in week 1-3 of alpha is an order of magnitude cheaper than catching it at external-operator launch.
- Shopify dev stores are free — no $29/mo gate to start. Production upgrade happens at Alpha-2 paper→real transition.
- The monetary-upside gap between B and A is substantial and real. A working physical arbitrage at retail scale has direct personal-life consequence (funding the dual-life); info products at retail scale rarely do.

#### Implications for §3B content

The §3B spec above (IDENTITY.md / `_operator_profile.md` / `_risk.md` / `principles.md` / task scaffolding / `_money_truth.md` schema) was written for physical products. All of it stands under Option B — no rewrites needed. Rules 1-6 apply directly; FX-on-inventory exposure is real; shipping/customs costs figure into landed-margin math.

#### Platform-integration gap (ADR-203 candidate)

YARNNN has native platform bots for Slack, Notion, GitHub, Commerce (Lemon Squeezy), Trading (Alpaca). **No Shopify bot exists yet.** For Alpha-1 this means:

- `track-catalog` task initially does **manual reconciliation** — operator (KVK or Claude) fetches current inventory/listing/price state from Shopify admin and writes to `/workspace/context/commerce/skus/` via YARNNN rail
- `rule-evaluation` still works — it reads whatever `/workspace/context/commerce/` has, regardless of how substrate got there
- `sourcing-proposal` / `reorder-proposal` etc. still emit — they just can't autonomously execute against Shopify; operator manually executes the approved action in Shopify admin, then updates YARNNN with the result

This is a **known gap**. Not a bug. It's the first real alpha friction — when operator + Claude hit "I approved a sourcing proposal but now I'm copy-pasting into Shopify admin manually," that's the observation that motivates **ADR-203: Shopify Platform Integration** (drafted organically from friction, not speculatively pre-drafted).

**Expected ADR-203 shape (not written yet — surfaces in alpha):**
- Platform integration pattern matching ADR-183 (Lemon Squeezy) + ADR-187 (Alpaca) — capability-gated per ADR-207 P4a, NOT a personified bot
- Shopify Admin API client in `api/integrations/core/shopify_client.py`
- `shopify_bot` agent role
- `commerce.*` write primitives extended with Shopify variants (`commerce.create_product_shopify`, etc.)
- OAuth connection flow for Shopify admin

**Expected timing:** ADR drafted in Week 2-3 of Alpha-1 after 15-30 manual operations surface the real pain points; shipped by Week 4 if the friction is persistent.

#### Alpha-2 upgrade path

When trader phase-transitions from paper to live (Alpha-2 trader), commerce likewise upgrades from Shopify dev-store to Shopify production (paid plan, real transactions, real FX exposure). The `_risk.md` budget scales from $10k operating-budget-on-paper to whatever KVK actually commits.

### Phase 1 — account creation (both accounts, KVK primary)

Run for both accounts in sequence (trader first is simpler because fewer Phase-0 dependencies; commerce follows once platform is confirmed).

**For each account:**

1. Sign up via normal YARNNN signup flow using the persona email alias. Note `user_id` from Supabase.
2. In the first YARNNN chat session, paste the IDENTITY.md content from §3A.1 (for trader) or §3B.1 (for commerce) as rich input. YARNNN processes via inference-driven scaffold (ADR-190).
3. Confirm / refine YARNNN-proposed `/workspace/BRAND.md`:
   - Trader: terse, quantitative, no hedging language
   - Commerce: bilingual-operator voice, practical, margin-focused
4. Approve YARNNN-proposed task scaffolding. Goal for each account:
   - Trader: converge on §3A.5 task set; `signal-evaluation` is non-negotiable
   - Commerce: converge on §3B.5 task set; `rule-evaluation` is non-negotiable
5. Connect the platform via integrations flow:
   - Trader: Alpaca paper API key
   - Commerce: LS sandbox / Shopify / Stripe (per §3B.0 choice)
6. Seed the identity-domain files via YARNNN rail. For each file, say something like: *"YARNNN, write this content exactly to `/workspace/context/<domain>/_operator_profile.md`:"* followed by the block-quoted content from the playbook.
   - `_operator_profile.md` (§3A.2 or §3B.2)
   - `_risk.md` (§3A.3 or §3B.3)
   - `principles.md` (§3A.4 or §3B.4)
   - Initial signal/rule state files at `/workspace/context/<domain>/signals/` or `/rules/` (can start empty — `signal-evaluation` or `rule-evaluation` populates on first run)
7. Store credentials in the shared vault.
8. Wait for first tracking + evaluation runs. First reconciler pass establishes `_money_truth.md` baseline (likely empty — accounts need trade/sale history to build performance).
9. Confirm first daily-update expository-pointer email arrives next morning.

### Phase 2 — Claude operator onboarding (both accounts)

Once Phase 1 is complete for an account and credentials are shared:

1. Claude logs in via authenticated web session (method resolved during this phase — likely a shared browser session or a KVK-initiated sign-in Claude picks up; §open questions).
2. Lands on `/overview`.
3. Opens YARNNN rail: *"I'm operating this account alongside KVK. Orient me: what does IDENTITY.md say about who this operator is? What signals/rules are declared? What's scaffolded? What's pending?"*
4. Reads identity-domain files via Context: IDENTITY.md + `_operator_profile.md` + `principles.md` + `_risk.md`
5. Reviews Team — scaffolded agent roster matches persona work
6. Reviews Work — evaluation tasks running, tracking cadence sensible, reactive proposal tasks wired
7. Visits `/workspace/context/{trading|commerce}/{signals|rules}/` and skims each state file. Baseline: "initialized, no history yet."
8. Writes baseline observation: `docs/alpha/observations/{YYYY-MM-DD}-{account}-first-session.md`. Capture: first impressions, anything surprising, whether per-signal / per-rule substrate populates or degrades gracefully, cockpit usability notes.
9. Confirms to KVK: "baseline set, beginning alpha operation."

### Phase 3 — first triggers, first decisions (both accounts)

- First ~2 weeks is warm-up. Signals/rules need to fire, trades/sales need to execute, `_money_truth.md` needs to accumulate history.
- Expect no strong Reviewer-calibration signal early (too few events per signal/rule).
- Focus observation on: does scaffolding work? Do proposals render correctly? Does the Reviewer's six-check framework actually execute? Does `_money_truth.md` populate attribution correctly?
- After ~20 events per account, preliminary calibration signal becomes available.
- After ~40 events, quarterly-audit tasks have enough substrate to run meaningfully.

### Phase 3 — first signals, first decisions

- First ~2 weeks are warm-up. Signals need to fire, trades need to execute (on paper), `_money_truth.md` needs to accumulate per-signal history. During this period:
  - Expect no strong Reviewer calibration signal — too few trades per signal
  - Focus observation on: does the scaffolding work? Do proposals render correctly? Does the Reviewer's structured reasoning (§3.4 checks) actually execute the checks? Does `_money_truth.md` populate by-signal attribution?
- After ~20 trades across signals, preliminary calibration signal becomes available.
- After ~40 trades, quarterly-signal-audit task has enough substrate to run meaningfully.

---

## 5. Operating protocol

### 5.1 Daily rhythm (trading days)

**Pre-market (7:30–9:15 ET):**
- 8:00: `track-universe` morning recurrence fires → writes `/workspace/context/trading/{ticker}/` per ADR-231 D2
- 8:05: `signal-evaluation` recurrence fires → state files updated under `/workspace/context/trading/signals/`
- 8:15: `pre-market-brief` fires → daily-update expository-pointer email arrives per ADR-202 → Claude clicks the deep-link to land at `/work` cockpit (`/overview` redirects to `/work` per ADR-225)
- 8:15–8:45: Claude reviews the cockpit four faces per ADR-228: **Mandate** (current MANDATE.md + AUTONOMY posture), **Money truth** (substrate fallback to `_money_truth.md` until live binding lands), **Performance** (judgment_log.md calibration — decision + material-outcome entries per ADR-281 §3), **Tracking** (proposal Queue + recurrence health). Reads pre-market brief at `/work?task=pre-market-brief` middle band. Notes any signal-state surprises.
- 8:45–9:15: If any trade-proposals pending from overnight or pre-market signal fires, Claude + KVK coordinate out-of-band on approval.

**Market hours (9:30–16:00 ET):**
- Signals can fire intraday (track-universe runs at 11:30 and 15:45). Each fire → `trade-proposal` reactive recurrence emits a ProposeAction → AI Reviewer reactive dispatch (ADR-194 v2 Phase 3) → cockpit Tracking face Queue.
- Claude checks the Tracking face Queue periodically (every 1–2 hours during market; not minute-by-minute — Simons-persona isn't a scalper).
- For each pending proposal:
  - Read the proposal card (action, signal attribution, Reviewer verdict + reasoning chain)
  - Apply the discretion ladder (§6)
  - Approve, escalate, or observe per the ladder

**Post-close (16:00–17:00 ET):**
- Claude reads day's `judgment_log.md` tail — AI Reviewer's verdicts + rationale (decision entries) + material outcomes when reconciler closes the loop. Were any rejections debatable? Any approvals that executed against declared signals correctly? Any concerning patterns?
- `outcome-reconciliation` runs as a chat-initiated or reactive-on-fill invocation — updates `_money_truth.md` with any day's fills. Per ADR-205 + Axiom 4, dispatch is operator-or-Claude chat-initiated, not cron-bound; the unified scheduler exists as periodic-trigger infrastructure but the load-bearing path is invocation-flow through the primitive matrix (ADR-194 v2 Phase 2b reactive Reviewer dispatch + ADR-204/207 ProposeAction → ExecuteProposal). Claude reads the update next morning.
- Observation note logged if anything friction-worthy surfaced.

### 5.2 Weekly rhythm

**Friday after close:**
- Optional mid-week pulse if week's observations are stacking.

**Sunday (performance-review day):**
- 18:00 ET: `weekly-performance-review` recurrence fires → output at `/workspace/reports/weekly-performance-review/{date}/output.md` (post-ADR-231 D2: deliverable-shape recurrences land at `/workspace/reports/{slug}/{date}/`, not `/tasks/{slug}/outputs/{date}/`).
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
- Talk to YARNNN in the rail — including asking it to explain Reviewer reasoning, walk through signal state, summarize `_money_truth.md` for a specific signal
- Trigger `track-universe`, `signal-evaluation`, `pre-market-brief` manually if scheduled runs miss (via `FireInvocation` per ADR-235 D1.c, or via the `/work` Run action which wraps the same primitive — useful when debugging a missed fire)
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

> **Discipline pointer:** Alpha-1 validates two objectives simultaneously —
> **A (system validation)** and **B (product / money-truth validation)**.
> Observations and weekly reports classify against both, using the
> **three-axis observation schema** + **dual weekly report templates**
> defined in [DUAL-OBJECTIVE-DISCIPLINE.md](./DUAL-OBJECTIVE-DISCIPLINE.md).
> That doc is authoritative for templates and anti-drift rules; §7.1 and
> §7.2 below now reference it rather than duplicating.

### 7.1 Observation note format

Canonical template + three-axis schema (Objective / Within-A scope /
FOUNDATIONS dimension) lives in
[DUAL-OBJECTIVE-DISCIPLINE.md §observation-note-template](./DUAL-OBJECTIVE-DISCIPLINE.md#observation-note-template).

Notes pin at `docs/alpha/observations/{YYYY-MM-DD}-{persona}-{slug}.md`.

Key rule (from DUAL-OBJECTIVE-DISCIPLINE.md R1): *"Observations without any axis tagged are not observations — they're private thoughts or todos. Route accordingly."*

### 7.2 Weekly rollup format

Single weekly rollup superseded by **two per-objective reports** —
`week-{N}-{persona}-A-system.md` and `week-{N}-{persona}-B-product.md`.
Templates in
[DUAL-OBJECTIVE-DISCIPLINE.md §dual-weekly-report-templates](./DUAL-OBJECTIVE-DISCIPLINE.md#dual-weekly-report-templates).

Both produced Sunday evening. Both read the same substrate
(`_money_truth.md`, `judgment_log.md`, observation notes, activity log);
they differ in framing (A = system-insight / ADR seeds / UX friction;
B = capital trajectory / per-signal attribution / honesty check /
hypothesis status).

Never combine A and B into one report. Never skip B when data is thin
— write the thin report honestly.

### 7.3 Decision tree — observation → ADR

- **Same friction 2+ weeks in a row** → ADR candidate
- **Single friction, prompt-fixable** → update YARNNN prompt + `api/prompts/CHANGELOG.md`, no ADR
- **Single friction, component-fixable** → patch, no ADR
- **Structural gap (missing primitive / missing dimension behavior / missing substrate field)** → ADR immediately, regardless of frequency
- **Simons-persona-only friction** → defer ADR judgment until Alpha-1.5 e-commerce corroborates (anti-verticalization gate per ADR-191 DOMAIN-STRESS-MATRIX). Might still warrant a prompt tweak or task-type refinement in the interim.
- **Reviewer-calibration friction** → feeds ADR-194 Phase 4 (calibration tuning), which explicitly waits for alpha data. Log in weekly Objective-B report Reviewer Calibration section.
- **Objective-B-only observation (money-truth impact, no architecture-level friction)** → log in weekly B report hypothesis-status section; feeds phase-transition readiness evaluation per §8; does not produce ADR work.

---

## 8. Phase transitions

Never skip phases. Each phase's clean-operation period is the license for the next.

| Phase | Current? | Scope | Trigger to advance |
|---|---|---|---|
| **Alpha-1** | ✅ now | Both accounts running (`alpha-trader` Alpaca-paper + `alpha-commerce` sandbox/test-mode per §3B.0 choice). KVK + Claude operating jointly. Observations + weekly reports produce ADR seeds. | — |
| **Alpha-1.5** (physical-commerce upgrade, if §3B.0 chose Option A/C) | no | Switch `alpha-commerce` from digital (LS sandbox) to physical (Shopify test → Shopify live). Adds physical unit-economic stress to commerce substrate. If §3B.0 chose Option B initially, this phase is a no-op. | 4+ weeks of Alpha-1 clean; per-direction commerce signals producing non-trivial attribution; KVK comfortable; platform-bot ADR drafted if Shopify needs new integration. |
| **Alpha-2** (real money, both accounts) | no | Trader: paper → live, $5k initial book. Commerce: sandbox/test → real transactions + real FX exposure. Phases can advance independently per account if one is clean and the other isn't. | 4+ weeks of Alpha-1 (or Alpha-1.5 if applicable) clean per-account; ≥100 AI Reviewer verdicts with outcome attribution; per-signal / per-rule performance within baseline; KVK comfort; explicit ADR amendment to this playbook per account. |
| **Alpha-3** (external operators) | no | Onboard first external friend(s) as operators. Could be trader, commerce, or both. Uses shared-operator governance model refined by Alpha-1/2 learnings. | 4+ weeks Alpha-2 clean per account; ICP signal present (operator wants to pay / refer others); external-operator-onboarding scope doc drafted. |

**Phase-independence per account:** an account's readiness for the next phase is evaluated per-account. If trader is Alpha-2-ready but commerce needs more observation, trader advances while commerce stays at Alpha-1. This is *explicitly allowed* and expected — domain-specific readiness is real.

### Why both accounts from Alpha-1 (not sequenced)

Previous playbook drafts sequenced trader first, commerce as Alpha-1.5 alone. Reversed in this version because:

- **Sequencing defeats the anti-verticalization gate.** Running only trader for months would pile up ADRs whose architecture-vs-domain classification we couldn't resolve until commerce finally lands. Parallel running means every observation categorizes cleanly as "trader-only / commerce-only / both."
- **The two personas exercise different dimensions of the same architecture.** Trader stresses Reviewer's per-trade expectancy logic + var-based risk; commerce stresses Reviewer's multi-dimensional (margin × turnover × FX) reasoning + inventory-and-turnover risk. Both exercise capital-EV reasoning, money-truth substrate, and cockpit surfaces — just against different substrate shapes.
- **KVK's operator-authenticity is real for both.** Trader is KVK-as-systematic-research; commerce is KVK-as-dual-life-entrepreneur. Neither is fictional; both are operator hypotheses KVK wants evidence on.

If one account turns out to be fundamentally broken (the architecture can't support it), that's a critical ADR finding — and we learn it in weeks, not months.

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

**Operational (KVK-decided, not architecture):**

1. **Credentials-vault mechanics** — vault location, rotation policy, backup. KVK's operational decision.
2. **Render workspace selection** — Claude needs the workspace ID via `mcp__render__select_workspace`. KVK provides after listing workspaces.
3. **Commerce-platform choice (§3B.0)** — A (digital / LS), B (physical / Shopify), or C (hybrid). KVK's call before Phase 0 commerce-step can proceed.
4. **KVK time budget** — hours/week committed to alpha observation. Shapes Claude's autonomy tolerance.
5. **Communication cadence** — daily / weekly / ad-hoc. Start ad-hoc; formalize if needed.
6. **Observation-doc review rhythm** — batch at weekly rollup (default), or time-sensitive escalation if friction warrants.
7. **ADR-amendment protocol from alpha** — same PR pattern; observation subfolder is the input.
8. **Claude's authenticated session access** — how does Claude Code (this session) actually log in to the web app? Likely via credentials passed through a browser session KVK initiates; refined during Phase 2 onboarding.

**Architectural (verify during Phase 3 first-triggers):**

9. **`_money_truth.md` per-signal / per-rule schema** — backend's current reconciler shape may or may not support `by_signal` (trader) or `by_sku`/`by_direction`/`by_rule` (commerce) attribution. Verify during first-triggers. If missing in either, log as structural-gap ADR candidate.
10. **Reviewer reasoning format** — does the AI Reviewer write its six-check chain to `judgment_log.md` decision entries in full, or produce a shorter summary? Verify against first few AI verdicts per account; may require prompt adjustment.
11. **Commerce platform integration gap (if §3B.0 = Option B Shopify)** — YARNNN lacks native Shopify integration. Either we use LS (digital) for Alpha-1 and draft a Shopify-platform-bot ADR for Alpha-1.5 physical upgrade, or we accept initial commerce substrate that's platform-naive (operator + Claude manually reconcile until a Shopify bot ships). Decision depends on §3B.0 outcome.
12. **Multi-workspace Claude authentication** — if Claude operates two accounts concurrently (trader + commerce), session management across two authenticated YARNNN sessions is an operational concern. Likely separate browser sessions or separate tabs; verify during Phase 2.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial playbook (Rohn-inspired, later corrected). |
| 2026-04-20 | v2 — Full rewrite. Persona corrected to Jim Simons (systematic quantitative) — Option B scope. Rohn persona superseded. |
| 2026-04-20 | v3 — **Two-account scope restored** (both accounts concurrent in Alpha-1). §3B added for `alpha-commerce` persona in KVK's voice: Korea↔USA international commerce operator testing dual-life economic hypothesis. §3B symmetric to §3A structure (IDENTITY.md + `_operator_profile.md` with 5 declared rules + 3 reserved + FX regime scalar / `_risk.md` statistical limits / `principles.md` six-check Reviewer framework / `_money_truth.md` schema with per-SKU + per-direction + per-rule attribution). §4 setup sequence rewritten with explicit KVK-vs-Claude ownership split — honest delineation of what Claude can handle autonomously (Render env vars once workspace selected, workspace onboarding with credentials) vs. what requires KVK (vault, platform signup, email provisioning, YARNNN signup). New §3B.0 platform-choice decision (digital LS / physical Shopify / hybrid) gates commerce setup. §8 phase transitions rewritten: both accounts in Alpha-1 from the start; Alpha-1.5 becomes "physical-commerce upgrade" (if chose Option A/C in §3B.0); Alpha-2 is per-account independent (trader-paper→live and/or commerce-sandbox→real can advance separately). §2 governance extended to name both accounts explicitly. §10 open questions expanded with Render workspace selection, §3B.0 choice, commerce platform integration gap, multi-workspace Claude auth. Previous "e-commerce is deferred" framing removed — sequenced-alpha defeats the anti-verticalization gate (ADR-191). v2 singular-trader framing fully superseded. |
| 2026-04-20 | v4 — **Decisions locked.** KVK delegated the three outstanding Phase-0 decisions to Claude. Claude resolved: commerce platform = **Option B Shopify** (physical products match the real operator hypothesis; monetary upside justifies higher implementation friction; platform-integration gap becomes ADR-203 candidate surfaced organically from alpha friction). Credentials vault = **1Password** (shared vault `YARNNN Alpha-1`). Persona email = **Gmail aliases** (Resend is outbound-only + delivery-webhook; inbound-parse deferred to ADR-204 candidate if alpha friction warrants). §4 Phase-0 checklist rewritten with locked values + KVK vs Claude task split. Env-var audit (executed via Render MCP) confirms pre-existing infrastructure supports alpha without new env var work (Alpaca + Shopify keys live per-user in `platform_connections`, not globally). §3B.0 updated with locked B commitment + ADR-203 (Shopify platform bot) expected emergence in Week 2-3 of alpha + Alpha-2 Shopify production upgrade path. |
