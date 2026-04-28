# Compositor — Architecture Reference

**Status:** Canonical architecture doc.
**Date:** 2026-04-27 (Phase 3 landing)
**Governs:** the compositor seam — how the FE renders against bundle composition manifests vs kernel defaults.
**Sibling docs:** [authored-substrate.md](./authored-substrate.md), [compose-substrate.md](./compose-substrate.md), [output-substrate.md](./output-substrate.md), [SERVICE-MODEL.md](./SERVICE-MODEL.md) (Frame 5).
**ADR home:** [ADR-225](../adr/ADR-225-compositor-layer.md). This doc is the reference; ADR-225 is the decision record + amendment trail.

---

## Purpose

This doc names the resolver pattern, the binding taxonomy, the kernel-default registry, and the singular-implementation discipline. It is the architecture-level entry point for understanding how a bundle's `SURFACES.yaml` becomes pixels on screen.

Read this when you're: writing a new library component, authoring a new bundle's SURFACES.yaml, debugging why a bundle override didn't render, or extending the resolver to a new tab. Read [ADR-225](../adr/ADR-225-compositor-layer.md) for the decision history.

---

## The seam in one diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  docs/programs/{slug}/SURFACES.yaml      ← bundle manifest (declarative)
│                                                                      │
│  api/services/composition_resolver.py    ← reads bundles, applies    │
│                                            phase overlays, merges    │
│                                            multi-bundle, returns dict│
│                                                                      │
│  GET /api/programs/surfaces              ← API contract              │
│                                                                      │
│  web/lib/compositor/useComposition.ts    ← FE fetcher + cache        │
│  web/lib/compositor/resolver.ts          ← match resolution +        │
│                                            kernel-default fallback   │
│  web/lib/compositor/kernel-defaults.ts   ← THE registry of kernel    │
│                                            chrome + cockpit panes    │
│                                                                      │
│  web/components/library/registry.tsx     ← LIBRARY_COMPONENTS dict   │
│                                            (kernel + bundle, single) │
│  web/components/library/MiddleResolver   ← detail content renderer   │
│  web/components/library/ChromeRenderer   ← detail chrome renderer    │
│  web/components/library/CockpitRenderer  ← list cockpit renderer    │
│                                                                      │
│  pixels                                                              │
└──────────────────────────────────────────────────────────────────────┘
```

The resolver pattern repeats at every step: declare in YAML → resolve via match (or fall back to kernel default) → dispatch through `LIBRARY_COMPONENTS` by `kind`. **One pattern, three call sites** (middle, chrome, cockpit). Adding a fourth concern would clone the same shape.

---

## Core invariants

These survive across phases and bundles. If a code change violates one, it's wrong.

### I1 — Kernel defaults are library components

The kernel doesn't have a special render path. Kernel-default chrome components live at `web/components/library/kernel-chrome/*.tsx` and are registered in `LIBRARY_COMPONENTS` alongside bundle components. The resolver dispatches them by `kind` like any bundle component would.

This is the load-bearing decision that makes the seam genuinely uniform. It means:
- Adding a new bundle is purely additive — no kernel branch.
- A bundle can mix kernel + bundle components in the same composition (e.g., alpha-trader's cockpit uses `KernelSinceLastLookPane` alongside `TradingProposalQueue`).
- "Override the kernel default" means "supply a different `kind` in your manifest" — no special API.

### I2 — Bundle declarations are data, not code

`SURFACES.yaml` carries no executable logic. Every binding is a filesystem path or a constrained filter spec. Every component reference is a `kind` string. The resolver inspects strings; it never `eval`s anything from a bundle.

### I3 — Components own their visual semantics; the resolver doesn't

The resolver decides *which* component renders. It does not impose layout, density, or styling. Bundle authors writing custom components honor the visual conventions of the slot they're filling (e.g., chrome metadata is "one-line operational signal," chrome actions are "in-row buttons"). Conventions are documented per-slot below; the compositor doesn't enforce them.

### I4 — Singular implementation per slot

There is one resolver, one registry, one per-slot renderer (`MiddleResolver` / `ChromeRenderer` / `CockpitRenderer`). No dual paths, no legacy fallbacks past the kernel-default level. If the resolver doesn't dispatch a component, the operator sees the kernel default. There is no third option.

### I5 — The seam respects the kernel/program boundary

Per [ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md) and [ADR-224](../adr/ADR-224-kernel-program-boundary-refactor.md): kernel code never branches on `program_slug`. The compositor reads bundle manifests; consumers (the four tabs) read the resolved composition. If you ever find yourself writing `if (programSlug === 'alpha-trader') ...` in a tab component, you've broken the seam — the answer is to declare the variation in the manifest.

---

## Binding taxonomy (6 types)

Per [ADR-225](../adr/ADR-225-compositor-layer.md) §2, bundles bind components to data via one of six binding types. Adding a seventh requires an ADR (anti-vocabulary-proliferation).

| Type | Resolves to | Example |
|---|---|---|
| `file` | One markdown file's full content | `/workspace/context/portfolio/_performance.md` |
| `frontmatter` | YAML frontmatter fields from a file | `{path: ..., fields: [pnl_30d, win_rate]}` |
| `task_output` | A frozen task output artifact | `{task_slug: daily-update, selector: latest}` |
| `action_proposals` | Filtered query against `action_proposals` table | `{filter: {status: pending}}` |
| `narrative` | Filtered query against narrative entries | `{filter: {weight: material}}` |
| `directory` | All files under a path (entity grid) | `/workspace/context/trading/` |

The resolver currently exposes a `resolveBindingPath(binding)` helper in `web/components/library/registry.tsx` that handles `file` / `frontmatter` / `directory` / `task_output` (path-shaped). `action_proposals` and `narrative` don't resolve to a single path — components handle those filter-shaped via `filters` on the component decl.

---

## The four resolution sites on Work

After Phase 3, the Work surface has four compositor-resolved slots:

### 1. Detail middle (content area)

- **Resolver:** `resolveMiddle(ctx, middles)` — 4-tier match (task_slug → output_kind+condition → output_kind → agent_role/class).
- **Renderer:** `<MiddleResolver>` (Phase 2).
- **Kernel default:** Falls through to one of four kind-specific middle components at `web/components/work/details/` (DeliverableMiddle, TrackingEntityGrid, ActionMiddle, MaintenanceMiddle). These take task-specific props (taskSlug, refreshKey, deliverableSpec) the registry doesn't thread, so they remain as the local fallback path. **Bundles may NOT register kernel-default middle replacements via `LIBRARY_COMPONENTS`** — they declare overrides in `tabs.work.detail.middles[].components` instead.
- **Bundle declaration:** `tabs.work.detail.middles[]` with `match`, `archetype`, `bindings`, `components`.

### 2. Detail chrome (metadata strip + actions row)

- **Resolver:** `resolveChrome(ctx, middles)` — same 4-tier match, looks up matched middle's `chrome` field.
- **Renderer:** `<ChromeRenderer>`.
- **Kernel default:** `KERNEL_DEFAULT_CHROME[output_kind]` in `kernel-defaults.ts` — registered library components (`KernelDeliverableMetadata`, etc.).
- **Bundle declaration:** `tabs.work.detail.middles[].chrome` (optional). Both `metadata` (single component) and `actions` (component array) independently optional — partial overrides allowed.
- **Action handler threading:** kernel and bundle chrome components both consume `WorkDetailActionsContext` (task, agents, mutationPending, pendingAction, actionNotice, onRunTask, onPauseTask, onEdit). Provider lives in `WorkDetail.tsx`.

### 3. List pinned tasks

- **Resolver:** Direct read of `composition.tabs.work.list.pinned_tasks: string[]`.
- **Renderer:** `WorkListSurface` consumes via `useComposition()`. Pinned slugs floated to top of group; non-pinned fall through to existing `compareTasks` order. Pinned rows render a small pin glyph next to the title.
- **Kernel default:** No pinning (empty list).
- **Bundle declaration:** `tabs.work.list.pinned_tasks: [slug-1, slug-2]`.

### 4. Cockpit (four faces of the operation, ADR-228)

Per ADR-228, the cockpit is no longer a flat pane registry. It is **four faces in fixed order** rendered directly by `<CockpitRenderer>`, with no compositor-resolver step between SURFACES.yaml and the faces.

- **Faces (universal, fixed order):**
  1. **Mandate** (`MandateFace`) — standing intent + autonomy posture, reads `_shared/MANDATE.md` + `_shared/AUTONOMY.md`. Skeleton state: destructive-tinted authoring CTA.
  2. **Money truth** (`MoneyTruthFace`) — where the account stands right now. Bundle-declared platform-live source (e.g., Alpaca for trader) with substrate fallback (`_performance.md`). Phase 1 of ADR-228 ships substrate-fallback path; platform-live ships in Commit 3.
  3. **Performance** (`PerformanceFace`) — mandate-attributed performance + Reviewer calibration from `/workspace/review/decisions.md`.
  4. **Tracking** (`TrackingFace`) — pending decisions (proposal queue with inline approve/reject) + operational state (bundle-fed) + recent activity (outcomes only — task-run delivery events excluded per ADR-228 D5).
- **Kernel default:** No bundle declaration → faces render kernel-default substrate paths.
- **Bundle declaration:** `tabs.work.list.cockpit.{mandate,money_truth,performance,tracking}` per-face binding map. Bundles cannot reorder or omit faces; they only fill them. Schema is open by design — face components consume only the keys they understand.
- **Cockpit context handler:** chat-draft seeder threads via `CockpitContext` provider in `<CockpitRenderer>`. The Mandate face uses it for skeleton-state authoring.

The flat `cockpit_panes` array, `KERNEL_DEFAULT_COCKPIT_PANES`, `resolveCockpitPanes`, and the six axis-shaped pane components from ADR-225 Phase 3 (`MandateStrip`, `MoneyTruthTile`, `KernelNeedsMePane`, `MaterialNarrativeStrip`, `TrustViolations`, `TeamHealthCard`) were all deleted by ADR-228.

The phase-aware banner (`tabs.work.list.banner`) is a separate concern handled by `<BundleBanner tab="work" />`, mounted directly in `WorkListSurface` since Phase 2.

---

## Per-slot conventions

When authoring a new component for a slot, honor these conventions. They're not enforced by the compositor; they're how the slot looks coherent across kernel and bundle implementations.

### Chrome metadata (single component slot)

- **Visual:** one-line operational signal strip. ~6-10 small inline elements separated by `·`. Total width fits the SurfaceIdentityHeader metadata slot.
- **Content shape:** mode badge (always first) → kind/role label → assigned agent (linked) → schedule → time-of-most-recent-thing-this-task-is-about.
- **What "operational" means:** signal that helps the operator answer "is this task healthy and current?" Not historical context (that's the narrative). Not synthesis (that's the middle).
- **Example kernel default:** `KernelDeliverableMetadata` — "Recurring · Report · Researcher · weekly · Last output: 3h ago".
- **Example bundle override:** `TradingPortfolioMetadata` — "Recurring · 📊 Portfolio · Researcher · Last sync: 30s ago · 12 positions". Same shape, substrate-aware signal.

### Chrome actions (array slot)

- **Visual:** in-row buttons/menus right-aligned in the SurfaceIdentityHeader actions slot.
- **Content shape:** primary action (Fire/Run if reactive) → overflow menu (Pause/Resume/Edit-in-chat).
- **CRUD discipline:** lifecycle ops are Direct (per ADR-215 R1); `Edit in chat` opens the rail composer with a seeded prompt (R5).
- **Example kernel default:** `KernelDeliverableActions` — single overflow menu (`OverflowMenu` from `web/components/library/kernel-chrome/`).
- **Example bundle override:** alpha-trader's signal task could ship a custom `TradingSignalActions` component with a "Backtest now" button alongside the overflow.

### Cockpit pane (array slot)

- **Visual:** vertical stack of cards/strips inside the cockpit zone (section label "Cockpit", subtle tint, padding).
- **Content shape:** Briefing/Queue/Dashboard-archetype cards per [ADR-198](../adr/ADR-198-surface-archetypes.md). No long-running interactive UI — panes are glance-shaped.
- **Order matters:** declared order = render order. Operators read top-to-bottom.

### Detail middle (variable slot)

- **Visual:** the entire content area below the chrome. Bundle middles take full width and decide their own layout.
- **Content shape:** archetype-driven (Document / Dashboard / Queue / Briefing / Stream per ADR-198). The `archetype` field on `MiddleDecl` is currently informational; future renderer hooks may key off it.

---

## How a bundle authors a Phase 3 override

Step-by-step, taking alpha-trader's `portfolio-review` as the example:

**1.** Decide what middle archetype the task wants. portfolio-review wants Dashboard (live tile rendering of `_performance.md`, `_positions.md`, `_risk_state.md`).

**2.** Declare the middle in `SURFACES.yaml`:

```yaml
- match: { task_slug: portfolio-review }
  archetype: dashboard
  bindings:
    performance: /workspace/context/portfolio/_performance.md
    positions: /workspace/context/portfolio/_positions.md
    risk: /workspace/context/portfolio/_risk_state.md
  components:
    - kind: PerformanceSnapshot
      source: performance
    - kind: PositionsTable
      source: positions
    - kind: RiskBudgetGauge
      source: risk
```

**3.** Decide whether the kernel chrome makes sense. For portfolio-review, "Last output: 3h ago" misleads (substrate regenerates each run; what matters is sync freshness, not artifact age). So override:

```yaml
  chrome:
    metadata:
      kind: TradingPortfolioMetadata
      source: performance  # reads frontmatter
    actions:
      - kind: KernelDeliverableActions  # reuse kernel actions
```

**4.** Author the new component(s). For `TradingPortfolioMetadata`: a `web/components/library/TradingPortfolioMetadata.tsx` that consumes `useWorkDetailActions()` for task + assignedAgent, fetches the source path's frontmatter, renders a one-line strip per the chrome metadata convention.

**5.** Register the new component in `web/components/library/registry.tsx`:

```typescript
TradingPortfolioMetadata: ({ source }) => <TradingPortfolioMetadata source={source} />,
```

**6.** Reload (the composition cache currently requires a hard refresh in dev). The portfolio-review detail page renders with the bundle middle + bundle chrome metadata + kernel chrome actions. Kernel chrome remains for every other task.

---

## Multi-bundle composition

When two bundles are active in a workspace (deferred until alpha-commerce activates concurrently with alpha-trader), the backend resolver merges their composition trees per [ADR-225 §2](../adr/ADR-225-compositor-layer.md):

| Field | Merge rule |
|---|---|
| `tabs.{tab}.list.pinned_tasks` | Union, preserve activation order, dedupe |
| `tabs.{tab}.list.pinned_shortcuts` | Union, dedupe by path |
| `tabs.{tab}.list.cockpit` | Per-face deep-merge; first-bundle wins on scalar conflicts within a face |
| `tabs.{tab}.detail.middles[]` | Union (concatenate); resolver's first-match-wins handles conflicts |
| `tabs.{tab}.list.banner` | First-bundle wins on scalar conflicts |
| `chat_chips` | Union, dedupe |

This is implemented in `_merge_list_or_detail_block` in `api/services/composition_resolver.py`. No FE work needed for multi-bundle support — the FE just consumes the merged tree.

---

## Naming gap (recorded for honesty)

The dispatcher component is named `MiddleResolver`. After Phase 3 it has a sibling (`ChromeRenderer`) and a peer (`CockpitRenderer`). The name overfits to "middle" — it suggests the component is the resolver for the middle slot specifically, when in fact `MiddleResolver` is the middle slot's renderer that calls into a shared `resolveMiddle` resolver.

Rename considered, rejected: too many call sites, too many ADR references, low payoff. The architecture-level mental model is:

- `web/lib/compositor/resolver.ts` exports the **resolver functions** (`resolveMiddle`, `resolveChrome`, `resolveCockpitPanes`).
- `web/components/library/{MiddleResolver, ChromeRenderer, CockpitRenderer}.tsx` are the **renderers** that call the resolver functions and dispatch through `LIBRARY_COMPONENTS`.

If the naming gets confusing in a code review, point at this section.

---

## Adding a new resolved slot (future)

If we ever extend the seam to a fifth concern (e.g., a "task header" slot above SurfaceIdentityHeader, or chrome on the Files tab), the recipe is:

1. Add the optional manifest field to the appropriate Tab block in `web/lib/compositor/types.ts`.
2. Update backend `_merge_list_or_detail_block` if the field is multi-bundle-mergeable.
3. Add a `resolveX(ctx, ...)` function in `web/lib/compositor/resolver.ts` paralleling existing resolvers.
4. Add a `KERNEL_DEFAULT_X` entry in `kernel-defaults.ts`.
5. Author kernel-default components in `web/components/library/kernel-{slot}/`.
6. Register them in `LIBRARY_COMPONENTS`.
7. Author an `<XRenderer>` that calls the resolver and dispatches through the registry.
8. Update consumers to mount the renderer.

The existing pattern is the spec. Don't invent a new shape.

---

## Related

- [ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md) — names compositor as a load-bearing OS layer (Principle 16)
- [ADR-223](../adr/ADR-223-program-bundle-specification.md) — `SURFACES.yaml` schema
- [ADR-224](../adr/ADR-224-kernel-program-boundary-refactor.md) — kernel/program boundary discipline
- [ADR-225](../adr/ADR-225-compositor-layer.md) — compositor decision record + amendment trail
- [ADR-198](../adr/ADR-198-surface-archetypes.md) — five archetypes (Document / Dashboard / Queue / Briefing / Stream)
- [ADR-167](../adr/ADR-167-list-detail-surfaces.md) — list/detail pattern, kind-aware detail
- [docs/design/SURFACE-CONTRACTS.md](../design/SURFACE-CONTRACTS.md) — per-tab cockpit contracts (consumes this doc as the seam reference)
