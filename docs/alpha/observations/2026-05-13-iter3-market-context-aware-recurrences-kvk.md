# 2026-05-13 — kvk — Iteration 3: Market-context-aware recurrences (ADR-268) + L2 fix

> **Type**: Steered-session observation. Closes iter-3 of the closed-loop development pattern. Successor to [iter-2](./2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md).
> **Persona**: `kvk` — `user_id=2abf3f96-118b-4987-9d95-40f2d9be9a18`, paper Alpaca EE8K
> **Outcome**: full architectural shift shipped end-to-end. Bundle's recurrences now schedule against semantic RTH anchors (`@market_open + 15min`), resolve to RTH-aligned UTC at materialize time, route through API + FE without crashes. First post-fix RTH window opens tonight 22:30 KST.

---

## Classification

- **Objective:** A-system (primary), B-product (preconditions trades; not a trade yet)
- **Within-A scope:** systematic-workflow (scheduler resolution path) + qualitative-agent-behavior (recurrences now fire at meaningful market times) + ui-ux (FE renders list-form schedules)
- **FOUNDATIONS dimension:** Trigger (Axiom 4) primary; Substrate (MANIFEST market_context) + Channel (FE display of list-form) secondary
- **Severity:** dead-stop (was blocking every potential trade since program activation)
- **Resolution path:** ADR-candidate (landed: ADR-268) + component-patch (8 backend files + 8 FE files + bundle YAML rewrite)
- **Money impact:** decision-impact (none yet; cleared the structural gate that prevented ANY trade-eligible bar fetch from happening at a meaningful market time)

---

## Stated objective

Pivot from iter-2's findings (which surfaced trade-execution as 3-layer blocked: L1 trilogy fix, L2 dispatch_specialist signature, L3 capability-flow wiring) by recognizing that **iter-3 needed a fourth layer first**: market-context awareness. The recurrence crons in the alpha-trader bundle encoded US RTH in UTC strings by hand (`signal-evaluation: "5 8 * * 1-5"` = pre-market 04:05 ET, 5h25min before NYSE opens). This had been silently wrong for the entire alpha-1 program lifetime — even with iter-2's L2+L3 fixes shipped, the scheduler would never trigger signal-eval at a time when RTH bars are meaningful.

Locked design: **Layer B per ADR-268** — market_context lives at the bundle MANIFEST level; recurrences use `@`-prefixed semantic vocabulary that resolves to UTC at materialize-due time; multi-market forward-compatible (Korean equities, crypto, futures all add by declaring their own market_context block + registering a MarketCalendar). Coupled L2 fix in same iter per design call.

## What happened

### Round 1 — ADR-268 landed (commit `047a79f`)

Built the kernel infrastructure for market-context-aware recurrences:
- `api/services/market_calendars.py` (new) — `MarketCalendar` base + `NyseUsCalendar` with inline 2026 + 2027 NYSE holidays + `CALENDARS` registry.
- `api/services/scheduling.py` — extended `compute_next_run_at` with optional `market_context` param. New `resolve_semantic_schedule` parses two grammars: anchored (`@market_open + 15min`) and interval (`@every 1min during regular_hours`).
- `api/services/recurrence.py` — `Recurrence.schedule` typed as `Optional[Union[str, list[str]]]`.
- `api/services/primitives/dispatch_specialist.py` — L2 fix: both kwarg mismatches corrected.
- Bundle changes: `MANIFEST.yaml` gains `market_context:` block; 7 of 15 `_recurrences.yaml` entries rewritten with semantic schedules.
- `api/test_adr268_market_context.py` — 22 assertions; all PASS.

### Round 2 — Bug surfaced + fixed (commit `e6c6293`)

Post-deploy validation surfaced TWO real bugs not caught by the pre-commit regression gate:

**Bug 1 — Race condition in initial materialize**: ran `reset.py kvk --confirm` before Render's auto-deploy completed. Reset triggered auto-re-fork with new bundle YAML, but `materialize_scheduling_index` ran against OLD production code. All 7 semantic-scheduled recurrences ended up with `next_run_at = NULL`. **Discovery**: P4 verification query. **Resolution**: re-running materialize against new code resolved them. Not a code bug — a timing artifact. Logged: when shipping a scheduler-touching change, wait for the deploy completion signal before triggering operator-side ops that depend on the new code path.

**Bug 2 — Pydantic 500 on `/api/recurrences`**: `TaskResponse.schedule` was typed `Optional[str]` but track-universe's authored schedule was `list[str]`. **Discovery**: curl returned `Internal Server Error`. **Resolution**: full list-aware widening across both sides:
- `TaskResponse.schedule + TaskUpdate.schedule` typed `Optional[Union[str, list[str]]]`. New `_decode_persisted_schedule()` helper round-trips JSON-encoded list strings from the index row.
- FE: `Recurrence.schedule: string | string[]`. `recurrenceLabel()` list-aware. New canonical `scheduleDisplay()` + list-aware `humanizeSchedule()` in `web/lib/schedule.ts`. 6 consumer sites routed through the canonical helper.
- Regression gate extended +11 assertions (TaskResponse list serialization round-trip + decoder edge cases). Total 33/33 PASS.

### Round 3 — Final validation

After deploy of `e6c6293`:
- `/api/recurrences` returns 200 with list-form schedule properly serialized.
- Second reset to pick up parallel commit `08415be` (operator-authored `track-regime` work) → kvk's workspace at 15 recurrences total.
- All 9 semantic-scheduled recurrences resolved to RTH-aligned UTC after re-materialize.
- 32/32 invariants verified on `verify.py kvk`.

### Tonight/tomorrow schedule (Seoul time, post-iter-3)

| Time | Fire | What it tests |
|---|---|---|
| 22:00 KST | pre-market-brief | First semantic-anchor fire (judgment mode) |
| 22:30 KST | track-positions/account/orders | First @every interval fire (mechanical mode) |
| **22:45 KST** | **signal-evaluation** | **First-ever real-RTH signal eval against actual RTH bars** |
| 22:45 KST | track-universe (1st of 3) | List-form schedule — first member fires |
| 01:45 KST Thu | track-universe (2nd) | List-form — second member |
| 04:00 KST Thu | track-universe (3rd) | List-form — third member |
| 05:30 KST Thu | track-regime | Operator-authored (commit 08415be) |
| 06:00 KST Thu | outcome-reconciliation | Daily P&L roll-up post-close |

## Friction

The big friction was the wire-shape gap between backend `Recurrence.schedule` (list-aware from the moment ADR-268 shipped) and `TaskResponse.schedule` (still str-only). Should have caught this with a broader test — the regression gate covered dataclass-level + parser-level shapes but not the API serialization shape. Added in Round 2 as +11 assertions in the same gate.

Secondary friction: the FE had 6 sites doing `{task.schedule}` directly. The audit was the time-consuming part; the fixes themselves were tiny.

Race-condition timing on the initial reset wasn't friction per se — surfaced the right learning: scheduler-touching changes need wait-for-deploy-completion before operator-side ops.

## Hypothesis

**For the "no trades" surface on kvk's workspace, status post-iter-3**:

- F1-A (environmental) — ✅ now structurally addressed. signal-evaluation fires at 22:45 KST (when KVK is awake).
- F1-B (systematic-dispatcher) — ✅ FIXED in iter-1 trilogy + iter-1 manual-fire trigger fix.
- F1-C (systematic-judgment) — UNTESTED at the trade-producing path. Tonight's signal-evaluation fire is the first test.
- F1-D (systematic-config-or-config-gap) — STILL OPEN. iter-2's L3 (capability-flow wiring) is unaddressed. Even with iter-3's market-hours fix, the specialist still doesn't have `platform_trading_get_market_data` because `required_capabilities` doesn't flow from recurrence YAML → DispatchSpecialist input schema → `get_headless_tools_for_agent`. **Iter-3 did NOT close L3.**

**Most likely outcome tonight**: track-universe at 22:45 KST will probably hit the same "platform bar-fetching tool not available in my tool surface" the iter-1 manual fire surfaced. The architecture is correct end-to-end; the capability is unwired.

The honest framing: **iter-3 fixed the trade-producing path's TIMING. iter-4 needs to fix the trade-producing path's TOOL ACCESS.**

## Counterfactual (Objective B)

Without iter-3, every signal-eval fire would have happened at 04:05 ET (pre-market) when bars don't reflect RTH price discovery. Reviewer would correctly stand down AND silently waste $0.30/fire.

Empirically observed in iter-1's pre-purge analysis: kvk's workspace had 10 Reviewer fires over 23 hours, all stand_down at $0.31/fire = $3.10 burned producing zero signal candidates. **Iter-3 redirects that burn to fires at meaningful market times.**

## What iter-4 needs to ship

Per iter-2's L3 spec, with iter-3's foundations in place:

1. `Recurrence` dataclass gains `required_capabilities: list[str]` field.
2. Parser reads `required_capabilities:` block from `_recurrences.yaml`.
3. `invocation_dispatcher.dispatch` threads required_capabilities through the Reviewer's context envelope.
4. `DispatchSpecialist.DISPATCH_SPECIALIST_TOOL` input schema gains optional `required_capabilities` array.
5. `dispatch_specialist.handle_dispatch_specialist` passes `task_required_capabilities` to `get_headless_tools_for_agent`.
6. alpha-trader bundle: add `required_capabilities: [read_trading]` to `track-universe`, `signal-evaluation`, `track-regime`. Add `[read_trading, write_trading]` to `trade-proposal`. (Operator authorship territory — KVK ratifies.)

Sized for one focused iter. ~3-4 hours including ADR amendment to ADR-227 or new ADR-269.

## Links

- **ADR-268**: [docs/adr/ADR-268-market-context-aware-recurrences.md](../../adr/ADR-268-market-context-aware-recurrences.md)
- **Iter-2 (predecessor)**: [2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md](./2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md)
- **Iter-1 (great-predecessor)**: [2026-05-13-iter1-e2e-aliveness-kvk.md](./2026-05-13-iter1-e2e-aliveness-kvk.md)
- **Commits**:
  - `047a79f` — ADR-268 kernel + bundle + L2 fix (+1335/-39 LOC, 9 files)
  - `08415be` — operator-authored track-regime wiring (parallel work)
  - `e6c6293` — list-aware wire shape: backend + 6 FE consumers + 11 regression assertions (+220/-22, 10 files)
- **Regression gate**: `api/test_adr268_market_context.py` — 33/33 PASS
- **Production state (post-iter-3)**: kvk workspace has 15 recurrences; all 9 semantic schedules resolved to RTH-aligned UTC; `/api/recurrences` returns 200 with list-form properly serialized; verify.py 32/32 green
- **F1 failure class** ([DUAL-OBJECTIVE-DISCIPLINE.md](../DUAL-OBJECTIVE-DISCIPLINE.md#named-failure-classes)) — iter-3 closes F1-A (environmental) structurally; F1-D (config-gap) is the next iter's target via L3 capability-flow wiring
