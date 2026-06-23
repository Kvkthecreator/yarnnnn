# ADR-358 — Layout Mode: Canvas vs Desktop. The Operator Chooses the Shell's Spatial Paradigm

> **Status:** Implemented (2026-06-23; canvas-fill refinement same-day). `layoutMode ∈ {canvas, desktop}` in `ShellChromeContext` (persisted `yarnnn:shell:layout-mode`, default canvas, SSR-safe post-mount restore) · UserMenu Canvas·Desktop toggle (desktop-only) · ShellCompositor flex-order branch (rail left in canvas, right in desktop) · ChatDrawer dock-side + resize-edge flip · SurfaceViewport single-surface gate (`viewport.isMobile || canvasMode`) · WindowFrame `chromeless` prop · **Desktop layer drops the gray wallpaper + padding in canvas** (`canvasFill` → the one surface fills the column edge-to-edge; not a floating window on a desktop). Gates: `api/test_adr358_layout_mode.py` 39/39 · `api/test_adr316_chat_rail.py` 16/16 (amended — the main-rail mount assertion now checks the durable `{chatRail}`-inside-`<main>` behavior, not the literal call-site position) · `api/test_adr297_phase1.py` 163/163 · `api/test_adr309_two_registers.py` 9/9 · `web` `tsc --noEmit` clean.
> **Authors:** KVK, Claude
> **Resolves a contradiction created by:** [ADR-316](ADR-316-chat-as-dockable-rail.md) (chat as a *fixed* dockable rail — chrome, not a window) **vs** [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D15 (surfaces as a *free-floating* macOS window manager — draggable, resizable on all four edges, z-stacked, cascading). These two decisions assume two different spatial design languages. Until now the shell ran half in each.
> **Amends:** [ADR-316](ADR-316-chat-as-dockable-rail.md) (the rail's left/right side + the "always a fixed rail" claim become **mode-conditional**) · [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D15 (the window manager's free-float + soft-cap-8 become **Desktop-mode-only**; Canvas mode caps visible windows at 1) · [compositor.md](../architecture/compositor.md) (the `main` flex row gains a mode discriminator).
> **Preserves:** [ADR-222](ADR-222-agent-native-operating-system-framing.md) kernel/compositor boundary (layout-mode is a compositor concern; the kernel is untouched) · [ADR-316](ADR-316-chat-as-dockable-rail.md) §Foundational principle (the `Viewing: X` ↔ `surfaceOverride` ↔ prompt-profile binding is **byte-for-byte unchanged in both modes** — `foregrounded` still feeds it) · ESSENCE §The System Shape (chat is how the operator drives the system in *both* modes) · Singular Implementation (one compositor, one chat component, one window manager — a *mode discriminator* over existing machinery, not a fork).
> **Dimensional classification:** **Channel** (Axiom 6 — the operator-facing spatial arrangement of the system).

---

## Context

[ADR-316](ADR-316-chat-as-dockable-rail.md) made chat a **fixed dockable rail** on the right — deliberately *chrome*, deliberately *not* a window. [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D15 made surfaces a **free-floating window manager**: cascade-positioned, draggable by the title bar, resizable on all four edges + four corners, z-stacked, soft-capped at 8 open windows.

The screenshot that triggered *this* discourse was the operator (KVK, 2026-06-23) noticing that these two paradigms **don't reinforce each other — they contradict each other.** Stated in the operator's own words: *if the chat surface becomes fixed/defined, then the other surfaces should follow suit (two panels, side-to-side resize only — the conventional chat+artifact layout); on the other hand, the freely-adjustable multiple-window arrangement is the macOS one, and then chat needs to follow THAT (stay a drawer, or migrate to a surface).*

The diagnosis is exact. There is no coherent third thing. There are **two whole spatial design languages**, and the shell currently welds one to the other at the rail seam:

| | **Canvas** (chat-interface convention) | **Desktop** (macOS convention) |
|---|---|---|
| Chat | Fixed panel | Free (drawer / window) |
| Surfaces | **One** artifact panel beside chat | **Many** floating windows |
| Resize | **Side-to-side only** (one divider) | **All four edges + corners**, drag-anywhere |
| Chat side | **Left** (ChatGPT/Claude convention) | Right rail (or a window) |
| Mental model | ChatGPT / Claude / Cursor canvas | Finder desktop |
| Window cap | **1 visible surface** | Soft cap 8 (ADR-297 D15.3) |

ADR-316 picked "chat is fixed chrome." ADR-297 D15 picked "surfaces float freely." **Welded together, the operator sees a fixed rail beside a floating-window field — half ChatGPT, half Finder.** That mismatch is the fault this ADR resolves.

### Why not just pick one

We considered ratifying a single paradigm and deleting the other. Rejected, for a reason the operator named directly: **both are already built.** ADR-316 shipped the fixed rail with side-to-side resize, postural width, and default-open posture. ADR-297 D15 shipped the full window manager. Throwing either away discards working, tested, operator-validated machinery to win a purity argument the operator doesn't want won.

More importantly, **neither paradigm is wrong** — they serve different operator postures (ESSENCE's Author vs Supervise vs Consult). The chat-interface convention (Canvas) is what most operators expect from an AI product and is calmest for the Author posture (the conversation IS the work, one artifact beside it). The macOS convention (Desktop) is the power-operator's multi-surface supervision view — reading the Queue, the Feed, and a Mandate side-by-side. **The right resolution is not to choose for the operator; it is to let the operator choose**, the same way ADR-316 already made *rail width* an operator-expressed posture dial rather than a kernel decree. This ADR lifts that principle one altitude: **layout *paradigm* is operator-expressed, not kernel-decreed.**

---

## Foundational principle

> **The shell's spatial paradigm is an operator preference, not a fixed architectural fact. Two layout modes — Canvas (chat-left + one artifact-right, side-to-side resize, the chat-interface convention) and Desktop (free-floating macOS window manager + chat as a right rail) — are coherent *whole* arrangements. The operator selects between them at the user-menu level. The compositor reads the choice and arranges the same surfaces + the same chat component + the same window manager accordingly. The `Viewing: X` ↔ `surfaceOverride` ↔ prompt-profile binding is identical in both — only the spatial frame differs.**

Three corollaries:

1. **Internal coherence per mode is the invariant.** Within a mode, chat and surfaces speak the *same* spatial language. Canvas: both are fixed panels, the only resize is the divider between them. Desktop: both float (or chat docks as a rail while surfaces float — see D3). The contradiction this ADR fixes is *cross-mode welding*; the fix is *intra-mode consistency*.

2. **This is Singular Implementation, not a fork.** One `ShellCompositor`, one `ChatDrawer` component, one `useSurfacePreferences` window manager. Layout-mode is a **render-branch discriminator** over that machinery — exactly the shape ADR-316 D5 used for `isMobile` (one component, two layout modes). It does not duplicate the compositor, the chat, or the window manager.

3. **The kernel is untouched.** Layout-mode lives entirely in the compositor (FE). No surface registry change, no `default_region` change, no backend, no schema. Per ADR-222 the compositor *reads* substrate and *arranges* it; choosing the arrangement paradigm is squarely a compositor responsibility.

---

## The decision

### D1 — A single operator preference `layoutMode ∈ {canvas, desktop}`, stored client-side, chosen at the user menu

A new preference `yarnnn:shell:layout-mode` (localStorage, mirroring `yarnnn:shell:chat-drawer-open` + `yarnnn:shell:chat-drawer-width`) carries the operator's choice. It is read by the compositor and exposed through `ShellChromeContext` (the existing home for chrome-shared state — `drawerOpen`, `launcherOpen` already live there).

**Default: `canvas`.** The chat-interface convention is what most operators arriving at an AI product expect, and it is the calmest Author-posture default. Desktop multi-window is the deliberate opt-in for operators running multi-surface supervision. (This is a product call, not only a layout call — see §Default rationale.)

The toggle lives in the **UserMenu** ([web/components/shell/UserMenu.tsx](../../web/components/shell/UserMenu.tsx), the initials-avatar dropdown rendered right of TopBarSurface) — the OS "System Settings"-adjacent home for shell-wide preferences (ADR-338 management-plane vocabulary). A two-item segmented control or radio: **Canvas · Desktop**. Switching is instant (a render branch), non-destructive (no window state is discarded — Desktop's `window-state` localStorage survives a trip through Canvas and is restored on switch-back), and SSR-safe (server renders the default; the post-mount effect applies the stored choice, mirroring the `drawerOpen` initializer pattern exactly — no hydration mismatch).

### D2 — Canvas mode: chat-LEFT + one artifact surface RIGHT, side-to-side divider only

In Canvas mode the `main` flex row inverts and constrains:

```
┌──────────────────────────────────────────────────┐  top: TopBarSurface (chrome)
├────────────────┬─────────────────────────────────┤
│  ChatRail      │  SurfaceViewport                 │  main: flex row (Canvas)
│  (LEFT,        │  (flex-1)                        │
│   width,       │  ┌── ONE surface, full-bleed ─┐  │
│   resizable)   │  │  HOME (no window chrome)   │  │
│  [Viewing: X]  │  │                            │  │
│  [conversation]│  └────────────────────────────┘  │
│  [Ask YARNNN…] │                                  │
└────────────────┴─────────────────────────────────┘
        ↑ the ONLY resize handle: the side-to-side divider
```

Concretely:
- **Chat docks to the LEFT** (the ChatGPT/Claude/Cursor convention — conversation reads left-to-right into the artifact). In Desktop mode the rail stays RIGHT (ADR-316 verbatim). The side is mode-conditional in `ChatDrawer`'s desktop branch: `order` / which-edge-the-resize-handle-sits-on flips on `layoutMode`. The resize *math* is unchanged (clamp MIN/MAX); only the anchored edge flips.
- **The left is ONE primary surface filling the column — not a desktop with a floating window on wallpaper.** This is the operator's load-bearing correction (2026-06-23): in Canvas the window area is *the surface*, sized to fill, immovable; the only resize is the chat↔surface divider. Concretely Canvas forces `MAX_VISIBLE = 1` *and* drops the desktop frame: the `Desktop` layer's gray wallpaper + padding are suppressed when a surface is mounted in canvas (`canvasFill = layoutMode === 'canvas' && hasWindows` → `bg-background`, no padding), so the surface fills edge-to-edge; `WindowFrame` renders `chromeless` (no title bar, no border, no rounding) and non-interactive (no drag/resize handles). Desktop mode keeps the D17 wallpaper + floating windows. The render path **reuses** `SurfaceViewport`'s existing single-surface `visibleSlug` branch — today gated on `viewport.isMobile && hasWindows` — extended to `viewport.isMobile || canvasMode`. Switching surface (Dock click / Launcher) replaces the visible one; the others stay mounted-but-hidden (D13 multi-mount lifecycle preserved — state is not lost). The FAB survives in both modes (chat is closable + re-summonable).
- **The only resize is the divider** between chat-left and surface-right. No per-window resize, because there is one full-bleed surface.

### D3 — Desktop mode: ADR-297 D15 window manager + chat as the ADR-316 right rail, both verbatim

Desktop mode is **today's shipped behavior, unchanged**: free-floating cascade windows (drag, resize-4-edges, z-stack, soft-cap-8) per ADR-297 D15, with chat as the right-docked rail per ADR-316. Nothing about Desktop mode is new — this ADR's only act on Desktop mode is to scope it behind `layoutMode === 'desktop'` so Canvas can be the alternative.

**The one resolved question from the trigger discourse** — *"chat keeps the drawer aspect OR migrates to a surface"* — is resolved as **keep the drawer/rail**. Chat stays chrome (the ADR-316 chat-as-chrome decision holds in Desktop mode; ADR-316 Alternative A "chat as a tiled window" remains rejected for the same reason — the command channel must not compete for `MAX_OPEN_WINDOWS` slots or be closable like content). Canvas mode makes chat a *fixed* panel (still chrome, not a window); Desktop mode makes chat a *dockable* rail (still chrome). In neither mode is chat a window. **Chat is never a window** — that invariant survives both modes and keeps the boundary clean (window manager owns surfaces; chat is the channel over them).

### D4 — Window geometry, cap, and Dehydration are mode-aware in exactly the spots ADR-316 D6 already touched

ADR-316 D6 already made window geometry clamp to the **Desktop container width** (not `window.innerWidth`) via `setDesktopBounds` + `computeMaximizedGeometryFromBounds`. That seam is where Canvas constrains:
- In Canvas mode the window manager renders one full-bleed surface, so cascade/maximize/drag math is inert (no multi-window arrangement to compute). The `MAX_OPEN_WINDOWS = 8` soft cap is replaced by `MAX_VISIBLE = 1` rendering — windows beyond the foregrounded one are mounted-hidden, not tiled.
- `desktopBounds` already reflects the flex-1 column width (which excludes the rail), so the Canvas full-bleed surface fills its column correctly with no new measurement.
- Switching modes does **not** discard `window-state` — Desktop's per-window geometry persists across a Canvas excursion and is restored on return (the operator's Finder arrangement survives).

### D5 — Mobile is unaffected and mode-independent

Below `MOBILE_BREAKPOINT_PX = 640`, both modes already collapse to the same thing: one full-screen surface + chat as a full-screen overlay (ADR-316 D5 + ADR-297 D15.2). Layout-mode is a **desktop-only** concern; on mobile the toggle is hidden (or inert) because there is one physically-possible arrangement. No second mobile path.

---

## What this ADR explicitly does NOT do

- **It does not make chat a window** in either mode. Chat stays chrome (fixed panel in Canvas, dockable rail in Desktop). ADR-316 Alternative A stays rejected.
- **It does not change the `surfaceOverride` payload, the backend context dispatch, or ADR-186 profile resolution.** `foregrounded` feeds `Viewing: X` + the agent context identically in both modes.
- **It does not touch the kernel** — no surface registry, `default_region`, backend, schema, or Render-service change. FE compositor only.
- **It does not delete the window manager or the rail.** Both survive; layout-mode scopes which is active.
- **It does not add a third mode.** Two whole arrangements; the contradiction was *welding*, the fix is *choosing*.

---

## Alternatives considered

### A — Pick one paradigm, delete the other (rejected)

Ratify either Canvas or Desktop as the sole shell and delete the loser. Purest Singular Implementation at the *paradigm* layer. **Rejected** because (a) both are built, tested, and operator-validated — deletion discards working machinery to win a purity argument; (b) the two serve genuinely different operator postures (Author-calm vs multi-surface-supervision); (c) the operator explicitly asked to *choose*, not to have one chosen. Singular Implementation is honored at the *machinery* layer (one compositor / chat / window manager) without forcing a single *arrangement*.

### B — Auto-switch mode based on surface count / posture (rejected for v1)

Derive the mode: stay Canvas until the operator opens a 2nd surface, then auto-promote to Desktop. Tempting (it makes the mode "derived, never stored," echoing ADR-340's attention-routing principle). **Rejected for v1** because mode-switching is a large visual reflow — doing it *automatically* mid-session is disorienting (the operator's chat jumps left↔right, the surface gains/loses window chrome). An explicit, operator-owned toggle is calmer and more legible. The derived-mode idea is recorded as a **forward horizon** (§Forward horizon) once the explicit toggle proves the two modes are individually correct.

### C — Canvas = ADR-316 rail kept on the RIGHT + window-cap-1 (rejected)

Make Canvas mode just "Desktop with a 1-window cap" — chat stays the right rail, surface fills the rest. Less code (no left/right flip). **Rejected** because it isn't the chat-interface convention the operator named: ChatGPT/Claude/Cursor put chat on the LEFT and the artifact on the RIGHT. A right-rail-+-single-surface reads as "a Desktop with one window," not "a canvas." The left-flip (D2) is what makes Canvas mode *feel* like the convention it's meant to match. The operator chose this explicitly.

---

## Default rationale

Defaulting to **Canvas** is a product position, not only a layout default:
- It matches the dominant AI-product convention (chat + artifact), lowering the "what is this OS?" cost for new operators.
- It is the calmest Author-posture default — the floor of the ESSENCE loop, where most early operators live.
- Desktop multi-window is a *deepening* affordance (multi-surface supervision = ESSENCE Loop 2), appropriately opt-in.

Operators who prefer the macOS arrangement flip once; the choice persists. If telemetry later shows most operators flip to Desktop, the default is a one-line change — the machinery is symmetric.

---

## Implementation plan

Single PR, FE-only. No backend, no schema, no env vars, no Render-service impact.

1. **`layoutMode` state in `ShellChromeContext`** — add `layoutMode: 'canvas' | 'desktop'` + `setLayoutMode`, persisted to `yarnnn:shell:layout-mode`, default `canvas`, restored post-mount (mirror the `drawerOpen` initializer exactly — SSR renders default, effect applies stored choice, no hydration mismatch).
2. **UserMenu toggle** ([UserMenu.tsx](../../web/components/shell/UserMenu.tsx)) — a Canvas · Desktop segmented control reading/writing `layoutMode`.
3. **`ShellCompositor` `main` row reads `layoutMode`** — Canvas: chat-left + flex-1 surface column (order flips); Desktop: flex-1 surface column + chat-right (today's order). The flex-row itself is shared; `order` / sibling-order is the branch.
4. **`ChatDrawer` desktop branch: mode-conditional anchored edge** — Canvas docks left (resize handle on the right edge); Desktop docks right (resize handle on the left edge, ADR-316 verbatim). One resize handler, mirrored edge. Posture-width defaults (AUTHOR/SUPERVISE) apply in both.
5. **`SurfaceViewport`: Canvas reuses the existing `visibleSlug` single-surface branch** — today gated on `viewport.isMobile && hasWindows`, extend the gate to also fire on `layoutMode === 'canvas'` (one `WindowFrame`, full-bleed). Add a `chromeless` prop to `WindowFrame` so Canvas suppresses the title bar + drag/resize handles (mobile keeps them per ADR-297 D15.2). Desktop mode's multi-window `mountSlugs.map(...)` branch is unchanged. `window-state` is preserved across mode switches (not cleared).
6. **Doc cascade** — update [compositor.md](../architecture/compositor.md) (`main` flex row gains the mode discriminator); add the supersession/amendment banners to ADR-316 (rail side + fixed-claim now mode-conditional) and ADR-297 D15 (free-float + cap-8 now Desktop-mode-only). No CHANGELOG (no prompt change).
7. **Regression gate** — `web/lib/shell/__tests__` (or the existing ADR-316/297 gate style): assert (a) `layoutMode` persists + defaults canvas, (b) Canvas mounts exactly one visible surface with no window chrome, (c) Canvas docks chat left, Desktop docks chat right, (d) the `surfaceOverride`/`Viewing:` binding is identical across modes, (e) Desktop `window-state` survives a Canvas round-trip.

---

## Definition of done

- The UserMenu offers Canvas · Desktop; the choice persists across reloads and defaults Canvas.
- **Canvas mode:** chat is a fixed LEFT panel; exactly one surface fills the RIGHT, full-bleed, no window chrome; the only resize is the side-to-side divider. Reads as the ChatGPT/Claude convention.
- **Desktop mode:** byte-for-byte today's behavior — free-floating cascade windows (ADR-297 D15) + right-docked chat rail (ADR-316).
- Switching modes is instant, non-destructive (Desktop window arrangement survives a Canvas excursion), and SSR-safe.
- `Viewing: X` → `surfaceOverride` → ADR-186 profile binding is identical in both modes.
- One compositor, one chat component, one window manager. No paradigm fork. Mobile unaffected.

---

## Forward horizon

- **Derived mode (Alternative B)** — once both modes are proven individually correct, auto-promotion (Canvas → Desktop on 2nd-surface-open) becomes a calm option, echoing ADR-340's "attention routing is OS-owned, derived-never-stored." Deferred until the explicit toggle validates the modes.
- **Per-workspace / per-program default** — a program bundle could declare its preferred default mode (a trading cockpit wants Desktop multi-surface; an authoring workspace wants Canvas). A `MANIFEST.yaml` hint feeding the default, overridable by the operator. Deferred — operator preference is the v1 source of truth.

---

## Related

- [ADR-316](ADR-316-chat-as-dockable-rail.md) — chat as a dockable rail (the fixed-rail decision this ADR makes mode-conditional)
- [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) — surfaces-as-windows + D15 window manager (the free-float this ADR scopes to Desktop mode)
- [ADR-312](ADR-312-home-as-composition.md) — Home as composition (the surface that fills the Canvas right panel by default)
- [ADR-338](ADR-338-management-plane.md) — management plane (the System-Settings vocabulary the UserMenu toggle lives in)
- [ADR-340](ADR-340-operator-experience-model.md) — operator experience model (the derived-mode forward horizon)
- [ADR-186](ADR-186-yarnnn-prompt-profiles.md) — prompt profiles (resolved from `foregrounded`, identical in both modes)
- [ESSENCE](../ESSENCE.md) — §The System Shape, §The User Experience Loop (Author vs Supervise postures the two modes serve)
- [compositor.md](../architecture/compositor.md) — the compositor seam the mode discriminator lives in
