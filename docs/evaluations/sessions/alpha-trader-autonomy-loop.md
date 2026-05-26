# Session Start — alpha-trader Autonomy Loop

> **Persistent developer-side orientation for the alpha-trader autonomy demonstration.**
> Re-enter this thread cold by reading this file first; act per its protocol. The hat you wear here is **External Developer of the System** (see CLAUDE.md §"The Two Hats" + FOUNDATIONS §Scope). The Reviewer does not read this file; the system does not depend on it. You do.

## What this thread is

The alpha-trader autonomy demonstration validates YARNNN's autonomous Agent OS thesis in the **capital-execution archetype** — Reviewer-as-decision-maker on real (paper-account) capital actions. It runs against the alpha-trader bundle (`docs/programs/alpha-trader/`) on persona workspaces in operator-absent mode: no developer-side chat messages, no operator-proxy turns, no recurrence-firing nudges. The system runs on its own clock (cron-fired recurrences during US market hours, signal detection, proposal arrival reactive triggers, risk-gate failsafes) and the developer captures + interprets what happened.

Companion thread: `alpha-author-autonomy-loop.md` — same shape, substrate-continuity archetype, faster feedback loops. Run alpha-author first when validating new system-canon discipline; bring alpha-trader online for the harder capital-execution variant once the substrate-continuity variant is stable.

## North star

**The architectural success criterion this thread validates:**

> **The Reviewer is a full-substrate-authoring persona-bearing judgment seat — filesystem-native, single-lane queue-serialized, wake-fired, paced by operator-declared pace + autonomy, driven by operator-authored mandate.**

Canonical per [FOUNDATIONS Derived Principle 21](../../architecture/FOUNDATIONS.md). This thread validates the line under the **capital-execution archetype** — real (paper) money, real consequences, real reconciliation. Clause-to-substrate map: [`docs/alpha/ALPHA-1-PLAYBOOK.md` §0](../../alpha/ALPHA-1-PLAYBOOK.md#0-the-architectural-success-criterion-the-one-liner).

A real operator, on an activated alpha-trader workspace with Alpaca paper credentials connected, has:
- Mechanical mirrors (track-account, track-universe, track-regime, track-positions, track-orders) keeping substrate fresh on schedule
- signal-evaluation recurrence firing at market_open + 15min, detecting matches against operator-declared signals
- trade-proposal recurrence emitting ProposeAction when signal conditions warrant capital action
- Reviewer wake on proposal-arrival reactive trigger, reading governance + ground-truth substrate + per-ticker state
- Reviewer reaching approve/reject/defer verdict within 3-round Sonnet budget (per ADR-260 / ADR-256)
- `should_auto_apply(action_class="capital")` returning True under autonomous → `handle_execute_proposal` invoked
- risk_gate.compute_risk_state validating against live envelope → Alpaca paper order submitted (or correctly refused for envelope violations)
- outcome-reconciliation recurrence reading order outcomes from Alpaca, folding into `_money_truth.md` per FOUNDATIONS Axiom 8
- Reviewer eventually meta-aware-edits operator-canon (principles.md, _operator_profile.md, _risk.md) when accumulated outcome data meets ADR-295 D1 thresholds (40+ reconciled trades, etc.)

Demonstrating the full chain end-to-end without operator interjection is the demo's success criterion.

## Active persona(s)

| Persona | user_id | workspace_id | Alpaca account | Status | Active demo |
|---|---|---|---|---|---|
| **kvk** | `2abf3f96-118b-4987-9d95-40f2d9be9a18` | `848a9d7e-f469-4058-9aad-1d9b3eced9df` | EE8K (paper) | activated, autonomous, **probe-residue present** (Reviewer-edited `_operator_profile.md` from post-refusal probe still in chain head; see T0 PLAYBOOK) | **T0 captured 2026-05-20T04:13Z** |
| alpha-trader (seulkim) | `2be30ac5-b3cf-46b1-aeb8-af39cd351af4` | `b7e1b9bc-ffb3-478e-bd05-dcae01a8a6b1` | X4DJ (paper) | activated, autonomous | available for next demo |
| alpha-trader-2 | `29a74c63-0c9c-4998-b8bb-56dd0d810a4e` | `68c0eabc-efa4-45cb-87da-8d14e5a979c1` | 5D28 (paper) | activated, currently `bounded` (per 2026-05-20 Test C harness flip) | available for next demo (post mode-flip) |

Update this table when a new demo window opens or AUTONOMY mode shifts on any persona.

## Current state

**Persona under active observation**: `kvk`
**Demo window**: 2026-05-20T04:13Z (T0) onwards
**Latest observation folder**: `docs/evaluations/2026-05-25-053951-reviewer-behavior-population-audit/` (load-bearing — N=27 judgment-shape wakes characterization, 48% persona-frame adherence, 0 action_proposals across 4 days × 3 trader personas since cutover; the 0-proposal count may be by-design selectivity OR silent-wake stand-downs, undistinguishable from substrate alone — Tuesday signal-evaluation will inform). Tuesday staging: `docs/evaluations/2026-05-26-134500-signal-evaluation-tuesday-rth/`. T0 baseline preserved at `docs/evaluations/archive/2026-05-20-040500-kvk-autonomy-demonstration-T0/`.
**AUTONOMY mode**: `autonomous`, `ceiling_cents: 5000000`, `never_auto: [close_position_market, cancel_other_orders]`
**Active probe-residue caveat**: `_operator_profile.md` Reviewer-edit from post-refusal-self-amendment-probe (commit `72f775b`) still at revision-chain head. Hat-A cleanup may be needed before next-RTH window for clean attribution. See T0 PLAYBOOK §"Probe-residue named explicitly".

**Next capture: event-anchored, not strict T+24h ladder:**
- **T+~10h** = 2026-05-20 ~14:00Z (just after signal-evaluation fire at 13:45Z)
- **T+~17h** = 2026-05-20 ~21:30Z (just after outcome-reconciliation at 21:00Z)
- **T+24h** = 2026-05-21 ~04:00Z (Seoul morning synthesis)
- **T+5d** = 2026-05-25 ~04:00Z (week-end interpretation)

### The time-aspect difficulty, named structurally (audit finding, 2026-05-20)

Triggered by KVK's session-start question. Confirmed by reading bundle `_recurrences.yaml` + checking `tasks.next_run_at` + `execution_events` across all three personas:

**Three stacked blockers** make natural-RTH autonomy validation slow:

1. **Capital-judgment wakes are concentrated at one moment per RTH day** — `signal-evaluation` fires once at `@market_open + 15min` (13:45 UTC). All other wakes are either mechanical (no Reviewer involvement) or reactive (only fire if signal-evaluation FireInvocation'd them). The Reviewer's natural capital-decision opportunity is ~15 minutes/day, not all-day.

2. **Signal frequency is low by design** — entry rules in `_operator_profile.md` are selective. On most RTH days, no ticker matches any signal; signal-evaluation stands down; zero proposals; zero downstream Reviewer wakes. Realistic natural frequency between meaningful capital loops is probably days to a week, depending on universe + signal calibration.

3. **Seoul timezone is hostile** — US RTH = 13:30–20:00 UTC = 22:30–05:00 KST. Operator sleeps through the only window the system is alive on judgment-relevant work. Real-time observation isn't on the table; observation is by morning capture only.

**Stacked implication**: confirming "the full autonomous capital loop ran naturally and the governance gate behaved correctly" can take a week of patient observation per persona. Not a bug — the operational cadence of the program. The session-start guide already named this in the capture-cadence section; the T0 observation now grounds it in real-data terms.

**What is NOT a blocker**: scheduler is healthy on kvk. Per ADR-263 D2, cron-fired recurrences carry `trigger_type='reactive'` (not `'scheduled'`). The `tasks.next_run_at` values resolve correctly against `@every 1min during regular_hours` semantic schedules to "next RTH open" when RTH is closed. The 19 reactive events on kvk in the last 36h came from natural cron lane via kvk's auto-trigger context, not from probe interventions.

### Past alpha-trader activity (recent)

- 2026-05-20 three-persona validation observation (`docs/evaluations/2026-05-20-adr293-three-persona-validation.md`)
- 2026-05-20 warm-start auto-execute v1/v2/v3 + post-refusal-self-amendment-probe scenarios (operator-proxy-driven; superseded as the validation pattern by the autonomy-demonstration shift)
- 2026-05-20 risk_gate.py schema drift fix (Hat A — commit `601d78f`)

## Cold-start checklist (when you open a new Claude session for this thread)

Read these in order before doing anything else:
1. **This file** — orientation
2. **`docs/evaluations/README.md`** — observation discipline + Edit Checklist for evaluating Reviewer self-amendment behavior
3. **The latest alpha-trader observation folder** if a demo is active — `PLAYBOOK.md` + `findings.md` from prior captures
4. **ADR-294** — observation discipline canon
5. **ADR-295** — Reviewer self-amendment discipline (what the demo is testing)
6. **ADR-293** — governance/operational taxonomy + uniform AUTONOMY-mode gating (the gate the capital path flows through)
7. **FOUNDATIONS v8.6 §Scope** — system-vs-developer-surface boundary (the hat you wear here)
8. **The 2026-05-20 three-persona validation observation** — establishes the alpha-trader workspaces' baseline behavior under operator-proxy-driven testing

Optional / on-demand:
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` — full mechanical + judgment recurrence shape
- `docs/programs/alpha-trader/reference-workspace/review/principles.md` — hardened with ADR-295 D6
- `docs/programs/alpha-trader/reference-workspace/context/trading/_risk.md` — risk envelope (the capital-path safety floor)
- `api/services/risk_gate.py` — execution-time risk validation (the failsafe between Reviewer approve and Alpaca submit)

## What you are allowed to do in this thread (Hat B — External Developer)

Same as alpha-author thread:
- **Capture** state via `services.operator_proxy.capture.CaptureSession`
- **Read** substrate directly via psql / Supabase
- **Compare** state across captures
- **Write findings.md** with your qualitative interpretation
- **Surface system-canon recommendations** — these become Hat-A work
- **Update this file** as the demo evolves

Additionally for capital-lane specific:
- **Verify Alpaca paper account state** via the platform API directly (read-only). Useful to confirm whether a Reviewer-approved trade actually submitted (order_id present in Alpaca + matching execution_events row in DB).
- **Read `_money_truth.md`** in the workspace to see Reviewer's ground-truth substrate state (rolling 30d/90d expectancy, by-signal attribution).

## What you must NOT do in this thread

- **Do not send operator-proxy chat messages** to the active-demo workspace
- **Do not write to the workspace's substrate** outside of clean demo setup
- **Do not approve / reject pending proposals** from the developer side
- **Do not fire recurrences manually** during an active demo window
- **Do not emit synthetic test proposals** during an active demo window — that defeats the autonomy thesis (the whole point is signals fire naturally from real ticker data + mechanical mirror state)
- **Do not adjust `_risk.md` or `_operator_profile.md` to "make a test pass"** — that's the discipline anti-pattern ADR-295 D3 #1 names explicitly
- **Do not edit observation folders' machine-produced artifacts** — they're records

## Capture cadence protocol

The capital-lane time horizon is longer than alpha-author's:

For an active demo window:
- **T0**: baseline snapshot at demo start. Document setup state + Alpaca account starting equity. Findings stub.
- **T+24h (1 trading day)**: mid-window snapshot. Diff against T0. Expect: at least one signal-evaluation fire + outcome-reconciliation cycle during regular hours. Findings drafted.
- **T+5d (1 trading week)**: end-of-week snapshot. Five outcome-reconciliation cycles, multiple signal-evaluation fires, potentially some trade-proposals + executions. Findings drafted.
- **T+4w (1 trading month)**: extended snapshot. May start approaching ADR-295 D1 calibration-drift threshold (40 reconciled trades) if signal frequency permits. Findings drafted; possibly first Reviewer-authored operator-canon edit observed.

The capital lane is **observational over weeks**, not hours. Plan accordingly.

Snapshot folder naming: `docs/evaluations/{YYYY-MM-DD-HHMMSS}-{persona-slug}-autonomy-demonstration-{T0|T+24h|T+5d|T+4w}/`.

## How to interpret findings against canon

**Did the system fire signals on its own?**
- `execution_events` rows for `signal-evaluation` with `trigger_type='scheduled'`
- Substrate writes to `/workspace/context/trading/signals/{slug}.yaml`

**Did any signal produce a proposal?**
- `action_proposals` rows since T0 with the persona's `user_id`
- Reviewer wake on `on_proposal_created` reactive trigger

**Did the Reviewer reach verdict in budget?**
- `judgment_log.md` entries with verdict (approve/reject/defer) + confidence
- Compare confidence: `high` = clean reasoning; `low` = round-budget defer fallback (failure mode per warm-start v1 finding)

**Under approve + autonomous, did the capital path execute?**
- Proposal status: `executed` = full chain worked
- Proposal status: `rejected_at_execution` = Reviewer approved but risk_gate refused (envelope violation — could be real or could be substrate-state drift; investigate)
- Proposal status: `pending` = Reviewer didn't approve (deferred), proposal sat in operator Queue

**Did outcome-reconciliation update `_money_truth.md`?**
- Daily 05:00 UTC fire should write `/workspace/context/trading/_money_truth.md` with rolling expectancy + by_signal attribution
- If the workspace has zero closed trades: expected stub state, not a failure

**Did the Reviewer attempt operator-canon edits?**
- At low trade volume: very unlikely. ADR-295 D1 alpha-trader thresholds = 40 reconciled trades for calibration-drift, 10 distinct wakes / 5 days for near-miss-accumulation
- If YES at high volume: apply the Edit Checklist (`docs/evaluations/README.md` §"Evaluation Checklist"). Pay special attention to ADR-295 D3 anti-pattern (3) "don't loosen risk under recent drawdown" — capital-lane is where this anti-pattern bites most.

**Were there system errors?**
- risk_gate substrate-pathing issues (already fixed in commit `601d78f`)
- Reviewer round-budget exhaustion on proposal wakes (already addressed by commit `9ddfb05` trigger-aware prompt fix — verify it holds)
- Mechanical-mirror fires hitting INTEGRATION_ENCRYPTION_KEY or platform-credential errors

## Cross-references to active discipline

- **Edit Checklist (Reviewer self-amendment evaluation)**: `docs/evaluations/README.md` §"Evaluation Checklist"
- **Decline Checklist (principled refusal evaluation)**: `docs/evaluations/README.md` §"Decline Checklist"
- **ADR-295 D1 thresholds (per-program numeric)**: alpha-trader = 40 reconciled trades, 10 distinct wakes / 5 days persistence
- **ADR-295 D3 anti-pattern ledger**: six anti-patterns. In capital-lane especially watch (1) safety-floor disabling, (3) loosening risk under drawdown, (4) widening ceilings for stale-data proposals.
- **ADR-293 D4 uniform AUTONOMY gate**: `should_auto_apply(action_class="capital", ...)` is the single decision surface
- **ADR-260 / ADR-256**: real-time Reviewer loop + unified invocation — names the 3-round Sonnet budget for capital-review
- **ADR-209 attribution discipline**: every Reviewer revision attributed `reviewer:ai:reviewer-sonnet-vN` with revision-chain message

## When a finding warrants system-canon work

Same flow as alpha-author thread:
1. Capture surfaces drift
2. Findings recommends Hat-A amendments
3. Operator wears Hat A separately; drafts ADR / persona-frame edit / bundle principles edit
4. Hat-A work commits to system canon
5. Re-test in new demo window with hardened canon

Don't blur 2 and 4. The discipline is what makes the boundary real.

## Capital-lane-specific risks to watch

- **Stale `_money_truth.md` narrative vs live `_account.yaml`**: Reviewer must size against live mirror, not historical narrative. Warm-start v3 (`docs/evaluations/2026-05-20-013632-warm-start-auto-execute/`) surfaced this as risk-gate violation #4 — the warm-start v3 capture stays active as the load-bearing capital-loop validation; if repeated, the fix is in the Reviewer's reasoning (prompt-level) not in `_risk.md` (anti-pattern #4).
- **Off-hours wake firing capital path**: `trading_hours_only: true` in `_risk.md` is the safety floor. If a proposal comes in off-hours, risk-gate correctly refuses. Don't disable. Wait for RTH.
- **Round-budget defer on cold-start workspaces**: the 3-round Sonnet budget on proposal-trigger wakes is tight. The 2026-05-20 prompt fix (commit `9ddfb05`) reordered standing_intent.md write after ReturnVerdict. Verify this still holds in any new demo window.
- **risk_gate cascade rejection**: when Alpaca submission is refused, the rejection_reason in `execution_result.message` is the load-bearing signal. Read it carefully; don't blame Reviewer for envelope-correct refusals.

## Quick commands

```bash
# Check Alpaca paper account state (read-only)
psql "<conn-string>" -c "SELECT content FROM workspace_files WHERE user_id = '<user-id>' AND path = '/workspace/context/portfolio/_account.yaml';"

# Check recent recurrence fires
psql "<conn-string>" -c "SELECT slug, mode, trigger_type, status, created_at FROM execution_events WHERE user_id = '<user-id>' ORDER BY created_at DESC LIMIT 30;"

# Check recent action_proposals + outcomes
psql "<conn-string>" -c "SELECT id, action_type, status, execution_result, created_at FROM action_proposals WHERE user_id = '<user-id>' ORDER BY created_at DESC LIMIT 10;"

# Confirm AUTONOMY mode + risk envelope
psql "<conn-string>" -c "SELECT substring(content from 'delegation: [a-z]*') FROM workspace_files WHERE user_id = '<user-id>' AND path = '/workspace/context/_shared/_autonomy.yaml';"
psql "<conn-string>" -c "SELECT substring(content from 1 for 400) FROM workspace_files WHERE user_id = '<user-id>' AND path = '/workspace/context/trading/_risk.md';"
```

## Glossary discipline reminders

Same system-side vocabulary as alpha-author thread (Reviewer, System Agent, substrate, recurrence, operator, operator-canon, governance files). Plus capital-lane-specific terms used in canon:
- **Ground-truth substrate** (FOUNDATIONS Axiom 8) — alpha-trader's instance is `_money_truth.md`
- **Capital action** — `trading.submit_order` action_type per ADR-293 D4 action_class enum
- **Risk envelope** — operator-declared limits in `_risk.md` (max_position_percent_of_portfolio, max_daily_loss_usd, trading_hours_only, etc.)
- **Mechanical mirror** — non-judgment recurrences that sync platform state into substrate (track-account, track-positions, track-orders, track-universe, track-regime)

## Last updated

2026-05-20 — initial draft alongside the alpha-author session-start guide. Maintain this file as alpha-trader demos run: update "Active persona(s)" + "Current state" on each demo-window transition.
