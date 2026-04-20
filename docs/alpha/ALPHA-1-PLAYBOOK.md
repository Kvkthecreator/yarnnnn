# Alpha-1 Playbook — Shared Operator Account + Omniscient Claude Presence

> **Status**: Canonical — first alpha cycle commitment
> **Date**: 2026-04-20
> **Authors**: KVK, Claude
> **Grounded in**: ADR-191 (polymath ICP + conglomerate alpha), ADR-194 v2 (Reviewer seat interchangeability), ADR-198 v2 (cockpit service model), FOUNDATIONS v6.0 (Axiom 2 Identity, Axiom 6 Channel, Derived Principle 12)
> **Rule**: This doc governs Alpha-1. Updated as we iterate. Archived when alpha concludes and learnings absorbed into subsequent ADRs.

---

## Purpose

End the doc-first phase. Start using YARNNN as the operator platform it was designed to be.

**One production operator account. Shared access. Both KVK and Claude operate it. Persona: a Jim-Rohn-inspired long-horizon trader.** This is not a sandbox — real platform API (Alpaca paper), real money-truth reconciliation, real cockpit use. The architecture gets tested by actual operation, not by architecture review.

**Scope discipline:** Alpha-1 is **one account**. Hardening a single workspace end-to-end teaches more than splitting attention across two simultaneous personas. The e-commerce account is the second-phase alpha (Alpha-1.5 in §Phase-transitions); we circle back once the trader setup is bulletproof and friction signals have settled.

This playbook captures:
1. The **governance model** — who fills which seat in the account, what's shared, what's not
2. The **setup spec** — exactly what the trader persona is, how it's seeded
3. The **operating protocol** — how we both use the account day-to-day without stepping on each other
4. The **friction-capture loop** — how observations turn into ADR seeds
5. **Claude's rules of engagement** — what I can do autonomously, what I escalate, what I never touch
6. **Phase transitions** — when and how we expand scope

---

## Governance model

### The account

| Account | Persona | Primary platform | Real/paper |
|---|---|---|---|
| `alpha-trader` | Jim-Rohn-inspired long-horizon compounder. Patient. Small-book US equities. Treats risk management as identity, not rule. | Alpaca (paper throughout Alpha-1) | Paper throughout Alpha-1; live is Alpha-2 decision |

Real Supabase user + workspace, created via normal signup. Normal OAuth for Alpaca paper connection. Normal YARNNN signup grant ($3 balance). No special infrastructure.

### Why Jim Rohn as the inspiration

Jim Rohn's philosophy isn't about trading mechanics — it's about the operator:

- **Work harder on yourself than you do on your job.** The account's identity is the operator's standards, not the market's. Principles come from conviction, not convention.
- **Compounding is everything.** Long-horizon thinking. Don't optimize for the next trade; optimize for the next decade of trades.
- **Discipline > motivation.** Risk rules aren't external guardrails; they're the operator's character. A Reviewer enforcing `_risk.md` is enforcing *who the operator is*, not *what they're allowed to do*.
- **Success leaves clues.** `_performance.md` isn't a scoreboard; it's the pattern library the Reviewer and operator learn from over time.
- **Ordinary means, extraordinary consistency.** The trader doesn't need rare setups or exotic instruments. A small ticker list, patient execution, and rigorous review compound.

This is structurally the **hardest stress test for the Reviewer layer** we could pick. An impatient scalper-trader is a weak test — most proposals are obvious rule-violations. A Rohn-trader generates subtle proposals where the Reviewer has to reason about whether *the trade matches the operator's declared character*, not just whether *the trade violates a rule*. That's capital-EV reasoning (ADR-194 §5, ADR-195 `_performance.md` read path) working the way the ADR claims.

It's also the hardest stress test for the cockpit. A Rohn-trader doesn't live in the Queue all day reacting to proposals. They check Overview in the morning, make one or two considered decisions, review outcomes weekly. If the cockpit only rewards high-frequency operators, this persona surfaces that gap immediately.

### Shared credentials, distinct seats

Account login credentials stored in a shared secret location (1Password / Bitwarden / team vault — KVK picks). Both KVK and Claude (via authenticated web access when available, or via KVK's browser relaying action requests when not) can log in.

**Within the account, three cognitive seats are filled distinctly:**

| Seat | Filled by | Scope |
|---|---|---|
| **Operator** | KVK (primary) | Makes strategy calls — "this week I'm focused on semis", "I want to increase position-size confidence on my highest-win-rate ticker", "the weekly review should emphasize X" |
| **AI Reviewer** | AI Reviewer agent (ADR-194 Phase 3 — already running via `review-proposal` task) | Reviews individual proposals against `_risk.md` + `_performance.md` + `principles.md`. Autonomous. Writes `decisions.md` with `ai:` tag. |
| **Meta-observer + Operator (secondary)** | Claude (this session, via authenticated operator login) | Lands on cockpit as operator. Reviews the AI Reviewer's calibration. Approves reversible proposals per principles. Escalates irreversibles to KVK. Watches friction. Proposes ADR changes from observation. Writes `decisions.md` with `human:` tag (session auth doesn't distinguish admin-as-Claude from admin-as-KVK — acceptable for Alpha-1; see §Audit-trail-limitation). |

This is the structural answer to "hand the keys to the AI." The cockpit already supports multiple humans with identity-tagged actions. Claude-as-operator uses the same interface a human uses — *because there is no other interface.* That's the test.

### What Claude can do as an authenticated operator

- Read every cockpit surface (Overview, Team, Work, Context, Review, `/chat`)
- Read `_performance.md`, `decisions.md`, any substrate file via the Context browser or `/api/workspace/file`
- Approve / reject **reversible** proposals via cockpit Queue
- Use the ambient YARNNN rail — talk to YARNNN, have it read context, invoke primitives
- Trigger tasks manually via `/work`
- Propose `principles.md` or `_risk.md` edits to KVK (do not self-apply; see §never-do)
- Read activity_log / token_usage / any audit telemetry

### What Claude does NOT do as operator

- **Approve irreversible actions without KVK confirmation.** `irreversible` reversibility class always escalates, regardless of Claude's judgment. Structural safety fence.
- **Change workspace identity (IDENTITY.md, BRAND.md, `_operator_profile.md`) without KVK.** These define the persona. If the persona evolves, joint decision.
- **Dissolve / archive / pause agents without KVK.** Authored team is the moat; disrupting it is the most consequential reversible action.
- **Modify `principles.md` or `_risk.md`.** Reviewer framework + risk rules ARE the operator's character. Claude can propose changes; KVK ratifies.
- **Switch platform connection from paper to live.** Never. Phase transition, not an operating decision.
- **Handle billing.** Alpha runs on KVK's card / $3 signup grant + top-ups.

### Audit-trail limitation (open)

Current audit doesn't distinguish "KVK logged in" from "Claude logged in" within the shared account. `decisions.md` tags both as `human:<user_id>` because session auth doesn't carry that metadata. For Alpha-1 this is acceptable — our trust loop is joint, we're both supervising the same work, post-hoc attribution is possible via cross-reference with observation notes (Claude logs every action to `docs/alpha/observations/`).

If this becomes a real problem, we add session-metadata flagging. Not blocking for Alpha-1.

---

## Setup spec — alpha-trader

### Persona identity

Seeded into `/workspace/IDENTITY.md` during the first YARNNN conversation (pasted as rich input per ADR-190 inference-driven scaffold):

```markdown
# Alpha Trader — a Jim-Rohn-inspired long-horizon compounder

## Who I am
I'm a retail trader with conviction and patience. My edge is not speed;
it's discipline. I believe compounding beats brilliance and that the
hardest work I do is on myself, not on the market. I'm long-only,
US equities, with a bias toward names I've researched deeply and hold
meaningfully.

I don't need to win every week. I need to not blow up, and to let the
compounding do its work. I measure my year, not my day.

## My book
Starting capital: $25,000 (paper). Target 10–20 positions over the
course of the year, averaging 2–3 open at a time. Hold duration 2–12
weeks typical; willing to hold winners longer.

## What I want YARNNN to do
- Track my small watchlist thoroughly. I'd rather know five tickers
  deeply than fifty superficially.
- Pre-market brief every trading day covering my watchlist: price
  action, news, earnings, sector context. I read it over coffee before
  the open.
- Propose trades ONLY when setups align with my declared strategy and
  my `_performance.md` track record supports the conviction. I approve
  every single one.
- Enforce my risk limits religiously. Don't ever approve a proposal
  that violates `_risk.md`. If the Reviewer sees me about to break my
  own rules, stop me.
- Weekly performance review every Sunday evening — honest, quantitative,
  and framed against my declared strategy. If I'm drifting from who I
  said I'd be, tell me.
- Quarterly reflection drafting — a longer piece reviewing the past
  quarter's decisions against my principles. I revise it myself; you
  draft it from the data.

## What I don't want
- Autonomous trade submission, period. Paper OR live. Every trade is
  mine to approve.
- Ignoring my risk limits "just this once." There is no just this once.
- Cheerleading or sycophancy. Give me the honest read. I want a candid
  partner, not an encourager.
- Optimizing for activity. If the right answer this week is to do
  nothing, say so.
- Suggestions based on general market commentary or FOMO. Only suggest
  based on MY watchlist, MY track record, MY declared strategy.

## My operator hypothesis (to be tested)
Risk discipline + patient compounding beats active trading for
retail operators at my capital level. YARNNN's job is to make me
faithful to that hypothesis, not to test it by letting me break it.
```

### Operator profile (strategy declaration)

Seeded into `/workspace/context/trading/_operator_profile.md`:

```markdown
# Operator profile — Alpha Trader

## Declared strategy
- Long-only US equities
- Concentration in sectors I research: large-cap tech, semiconductors,
  select AI infrastructure
- Holding period: 2–12 weeks typical; longer for high-conviction
- Position count: 2–3 open at a time, 10–20 over a year
- Sizing: 3–10% of portfolio per position, never more than one position
  at 10%+

## Declared edge
I don't trade faster or smarter. I hold positions in names I know
deeply, wait for setups that match clear criteria, and don't
over-trade between setups. My advantage is patience and honest
self-review.

## What "success" looks like
- Year-over-year compounding consistent with index + a modest edge
- Win rate on declared-strategy setups ≥ 55%
- Average loss ≤ average win × 0.75
- Zero "impulsive" trades (trades taken outside declared setups)
- Track record in `_performance.md` that a senior operator would
  recognize as disciplined

## What I'm NOT trying to do
- Not trying to match prop traders on return
- Not trying to beat the index on 3-month windows
- Not trying to win every week
- Not trying to have a position all the time
```

### Reviewer principles

Seeded into `/workspace/review/principles.md`:

```markdown
# Reviewer principles — Alpha Trader

## Auto-approve
- NONE. Every trade is human-reviewed for Alpha-1.
- Reads (positions, quotes, market data) do not generate proposals.

## Always escalate to human
- All `trading.submit_*` proposals (bracket, trailing stop, market order,
  partial close)
- All `trading.cancel_*` actions
- All watchlist modifications
- All `commerce.*` actions (N/A for this account, but principle is
  platform-wide)

## Capital-EV orientation — reason in character, not just in rules
- Before evaluating whether a proposal violates `_risk.md`, evaluate
  whether it matches the operator's declared strategy in
  `_operator_profile.md`. A rule-compliant proposal that contradicts
  declared character should be flagged with that contradiction even
  if approved.
- Reference `_performance.md` — if a similar proposal has lost 3 of
  the last 4 times, surface that pattern as part of the review. Don't
  reject automatically; the operator decides, but they decide with
  the pattern visible.
- Challenge over-concentration. If a trade would push any sector
  above 50% of book, flag loudly even if technically within
  `max_position_percent_of_portfolio`.
- Challenge impulsivity. If a trade is in a ticker not on the
  declared watchlist, that's a signal of drift; require explicit
  acknowledgment from operator ("yes, I'm expanding my universe").

## Tone
Honest over polite. Skeptical over permissive. The operator asked
for candor; give it.

## When deferring to human (beyond always-escalate)
- Proposal passes all rules but the AI Reviewer's confidence is ≤ 60%
- Two or more principles pull in opposite directions
- The proposal is the first of its kind (no historical pattern in
  `_performance.md` yet)
```

### Risk parameters

Seeded into `/workspace/context/trading/_risk.md`:

```markdown
max_position_size_usd: 3750          # 15% of $25k starting capital
max_position_percent_of_portfolio: 10  # Never >10% except rebalance
max_daily_loss_usd: 375              # 1.5% daily loss limit
max_weekly_loss_usd: 1000            # 4% weekly loss limit
max_day_trades: 1                    # Paper doesn't have PDT, but honor the discipline
max_order_size_shares: 100
require_stop_loss: true
allowed_tickers: [AAPL, MSFT, GOOGL, NVDA, AMD, META, SMH, SPY, QQQ]
blocked_tickers: []
trading_hours_only: true
min_days_between_same_ticker_open: 3
max_sector_concentration_percent: 50
require_operator_profile_alignment: true   # Enforced by Reviewer, not a raw rule
```

### Task scaffolding target

YARNNN composes via conversation during first session. Target set (iterate if YARNNN proposes different tasks that fit better):

- `track-watchlist` (accumulates_context, 3× daily @ 8:00/11:30/15:45 ET) — feeds `/workspace/context/trading/`
- `pre-market-brief` (produces_deliverable, daily @ 8:15 ET) — composed from watchlist + sector news + `_performance.md` patterns
- `trade-proposal` (reactive, fires from tracker setup-detection) — emits `ProposeAction` for bracket orders
- `weekly-performance-review` (produces_deliverable, Sunday 6pm ET) — reads `_performance.md` + honest assessment against `_operator_profile.md`
- `quarterly-reflection` (goal, bounded 4-week cycle ending last Sunday of each quarter) — drafts a longer review piece; operator revises

---

## Setup sequence (one-time)

### Phase 0 — prerequisites

- [ ] Shared-credentials vault chosen — KVK picks, communicates location to Claude
- [ ] Persona email address created (e.g., `alpha-trader@kvk-personal.com` or a Gmail alias)
- [ ] Alpaca paper API key provisioned (API key + secret, scoped to paper account)
- [ ] Gmail / inbox for this persona decided (daily-update emails land here)

### Phase 1 — account creation (KVK)

1. Sign up via normal YARNNN signup flow using the persona email
2. Note the `user_id` from Supabase
3. In the first YARNNN chat session, paste the IDENTITY.md content from §Setup-spec as rich input — YARNNN processes via inference-driven scaffold (ADR-190)
4. Confirm YARNNN-proposed `/workspace/BRAND.md` (low stakes — tone + voice; Claude's judgment call if KVK defers)
5. Approve YARNNN-proposed task scaffolding. Goal: converge to the target set in §task-scaffolding. Iterate if YARNNN proposes different tasks that fit the persona better.
6. Connect Alpaca paper via the integrations flow
7. Seed `_operator_profile.md`, `principles.md`, `_risk.md` per §Setup-spec via the YARNNN rail:
   - "YARNNN, set my operator profile at `/workspace/context/trading/_operator_profile.md` to: [paste]"
   - "YARNNN, set my review principles to: [paste]"
   - "YARNNN, set my risk parameters at `/workspace/context/trading/_risk.md` to: [paste]"
8. Store credentials in the shared vault
9. Confirm first daily-update email delivers (tomorrow morning baseline check)

### Phase 2 — Claude operator onboarding

Once Phase 1 is complete and credentials shared:

1. Claude logs in via authenticated web access
2. Lands on `/overview`
3. Opens the YARNNN rail: *"I'm operating this account alongside KVK. Orient me: what does IDENTITY.md say about who this operator is? What's scaffolded? What's pending?"*
4. Reads IDENTITY.md + `_operator_profile.md` + `principles.md` + `_risk.md` via Context
5. Reviews Team — confirms scaffolded agent roster matches the persona's work
6. Reviews Work — confirms task cadences are sensible
7. Writes the baseline observation: `docs/alpha/observations/{date}-alpha-trader-first-session.md`
   - Include: first impressions, anything surprising, anything missing, immediate friction if any
8. Confirms to KVK: "baseline set, beginning alpha operation."

---

## Operating protocol (day-to-day)

### Daily rhythm (trading days)

**Morning (8:00–9:30 ET):**
- 8:00: `track-watchlist` fires
- 8:15: `pre-market-brief` fires → email arrives (expository pointer per ADR-202) → Claude opens Overview from deep-link
- 8:15–8:45: Claude reads Overview. Checks Queue for any overnight/pre-market proposals. Reviews yesterday's decisions tail.
- 8:45–9:00: If any proposals pending, Claude + KVK coordinate out-of-band (quick message exchange in this session or agreed channel) on anything requiring joint judgment
- 9:30: market open — no special action unless a trade fires

**During market hours (9:30–16:00 ET):**
- Claude checks Overview Queue periodically (not continuously — Rohn-trader isn't a scalper; we don't need minute-by-minute attention)
- If a `trade-proposal` fires: Claude reviews against principles + `_performance.md`. Rohn-trader principles mean **defer to KVK by default** — most trade proposals should escalate, not auto-approve, because the trader's character is that *they* approve their trades
- Any unexpected cockpit behavior, rail response, or agent output gets noted for observation log

**Evening (after market close):**
- Claude reads the day's `decisions.md` tail — who decided what? How did the AI Reviewer perform?
- Claude reads `_performance.md` updates from the reconciler (runs daily; reconciles any fills)
- Friction observed today → observation note: `docs/alpha/observations/{date}-alpha-trader-{brief-tag}.md`

### Weekly rhythm

**Friday after close:**
- Claude writes a mid-week pulse note if week's observations warrant — otherwise skip

**Sunday evening:**
- 6:00 ET: `weekly-performance-review` fires → output lands in `/tasks/weekly-performance-review/outputs/{date}/`
- 6:15–7:00: Claude + KVK review the output together (async OK — shared access)
- KVK captures "what this surface SHOULD have shown" as observation notes
- Claude + KVK jointly write the week's rollup report: `docs/alpha/reports/week-{N}-alpha-trader.md`
  - What worked
  - What surfaced as friction
  - What warranted an ADR change (if anything)
  - What we learned about the Rohn-persona's actual use of YARNNN

### Coordination between Claude and KVK

- **Out-of-band updates** happen in this Claude Code session or a dedicated chat — not inside YARNNN.
- **In-band in YARNNN**: both use `/chat` rail to talk to YARNNN. Conversation history is session-scoped and shared. No impersonation; each message is attributed to whoever's logged in.
- **Proposal approval**: first authorized operator to respond wins (no approval lock). OK for Alpha-1; revisit if it causes confusion.

### Claude's discretion ladder (decision rules when acting as operator)

For this account specifically (Rohn-trader persona), the discretion ladder is tighter than a generic operator:

| Situation | Claude action |
|---|---|
| AI Reviewer approved; proposal executed | Verify execution + outcome reconciliation next day. Note if outcome deviates from Reviewer's reasoning. |
| AI Reviewer deferred; proposal pending | **Default: escalate to KVK.** Rohn-trader's character is that the operator approves their own trades. Only Claude-approves if (a) clearly within `_risk.md`, (b) clearly within `_operator_profile.md` declared strategy, (c) `_performance.md` pattern supports it, (d) proposal is reversibility=reversible, (e) Claude can articulate why KVK would also approve. Any one of these missing → escalate. |
| AI Reviewer rejected | Review the reasoning. Log as observation if reasoning looks wrong (calibration input). Don't override. |
| No Reviewer decision yet | Wait. Don't preempt. |
| Irreversible proposal | Always escalate. Full stop. |
| Proposal for a ticker not on declared watchlist | Escalate even if rules permit — it's a character drift signal, operator decides. |

### Escalation mechanics

Claude escalates → leaves proposal in `pending` → writes observation note naming `proposal_id` + reasoning → messages KVK out-of-band → KVK decides. Proposal TTL is the safety net; silent expiration is acceptable outcome for anything KVK doesn't get to in time.

---

## Friction-capture loop

Every observed friction becomes an ADR seed. This is the point of Alpha-1.

### Observation note format

Pin as `docs/alpha/observations/{YYYY-MM-DD}-alpha-trader-{slug}.md`:

```markdown
# {date} — alpha-trader — {one-line summary}

**Context:** what was I trying to do?
**What happened:** what the cockpit / YARNNN / the agent did.
**Friction:** what was harder or more confusing than it should be.
**Hypothesis:** what architectural / UX / prompt change would resolve it.
**Dimensional classification:** which FOUNDATIONS v6.0 dimension does this affect? (Substrate / Identity / Purpose / Trigger / Mechanism / Channel)
**ADR candidate:** does this warrant a new ADR, an amendment, or is it a code-level tweak?
**Rohn-persona fit:** does this friction matter specifically because of who this operator is, or would any operator hit it?
```

### Weekly rollup

End of each week: consolidate observations into a report at `docs/alpha/reports/week-{N}-alpha-trader.md`. The report answers:

- What's working?
- What surfaced as friction more than once?
- What did KVK want that the architecture didn't support?
- What did AI-operator Claude want that might not generalize to a human?
- Is the Rohn-persona operating naturally in the cockpit, or is the cockpit fighting their character?

### Decision tree — when an observation becomes an ADR

- **Same friction for 2+ weeks** → ADR candidate
- **Single friction, fixable by a prompt tweak** → update YARNNN prompt, log in `api/prompts/CHANGELOG.md`, no ADR
- **Single friction, fixable by a component tweak** → patch, no ADR
- **Structural gap (missing primitive, missing dimension behavior)** → ADR immediately
- **Persona-only friction (specific to Rohn-trader character)** → defer ADR; might be dispositive only if reproduced in e-commerce once Alpha-1.5 starts

This last bullet is the **anti-verticalization gate** (per ADR-191 DOMAIN-STRESS-MATRIX). A frictio that only shows up for a Rohn-trader character is not automatically architecture-level — it might be domain-specific and the right fix might be a task-type template or prompt nuance, not an ADR.

---

## Phase transitions

Alpha-1 scopes to **paper trading + Rohn-trader persona alone**. Transitions are explicit decisions.

| Phase | Trigger | Decision locus |
|---|---|---|
| **Alpha-1** (current) | Rohn-trader running on Alpaca paper; Claude + KVK operating; friction captured | — |
| **Alpha-1.5** (add e-commerce persona) | 2+ weeks of Alpha-1 clean operation; friction trend declining; e-commerce persona identity drafted | Joint decision, captured in playbook update |
| **Alpha-2** (real trading, small book) | Alpha-1.5 clean for 2 weeks + Reviewer calibration data sufficient (enough `ai:` decisions in `decisions.md` to assess calibration) + KVK comfort | Joint decision; requires explicit ADR amendment |
| **Alpha-3** (external operator onboarded) | 4+ weeks Alpha-2 clean; ICP signal present; scope doc drafted | Joint decision with external-operator onboarding doc |

Never skip phases. Each phase's clean period is the license for the next.

### E-commerce persona — deferred to Alpha-1.5

The e-commerce persona was part of the original two-account plan. It's deferred, not cancelled. Reasons:
- **Single-account attention produces sharper friction signal.** Two simultaneous alphas dilutes focus.
- **Trader is the harder stress test.** Rohn-persona exercises Reviewer capital-EV reasoning, `_performance.md` pattern-reading, proposal discipline — if these work for trader, they'll work for commerce. Reverse is not as clearly true.
- **Circling back once trader is bulletproof is a deliberate reinforcement pattern.** When we add e-commerce, we'll know which frictions are architecture-level (both accounts feel them) vs. domain-specific (only one does).

When we circle back to e-commerce, the playbook expands with a second persona spec, a second operator profile, a second principles + `_risk.md`, and §Governance updated for two shared accounts. `DOMAIN-STRESS-MATRIX.md` Impact tables then gain two real columns of data.

---

## Claude's rules of engagement (summary)

**I can:**
- Read any cockpit surface, any substrate file, any audit trail
- Approve/reject reversible proposals per principles (Rohn-trader's tighter discretion ladder applies)
- Talk to YARNNN in the rail
- Trigger tasks manually
- Observe friction and write observation notes
- Propose ADR changes, principles edits, prompt tweaks — *to KVK for ratification*

**I escalate:**
- Irreversible proposals (always)
- Proposals outside declared principles (even if I agree with them)
- Ambiguous Reviewer-deferrals (KVK decides)
- Persona-identity changes (IDENTITY.md, BRAND.md, `_operator_profile.md`, `principles.md`, `_risk.md`)
- Any trade proposal for a Rohn-trader unless all five conditions in the discretion ladder are met

**I never:**
- Change workspace identity without KVK
- Dissolve agents without KVK
- Modify `principles.md`, `_risk.md`, or `_operator_profile.md` directly
- Switch platform from paper to live
- Handle billing
- Act in ways incompatible with the Rohn-persona's declared character (e.g., approving impulsive trades just because they're rule-compliant)

**I ask KVK when:**
- Unsure whether a proposal matches character (not just rules)
- Encountering architectural behavior that contradicts an axiom or ADR
- Observing friction that might warrant immediate ADR change vs. defer-and-accumulate
- Considering a principles / `_risk.md` / `_operator_profile.md` edit

---

## What this playbook does NOT address (open for Alpha-1 Week 1 iteration)

1. **Credentials-sharing mechanics** — vault location, rotation policy, backup. KVK's operational decision.
2. **KVK's time budget** — hours/week. Shapes how much Claude operates autonomously.
3. **Communication cadence** — daily, weekly, ad-hoc. Start ad-hoc; formalize if needed.
4. **Observation-doc review rhythm** — probably batch at the weekly rollup; adjust if time-sensitive friction appears.
5. **ADR-amendment protocol from alpha** — Claude drafts, KVK ratifies, same PR pattern as before. Observations subfolder is the input layer.
6. **Claude's authenticated session access to the web app** — operational detail: how does Claude Code (this session) actually log in? Likely via credentials from the shared vault passed into a browser session KVK initiates; refined during Phase 2 onboarding.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial playbook. Single account (alpha-trader) running Jim-Rohn-inspired persona. Governance model (Operator = KVK, AI Reviewer = reviewer agent, Meta-observer + secondary operator = Claude). Setup spec including IDENTITY.md / _operator_profile.md / principles.md / _risk.md with Rohn-character reasoning. Phase 2 Claude-onboarding sequence. Daily + weekly operating protocol tuned to long-horizon trader (not scalper). Rohn-specific discretion ladder (tighter than generic). Friction-capture with Rohn-persona-fit dimension. Phase transitions defer e-commerce to Alpha-1.5 and frame it as deliberate scope discipline. Six open questions flagged for Week-1 iteration. |
