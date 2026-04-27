# Reference Workspace — alpha-prediction (sketch)

> Per ADR-223 §6 lifecycle states + §5 reference-workspace conventions: reference programs (status: reference) may ship a minimal reference-workspace/ — the SPEC's value is the litmus test, not the operator-ready scaffolding.
>
> This folder will populate when activation preconditions land (see [MANIFEST.yaml](../MANIFEST.yaml) `activation_preconditions`).

## Why this is empty

alpha-prediction is a **reference SPEC** — it exists to constrain kernel-layer decisions, not to ship as a built program. The kernel must support terminal_binary oracles, time-to-resolution as a first-class field, and Kelly sizing primitives — but those primitives are exercised by reading the SPEC, not by activating a workspace.

When activation_preconditions land and this graduates to `status: active`, this folder will populate with operator-template files mirroring the alpha-trader bundle's structure (`context/_shared/MANDATE.md` + `IDENTITY.md` + `BRAND.md` + `CONVENTIONS.md` + `AUTONOMY.md`, `review/IDENTITY.md` + `principles.md`, `memory/awareness.md`).
