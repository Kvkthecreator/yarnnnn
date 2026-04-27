---
title: External Oracle Thesis — Discourse
date: 2026-04-26
status: v4 — alpha-commerce reclassification under OS framing
trigger: Apoorva Mehta / Abundance launch post (2026-04-25), discourse 2026-04-26
related:
  - docs/analysis/autonomous-business-thesis-2026-04-15/
  - docs/programs/README.md (OS / program separation, commit e094d98)
  - docs/programs/alpha-trader/README.md
  - docs/programs/alpha-prediction/README.md
  - docs/programs/alpha-defi/README.md
  - docs/adr/ADR-194-reviewer-layer.md (v2)
  - docs/adr/ADR-195-money-truth-substrate.md (v2)
  - docs/adr/ADR-187-trading-integration.md
  - docs/adr/ADR-209-authored-substrate.md
  - docs/adr/ADR-219-invocation-narrative-implementation.md
  - docs/adr/ADR-221-layered-context-strategy.md
  - docs/adr/ADR-181-source-agnostic-feedback-layer.md
  - docs/adr/ADR-141-unified-execution-architecture.md
  - FOUNDATIONS.md (Axiom 8 Money-Truth)
revision_notes: |
  v3 (2026-04-26): OS/program separation lands as `docs/programs/` (commit e094d98),
  resolving §9.1 (narrowing-as-rhetorical), §9.2 (repository narrowing), §9.6 (alpha-commerce
  treatment). The framing the operator landed on: YARNNN-the-OS stays domain-agnostic; one
  program (alpha-trader) is actively built; two reference SPECs (alpha-prediction, alpha-defi)
  constrain OS decisions without claiming code. The reference triangle spans the oracle-shape
  space (continuous price / binary terminal / on-chain settled), preventing the OS from
  accidentally fitting alpha-trader's shape. §9 rewritten to log the resolution; §9.3 / §9.4 /
  §9.5 carried forward as still-open. §10 updated to reflect the new committed state.

  v2 (2026-04-26, earlier same day): Third-eye review surfaced three productive corrections:
  (a) the doc was bundling axiom acknowledgment + architectural primitive + positioning narrowing
  into a single decision when they should be unbundled; (b) mandate-as-oracle-spec was understated —
  it's load-bearing, not an extension; (c) §6.1 was avoiding a position that the thesis's spine
  requires. Also integrates ADR-219 + ADR-221 (both shipped 2026-04-25/26) which materially
  reduce the substrate-replay storage cost. Sections updated: §4.1, §4.5 (new), §5 (rewritten),
  §6.1 (commits a position), §7 (split into A/B/C buckets), §9 (new — points for further discourse).
---

# External Oracle Thesis

## TL;DR

Apoorva Mehta's Abundance launch post crystallized a question that had been latent in YARNNN's foundations for months: **what makes the self-improvement flywheel actually flywheel?**

The answer this discourse converged on:

> **An external oracle — an objective, time-stamped, exogenous signal that grades the work independently of the operator's interpretation.**

Trading is the cleanest example because the oracle (market prices) reports continuously and unambiguously. But the *oracle property*, not "trading" specifically, is what unlocks the flywheel.

**v3 landed the resolution:** the right framing is not "narrow YARNNN to finance" or "delete the agnostic surface" — it's **OS / Program separation**. YARNNN-the-OS stays domain-agnostic; one program (alpha-trader) is actively built; two reference SPECs (alpha-prediction, alpha-defi) constrain OS decisions without claiming code. The reference triangle spans the oracle-shape space (continuous price / binary terminal / on-chain settled), preventing the OS from accidentally fitting alpha-trader's shape. Self-funding becomes structural: alpha-trader running on top of YARNNN, paying for YARNNN, validates both layers simultaneously.

Read §11 first for the current committed state. §1–§8 give the discourse arc. §9 is preserved as historical record with resolution notes inline.

---

## 1. The Discourse

Chronological reconstruction so a third reviewer can follow the reasoning, not just the conclusion.

### 1.1 Trigger

Apoorva Mehta's Abundance launch post (2026-04-25). Bloomberg/Yahoo: $100M seed, ~10-person Palo Alto team, 9 months self-capital, claims of beating benchmarks at high Sharpe and low directional exposure, AI agents replacing fundamental PMs.

The post articulates the underlying thesis cleanly:

> "Capital allocation drives the economy. […] Even the best investors are limited. They can only track so many opportunities, process so much information, and make so many high-quality decisions. […] AI changes the equation entirely. Agents can absorb more information, connect more dots, and evaluate more possibilities with a consistent standard than humans can on their own. **What was once left to individual judgement can become an optimizable system. A new hill to climb.**"

Four open problems Abundance names:
1. Token efficiency in self-improving agents
2. Robustness in long-running agents (20+ hours)
3. Identifying and sourcing alternative datasets
4. Handling extremely large amounts of data while staying within context limits

### 1.2 Conceptual symmetry — and where it breaks

Initial read: the framework Abundance articulates is **structurally similar to YARNNN's foundation**:

- ADR-195 v2 `_performance.md` ↔ Abundance's optimizable system thesis (money-truth as substrate)
- ADR-194 v2 Reviewer with capital-EV reasoning ↔ AI agents making consequential allocation decisions
- ADR-181 source-agnostic feedback ↔ "consistent standard" feedback loops
- ADR-159 + ADR-186 (compact index, profile-aware prompts) ↔ Abundance open problem #1
- ADR-173 + ADR-182 (accumulation-first, mechanical pre-gather) ↔ Abundance open problem #4

The Abundance post reads as autonomy-first (no Reviewer mentioned). YARNNN explicitly commits to operator-as-default-Reviewer (ADR-194 v2). For a fund with LP fiduciary cover, autonomy-first is correct. For a single operator with their own capital, operator-in-the-seat is correct. **Same axis, different position.**

### 1.3 The operator's question

> "Is this question solvable for us, in our own respects and build?"

The honest answer required acknowledging three structural advantages Abundance has that YARNNN, in the general case, doesn't:

1. **A single, unforgiving feedback signal.** P&L. Marks to market within hours-to-days.
2. **Bounded action space.** Buy, sell, size, hold. ~5–10 dimensions per decision.
3. **Stationary-ish ground truth.** "Did this trade make money over horizon H" is a stable question.

YARNNN tasks in the general case have **delayed, ambiguous, multi-attribution outcomes.** Did the deal close because of the brief, or despite it? Was the competitor we flagged actually the one that mattered?

### 1.4 The operator's strategic pivot

> "Alpha-trader was the go-to testing for our framework exactly because it provides unequivocal streamlined specifics into a loop framework that is or is not working. […] If we can get even 1/10th of their performance, even with one specific use case which is trading, we can bootstrap our YARNNN service model financially ourselves by actually creating the system that is similar to theirs."

Plus a concrete observation: read primitives for Alpaca / Alpha Vantage may be the real gap.

### 1.5 Code audit (2026-04-26)

**Wired as `platform_trading_*` tools:**
- Account, positions, orders, portfolio history (Alpaca account)
- Bars/OHLCV via `platform_trading_get_market_data`
- 30 days of daily prices, OR 1Hour/1Min intraday from Alpaca

**Defined in client but NOT exposed as a tool:**
- `get_fundamentals()` at `api/integrations/core/alpaca_client.py:718` — sector, industry, market cap, P/E, dividend yield, 52-week high/low, 50/200-day MAs (Alpha Vantage OVERVIEW). No corresponding entry in `platform_tools.TRADING_TOOLS`. **Agents can't call it.**

**Doesn't exist anywhere:**
- News (no Alpha Vantage NEWS_SENTIMENT, no Alpaca News API)
- Earnings, insider transactions, economic indicators
- Options chains, real-time quotes
- Cross-ticker correlation, sector breadth
- Anything resembling alternative datasets (Mehta's open problem #3)

**Verdict: read primitives are a real gap, but not the biggest gap.** Bigger gaps in order:
1. No backtest harness (Abundance demos several times a day; YARNNN has no replay mechanism)
2. No proposal-to-outcome attribution at strategy level (only position-level P&L via ADR-195)
3. Read primitives (the operator-identified gap)
4. No regime-awareness

### 1.6 The operator's reframe — the productive insight

This is where the conversation pivoted. The operator observed:

> "The backtest harness sounds to me a very similar practice of context accumulation with the filesystem native structure. […] aside from the 'back-dating' or 'reflective, past data to obtain intelligence' style of the backtest harness, the fundamentals are essentially the same (time is what is different)."

**The structural claim:** a backtest harness and context accumulation are the same operation viewed through different time axes:

> "Reconstruct the substrate as it existed at time T, run reasoning against it, observe what outcome would have / did follow."

In existing YARNNN vocabulary, the framework already has the ingredients:
- **ADR-209 Authored Substrate** — every `workspace_files` mutation is content-addressed and parent-chained. Reconstructing any file at any past revision is already a primitive. This is exactly what a backtest harness needs as its substrate primitive.
- **ADR-181 source-agnostic feedback** — `system_outcome` source already exists. Whether the outcome is "trade closed at +2%" or "user edited the brief 14 times," the routing shape is identical.
- **ADR-141 task pipeline** — already deterministic given inputs. Re-running it against past substrate is mechanically possible.
- **ADR-149 DELIVERABLE.md inference** — feedback distills into preference deltas. Same shape regardless of domain.

**Most of the harness is already latent in what's been built.**

### 1.7 Where the abstraction breaks

The substrate-replay layer generalizes cleanly. **The outcome ground truth doesn't.**

For trading: outcome ground truth is exogenous, machine-readable, timestamped, unambiguous. Two distinct sources (substrate = what the agent knew; oracle = what actually happened), both objective.

For non-trading: there is no exogenous oracle. "What happened" to a brief, a digest, a research summary lives **inside the same workspace whose substrate we're replaying.** Operator behavior (read, edit, ignore, cite) is the only signal — endogenous, noisy, delayed, multi-attributable.

**This is the asymmetry that doesn't dissolve.** Trading's free lunch is the external oracle. The framework can be agnostic about substrate-replay (and should be); it can't be agnostic about where outcome truth comes from.

Three tiers of generality:

- **Tier 1 (fully general):** substrate replay primitive, counterfactual re-execution, outcome ledger schema (`feedback.md` with `source: system_outcome`).
- **Tier 2 (domain-specific):** outcome connectors (Alpaca/market data, LS revenue events, content read/edit/forward telemetry). General concept; per-domain implementation.
- **Tier 3 (no generalization):** strategy primitives — position sizing, stop-loss logic, regime detection. These are trading. They don't generalize. Don't try.

### 1.8 The operator's final pivot

> "I am actually willing to intentionally and explicitly fix YARNNN for only those that have external oracles? OR, an explicit external oracle re-interpreted via mandate?"

The realization: this isn't "trading vs everything else." It's **"does this workspace's work move a needle that exists outside the workspace?"**

The operator's standing question, before committing:

> "Maybe trying to understand what kind of workspaces, domains, industries this encapsulates will help us create a stronger discourse and boundary."

That's what the rest of this doc addresses.

---

## 2. The External Oracle as Axis

### 2.1 The boundary

> A workspace has an external oracle when there exists an objective, time-stamped, exogenous signal that grades the work independently of the operator's interpretation.

Three required properties:

1. **Objective** — does not depend on operator interpretation. Two operators looking at the signal would read it the same way.
2. **Time-stamped** — binds to a specific moment, enabling temporal attribution: "this proposal was made at T1, the outcome resolved at T2."
3. **Exogenous** — originates outside the workspace. The operator cannot move it by reinterpreting their own work.

**Continuity** and **latency** are quality dimensions, not gating ones. Trading's oracle reports continuously (every market tick); revenue's reports daily/weekly/monthly. Both qualify; trading's is just stronger.

### 2.2 Why this is the right axis

**It's the property that makes the flywheel actually flywheel.** YARNNN's foundation thesis is: substrate accumulates → agents reason → proposals emerge → outcomes feed back → substrate improves. The external oracle is the only thing that closes the loop without operator vibes.

Without an oracle:
- "Outcomes" are operator interpretations of operator behavior
- `_performance.md` is operator-graded
- `principles.md` evolves from operator preference, not from being-right-or-wrong
- The "self-improving against a consistent standard" thesis collapses to "preference-tracking"

Preference-tracking is still useful (it's most of what current LLM products do). But it's not what differentiates YARNNN from any other AI product. The oracle is.

**It's the property that justifies architectural commitments already made.** Several ADRs only have full meaning when an oracle exists:

- **ADR-194 v2 Reviewer** — reasoning over `_performance.md` requires `_performance.md` to contain external truth. Without an oracle, the Reviewer is adjudicating operator-graded vibes.
- **ADR-195 v2 Money-Truth Substrate** — money-truth presupposes some signal is true in a way the operator can't move. Without an oracle, it's "operator's-current-belief.md."
- **ADR-181 Source-agnostic Feedback** — `system_outcome` presupposes a system that can detect outcomes. Without an oracle, only `user_feedback` and `tp_evaluation` exist, both operator-mediated.
- **FOUNDATIONS Axiom 8 Money-Truth** — explicitly elevates external financial truth as foundational. Structurally honest only for oracle-bearing workspaces.

The architecture has been pulling toward oracle-bearing all along. Naming it explicitly is the alignment move.

**It's the property that finishes the Reviewer's thinking.** The Reviewer's job is "independent judgment on proposed actions" (ADR-216). Without an oracle, the Reviewer reasons from operator-authored `principles.md`, which evolves from operator-authored feedback, which reflects operator preference. Closed loop, no external grounding. Reviewer becomes elaborate operator-self-supervision.

With an oracle: `_performance.md` carries external truth; outcome divergence from `principles.md` produces objective evidence; the Reviewer's judgments can be graded against actual outcomes; `principles.md` evolves from what worked, not what the operator preferred.

### 2.3 What oracles look like, structurally

| Property | Strong oracle | Weak oracle | Absent oracle |
|---|---|---|---|
| Source | Exogenous, machine-readable | Mixed | Operator-mediated |
| Latency | Hours to days | Months | Indefinite |
| Attribution | Single-cause, clean | Multi-cause, contested | Interpretive |
| Granularity | Per-action | Per-period | Per-vibe |
| Stationarity | Stable question | Drifting question | No stable question |
| Examples | Trading P&L, conversion rate | Hiring outcomes, B2B sales | "Was this strategy good?" |

Strong oracles → flywheel turns daily. Weak oracles → flywheel turns quarterly. Absent oracle → no flywheel; YARNNN reduces to "AI agents that help with knowledge work" — a commodity space.

### 2.4 Mandate-as-oracle-spec — load-bearing, not an extension

**[Promoted from "subtle extension" to load-bearing mechanism after third-eye review.]**

The original draft framed mandate-as-oracle-spec as a fringe extension — "operators without natural oracles can sometimes manufacture one." The third-eye review correctly flagged that this understates its role.

If naturally oracle-bearing operators are rare (a few thousand globally for any given domain), but mandate-induced oracles are common (any operator willing to commit to a measurable target), then the **product job changes shape**:

> The product job is not *filtering for* oracle-bearing operators. It is *coaching operators into instrumented commitments.*

That's a meaningfully different product, and a more defensible one. Filtering is gatekeeping; coaching is activation. Operators arrive without an oracle; YARNNN's job during onboarding is to help them name one and instrument it.

This makes **MANDATE.md hardening with a required `## Outcome Signal` section the activation moment of the platform** — the moment the operator goes from "I want AI to help me with my work" to "I am committing to be measured against this thing." Everything downstream (Reviewer engagement, principle-evolution, flywheel turning) depends on this commitment.

**The strict version of the mechanism:**

1. The target is measurable by an external system, not by the operator's judgment
2. The operator commits to instrumenting it (an `OutcomeProvider` connector or, for declared targets, a periodic measurement task that reads the external source)
3. The mandate names the target explicitly with a horizon ("CAC ≤ $X by month N")
4. The system surfaces the gap between current state and the target on every operator interaction

**The loose version is rejected.** "My mandate is to do thoughtful research" doesn't manufacture an oracle; it manufactures a vibe. YARNNN's onboarding flow should treat loose mandates as incomplete and prompt the operator toward measurability. This is friction, but it's productive friction — the operators who can't name a measurable target are exactly the operators for whom YARNNN's depth is wasted.

Examples of mandate-induced oracle activation:
- A SaaS founder declares "MRR ≥ $50K by Q3" → onboarding seeds a Stripe `OutcomeProvider` + a `revenue` context domain
- A DTC operator declares "first-time-buyer conversion ≥ 4.5% by month 6" → onboarding seeds a Shopify connector + a `conversion` domain
- A creator declares "12 essays at ≥5K reads each by year-end" → onboarding seeds a Substack/Beehiiv read-count connector + a `publication` domain
- A trader declares "beat SPY by 200 bps over the next 12 months at Sharpe ≥ 1" → onboarding seeds an Alpaca connector + a `portfolio` domain (alpha-trader's existing path)

In every case, **the activation step is the same**: name the measurable target, plug in the connector that reads it, commit to the measurement horizon. The rest of the platform's depth (Reviewer, principle-evolution, substrate accumulation) follows from this single act.

**Implication for the architecture:** ADR-207's MANDATE.md gate (currently: must be non-empty for `ManageTask(create)`) hardens further — must contain an `## Outcome Signal` section with at least one measurable target, target horizon, and named `OutcomeProvider` connector. This is a small ADR amendment with significant downstream effects.

---

## 3. Domain Classification

### 3.1 Strong oracle domains (flywheel turns daily-to-weekly)

The unifying feature isn't "money" specifically — it's that **the mandate produces an action whose success is measured by something the operator doesn't control and can't reinterpret.**

| Domain | Oracle | Latency | Operator profile |
|---|---|---|---|
| Trading / capital allocation | Market prices, P&L | Continuous | Solo trader, prop trader, RIA |
| E-commerce / DTC | Revenue, conversion, churn, refund rate, LTV, AOV | Hours-to-days | Shopify operator, brand owner |
| SaaS operations | MRR, activation, retention cohorts, expansion | Days-to-weeks | Indie SaaS founder, growth lead |
| Performance marketing | CAC, ROAS, attributed revenue, paid CPA | Hours-to-days | Paid acquisition lead, affiliate marketer |
| Affiliate / creator monetization | Clicks, commissions, conversions | Days | Newsletter operator, affiliate creator |
| Sports betting / prediction markets | Settled outcomes | Hours-to-days | Sharp bettor, prediction market trader |
| Inventory / supply chain | Stockout rate, turnover, fill rate | Days | DTC ops, 3PL operator |
| Lending / credit | Default rate, recovery, charge-offs | Months (but graded continuously) | Loan originator, credit fund |
| Insurance underwriting | Loss ratio, claim frequency | Months | MGA operator, niche underwriter |
| Sales operations | Closed-won, pipeline velocity | Weeks-to-months | Solo sales ops, RevOps lead |
| Algorithmic content monetization | Ad revenue, subscription conversion | Days | Substack/Beehiiv operator |
| Yield farming / DeFi | APY, impermanent loss, protocol returns | Continuous | DeFi treasury operator |

**The unifying *operator* type:** "someone whose week is partly graded by a number that someone else publishes."

### 3.2 Weak oracle domains (flywheel turns slowly, signal is noisy)

These domains *have* oracles but feedback latency and signal-to-noise ratio is poor.

| Domain | Oracle | Why it's weak |
|---|---|---|
| Hiring | Tenure, performance review, regrettable-attrition rate | 12+ month lag, multi-causal |
| Product management | Feature adoption, retention impact, revenue attribution | Slow, contested attribution |
| B2B sales (vs sales ops) | Closed-won | 3–12 month cycles, multi-touch |
| Content marketing (vs algorithmic monetization) | Pipeline-attributed revenue | Multi-touch, lagged |
| Recruiting | Hire conversion, candidate experience | Indirect, lagged |
| Brand marketing | Brand-tracked NPS, share-of-voice | Quarterly at best, noisy |

**Flywheel still turns**, but slowly enough that within a 6–12 month window, operator-vibe-grading dominates oracle signal. Substrate accumulation has standalone value here; self-improvement loop is real but slow.

### 3.3 Absent oracle domains (no flywheel)

| Domain | Why no oracle |
|---|---|
| General research, reading, learning | No external grader |
| Internal documentation, knowledge management | Internal-only consumers |
| Pure thought-partner / coaching use cases | Subjective by design |
| Strategy work without budget consequences | Decisions don't bind |
| Creative writing for its own sake | No external scoreboard |
| Personal productivity, GTD, journaling | Self-reported only |
| Most consulting deliverables | Deliverable IS the product, attribution interpretive |

These workspaces can still benefit from YARNNN as "AI helps me think and remember." They cannot benefit from the flywheel. The system can't get better at serving them in the structural sense.

### 3.4 The honest count

Strong: ~12 distinct operator categories. Weak: ~6. Absent: many — most "knowledge worker" use cases.

The strong-oracle population is **smaller than the absent-oracle population by orders of magnitude** in raw operator count, but each strong-oracle operator has:
- Higher willingness to pay (the platform pays for itself in measurable ROI)
- Cleaner success measurement (case studies write themselves)
- Stronger flywheel compounding (the platform actually gets better for them)
- Lower churn (switching = quality regression in money)

**This is the bet:** smaller market, deeper value, sharper positioning.

---

## 4. Architectural Implications

### 4.1 What changes (less than you might think)

The framework is already shaped right for oracle-bearing operators. Concrete changes:

1. **MANDATE.md hardens to require a `## Outcome Signal` section.** See §2.4 — this is the activation moment of the platform, not a passive declaration. Hardens ADR-207's existing mandate gate: must name a measurable target, horizon, and connector. Operator-graded mode is the *default*, not the fallback (see §4.5).

2. **Workspace classification at signup is replaced by mandate-driven activation.** No tier or mode declaration. The operator authors a mandate; the mandate either names an oracle (workspace activates oracle-graded mode automatically) or doesn't yet (workspace runs operator-graded; YARNNN coaches toward oracle declaration over time).

3. **`OutcomeProvider` interface formalization.** ADR-195 v2 already named this; Phase 5a Trading is shipped. Formalize the interface so future connectors (Stripe, Shopify, Substack, Plausible, GA4) plug in cleanly. Don't over-design — let the second connector force the abstraction.

4. **The substrate-replay primitive.** Tier 1 from §1.7 — the abstraction the operator's reframe surfaced. Built on top of ADR-209's revision graph + ADR-221's narrative rollup (see §4.5). Foundation for both the trading backtest harness and any future replay-based eval. Single architectural primitive, multiple consumers.

5. **`get_fundamentals` wired as a `platform_trading_*` tool.** Small unforced error from §1.5 — the method exists at `alpaca_client.py:718`, no tool surface exposes it. 30-minute fix, ships immediately.

### 4.2 What doesn't change

- ADR-141 task pipeline (already deterministic, replay-ready)
- ADR-181 source-agnostic feedback (already accommodates `system_outcome`)
- ADR-209 authored substrate (already provides the time-axis primitive)
- ADR-194 v2 Reviewer machinery (the *machinery* is correct; only the *applicability gate* changes — Reviewer is structurally meaningful in oracle-bearing mode, degraded in no-oracle mode)
- The 9-agent roster, the primitive matrix, the four output kinds — all unchanged

**The architecture has been pulling toward this all along.** The change is naming the boundary, not redesigning the system.

### 4.3 What this implies for ADR-194 v2 (Reviewer)

A future amendment could split Reviewer modes:

- **`oracle-graded`** — full Reviewer machinery, AI Reviewer eligible per principles.md thresholds, principle-evolution loop grounded in outcome divergence
- **`operator-graded`** — Reviewer reduced to operator-confirmed approvals; AI Reviewer disabled by default because there's no objective signal to ground its judgment

This isn't a tier difference in the pricing sense — it's a **mode of operation** the workspace declares via MANDATE.md.

### 4.4 What this implies for FOUNDATIONS

FOUNDATIONS v6.x Axiom 8 (Money-Truth) is the closest existing axiom. The third-eye review is right that this should ship regardless of positioning — it's free, it aligns with the architectural pull that's been there for months, and it doesn't bundle a positioning commitment.

Two refinements to commit as a FOUNDATIONS amendment:

1. **Generalize Axiom 8 to "External Oracle Truth"** — money-truth becomes one shape of external oracle (the most common shape for operator workspaces, but not the only shape). Conversion rates, retention curves, fill rates are oracles even when not strictly "money."
2. **New Derived Principle** — "The flywheel turns to the strength of the oracle." Workspaces with strong oracles compound quickly; workspaces with weak or absent oracles compound slowly or not at all. Operator-graded mode is honest; oracle-graded mode is the upgrade path (§4.5).

These ship as a FOUNDATIONS bump independent of any positioning decision.

### 4.5 Operator-graded mode is the default, not the fallback

**[New section in v2 — third-eye review correctly identified that §5 was framing this as a binary when §4.3 had the better answer.]**

Original draft framing: "narrow ICP to oracle-bearing operators OR stay broad and serve everyone." This is a false dichotomy that the architecture itself rejects. The honest framing:

- **Operator-graded mode is where every workspace starts.** The operator hasn't named an oracle yet. YARNNN provides substrate accumulation, agent reasoning, Reviewer-as-operator (no AI Reviewer), and feedback as operator-mediated. The flywheel is weak but the platform is useful.
- **Oracle-graded mode is the upgrade path** triggered by mandate hardening (§2.4). The operator names a measurable target, plugs in an `OutcomeProvider`, and the platform's full depth (AI Reviewer eligibility, principle-evolution from outcomes, substrate-replay for backtest, money-truth in the working memory) activates.

This isn't a tier in the pricing sense — it's a **mode of operation the workspace earns through commitment**. An operator can move from operator-graded to oracle-graded the moment they commit to a measurable target.

**Why this framing is better than the original §5 dichotomy:**

- Doesn't force a positioning commitment that's separable from the architecture
- Names operator-graded mode honestly (it's where operators start, not where they fail)
- Makes the upgrade path clear and operator-controlled
- Lets the platform serve the broad market while keeping its depth available for the operators who unlock it
- Resolves the §5.3 worry about "narrowing forecloses optionality" — narrowing is no longer the question

This is what §4.3 was already pointing at. The v2 doc commits to it as the default architectural stance.

### 4.6 Substrate-replay is closer to free than the original draft suggested

**[New section in v2 — third-eye review correctly noted that ADR-219 + ADR-221 materially changed the cost model.]**

The original §6.5 framed substrate-replay storage cost as an open question. After ADR-219 (invocation + narrative, shipped 2026-04-25/26) and ADR-221 (layered context strategy, shipped 2026-04-26), the cost model is much more answerable:

- **ADR-209's revision chain** provides per-file content-addressed history. Reconstructing any file at any past revision is already O(walk the parent chain).
- **ADR-221's filesystem-native rollup** (`recent.md`, `conversation.md`) gives us a narrative-side compaction primitive that doesn't require LLM summarization. Past invocations compact deterministically.
- **ADR-219's narrative substrate** logs every invocation as a chat-shaped entry with material/routine/housekeeping weight. The narrative-as-of-time-T is reconstructible by filtering on revision timestamps.

Combined, these give us **deterministic substrate-replay without new infrastructure**. The substrate-replay primitive becomes a query layer over existing tables, not a new storage system. Cost concerns shrink to indexing optimization, not storage architecture.

What's left for the substrate-replay primitive build:
- A read API ("render workspace state as of revision R" or "as of timestamp T")
- A counterfactual re-execution path that runs ADR-141's task pipeline against historical substrate without writing back to live state
- A diff layer that compares counterfactual outcome to actual outcome via the `OutcomeProvider`

None of these require new tables. ADR-219 and ADR-221 quietly solved most of the storage question.

---

## 5. The Positioning Bet — Unbundled

**[Section rewritten in v2. Third-eye review correctly flagged that the original §5 conflated three decisions — axiom acknowledgment, architectural primitive, positioning narrowing — and bundled approval invited approving-positioning-by-approving-architecture. The unbundling is the right move.]**

### 5.1 The three decisions that were originally bundled

The original draft treated the external oracle thesis as one decision. It's three:

| Decision | Cost | Reversibility | Should ship |
|---|---|---|---|
| **A. Axiom acknowledgment** — name external-oracle-truth in FOUNDATIONS, add the flywheel-strength derived principle | Low (doc edit) | Trivially reversible | **Yes, regardless of B or C** |
| **B. Architectural primitive** — substrate-replay built on ADR-209 + ADR-221, `OutcomeProvider` interface formalization, `get_fundamentals` wired, MANDATE.md `## Outcome Signal` hardening | Medium (1–2 weeks of work) | Reversible — primitive can be deprecated if unused | **Yes, regardless of C** |
| **C. Positioning narrowing** — lead marketing/onboarding/surface choices with "for operators graded by external scoreboards" | High (rebrand, surface redesign, sales messaging) | Hard to reverse — narrowing publicly then broadening reads as desperation | **Separate decision, not in this doc** |

Bundling them invites approving the positioning by approving the architecture. They should be approved separately.

### 5.2 Why A and B are independent of C

Decisions A and B improve the platform regardless of whether positioning narrows:

- The axiom is true whether YARNNN sells to oracle-bearing operators only or to everyone. Workspaces with stronger oracles will compound faster either way; the framework should name this honestly.
- The substrate-replay primitive serves alpha-trader (operator's own use, self-funding bet) and any future replay-based eval. It's not a positioning commitment.
- MANDATE.md hardening with `## Outcome Signal` is honest activation regardless of broader positioning. An operator-graded workspace simply states "no oracle yet" in the section; the section's existence prompts the question even when the answer is operator-graded.

A and B should ship in the next 2–4 weeks. They don't wait on C.

### 5.3 The narrowing decision (C) on its own merits

**The third-eye review's strongest pushback:** the narrowing is rhetorical, not surface-level. Cursor wins because the IDE is a vertical surface for engineers. Harvey wins because the legal-research surface is vertical for lawyers. Hebbia wins because the financial-analyst surface is vertical for that exact role.

YARNNN's surface (Chat / Work / Agents / Files) is a **horizontal cockpit**. Telling oracle-bearing operators "this is for you" while shipping a horizontal product reads as positioning without conviction.

The honest options:

**C-strict — earn the narrowing with surface choices.** Trading-native dashboards, P&L-first Overview surface, mandate flow that asks "what number do you want to move" first. The surface itself becomes vertical for operators. Highest cost, highest conviction, highest reversibility cost.

**C-light — narrowing as messaging only.** Marketing copy and ICP targeting shift to oracle-bearing operators; surface stays horizontal. Lower cost, lower conviction. Risk: the surface contradicts the messaging and operators sense it.

**C-defer — keep messaging neutral, let the architecture pull naturally.** A and B ship; the platform gets visibly better for oracle-bearing operators because the flywheel actually turns for them; that becomes the case study material that drives organic narrowing later. Lowest cost, lowest immediate conviction, optionality preserved.

**The third-eye review's lean:** C-defer with surface-level commitments earned over time, not C-strict committed up front. The v2 doc agrees. The narrowing decision should be made when there's evidence (alpha-trader working, first paying oracle-bearing operator, reproducible flywheel pattern) — not as a leap of faith.

### 5.4 The Abundance comparison — useful as motivation, not as validation

The original draft leaned on Abundance as structural validation ("they're making the same bet at fund scale"). The third-eye review correctly flagged that this is mathematically iffy — a $100M fund running one strategy with 10 quants is not architecturally analogous to a platform serving many operators each running their own oracle.

The honest read: **Abundance motivates the thesis (they're proof that AI-driven decision-making in oracle-bearing domains works), but doesn't validate YARNNN's specific structural bet.** Their depth in one domain at fund scale doesn't tell us whether platform-scale flywheel-per-operator works.

Use the comparison as motivation, not as validation. The validation has to come from YARNNN's own first oracle-bearing operator (alpha-trader, then alpha-commerce, then external).

### 5.5 Reference: the original narrow-vs-broad framing (preserved for context)

The v1 draft's narrow-vs-broad table is preserved below as historical record of the framing the v2 unbundling rejected. The point: this dichotomy was the wrong question. Decisions A and B are independent of any narrow-vs-broad commitment; decision C should be made when there's evidence, not now.

| Cascading implication | Narrow (oracle-bearing) | Broad (agnostic) |
|---|---|---|
| Marketing copy | "For operators who run a P&L" | "For knowledge workers" |
| Onboarding | Asks about oracle at signup | Asks about role/domain |
| First demo | Alpha-trader / DTC operator | Generic researcher / writer |
| Pricing logic | Tied to flywheel ROI (high WTP) | Tied to time saved (commodity WTP) |
| Self-funding case | Real (alpha-trader → revenue) | Speculative |
| Moat shape | Flywheel depth in oracle-bearing domains | Surface area across domains |
| Competitive frame | Vertical fund-of-agents | Horizontal AI productivity |

The pull from FOUNDATIONS Axiom 8, ADR-194 v2, ADR-195 v2, ADR-187, and the autonomous-business-thesis-2026-04-15 has been toward oracle-bearing depth all along. The v2 doc commits to that pull at the **architectural level** (decisions A and B). At the **positioning level** (decision C), the v2 doc defers — let the architecture pull naturally and earn the surface-level narrowing through evidence.

---

## 6. Open Questions for the Third Eye

Things this draft does not resolve and that benefit from external perspective.

### 6.1 Substrate vs. raw-model — the thesis commits a position

**[v2 update: third-eye review correctly identified that this was the thesis's central bet framed as an open question. The doc should commit. It does, here.]**

The question: if models keep getting better, does the flywheel matter less than the substrate?

**The thesis's position: substrate compound > raw model.** This is the accumulation moat thesis (since ADR-072) restated for the oracle-bearing era. The argument:

- Raw model capability is converging. Frontier models from any provider will be roughly equivalent within 12–18 months. Capability is becoming commodity.
- What does *not* converge is **the substrate the model reasons over**. Two operators using the same frontier model produce wildly different results based on what the substrate has accumulated about their work, their oracle, their preferences, their past outcomes.
- The flywheel — substrate accumulates, oracle grades, principles evolve — is the mechanism by which substrate compounds. An operator who has run the flywheel for 12 months has a substrate no model upgrade can replicate.
- Therefore: the moat is the operator's accumulated substrate, not the model running on top of it. Switching costs are quality regression in the operator's measured outcome — exactly the moat shape the autonomous-business-thesis-2026-04-15 named.

**Why this is the right bet:**
- It's the only durable positioning in a world where model capability commodifies
- It aligns with how every successful AI product moat has actually formed (Cursor's repo context, Harvey's case-history accumulation, Replit's project state)
- It's structurally true for oracle-bearing workspaces specifically, because outcome-graded substrate is harder to replicate than preference-graded substrate

**What the bet is hedged against:**
- Frontier models that have so much in-context capability that no accumulation matters — possible but not the current trajectory
- Operators who don't run the flywheel long enough for accumulation to matter — partially addressed by mandate-as-oracle-spec (§2.4) which front-loads the commitment

**What follows from committing this position:**
- Architectural priority should favor substrate quality over model orchestration sophistication. ADR-209 (authored substrate), ADR-181 (feedback layer), ADR-219/221 (narrative/rollup) are the right things to invest in. Multi-model routing, agent-graph coordination, and similar model-side complexity are deprioritized.
- The substrate-replay primitive (§4.6) is high-priority because it makes the substrate compound *legibly* — operators can see why the system gets better for them.
- Pricing should track substrate depth, not model usage. An operator with 12 months of accumulated oracle-graded substrate should pay differently than a 30-day operator, regardless of model spend.

The thesis commits this position. Future ADRs and architectural decisions should be evaluated against it.

### 6.2 Does narrowing too aggressively foreclose optionality?

The bet narrows ICP voluntarily. But:
- If the flywheel works for trading, does it generalize easily to commerce, then SaaS, then performance marketing? Or does each domain require Tier 2 and Tier 3 work that takes 6+ months apiece?
- Is there a version of the narrowing that's "lead with oracle-bearing, allow absent-oracle as degraded mode" rather than "oracle-bearing only"? §4.3 hints at this.
- What does the pricing model look like in the narrow vs. broad framing, and does that shape the answer?

### 6.3 Is alpha-trader actually a representative test of the framework?

The thesis treats alpha-trader as the proving ground. But:
- Trading's oracle is *unusually* clean — continuous, exogenous, low-latency. Does success at trading really validate the framework for slower-oracle domains (revenue, retention)?
- Conversely, does alpha-trader risk over-optimizing for the trading-shaped feedback loop, producing infrastructure that doesn't generalize?
- Is "1/10th of Abundance's performance" the right bar, or is it the wrong frame entirely (and what's the right frame)?

### 6.4 What's the principle-evolution loop?

ADR-194 v2 has `principles.md` operator-authored only. The thesis identifies that for the flywheel to fully turn, principles must evolve from outcomes — but that's currently unbuilt and not designed.

- Should YARNNN propose principle amendments to the operator (legibility-preserving)?
- Should it auto-update with audit trail (ADR-209-style attribution)?
- Should it gate updates on Reviewer judgment, operator approval, or both?
- Is this a small ADR amendment or a large architectural commitment?

### 6.5 The substrate-replay primitive

§4.1 names this as a Tier 1 build. But:
- What's the API surface? Read-only "render workspace at revision R," or full counterfactual re-execution against the task pipeline?
- What's the storage cost — does ADR-209's revision chain support arbitrarily-deep replay, or do we need TTL/compaction?
- What's the relationship to ADR-141's task pipeline determinism — is replay deterministic enough for trading backtests, or do non-determinism sources (model drift, tool latency) make it advisory only?

### 6.6 The mandate-as-oracle-spec move

§2.4 proposes that operators without natural oracles can manufacture them via measurable mandate targets. But:
- How strict should YARNNN be about target measurability? "Reduce CAC by 15%" is measurable; "ship a great product" isn't. Where's the line?
- Does the system enforce instrumentation, or trust the operator?
- Does this create a two-class user system (real-oracle operators vs declared-oracle operators) and does that matter?

---

## 7. Recommendation — Split into A / B / C buckets

**[v2: third-eye review correctly identified that bundled approval invites approving-positioning-by-approving-architecture. The recommendations are split below by reversibility cost and dependency.]**

### Bucket A — Ship now (axiom + small unforced errors)

These are free or near-free and don't bundle any positioning commitment. Ship in the next week.

1. **FOUNDATIONS amendment.** Generalize Axiom 8 from "Money-Truth" to "External Oracle Truth"; add a new Derived Principle: "The flywheel turns to the strength of the oracle." (See §4.4.)
2. **Wire `get_fundamentals` as a `platform_trading_*` tool.** Method exists at `alpaca_client.py:718`; no tool wraps it. 30-minute fix that immediately expands alpha-trader's reasoning surface.
3. **Commit the substrate-vs-raw-model position.** Update FOUNDATIONS or NARRATIVE.md to reflect that substrate compound > raw model is the central bet, not an open question. (See §6.1.)

### Bucket B — Build next (architectural primitives, no positioning commitment)

These earn the platform's depth regardless of positioning. 1–4 weeks of work depending on scope.

4. **MANDATE.md hardening with `## Outcome Signal` section.** ADR-207 amendment. Operator-graded mode is the default; oracle-graded mode is the upgrade path activated by naming a measurable target. (See §2.4 + §4.5.)
5. **`OutcomeProvider` interface formalization.** ADR-195 v2 already named it; Phase 5a Trading is shipped. Formalize the contract so the second connector (Stripe? Shopify?) plugs in cleanly. Don't over-design.
6. **Substrate-replay primitive.** Built on ADR-209 + ADR-221 (storage cost largely solved — see §4.6). Read API for "render workspace state at revision R / time T" + counterfactual re-execution path through ADR-141's task pipeline. Foundation for trading backtest *and* any future replay-based eval.
7. **Operator-graded mode hardening.** Make sure `_performance.md` honestly labels operator-graded vs oracle-graded, AI Reviewer is gated by mode, and onboarding doesn't pretend the flywheel works equally for both. (See §4.5.)

### Bucket C — Defer (positioning narrowing — needs evidence first)

The narrowing decision should not be made now. Defer until alpha-trader produces real evidence.

8. **Lead-with-narrowing positioning** (marketing copy, onboarding flow, surface choices). Defer per §5.3 — the third-eye review's lean toward C-defer is the right one. Surface-level narrowing earned through evidence (alpha-trader working, first paying oracle-bearing operator, reproducible flywheel pattern), not as a leap of faith.
9. **Vertical surface choices** (trading-native dashboards, P&L-first Overview). Defer until there's evidence the horizontal cockpit isn't enough for oracle-bearing operators.

### Sequencing dependencies

- A.1, A.2, A.3 are independent — ship in parallel
- B.4 depends on A.1 (axiom names the property the mandate gates on)
- B.5 enables B.6 (substrate-replay needs `OutcomeProvider` to grade counterfactuals)
- B.6 enables alpha-trader's first real backtest harness milestone — likely the trigger for the C.8 / C.9 evidence threshold
- B.7 should ship alongside B.4 (mode honesty matches mandate honesty)

### Schedule check

- Schedule a review of principle-evolution after alpha-trader Phase 1 produces real outcomes — likely 4–8 weeks out (covered in §6.4).
- Schedule a positioning-narrowing decision review when alpha-trader's first 30 days of paper-trading replay against substrate-replay yields a measurable result — that's the evidence point for Bucket C.

The split above is the recommendation the v2 doc commits. Bucket A and most of Bucket B should not wait on the operator's positioning decision; Bucket C explicitly waits on evidence.

---

## 8. What This Document Is Not

- Not an ADR. ADRs commit architectural decisions; this is exploratory framing that points at three near-term ADRs (FOUNDATIONS amendment, MANDATE.md hardening, substrate-replay primitive).
- Not a positioning document. Positioning is Bucket C and explicitly deferred.
- Not an implementation plan. Bucket A and B are scoped enough to point at, but full implementation specs come in their respective ADRs.
- Not the only valid reading. The Abundance post and the existing FOUNDATIONS could be read other ways; this is one coherent reading.

---

## 9. Points for Further Discourse — What v2 Did Not Resolve

> **v3 status note:** §9.1, §9.2, and §9.6 are now resolved by §11 (OS / Program Separation). They are kept in place below as historical record of how the discourse landed. §9.3, §9.4, §9.5 remain live and forward-looking. Read §11 first; treat §9.1 / §9.2 / §9.6 as superseded.

**[Original v2 framing preserved below.]**

**[New section in v2. The third-eye review accepted most of the framing but surfaced points that v2 either still under-treats or that benefit from more operator-side judgment. These are isolated here so the next round of discourse can target them directly.]**

The v2 doc agreed with the third-eye review on:
- Unbundling A / B / C (§5 rewrite)
- Promoting mandate-as-oracle-spec to load-bearing (§2.4 rewrite)
- Committing a position on §6.1 (substrate compound > raw model)
- Integrating ADR-219 + ADR-221 to lower substrate-replay cost (§4.5, §4.6)
- Treating operator-graded mode as default, not fallback (§4.5)
- Using Abundance as motivation, not validation (§5.4)

The points worth pushing further on, in order of how much operator judgment they need:

### 9.1 The narrowing-as-rhetorical critique deserves an explicit answer

> **Resolved in §11.2:** Dissolved by the OS / Program separation. The cockpit is the OS shell; programs are allowed to ship their own surfaces inside it without the shell pretending to be vertical. Original v2 framing follows.

The third-eye review's strongest pushback was that the narrowing is rhetorical, not surface-level — Cursor/Harvey/Hebbia win because the *product surface* is vertical, while YARNNN's surface is a horizontal cockpit. Telling oracle-bearing operators "this is for you" while shipping a horizontal product reads as positioning without conviction.

The v2 doc deferred this with C-defer (let evidence drive surface narrowing). But that defers a real question: **does YARNNN's horizontal cockpit actually serve oracle-bearing operators well enough to keep them, or does the narrowing eventually require vertical surface commitments?**

The honest answers diverge:
- If the cockpit + alpha-trader's TASK.md / `_performance.md` substrate is enough that operators stop noticing the horizontality, then C-defer is fine.
- If oracle-bearing operators expect P&L-first dashboards, vertical onboarding, and trading-native primitives, then C-strict (vertical surface choices) is forced and C-defer is just procrastinating the decision.

**This is an operator-judgment question.** A third reviewer or the operator themselves should sit with it before Bucket B fully ships. The substrate-replay primitive in B.6 is the inflection point — once it lands and alpha-trader has a real backtest, the question becomes: does the horizontal cockpit show backtest results well, or does it want to be a trading-native dashboard? The answer there is the answer to C.

**Proposed forcing function:** when B.6 lands, ship the trading backtest UI in the existing horizontal cockpit first. If the operator's own use of it feels constrained or wrong, that's evidence for C-strict. If it feels natural enough, evidence for C-defer was correct.

### 9.2 Operator's intentional repository narrowing — the bigger move

> **Resolved in §11.2:** Retired. Repository deletion was the wrong question; repository discipline (don't build new programs while alpha-trader is the only one) is the right answer. Original v2 framing follows.

The operator named in this round of discourse:

> "I'm seriously thinking of even narrowing down the repository, service philosophy, intentionally, at this stage to more finance specific. […] The realistic scenario is that I need to dogfood the investing capital myself."

This is a stronger move than the v2 doc captured. The v2 doc deferred *positioning* narrowing (Bucket C). The operator is asking about narrowing *the repository and service philosophy* — i.e., whether to delete the agnostic surface area and commit the codebase to finance-specific.

The arguments for this stronger move:
- **Single-operator dogfooding economics.** The operator can't afford to bootstrap targeting multiple ICPs. Trading is the one ICP where they're both the operator and the test user, with their own capital as the validation signal. Every other ICP requires acquiring external operators, which costs time + money the operator doesn't have.
- **Sequencing.** "If the primary use case (money-making truth) is validated, ironically, the agnostic approach can also come separately, sequentially after that as a whole collective service tightening is achieved." — this is the operator's framing, and it inverts the usual platform-first sequencing. Validate one oracle-bearing use case to revenue, then generalize.
- **Conviction discipline.** Narrowing the repository forces architectural choices that horizontal-cockpit framing avoids. It's the C-strict version of decision C, but applied at the codebase level rather than just the marketing level.

The arguments against:
- **Reversibility cost is high.** Deleting agnostic surface area is reversible-but-painful. Adding it back later is harder than starting agnostic.
- **The architectural pull may not need a repository commitment to manifest.** Bucket A and B already serve oracle-bearing operators preferentially; the absent-oracle population still gets value from the substrate accumulation primitives even without flywheel depth.
- **Risk of premature optimization.** Narrowing the repo before alpha-trader is validated is committing to a direction before the validation arrives. The bet inverts: now the validation has to land *because the repo is narrowed*, not despite it.

**This is the operator-side decision the v2 doc most needs the next round of discourse on.** It's a stronger commitment than the v2 doc made and a stronger commitment than the third-eye review pushed for. The arguments for are real; the arguments against are also real. The third-eye review or the operator's own judgment is needed here.

A useful frame for deciding: **what would have to be true for repository narrowing to be the right move in 2 weeks vs. 2 months vs. never?** If the answer is "alpha-trader has a working backtest harness and one paying alpha-commerce operator," that's a reasonable trigger. If the answer is "we just need to commit," that's possibly conviction wobble masquerading as strategic clarity.

### 9.3 Coaching-into-instrumented-commitments as the real product job

§2.4 promoted mandate-as-oracle-spec to load-bearing. But the third-eye review pointed at a deeper implication that v2 didn't fully unpack:

> "If oracle-bearing is rare in nature but mandate-induced oracles are common, the product job becomes coaching operators into instrumented commitments, not filtering them."

This reframes YARNNN's onboarding job from "find the right operator type" to "transform the operator's intent into a measurable commitment." That's a meaningfully different product job:

- Onboarding becomes a **conversation about what the operator actually wants to be measured against**, not a form-filling exercise about role/domain.
- The mandate flow becomes the **first interaction that demonstrates YARNNN's value** — the operator leaves onboarding with something they didn't have before (a clear measurable target + the connector that reads it).
- The Reviewer's role as "the seat that grades the work against the oracle" becomes immediately meaningful from day one, not an emergent property after months of substrate accumulation.

This is closer to what successful B2B onboarding looks like (Stripe's checkout setup, Linear's first-issue flow) — the onboarding *is* the product demo, not a precursor to it.

The v2 doc nodded at this but didn't commit it as a product principle. **Whether YARNNN's onboarding flow should be redesigned around mandate-coaching is a near-term product decision the next round of discourse should resolve.**

### 9.4 The principle-evolution loop is still under-specified

§6.4 left this open. It's worth a more concrete pass before alpha-trader Phase 1 produces real outcomes:

- **Trigger.** What event causes YARNNN to propose a principle amendment? Outcome divergence beyond N% over rolling window? Reviewer rejection rate exceeding threshold? Operator-flagged surprise?
- **Audit shape.** ADR-209 attribution (`authored_by: yarnnn:reviewer`) handles the substrate audit, but the *reasoning* for the proposed amendment lives where? `decisions.md`? A new `principles_log.md`?
- **Approval gate.** Operator-only? AI Reviewer with operator final-say? Principles.md self-modifying inside thresholds (dangerous)?
- **Frequency cap.** How often can principles.md change before instability outweighs improvement?

This is small-ADR territory, not a discourse question — but it should land before alpha-trader graduates to Phase 1, otherwise the loop is incomplete at the moment outcomes start arriving.

### 9.5 The "1/10th of Abundance" framing should be retired

The operator used it shorthand-style early in the discourse. The v2 doc kept it implicit. The third-eye review correctly pointed out the comparison is mathematically iffy.

A cleaner framing: **a positive-expectancy paper-trading system that survives a real drawdown and the operator would run with their own capital, scaled to whatever capital they choose to deploy.** That's a falsifiable target that doesn't require Abundance as a benchmark.

Specific bar candidates:
- Beat SPY by 100–300 bps over 12-month rolling window
- Sharpe ≥ 1.0 over the same window
- Max drawdown < 15%
- Survive at least one drawdown event without principle-corruption

The next round of discourse should commit a specific bar so "alpha-trader is working" has a definition.

### 9.6 The repository narrowing's effect on existing alpha-commerce work

> **Resolved in §11.2:** Clarified. Commerce work (ADR-183/184, Commerce Bot, LS integration) is OS-layer capability — it stays. alpha-commerce graduates to a built program when alpha-trader passes its success bar and a real commerce operator activates the workspace shape. Original v2 framing follows.

The operator's stronger framing (§9.2) implies de-prioritizing alpha-commerce work. But ADR-183/184 (commerce + product-health-metrics) shipped, the Commerce Bot exists in `AGENT_TEMPLATES`, and the architecture has invested in commerce as a parallel oracle-bearing track.

If the repository narrows to finance-specific, what happens to:
- Commerce Bot, `commerce-digest`, `revenue-report` task types?
- The directory registry's `customers/` and `revenue/` domains?
- The Lemon Squeezy integration and its API client?

Three options:
- **Delete cleanly.** Single-implementation discipline. Commerce work resurfaces if/when the agnostic generalization comes.
- **Quarantine.** Move commerce-specific code to a separate module marked deferred; let it bit-rot rather than actively delete.
- **Keep as second oracle-bearing proof.** Treat alpha-trader and alpha-commerce as parallel proofs of the framework rather than alpha-trader as the sole proof.

The third option is what the v2 doc's "operator-graded as default, oracle-graded as upgrade" framing implies. The first option is what repository narrowing implies. **These are not the same direction; the operator's judgment is needed on which.**

---

## 10. Closing (v2 record)

> **v3 note:** This closing reflects the v2 commitment state. The v3 resolution in §11 supersedes §9.1, §9.2, §9.6 and adds the OS / Program separation as the operating frame. Read §11 for the current committed state.

The v2 doc commits to:
- The axiom amendment (Bucket A.1)
- The substrate-vs-model bet (Bucket A.3)
- The architectural primitives (Bucket B)
- Operator-graded mode as default
- Mandate-as-oracle-spec as load-bearing
- Deferral of positioning narrowing pending evidence (Bucket C)

The v2 doc does *not* commit to:
- Repository narrowing (§9.2 — **resolved in §11**: not narrowing; OS / program separation instead)
- Vertical surface choices vs. horizontal cockpit (§9.1 — **resolved in §11**: programs ship their own surfaces inside the OS cockpit)
- Onboarding redesign around mandate-coaching (§9.3 — still open, near-term product decision)
- A specific alpha-trader success bar (§9.5 — partially captured in alpha-trader/README.md; numeric bar still pending operator commitment)

Live in v3 for the next round of discourse: §9.3 (onboarding), §9.4 (principle-evolution loop), §9.5 (numeric success bar).

The intent of the doc remains: give a third reviewer enough material to push back productively on the strongest version of this framing.

---

## 11. Resolution: OS / Program Separation (added 2026-04-26)

After the third-eye round, the discourse converged on a sharper framing than "narrow vs. broad" or "delete the non-finance code." Resolves §9.1, §9.2, §9.6.

### 11.1 The frame

> **YARNNN-the-OS** is the substrate (authored substrate, primitive matrix, task pipeline, Reviewer machinery, narrative + layered context, money-truth substrate, source-agnostic feedback, prompt profiles, FOUNDATIONS axioms, the four-tab cockpit, the universal agent roster). Domain-agnostic by construction.
>
> **A program** is a serious application built on top — opinionated about its own surfaces, scaffolding, success bar, and iteration cycle. Programs are allowed to be vertical in ways the OS cannot be. macOS doesn't become "Photoshop OS" when Adobe ships Photoshop.

### 11.2 What this dissolves

- **§9.2 (repository narrowing):** retired. Repository deletion was the wrong question; repository discipline (don't build new programs while alpha-trader is the only one) is the right answer. The 5–8% of platform-integration code is OS-layer capability that any future program can re-host. Keep, freeze, ignore.
- **§9.1 (vertical surface vs. horizontal cockpit):** dissolved. The cockpit is the OS shell; programs are allowed to ship their own surfaces inside it (a P&L-first Overview pane, backtest UI, portfolio dashboard) without the shell pretending to be vertical.
- **§9.6 (alpha-commerce treatment):** clarified. Commerce work (ADR-183/184, Commerce Bot, LS integration) is OS-layer capability — it stays. There is no "second program" being actively built; alpha-commerce graduates to a built program when alpha-trader passes its success bar and a real commerce operator activates the workspace shape. Until then it is a future program-shape, not deleted code.

### 11.3 What this commits

- **alpha-trader is the only program being actively built for the next 90 days.** New surfaces, new scaffolding, new task types, new context domains — all alpha-trader.
- **Three reference programs** form the OS-design litmus triangle: alpha-trader (primary, built), alpha-prediction (reference, SPEC only), alpha-defi (reference, SPEC only). Each stresses different oracle-shape dimensions (continuous price / binary terminal outcome / on-chain settled state). Together they prevent the OS from accidentally fitting alpha-trader's shape.
- **OS-layer ADRs are reviewed against all three references.** A primitive that only serves one is program-layer, not OS-layer. The reference SPECs are the litmus.
- **Bucket A + B work** (axiom amendment, MANDATE.md `## Outcome Signal` hardening, substrate-replay primitive, OutcomeProvider formalization, `get_fundamentals` wire) ships as OS-layer because it serves the triangle, with alpha-trader as first beneficiary.

### 11.4 New artifacts

- [docs/programs/README.md](../programs/README.md) — OS / program separation framing + program registry
- [docs/programs/alpha-trader/README.md](../programs/alpha-trader/README.md) — primary program spec (surfaces, scaffolding, OS dependencies, success bar candidates from §9.5, phase milestones)
- [docs/programs/alpha-prediction/README.md](../programs/alpha-prediction/README.md) — reference SPEC, design test only, zero code
- [docs/programs/alpha-defi/README.md](../programs/alpha-defi/README.md) — reference SPEC, design test only, zero code (the heaviest litmus)

### 11.5 What's still live for the next round

Resolutions land cleanly for §9.1, §9.2, §9.6. Still open and waiting for evidence:

- **§9.3 (onboarding redesign around mandate-coaching)** — near-term product decision. Defer until alpha-trader Phase 1 produces real MANDATE-authoring data.
- **§9.5 (alpha-trader success bar)** — partially captured in [docs/programs/alpha-trader/README.md](../programs/alpha-trader/README.md) §"Success bar" (process obedience over 90 days; phase transition to live; Sharpe > 1.0; self-funding milestone). Operator commitment to specific numbers still pending.
- **§6.4 (principle-evolution loop)** — schedule a check after alpha-trader Phase 1 produces real outcome data.
- **§6.1 (substrate vs. raw model)** — committed in §6.1 update, not changed by this resolution; still the central bet.

### 11.6 What this means going forward

- The OS doesn't change because alpha-trader is the only program. The OS keeps its general-purpose contract.
- The program is allowed to be opinionated — P&L-first surfaces, capital-EV Reviewer principles, backtest UI, signal attribution review — without the OS pretending to be vertical.
- Investment decisions clarify: OS-level work serves the triangle; program-level work makes alpha-trader closer to working.
- Self-funding becomes structural: alpha-trader running on top of YARNNN, paying for YARNNN, validates both layers simultaneously. OS validation is implicit in program validation.

This resolution is not a positioning document. It is the architectural framing under which positioning decisions can be made cleanly when evidence supports them.

---

## 12. Amendment: alpha-commerce Reclassification (added 2026-04-27)

§11.2's resolution of §9.6 said:

> "alpha-commerce treatment: Commerce work (ADR-183/184, Commerce Bot, LS integration) is OS-layer capability — it stays."

That framing is **superseded** by ADR-222 (OS framing canonization) + ADR-224 v3 (kernel/program boundary refactor). Under the OS framing, program-shape declarations don't sit in the kernel as "OS-layer capability" — they live in their program bundle.

**Corrected classification.** alpha-commerce becomes a fourth program bundle with `MANIFEST.yaml` `status: deferred`. The bundle is created by ADR-224 v3 implementation as a home for shipped-but-homeless commerce artifacts (revenue-report task type, customers/ + revenue/ context-domain conventions, COMMERCE_TOOLS, commerce_bot template residue). Bundle is near-empty per ADR-223 §5; populates further when commerce activates.

**Why this matters.**

- **Honest kernel boundary.** The kernel had been carrying program-specific declarations as "OS-layer capability" — exactly the conflation Derived Principle 16 is meant to prevent. Moving them to a deferred bundle restores the boundary.
- **alpha-commerce is intentionally NOT part of the litmus triangle.** Its oracle shape (revenue / conversion / churn) is too close to alpha-trader's continuous-price shape to add discriminating power for the kernel-vs-program test. The litmus triangle remains alpha-trader (primary built) + alpha-prediction (reference SPEC) + alpha-defi (reference SPEC). alpha-commerce is parking-lot, not litmus.
- **Lifecycle states formalized.** Per ADR-223, four states: `active` | `reference` | `deferred` | `archived`. alpha-commerce is the first instance of `deferred` — distinct from `reference` because it has homeless artifacts to host, not a litmus-test purpose to fulfill.
- **No change to the discipline commitment.** alpha-trader remains the only program being actively built. alpha-commerce activates only when a real commerce operator shows up and the activation_preconditions in its MANIFEST hold.

**Updated artifact registry** (added to §11.4 retroactively):

- [docs/programs/alpha-commerce/](../programs/alpha-commerce/) — deferred future program; MANIFEST + minimal SURFACES + reference-workspace placeholder; created by ADR-224 v3 implementation.
- [docs/programs/README.md](../programs/README.md) — gains lifecycle-states section + alpha-commerce row + clarification that alpha-commerce sits outside the litmus triangle by design.

This amendment closes a small but real inconsistency between the thesis's §11 resolution and the OS framing the resolution itself committed to. The substrate of the architecture and the substrate of the documentation now agree.
