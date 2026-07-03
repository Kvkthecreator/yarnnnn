# ADR-402: Model Routing as Kernel Data — the single model-selection site

**Status**: Part A Implemented (2026-07-03) · Part B (tier experiment → routing decision) pending
**Date**: 2026-07-03
**Dimension**: Mechanism (primary, Axiom 5) + Identity (occupant attribution, Axiom 2)
**Supersedes**: the ADR-260 D2/D8 + ADR-263 D2 inline model/round selection in `agents/freddie_agent.py`
**Relates to**: ADR-315 (occupant contract — the provider seam), ADR-380 (name-the-seam discipline), ADR-382/383 (persona agents — the deferred per-agent override), ADR-396 (metering basis), ADR-400 (the envelope the tiers are measured on)

---

## 1. Context

Rung 4 — deliberately last, per the operator's directive: posture first, model
question last — of the Freddie envelope/agent optimization program (Rungs 0–3:
ADR-383 trigger-framing re-carve, ADR-397 liturgy→reactive, ADR-398 chat
legibility, ADR-399 turn artifact, ADR-400 envelope collapse).

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
   predates the ADR-400 thin envelope; nothing re-examined it. Known Haiku
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
current value is a naming fossil: the v9 bump to a model-neutral name lands
with the Part-B routing decision (a behavior change), not with Part A (byte
-identical).

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
3. **Inversion check**: proposal shape on Haiku (the discrete verdict call may
   be the shape that *least* needs the stronger tier) via the bare-steward
   reactive probe.

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

### Part B results

*(recorded when the runs land — routing decision + diff receipts +
`execution_events` cost deltas + the v9 identity bump if routing changes)*

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
