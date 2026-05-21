# Session Opener — ADR-297 D11 Uniform Compositor Implementation

Drop-in prompt for a fresh session to implement ADR-297 D11. Copy from
the **PROMPT** section below.

---

## Context for the operator (you, KVK)

This session ratified ADR-297 D11 — **Universal Surface Application**.
Everything operator-visible is a surface; chrome (top bar, dock,
launcher, chat composer) are not exceptions but surfaces mounted into
named layout regions by a compositor. See
`docs/adr/ADR-297-surfaces-as-substrate-mirror.md` §D11 + the
"Implementation path for D11 — Uniform Compositor" section.

The fresh session executes that path (Phases A + B + C minimum;
D + E optional).

---

## PROMPT (copy-paste into fresh session)

```
We're implementing ADR-297 D11 — Universal Surface Application.

READ FIRST (in order):
1. docs/adr/ADR-297-surfaces-as-substrate-mirror.md — full ADR, focus
   on §D11 "Universal Surface Application" and the "Implementation
   path for D11 — Uniform Compositor" section. This is the blueprint.
2. docs/architecture/FOUNDATIONS.md Axiom 6 (Channel) + Derived
   Principle 12 (Channel legibility gates autonomy).
3. docs/adr/ADR-198-surface-archetypes.md — existing archetype catalog
   (Document/Dashboard/Queue/Briefing/Stream). D11 widens this with
   Input / Navigator / Chrome.
4. web/components/shell/AuthenticatedLayout.tsx — the current hardcoded
   shell that D11 dissolves into compositor-driven mounts.
5. api/services/kernel_surfaces.py + api/test_adr297_phase1.py — the
   kernel surface registry that D11 extends.

THE AXIOMATIC COMMITMENT (locked in ADR-297):
Surface = viewport panel. Chrome is not a special case — top bar,
dock, launcher, chat composer are all surfaces mounted into named
layout regions by the compositor. What's "always visible" or
"summon-only" is layout policy (2nd-order), not architectural special-
casing.

EXECUTE PHASES A + B + C (minimum viable D11):

Phase A — Taxonomy + types (~1h):
- Extend ARCHETYPES in api/services/kernel_surfaces.py with `input`,
  `navigator`, `chrome`.
- Add kernel surface declarations: `chat-composer` (Input, default
  region: bottom-fixed), `launcher` (Navigator, floating-overlay),
  `dock` (Navigator, bottom-floating), `top-bar` (Chrome, top).
- web/lib/compositor/types.ts: new LayoutRegion enum (main | top |
  bottom-floating | bottom-fixed | floating-overlay). Surface type
  gains `default_region?` and `default_visibility?` fields.
- Update api/test_adr297_phase1.py regression gate (the +3 new
  archetypes + +4 new chrome surfaces should appear in
  kernel_surface_slugs()).

Phase B — Compositor + Layout (~2h):
- Build web/components/shell/ShellCompositor.tsx. Reads surface
  registry from useComposition(), partitions surfaces by
  default_region, mounts each region's surface(s) via SurfaceRegistry.
- Replace AuthenticatedLayout's hardcoded JSX (top header / main /
  Dock / Launcher mounts) with <ShellCompositor />.
- Each existing chrome element (Dock, Launcher, LauncherButton,
  TopBar) becomes a surface component registered in SurfaceRegistry.
  Their JSX bodies don't change; their *invocation* moves from
  explicit JSX to compositor-driven mounting.
- Verify Dock + Launcher still function operationally (click pinned
  icon → setSurface dispatches → SurfaceViewport swaps → URL updates
  via history.replaceState).

Phase C — Chat composer as Input surface (~1.5h):
- Extract chat composition affordance from web/components/feed-surface/
  (specifically FeedPanel + the composer input within it) into a
  standalone ChatComposerSurface component.
- Register as kernel surface: chat-composer (Input archetype,
  default_region: bottom-fixed, default_visibility: always).
- Feed surface (/feed) trims to pure Stream archetype — timeline read
  only, no composer embedded.
- Remove ThreePanelLayout(conversation=…) calls from all atomic
  surface pages — composer is shell-mounted, not per-surface. Touch:
  - web/app/(authenticated)/cadence/page.tsx (uses ThreePanelLayout)
  - Any other atomic surface with conversation prop
- Mobile divergence: composer surface declares mobile-shape (full-
  screen on summon; bottom-bar-summon-icon when collapsed). Acceptable
  industry-convention compromise per ADR-297 D9.

DISCIPLINE:
- Singular Implementation — every refactor commit lands TS-clean +
  regression gate green. No half-states.
- ADR-209 attribution preserved for substrate writes.
- ADR-297 axiom (surface = viewport panel; URL is transport, not
  identity) holds through every commit.
- Per-slug Next.js routes (/cadence, /mandate, etc.) survive as
  bookmark-safety entry vectors — they don't render content, they
  hydrate DeskState on cold load and the SurfaceViewport in
  AuthenticatedLayout owns the render. This is already wired (commit
  b5d1a1e); D11 builds on top.

OUT OF SCOPE FOR THIS SESSION:
- Phase D (operator-facing layout customization UI)
- Phase E (multi-surface main region — D10 advance)
- Composed surfaces (ADR-297 D10, requires its own ADR)
- ADR-198 catalog formal amendment (D11's archetype additions are
  declared in-place via ADR-297 D11; ADR-198 amendment is a doc-only
  follow-up)

DELIVERABLES:
1. ADR-297 status: §D11 flipped from "declared, not yet implemented"
   → "Implemented" (with date).
2. Three commits (one per phase), each pushed.
3. Regression gate updated + green.
4. Operator-visible result: clicking pinned-Dock icon swaps surface
   content in viewport without URL navigation; chat composer is
   visible at bottom of every atomic surface; Feed surface is pure
   timeline read; no surface carries its own per-surface chat panel.

START with Phase A. After each phase: commit + push + verify TS +
regression gate before proceeding. Use TodoWrite to track phases.

Operator (me) is available for review between phases. Don't bundle
phases unless they would be functionally incomplete separately.
```

---

## Why this prompt is structured this way

- **READ FIRST list** prevents the fresh session from re-litigating
  decisions already made. ADR-297 D11 is the spec; the session
  executes it.
- **Axiomatic commitment block** restates the core decision so the
  session can't drift into chrome-as-special-case patterns under
  context pressure.
- **Phase decomposition** matches the implementation path in
  ADR-297. Each phase is TS-green-deliverable independently.
- **Discipline block** names the load-bearing invariants (Singular
  Implementation, ADR-297 axiom, per-slug routes as bookmark
  transport).
- **OUT OF SCOPE** prevents scope creep into D10 / composed surfaces /
  layout customization UI — those are forward horizons.
- **Deliverables checklist** gives an objective stop signal.

If the fresh session starts proposing a different architecture, point
it at this doc + ADR-297 §D11 and ask why it's diverging.
