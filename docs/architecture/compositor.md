# Compositor — Architecture Reference

> **ADR-312 vocabulary note (2026-06-02):** the **cockpit surface renames to Home** (`slug: home`, route `/home`, `HomeRenderer`/`HomeHeader`), and the bundle composition key **`tabs.work.list.cockpit` → `tabs.work.list.home`**. The compositor seam below is unchanged — only the surface name and composition key. The Home is a *composition over the workspace's present constituents* (six kernel slots; the program declares each slot's weight/label/shape via `home.program_sections`), substrate-forward when empty. The two registers (ADR-309) refine to three: `intent` + `os-config` + `application` (ADR-312 D5). Read "cockpit" below as "Home."

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

## Two registers, one window manager (ADR-309)

Everything the operator sees inside the authenticated workspace is a window
mounted by the one window manager (`useSurfacePreferences`, ADR-297). But
windows come in **two registers**, and the distinction is load-bearing —
collapsing them into a flat "surface" concept was the un-hardening ADR-309
closed.

- **System Settings** (`register: settings`) — the OS configuring *itself*.
  Finite, kernel/program-defined, bound 1:1 to a governance substrate file,
  bespoke editor/view. Mandate, Autonomy, Principles, Pace, Identity,
  Program, Settings, Connectors. The operator does not install or request
  these; they exist because the OS/program exists (the macOS System Settings
  analog). Their per-file content parsers live in `web/lib/content-shapes/`
  (ADR-245).

- **Applications** (`register: application`) — open files + live state. A
  typed userspace file (report, PDF, image), a folder (Files = Finder), or
  live state composed into a view (Cockpit = Activity Monitor). Feed, Queue,
  Activity, Agents, Cadence, Files, Cockpit. **Artifacts are files**, not
  surfaces: a Reviewer-generated report/PDF is substrate; the viewer
  Application opens it via the **type→application association**
  (`web/lib/file-types`, `resolveViewerApplication`). The report Application
  is `DeliverableMiddle`; the generic file/PDF/image viewer is ContentViewer
  dispatching through the association table. One artifact, potentially many
  Applications showing it (Files dispatches; Cockpit embeds).

`register` is declared per surface in `api/services/kernel_surfaces.py` and
mirrored on the FE `Surface` type. Chrome (top-bar, launcher, chat-drawer)
is neither register — it is the window manager's own framing.

> **STALE SECTION — corrected 2026-08-02 (the ADR-512 canon pass; drift flagged by the
> chat-architecture audit).** The two paragraphs below describe the pre-ADR-454
> chat-drawer/rail model and are preserved as history only. **ADR-454 D3 gated the
> steward's chat chrome off entirely** (`STEWARD_CHROME_ENABLED`); the live chat is a
> **windowed kernel surface** — a `SurfaceRegistry` row (`chat`), launcher-tier primary,
> dock anchor + default landing per ADR-435 — an app under the Think act (ADR-507), not
> chrome and not a rail. The `Viewing:`/`surfaceOverride` binding described below died
> with the drawer. Read the FE `SurfaceRegistry` + `kernel_surfaces.py` for the live set.

**Chat is the command rail, not an overlay (ADR-316).** The chat-drawer
chrome lives in the `main-rail` region — a flex sibling of `SurfaceViewport`
inside `main` that *reduces* the surface area when open, never occluding it.
On desktop it docks to the right of the window area (the foregrounded surface
reflows and stays co-visible, so the chat header's `Viewing: X` label is
honest); on mobile (<640px) it degrades to a full-screen overlay because the
surface cannot be co-visible. The same `foregrounded` slug that names the
`Viewing:` surface scopes the agent's context (`surfaceOverride`) and resolves
its prompt profile (ADR-186) — one gesture (`foregroundSurface`) both raises
the window and scopes the conversation. Chrome that frames content sits beside
it; it does not cover it.

> **The shell's 640px is the SHELL's threshold, not every surface's.** A surface
> may declare its own width ladder when its internal layout needs more room than
> the window does — the authoring workbench does (`WORKBENCH_*_PX`, four rungs;
> see AUTHORING.md rule 15). Those thresholds live in the same file as
> `MOBILE_BREAKPOINT_PX` **deliberately**: they were previously spelled as raw
> `md:` classes inside the surface, which is how the shell and the workbench came
> to disagree about what a tablet is and left a band where three desktop columns
> rendered with no room for them. A surface-specific ladder is legitimate; a
> second *undeclared* spelling of one is the drift. Surfaces measure their own
> container (`useNarrowContainer` / `useWorkbenchWidth`), because a surface can be
> narrow inside a roomy window.

**Two layout modes — the operator picks the spatial paradigm (ADR-358).** The
shell's arrangement is an operator preference (`layoutMode ∈ {canvas, desktop}`
in `ShellChromeContext`, persisted, default **canvas**), chosen at the UserMenu.
**Canvas:** one surface fills the column edge-to-edge (window chrome suppressed
via `canvasFill` + `chromeless`) with chat docked as a flex **rail on the
right** — the two-panel chat-interface composition, side-to-side divider only.
**Desktop:** the ADR-297 D15 free-floating window manager, with chat as a
**summoned `position: fixed` overlay** (FAB-summoned, floats over the windows,
consumes zero flex space) — *not* a pinned rail, so "everything floats in
Desktop, chat included." The `main` flex row order is fixed (surface, then
rail); the docked-vs-overlay decision lives entirely in `ChatDrawer`
(`railMode` vs `overlayMode`). Chat is chrome in every mode, **never** a window
(ADR-316 Alternative A stays rejected — the command channel must not be
closable/buryable like content). Singular Implementation: one compositor, one
chat component, one window manager; the window-manager core is mode-agnostic,
and the `Viewing: X` ↔ `surfaceOverride` ↔ prompt-profile binding is identical
in every mode.

**Window-namespaced deep-link params (ADR-358 D6).** Several windows are open at
once but there is only ever **one** query string, so each window's intra-surface
params are namespaced by its slug: `?{slug}.{key}`
(`workspace-settings.pane=autonomy`, `settings.pane=billing`,
`recurrence.pane=activity`, `agents.agent=reviewer`). A window reads only its own
namespace, so open windows never collide and each persists its own deep-link
state. Singular Implementation: `scopeParamKey(slug, key)` forms the one prefix;
`navigateToSurface(slug, params)` scopes by the target slug; surfaces use the
`useSurfaceParam(slug)` hook (read/write their own params); `SettingsPaneShell`
takes a `windowSlug` prop. Callers never hand-build the prefix.

> **Premise corrected 2026-08-20 (ADR-297 D19.8).** D6 originally justified this by
> D5's `/desktop` baseline — "every window sits on one pathname, therefore one query
> string." D5's pathname-preservation is now withdrawn (the pathname follows the
> foreground), but **the namespacing is unchanged and still required**: a backgrounded
> window's params are remembered and re-applied when it returns, so two windows'
> vocabularies would still collide on a flat `?pane=`. The rule outlived its original
> reason — keep it.

**What a param is FOR, and how long it lives.** Two registries in
`lib/shell/surface-preferences.ts` answer two different questions, and a surface
that registers in neither gets the wrong default for both:

- `SURFACE_PARAM_KEYS` — which keys a surface OWNS. Unlisted keys are dropped on
  read. A surface absent from this map is *unconstrained*: any key delivered to
  it is accepted and persisted forever, including one it has never read.
- `SURFACE_EPHEMERAL_PARAM_KEYS` — which owned keys must not be REPLAYED on a
  bare launch. `reconcileUrl` merges `incoming < remembered < delivered`, so a
  remembered key outranks a live deep-link. The test is whether replaying it
  answers a question the member is asking *now* (a resting posture — restore) or
  one they asked once and moved on from (a specific object they drilled into —
  forget). Document identity is always the second kind.

**One arrival door per surface.** A deep-link param is inbound transport: the
surface OPENS it and then DRAINS it, in exactly one handler, keyed on the param
value. Do not add a second consumer — in canvas and mobile modes `SurfaceViewport`
renders only the foregrounded surface, so a backgrounded window is *unmounted*
and a cross-surface jump REMOUNTS it; a mount-time capture and a post-mount
effect then race over one param and both lose (operator-observed 2026-08-13:
Radar's "open folder" landed on generic Recents with the param stranded in the
URL). Staleness is handled by the drain plus an honest ephemeral classification,
never by a guard that can outvote the live signal. Gate:
`web/scripts/gates/files_arrival_door.mjs`.

**An arrival door NORMALIZES before it opens** (ADR-587). The door is where a
name from OUTSIDE the app enters — a link someone was sent, a path pasted back
from an external AI — so it is where the ADR-512 D5 reference grammar is
applied, via `toWorkspacePath` (`web/lib/interop/fileHandle.ts`). Files
previously matched `workspace_files.path` verbatim, so of the honest spellings
of one name only the absolute `/workspace/…` form resolved; a
`yarnnn://workspace/…` handle or a bare relative path fell through to an empty
selection, and the surface then rendered its Recents — which looks like a
working page. A refusal (another scheme, `..`) opens nothing rather than
guessing.

**A surface param is slug-namespaced** (`scopeParamKey`: `files.path`, not
`path`). The reconciler only adopts params matching the foreground slug and
leaves the rest untouched, so a bare param is not a fallback — it is never read
at all. ADR-587 found three emitters that had been dead links for this reason.
Gate: `api/test_adr587_handle_grammar_parity.py` (D3).

**Agent-composed Applications** — the orchestration layer authoring a new
Application by writing an application-manifest *file* in the substrate
(everything-is-a-file extends to app definitions; the compositor reads
installed-app manifests the way Finder reads `/Applications`), including
mandate-driven self-initiative — is the **named, deferred horizon** per
ADR-309 §Forward horizon. Not built; the seam is kept clean (the compositor
already reads declarative surface manifests, which is the mechanism a
runtime-authored app manifest would reuse).

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
| `file` | One markdown file's full content | `/workspace/operation/portfolio/_money_truth.md` |
| `frontmatter` | YAML frontmatter fields from a file | `{path: ..., fields: [pnl_30d, win_rate]}` |
| `task_output` | A frozen task output artifact | `{task_slug: daily-update, selector: latest}` |
| `action_proposals` | Filtered query against `action_proposals` table | `{filter: {status: pending}}` |
| `narrative` | Filtered query against narrative entries | `{filter: {weight: material}}` |
| `directory` | All files under a path (entity grid) | `/workspace/operation/trading/` |

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
  1. **Mandate** (`MandateFace`) — standing intent + autonomy posture, reads `constitution/MANDATE.md` + `governance/AUTONOMY.md`. Skeleton state: destructive-tinted authoring CTA.
  2. **Money truth** (`MoneyTruthFace`) — where the account stands right now. Bundle-declared platform-live source (e.g., Alpaca for trader) with substrate fallback (`_money_truth.md`). Phase 1 of ADR-228 ships substrate-fallback path; platform-live ships in Commit 3.
  3. **Performance** (`PerformanceFace`) — mandate-attributed performance + Reviewer calibration from `/workspace/persona/judgment_log.md`.
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

**1.** Decide what middle archetype the task wants. portfolio-review wants Dashboard (live tile rendering of `_money_truth.md`, `_positions.md`, `_risk_state.md`).

**2.** Declare the middle in `SURFACES.yaml`:

```yaml
- match: { task_slug: portfolio-review }
  archetype: dashboard
  bindings:
    performance: /workspace/operation/portfolio/_money_truth.md
    positions: /workspace/operation/portfolio/_positions.md
    risk: /workspace/operation/portfolio/_risk_state.md
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

---

## Navigating between surfaces (the singular path)

> **The one rule.** Inside the authenticated shell, ask one question: *am I moving
> **between** surfaces, or **within** one?* Everything follows from the answer.

| You are… | Use | Pathname | URL params |
|---|---|---|---|
| moving to another surface — any trigger: dock, launcher, button, **text link** | `navigateToSurface(slug, params?)`; `<SurfaceLink to=… params=…>` when the trigger is a link | **follows the target** (`/{slug}`) | replaced with the target's |
| changing what the current surface shows (which agent, which file, which pane) | `useSurfaceParam(slug)` → `setSurfaceParams` | **unchanged** | replaced in place |
| leaving the shell entirely (auth, marketing, a stub) | `router.push` / server `redirect()` | n/a | n/a |

**Three things that are never correct inside the shell:**

1. **A raw `<a href="/{surface}">`.** It is a document load: the SPA unmounts, remounts,
   paints the *remembered* foreground, and only then does the pathname sync foreground
   the target — a visible two-step. Use `SurfaceLink`, which renders a real `<a>` (so
   middle-click, cmd-click and screen readers still work) and intercepts only the plain
   left-click. Gated by `api/test_adr297_navigation_enactment.py`.
2. **`router.push('/{surface}')` for cross-surface navigation.** The compositor owns
   navigation; the browser router is transport, not control (ADR-222). Same gate.
3. **Hand-adding a route to `PROTECTED_PREFIXES`.** It **derives** from
   `KERNEL_SURFACE_SLUGS` — a surface is auth-gated because it *is* a surface. Older
   surface ADRs (e.g. ADR-243, ADR-331) list "added `/x` to `PROTECTED_PREFIXES`" as a
   step; that step is obsolete, and forgetting it is exactly how eight live surfaces went
   ungated until 2026-08-20. Gated by `api/test_auth_gate_covers_every_surface.py`.

**The address bar is honest.** `reconcileUrl` owns pathname *and* query together: the URL
always names the foregrounded surface and carries only that surface's params, namespaced
`{slug}.{key}`. This is a round-trip contract — what `reconcileUrl` writes, the cold-load
sync (`resolveRouteSurface`) must read back as the same surface, so a refresh reloads what
you were looking at. Both halves are pure functions in `web/lib/shell/route-sync.ts` and a
gate executes the round trip (`api/test_adr297_pathname_follows_foreground.py`).

Canon: [ADR-297](../adr/ADR-297-surfaces-as-substrate-mirror.md) **D19.5** (the verb),
**D19.6** (intra-surface), **D19.8** (the pathname follows the foreground — withdraws
D19.2's pathname clause and supersedes [ADR-358](../adr/ADR-358-layout-mode-canvas-vs-desktop.md) D5's
`/desktop`-baseline half).

## Related

- [ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md) — names compositor as a load-bearing OS layer (Principle 16)
- [ADR-223](../adr/ADR-223-program-bundle-specification.md) — `SURFACES.yaml` schema
- [ADR-224](../adr/ADR-224-kernel-program-boundary-refactor.md) — kernel/program boundary discipline
- [ADR-225](../adr/ADR-225-compositor-layer.md) — compositor decision record + amendment trail
- [ADR-198](../adr/ADR-198-surface-archetypes.md) — five archetypes (Document / Dashboard / Queue / Briefing / Stream)
- [ADR-167](../adr/ADR-167-list-detail-surfaces.md) — list/detail pattern, kind-aware detail
- [ADR-297](../adr/ADR-297-surfaces-as-substrate-mirror.md) D19.5–D19.8 — the navigation verbs + the pathname contract (see "Navigating between surfaces" above)
- [docs/design/WORKSPACE.md](../design/WORKSPACE.md) — per-tab cockpit contracts (consumes this doc as the seam reference)
