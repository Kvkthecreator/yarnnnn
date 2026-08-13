# Archived development docs

Completed handoffs and phase-planning documents. Preserved for history;
**none of it describes current work or current setup.**

The live developer doc is [`../SETUP.md`](../SETUP.md).

## Criterion

A development doc belongs here when the work it scoped is **done, abandoned, or
superseded** — a handoff that was delivered, a phase plan whose decisions landed
in an ADR, a debt list that has been paid or re-scoped elsewhere.

A doc describing how to set up or operate the repo today stays in `../`.

## Contents (archived 2026-08-13)

| Doc | Why |
|-----|-----|
| `HANDOFF-projects-scope.md` | Handoff for "projects as a first-class concept" (ADR-119 Phase 2). Its companion design doc `design/PROJECTS-PRODUCT-DIRECTION.md` has since been deleted outright. |
| `PHASE-1-TECHNICAL-DEBT.md` | Phase-1 debt list from the ADR-072-era pipeline. |
| `PHASE-2-WORKFLOW-HARDENING.md` | Phase-2 planning against ADR-072 / ADR-056 / ADR-053, all superseded; its own header says "Decisions made — see ADR-073". |
| `deliverable-quality-testing.md` | Quality-testing notes in the retired `deliverable` vocabulary (renamed to `agent` by ADR-103). |

## Moving something here

**Re-path every inbound link in the same commit** — see the note in
[`../../testing/archive/README.md`](../../testing/archive/README.md) for why
this matters and the grep to run.
