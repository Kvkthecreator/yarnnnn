# Cadence and Wakes — Canonical Synthesis

> **Status:** Canonical · **the two formerly-in-flight concepts are now IMPLEMENTED** per [ADR-327](../adr/ADR-327-budget-and-the-self-improving-loop.md) (Phases 1–6, 2026-06-08) — §11a self-improving loop (`_calibration.md` kernel mirror + persona posture + `ground_truth` declaration) · §12a pace→budget reframe (pace retired; `_pace.yaml` + `_token_budget.yaml` collapsed to one `_budget.yaml`). Last extended 2026-06-08.
> **Scope:** This is the single load-bearing reference for the full **wake / recurrence / cadence / pace / autonomy** framework. §1a maps how the five concepts relate (the operator's Pace + Autonomy + Identity trifecta over the wake unit). The implemented mechanics are canon; the two discourse-open sections state target architecture pending ADR.
> **Distills:** [ADR-260](../adr/ADR-260-real-time-reviewer-loop.md) · [ADR-261](../adr/ADR-261-recurrences-as-prompts.md) · [ADR-263](../adr/ADR-263-recurrence-mode-mechanical-vs-judgment.md) · [ADR-268](../adr/ADR-268-market-context-aware-recurrences.md) · [ADR-274](../adr/ADR-274-reviewer-cadence-self-awareness.md) · [ADR-275](../adr/ADR-275-introspection-cadence-reviewer-authored.md) · [ADR-276](../adr/ADR-276-reactive-trigger-envelope-governance-preload.md) · [ADR-284](../adr/ADR-284-standing-intent-substrate-and-occupant-envelope.md) · [ADR-296 v2](../adr/ADR-296-continuous-judgment-cycle.md) · [ADR-298](../adr/ADR-298-reviewer-wake-queue-and-pace.md) · [ADR-301](../adr/ADR-301-reviewer-pulse-envelope.md) · autonomy gate: [ADR-217](../adr/ADR-217-workspace-autonomy-substrate.md) (autonomy substrate) · [ADR-307](../adr/ADR-307-unified-permission-taxonomy.md) (permission taxonomy) / [`review_policy.py::should_auto_apply`](../../api/services/review_policy.py)
> **Builds on:** [FOUNDATIONS](FOUNDATIONS.md) Axiom 4 (Trigger) · Axiom 5 (Mechanism — the autonomy axis) · Derived Principle 18 (Standing intent implies Trigger-authoring authority) · Derived Principle 20 (Wake-as-irreducible-unit) · [ADR-209](../adr/ADR-209-authored-substrate.md) (Authored Substrate)
> **Purpose:** Single load-bearing reference for how cadence and wakes work in YARNNN. ADRs decide; this synthesizes.

---

## 1. The core thesis

YARNNN's Reviewer is **event-fired, not continuously-running**. Every action the Reviewer takes is downstream of a **wake** — a discrete event-driven invocation gated through one funnel. Cadence is the operator-visible shape of wake authority: which wakes can fire, on what triggers, with what budget envelope.

Three claims hold:

1. **Wake is the irreducible unit of agent activity** (Derived Principle 20). There is no Reviewer activity without a wake. There is no "background reasoning loop." A wake = a triggering event + an evaluation funnel decision + (on escalation) one bounded LLM invocation.

2. **Trigger authoring is an Identity-layer responsibility** (Axiom 4 sub-clause + Derived Principle 18). The Reviewer authors its own cadence by writing to substrate (`_recurrences.yaml` via `Schedule`, `_hooks.yaml` via `ManageHook`, `standing_intent.md` via `WriteFile`). The kernel scaffolds at bundle-fork time but does not own ongoing cadence policy. The operator declares deliverable preferences and the Reviewer reconciles them.

3. **Cost flows through wakes.** Every wake that escalates past the funnel fires a full Reviewer Sonnet loop (~$0.05-0.20 per fire). Cadence frequency × escalation rate × loop depth = workspace spend. Cadence is the upstream cost gate; autonomy (delegation) is the downstream action gate. Both matter; cadence dominates if misconfigured.

4. **A wake is a situation, not a task** (ADR-318). The upstream half — a judgment recurrence — is deliberately thin: `{slug, schedule, prompt}` (ADR-261 D3), a glorified prompt at a future invocation. The downstream half — the wake itself — is **agentic**: the recurrence-fire envelope already delivers the Reviewer its full operating context (`operating_context_block` = clock + market state + tenure; `schedule_index_md` = its own cadence; `standing_intent.md` = its forward-state) plus `Schedule`-authoring authority. So the Reviewer is not a function that runs one prompt and exits — it is a standing judgment seat woken for a reason. It serves the named task fully, then reasons forward from its operating context (a position that needs watching, a future wake to author, a cadence that's wrong) and authors what's warranted. This is the posture that makes multi-day autonomy real with no new machinery — the architecture already configures for it; the persona-frame names it. (Stance, not checklist — anti-rebloat per DP22.)

---

## 1a. The five concepts are one loop, sliced three ways

The terms **wake / recurrence / cadence / pace / autonomy** are not five features. They are **one judgment loop, sliced along the FOUNDATIONS dimensions and gated by the operator's trifecta.** Hold the whole thing this way:

> A **wake** is the atom. **Recurrence + cadence** decide *when* wakes happen. **Budget** bounds total *cost* (the operator's dollar envelope; replaces the retiring "pace" dial — §12a). **Autonomy** decides what a wake is allowed to *do* without the operator. The loop's purpose is **self-improvement**: the Reviewer authors its own cadence *and allocates wakes within the budget* against operator intent + ground truth.

**The orthogonal-dials map** (the operator's trifecta — ADR-298 D11). Three dials, three FOUNDATIONS dimensions, three different questions. They are deliberately orthogonal — none touches another's axis:

| Dial | Dimension | Substrate | Question it answers | Who owns it |
|---|---|---|---|---|
| **Budget** *(replaces "Pace" — §12a)* | Trigger (Axiom 4) — cost envelope | `governance/_budget.yaml` *(today `_pace.yaml`, retiring)* | *How much* can the operation spend? | Operator declares; Reviewer allocates wakes within it |
| **Autonomy** | Mechanism (Axiom 5) | `governance/_autonomy.yaml` | *How far* does a verdict bind without a click? | Operator only |
| **Identity (persona)** | Identity (Axiom 2) | `persona/IDENTITY.md` + `principles.md` | *How* does the agent reason? | Operator authors; Reviewer refines within bounds |

*Trifecta naming note: ADR-298 D11 named this "Pace + Autonomy + Identity." Post-§12a the first dial retires from "pace" (tempo) to "budget" (cost envelope) — same Trigger-dimension slot, honest concept. "Pace + Autonomy + Identity" survives as the historical name; the live dials are **Budget + Autonomy + Identity**.*

And the irreducible unit they all act on:

| Unit | Dimension | What it is | Authored by |
|---|---|---|---|
| **Wake** | Trigger | The atom of agent activity — *something changed, judgment is warranted, now* | Kernel (one of five sources) |
| **Recurrence** | Trigger | A time-driven wake's config — `{slug, schedule, prompt, mode}` in `_recurrences.yaml` | Operator + Reviewer (co-author via `Schedule`) |
| **Cadence** | Trigger | The composed shape of all Reviewer-authored wakes (recurrences + hooks + standing intent) | Reviewer (the self-improvement surface) |

**Why orthogonality matters.** Budget never touches what a wake *does* (that's autonomy). Autonomy never touches *how much* the operation spends or *when* a wake fires (that's budget + cadence). Persona never touches *cost* or *binding* (it shapes the reasoning). This separation is what lets the operator dial spend, trust, and reasoning-character independently — and it is what makes "self-working, self-improving" safe: you can give the agent full cadence-authoring authority *and wake-allocation-within-budget* (self-improvement) while keeping a hard autonomy floor (never_auto) and a hard dollar ceiling.

> **⚠ Two pieces in flight (2026-06-08).** This map states the *target* relationship; the **orthogonality is settled canon**. The first dial is mid-rename: **"pace" (tempo) retires → "budget" (dollar cost envelope)** — direction resolved, ADR pending (§12a). The self-improving loop's *driving mechanism* is still open (§11a). Read both before treating the substrate paths as final — `_pace.yaml` becomes a budget file.

---

## 2. The five wake sources

All wakes flow through one singular gateway: `services/wake.py::submit_wake_proposal(client, user_id, source, payload)`. Five exhaustive sources, enumerated in `WakeSource = Literal[...]`:

| Source | Triggering event | Typical payload |
|---|---|---|
| `cron_tick` | Scheduler walks `/workspace/_recurrences.yaml`; an entry's `next_run_at <= now` | recurrence dict, prompt, slug, capabilities |
| `addressed` | Operator sends a chat message to the Reviewer (SSE-streamed) | message content, session_id |
| `proposal_arrival` | An `action_proposals` row is created (e.g. trade-proposal, ship-proposal) | proposal_id, action shape, source |
| `substrate_event` | Scheduler walks `/workspace/_hooks.yaml`; a recent `workspace_file_versions` row matches a declared hook | hook slug, path, field_change, prompt |
| `manual_fire` | Operator invokes `FireInvocation(slug)` via chat (operator-explicit assertion) | recurrence slug, payload from recurrence |

**Five sources, one gateway.** No parallel invocation paths exist. Every Reviewer wake is attributable to exactly one source.

---

## 3. The wake evaluation funnel

`services/wake_evaluation.py::evaluate(client, user_id, source, payload)` returns one `FunnelDecision`:

| Decision | Meaning | Cost |
|---|---|---|
| `skip` | Tier 1 rejected — wake does not fire (budget exhausted, recent fire, mechanical short-circuit, etc.) | $0 |
| `tier_2_wait` | Tier 2 Haiku decided "no, not now" | ~$0.001 |
| `tier_2_observe` | Tier 2 Haiku decided "observe but don't escalate to full Reviewer" | ~$0.001 |
| `escalate` | Wake fires; full Reviewer Sonnet loop runs | ~$0.05-0.20 |
| `mechanical` | Recurrence with `mode=mechanical` bypasses Reviewer entirely; deterministic Python via `@primitive:` directive | $0 |

### Tier 1 — deterministic, zero LLM

`tier_1_decision(source, payload, budget: BudgetSignals)` is pure Python. Gates:

- **Balance check** — workspace `balance_usd > 0` (else `skip`)
- **Daily spend ceiling** — cumulative spend below operator-declared cap (else `skip`)
- **Daily judgment-recurrence cap** — judgment-cadence count below cap (else `skip`)
- **Per-slug min-interval floor** — most-recent fire of this slug older than configured floor (else `skip`)
- **Mode discriminator** — if recurrence is `mode=mechanical`, return `mechanical` (no Reviewer wake)
- **Operator presence** — `source=="addressed"` auto-escalates (operator-presence is wake-warrant)
- **Otherwise** — return `tier_2` to defer to Haiku

### Tier 2 — cheap Haiku call (~$0.001)

`tier_2_decision(client, user_id, source, payload)` — async Haiku call with minimal envelope. Asks: *"does this moment warrant your full attention?"* — given recent activity, standing intent, this trigger's prompt. Returns `tier_2_wait | tier_2_observe | escalate`.

### Escalate path

Only on `escalate` does the Reviewer's full real-time loop run (ADR-260): synchronous, bounded rounds (≤12 addressed/scheduled, ≤3 reactive per D8), governance envelope pre-loaded, real-time handoff narration to feed surface.

---

## 4. Recurrences (the cron_tick configuration)

Operator/Reviewer-authored time-driven wakes live in **`/workspace/_recurrences.yaml`** (constant `RECURRENCES_PATH` in `services/conventions.py`).

### Schema

Flat YAML list. Each entry:

```yaml
- slug: signal-evaluation                # stable identifier
  schedule: "*/30 9-16 * * 1-5"          # cron (UTC) | list of crons | null (reactive-only)
  mode: judgment                          # judgment (default) | mechanical
  prompt: |                               # addressed-equivalent message OR @primitive: directive
    Walk the universe. For each ticker, evaluate signal conditions...
  required_capabilities: [trading]        # optional — gated against connected platforms
  paused: false                           # optional — operator/Reviewer pause without archiving
  options:                                # optional — recurrence-specific config
    ...
```

### Mode discriminator (ADR-263)

- **`mode: judgment`** — Reviewer wakes with the prompt as envelope, reasons against substrate, may execute or propose actions.
- **`mode: mechanical`** — Deterministic Python via the `@primitive:` directive in the prompt body. No LLM cost. Used for substrate maintenance (e.g. polling Alpaca account balance into substrate).

### Schedule shapes

- **Cron string** — `"0 7 * * *"` (UTC plain) or semantic (ADR-268: `"@market_open - 30min"`, resolved against operator timezone + market state)
- **List** — multiple fires per period (e.g. `["@market_open + 5min", "@noon", "@market_close - 5min"]`)
- **null** — reactive-only; recurrence carries no time trigger but stays available for `manual_fire` source

### Authorship

`/workspace/_recurrences.yaml` is mutated **only** via the `Schedule` primitive (`services/primitives/schedule.py::handle_schedule`). Five actions: `create | update | pause | resume | archive`. Every write enforces `authored_by` per ADR-274 D1 (fail-fast on missing/empty). Authored-by taxonomy:

- `operator` — operator via chat or modal
- `reviewer:{occupant}` — Reviewer mid-loop via Schedule
- `system:bundle-fork` — initial scaffold from program bundle
- `system:bundle-fork-from-preferences` — initial scaffold from `_preferences.yaml` declarations

The scheduler index (`tasks` DB table) is reconstructable from filesystem state via `services/scheduling.py::materialize_scheduling_index()` — substrate is canonical; the DB row is a thin scheduling helper.

---

## 5. Hooks (the substrate_event configuration)

Substrate-event wakes live in **`/workspace/_hooks.yaml`**. Sibling shape to recurrences; same composition through the singular funnel.

### Schema

```yaml
- slug: pre-ship-audit
  event: substrate_change
  path_match: "/workspace/content_output/**/profile.md"   # fnmatch glob
  field_change:                                            # optional frontmatter matcher
    status: ready_to_ship
  prompt: |
    A piece advanced to ready_to_ship. Read it, ship-gate audit, decide.
```

### Behavior

The scheduler walks `/workspace/_hooks.yaml` at every tick. For each hook, it queries recent `workspace_file_versions` rows. On match (path glob + optional frontmatter field transition), it calls `submit_wake_proposal(source="substrate_event", payload={hook_slug, path, field_change, prompt})`.

### Authorship

`/workspace/_hooks.yaml` is mutated only via the `ManageHook` primitive (`services/primitives/manage_hook.py::handle_manage_hook`). Same five actions as Schedule, same fail-fast `authored_by` contract.

---

## 6. Operator preferences (the cadence-intent declaration)

**`/workspace/governance/_preferences.yaml`** is the operator's deliverable-cadence intent declaration — *"I want a pre-market brief at @market_open - 30min, a weekly review on Sunday 18:00 UTC, a quarterly signal audit at quarter-end."*

### Role in the architecture

Preferences are **intent**, not execution. The Reviewer reads `_preferences.yaml` at every wake (pre-loaded in governance envelope per ADR-276) and authors corresponding `Schedule` calls to materialize the preferences into `_recurrences.yaml`. ADR-275 D9-D11 establishes:

- **Initial preferences** are honored at bundle-fork time deterministically (`_seed_recurrences_from_preferences` in `services/programs.py`; authored_by = `system:bundle-fork-from-preferences`).
- **Subsequent preference edits** are reconciled by the Reviewer. Operator edits `_preferences.yaml`; Reviewer reads diff against `_recurrences.yaml`; Reviewer authors `Schedule(action="update"|"pause"|"archive")` to converge.

### Why the indirection?

Direct operator authoring of `_recurrences.yaml` was rejected because cadence is judgment-shaped, not declaration-shaped — schedule expressions, capability gates, prompt wording, and mode discrimination are Reviewer-domain concerns. Preferences let the operator declare *what they want* in operator vocabulary; the Reviewer translates to kernel vocabulary.

### Lock contract

`SHARED_PREFERENCES_PATH` is in `DEFAULT_REVIEWER_WRITE_LOCKS` per ADR-258 D9 + ADR-275 D6. **The Reviewer reads but never writes preferences.** Only the operator authors them.

---

## 7. Standing intent (the Reviewer's forward-looking state)

**`/workspace/persona/standing_intent.md`** (constant `REVIEW_STANDING_INTENT_PATH`) is the Reviewer's own working state — single-writer, forward-looking. Three canonical sections per ADR-284:

- **What I'm watching for** — substrate transitions, market conditions, operator messages the Reviewer expects to matter
- **What would change my next move** — explicit triggers that would shift the Reviewer's posture
- **Open questions to the operator** — surfaced for the operator to address at their convenience

### Read by Tier 2

`standing_intent.md` is pre-loaded into the Tier 2 Haiku envelope. It shapes the *"does this moment warrant my full attention?"* decision — if the wake aligns with what the Reviewer is watching for, Tier 2 escalates; otherwise it observes or waits.

### Written every cycle

The Reviewer writes (or re-writes) `standing_intent.md` at every judgment cycle terminus, even no-fire cycles. This is the audit trail of *why the Reviewer didn't act* — load-bearing for cross-session continuity and operator transparency.

---

## 8. The governance envelope

`services/reviewer_envelope.py::load_reviewer_governance_envelope(client, user_id)` is the singular shared helper for both addressed and reactive triggers (per ADR-276 + ADR-301 D5 — operating context block consolidated into the envelope helper). At every wake that escalates, the Reviewer perceives:

**Governance (kernel-universal — present in every workspace)**:
- `IDENTITY.md` — Reviewer occupant persona
- `principles.md` + `_principles.yaml` — judgment framework + thresholds
- `PRECEDENT.md` — historical decisions
- `MANDATE.md` — operator's standing intent
- `_autonomy.yaml` — delegation ceiling
- `_preferences.yaml` — operator's deliverable cadence preferences
- `_pace.yaml` — operator's pace budget (ADR-298 D11)

**Seat continuity (ADR-284 — kernel-universal)**:
- `OCCUPANT.md` — current seat occupant identity
- `standing_intent.md` — what the Reviewer was watching for last cycle

**Reviewer pulse (ADR-301 — kernel-universal)**:
- `_schedule_index.md` — literal `schedule:` string + mode + last_run_at + next_run_at + paused for every recurrence in this workspace
- `_recent_execution.md` — execution_events rollup for the last 24h with outcomes, costs, durations, per-wake-source counts

Both pulse files are **mechanically mirrored per scheduler tick** by `services.kernel_mirrors` (writes via `services.primitives.mirror_schedule_index` + `mirror_recent_execution`). Diff-aware — most ticks produce zero substrate revisions. Attribution `system:mirror-schedule-index` and `system:mirror-recent-execution` per ADR-209.

**Program substrate (bundle-declared via MANIFEST `substrate_abi.reviewer_wake_envelope`)**:
- `_operator_profile.md` — operator-authored ICP context (alpha-trader)
- `_risk.md` — risk envelope declarations (alpha-trader)
- `_performance.md` — money-truth substrate (alpha-trader)
- signal-files summary — recent substrate-event signals (alpha-trader)

**Operating context (ADR-274 + ADR-301 D5 — assembled by envelope helper)**:
- `operating_context_block` — `## Operating Context` block: now UTC + operator timezone + market state + workspace tenure. Composed by `services.reviewer_envelope.build_operating_context_block` (consolidated home post-ADR-301 D5; the prior `agents.reviewer_agent` location preserved as import re-export shim).

**Specs inventory (program-bundled capability library)**:
- `specs_inventory` — name + title list of `/workspace/operation/specs/*.md` files. Bodies read on demand via `ReadFile`.

Envelope load time is logged on `execution_events.envelope_load_ms` (migration 175) for capacity tuning — zero LLM cost observability.

### 8a. Pulse Discipline (ADR-301)

The Reviewer's persona frame instructs it to read `_schedule_index.md` and `_recent_execution.md` **before** reasoning about cadence or recent activity. This closes a documented failure mode: pre-ADR-301 the Reviewer's only basis for reasoning about its own cadence was memory + the persona-frame instruction to call `ListRevisions` + `GetSystemState` mid-loop. Under bounded tool-round budgets the Reviewer skipped the verification round and made up the schedule literal — see [`docs/evaluations/2026-05-24-045348-reviewer-schedule-self-misdiagnosis/findings.md`](../observations/2026-05-24-045348-reviewer-schedule-self-misdiagnosis/findings.md) for the empirical case (Reviewer asserted "signal-evaluation failed to fire 3× RTH today" when literal schedule is `@market_open + 15min` = 1 fire).

With the pulse files in the envelope, the Reviewer reasons from substrate, not memory. Schedule-hallucination class is structurally closed.

### 8b. Temporal model — how time reaches agent behavior

> **Canonical home for "how should I think about time for agent behavior."** Time concepts were previously scattered across FOUNDATIONS Axiom 4, ADR-268 (market-context-aware recurrences), and ADR-274 (trigger-authoring). This section is the singular synthesis; those ADRs point here.

**The governing principle (FOUNDATIONS Axiom 4 v8.5): time is *perceived*, not *stored*.** An agent does not read a clock out of workspace substrate; the runtime tells the wake-time envelope what time it is, fresh, on every wake. This mirrors Claude Code injecting the current date into each invocation. There is no `now` field in any `.md` or `.yaml` — and there must never be one, because persisted time goes stale between invocations.

Time acts on **three orthogonal planes**. Keep them separate when designing a persona's behavior — conflating them is the main source of confusion:

| Plane | Question it answers | Mechanism | Determinism |
|---|---|---|---|
| **1. Trigger** | *When should the agent wake at all?* | `_recurrences.yaml` schedules (incl. semantic `@market_open + 15min`) resolved against the bundle calendar by the scheduler (§2, §4) | Fully mechanical, zero LLM |
| **2. Perception** | *What temporal context must the agent know to reason well?* | The `operating_context_block` in the governance envelope (§8) — `now` + operator timezone + workspace tenure + (program-declared) market state | Projection, zero LLM |
| **3. Gate** | *What temporal constraint should mechanically block an action?* | A risk-gate / policy rule (e.g. `trading_hours_only` → `NyseUsCalendar.is_open_now()`), evaluated pre-execution | Deterministic, zero LLM |

**The kernel-universal vs program-declared split inside Plane 2** is the part that makes this scale across alpha workspaces:

- **Kernel-universal (every workspace, unconditionally):** `now` (UTC + operator-local), operator timezone, workspace tenure. Any program's agent can reason about time-of-day ("it's 2am operator-local, defer the noisy notification") and maturity ("3 days old, be conservative") with no per-program wiring.
- **Program-declared (only when the active bundle ships a `market_context:` block):** the **market state** line. Rendered via the graceful `if mc:` skip in `build_operating_context_block` — absent bundles simply don't get the line.

Each program's load-bearing temporal concept differs, and the design deliberately does **not** force "market state" onto all of them:

| Program | `market_context` in MANIFEST | Load-bearing temporal concept |
|---|---|---|
| alpha-trader | full (`us_equities`, `nyse_us`, sessions) | market sessions (RTH open/close) |
| alpha-author | declared but `exchange: operator_authored`, `trading_days: any` | operator-local time-of-day (publish windows); explicitly *not* market-gated |
| alpha-prediction | none | time-to-expiry / resolution |
| alpha-defi | none | block time (24/7, no calendar) |
| alpha-commerce | none | settlement cadence (daily reconciliation) |

**How to design temporal behavior for a new or stress-tested program** — ask one question per plane:
1. *When should it wake?* → author a `_recurrences.yaml` schedule (Plane 1). Use semantic schedules only if the program has a calendar.
2. *What must it perceive to reason well?* → for most non-trader programs, kernel-universal `now` + timezone + tenure is enough. Only extend the bundle `market_context` (or add an analogous envelope field) if a stress test shows a genuine reasoning gap. **Discover the need empirically; do not generalize speculatively** (same demand-pull discipline as ADR-224/225).
3. *What should mechanically block an action?* → a Plane-3 gate, only for programs with consequential external writes.

**Anti-pattern:** putting time-of-day *logic* into a persona's prose principles ("only trade 9:30–4"). That re-implements the clock in prose. Time-of-day belongs in Plane 1 (don't wake off-hours) + Plane 3 (mechanically block); Plane 2 gives the agent the *awareness* to reason about edge cases. Prose principles reason *about* perceived time — they never assert what time it is.

---

## 9. Telemetry — observability of wake activity

Two columns on `execution_events` populate at every Reviewer wake (migration 177):

```sql
ALTER TABLE execution_events
  ADD COLUMN wake_source TEXT,
  ADD COLUMN funnel_decision TEXT;
```

Constraints enforce the 5-source × 5-decision taxonomy. NULL-on-row means pre-migration; post-Checkpoint-1 (2026-05-17) every row carries both.

### Queries the operator should be able to run

- **24h wake distribution**: `SELECT wake_source, funnel_decision, COUNT(*) FROM execution_events WHERE user_id = $1 AND created_at > now() - interval '1 day' GROUP BY wake_source, funnel_decision`
- **Escalation rate**: ratio of `funnel_decision='escalate'` to total wakes — captures how often the Reviewer is fully firing.
- **Cost attribution**: `SUM(cost_cents)` grouped by `wake_source` — shows which sources drive spend.
- **Recurrence health**: ratio of `cron_tick`-sourced wakes that returned `escalate` vs `skip` vs `tier_2_wait` per slug.

Per ADR-291, `execution_events` is the unified cost ledger — wake telemetry and cost telemetry share one substrate.

---

## 10. The full lifecycle of one wake

End-to-end, in order:

1. **Trigger** — one of the five sources occurs (cron tick / chat message / proposal row / substrate transition / operator FireInvocation).
2. **Proposal** — source module calls `submit_wake_proposal(source, payload)`.
3. **Tier 1 funnel** — deterministic gates check balance, spend, judgment cap, min-interval, mode. Returns one of {`skip`, `mechanical`, `tier_2`, `escalate` for `addressed`}.
4. **Tier 2 funnel (if Tier 1 returned `tier_2`)** — Haiku call with minimal envelope including `standing_intent.md`. Returns `tier_2_wait | tier_2_observe | escalate`.
5. **Telemetry write** — `execution_events` row stamped with `wake_source` + `funnel_decision` + cost + duration.
6. **Mechanical short-circuit (if `mechanical`)** — `@primitive:` directive in recurrence prompt executes deterministic Python. Substrate updated. No Reviewer wake. End.
7. **Escalation (if `escalate`)** — `invoke_reviewer(trigger=..., context=...)` runs the bounded loop. Governance envelope pre-loaded. Operating Context block injected. Reviewer reasons, may author Schedule/ManageHook/WriteFile/ProposeAction, may execute under AUTONOMY gate. Feed surface narrates handoffs in real-time per ADR-260 D6. Standing intent re-written at cycle terminus.
8. **Cycle terminus** — `execution_events` row updated with final cost, duration, decision summary.

---

## 11. The Reviewer's three authoring surfaces

Per ADR-274 + ADR-275 + ADR-296 v2 D3, the Reviewer's authority over cadence is **explicit, attributed, and bounded**:

| Surface | Primitive | What it controls |
|---|---|---|
| `/workspace/_recurrences.yaml` | `Schedule` (create/update/pause/resume/archive) | Time-driven wakes — when the Reviewer fires periodically |
| `/workspace/_hooks.yaml` | `ManageHook` (create/update/pause/resume/archive) | Substrate-event wakes — what transitions the Reviewer watches |
| `/workspace/persona/standing_intent.md` | `WriteFile` (Reviewer-scoped) | Forward-looking working state — what the Reviewer expects to matter next |

**`FireInvocation` is NOT in `REVIEWER_PRIMITIVES`** (per ADR-296 v2 D3). The Reviewer cannot invoke itself ad-hoc. It can only:
- Author future cadence (`Schedule`, `ManageHook`)
- Declare what it's watching for (`standing_intent`)
- Be woken by one of the five sources

This is structurally load-bearing — the Reviewer's authority is over *standing intent* (what triggers should fire), not over *immediate invocation* (firing itself right now). The operator retains `FireInvocation` in `CHAT_PRIMITIVES` for explicit manual fire.

---

## 11a. The self-improving loop — kernel-universal shape, program-declared inputs

> **✅ IMPLEMENTED via [ADR-327](../adr/ADR-327-budget-and-the-self-improving-loop.md) D6 (Phase 5, commit `2f3e0a8`, 2026-06-08).** The loop is kernel-universal machinery + a domain-agnostic persona posture; the bundle declares only its inputs (its ground-truth file). The driving mechanism: a kernel mirror `_calibration.md` (`services/primitives/mirror_calibration.py`, sibling of the ADR-301 pulse files) correlates the Reviewer's cadence-authoring history against ground-truth outcome quality (per-recurrence fires vs proposals-produced + ground-truth head); the minimal persona frame's "reason forward from your operating context" posture extends to cite it. The bundle declares `substrate_abi.ground_truth` (alpha-trader → `_money_truth.md`). **Deferred (D6.d):** second-program (alpha-author) validation before the generalization is declared canon-complete.

### What "self-improving" actually means here

The thesis is "agents that improve with tenure." The honest, narrow, defensible definition: **the Reviewer adjusts *when and how* it operates — its cadence and its judgment — measured against ground truth, not against getting smarter.** Improvement is a substrate-and-cadence phenomenon, not a model phenomenon. The Reviewer has the *authority* to improve (Derived Principle 18 — it authors its own cadence via `Schedule`); the open work is giving it the *pressure and feedback* that make improvement happen reliably rather than only when the LLM happens to choose to.

### The loop shape (kernel-universal)

```
   operator intent                ground-truth substrate
   (mandate, preferences,         (program-declared file:
    budget envelope)                _money_truth.md for trader,
        │                           a corpus-coherence / revenue /
        │                           client-acceptance file for others)
        └───────────────┬───────────────┘
                        ▼
        Reviewer reasons at wake  (persona-frame instruction —
        "read your calibration trail + ground truth before
         reasoning about cadence; where your past cadence
         choices were falsified by ground truth, re-author")
                        ▼
        authors cadence (Schedule) + refines judgment (principles
        application) + rewrites standing_intent
                        ▼
        outcomes accumulate into ground-truth substrate ───┐
                        ▲                                   │
                        └───────────────────────────────────┘
```

The shape is **identical across every program.** Only two things differ per program, and both are *declarations*, not machinery:

| What the bundle declares | alpha-trader | alpha-author | alpha-commerce |
|---|---|---|---|
| **Ground-truth file** (the calibration substrate the Reviewer reasons against) | `_money_truth.md` | corpus-coherence / engagement file | revenue / cohort file |
| **What "outcome" means** (how the world's verdict reaches substrate) | fills → P&L → per-signal attribution | published-piece performance | settlement / churn |

Everything else — the reasoning posture, the envelope wiring that pre-loads ground truth + calibration trail, the `Schedule`-authoring authority, the standing-intent write — is **kernel.** This is the same kernel-vs-program split as the temporal model (§8b): the *machinery* is universal; the *inputs* are program-declared via MANIFEST `substrate_abi.reviewer_wake_envelope`.

### Why kernel + persona-frame, not per-bundle scaffolding

The current state (status quo): alpha-trader ships `outcome-reconciliation` (a judgment recurrence that folds fills into `_money_truth.md`) and a persona-frame that mentions money-truth. Every new program would re-invent this. That is exactly the over-scaffolding the operator flagged.

The target: the **persona-frame carries a domain-agnostic improvement posture** ("read your calibration trail and the active program's ground-truth file before reasoning about cadence; re-author cadence where ground truth has falsified a prior choice"), and the **envelope pre-loads whatever the bundle declared as its ground-truth file.** A new program becomes "declare your ground-truth file in MANIFEST" — no new loop code, no new recurrence shape, no persona-frame fork.

> Note the alignment with §3.2.1 of `agent-composition.md`: the *rules of judgment* (including stewardship-of-intent) already live in each program's `principles.md`, and the *reasoning posture* lives in the persona-frame. The self-improving loop is the cadence-axis instance of the same partition — domain flavor in `principles.md` + program-declared ground-truth file; universal posture in the persona-frame.

### The open questions for discourse

1. **What is the calibration-pressure mechanism?** Today the Reviewer *may* re-author cadence if it chooses. What injects *pressure* — a structured "your last N cadence choices produced stale/low-value outcomes" signal in the envelope? Is that a new mirror file (like `_recent_execution.md`) that correlates cadence-fires against outcome quality? This is the thinnest-mechanized part of the whole framework (Finding A).

2. **How does the bundle declare its ground-truth file generically?** A MANIFEST key (`substrate_abi.ground_truth: operation/.../_money_truth.md`)? Does the persona-frame reference it by role ("your ground-truth file") rather than by name, so the same prompt works across programs?

3. **What's the second-program validation?** The loop generalizes on paper; it has only ever been validated against money-truth (one data point). The improvement claim is real for trader; for alpha-author "cadence improvement against corpus-coherence" is unproven. Demand-pull discipline (per §15 #6): build the generalization, but validate the loop against a second program's stress test before declaring it canon.

### Per-workspace sovereignty — the property that bounds the loop

The self-improving loop is a *bounded* recursive-self-improvement loop: the Reviewer improves the dial it controls (cadence + judgment-within-mandate), against kernel-written ground truth it cannot author (`_calibration.md` + the program's ground-truth file), within a budget it cannot raise (`governance/_budget.yaml`, locked from the Reviewer per `CALLER_WRITE_POLICY["reviewer"]`). **Per-workspace sovereignty is the fourth fence, and it is the one that keeps the loop's blast radius equal to exactly one operator's budget.**

Every revision in `workspace_file_versions` is scoped `(user_id, path)`; the blob store (`workspace_blobs`) is content-addressed and shared for dedup, but *scoping lives at the revision layer*, not the blob layer. There is no cross-workspace learning, no shared persona priors, no marketplace of calibrated Reviewers. Each operator's loop is sovereign: one operator's Reviewer re-authoring its cadence cannot affect another operator's substrate, calibration trail, or envelope.

This is a **load-bearing safety property, not an incidental implementation fact.** It is what keeps YARNNN structurally outside the multilateral-coordination regime that Anthropic's "Recursive Self-Improvement" framing worries about — there is no compounding across operators, so there is nothing to coordinate. The moment cross-workspace learning is introduced (shared persona priors, a marketplace of calibrated Reviewers, federated calibration), that whole problem is imported: a misaligned cadence choice could propagate beyond the operator who authored it. **Treat any future cross-workspace-learning ADR as crossing this tripwire — it must explicitly re-derive the containment story the per-workspace boundary currently provides for free.** See `docs/analysis/moat-architecture-audit-2026-06-08.md` §2 (Claim 4) + §4.

---

## 12. Cadence and cost — the upstream gate

Cadence is the **upstream cost gate**; autonomy (delegation) is the downstream action gate.

| Concern | Mechanism | Effect |
|---|---|---|
| **How often the Reviewer fires** | Cadence (`_recurrences.yaml` + `_hooks.yaml` + Tier 1/2 funnel) | Determines wake frequency × escalation rate |
| **What the Reviewer can do when it fires** | Autonomy (`_autonomy.yaml` delegation ceiling) | Determines which verdicts auto-execute vs require operator approval |

A workspace with high cadence (many recurrences, low min-intervals, broad hook matching) burns judgment budget regardless of autonomy posture. A workspace with restricted autonomy still pays for every wake that escalates — the Reviewer reasoned, even if it can't execute.

**The implication for operator transparency:** cadence visibility is at least as important as autonomy visibility in the operator UI. Today (2026-05-21) the cockpit shows autonomy at `/workspace` Delegation card; cadence visibility is fragmented across `/schedule` (recurrence list, no attribution), `/work` (deliverable runs), and `execution_events` (DB-only, not surfaced). Closing that gap is downstream work — see [`docs/design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md`](../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md) for the parked surface-model discussion.

### Pace as the workspace-wide rhythm budget (ADR-298 D11 + ADR-300)

> **⚠ HISTORICAL — pace was DELETED by ADR-327 (2026-06-08).** This subsection documents what pace *was* (a population guardrail / drain throttle) for trace continuity only. The code described below no longer exists (`services/pace.py` deleted, `_pace.yaml` collapsed into `_budget.yaml`). For the live model read §12a.

Inside the cadence/cost gate above, **pace** is the workspace-wide budget that bounds total wake frequency. Pace is the Trigger-dimension dial of the **Pace + Delegation + Identity** operator trifecta (canonized by [ADR-298 D11](../adr/ADR-298-reviewer-wake-queue-and-pace.md)). The operator picks one of `hourly | daily | weekly | continuous`; the Schedule primitive pace-gates every new recurrence at declaration time (ADR-298 D5), refusing any creation that would push the total declared fire-frequency past the budget.

The atomic operator-facing edit surface for pace is **`/pace`** (Document archetype, 16th kernel surface — [ADR-300](../adr/ADR-300-pace-as-atomic-kernel-surface.md)). `PaceStatusItem` (system-status popover; `PaceBadge` already deleted per ADR-297 D20) consumes `api.pace()`. Pace is distinct from:

- **Cadence** — the per-recurrence taxonomy (`recurring | reactive`) surfaced on `/cadence`.
- **Schedule** — the per-recurrence cron string field on a recurrence YAML.

All three are Trigger-dimension concepts (Axiom 4) at different scopes. Pace is workspace-wide; Cadence is per-recurrence framing; Schedule is per-recurrence timing.

---

## 12a. Pace re-check → Budget reframe (pace retires)

> **✅ IMPLEMENTED via [ADR-327](../adr/ADR-327-budget-and-the-self-improving-loop.md) (Phases 1–6, 2026-06-08).** **"Pace" as a tempo/wake-frequency dial retired entirely; replaced by a dollar budget over a timeframe** (`governance/_budget.yaml`, collapsing the former `_pace.yaml` + `_token_budget.yaml`). Tempo is the Reviewer's allocation problem within the budget (the self-improving loop, §11a), not an operator dial. Backend: `services/budget.py` + Tier-1 window-budget gate (scheduled-hard/reactive-warn) + deleted pace machinery (−1922 LOC) + dissolved lane split. Frontend: `/budget` surface with window-to-date utilization + `/pace`→`/budget` redirect. The diagnosis below is preserved as the *why*; ADR-327 §6 records the implementation outcome.

### The diagnosis: the code and the UI describe two different concepts

**What pace does in code today** ([`services/pace.py`](../../api/services/pace.py), [`services/wake_drainer.py`](../../api/services/wake_drainer.py), [`services/primitives/schedule.py`](../../api/services/primitives/schedule.py)):
- **Declaration-time**: refuses a new `_recurrences.yaml` entry if total cron fire-frequency would exceed the budget (`check_population_constraint` → `pace_exceeded` error).
- **Drain-time**: throttles the *paced lane* of the wake queue to a minimum interval between drains (`paced_lane_eligible_to_drain`).

That is a **population guardrail** — "don't let cron declarations exceed a budget; throttle the lane if they pile up."

**What the UI sells** (`web/components/workspace-concepts/PaceCard.tsx`): *"How often the Reviewer wakes through the paced lane."* Four tiers — `Weekly ~7×/wk`, `Daily ~24×/day`, `Hourly ~168×/day`, `Continuous` — presented as a **tempo preference** the operator picks ("how fast do you want your agent to work").

**These are different concepts wearing the same word.** Two concrete consequences of the mismatch:

1. **The dial is inert in the common case.** The live alpha-trader workspace has 2 judgment recurrences firing ~twice/day. Picking `weekly` vs `hourly` changes *nothing observable* — both ceilings are far above the actual fire rate. The operator believes they're setting the agent's rhythm; they're setting a ceiling the cadence already lives under.
2. **It only bites in the over-declaration case** — it's a guardrail that activates when (operator or Reviewer) declares more cron than the cap allows. That's a useful safety property, but it is *not* "how often your agent works."

**And there are already TWO cost/frequency governance files, not one.** The ADR-327 research surfaced that `_pace.yaml` (frequency cap) sits beside `governance/_token_budget.yaml` (`daily_spend_ceiling_usd` — a *real, enforced* Tier-1 spend gate via `services/token_budget.py` + `BudgetSignals`, plus `max_judgment_recurrences_per_day` + a per-slug `min_interval` floor). [ADR-313](../adr/ADR-313-fire-frequency-gate-partition.md) audited the two, named the boundary ("pace owns drain-rate; token-budget owns cost + per-slug floor"), and chose to *keep both* — fixing the *developer*-facing confusion with documentation. It did not touch the *operator*-facing confusion (the cap-vs-vibe-vs-truth problem below). The budget reframe dissolves the partition: once "how often" is no longer an operator dial, pace's drain-rate gate has no operator-facing input left, and the two files collapse into one `_budget.yaml`. **The vestigial `monthly_budget_usd` field on `_pace.yaml` (parsed, displayed, zero enforcement) was the half-built shadow of this — the budget concept already wanted to exist.**

### The root error the operator named (2026-06-08)

The four-tier dial smears **three different numbers** into one control, and they contradict each other:

1. The **ceiling** the code enforces ("at most 24 fires/day" for `daily`).
2. The **label** ("Daily") — a tempo vibe that doesn't match the ceiling. *"Daily" reads like ~hourly to a layperson* ("24 hours, so once an hour") — the label fights its own number.
3. The **actual wake count** (~2/day for live alpha-trader) — the truth, shown nowhere.

A dial that conflates a cap, a vibe, and a hidden truth cannot produce a correct mental model. And the "unequal distribution" objection is fatal to any frequency framing: wakes cluster at market-open, so *no* single frequency word ("daily", "hourly") is ever honest — the distribution is the Reviewer's, not a uniform rate.

### The deeper tension with self-improvement

If the Reviewer authors its own cadence against ground truth (§11a), then **"operator sets how often the agent works" fights "agent figures out its own cadence."** Tempo is the *agent's* job — a separate operator tempo-dial is the operator second-guessing the exact thing the agent exists to figure out. The operator's *legitimate* concern was never "how often"; it was **"how much will this cost"** and **"don't run away."** Both are budget concerns, not tempo concerns. Pace was always a budget wearing a frequency costume.

### The settled reframe: pace retires, a dollar budget replaces it

**One concept, singular, absorbing.** There is no separate tempo dial and no separate "pace." The operator declares **one dollar budget over a timeframe** (`$X/month`); the Reviewer allocates judgment wakes within it against ground truth. Tempo intent ("morning brief, quiet otherwise") is not a dial — it lives where standing intent already lives (`MANDATE.md` / `_preferences.yaml`), read every wake. **One loop, three inputs: budget (envelope) + mandate (intent) + ground truth (calibration).**

| Old (retired) | New (singular) |
|---|---|
| `_pace.yaml` `kind: weekly\|daily\|hourly\|continuous` (drain-throttle) | A dollar budget over a timeframe (`$X/month`) — the operation's spend envelope |
| `monthly_budget_usd` (vestigial, zero enforcement) | **This becomes the concept** — the single hard gate |
| Drain-throttle (`paced_lane_eligible_to_drain`) as the cost guarantee | Cost guarantee moves to the budget gate; throttle dissolves (or survives only as a stampede smoother, see Q1) |
| Tempo as an operator dial | Tempo as Reviewer allocation within the budget (§11a self-improving loop) |
| "Reviewer wakes ~24×/day" (a lie) | "Funds ~$X of judgment/month — the Reviewer spends it where the work is" |

**What counts against the budget** (resolved 2026-06-08): **every Reviewer judgment wake — scheduled *and* reactive (proposal / chat / hook).** Mechanical recurrences are **free and out of scope** (they never wake the Reviewer; track-positions firing every minute is $0 and irrelevant to the budget). The budget is denominated in **dollars** because that's what the operator actually pays — and once it's dollars, reactive wakes *must* count, because they cost real dollars. A budget that excluded them would understate the invoice.

### Singular-implementation scope (no coexistence — pace is deleted, not deprecated)

Per the project's Singular Implementation discipline, the reframe **deletes** the pace concept end-to-end; it does not leave a pace dial beside a budget concept. ADR scope spans backend **and** frontend:

**Backend deletions:** `services/pace.py` (`parse_pace_yaml`, `cron_fires_per_day`, `check_population_constraint`, `pace_at_least_as_frequent`, `min_interval_seconds`), the `pace_exceeded` gate in `services/primitives/schedule.py`, `paced_lane_eligible_to_drain` in `services/wake_drainer.py` (and the paced/live lane *split* if the throttle fully dissolves — see Q1), the `_pace.yaml` envelope read in `reviewer_envelope.py`, the `SHARED_PACE_PATH`/`GOVERNANCE_PACE_PATH` constant, the activation default-seed in `services/programs.py`, and the bundle `minimum_pace` gate.
**Backend additions:** one dollar-budget substrate file (rename/repurpose `_pace.yaml` → a budget file, or a new `governance/_budget.yaml`), a **real Tier-1 funnel gate** in `wake_evaluation.py` (`skip` when month-to-date spend ≥ budget — reads the existing `execution_events` cost ledger per ADR-291), and a budget-utilization rollup.
**Frontend deletions:** `web/components/workspace-concepts/PaceCard.tsx`, `web/app/(authenticated)/pace/page.tsx` (the `/pace` atomic surface, ADR-300), `web/components/shell/system-status/PaceStatusItem.tsx` (the system-status popover; `PaceBadge` already gone per ADR-297 D20), `web/lib/content-shapes/pace.ts` (`useCockpitPace`, `paceKindLabel`, `PaceKind`), and the `api.pace()` client namespace (`web/lib/api/client.ts` `/api/pace` + `api/routes/pace.py`).
**Frontend additions:** one budget surface (the renamed atomic surface) that shows the dollar budget **and its month-to-date utilization** (the two-number control: "set $X/mo" + "$Y used, Z days left, on pace"). The control *position* in the cockpit stays (operators still have one governance dial here); only its meaning + data change.

### Two hard problems the reframe inherits (ADR must answer these)

1. **"One budget for all judgment wakes" means a chatty operator can starve scheduled work.** 40 chat turns today draw down the budget meant for tomorrow's signal-evaluation. Resolution shape (to ratify in ADR): **reactive wakes warn-but-don't-block** (operator presence stays warrant — never "you've used up your chat budget"), while **scheduled wakes get first claim** on remaining budget. This is a priority rule on the Tier-1 gate, not just a counter.

2. **A dollar budget is only honest if paired with a utilization surface.** "$12 of $50 used, 18 days left, on pace" — the data exists (`execution_events` unified cost ledger, ADR-291) but is **DB-only, surfaced nowhere** (the §15 #4 transparency gap). The budget concept has a hard dependency on this surface; you cannot ship "set a budget" without "here's where it went." This is net-new FE + a rollup, in the same ADR.

### Remaining open question for the ADR

1. **Does any throttle survive?** If the budget gate is the hard ceiling, is there residual value in a minimum-interval *stampede smoother* (preventing many queued wakes from draining in one burst), or does the paced/live lane split dissolve entirely? Leaning dissolve — the lane split existed to serve the pace throttle; with pace gone its reason to exist goes too. Confirm against the wake-queue's single-in-flight behavior before deleting.

---

## 13. Substrate locations — definitive map

| Path | Writer | Reader | Contract |
|---|---|---|---|
| `/workspace/_recurrences.yaml` | `Schedule` primitive (operator, Reviewer); bundle fork | Scheduler (`cron_tick` source), Reviewer (governance envelope), operator (read-only) | Singular cadence substrate; one execution shape via `mode` discriminator |
| `/workspace/_hooks.yaml` | `ManageHook` primitive (operator, Reviewer); bundle fork | Scheduler (`substrate_event` source at every tick), Reviewer | Substrate-event wake declarations |
| `/workspace/governance/_preferences.yaml` | Operator only (bundle fork seeds initial) | Reviewer (governance envelope; reconciles changes) | Operator's deliverable cadence intent; Reviewer-write-locked |
| `/workspace/persona/standing_intent.md` | Reviewer (cycle terminus) | Reviewer (next wake, Tier 2 envelope) | Reviewer's forward-looking state |
| `/workspace/governance/_autonomy.yaml` | Operator only | `should_auto_execute_verdict()` gate; governance envelope | Delegation ceiling + paused state |
| `/workspace/governance/_pace.yaml` ⚠ **retiring → `_budget.yaml`** (§12a) | Operator only (path in `DEFAULT_REVIEWER_WRITE_LOCKS`); bundle fork at activation seeds initial | *Today:* `Schedule` primitive pace-gate (ADR-298 D5); governance envelope; `/pace` surface. *Post-budget-ADR:* a Tier-1 funnel cost gate reading month-to-date spend from `execution_events` | *Today:* workspace-wide rhythm budget (`kind` field). *Post-ADR:* a dollar budget over a timeframe; tempo dissolves into Reviewer allocation (§12a). Singular replacement — no pace/budget coexistence. |
| `execution_events` (DB, migration 177) | `services/wake.py` (every wake) | Operator queries, telemetry | Wake source + funnel decision + cost + duration |
| `workspace_file_versions` (DB, ADR-209) | Every substrate write | Hook walker, ListRevisions/ReadRevision primitives | Attributed revision chain — provenance of every cadence change |

---

## 14. What to read next

- **For the Reviewer's reasoning model**: [`reviewer-substrate.md`](reviewer-substrate.md)
- **For the operator's view of invocations**: [`invocation-and-narrative.md`](invocation-and-narrative.md)
- **For the substrate-attribution model**: [`authored-substrate.md`](authored-substrate.md)
- **For the wake-source full audit**: [`adr296-canon-and-runtime-audit.md`](adr296-canon-and-runtime-audit.md)
- **For ADR-296 v2 implementation scope**: [`adr296-implementation-scope.md`](adr296-implementation-scope.md)
- **For the parked frontend surface question**: [`../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md`](../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md)

---

## 15. Open hardening questions (not blocking)

Items the audit surfaced that are not architecturally drift but worth ADR attention before scale:

1. **Tier 2 prompt and contract codification** — ADR-296 v2 D2 names the *intent* of the Tier 2 Haiku ("does this moment warrant your full attention?") but the exact prompt template is implementation-internal. Worth lifting into canon for prompt-stability discipline.

2. **Mechanical-mode dispatcher path documentation** — ADR-261 D1 + ADR-263 establish `mode=mechanical` recurrences execute via `@primitive:` directives, but the exact dispatcher entry point (`invocation_dispatcher.py::dispatch_mechanical_recurrence` or similar) is not surfaced in public-API docs. Implementation exists; documentation lags.

3. **Multiple-fires-per-recurrence list resolution** — ADR-268 allows `schedule: [list]` for multiple fires per day. The scheduler's resolution of the list to individual `next_run_at` values is implementation-internal. Worth a one-paragraph addition to ADR-261 or this doc.

4. **Operator-visible cadence surface** — `_preferences.yaml` is read by the Reviewer at every wake but never displayed in the operator UI. `standing_intent.md` is similarly invisible. `_hooks.yaml` entries don't appear anywhere. This is **the largest operator-transparency gap** and the prompt for the surface-model discussion at [`docs/design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md`](../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md).

5. **Standing intent → Tier 2 envelope contract** — `standing_intent.md` is described as shaping Tier 2 reasoning, but the exact way it's surfaced into the Haiku call (verbatim inclusion, summarized, structured?) deserves explicit contract documentation. Drift-resistance discipline.

6. **`market_context` shape is equities-vocabulary** (Plane 2, §8b) — the program-declared market-state slot uses `exchange` / `sessions` / `calendar` keys shaped for equities. alpha-prediction (needs *time-to-expiry*) and alpha-defi (needs *block time*) won't fit `sessions: {regular_hours...}`. When a second program's stress test reveals a temporal-perception gap, resolve it then — either a more abstract `market_context` shape or a program-specific envelope field beside it. **Demand-pull: do not abstract before a second program has spoken** (the kernel-vs-program over-design trap, per the [2026-06-04 temporal-awareness audit](../evaluations/2026-06-04-temporal-awareness-kernel-vs-program-audit/findings.md)). Today only trader (sessions) and author (explicitly market-agnostic) populate it.

7. **Risk-gate calendar hardcoded to `nyse_us`** (Plane 3, §8b) — `risk_gate._nyse_calendar()` returns `get_calendar("nyse_us")` even though the bundle declares `market_context.calendar`. Harmless while exactly one execution-bearing program exists (alpha-trader). The moment a second execution program ships with a different calendar, the gate must resolve its calendar from the workspace's `market_context.calendar` instead of hardcoding. Flagged in `risk_gate.py`; bounded, known debt.

These are hardening opportunities, not architectural drift. Cadence + wakes are first-class in the kernel as of 2026-05-20 (ADR-296 v2 fully implemented). The remaining work is observability, transparency, and discipline-of-documentation.
