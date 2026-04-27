# Reference Workspace — alpha-commerce (sketch)

> Per ADR-223 §6 lifecycle states + §5 reference-workspace conventions: deferred bundles ship a near-empty reference-workspace/ — the bundle's value is the SPEC + the architectural home it provides for residue, not the operator-ready scaffolding.
>
> This folder will populate when activation_preconditions land (see [MANIFEST.yaml](../MANIFEST.yaml)).

## Why this is empty

alpha-commerce is `status: deferred`. No operator is running it as a primary program; the bundle exists to give commerce-shaped artifacts (commerce_bot, customers/revenue domains, revenue-report task) an architectural home post-ADR-224. When a real commerce operator drives the program forward, this folder populates with operator templates mirroring the alpha-trader bundle's structure.
