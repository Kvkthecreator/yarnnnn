# 2026-05-13 — Regime wiring — close the "declared but unenforced" gap

> **Type**: Architectural-shift observation. Records the substrate + recurrence + principles change that wires the regime predicate end-to-end.
> **Trigger**: Conversational architecture audit on 2026-05-13 (same day as iter-1 + iter-2). Surfaced that `_operator_profile.md` Signal 5 (volatility-regime filter) and `_risk.md::apply_vix_regime_scalar` were declarative in substrate but unenforced anywhere in the runtime path.
> **Not an iter**: This is a follow-on from iter-2's architectural audit, not a steered-session iteration. No live persona was operating during this change. The verification path runs against kvk's next post-activation chain.

---

## Classification

- **Objective:** A-system (primary). Regime is structural infrastructure that gates sizing.
- **Within-A scope:** systematic-workflow (new judgment recurrence + principles enforcement) + substrate-shape (new `_regime.yaml`).
- **FOUNDATIONS dimension:** Substrate (new canonical `_regime.yaml` file + new spec) + Mechanism (new judgment recurrence + new Reviewer rules) + Trigger (semantic schedule `@market_close + 30min` per ADR-268).
- **Severity:** declarative-unenforced (the worst kind — substrate says "this matters" while runtime ignores it; same trap class as the L2/L3 gaps surfaced in iter-2).
- **Resolution path:** bundle-level evolution (no kernel changes, no new ADR, per ADR-176 work-first + ADR-188 contextual workspace).
- **Money impact:** sizing-impact when active. Operator declared the scalar reduces all sizing by 0.5 in elevated-VIX regimes; without enforcement, the operation was always sizing at 1.0×.

---

## What was wrong

Five-layer audit showed:

| Layer | State pre-fix |
|---|---|
| L1 — Operator declares regime intent | ✅ Wired (`_operator_profile.md` Signal 5 + `_risk.md` line 33) |
| L2 — Specs ask for regime reporting | ✅ Wired (`pre-market-brief.md` §4, `weekly-performance-review.md` §4) |
| L3 — Recurrences ingest VIX data | ❌ Missing (VIXY not in `_universe.yaml`; no separate fetch) |
| L4 — Regime is computed | ❌ Missing (nothing computes VIX/VIXY SMA-20 or the predicate) |
| L5 — Regime state is persisted in substrate | ❌ Missing (no `_regime.yaml`) |
| L6 — Reviewer applies regime to sizing at proposal time | ❌ Missing (`principles.md` had no regime rule; `trade-proposal` prompt didn't reference regime) |

Grep confirmation: `apply_vix_regime_scalar` appeared exactly twice in the codebase — both in test-scaffolding scripts as prose. **No code path multiplied position size by 0.5 anywhere.**

This is the same shape as iter-2's three-layer trade-execution gap: substrate declares intent, prompts describe the flow, runtime wiring never lands. Same trap class.

---

## What shipped

**Zero Python code.** Five files, all bundle-level + behavioral-artifact updates:

1. **`docs/programs/alpha-trader/reference-workspace/specs/regime-state.md`** (new) — schema for `_regime.yaml`, documents the VIXY-as-VIX-proxy decision with calibration thresholds (operator-tunable defaults: `vixy_active_threshold: 22.0`, `vixy_deactivation_threshold: 17.5`).
2. **`docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`** — new `track-regime` judgment recurrence at `@market_close + 30min` (ADR-268 semantic schedule), reads VIXY + SPY via existing `platform_trading_get_market_data` tool, computes SMAs + regime predicate + trend regime, writes `_regime.yaml`. Plus `trade-proposal` prompt extended with regime-read + scalar-application requirement before sizing math.
3. **`docs/programs/alpha-trader/reference-workspace/review/principles.md`** — two new Hard rejection rules: rule 6 (regime scalar must be cited correctly in `sizing_formula_trace`) and rule 7 (regime substrate freshness — reject if `_regime.yaml` is >24h old or `data_stale: true`). Rule 7 carries a bootstrap exception that mirrors the existing money-truth bootstrap clause: when `_regime.yaml` doesn't exist yet, treat as inactive with `scalar = 1.0` and explicit trace note. Calibration begins from zero; we don't refuse-to-trade on cold-start.
4. **`docs/alpha/observations/2026-05-13-regime-wiring.md`** (this file).
5. **`api/prompts/CHANGELOG.md`** — entry per CLAUDE.md rule 7 (recurrence prompts + principles.md are behavioral artifacts).

---

## Why this shape (Option A vs. Option B)

Considered two scopes:

- **Option A (shipped)**: honor the minimum the operator declared. VIX scalar only. Binary on/off. Portfolio-wide. Trend regime reported but not actuated.
- **Option B (deferred)**: build per-signal regime gating (`valid_regimes: [...]` on each signal), promote trend regime to a sizing input.

Chose A. Three reasons:

1. **Singular Implementation favors honoring declared intent before expanding.** The operator wrote a minimal regime model; wire that. If observation says it's too crude, expand with evidence.
2. **The article-validated learning was "regime is the missing input."** Satisfied by L3-L6 wiring of the existing declaration. The architectural claim doesn't require expanding the *declaration*.
3. **`trend_regime` is reported but not actuated.** This is honest about what was declared. Promoting trend to a sizing input is a `principles.md` evolution, not a schema or infrastructure change — easy to do later if observation warrants.

---

## Why no Python code

Initial implementation plan called for `api/services/back_office/regime_tracker.py`. Re-audit found:

- `api/services/back_office/` was deleted by ADR-260/261/262 ("back-office work is now Reviewer-driven recurrence prompts").
- The closest analog (`track-universe`) computes indicators (SMA/RSI/ATR) **via the LLM at runtime**, not in Python — Alpaca doesn't ship indicators, and adding Python indicator math creates a parallel-implementation problem.
- Mechanical `SyncPlatformState` (ADR-264) is the pattern for pure mirroring, but regime needs SMA computation, so it fits judgment-mode by the existing pattern.

Singular Implementation: match what `track-universe` does. Same primitives. Same shape. Different substrate target.

---

## Why no new ADR

Kernel boundary (ADR-222) is preserved:

- No new primitive (uses existing `platform_trading_get_market_data` + `WriteFile`).
- No new registry entry.
- No `directory_registry.py` change (`/workspace/context/trading/` exists; `_regime.yaml` is a new file within an existing domain).
- No `task_types.py` change (not a task type — it's a bundle-level recurrence per ADR-261).
- No FOUNDATIONS amendment.

This is the shape ADR-176 + ADR-188 were built for — contextual bundle evolution without kernel touch. ADR-264 D5 explicitly anticipates per-bundle judgment recurrences for compute work.

---

## Verification path

Post-merge, on kvk's workspace:

1. **Pre-flight (zero changes needed)**: kvk's live workspace already has the original 13-entry `_recurrences.yaml` from the most recent fork. To pick up the new `track-regime` entry + extended `trade-proposal` prompt + new `principles.md` rules, run a re-fork — operator-driven re-activation per ADR-226 (skipping ahead of bundle-version migration tooling). Note: this overwrites operator-customized substrate; reasonable for alpha persona, not for real operators (ADR-226 follow-on tooling pending).

2. **First `track-regime` fire**: next post-RTH-close fire (~16:30 ET / 05:30 KST next morning local). Expected: `/workspace/context/trading/_regime.yaml` lands with current VIXY close + SPY close + computed predicates. Watch `/workspace/review/decisions.md` for a freshness-degradation note if Alpaca's market-data endpoint is rate-limited or unreachable.

3. **First post-regime `signal-evaluation` + `trade-proposal`**: next RTH morning. If a signal fires, the resulting proposal's `sizing_formula_trace` MUST include either the active-regime line (with VIXY value) or the inactive-regime line (`regime_scalar: 1.0`). If trace is silent on regime, rule 6 rejects the proposal — observable in `decisions.md`.

4. **Bootstrap-exception verification**: if a signal fires before the first `track-regime` fire completes (gap window: first ~24h after activation), proposal should include `"regime_scalar: 1.0 (bootstrap — _regime.yaml not yet populated)"`. If the Reviewer either rejects or omits the bootstrap note, the principles rule needs language tightening.

5. **Regression — existing reports**: `pre-market-brief` §4 (Regime State section) and `weekly-performance-review` §4 (Regime History section) should now read directly from `_regime.yaml` instead of computing inline. Operator should observe no regression in either deliverable's regime content; section quality may improve since the Reviewer is no longer doing the compute twice.

---

## Friction

Three honest costs of this shape:

1. **VIXY proxy tracking error**: Alpaca doesn't carry spot VIX, so VIXY (a futures ETF) approximates the operator's declared "VIX > 25" predicate. Operator may need 30+ days of observation to tune `vixy_active_threshold` from the default 22.0. Documented in `regime-state.md`. The alternative (non-Alpaca data source) would require new infrastructure outside iter scope; deferred.

2. **Bootstrap exception is a small attack surface**: an operator (or a buggy `track-regime` recurrence) could leave `_regime.yaml` permanently absent, and rule 7's bootstrap clause would treat regime as inactive forever. Mitigated by morning-calibration's general substrate-freshness checks (operator-side observation) but not hard-gated. Acceptable for paper trading; should be tightened before Alpha-2 live decision.

3. **Trend regime is reported but unused at sizing time.** Specs ask for it, `_regime.yaml` carries it, no rule reads it. This is the declared minimum; promoting trend-regime to sizing is a `principles.md` evolution after observation.

---

## What this does NOT close

- **Iter-2's L3 gap** (capability flow from recurrence YAML → DispatchSpecialist → `get_headless_tools_for_agent`). Regime doesn't need L3 because it uses the Reviewer's existing `platform_trading_get_market_data` path (same as `track-universe`), not specialist sub-LLM dispatch. L3 remains queued for a follow-on iter with its own ADR.

- **Cost-truth wiring** (SCOPE.md commitment). Money-truth is wired via `outcome-reconciliation`; cost-truth (actual fees + slippage + infra cost per trade) is half-built and load-bearing for Alpha-2 live-trading decision. Out of scope here.

- **Per-signal regime conditioning** (`valid_regimes: [...]` on each signal). Option B, deferred until operator observation warrants.

---

## Links

- **Operator's declared regime intent**: [_operator_profile.md Signal 5](../../programs/alpha-trader/reference-workspace/context/trading/_operator_profile.md) lines 52-56
- **Risk file regime scalar declaration**: [_risk.md line 33](../../programs/alpha-trader/reference-workspace/context/trading/_risk.md) `apply_vix_regime_scalar: true`
- **New spec**: [regime-state.md](../../programs/alpha-trader/reference-workspace/specs/regime-state.md)
- **Recurrence + prompt change**: [_recurrences.yaml](../../programs/alpha-trader/reference-workspace/_recurrences.yaml) — new `track-regime` entry + extended `trade-proposal` prompt
- **Principles rules**: [principles.md](../../programs/alpha-trader/reference-workspace/review/principles.md) Hard rejection rules 6 + 7
- **Iter-2 (predecessor)**: [2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md](./2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md) — same trap class, different gap
- **ADR-264** (substrate-canonical, judgment-vs-mechanical pattern): docs/adr/ADR-264-substrate-canonical-world-and-syncplatformstate.md
- **ADR-268** (semantic schedules): docs/adr/ADR-268-market-context-aware-recurrences.md
- **CHANGELOG entry**: api/prompts/CHANGELOG.md `2026.05.13.1`
