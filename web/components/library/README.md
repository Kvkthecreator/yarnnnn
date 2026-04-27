# System Component Library — ADR-225 §3

Universal components composition manifests reference. Per ADR-222 Principle 16: **system component library is additive-only**. Components shipped here serve programs (programs declare what they need); the library grows via demand-pull, not speculation.

## Discipline

- **Each component is a TSX file with the same name as the SURFACES.yaml `kind` field.** `kind: PerformanceSnapshot` → `PerformanceSnapshot.tsx`.
- **Components accept a `binding` prop** matching one of the 6 binding-type taxonomy shapes (`file | frontmatter | task_output | action_proposals | narrative | directory` per ADR-225 §2). They fetch+render via existing hooks (`useTaskOutputs`, `useWorkspaceFile`, etc.).
- **Components are PURE READERS in both compose modes.** Surface compose: live binding, re-rendered per load. Document compose: frozen snapshot at compose time. Same render, different data freshness. **Components do not mutate.** Operator interactions that mutate (approve, reject, edit) flow through existing primitive surfaces.
- **Components are additive-only.** Removing a component is breaking and requires a deprecation cycle with ADR ratification.
- **No new component shipped without a bundle (or kernel-default middle) that uses it.** The library grows because programs demand it, not on speculation.
- **A program may NOT ship its own components.** Components needed for a program contribute to this universal library first (PR convention); the bundle then references them. Same rule as macOS frameworks vs `.app` bundles.

## Current set (alpha-trader Phase 2)

| Component | Used by | Binding shape | Status |
|---|---|---|---|
| `PerformanceSnapshot` | alpha-trader portfolio-review middle | file (markdown) | Placeholder render |
| `PositionsTable` | alpha-trader portfolio-review middle | file (markdown) | Placeholder render |
| `RiskBudgetGauge` | alpha-trader portfolio-review middle | file (markdown) | Placeholder render |
| `TradingProposalQueue` | alpha-trader trading-signal middle | action_proposals | Placeholder render |

These are **placeholder implementations** — they read the substrate path, render a simple representation. Real visual designs land additively as alpha-trader matures into a built program. The point of Phase 2 is the wiring (resolver → component dispatch via `kind`), not the visual polish.

## Future expansion (deferred until needed)

Per the alpha-trader paper design ([docs/analysis/alpha-trader-surface-design-2026-04-27.md](../../../docs/analysis/alpha-trader-surface-design-2026-04-27.md) §"Cross-cutting components"), the v1 library scope was sketched at 14 components. The Phase 2 implementation refinement: **build components only as bundles surface them**. The remaining 10 paper-design components (`MetricCardRow`, `TaskOutputViewer`, `NarrativeRail`, `QueueCard`, `AlertCard`, `TaskList`, `FilterChipRow`, `AttributedActionReview`, `AgentRoster`, `ReviewerHealthCard`, `PrincipleEditor`, `ReviewerCalibrationView`, `FileTree`, `PinnedShortcutRow`) land when needed.

## Existing kind-aware middles (kernel defaults)

The 4 existing kind-middles (`DeliverableMiddle`, `TrackingEntityGrid`, `ActionMiddle`, `MaintenanceMiddle`) at `web/components/work/details/` continue to render as kernel-default fallback when no bundle middle matches. Per ADR-225 §5 implementation refinement: they are NOT relocated to `library/` in Phase 2 — relocation is mechanical busywork until a bundle actually overrides one.
