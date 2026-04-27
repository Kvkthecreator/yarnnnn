---
title: alpha-trader Bootstrap — kvk Dogfooding Runbook
date: 2026-04-27
status: ops runbook (NOT an ADR)
related:
  - docs/alpha/ALPHA-1-PLAYBOOK.md (Alpha-1 governance + operating protocol — kvk operator role)
  - docs/alpha/E2E-EXECUTION-CONTRACT.md (E2E test contract for the framework loop)
  - docs/alpha/personas/alpha-trader/MANDATE.md (kvk's persona-canonical mandate)
  - docs/programs/alpha-trader/README.md (program-layer spec — what alpha-trader IS)
  - docs/adr/ADR-226-reference-workspace-activation-flow.md (universal OS activation flow — what this runbook is NOT)
  - docs/adr/ADR-187-trading-integration.md (alpaca + alpha vantage wiring)
  - docs/adr/ADR-194-reviewer-layer.md (Reviewer seat — kvk fills it manually until AI Reviewer is calibrated)
  - docs/adr/ADR-195-money-truth-substrate.md (_performance.md as canonical money-truth)
---

# alpha-trader Bootstrap — kvk Dogfooding Runbook

> **What this is:** the persona-layer runbook that walks the alpha-trader operator (kvk; or Claude-acting-as-operator-on-behalf, in alpha-test mode 1) from clean-slate workspace to autonomous paper-trading loop running. Operational, specific to the alpha-trader persona + alpaca paper account. Not an ADR. Not OS-architecture work. **Dogfooding to validate the framework end-to-end.**
>
> **What this is NOT:** the universal reference-workspace activation flow. That lives at [ADR-226](../../../adr/ADR-226-reference-workspace-activation-flow.md) and is what *every* operator running *any* program does at signup. ADR-226 is OS-level; this file is alpha-trader-persona-level.

## Framing — operator setup, then autonomous loop

The bootstrap has two phases that should never blur:

**Phase A — Operator setup** (the human-or-Claude-as-operator does these steps).
The operator goes from clean signup through the activation conversation,
authors persona content (mandate, signals, risk, principles), connects the
Alpaca paper account, and then **stops driving**. This is what every alpha
operator does at workspace activation. Steps 1–5 below.

**Phase B — Autonomous loop** (the system runs itself).
With the workspace authored + alpaca connected + AUTONOMY.md set to
`bounded_autonomous` (paper-mode carve-out per ADR-217), the framework's
invocation paths fire on their own:

- Operator-or-Claude-on-behalf chat-initiates a task ("@yarnnn run signal-evaluation")
  — chat-initiated invocation, run-now per ADR-205 chat-first triggering.
- Tasks emit proposals to `action_proposals`, which trigger reactive
  Reviewer dispatch per ADR-194 v2 Phase 2b (`handle_propose_action`
  post-insert hook).
- AI Reviewer (Simons persona at `/workspace/review/IDENTITY.md`) applies
  the six-check chain from `principles.md`, reads `_performance.md` for
  capital-EV, decides approve/reject/defer per AUTONOMY.md ceiling.
- Approved reversible-paper proposals fire `ExecuteProposal` →
  `platform_trading_submit_order` → alpaca paper fill.
- `back-office-outcome-reconciliation` (chat-initiated or
  reactive-on-fill) reconciles to `_performance.md`.
- Next operator-or-Claude chat-initiation reads richer substrate.

This is **not** a cron sweep. It's not "the scheduler fires tasks." It's
chat-initiated and event-reactive invocation flowing through the primitive
matrix per ADR-204/207. Per ADR-205 + Axiom 4, schedule is an annotation,
not a precondition; the dispatch authority is TASK.md + capability gate +
AUTONOMY.md, not the unified scheduler. The unified scheduler exists as
infrastructure for periodic trigger sub-shape but it is not the load-
bearing path that closes the alpha-trader loop.

**The operator's job during Phase B is observation + course-correction**,
not driving. Watch the cockpit. Note what surfaces (proposals, decisions,
fills, performance writes). Log friction to
`docs/alpha/observations/{date}-{topic}.md`. Don't intervene unless
something breaks or AUTONOMY.md needs revision.

## Why this is a separate document

A discourse pass on ADR-226 sharpened that two activation concerns had been bundled together:

1. **Universal activation flow** — what every operator does. Program selection, fork-the-reference, differential authoring conversation. ADR-226's job.
2. **kvk's specific dogfooding bootstrap** — kvk's workspace already exists, has accumulated test data, has an alpaca paper account. The need is to get it producing paper trades through the framework loop. Persona-layer.

Bundling them risks designing OS-level infrastructure for kvk-specific reality, accidentally fitting the OS to one operator. The split keeps each concern principled. Anything kvk's bootstrap surfaces that the OS *actually* needs becomes its own ADR — justified by demand, not bundled into ADR-226.

## What kvk's existing workspace looks like (assumed starting state)

Before this runbook starts, the assumption is:

- kvk's user account exists. Workspace is initialized per ADR-205/206 + (if applicable) post-ADR-226 with `program_slug='alpha-trader'`.
- Alpaca paper account exists. API keys provisioned. Connected to YARNNN as a `platform_connections` row with `platform='trading'` (or whichever the live wiring uses).
- Test data may exist from prior framework iterations — old tasks, old reviewer decisions, partial principles. **Tolerated, not blocking.** kvk audits and cleans manually as bootstrap progresses.
- The cockpit (post-ADR-225 Phase 2) renders alpha-trader bundle chrome (banner, pinned tasks, detail middles for trading-signal / portfolio-review).

The bootstrap walks kvk from this state to **first paper trade closing the loop end-to-end** — proposed → reviewer-approved → submitted to Alpaca → fill confirmed → reconciled into `_performance.md` → next cycle reads richer substrate.

## The end-to-end loop kvk needs to validate

Per ADR-207 7-arrow loop: **Mandate → Rules → Proposal → Verdict → Approval → Action → Outcome**.

For kvk's paper trading dogfooding:

| Arrow | Substrate | kvk action | Status |
|---|---|---|---|
| Mandate | `/workspace/context/_shared/MANDATE.md` | Author edge hypothesis, primary action, success criteria | ✅ Authored at `docs/alpha/personas/alpha-trader/MANDATE.md` (paste-ready into UpdateContext) |
| Rules — Profile | `/workspace/context/trading/_operator_profile.md` | Author 5-8 declared signals with measured edge | ⚠️ Persona-canonical content needed; not yet in repo |
| Rules — Risk | `/workspace/context/trading/_risk.md` | Author position-sizing formula, var budget, sector limits, regime scalar | ⚠️ Persona-canonical content needed |
| Rules — Reviewer | `/workspace/review/principles.md` | Author hard rejection rules + capital-EV thresholds | ⚠️ Reference template exists in alpha-trader bundle; needs kvk's tuning |
| Proposal | `action_proposals` row + signal attribution | trading-signal task fires, proposes order with signal name + sized stop | Wiring shipped (ADR-187 + ADR-225); content depends on rules being authored |
| Verdict | `/workspace/review/decisions.md` | Reviewer approves/rejects with reasoning | Wiring shipped (ADR-194 v2); kvk fills the seat manually until AI Reviewer is calibrated |
| Approval | UI Approve/Reject affordance | kvk clicks Approve in `/agents?agent=reviewer` Queue | Wiring shipped (ADR-202) |
| Action | Alpaca submit_order via platform_tools | `trading-execute` task fires Reviewer-approved order | Wiring shipped; needs AUTONOMY.md to permit auto-execute or manual approve flow |
| Outcome | `/workspace/context/portfolio/_performance.md` | back-office-outcome-reconciliation reads broker fills, writes performance | Wiring shipped (ADR-195 v2 Phase 5a) |

The wiring is shipped. **What kvk needs to do is author the rules.** The bootstrap is fundamentally a persona-content authoring exercise; the framework infrastructure already supports it.

## The runbook — six concrete steps

### Step 1 — Verify activation state

Before authoring, confirm the workspace is in the post-fork state ADR-226 produces:

- [ ] `/workspace/context/_shared/MANDATE.md` exists (skeleton or authored — either is fine; Step 2 handles).
- [ ] `/workspace/context/_shared/CONVENTIONS.md` matches alpha-trader's program canon (sourced from `docs/programs/alpha-trader/reference-workspace/context/_shared/CONVENTIONS.md`, frontmatter stripped).
- [ ] `/workspace/context/_shared/AUTONOMY.md` matches alpha-trader's canon defaults.
- [ ] `/workspace/review/IDENTITY.md` has the Simons-style Reviewer persona canon.
- [ ] `/workspace/review/principles.md` exists as the alpha-trader template (skeleton, will be tuned in Step 4).
- [ ] alpaca `platform_connections` row is `status='active'`. (Verify via `/settings/connectors`.)
- [ ] Cockpit `/work` shows the "Paper-only..." banner per ADR-225 phase overlay.

If any item fails, fix before continuing — ADR-226 forking is the precondition for this bootstrap. If activation hasn't run for kvk's existing workspace, run it (one-shot manual fork via the activation primitive, or re-init through the onboarding flow).

### Step 2 — Author MANDATE.md from the persona-canonical source

The persona-canonical mandate already exists at `docs/alpha/personas/alpha-trader/MANDATE.md`. Paste it verbatim into kvk's workspace via YARNNN chat:

```
@yarnnn — paste this verbatim into /workspace/context/_shared/MANDATE.md via UpdateContext(target="mandate"):

[contents of docs/alpha/personas/alpha-trader/MANDATE.md, excluding the HTML comment header]
```

YARNNN routes through `UpdateContext`; ADR-209 captures the revision with `authored_by="operator"` (kvk-attributed via the chat session).

**Verification:** `MANDATE.md` no longer contains the bundle's "operator-author-here" prompts; instead contains the canonical alpha-trader mandate (Primary Action, Success Criteria, Daily Discipline, Outcome Signal sections). The `ManageTask(create)` hard gate per ADR-207 P2 now passes.

### Step 3 — Author `_operator_profile.md` (5-8 declared signals)

This is the substantive authoring step — kvk's edge hypothesis made concrete.

Source content: kvk's existing trading thesis (from prior alpha iterations, or fresh if starting clean). The structure:

```markdown
# Operator Profile — alpha-trader

## Edge hypothesis (one paragraph)
Why this edge exists. Who's on the other side. What would falsify it.

## Declared signals (5-8 total)

### Signal 1 — {name}
- Entry conditions (literal, mechanical):
  - {condition 1, with thresholds}
  - {condition 2}
- Stop distance derivation: {formula or rule}
- Expected expectancy: {historical or theoretical}
- Retire-flag threshold: {below this, signal auto-defers}

### Signal 2 — {name}
... (etc., 5-8 total)

## Universe
{watchlist — tickers + how the universe is curated}

## Time horizon
{intraday / 2-10 day / longer}
```

Author via YARNNN chat:

```
@yarnnn — author /workspace/context/trading/_operator_profile.md with the following content. Use UpdateContext(target="domain", domain="trading", file="_operator_profile.md") with authored_by="operator":

[content]
```

**Verification:** `_operator_profile.md` exists at `/workspace/context/trading/_operator_profile.md`. Alpha-trader's `**Required Capabilities:** read_trading` task scaffolding can now reason against real signal definitions, not placeholders.

### Step 4 — Tune `principles.md` (Reviewer rules)

The bundle ships an alpha-trader-typical principles.md template (`docs/programs/alpha-trader/reference-workspace/review/principles.md`, tier=`authored`). Already forked into kvk's `/workspace/review/principles.md` per ADR-226. Now kvk tunes it.

Tuning happens through YARNNN chat:

```
@yarnnn — review /workspace/review/principles.md and walk me through tuning each section to my edge. Start with the hard rejection rules, then capital-EV thresholds. Use UpdateContext writes for each section.
```

YARNNN's profile-aware prompt (ADR-186) surfaces the right framing — "you're authoring Reviewer principles for an alpha-trader workspace; the bundle ships defaults; tune them to your edge." Conversation walks Section 1 (hard rejection), Section 2 (capital-EV thresholds), Section 3 (auto-approve threshold — kept commented out for now per ADR-194 v2 Phase 3 safe default), through `principles.md` end.

**Verification:** `principles.md` contains kvk-tuned content, not the bundle template. Reviewer (kvk-as-occupant for now) reads it on every proposal verdict.

### Step 5 — Compose first trading-signal task

With Mandate + Profile + Risk + Principles authored, kvk asks YARNNN to scaffold a `trading-signal` task:

```
@yarnnn — scaffold a trading-signal task. Daily cadence. Reads trading + portfolio domains. Writes signal proposals to action_proposals.
```

YARNNN consults the bundle's task_types (per ADR-224 fallback path: `get_task_type('trading-signal')` returns the alpha-trader-bundled definition); applies the bundle's `default_objective` + `default_deliverable` + `instruction` from MANIFEST.yaml; calls `ManageTask(action='create', type_key='trading-signal')`. Hard gate per ADR-207 P2 passes (MANDATE.md is authored). Task materializes at `/tasks/trading-signal/TASK.md`.

**Verification:** task exists. `/work` list-mode pinned-tasks renders it (per ADR-225 alpha-trader SURFACES.yaml). Detail middle (per ADR-225 §4 task_slug match) shows the bundle's `queue` archetype with `TradingProposalQueue` component.

### Step 6 — Hand off to the autonomous loop, observe

This is the validation moment. Operator setup is complete; now the system
runs itself per Phase B. The operator (kvk-or-Claude-on-behalf) makes one
chat-initiated invocation to seed the cycle, then **stops driving**.

```
@yarnnn — let's start running. Take signal-evaluation, read the universe,
emit proposals where signals fire honestly.
```

What happens next without operator intervention:

- YARNNN invokes `ManageTask(action='trigger', slug='signal-evaluation')`
  via the chat surface. This is a chat-initiated invocation per ADR-205
  chat-first triggering — the canonical path for first-cycle dispatch.
- Pipeline reads accumulated context (operator profile, declared signals,
  current positions, market data via `platform_trading_get_market_data`),
  evaluates each declared signal mechanically against entry conditions.
- Where conditions fire: emits `action_proposals` rows with full
  signal attribution + sized stop + sizing-formula derivation +
  expectancy lookup against `_performance.md` (or "no track record" flag
  on the first cycles).
- Each proposal insert triggers reactive Reviewer dispatch per ADR-194
  v2 Phase 2b — the `handle_propose_action` post-insert hook routes
  through `services/review_proposal_dispatch.py`.
- AI Reviewer (Simons persona at `/workspace/review/IDENTITY.md`,
  forced-tool-call per ADR-194 v2 Phase 3) applies the six-check chain
  from `principles.md`, reads `_performance.md` (sparse on first runs),
  reads AUTONOMY.md to know its ceiling.
- Reviewer decides per AUTONOMY.md `bounded_autonomous` carve-out:
  - **Approve + reversible + within ceiling** → fires `ExecuteProposal`
    → `trading-execute` task → `platform_trading_submit_order` → Alpaca
    paper fill.
  - **Reject** → entry written to `decisions.md`, proposal closed.
  - **Defer to human** (when capital-EV is uncertain — e.g., thin track
    record on first cycles) → routed to operator queue.
- Subsequent operator chat-initiations read richer substrate. After the
  first paper fills land + reconciler writes `_performance.md`, the next
  cycle's Reviewer has real expectancy data to reason against.

**Operator role during Phase B**: observe in the cockpit, log friction to
`docs/alpha/observations/{date}-{topic}.md`. Don't intervene unless
AUTONOMY.md needs revision or something is structurally broken (proposals
stuck, dispatch path failing, reconciler not writing).

**Verification — the loop has closed when:**

1. ✅ At least one chat-initiated `signal-evaluation` cycle has emitted
   one or more proposals with signal attribution.
2. ✅ AI Reviewer has dispatched on each proposal — entry in
   `decisions.md` shows reasoning + verdict + occupant-class signature.
3. ✅ At least one approved + reversible + paper proposal has fired
   `trading-execute` → `platform_trading_submit_order` → Alpaca paper
   fill confirmed.
4. ✅ `back-office-outcome-reconciliation` invocation has written the
   trade outcome to `/workspace/context/portfolio/_performance.md`
   (chat-initiated by operator-on-behalf, or reactive on fill event).
5. ✅ Next-cycle `signal-evaluation` reads the richer `_performance.md`
   — signal expectancy now has +1 datapoint per fired signal. The
   recursive accumulation per Axiom 7 is structurally observable.

The loop closing is the validation. Failures along the way are dogfooding
observations (per ALPHA-1-PLAYBOOK §7) and become ADR seed candidates.

## What this runbook does NOT solve

- **Live trading transition.** This runbook stops at paper. Phase 2 (Live Float per the alpha-trader README) is its own milestone with its own ratification (Reviewer-approved phase flip + AUTONOMY.md update + initial live capital).
- **Calibration of AI Reviewer.** kvk fills the Reviewer seat manually throughout this runbook. AI Reviewer (ADR-194 v2 Phase 3) requires calibration data that this runbook generates, not the other way around.
- **Multi-strategy arbitration.** If kvk runs alpha-prediction or alpha-defi later, multi-program coordination is its own concern — beyond this runbook.

## Observations expected (and where to log them)

Bootstrapping always surfaces gaps. Where the framework needs work, observations land at `docs/alpha/observations/{date}-{topic}.md` per ALPHA-1-PLAYBOOK §7. The bootstrap is a discovery vehicle as much as a validation vehicle:

- **Wiring gaps.** ADR-187 §"Gap to wire" notes `get_fundamentals()` exists in `alpaca_client.py:718` but isn't exposed as a tool. If signal definitions in Step 3 reference fundamentals, this gap surfaces immediately. Log it; ADR or 30-min fix per the thesis.
- **Prompt friction.** YARNNN's authoring conversation in Steps 2-4 may surface that the activation overlay (ADR-226 §3) needs stronger trader-specific framing. Log it; ADR-186 prompt profile extension.
- **Substrate friction.** Per-instrument folder conventions, `_signals.md` synthesis schema, `_universe.md` curation — all surface in Step 3-5 use. Log gaps; bundle MANIFEST or directory-registry refinements.
- **Reviewer seat friction.** kvk filling the seat manually surfaces what the AI Reviewer's calibration needs. Log it; ADR-194 v2 Phase 3 calibration data.
- **Compositor friction.** ADR-225 Phase 2 ships placeholder visuals for `PerformanceSnapshot` / `PositionsTable` / `RiskBudgetGauge` / `TradingProposalQueue`. Real use will surface what they should actually render. Log it; library component evolution (additive, no ADR needed unless contract changes).

The friction is the point. The bootstrap's value is partly the loop closing, and partly the observation log it generates.

## Status tracking

| Step | Status | Notes |
|---|---|---|
| Step 1 — Verify activation state | Not started | Run after ADR-226 implementation lands |
| Step 2 — Author MANDATE.md | Not started | Persona-canonical source ready |
| Step 3 — Author `_operator_profile.md` | Not started | kvk's signal definitions to be drafted/imported |
| Step 4 — Tune `principles.md` | Not started | YARNNN-mediated walk |
| Step 5 — Compose first trading-signal task | Not started | Depends on Steps 2-4 |
| Step 6 — Run the loop end-to-end | Not started | The validation moment |

This file updates as bootstrap progresses. When the loop closes, this runbook moves to status: validated and the observations log becomes the source of any follow-on architectural work.
