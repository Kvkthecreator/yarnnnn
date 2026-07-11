# Shell chrome from first principles — how many rows, and who owns them

**Date**: 2026-07-11 (operator-commissioned 2026-07-10, from the first Studio session)
**Hat**: A (system audit; the decision ADR is ADR-442)
**The observation**: a foregrounded Studio stacks three chrome rows — TopBarSurface
(h-14) + GlobalLocatorStrip (h-7) + the Studio's own header row — with scattered
buttons and no clear hierarchy; desktop mode adds a fourth (the WindowFrame h-8
title bar). Compare the macOS menu-bar model (ONE global bar; the foreground app
declares its menus into it) and Claude Design's single top bar (title + surface
actions hoisted into one authority).

---

## 1. The chrome stack today (receipts)

| Row | Owner | Contents | When |
|---|---|---|---|
| 1 · h-14 | `TopBarSurface` (`TopBarSurface.tsx:355`) | wordmark → /desktop · launcher trigger · Dock (Home anchor + kept/open icons, `:400-434`) · AttentionCenter bell · UserMenu (`:445-448`) | always |
| 2 · h-7 | `GlobalLocatorStrip` (`GlobalLocatorStrip.tsx:92`) | `‹SurfaceTitle› › ‹crumb› › ‹crumb›` for the FOREGROUNDED surface; the single back affordance (root-click fires the leaf's onClick) | always on desktop/tablet; leaf-back-chip on mobile |
| 3 · h-8 | `WindowFrame` (`WindowFrame.tsx:286`) | traffic lights + window title, per window | desktop layout mode only (`chromeless` suppresses it in canvas, `SurfaceViewport.tsx:166`) |
| 4 · varies | each surface, hand-rolled in-body | Studio: icon + artifact name + relPath + "Open in Files" + "New / open…" (`StudioSurface.tsx:213-236`) · Chat: lane-list header + active-lane header (`ChatSurface.tsx:200,302`) · Files: `SurfaceIdentityHeader` on selection (`files/page.tsx:878`) · split-nav shells: `PaneHeader` per pane (`SettingsPaneShell.tsx:112`) | per surface |

**The one contribution channel that exists**: `useWindowCrumb(slug, segments)`
(`BreadcrumbContext.tsx:131-143`) — per-slug identity segments, consumed solely
by the locator strip. **There is no channel for a surface to contribute
ACTIONS** to shared chrome (verified: `ShellChromeContext` exposes only
email/launcher/drawer/layoutMode; `createPortal` used only by modals). So every
surface that needs verbs hand-rolls a header row — that is where row 4 comes
from, and why the Studio's buttons read as scattered.

## 2. First-principles derivation

Start from the two settled invariants: **window = surface** (ADR-297 D15 — the
foreground surface IS "the app" in the macOS analogy) and **ADR-438's two
honest layout modes** (canvas focus / desktop spatial).

Chrome content divides into exactly two classes:

- **System chrome** — belongs to the OS, identical on every surface: the brand
  anchor, the launcher, the Dock, attention, the account. This is macOS's
  menu-bar *right side* + Dock, already fused into row 1. Nothing
  surface-specific may enter it, or the Dock's stable geography breaks.
- **Surface chrome** — belongs to the foreground surface: *where am I* (identity/
  crumbs) and *what can I do to this surface as a whole* (primary verbs). This
  is macOS's menu-bar *left side* — the part the foreground app DECLARES.

The status quo puts system chrome in row 1, surface *identity* in row 2, and
surface *actions*… nowhere — so each surface improvises row 4. The defect is
not "too many bars" in general; it is that **surface chrome is split across two
rows because the declaration channel only carries half of it.**

### The three candidate shapes

**(a) One row — merge locator + actions into the TopBar** (the literal macOS
menu bar). Rejected: yarnnn's top bar center is the Dock (D19.5). Surface
identity + crumbs + actions + Dock icons + bell + avatar in one h-14 row
collide at common widths, and every Dock re-sort would reflow the crumb. macOS
avoids this only by putting the Dock on another edge.

**(b) Status quo + guidelines** (per-surface headers, but tidier). Rejected:
this is the accretion that produced the operator's complaint; without a
declared channel the next surface hand-rolls row 4 again.

**(c) Two rows, two authorities** — row 1 stays pure system chrome; row 2 (the
existing locator strip, already keyed on `foregrounded`, already fed by a
declaration channel) grows the missing half: a **declared action slot**. The
per-surface surface-scoped header row dies. **Chosen** — it is the menu-bar
model adapted to where yarnnn's Dock actually lives, and it is the smallest
move that makes the contract total.

### Where "you are here" lives

Where it already does — the surface bar's left side. Identity and location are
the same declaration (the crumb); nothing moves.

### Which row dies

Row 4 — *where its content is surface-scoped*. The seam that decides:

> A header row that describes **the surface and its open document** (identity +
> whole-surface verbs) is surface chrome → declared into the bar. A header row
> that describes **a selection or pane within the surface** (Files' selected
> node + Properties; Chat's active-lane model chip; a split-nav `PaneHeader`)
> is content → stays in-body.

The Studio's header is entirely surface-scoped (artifact name = the crumb;
"Open in Files" = a whole-surface verb; "New / open…" = literally the
strip's existing root-click back idiom, `setParam({file:null})`) — it dies
completely, 3 rows → 2. Files/Chat keep their selection-scoped rows.

### Desktop mode

The WindowFrame title bar is the **window's frame** (per-window, N of them) —
a different job from the one foreground surface bar, and ADR-438 D3 keeps
desktop mode honest. It stays. A named follow-on (not built): declared actions
could render into each WindowFrame's bar, making the declaration
frame-agnostic the way ADR-436 renderers are.

## 3. What this feeds

**ADR-442**: (D1) two chrome authorities, one row each; (D2) the surface-chrome
declaration contract — `useWindowCrumb` (identity, existing) + `useSurfaceActions`
(new, same channel); (D3) the surface-scoped vs content-scoped seam; (D4) the
Studio adopts first (its header row deleted); (D5) Chat registers its
active-lane crumb (locator honesty); (D6) WindowFrame unchanged, follow-on
named; (D7) the component keeps the `GlobalLocatorStrip` name (the gate
`test_global_locator_strip.py` pins it; relabel-keep-name precedent) while its
role becomes "the surface bar."
