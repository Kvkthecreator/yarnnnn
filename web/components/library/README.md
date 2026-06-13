# System Component Library — ADR-225 §3 + ADR-273 D1

Universal components composition manifests reference. Per ADR-222 Principle 16: **system component library is additive-only**. Components shipped here serve programs (programs declare what they need); the library grows via demand-pull, not speculation.

## Folder convention (ADR-273 D1)

The library is one universal registry (`LIBRARY_COMPONENTS` in `registry.tsx`), but the filesystem split makes the kernel-vs-program boundary legible:

```
web/components/library/
├── CockpitHeader.tsx              kernel-general (always renders, Layer 1)
├── CockpitRenderer.tsx            kernel-general (dispatch)
├── CockpitContext.tsx             kernel-general
├── MiddleResolver.tsx             kernel-general
├── ChromeRenderer.tsx             kernel-general
├── BundleBanner.tsx               kernel-general
├── WorkDetailActionsContext.tsx   kernel-general
├── kernel-chrome/                 kernel-general (chrome registry)
├── registry.tsx                   imports from ./ and ./programs/*
└── programs/
    └── alpha-trader/              program-specific (alpha-trader)
        ├── TraderRegime.tsx
        ├── TraderPortfolio.tsx
        ├── TraderMoneyTruth.tsx
        ├── TraderExpectancy.tsx
        ├── TraderPositions.tsx
        ├── TraderSignals.tsx
        └── TraderOrders.tsx
```

**Kernel-general components** at the library root render for every workspace regardless of active program. **Program-specific components** at `programs/{slug}/` render only when their SURFACES.yaml declares them in `home.program_sections[]` (the composition key renamed `cockpit`→`home` per ADR-312 D2). Future programs (alpha-commerce, alpha-defi) each get their own `programs/{slug}/` subdirectory, mirroring `docs/programs/{slug}/` on the backend.

## Discipline

- **Each component is a TSX file with the same name as the SURFACES.yaml `kind` field.** `kind: TraderPortfolio` → `programs/alpha-trader/TraderPortfolio.tsx`.
- **Components accept a `binding` prop** matching one of the 6 binding-type taxonomy shapes (`file | frontmatter | task_output | action_proposals | narrative | directory` per ADR-225 §2). They fetch+render via existing hooks (`useTaskOutputs`, `useWorkspaceFile`, etc.) — or call dedicated program-data API routes (`/api/programs/alpha-trader/{regime,signals,indicators,money-truth,positions,portfolio-history,recent-orders}` per ADR-312 D9; pace is the kernel `/api/pace`).
- **Components are PURE READERS in both compose modes.** Surface compose: live binding, re-rendered per load. Document compose: frozen snapshot at compose time. Same render, different data freshness. **Components do not mutate.** Operator interactions that mutate (approve, reject, edit) flow through existing primitive surfaces.
- **Components are additive-only.** Removing a component is breaking and requires a deprecation cycle with ADR ratification.
- **No new component shipped without a bundle (or kernel-default middle) that uses it.** The library grows because programs demand it, not on speculation.
- **Program-specific components register in the universal `LIBRARY_COMPONENTS` dict** alongside kernel components — the registry is one flat namespace keyed by `kind`. Folder location is filesystem signal for human readers and future contributors; it does not affect dispatch.

## Responsive convention (mobile-safe layout)

> **Why this exists**: Home renders in a narrow phone viewport (~390px) as well as on desktop. A fixed multi-column grid that fits a wide card overflows its cells on a phone — the `TraderMoneyTruth` `grid-cols-3` collision (operator screenshot, 2026-06-12) was exactly this. There is no render-at-width test in the suite, so responsive bugs are invisible to gates unless a convention is enforced statically.

Two rules, enforced by `api/test_library_responsive.py` (a grep gate — it does not render; it pins the at-rest source):

1. **Metric/column grids are mobile-first.** Any `grid-cols-N` (N ≥ 2) MUST pair with a phone fallback: write `grid-cols-1 sm:grid-cols-N` (stack on phones, N-up from `sm:`). A bare `grid-cols-3` is a gate failure. Single-column grids and grids that already declare a `sm:`/`md:`/`lg:` breakpoint pass.
2. **Rows with right-aligned metadata wrap.** A `flex … justify-between` row whose right cluster carries metrics/timestamps (the headline-plus-tape shape, e.g. `TraderRegime`) MUST use `flex-wrap` so the cluster drops below the headline on narrow widths instead of colliding. (Advisory in the gate — `flex-wrap` is recommended, not hard-failed, because not every justify-between row has overflow risk.)

The convention is scoped to `components/library/` (the kernel + program component library this README owns). Components elsewhere in `web/components/` are not gated here; if a future finding shows the same class of bug outside the library, widen the gate's scope rather than copying the rule.

## Current set (alpha-trader, post-ADR-273 Phase 5)

All program-data routes mounted at `/api/programs/alpha-trader/*` per ADR-312 D9.

| Component | Path | Used by | Binding shape |
|---|---|---|---|
| `TraderRegime` | `programs/alpha-trader/TraderRegime.tsx` | home program_sections (order: 1) | `/api/programs/alpha-trader/regime` |
| `TraderPortfolio` | `programs/alpha-trader/TraderPortfolio.tsx` | home program_sections (order: 2) | `…/portfolio-history` + `…/money-truth` |
| `TraderMoneyTruth` | `programs/alpha-trader/TraderMoneyTruth.tsx` | home program_sections (order: 3) | `…/money-truth` |
| `TraderExpectancy` | `programs/alpha-trader/TraderExpectancy.tsx` | home program_sections (order: 4) | `…/money-truth.by_signal` |
| `TraderPositions` | `programs/alpha-trader/TraderPositions.tsx` | home program_sections (order: 5) | `…/positions` + `…/indicators` |
| `TraderSignals` | `programs/alpha-trader/TraderSignals.tsx` | home program_sections (order: 6) | `…/signals` |
| `TraderOrders` | `programs/alpha-trader/TraderOrders.tsx` | home program_sections (order: 7) | `…/recent-orders` |

## Future expansion (deferred until needed)

Per the alpha-trader paper design ([docs/analysis/alpha-trader-surface-design-2026-04-27.md](../../../docs/analysis/alpha-trader-surface-design-2026-04-27.md) §"Cross-cutting components"), the v1 library scope was sketched at 14 components. The Phase 2 implementation refinement: **build components only as bundles surface them**. The remaining 10 paper-design components (`MetricCardRow`, `TaskOutputViewer`, `NarrativeRail`, `QueueCard`, `AlertCard`, `TaskList`, `FilterChipRow`, `AttributedActionReview`, `AgentRoster`, `ReviewerHealthCard`, `PrincipleEditor`, `ReviewerCalibrationView`, `FileTree`, `PinnedShortcutRow`) land when needed.

## Universal kernel-default middle (post-Phase-I)

`DeliverableMiddle` at `web/components/work/details/DeliverableMiddle.tsx` is the **sole** kernel-default middle, rendering universally when no bundle middle matches by `task_slug`. Per ADR-261 D1 ("one execution shape") + ADR-262 §6.1, every recurrence's substrate lives at the slug-templated path `/workspace/reports/{slug}/{date}/output.md`; `DeliverableMiddle` reads that and degrades gracefully ("No past outputs yet") for reactive recurrences and recurrences that haven't fired yet. The legacy per-shape middles (`TrackingEntityGrid`, `ActionMiddle`, `MaintenanceMiddle`, `TrackingMiddle`) were DELETED in commit `6f586e3` (Phase I sweep, 2026-05-10).
