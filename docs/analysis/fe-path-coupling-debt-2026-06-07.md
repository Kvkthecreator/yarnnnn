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

---

## Audit update (2026-06-07, same day) — the trigger condition is closer than "hypothetical"

A follow-on audit (commit `18af8aa`) re-walked the path-as-identity layer with receipts. Two findings change the deferral calculus from "speculative future" to "scheduled second wave."

### Finding 1 — the ADR-320 migration was incomplete; six globs were missed

Six content-shape `PATH_GLOB`s (`mandate / identity / brand / autonomy / pace / inference-meta`) still pointed at the dead `_shared/` root after the migration "completed." Their docstrings already named the correct five-root path — only the glob *value* was stale (mandate.ts said `constitution/MANDATE.md` in its header while its glob said `_shared/`). Fixed in `18af8aa`. **Implication:** the 45-edit migration silently under-covered the literal layer. A manifest would have made under-coverage structurally impossible (one source, regenerate-or-fail) — the literals can't drift out of sync with the source if they *are* the source.

These globs are also **latent, not live**: `shapeForPath` (the only `PATH_GLOB` consumer) has zero live callers; the live registry keys on `shapeKey`. So the miss was invisible to the type-checker and to runtime — pure documentary drift embedded in code. That's the *worst* kind for a manifest to prevent, because nothing catches it.

### Finding 2 — a second root change is already on the books (Family 2)

The literal layer is split:

- **Family 1 — governance literals** (`constitution/ persona/ operation/ governance/`): backend-migrated, FE now aligned (`18af8aa`). Stable.
- **Family 2 — accumulation/domain literals** (`context/{domain}/`): `money-truth.ts` glob + the whole `recurrence-shapes.ts` domain map still name `context/`. They are **correctly** aligned to the *still-un-migrated* backend (`conventions.py:160` emits `/workspace/context/{domain}`; `directory_registry` + `workspace.py scope=context` + `assembly.py` likewise — recorded in MEMORY.md "ADR-320 Writer Audit — accumulation path-layer NOT migrated").

So the third hand-edit of this exact literal layer is **already scheduled**: when the backend accumulation-path migration re-roots `context/{domain}/ → operation/{domain}/`, the FE Family-2 literals must move with it. That is the **second root-change trigger** this note named as the YAGNI threshold — no longer hypothetical, it's on the roadmap as a known-deferred backend migration.

### The sharpened call

The manifest has now *earned* its churn — two distinct evidences (a silent under-coverage that types couldn't catch + a scheduled second wave). But the **cleanest landing moment is the Family-2/backend-accumulation migration, not now**, because:

1. Building it now, against only Family-1 (already-stable) literals, repeats the speculative-abstraction anti-pattern — you'd build the manifold before the second consumer arrives, just by a few weeks.
2. Building it *as part of* the accumulation migration means FE + backend re-root through **one** source in the same change — the manifest proves itself by absorbing a real root change instead of a hypothetical one. (Same discipline ADR-320 itself followed: doc-first, but code-validated.)
3. The natural shape is now legible from the audit: the FE consumes paths as `api.workspace.getFile('<literal>')` with the literal duplicated across content-shapes + components + route pages + a hardcoded map in `WorkspaceSection.tsx`. A `/api/workspace/paths` endpoint (or build-time codegen from `workspace_paths.py`) collapses all of those to one resolver. The endpoint shape is the lighter lift — `workspace.py` already imports `workspace_paths` constants at three sites; exposing them as a JSON map is ~20 lines.

**Recommendation:** keep the manifest deferred, but **bind its trigger explicitly to the backend accumulation-path migration** (not "some future root change"). When that migration is scoped, the FE path-manifest becomes a sub-deliverable of it — they re-root together, one source, and the manifest is validated by a real change rather than authored on spec. Until then: Family-1 is fixed and stable; Family-2 is intentionally left aligned to the un-migrated backend; the debt is named, scoped, and trigger-bound.
