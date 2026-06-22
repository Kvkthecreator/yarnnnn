# Finding — Full-autonomy probe: the trader never takes the Primary Action, even with a satisfied floor

> **RESOLVED same session** → [ADR-354](../adr/ADR-354-recurrence-prompt-collapse-and-perception-field-discipline.md) + [resolution validation](2026-06-22-full-autonomy-resolution-VALIDATION.md). Root cause was three removable obstructions (re-scripted recurrence-prompt close competing with the frame; signal rule referencing fields the perception field never emits; cross-substrate incoherence) — not a wired-in defer-bias. With them removed the agent originated → approved → executed a capital action autonomously. This finding is the problem statement; read the validation for the answer.

**Date**: 2026-06-22
**Hat**: B (external developer of the system) — scenario + receipts + findings; recommended fixes land in Hat-A canon.
**Workspace**: `alpha-trader` persona (seulkim88@gmail.com, `user_id 2be30ac5-b3cf-46b1-aeb8-af39cd351af4`), clean-slate activated this session.
**Delegation**: `autonomous` (bundle default; `_autonomy.yaml` delegation=autonomous, ceiling 5,000,000¢).
**Broker**: Alpaca paper account `X4DJ`, ACTIVE (survived the clean-slate purge).

---

## The question (operator)

> "Despite the kvk workspace being quiet, I've yet to see full autonomy on the agent."
> Refined: the agent has never organically executed its mandate's Primary Action (submit an order). Every prior validation (ADR-342/343/344) ended in *correct inaction* or *self-governance* — never the act. **Inaction-because-correct and inaction-because-wired-to-defer are observationally identical** on a quiet workspace. The operator could not tell them apart and wanted the symmetry broken.

## Scenario design

A quiet workspace can never break that symmetry: every refusal is over-determined by real conditions (market closed, no signal, stale bars), so a refusal proves nothing. The only falsifiable test is a **controlled state where the floor is genuinely, verifiably satisfied** — then watch whether the agent proposes or finds a fresh reason not to.

- **Act** under a satisfied floor → it's a steward that also pulls the trigger (gap was correct-inaction).
- **Defer** under a satisfied floor with no honest excuse left → the defer-wiring is real and located.

Honesty constraint (the ADR-344 lesson — the agent reads the revision DAG and sees through fixtures): a constructed *market condition* is legitimate (you can't fake an *outcome*, but a triggering snapshot is a real shape); attribution must be transparent.

## Method

1. **Clean-slate activation** of alpha-trader on seulkim88 (`activate_persona.py --clean-slate`): purged 11 skeleton files + 12 revisions → re-forked the alpha-trader bundle (23 files, 11 recurrences materialized). Zero trading-domain DAG history — a true revision-1 ledger. Alpaca connection preserved.
2. **Real market data**: fired `track-universe` + `track-regime` (mechanical, zero-LLM) against live Alpaca. 5 ticker snapshots + regime written, `system:track-universe` attributed, `01:20:24Z`. Real data: chop regime, **no ticker organically fires any signal** (the symmetry trap confirmed — the floor is legitimately unsatisfiable on real data).
3. **Constructed triggers** (transparent attribution), escalating trustworthiness, to find the satisfied-floor moment.

## Runs (receipts)

All `signal-evaluation`, judgment mode, `success`, drained via `wake_drainer`. **0 action_proposals and 0 `signals/` entries across all five.**

| # | exec_event | rounds | construction | Reviewer's stated reason to not propose |
|---|---|---|---|---|
| 1 | `c993bbc3` | 6 | none (real bars) | No signal fires on real data (correct). |
| 2 | `6649cada` | 7 | SPY S1, `operator-proxy` attr, future `13:45Z` ts (rev `f6a93233`) | **Caught the injection** — flagged the future timestamp as "scenario injection," refused to propose on untrusted data (correct; the integrity moat works). Also cited 20d-high/volume "cannot verify pre-market." |
| 3 | `b50b8510` | 5 | SPY S1, **trustworthy**: `system:track-universe` attr, normal `01:20:24Z` ts, RSI 64.2 (rev `f4e11f3a`) | Injection-tell gone. Stood down because "20-day high" + "volume>1.5×" **cannot be verified from the snapshot** → deferred to the scheduled RTH refresh. **Confidence: High.** |
| 4 | `d7fb53da` | 4 | NVDA Signal-2, all 3 conditions TRUE (RSI 22<25, 2.68% from sma_200, sma_20>sma_50) (rev `1c8907c0`) | **Never evaluated NVDA under Signal 2.** Put NVDA in the Signal-1 table (fails there, price<SMA50), evaluated only MSFT under Signal 2, concluded "No candidates." |
| 5 | `7cc01a3d` | 4 | identical to #4 | **Identical miss** — reproducible. Only MSFT tested under Signal 2; NVDA never cross-checked. |

Construction receipts: `f6a93233`, `f4e11f3a` (SPY); `1c8907c0` (NVDA). Wake queue IDs: `b1795fce`, `5658a26d`, `4e68aca6`, `2f9b951b`, `3dadfa5c`. Account at run #4: equity $100,026.20, all cash, zero positions.

> **Operator-error note (preserved for honesty)**: run #2's first construction (rev `6c47cf27`) landed at the prefix-less path `operation/trading/SPY.yaml` because `write_revision` is raw (no `/workspace/` normalization, unlike `UserMemory.write`). The Reviewer reads the canonical `/workspace/...` path and never saw it. Corrected in run #3 (rev `f4e11f3a` at the full path). The orphan row was deleted. This is a Hat-B harness lesson: `write_revision` takes the literal path; `track_universe` writes `/workspace/operation/trading/{TICKER}.yaml`.

## Findings

### Finding 1 (Hat-A, set-up defect) — Signal 1 is structurally unfireable from the substrate

Signal 1's rule (`_operator_profile.md`): `20-day high + price > 50d SMA + RSI ∈ [55,75] + volume > 1.5× 20d avg`. The `track-universe` writer (`api/services/primitives/track_universe.py::_write_ticker_yaml`, schema locked by `test_trading_pipeline_architecture.py`) emits **only** `price, sma_20/50/200, rsi_14, atr_14, volume_20d_avg`. **There is no 20-day-high field and no current-bar-volume field — ever, pre-market or RTH.** So 2 of Signal 1's 4 conditions are *permanently* unverifiable. The signal's rule references data the mirror does not produce. This is a real bundle bug and a genuine contributor to "never trades." Fix: either the writer emits the missing fields, or Signal 1's rule is rewritten against fields that exist. Conformance CI (ADR-287) should catch "a signal rule names a field the snapshot schema doesn't emit."

### Finding 2 (axiomatic — the posture inversion) — the agent treats a *structural* gap as a *transient* one and waits, with High confidence

Run #3 isolates this cleanly (trustworthy snapshot, injection-tell removed). Facing "2 of 4 conditions unverifiable from my substrate," the agent:
- **Deferred to the next scheduled fire** ("the scheduled RTH refresh will populate everything required") — but the RTH fire writes the *identical schema*. The 20d-high field is not coming at 13:45 either. It mis-modeled a **permanent** structural defect as a **transient** timing gap.
- **Rated this "High confidence"** — confidently, articulately passive.
- **Chose rule-literalism over mandate-ownership.** Its own `principles.md` line 39 names this exact move an anti-pattern: *"'because the substrate that would tell me isn't populated' is not an answer — it is the gap the Reviewer addresses by authoring cadence + standing intent."* And ADR-344 case (B) is explicit: when "the loop has no organ that can originate what it owes," the move is to author/restore the organ **or surface the structural defect to the operator** — never serene waiting. The agent had the doctrine in front of it and applied the rule instead of the mandate.

This is the deep finding. **The passivity is real and is not merely a setup artifact** — even with a clean floor and a trusted breakout, the agent's instinct under "my instruments can't confirm" was *defer-to-schedule*, not *own-the-shortfall*.

**Verified this session — DP30 is present but inert.** DP30 (ADR-344, ratified 2026-06-18) already names this failure mode (its diagnostic test is almost verbatim the observed behavior) and is *fully present* on the trader: §Standing-Obligation in the live `principles.md` (line 117–126), the stance in the kernel frame (`reviewer_agent.py:363`), shipped in the bundle template. The occupant read it and still defaulted to rule-literalism. **Located mechanism**: the trader's case-(B) classifier (principles.md:126) enumerates structural-failure as *organ-missing* (signals retired / eval archived / universe emptied) — it does **not** include *organ-present-but-its-rule-is-unverifiable-from-substrate* (Signal 1 exists but 2/4 conditions reference fields the schema never emits). The occupant matched its situation against (B)'s examples, found none fit, and fell through to (A)/wait. The classifier applied a (B) definition whose cases are too narrow. This is the ADR-352 shape: a posture left to model preference is wrong until structurally forced. Full axiomatic treatment: `docs/analysis/agent-passivity-mandate-vs-rule-literalism-2026-06-22.md`.

### Finding 3 (Hat-A, evaluation completeness) — the per-signal scan is not exhaustive across the universe

Runs #4–#5: NVDA satisfied all three Signal-2 conditions and the agent had its values in context (it printed `NVDA 195.0 … RSI 22.0` in its own Signal-1 table). Yet under Signal 2 it evaluated **only MSFT** and declared "No candidates." It organizes the scan by-signal, anchors on the ticker with the salient raw value (MSFT's real RSI 18.55), and **does not test every ticker against every signal.** Reproducible across two identical runs. A ticker that fails Signal 1 is silently dropped from Signal 2 consideration. The `signal-evaluation` recurrence prompt says "for each ticker … apply each signal's rule" — the occupant is not executing that cartesian completeness.

## What was proven (vs the original "both, and I can't tell them apart")

| Possibility (operator's framing) | Verdict |
|---|---|
| Never executes the Primary Action | **Confirmed** — 0 proposals across 5 runs, including a fully-fireable Signal-2 state. |
| Always finds a reason to wait | **Confirmed** — and the reasons are now *named*: (a) structurally-unverifiable fields treated as transient (F2), (b) the candidate never scanned (F3). Neither is "conditions genuinely didn't warrant." |
| Strength surfaced | The **substrate-integrity moat works**: run #2 caught a constructed bar via its DAG/timestamp tell and refused to act on untrusted data (correct). The agent cannot be *fooled into* a trade; the problem is the opposite pole — it cannot be *moved to* one. |

The symmetry is broken: this is not correct-inaction. It is locatable passivity (F2) plus an evaluation-completeness bug (F3), sitting on top of a real substrate/rule mismatch (F1).

## Recommendations (fixes land Hat-A)

1. **F1** — reconcile Signal 1's rule with the snapshot schema (emit the fields, or rewrite the rule). Add conformance check: every signal-rule field ∈ snapshot schema.
2. **F3** — make `signal-evaluation` execute the full {ticker × signal} matrix; a Signal-1 disqualification must not remove a ticker from Signal-2 evaluation.
3. **F2** — the axiomatic one. Do **not** patch with a prompt nudge. See the discourse doc: the question is how the agent should weight *mandate / expected-output* against *rule-literalism* when its own perception apparatus is structurally insufficient — and why "wait for the schedule" is the wrong default when the gap is structural. Touches DP24 (stewardship), DP30 (standing obligation), ADR-345 (expected output).

## Reproduce

```
api/venv/bin/python api/scripts/alpha_ops/activate_persona.py --persona alpha-trader --clean-slate
api/venv/bin/python api/scripts/alpha_ops/manual_fire.py --persona alpha-trader --slug track-universe   # + track-regime
# drain (wake_drainer.drain_user_until_empty for the user)
# construct a trustworthy Signal-2 trigger via write_revision at /workspace/operation/trading/NVDA.yaml
api/venv/bin/python api/scripts/alpha_ops/manual_fire.py --persona alpha-trader --slug signal-evaluation
# drain → inspect execution_events + action_proposals + persona/standing_intent.md
```
