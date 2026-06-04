# ADR-315: Reviewer Occupant Contract — Carving the Occupant from the Seat

**Status:** Accepted — L2 (code) Implemented 2026-06-04; L1 (docs) + import-suite validation carry-over; L3 deferred
**Date:** 2026-06-04
**Authors:** KVK, Claude
**Related:** [reviewer-occupant-carveout-2026-06-04.md](../analysis/reviewer-occupant-carveout-2026-06-04.md) (framing), [reviewer-substrate.md](../architecture/reviewer-substrate.md), [agent-composition.md](../architecture/agent-composition.md) §3.2.x
**Amends:** ADR-194 v2 (clarifies seat-vs-occupant — does NOT reverse the ABC-retraction), ADR-256 (`invoke_reviewer` boundary named as a contract), ADR-284/288/289/301 (regression gates retargeted, behavioral assertions preserved)
**Preserves:** FOUNDATIONS Axiom 1 §4 (substrate-as-bus), Axiom 2 (seat-occupant), Derived Principle 7 (singular implementation / anti-premature-modularity), Derived Principle 15 (seats persist, occupants rotate), Derived Principle 22 (persona-frame carries only the model↔runtime contract)

---

## Context

The 2026-06-04 architecture audit asked whether the persona-bearing judgment
seat could be made portable, modular, and separately documented. A code audit
found the carve is ~90% structurally already done (see the framing doc for
receipts): the substrate/kernel never imports the occupant; the occupant
consumes a substrate-assembled context bag through one function boundary
(`invoke_reviewer(trigger, context)`); the in/out contract (`ReviewerContext` /
`ReviewerOutput`) already exists, privately, inside the occupant module.

The live tension: ADR-194 v2 retracted v1's "Reviewer ABC" — *"the seat is
substrate, not a pluggable abstraction in code."* The resolution is the
seat≠occupant distinction: **the seat stays substrate; the occupant becomes a
contract-bounded module.** The boundary is a *data* contract over substrate
(TypedDicts), not an OO abstraction over the seat.

## Decision

### D1 — Seat stays substrate; occupant is carved (no ABC reversal)

The Reviewer **seat** remains exactly what ADR-194 v2 made it: `/workspace/review/*`
files + ADR-209 attribution + the wake/verdict contract. No abstraction, no
dependency injection, no ABC. The Reviewer **occupant** (the AI agent that fills
the seat — `reviewer_agent.py` + persona-frame) is the unit carved out. This
*completes* Derived Principle 15 (occupants rotate); it does not reverse ADR-194
v2.

### D2 — `occupant_contract.py` is the canonical home of the published ABI

`api/agents/occupant_contract.py` (NEW) is the single definition home for:
- `ReviewerContext` (TypedDict — the substrate→occupant input bag)
- `ReviewerOutput` (TypedDict — the occupant→substrate return)
- `REVIEWER_MODEL_IDENTITY` (the current AI occupant's identity string)

It is **pure data** — zero heavy imports (no `anthropic`, no `services.*`). It
imports standalone, which is the proof the ABI is decoupled from the LLM
runtime. `reviewer_agent.py` imports the three symbols from the contract and
re-exports them in its namespace (one definition, re-exported — NOT a dual
definition, so `from agents.reviewer_agent import ReviewerContext` keeps
resolving for existing callers/tests without churn).

### D3 — Kernel/harness depends on the contract, never on the occupant impl

The four call sites that previously imported these symbols from
`agents.reviewer_agent` now import from `agents.occupant_contract`:
`services/programs.py`, `routes/feed.py`, `services/wake.py`,
`services/review_proposal_dispatch.py`. This kills the one reverse leak: the
kernel depends on the contract; only the harness (`wake.py` /
`review_proposal_dispatch.py` / `feed.py`) imports the occupant's behavior
(`invoke_reviewer`).

### D4 — Four source-text gates retargeted; behavioral assertions preserved

The regression gates that source-grep `reviewer_agent.py` for the *definitions*
moved by D2 are retargeted to `occupant_contract.py`; their *usage-site*
assertions stay on `reviewer_agent.py`:

| Gate | Definition-site assertion → `occupant_contract.py` | Usage-site assertion stays on `reviewer_agent.py` |
|---|---|---|
| `test_f1_reviewer_telemetry_passthrough.py` | `class ReviewerOutput` AST ClassDef + six telemetry fields | `output: ReviewerOutput = {...}` dict literal + cancellation stand_down |
| `test_adr289_invocation_id_anchoring.py` | `class ReviewerOutput(...invocation_id)` regex | dict-literal `"invocation_id": invocation_id` stamp |
| `test_reviewer_context_contract.py` | `recurrence_prompt: str` / `recurrence_slug: str` present, `trigger_slug` absent | `_validate_context_shape` import (runtime) |
| `test_adr288_caller_identity.py` | `ground_truth_md: str` field present | `caller_identity=f"reviewer:{REVIEWER_MODEL_IDENTITY}"` injection; `performance_md` absent |

No behavioral assertion is weakened — only the file a definition is read from
changes. `performance_md`-absence is additionally asserted on
`occupant_contract.py` (the field moved with the class).

### D5 — Documentation split by domain (L1)

`reviewer-substrate.md` (269 lines) splits into two domain-scoped docs:

- **`reviewer-seat-substrate.md`** (Kernel domain) — the seven seat files,
  occupant-rotation protocol (`OCCUPANT.md` + `handoffs.md` + `rotate_occupant`),
  calibration trail, attribution, write-locks, the prospective-attribution
  contract with chat surfaces. This is *seat*, i.e. substrate.
- **`reviewer-occupant.md`** (Personification domain) — the AI Reviewer
  occupant: `reviewer_agent.py` structure, model selection by trigger, the
  persona-frame discipline (pointing at `agent-composition.md §3.2.x` as the
  singular partition canon, no content move), and how the occupant consumes the
  contract. Names today's occupant (`ai:reviewer-sonnet-v8`) as one of the
  occupant classes (`human` / `ai` / `external:<service>` / `impersonated`).

Plus a new short **`reviewer-occupant-contract.md`** publishing the ABI
(`ReviewerContext` / `ReviewerOutput` / `invoke_reviewer` / the
`reviewer_envelope` kernel-side assembler) as the named seam between the two.
`reviewer-substrate.md` becomes a one-screen index pointing at the three.
Cross-refs updated: CLAUDE.md "Reviewer seat" pointer block, `agent-composition.md`
§6 appendix, GLOSSARY "Reviewer / Reviewer seat / Occupant" entries,
`architecture/README.md` index.

> **L1 is carry-over** (mechanical doc work; specified completely here). It is
> deferred from the 2026-06-04 session only because the import-based reviewer
> suite (which validates L2) requires `anthropic` installed, so L2 validation +
> L1 doc-split land together on the next pass. No design ambiguity remains.

### D6 — L3 (package carve) deferred with an explicit trigger

Restructuring `api/agents/reviewer_*` into a self-contained `api/agents/reviewer/`
package (depending only on the published contract + `services.anthropic`) is the
literally-extractable unit — the form a future external `external:<service>`
occupant or open-core split would take. **Not built now.** Per Derived Principle
7, the package move earns its churn only when a second consumer exists. L2's
published contract already delivers portability + separate documentation; L3
changes only the file *layout*, not the boundary. **Trigger:** productizing an
external judgment occupant, or a ratified open-core decision.

## Consequences

### Positive
- The occupant is portable + separately documented without reversing ADR-194 v2.
- The substrate-bus ABI from the 2026-06-04 audit is now a named, importable
  surface (`occupant_contract.py`) — the open-core seam is legible and stable.
- `occupant_contract.py` imports with no LLM runtime, which is a standing,
  testable proof that the ABI is decoupled.
- Kernel no longer imports the occupant implementation (one reverse leak closed).

### Costs / risks
- Four regression gates retargeted — a real (bounded, documented) surface on the
  most-read LLM-facing module. Mitigated: behavioral assertions preserved; only
  the read-from file changes.
- Re-export in `reviewer_agent.py` is a deliberate, minimal compatibility
  affordance (one definition, re-exported) — NOT a dual implementation. If a
  future cleanup wants all callers/tests to import from `occupant_contract`
  directly, that is a follow-on sweep, not required by this ADR.

## Implementation status (2026-06-04)

**Landed (L2 — validated by `py_compile` + standalone-import of
`occupant_contract.py` + the four retargeted source-text gates):**
- `api/agents/occupant_contract.py` (new)
- `api/agents/reviewer_agent.py` (3 defs → imports from contract, re-exported)
- `api/services/programs.py`, `api/routes/feed.py`, `api/services/wake.py`,
  `api/services/review_proposal_dispatch.py` (import source → contract)
- `api/test_f1_reviewer_telemetry_passthrough.py`,
  `api/test_adr289_invocation_id_anchoring.py`,
  `api/test_reviewer_context_contract.py`,
  `api/test_adr288_caller_identity.py` (gate retargeting)

**Carry-over (needs `anthropic` installed / a full test env):**
- L1 doc split (D5) — mechanical, fully specified above.
- Run the import-based reviewer suite to confirm runtime parity:
  `test_adr274 / 275 / 276 / 301 / reviewer_context_contract (runtime part) /
  envelope_observability / reviewer_formalization / adr284 / adr247`.
- Cross-ref sweeps (CLAUDE.md, GLOSSARY, agent-composition §6, README index).
- `api/prompts/CHANGELOG.md` entry IF any persona-frame content changed (it did
  not in L2 — pure symbol relocation; add the entry only with the L1/D5 pass if
  doc pointers in prompt-adjacent files move).

## Test plan
1. `python3 -c "import ast; ast.parse(open('api/agents/occupant_contract.py').read())"` — parses.
2. From `api/`: `python3 -c "import agents.occupant_contract as c; print(c.REVIEWER_MODEL_IDENTITY, c.ReviewerContext.__annotations__ and 'OK')"` — standalone import, no `anthropic`.
3. `python3 -m pytest api/test_f1_reviewer_telemetry_passthrough.py api/test_adr289_invocation_id_anchoring.py api/test_reviewer_context_contract.py::test_reviewer_context_typeddict_canonical_keys api/test_adr288_caller_identity.py::test_envelope_key_renamed_to_ground_truth_md -q` (source-text gates — runnable without `anthropic`).
4. `python3 -m py_compile` on all six touched modules.
5. **Carry-over:** full import-based reviewer suite in an env with `anthropic`.
