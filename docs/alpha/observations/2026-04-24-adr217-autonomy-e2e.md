# alpha-trader E2E Observation Log — ADR-217 Workspace Autonomy Validation

> **Run date**: 2026-04-24 (immediately after ADR-216 E2E same session)
> **Session operator**: KVK + Claude (Mode 1, headless)
> **Commits exercised**: ADR-217 1–4 (ADR + substrate wire-up + scaffold migration + canon doc)
> **Purpose**: Validate ADR-217 workspace-autonomy unification — does moving delegation from Reviewer-owned modes.md to workspace-scoped `/workspace/context/_shared/AUTONOMY.md` close the E2E governance conflict while preserving the narrow-never-widen invariant?
> **Status**: ADR-217 validated end-to-end. Simons persona correctly narrowed delegation per D4. Architecture works as designed.

---

## Headline finding

**ADR-217 works.** The dispatcher reads AUTONOMY.md cleanly through the rewritten `load_autonomy()` path. The Reviewer agent (now `ai:reviewer-sonnet-v3`) reasons with explicit awareness of the narrow-never-widen rule. And the Simons persona's `principles.md` narrowing conditions — authored at Commit 3 — fire correctly against the fresh-account state.

Reviewer verdict on the NVDA test proposal:

> "All six checks pass on their face — Signal 2 attribution is clean, RSI(14)=23.4 fires the <25 trigger, quality filter and trend condition pass, sizing math is formula-compliant... all _risk.md limits are within bounds, and sector/portfolio concentration is acceptable. However, principles.md §Narrowing conditions explicitly states: 'If _performance.md doesn't yet exist (fresh account — I have no track record to calibrate against)' → defer. The _performance.md substrate confirms zero realized trades... The Check 4 expectancy figures cited in the rationale are explicitly labeled 'synthesized' (not realized), which means they carry no epistemic weight under this framework."

`reviewer_identity: ai:reviewer-sonnet-v3` — v3 live in prod, confirming ADR-217 Commit 2 shipped cleanly.

---

## What's different vs the ADR-216 E2E earlier in the session

Same persona (Simons), same proposal shape (NVDA Signal 2 mean-reversion-oversold), same substrate reads. But:

| Dimension | Earlier (ADR-216 only) | Now (ADR-216 + ADR-217) |
|---|---|---|
| Autonomy declaration location | `/workspace/review/modes.md` (Reviewer-owned) | `/workspace/context/_shared/AUTONOMY.md` (workspace-scoped, operator-authored) |
| Dispatcher read path | `load_modes()` → `modes_for_domain()` | `load_autonomy()` → `autonomy_for_domain()` with `default` fallback |
| principles.md carried | Auto-approve policy + framework (two concerns) | Framework + narrowing conditions only (one concern) |
| Reviewer identity | `ai:reviewer-sonnet-v2` | `ai:reviewer-sonnet-v3` (explicit narrow-never-widen invariant) |
| Conflict resolution | Reviewer inferred the rule correctly at runtime | Rule is now in the system prompt explicitly |
| Governance shape | 3 authoring mouths (modes + principles Auto-approve + MANDATE) | 1 authoring mouth (AUTONOMY.md), with principles.md as narrowing layer |

The earlier E2E deferred because principles.md + modes.md disagreed on Auto-approve. This E2E deferred because principles.md's narrowing condition ("defer when _performance.md empty") fires regardless of delegation ceiling. **Two different reasons for the same observable outcome** — but only the second is architecturally clean. The earlier deferral was conflict resolution; the current deferral is declared framework working as specified.

---

## The governance lesson for the operator

Post-ADR-217, the question "why did my persona defer even though I set bounded_autonomous?" has a clean answer: **your persona's narrowing conditions fired**. Specifically, `principles.md §Narrowing conditions this persona imposes` declares that the Simons persona defers when `_performance.md` doesn't exist. Fresh account → empty track record → defer, by design.

To actually see the bold-autonomy flow through to an Alpaca paper order on a fresh account, the operator has two choices:

1. **Let the first ~20 trades route through the Queue manually.** The persona is working exactly as designed — it refuses to act autonomously with no track record. Accept that, click approve in the Queue, populate `_performance.md` via outcome reconciliation, watch the narrowing condition relax after 20 trades.

2. **Edit the narrowing condition in principles.md.** The operator can author "trust synthesized expectancy baselines for the first N trades" or "defer only when `_performance.md` shows negative expectancy, not when it's absent" — principles.md is operator-authored framework. The persona applies whatever the operator declares.

Both are legitimate. The architecture doesn't decide; it surfaces the choice legibly via decisions.md. The verdict quotes the exact principles.md clause it applied. Future edits to principles.md would produce different verdicts on the same proposal, and the decisions.md log would make the evolution visible.

---

## What's architecturally confirmed by this run

### 1. Single authoring mouth for delegation works

Pre-ADR-217: modes.md (`bounded_autonomous`) + principles.md (`Auto-approve = NONE`) + MANDATE (amended carve-out). Three files disagreed. Reviewer resolved via strictest-source.

Post-ADR-217: AUTONOMY.md (`trading.level: bounded_autonomous, ceiling_cents: 2000000`) is the sole authoritative delegation mouth. principles.md carries only the framework + narrowing conditions. MANDATE describes the intended posture and references AUTONOMY.md as the enforced version. **No conflict to resolve** — three files, different concerns, same operator intent expressed coherently across all three.

The run never triggered "modes says X but principles says Y" reasoning. The only defer logic that fired was the declared narrowing condition. Clean.

### 2. Narrow-never-widen invariant is semantically live

The v3 system prompt declares the invariant explicitly:

> "Your principles can narrow delegation (add defer conditions) but never widen it. If your principles and the raw delegation conflict on auto-approve eligibility, apply the stricter."

The Reviewer's verdict cites the narrowing condition by name (`principles.md §Narrowing conditions`) and explains *why* it applied (empty `_performance.md`). This is the architecture working exactly as D4 specified.

Note: the dispatcher's `is_eligible_for_auto_approve` returned `eligible=True` (bounded_autonomous, $3,390 ≤ $20,000 ceiling, reversible, not in never_auto). The Reviewer agent saw that green light and still deferred because its own persona-framework has a narrower boundary. This is the servant being more conservative than the master permits — exactly the ADR-217 D4 rule.

### 3. Category correction validated

Placing AUTONOMY.md under `/workspace/context/_shared/` (sibling to MANDATE/IDENTITY/BRAND/CONVENTIONS) rather than `/workspace/review/` means the seat rotation primitive can't accidentally overwrite the delegation. Seat rotation (future) would touch OCCUPANT.md + handoffs.md only; AUTONOMY.md stays put. Operator's standing intent survives occupant swaps, as ADR-217 D8 specified.

### 4. Scaffold update pattern is reusable

The scaffold_trader.py migration (Commit 3) demonstrates the pattern for moving a persona across the reframe:

- Delete old constant (`REVIEWER_MODES_MD`).
- Add new constant (`REVIEWER_AUTONOMY_MD`) with narrowed schema.
- Edit `PRINCIPLES_MD` to remove operational policy sections (they move to the new file).
- Swap SUBSTRATE_FILES entries.
- Update module docstring + print banner.

This same shape will apply for alpha-commerce + any future persona scaffolding. One template, every future persona follows it.

### 5. CHANGELOG + canon doc discipline shows value immediately

The session generated three canon-doc artifacts:

- ADR-217 (the decision).
- `api/prompts/CHANGELOG.md` entry [2026.04.24.3] (the prompt change + migration guidance).
- `docs/architecture/agent-composition.md` (the running architectural reference).

A future Claude or engineer opening the codebase doesn't have to piece together what happened across multiple ADRs — they can read agent-composition.md for the current state, CHANGELOG.md for the prompt history, and ADR-217 for the specific decision's reasoning. Each doc serves a distinct purpose; together they make the iteration cumulative rather than scattered.

---

## What didn't need any work

- The Alpaca connection logic — connect.py just works.
- The purge flow — the FK-order hotfix from earlier in the session + ADR-217 cleanup left the reset path clean.
- The specialist pre-ensure bridge — works identically to the ADR-216 E2E.
- The `_performance.md` read path — handled correctly as "empty means thin substrate" by the Reviewer.

---

## Open items (not blocking)

### verify.py invariants still stale

The script still expects pre-ADR-205 roster (12 agents, trading_bot row, etc.). Noted during the ADR-216 E2E; not fixed this session. Eventual follow-up: rewrite verify.py invariants against the post-ADR-217 world (YARNNN only at signup, no modes.md, AUTONOMY.md in `_shared/`).

### proposal-cleanup materialization py3.9 leak

`[PROPOSE_ACTION] proposal-cleanup materialize failed: unsupported operand type(s) for |: 'type' and 'NoneType'` — py3.10+ union syntax in a swallowed code path. Unrelated to ADR-217; surfaces in local-harness runs only (Render is py3.11). Separate hardening pass.

### Autonomous-action chat notifications (ADR-217 D6)

ADR-217 D6 declares that when autonomy permits the AI to act without human click, a `role='system'` message lands in the active chat thread. This is pending frontend work and didn't need to fire in this E2E because the Reviewer deferred. When a later proposal does auto-approve (post-20-trade calibration OR after operator narrows principles.md), D6 will want validation.

---

## Summary

### What worked
- ADR-217 Commit 2 substrate + dispatcher wire-up clean end-to-end.
- Reviewer v3 prompt live; narrow-never-widen invariant explicit.
- Scaffold_trader migration produces the new 8-file substrate set cleanly.
- The Simons persona reasoned substrate-specifically about the narrowing condition, citing the principles.md clause by name.
- The delegation ceiling in AUTONOMY.md held (dispatcher reported eligible=True, $3,390 ≤ $20,000) but was narrowed by the persona's own framework (correct D4 behavior).

### What didn't need changing
- The earlier ADR-216 persona wiring (Commit 2) — works identically; v2 → v3 bump is prompt-only, no structural change.
- Alpaca connection.
- Purge harness.
- Specialist pre-ensure bridge.

### What the observation proves about ADR-217

**Workspace-scoped autonomy with narrow-never-widen is architecturally right.** The single authoring mouth removed the ADR-216 E2E's three-mouth governance conflict; the narrow-never-widen invariant preserved the operator's ability to author persona-specific defer rules; the substrate relocation (AUTONOMY.md → `_shared/`) cleanly separated operator-intent from seat-bound substrate.

The E2E didn't produce an autonomous Alpaca order — but the reason it didn't is **exactly the reason the architecture wants it not to**, and that reason is now legibly surfaced in decisions.md with quote-level precision.

### What follow-ups naturally surface

1. **Canon doc maintenance**: agent-composition.md should be amended whenever ADRs touch composition (per §5.3). The next such ADR is the test.
2. **Operator affordance**: principles.md editing surface. The operator can currently edit it directly via the Files tab, but there's no symmetric chat-driven path (UpdateContext target for principles). Consider a future commit adding `target="principles"` to UpdateContext for parity with `target="autonomy"` and `target="mandate"`.
3. **Commerce persona**: scaffold_commerce.py (when it exists) should follow the same pattern — AUTONOMY.md declaring commerce delegation, principles.md carrying commerce-persona framework.
4. **First-N-trades autonomy carve-out**: architectural pattern worth a future ADR — "persona grants narrow auto-approval during calibration period (first N trades), then tightens after enough outcomes accumulate." Different from simple manual-then-bounded progression.

---

## What the conversation learned that doesn't belong in code or ADRs

The session's conceptual arc was the real architectural work:

1. **Autonomy is orchestration, not judgment.** Operator-authored delegation the Reviewer executes within, not Reviewer-owned config.
2. **Persona ≠ principles ≠ autonomy.** Three axes (Identity/Purpose-at-agent/Purpose-at-workspace) needing three files with different edit cadences.
3. **File placement follows authorship.** Reviewer-seat vs operator-workspace is the right category axis, not what-the-Reviewer-reads.
4. **Canon docs close iterative-refactoring gaps.** Every reframe adds ADRs; without a running reference, each new reader reconstructs the picture from scratch.

These were conceptual alignments during the session. Most of them landed in ADR-217's prose, but the meta-lesson — that architectural conversations like this one produce value beyond code — is itself worth preserving as a session artifact.

---

## Next-cycle setup

The E2E validates the architecture. To advance the actual trading operation:

1. **Let the first 20 trades route through the Queue.** Operator clicks approve; each click → ExecuteProposal → Alpaca paper order → outcome reconciliation populates `_performance.md`. After 20 trades, the narrowing condition ("_performance.md empty") no longer applies; the Simons persona will auto-approve the 21st proposal if all other checks pass and the expectancy is positive.
2. **Observe the narrowing condition's release.** First auto-approved proposal post-20-trade is the next validation point — proves that the narrowing condition was transient-by-design, not permanent.
3. **Tune ceiling_cents as confidence grows.** Early calibration might start tight; widen as the track record validates.

This is the thesis-prediction path: persona-bearing Agent with operator-authored delegation + framework, reasoning through accumulated substrate, self-improving along a visible calibration axis. ADR-217 validates the first lap. Twenty trades plus one validates the compounding.
