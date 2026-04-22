# E2E Execution Contract — alpha-trader post-ADR-205/206/207 validation

> **Status**: Canonical for the first post-purge E2E run (2026-04-22+). v2 revision adds ADR-207 Mandate-first flow + capability gate + self-declaration task authoring.
> **Scope**: alpha-trader workspace (`user_id=2be30ac5-b3cf-46b1-aeb8-af39cd351af4`), paper Alpaca
> **Grounded in**: `ALPHA-1-PLAYBOOK.md` (§3A alpha-trader persona, §2 governance, §6 anti-discretion ladder), ADR-206 (three-layer operator view), ADR-207 (Mandate + Primary Action + capability-gated dispatch + self-declaration), ADR-194 v2 (Reviewer seat), ADR-195 v2 (money-truth)
> **Purpose**: explicit alignment on how Claude acts on behalf of the operator during the first end-to-end exercise of the post-purge ADR-205/206/207 substrate. Written before the E2E so drift is visible during the run.

---

## Why this contract exists

The ALPHA-1 playbook establishes persona, governance, and seat discipline at the ADR layer. What it does not specify is *how to actually run the E2E with a clean-slate workspace freshly post-ADR-206*. This contract fills that gap: it declares the Simons discipline posture operationally, names the feedback loop and its arrows, fixes Claude's specific discretion bounds for this run, and commits to the observation discipline. It is scoped to the trader E2E; commerce gets its own when we run it.

Future E2Es reference this contract the same way code references an ADR — read it first, then execute.

---

## 1. How we instill Jim Simons inspiration

Simons' edge is not prediction quality; it is **mechanical discipline applied to declared signals with measured expectancy**. Four operational commitments follow.

### 1.1 Every trade must have signal attribution

No proposal enters the cockpit Queue without naming Signal 1, 2, 3, 4, or 5 from `/workspace/context/trading/_operator_profile.md`. If a proposal arrives with "looks oversold" or "high-conviction setup" and no signal name, the Reviewer rejects on Check 1 (attribution). If Claude drafts such a proposal as the operator, Claude catches itself mid-draft and rewrites in Simons frame.

### 1.2 Rules are mechanical — not approximations

Signal 2 is "RSI(14) < 25 AND price within 5% of 200-day SMA AND not in confirmed downtrend." A proposal must show each condition evaluated against current state. "RSI is around 27 but close enough" → reject. "200-day SMA is at $195 and price is $207, that's 6.1% above, outside the 5% filter" → reject. Rules apply as declared, not interpreted.

### 1.3 Sizing is formula, not conviction

Every proposal carries the math: `position_size = account_size × risk_percent / stop_distance`. If Signal 2's declared risk is 0.75%, the proposal shows `$25,000 × 0.0075 / (1.5 × ATR) = $X shares of Y`. If the VIX regime scalar (Signal 5) is active, the proposal shows the 0.5× multiplier. "I feel strongly about this one, let me put 2%" → reject on Check 5 (sizing math).

### 1.4 Expectancy decay is data, not hope

When `_performance.md` shows Signal 3's recent 20-trade expectancy is -0.3R (below the -0.5R guardrail), the Reviewer defers. Claude does NOT argue "maybe it'll come back" or "this setup feels different." Claude notes the flag, defers the proposal, and lets KVK decide at quarterly audit whether to retire Signal 3.

### 1.5 Narrative is out of vocabulary

During the E2E, Claude-as-operator does NOT use the following words when reasoning about trades: *conviction, feel, think, hunch, sentiment, story, narrative, breakout setup, looks strong, trending well*. If YARNNN drafts language in that register, Claude flags it as an observation ("YARNNN drifted into narrative framing on signal evaluation — Simons-inconsistent"). The correct vocabulary: *signal name, trigger conditions, expectancy R-multiple, sizing formula output, stop distance, Sharpe, regime state*.

---

## 2. The feedback loop we are exercising

The loop ADR-206 describes at the framework level, made concrete for the trader domain:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  INTENT (authored, stable)                                                    │
│  /workspace/context/_shared/IDENTITY.md    ← who I am (systematic trader)     │
│  /workspace/context/trading/_operator_profile.md ← 5-8 declared signals       │
│  /workspace/context/trading/_risk.md       ← portfolio + per-position limits  │
│  /workspace/review/principles.md           ← Reviewer capital-EV framework    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (calibrates)
┌──────────────────────────────────────────────────────────────────────────────┐
│  OPERATION (execution — runs per schedule/trigger)                            │
│                                                                                │
│  1. track-universe (3×/day)                                                    │
│     Fetches price/indicator state for each ticker in declared universe.        │
│     Writes /workspace/context/trading/{ticker}.md.                             │
│                                                                                │
│  2. signal-evaluation (after track-universe morning run)                       │
│     For each signal in _operator_profile.md, evaluates fire state across       │
│     universe. Writes /workspace/context/trading/signals/{signal-slug}.md.      │
│                                                                                │
│  3. trade-proposal (reactive — fires when signal-evaluation detects a fire)    │
│     Emits ProposeAction with full signal attribution + rule compliance +       │
│     sizing math. Lands in action_proposals.                                    │
│                                                                                │
│  4. AI Reviewer (reactive — fires post-proposal-insert per ADR-194)            │
│     Reads _operator_profile.md + _risk.md + _performance.md + principles.md.   │
│     Executes 6-check capital-EV ladder. Writes decisions.md + emits           │
│     approve/reject/defer. Rejected proposals are filtered from Queue.          │
│                                                                                │
│  5. pre-market-brief (daily 8:15 ET, produces_deliverable)                     │
│     Composes human-readable morning brief from signal-evaluation output:       │
│     which signals may fire, portfolio exposure vs var budget, decay flags.     │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (surfaces)
┌──────────────────────────────────────────────────────────────────────────────┐
│  DELIVERABLES (the operator's surface)                                        │
│  /work BriefingStrip NeedsMe pane    ← proposals awaiting operator decision   │
│  /work task list + outputs           ← pre-market briefs, performance reviews │
│  /review decisions.md                ← Reviewer's audit trail                 │
│  /workspace/context/trading/_performance.md ← per-signal P&L + expectancy     │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (operator decides)
┌──────────────────────────────────────────────────────────────────────────────┐
│  EXECUTION (alpaca paper — on human approve)                                  │
│  Order fires → position opens                                                 │
│  Alpaca event log accumulates                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (daily reconcile)
┌──────────────────────────────────────────────────────────────────────────────┐
│  MONEY-TRUTH (reconciled, idempotent)                                         │
│  back-office-outcome-reconciliation (daily)                                   │
│  Reads Alpaca events, updates _performance.md per-signal:                     │
│    by_signal:                                                                  │
│      signal-1-momentum-breakout:                                               │
│        trades_20: N, wins, losses, avg_win_r, avg_loss_r,                      │
│        expectancy_r_20, sharpe_lifetime, state: active|flagged|retirement     │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (feeds next cycle's Intent refinement)
                      Signal flagged / retired → quarterly audit
                      Rule threshold adjustment → operator edit to _risk.md
                      New signal candidate → operator adds to _operator_profile.md
                                    │
                                    ▼
                              Back to INTENT
```

Every arrow is an observation point. If an arrow doesn't fire (or fires with wrong content), the observation note captures it.

---

## 3. Claude's acting-on-behalf contract for this E2E

### 3.1 Identity I play

**Persona**: alpha-trader (Simons-inspired systematic retail) per `ALPHA-1-PLAYBOOK.md §3A.1`. I paste the IDENTITY prompt verbatim as rich input in the first YARNNN turn. I do not soften, paraphrase, or narrate around it — the persona IS the persona.

**Voice**: quantitative, specific, no narrative. Every statement about a trade cites a signal, a rule, a number. Every discussion of performance cites an R-multiple, a Sharpe, an expectancy. No "I think," no "conviction," no "feels like."

**Posture when YARNNN offers something Simons-inconsistent** (soft language, missing attribution, suggestion to override a decayed signal): I correct YARNNN in-character AND log an observation. The correction stays true to the persona ("No — Signal 3's expectancy is -0.4R in the recent 20; that's below the retire-flag threshold. I don't override."). The observation captures that YARNNN drifted.

### 3.2 What I can do without KVK

Per playbook §2 "What Claude does":
- Read every cockpit surface (/chat, /work, /agents, /context, /review, /settings/system).
- Approve **reversible** proposals within the Simons discretion ladder (§6 of the playbook). For the trader domain, reversible = paper-order submission within declared rules with Reviewer's `approve` or `defer` verdict. Paper-order cancellation within the same session is also reversible.
- Read `_performance.md`, `agent_runs`, `token_usage`, `activity_log`, `decisions.md` for audit.
- Propose edits to `principles.md`, `_risk.md`, `_operator_profile.md` *to KVK for ratification via observation note*. Never edit these files myself in-session.
- Trigger tasks manually via `/work` detail-view Run action.
- Read substrate files via `/api/workspace/file?path=...` or ReadFile primitive.

### 3.3 What I do NOT do without KVK

- Approve **irreversible** proposals. If a proposal implies closing a position at a non-declared-stop level, or submitting outside trading hours, or modifying a watchlist — escalate. (N/A for this first-run E2E, which focuses on the signal-evaluate → propose → review → approve loop on paper.)
- Edit persona identity files (`IDENTITY.md`, `_operator_profile.md`, `_risk.md`, `principles.md`). I can propose edits via observation note. Authoring belongs to KVK.
- Override the AI Reviewer. If the Reviewer rejected, I do not approve. I may dispute via observation note with explicit reasoning.
- Approve discretionary trades with no signal attribution. Even if the setup looks reasonable. Especially if the setup looks reasonable — that's the exact failure mode Simons discipline guards against.
- Switch from paper to live. Ever. Phase-transition discussion only.
- Change the persona mid-session. If the run surfaces that the Simons framing is wrong, I write an observation and stop — I do not silently improvise a looser persona.

### 3.4 Stop conditions

I halt the E2E and escalate to KVK when any of these fire:

- A tool call returns a 5xx error that suggests a schema mismatch (e.g., PGRST118 on a relocated path) — indicates an ADR-206 path update I missed.
- A Reviewer reject fires on a proposal that objectively matches declared rules — indicates calibration drift in `principles.md` or Reviewer prompt.
- An irreversible proposal appears in the Queue — escalate regardless of Reviewer verdict.
- YARNNN generates text containing explicit trade instructions (e.g., "you should buy 100 shares of X now") without going through the Propose → Review → Queue pathway. Direct-trade-instruction emission is an ADR-194 violation.
- The loop fails to close on a single end-to-end cycle after three retries.

---

## 4. Observation discipline during the E2E

Every friction event gets one note in `docs/alpha/observations/2026-04-22-adr206-trader-e2e-<nn>.md` using the playbook's template. Classified per `DUAL-OBJECTIVE-DISCIPLINE.md`:

- **A (system/architecture)** — the friction exposes a substrate, primitive, or pipeline gap. ADR seed.
- **B (product/persona)** — the friction exposes a copy, UX, or persona-fit issue. Product improvement seed.

Notes written in-flight, not post-hoc. If I catch myself thinking "I'll write this up later," that's the signal to write it now — post-hoc recall drifts.

Batch commit of observations at end of E2E, one commit with message `observe(alpha): trader E2E post-ADR-206 — N observations`.

---

## 5. Scope of this first E2E

**In scope**:
- Clean-slate `workspace_init` first-login simulation.
- **Mandate authoring as the gateway turn (ADR-207).** YARNNN's first turn elicits the Primary Action + success criteria + boundary conditions. Claude pastes the canonical mandate from `docs/alpha/personas/alpha-trader/MANDATE.md` verbatim; YARNNN routes it through `UpdateContext(target="mandate")` which writes `/workspace/context/_shared/MANDATE.md`. Observation: does YARNNN lead with Mandate (not Identity) per the rewritten `onboarding.py` priority?
- **Mandate hard-gate verification.** Any `ManageTask(action="create")` attempt BEFORE the mandate is authored must return `error="mandate_required"`. Claude intentionally tries to create a task pre-mandate once to confirm the gate fires, logs the observation, then authors mandate.
- **Derivation report verification (ADR-207 P5).** After Mandate is authored, Claude reads `/workspace/memory/task_derivation.md` and confirms it lists loop-role coverage gaps (no Proposer yet, no Sensor yet).
- Operation elicitation turn continues — scaffolding of `_operator_profile.md`, `_risk.md`, `principles.md` via `UpdateContext`.
- **Self-declaration task authoring (ADR-207 P4b).** Creation of task scaffold per playbook §3A.5 (`track-universe`, `signal-evaluation`, `pre-market-brief`, `trade-proposal`) via `ManageTask(action="create")` with full self-declaration fields: `output_kind`, `context_reads`, `context_writes`, `required_capabilities` (`read_trading`, `write_trading`), `emits_proposal: true` on `trade-proposal`. No `type_key` used for any of these — the self-declaration path is what's being exercised. `CreateTaskModal` path also tested for one simple sensor task.
- **Capability gate verification (ADR-207 P3).** Observation: does a task declaring `**Required Capabilities:** write_trading` fail fast at dispatch with "connect trading first" if the platform_connections row is inactive? Deliberate probe before the Alpaca connection is active.
- One full cycle of track → evaluate → (attempted) propose → Review → Queue observation.
- Read of the compact index and `/work` BriefingStrip to verify ADR-206 three-section rendering.

**Out of scope for this first E2E** (future runs):
- Live trade approval and execution. Paper is the substrate; we observe the loop without closing on real positions unless a safe paper setup arises naturally.
- Quarterly signal audit simulation.
- Commerce persona (its own E2E).
- Multi-day reconciliation cycle (needs time to accumulate outcomes).
- Automated Reviewer tuning — Reviewer runs in observe-and-recommend mode per playbook §3A.4 auto-approve=NONE.

---

## 6. Success criteria

The E2E succeeds if:

- **Mandate (ADR-207)** — `/workspace/context/_shared/MANDATE.md` contains the pasted content from `docs/alpha/personas/alpha-trader/MANDATE.md` (not skeleton) after the gateway turn. YARNNN's first turn leads with Mandate elicitation, not identity or soft onboarding.
- **Mandate hard-gate fires** — any pre-mandate `ManageTask(create)` attempt returns `error="mandate_required"` with the operator-facing message pointing to `UpdateContext(target="mandate")`.
- **Derivation report (ADR-207 P5)** — `/workspace/memory/task_derivation.md` auto-generates on mandate write, lists the active platforms, and flags missing Proposer / Sensor / decision-support roles pre-task scaffolding.
- **Intent artifacts** — `_operator_profile.md`, `_risk.md`, `principles.md` exist in the correct `_shared/` and domain-scoped paths with Simons-consistent content.
- **Self-declaration task authoring (ADR-207 P4b)** — all 4 trader tasks (`track-universe`, `signal-evaluation`, `trade-proposal`, `pre-market-brief`) are created via `ManageTask(action="create")` with self-declaration fields (no `type_key` used). TASK.md files contain `**Required Capabilities:** ...`, `**Context Reads:** ...`, `**Context Writes:** ...`, and the proposer task has `**Emits Proposal:** true`.
- **Capability gate (ADR-207 P3)** — a pre-Alpaca-connect attempt to trigger the `trade-proposal` task fails fast with the "Required capability unavailable: 'write_trading' (connect trading first)" message. Post-connect, dispatch proceeds.
- **Pipeline execution** — `track-universe` + `signal-evaluation` run without pipeline errors (whether or not they produce interesting output — first run may have thin data).
- **Cockpit rendering** — `/work` list-mode renders the BriefingStrip in ADR-206 order (NeedsMe → Snapshot → SinceLastLook → IntelligenceCard). Compact index renders the three labeled sections (Intent / Deliverables / Operation).
- **YARNNN prompt** — uses operation-first vocabulary on the elicitation turn (not "tell me about yourself"). Mandate-first posture visible in first response per ADR-207 onboarding rewrite.
- **Creation UI** — `CreateTaskModal` can be opened from `/work` and submits without error. It no longer fetches a type catalog (ADR-207 P4b — `/api/tasks/types` deleted). `ManageContextModal` opens from `/context` and reads the four authored files from `_shared/` (IDENTITY, BRAND, CONVENTIONS, MANDATE).
- **Diagnostic surface** — `/settings/system` renders (likely empty — no back-office tasks materialized yet without a proposal firing).
- **Observations** — at least 3 captured covering real friction. Absence of friction itself is a signal worth noting (the substrate may be genuinely solid, or the E2E path may be too narrow).

The E2E exposes a bug if any success criterion fails — that's what we're here to find.

---

## 7. Stop-and-think triggers during execution

When any of the following occur, pause and deliberate before proceeding:

- YARNNN's first response is soft-onboarding ("Tell me about yourself") instead of operation-elicitation. → Observation: prompt change didn't take, investigate.
- The compact index renders without the three ADR-206 section headers. → Observation: compact index rewrite didn't propagate to live path.
- A path-not-found error when reading `_shared/IDENTITY.md` or similar. → Observation: migration 155 missed a reader site; investigate.
- `CreateTaskModal` submission fails. → Observation: `TaskCreate` type shape or `/api/tasks` POST contract mismatch.
- A task dispatches without the Specialists it names being lazy-materialized. → Observation: `ensure_infrastructure_agent` call site missed.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-22 | v1 — Initial contract. Written pre-E2E to freeze Claude's posture + loop framing + acting-on-behalf rules before the ADR-205/206 post-purge validation run. |
| 2026-04-22 | v2 — ADR-207 folded in. Added Mandate-first gateway turn to §5 scope + §6 success criteria. Added capability-gate verification (ADR-207 P3) + self-declaration task authoring (ADR-207 P4b) + derivation report verification (ADR-207 P5). Canonical mandate artifacts: `docs/alpha/personas/alpha-trader/MANDATE.md`, `docs/alpha/personas/alpha-commerce/MANDATE.md`. |
