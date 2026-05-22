# E2E Execution Contract — alpha-trader + alpha-author post-ADR-298 Phase 3 validation

> **Status**: Canonical for the post-wake-queue-cutover E2E run (2026-05-22+). v6 revision folds in **ADR-298** (single-lane Reviewer execution per workspace via `wake_queue`; two-lane drain paced/live; operator-authored `_pace.yaml` as wake-frequency budget; Schedule primitive pace-gates at declaration time; bundle `minimum_pace` activation gate) and **ADR-297** (surfaces-as-substrate-mirror — atomic kernel surfaces, dock + launcher + viewport panel, compositor emits surfaces[] registry). Carried forward from v5: ADR-296 v2 (wake is event-driven + evaluation-gated, 5 wake sources, FireInvocation removed, substrate-event hooks). v4 chain: ADR-260, ADR-261, ADR-262, ADR-264, ADR-259, ADR-258 revised, ADR-254.
> **Scope**: both archetypes. **alpha-trader** (autonomous-execution archetype; paper Alpaca; recommended dogfooding persona `alpha-trader-2`, `user_id=2abf3f96-118b-4987-9d95-40f2d9be9a18`). **alpha-author** (substrate-continuity archetype; dogfooding personas `yarnnn-author` `0b7a852d-4a67-447d-91d9-2ba1145a60d7`, `netflix-script-author`, `korea-thriller-shorts`). Sequenced: alpha-author validates the substrate-event wake source (faster feedback, single scheduler tick); alpha-trader validates the cron_tick + proposal_arrival path under real RTH cadence.
> **Grounded in**: `ALPHA-1-PLAYBOOK.md` (§3A alpha-trader, §3C alpha-author, §2 governance, §6 anti-discretion ladder), ADR-296 v2 (wake architecture), ADR-206 (three-layer operator view), ADR-207 (Mandate + Primary Action + capability gate), ADR-231 (task abstraction sunset — recurrence declarations as the work model), ADR-235 (`UpdateContext` dissolution), ADR-228 (cockpit-as-operation), ADR-230 (persona/program registry), ADR-194 v2 (Reviewer seat), ADR-195 v2 (money-truth).
> **Purpose**: explicit alignment on how Claude acts on behalf of the operator during the first E2E exercise after the wake refactor. Written before the E2E so drift is visible during the run. Both archetypes ship from the same contract; sequencing is operational (alpha-author first), not architectural.

---

## Why this contract exists

The ALPHA-1 playbook establishes persona, governance, and seat discipline at the ADR layer. What it does not specify is *how to actually run the E2E with a clean-slate workspace freshly post-ADR-206*. This contract fills that gap: it declares the Simons discipline posture operationally, names the feedback loop and its arrows, fixes Claude's specific discretion bounds for this run, and commits to the observation discipline. It is scoped to the trader E2E; commerce gets its own when we run it.

Future E2Es reference this contract the same way code references an ADR — read it first, then execute.

---

## 0. What this contract validates (the one-liner)

The E2E succeeds when behavior in production matches this single-sentence description of the Reviewer:

> **The Reviewer is a full-substrate-authoring persona-bearing judgment seat — filesystem-native, single-lane queue-serialized, wake-fired, paced by operator-declared pace + autonomy, driven by operator-authored mandate.**

This is the canonical formalization per [FOUNDATIONS Derived Principle 21](../architecture/FOUNDATIONS.md). Read this line as the spec. Every success criterion in §6 derives from one of its clauses. If an observed behavior contradicts a clause, that's either a code bug (Hat-A fix lands a system canon change) or a line revision (Hat-B finding seeds a new ADR). Both outcomes are valid; what isn't valid is silently absorbing the contradiction without naming it.

Companion canon: [`ALPHA-1-PLAYBOOK.md` §0](./ALPHA-1-PLAYBOOK.md#0-the-architectural-success-criterion-the-one-liner) carries the clause-to-substrate map.

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

## 2. The feedback loop we are exercising (alpha-trader)

The loop ADR-206 describes at the framework level, made concrete for the trader domain. Post-ADR-296 v2: the wake sources are explicit; the `trade-proposal` recurrence is gone; `signal-evaluation` emits `ProposeAction` inline; the Reviewer wakes on the resulting `proposal_arrival` wake source.

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
│  1. track-universe (3×/day) [wake_source=cron_tick]                            │
│     Fetches price/indicator state for each ticker in declared universe.        │
│     Writes /workspace/context/trading/{ticker}.yaml per ADR-254.               │
│                                                                                │
│  2. signal-evaluation (after track-universe morning run) [wake_source=cron_tick]│
│     For each signal in _operator_profile.md, evaluates fire state across       │
│     universe. Writes /workspace/context/trading/signals/{signal-slug}.yaml.    │
│     When a signal fires: emits ProposeAction INLINE (per ADR-296 v2 — no       │
│     separate trade-proposal recurrence, no FireInvocation chain). Lands in     │
│     action_proposals.                                                          │
│                                                                                │
│  3. AI Reviewer [wake_source=proposal_arrival, funnel_decision=escalate]      │
│     Wakes on proposal-insert via services/wake.py::submit_wake_proposal.       │
│     Reads _operator_profile.md + _risk.md + _money_truth.md + principles.md.   │
│     Executes 6-check capital-EV ladder. Writes judgment_log.md + emits        │
│     approve/reject/defer. Rejected proposals are filtered from Queue.          │
│                                                                                │
│  4. pre-market-brief (daily 8:15 ET, produces_deliverable) [cron_tick]        │
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

## 2b. The substrate-event loop (alpha-author)

The alpha-author archetype exercises the **substrate-event wake source** introduced by ADR-296 v2 D2. This is the loop the alpha-author canary validates ahead of the alpha-trader RTH cycle.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  INTENT (authored, stable)                                                    │
│  /workspace/context/_shared/IDENTITY.md     ← who I am (author persona)       │
│  /workspace/context/authored/_voice.md      ← voice fingerprint               │
│  /workspace/context/authored/_editorial.md  ← editorial principles            │
│  /workspace/context/_shared/_preferences.yaml ← cadence prefs per platform    │
│  /workspace/review/principles.md            ← Reviewer's editorial framework  │
│  /workspace/_hooks.yaml                     ← substrate-event hook decls      │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (operator drafts a piece, marks it ready)
┌──────────────────────────────────────────────────────────────────────────────┐
│  SUBSTRATE TRANSITION                                                          │
│  /workspace/context/authored/{piece-slug}/content.md  ← draft body            │
│  /workspace/context/authored/{piece-slug}/profile.md  ← frontmatter status:   │
│     transitions  draft → ready_for_review                                     │
│  Operator writes via WriteFile(scope="workspace") or the cockpit editor.      │
│  ADR-209 attribution: authored_by="operator", revision chain captures change. │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (next scheduler tick — within ~5min)
┌──────────────────────────────────────────────────────────────────────────────┐
│  WAKE EVALUATION [wake_source=substrate_event]                                │
│  services/wake_sources/substrate_event.py::walk_hooks queries                 │
│  workspace_file_versions since last walk. For each revision matching          │
│  /workspace/_hooks.yaml::path_match glob AND transitioning into the           │
│  declared field_change (transition guard prevents re-fires on preserving      │
│  writes), submit_wake_proposal(source="substrate_event", payload={hook,       │
│  path, field_change}). Tier 1 funnel: hook_match → escalate.                  │
│  funnel_decision=escalate stamped on execution_events row.                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  AI Reviewer (pre-ship-audit)                                                 │
│  Wakes with substrate_event envelope: hook prompt + substrate_event_path +    │
│  substrate_event_field_change + governance pre-load (ADR-276). Reads draft    │
│  + voice fingerprint + editorial + recent corpus + specs/voice-audit.md +    │
│  specs/continuity-audit.md. Audits against voice/continuity/anti-slop/        │
│  editorial criteria + cadence context.                                        │
│  Emits APPROVE / DEFER / REJECT with structured reasoning to                   │
│  /workspace/review/judgment_log.md AND updates standing_intent.md per         │
│  ADR-284.                                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (verdict-dependent)
┌──────────────────────────────────────────────────────────────────────────────┐
│  PUBLICATION (on APPROVE + delegation:bounded + ceiling-category match)       │
│  ExecuteProposal binds publication via the connected platform integration     │
│  (LinkedIn/Medium/X when audience-bearing; cockpit Queue otherwise).          │
│                                                                                │
│  DEFER → operator iterates, re-marks ready_for_review → hook re-fires (the    │
│  transition guard correctly distinguishes new transitions from preserving     │
│  writes).                                                                      │
│  REJECT → operator reads structured reasoning, decides to rewrite or kill.    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (post-publication, on cadence)
┌──────────────────────────────────────────────────────────────────────────────┐
│  CORPUS COHERENCE (cron-tick judgment recurrences)                            │
│  corpus-coherence-check (Mon+Thu) — cross-corpus voice/continuity/cadence    │
│  revision-audit (Fri) — long-arc artifact iteration check                     │
│  outcome-reconciliation — folds audience signal (when audience-bearing) into  │
│  /workspace/context/authored/_signal.md per ADR-282                           │
│                                                                                │
│  Findings feed back to Intent (voice fingerprint refines, editorial rules     │
│  evolve, cadence preferences tune).                                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                              Back to INTENT
```

Every arrow is an observation point. The substrate-event arrow (operator transition → scheduler tick → hook fire) is **the canonical test of ADR-296 v2 D2** — if this arrow fires correctly within one scheduler tick (~5 min) on a real frontmatter transition, the new wake source works end-to-end.

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
- **The Reviewer attempts to call `FireInvocation` in any trace** — ADR-296 v2 D3 removed it from `REVIEWER_PRIMITIVES`. The tool shouldn't be available; if a trace shows the Reviewer trying to call it, either the registry change regressed or a prompt still teaches it. Escalate.
- **A recurrence named `trade-proposal` appears in `execution_events`** — ADR-296 v2 Checkpoint 2 deleted that recurrence on the alpha-trader bundle. If a row appears with `slug=trade-proposal`, the bundle migration didn't propagate to the live workspace or a stale `_recurrences.yaml` is being read.
- **A substrate-event hook fires without a `wake_source=substrate_event` row in `execution_events`** — telemetry-and-behavior mismatch. The walker either skipped the row write or the funnel-decision stamping regressed.

---

## 4. Observation discipline during the E2E

Every friction event gets one note in `docs/alpha/observations/2026-04-22-adr206-trader-e2e-<nn>.md` using the playbook's template. Classified per `DUAL-OBJECTIVE-DISCIPLINE.md`:

- **A (system/architecture)** — the friction exposes a substrate, primitive, or pipeline gap. ADR seed.
- **B (product/persona)** — the friction exposes a copy, UX, or persona-fit issue. Product improvement seed.

Notes written in-flight, not post-hoc. If I catch myself thinking "I'll write this up later," that's the signal to write it now — post-hoc recall drifts.

Batch commit of observations at end of E2E, one commit with message `observe(alpha): trader E2E post-ADR-206 — N observations`.

---

## 5. Scope of this E2E (v6 — post-ADR-298 Phase 3 cutover, post-ADR-297 atomic surfaces)

**Sequencing**: alpha-author runs first (substrate-event canary, fast feedback, single scheduler tick); alpha-trader runs second (cron_tick + proposal_arrival path under real RTH cadence). Both share this scope; persona-specific items are tagged `[alpha-trader]` or `[alpha-author]` where they diverge.

**v6 readiness baseline (validated 2026-05-22)**: ADR-298 Phase 3 cutover landed and was validated end-to-end in [`docs/observations/2026-05-22-020000-canary-v5-adr298-cutover/`](../observations/2026-05-22-020000-canary-v5-adr298-cutover/) — every layer of the wake architecture (L1 walker dedup → L2 enqueue → L3 lane eligibility + lock → L4 dispatch → L5 queue terminal → L8 telemetry pairing) passed structurally on N=1 substrate-event reactive wake. Phase 3 test gate 39/39 PASS, cumulative ADR-298 gate 134/134 PASS. What canary v5 did NOT exercise: **L6 (Reviewer substrate writes)** — gated upstream by balance check on the test workspace. The next required validation is one observed L6 fire on a workspace with positive balance + `delegation: autonomous`. That's the missing observation; everything below assumes it as the target.

**In scope**:

- **Single-lane queue execution (ADR-298 D1).** Per workspace, no two Reviewer sessions run concurrently. Verify by tailing `wake_queue` during a window with multiple wake sources potentially firing — expect at most one row in `status=locked` per `user_id` at any moment. Reversal of ADR-261 D3 §1–§3 parallel-concurrent guarantee.
- **Two-lane drain (ADR-298 D3).** Wake sources land on `lane=paced` (cron_tick on judgment-mode recurrences) or `lane=live` (everything else). Paced lane respects `_pace.yaml` cap; live lane drains without pace gating. Verify telemetry shows correct lane assignment on each wake.
- **Pace substrate + Schedule gate (ADR-298 D5 + Phase 2).** `[alpha-trader]` `_pace.yaml` exists at `/workspace/context/_shared/_pace.yaml` post-fork (bundle ships default per Phase 4); locked in `DEFAULT_REVIEWER_WRITE_LOCKS`. Schedule primitive `create`/`update(schedule)` pace-gates at declaration time — `Schedule(action="create", schedule="*/1 * * * *")` on a workspace with `pace: {kind: daily}` returns `pace_exceeded` error. `[alpha-author]` same shape; bundle declares `minimum_pace: daily`. Verify both bundles ship pace at activation per Phase 4 activation gate.
- **Cross-source dedup at insert time (ADR-298 D6).** `UNIQUE (user_id, wake_source, dedup_key)` on `wake_queue` enforces dedup at enqueue. Legacy `execution_events.wake_dedup_key` column DROPPED via migration 180 + walker pre-check + telemetry kwarg removed (commit `dc36cdf`). Single dedup surface. Verify: trigger the same substrate transition twice within one scheduler tick window — expect one `wake_queue` row, not two.
- **Atomic kernel surfaces (ADR-297).** Cockpit nav is now 13 atomic kernel surfaces (mandate, delegation, principles, identity, brand, program, cockpit, cadence, etc.) emitted by the compositor as `surfaces[]` registry. Verify the dock + launcher renders the kernel set + active program surfaces. Per ADR-297 D17, Desktop is the load-bearing layer + FAB-on-desktop is the universal summon entry point. Persistent vocabulary: the operator no longer navigates by tabs (Feed/Work/Files/Agents framing dissolved); operator summons atomic surfaces.
- **Persona activation via canonical harness (ADR-230 + ADR-226).** Claude runs `python -m api.scripts.alpha_ops.activate_persona --persona alpha-trader-2 --dry-run` first, reviews the planned actions, then runs without `--dry-run` (or with `--skip-connect` if Alpaca creds aren't handy). The harness invokes `fork_reference_workspace` per ADR-226 — same primitive a real operator hits via Settings → Workspace (ADR-244). Per the 2026-05-11 ADR-226 amendment the fork calls `materialize_scheduling_index` inline; `verify.py` sees the recurrences in the `tasks` index immediately. Per ADR-298 Phase 4 the fork seeds `_pace.yaml` from bundle `minimum_pace` when operator has no pace declared. Observation: does the fork land the bundle's `_recurrences.yaml` + spec library + `_shared/*` (including `_pace.yaml`, `_preferences.yaml`, `_autonomy.yaml`) + `trading/*` files?

- **Persona activation via canonical harness (ADR-230 + ADR-226).** Claude runs `python -m api.scripts.alpha_ops.activate_persona --persona alpha-trader-2 --dry-run` first, reviews the planned actions, then runs without `--dry-run` (or with `--skip-connect` if Alpaca creds aren't handy). The harness invokes `fork_reference_workspace` per ADR-226 — same primitive a real operator hits via Settings → Workspace (ADR-244). Per the 2026-05-11 ADR-226 amendment the fork calls `materialize_scheduling_index` inline; `verify.py` sees the recurrences in the `tasks` index immediately. Observation: does the fork land the bundle's `_recurrences.yaml` + spec library + `_shared/*` + `trading/*` files? Does verify.py report 28/29 (or 29/29 with Alpaca connected)?
- **Mandate authoring as the gateway turn (ADR-207 + ADR-235).** YARNNN's first turn elicits the Primary Action + success criteria + boundary conditions. Claude pastes the canonical mandate from `docs/alpha/personas/alpha-trader-2/overrides/context/_shared/MANDATE.md` (or authors fresh via chat); YARNNN routes operator-shared substrate writes through `WriteFile(scope="workspace", path="context/_shared/MANDATE.md", content=...)` per ADR-235 D1.b. Observation: does YARNNN lead with Mandate (not Identity)? Does the write produce an authored revision attributed to `operator` per ADR-209?
- **Mandate hard-gate verification.** Any `Schedule(action="create")` attempt BEFORE the mandate is authored must return `error="mandate_required"`. Claude intentionally tries to create a recurrence pre-mandate once to confirm the gate fires, then authors mandate. (Note: since the bundle's `_recurrences.yaml` is forked at activation, the operator typically doesn't *create* new recurrences in normal flow — verification of the gate is exercised by trying to add a *new* one, e.g. `Schedule(action="create", slug="test-gate")`.)
- **Derivation report verification (ADR-207 P5).** After Mandate is authored, Claude reads `/workspace/memory/task_derivation.md` and confirms it lists loop-role coverage. (Doc name preserved post-ADR-231; content reflects current canon.)
- **Authored intent substrate.** `_operator_profile.md` (universe + signal definitions), `_risk.md` (position-sizing + risk parameters), `principles.md` (Reviewer rules) exist with persona-consistent content. The bundle's templates seeded the prompts; operator content overwrites them via `WriteFile(scope="workspace")` or `InferContext`. The bundle's `_universe.yaml` (ADR-254 D4 operator-declared ticker list) is also operator-tuned.
- **Bundle recurrence inventory (ADR-261/262 + ADR-296 v2).** **[alpha-trader]** Per [ALPHA-1-PLAYBOOK §3A.5](./ALPHA-1-PLAYBOOK.md#3a5-recurrence-set), the bundle ships **13 recurrences** post-ADR-296 v2 in single canonical `/workspace/_recurrences.yaml` (was 14 pre-collapse; `trade-proposal` deleted, `signal-evaluation` emits `ProposeAction` inline). Verify post-fork: all 13 present in workspace_files at that path, all 13 reflected in the `tasks` scheduling index with `declaration_path='/workspace/_recurrences.yaml'`, all `paused=false` and `status='active'`. The three mechanical mirrors (`track-account`, `track-orders`, `track-positions` per ADR-264) carry `mode: mechanical` and `@primitive: SyncPlatformState` directives; the other 10 carry `mode: judgment`. **[alpha-author]** Bundle ships **3 judgment recurrences** (`corpus-coherence-check`, `revision-audit`, `outcome-reconciliation`) per ALPHA-1-PLAYBOOK §3C.2. Smaller because primary driver is the substrate-event hook, not cron.
- **Bundle hook inventory (ADR-296 v2 D2) — new.** **[alpha-trader]** `/workspace/_hooks.yaml` ships with `hooks: []` by design (see §3A.5b). Verify the file exists post-fork; empty list is correct. **[alpha-author]** Bundle ships **1 substrate-event hook**: `pre-ship-audit` (path_match `/workspace/context/authored/*/profile.md`, field_change `status: ready_for_review`). Verify post-fork: hook present, `paused: false`, prompt body intact. This is the load-bearing test of D2.
- **Reviewer wake-source taxonomy (ADR-296 v2 D1).** Verify the Reviewer's unified `invoke_reviewer(trigger, context)` entry point fires correctly across all five wake sources via the singular `services/wake.py::submit_wake_proposal` gateway (plus `stream_addressed_wake` for the SSE-streaming addressed path):
    - `cron_tick` — scheduler-walked recurrence due in `tasks` index. alpha-trader exercises this on every `track-universe` / `signal-evaluation` / `pre-market-brief` / `morning-*` fire. alpha-author exercises it on `corpus-coherence-check` / `revision-audit` / `outcome-reconciliation` fires.
    - `addressed` — operator addresses YARNNN/Reviewer via chat. Both personas exercise. Streaming via `stream_addressed_wake`; funnel auto-escalates (operator presence is wake-warrant).
    - `proposal_arrival` — `services/wake.py::submit_wake_proposal(source="proposal_arrival", ...)` fired by `handle_propose_action`. alpha-trader: `signal-evaluation` emits inline → proposal_arrival → Reviewer wakes. alpha-author: pre-ship-audit hook → Reviewer wakes (substrate_event source) → if Reviewer emits ProposeAction(publication) → proposal_arrival wake for second judgment cycle (optional).
    - `substrate_event` — `services/wake_sources/substrate_event.py::walk_hooks` walks `workspace_file_versions` against `_hooks.yaml` declarations. **alpha-author canary**: operator transitions `profile.md` frontmatter `status` to `ready_for_review` → next scheduler tick fires the pre-ship-audit hook. Verify telemetry: `wake_source=substrate_event`, `funnel_decision=escalate`, `error_reason=null`.
    - `manual_fire` — operator triggers via `/work` Run action or chat `FireInvocation` (CHAT_PRIMITIVES; preserved per ADR-296 v2 D3).
- **Wake telemetry stamping (ADR-296 v2 + migration 177) — new.** Every `execution_events` row must carry `wake_source` + `funnel_decision` columns populated correctly. Spot-check after each natural fire. Skip-decisions (balance exhausted, spend ceiling, judgment cap, min-interval floor) stamp `funnel_decision=skip`; mechanical-mode recurrences stamp `funnel_decision=mechanical`; Reviewer-invoked judgment recurrences stamp `funnel_decision=escalate`.
- **Sub-LLM specialist dispatch (ADR-261 D7 + ADR-176).** Verify production-role specialists (researcher/analyst/writer/tracker/designer/reporting per ADR-176) materialize as focused-prompt `DispatchSpecialist` calls invoked from the Reviewer's loop — not as separate Layer-2 task-pipeline executions. The headless task pipeline is dissolved per ADR-261. Specialist agent rows still lazy-create on first dispatch per ADR-205.
- **D3 invariant: Reviewer cannot self-invoke — new.** Verify FireInvocation is **not** in any Reviewer prompt trace and not in `REVIEWER_PRIMITIVES`. ManageHook + Schedule + WriteFile-to-standing-intent are the Reviewer's cadence/event-interest authoring surfaces per ADR-296 v2 D3. If any trace shows the Reviewer attempting FireInvocation, it's an ADR-296 v2 D3 violation — escalate per §3.4.
- **Funnel honest framing — new.** `services/wake_evaluation.py::tier_2_decision` exists but is **not currently wired** by `services/wake.py` — Tier 1 kernel gates are inline; Tier 2 Haiku never fires today. Observation discipline: do NOT claim "Tier 2 evaluated and escalated" in any note. The autonomy story right now is "wake sources land properly + inline kernel gates short-circuit when they should." The funnel module is scaffolded for v3; its activation is a future ADR. Any observation that erroneously credits Tier 2 with a decision is dual-objective-A (system finding: ADR-296 v3 seed for actually wiring the funnel).
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

- **Activation harness lands clean.** **[alpha-trader]** `activate_persona.py --persona alpha-trader-2` completes without error; bundle fork writes the expected file set (13 `_recurrences.yaml` entries + `_hooks.yaml` with empty list + 5 specs + `_shared/*` + `trading/*` + `review/*`). Per the 2026-05-11 ADR-226 amendment, post-fork the `tasks` index shows 13 rows with `declaration_path='/workspace/_recurrences.yaml'` immediately — no scheduler-tick wait. **[alpha-author]** `activate_persona.py --persona yarnnn-author` (or sibling) writes 3 `_recurrences.yaml` entries + `_hooks.yaml` with the pre-ship-audit hook + the bundle's `specs/*` + `_shared/*` + `authored/*` + `review/*`.
- **Mandate (ADR-207 + ADR-235)** — `/workspace/context/_shared/MANDATE.md` contains the operator-authored content after the gateway turn, written via `WriteFile(scope="workspace", ...)` and recorded as an authored revision per ADR-209 (`authored_by="operator"`). YARNNN's first turn leads with Mandate elicitation, not identity or soft onboarding.
- **Mandate hard-gate fires** — any pre-mandate `Schedule(action="create")` attempt returns `error="mandate_required"` with the operator-facing message pointing to `WriteFile(scope="workspace", path="context/_shared/MANDATE.md", ...)`.
- **Derivation report (ADR-207 P5)** — `/workspace/memory/task_derivation.md` auto-generates on mandate write, reflects current loop-role coverage.
- **Intent artifacts** — **[alpha-trader]** `_operator_profile.md`, `_risk.md`, `principles.md` exist with persona-consistent content. Bundle templates seeded the prompts; operator content overwrites them. `_universe.yaml` is operator-tuned ticker list. **[alpha-author]** `authored/_voice.md`, `authored/_editorial.md`, `_shared/_preferences.yaml`, `review/principles.md` exist with persona-consistent content.
- **Bundle recurrence inventory (ADR-261/262 + ADR-296 v2)** — **[alpha-trader]** `verify.py --persona alpha-trader-2` reports 13/13 `scaffolded_recurrences` checks pass against the canonical bundle slug set (`narrative-digest, outcome-reconciliation, proposal-cleanup, morning-calibration, morning-reflection, pre-market-brief, signal-evaluation, track-universe, track-account, track-orders, track-positions, weekly-performance-review, quarterly-signal-audit`). `trade-proposal` absent (per ADR-296 v2 collapse). All 13 declaration_paths equal `/workspace/_recurrences.yaml`. **[alpha-author]** 3/3 recurrences present (`corpus-coherence-check, revision-audit, outcome-reconciliation`).
- **Bundle hook inventory (ADR-296 v2 D2)** — **[alpha-trader]** `/workspace/_hooks.yaml` exists with `hooks: []`. **[alpha-author]** `/workspace/_hooks.yaml` carries the `pre-ship-audit` hook with `event=substrate_change`, `path_match=/workspace/context/authored/*/profile.md`, `field_change={status: ready_for_review}`, `paused: false`, prompt body intact.
- **Reviewer wake-source taxonomy (ADR-260 + ADR-256 + ADR-296 v2 D1)** — `invoke_reviewer` fires correctly for at least three of the five wake sources during the run: `addressed` (chat turn), `proposal_arrival` (post-proposal-insert via `submit_wake_proposal`), and (persona-specific) either `cron_tick` (alpha-trader signal-evaluation) or `substrate_event` (alpha-author pre-ship-audit hook). Decisions land in `/workspace/review/judgment_log.md` as `--- decision ---` entries with `authored_by="reviewer:<occupant>"` per ADR-281 §3 + ADR-209; material outcomes land as `--- material-outcome ---` entries gated by `render_lineage_entry_if_material`. Per-action narration via `services/reviewer_chat_surfacing.py::narrate_reviewer_action` produces a System-Agent bubble in the feed for each consequential successful Reviewer action.
- **Wake telemetry stamping (ADR-296 v2 + migration 177)** — every `execution_events` row carries non-null `wake_source` ∈ {`cron_tick`, `addressed`, `proposal_arrival`, `substrate_event`, `manual_fire`} + non-null `funnel_decision` ∈ {`skip`, `escalate`, `mechanical`} (Tier 2 values `tier_2_wait` / `tier_2_observe` will not appear today; the funnel is scaffolded-not-live per §5). At least one row per source appears across the run.
- **D3 invariant: Reviewer cannot self-invoke** — no `FireInvocation` tool call appears in any Reviewer prompt trace during the run. Schedule + WriteFile-to-standing-intent + ProposeAction + ManageHook are the surfaces the Reviewer uses to shape future wake evaluation.
- **Substrate-event canary (ADR-296 v2 D2) [alpha-author]** — the canonical close-out: operator writes a draft, transitions `profile.md` `status` from `draft` to `ready_for_review`, expects within one scheduler tick (~5 min) an `execution_events` row with `wake_source=substrate_event`, `funnel_decision=escalate`; the Reviewer reads the draft + voice + editorial + recent corpus + the hook's `substrate_event_path` envelope field, writes APPROVE/DEFER/REJECT to `judgment_log.md` with structured reasoning + updates `standing_intent.md` per ADR-284. A clean close-out validates ADR-296 v2 D2 end-to-end.
- **Sub-LLM specialist dispatch (ADR-261 D7)** — at least one Reviewer-loop turn invokes `DispatchSpecialist` against a production-role specialist (e.g. researcher) and integrates the focused-prompt output. No Layer-2 task-pipeline execution observed (it's dissolved per ADR-261).
- **Mechanical mirror executors (ADR-264) [alpha-trader]** — at least one of `track-account` / `track-orders` / `track-positions` fires during market hours via the `@primitive: SyncPlatformState` directive at zero LLM cost. `execution_events` row carries `wake_source=cron_tick`, `funnel_decision=mechanical`. Output files land at `/workspace/context/portfolio/{account,orders,positions}.yaml`.
- **Pipeline execution** — **[alpha-trader]** `track-universe` + `signal-evaluation` run via the singular wake gateway (`services/wake.py::submit_wake_proposal` → `wake_sources.cron_tick.dispatch_recurrence`) without errors. When `signal-evaluation` detects a fire condition, it emits `ProposeAction` inline (no `trade-proposal` recurrence anywhere in `execution_events`). Outputs land at the operator-declared CONVENTIONS.md slug-templated paths (`/workspace/context/trading/{ticker}.yaml` per ADR-254 D5, `/workspace/context/trading/signals/{slug}.yaml`).
- **Cockpit rendering (ADR-228)** — `/work` cockpit renders four faces against substrate. AUTONOMY chip (ADR-238) surfaces in the feed composer header.
- **YARNNN prompt** — uses operation-first vocabulary on the elicitation turn. Mandate-first posture visible in first response. The five-profile prompt registry (ADR-233 Phase 1) routes the workspace conversation through `prompts/chat/workspace.py`.
- **Feed surface (ADR-259)** — tab label "Feed", URL `/feed`, backend route `/api/feed/*`. Cross-pollution from old `chat` vocabulary observable only in the runtime characteristic (Anthropic API call shape; `chat` permission mode in `CHAT_PRIMITIVES` registry) — not in surface names or operator-facing copy.
- **OCCUPANT runtime-truth alignment (ADR-284 D3)** — `verify.py --persona alpha-trader-2` `occupant_attribution` invariant passes: `/workspace/review/OCCUPANT.md` frontmatter declares `occupant_class: ai` + `occupant: ai:reviewer-sonnet-*` (post-bundle-fork, written by `_populate_occupant_for_runtime` with `authored_by="system:occupant-fork"` per ADR-209). A failure here indicates either the bundle-fork helper regressed or the live workspace pre-dates the ADR-284 Phase 1 ship (needs re-fork).
- **Standing intent substrate (ADR-284 D2 + D6)** — after the first judgment-mode recurrence fires post-activation (typically `signal-evaluation` at market open + 15min, or any addressed Reviewer turn), `/workspace/review/standing_intent.md` exists with frontmatter (`as_of`, `horizon`, `occupant`) + three section headings (*What I'm watching for* / *What would change my next move* / *Open questions to the operator*) + `authored_by="reviewer:ai:reviewer-sonnet-*"`. On a subsequent no-fire judgment cycle, the file is updated (not absent) — substrate counterpart to no-fire judgment per ADR-284 D2 + bundle principles.md "Default posture: action". Specificity check: entries cite signal/ticker/threshold/distance, not generic "watching for opportunities" noise.
- **Reviewer wake envelope renders standing-intent sections (ADR-284 D4)** — Reviewer prompt traces show `## OCCUPANT.md — Your current seat` + `## standing_intent.md — What you were watching for last cycle` sections (or the empty-state hint `(empty — first cycle, author it as part of this judgment)` on the first cycle). The persona prompt section "Your standing intent has a substrate home" composes with the envelope rendering so the contract is load-bearing.
- **Single-lane queue execution (ADR-298 D1)** — at no point during the run does `wake_queue` show two rows in `status=locked` simultaneously for the same `user_id`. `has_in_flight` check in `wake_drainer.py::drain_can_acquire_for_user` enforces this; observe via `SELECT user_id, status, locked_by, created_at FROM wake_queue WHERE status='locked'` during a window of multiple wake sources potentially firing.
- **Cross-source dedup (ADR-298 D6)** — same substrate transition triggered twice within one scheduler tick window produces exactly one `wake_queue` row (UNIQUE `(user_id, wake_source, dedup_key)`). Legacy `execution_events.wake_dedup_key` column dropped per Phase 5; verify via `SELECT column_name FROM information_schema.columns WHERE table_name='execution_events' AND column_name='wake_dedup_key'` returns zero rows.
- **Pace substrate + Schedule gate (ADR-298 D5 + Phase 2)** — `/workspace/context/_shared/_pace.yaml` exists post-activation (bundle ships per Phase 4 `minimum_pace` declaration; default-seed for first activation). Attempt `Schedule(action="create", schedule="*/5 * * * *")` on a workspace with `pace: {kind: daily}` returns `error="pace_exceeded"`. Pace is included in Reviewer wake envelope per ADR-276 helper; Reviewer surfaces Clarify when its proposed recurrence would breach.
- **L6 closure — the missing observation** — on a workspace with positive balance + `delegation: autonomous`, observe ONE full cycle: wake_queue enqueue → drain → Reviewer reads ground-truth substrate → emits a verdict via `ReturnVerdict` (or directives) → if `ProposeAction` fired, `should_auto_apply` returns True → `handle_execute_proposal` invokes real platform write (Alpaca paper order, or Resend send for alpha-author publication) → outcome reconciliation reads back into `_money_truth.md` / `_performance.md` per ADR-195 v2. This is the single observation that flips the line from "architecture-claim" to "validated."
- **Diagnostic surface** — `/settings/system` renders cleanly (likely empty content; the surface itself should respond).
- **Substrate update infrastructure ready (ADR-292)** — `bundle_update_available(client, user_id)` and `kernel_update_available(client, user_id)` return None for a freshly-activated workspace (MANDATE.md frontmatter recorded `activated_bundle_version` + `activated_kernel_version` at fork time, matching current canon). When the platform later bumps `KERNEL_VERSION` or a bundle `version:`, these helpers return non-None and surface the update affordance in Settings → Workspace. The operator clicks Update; `apply_substrate_update(scope=..., source="operator")` runs and appends to `/workspace/_shared/substrate-update-log.md`. NOT a daily cron — operator-initiated, like Claude Code's `claude --update`.
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
- A `trade-proposal` slug appears in any `execution_events` row or in any Reviewer prompt trace. → Observation: ADR-296 v2 Checkpoint 2 bundle migration didn't propagate to the live workspace (stale `_recurrences.yaml` cached on read, or fork didn't run on the test workspace), or a prompt still teaches the FireInvocation chain. Investigate via `git log` on the bundle path + `bundle_update_available()` on the workspace.
- `execution_events` rows show `wake_source IS NULL` or `funnel_decision IS NULL` after ADR-296 v2 Checkpoint 1 telemetry should have populated them. → Observation: telemetry population regressed; one of the `record_execution_event` call sites lost the `wake_source=...` / `funnel_decision=...` kwarg.
- The Reviewer's prompt trace shows `FireInvocation` listed among its available tools. → Observation: ADR-296 v2 D3 invariant violation. Check `services/primitives/registry.py::REVIEWER_PRIMITIVES` — `FireInvocation` should be absent (only in `CHAT_PRIMITIVES`).
- `walk_hooks` is invoked on a scheduler tick **[alpha-author]** but no `wake_source=substrate_event` row appears in `execution_events` despite a matching `workspace_file_versions` revision in the window. → Observation: either the hook glob/transition guard isn't matching the revision (check `_path_matches` + `_field_change_matches` logic) or `submit_wake_proposal` raised before stamping the row. Read the scheduler logs.
- A note in observation drafts credits Tier 2 Haiku with an "escalate" or "wait" decision. → Observation: the writer of the note misread the funnel state — Tier 2 is scaffolded-not-live in v2. Reword to credit "Tier 1 kernel gate" (inline budget checks) for the decision; record the misread as a dual-objective-B finding (the contract's framing didn't carry — future v3 wiring should make the distinction obvious in telemetry).

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-22 | v1 — Initial contract. Written pre-E2E to freeze Claude's posture + loop framing + acting-on-behalf rules before the ADR-205/206 post-purge validation run. |
| 2026-04-22 | v2 — ADR-207 folded in. Added Mandate-first gateway turn to §5 scope + §6 success criteria. Added capability-gate verification (ADR-207 P3) + self-declaration task authoring (ADR-207 P4b) + derivation report verification (ADR-207 P5). Canonical mandate artifacts: `docs/alpha/personas/alpha-trader/MANDATE.md`, `docs/alpha/personas/alpha-commerce/MANDATE.md`. |
| 2026-04-29 | v3 — Post-refactor-wave realignment. Folds in ADR-231 (task abstraction sunset → recurrence declarations + natural-home substrate + `/api/recurrences` URL flip + invocation dispatcher), ADR-235 (`UpdateContext` dissolution → `WriteFile(scope="workspace")` for operator-shared writes, `InferContext`/`InferWorkspace` for inference, `ManageRecurrence` for lifecycle), ADR-230 (canonical activation harness `activate_persona.py`), ADR-228 (cockpit four-face reshape replaces ADR-198 v2 BriefingStrip framing), ADR-227 (capability-gated tool augmentation — fixes the 2026-04-28 Tracker WebSearch defect), ADR-226 (reference-workspace activation flow), ADR-238 (AUTONOMY chip), ADR-239 (cockpit decisions parser unification), ADR-233 (five-profile prompt registry at `prompts/{chat,headless}/`). Renames `CreateTaskModal` → `CreateRecurrenceModal`, removes `/api/tasks/types` reference. Recommends `alpha-trader-2` as the dogfooding persona (kvk-as-operator stat-arb). |
| 2026-05-11 | v4 — Post-real-time-Reviewer-loop realignment (Bucket C of the alpha-doc audit). Folds in ADR-260 (real-time Reviewer loop, three triggers `addressed | reactive | scheduled`, no mid-loop trigger), ADR-261 (recurrences-as-prompts: per-shape declaration files dissolved into single `/workspace/_recurrences.yaml`; `output_kind` enum dissolved; `ManageRecurrence` → `Schedule`; headless task pipeline dissolved; specialists become `DispatchSpecialist` sub-LLM calls), ADR-262 (output topology via CONVENTIONS.md + operator-authored specs at `/workspace/specs/`), ADR-264 (mechanical-mirror recurrences `track-account` / `track-orders` / `track-positions` via `@primitive: SyncPlatformState` deterministic Python executors, zero LLM cost), ADR-259 (Chat surface renamed Feed; `/chat` → `/feed`; `routes/feed.py`), ADR-258 revised (Reviewer as personified chat-mode operator using `REVIEWER_PRIMITIVES` 16-tool curated subset, per-action narration via `services/reviewer_chat_surfacing.py`), ADR-254 (file-format discipline: `.yaml` for machine-parsed structured config, `.md` for LLM-readable prose, `_universe.yaml` + `_autonomy.yaml` + `_principles.yaml` introduced). §5 + §6 rewritten to reflect bundle-ships-14-recurrences-via-fork model (operator no longer composes the recurrence set via chat). Activation-harness materialize-after-fork wiring shipped 2026-05-11 per ADR-226 amendment. Companion alpha-doc cleanup: PLAYBOOK §3A.5/§3A.5b unified into a single canonical 14-recurrence table; PLAYBOOK §3B alpha-commerce lifted to `docs/alpha/parked/`; BOOTSTRAP.md archived to `docs/alpha/parked/` (its workflow distilled to harness commands in OPERATOR-HARNESS.md). |
| 2026-05-20 | v5 — Post-ADR-296 v2 wake-architecture realignment. Folds in ADR-296 v2 (wake is event-driven + evaluation-gated: five wake sources `cron_tick | addressed | proposal_arrival | substrate_event | manual_fire` flow through singular `services/wake.py::submit_wake_proposal` gateway; Reviewer event-fired not continuously-running; FireInvocation removed from `REVIEWER_PRIMITIVES` per D3; substrate-event hooks at `/workspace/_hooks.yaml` are the sibling declarative shape to recurrences per D2; telemetry stamps `wake_source` + `funnel_decision` per migration 177). Scope expanded from alpha-trader-only to **both archetypes** — alpha-author runs first as substrate-event canary (faster feedback, single scheduler tick), alpha-trader runs second under real RTH cadence. New §2b alpha-author substrate-event loop diagram. §2 alpha-trader loop diagram redrawn: `trade-proposal` arrow removed (recurrence deleted in Checkpoint 2), `signal-evaluation` emits `ProposeAction` inline, Reviewer wakes on resulting `proposal_arrival` wake source. §3.4 stop conditions extended with wake-architecture invariants (no FireInvocation in Reviewer traces, no `trade-proposal` slug in execution_events, hook fires must have telemetry stamp). §5 inventory: alpha-trader **13** recurrences (was 14); alpha-author 3 recurrences + 1 hook. New scope items: bundle hook inventory, wake-source taxonomy verification across 5 sources, wake telemetry stamping, D3 self-invocation invariant, substrate-event canary close-out. **Honest framing** added: `services/wake_evaluation.py` Tier 2 funnel is scaffolded-not-live; observation discipline must not credit Tier 2 with decisions — it's an ADR-296 v3 seed. §6 success criteria refreshed with persona-specific tags `[alpha-trader]` / `[alpha-author]`. §7 stop-and-think triggers extended with telemetry + invariant misses. Companion alpha-doc cleanup: PLAYBOOK §3A.5 collapsed from 14 → 13 recurrences (drops `trade-proposal` row, updates `signal-evaluation` row to emit inline); PLAYBOOK §3A.5b new (alpha-trader empty hooks by design); PLAYBOOK §3C new (alpha-author program/persona spec). |
