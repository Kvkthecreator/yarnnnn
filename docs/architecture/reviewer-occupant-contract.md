# Reviewer Occupant Contract

> **Status**: Canonical
> **Date**: 2026-06-04 (published per ADR-315 D5)
> **Authors**: KVK, Claude
> **Scope**: The **published ABI** between the Reviewer seat (substrate, kernel-owned) and the Reviewer occupant (a swappable module). This is the named seam — the data contract every kernel/harness caller depends on, and every occupant implements.
> **Definition home**: `api/agents/occupant_contract.py` (the symbols) + `api/services/reviewer_envelope.py` (the kernel-side assembler) + `api/agents/reviewer_agent.py::invoke_reviewer` (the occupant-side entry).
> **Upstream**: [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) (the carve). [reviewer-seat-substrate.md](reviewer-seat-substrate.md) (the seat). [reviewer-occupant.md](reviewer-occupant.md) (the occupant).

---

## Purpose

[ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) carved the Reviewer occupant out of the seat. The seat stays substrate (no ABC — see [reviewer-seat-substrate.md](reviewer-seat-substrate.md)); the occupant becomes a contract-bounded module (see [reviewer-occupant.md](reviewer-occupant.md)). **This document publishes the contract between them.**

The contract is a **data contract over substrate** — TypedDicts that flow across one function boundary — not an OO abstraction over the seat. Its canonical home is `api/agents/occupant_contract.py`, which is **pure data**: it imports `typing` only, with no `anthropic` and no `services.*`. That standalone-importability is the standing, testable proof that the ABI is decoupled from the LLM runtime (ADR-315 D2).

---

## The three symbols

`api/agents/occupant_contract.py` is the single definition home for:

| Symbol | Kind | Meaning |
|---|---|---|
| `ReviewerContext` | `TypedDict` | The substrate → occupant **input** bag. Each trigger pre-loads what it has; the occupant fetches anything else via the `ReadFile` tool. |
| `ReviewerOutput` | `TypedDict` | The occupant → substrate **return** shape. One shape across all triggers; `verdict`/`reasoning`/`confidence` always present on success. |
| `REVIEWER_MODEL_IDENTITY` | `str` | The current AI occupant's identity string (today: `ai:reviewer-sonnet-v8`). Used in `authored_by="reviewer:{...}"` attribution per ADR-209 + ADR-288. |

`reviewer_agent.py` imports these three from the contract and **re-exports** them in its namespace, so existing `from agents.reviewer_agent import ReviewerContext` callers keep resolving (one definition, re-exported — not a dual definition). New code should import from `occupant_contract.py` directly.

---

## The full contract flow

```
load_reviewer_governance_envelope(client, user_id)  →  (envelope_dict, elapsed_ms)   [kernel side]
    envelope_dict keyed by ReviewerContext field names
        →  invoke_reviewer(trigger, context: ReviewerContext)  →  ReviewerOutput | None   [occupant side]
            →  reviewer_audit / dispatcher write back to substrate                         [kernel side]
```

### Kernel side — the envelope assembler

`api/services/reviewer_envelope.py::load_reviewer_governance_envelope(client, user_id) -> tuple[dict, int]`

Reads substrate (governance + domain paths) in parallel via `asyncio.gather` and returns:
- `envelope_dict` — keyed by `ReviewerContext` field names; drops directly into the context bag passed to `invoke_reviewer`.
- `elapsed_ms` — wall-clock ms, routed to `execution_events.envelope_load_ms` (reactive path) or the structured logger (addressed path) per ADR-276.

The kernel-universal envelope (`_UNIVERSAL_ENVELOPE_DECLS`, always present) is the set of governance + identity files every wake carries. Its growth is ADR-attributed (6 pre-ADR-284 → +occupant_md/standing_intent_md ADR-284 → +pace_yaml ADR-298 D11 → +schedule_index_md/recent_execution_md ADR-301). Per-trigger sub-shapes add `proposal_row` (proposal-arrival), `recurrence_prompt`+`recurrence_slug` (recurrence-fire), or `user_message` (addressed).

### Occupant side — the entry point

`api/agents/reviewer_agent.py::invoke_reviewer(trigger, context: ReviewerContext) -> ReviewerOutput | None`

- `trigger` ∈ `{addressed, reactive}` (ADR-256 unified entry; four-mode taxonomy collapsed to two by ADR-263 D2).
- `context` — the `ReviewerContext` bag. The first thing `invoke_reviewer` does is `_validate_context_shape`: a bag that satisfies no valid sub-shape fails loud (log error + return `None`), replacing the prior silent fallback where mismatched context names caused the Reviewer to wake with an empty user message and produce an inert `stand_down`.
- returns one `ReviewerOutput` (or `None` on shape violation).

### Kernel side — write-back

`reviewer_audit.py` + the dispatcher write the verdict back to substrate (`judgment_log.md`, `standing_intent.md`) with `authored_by="reviewer:{REVIEWER_MODEL_IDENTITY}"`.

---

## The dependency rule (ADR-315 D3)

> **The kernel/harness depends on the contract, never on the occupant implementation.**

The four kernel/harness call sites that previously imported these symbols from `agents.reviewer_agent` import them from `agents.occupant_contract`: `services/programs.py`, `routes/feed.py`, `services/wake.py`, `services/review_proposal_dispatch.py`. Only the harness (`wake.py` / `review_proposal_dispatch.py` / `feed.py`) imports the occupant's *behavior* (`invoke_reviewer`); everyone else imports only the *contract*. This closes the one reverse leak — the kernel no longer depends on the occupant's implementation file.

The standing regression proof: any CI gate that grep-asserts the contract symbols' definitions reads `occupant_contract.py`; usage-site assertions stay on `reviewer_agent.py` (ADR-315 D4).

---

## Why a published contract, not just an internal boundary

- **Portability without ABC.** The occupant is portable + separately documented without reversing ADR-194 v2's "no Reviewer ABC" retraction. The boundary is data (TypedDicts over substrate), not an OO abstraction over the seat.
- **The open-core seam is legible.** A future `external:<service>` occupant or an open-core split takes the form of a second consumer of this exact contract. Publishing it makes that seam stable and named in advance.
- **Decoupling is testable.** `occupant_contract.py` imports with no LLM runtime — a standing, machine-checkable proof that the ABI doesn't drag the occupant's dependencies into the kernel.

The literal package carve (`api/agents/reviewer/`) that would house an external occupant is deferred (ADR-315 D6) — the published contract already delivers portability + separate documentation; the package move changes only file layout, not the boundary, and earns its churn only when a second consumer exists.

---

## Relationship to other canons

- [reviewer-seat-substrate.md](reviewer-seat-substrate.md) — the seat (substrate) on the kernel side of this contract.
- [reviewer-occupant.md](reviewer-occupant.md) — the occupant (module) on the implementation side of this contract.
- [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) — the carve that produced this contract.
- [ADR-256](../adr/ADR-256-unified-reviewer-invocation.md) — the `invoke_reviewer` unified entry point.
- [ADR-276](../adr/ADR-276-reactive-trigger-envelope-governance-preload.md) — the envelope helper (`load_reviewer_governance_envelope`) that assembles the kernel side.
