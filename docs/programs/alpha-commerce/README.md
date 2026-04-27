# alpha-commerce (Reference)

> Reference program SPEC under the agent-native operating system framing canonized by [ADR-222](../../adr/ADR-222-agent-native-operating-system-framing.md), bundle layout per [ADR-223](../../adr/ADR-223-program-bundle-specification.md), homed by the boundary refactor in [ADR-224](../../adr/ADR-224-kernel-program-boundary-refactor.md). Currently `status: deferred` — captures commerce-shaped artifacts that have shipped in code (per [ADR-183](../../adr/ADR-183-commerce-substrate.md) + [ADR-184](../../adr/ADR-184-product-health-metrics.md)) but didn't have a bundle home until now.
>
> Machine-readable contract: [MANIFEST.yaml](MANIFEST.yaml). Sketch composition manifest: [SURFACES.yaml](SURFACES.yaml). Bundled starter substrate (sketch only until activation): [reference-workspace/](reference-workspace/).

## Why this bundle exists in `deferred` status

Per ADR-184, commerce was scoped as a fourth platform class with two context domains (`customers/` + `revenue/`), four task types (`commerce-digest`, `revenue-report`, `commerce-execute`, ...), and a Commerce Bot capability. None of these had a program-layer architectural home — they lived as residue in the kernel registries (`task_types.py`, `directory_registry.py`, `orchestration.py CAPABILITIES`).

ADR-224's boundary refactor deletes the residue from kernel and creates this bundle as the canonical home. `status: deferred` because:

1. **No operator is running alpha-commerce as a primary program.** The kvk operator runs alpha-trader; alpha-commerce is conceptually a future second program.
2. **Activation requires a real operator.** Per ADR-223 §6, deferred → active is governed by activation_preconditions, which include "a real operator willing to author honest principles + supervise the workspace."
3. **Templates are surfaced to YARNNN composition only when active.** Per ADR-224 §3, deferred bundles' templates are not surfaced to composition reasoning — `bundle_reader.all_active_bundles()` filters by `status='active'`.

## Triangle position

| Property | alpha-commerce |
|---|---|
| Oracle source | Commerce platform (Lemon Squeezy / Stripe) settled events |
| Oracle shape | Continuous (revenue, MRR, churn rates) |
| Latency | Realtime webhooks → daily settles |
| Action irreversibility | Capped (refunds reversible within window) |
| Custody | Platform-held |
| Capital threshold | $100+ revenue (any commerce operator with one paying customer) |
| Knowledge edge | Product/marketing fit, customer segments, pricing |

Distinct enough from alpha-trader (continuous price + brokerage held + intraday) and the reference triangle (alpha-prediction + alpha-defi) to constrain OS decisions independently. When activated, would join the reference set — though current registry-of-three may stand if alpha-commerce remains primarily residue-housing.

## What activates this bundle

Per ADR-223 §6 lifecycle states + ADR-224 §3 active-program semantics:

- **Today (deferred):** templates are *not* surfaced to YARNNN composition. The bundle's contract is preserved; its content informs OS-layer decisions about commerce-shaped patterns.
- **When activated:** `MANIFEST.yaml` `status` flips to `active`. `bundle_reader.all_active_bundles()` includes it. YARNNN composing in chat finds `revenue-report` and `commerce-digest` as available templates. Operator scaffolding `customers/` and `revenue/` directories at first-write reads metadata from this bundle.

## What this bundle does NOT yet ship

- **No reference-workspace operator templates.** `reference-workspace/` ships near-empty per ADR-223 §5 reference-workspace discipline. Real population (operator-template MANDATE, principles.md, full SURFACES.yaml) lands when alpha-commerce graduates from `deferred` to `active`.
- **No commerce-specific Reviewer principles.** When activated, would ship a commerce-shaped Reviewer persona (e.g., conservative-churn-investor, growth-marketer) and principles (e.g., never offer >50% discount without explicit operator approval).
- **No phase milestones.** `phases: []` until the program has a real operator path to validate against.
