# 2026-05-13 — kvk — Iteration 1: E2E aliveness exercise from cold-start

> **Type**: Steered-session observation seed. Scaffolded at the start of the session; body filled in during/after execution. KVK steers; Claude operates Mode 1 per [CLAUDE-OPERATOR-ACCESS.md](../CLAUDE-OPERATOR-ACCESS.md).
> **Iteration**: 1 of N. First iteration of the steered closed-loop development pattern named in [OPERATOR-HARNESS.md §"Steered session pattern"](../OPERATOR-HARNESS.md).
> **Persona**: `kvk` (`kvkthecreator@gmail.com`, paper Alpaca EE8K)
> **Why this opener**: cold-start purge tests the *whole* loop from scratch. If post-purge bootstrap is green end-to-end, everything upstream of trade behavior is verified before subsequent iterations look at trade-decision quality.

---

## Classification

- **Objective:** A-system (primary), B-product (secondary — confirms the system is alive enough to *produce* B-data in later iterations)
- **Within-A scope:** systematic-workflow (bootstrap path), qualitative-agent-behavior (Reviewer reasoning quality post-trilogy-fix)
- **FOUNDATIONS dimension:** Substrate (workspace re-fork), Identity (Reviewer + Specialists materialize), Trigger (scheduler walk + reactive wake), Mechanism (deterministic mirror + judgment-mode dispatch)
- **Severity:** *(filled post-run)*
- **Resolution path:** *(filled post-run)*
- **Money impact:** none for this iteration (no trades expected during the exercise window itself; this confirms the loop is alive so subsequent iterations can interpret trade behavior)

---

## Stated objective (the single thing this iteration confirms)

**E2E aliveness from cold-start.** Specifically: a clean-state `kvk` workspace, re-bootstrapped via the canonical harness, can complete the full Mandate → Reviewer-loop → narrative-trail chain without falling over at any layer.

Concretely, six aliveness invariants:

1. **L4 reset purges cleanly**: `reset.py kvk --confirm` returns 200; post-purge `verify.py kvk` shows expected pre-activation shape (1 YARNNN agent, skeletons present, 0 specialists, 0 recurrences, 0 platform_connections).
2. **Activation forks the bundle**: `activate_persona.py --persona kvk` reads `personas.yaml`, forks `docs/programs/alpha-trader/reference-workspace/` per ADR-226, applies persona overrides, populates `_recurrences.yaml` with 14 entries (11 judgment + 3 mechanical mirrors), and inline-materializes the scheduling index per the 2026-05-11 ADR-226 amendment.
3. **Platform connect succeeds**: `connect.py kvk` POSTs paper Alpaca creds to `/integrations/trading/connect`, Render encrypts, `platform_connections` row created.
4. **Post-bootstrap verify is green**: `verify.py kvk` shows 29/29 invariants (Alpaca connected) — confirms structural health on Objective A.
5. **Reviewer can wake and reason**: at least one judgment-mode invocation (addressed or scheduled) produces a `decisions.md` entry with **real prose reasoning**, not enum-string residue. This is the load-bearing aliveness check post-trilogy-fix (`6027459` / `85c9736` / `e55d201`).
6. **Mechanical mirrors fire**: at least one of the three `@primitive: SyncPlatformState` mirror recurrences (`track-account` / `track-orders` / `track-positions`) writes substrate on its next due tick. Zero-LLM path stays alive.

If all six are green, the system is alive end-to-end and Iteration 2 (Reviewer reasoning audit) gets a clean baseline to interpret. If any fails, the failure becomes the work; subsequent iterations queue.

---

## Procedure

Steered. KVK directs each step; Claude narrates intent before each consequential action per the steered-session pattern. Per-turn-go default-deny rule applies to all state-mutating commands per [CLAUDE-OPERATOR-ACCESS.md §"Architectural authority vs invocation authorization"](../CLAUDE-OPERATOR-ACCESS.md#architectural-authority-vs-invocation-authorization-the-axiom).

```bash
# Phase 1 — Pre-purge state capture (read-only, no per-turn go needed)
.venv/bin/python -m api.scripts.alpha_ops.verify --persona kvk --cost --cost-days 7
# Capture: current recurrence count, last decisions.md entries, cost rollup before purge

# Phase 2 — Purge (DEFAULT-DENY: needs explicit per-turn go from KVK)
.venv/bin/python -m api.scripts.alpha_ops.reset kvk --confirm

# Phase 3 — Activate (DEFAULT-DENY: needs explicit per-turn go)
.venv/bin/python -m api.scripts.alpha_ops.activate_persona --persona kvk --skip-connect

# Phase 4 — Verify cold-start shape (read-only)
.venv/bin/python -m api.scripts.alpha_ops.verify --persona kvk
# Expected: 28/29 (1 FAIL = platform_connections count 0 vs expected 1, pre-connect)

# Phase 5 — Connect Alpaca (DEFAULT-DENY: needs explicit per-turn go)
#          Requires ALPHA_KVK_ALPACA_KEY + ALPHA_KVK_ALPACA_SECRET in env (1Password)
.venv/bin/python -m api.scripts.alpha_ops.connect kvk

# Phase 6 — Post-connect verify (read-only)
.venv/bin/python -m api.scripts.alpha_ops.verify --persona kvk
# Expected: 29/29

# Phase 7 — Open feed surface and author MANDATE
#           KVK uses cockpit (Mode 2). Claude observes via service-key reads.
#           Mandate authoring belongs to KVK — never Claude unilaterally.

# Phase 8 — First addressed Reviewer turn observation
#           KVK types a question into the feed addressed to the Reviewer.
#           Claude reads /workspace/review/decisions.md tail post-turn,
#           verifies entry is well-formed prose (not enum string).

# Phase 9 — Scheduled recurrence observation
#           Wait for next due tick OR fire one judgment-mode recurrence manually
#           (DEFAULT-DENY for external_action recurrences; safe for accumulation-shape).
#           Claude reads decisions.md tail again, verifies recurrence-fire entry shape.
```

---

## Expected observable per layer

| Aliveness invariant | Code layer (yarnnn correctness) | System layer (yarnnn-as-used) | Outcome layer (paper EE8K) |
|---|---|---|---|
| 1. L4 reset purges cleanly | `reset.py` returns 200; SQL inspection shows agents/tasks/workspace_files/platform_connections all gone for kvk's user_id | — | — |
| 2. Activation forks bundle | `_recurrences.yaml` exists with 14 entries; `_shared/MANDATE.md`, `IDENTITY.md`, `BRAND.md`, `AUTONOMY.md`, `PRECEDENT.md` present; `review/IDENTITY.md` + `review/principles.md` present; `context/trading/_operator_profile.md` + `_risk.md` + `_universe.yaml` present; `specs/` library forked (5 files) | — | — |
| 3. Platform connect | `platform_connections` row created with `kind='trading'`, `status='connected'`; encrypted creds present | — | Paper EE8K account responds to Alpaca API ping |
| 4. Verify 29/29 | All invariants in `personas.yaml::expected` block pass | — | — |
| 5. Reviewer wakes + reasons | `decisions.md` gets one new `--- decision ---` or `--- recurrence-fire ---` entry; entry has multi-line prose reasoning (not enum string like `"stand_down"`) | Feed surface shows ReviewerCard rendering verdict; per-action narration appears as System Agent bubbles | — |
| 6. Mechanical mirror fires | `/workspace/context/portfolio/{account,orders,positions}.yaml` updated by `SyncPlatformState`; no token_usage row (zero-LLM path) | — | Position/account state from Alpaca paper reflected in substrate |

---

## The four-way "no trades" disambiguation

Naming this here so the *next* iteration (reasoning audit) has the four hypotheses to classify against. Not the question for *this* iteration — Iter 1 confirms aliveness, period — but the work that follows depends on this being explicit.

| Hypothesis | What it looks like in `decisions.md` | What it looks like in `token_usage` | What it looks like in `_money_truth.md` | Disambiguator |
|---|---|---|---|---|
| **A. Environmental** (operator timezone vs US RTH) | Recurrence-fire entries exist; reasoning correctly notes "market closed, no evaluation" or absent during off-hours | Normal cadence; cost-per-fire ~$0.01-0.10 (Haiku, evaluation correctly short-circuits) | Untouched (no candidates) | Markets-open observation window (Iter 3) — same persona, same code, different time-of-day |
| **B. Systematic-dispatcher** (Reviewer literally never wakes) | Either zero new entries OR entries with enum-string reasoning ("stand_down" verbatim, no prose) | Zero fires OR fires that all log the universal stand_down at ~$0.30 each | Untouched | Post-trilogy-fix Reviewer activity audit — was today's fix load-bearing |
| **C. Systematic-judgment** (Reviewer wakes, reasons, correctly declines) | Entries with rich prose reasoning declining trades on declared check (Check 1 attribution, Check 4 expectancy guardrail, Check 5 sizing, etc.) | Normal cadence + cost | Untouched if no fires; updated if some fires hit reconciler | Cross-reference reasoning text against `principles.md` six-check ladder — is the decline well-formed |
| **D. Systematic-config** (Reviewer wakes, reasons, declines because AUTONOMY/principles too restrictive) | Entries with prose reasoning declining on `_risk.md` ceiling or AUTONOMY `auto_approve_below_cents` boundary | Normal cadence + cost | Untouched | Read `_risk.md` + `AUTONOMY.md` + principles.md; check if declared posture is what KVK intended |

A → environmental, not actionable here (queue for markets-open observation)
B → code bug, must fix before iterating
C → success, not failure (write up + move to other observations)
D → mis-config, edit operator substrate (KVK authority, not Claude)

These produce identical observable surfaces (zero executions) without the disambiguator. Conflating them is the failure mode this iteration's aliveness exercise prevents downstream.

---

## Context

*(filled post-run)*

## What happened

*(filled post-run)*

## Friction

*(filled post-run)*

## Hypothesis

*(filled post-run)*

## Counterfactual (Objective B only)

*(filled post-run, even if "N/A — Iter 1 doesn't test trade decisions")*

## Links

- Steered-session pattern: [OPERATOR-HARNESS.md §"Steered session pattern"](../OPERATOR-HARNESS.md)
- "No trades" failure class: [DUAL-OBJECTIVE-DISCIPLINE.md §"Named failure classes"](../DUAL-OBJECTIVE-DISCIPLINE.md)
- Reviewer dispatcher fix series: commits `6027459` (context-shape contract), `85c9736` (reasoning capture), `e55d201` (context-key mismatch)
- PnL substrate rename: commit `2c11c4e` (ADR-267 + canonical rename sweep)
- Persona registry: [personas.yaml](../personas.yaml) → `kvk` row
- Prior post-refactor observation: [2026-04-29-post-refactor-wave-e2e.md](./2026-04-29-post-refactor-wave-e2e.md)
