# AUDIT — the trader money-truth organ never materializes: the mechanical reconciler is orphaned, and the judgment prompt asserts a precondition the system no longer satisfies

**Date**: 2026-06-25. **Hat**: B (evaluation/audit — recommends a Hat-A fix, does not make it). **Workspaces audited**: `kvk-trader` (`U=2abf3f96…`, the dedicated trading test account), `alpha-trader-2` (`U=29a74c63…`), `alpha-trader` (`U=2be30ac5…`). **Trigger**: the parked trader-tenure construction (`2026-06-25-trader-tenure-tension-PARKED.md`) noted `kvk-trader._money_truth.md` is "MISSING"; this audit characterizes *why* — and the answer is a genuine kernel-wiring conflict, not a one-off missing file.

> **The finding in one sentence.** The trader's ground-truth organ (`_money_truth.md`) is written by a **mechanical reconciler (`reconcile_user`) that has no live scheduler caller** — it lost its caller when ADR-260/261 dissolved back-office tasks — while the **`outcome-reconciliation` judgment recurrence prompt tells the agent the reconciler "*has folded* yesterday's fills into `_money_truth.md`,"** a precondition that is never satisfied. On a workspace that never got the organ bootstrapped by some other path (kvk-trader), the file therefore **never materializes**, the reflection loop has nothing to join, and the daily-P&L email returns `no_money_truth`. The whole ground-truth → reflection → P&L chain is dark.

---

## What the three trader accounts actually show

| Account | `_money_truth.md` | other organs | reconciliation recurrence | execution_events |
|---|---|---|---|---|
| **kvk-trader** (test) | **MISSING** | `_universe.yaml`, `_risk.md`, `_signals_summary.md` (says *"no signal state files found"*), MANDATE, principles | `outcome-reconciliation` `@market_close + 1h`, **`mode: None`**, unpaused | 2,032 fired |
| **alpha-trader-2** | **present** (stub, *"initialized at first outcome-reconciliation fire 2026-06-10"*, 0 trades) | full organ set | same prompt, **`mode: judgment`** | (organ-complete) |
| **alpha-trader** | MISSING | `_universe.yaml`, `_risk.md`, … | — | purged 2026-05-29, not re-activated |

Two test accounts that should be identical diverge on whether the ground-truth organ was *ever* bootstrapped — and one (kvk) is the account we dedicated for testing.

## The root cause (receipts)

**1. The organ is written only by the mechanical reconciler, and it is designed to write an empty stub even with zero fills.**
`api/services/outcomes/ledger.py::fold_outcome_candidates` (lines 104–128):
```
if not candidates:
    # Empty-stub-on-first-run: ensure `_money_truth.md` exists so
    # the file exists from first task ... a workspace in paper-only
    # no-fills state has no `_money_truth.md`
    existing = await _read_money_truth_file(...)
    if existing is None:
        stub = _init_money_truth(provider.context_domain)   # context_domain = "trading"
        ... _upsert_money_truth_file(...)                    # → /workspace/operation/trading/_money_truth.md
```
So the *path is correct* (`TradingOutcomeProvider.context_domain = "trading"` → `/workspace/operation/trading/_money_truth.md`, exactly where kvk lacks it and a2 has it). The empty-stub-on-zero-fills behavior is *intended*. The code is not the bug; its **caller is missing**.

**2. `reconcile_user` has no live scheduler caller.**
`grep -rn "reconcile_user"` across `api/` returns only:
- `services/outcomes/reconciler.py` (the definition + a docstring),
- `services/outcomes/operator.py:254` (a *manual* operator-CSV-intake path),
- `services/outcomes/__init__.py` (the export).

There is **no call from `unified_scheduler.py`, the wake/dispatch path, or `reviewer_envelope.py`.** The scheduler tick walks hooks + drains the wake queue; it never invokes the mechanical reconciler.

**3. The documented caller was dissolved.** `reconciler.py:13-14` still claims *"The back-office task `back-office-outcome-reconciliation` (ADR-195 Phase 2) calls `reconcile_user` once per user per day."* But **back-office tasks were dissolved into recurrences by ADR-260/261**; the only surviving references to `back-office-outcome-reconciliation` are a one-shot migration script (`phaseB_unify_recurrences.py`) and dead docstrings. The caller is gone; the docstring is stale.

**4. The judgment recurrence prompt asserts the dissolved precondition as already-true.** Both kvk and a2 run the identical `outcome-reconciliation` prompt:
> *"The deterministic reconciler **has folded** yesterday's fills into `operation/trading/_money_truth.md` (signal attribution recovered via the broker's client_order_id round-trip). **Read the reconciled outcomes** and reason about them as the operation's standing judgment…"*

This tells the agent to *read* a file the (now-uncalled) mechanical step was supposed to have just written. With zero fills there is also nothing for the LLM to fold, and the judgment wake has no mandate/primitive to create the stub itself. So the wake fires (kvk has 2,032 events), reads a prompt premised on a fold that never happened, finds no `_money_truth.md`, and reasons over absence.

**5. Downstream the chain goes dark.** `daily_pnl_email.maybe_send_daily_pnl_email` returns `{"sent": False, "reason": "no_money_truth"}` (line 296) when the organ is absent — so kvk also never receives a P&L email. Reflection-loop join (verdict ↔ outcome) has nothing to bind. Any tenure / self-improvement eval on kvk is **structurally impossible** until the organ exists.

## Why a2 has the file and kvk doesn't

a2's stub frontmatter says *"initialized at first outcome-reconciliation fire 2026-06-10"* — i.e. a2 got bootstrapped through *some* path (the manual `operator.py` intake, or a back-office run that fired before the ADR-260/261 collapse removed the caller). kvk never got that one-time bootstrap, and nothing in the live path will ever create it now. **The organ's existence is currently an accident of bootstrap history, not a guaranteed invariant** — which is the actual conflict: a workspace can run its full trader recurrence set indefinitely and never acquire its ground-truth organ.

## The conflict, stated for the fix-author (Hat-A)

This is a **single-writer / dissolved-caller** defect (ADR-286 + ADR-260/261 fallout): the path `/workspace/operation/trading/_money_truth.md` has a *designed* writer (`reconcile_user`'s empty-stub branch) whose **scheduler invocation was removed when back-office tasks dissolved**, and the surviving *judgment* recurrence prompt **claims the mechanical step ran**. Three coherent repair directions (for discourse, not prescribed here):

1. **Re-wire the mechanical reconciler into the live path** — call `reconcile_user` (mechanically, zero-LLM) *before* the `outcome-reconciliation` judgment wake assembles its envelope, so the prompt's "has folded" precondition is true again. Most faithful to the prompt's existing contract; restores the empty-stub-on-first-run guarantee. (Where: the dispatch path for the `outcome-reconciliation` slug, or a scheduler pre-step gated on that slug — mirror the `daily_pnl_email` post-step at `wake.py:830`.)
2. **Materialize the organ at activation** — write the `_init_money_truth` stub during `fork_reference_workspace` so every trader workspace has the organ from day one (decouples organ existence from fill history). Simplest invariant; doesn't fix the "has folded" prompt lie for ongoing reconciliation.
3. **Both** — activation seeds the stub (invariant) *and* the mechanical fold runs before the judgment wake (ongoing truth). Likely the correct end-state.

Whichever lands, the **stale docstring** (`reconciler.py:13`) and the **prompt's asserted precondition** must be reconciled with reality in the same change (CLAUDE.md §1 doc-alongside-code).

## Scope note — does the author have the same hole?

The alpha-author analog (`_signal.md` is the author's ground-truth organ) does **not** present identically: the author's `_signal.md` exists on the funded test workspace (it is empty, len 0, but present), and the author tenure eval seeds it directly via `write_revision`. The orphaned-`reconcile_user` defect is specifically the **trading provider's** materialization path. Whether the author's `_signal.md` is materialized by a live caller or only by manual/seed paths is a **separate check worth doing** before relying on the author rig long-term — flagged, not audited here.

## Receipts index

| Claim | Receipt |
|---|---|
| kvk lacks `_money_truth.md`; a2 has it | `workspace_files` query, this session |
| empty-stub-on-zero-fills is intended | `ledger.py:104-128` |
| trading domain → `operation/trading/_money_truth.md` | `outcomes/trading.py:40` `context_domain = "trading"` |
| `reconcile_user` has no live scheduler/dispatch caller | `grep -rn reconcile_user api/` → only def + `operator.py` (manual) + `__init__` |
| documented caller dissolved | `reconciler.py:13` stale; `back-office-outcome-reconciliation` only in `phaseB_unify_recurrences.py` + docstrings; ADR-260/261 |
| prompt asserts the fold already happened | kvk + a2 `outcome-reconciliation` recurrence prompt: *"has folded … Read the reconciled outcomes"* |
| downstream P&L goes dark | `daily_pnl_email.py:296` `no_money_truth` |
| a2 bootstrapped via a one-time path | a2 stub frontmatter *"initialized at first outcome-reconciliation fire 2026-06-10"* |
