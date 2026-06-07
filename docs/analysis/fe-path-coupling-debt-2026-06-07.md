# FE Path-Coupling — Named Debt (post-ADR-320)

> **Status**: Analysis / named debt. NOT an ADR, NOT a fix. Captured so the finding survives; the fix is deliberately deferred (YAGNI until a second trigger).
> **Date**: 2026-06-07
> **Origin**: regroup after the ADR-320 five-root migration. The operator asked whether the FE scaffolding is "too hard-fixed."

## The finding

The ADR-320 root migration touched ~45 frontend files. Most were unavoidable (you cannot rename a root without touching things that name it). But the *count* exposed a structural fact: **the frontend re-declares workspace paths the backend already owns.**

There are **two distinct FE relationships to paths**, and they behaved very differently under the migration:

1. **Path-as-identity** (the FE needs to know "the mandate lives at `constitution/MANDATE.md`" to fetch/render it). Re-declared as **string literals** across ~45 sites: `web/lib/content-shapes/*.ts` write-path constants, route pages (`mandate/`, `identity/`, `autonomy/`, `principles/`, `pace/`), components, and a hardcoded path-map in `web/components/settings/WorkspaceSection.tsx`. **This is the hard-fixed layer.** The backend has a single source (`api/services/workspace_paths.py`); the FE has no shared equivalent, so it re-declares — and a root change means N hand-edits.

2. **Path-as-compose-binding** (the compositor reads `SURFACES.yaml` bindings against substrate to render Home — ADR-225 / ADR-312). **This layer is already dynamic by design.** Home renders `program_sections` declaratively; it does not hardcode trader paths. It absorbed the migration gracefully — the cockpit needed near-zero edits; the *content-shapes + route pages* (layer 1) took the 45 edits.

So the operator's intuition was correct and precise: **part of the FE is correctly dynamic (compositor), part is hard-fixed (path literals)** — and the 45-edit cost came entirely from the hard-fixed part.

## The candidate fix (deferred)

A **shared path-manifest**: generate the FE's path constants from `api/services/workspace_paths.py` (a build-time codegen step, or a single `/api/workspace/paths` endpoint the FE consumes). Then the *next* root change is one edit (`workspace_paths.py`) + a regenerate, not 45 hand-edits. This would make path-as-identity as dynamic as path-as-compose-binding already is.

## Why deferred (the discipline call)

- The literals are now **correct** (post-migration). The debt is *latent cost-of-next-change*, not a current bug.
- Building a codegen/manifest layer to make a *hypothetical future* root change cheaper is speculative. Same logic as ADR-315's L3 package-carve deferral: **the abstraction earns its churn only when a second consumer/trigger exists.**
- **Trigger to revisit**: a *second* workspace-root change appearing on the roadmap (or a third surface — e.g. a mobile client — also needing to resolve these paths). At that point the manifest pays for itself; until then, YAGNI.

## What is explicitly NOT the debt

- The compositor (`web/lib/compositor/`, `web/components/library/`) — already dynamic, correctly absorbed the change. Do not "fix" it.
- The backend — `workspace_paths.py` is already the single source; it worked exactly as intended (one file changed, ~50 backend consumers followed via constant imports; only literals/prompts needed hand work).

## Cross-reference

The runtime-writer audit (`docs/analysis/SESSION-PROMPT-adr320-runtime-writer-audit.md`) covers the *backend* writer surface. This note covers the *frontend reader/writer* path-coupling. They are complementary; neither subsumes the other.
