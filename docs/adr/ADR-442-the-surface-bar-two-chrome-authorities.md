# ADR-442 — The surface bar: two chrome authorities, one declaration contract

> **Status**: **Accepted + Implemented** (2026-07-11, operator-commissioned
> 2026-07-10 from the first Studio session — "three chrome rows, scattered
> buttons, no clear hierarchy"). Derivation:
> `docs/analysis/the-shell-chrome-one-authority-2026-07-11.md`.

**Date**: 2026-07-11
**Dimension**: Channel (Axiom 6 — the shell's chrome hierarchy)

**Extends / builds on**: ADR-297 D19 (the one global locator; `useWindowCrumb`
is the declaration channel this completes), ADR-438 (two honest layout modes —
both preserved), ADR-436 (the mount-owns-frame lens; the named follow-on
applies it to WindowFrame), ADR-412 (three chromes — untouched), ADR-440 D2
(the Studio surface — the first adopter).

**Amends**: ADR-440's Studio workbench header (deleted — its content re-homes
into the declaration contract).

**Preserves**: window = surface; the TopBar D19.5 three-region layout
byte-identical; the ADR-438 layout modes and the WindowFrame title bar;
the locator strip as the SINGLE back affordance; `GlobalLocatorStrip` as the
component name (the `test_global_locator_strip.py` gate pins it —
relabel-keep-name; its ROLE becomes "the surface bar").

---

## 1. The problem

A foregrounded Studio stacks three chrome rows (TopBar h-14 + locator h-7 +
the Studio's hand-rolled header), four in desktop mode (WindowFrame h-8).
Root cause, from the audit: chrome content divides into **system chrome**
(brand · launcher · Dock · attention · account — row 1, correct) and
**surface chrome** (the foreground surface's identity + its whole-surface
verbs) — but the declaration channel (`useWindowCrumb`) carries only the
identity half. With no way to declare ACTIONS into shared chrome, every
surface hand-rolls a header row; buttons scatter; a third row appears.

## 2. D1 — Two chrome authorities, one row each

- **Row 1 — system chrome**: `TopBarSurface`, unchanged. Nothing
  surface-specific ever enters it (the Dock's geography stays stable).
- **Row 2 — the surface bar**: `GlobalLocatorStrip`, evolved. The foreground
  surface **declares** its chrome into it: identity/location on the left
  (the existing crumb) + **primary actions on the right** (new). This is the
  macOS menu-bar model adapted to where yarnnn's Dock actually lives (fused
  into row 1): the app declares, the bar renders, one authority.

Rejected alternatives (recorded): merging everything into the TopBar (one row —
collides with the center Dock at common widths) and the status quo with
guidelines (the accretion that produced the complaint). See the analysis doc.

## 3. D2 — The declaration contract

One channel, two halves, both per-slug, both rendered only for the
foregrounded surface:

```ts
useWindowCrumb(slug, segments)        // identity/location (existing, ADR-297 D19)
useSurfaceActions(slug, actions)      // whole-surface verbs (NEW)

interface SurfaceAction {
  id: string;
  label: string;
  icon?: ComponentType<{ className?: string }>;
  onClick?: () => void;                       // button-shaped
  to?: KernelSurfaceSlug; params?: …;         // link-shaped → SurfaceLink
                                              // (native affordances preserved)
}
```

Actions are **data, never JSX** — the surface declares, the bar owns the
rendering (style, placement, density), exactly as the crumb works. Link-shaped
actions render through `SurfaceLink` so middle-click/new-tab/a11y survive.
The registry lives beside the crumb registry in `BreadcrumbContext`
(one declaration home; Singular Implementation). The strip remains the single
back affordance — the root title click fires the leaf crumb's `onClick`.

## 4. D3 — The seam: surface-scoped dies, content-scoped stays

> A header row describing **the surface and its open document** (identity +
> whole-surface verbs) is surface chrome → declared into the bar and deleted
> from the body. A header row describing **a selection or pane within the
> surface** stays in-body.

Applied: Files' selection header (`SurfaceIdentityHeader` + Properties) and
Chat's active-lane header (name + model chip) are content-scoped — they stay.
Split-nav `PaneHeader`s are pane-scoped — they stay.

## 5. D4 — The Studio adopts first (the pain case)

The Studio workbench header row (`StudioSurface.tsx` — icon + name + relPath +
"Open in Files" + "New / open…") is entirely surface-scoped and **dies**:

- artifact name → the crumb (`Studio › ‹artifact›`);
- back-to-start → the strip's existing root-click idiom (the leaf's `onClick`
  clears `studio.file`) — the "New / open…" button folds into it;
- "Open in Files" → a declared link-shaped action.

Studio chrome rows in canvas: **3 → 2** (desktop: 4 → 3). The visible relPath
drops from chrome (it lives in Files, one declared action away).

## 6. D5 — Chat registers its crumb (locator honesty)

`/chat` registered nothing — the locator read a bare "Chat" even deep in a
lane. `ChatSurface` now registers the active lane as its crumb
(`Chat › ‹lane›`, root-click returns to the lane list). Its in-body headers
stay (content-scoped, D3).

## 7. D6 — Desktop mode; the named follow-on

The WindowFrame title bar is the **window's frame** (N per screen) — a
different job from the one foreground surface bar. Unchanged. Named follow-on,
not built: rendering a window's declared actions into its own WindowFrame bar
(the declaration is already frame-agnostic; only a second consumer is needed).

## 8. Consequences

- **Positive**: surface chrome has one authority and a total contract — the
  next surface declares instead of hand-rolling row 4; the Studio's stack
  drops to two rows with its verbs in a consistent place; "you are here" and
  "what can I do here" finally live on the same line.
- **Cost**: one context extension + one strip render addition + the Studio
  and Chat registrations. No registry/slug moves, no backend.
- **Risk**: low — the strip's existing behaviors (back affordance, mobile
  collapse, empty-Desktop placeholder) are preserved; the gate
  `test_global_locator_strip.py` still passes unchanged.

## 9. The one-line statement

**Chrome divides into system and surface classes with one authority each: the
TopBar stays pure system chrome, and the locator strip becomes the surface
bar — the foreground surface declares its identity (crumb) and its
whole-surface verbs (`useSurfaceActions`, data not JSX) into it; header rows
that describe the surface die (the Studio's first, 3 rows → 2), rows that
describe a selection stay in-body, and the WindowFrame remains the per-window
frame with action-rendering named as the frame-agnostic follow-on.**
