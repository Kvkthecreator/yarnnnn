# ADR-297 — Surfaces as Substrate Mirror: Atomic Surfaces, Summon Index, Compositor as Registry

> **Status:** Implemented (2026-05-21, same-session clean-slate migration)
> **Amendment (2026-05-21 same-session, pre-Phase-2-implementation):** D1 kernel surface list extended from 12 to 13 entries with the addition of `cockpit` (Dashboard archetype). Resolves an ambiguity the deletion-scope audit surfaced: `/work` today hosts cockpit rendering (ADR-228 four-face stack via `CockpitRenderer`) inside its dashboard tab. Clean-slate migration dissolves `/work` entirely — recurrence list folds into Cadence, task detail becomes drill-down from Cadence (`/cadence/{slug}`), and cockpit rendering relocates to its own atomic Cockpit surface. The 13th kernel surface honors substrate-mirrors-surface for the cockpit-as-substrate-read concept that ADR-228 already established; no rewrite of `CockpitRenderer`, just relocation.
> **Authors:** KVK, Claude
> **Supersedes:** [ADR-244](ADR-244-workspace-settings-surface.md) (workspace settings surface as container — replaced by atomic kernel surfaces) · [ADR-266](ADR-266-workspace-surface-content-discipline.md) (workspace page-as-container reshape — replaced by atomic + index) · [ADR-243](ADR-243-schedule-surface.md) (Schedule surface as a tab — folds into atomic Cadence surface) · the 4-tab nav portion of [ADR-214](ADR-214-agents-page-consolidation.md) (Feed/Work/Agents/Files framing — dissolves into pinned-surface dock + summon index)
> **Amends:** [ADR-205](ADR-205-workspace-primitive-collapse.md) F1 (chat-first landing — replaced by last-used home) · [ADR-225](ADR-225-compositor-layer.md) (compositor extended from middle-component-resolver to full surface-registry) · [ADR-198](ADR-198-surface-archetypes.md) (every surface declares its archetype) · [ADR-251](ADR-251-system-agent-reviewer-first-class-surfaces.md) (Reviewer-page tab structure — governance content moves to atomic surfaces, Reviewer page shrinks to Reviewer-substance only)
> **Preserves:** [FOUNDATIONS](../architecture/FOUNDATIONS.md) Axioms 1–9 · [ADR-209](ADR-209-authored-substrate.md) (attribution model) · [ADR-222](ADR-222-agent-native-operating-system-framing.md) (kernel/userspace boundary — this ADR enacts the boundary at the surface layer) · [ADR-216](ADR-216-orchestration-surface-vs-judgment-persona.md) (orchestration vs judgment taxonomy) · [ADR-223](ADR-223-program-bundle-specification.md) (bundle structure) · [ADR-213](ADR-213-surface-pull-composition.md) (compose-on-demand)
> **Companion discourse:** [`docs/design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md`](../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md) (parked design discussion that produced this ADR's convergence) · [`docs/architecture/cadence-and-wakes.md`](../architecture/cadence-and-wakes.md) §15 item 4 (operator-visible cadence surface — closed by this ADR's atomic Cadence surface)

---

## Context

Three sessions of frontend work (ADR-244 → ADR-251 → ADR-266) iterated on a **page-as-container** model: `/workspace` rendering four governance concepts as inline cards, Reviewer-page tabs mirroring some of the same content, `/schedule` as a separate-but-related cadence surface, four top-level tabs (Feed · Work · Agents · Files) as the nav spine. Each iteration tightened the model but left recurring symptoms:

1. **Container churn.** Every new authored concept triggered re-litigation of *"which container does this go in?"* — Workspace page, Reviewer tab, Settings, or new top-level surface. The cadence/wake surfacing question (the prompt for this ADR's discourse session) was the fourth instance.
2. **Surface duplication.** ADR-266 explicitly said `/workspace` *"replaces the Mandate/Autonomy/Principles tabs on the YARNNN agent detail."* The Reviewer page still renders the same `DelegationCard` and `PrinciplesCard` components inside its Autonomy and Principles tabs. Two surfaces, one substrate — Singular Implementation violated for ~7 months.
3. **Substrate atomicity vs surface coupling.** Each authored concept already has its own substrate file (`MANDATE.md`, `_autonomy.yaml`, `principles.md`, `IDENTITY.md`, `BRAND.md`, `_recurrences.yaml`, `_hooks.yaml`, `standing_intent.md`). The kernel treats them as atomic per FOUNDATIONS Axiom 1. The container model is the **only** layer that violates that atomicity.
4. **Compositor underused.** [ADR-225](ADR-225-compositor-layer.md) shipped a working compositor layer that already supports per-bundle SURFACES.yaml composition. The compositor's output is currently scoped to middle-component resolution inside fixed surfaces. The full-surface composition capability already exists in the code; it's not yet exposed at the shell level.
5. **OS framing canonized but not enacted at the surface layer.** [ADR-222](ADR-222-agent-native-operating-system-framing.md) canonized YARNNN as an Agent-Native OS where kernel/program/userspace boundaries are literal. The substrate layer honors this rigorously (kernel substrate files, per-bundle `_recurrences.yaml`, operator-writable workspace content). The surface layer doesn't yet — kernel surfaces, program surfaces, and operator concepts are bundled together on container pages.

This ADR closes all five gaps with one structural principle: **surface shape and surface authorship both mirror substrate**. The implementation is continuous with existing infrastructure (extends ADR-225's compositor) rather than a green-field rebuild.

---

## Foundational principle

> **Surface shape and surface authorship both mirror substrate.**

### Surface = viewport panel, not URL destination (2026-05-21 same-session amendment)

A surface is a **mountable React component bound to substrate**, addressed
by surface state (slug + params), rendered into the shell's viewport.
URLs are *optional addressing transport*, not the surface's identity.

**Implementation status (2026-05-21)**: the axiom is enacted at the
source-of-truth layer (DeskContext is canonical for surface identity;
Dock + Launcher dispatch `setSurface`, not `router.push`; the per-slug
URLs sync to DeskState via the pathname → atomic-slug useEffect in
DeskContext). The per-slug Next.js routes (`/cadence`, `/mandate`,
etc.) survive as **deep-link transport** and bookmark safety — they
are no longer the surface's identity, just one way to reach it.
SurfaceRegistry + SurfaceViewport components are committed and ready
for use when ADR-297 D10 advances to multi-surface coexistence (split-
mode / peek / pinned-content). At that point the route files become
thin AtomicSurfaceMount wrappers and the actual render moves into
SurfaceViewport. For the alpha-1 single-active-surface state, this
intermediate shape honors the axiom without requiring full component
extraction across 13 surfaces.

This commits the OS-shell framing of ADR-222 at the frontend layer. A
surface in YARNNN is structurally analogous to an *app window* in macOS:
it has state, it mounts into a viewport, it can coexist with other
surfaces, it persists across navigations within the shell.

The axiom rules out:
- URL-per-surface as primary identity (browser-page semantics)
- Next.js route-per-surface as the canonical mounting story
- Browser back/forward as the surface-switching mechanism (becomes a
  side effect of surface state, not the driver)

The axiom unlocks (latent capability — implemented when operator demand
surfaces):
- Multi-open (two surfaces side-by-side)
- Peek (transient overlay preview without navigating away)
- Pinned-content (surface persistently visible, not just an icon)
- Action mode (launcher executes intent directly into surface state)

Companion mechanism: `DeskContext` (ADR-013 / ADR-022 / ADR-023, never
deleted, partially buried under URL-route accretion through ADR-244 /
ADR-251 / ADR-266) is the **surface registry at runtime**. Its
reducer's `surface` field carries active surface state; URL hash is the
deep-link adapter, not the primary identity.

The corollaries:

1. **Atomicity** — Substrate is atomic (one concept per file). Surfaces are atomic (one concept per surface). 1:1 mapping between substrate file class and surface.
2. **Authorship tiers** — Substrate has three authorship tiers (kernel / program-bundle / workspace-operator). Surfaces have the same three tiers. Each surface inherits the tier of its substrate.
3. **Attribution** — Substrate writes carry `authored_by` per ADR-209. Surfaces display provenance where it aids operator understanding.
4. **Composability** — Substrate is composable (operator/Reviewer authors new files via primitives). Surfaces can become composable (Thesis 2, forward horizon — see §Forward horizon).

This principle subsumes and clarifies the prior surface-model attempts. There is no need to choose a container's "right" home for a concept — each concept lives where its substrate lives, at its own surface.

---

## Decisions

### D1 — Atomic surfaces, one per substrate concept

Every operator-authored governance concept becomes its own self-contained surface. The page-as-container model dissolves.

**Kernel surfaces** (universal — every YARNNN workspace has these):

| Surface | Substrate | Archetype (ADR-198) |
|---|---|---|
| Feed | session_messages (chat narrative) | Stream |
| Cadence | `/workspace/_recurrences.yaml` + `/workspace/_hooks.yaml` + `/workspace/review/standing_intent.md` + execution_events telemetry | Dashboard |
| Delegation | `/workspace/context/_shared/_autonomy.yaml` | Document |
| Mandate | `/workspace/context/_shared/MANDATE.md` | Document |
| Principles | `/workspace/review/principles.md` + `/workspace/review/_principles.yaml` | Document |
| Identity | `/workspace/context/_shared/IDENTITY.md` | Document |
| Brand | `/workspace/context/_shared/BRAND.md` | Document |
| Files | `workspace_files` (all paths) | Browser (raw substrate viewer; ADR-198 catalog extends with Browser as needed) |
| Agents | `agents` table + per-agent substrate | Roster (extends ADR-198 catalog) |
| Program | `/workspace/_program.yaml` + bundle MANIFEST | Document |
| Queue | `action_proposals` (pending) | Queue |
| Activity | `execution_events` | Stream |

Container surfaces dissolve. Specifically:
- `/workspace` (current four-card render) → dissolved; the URL becomes a redirect to the index for backward compatibility (or removed if no inbound links remain after migration).
- `/agents?agent=reviewer` Autonomy + Principles tabs → dissolved; deep-links redirect to atomic Delegation / Principles surfaces. Reviewer page shrinks to Reviewer-substance-only (Identity, Capabilities, Activity).
- `/schedule` (ADR-243) → folds into atomic Cadence surface.
- Settings page (Billing · Usage · Account) retains only billing/usage/danger-zone content; workspace governance migrates out.

### D2 — Three authorship tiers, mirroring substrate

| Tier | Substrate scope | Surface authoring | Indexed when |
|---|---|---|---|
| **Kernel** | Universal substrate (`_autonomy.yaml`, `MANDATE.md`, etc. — present in every workspace) | Platform code in `web/components/library/` (canonical files) | Always (every workspace) |
| **Program** | Bundle-shipped substrate (per-program `SURFACES.yaml`, domain folders, program-specific task slugs) | Bundle files at `docs/programs/{slug}/SURFACES.yaml` + components at `web/components/library/programs/{slug}/` | When bundle is active for the workspace |
| **Composed** | Operator/Reviewer-authored arbitrary substrate (future custom views, ad-hoc compositions) | `WriteFile` to workspace per ADR-209 (forward horizon — see §Forward horizon) | When composed surface declaration exists in workspace |

The substrate location *is* the boundary. Adding a new surface follows a deterministic test:

- Does it render substrate that every YARNNN workspace has? → Kernel surface.
- Does it render substrate that only a specific program's workspaces have? → Program surface (lives in the bundle).
- Does it render substrate that's operator-arbitrary? → Composed surface (forward horizon).

No new boundary vocabulary required; the principle is **substrate-location-determines-surface-tier**.

### D3 — Compositor as full surface registry

[ADR-225](ADR-225-compositor-layer.md)'s compositor extends from middle-component-resolver to the **full surface registry for the shell**. Specifically:

- Kernel surfaces become "default bundle" entries the compositor always emits (a `kernel` pseudo-bundle in the composition output).
- Program surfaces continue to flow from per-bundle SURFACES.yaml when the bundle is active (existing ADR-225 behavior, scope-expanded).
- The compositor's output schema gains a top-level `surfaces[]` array — flat list of all available surfaces for the workspace, each entry declaring slug, title, archetype, tier (`kernel | program:{slug} | composed`), substrate paths, icon, default-pinned-flag.
- Composed surfaces (forward horizon) register through the same schema; the compositor reads workspace-authored composition manifests in addition to bundle-shipped ones.

The shell components (dock + summon index + atomic surface routes) consume this compositor output as their single source of truth. There is no parallel surface registry in the frontend code.

**Singular Implementation discipline**: the existing `KindMiddle` switch in `WorkDetail.tsx` (the legacy compositor consumer per ADR-225 Phase 2) deletes. All surface resolution flows through the extended compositor.

### D4 — Summon-first index, not destination-based hub

The index of all available surfaces is an **overlay**, not a route.

- **Trigger**: visible icon affordance in the persistent shell chrome (top-right; canonical placement for global launchers); also voice-summonable in future (operator's note — voice deferred but the overlay is designed to be summon-source-agnostic).
- **Behavior**: opens over the current context without context-switching the underlying surface. Operator types or scrolls to find a surface, Enter or click navigates to it; Escape dismisses without effect.
- **Subtle tier grouping**: surfaces group visually by tier with small section headers (e.g. *"Workspace"* / *"Trader"* / *"Custom"*). Provenance is legible — operator sees "this surface exists because I'm running alpha-trader" — without the tier metadata feeling load-bearing.
- **Content**: every surface from the compositor's registry, scoped to the active workspace's bundles. Composed surfaces appear when present.

**No keyboard-only constraint** — the icon is the primary affordance; keyboard hotkey is a power-user enhancement, not the required entry point. (Operator preference noted: summon-first, not keyboard-first. Voice is the forward direction beyond keyboard.)

### D5 — Pinned-surface dock with Feed-only default

The shell carries a **dock** — a persistent row of always-visible surface icons.

- **Position**: bottom of viewport (desktop; canonical Dock-pattern), bottom-nav (mobile).
- **Defaults**: Feed only. Every other surface is summon-only until the operator pins it.
- **Pinning**: operator pins any surface from the index via a contextual action (long-press, right-click, or pin-button on the surface header). Pinned surfaces persist per-workspace in a `pinned_surfaces` array (likely `user_memory` or new `user_preferences` table; finalized at implementation).
- **Pin order**: drag-reorderable within the dock.
- **Discoverability**: the launcher icon (D4) is always visible adjacent to the dock; operators discover non-pinned surfaces through it.

**Rationale for Feed-only default**: operator's explicit choice. New operators see a minimal shell, discover surfaces organically through the launcher as they need them. The dock grows with operator expertise; it doesn't presuppose what matters.

### D6 — Last-used home (macOS-natural)

On workspace open, the operator lands on the **most-recently-active surface**.

- First-time operators (no surface history) land on Feed (the only default-pinned surface).
- Subsequent visits restore the surface and, where applicable, the within-surface state (selected file, scroll position — implementation-detail-level).
- The chat-first landing of [ADR-205 F1](ADR-205-workspace-primitive-collapse.md) is superseded: Feed remains the *first-time* default but not the perpetual one.

Persisted per-workspace in the same store as pinned-surface preferences.

### D7 — Shell chrome simplifies

The 4-tab nav (Feed · Work · Agents · Files) dissolves. The new shell:

- **Top chrome**: brand mark (left), launcher icon + user menu (right). No nav tabs.
- **Bottom chrome**: dock with pinned surfaces (desktop); bottom-nav-equivalent on mobile.
- **PageHeader** (per existing ADR-167 v2 amendment): retained per-surface for title + provenance + per-surface actions. Its navigation role (breadcrumb-as-mode-switch) dissolves; provenance role remains.

`web/components/shell/ToggleBar.tsx` deletes. `web/lib/routes.ts` shrinks dramatically — most top-level route constants become surface-slug references resolved through the compositor.

### D8 — Migration discipline (Singular Implementation)

This ADR enacts in **one ratification + one implementation PR** per migration phase. No dual-render, no transitional shell-chrome-coexists-with-launcher, no progressive disclosure. Either the new model is live or the old one is.

Migration phases:

- **Phase 1 — Compositor extension**: extend ADR-225 compositor schema to emit full `surfaces[]` registry including kernel surfaces. Backend-only; no frontend visible change. Surfaces are still rendered through existing routes/components.
- **Phase 2 — Shell rebuild**: top-chrome + dock + launcher land. Existing routes preserved during this PR but linked from the launcher, not the deleted nav tabs. Atomic surfaces that don't yet exist as separate routes get created (Cadence, etc.). Container surfaces (`/workspace` four-card render) atomized into their constituent atomic surfaces.
- **Phase 3 — Container deletion**: `/workspace` container, Reviewer Autonomy/Principles tabs, `/schedule` standalone surface deleted (URLs redirect to atomic equivalents). `WorkspaceConfigSection.tsx`, `ReviewerDetail.tsx`'s Autonomy/Principles branches, etc. deleted. Singular Implementation enforced — no parallel code paths.

Phase 1 is independent (ships without UX change). Phases 2 + 3 must land together for Singular Implementation discipline; deferred-deletion violates this ADR's spirit.

### D9 — Mobile follows conventional patterns

Desktop and mobile diverge on shell mechanics, converge on substrate:

| Layer | Desktop | Mobile |
|---|---|---|
| Dock | Bottom row, click-to-navigate | Bottom-nav, tap-to-navigate |
| Launcher | Overlay (modal-shaped, opens over context) | Destination route (full-screen — overlays on small viewports are anti-pattern per iOS/Android conventions) |
| Atomic surfaces | Same content, side-by-side affordances where viewport permits | Same content, full-width, stacked sections |
| Pinned defaults | Same (Feed-only) | Same (Feed-only) |

Acceptable compromises noted: mobile loses summon-on-top-of-context; gains bottom-nav muscle memory. Operator accepts this convention boundary explicitly.

### D10 — Forward horizon: composed surfaces (Thesis 2, not designed)

The substrate-mirror principle naturally extends to **composed surfaces** — operator or Reviewer-authored views that combine substrate reads, kernel components, and program components into custom dashboards. The architectural slots are reserved in this ADR (D2 tier 3, D3 compositor schema accommodates composed entries, D4 index displays composed group) but the **authoring path is not designed here**.

A future ADR — provisional title *"Composed Surfaces — Operator-Authored Views"* — will specify:
- Authoring primitive (operator chat-driven? Reviewer mid-loop? Both?)
- Persistence shape (workspace file at `/workspace/views/{slug}.yaml`? new substrate?)
- Component vocabulary (which kernel/program components are composable?)
- Discovery + sharing patterns

This ADR commits to **not blocking** that direction. Specifically: the surface registry schema (D3) accommodates a `tier: composed` entry; the launcher (D4) supports a "Custom" section; the dock (D5) accepts composed surfaces in the pinned set with no special-casing. We don't build the authoring path; we don't preclude it.

### D11 — Universal Surface Application (2026-05-21 same-session amendment)

The axiom **surface = viewport panel, not URL destination** (D1 amendment) applies *universally*. Everything operator-visible is a surface. No exceptions:

- **Chat composer is a surface** (Input archetype — writes session_messages)
- **Feed timeline is a surface** (Stream archetype — reads session_messages)
- **Dock is a surface** (Navigator archetype — renders pinned surface registry)
- **Launcher overlay is a surface** (Navigator archetype — renders full surface registry)
- **Top bar is a surface** (Chrome archetype — renders brand + launcher trigger + user menu)

What today exists as hardcoded "shell chrome" in `AuthenticatedLayout.tsx` is, under D11, a collection of surfaces mounted into named layout regions by the compositor.

**Why this matters**: the chrome-vs-content distinction is the place where "page-as-container" patterns reassert themselves under different names. A surface that's "always visible" looks like chrome; a surface that's "summon-only" looks like a modal. D11 commits that *visibility policy* is a separate concern from *what a thing fundamentally is*. Everything is a surface. Some surfaces are mounted-by-default; others are summon-only; others are always-visible in a fixed region. The shell becomes a **compositor** that reads layout policy and mounts surfaces into regions, not a fixed layout.

**Archetype catalog widens** (extends ADR-198 + the `browser`/`roster` additions already in this ADR):
- `Document` / `Dashboard` / `Queue` / `Briefing` / `Stream` (ADR-198 — content shapes)
- `Browser` / `Roster` (this ADR D1 — content shapes)
- **`Input`** (new — composer, command bar, search field; writes substrate)
- **`Navigator`** (new — dock, launcher overlay, breadcrumb; lists/dispatches surface set)
- **`Chrome`** (new — top bar, status bar, brand mark; structural framing)

**Layout regions** (where surfaces mount):
- `main` — primary content area (one surface today; multi-surface composition in D10 future)
- `top` — top-of-viewport chrome region
- `bottom-floating` — bottom-floating affordance (today: Dock)
- `bottom-fixed` — bottom-fixed input region (today: nothing; future composer home for D11 implementation)
- `floating-overlay` — modal-style overlay summoned over `main` (today: Launcher)

**Layout policy** is operator-configurable second-order. The kernel ships default policy:
- Top bar always mounted in `top`
- Dock always mounted in `bottom-floating` (pinned surfaces only)
- Composer always mounted in `bottom-fixed` (Input surface — every operator can chat with YARNNN from any surface)
- Launcher mounted in `floating-overlay` on summon
- Active atomic surface mounted in `main`

Operator preferences (future, via `useSurfacePreferences` extension) can override defaults: hide composer, move dock to right rail, etc. Layout policy is the 2nd-order concern; the universal-surface axiom is the 1st.

**Why D11 and not its own ADR**: D11 is the *logical completion* of the surface-mirrors-substrate principle (the foundational principle of this ADR). It doesn't introduce new concepts so much as remove an unprincipled exception — chrome-as-special-case. Same ADR; explicit amendment for trace continuity.

D11 implementation status: **Phases A + B + C Implemented 2026-05-21** (commits `72da5d4` A · `265042b` B · Phase C in this same session). Phase C shipped in the **safer-shape** variant — see "D11 Phase A + B + C — landed 2026-05-21" below for the divergence from the original spec and the explicit Phase C.2 follow-on scope. Phases D + E remain forward horizon.

### D12 — Top-center merged dock-bar (2026-05-21 same-session amendment)

**Supersedes** D5 §Position (Dock at bottom of viewport) + D7 §Top-chrome distribution (brand left, launcher icon + user menu right) + D7 §Bottom-chrome (Dock at bottom). Also supersedes D11 §Layout-policy line *"Dock always mounted in `bottom-floating`"*.

The Dock relocates from `bottom-floating` to `top` and merges with the prior right-side TopBar elements (launcher trigger + user menu) and the prior left-side brand mark into a **single centered top dock-bar**. Bottom-floating chrome dissolves entirely.

**Operator-visible result** — the top of every authenticated surface carries one horizontal strip with this ordering (left to right):

1. **Brand mark** (yarnnn circle icon) — clickable, navigates to last-active home (D6).
2. **Divider** (subtle vertical separator).
3. **Launcher trigger** (four-box icon) — opens the Launcher overlay (overlay itself remains in `floating-overlay` region per D11).
4. **Divider** (subtle vertical separator).
5. **Pinned surfaces** in pin order (Feed by default per D5's Feed-only commitment; more as the operator pins via the Launcher overlay).
6. **Divider** (subtle vertical separator).
7. **User menu** (avatar) — opens the existing UserMenu dropdown.

**Layout-policy revisions** (overrides D11 §Layout-policy defaults):
- Top bar always mounted in `top` — body is the merged dock-bar (above ordering).
- Dock kernel surface DELETED from the registry — its responsibility (rendering pinned-surface icons + dispatching `setSurface` on click) absorbs into the top-bar body.
- Launcher trigger no longer a separate top-right concern — it's slot #3 in the dock-bar.
- Composer always mounted in `bottom-fixed` (unchanged from D11).
- Launcher overlay still mounted in `floating-overlay` on summon (only the *trigger* moves; the overlay itself is unaffected).
- `bottom-floating` layout region survives in the type union (a future chrome surface might use it) but no kernel surface targets it.

**Rationale** — three threads:

1. **Singular Implementation**: pre-D12, two navigator regions (top-right launcher trigger + bottom-floating Dock) did adjacent jobs. D12 collapses to one. The macOS Dock analogy that D5 originally invoked is honored more precisely — macOS Finder sits leftmost in the Dock; here the launcher trigger sits leftmost (after brand) in the relocated Dock. One Navigator surface, one canonical location.

2. **Composer real estate**: ADR-297 D11 added the shell-bottom `ChatComposerSurface`. With the Dock still floating at `fixed bottom-3`, the composer needed an `h-16` breathing-room spacer below it to prevent the Dock overlaying composer controls. That wasted vertical real estate on every authenticated surface. With the Dock relocated to `top`, the composer gets the full bottom region — no spacer, cleaner shape.

3. **Visual hierarchy**: a centered top dock-bar reads as "the workspace navigation surface" — a single recognizable region. The pre-D12 split (brand-left, launcher-right, dock-bottom) scattered navigation cues across three viewport edges. Operators reported (this session, KVK 2026-05-21) the bottom-floating Dock + bottom-fixed composer competed for attention in the same viewport region.

**What D12 does NOT change**:
- Pinning behavior: operator still pins from the Launcher overlay (D5 mechanic preserved).
- Default-pinned set: Feed only (D5 commitment preserved).
- Pin persistence: same `useSurfacePreferences` localStorage path (D5 substrate preserved).
- D6 last-active-home behavior: brand-mark click still navigates to last-active surface.
- Launcher overlay shape: type-to-filter, per-row pin toggle, tier grouping — all unchanged.
- Mobile divergence: a future operator-observed pain point determines mobile shape; the top-center bar is a desktop-first decision. Mobile fallback inherits the desktop bar until mobile-specific operator pressure surfaces.

**Why D12 and not its own ADR**: same rationale as D11 — refinement of the surface-mirrors-substrate principle's layout-policy expression. D12 changes *where* the Dock surface mounts and which surface *owns* the launcher-trigger affordance; it doesn't reopen the axiom that everything is a surface. Same ADR; explicit amendment for trace continuity.

D12 implementation status: **Implemented 2026-05-21** (this session, commit follows this doc-only amendment).

---

## Implementation path for D11 — Uniform Compositor

A future session opens with this scoped plan. Each phase ships independently and is TS-clean + regression-gate-green.

**Phase A — Taxonomy + types** (~1h):
1. Extend `ARCHETYPES` enum in `api/services/kernel_surfaces.py` with `input`, `navigator`, `chrome`.
2. Add new kernel-surface declarations: `chat-composer` (Input), `launcher` (Navigator — wraps existing Launcher.tsx), `dock` (Navigator — wraps existing Dock.tsx), `top-bar` (Chrome). Each declares its default layout region.
3. Add new `LayoutRegion` enum to `web/lib/compositor/types.ts`: `main | top | bottom-floating | bottom-fixed | floating-overlay`.
4. Extend `Surface` type with `default_region?: LayoutRegion` and `default_visibility?: 'always' | 'summon' | 'pinned-only'` fields.
5. Update Phase 1 regression gate to cover new archetypes + the new chrome-surface entries.

**Phase B — Compositor & Layout** (~2h):
1. Replace AuthenticatedLayout's hardcoded JSX with a `ShellCompositor` component that reads the surface registry, partitions surfaces by `default_region`, and mounts each region's surface(s).
2. `ShellCompositor` consumes layout policy (kernel default + operator overrides) — for alpha-1, kernel default only.
3. Each chrome element (Dock, Launcher, TopBar, ChatComposer) becomes a surface component registered in `SurfaceRegistry`; the compositor mounts them via the same path as content surfaces.
4. Existing `<Dock>` and `<Launcher>` components become surface implementations; their *invocation* shifts from explicit JSX in AuthenticatedLayout to compositor-driven mounting.

**Phase C — Chat composer as Input surface** (~1.5h):
1. Extract chat composition affordance from `web/components/feed-surface/` into a standalone `ChatComposerSurface` component (Input archetype, mounted in `bottom-fixed` region by default).
2. Feed surface trims to pure Stream archetype (timeline read only).
3. Remove `ThreePanelLayout(conversation=…)` calls from all atomic surface pages — composer is shell-mounted, not per-surface.
4. Mobile divergence: composer surface declares mobile-shape (full-screen on summon; bottom-bar-summon-icon when collapsed).

**Phase D — Layout policy persistence** (~1h, optional):
1. Extend `useSurfacePreferences` with `surfaceLayoutOverrides` — per-surface region/visibility overrides.
2. Add operator-facing UI for moving/hiding chrome surfaces (right-click → "Move to right rail", etc.).
3. Persist to localStorage same pattern as `pinnedSurfaces`.

**Phase E — Multi-surface main region** (the D10 advance):
1. `main` region accepts an array of surface declarations, not just one.
2. Default layout: single-active. Split-mode + peek layouts unlock when operator demands.

Phases A + B + C are the minimum-viable D11. Phase D is operator-customization. Phase E is the D10 multi-surface advance enabled by the uniform-compositor foundation.

---

## What this ADR does NOT do

- **Does not specify the surface registry schema in detail.** Schema design lands in the Phase 1 implementation PR (compositor extension), informed by ADR-225's existing schema. ADR fixes principles, not field names.
- **Does not build composed-surface authoring.** Forward horizon only (D10).
- **Does not rename existing primitives.** All authoring primitives (`Schedule`, `ManageHook`, `WriteFile`, etc.) unchanged.
- **Does not change substrate.** Every substrate path and schema preserved. This is purely a frontend reshape.
- **Does not amend FOUNDATIONS or GLOSSARY.** No new axioms; this is the surface-layer enactment of existing axioms (1 — Substrate; 6 — Channel) and OS framing (ADR-222).
- **Does not specify cadence-surface design.** The atomic Cadence surface exists per D1's enumeration but its archetype/content/interactions are spec'd in implementation. The `cadence-and-wakes.md` canon doc already provides the substrate map; the surface design follows from it.

---

## D11 Phase A + B + C Implementation — landed 2026-05-21 (same-session)

The minimum-viable D11 stack shipped as three incremental commits, each
TS-clean and regression-gate-green. The session opened from the prompt
at `docs/design/SESSION-OPENER-ADR-297-D11.md`.

**Commit `72da5d4` — Phase A: taxonomy + chrome surfaces in kernel
registry.**
- `api/services/kernel_surfaces.py::ARCHETYPES` extends with the three
  D11 entries: `input` (writes substrate), `navigator` (lists/dispatches
  surface set), `chrome` (structural framing). Adds the four chrome
  kernel-surface declarations: `top-bar` (chrome / `top` region),
  `dock` (navigator / `bottom-floating`), `launcher` (navigator /
  `floating-overlay` / `summon`), `chat-composer` (input /
  `bottom-fixed`). Each carries a paired `default_region` +
  `default_visibility` field. Chrome surfaces are not launcher-
  navigable (`route == ""`) and not dock-pinnable.
- `web/lib/compositor/types.ts::Archetype` synced to Python — picks up
  the pre-existing D1 drift (`browser`, `roster`) and the new D11 trio.
  New `LayoutRegion` and `SurfaceVisibility` type unions. `Surface`
  interface gains optional `default_region` + `default_visibility`
  fields.
- Regression gate `api/test_adr297_phase1.py` extended: surface-count
  floor raised 10 → 17, `expected_slugs` gains the four chrome
  surfaces, two new test groups assert D11 archetype catalog +
  chrome-surface (archetype, region, visibility) tuples + paired-fields
  invariant + canonical-enum membership for regions/visibility. **120
  assertions PASS**.

**Commit `265042b` — Phase B: shell compositor dissolves chrome into
surfaces.**
- `web/components/shell/ShellCompositor.tsx` — partitions
  `composition.surfaces` by `default_region`; mounts each region's
  chrome surface(s) via `CHROME_SURFACE_REGISTRY`. The `main` region
  mounts `SurfaceViewport` (single content surface today; the D10
  multi-surface advance is forward horizon).
- `web/components/shell/ChromeRegistry.tsx` — slug → component map for
  the four D11 chrome surfaces. Distinct from `KERNEL_SURFACE_REGISTRY`
  (content surfaces) only in WHICH JSX slot the compositor mounts into;
  both come from the same kernel registry.
- `web/components/shell/ShellChromeContext.tsx` — lightweight provider
  for chrome-shared state (userEmail, launcher open/close). Chrome
  surfaces consume this instead of receiving N props through M JSX
  slots; the compositor mounts them with zero props.
- Four chrome-surface components at
  `web/components/shell/chrome/{TopBar,Dock,Launcher,ChatComposer}Surface.tsx`.
  Top bar is self-contained (brand mark + LauncherButton + UserMenu +
  D6 last-active-home navigation). Dock + Launcher are zero-prop
  wrappers around the pre-existing Dock + Launcher components — same
  bodies, just invocation moves from inline JSX to compositor mount.
  ChatComposerSurface is the Phase C target.
- `AuthenticatedLayout.tsx` shrinks 263 → 197 lines: hardcoded shell
  JSX (top header, Dock, Launcher mounts, SurfaceViewport) DELETED;
  body owns only the auth check, provider stack, NarrativeContext
  handoff machinery, and last-active-surface recording. Singular
  Implementation — no parallel mount paths.
- Validation: tsc clean, `next build` clean (all 30+ routes compile,
  bundle sizes unchanged ±1KB), regression gate 120/120 unchanged.

**Phase C (this commit) — universal shell composer (safer shape).**
- `ChatComposerSurface` body shipped: input bar, send/stop button,
  attach-file PlusMenu, CommandPicker, file/image/docx attachment
  previews, paste-to-attach, Enter-to-send. Reads workspace-global
  state from `NarrativeContext` (sendMessage, loopActive,
  stopActiveLoop) and current surface from `DeskContext`. Universal
  scope — no per-surface props (no `surfaceOverride`, `draftSeed`,
  `pendingActionConfig`, `emptyState`, `narrativeFilter`,
  `contextLabel`).
- `ShellChromeContext` gains a `composerSuppressed` flag + paired
  `useSuppressShellComposer()` hook. Surfaces that mount their own
  composer (today: /agents /context /cadence via
  `ThreePanelLayout.conversation`, plus /feed via `ConversationDrawer`)
  call the hook on mount; the shell-bottom `ChatComposerSurface`
  renders `null` while any suppressor is registered.
- `ThreePanelLayout` mounts a tiny `ShellComposerSuppressor` component
  when its `conversation` prop is set. `FeedSurface` calls
  `useSuppressShellComposer()` unconditionally (/feed owns the
  Conversation drawer affordance).
- **What this Phase C does NOT do** — the *safer shape* commitment, made
  explicit so the follow-on scope is unambiguous:
  - Per-surface `ConversationPanel` mounts on /agents /context /cadence
    are preserved verbatim. `ThreePanelLayout.conversation` prop
    survives. /feed `ConversationDrawer` survives.
  - No publish/subscribe pattern lifting `draftSeed`,
    `pendingActionConfig`, `plusMenuActions`, `surfaceOverride`,
    `contextLabel` through global context. Those per-surface
    affordances remain prop-threaded through `ConversationPanel` as
    today.
  - No deletion of `ConversationPanel`, `ConversationDrawer`, or the
    `conversation` prop on `ThreePanelLayout`.
  - **Phase C.2 (follow-on)** lifts those per-surface affordances into
    a chat-composer-intent publish/subscribe pattern on DeskContext or
    a sibling context, then deletes the per-surface `ConversationPanel`
    mounts and the `conversation` prop. Operator UX shifts at that
    point — the right-panel chat goes away on /agents /context
    /cadence, replaced by the shell composer + a separate messages-
    read surface. That UX shift is the reason Phase C.2 deserves its
    own session.

**Operational result of A + B + C**:
- Compositor mounts every chrome element from the kernel registry.
  Adding a new chrome surface in the future is a single
  `kernel_surfaces.py` declaration + a single `ChromeRegistry.tsx`
  registration; the compositor picks it up without code changes.
- Operator-visible behavior: shell composer visible at the bottom of
  every surface that doesn't own its own (today: most read-only
  surfaces — `/cockpit`, `/mandate`, `/principles`, `/identity`,
  `/brand`, `/program`, `/queue`, `/activity`, `/delegation`). The
  three rich surfaces (/agents /context /cadence) and /feed continue
  to own their bespoke chat affordance.
- Validation: tsc clean, `next build` clean, regression gate 120/120.

The D11 axiom (surface = viewport panel; chrome is not a special case)
now holds *structurally*: every chrome element is a registered surface
mounted by region. The Phase C.2 follow-on is purely about per-surface
affordance migration, not about reopening the axiom.

---

## Phases 2 + 3 Implementation — landed 2026-05-21 (same-session)

The full atomic-shell migration shipped as a sequence of incremental
commits, each TS-clean and regression-gate-green:

**Shell rebuild**:
- `web/lib/shell/surface-preferences.ts` — localStorage-backed pinned-
  surfaces + last-active-surface persistence (D5 + D6 substrate). Default-
  pinned: Feed only.
- `web/lib/shell/useSurfacePreferences.ts` — React hook over the
  persistence helpers.
- `web/lib/shell/surface-icons.tsx` — `icon_key` → lucide-react resolver.
- `web/components/shell/Dock.tsx` — persistent bottom dock of pinned
  surfaces, active-route highlight.
- `web/components/shell/Launcher.tsx` — summon-first overlay; type-to-
  filter; per-row pin toggle; subtle tier grouping (Workspace /
  <Program> / Custom).
- `web/components/shell/LauncherButton.tsx` — always-visible icon in top
  chrome (LayoutGrid).
- `web/components/shell/SurfacePage.tsx` — common content chrome for
  atomic surfaces.
- `web/components/shell/AuthenticatedLayout.tsx` — rewired. ToggleBar
  import + render REMOVED. Dock + Launcher + LauncherButton mounted.
  Last-used home behavior implemented (recordVisit on pathname change,
  resolves slug to route on logo click).

**Atomic surface routes** (10 new + 1 renamed):
- `/mandate` — MandateCard full variant
- `/delegation` — DelegationCard full variant (formerly "Autonomy" tab)
- `/principles` — PrinciplesCard full variant (formerly "Principles" tab)
- `/identity` — IdentityBrandCard (co-renders identity + brand)
- `/brand` — redirects to /identity (peer atomic, splittable later)
- `/program` — ProgramLifecycleDrawer + workspace state fetch
- `/cockpit` — CockpitRenderer (ADR-228 four-face + ADR-273 program
  sections intact; 13th kernel surface)
- `/queue` — thin placeholder pointing to Feed (richer queue view is a
  follow-on if demand surfaces)
- `/activity` — RETAINED (no change; "Manage →" deep-link updated to
  `/cadence?task=`)
- `/agents` — RETAINED (Reviewer tabs reduced — see below)
- `/cadence` — RENAMED from `/work` via filesystem move. Dashboard tab
  dissolved (cockpit content moved to `/cockpit`). Detail mode + agent
  filter + recurrence list preserved.

**Inbound-link reroutes**:
- `UserMenu.tsx` `/workspace` → `/mandate`; menu label "Workspace" →
  "Mandate"
- `auth/callback/page.tsx` first-run `/workspace?first_run=1` →
  `/program?first_run=1`
- `operation/page.tsx` `/workspace` → `/mandate`
- `CockpitHeader.tsx` `AUTONOMY_EDIT_HREF` updated from
  `/agents?agent=reviewer&tab=autonomy` to `/delegation`
- `CockpitRenderer.tsx` UnactivatedCockpitCTA `/settings?tab=workspace`
  → `/program`
- `activity/page.tsx` JobCard "Manage →" `/work?task=` → `/cadence?task=`

**Deletions** (Singular Implementation):
- `web/components/shell/ToggleBar.tsx` — 4-tab nav DELETED
- `web/app/(authenticated)/workspace/page.tsx` — container DELETED
- `web/app/(authenticated)/schedule/page.tsx` — redirect-stub DELETED
- `web/components/workspace-config/WorkspaceConfigSection.tsx` — DELETED
- `web/components/workspace-config/WorkspacePostureLine.tsx` — DELETED
- `web/components/workspace-config/` directory — REMOVED (drawer
  relocated to `web/components/library/ProgramLifecycleDrawer.tsx`)
- `AgentContentView.tsx` Reviewer `autonomy` + `principles` tabs DELETED
  (REVIEWER_TABS shrunk from 5 to 3: identity · capabilities · activity)

**Verification**:
- TS clean (`npx tsc --noEmit` exit 0 after `.next` cache reset)
- ADR-297 regression gate: 58/58 PASS (cockpit surface declared, all
  required fields present, archetype enum compliance, Feed-only default
  pin invariant)
- `composition` field preserved verbatim (Phase 1 additive contract
  honored — `surfaces[]` is the new field; existing consumers unaffected)

---

## Phase 1 Implementation — landed 2026-05-21

Phase 1 (compositor extension) shipped as a backend-only additive change with no UX impact. Specifically:

- **`api/services/kernel_surfaces.py`** (new): declares 12 canonical kernel surfaces (Feed, Cadence, Delegation, Mandate, Principles, Identity, Brand, Files, Agents, Program, Queue, Activity) with slug + title + archetype + substrate_paths + icon_key + default_pinned + route + summary. Two archetypes added to the ADR-198 catalog: `browser` (Files) and `roster` (Agents). `default_pinned: True` set only on Feed per D5.
- **`api/services/composition_resolver.py`**: `resolve_workspace_composition` extended to emit a new top-level `surfaces[]` field alongside the existing `composition` tree. Kernel surfaces always present (every workspace); program surfaces appended from each active bundle's optional top-level `surfaces:` block in its SURFACES.yaml (currently zero bundles ship the block — they will adopt during Phase 2). Bad bundle entries are logged and skipped, never raised — kernel surfaces always emit. New helper `_resolve_program_surfaces(bundles)` is the single program-tier resolver.
- **`web/lib/compositor/types.ts`**: new `Surface` + `SurfaceTier` types; `SurfacesResponse` extended with `surfaces: Surface[]`. Type-level only; no consumer migration in Phase 1.
- **`web/lib/compositor/useComposition.ts`**: `EMPTY_RESPONSE` updated with `surfaces: []` for type compatibility during pre-fetch loading state.
- **`api/test_adr297_phase1.py`** (new): regression gate, 55/55 passing. Five test groups: kernel-surfaces module hygiene, `kernel_surface_entries()` shape, empty-workspace resolver behavior, program-surface emission + bad-entry skip behavior, schema-version stability canary.

What did NOT change in Phase 1: the existing `composition.tabs` tree still drives the legacy 4-tab nav frontend. The Shell, dock, launcher, atomic-surface routes — all Phase 2 work. The shell-rebuild PR is the next session.

The frontend can read `useComposition().data.surfaces` today, but nothing renders against it yet. Validation that the compositor emits the correct surfaces[] for the operator's active workspace is now possible via direct API call to `GET /api/programs/surfaces`.

---

## Implementation outline (for the follow-on PR)

Sketch only — full PR plan accompanies Phase 1 commit:

1. **Compositor schema extension** (`api/services/composition_resolver.py`): emit top-level `surfaces[]` array with full kernel + program registry. Kernel surfaces declared in `api/services/kernel_surfaces.py` (new) or equivalent canonical location.
2. **Surface registry types** (`web/lib/compositor/types.ts`): extend with `Surface` type — slug, title, archetype, tier, substrate_paths, icon_key, default_pinned, route.
3. **Shell rebuild** (`web/components/shell/`): replace `ToggleBar` + breadcrumb-as-nav with `Dock` + `LauncherButton` + `LauncherOverlay`. PageHeader simplifies to title + provenance + per-surface actions.
4. **Atomic surface routes**: ensure every kernel surface has a route. Cadence is the largest net-new surface (consumes content from `cadence-and-wakes.md` §10 lifecycle + §11 authoring surfaces + §9 telemetry).
5. **Surface state persistence**: `pinned_surfaces` + `last_active_surface` in user preferences (`user_memory` table or new `user_preferences` per implementation review).
6. **Container deletion** (Phase 3): `WorkspaceConfigSection.tsx`, Reviewer Autonomy/Principles tab branches, `/schedule` page, related route constants — all deleted in the same PR per Singular Implementation.
7. **Cross-link updates**: every link in the codebase pointing to `/workspace`, `/agents?agent=reviewer&tab=autonomy`, `/agents?agent=reviewer&tab=principles`, `/schedule` updates to atomic-surface equivalents. Grep-and-rename pass.
8. **Mobile**: separate composition for mobile shell (bottom-nav + launcher-as-destination). Possibly a separate PR after desktop lands.
9. **CHANGELOG**: `api/prompts/CHANGELOG.md` entry if any TP prompt references container surfaces (likely none, but verify).
10. **ADR status flip**: this ADR moves from Proposed → Implemented on the PR that lands Phases 2 + 3.

---

## Companion docs to update

When this ADR ratifies:

- [`docs/design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md`](../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md) — status note added: *"Discussion converged 2026-05-21. Ratified by ADR-297."* Doc preserved as historical artifact of how the decision was reached.
- [`docs/architecture/cadence-and-wakes.md`](../architecture/cadence-and-wakes.md) — §15 item 4 (operator-visible cadence surface) crossed off with reference to ADR-297's atomic Cadence surface.
- [`docs/architecture/FOUNDATIONS.md`](../architecture/FOUNDATIONS.md) — no axiom changes. Optional: one-sentence note in Axiom 6 (Channel) section that "atomic surfaces mirror substrate concepts per ADR-297."
- [`docs/architecture/SERVICE-MODEL.md`](../architecture/SERVICE-MODEL.md) — compositor row updated to note expanded scope (full surface registry vs middle-component-resolver only).
- [`docs/design/WORKSPACE.md`](../design/WORKSPACE.md) — surface-contracts section rewritten to reflect the dock + launcher shell.
- [`CLAUDE.md`](../../CLAUDE.md) — ADR-297 summary added in the alphabetical-ADR section.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Discoverability gap for new operators** (no nav tabs, launcher needs learning) | Launcher icon always visible in shell chrome; Feed-only default ensures operators see *something* immediately; first-time onboarding can prompt "try the launcher" once |
| **Mobile divergence introduces dual-implementation risk** | Mobile follows conventional bottom-nav + destination-launcher pattern; same compositor output; only the shell render diverges |
| **Container deletion breaks bookmarks/inbound links** | URL redirects from old container routes to atomic equivalents; grep pass for code-level link updates |
| **ADR-225 compositor extension is non-trivial** | Phase 1 lands compositor change *before* shell rebuild; backend-only, no UX change, derisks the shell PR |
| **Operator confusion during migration** | Singular Implementation discipline — when the PR lands, the new model is live entirely. No half-states. Old shell deleted, new shell mounted, in one PR. |
| **Composed-surface authoring pressure surfaces before ADR ready** | D10 commits to non-blocking; if pressure surfaces early, the schema accommodates a stub Custom group with a "coming soon" placeholder |

---

## Acceptance criteria for "Implemented"

- Phase 1 (compositor extension) merged.
- Phase 2 + 3 (shell rebuild + container deletion) merged in single PR.
- No surface uses the page-as-container pattern. Every authored substrate concept has its own atomic surface.
- 4-tab nav (`ToggleBar.tsx`) deleted from `web/components/shell/`.
- `/workspace` URL redirects to launcher (or is removed if no inbound links remain).
- Reviewer page renders Identity · Capabilities · Activity only.
- Launcher icon visible in top-right of shell chrome on every authenticated route.
- Dock renders at bottom (desktop) / bottom-nav (mobile) with default Feed-pinned.
- Last-used surface persists across workspace opens.
- Operator's bookmarks pointing to old container URLs resolve via redirects.
- This ADR's status flips Proposed → Implemented in commit message.
