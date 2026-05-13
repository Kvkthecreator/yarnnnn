# Architecture Flows

The visual flow diagrams + machine-readable spec live in the web app at:

- **Cockpit UI**: `/admin/flows` (admin-gated route — five trigger/execution flows, specialist sub-loop, invariants & cross-cuts)
- **Source of truth**: [`web/lib/data/flows.json`](../../../web/lib/data/flows.json) — rich LLM-consumable spec (nodes, gates, cross-cuts, invariants, mermaid diagrams)

## When to update

This artifact is a snapshot, not canonical doc. Refresh when:

- A new dispatch trigger is added (currently 2: `addressed`, `reactive` per ADR-263 D2)
- The Reviewer's invocation contract changes (`invoke_reviewer` signature, primitive surface, trigger taxonomy)
- A new substrate write path is introduced that bypasses `write_revision` (would be an INV-2 violation)
- A new flow becomes load-bearing enough to deserve a panel (rare — current 5 cover the runtime)

To refresh: audit the file:line refs in `flows.json` against the current code, update the `snapshot` block at the top (`as_of`, `commit`, `note`), bump any changed mermaid diagrams, and re-verify every cited line.

For current canon, refer to:

- [`docs/architecture/SERVICE-MODEL.md`](../SERVICE-MODEL.md) — service-shape canon
- [`docs/architecture/FOUNDATIONS.md`](../FOUNDATIONS.md) — axiomatic model
- Named ADRs: 209, 256, 258 revised, 259, 260, 261, 262, 263
