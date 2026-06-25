# ADR-297 — Surfaces as Substrate Mirror: Atomic Surfaces, Summon Index, Compositor as Registry

> **Status:** Implemented (2026-05-21, same-session clean-slate migration)
> **Amendment (2026-05-21 same-session, pre-Phase-2-implementation):** D1 kernel surface list extended from 12 to 13 entries with the addition of `cockpit` (Dashboard archetype). Resolves an ambiguity the deletion-scope audit surfaced: `/work` today hosts cockpit rendering (ADR-228 four-face stack via `CockpitRenderer`) inside its dashboard tab. Clean-slate migration dissolves `/work` entirely — recurrence list folds into Cadence, task detail becomes drill-down from Cadence (`/cadence/{slug}`), and cockpit rendering relocates to its own atomic Cockpit surface. The 13th kernel surface honors substrate-mirrors-surface for the cockpit-as-substrate-read concept that ADR-228 already established; no rewrite of `CockpitRenderer`, just relocation.
> **Amendment (2026-05-22 — [ADR-300](ADR-300-pace-as-atomic-kernel-surface.md)):** D1 kernel surface list extended from 15 to 16 with the addition of `pace` (Document archetype). Closes the asymmetry where Delegation (`_autonomy.yaml`) and Mandate (`MANDATE.md`) had atomic surfaces but Pace (`_pace.yaml`) — the Trigger-dimension dial of the canonized ADR-298 D11 trifecta — did not. Slotted between `cadence` and `delegation` to keep Trigger-dimension surfaces adjacent before transitioning into Mechanism (Delegation) and Identity (Identity / Brand / Principles) per axiom order. PaceBadge on the Cockpit becomes a read-only deep-link to `/pace`; no other surface changes.
> **Amendment (2026-06-23 — [ADR-358](ADR-358-layout-mode-canvas-vs-desktop.md)):** the D15 free-floating window manager (cascade · drag · 4-edge resize · z-stack · soft-cap-8) is now the **Desktop layout mode** — one of two operator-chosen spatial paradigms. The other, **Canvas mode** (the default), renders exactly **one** full-bleed surface (the foregrounded `visibleSlug`) with window chrome suppressed, filling the column with chat docked as a right-side rail — the chat-interface convention. Canvas reuses `SurfaceViewport`'s existing single-surface branch (gated on `viewport.isMobile || canvasMode`); the multi-window manager is untouched and active in Desktop mode. In Desktop, chat is a summoned `position: fixed` overlay (not a pinned rail — ADR-358 D3), so the desktop genuinely floats. The window-manager core (`useSurfacePreferences`) is deliberately mode-agnostic — the seam is clean.
> **Amendment (2026-06-25 — [ADR-370](ADR-370-context-surface-the-operations-boundary.md)):** the kernel surface registry gains a **composition** surface, `context` (Dashboard archetype, `launcher_tier: primary`) — the operation's boundary (In · Out · Flow). The `feed` mirror folds into it as the Flow lens: `feed` stays in the registry (the Flow body) but drops to `default_pinned: False`, its launcher slot inherited by `context`; the `/feed` route becomes an ADR-308 redirect stub → `/context?context.pane=flow`. Net top-level surfaces unchanged (Context replaces Feed's slot, not adds to it). This is the third composition (after Home and Notifications) — surfaces remain mirrors-or-compositions; the registry is still the single source of truth.
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

D12 implementation status: **Implemented 2026-05-21** (commit `f52ac39` enacts the doc-only `bcd8d08`).

### D13 — Surfaces are windows: multi-mount lifecycle, desktop boot, open-state Dock (2026-05-21 same-session amendment)

**Refines** D6 (last-active home — same-session amendment). **Brings forward** D10's "multi-surface main region" partial — the multi-mount lifecycle clause lands; the "split-mode + peek" viewport composition stays forward horizon.

D11 + D12 made the structural claim that *every operator-visible thing is a surface*. D13 takes the metaphor one step further: **surfaces are application windows in a macOS-like Dock metaphor**. Specifically:

- A surface, once opened, **stays mounted** in the React tree (lifecycle decoupled from "currently foregrounded"). Closing is an explicit affordance.
- The Dock (the top-center dock-bar per D12) shows **open-state indicators** — a small dot under each pinned icon signals "this surface has a live mount." Clicking an open surface's icon **foregrounds** it (brings its mounted tree into the visible viewport). Clicking a not-yet-open surface **mounts** it.
- **No default surface on cold start**. First-time operators (no surface history) boot to the **desktop** — a deliberately-empty viewport with the top-center dock-bar visible and an empty-state prompt ("click an icon to begin"). Returning operators boot to their last-active foregrounded surface (D6 refined — preserved for the returning-operator path, supplemented for the first-time path).

**Why the metaphor was incomplete before D13**: D5 + D11 + D12 modeled the Dock visually as a macOS Dock, but the behavior under the hood was browser-tab-shaped — `setSurface` dispatch unmounted the prior surface and mounted the new one. Operators reading the Dock metaphor expected window-manager behavior (state persistence, foreground/background, multiple-open simultaneously). The visual cue (Dock with persistent pinned icons) and the runtime behavior (replace-on-dispatch) disagreed. D13 resolves the disagreement by changing the runtime behavior to match the metaphor.

**Concrete commitments**:

1. **Surface-mount lifecycle is multi-mount.** When the operator opens a content surface (Dock click, Launcher selection, or programmatic `setSurface`), the compositor mounts it. The prior foregrounded surface **stays mounted** but is hidden via `display: none` (or `hidden` attribute — TBD at implementation). All open surfaces stay in the React tree until explicitly closed.

2. **Open-surfaces registry.** A new `useOpenSurfaces()` hook (or DeskContext extension) tracks the ordered set of currently-open surface slugs + the foregrounded slug. The compositor reads this registry and renders every open surface in `main`, applying `display: none` to all but the foregrounded one.

3. **Foreground = the visible surface.** Exactly one open surface is foregrounded at any time. `setSurface` semantics change: if the target surface is already open → foreground it (no remount); if not open → open and foreground it.

4. **Close affordance.** Right-click (or long-press) on a Dock icon shows a contextual menu with "Close." Close removes the surface from the open-surfaces registry and unmounts it. If the closed surface was foregrounded, foreground falls through to the next-most-recently-foregrounded open surface; if no other surfaces are open, fall through to the desktop.

5. **Desktop empty state.** When the open-surfaces registry is empty (cold start for first-time operators, or after closing the last open surface), the compositor renders a **desktop surface** in `main`. The desktop is not in the kernel registry — it's the *absence* of any open surface, plus an inviting empty-state prompt anchored to the Dock. A future ADR may promote the desktop to a first-class kernel surface (with operator-customizable wallpaper, pinned-files, etc.); D13 ships the minimal version: empty viewport with the Dock visible and one line of empty-state copy.

6. **D6 refined, not superseded.** Returning operators (with a non-empty open-surfaces registry persisted from prior session) boot to the foregrounded surface from that session. First-time operators (empty registry) boot to the desktop. The "last-active surface" concept survives within the open-surfaces registry — it's the most-recently-foregrounded slug, persisted alongside the registry itself.

7. **Open-state indicator dot in the Dock.** Each pinned Dock icon shows a small dot below it when the corresponding surface is currently in the open-surfaces registry. macOS Dock convention. Visual only — clicking semantics already covered by D5/D12.

8. **Open-but-not-pinned surfaces in the Dock.** A surface can be open without being pinned (operator opened it from the Launcher; didn't pin). Per macOS convention, open-but-not-pinned surfaces appear in the Dock to the right of the pinned set, separated by a divider, until closed. They disappear from the Dock on close. (D13 v1 implementation may defer this to a follow-on tick — minimum-viable D13 ships open-state dots on *pinned* icons only; the open-but-not-pinned tail follows.)

**Persistence**:
- Open-surfaces registry persists per workspace via `useSurfacePreferences` (extends the localStorage path) — same store as pinned-surfaces and last-active.
- Each entry stores `{slug, openedAt}`; foreground tracked separately as `foregroundedSlug` for fast resolution.
- Persistence captures the *fact* that a surface is open; it does NOT capture per-surface transient state (scroll position, form drafts, etc.). Surface state persistence is a per-surface concern — D13 ships the lifecycle plumbing; state retention within a surface is the surface's own job. (For the alpha-1 operator, most surfaces are substrate-backed reads, so state persistence is automatic via re-read.)

**Memory budget**: full macOS-literal multi-mount is bounded by the kernel surface count + a small program-surface contribution (today: 13 + ≤3). React tree of ~15 hidden surfaces is acceptable for desktop browsers; if a surface proves heavy (Cockpit with its 7 trader sections; Files with its tree) we'll add per-surface memoization or virtualization. **No LRU cache, no eviction heuristic** — the open-surfaces registry is operator-authored, not memory-managed. Operators close what they don't want; that's the contract.

**Why D13 and not its own ADR**: same rationale as D11/D12 — refinement of the surface-mirrors-substrate principle's *layout-policy + lifecycle* expression. D13 doesn't reopen the axiom; it refines how the compositor mounts content surfaces (one-at-a-time → multi-mount with foreground/background). Same ADR; explicit amendment for trace continuity.

**What D13 does NOT do**:
- Does not introduce split-mode / peek layouts in `main` (still single-foregrounded; D10's full multi-surface viewport stays forward horizon).
- Does not introduce a keyboard switcher (cmd-tab equivalent) — operator demand can pull it forward; not in v1.
- Does not promote the desktop to a kernel surface with first-class wallpaper/pinned-files affordances — minimum-viable empty state only.
- Does not change pinning mechanic, Launcher overlay shape, composer surface behavior, or chat composer suppression rules.
- Does not change atomic-route bookmark-safety (`/cadence`, `/mandate`, etc. still hydrate DeskState on cold load; they just *open* the surface into the open-surfaces registry rather than replacing the prior one).
- Does not block any surface from being closed (every open surface can be closed; the desktop empty state is a legitimate destination).

D13 implementation status: **Implemented 2026-05-21** (this session, code commit follows this doc).

### D14 — Window chrome + Keep-in-Dock semantic (2026-05-21 same-session amendment)

**Supersedes** D5 §Defaults + D5 §Pinning mechanic (the "pinned" concept dissolves; "kept" replaces) and **dissolves** D13 §8 (the open-but-not-pinned-tail follow-on — its rationale gets absorbed into the unified Keep/Open Dock model).

D13 made surfaces multi-mount and gave each a foreground/background lifecycle, but the operator-visible affordance kept the pre-D13 page-as-container appearance: when a surface foregrounded, it filled the viewport edge-to-edge with no visual indication it was a window. The Dock continued to show only "pinned" surfaces — a concept independent of "open" — which made open-but-not-pinned surfaces invisible to the Dock entirely. Both gaps were operator-observed (KVK 2026-05-21) immediately after D13 shipped: *"now, when i click on the surfaces, aren't i suppose to see the windows? […] and thus, the pin concept is fundamentally mis aligned now."*

D14 closes both gaps with one coherent move. Two parts, locked together because they are coupled (the window's close affordance interacts with Dock semantics; the Dock's contents reflect window lifecycle).

**Part 1 — Pure window chrome.**

Every open content surface mounts inside a visible window frame:
- **32px title bar** at the top of the frame. Left: surface name (e.g. "Feed", "Cockpit", "Delegation"). Right: × close button.
- **Subtle border** (1px) + rounded corners around the entire frame.
- **Inset from the desktop edges** — the window doesn't extend to the viewport edge; there's a small breathing margin (the visible "desktop wallpaper" border, in macOS parlance).
- **Surface body** mounts below the title bar. The per-surface `PageHeader` (which today renders breadcrumb + per-surface actions) continues to render inside the body, unchanged. The window title bar shows the *surface name*; the PageHeader shows *subtitle + actions*. Minor visual redundancy (the name appears twice — once in window title, once in PageHeader) is the price for not invading every surface's existing chrome. Future v2 may collapse them; D14 ships the minimum surgery.

The desktop empty state (D13 §5) continues to render edge-to-edge with no window frame (there is no window).

**Part 2 — Pin reframed as Keep-in-Dock.**

The "Pinned" concept that lived in D5 + D11 + D12 + D13 is dissolved entirely. "Keeping" replaces it, with cleaner semantics:

- **The Dock shows the union of (kept surfaces) + (open surfaces).** No separation between rails; a single canonical row.
- **Kept** is the operator's "I want this in the Dock permanently" declaration — the macOS "Keep in Dock" semantic. Persists across sessions.
- **Open** is the runtime "this surface has a live mount" state, tracked in the open-surfaces registry from D13.
- A Dock icon's appearance reflects its combined state:
  - **Kept + Open** — solid icon, indicator dot, persists across sessions.
  - **Open + Not-Kept** — solid icon, indicator dot. Disappears from Dock when closed.
  - **Kept + Not-Open** — muted/gray icon, no indicator dot, persists. Click opens.
- **Right-click menus** reshape to the new model:
  - Open + Kept → "Close" / "Remove from Dock"
  - Open + Not-Kept → "Close" / "Keep in Dock"
  - Kept + Not-Open → "Open" / "Remove from Dock"

**Default-kept set**: `['feed']` (preserves the D5 rationale verbatim — first-boot operators see one anchor in the Dock; every other surface enters the Dock when first opened and stays only if explicitly Kept). The slot is renamed from `pinned-surfaces` to `kept-surfaces` in localStorage; no migration shim per Singular Implementation discipline.

**API rename** (atomic):
- `useSurfacePreferences().pinned` → `.kept`
- `.pin(slug)` → `.keep(slug)`
- `.unpin(slug)` → `.release(slug)`
- `.isPinned(slug)` → `.isKept(slug)`
- localStorage key prefix `yarnnn:shell:pinned-surfaces:` → `yarnnn:shell:kept-surfaces:`
- Default constant `DEFAULT_PINNED_SURFACES` → `DEFAULT_KEPT_SURFACES`

The Launcher's per-row pin/unpin toggle becomes a keep/release toggle; the icon stays the same (a pin), the verb shifts. The Launcher is no longer the primary keep affordance — operators are expected to discover Keep-in-Dock via right-click on an open Dock icon — but the Launcher's pin toggle survives as a power-user shortcut.

**Why D14 and not its own ADR**: same rationale as D11/D12/D13 — refinement of the surface-mirrors-substrate principle's layout-policy expression. D14 doesn't reopen the axiom; it brings the visual and the semantic into alignment with the macOS-window-manager metaphor D13 declared. Same ADR; explicit amendment for trace continuity.

**What D14 does NOT do**:
- Does not introduce window drag-to-resize or drag-to-reposition. Windows are full-bleed within their inset; one window foregrounded at a time. Split-mode / peek / tile layouts remain forward horizon (the D10 advance).
- Does not absorb the per-surface PageHeader into the window title bar. PageHeader keeps its breadcrumb + actions role inside the surface body. A future ADR may collapse them when operator pressure justifies it.
- Does not change the Launcher overlay's primary affordance shape (type-to-filter + tier grouping + per-row keep toggle). Only the verbiage shifts (pin → keep).
- Does not change the chat-composer suppression rules, atomic-route bookmark-safety, or any aspect of D11/D12 chrome architecture.

D14 implementation status: **Implemented 2026-05-21** (this session, code commit lands together with this doc per the single-combined-commit cadence locked in question Q2 of the D14 design discourse).

### D14.1 — Shared registry context + Launcher Keep-toggle removal (2026-05-22 patch)

**Bug-fix amendment** following operator observation that the Dock failed to show open-but-not-kept surfaces (a misalignment with the D14 §"Dock = kept ∪ open" semantic). Two coupled corrections:

**Correction 1 — single source of truth for surface preferences.**

Pre-D14.1 every consumer of `useSurfacePreferences` held its own local `useState` for `(kept, open, foregrounded)`. TopBarSurface and SurfaceViewport mounted as siblings; each call to `useSurfacePreferences` allocated its own registry instance. A write through one (e.g., AuthenticatedLayout's pathname watcher calling `foregroundSurface`) updated only that one's local state — the Dock's `open[]` slice stayed stale at `[]`, so newly-opened surfaces never appeared in the Dock.

D14.1 lifts the state into a `SurfacePreferencesProvider` Context mounted in AuthenticatedLayout. Every `useSurfacePreferences` call now reads from + writes through the same context value. The Dock correctly reflects `kept ∪ open` as D14 specified.

**Correction 2 — Launcher Keep-toggle deleted.**

Pre-D14.1 the Launcher overlay carried a per-row pin/keep toggle, and the Dock right-click menu carried a Keep/Remove action. Two affordances for the same Keep operation. macOS doesn't work this way — Launchpad has no pin affordance; Keep is exclusively a Dock right-click action discovered after using an app.

D14.1 deletes the per-row Keep toggle from the Launcher entirely. The Launcher becomes pure launch: click → open + foreground. Keep is exclusively a Dock-right-click action. Singular Implementation: one Keep affordance.

The Launcher's prop surface shrinks accordingly: `kept`, `onKeep`, `onRelease` props deleted. The `Pin` / `PinOff` icon imports are dropped. `LauncherSurface` wrapper simplifies to read only `foregroundSurface` from the hook.

**Why D14.1 and not D15**: this is a correction to D14's enactment, not a new architectural decision. D15 (forthcoming this same session) is the multi-window manager amendment — independent concern, much larger scope.

D14.1 implementation status: **Implemented 2026-05-22** (this session, single commit).

### D15 — Window manager (multi-visible, draggable, resizable, z-stacked) (2026-05-22 same-session amendment)

**Brings forward** D10 §"main region accepts an array of surface declarations, not just one. Default layout: single-active. Split-mode + peek layouts unlock when operator demands" — operator pulled this forward 4 commits after D13. Pre-D15 the multi-mount lifecycle was real but only ONE window was visible at a time; D13+D14 shipped a tabbed shell with window chrome painted on, not a window manager.

D15 ratifies the full macOS/Windows window-manager model: multiple windows visible simultaneously, each independently positioned + sized + z-stacked, with operator-controllable drag + resize + raise-on-click + close.

**Locked decisions** (operator-confirmed in the D15 design discourse, 2026-05-22):

1. **Window arrangement — cascade always.** Every newly-opened window opens at a default size (70% × 70% viewport) and is cascaded +30px right/down from the last-opened window's position. macOS-default. Wraps back to top-left when cascade reaches viewport edge. First window opens at the cascade origin (default offset from desktop top-left, not auto-maximized).

2. **Mobile breakpoint — <640px is single-window.** Phones (<640px) collapse to single-window UX: full-screen current window (within the desktop padding), drag/resize/overlap disabled, switch via Dock click. Tablets (640px+) and desktop get full multi-window. Window chrome (title bar + close ×) still visible at every viewport for consistency.

3. **Performance cap — soft cap at `MAX_OPEN_WINDOWS` (8) open windows.** ~~Opening a 9th surface shows a prompt: "You have 8 windows open. Close one before opening this." Cap is operator-visible; no automatic LRU eviction (state-loss surprise is worse than explicit cap).~~ **Amended 2026-06-25 (ADR-369 follow-on) — the cap RECEDES, it does not REFUSE.** The original refusal-prompt was the one move ADR-340 DP29 forbids: a primary act (clicking a launcher/Dock surface) is never blocked. Two premises also shifted — the surface census collapsed (ADR-340/346/349: only ~10 window-grade surfaces remain; the rest are panes-in-windows or chrome, none of which count), so 8 now sits at ~80% of the openable set; and the refusal counted the *persisted* `open[]` array, so 8 stale windows from a prior session blocked navigation on a fresh load. New behaviour: opening past the cap **auto-recedes the least-recently-used window** — the lowest-z OPEN window excluding the foregrounded one (z is the recency signal; the operator never loses the window they're looking at), via the existing `closeSurfaceWrite`. The original "state-loss surprise" objection is moot: surfaces are substrate-backed (a receded window re-fetches cleanly on reopen; only its geometry is dropped, then cascades fresh). The cap is now a pure perf ceiling on simultaneously-mounted React trees. Enforced in `useSurfacePreferences.foregroundWindowGrade`; the `capHit`/`clearCapHit` plumbing + the blocking toast are deleted (Singular Implementation). Gate: `api/test_window_cap_lru_recede.py`.

4. **Z-stacking — click anywhere in a window raises it.** macOS-default raise-on-click. Click in any part of any window (body or title bar) → that window becomes foreground (z-index raised to top). The DeskContext `foregrounded` slug updates accordingly.

5. **Window buttons — close × only.** No minimize, no maximize. Rationale: (a) D13 multi-mount already preserves state for hidden windows, so "minimize" would duplicate the concept; (b) maximize is unnecessary in cascade-arrangement where windows already default to 70%×70% — operator can drag to maximize manually if they want full-bleed.

6. **Title-bar = drag handle.** Click anywhere in the title bar (not on the × button) + drag → moves the window. macOS-default.

7. **Resize handles on all four edges + four corners** (8 handles). Cursor-style hints (`ew-resize`, `ns-resize`, `nesw-resize`, `nwse-resize`) on hover. Drag from any edge/corner resizes the window with the opposite edge/corner anchored.

8. **Dock click semantics extend.** Click a Dock icon (kept or open):
   - If surface is NOT open → open + foreground (cascade-positioned).
   - If surface IS open and NOT foregrounded → raise it to foreground.
   - If surface IS open and IS foregrounded → **hide** (send to background; window stays mounted but `display: none`'d). macOS hidden behavior — clicking the active app's Dock icon hides it.

**Window state per surface** (persisted to localStorage alongside open + kept + foregrounded):
```
{
  slug: string;
  x: number;       // viewport-relative pixel position of top-left corner
  y: number;
  width: number;
  height: number;
  z: number;       // z-index (relative ordering among open windows)
}
```
- One row per slug in `kept ∪ open` (kept-not-open windows persist their last-used arrangement so Re-Open lands them where they were).
- Stored in a single localStorage key: `yarnnn:shell:window-state:{userId}`.
- Initial state: cascade-derived defaults from viewport size.

**Bounds clamping**: window position bounded so the title bar is always at least partially visible (drag past viewport edge → snap-back). Window size bounded by minimum dimensions (320 × 240) and maximum (viewport - 32px padding). Resize past min/max → clamp.

**Why D15 and not its own ADR**: same rationale as D11/D12/D13/D14/D14.1 — refinement of the surface-mirrors-substrate principle's layout-policy expression. D15 doesn't reopen the axiom; it advances the `main` region's mount semantics from "render-N-windows-but-show-1" to "render-N-windows-show-all-at-their-positions." Same ADR; explicit amendment for trace continuity.

**What D15 does NOT do**:
- Does not introduce snap-to-half / snap-to-quarter productivity gestures. Pure drag/resize only. Future v2 may add snap zones.
- Does not introduce a maximize button or keyboard shortcut (F-key, ⌘↑, etc.). Operator drags to full-bleed manually.
- Does not introduce window minimize-to-dock as a distinct state (no minimize button). Hide-via-dock-click of foregrounded window is the lightweight alternative.
- Does not introduce window-grouping / spaces / virtual desktops. One desktop, N windows.
- Does not introduce keyboard switcher (cmd-tab equivalent). Mouse + Dock only.
- Does not introduce window-thumbnail previews (Mission Control). Far forward horizon.
- Does not implement focus-stealing prevention beyond click-to-raise. New windows raise to top on open (assumed deliberate).

D15 implementation status: **Implemented 2026-05-22** (this session, code commit lands together with this doc per the same combined-commit cadence as D14).

### D16 — Universal summon chat drawer (2026-05-22 same-session amendment)

> **AMENDED by [ADR-316](ADR-316-chat-as-dockable-rail.md) (2026-06-04):** the chat-drawer's *spatial mounting* changes — region `floating-overlay` → `main-rail`, `position: fixed` overlay → flex sibling of `SurfaceViewport` inside `main`. Opening chat now *reduces* the surface area instead of occluding it, so the `Viewing: X` label (D16 §5) is honest. D16 §5's `surfaceOverride` ↔ `foregrounded` ↔ `Viewing:` binding is **preserved and strengthened** (the occlusion that undermined it is gone). On mobile (<640px) the overlay survives — split is impossible there. Read D16's `floating-overlay` / "floats over whichever window is foregrounded" language as superseded by the rail model; everything else (one FAB, one drawer, universal, DeskContext→`foregrounded` context) stands.

**Supersedes** D11 §Layout-policy line *"Composer always mounted in `bottom-fixed` (Input surface — every operator can chat with YARNNN from any surface)"* and **dissolves** D14.1's `useSuppressShellComposer()` machinery in full. Also dissolves the legacy `ConversationDrawer` on /feed (its responsibility absorbs into the universal drawer). Finishes the D11 Phase C.2 follow-on that was outstanding.

D11 through D15 left three distinct chat affordances in the codebase, each operating under different rules:
- `ChatComposerSurface` at `bottom-fixed` (D11 Phase C universal write path)
- `ConversationPanel` right panels on /agents /context /cadence via `ThreePanelLayout.conversation` (legacy from ADR-289, preserved under Phase C safer-shape via `useSuppressShellComposer`)
- `ConversationDrawer` slide-over on /feed (ADR-289)

Operator-observed (KVK 2026-05-22): *"some surfaces seem to show the bottom chat while others don't […] we need a singular, streamlined philosophy."* The fragmentation was real. Three write paths, three places, no predictable behavior across surfaces.

D16 collapses to one. The /feed Talk-button-and-drawer pattern that ADR-289 already proved (the operator already knows the shape; it works on mobile via full-screen takeover; it preserves window real estate when closed) generalizes from `/feed`-only to **universal shell chrome**: one FAB visible on every surface, one drawer that hosts the composer + addressed-conversation timeline.

**Decisions**:

1. **One FAB** at viewport **bottom-center**, fixed position, z-stacked above windows. Reclaims the `bottom-floating` region D12 vacated, for a different purpose (chat-summon, not pinned-surfaces). Icon: `MessageCircle` (lucide), 48px circle with subtle shadow. Filled when the drawer is open; outline-style when closed.

2. **One drawer**, slide-over from the right. Drawer body (top to bottom):
   - Persona header (yarnnn circle icon + persona name + "Conversation" subtitle + close ×)
   - Scrollable addressed-conversation timeline (`pulse='addressed'` filter, same as existing ConversationPanel scoping)
   - Composer input at bottom (textarea + plus menu + send / stop button + command picker `/` prefix + attachments preview)
   Drawer width: default 400px, resizable 320–720px via left-edge drag handle (persists localStorage key `yarnnn:shell:chat-drawer-width:{userId}`). Mobile (<640px): full-screen takeover.

3. **Universal** — every surface gets the same FAB + drawer. No per-surface variation, no special /feed behavior, no per-window mounting. The drawer floats over whichever window is foregrounded (D15 multi-window unchanged).

4. **`chat-drawer` kernel surface** replaces `chat-composer` in the kernel registry. Archetype: `input`. `default_region: floating-overlay`. `default_visibility: summon`. The compositor mounts it once in the floating-overlay region; the FAB is rendered by the surface itself, the drawer body is rendered conditionally on `drawerOpen` from `ShellChromeContext`.

5. **Per-surface context** flows through DeskContext, not through props. The drawer reads the current `DeskState.surface` (atomic slug + params) and passes a `surfaceOverride: { type: 'atomic', slug }` to the underlying composer so YARNNN knows "the operator is asking about Cadence" when they summon chat from /cadence. The old per-surface `draftSeed` / `pendingActionConfig` / `plusMenuActions` / `contextLabel` props from `ConversationPanel` are NOT re-introduced via DeskContext — they were never essential; they were affordances added per-surface ad-hoc. Operators who want those affordances back can request them and we'll add specific extensions to DeskContext at that time.

6. **Deletions** (Singular Implementation discipline):
   - `web/components/shell/chrome/ChatComposerSurface.tsx` — DELETED (replaced by `ChatDrawerSurface`)
   - `web/components/feed/ConversationDrawer.tsx` — DELETED (responsibility absorbed)
   - `useSuppressShellComposer()` hook + `composerSuppressed` flag in `ShellChromeContext` — DELETED (nothing to suppress)
   - `ThreePanelLayout.conversation` prop + the right-panel ConversationPanel mount + the inline FAB inside ThreePanelLayout — DELETED
   - `FeedSurface`'s `drawerOpen` state + `ConversationDrawer` import + chip-click-opens-drawer wiring — DELETED
   - `bottom-fixed` layout-region mounting in `ShellCompositor` — DELETED (region survives in the type union for future use)
   - `useSuppressShellComposer` import in FeedSurface — DELETED

7. **What stays unchanged**: `ConversationPanel.tsx` keeps its composer + timeline body — it remains the canonical chat-UI component. The universal drawer mounts a ConversationPanel inside its body, same pattern the legacy `/feed` ConversationDrawer used. NarrativeContext, session_messages, sendMessage all unchanged. D14 Keep/release Dock semantics unchanged. D15 window-manager unchanged.

**Rationale — why FAB + drawer instead of bottom-strip**:

(a) **Window real estate**: the D11 Phase C bottom strip ate ~96px of viewport height on every surface. Cockpit (with its 7 trader sections), Cadence (with its task list), and Files (with its tree) all benefit from getting that height back.

(b) **Architectural consistency with D14.1**: D14.1 collapsed two affordances (Launcher per-row Keep toggle + Dock right-click Keep) into one summon-style affordance (Dock right-click only). D16 applies the same pattern to chat: three persistent-or-semi-persistent composers collapse into one summon-style drawer. The shell's design language becomes consistent — every persistent UI element is justified against "could this be summon-style instead?"

(c) **Mobile-natural**: FAB + slide-over is the canonical mobile pattern. The legacy bottom-strip composer was awkward on mobile (it competed with the OS keyboard for vertical space). The drawer takes full-screen on mobile — dedicated chat surface for the duration the operator is writing.

(d) **/feed-proved**: the FAB + drawer pattern is already in the codebase and operator-tested on /feed via ConversationDrawer. D16 doesn't invent; it generalizes.

**Why D16 and not its own ADR**: refinement of the surface-mirrors-substrate principle's *layout-policy* expression. D16 changes WHERE the Input surface mounts and HOW it's summoned, not WHAT it fundamentally is (still an Input archetype surface). Same ADR; explicit amendment for trace continuity.

**What D16 does NOT do**:
- Does not add keyboard shortcut to summon (⌘K or similar). FAB-click only. Future ADR may add keyboard summon.
- Does not add unread-indicator dot on the FAB. Visual signal for "addressed message arrived while drawer was closed" deferred until operator-observed pain.
- Does not change the chat surface itself (the `feed` kernel surface — read-only timeline). /feed remains a content surface; the conversation drawer is the chat affordance summoned from any surface including /feed.
- Does not introduce per-window composers (Direction D from the design discourse — rejected as too much complexity for too little gain).
- Does not preserve the per-message `onMakeRecurring` callback that the legacy `/feed` ConversationDrawer plumbed into ConversationPanel. The in-line "Run this on a schedule" affordance on addressed messages disappears as a temporary regression. Operator can still graduate messages to recurrences via direct chat ("run this on a schedule"). A follow-on may relocate the affordance to a per-message right-click menu (consistent with the D14 Dock right-click pattern) — but D16 leaves the affordance off rather than threading a per-surface prop through the universal drawer (which would re-introduce exactly the per-surface coupling that D16 collapses).

D16 implementation status: **Implemented 2026-05-22** (this session, code commit lands together with this doc per the same combined-commit cadence as D14/D15).

### D17 — Desktop as load-bearing layer + Agent OS boot model + FAB-on-desktop (2026-05-22 same-session amendment)

**Supersedes** the pre-D11 `HOME_ROUTE = "/feed"` boot convention (auth callback + middleware now redirect to `/desktop`). **Refines** D13 §5 (the prior "Desktop empty state" framing — D17 ratifies Desktop as an always-rendered layer, not just an empty-state component). **Refines** D16 §1 (FAB position — was viewport-fixed `bottom-center`; D17 moves it inside the Desktop wrapper so it lives on the desktop layer, not on top of windows).

Three coupled corrections that fix an architectural confusion the operator surfaced (KVK 2026-05-22): *"I'm confused — shouldn't the FAB be not on the actual surfaces, but on the 'desktop'?"* Followed by: *"What exactly do we call the layout I'm referring as 'desktop' here? Isn't it the empty state where 0 surfaces are 'opened'? Tell me if this is clearly identifiable and do-able in code."* And then: *"Maybe the framing needs to think in terms of what page/redirect we go to when we log in — and thus what IS our Agent OS metaphor that correctly applies this desktop concept."*

The audit traced the confusion to two structural issues:

1. **`HOME_ROUTE = "/feed"` was a relic from the pre-D11 single-page world.** Login auth-callback forced every operator (first-time + returning) onto `/feed` → pathname watcher fired → Feed surface auto-opened into a window. No operator ever saw the empty desktop. The macOS metaphor we ratified in D14/D15 was defeated on Day 1 of every operator's experience.

2. **"Desktop" was two different things in code:** (a) the `<Desktop />` component rendered ONLY when zero windows open, and (b) the padded gray `bg-muted/30 p-3 sm:p-4` wrapper rendered ONLY when ≥1 windows open. ADR prose used "desktop" loosely for both; code had no shared name. The two paths had no continuity — different content, different conditions, never visible simultaneously.

**D17 ratifies the YARNNN Agent OS boot model**: YARNNN is a macOS-window-manager OS. Login boots to the Desktop. Last-session windows restore automatically. The Desktop is a single always-rendered layer that exists at all times; windows float above it. The Desktop is load-bearing.

**Decisions**:

1. **Desktop = the always-rendered persistent background layer of the authenticated viewport.** Visible wherever windows don't cover it. Renders empty-state copy as a conditional child when no windows are open; renders windows as conditional absolute-positioned children on top. ONE wrapper in SurfaceViewport, not two paths.

2. **Authenticated boot URL is `/desktop`.** New `web/app/(authenticated)/desktop/page.tsx` route. `HOME_ROUTE` constant updates from `"/feed"` → `"/desktop"`. Auth callback + middleware redirects target `/desktop`. The marketing landing at `/` stays public (Next.js `app/page.tsx` unchanged).

3. **Per-slug routes survive as deep-link transports.** `/feed`, `/cadence`, `/mandate`, etc. continue to work — cold-load to them opens that surface, foregrounds it (existing AuthenticatedLayout pathname watcher behavior). Bookmark-safety + shareability preserved. Only the **default** boot changes — operator landing on `/desktop` with non-empty registry sees their restored session; operator landing on `/desktop` with empty registry sees the empty Desktop.

4. **Last-session restore is automatic.** The open-surfaces registry persisted by D13 is now actually load-bearing. SurfaceViewport reads `useSurfacePreferences().open` on mount; windows hydrate with their persisted geometry from `windowStates`; the previously-foregrounded slug regains foreground. Operator who had Cockpit + Cadence + Mandate open yesterday sees the same arrangement today.

5. **Context-aware Desktop empty-state copy.**
   - **First-time operator** (no localStorage entries — `kept`, `open`, `foregrounded`, `windowStates` all default-empty): "Welcome to YARNNN. Click the launcher (grid icon ↑) above to see all surfaces, or click any pinned icon in the top dock." Subtle arrow/indicator pointing at the launcher.
   - **Returning operator with empty registry** (closed all windows + released all kept): "Nothing open. Click an icon in the top dock to open a surface, or use the launcher to browse."
   - Detection: first-time = `windowStates` is empty AND `open` is empty AND `kept` matches the default `['feed']` exactly (operator hasn't touched anything). Returning-empty = anything else.

6. **TopBar brand-mark click navigates to `/desktop`.** Pre-D17 it navigated to the foregrounded surface's route (D6 last-active-home semantics, now superseded by D17's "return to desktop" semantics). The macOS-equivalent: click the wallpaper / use Mission Control to show the desktop. The "last-active" concept survives as `foregrounded` in the registry — when you click the brand mark you go to desktop; the foregrounded window is still mounted and reachable via its Dock icon.

7. **FAB moves from viewport-fixed to inside the Desktop layer.** D16 mounted ChatFAB as `fixed left-1/2 bottom-X z-[60]` — on top of windows. D17 mounts it as an absolute-positioned child of the Desktop wrapper inside SurfaceViewport, at the bottom-center of the Desktop layer. Z-stack: FAB has lower z than windows (z-stack 10+). When windows don't cover the Desktop's bottom-center area, FAB is visible there. When windows cover it, FAB is hidden underneath.

8. **D15 window bounds-clamping respects a reserved Desktop strip at bottom-center.** To prevent the FAB from being permanently unreachable (a real concern the operator named), D17 reserves a ~96px-tall × ~120px-wide area at the bottom-center of the Desktop where windows cannot be positioned/resized. The reserved strip ensures the FAB is always reachable — operator can drag/resize windows freely everywhere else, but never into the FAB's home. The window-state clampWindowState helper gains an optional `reservedBottomCenter` zone.

9. **The drawer (D16 ChatDrawer) stays in `floating-overlay` region.** Only the FAB moves. The drawer continues to slide-over from the right when summoned, z-stacked above everything per D16. This split (FAB on Desktop, drawer in floating-overlay) reflects their different natures: the FAB is a desktop-level affordance (a tool sitting on the wallpaper); the drawer is a temporary overlay that covers content.

**Why D17 and not its own ADR**: continues the D11–D16 pattern of refining the surface-mirrors-substrate principle's layout-policy expression. D17 doesn't reopen the axiom (everything is still a surface); it ratifies a structural concept (Desktop) that was already implicit in the implementation and makes it consistent. Same ADR; explicit amendment for trace continuity.

**What D17 does NOT do**:
- Does not auto-restore window geometry for surfaces that weren't open at last logout but were previously seen. The `windowStates` registry only restores what was open.
- Does not add a "minimize all windows" / "show desktop" keyboard shortcut (the macOS F11 / cmd-F3 equivalent). Brand-mark click is the only "show desktop" affordance in v1.
- Does not change first-time operator onboarding beyond the empty-state copy. A richer onboarding flow is a future ADR.
- Does not change the per-slug routes' rendering behavior (cold-load to `/cadence` still opens Cadence + foregrounds it).
- Does not change ChatDrawer behavior (drawer width, mobile takeover, persona header, etc.) — only the FAB's mount location changes.

D17 implementation status: **Implemented 2026-05-22** (this session, code commit lands together with this doc per the same combined-commit cadence as D14/D15/D16).

### D18 — Z-tier ladder + inter-surface interaction + URL-sync-on-close (2026-05-22 same-session amendment)

**Refines** D15 (window z-stacking — caps the unbounded `windowState.z` at `WINDOW_Z_MAX = 99` and adds compaction). **Refines** D13/D14 (Dock click semantics — extends to inter-surface interaction on background windows). **Refines** D17 (URL transport — closes the loop so closing the foregrounded window navigates URL to `/desktop`, preventing the AuthenticatedLayout pathname watcher from re-foregrounding the just-closed surface).

Three operator-surfaced interaction bugs (KVK 2026-05-22 follow-up to the D17 ship), all rooted in z-stacking + URL-vs-registry sync gaps:

1. **"Can't click on another window's close when I'm on another surface"** — the Launcher overlay (`z-50`) was getting covered by raised windows whose effective `zIndex` (`10 + windowState.z`) exceeded 50 after multiple click-to-raise events. The reported symptom was actually "can't reach the Launcher" but the more honest framing was "inter-surface accessibility" — clicking the × on a background window's exposed title bar should close it without first requiring a raise.

2. **"The search surface (Launcher) should always be the thing that shows up above everything else"** — direct: the Launcher overlay must be the topmost UI affordance when summoned. The current z-stack had no central source of truth; hardcoded `z-50` values across the codebase (Launcher, ChatDrawer, UserMenu, TopBar context menu, TopBar cap-hit toast) all collide at the same tier. Windows could raise above all of them.

3. **"Can't close out of feed and go to empty desktop"** — D17 ratified Desktop as load-bearing, but closing the foregrounded window left the URL at `/feed` (or whatever surface). AuthenticatedLayout's pathname watcher fired on the unchanged URL → re-foregrounded the just-closed surface. The empty Desktop was structurally unreachable from a surface URL until you manually navigated to `/desktop`.

**Decisions**:

1. **Z-tier ladder**: new `web/lib/shell/z-tiers.ts` constants file declares the canonical z-stack. ONE source of truth; every component imports from here.

   | Tier | Layer | z-index |
   |---|---|---|
   | `Z_DESKTOP_FAB` | Desktop layer FAB | 5 |
   | `WINDOW_Z_BASE` | window z-baseline | 10 |
   | `WINDOW_Z_MAX` | window z-cap | 99 |
   | `Z_DRAWER_BACKDROP` | ChatDrawer backdrop | 100 |
   | `Z_DRAWER_BODY` | ChatDrawer body | 101 |
   | `Z_POPOVER` | UserMenu / context menu / cap-hit toast | 200 |
   | `Z_LAUNCHER_OVERLAY` | Launcher search overlay | 400 |

2. **Window z-bump capped + compacted**: `raiseWindow` and `foregroundSurface` enforce `Math.min(WINDOW_Z_MAX, computeNextZ(...))`. When the cap is hit, `compactWindowZ()` re-ranks all open windows from `1..N` so the values don't permanently stick at 99. Compaction preserves order — the window that had the highest z gets the highest post-compaction z. Effective rendered z stays `WINDOW_Z_BASE + z`, never exceeding `WINDOW_Z_BASE + WINDOW_Z_MAX = 109`.

3. **Inter-surface interaction on background windows**:
   - **Close button on a background window**: clicking the × closes that window without first raising it. Verified by `stopPropagation` on the close button's mousedown (already present; D18 ensures it works reliably and is documented).
   - **Drag title bar on a background window**: raise AND begin drag in one motion. The drag handler explicitly calls `onRaise()` at session-start (already present in D15); D18 documents this as the contract.
   - **Resize edges on a background window**: raise AND begin resize in one motion. Same pattern as drag — handler calls `onRaise()` at session-start.
   - **Click anywhere else on a background window**: raise to foreground (unchanged D15 behavior).
   - These four behaviors together are the "inter-surface accessibility" contract — operators interact with background windows without the friction of "raise first, then interact."

4. **⌘W keyboard shortcut**: macOS-standard "close current window" binding. Pressing ⌘W (or Ctrl+W on non-Mac) closes the currently-foregrounded window. Listener attached at AuthenticatedLayoutInner level. Fallback for cases where the close button is fully occluded.

5. **URL-sync-on-close**: when `closeSurface(slug)` empties the registry OR closes the slug matching the current pathname, navigate to `/desktop`. The pathname watcher then has nothing to foreground; the operator lands on the empty Desktop. Implementation: the close handler in TopBarSurface's right-click menu, the close button in WindowFrame, and the ⌘W shortcut all check `if pathname matches the closed slug → router.push('/desktop')`. The check happens at the call-site rather than inside `doCloseSurface` because the hook doesn't have access to the router.

6. **Singular Implementation**: every hardcoded `z-50` / `z-40` / `z-60` / `z-[5]` / `zIndex: 10 + …` across shell components is replaced by imports from `z-tiers.ts`. The constants file is the only place a z-value is authored.

**Why D18 and not its own ADR**: continues the D11–D17 pattern of refining the surface-mirrors-substrate principle's interaction-layer expression. D18 doesn't reopen the axiom; it ratifies a structural concept (z-tier ladder) that was already implicit and makes it consistent + bounded. The URL-sync-on-close fix is a coherence patch for D17. Same ADR; explicit amendment for trace continuity.

**What D18 does NOT do**:
- Does not add per-Dock-icon hover-close affordance (rejected — right-click → Close already exists per D14; ⌘W covers keyboard ergonomics).
- Does not add cmd-tab keyboard window switcher (still forward horizon).
- Does not add per-window context menus on the title bar (right-click in D14 is Dock-icon only; window title-bar right-click is forward horizon).
- Does not change ChatDrawer / Launcher overlay visual design — only their z-stacking.
- Does not add z-tier enforcement for non-shell components (other parts of the app keep their own z values; the ladder is shell-scoped).

D18 implementation status: **Implemented 2026-05-22** (this session, code commit lands together with this doc per the same combined-commit cadence as D14/D15/D16/D17).

### D18.1 — Drawer + Launcher mutex + drawer fade transition (2026-05-22 follow-up patch)

Operator-observed (KVK 2026-05-22, post-D18) cosmetic + interaction follow-ups on the chat drawer:

1. **"There is a flicker going on with the surface (top I assume) when I open the chat drawer"** — the drawer's backdrop snap-mounted at full opacity with `bg-foreground/10 backdrop-blur-[1px]`, instantly dimming + blurring the foregrounded window. No transition; the visual snap read as a flicker on the upmost surface.

2. **"What's the right approach if the chat drawer is open while the launcher" [is also open]?** — pre-D18.1, both shell overlays could coexist; the launcher's `Z_LAUNCHER_OVERLAY = 400` stacked above the drawer's `Z_DRAWER_BODY = 101`. Operator opens drawer, then summons launcher → launcher appears over drawer; closing launcher reveals drawer behind it unexpectedly. Confusing mental model — operator can't tell what's active.

**Decisions** (D18.1):

1. **Drawer + Launcher mutex**: only one shell overlay open at a time. `openDrawer()` auto-closes the launcher; `openLauncher()` auto-closes the drawer. `toggleDrawer()` follows the same rule when transitioning closed → open. Implemented in `ShellChromeContext` so all callers (FAB, launcher trigger, etc.) inherit the behavior. Drawer state (ConversationPanel scroll position, attachment uploads in flight) is preserved across close/re-open because D18.1's render-always pattern keeps the drawer mounted (see decision 2).

2. **Drawer backdrop + body fade-and-slide transition**: drawer wrapper renders always (no `if (!open) return null`); backdrop and body toggle visibility via opacity + transform + `pointer-events-none`. Backdrop: `transition-opacity duration-150` between opacity-0 and opacity-100. Body: `transition-transform duration-150` between `translate-x-full` (off-screen right) and `translate-x-0` (in place). Body slides in from the right (macOS-Sheet-like); backdrop fades. ConversationPanel stays mounted across open/close cycles — no state loss.

3. **Mutex is symmetric in code, asymmetric in operator intent**: pre-decision the operator preferred symmetric mutex (closing-on-both-sides matches the cleanest mental model). The asymmetric "drawer auto-closes on launcher open but not vice versa" option was rejected as too clever — symmetric is easier to predict.

**Files** (~2 changed, no new):
- `web/components/shell/ShellChromeContext.tsx` — `openDrawer` + `toggleDrawer` close launcher first; `openLauncher` closes drawer first; close handlers unchanged.
- `web/components/shell/chrome/ChatDrawer.tsx` — `if (!open) return null` removed; backdrop + body always rendered with transition classes that toggle on `open`. `aria-hidden={!open}` added to drawer body for a11y when closed.

**What D18.1 does NOT do**:
- Does not animate other overlays (Launcher, UserMenu dropdown, TopBar context menu, cap-hit toast). Each could benefit from similar fade-in/out but operator pain was on the drawer specifically; other overlays open/close briefly enough that snap-mount isn't a felt issue.
- Does not change the drawer's mobile takeover behavior (still full-screen on `<640px`).
- Does not introduce a focus trap inside the drawer (forward horizon — useful for keyboard navigation but not operator-observed pain yet).

D18.1 implementation status: **Implemented 2026-05-22** (this session, code commit lands together with this patch note).

---

### D18.2 — Cockpit polish: feed icon, talk button deletion, raise-on-click, drawer flicker (2026-05-22 follow-up batch)

Operator-observed (KVK 2026-05-22, post-D18.1) four collateral gaps once the multi-window + drawer pattern was in steady use:

1. **Icon collision.** Feed Dock icon and ChatDrawer FAB both rendered as `MessageCircle` — visually identical, two different things. Operator confusion: "the chat FAB button and feed surface icon is the same."

2. **Per-surface "Talk" button is redundant chrome.** Pre-D16, FeedSurface had a "Talk" button in its action row that opened a `/feed`-local ConversationDrawer. D16 generalized chat affordances into the universal FAB-summoned drawer, but the in-header Talk button survived. With the FAB summoning the drawer from every surface, the Talk button is dual-implementation.

3. **Raise-on-click broken in the window body.** Operator-observed: "when clicking on a surface not the primary one, we should make that the main surface displayed. Right now I can only grab it (although when I click on close button, that works)." Diagnosis: `handleFrameMouseDown` was wired on the outer div's bubble-phase `onMouseDown`; empirically unreliable against scrollable inner content + nested handlers. Capture phase fires unconditionally regardless of descendant `stopPropagation`.

4. **Drawer re-open flicker.** Operator-observed: "there is still a flickering aspect when i re-open the chat drawer." Diagnosis: `backdrop-blur-[1px]` on the backdrop transitioning opacity caused Chromium to drop the GPU compositor layer at opacity:0 and recreate it with `backdrop-filter` on next open — visible as a 1-frame paint flash.

**Decisions** (D18.2):

1. **Feed icon swapped `message-circle` → `scroll-text`**. Narrative ledger metaphor matches the surface's actual content shape (every invocation, every wake, append-only). FAB stays as MessageCircle (chat conversation summon). No more icon collision.

2. **In-header Talk button DELETED from FeedSurface**. Singular Implementation: the FAB is the singular summon path. Empty-state chip clicks + OperatorEventMarker's "open conversation →" affordance continue to route through `useShellChrome().openDrawer()`.

3. **WindowFrame raise-on-click switched to `onMouseDownCapture`.** Capture phase fires before any descendant handler can `stopPropagation()`. Matches macOS behavior (clicking anywhere in a background window raises it).

4. **`backdrop-blur-[1px]` removed from the ChatDrawer backdrop.** Replaced with slightly stronger bg dim (`bg-foreground/10` → `bg-foreground/15`). The 1px blur was barely perceptible; the layer stays put across open/close cycles, no paint flash.

**Files**:
- `api/services/kernel_surfaces.py` — Feed `icon_key` `message-circle` → `scroll-text`.
- `web/lib/shell/surface-icons.tsx` — `ScrollText` registered.
- `web/components/feed-surface/FeedSurface.tsx` — Talk button + `personaName` + `useReviewerPersona` + `MessageCircle` import deleted.
- `web/components/shell/WindowFrame.tsx` — `onMouseDown` → `onMouseDownCapture`; handler renamed `handleFrameMouseDownCapture`.
- `web/components/shell/chrome/ChatDrawer.tsx` — backdrop `backdrop-blur-[1px]` removed.

D18.2 implementation status: **Implemented 2026-05-22** (commit `ed155c5`).

---

### D18.3 — Close-surface URL-sync race fix (2026-05-22 follow-up patch)

Operator-observed (KVK 2026-05-22, post-D18.2): "I can't close the topmost window and land on an empty desktop." Close × clicked, window briefly disappears, then re-mounts immediately. Pure architectural race; no axiom change.

**Diagnosis**: Two `useEffect`s in `AuthenticatedLayout.tsx` raced. Effect A (pathname → foreground surface) re-fired on every close because `foregroundSurface`'s callback identity changes whenever `open` changes — so closing `feed` while pathname was `/feed` immediately re-opened it. Effect B (foregrounded===null + open===[] → /desktop) was supposed to handle the empty-registry case, but ran *after* Effect A had already resurrected the surface.

Same race in the multi-window case: closing the foregrounded window when others exist falls back to the next-most-recent, but pathname is stale → Effect A re-foregrounds the closed surface.

**Decision** (D18.3): URL sync moves inside `closeSurface` itself in `useSurfacePreferences`. When the foregrounded surface is closed, the registry mutation AND the `router.push` happen in the same React batch — pathname is updated to either `/desktop` (registry empty) or the fallback surface's route. By the time Effects A/B run, pathname matches the new state, no resurrection possible.

Singular Implementation: the duplicate "Effect B" URL-sync-on-close `useEffect` in `AuthenticatedLayout` was DELETED. One URL-sync path now, owned by `closeSurface`.

**Files**:
- `web/lib/shell/useSurfacePreferences.tsx` — `usePathname` + `useRouter` + `useComposition` wired in; `doCloseSurface` navigates synchronously when closing the foregrounded surface AND pathname matches a kernel surface route.
- `web/components/shell/AuthenticatedLayout.tsx` — Effect B (URL-sync-on-close) DELETED; `open` removed from destructure (was only used by deleted effect).

D18.3 implementation status: **Implemented 2026-05-22** (commit `07ecec2`).

---

### D19 — Surface internals are window-shaped, not page-shaped (2026-05-22, doc-first)

Operator-observed (KVK 2026-05-22, post-D18.3): "I think there is some confusion on how the launcher and navigation occurs. We have surfaces that should be the central UI UX under desktop. But then, I get re-routed to pages like agents, in which the navigational considerations seem to break."

Diagnosis surfaced an unfinished migration: D11→D17 ratified the Agent-OS metaphor at the shell layer (Desktop + WindowFrame + universal FAB + Dock) and migrated 10 of the 13 atomic surface page.tsx files into thin window-shaped wrappers, but **three surface page.tsx files (`agents`, `cadence`, `context`/files) were never refactored from their pre-ADR-297 page paradigm.** They still:

1. Render `<ThreePanelLayout>` (a workspace-wide outer chrome — but the WindowFrame IS the chrome now).
2. Call `setBreadcrumb` (page-level concept; windows have title bars, not workspace breadcrumbs).
3. Use `router.push('/work?agent=X')` for cross-surface navigation (route-replacement metaphor — should be window-opening metaphor per the OS framing).

The legacy three never made the migration because they had the most complex internal state (multi-pane layouts, intra-surface selection, cross-surface deep-links). The other 10 are clean: `feed`, `cockpit`, `delegation`, `mandate`, `principles`, `identity`, `brand`, `queue`, `activity`, `program` — each is a 20-60-line wrapper that imports a `<SurfaceComponent />` and renders it inside the WindowFrame.

The collision: clicking around inside a legacy-shaped surface window feels like the operator has *left* the Desktop paradigm — they're now inside a "page" with its own three-panel chrome, its own breadcrumb, its own router-based navigation. The window framing is structurally present but the *content* doesn't honor the windowed metaphor. Cross-surface `router.push` calls additionally produce the wrong gesture (navigate-to-page instead of open-new-window).

**Operator framing** (KVK): *"Figma on browser is the better metaphor here."* Figma is unambiguously desktop-app-shaped, runs in Chrome, treats URLs as deep-link transports for document state, has no concept of "leaving the canvas to go to a settings page." Settings is a panel/modal *over* the canvas. Browser back/forward is undo-shaped, not page-history-shaped. That's the reference for D19.

**Decisions** (D19):

1. **Surface internals are window-shaped, not page-shaped.** Every component mounted in a `WindowFrame` is content-only — no outer chrome rendered by the surface itself. The window IS the chrome.

2. **`ThreePanelLayout` is dissolved for atomic surfaces** (Singular Implementation): it represented a workspace-wide layout shell from the pre-ADR-297 paradigm. Inside a window, a workspace-wide left tree nav is structurally wrong (the Dock IS the navigation rail). The three current consumers (`agents`, `cadence`, `context`) each refactor:
   - `agents` + `cadence` already pass `leftPanel` as omitted/optional; the wrapper collapses to its center children. Drop the wrapper entirely.
   - `context` (Files surface) does carry a legitimate tree (the workspace filesystem tree IS the surface's content). Keep the tree as the surface's *internal* layout, not as outer chrome. The Files surface owns its own two-pane render directly.
   - `ThreePanelLayout.tsx` DELETED.

3. **Workspace-wide breadcrumb is not set from inside atomic surfaces.** The window's title bar is the breadcrumb. Intra-surface selection (e.g. which agent is selected on `/agents`) is window-internal state — it appears as a sub-label inside the surface's own UI, not as a workspace-level `setBreadcrumb` call. `BreadcrumbContext` is retained as infrastructure for legacy non-atomic routes (settings, docs/[id]) where the page paradigm is honest; atomic surfaces stop writing to it.

4. **Intra-surface URL state stays.** `/agents?agent=reviewer` is fine — it's the window's deep-link state for which agent is selected. Same shape as Figma's `?node-id=X`. The atomic-surface URL plus its query params together identify the surface's complete state.

5. **Cross-surface navigation is window-opening, not route-replacing.** Every `router.push('/{atomic-surface-slug}')` call from inside an atomic surface is converted to `foregroundSurface('{slug}')`. The result: clicking "See this agent's work" from inside Agents opens a new Cadence window alongside the Agents window (macOS multi-app gesture), instead of replacing the Agents content with Cadence content (browser-page gesture). Operator can ⌘W close either independently; the Dock shows both.

6. **`/desktop` is the canonical workspace URL.** Atomic-surface URLs (`/feed`, `/cadence`, etc.) remain as deep-link transports — pasting one opens that surface in a window on the Desktop. They are NOT first-class destinations. The Desktop is the destination; surfaces are windowed apps.

7. **Settings-class pages stay as pages** (Option α per discourse — committed). `/settings`, `/connectors`, `/auth/callback`, `/docs/[id]` etc. are not atomic surfaces. They render outside the Desktop layer via the existing `isLegacyNonAtomicRoute` branch in `SurfaceViewport`. This is the honest boundary: settings ARE pages, surfaces ARE windows, the SurfaceViewport's branch is the structural delimiter. Two paradigms total in the authenticated app — Desktop+windows for everything operational, pages for configuration. macOS-faithful (Preferences in macOS is technically a window but feels like settings; the YARNNN equivalent is a real page route, which is the same cognitive boundary). Option β (everything-is-a-surface, including Settings) was discussed and rejected as more aggressive than the operator-felt pain warranted.

**What D19 enacts (mechanical changes)**:

- Refactor `app/(authenticated)/agents/page.tsx` (~188 lines) → window-shaped `<AgentsSurface />` component. Drop `ThreePanelLayout`. Drop `setBreadcrumb`. Convert cross-surface `router.push` calls to `foregroundSurface`.
- Refactor `app/(authenticated)/cadence/page.tsx` (~383 lines) → window-shaped `<CadenceSurface />` component. Same migration shape.
- Refactor `app/(authenticated)/context/page.tsx` (Files) → window-shaped surface component. The internal tree stays as the surface's content; outer `ThreePanelLayout` wrapper dissolved.
- Delete `web/components/shell/ThreePanelLayout.tsx`.
- Audit + delete `setBreadcrumb` calls from atomic-surface components (`AgentContentView`, others as found). Surface-internal title display moves into the surface's own header.
- Convert remaining cross-surface `router.push('/{atomic-slug}')` call sites to `foregroundSurface('{slug}')` via grep. The push-to-self pattern (`router.push('/agents?agent=X')` from within `/agents`) stays — that's intra-surface state, not cross-surface navigation.

**What D19 does NOT do**:

- Does not change the substrate layer. Substrate axioms (Axiom 1, ADR-209) untouched.
- Does not refactor the 10 already-thin atomic-surface wrappers (`feed`, `cockpit`, etc.). They were already window-shaped; no work needed.
- Does not move Settings into the Desktop (Option β rejected).
- Does not introduce window-grouping / spaces / virtual desktops (forward horizon item from D15-D18).
- Does not change the deep-link URL contract — pasting `/cadence?task=foo` still works (and opens the surface in a window). Bookmarks remain stable.
- Does not change ⌘W close, drawer summon, FAB position, or any chrome behavior already shipped.
- Does not refactor `BreadcrumbContext` (keeps it for legacy non-atomic routes where it's load-bearing).
- Does not delete the per-slug `app/(authenticated)/{slug}/page.tsx` files — they remain as deep-link mount points; their content is now the thin wrapper pattern matching the already-migrated 10.

**Companion canonical doc updates** (same enactment commit):

- `docs/design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md` — D19 referenced as the post-migration completion.
- `CLAUDE.md` — atomic-surface internals section gets the window-shape rule.

D19 ratification status: **Implemented 2026-05-30** (was Proposed 2026-05-22 → Enacting; the call-site migration landed via [`docs/design/ADR-297-NAVIGATION-ENACTMENT-PLAN.md`](../design/ADR-297-NAVIGATION-ENACTMENT-PLAN.md). `navigateToSurface` is the single cross-surface verb; the legacy Supervisor Desk (`DeskContext`) is deleted; regression guard at `api/test_adr297_navigation_enactment.py` enforces the boundary. Commits `fbfcb02` / `9c66bdc` / `70b2b86` + Phase 5.).

---

### D19.4 — Inside the authenticated workspace, every surface is a window (2026-05-22, doc-first)

**Reverses D19.7** (Option α — "settings stays a page"). Same-session reversal after operator surfaced the real architectural cost.

**Operator-observed (KVK 2026-05-22, post-D19.3)**: clicking Settings from the UserMenu **erases the workspace**. The Desktop layer and every open window disappear from the DOM (SurfaceViewport's `isLegacyNonAtomicRoute` branch returns `<>{children}</>`, which renders the page tree alone — no Desktop, no windows). Operator framed it as *"settings get drowned behind existing windows. meaning, in theory, the desktop there can't be things surfacing it breaks the OS concept."*

This is a real axiom violation, not just a perception. macOS Preferences opens *on top of* your existing apps — you can still see Safari, iTerm, etc. behind/around it. The YARNNN equivalent currently REPLACES the workspace with a page; that is the opposite of the OS metaphor.

D19.7 had argued Settings is a legitimate page-shaped thing (long-form preferences, billing tabs, OAuth callbacks). True structurally — Settings IS a tabbed preferences pane — but the *windowed*-ness of macOS Preferences is the load-bearing detail. macOS Preferences is technically a window. The cognitive boundary D19.7 imagined ("settings ARE pages, surfaces ARE windows") was false — in macOS, both are windows, and the only things that aren't windows are unauthenticated routes (login, marketing).

**Decisions** (D19.4):

1. **The new axiom**: *Inside the authenticated workspace, every surface is a window mounted on the Desktop.* Pages survive only at the **authentication boundary** (`/auth/callback`, `/login`) and for **operator-external content** (`/docs/[id]` public viewer, marketing routes `/`, `/pricing`, `/faq`, `/how-it-works`, `/invest`, `/privacy`, `/terms`).

2. **`settings` becomes the 14th kernel surface**. Atomic, window-shaped. Internal tab structure preserved (`?tab=billing` / `?tab=usage` / etc. = window-internal deep-link state per D19.4). The existing `app/(authenticated)/settings/page.tsx` refactors to the thin-wrapper window pattern (same shape as `feed`, `cockpit`, etc.). Settings opens as a window on the Desktop alongside whatever else is open. Operator can ⌘W close it, drag it, resize it, minimize it to the Dock — same chrome as everything else.

3. **`connectors` becomes the 15th kernel surface**. Operator declined the "fold into Settings as a tab" option (which was the simpler-Singular-Implementation move) and chose a separate surface. Reason: integrations are a workspace-level concern (live OAuth state, sync status, per-platform substrate) more than an account-shaped preference. They earn their own atomic surface. `app/(authenticated)/connectors/page.tsx` refactors to thin-wrapper window pattern.

4. **UserMenu shrinks** to: header (email + balance + theme toggle) + "Settings" (`foregroundSurface('settings')`) + "Sign out". The Mandate / Activity / Billing / Connectors menu entries are DELETED. Mandate + Activity are atomic surfaces discoverable via Dock + Launcher — UserMenu doesn't need to be a parallel discovery affordance for them. Billing is a Settings tab — `?tab=billing` is intra-Settings deep-link state, not a separate menu entry. Connectors is its own surface now — operator opens it via Launcher or by adding it to the Dock.

5. **Billing stays as a Settings tab**, not its own surface. Billing is account-state-changing chrome that lives naturally inside the Settings preferences pane; the Settings surface's intra-surface `?tab=billing` deep-link is sufficient. Singular Implementation: one Settings surface, multiple tabs.

6. **`isLegacyNonAtomicRoute` branch tightens** in `SurfaceViewport`. Pre-D19.4 it caught `/settings`, `/connectors`, `/docs/[id]`, plus marketing/auth. Post-D19.4 it catches only `/auth/*`, `/docs/[id]`, and marketing/static routes (`/`, `/pricing`, `/faq`, `/how-it-works`, `/invest`, `/privacy`, `/terms`, `/sitemap.xml`, `/robots.txt`, `/llms.txt`, `/blog/*`). The branch survives at the authentication boundary, not inside it.
   > **ADR-308 (2026-06-01) finishes this invariant.** D19.4 *declared* the branch auth-boundary-only but the ~12 authenticated-interior **redirect stubs** (`/chat`, `/context`, `/backend`, `/memory`, …) were still `'use client'` pages that painted one orphaned frame inside `SurfaceViewport` before redirecting — so the invariant was true in prose, false in code (operator re-observed the "looks fine, breaks" seam on `/context` 2026-06-01). ADR-308 converts every interior stub to a server `redirect()` (fires before any layout mounts, never enters the shell), making D19.4's invariant true in code. See [ADR-308](ADR-308-redirect-stubs-as-pure-transport.md).

7. **Per the D19.5 cross-surface navigation rule**: any code calling `router.push('/settings')` or `router.push('/connectors')` from inside the authenticated workspace converts to `foregroundSurface('settings')` / `foregroundSurface('connectors')`. Grep + audit covers `WorkspaceSection.tsx`, `UserMenu.tsx`, and any other call sites. Marketing pages can still link to `/settings` — first-paint cold-load via Effect A opens the Settings window on the Desktop, just like `/cadence` or `/agents` per D19.2.

**What D19.4 enacts (mechanical)**:
- `api/services/kernel_surfaces.py`: add two entries — `settings` (icon `settings`, archetype `dashboard`, route `/settings`) + `connectors` (icon `link-2`, archetype `dashboard`, route `/connectors`).
- `web/lib/shell/surface-icons.tsx`: register `settings` → `Settings` icon, `link-2` → `Link2` icon (both already in lucide-react).
- `web/types/desk.ts`: extend `KernelSurfaceSlug` union + `KERNEL_SURFACE_SLUGS` array with `'settings'` + `'connectors'`.
- `web/components/shell/SurfaceRegistry.tsx`: import + register both pages.
- `web/app/(authenticated)/settings/page.tsx`: refactor to window-shape (drop outer chrome if any — likely already mostly content-only; the `<div>` wrappers + page paddings get the window treatment).
- `web/app/(authenticated)/connectors/page.tsx`: same window-shape refactor.
- `web/components/shell/UserMenu.tsx`: shrink to email + balance + theme + Settings + Sign out. Mandate / Activity / Connectors entries deleted; Billing entry deleted (operators reach it via Settings tab nav). The "Settings" entry uses `foregroundSurface('settings')` per D19.2 (no URL rewrite).
- `web/components/settings/WorkspaceSection.tsx`: the `router.push('/feed')` call sites that operate from inside the Settings page (e.g. on first-paint redirect) convert to `foregroundSurface('feed')`.
- `api/test_adr297_phase1.py`: increment expected surface count from 16 (13 content + 3 D12 chrome) to 18 (15 content + 3 D12 chrome); add `settings` + `connectors` to expected slug set; assert their declared archetype.

**What D19.4 does NOT do**:
- Does not move marketing pages (`/`, `/pricing`, `/faq`, etc.) into the workspace. They live outside authentication.
- Does not move `/auth/callback`, `/login`, etc. into the workspace. They're pre-authenticated.
- Does not move `/docs/[id]` into the workspace. Operator-external public content.
- Does not introduce a new "preferences" archetype — Settings + Connectors map to `dashboard` archetype for v1 (read-mostly status boards with action affordances inline). Future ADR can split if pressure surfaces.
- Does not change Billing's location — stays as Settings tab via `?tab=billing` deep-link. NOT a separate kernel surface.
- Does not refactor the existing Settings/Connectors page internals beyond the window-shape transform. Tab navigation, OAuth flows, plan upgrade UI all preserved verbatim.
- Does not change `isLegacyNonAtomicRoute`'s structural role — it survives as the auth-boundary delimiter. The set of routes it catches shrinks.

**Companion canonical doc updates** (same enactment commit):
- `CLAUDE.md`: the atomic-surface section gains "Settings + Connectors are atomic surfaces" + the new axiom in the OS-framing paragraph.

**Implementation order** (single commit recommended given the locked scope; mirror D19 enactment shape):
1. Backend: add the two `kernel_surfaces.py` entries + frontend icon registry entry.
2. Type union: extend `KernelSurfaceSlug` + `KERNEL_SURFACE_SLUGS` + `isKernelSurfaceSlug` will pick up both automatically.
3. Frontend registry: import both pages into `SurfaceRegistry.tsx`.
4. Refactor `settings/page.tsx` + `connectors/page.tsx` to window-shape.
5. Shrink UserMenu.
6. Sweep `router.push('/settings'|'/connectors')` call sites and convert to `foregroundSurface`.
7. Update phase1 regression gate.
8. Validate: tsc + next build + python phase1 gate.

D19.4 ratification status: **Implemented 2026-05-30** (was Proposed 2026-05-22 → Enacting; Settings/WorkspaceSection page-pushes converted to `navigateToSurface` per [`docs/design/ADR-297-NAVIGATION-ENACTMENT-PLAN.md`](../design/ADR-297-NAVIGATION-ENACTMENT-PLAN.md) Phase 2).

---

### D19.6 — Intra-surface deep-link updates preserve the pathname baseline (2026-06-12, Implemented)

**Trigger** (operator-observed, KVK 2026-06-12): clicking a file in the Files surface, or an agent in the Agents surface, changed the URL and disrupted the launcher/topbar. Root cause: a surface running as a *window* on the Desktop (pathname `/desktop`) wrote its deep-link param via `router.push/replace('/{slug}?param=X')`, which flipped pathname `/desktop → /{slug}`. That pathname flip trips three shell mechanisms that branch on the `/desktop` baseline: `AuthenticatedLayout`'s pathname→foreground effect, `SurfaceViewport`'s `pathnameSlug` resolution, and `closeSurface`'s URL-sync.

**The gap.** D19.2 covered *bare* cross-surface navigation (URL stays as-is). D19.5's `navigateToSurface(slug, params)` covered *cross-surface navigation WITH params* (pathname flip is correct — you're moving surfaces). Neither covered the third case: **intra-surface deep-link update** — "I'm already in this surface, change which entity it shows" (switch agents, select a recurrence, clear a filter). For that case a pathname flip is the disruption, not the goal.

**Decision.** Add one sanctioned intra-surface verb to the window manager (`useSurfacePreferences`):

```ts
setSurfaceParams(params: Record<string, string | null>): void
```

- Updates the foregrounded surface's URL params under the **current** pathname via `window.history.replaceState` — **no pathname flip, no foreground effect, no Next navigation event.** A `null`/`''` value deletes that key; unmentioned keys are preserved.
- Surfaces keep reading `useSearchParams()` as their single source of truth — **no parallel component state** (Singular Implementation). Next 14.2 patches `history.replaceState` (`node_modules/next/dist/client/components/app-router.js`) so the router syncs and `useSearchParams()` re-renders, while the pathname→foreground effect stays quiet because no navigation event fires.

**The three-verb model after D19.6:**

| Verb | Case | pathname | URL params |
|---|---|---|---|
| `foregroundSurface(slug)` | bare cross-surface (Dock/Launcher) | as-is (D19.2) | as-is |
| `navigateToSurface(slug, params?)` | cross-surface with deep-link | **flips** to `/{slug}` | written |
| `setSurfaceParams(params)` | **intra-surface deep-link update** | **preserved** | replaced in place |

**What stays cross-surface (unchanged).** External `href`/`navigateToSurface` deep-links *into* these surfaces (`/recurrence?task=` from Home, `/agents?agent=` from Reviewer panels, `/activity?slug=` from RecurrenceList) are genuine cross-surface navigation — the pathname flip is correct there, and the param reads on cold-load. Only the surface's *own* intra-surface param updates use `setSurfaceParams`.

**Enacted (same commit):**
- `web/lib/shell/useSurfacePreferences.tsx`: `setSurfaceParams` verb + interface + context wiring.
- `web/app/(authenticated)/agents/page.tsx`: 2 call sites (reviewer card, agent card).
- `web/app/(authenticated)/recurrence/page.tsx`: 3 call sites (select, clear-agent-filter, back-to-list).
- `web/app/(authenticated)/activity/page.tsx`: 1 call site (clear slug filter).
- Files (`541285a`, the reported bug) needed no `setSurfaceParams` — its `?path=` was redundant with `selectedPath` component state, so it dropped the URL write entirely. Files' `?path=`/`?domain=` survive as cold-load deep-links only.

Audit + reasoning: [`docs/analysis/intra-surface-url-navigation-audit-2026-06-12.md`](../analysis/intra-surface-url-navigation-audit-2026-06-12.md). Regression gate: `api/test_adr297_d196_intra_surface_nav.py`.

---

### D20 — Agent-OS menu-bar status cluster (2026-05-24, doc-first)

**Refines** D19.5 (three-region top-bar layout — left brand · center Dock · right UserMenu) by populating a new persistent indicator slot in the Right region. **Consolidates** three scattered FE chrome elements (the AutonomyHeaderChip on Feed per ADR-238 D4, the `balance_usd` line in the UserMenu dropdown header, the PaceBadge on the Cadence list surface per ADR-300 D5) into a single always-visible status cluster, modeled on the macOS menu-bar status-item cluster (Wi-Fi · battery · clock · volume).

**Operator framing**: an agent OS has operator-level standing state — autonomy posture, pace + wake queue depth, runway balance, platform connection reach — that is true regardless of which surface is foregrounded. Pre-D20 this state was scattered (visible on Feed but not on Work; visible in UserMenu dropdown but only after a click; visible on Cockpit but only when the operator was on Cockpit). D20 lifts these signals into the top-bar where they're always glanceable, matching how macOS treats Wi-Fi/battery/clock — operator-level state that earns persistent menu-bar real estate independent of the foreground application.

**First-principles cut** (what earns a slot, what does not):

A signal earns a menu-bar slot when it satisfies all four:
1. **Always relevant**, regardless of foregrounded surface (Wi-Fi matters in Mail and in Xcode).
2. **Status, not content** (a state to read at a glance, not information to consume).
3. **Affects the system's capacity to do work** (battery=runway, Wi-Fi=reach, volume=channel).
4. **Operator-actionable** (click leads somewhere the operator can act).

Applied to agent-OS signals — four indicators qualify; one near-miss is explicitly rejected:

| Indicator | Always-relevant? | Status not content? | Affects capacity? | Operator-actionable? | Verdict |
|---|---|---|---|---|---|
| **Autonomy** (level + ceiling + paused?) | governs every Reviewer wake | "Bounded · $X" is state | defines what agent *can* do | click → `/autonomy` | **YES** |
| **Pace + wake queue** (kind + paced/live depth) | governs every cron fire | "Daily · 3 pending" is state | defines what agent *will* do soon | click → `/pace` | **YES** |
| **Balance** (`balance_usd`) | hard stop at zero | runway state | defines runway (battery analog) | click → `/settings?tab=billing` | **YES** |
| **Connections** (platform reach + capability gaps) | tool/data reach | "3/4" is state | defines tool reach (Wi-Fi analog) | click → `/connectors` | **YES** |
| **Mandate** | content, not state — it's a constitution | document, not posture | indirectly (autonomy/pace follow *from* mandate) | edit via chat/Files | **NO** — synthesis-level, lives in concept-card surfaces, not menu-bar chrome |

Mandate is the load-bearing exclusion. Autonomy + pace + balance + connections are *consequences* of Mandate; putting Mandate in the menu bar is the macOS-equivalent of putting "macOS version" there — true but wrong category.

**Decisions** (D20):

1. **Four-slot cluster, in this order**: Autonomy · Pace · Balance · Connections. The order is intentional — kernel governance (autonomy) first, kernel tempo (pace) second, kernel runway (balance) third, kernel reach (connections) fourth. Right-region placement, between the Dock and the UserMenu, with a small horizontal gap. Each slot is **icon-only** (not icon+label) at all viewport widths — matches the macOS Wi-Fi pattern where the menu-bar item is the triangle, not "Wi-Fi · La Dolce Vita".

2. **Click → popover, not navigation**. Each chip opens a popover anchored to the chip (macOS Control Center pattern, screenshot-confirmed). The popover renders rich current state — current value + brief secondary context (e.g., autonomy ceiling + actions used today; pace kind + queue depth + next wake; balance + burn rate + runway days; per-platform connection status + capability gaps). The popover footer carries a single `→ Settings…`-style link to the corresponding atomic surface for editing. **Popovers are read-only.** Every mutation routes to the atomic surface (`/autonomy` per ADR-297 D1, `/pace` per ADR-300, `/settings?tab=billing`, `/connectors` per D19.4). This honors ADR-297 D1 (atomic surfaces own their substrate's edit affordance) and ADR-300 D5 (Singular Implementation — one edit location per shape).

3. **Data sources** — all existing, no new endpoints:
   - Autonomy → `useAutonomy()` hook per ADR-238 D2 (reads `/workspace/context/_shared/_autonomy.yaml`)
   - Pace + queue → `api.cockpit.pace()` per ADR-298/ADR-300 (`pace_kind`, `paced_lane_depth`, `live_lane_depth`)
   - Balance → `api.integrations.getLimits()` returns `balance_usd`
   - Connections → `api.workspace.state()` per ADR-244 returns `capability_gaps`
   - **No new API routes, no new substrate, no new write helpers.** Pure FE chrome consolidation.

4. **Responsive collapse** — two breakpoints:
   - **`md+` (≥768px)**: all four icon chips inline in the Right region, with a small gap between them.
   - **`<md`**: a single rollup chip (`Cpu` or `Activity` icon) replaces the cluster. Clicking it opens a popover that lists all four indicators stacked vertically with the same rich state + per-row deep-link footer. Mirrors macOS Control Center collapse on small displays. The Right region stays narrow enough that the Dock + UserMenu remain visible.
   - Icon-only chip means no label-vs-icon-only breakpoint is needed — the chip shape is constant at all widths; only the cluster's *count* collapses.

5. **Singular Implementation deletions** (enacted in the same commit that lands D20):
   - **AutonomyHeaderChip on Feed** (ADR-238 D4) — deleted. The autonomy posture is now in the top-bar cluster, visible on every surface (not just Feed). Two-location render of the same data violates D8. ADR-238 amended with a status note recording the consolidation.
   - **Balance line in UserMenu dropdown header** (`web/components/shell/UserMenu.tsx`) — deleted. Balance is now in the top-bar cluster. The UserMenu retains email + theme toggle + Settings + Sign out per D19.4; the balance display moves out.
   - **PaceBadge on `/cadence`** (CadenceList header) — already a read-only deep-link per ADR-300 D5; D20 amends to: the badge is deleted from `/cadence` because the top-bar Pace chip serves the same purpose from a more universal location. The `/pace` atomic surface remains the edit location. ADR-300 amended with a status note recording the consolidation. (ADR-300 D5's "PaceBadge on Cockpit" wording was loose — the badge has lived on `/cadence` since the move; the consolidation rationale is unchanged.)
   - **No backwards-compat shim, no flag-gated rollout.** The chips ship; the duplicates ship deleted; one location per signal.

6. **Why D20 and not its own ADR**: continues the D11–D19 pattern of refining the surface-mirrors-substrate principle's chrome-layer expression. D20 doesn't reopen the axiom (everything is still a surface; menu-bar chips are not surfaces, they're *links* to surfaces — same shape as Dock icons). It ratifies a structural concept (kernel-runtime status cluster) that completes the macOS-faithful three-region top-bar. Same ADR; explicit amendment for trace continuity. Precedent: D14, D15, D16, D17, D18, D19 all stayed in-ADR for the same reason.

**What D20 does NOT do**:
- Does not introduce program-shaped status indicators. The four chips are kernel-general; programs do not declare additional status items via `SURFACES.yaml`. (If pressure surfaces, a future ADR can extend `SURFACES.yaml` with a `chrome.status_cluster:` block — but D20 ships the kernel four only.)
- Does not allow inline mutations from the popover. Every popover is read-only; every edit happens on the atomic surface. Operators do not toggle autonomy from the popover, do not switch pace kind from the popover, do not reconnect a platform from the popover. The popover's footer link is the only outbound action.
- Does not introduce new substrate. The cluster reads what's already authored; no new files, no new YAML keys.
- Does not introduce a new component registry pattern. The cluster mounts as a fixed-shape FE module (`web/components/shell/system-status/`); contents are not pluggable.
- Does not change the Dock semantics. The Dock continues to host surface launchers (D14 kept ∪ open); the status cluster is a separate concern in a separate region.
- Does not add Reviewer occupant name, active program slug, or sync error indicators to the cluster. Reviewer occupant is covered by the autonomy popover's secondary text; active program lives near the brand wordmark (deferred to a follow-on patch if desired); sync error rolls into the Connections popover's per-platform state.

**Companion canonical doc updates** (same enactment commit):
- ADR-238 — status-header amendment recording the AutonomyHeaderChip deletion.
- ADR-300 — status-header amendment recording the PaceBadge deletion (refines D5 — "deep-link to `/pace`" was the original Singular Implementation; D20 advances to "indicator lives in top-bar cluster, Cockpit doesn't surface pace at all" because the cluster is more universal).
- `docs/design/WORKSPACE-COMPONENTS.md` — one-paragraph note in the concept-registry preamble distinguishing kernel-runtime chrome (this cluster) from substrate-concept components (the L2-parser + L3-component pattern that registry governs). The cluster does NOT use the L2/L3 pattern; it reads runtime state via hooks + API calls, not via content-shape parsers.

**Implementation outline** (single commit):
- `web/components/shell/system-status/` — new directory.
  - `SystemStatusCluster.tsx` — orchestrator, renders the four chips + responsive collapse to rollup chip.
  - `StatusItemPopover.tsx` — shared popover shell (anchor, framing, footer-link slot).
  - `AutonomyStatusItem.tsx` — chip + popover (consumes `useAutonomy()`).
  - `PaceStatusItem.tsx` — chip + popover (consumes `api.cockpit.pace()`).
  - `BalanceStatusItem.tsx` — chip + popover (consumes `api.integrations.getLimits()`).
  - `ConnectionsStatusItem.tsx` — chip + popover (consumes `api.workspace.state()`).
- `web/components/shell/chrome/TopBarSurface.tsx` — mount `<SystemStatusCluster />` in the Right region between Dock and UserMenu; add the appropriate gap.
- Deletions (Singular Implementation):
  - `web/components/tp/AutonomyHeaderChip.tsx` — delete the file; remove the import + mount from `ChatPanel.tsx` / Feed surface.
  - `web/components/shell/UserMenu.tsx` — delete the balance display line in the dropdown header; remove the `api.integrations.getLimits()` call if no longer needed.
  - `web/components/work/PaceBadge.tsx` — delete the file (its only call site is `CadenceList.tsx`); remove the import + mount from CadenceList.
  - `web/components/feed-surface/PauseAutonomyModal.tsx` — delete the file (orphaned once AutonomyHeaderChip is deleted; pause/resume now happens on the `/autonomy` atomic surface via AutonomyCard's confirm-modal pattern per WORKSPACE-COMPONENTS.md §"Confirm-modal pattern").
- `docs/design/WORKSPACE-COMPONENTS.md` — append the kernel-runtime-chrome vs substrate-concept paragraph.

D20 ratification status: **Proposed 2026-05-24** (doc-first; enactment lands in the follow-on commit per the same combined-commit cadence as D14–D19). *Note (2026-05-30): the menu-bar status-cluster deletions (AutonomyHeaderChip, UserMenu balance line, PaceBadge) are independent of the navigation enactment and are NOT in scope of [`ADR-297-NAVIGATION-ENACTMENT-PLAN.md`](../design/ADR-297-NAVIGATION-ENACTMENT-PLAN.md); D20 remains Proposed on its own track.*

#### D20 amendment (2026-05-25) — Canonical-icon discipline + `gauge` registry repair

**Operator-observed**: post-D20 enactment, the Pace chip in the SystemStatusCluster rendered an `Activity` glyph while the `/pace` Dock icon rendered the generic `Box` fallback. Two divergent icons for the same surface, visible side-by-side on the top bar.

**Root cause** (two bugs, one fix):
1. `kernel_surfaces.py::pace.icon_key = "gauge"` was declared, but `surface-icons.tsx::ICON_REGISTRY` had no `gauge` entry — `resolveSurfaceIcon('gauge')` fell through to the `Box` safe-fallback. Every consumer of the canonical resolver (Dock, Launcher) rendered Box.
2. The SystemStatusCluster's four chips (`AutonomyStatusItem`, `PaceStatusItem`, `ConnectionsStatusItem`) imported lucide icons directly instead of consuming `resolveSurfaceIcon()`. Cluster icons were chosen independently of the canonical icon-key registry, opening the door to drift between Dock/Launcher and the cluster.

**Amendment ratifies the discipline that should have been ratified in D20 §6 but was implicit**:

> **A surface has exactly one canonical icon, declared in `kernel_surfaces.py::icon_key` and resolved via `surface-icons.tsx::resolveSurfaceIcon()`. Every chrome consumer of that surface — Dock, Launcher, SystemStatusCluster chip, future surface-list affordances — renders the same icon by calling the same resolver. State-specific overrides on a chip (e.g., autonomy showing `Pause` when paused) are the only allowed deviation, and they override the default only for that specific state.**

This is the Singular Implementation principle (D8) applied to the icon layer. The icon-key registry is the single source of truth; every other render path is a consumer.

**Enacted in same commit as this amendment**:
- `surface-icons.tsx` — `Gauge` imported from lucide-react; `gauge: Gauge` added to `ICON_REGISTRY`. Closes the Box-fallback bug for `/pace`.
- `AutonomyStatusItem.tsx` — `ShieldCheck`/`ShieldAlert` direct imports deleted; uses `resolveSurfaceIcon('shield-check')` as the default chip icon. `Pause` override retained for the paused state only.
- `PaceStatusItem.tsx` — `Activity` direct import deleted; uses `resolveSurfaceIcon('gauge')`. Chip + popover header now show the canonical Gauge glyph.
- `ConnectionsStatusItem.tsx` — `Link2` direct import deleted; uses `resolveSurfaceIcon('link-2')`. Same glyph as before (Link2 was the right one), now sourced through the canonical resolver.
- `BalanceStatusItem.tsx` — UNCHANGED. Balance has no atomic kernel surface (edit target is `/settings?tab=billing` intra-surface deep-link). `Zap` is the local canonical glyph; docstring updated to record the rule that if Balance ever earns its own atomic surface, the icon declaration relocates to `kernel_surfaces.py` + `surface-icons.tsx` and this chip refactors to `resolveSurfaceIcon()` like the other three.

**Why this is an amendment paragraph and not a new D-number**: the discipline is the *natural* reading of D20 §6 ("complete the macOS-faithful three-region top-bar") + D8 (Singular Implementation). The amendment makes the implicit explicit after the operator caught the drift; no new architectural concept lands. Same ADR, recorded amendment for trace continuity.

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
