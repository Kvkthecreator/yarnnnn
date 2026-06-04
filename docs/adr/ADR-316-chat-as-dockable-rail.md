# ADR-316 — Chat as a Dockable Rail, Not an Occluding Overlay. The Command-Line Over the Active Surface

> **Status:** Implemented (2026-06-04). Backend region (`main-rail`) + FE compositor types + ShellCompositor flex-row + ChatDrawer two-mode (rail desktop / overlay mobile) + Desktop-relative window geometry (D6 via `setDesktopBounds` + `computeMaximizedGeometryFromBounds`) all landed. Gates: `api/test_adr316_chat_rail.py` 16/16 · `api/test_adr297_phase1.py` 137/137 · `api/test_adr309_two_registers.py` 9/9 · `web` `tsc --noEmit` clean.
> **Authors:** KVK, Claude
> **Supersedes:** the chat-as-`floating-overlay` decision from [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D16 (the `ChatDrawerSurface` mounted in the `floating-overlay` region, `position: fixed`, occluding `main`). The `surfaceOverride` ↔ `Viewing:` ↔ window-manager binding from D16 §5 is **preserved and strengthened** — only the spatial mounting changes.
> **Amends:** [ADR-309](ADR-309-two-registers-settings-and-applications.md) (chat is neither register — it is the window manager's own *command channel*, a third class of chrome alongside top-bar + Dock; this ADR names it) · [compositor.md](../architecture/compositor.md) (the "chat-drawer is chrome" line is made literal: chrome *frames* content, it does not *occlude* it) · [ADR-186](ADR-186-yarnnn-prompt-profiles.md) (the foregrounded surface that drives `surfaceOverride` is the same signal that resolves the prompt profile — co-visibility makes the binding legible).
> **Preserves:** [ADR-222](ADR-222-agent-native-operating-system-framing.md) kernel/compositor boundary (chat is chrome the window manager owns, not a surface-window competing for slots) · [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) window manager, Desktop layer, WindowFrame, multi-mount (unchanged — surfaces are still windows) · [ADR-216](ADR-216-orchestration-surface-vs-judgment-persona.md) (YARNNN-the-surface is *how the operator drives the system*; the rail is that driving channel) · [ESSENCE](../ESSENCE.md) §The System Shape (chat is orchestration, not a window among many) · [FOUNDATIONS](../architecture/FOUNDATIONS.md) Axioms 1–9.
> **Dimensional classification:** **Channel** (Axiom 6 — the operator-facing window onto the system).

---

## Context

The screenshot that triggered this discourse: an operator on `/home` watching the Reviewer author `standing_intent.md` on its own initiative and narrate its reasoning about MANDATE authority. The chat header read **"Reviewer · Viewing: Home."** But the chat was a `position: fixed` overlay drawer occupying the right half of the viewport — **so the Home it claimed to be "Viewing" was occluded by the very panel making the claim.**

That is the fault this ADR fixes. It is small in code and load-bearing in concept.

### What the operator is actually doing in the OS

[ESSENCE](../ESSENCE.md) is explicit that YARNNN **is not a chat UI** ("YARNNN the chat surface is how the operator drives a running system, not the whole product"). The core interaction is **supervision of an operation that runs without the operator**, by reading substrate and rendering verdicts on what it proposes (ESSENCE Loop 2). There are three operator postures, and the operator's relationship to chat *inverts* across them:

| Posture | What the operator does | Chat's role |
|---|---|---|
| **Author** (Loop 1, the floor) | Writes/corrects substrate by talking | Chat is the workspace; substrate is the byproduct |
| **Supervise** (Loop 2, the deepening) | Reads operation state; approves/rejects from the Queue; audits the judgment trail | Chat is a **side-channel for intervention** — the surface must stay visible |
| **Consult** (cross-cutting) | "Why did you author that?", "What's my exposure?" | Chat **over a specific surface** — the thing being asked about must stay visible |

In two of three postures, **the surface must remain co-visible with chat.** The occluding overlay breaks that in exactly the postures that matter most for the supervised-autonomy loop YARNNN exists to run.

### Why the overlay is the un-hardening

[ADR-309](ADR-309-two-registers-settings-and-applications.md) hardened "surface" into two registers (System Settings + Applications) sharing one window manager, and named chrome — "top-bar, launcher, chat-drawer" — as *neither register*, "the window manager's own framing." That classification is correct. But the chat-drawer's *implementation* contradicts the word "framing": chrome that frames content sits beside it; this chrome sits **on top of** content via `position: fixed` + `z-index: 101` in the `floating-overlay` region, a sibling outside the `main` flex column ([ShellCompositor.tsx:118-136](../../web/components/shell/ShellCompositor.tsx#L118-L136)).

So the un-hardening is precise: **chat is classified as framing but implemented as occlusion.** This ADR makes the implementation match the classification.

---

## Foundational principle

> **Chat is the OS shell's command line over the active surface — a dockable rail that *reduces* the surface area, never an overlay that *covers* it. `Viewing: X` is a load-bearing binding between the conversation and the surface in view: the same foregrounded slug that names the surface scopes the agent's context and resolves its prompt profile.**

Two corollaries:

1. **Chat is chrome, not a window.** It does not enter the window manager's `open`/`foregrounded`/`windowStates` registry. Surfaces are windows (ADR-297); chat is the command channel over whichever surface is foregrounded. This keeps Singular Implementation: two paradigms (surfaces-as-windows, chat-as-chrome), cleanly separated — not three.

2. **The rail width is the posture dial.** Narrow when supervising (operator mostly reads the surface, occasionally types); wide when authoring (the conversation *is* the work). No explicit mode toggle — a draggable divider plus a sensible per-surface default expresses posture.

---

## The decision

### D1 — Chat moves from `floating-overlay` (fixed, occluding) to a flex sibling of `SurfaceViewport` inside `main`

The `main` region becomes a **flex row**:

```
┌──────────────────────────────────────────────────┐  top: TopBarSurface (chrome)
├─────────────────────────────────┬────────────────┤
│  SurfaceViewport (flex-1)        │  ChatRail      │  main: flex row
│  ┌── windows (absolute) ──┐      │  (width,       │
│  │ HOME · Queue · Mandate │      │   resizable)   │
│  └────────────────────────┘      │  [Viewing: X]  │
│                                  │  [conversation]│
│                                  │  [Ask YARNNN…] │
└─────────────────────────────────┴────────────────┘
```

`SurfaceViewport`'s window-layout area is the flex-1 column; the rail is its right sibling. When the rail is open, the window area is genuinely narrower — windows tile within it, never under the rail. The `floating-overlay` region survives in the `LayoutRegion` union (Launcher still uses it) but **no longer hosts chat**.

### D2 — `position: fixed` → flex child; the existing left-edge resize is retained verbatim

The drawer already resizes from its left edge and persists width to `localStorage` ([ChatDrawer.tsx:90-124](../../web/components/shell/chrome/ChatDrawer.tsx#L90-L124)). The resize math (`window.innerWidth - e.clientX` clamped to MIN/MAX) is unchanged — it already computes a right-rail width. Only the element's `position` changes from `fixed` to a flex child with `flex: 0 0 {width}px`. The conversation panel stays mounted across open/close (D18.1 preserved — no state loss).

### D3 — The `Viewing: X` ↔ `surfaceOverride` ↔ prompt-profile binding is preserved and made legible

This binding already exists end-to-end and is the most valuable part of the current implementation:

- `foregrounded` (window manager) is the single source feeding both the `Viewing: X` label **and** the `surfaceOverride` payload sent to the agent ([ChatDrawer.tsx:56-71](../../web/components/shell/chrome/ChatDrawer.tsx#L56-L71)).
- The backend dispatches context on `surface.type`/`surface.slug` ([feed.py:722+](../../api/routes/feed.py#L722)) — which is the same signal ADR-186 resolves the prompt profile from.

This ADR changes **nothing** about that contract. It removes the occlusion that *undermined* it: previously the operator was told "Viewing: Home" while Home was covered; now the binding is honest because Home stays on screen. **The act of foregrounding a surface (`foregroundSurface(slug)`) both raises the window AND scopes the conversation — one gesture, two effects.** No separate "set chat context" mechanism is introduced or needed.

### D4 — The FAB toggles rail visibility (collapse to reclaim full surface width); semantics, not verb, change

The FAB ([Desktop.tsx:132-149](../../web/components/shell/Desktop.tsx#L132-L149)) keeps its `toggleDrawer` verb and viewport-fixed bottom-right position (`Z_FAB=150`). What changes is meaning: open = rail docked (surface narrows); closed = rail collapsed (surface full-width). The FAB remains the always-addressable summon affordance — the property ESSENCE requires of YARNNN-the-surface ("how the operator drives the system" must be reachable from anywhere). Hidden via `opacity-0` when the rail is open (unchanged).

### D5 — Mobile/narrow (`< MOBILE_BREAKPOINT_PX = 640`) keeps the overlay; the rail degrades to a full-screen takeover

Split is impossible below 640px. The existing `isMobile` branch already does full-screen takeover ([ChatDrawer.tsx:54](../../web/components/shell/chrome/ChatDrawer.tsx#L54), [useViewport.ts](../../web/lib/shell/useViewport.ts)). On mobile the chat renders as it does today (overlay), because there is no co-visible surface to honor. This is **not a second paradigm** — it is the same component choosing flex-sibling on wide and overlay on narrow, gated by the existing `isMobile` signal. The `Viewing:` label on mobile reverts to a breadcrumb (the surface is not co-visible by physical necessity), which is honest.

### D6 — Window geometry clamps against the Desktop container width, not `window.innerWidth`

The one real risk. Windows are absolute-positioned against `window.innerWidth` in cascade/maximize math ([useSurfacePreferences.tsx:362-374](../../web/lib/shell/useSurfacePreferences.tsx#L362-L374), [surface-preferences.ts](../../web/lib/shell/surface-preferences.ts) `computeMaximizedGeometry`). With the rail reducing the window area, windows computed against full viewport width would overflow under the rail. The fix: geometry math reads the **Desktop container's** measured width (which flex already reduces by the rail width), not `window.innerWidth`. There is precedent for both adding and removing such clamps — D19.5.1 *deleted* a `FAB_RESERVED` clamp when the FAB moved above windows. This ADR is the inverse: the rail is a genuine layout citizen, so the window area's available width is the container's, not the viewport's. `maximize` snaps to the container; cascade origins from the container box.

### D7 — Z-tiers simplify on desktop; survive for the mobile overlay branch

`Z_DRAWER_BACKDROP` (100) and `Z_DRAWER_BODY` (101) are overlay-only concepts. On desktop the rail is a flex child with no backdrop and no special z (it sits in normal flow beside the window area). Both constants survive in [z-tiers.ts](../../web/lib/shell/z-tiers.ts) **for the mobile overlay branch only** — Singular Implementation is honored because there is one chat component with two layout modes, not two components.

---

## What this ADR explicitly does NOT do

- **It does not make chat a window.** Chat never enters `useSurfacePreferences`' `open`/`windowStates` registry. Surfaces are windows; chat is chrome. (The "chat as a tiled window" alternative was considered and rejected — see below.)
- **It does not change the `surfaceOverride` payload, the backend context dispatch, or ADR-186 profile resolution.** Those are correct; the occlusion was the only fault.
- **It does not change the FAB position, the launcher, the Dock, or the top-bar.** Only chat's mounting and layout participation change.
- **It does not touch mobile behavior** beyond confirming the overlay is correct there.

---

## Alternatives considered

### A — Chat as a tiled surface-window (rejected)

Delete the drawer entirely; let chat be one more surface-window in the ADR-297 window manager, snappable beside Home. Purest Singular Implementation (no separate chat layout code). **Rejected** because it demotes chat from "always-addressable shell command channel" to "one window among many competing for `MAX_OPEN_WINDOWS` slots." That contradicts ESSENCE's framing of YARNNN-the-surface as *how the operator drives everything* (ADR-216) — the command channel must not be subject to the soft cap or to being closed like content. Chat-as-chrome (this ADR) keeps the boundary clean: window manager owns *surfaces*; chat is the channel *over* them.

### B — Keep the overlay, just narrow it (rejected)

Make the overlay thin enough that "most" of the surface shows. **Rejected** — occlusion of *any* part of a co-bound surface still breaks the `Viewing:` contract, and "thin overlay" is a worse version of "dock the rail" (the surface still can't reflow into the reclaimed space).

### C — Both overlay and split, fully separate code paths (rejected as stated, satisfied in spirit)

A fully forked overlay-vs-split implementation. **Rejected** as two implementations — but the *intent* (overlay on narrow, split on wide) is satisfied by D5's single-component / two-layout-modes design gated by the existing `isMobile` signal. One component, one resize handler, one width store; the layout mode is a render branch, not a parallel path.

---

## Implementation plan

Single PR, reviewable in steps. No backend changes, no schema, no env vars, no Render-service impact (FE-only).

1. **Move chat out of `floating-overlay`, into `main` as a flex sibling.** `ShellCompositor` `main` region → flex row: `SurfaceViewport` (flex-1) + `ChatRail` (flex `0 0 {width}`, desktop) / overlay (mobile). Remove chat from the `floating-overlay` `mountRegion` call; mount the rail inside `main`.
2. **Convert `ChatDrawer`'s root from `position: fixed` to flex child on desktop; keep the `isMobile` overlay branch.** Retain the left-edge resize + width store verbatim. Drop the backdrop on the desktop branch.
3. **Reframe window geometry math** to clamp against the Desktop container width, not `window.innerWidth` (D6). Verify `maximize` + cascade origin against the container box.
4. **FAB semantics** (D4): docstring + label update ("Open conversation" → unchanged verb; the meaning is now dock/undock the rail).
5. **Per-surface default rail width** (the posture dial) — **DEFERRED**. The rail mechanics shipped: it docks/reduces, drag-resizes, persists one width. The *auto-posture* refinement (substrate-forward Home → wider author default; operation-running Home with populated Queue → narrower supervise default, read from Home's activation/composition state) is a follow-on — the manual drag handle already expresses posture; the auto-default is a convenience that depends on Home composition state and is best landed once the operator has used the rail. Recorded honestly rather than silently scoped in.
6. **Doc cascade:** update [compositor.md](../architecture/compositor.md) "chat-drawer is chrome" line to "chat is the dockable command rail — chrome that frames, never occludes"; mark ADR-297 D16's `floating-overlay` chat mounting superseded; mark ADR-309's chat-drawer reference. CHANGELOG not required (no prompt change). **Landed.**
7. **Regression gate:** `api/test_adr316_chat_rail.py` (16 assertions — region is `main-rail` not `floating-overlay`, `main` is a flex row, main-rail mounted inside `<main>`, desktop-relative geometry seam wired, ChatDrawer carries both layout modes). **Landed — 16/16.**

---

## Definition of done

- On desktop, opening chat **narrows** the surface area; the foregrounded surface stays fully visible and reflows. "Viewing: Home" is honest — Home is on screen.
- Windows never render under the rail (geometry clamps to container).
- On mobile (<640px), chat is a full-screen overlay (unchanged); `Viewing:` degrades to breadcrumb.
- The `surfaceOverride` → backend context → ADR-186 profile binding is byte-for-byte unchanged.
- One chat component, two layout modes, one resize handler, one width store. No `floating-overlay` chat. No chat in the window registry.

---

## Related

- [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) — window manager; surfaces-as-windows (preserved); D16 chat-drawer mounting (superseded here)
- [ADR-309](ADR-309-two-registers-settings-and-applications.md) — two registers; chrome-is-neither-register (this ADR names chat as the command-channel class of chrome)
- [ADR-312](ADR-312-home-as-composition.md) — Home as composition; the rail's per-surface width default reads Home's activation/composition state
- [ADR-186](ADR-186-yarnnn-prompt-profiles.md) — prompt profiles; resolved from the same foregrounded slug the rail binds
- [ADR-216](ADR-216-orchestration-surface-vs-judgment-persona.md) — YARNNN-the-surface is orchestration, the channel the operator drives the system through
- [ESSENCE](../ESSENCE.md) — §The System Shape, §The User Experience Loop (the three operator postures)
- [compositor.md](../architecture/compositor.md) — the compositor seam; chat-as-chrome line
