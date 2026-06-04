# Eval-suite catch-up AUDIT — drift between declared suites and shipped canon

**Date**: 2026-06-04
**Hat**: B (external developer surface — toolchain that probes the system). This is a criterion-first audit. It maps drift and recommends Hat-B suite work + a small number of Hat-A canon gaps. It does **not** mutate suites — criterion work precedes mutation (README §"criterion-declaration discipline").
**Scope**: the gap between the declared eval suites/scenarios (`docs/evaluations/eval-suites/`, `scenarios/`) and canon shipped since the last framework-level catch-up (`2026-05-30-eval-suite-framework-update-AUDIT.md`).
**North star this audit clears the path toward**: the advisory-trader E2E validation harness — *"would a real trader trust this verdict and return tomorrow?"* (see §6). Priorities below are ordered by proximity to that destination, not by ease.

> Read order: this doc → `EVAL-SUITE-DISCIPLINE.md` (the suite shape) → `README.md` (criterion discipline) → the prior catch-up (`2026-05-30-eval-suite-framework-update-AUDIT.md`). This doc is the *delta* since 2026-05-30.

---

## §0 One-paragraph state of the world

The 2026-05-30 framework update built the v2 harness (C1–C7) and authored two v2 suites. Since then, **the harness itself has not gone stale** — wake/pace, surface/shell, and temporal/market canon all moved, but none of it breaks the *runner* or invalidates the *suite shape*. What moved is two things the suites must absorb. **First, the Reviewer architecture the suites exercise was re-published** (ADR-315 seat/occupant carve → `api/agents/occupant_contract.py`) and the Reviewer's standby posture was re-specified (ADR-314 frame-indexes-intent). The suites don't yet assert against the published contract, and one new posture cell (standby/bare-kernel) has zero coverage. **Second — and this is the load-bearing finding — the entire declared suite surface is `persona: yarnnn-author`.** All three eval-suites carry `persona: yarnnn-author`; there is **no advisory-trader judgment suite at all**. The only trader coverage is scenario-level (`warm-start-auto-execute`, `cold-start-governance-self-amend`, `post-refusal-self-amendment-probe`) and it validates the **auto-execute (autonomous capital) path** — the opposite of the beachhead's *advisory* mode. The catch-up that matters most is not fixing a stale clause inside the author suite; it is that **the eval suite is pointed away from the market we decided to validate.** Two genuinely new behavioral surfaces (ADR-310 judged interop writes; ADR-315 contract conformance) have zero coverage. And `yarnnn-author-baseline.yaml` is a self-deprecated v1 corpse still sitting in `eval-suites/` (Singular-Implementation smell).

---

## §1 Per-suite criterion audit (criterion-first, per README discipline rule 0)

For each declared suite: is its criterion still **well-formed** against shipped canon, and is the suite **stale / current / missing-coverage**?

### §1.1 `yarnnn-author-judgment.yaml` — **CURRENT (criterion well-formed), with one missing cell**

- **Criterion**: "in a concrete known situation, does the Reviewer reason the way a domain editor holding the yarnnn-author mandate would?" (judgment-coherence read, §2.1).
- **Well-formed?** Yes. The `prior:` hypotheses (clean-voice approve-with-cite, anti-pattern defer-with-directive, pressure-resistance refuse-with-reason, pace-coherence structural read) all measure mandate-coherence, not a pre-declared cell. They honor §4.
- **Canon that touched it**:
  - **ADR-314** (frame indexes intent, does not assert it; Implemented 2026-06-02, `api/agents/reviewer_agent.py::_compute_minimal_frame`). Every eval `requires` `_autonomy.yaml field default.delegation equals autonomous` — i.e. **operating state**, MANDATE present. In operating state ADR-314 is *behaviorally identical* to the prior frame (the index resolves to the same decisive action). **So these six evals are not invalidated by ADR-314.** The gap is a *missing* eval (§3, the standby cell), not a stale one.
  - **ADR-315** (occupant contract). The suite asserts behavior (transcripts + substrate writes), not occupant internals — it does not couple to `_PERSONA_FRAME_SECTIONS` or `_compute_minimal_frame`. **Contract-clean.** No retarget needed.
  - **ADR-313** pace doctrine clarification (drain-rate, not token-budget): `pace-coherence` eval reads `_pace.yaml`/`_preferences.yaml`/`_recurrences.yaml` and reports alignment; it never asserts pace-as-token-budget. **Current.**
- **Verdict**: **CURRENT.** No stale priors. One missing-coverage cell (standby posture — §3.2).

### §1.2 `yarnnn-author-responsiveness.yaml` — **CURRENT (criterion now well-formed — the §4 stale-prior fix already landed)**

- **Criterion**: "when the operator changes governing substrate, does the Reviewer's next reasoning track the change?" (substrate-responsiveness read, §2.2).
- **Well-formed?** Yes — *and the 2026-05-30 audit's §4 stale-prior fix is present in the file.* Lines 28–45 + the eval priors now state the ADR-307 queue behavior ("bounded WriteFile QUEUES as `family='substrate'`; supersedes ADR-293 D10 fall-through-to-Clarify"). The prior catch-up's headline gap is **closed in the manifest.**
- **Residual check against newer canon**:
  - **ADR-310** (judged substrate). The responsiveness suite reads operator-authored mutations. ADR-310 introduces a *second* author class (foreign-LLM `yarnnn:mcp` writes that wake the Reviewer). That's a new surface this suite does not cover — but it's **additive missing-coverage**, not a stale prior in this suite. Logged as §3.1.
  - **ADR-315 contract**: the suite asserts `action_proposals.family='substrate'` shape-receipts (raw/{eval}/shape-receipts.md) — that's contract-shape assertion, which is exactly the ADR-315-correct level (assert the published `ReviewerOutput`/proposal shape, not occupant impl). **Contract-clean.**
- **Verdict**: **CURRENT.** The one previously-stale prior is fixed. No new stale clause introduced by post-05-30 canon.

### §1.3 `yarnnn-author-baseline.yaml` — **STALE (deprecated corpse; delete)**

- Self-labeled `DEPRECATED — split into two read-kind suites (2026-05-29)`. It is the v1 monolith superseded by §1.1 + §1.2.
- `run_eval_suite.py` does **not** load it (the `baseline` references in the runner are an unrelated snapshot-timing concept — `_baseline_at_time`, the pre-fire substrate snapshot).
- A self-deprecated suite manifest still living in `eval-suites/` is a **Singular-Implementation violation** (README discipline: one canonical path; delete legacy when replacing).
- **Verdict**: **STALE — archive/delete.** Recommendation §3.4.

---

## §2 The load-bearing finding — the suite surface points away from the beachhead

This is the finding the north star makes load-bearing, and it is not a clause-level staleness — it is a **coverage-orientation gap**.

### §2.1 All declared judgment/responsiveness coverage is `yarnnn-author`

| Suite | persona | read_kind |
|---|---|---|
| `yarnnn-author-judgment.yaml` | yarnnn-author | judgment_coherence |
| `yarnnn-author-responsiveness.yaml` | yarnnn-author | substrate_responsiveness |
| `yarnnn-author-baseline.yaml` (dead) | yarnnn-author | (v1 monolith) |

yarnnn-author is the **substrate-continuity archetype** (`sessions/alpha-author-autonomy-loop.md`): faster feedback, no capital, voice-quality ground truth. It is a legitimate and well-built suite. But the strategic decision (carry-over §0) is that the **first beachhead is independent/retail trading, advisory mode**, because P&L is the cleanest ground-truth scoreboard and advisory mode dissolves the capital-trust cliff. **The eval suite has zero judgment-coherence coverage for the persona class we decided to validate.**

### §2.2 The trader scenarios that exist validate the *wrong mode* for the beachhead

The three trader scenarios — all scenario-level, **no eval-suite wraps them** —:

- `warm-start-auto-execute.yaml` (`persona: kvk`): explicitly validates `should_auto_apply(action_class="capital") returning True under autonomous + verdict=approve` → `handle_execute_proposal` → Alpaca `submit_order` → `pending → executed`. This is the **fully-autonomous capital path.**
- `cold-start-governance-self-amend.yaml`: governance self-amendment discipline (principled refusal).
- `post-refusal-self-amendment-probe.yaml`: operator-pressure resistance on risk-envelope files.

The beachhead is **advisory** (Phase 0 of the graduated-execution model): Reviewer renders a verdict *the operator pulls the trigger on*. The trust question is not "does auto-execute fire correctly" — it's "**is the verdict one a real trader would trust and approve**." The existing scenarios test the auto-execute branch (correct to have, for the autonomous horizon) but **none reads the advisory verdict against trading ground truth** the way the author judgment suite reads voice quality against the voice criterion.

### §2.3 Why this is the catch-up that matters most

The 2026-05-30 audit caught the suite up to *the framework*. This audit's job (carry-over §4) is to clear the path to the *advisory-trader E2E*. The structural fixes worth prioritizing are the ones the **trader-trust loop depends on** — and the loop depends on a trader judgment suite existing at all. A perfectly caught-up author suite does not advance the north star by one inch.

---

## §3 New behavioral surfaces / missing coverage (zero current coverage)

Ordered by proximity to the advisory-trader north star.

### §3.1 [P0] Advisory-trader judgment suite — **MISSING ENTIRELY**

- **Canon it rests on**: alpha-trader bundle (`docs/programs/alpha-trader/reference-workspace/review/principles.md`), the graduated-execution Phase 0 (advisory), ADR-195 money-truth substrate (`_money_truth.md` / `_performance.md` as the P&L scoreboard), ADR-194 v2 Reviewer seat. The temporal-awareness finding (2026-06-04, CLOSED) just hardened the market-hours gate — the trader execution path is now correct enough to validate judgment against.
- **The gap**: there is no `alpha-trader-judgment.yaml` (substrate-responsiveness or judgment-coherence). No eval reads a trader verdict against accumulated trading context the way `clean-voice-approve` reads an author verdict against `_voice.md`.
- **The criterion this suite would declare** (operationalized for §6): given a signal-evaluation wake or an emitted trade proposal in **advisory (bounded) mode**, does the Reviewer (a) read `_money_truth.md` / `_risk.md` / `_operator_profile.md` / `principles.md` from the envelope, (b) render an approve/reject/defer verdict that cites the *specific* envelope condition (sizing vs `_risk.md` ceiling, regime vs `_regime.yaml`, expectancy vs threshold), and (c) land the verdict as a **queued proposal for operator approval** (advisory shape — `action_proposals` pending, NOT auto-executed)? The shape-receipt to capture: `family='capital'`/`'trade'`, `status='pending'`, `source='reviewer:*'`, **no auto-execute** under bounded.
- **The trust read** (the human judgment, §6): would a trader holding this mandate approve this verdict, or does it read as ungrounded / mechanical / missing the obvious risk?

### §3.2 [P1] Standby-state posture (ADR-314) — **MISSING**

- **Canon**: ADR-314 — frame indexes intent rather than asserting it; in **standby state (bare kernel, no MANDATE)** the Reviewer must "reason honestly about that absence rather than inventing intent." `api/test_adr314_substrate_conditional_posture.py` covers the *frame string* (6/6); nothing covers the *behavior* under a real bare-kernel wake.
- **The gap**: every author-judgment eval `requires` `delegation == autonomous` (operating state). No eval fires against a bare-kernel workspace to confirm the Reviewer doesn't confabulate a primary action that doesn't exist yet.
- **Operationalization**: activate a bare-kernel persona (no program forked), fire an addressed wake ("what should I do?"), read whether the response names the absence ("no mandate declared; activate a program to establish primary intent") vs. inventing direction. This is a judgment-coherence read with a `prior:` that a coherent installed-judgment-seat surfaces the absence honestly.
- **Note**: this is a *kernel-universal* surface (applies to author and trader alike), so it can live in either suite or a small `kernel-posture.yaml`. Lower priority than §3.1 only because the beachhead operator activates a program immediately.

### §3.3 [P1] Judged-interop write (ADR-310/311) — **MISSING**

- **Canon**: ADR-310 D2 (eventually-judged model) + the wired path: `remember_this` (foreign LLM via MCP) → `WriteFile` with `authored_by="yarnnn:mcp"` → `submit_foreign_write_wake()` (`api/services/mcp_composition.py:806`) → `submit_wake_proposal(source="substrate_event")` (`api/services/wake.py`) → drainer → `_invoke_substrate_event_wake` → Reviewer wakes with a `mcp-foreign-write-review` hook prompt.
- **The gap**: zero scenarios exercise a foreign-LLM write being judged. `author-wake-source-disambiguation.yaml` tests `wake_source` citation but only for an *addressed* (operator) wake — never a `substrate_event` from MCP. The wake path is code-wired + unit-tested at the gate (`test_adr310_mcp_write_gate.py`, 12 assertions) but has **no integration/behavioral coverage** that the Reviewer actually receives the foreignness signal and judges the write against ground truth.
- **Operationalization**: setup operator ground truth at a commons path; dispatch `remember_this` with `caller_identity="yarnnn:mcp"` (direct `dispatch_remember_this`, the scenario-runner path); assert (a) revision `authored_by="yarnnn:mcp"`, (b) one `wake_queue` row `source="substrate_event"` slug `mcp-foreign-write-review`, (c) drainer → Reviewer reads the write's foreignness + judges coherence with ground truth. A second eval: a foreign write that *contradicts* ground truth — does the Reviewer flag it?
- **Why P1 not P0**: it's the interop *distribution* face, not the beachhead *trust* loop. Strategically important (the moat's second face) but downstream of proving the advisory verdict works at all.

### §3.4 [P2] Contract-conformance assertion (ADR-315) — **PARTIAL → can harden**

- **Canon**: ADR-315 published `ReviewerContext` / `ReviewerOutput` / `REVIEWER_MODEL_IDENTITY` / `invoke_reviewer` in `api/agents/occupant_contract.py` (pure data, no LLM runtime). Hat-A gates already cover the contract (`test_reviewer_context_contract.py`, `test_f1_reviewer_telemetry_passthrough.py`, etc.).
- **The eval-side opportunity**: the suites assert *behavior*; they should keep asserting against the **published shape** (`ReviewerOutput.verdict/reasoning/confidence`, `action_proposals.family`), never against occupant internals (`_PERSONA_FRAME_SECTIONS`, `_compute_minimal_frame`, model-selection constants, round budgets). Current suites are already contract-clean (§1.1/§1.2). **This is a discipline note for the new trader suite (§3.1), not a fix to existing suites.** When §6's E2E harness is built, its shape-receipts must read `occupant_contract.py` field names, not reviewer_agent internals.

---

## §4 Surface/shell + wake/pace + temporal — assessed, **no eval impact**

For completeness, the canon clusters that moved but do **not** touch the eval suite:

| Cluster | ADRs | Verdict | Why |
|---|---|---|---|
| Surface/shell | ADR-308 (redirect transport), ADR-309 (two-register), ADR-312 (home as composition), ADR-316 (chat as dockable rail) | **OUT-OF-SCOPE** | Scenarios are backend Reviewer-behavior probes. Zero scenarios assert `/chat`, `/feed`, `/home`, `/cockpit`, register names, or route shape (grep clean). The suite would survive a wholesale route rename. |
| Wake/pace | ADR-298 (wake queue), ADR-313 (pace = drain-rate, not token-budget — doctrine clarification) | **CURRENT** | All pace evals (`pace-coherence`, `counterfactual-pace-raise`) read pace as drain-rate / fires-per-day. Zero token-budget assertions. ADR-313 is a conceptual partition clarification — no behavior changed, no eval changed. |
| Temporal/market | ADR-274 (envelope operating-context), ADR-268 (market calendar), 2026-06-04 temporal finding (CLOSED) | **CURRENT** | `counterfactual-mandate-tightening` correctly cites ADR-274/276 envelope reassembly. Market-calendar scheduling is bundle-static config, not a Reviewer-runtime behavior a scenario probes. The temporal finding's market-hours fix is a `risk_gate` wiring fix, fully resolved, and *enables* §3.1 (the execution path is now trustworthy enough to judge against). |

---

## §5 Where canon itself lacks a clear expected behavior (Hat-A flags, not Hat-B measurement)

Per README rule 0 sub-point 4: name the cases where the right next move is **canon work, not eval measurement.**

1. **Advisory-mode verdict shape under bounded autonomy for *capital* actions is under-specified for the eval.** ADR-307 settled that bounded `WriteFile` → `family='substrate'` queue. But the trader beachhead's advisory verdict is a *capital* action under bounded mode. Does an approve verdict in advisory mode produce a `family='capital'` queued proposal the operator approves, and is that the canonically-correct shape? The scenarios assume *autonomous* auto-execute; the *advisory bounded* capital path needs a canon receipt (an ADR clause or a validated execution_event) before §3.1's eval can declare its shape-criterion. **→ Hat-A: confirm/validate the bounded-mode capital queue shape (likely a small ADR-307 corollary or a validated receipt in the alpha-trader bundle), then §3.1 can assert against it.** Until then, §3.1's shape-receipt is a hypothesis, not a contract.

2. **"Trustworthy trader verdict" has no canonical operationalization yet.** The author suite has `_voice.md` as a declared ground-truth criterion the verdict is read against. The trader suite's analog is `_money_truth.md` + `_risk.md` + `principles.md` — but there is no canon clause stating *what makes a trader verdict mandate-coherent* the way the author MANDATE names the anti-slop floor. **→ Hat-A: the alpha-trader bundle's `principles.md` + MANDATE should name the verdict-coherence criteria explicitly enough that a `prior:` can be written from them.** This is the criterion-audit gate for §3.1 — write/confirm the canon criterion before building the suite. (This is precisely the 2026-05-25 lesson: don't measure against a criterion that isn't well-formed in canon.)

These two are the **gating Hat-A work** for the §6 destination — they are upstream of building the trader suite.

---

## §6 The destination (named, not built here) — advisory-trader E2E validation harness

The catch-up's purpose is to clear the path to re-pointing the eval suite as the **advisory-trader E2E validation harness**. The loop:

> operator declares mandate → recurrence fires (or signal proposal emitted) → Reviewer renders an **advisory** verdict against accumulated trading context (`_money_truth.md` / `_risk.md` / `_regime.yaml` / `principles.md`) → operator approves/rejects → outcome reconciles against P&L ground truth (`_performance.md`) → calibration accumulates over tenure (`decisions.md` / calibration trail).

The north-star criterion, operationalized: **"would a real trader holding this mandate trust this verdict and return tomorrow?"** — read as a judgment-coherence prose finding (§6.2 of EVAL-SUITE-DISCIPLINE), with the verdict's grounding (does it cite the *specific* envelope condition?), shape (advisory queued proposal, not auto-execute), and calibration-over-tenure (does the verdict-vs-outcome record improve?) as the three sub-reads. That criterion, operationalized and gated on §5's canon work, is what makes the eval suite the pre-flight check before 5 real fintwit/algo users.

---

## §7 Prioritized update plan (ordered by proximity to the north star, per DoD #4)

| # | Item | Hat | Type | Gating dependency |
|---|---|---|---|---|
| **1** | **[Hat-A first] Confirm advisory bounded-mode capital queue shape + write the trader verdict-coherence criterion into alpha-trader `principles.md`/MANDATE** (§5.1 + §5.2) | A | Canon | **None — this is the unblocker.** §3.1 cannot declare a well-formed criterion until this lands. |
| **2** | **Author `alpha-trader-judgment.yaml` advisory suite** (§3.1) — judgment-coherence reads of advisory verdicts against trading ground truth; shape-receipt = queued capital proposal, not auto-execute | B | New suite | Gated on #1 |
| **3** | Wrap the existing trader scenarios under a suite OR retire `warm-start-auto-execute` framing as the *autonomous-horizon* (Phase 1) suite, clearly separated from the advisory (Phase 0) suite #2 | B | Suite reorg | After #2 (don't conflate advisory and auto-execute) |
| **4** | Add judged-interop eval (§3.3) — foreign-LLM `remember_this` → Reviewer wakes → judges; one coherent + one contradicting fixture | B | New scenario + eval | None (independent of trader work) |
| **5** | Add standby-posture eval (§3.2, ADR-314) — bare-kernel addressed wake, Reviewer surfaces absence | B | New eval | None |
| **6** | **Delete `yarnnn-author-baseline.yaml`** (§1.3) — self-deprecated v1 corpse, Singular-Implementation cleanup | B | Cleanup | None — do immediately |
| **7** | Discipline note: new trader suite asserts against `occupant_contract.py` published shape, never `reviewer_agent.py` internals (§3.4) | B | Discipline | Folds into #2 |

**Sequencing logic**: #1 is the only true blocker (it's Hat-A canon work — the criterion must be well-formed in canon before the suite measures against it, per the 2026-05-25 lesson). #6 is a free immediate cleanup. #2 is the north-star item. #4/#5 advance coverage breadth but are off the critical path to the trader-trust loop.

---

## §8 Receipts (this audit's grounding)

- All three eval-suites carry `persona: yarnnn-author` — `grep -H "^persona:" docs/evaluations/eval-suites/*.yaml` (3/3 yarnnn-author).
- `yarnnn-author-baseline.yaml` self-labeled DEPRECATED (header lines 1–5); not loaded by `run_eval_suite.py` (the `baseline` refs there are `_baseline_at_time` snapshot timing, `run_eval_suite.py:489,493`).
- Trader scenarios validate auto-execute: `warm-start-auto-execute.yaml` §"What this validates" — `should_auto_apply(action_class="capital") returning True under autonomous`; `persona: kvk`.
- `yarnnn-author-responsiveness.yaml:28–45` carries the ADR-307 queue-not-Clarify prior (the 2026-05-30 §4 stale-prior fix is *present* — closed).
- ADR-314 Implemented 2026-06-02, frame-indexes-intent in `reviewer_agent.py::_compute_minimal_frame`; `test_adr314` 6/6 (frame-string coverage; no behavioral standby eval).
- ADR-315 published contract at `api/agents/occupant_contract.py` (pure data); `ReviewerContext`/`ReviewerOutput`/`REVIEWER_MODEL_IDENTITY`/`invoke_reviewer(trigger: Literal["addressed","reactive"])`.
- ADR-310 judged-interop wake path wired: `mcp_composition.py:806 submit_foreign_write_wake` → `wake.py submit_wake_proposal(source="substrate_event")`; gated by `test_adr310_mcp_write_gate.py` (12) — no integration/behavioral eval; zero scenarios reference `mcp`/`remember_this`/`yarnnn:mcp`/`substrate_event`-from-MCP.
- Wake/pace/surface/temporal grep-clean for eval impact (§4) — three survey passes, 2026-06-04.
- 2026-06-04 temporal-awareness finding CLOSED (`docs/evaluations/2026-06-04-temporal-awareness-kernel-vs-program-audit/findings.md`) — market-hours `risk_gate` now DST/holiday-correct via `NyseUsCalendar`; the trader execution path is trustworthy enough to judge against (enables §3.1).

---

## §9 Resolution (same session, 2026-06-04) — operator re-scoped to full autonomy; trader suite scaffolded

The operator re-scoped the trader north star from **advisory** (the audit's §2/§6 framing) to **full autonomy**: the Reviewer acts ALONE on capital under `delegation: autonomous`, and runs the daily P&L confirmation without intervention. Main persona = `kvk` (`kvkthecreator@gmail.com`). This re-scope is recorded here, and the §7 plan was executed against it.

### §9.1 The full-autonomy posture is already canon (the §5 Hat-A blocker substantially dissolved)

Reading the criterion-bearing canon (per the discipline gate) found the bundle **already ships** exactly the re-scoped posture:
- `_autonomy.yaml`: `delegation: autonomous` (operator-elected, ADR-269) + `never_auto: [close_position_market, cancel_other_orders]` + `_risk.md` hard caps. Full autonomy with a hard safety floor — not advisory.
- `principles.md`: the verdict-coherence criterion is **well-formed** — 7 hard rejection rules (sizing formula, signal attribution, stop, var budget, discretionary-vocabulary, regime scalar, regime freshness), 3 mandatory exit triggers ("silent stand-down forbidden"), capital-EV thresholds, and the mandatory cycle-closing contract (ReturnVerdict or stand_down + standing_intent; "text-only forbidden"). **The §5.2 "criterion not well-formed in canon" gap is resolved** — a `prior:` can be written directly from these.
- The judgment moments already exist as recurrences: `signal-evaluation` (@market_open+15min, judgment, inline ProposeAction per ADR-296 v2) + `outcome-reconciliation` (@market_close+1h, judgment).

So the §5.1 advisory-bounded-mode shape question is **moot under full autonomy** — `warm-start-auto-execute` already validates the autonomous auto-execute mechanism.

### §9.2 The one real Hat-A gap: the daily P&L email had no sender (ADR-317, built this session)

The operator's "Reviewer runs the daily P&L confirmation alone, I receive it without intervention" requirement hit a hard canon wall: **the Reviewer cannot send the email.** `platform_email_send_to_operator` is permanently excluded from `REVIEWER_PRIMITIVES` (the 2026-05-25 v4 canary proved it collapsed verdict quality ~74%). The intended post-judgment dispatcher (registry.py:451 comment) **did not exist** — `operator_notifications.daily_pnl_reconciliation` had zero live consumers.

**Built this session (Hat-A, ADR-317, Implemented):** `api/services/daily_pnl_email.py` — a post-judgment dispatcher fired after the `outcome-reconciliation` wake completes (`wake.py::_invoke_recurrence_wake`, slug-gated, best-effort), reads `_money_truth.md` windows + the operator's `operator_notifications` opt-in, sends an expository-pointer email (ADR-202 shape) via the system Resend wire. **Reviewer triggers; dispatcher sends.** Default-off (ADR-299). Regression gate `api/test_adr317_daily_pnl_dispatcher.py` 13/13 (locks: opt-in default-off, windows render without fabrication, `REVIEWER_PRIMITIVES` stays clean, hook slug-gated). No new env var (rides existing `RESEND_API_KEY` on API + Unified Scheduler), no Render parity drift.

### §9.3 The two-activity split (the operator's "running multi-day" instinct, resolved)

The operator's instinct — "I want the workspace itself running on multi-day" — exposed that the eval-suite harness (reset-to-clean, single-session, §3.1) and a live multi-day autonomous run are **two genuinely different validation activities**, and conflating them would fight the harness's spine. Resolved as a split, both built:

1. **Constructed-situation eval-suite** (`docs/evaluations/eval-suites/alpha-trader-autonomous-loop.yaml`, persona kvk, judgment_coherence) — the **pre-flight gate**. Three evals: `signal-auto-execute` (wraps `warm-start-auto-execute` — Singular Implementation, no duplication), `reconciliation-judgment` (new scenario `trader-reconciliation-judgment.yaml`), `eod-pnl-compose-and-send` (new scenario `trader-eod-pnl-send.yaml`, exercises the full ADR-317 path). Loads clean against the v2 runner; scenarios parse; persona resolves.

2. **Live multi-day autonomy demonstration** — `sessions/alpha-trader-autonomy-loop.md` re-pointed for the kvk full-autonomy run. This is the **tenure read** (does the loop close + calibration improve over a real week — the future compounding-loop read-kind, EVAL-SUITE-DISCIPLINE §2.3). The eval-suite is the gate before this is worth starting.

### §9.4 What remains (carried forward, not done this session)

- **The eval-suite has not had a live run.** It loads + parses; the first live read (judgment-suite-first per §7) is a separate Hat-B session — same gate EVAL-SUITE-DISCIPLINE §12 names for the author suites.
- **§3.3 judged-interop + §3.2 standby-posture** evals — still zero coverage, still off the trader critical path (audit §7 items #4/#5).
- **Second trader persona** (alpha-trader-2, "one or two like author") — deferred; kvk-only first per the operator's answer.
- The `operator_notifications.signal_fire_alert` + `regime_state_change_alert` opt-ins (also default-off) can adopt the same ADR-317 post-judgment-dispatcher shape in follow-on work.

### §9.5 Receipts (this resolution)

- `_autonomy.yaml` ships `delegation: autonomous` + `never_auto` floor — `docs/programs/alpha-trader/reference-workspace/context/_shared/_autonomy.yaml`.
- `principles.md` names the 7 hard rejection rules + mandatory exit triggers + cycle-closing contract — `docs/programs/alpha-trader/reference-workspace/review/principles.md`.
- ADR-317 dispatcher: `api/services/daily_pnl_email.py` + `wake.py::_invoke_recurrence_wake` slug-gated hook + `api/test_adr317_daily_pnl_dispatcher.py` (13/13) + `docs/adr/ADR-317-daily-pnl-post-judgment-dispatcher.md`.
- `REVIEWER_PRIMITIVES` excludes the email tool — `registry.py:431` (the architectural commitment ADR-317 honors, test-locked).
- Suite + scenarios load against v2 runner — `load_suite()` returns 3 evals; `trader-reconciliation-judgment.yaml` + `trader-eod-pnl-send.yaml` parse; persona `kvk` resolves in `docs/alpha/personas.yaml`.
- `yarnnn-author-baseline.yaml` deleted (§7 #6) + EVAL-SUITE-DISCIPLINE §7 "Executed" correction.
