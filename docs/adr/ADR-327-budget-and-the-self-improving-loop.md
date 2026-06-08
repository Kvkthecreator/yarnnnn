# ADR-327 — Budget and the Self-Improving Loop: Pace Retires, Cost Governance Collapses, Calibration Drives Cadence

**Status:** **Implemented (Phases 1–6, 2026-06-08)** · live-workspace migration script (`adr327_collapse_pace_tokenbudget_to_budget.py`) runs at deploy
**Date:** 2026-06-08
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon — real-operator-facing)

> **Discourse base:** the 2026-06-08 wake/pace/autonomy/recurrence/cadence audit + discourse, synthesized in [`cadence-and-wakes.md`](../architecture/cadence-and-wakes.md) §1a / §11a / §12a. This ADR ratifies the two in-flight sections of that doc and drives the code change. Receipts inline.

**Supersedes:**
- [ADR-300](ADR-300-pace-as-atomic-kernel-surface.md) entirely (the `/pace` atomic kernel surface — repurposed to `/budget`).
- [ADR-298](ADR-298-reviewer-wake-queue-and-pace.md) D4 (pace declaration `kind: hourly|daily|weekly|continuous`), D5 (pace-as-recurrence-population-constraint), D11 (the "Pace + Autonomy + Persona" trifecta naming — the *first* dial renames). **ADR-298's wake-queue (D1–D3, D6–D10) is NOT superseded** — single-lane execution, the queue substrate, cross-source dedup, and stale-lock reclaim are all preserved.
- [ADR-313](ADR-313-fire-frequency-gate-partition.md) (the Pace-vs-Token-Budget two-gate partition). ADR-313 named the boundary between two cost/frequency files and chose to keep both; ADR-327 dissolves the partition by collapsing the two files into one. ADR-313's audit (the two gates are not duplicates *as implemented*) is preserved as historical record; its *keep-both* conclusion is reversed because the operator-facing reframe removes pace's reason to be a separate gate.

**Amends:**
- [ADR-291](ADR-291-unified-cost-ledger.md) (no schema change — the budget gate reads the existing `execution_events` cost ledger; this ADR adds a reader, not a writer).
- [ADR-293](ADR-293-governance-operational-substrate-taxonomy.md) D7 (the governance file set loses `_pace.yaml`; `_token_budget.yaml` is renamed and re-scoped to `_budget.yaml`).
- [ADR-281](ADR-281-substrate-canonical-substrate-only-prompts.md) (adds one kernel mirror — `_calibration.md` — built on the same diff-aware mechanical-writer pattern as the ADR-301 pulse files; respects DP19 "the kernel does not compute for the prompt").
- [ADR-275](ADR-275-introspection-cadence-reviewer-authored.md) (the self-improving loop generalizes the introspection-cadence-is-Reviewer-authored principle from trader-specific to kernel-universal).

**Preserves:** FOUNDATIONS Axioms 0–9 · Axiom 4 (Trigger) · Axiom 5 (Mechanism — autonomy axis untouched) · Derived Principle 18 (standing intent implies Trigger-authoring authority) · Derived Principle 19 (kernel does not compute for the prompt) · Derived Principle 20 (wake-as-irreducible-unit) · DP22 (persona-frame anti-rebloat — posture not checklist) · ADR-194 v2 Reviewer substrate · ADR-209 Authored Substrate · ADR-216 orchestration-vs-judgment · ADR-298 D1–D3/D6–D10 wake-queue · ADR-301 pulse envelope.

---

## 1. Problem statement

Two problems, one root.

### Problem A — "Pace" is the wrong operator concept

The operator-facing pace dial (`weekly | daily | hourly | continuous`, surfaced at `/pace` per ADR-300) smears **three contradictory numbers** into one control:

1. **The ceiling the code enforces** — `daily` = "at most ~24 paced-lane fires/day" (`services/pace.py::cron_fires_per_day` × `check_population_constraint`).
2. **The label's vibe** — "Daily" reads to a layperson as *~hourly* ("24 hours in a day, so once an hour"). The label fights its own number.
3. **The actual wake count** — the live alpha-trader workspace has 2 judgment recurrences firing ~twice/day. Picking `weekly` vs `hourly` changes *nothing observable* — both ceilings sit far above the real rate. The truth is shown nowhere.

A dial conflating a cap, a vibe, and a hidden truth cannot produce a correct mental model. And the **unequal-distribution objection is fatal to any frequency framing**: judgment wakes cluster (market-open for trader), so no single frequency word is ever honest — the distribution is the Reviewer's, not a uniform rate.

The deeper tension: if the Reviewer authors its own cadence against ground truth (Derived Principle 18 + ADR-275), then *"operator sets how often the agent works"* fights *"the agent figures out its own cadence."* Tempo is the agent's job. A separate operator tempo-dial is the operator second-guessing the precise thing the agent exists to figure out.

The operator's *legitimate* concern was never "how often." It was **"how much will this cost"** and **"don't run away."** Both are budget concerns. **Pace was always a budget wearing a frequency costume.**

### Problem B — Cost/frequency governance is split across two files

"How often / how much can work fire?" is answered today by **two governance files** with an artificial partition ([ADR-313](ADR-313-fire-frequency-gate-partition.md)):

| File | Owns | Enforcement site |
|---|---|---|
| `governance/_pace.yaml` | drain-lane rate (`kind` → `min_interval_seconds`) + recurrence-population constraint | `wake_drainer.py::paced_lane_eligible_to_drain` + `schedule.py` pace-gate |
| `governance/_token_budget.yaml` | `daily_spend_ceiling_usd` + `max_judgment_recurrences_per_day` + `min_interval_between_recurrence_fires_seconds` | `wake.py` Gate B (ADR-293 D7) + Tier-1 `BudgetSignals` |

ADR-313 audited these, **falsified** "they break the Reviewer," **confirmed** "they confuse future developers," and chose to fix the confusion with *documentation* (name the boundary, keep both files). That fixed the *developer*-facing confusion. It did not touch the *operator*-facing confusion (Problem A) — and the operator-facing reframe removes pace's reason to exist as a separate gate. Once "how often" is no longer an operator dial, Gate A's drain-rate-from-pace has no operator-facing input left to read; the two gates collapse into one budget.

### Problem C — "Self-improving" is asserted, not driven

The thesis is "agents that improve with tenure." The Reviewer has the *authority* to improve (it authors its own cadence via `Schedule`, Derived Principle 18) but nothing **drives** it to, and nothing **measures** whether it does. Improvement happens only when the LLM happens to choose it. For a thesis built on tenure-driven improvement, the improvement loop is the thinnest-mechanized part of the architecture — and what mechanization exists (trader's `outcome-reconciliation` → `_money_truth.md` + a money-truth-flavored persona frame) is **bundle-specific scaffolding** every new program would re-invent.

**Why A/B and C are one ADR:** budget is *one input to the self-improving loop* (the envelope the Reviewer allocates within); calibration is *the other input* (the evidence for how to allocate). Specifying the budget gate without the loop would re-discover the loop's questions inside it; specifying the loop without budget would leave "allocate within what?" unanswered. Budget without calibration is "spend within a ceiling blindly"; calibration without budget is "improve with no envelope." Together they are the complete loop. They cannot ship apart.

---

## 2. Decisions

### D1 — Pace retires. A dollar budget over a timeframe replaces it.

There is **no tempo dial and no "pace" concept.** The operator declares **one dollar budget over a timeframe**; the Reviewer allocates judgment wakes within it against ground truth. Tempo is the Reviewer's allocation problem (D6), not an operator dial.

Tempo *intent* does not vanish — it moves to where standing intent already lives. "Morning brief, quiet otherwise" is a `MANDATE.md` / `_preferences.yaml` statement the Reviewer reads every wake, not a separate control.

**The live operator trifecta becomes Budget + Autonomy + Identity** (ADR-298 D11's "Pace + Autonomy + Persona" survives only as the historical name). Same three FOUNDATIONS dimensions; the Trigger-dimension dial renames from a tempo cap to a cost envelope.

### D2 — Cost governance collapses to one file: `governance/_budget.yaml`

`_pace.yaml` and `_token_budget.yaml` collapse into a single `governance/_budget.yaml`. Singular Implementation — one file is the sole per-workspace cost/frequency governance.

```yaml
# governance/_budget.yaml — the operation's spend envelope (ADR-327)
# Operator-authored. The Reviewer reads but cannot write (governance lock).
# Replaces _pace.yaml (deleted) + _token_budget.yaml (folded in).

budget:
  amount_usd: 50.00          # the spend envelope
  window: monthly            # monthly | weekly | daily — the timeframe the amount covers

# Hard safety floor, independent of the envelope (a single runaway wake
# can't blow the whole window in one fire). Optional; kernel default applies.
per_wake_ceiling_usd: 1.00

# Per-slug fire floor — survives from _token_budget.yaml (ADR-313 Gate 3).
# A recurrence cannot fire more frequently than this many seconds apart.
min_interval_between_recurrence_fires_seconds: 60
# overrides:
#   signal-evaluation:
#     min_interval_seconds: 900
```

**What dies from the old files** (the frequency-cap concepts, with no replacement — they were the wrong concept):
- `_pace.yaml::kind` (`hourly|daily|weekly|continuous`) — deleted.
- `_pace.yaml::every` — deleted.
- `_token_budget.yaml::max_judgment_recurrences_per_day` — deleted. (Fire-count-as-governance was a proxy for cost; the dollar budget governs cost directly. A fire that costs nothing shouldn't count against a fire-count cap, and a fire that costs a lot is already governed by the dollar gate.)

**What survives, re-homed:**
- `_token_budget.yaml::daily_spend_ceiling_usd` → generalized to `budget.amount_usd` + `budget.window` (timeframe now operator-chosen, not hardwired daily).
- `_token_budget.yaml::min_interval_between_recurrence_fires_seconds` + `overrides:` → preserved verbatim (the per-slug floor is a legitimate anti-thrash mechanic orthogonal to cost; ADR-313 Gate 3).

`_budget.yaml` is **operator-only** (in the governance root → `DEFAULT_REVIEWER_WRITE_LOCKS` per ADR-320; the Reviewer reads it in the wake envelope but cannot raise its own ceiling).

### D3 — The budget is a hard Tier-1 funnel gate over `execution_events`

The dollar budget is enforced as a **Tier-1 deterministic gate** (`wake_evaluation.py`), reusing the existing `spend_ceiling` machinery:

- `BudgetSignals` gains `window_spend` + `window_budget` (replacing `daily_spend` + `spend_ceiling`; same shape, operator-chosen window).
- `window_spend` = `SUM(execution_events.cost_usd)` over the current budget window (`monthly` → since UTC month start; `weekly`/`daily` analogous) — the existing ADR-291 unified cost ledger, no new writer.
- Tier-1 returns `skip` when `window_spend >= window_budget` **for scheduled (cron-tick) wakes** — see D4 for the priority rule on reactive wakes.
- `per_wake_ceiling_usd` is the runaway floor — a single fire's projected cost above it routes to operator (this is the safety the old drain-throttle accidentally provided).

### D4 — All judgment wakes draw from one budget; scheduled gets first claim, reactive warns-but-doesn't-block

Every Reviewer **judgment** wake draws from the budget — scheduled (`cron_tick`) *and* reactive (`addressed`, `proposal_arrival`, `substrate_event`, `manual_fire`). Mechanical recurrences (`mode: mechanical`) are **free and out of scope** — they never wake the Reviewer ($0; `track-positions` firing every minute is irrelevant to the budget).

The priority rule resolves "a chatty operator can starve scheduled work":

- **Scheduled wakes** (`cron_tick`): hard-gated. `window_spend >= window_budget` → `skip` (the operation goes quiet rather than over-spend; the Reviewer's next wake surfaces the budget exhaustion).
- **Reactive wakes** (operator-present / proposal / hook): **warn-but-don't-block.** Operator presence is warrant (ADR-296 v2 Tier-1 auto-escalate for `addressed` is preserved). You never want "sorry, you've used up your chat budget." Over-budget reactive wakes still fire; they surface a budget-overage signal to the operator (the budget is honest about being exceeded, it doesn't silently refuse the operator).

This makes the budget honest in both directions: it protects the operation's scheduled work from being drained by conversation, and it never refuses the operator mid-conversation.

### D5 — The drain-throttle and paced/live lane split dissolve

`paced_lane_eligible_to_drain` (the `_pace.yaml`-driven minimum-interval throttle, ADR-313 Gate A) is **deleted.** Its only job was serving the pace dial; with pace gone, its reason to exist goes.

The **paced/live lane split** in `wake_queue` (ADR-298) collapses to a single FIFO lane. **Verify before deletion:** the lane split's *other* role was load-shaping; confirm against the single-in-flight constraint (ADR-298 D1, preserved) that one lane + single-in-flight + the per-slug min-interval floor (D2) is sufficient to prevent stampede. If a residual stampede-smoother is empirically needed, it is a cost-agnostic queue mechanic, not a pace concept — it would not resurrect `_pace.yaml`.

(ADR-298's `wake_queue` table, `submit_wake_proposal` gateway, cross-source dedup at enqueue, single-in-flight, and stale-lock reclaim are all **preserved** — D5 touches only the pace-derived throttle + the lane partition.)

### D6 — The self-improving loop is kernel-universal; the bundle declares only its inputs

The loop that makes "self-improving" real is ratified as a **kernel-universal** pattern (machinery written once), parameterized by **program declarations** (inputs only). This generalizes ADR-275 (introspection-cadence-is-Reviewer-authored) from trader-specific to every program.

**The loop:** operator intent (budget envelope + mandate + preferences) + ground-truth substrate (program-declared) → Reviewer reasons at wake → authors cadence (`Schedule`) + refines judgment + rewrites `standing_intent` → outcomes accumulate into ground-truth substrate → (next wake reads it).

Three kernel pieces + one program declaration:

**D6.a — Kernel mirror `_calibration.md`** (new; sibling of the ADR-301 pulse files `_schedule_index.md` + `_recent_execution.md`). Written mechanically per scheduler tick by `services.kernel_mirrors`, diff-aware (most ticks write nothing), zero-LLM. It correlates two things already in substrate:
- The Reviewer's **cadence-authoring history** — `workspace_file_versions` for `_recurrences.yaml` (every `Schedule` call, attributed, ADR-209).
- **Outcome quality** — read from the program-declared ground-truth file (D6.c).

Output is the *evidence*, not a verdict: "you authored `signal-evaluation` at `@market_open + 15min`; the last 5 fires produced 0 proposals." The Reviewer judges what to do with it. This respects DP19 (the kernel does not compute *for the prompt* at prompt-assembly time — the correlation is written to substrate first, then read like any other envelope file).

**D6.b — Persona-frame posture** (domain-agnostic, stance not checklist per DP22). Added to the Reviewer `_PERSONA_FRAME`:
> *Before reasoning about cadence, read `_calibration.md`. Where your prior cadence choices have been falsified by ground truth — fires that produced no value, deliverables that arrived stale, wakes that found nothing — re-author. Cadence is yours to improve; the calibration trail is your evidence.*

It carries **no domain nouns** — it says "ground truth," and the envelope supplies *which* file (D6.c). No per-program persona fork.

**D6.c — Program declares its ground-truth file.** The bundle's `MANIFEST.substrate_abi` gains a `ground_truth:` key naming the file the calibration mirror correlates against and the Reviewer reasons from. Trader: `operation/trading/_money_truth.md`. Author: a corpus-coherence / engagement file (declared when that program's loop is built). **No new loop code, no new recurrence shape, no persona fork per program** — the same kernel-vs-program split as the temporal model (cadence-and-wakes.md §8b) and the substrate ABI (ADR-281).

**D6.d — Demand-pull validation.** The loop generalizes on paper; it has been validated only against money-truth (one data point). The kernel machinery (D6.a/b) ships now; a *second program's* ground-truth declaration + stress test must validate the generalization before the loop is declared canon-complete. Build the generalization; prove it against a second program before claiming it. (Same discipline as ADR-224/225 demand-pull.)

### D7 — Singular FE/BE deletion scope (no coexistence)

Per Singular Implementation, pace is **deleted end-to-end**, not deprecated beside budget.

**Backend deletions:**
- `services/pace.py` (entire module: `parse_pace_yaml`, `read_pace`, `cron_fires_per_day`, `check_population_constraint`, `pace_at_least_as_frequent`, `min_interval_seconds`, `Pace`).
- The `pace_exceeded` gate + `check_population_constraint` call in `services/primitives/schedule.py` (D2 — recurrence creation no longer pace-gated; only the per-slug floor + budget apply).
- `paced_lane_eligible_to_drain` in `services/wake_drainer.py`; the paced/live lane split in `services/wake_queue.py` + `resolve_lane` (D5, pending stampede verification).
- `_pace.yaml` read in `services/reviewer_envelope.py`; `GOVERNANCE_PACE_PATH` + lock entry in `services/workspace_paths.py`.
- The pace default-seed in `services/programs.py::fork_reference_workspace` (D8 in ADR-298); the bundle `minimum_pace` gate + `services/bundle_reader.py::get_minimum_pace`; `MANIFEST.minimum_pace` declarations.
- `_token_budget.yaml` references → renamed to `_budget.yaml` (`services/token_budget.py` → `services/budget.py`, re-scoped per D2/D3; `GOVERNANCE_TOKEN_BUDGET_PATH` → `GOVERNANCE_BUDGET_PATH`).
- ADR-313's two-gate doctrine references (the partition is dissolved).

**Backend additions:**
- `governance/_budget.yaml` substrate + loader (`services/budget.py`, repurposed from `token_budget.py`).
- `BudgetSignals.window_spend` + `window_budget`; the window-spend query over `execution_events` (ADR-291).
- Tier-1 budget gate with the D4 scheduled-vs-reactive priority rule in `wake_evaluation.py`.
- `_calibration.md` mirror writer in `services.kernel_mirrors` + envelope slot in `reviewer_envelope.py` + `_PERSONA_FRAME` posture (D6).
- `MANIFEST.substrate_abi.ground_truth` declaration on alpha-trader (`_money_truth.md`) + reader in `services/bundle_reader.py`.

**Frontend deletions:**
- `web/components/workspace-concepts/PaceCard.tsx`.
- `web/app/(authenticated)/pace/page.tsx` (the `/pace` atomic surface, ADR-300; `/pace` survives as a redirect stub to `/budget` for bookmark safety).
- `web/components/shell/system-status/PaceStatusItem.tsx` (`PaceBadge` already gone per ADR-297 D20).
- `web/lib/content-shapes/pace.ts` (`useCockpitPace`, `paceKindLabel`, `PaceKind`).
- `api.pace()` namespace in `web/lib/api/client.ts` (`/api/pace`) + `api/routes/pace.py`.

**Frontend additions:**
- `/budget` atomic surface (repurposed `/pace`) showing **two numbers**: the dollar budget (`amount_usd` + `window`, operator-editable) **and** its window-to-date utilization ("$12 of $50 used, 18 days left, on pace"). The control *position* in the cockpit/system-status stays (operators still have one Trigger-dimension governance dial here); only its meaning + data change.
- `BudgetCard` + `useCockpitBudget` + `api.budget()` (mirroring the deleted pace shapes).

### D8 — The budget surface is a hard dependency, not a follow-on

A dollar budget is only honest if the operator can *see it draw down.* The utilization data exists (`execution_events` unified cost ledger, ADR-291) but is **DB-only, surfaced nowhere** (the cadence-and-wakes.md §15 #4 transparency gap). The `/budget` surface (D7) is therefore **in scope for this ADR**, not deferred — "set a budget" cannot ship without "here's where it went."

---

## 3. What this ADR deliberately does NOT do

- **Does not touch autonomy** (Mechanism axis, `_autonomy.yaml`, `should_auto_apply`). Budget gates *cost/when*; autonomy gates *what-binds*. Orthogonal (cadence-and-wakes.md §1a).
- **Does not touch the wake queue, single-lane execution, or cross-source dedup** (ADR-298 D1–D3/D6–D10 preserved). Only the pace-derived throttle + lane split (D5).
- **Does not change `execution_events` schema** (ADR-291 reader-only).
- **Does not change recurrence shape** (`{slug, schedule, prompt, mode}` per ADR-261 unchanged; the calibration loop reads the *history* of these, not their shape).
- **Does not introduce per-program loop code** (D6 is kernel machinery + one MANIFEST key).

---

## 4. Implementation phases

Each phase lands green (test gate + backend boots + frontend builds), Singular at every step.

- **Phase 1 — `_budget.yaml` substrate + loader.** Collapse `_pace.yaml` + `_token_budget.yaml` → `_budget.yaml`. `services/budget.py` (from `token_budget.py`). Bundle reference-workspaces + activation seed updated. Migration of any live workspaces' two files → one. Test gate: schema parse + lock + envelope read.
- **Phase 2 — Tier-1 budget gate + D4 priority rule.** `BudgetSignals.window_spend/window_budget`; window-spend query over `execution_events`; scheduled-hard / reactive-warn rule in `wake_evaluation.py`. Delete the `pace_exceeded` gate in `schedule.py`. Test gate: budget exhaustion skips scheduled, passes reactive.
- **Phase 3 — Drain-throttle + lane split removal.** Delete `paced_lane_eligible_to_drain`; collapse the lane split (verify stampede behavior against single-in-flight + per-slug floor first). Delete `services/pace.py`. Test gate: ADR-298 wake-queue gates still green (single-in-flight, dedup, reclaim).
- **Phase 4 — Self-improving loop (D6).** `_calibration.md` mirror writer + envelope slot + persona posture; `MANIFEST.substrate_abi.ground_truth` on alpha-trader + reader. Test gate: mirror writes diff-aware; envelope carries calibration; persona posture present.
- **Phase 5 — FE collapse.** Delete pace FE (D7); ship `/budget` surface with utilization (D8); `/pace` redirect stub. Test gate: frontend build clean; `/budget` renders budget + window-to-date spend.
- **Phase 6 — Doc cascade + grep gate.** cadence-and-wakes.md §12a/§11a → Implemented; GLOSSARY pace→budget; supersession banners on ADR-298/300/313; final grep gate (zero live `_pace.yaml` / `pace.py` / `api.pace` references).

---

## 5. Open question carried into implementation

1. **Does any queue throttle survive D5?** Leaning dissolve (the lane split existed to serve the pace throttle). Confirm against `wake_queue` single-in-flight before deleting the lane partition — if a cost-agnostic stampede smoother is empirically needed, it is a queue mechanic, not a resurrected pace concept.
2. **Budget window default + first-activation seed.** alpha-trader's old `daily_spend_ceiling_usd: 10.00` maps to roughly `monthly` `$300` or stays `daily`/`$10` — pick the seed that matches the bundle's actual fire economics when Phase 1 lands (read recent `execution_events` to size it honestly rather than guessing).
3. **D6.d second-program validation target.** alpha-author is the natural second program (corpus-coherence as ground truth). Its `ground_truth:` declaration + a stress test is the gate before declaring the loop canon-complete.

---

## 6. Implementation outcome (2026-06-08)

Six phases, each landing green, on branch `adr-327-budget-and-self-improving-loop`:

| Phase | Commit | Gate | What |
|---|---|---|---|
| 1 | `e877c36` | test_adr327_phase1 35/35 | `services/budget.py` (from token_budget.py) + `_budget.yaml` substrate + loader + envelope swap `pace_yaml`→`budget_yaml` + bundle `_token_budget.yaml`→`_budget.yaml` ($50/monthly) + live-migration script. |
| 2 | `38efaab` | test_adr327_phase2 30/30 | Tier-1 budget gate (`window_spend`/`window_budget`) + D4 scheduled-hard/reactive-warn in wake.py Gate B; judgment-cap (Gate B.2) deleted. |
| 3+4 | `16fb0da` | ADR-298 phase1 41/41, phase3 39/39 | **−1922 LOC.** Deleted: schedule.py pace gates, `paced_lane_eligible_to_drain`, lane split (collapsed to single "live" lane — stampede-verified against single-in-flight + per-slug floor), `services/pace.py`, `services/token_budget.py`, `routes/pace.py`→`routes/budget.py`, programs.py minimum_pace gate, bundle `minimum_pace`. |
| 5 | `2f3e0a8` | test_adr327_phase5 24/24 | `_calibration.md` kernel mirror (`mirror_calibration` primitive + kernel_mirrors runner + scheduler tick) + envelope slot + minimal-frame posture + `substrate_abi.ground_truth` + bundle_reader. |
| 6 | `b1ad7a4` | test_adr327_phase6_fe 30/30 + tsc clean | FE pace→budget collapse: deleted PaceCard/pace.ts/PaceStatusItem; shipped `/budget` surface (BudgetCard + useCockpitBudget + BudgetStatusItem + utilization view) + `/pace`→`/budget` redirect stub. |

**Resolved open questions:** Q1 — the lane split dissolved (single FIFO lane; single-in-flight + window budget + per-slug floor are sufficient; no residual throttle needed). Q2 — seed is `monthly`/`$50` (sized against observed 30-day spend ≈$50, dev/eval-inflated, so comfortable headroom for a real operator).

**Deferred:** Q3 — D6.d second-program (alpha-author) validation of the generalized loop. The kernel machinery ships now; the generalization is proven against a second program's `ground_truth:` declaration + stress test before the loop is declared canon-complete. The live-workspace migration script runs at deploy (not in-branch — live DB shared across branches).

**Honest note on adjacent test rot:** 5 pre-existing red gates (test_adr275, test_adr274, test_adr284_phase2, test_envelope_observability, + a standing_intent-heading assertion in test_adr284) reference old bundle paths (`review/`→`persona/`, `context/_shared/`→`governance/` moves from prior ADRs) — confirmed red on the true pre-ADR-327 baseline (`2ae3260`) via worktree; **not caused by ADR-327.** Left for a separate rot sweep rather than silently absorbed. The envelope keys/count portion of test_adr284 that ADR-327 *did* change (pace_yaml→budget_yaml, +calibration_md) was updated.
