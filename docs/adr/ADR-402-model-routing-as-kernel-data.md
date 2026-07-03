# ADR-402: Model Routing as Kernel Data — the single model-selection site

**Status**: Implemented (2026-07-03) — Part A (table) + Part B (tier decision: one model, `claude-sonnet-4-6`, all shapes)
**Date**: 2026-07-03
**Dimension**: Mechanism (primary, Axiom 5) + Identity (occupant attribution, Axiom 2)
**Supersedes**: the ADR-260 D2/D8 + ADR-263 D2 inline model/round selection in `agents/freddie_agent.py`
**Relates to**: ADR-315 (occupant contract — the provider seam), ADR-380 (name-the-seam discipline), ADR-382/383 (persona agents — the deferred per-agent override), ADR-396 (metering basis), ADR-403 (the envelope the tiers are measured on)

---

## 1. Context

Rung 4 — deliberately last, per the operator's directive: posture first, model
question last — of the Freddie envelope/agent optimization program (Rungs 0–3:
ADR-383 trigger-framing re-carve, ADR-397 liturgy→reactive, ADR-398 chat
legibility, ADR-399 turn artifact, ADR-403 envelope collapse).

Before this ADR, model selection for the Freddie occupant lived as two
hardcoded constants + an inline branch in `agents/freddie_agent.py`:

```python
_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-5-20251001"
...
use_sonnet = (trigger == "reactive") and not is_recurrence_fire
model = _SONNET if use_sonnet else _HAIKU
...
max_rounds = 3 if use_sonnet else 20
```

Three problems:

1. **The routing is an accident of history, not a decision.** Proposal wakes
   (the shape with the *least* open-ended judgment — a discrete verdict call)
   get the stronger model with a 3-round behavioral cap; the operator-facing
   chat (addressed) and the read-heavy recurrence loop run Haiku. The split
   predates the ADR-403 thin envelope; nothing re-examined it. Known Haiku
   signatures on the chat shape: stochastic silent exits (~1/12), count fuzz
   in reports, standing-cadence-from-test-asks judgment lapses.
2. **Policy is buried in code.** Changing which model serves which shape — or
   running a tier experiment — required editing the occupant's loop.
3. **Dead residue**: the `_CALLER_SONNET`/`_CALLER_HAIKU` pair was assigned
   and never consumed (attribution flows through `caller_identity`, ADR-288
   D1) — a fossil of the deleted `token_usage` ledger.

### The strategic frame (operator-settled, 2026-07-03)

The operator's question: should model *choice* even be Freddie's concern, or
should Freddie stabilize on one reliable model with model selection deferred
downstream (per-persona-agent)? Resolution — the dichotomy is real at the
**policy** level, false at the **mechanism** level:

- **Mechanism now**: the table is where the model id *lives* — even a
  maximally-stabilized Freddie has one. A table whose rows all point at the
  same model IS the stabilized Freddie. Mechanism and policy are separable.
- **Policy: stabilization prior** (§5). Freddie is a system agent; the default
  outcome is ONE model for all shapes, chosen by evidence.
- **Downstream**: per-agent model choice is a product surface for persona
  agents (ADR-382/383), not for the steward. Named as a seam (§6), not built —
  ADR-380 discipline.

## 2. Decision — Part A (the mechanism, a pure refactor)

**D1 — One routing table.** `api/services/model_routing.py` declares
`DEFAULT_ROUTES: {shape: ModelRoute(model, max_rounds)}` over three trigger
shapes — `addressed` | `proposal` | `recurrence` — exactly the sub-shapes
`invoke_freddie` already differentiates. `resolve_route(trigger,
is_recurrence_fire)` is the only entry point; `classify_shape` mirrors the
legacy branch byte-for-byte (including the else-branch for unknown triggers).
Part-A table values are byte-identical to the pre-table branch:

| shape | model | max_rounds |
|---|---|---|
| addressed | claude-haiku-4-5-20251001 | 20 |
| proposal | claude-sonnet-4-6 | 3 |
| recurrence | claude-haiku-4-5-20251001 | 20 |

**D2 — Env-overridable per deployment, read at resolve time.**
`YARNNN_MODEL_{SHAPE}` / `YARNNN_ROUNDS_{SHAPE}`. This is what makes Part B
cheap: the tier probes flip env vars against the same code. Malformed values
fall back to the table with a logged warning.

**D3 — Provider-optionality boundary (held, not built).** Model ids live ONLY
in the table; Anthropic client usage stays inside the occupant module
(`freddie_agent.py`); nothing outside the occupant branches on model. The
ADR-315 occupant contract (`agents/occupant_contract.py`, pure data) remains
the seam a future non-Anthropic occupant implements. Deliberately a TABLE,
not a provider abstraction.

**D4 — `max_rounds` is a cost ceiling, not a behavioral constraint**
(trust-the-model, Claude Code-aligned). The 3-round proposal value contradicts
that philosophy — it is carried into the table as-is for byte-identity and
re-examined by Part B.

**D5 — Identity ≠ model.** `FREDDIE_MODEL_IDENTITY` (`ai:freddie-sonnet-v8`)
names the occupant VERSION (seat-rotation protocol, ADR-315), not the model
tier; the model actually used on an invocation is recorded honestly in
`execution_events.model` (ADR-291). It is NOT derived per-wake from the table
— one identity, one ledger, no attribution fragmentation. The "sonnet" in the
current value was a naming fossil while Haiku served most wakes; the Part-B
outcome (Sonnet everywhere) makes it accurate again, so the model-neutral v9
rename is deferred as cosmetic (see Part B results).

**Deleted**: `_SONNET`, `_HAIKU`, `use_sonnet`, and the dead
`_CALLER_SONNET`/`_CALLER_HAIKU` pair. The two Hat-B probe scripts that
imported the private constants now read `DEFAULT_ROUTES`.

**Gate**: `api/test_adr402_model_routing.py` (9 tests) — no raw model ids in
`freddie_agent.py`/`occupant_contract.py`, occupant consumes the table,
classification byte-identity, env-override semantics, and a Part-A anchor
pinning the routing values (updated in the same commit as any ratified
routing change).

## 3. Part B — the tier experiment (evidence → routing decision)

Protocol (Hat-B, `probe_freddie_addressed_baseline.py` — 6 byte-stable asks,
bare-kernel workspace, local code):

1. **Haiku baseline** on the Part-A code (also the Part-A e2e validation).
2. **Addressed on Sonnet** (`YARNNN_MODEL_ADDRESSED=claude-sonnet-4-6`), same
   asks — diff wall/tools/close-rate/response quality; watch for the Haiku
   signatures disappearing (silent exits, count fuzz, cadence lapses).
3. **Proposal-shape assessment**: structural, not empirical — the lane has
   zero live fires ever (see Part B results), so the inversion hypothesis
   (proposals fine on the cheaper tier) is untestable on real traffic and
   the shape follows the stabilization default. The recurrence shape is
   validated on the ratified model via the bare-steward live wake instead.

### The decision rule — stabilization prior

The default outcome is **one model for all three shapes**. A split survives
only on objective evidence:

- **(a)** the cheaper model is *indistinguishable* on a shape (split = free
  money — keep it), or
- **(b)** the stronger model is *necessary* on a shape and too expensive to
  run everywhere.

Absent either, collapse to the winner. Cost delta is surfaced against the
ADR-396 metering basis (model choice changes cost-per-judgment-invocation:
addressed Haiku→Sonnet ≈ 3× the per-call meter; a Starter allowance buys
roughly ⅓ the calls).

### Part B results (2026-07-03)

Both arms: the 6 byte-stable asks, bare-kernel workspace, local code on the
Part-A table, identical envelope. Receipts:
`docs/evaluations/2026-07-03-rung4-partA-haiku/` (+`-recheck5`) and
`docs/evaluations/2026-07-03-rung4-partB-sonnet-addressed/`.

| metric | Haiku 4.5 (baseline) | Sonnet 4.6 (`YARNNN_MODEL_ADDRESSED`) |
|---|---|---|
| closed | 5/6 + 1 recheck (stochastic silent exit, turn 5 — the known ~1/12 signature) | **6/6 first pass, 0 errors** |
| mean wall | ~32.6s | 34.8s |
| mean rounds / tools | 6.2 / 10.2 | **3.3 / 4.2** |
| attribution-mismatch catch (seeded) | **MISSED** — turn 4 reported "well-attributed" (a false claim); turn 3 silent on it | **CAUGHT** in turns 3 AND 4, with the correct rule verdict (flag, don't re-attribute another principal's write) |
| proposal dedup | re-proposed placements already pending | recognized the pending queue, declined to duplicate |
| observed cost/turn | $0.050 (understated: silent-exit tokens unrecorded + recheck) | $0.071 — **1.4×, not the 3× sticker** (half the rounds) |

The decision rule resolves cleanly:

- **(a) cheaper-indistinguishable — FALSE.** Haiku is distinguishably worse
  on the steward duties themselves: it missed the seeded attribution
  mismatch and reported a falsely-clean workspace (exactly the bare-Freddie
  eval Finding-1 class), re-proposed duplicate work, and carries the
  stochastic silent exit.
- **(b) stronger-necessary-but-unaffordable — FALSE.** Sonnet's efficiency
  (half the rounds) absorbs most of the tier premium: 1.4× observed.

**Ratified routing: `claude-sonnet-4-6` for all three shapes, uniform
`max_rounds=20` cost ceiling.** The legacy Sonnet/3 proposal split retires —
`wake_source='proposal_arrival'` has zero rows ever (the lane has never
fired live), so no evidence supports any split there; the 3-round cap was a
behavioral constraint contradicting D4 (the ADR-403 verdict-early ask rule
is the proposal behavior control).

**Cost delta vs the ADR-396 metering basis**: the per-judgment-invocation
meter moves from ~$0.05 to ~$0.07 observed on addressed turns (worst case
~3× on equal-round wakes; observed 1.4× because rounds halve). A Starter
$15 allowance buys roughly 210 wakes instead of ~300 at observed rates.

**Sample-size honesty**: one 6-ask run per arm. The Haiku failure evidence is
cumulative (the silent-exit signature reproduces across many prior runs; the
attribution miss is against seeded substrate, near-deterministic); the Sonnet
6/6 does not prove a zero silent-exit rate — the routing stays a data change
if live telemetry contradicts it.

**Identity**: `FREDDIE_MODEL_IDENTITY = "ai:freddie-sonnet-v8"` is now
*accurate again* (every wake runs Sonnet), so the model-neutral v9 rename is
DEFERRED as cosmetic — 17 files pin the string; `execution_events.model` is
the honest per-wake record either way (D5).

**Future candidate**: `claude-sonnet-5` (same $3/$15 sticker, $2/$10 intro
through 2026-08-31) is a data-change candidate but NOT a drop-in: adaptive
thinking on by default (the occupant loop would need thinking-block echo
handling), non-default sampling params rejected (the call path is clean —
verified), and a ~30% tokenizer shift. Its own probe run before any switch.

## 4. The deferred seam — per-agent model declaration

When persona agents ship (ADR-382), model choice becomes a per-seat property
(a trader seat may warrant a stronger tier than a digest seat). The resolution
order is declared now, built later:

1. per-agent declaration (the agent's governance sidecar, ADR-383
   agent-universal file structure) — future;
2. kernel routing table default (this ADR);
3. deployment env override.

Same pattern the codebase already ratified once: `CALLER_WRITE_POLICY`
class-defaults refined by per-principal `principal_grants` (ADR-373). The
kernel table is the class default; the seat declaration is the override.

## 5. What this ADR does NOT do

- No provider abstraction (the occupant contract is the seam; a table is not
  an abstraction layer).
- No repo-wide model-id sweep: other LLM call sites (dispatch_specialist,
  harvest, memory, telemetry, web_search, …) have their own model choices —
  out of the occupant seam's scope. Candidate follow-on if the table proves
  itself.
- No per-agent model declaration (§4 — named, deferred).
- No change to `FREDDIE_MODEL_IDENTITY` in Part A (§2 D5).
