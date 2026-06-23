# ADR-358 — Layout Mode: Canvas vs Desktop. The Operator Chooses the Shell's Spatial Paradigm

> **Status:** Implemented (2026-06-23; revised same-day after operator review — see D2/D3 revision notes). `layoutMode ∈ {canvas, desktop}` in `ShellChromeContext` (persisted `yarnnn:shell:layout-mode`, default canvas, SSR-safe). **Canvas:** surface fills the LEFT edge-to-edge (`canvasFill` drops the desktop wallpaper/padding; `WindowFrame` `chromeless` + non-interactive single-surface), chat docks RIGHT as a flex rail; side-to-side divider only. **Desktop:** ADR-297 D15 free-floating window manager unchanged + chat as a **summoned `position: fixed` overlay** (FAB-summoned, zero flex space — NOT a fixed rail), so Desktop no longer "feels like a fixed layout." Chat is chrome in every mode, never a window — `railMode` (canvas+wide) docks, `overlayMode` (desktop+mobile) summons. ShellCompositor order is fixed (surface, then rail); the docked-vs-overlay decision lives in ChatDrawer. Default-open posture is mode-aware (open canvas-rail / closed desktop-overlay) and re-derives on toggle. UserMenu Canvas·Desktop toggle (desktop-only). **D5 (navigation stays on `/desktop`):** `foregroundSurface` + `navigateToSurface` deliver pane/params via `history.replaceState` (pathname preserved), never `router.push` to a surface page route — so chat persists across navigation and the URL stays `/desktop`. **D6 (window-namespaced params):** every intra-surface deep-link param is namespaced by its window's slug (`{slug}.{key}` — `workspace-settings.pane`, `settings.pane`, `recurrence.pane`/`.task`, `agents.agent`) so multiple open windows never collide on the shared query string; one helper `scopeParamKey` forms the prefix, `navigateToSurface` scopes by target slug, surfaces use the `useSurfaceParam(slug)` hook, `SettingsPaneShell` takes a `windowSlug` prop, all redirect stubs + `ACTIVITY_ROUTE` target namespaced params. Gates: `api/test_adr358_layout_mode.py` 41/41 · `api/test_adr316_chat_rail.py` 16/16 · `api/test_adr297_navigation_enactment.py` 22/24 (2 fails are pre-existing `operation`-slug registry drift, ADR-349 era — unrelated) · `api/test_adr340_p2_settings_fold.py` 92/92 (windowSlug-scoped) · `api/test_adr297_d196_intra_surface_nav.py` 26/26 (useSurfaceParam) · `api/test_adr340_d8_machinery_fold.py` 31/32 (1 fail is pre-existing recurrence launcher-tier drift — unrelated) · `api/test_adr308_redirect_stubs_transport.py` 13/13 · `api/test_adr297_phase1.py` 163/163 · `web` `tsc --noEmit` clean.
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
| Chat | Docked fixed rail (RIGHT) | **Summoned overlay** (FAB, floats — not pinned) |
| Surfaces | **One** surface fills the column | **Many** floating windows |
| Resize | **Side-to-side only** (one divider) | **All four edges + corners**, drag-anywhere |
| Chat side | **Right** (surface-left, chat-right) | Overlay slides in from the right, over the windows |
| Mental model | ChatGPT / Claude / Cursor canvas | Finder desktop (everything floats, chat too) |
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

### D2 — Canvas mode: ONE surface fills the LEFT, chat docks RIGHT, side-to-side divider only

> **Revised 2026-06-23 (operator review):** chat docks **RIGHT** in Canvas (surface fills the left). The original D2 put chat left (ChatGPT convention); the operator chose surface-left/chat-right (the artifact leads, chat is the assistant beside it). Equivalent geometry, opposite anchor.

```
┌──────────────────────────────────────────────────┐  top: TopBarSurface (chrome)
├─────────────────────────────────┬────────────────┤
│  SurfaceViewport (flex-1)        │  ChatRail      │  main: flex row (Canvas)
│  ┌── ONE surface, full-bleed ─┐  │  (RIGHT,       │
│  │  HOME (no window chrome)   │  │   width,       │
│  │  fills the column          │  │   resizable)   │
│  │                            │  │  [Viewing: X]  │
│  └────────────────────────────┘  │  [conversation]│
│                                  │  [Ask YARNNN…] │
└─────────────────────────────────┴────────────────┘
                ↑ the ONLY resize handle: the side-to-side divider
```

Concretely:
- **Chat docks to the RIGHT** (surface-left/chat-right — the artifact is the focus, chat the assistant beside it). The rail's border sits on its left edge; the drag handle is on its left edge; resize width = `innerWidth − e.clientX` (ADR-316 geometry, unchanged).
- **The left is ONE primary surface filling the column — not a desktop with a floating window on wallpaper.** In Canvas the window area is *the surface*, sized to fill, immovable; the only resize is the chat↔surface divider. Canvas forces `MAX_VISIBLE = 1` *and* drops the desktop frame: the `Desktop` layer's gray wallpaper + padding are suppressed when a surface is mounted in canvas (`canvasFill = layoutMode === 'canvas' && hasWindows` → `bg-background`, no padding), so the surface fills edge-to-edge; `WindowFrame` renders `chromeless` (no title bar, no border, no rounding) and non-interactive (no drag/resize handles). The render path **reuses** `SurfaceViewport`'s single-surface `visibleSlug` branch — extended from `viewport.isMobile` to `viewport.isMobile || canvasMode`. Switching surface (Dock click / Launcher) replaces the visible one; the others stay mounted-but-hidden (D13 multi-mount lifecycle preserved).
- **The only resize is the divider** between surface-left and chat-right. No per-window resize — there is one full-bleed surface.

### D3 — Desktop mode: free-floating window manager + chat as a SUMMONED OVERLAY (not a fixed rail)

> **Revised 2026-06-23 (operator review):** Desktop-mode chat is **not** a fixed right rail. The operator observed the rail "feels like a fixed layout, but it shouldn't" — in a free-floating desktop, a pinned rail is the one thing that doesn't float. So in Desktop mode chat reverts to the **pre-ADR-316 summoned overlay**: closed by default, FAB-summoned, a `position: fixed` right-side panel sliding over the floating windows; it consumes **zero flex space** (does not reduce/pin the layout). This restores the "everything floats in Desktop, chat included" coherence.

Desktop mode keeps the ADR-297 D15 window manager unchanged (free-floating cascade windows — drag, resize-4-edges, z-stack, soft-cap-8). What changes vs the first ADR-358 cut: chat is an **overlay**, not a rail.

**The trigger-discourse question** — *"chat keeps the drawer aspect OR migrates to a surface"* — is resolved as **keep the drawer (overlay), reject chat-as-surface**. Recommendation rationale (delegated to the implementer, KVK 2026-06-23): chat-as-a-window would re-open ADR-316 Alternative A — the command channel must not be closable/buryable/cap-subject like content, and making it a window in Desktop but chrome in Canvas would re-introduce the very cross-mode inconsistency this ADR exists to kill. The overlay reuses the proven mobile branch (one component, one render path) and keeps the durable invariant: **chat is chrome in EVERY mode, never a window** — only *docked* (Canvas rail) vs *summoned* (Desktop/mobile overlay) varies. That is a one-axis variation, trivially extensible.

The default-open posture is therefore mode-aware: **Canvas (wide) → rail defaults OPEN** (the two-panel composition); **Desktop + mobile → overlay defaults CLOSED** (it would otherwise pop open over the windows). Switching mode re-derives the posture (→Canvas opens the rail; →Desktop closes the overlay).

### D4 — Window geometry, cap, and Dehydration are mode-aware in exactly the spots ADR-316 D6 already touched

ADR-316 D6 already made window geometry clamp to the **Desktop container width** (not `window.innerWidth`) via `setDesktopBounds` + `computeMaximizedGeometryFromBounds`. That seam is where Canvas constrains:
- In Canvas mode the window manager renders one full-bleed surface, so cascade/maximize/drag math is inert (no multi-window arrangement to compute). The `MAX_OPEN_WINDOWS = 8` soft cap is replaced by `MAX_VISIBLE = 1` rendering — windows beyond the foregrounded one are mounted-hidden, not tiled.
- `desktopBounds` already reflects the flex-1 column width (which excludes the rail), so the Canvas full-bleed surface fills its column correctly with no new measurement.
- Switching modes does **not** discard `window-state` — Desktop's per-window geometry persists across a Canvas excursion and is restored on return (the operator's Finder arrangement survives).

### D5 — In-app surface navigation stays on `/desktop`; it never flips the pathname to a surface's page route

> **Added 2026-06-23 (operator review):** the operator observed (a) chat closes when navigating between surfaces, and (b) opening Autonomy routed the browser to a separate page `/workspace-settings?pane=autonomy` — *"we should stay on desktop."* Both are one root cause.

The window manager's navigation verbs (`foregroundSurface` / `navigateToSurface` in `useSurfacePreferences`) previously delivered pane/param selections via `router.push(\`${parentRoute}?pane=…\`)` — a real Next.js navigation that **flips the pathname** to the surface's own page route. That route change leaves the `/desktop` SPA, which re-runs the shell's mount path and **resets the chat rail's open/closed posture** (Bug a), and visibly changes the URL to a standalone-looking page (Bug b). This contradicts ADR-297 D17 (`/desktop` is the canonical baseline), D19.2 (the Dock dot is the foreground signal, *not* the URL), and D19.6 (pane/param updates are intra-surface deep-link state that must **not** flip the pathname).

**The fix:** both verbs now deliver pane/params via `window.history.replaceState`, **preserving the current pathname** (the `/desktop` baseline). The foregrounded window reads `?pane=`/params from `useSearchParams` regardless of pathname (Next 14.2 patches `replaceState` so `useSearchParams` syncs without a navigation event — the same mechanism `setSurfaceParams` (D19.6) already used). Result: navigating between surfaces stays on `/desktop`, the shell never unmounts, **chat persists across navigation** (the Canvas two-pane continuity holds), and the URL no longer reads as a separate page. The per-slug page routes survive purely as cold-load **deep-link transports** + ADR-308 server `redirect()` stubs (bookmark/share safety); in-app navigation never uses them.

Offending call sites converted in the same change: `HomeHeader`'s Autonomy badge (`<Link href="/workspace-settings?pane=autonomy">` → `foregroundSurface('autonomy')`), `AttentionCenter` + `BudgetCard` billing (`router.push('/settings?pane=billing')` → `navigateToSurface('settings', { pane: 'billing' })`). Guard: `api/test_adr297_navigation_enactment.py` asserts the verbs use `history.replaceState`, not a pathname-flipping `router.push`.

### D6 — Intra-surface deep-link params are window-NAMESPACED (`{slug}.{key}`)

> **Added 2026-06-23 (operator review, deeper fix):** D5 keeps every window on the one `/desktop` baseline, which means multiple windows now share **one** query string. But each window has its **own** param vocabulary — `settings` reads `pane ∈ {billing,usage,account}`, `workspace-settings` reads `pane ∈ {mandate,autonomy,connectors,…}`, `recurrence` reads `pane ∈ {activity}` + `task`/`slug`/`agent`, `agents` reads `agent`. A **flat** `?pane=` collided: `/desktop?pane=connectors` rendered Billing because the foregrounded `settings` window read `pane=connectors`, found no match, and fell back to its default while the URL still said `connectors` (operator-flagged). The D5 stopgap (clear the stale pane on window-foreground) only papered over it and couldn't let two windows each remember their own pane.

**The decision:** every intra-surface deep-link param is **namespaced by the owning window's slug** — `?{slug}.{key}=value` (e.g. `workspace-settings.pane=autonomy`, `settings.pane=billing`, `recurrence.pane=activity`, `recurrence.task=…`, `agents.agent=reviewer`). A window reads + writes **only its own namespace**, so N windows open at once never collide and each persists its own deep-link state in the URL simultaneously. A new window inherits this for free — it gets its own namespace by construction. This is the true future-proof resolution; the D5 stale-clear is **removed** (no longer needed — namespaces don't collide).

**Singular Implementation — one place forms the prefix.** Callers never hand-build `${slug}.`:
- `scopeParamKey(slug, key)` → `` `${slug}.${key}` `` — the single prefix-forming function (`web/lib/shell/useSurfacePreferences.tsx`).
- `navigateToSurface(slug, params)` namespaces each param under the **target** slug automatically (call sites pass bare keys — `{pane:'billing'}` — unchanged).
- `foregroundSurface(paneSlug)` sets the **parent** window's `{parent}.pane`.
- Surfaces read/write their OWN params through the `useSurfaceParam(slug)` hook: `const p = useSurfaceParam('recurrence'); p.get('pane'); p.set({ task: slug })` — the hook namespaces transparently and is the only sanctioned way a surface touches the URL for its own state.
- `SettingsPaneShell` takes a `windowSlug` prop (the two Settings doors pass `settings` / `workspace-settings`); `?tab=` stays a flat legacy alias for the account door.
- ADR-308 redirect stubs target the namespaced param (`/autonomy` → `/workspace-settings?workspace-settings.pane=autonomy`); `ACTIVITY_ROUTE` + the "View runs" links target `/recurrence?recurrence.pane=activity`.

Guard: `api/test_adr340_p2_settings_fold.py` (shell scopes by `windowSlug`, stubs namespaced) + `api/test_adr297_d196_intra_surface_nav.py` (pages use `useSurfaceParam`) + `api/test_adr340_d8_machinery_fold.py` (activity nav targets namespaced).

### D7 — Mobile is unaffected and mode-independent

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
