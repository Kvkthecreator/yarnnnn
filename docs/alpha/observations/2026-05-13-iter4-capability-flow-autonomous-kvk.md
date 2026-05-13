# 2026-05-13 — kvk — Iteration 4: Capability-flow wiring (ADR-269) + autonomous AUTONOMY flip

> **Type**: Steered-session observation. Closes iter-4 of the closed-loop development pattern. Successor to [iter-3](./2026-05-13-iter3-market-context-aware-recurrences-kvk.md).
> **Persona**: `kvk` — `user_id=2abf3f96-118b-4987-9d95-40f2d9be9a18`, paper Alpaca EE8K
> **Outcome**: closes iter-2's L3 layer (last of three identified as blocking trade execution). With trilogy (L1, iter-1) + dispatch_specialist signature (L2, iter-3) + capability-flow wiring (L3, this iter) + ADR-268 market-hours + autonomous AUTONOMY, the trade-producing path is structurally complete end-to-end for the first time. Tonight's RTH window (22:30 KST onward) is the first test of the full system under autonomous posture.

---

## Classification

- **Objective:** A-system (primary), B-product (the autonomous-execution interpretation chosen by operator means tonight's signal fires can bind directly to paper-Alpaca orders without operator click)
- **Within-A scope:** systematic-workflow (capability-flow chain) + qualitative-agent-behavior (Reviewer dispatches specialist with right tools) + Substrate (operator-authored autonomous posture)
- **FOUNDATIONS dimension:** Mechanism (Axiom 5) primary — refines tool surface during specialist sub-LLM-call. Secondary: Identity (Axiom 2) preserves universal specialist roster + overlay; Substrate (Axiom 1) operator-authored autonomous flip + bundle declarations
- **Severity:** dead-stop (was the last structural block preventing real trade emission)
- **Resolution path:** ADR-candidate (landed: ADR-269) + component-patch (9 files iter-4 + 2 files fork-skip follow-on) + bundle authorship + operator-authored AUTONOMY flip
- **Money impact:** decision-impact preconditioned — system can now produce real trade proposals; first one fires tonight if any of 5 signals trigger on real RTH bars

---

## Stated objective

Close iter-2's L3 (the third of three layers blocking trade execution per iter-2's observation). Operator chose Interpretation A (full autonomous execution from first signal fire) over the Phase-0 paper-seed Interpretation B (operator click in trade-firing path), with hybrid L3 ownership (recurrence declares default, Reviewer can extend per-dispatch). Ship iter-4 in one session so tonight's RTH window benefits from all four layers (L1 + L2 + L3 + market-hours).

## What happened

### Round 1 — ADR-269 + L3 wiring (commit `3f1e720`)

Closed iter-2's L3 by shipping the full capability-flow chain:

- `Recurrence` dataclass gains `required_capabilities: list[str]` field; parser reads from YAML body
- `invocation_dispatcher.dispatch` threads `recurrence_required_capabilities` into the Reviewer's context envelope
- `reviewer_agent` surfaces the capabilities section in the recurrence-fire system context with a one-paragraph instruction to pass them through (or extend) when calling DispatchSpecialist
- `DISPATCH_SPECIALIST_TOOL` input_schema gains `required_capabilities: array` property
- `handle_dispatch_specialist` passes `task_required_capabilities` to `get_headless_tools_for_agent`
- The merge happens inside `get_platform_tools_for_agent` — already accepted the kwarg per ADR-227; this ADR delivered it

Bundle authorship in same commit:
- 5 trading recurrences gain `required_capabilities`: track-universe / signal-evaluation / track-regime / outcome-reconciliation declare `[read_trading]`; trade-proposal declares `[read_trading, write_trading]`
- Housekeeping recurrences NOT burdened
- Mechanical mirrors NOT burdened (they bypass capability gate per SyncPlatformState architecture)

Operator-authored AUTONOMY flip in same commit:
- `_autonomy.yaml`: `delegation: autonomous`, `ceiling_cents: 5000000` ($50k, safety net), `never_auto: [close_position_market, cancel_other_orders]` preserved
- `AUTONOMY.md` prose rewritten: new "Current posture" section names operator's autonomous election; "Phase progression" preserved as historical reference for revert path

71-assertion regression gate. All PASS.

### Round 2 — Fork-skip bug surfaced + fixed (commit `cc68011`)

Post-deploy + reset + verify showed kvk's `_autonomy.yaml` had `delegation: manual` instead of the autonomous content from the bundle. **Root cause traced**: order of operations in workspace activation:
1. `workspace_init.initialize_workspace` seeds kernel-default content for ~10 files including `_autonomy.yaml` (always writes if not existing)
2. Then `fork_reference_workspace` runs. Its overwrite rule (programs.py:211): skips files whose existing content is NOT skeleton per `is_skeleton_content`. The kernel-default `delegation: manual` is real config, not skeleton.

**Result**: bundle's canonical `_autonomy.yaml` (and potentially other files) silently dropped on activation. Operator gets kernel defaults instead of bundle-authored values.

Fix shipped in `cc68011`:
- workspace_init now enumerates the bundle's reference-workspace/ at activation time
- Skips the kernel-default seed for any path the bundle owns
- Bundle fork then writes its canonical content (since the file doesn't exist after the skip)
- Generic workspaces (no program_slug) unchanged

Also patched kvk's live workspace via UserMemory.write to land autonomous posture immediately for tonight (didn't wait for next reset cycle).

### Round 3 — Final validation

After deploy + force-materialize:

- All 15 recurrences with RTH-aligned UTC `next_run_at` populated
- Trading recurrences carry `required_capabilities` declarations (visible via `/api/recurrences`)
- `_autonomy.yaml` shows `delegation: autonomous` + `ceiling_cents: 5000000`
- verify.py 32/32 green

### Tonight's RTH window (KST)

| Time | Fire | What's tested |
|---|---|---|
| 22:00 KST | pre-market-brief | First post-iter-4 judgment-mode fire; Reviewer reads substrate, dispatches specialist with `read_trading` → specialist gets Alpaca tools |
| 22:30 KST | track-positions/account/orders | Mechanical mirrors at RTH open. Zero LLM, direct platform_tool dispatch |
| **22:45 KST** | **signal-evaluation** | **The load-bearing test: Reviewer dispatches specialist with `read_trading`, specialist fetches RTH bars for AAPL/MSFT/NVDA/SPY/TSLA, signal eval runs against real bars, fires trade-proposal if any signal triggers** |
| 22:45 KST | track-universe (1st of 3) | List-form schedule, same dispatch path |
| 01:45 KST Thu | track-universe (2nd of 3) | Midday RTH snapshot |
| 04:00 KST Thu | track-universe (3rd of 3) | Pre-close snapshot |
| 05:30 KST Thu | track-regime | VIXY/SPY regime refresh |
| 06:00 KST Thu | outcome-reconciliation | Daily P&L roll-up (no-op if no trades fired today) |

**Under `delegation: autonomous` with `ceiling_cents: $50k`**: if a signal fires and the Reviewer approves the trade-proposal, the order auto-fires at paper Alpaca within the same dispatch loop — no operator click needed. Hard safety floor remains: `never_auto: [close_position_market, cancel_other_orders]` + risk_gate.py enforced before any order (max_position_size_usd: 1000, max_daily_loss_usd: 200, trading_hours_only).

## Friction

The fork-skip bug surfacing during post-deploy validation was the major friction — but it's the kind of friction that's diagnostic-rich. The kernel-vs-bundle ownership conflict is a real architectural pattern that needed naming and fixing. Without iter-4's specific scenario (operator-authored AUTONOMY flip in the bundle), the bug would have stayed silent indefinitely.

Singular Implementation rule served as the right hammer: workspace_init seeding + bundle fork were doing the same job in conflicting directions. The fix is "bundle wins by construction when present" — one source of truth per path.

Race-condition between Render deploy and operator-side reset (iter-3 pattern) recurred. Logged as a steered-session learning *again*: scheduler-touching changes need wait-for-deploy-completion verification, not just elapsed-time waits. Future iters might benefit from a `wait_for_deploy()` helper that polls a version-tagged endpoint until it returns the expected SHA.

## Hypothesis

**For the "no trades" surface on kvk's workspace, status post-iter-4**:

All four F1 hypotheses now structurally addressed:

- **F1-A (environmental)** ✅ — signal-evaluation fires at 22:45 KST (markets-open + operator-awake)
- **F1-B (systematic-dispatcher)** ✅ — trilogy + manual-fire trigger fixes shipped iter-1
- **F1-C (systematic-judgment)** ✅ — Reviewer wakes with real RTH bars, real principles framework, full reasoning surface
- **F1-D (systematic-config-or-config-gap)** ✅ — capability flow wired end-to-end, autonomous delegation flipped

**Most likely outcome tonight**: one of two scenarios:

1. **Signal fires + Reviewer approves + paper order fires.** First real autonomous trade on kvk's workspace. Closed-loop cycle proven.
2. **Signal does NOT fire (no setups meet 6-check ladder).** Reviewer correctly stands down with prose reasoning. Substrate accumulates fresh bars. Tomorrow's track-universe + signal-evaluation tries again with newer data.

**What this iter does NOT predict**: whether the trade will be profitable. ADR-269 closes the structural gate; profitability is the B-product question that takes weeks/months to answer per SCOPE.md's 90-day rolling window.

## Counterfactual (Objective B)

Without iter-4, last week's "no trades" would continue indefinitely:
- ADR-268 fixed timing (signal-eval at RTH open) but specialists still couldn't fetch bars → Reviewer stands down on every fire with "platform tool not in surface"
- The architecture would have remained correct at every layer except one — and that one prevents any closed-loop cycle from completing

Iter-4 closes the structural loop. Whether the system *produces edge* (positive expectancy across closed paper trades) is now a separate, observable question.

## What iter-5+ might look like

With L1-L4 closed and tonight's window as first real test, future iters depend on what tonight reveals:

- **If first cycle completes successfully**: iter-5 = observation pass over the first 1-3 closed cycles. What does Reviewer reasoning look like at scale? Are the 6 checks discriminating well? Calibration loop starts.
- **If signal-eval crashes or surfaces another gap**: iter-5 = fix that gap, same playbook (steered session, narrate-before-act, observation note, ADR if architectural).
- **If signals never fire over many cycles**: iter-5 = signal-definition calibration. Are the signal conditions too tight? Operator-authorship work in `_operator_profile.md`.

Phase-0 → Phase-1 graduation per AUTONOMY.md is not relevant now since operator chose autonomous from the start. Next AUTONOMY-related question: when does ceiling_cents shrink (if losses surface) or expand (if confidence builds)?

## Links

- **ADR-269**: [docs/adr/ADR-269-capability-flow-wiring.md](../../adr/ADR-269-capability-flow-wiring.md)
- **Iter-3 (predecessor)**: [2026-05-13-iter3-market-context-aware-recurrences-kvk.md](./2026-05-13-iter3-market-context-aware-recurrences-kvk.md)
- **Iter-2 (great-predecessor, named the L1/L2/L3 layers)**: [2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md](./2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md)
- **Iter-1 (where the whole closed-loop-development pattern started)**: [2026-05-13-iter1-e2e-aliveness-kvk.md](./2026-05-13-iter1-e2e-aliveness-kvk.md)
- **Commits**:
  - `3f1e720` — ADR-269 + L3 wiring + alpha-trader bundle declarations + AUTONOMY flip (+697/-10 LOC, 9 files)
  - `cc68011` — fork-skip fix: workspace_init skips bundle-owned paths (+54 LOC, 2 files)
- **Regression gate**: `api/test_adr269_capability_flow.py` — 74/74 PASS. ADR-268 gate 33/33 PASS (no regression). ADR-269 + ADR-268 combined: 107/107 PASS.
- **Production state (post-iter-4)**: kvk has 15 recurrences with RTH-aligned UTC, autonomous AUTONOMY active, capability-flow wired, all structural gates closed
- **F1 failure class** ([DUAL-OBJECTIVE-DISCIPLINE.md](../DUAL-OBJECTIVE-DISCIPLINE.md#named-failure-classes)) — all four hypotheses structurally addressed
