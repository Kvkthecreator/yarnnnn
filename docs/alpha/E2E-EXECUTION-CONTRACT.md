# E2E Execution Contract — alpha-trader post-ADR-260/261/262 validation

> **Status**: Canonical for the post-real-time-Reviewer-loop E2E run (2026-05-11+). v4 revision folds in ADR-260 (real-time Reviewer loop + three triggers `addressed | reactive | scheduled`), ADR-261 (recurrences-as-prompts: single canonical `/workspace/_recurrences.yaml`, `output_kind` enum dissolved, headless task pipeline dissolved, specialists as `DispatchSpecialist` sub-LLM calls), ADR-262 (output topology via CONVENTIONS.md + operator-authored specs at `/workspace/specs/`), ADR-264 (mechanical-mirror recurrences via `@primitive: SyncPlatformState` deterministic Python executors), ADR-259 (Chat surface renamed Feed), ADR-258 revised (Reviewer as personified chat-mode operator with `REVIEWER_PRIMITIVES` curated subset + per-action narration), ADR-254 (file-format discipline — `.yaml` for machine-parsed, `.md` for prose).
> **Scope**: alpha-trader workspace (`user_id=2be30ac5-b3cf-46b1-aeb8-af39cd351af4`), paper Alpaca. Note: alpha-trader-2 (`stat-arb` persona, kvk-as-operator) is now the recommended dogfooding persona post-ADR-230.
> **Grounded in**: `ALPHA-1-PLAYBOOK.md` (§3A alpha-trader persona, §2 governance, §6 anti-discretion ladder), ADR-206 (three-layer operator view), ADR-207 (Mandate + Primary Action + capability gate), ADR-231 (task abstraction sunset — recurrence declarations as the work model), ADR-235 (`UpdateContext` dissolution), ADR-228 (cockpit-as-operation), ADR-230 (persona/program registry), ADR-194 v2 (Reviewer seat), ADR-195 v2 (money-truth).
> **Purpose**: explicit alignment on how Claude acts on behalf of the operator during the first E2E exercise after the substrate dissolution wave. Written before the E2E so drift is visible during the run.

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

When `_money_truth.md` shows Signal 3's recent 20-trade expectancy is -0.3R (below the -0.5R guardrail), the Reviewer defers. Claude does NOT argue "maybe it'll come back" or "this setup feels different." Claude notes the flag, defers the proposal, and lets KVK decide at quarterly audit whether to retire Signal 3.

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
│     Reads _operator_profile.md + _risk.md + _money_truth.md + principles.md.   │
│     Executes 6-check capital-EV ladder. Writes judgment_log.md + emits        │
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
│  /work Tracking face Queue            ← proposals awaiting operator decision   │
│  /work task list + outputs           ← pre-market briefs, performance reviews │
│  /review judgment_log.md             ← Reviewer's lineage (ADR-281 §3)        │
│  /workspace/context/trading/_money_truth.md ← per-signal P&L + expectancy     │
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
│  outcome-reconciliation (daily)                                               │
│  Reads Alpaca events, updates _money_truth.md per-signal:                     │
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
- Read `_money_truth.md`, `agent_runs`, `token_usage`, `activity_log`, `judgment_log.md` for audit.
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

## 5. Scope of this E2E (v4 — post-ADR-260/261/262)

**In scope**:

- **Persona activation via canonical harness (ADR-230 + ADR-226).** Claude runs `python -m api.scripts.alpha_ops.activate_persona --persona alpha-trader-2 --dry-run` first, reviews the planned actions, then runs without `--dry-run` (or with `--skip-connect` if Alpaca creds aren't handy). The harness invokes `fork_reference_workspace` per ADR-226 — same primitive a real operator hits via Settings → Workspace (ADR-244). Per the 2026-05-11 ADR-226 amendment the fork calls `materialize_scheduling_index` inline; `verify.py` sees the recurrences in the `tasks` index immediately. Observation: does the fork land the bundle's `_recurrences.yaml` + spec library + `_shared/*` + `trading/*` files? Does verify.py report 28/29 (or 29/29 with Alpaca connected)?
- **Mandate authoring as the gateway turn (ADR-207 + ADR-235).** YARNNN's first turn elicits the Primary Action + success criteria + boundary conditions. Claude pastes the canonical mandate from `docs/alpha/personas/alpha-trader-2/overrides/context/_shared/MANDATE.md` (or authors fresh via chat); YARNNN routes operator-shared substrate writes through `WriteFile(scope="workspace", path="context/_shared/MANDATE.md", content=...)` per ADR-235 D1.b. Observation: does YARNNN lead with Mandate (not Identity)? Does the write produce an authored revision attributed to `operator` per ADR-209?
- **Mandate hard-gate verification.** Any `Schedule(action="create")` attempt BEFORE the mandate is authored must return `error="mandate_required"`. Claude intentionally tries to create a recurrence pre-mandate once to confirm the gate fires, then authors mandate. (Note: since the bundle's `_recurrences.yaml` is forked at activation, the operator typically doesn't *create* new recurrences in normal flow — verification of the gate is exercised by trying to add a *new* one, e.g. `Schedule(action="create", slug="test-gate")`.)
- **Derivation report verification (ADR-207 P5).** After Mandate is authored, Claude reads `/workspace/memory/task_derivation.md` and confirms it lists loop-role coverage. (Doc name preserved post-ADR-231; content reflects current canon.)
- **Authored intent substrate.** `_operator_profile.md` (universe + signal definitions), `_risk.md` (position-sizing + risk parameters), `principles.md` (Reviewer rules) exist with persona-consistent content. The bundle's templates seeded the prompts; operator content overwrites them via `WriteFile(scope="workspace")` or `InferContext`. The bundle's `_universe.yaml` (ADR-254 D4 operator-declared ticker list) is also operator-tuned.
- **Bundle recurrence inventory (ADR-261/262).** Per [ALPHA-1-PLAYBOOK §3A.5](./ALPHA-1-PLAYBOOK.md#3a5-recurrence-set), the bundle ships 14 recurrences in single canonical `/workspace/_recurrences.yaml`. Verify post-fork: all 14 present in workspace_files at that path, all 14 reflected in the `tasks` scheduling index with `declaration_path='/workspace/_recurrences.yaml'`, all `paused=false` and `status='active'`. No per-shape `_spec.yaml` / `_action.yaml` / `_recurring.yaml` files; no `/workspace/_shared/back-office.yaml`; no `output_kind` enum field. The three mechanical mirrors (`track-account`, `track-orders`, `track-positions` per ADR-264) carry `mode: mechanical` and `@primitive: SyncPlatformState` directives; the other 11 carry `mode: judgment`.
- **Reviewer real-time loop (ADR-260 + ADR-256).** Verify the Reviewer's unified `invoke_reviewer(trigger, context)` entry point fires correctly across the three trigger shapes (`addressed | reactive | scheduled`). Specifically: chat-addressed turn elicits a `ReviewerOutput` with `verdict + reasoning + confidence`; proposal-reactive trigger (signal fire → `trade-proposal` → `handle_propose_action`) routes through `services/review_proposal_dispatch.py` and writes an attributed `--- decision ---` entry to `/workspace/review/judgment_log.md` per ADR-281 §3 + ADR-209; scheduled-trigger (morning-reflection cron) writes pattern observations to `/workspace/review/handoffs.md`. Per ADR-258 revised, the Reviewer calls `CHAT_PRIMITIVES` directly via `REVIEWER_PRIMITIVES` subset (16 tools) — verify no parallel `_dispatch_tool_call` machinery surfaces.
- **Sub-LLM specialist dispatch (ADR-261 D7 + ADR-176).** Verify production-role specialists (researcher/analyst/writer/tracker/designer/reporting per ADR-176) materialize as focused-prompt `DispatchSpecialist` calls invoked from the Reviewer's loop — not as separate Layer-2 task-pipeline executions. The headless task pipeline is dissolved per ADR-261. Specialist agent rows still lazy-create on first dispatch per ADR-205.
- **Mechanical mirror executors (ADR-264).** Verify `track-account`, `track-orders`, `track-positions` fire as zero-LLM-cost deterministic Python via the `@primitive: SyncPlatformState` directive in the prompt. Output files land at `/workspace/context/portfolio/{account,orders,positions}.yaml` per ADR-254 D5 (machine-parsed `.yaml`, not `.md`). Observation: does the scheduler dispatch them inline without invoking the LLM tier?
- **Capability gating (ADR-261 + ADR-258 evolution).** Per ADR-261 D5 the `required_capabilities` field on recurrence declarations dissolved with the rest of the per-shape schema. Capability gating now happens at prompt-level (the recurrence's `prompt` field encodes what platforms it expects to be connected) + dispatch-time via `services/agent_creation.py::ensure_infrastructure_agent`. Observation: does a `track-universe` invocation against a workspace without `platform_connections.status='active'` for Alpaca degrade gracefully (Reviewer notes the gap in its verdict) rather than crashing?
- **One full cycle of track → evaluate → (attempted) propose → Review → Queue.** Confirm the **chat-initiated path** (per ADR-205 chat-first triggering) fires when Claude addresses `@yarnnn — trigger track-universe now`. Confirm the path is real-time and synchronous per ADR-260 — operator sees the Reviewer's narration mid-loop, not as a post-hoc lump per ADR-258 revised's per-action narration commit.
- **Cockpit four-face rendering (ADR-228).** Read `/work` cockpit and verify the four faces render against operator substrate: **Mandate** (reads `_shared/MANDATE.md` + `_shared/AUTONOMY.md`), **Money truth** (substrate fallback to `_money_truth.md` if Alpaca live binding deferred), **Performance** (mandate-attributed performance + `judgment_log.md` calibration — decision + material-outcome entries per ADR-281 §3), **Tracking** (proposal queue + recurrence health).
- **Feed surface naming (ADR-259).** Per ADR-259 the chat surface is now `/feed`. Verify the tab label "Feed" renders in the `ToggleBar` (5 segments: `Chat`-renamed-Feed / Work / Schedule / Agents / Files), URL `/chat` redirects to `/feed`, and the feed surface routes through `routes/feed.py` (renamed from `routes/chat.py`).
- **Standing intent substrate + OCCUPANT runtime-truth alignment (ADR-284).** Per ADR-284 the Reviewer's forward-looking judgment now has a substrate home at `/workspace/review/standing_intent.md` (kernel-universal `reviewer-workbench` role per ADR-281 §3), and OCCUPANT.md is runtime-truth-aligned (populated by `services.programs.fork_reference_workspace` via `_populate_occupant_for_runtime` with the actual seat occupant — `ai:reviewer-sonnet-v8` for current alpha state, not the pre-ADR-284 `occupant_class: human` template default). Verification: (a) `verify.py --persona alpha-trader-2` `occupant_attribution` invariant passes (OCCUPANT.md frontmatter declares `occupant_class: ai` + `occupant: ai:reviewer-sonnet-*`); (b) the Reviewer's wake envelope renders `## OCCUPANT.md — Your current seat` + `## standing_intent.md — What you were watching for last cycle` sections (or empty-state hint on first cycle); (c) after the first judgment-mode recurrence fires post-activation, `/workspace/review/standing_intent.md` exists with `authored_by="reviewer:ai:reviewer-sonnet-*"`; (d) on no-fire cycles, the file is still updated (substrate counterpart to no-fire judgment per ADR-284 D2 + bundle principles.md "Default posture: action"). The structural answer to "what does the Reviewer plan to do?" — an operator-readable substrate file naming what's being watched for.

**Out of scope for this E2E** (future runs):

- Live trade approval and execution. Paper is the substrate.
- Quarterly signal audit simulation.
- Multi-day reconciliation cycle (needs time to accumulate outcomes).
- Automated Reviewer auto-execution beyond `auto_approve_below_cents` threshold (per ADR-194 v2 Phase 3 + ADR-253 D1; alpha defaults to defer-everything until `_money_truth.md` accumulates).
- alpha-commerce persona (parked per SCOPE.md; see [docs/alpha/parked/alpha-commerce-persona-spec.md](./parked/alpha-commerce-persona-spec.md)).

---

## 6. Success criteria

The E2E succeeds if:

- **Activation harness lands clean.** `activate_persona.py --persona alpha-trader-2` completes without error; bundle fork writes the expected 27-file set (14 _recurrences.yaml entries + 5 specs + _shared/* + trading/* + review/*). Per the 2026-05-11 ADR-226 amendment, post-fork the `tasks` index shows 14 rows with `declaration_path='/workspace/_recurrences.yaml'` immediately — no scheduler-tick wait.
- **Mandate (ADR-207 + ADR-235)** — `/workspace/context/_shared/MANDATE.md` contains the operator-authored content after the gateway turn, written via `WriteFile(scope="workspace", ...)` and recorded as an authored revision per ADR-209 (`authored_by="operator"`). YARNNN's first turn leads with Mandate elicitation, not identity or soft onboarding.
- **Mandate hard-gate fires** — any pre-mandate `Schedule(action="create")` attempt returns `error="mandate_required"` with the operator-facing message pointing to `WriteFile(scope="workspace", path="context/_shared/MANDATE.md", ...)`.
- **Derivation report (ADR-207 P5)** — `/workspace/memory/task_derivation.md` auto-generates on mandate write, reflects current loop-role coverage.
- **Intent artifacts** — `_operator_profile.md`, `_risk.md`, `principles.md` exist with persona-consistent content. Bundle templates seeded the prompts; operator content overwrites them. `_universe.yaml` is operator-tuned ticker list.
- **Bundle recurrence inventory (ADR-261/262)** — `verify.py --persona alpha-trader-2` reports 14/14 `scaffolded_recurrences` checks pass against the canonical bundle slug set (`narrative-digest, outcome-reconciliation, proposal-cleanup, morning-calibration, morning-reflection, pre-market-brief, signal-evaluation, track-universe, track-account, track-orders, track-positions, trade-proposal, weekly-performance-review, quarterly-signal-audit`). All 14 declaration_paths equal `/workspace/_recurrences.yaml`.
- **Reviewer real-time loop (ADR-260 + ADR-256)** — `invoke_reviewer` fires correctly for at least the `addressed` trigger (chat) and the `reactive` trigger (post-proposal). Decisions land in `/workspace/review/judgment_log.md` as `--- decision ---` entries with `authored_by="reviewer:<occupant>"` per ADR-281 §3 + ADR-209; material outcomes land as `--- material-outcome ---` entries gated by `render_lineage_entry_if_material` (the 5-condition material-outcome gate). Per-action narration via `services/reviewer_chat_surfacing.py::narrate_reviewer_action` produces a System-Agent bubble in the feed for each consequential successful Reviewer action.
- **Sub-LLM specialist dispatch (ADR-261 D7)** — at least one Reviewer-loop turn invokes `DispatchSpecialist` against a production-role specialist (e.g. researcher) and integrates the focused-prompt output. No Layer-2 task-pipeline execution observed (it's dissolved per ADR-261).
- **Mechanical mirror executors (ADR-264)** — at least one of `track-account` / `track-orders` / `track-positions` fires during market hours via the `@primitive: SyncPlatformState` directive at zero LLM cost. Output files land at `/workspace/context/portfolio/{account,orders,positions}.yaml`.
- **Pipeline execution** — `track-universe` + `signal-evaluation` run via the invocation dispatcher (`services/invocation_dispatcher.py`) without errors. Outputs land at the operator-declared CONVENTIONS.md slug-templated paths (`/workspace/context/trading/{ticker}.yaml` per ADR-254 D5, `/workspace/context/trading/signals/{slug}.yaml`).
- **Cockpit rendering (ADR-228)** — `/work` cockpit renders four faces against substrate. AUTONOMY chip (ADR-238) surfaces in the feed composer header.
- **YARNNN prompt** — uses operation-first vocabulary on the elicitation turn. Mandate-first posture visible in first response. The five-profile prompt registry (ADR-233 Phase 1) routes the workspace conversation through `prompts/chat/workspace.py`.
- **Feed surface (ADR-259)** — tab label "Feed", URL `/feed`, backend route `/api/feed/*`. Cross-pollution from old `chat` vocabulary observable only in the runtime characteristic (Anthropic API call shape; `chat` permission mode in `CHAT_PRIMITIVES` registry) — not in surface names or operator-facing copy.
- **OCCUPANT runtime-truth alignment (ADR-284 D3)** — `verify.py --persona alpha-trader-2` `occupant_attribution` invariant passes: `/workspace/review/OCCUPANT.md` frontmatter declares `occupant_class: ai` + `occupant: ai:reviewer-sonnet-*` (post-bundle-fork, written by `_populate_occupant_for_runtime` with `authored_by="system:occupant-fork"` per ADR-209). A failure here indicates either the bundle-fork helper regressed or the live workspace pre-dates the ADR-284 Phase 1 ship (needs re-fork).
- **Standing intent substrate (ADR-284 D2 + D6)** — after the first judgment-mode recurrence fires post-activation (typically `signal-evaluation` at market open + 15min, or any addressed Reviewer turn), `/workspace/review/standing_intent.md` exists with frontmatter (`as_of`, `horizon`, `occupant`) + three section headings (*What I'm watching for* / *What would change my next move* / *Open questions to the operator*) + `authored_by="reviewer:ai:reviewer-sonnet-*"`. On a subsequent no-fire judgment cycle, the file is updated (not absent) — substrate counterpart to no-fire judgment per ADR-284 D2 + bundle principles.md "Default posture: action". Specificity check: entries cite signal/ticker/threshold/distance, not generic "watching for opportunities" noise.
- **Reviewer wake envelope renders standing-intent sections (ADR-284 D4)** — Reviewer prompt traces show `## OCCUPANT.md — Your current seat` + `## standing_intent.md — What you were watching for last cycle` sections (or the empty-state hint `(empty — first cycle, author it as part of this judgment)` on the first cycle). The persona prompt section "Your standing intent has a substrate home" composes with the envelope rendering so the contract is load-bearing.
- **Diagnostic surface** — `/settings/system` renders cleanly (likely empty content; the surface itself should respond).
- **Observations** — at least 3 captured covering real friction. Absence of friction itself is a signal worth noting.

The E2E exposes a bug if any success criterion fails — that's what we're here to find.

---

## 7. Stop-and-think triggers during execution

When any of the following occur, pause and deliberate before proceeding:

- YARNNN's first response is soft-onboarding ("Tell me about yourself") instead of operation-elicitation. → Observation: prompt change didn't take, investigate the ADR-233 five-profile dispatch in `prompts/chat/workspace.py`.
- The compact index renders without the three ADR-206 section headers. → Observation: compact index rewrite didn't propagate to live path.
- A path-not-found error when reading `_shared/IDENTITY.md` or similar. → Observation: ADR-226 fork-time path tier-frontmatter strip missed a file; investigate `workspace_init._fork_reference_workspace`.
- `CreateRecurrenceModal` submission fails. → Observation: `RecurrenceCreate` type shape or `/api/recurrences` POST contract mismatch (ADR-231 Phase 3.8 rename).
- A recurrence dispatches without the production roles it names being lazy-materialized. → Observation: `ensure_infrastructure_agent` call site missed. (Under LAYER-MAPPING.md / ADR-212, "production role" replaces the retired entity term "Specialist"; per-workspace production-role rows in the `agents` table still carry `class="specialist"` as a data-compatibility enum slug.)
- A dispatched agent uses WebSearch instead of the `platform_trading_*` tools when its recurrence declares `read_trading`. → Observation: the ADR-227 fix regressed; check `task_required_capabilities` plumbing through `get_headless_tools_for_agent`.
- An attempt to call the deleted `UpdateContext` primitive surfaces in chat traces. → Observation: ADR-235 dissolution incomplete; the prompts/chat profile or a tool-doc still references the dead primitive.
- OCCUPANT.md declares `occupant_class: human` on a workspace where the AI is actually running the seat (every judgment-mode `execution_events` row attributed to `reviewer:ai:reviewer-sonnet-*`). → Observation: ADR-284 Phase 1 `_populate_occupant_for_runtime` did not fire at bundle-fork time. Either the workspace pre-dates Phase 1 ship and needs re-fork, or the helper raised silently. Check `programs.py::fork_reference_workspace` `[FORK]` log lines around OCCUPANT write.
- Reviewer stand-down on a judgment-mode recurrence cycle WITHOUT a `/workspace/review/standing_intent.md` revision in `workspace_file_versions`. → Observation: ADR-284 Phase 2 contract not landing. The persona prompt instructs the write; the bundle's recurrence prompt instructs the write; principles.md declares the contract — but the Reviewer didn't honor it. Check prompt traces for the standing-intent section presence + the per-recurrence "AND update standing_intent.md" clause. The failure mode the ADR-284 work is structurally closing is exactly this — observation rather than judgment.
- `standing_intent.md` exists but content is generic ("watching for opportunities", "monitoring the market") rather than specific (cites signal/ticker/threshold/distance). → Observation: Phase 2 bundle IDENTITY.md "Specifics matter" clause not landing in Reviewer behavior. The substrate exists but isn't carrying forward-looking judgment in a form the operator can audit.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-22 | v1 — Initial contract. Written pre-E2E to freeze Claude's posture + loop framing + acting-on-behalf rules before the ADR-205/206 post-purge validation run. |
| 2026-04-22 | v2 — ADR-207 folded in. Added Mandate-first gateway turn to §5 scope + §6 success criteria. Added capability-gate verification (ADR-207 P3) + self-declaration task authoring (ADR-207 P4b) + derivation report verification (ADR-207 P5). Canonical mandate artifacts: `docs/alpha/personas/alpha-trader/MANDATE.md`, `docs/alpha/personas/alpha-commerce/MANDATE.md`. |
| 2026-04-29 | v3 — Post-refactor-wave realignment. Folds in ADR-231 (task abstraction sunset → recurrence declarations + natural-home substrate + `/api/recurrences` URL flip + invocation dispatcher), ADR-235 (`UpdateContext` dissolution → `WriteFile(scope="workspace")` for operator-shared writes, `InferContext`/`InferWorkspace` for inference, `ManageRecurrence` for lifecycle), ADR-230 (canonical activation harness `activate_persona.py`), ADR-228 (cockpit four-face reshape replaces ADR-198 v2 BriefingStrip framing), ADR-227 (capability-gated tool augmentation — fixes the 2026-04-28 Tracker WebSearch defect), ADR-226 (reference-workspace activation flow), ADR-238 (AUTONOMY chip), ADR-239 (cockpit decisions parser unification), ADR-233 (five-profile prompt registry at `prompts/{chat,headless}/`). Renames `CreateTaskModal` → `CreateRecurrenceModal`, removes `/api/tasks/types` reference. Recommends `alpha-trader-2` as the dogfooding persona (kvk-as-operator stat-arb). |
| 2026-05-11 | v4 — Post-real-time-Reviewer-loop realignment (Bucket C of the alpha-doc audit). Folds in ADR-260 (real-time Reviewer loop, three triggers `addressed | reactive | scheduled`, no mid-loop trigger), ADR-261 (recurrences-as-prompts: per-shape declaration files dissolved into single `/workspace/_recurrences.yaml`; `output_kind` enum dissolved; `ManageRecurrence` → `Schedule`; headless task pipeline dissolved; specialists become `DispatchSpecialist` sub-LLM calls), ADR-262 (output topology via CONVENTIONS.md + operator-authored specs at `/workspace/specs/`), ADR-264 (mechanical-mirror recurrences `track-account` / `track-orders` / `track-positions` via `@primitive: SyncPlatformState` deterministic Python executors, zero LLM cost), ADR-259 (Chat surface renamed Feed; `/chat` → `/feed`; `routes/feed.py`), ADR-258 revised (Reviewer as personified chat-mode operator using `REVIEWER_PRIMITIVES` 16-tool curated subset, per-action narration via `services/reviewer_chat_surfacing.py`), ADR-254 (file-format discipline: `.yaml` for machine-parsed structured config, `.md` for LLM-readable prose, `_universe.yaml` + `_autonomy.yaml` + `_principles.yaml` introduced). §5 + §6 rewritten to reflect bundle-ships-14-recurrences-via-fork model (operator no longer composes the recurrence set via chat). Activation-harness materialize-after-fork wiring shipped 2026-05-11 per ADR-226 amendment. Companion alpha-doc cleanup: PLAYBOOK §3A.5/§3A.5b unified into a single canonical 14-recurrence table; PLAYBOOK §3B alpha-commerce lifted to `docs/alpha/parked/`; BOOTSTRAP.md archived to `docs/alpha/parked/` (its workflow distilled to harness commands in OPERATOR-HARNESS.md). |
