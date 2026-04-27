# Reference Workspace — alpha-defi (sketch)

> Per ADR-223 §6 lifecycle states + §5 reference-workspace conventions: reference programs (status: reference) may ship a minimal reference-workspace/ — the SPEC's value is the litmus test, not the operator-ready scaffolding.
>
> This folder will populate when activation preconditions land (see [MANIFEST.yaml](../MANIFEST.yaml) `activation_preconditions`) — and notably, several preconditions block on custody/idempotency/24x7-scheduling primitives that are themselves OS-layer work the SPEC is designed to constrain.

## Why this is empty

alpha-defi is the **heaviest litmus** in the reference triangle and explicitly the hardest of the three to activate. Activation depends on OS-layer custody primitives, idempotency at the action envelope, block-keyed substrate replay, and a 24/7 scheduling model — each of which the SPEC pressures the kernel into supporting cleanly *before* this folder usefully populates.

When the OS primitives ship and activation_preconditions are met, this folder will populate with operator-template files mirroring the alpha-trader bundle's structure (`context/_shared/MANDATE.md` + `IDENTITY.md` + `BRAND.md` + `CONVENTIONS.md` + `AUTONOMY.md` adapted for irreversibility, `review/IDENTITY.md` + `principles.md` adapted for MEV/slippage/depeg risk, `memory/awareness.md`).
