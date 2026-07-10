# ADR-438 — The Layout-Mode Collapse: two modes with honest jobs, one context-derived open contract

> **Status**: **Accepted** (2026-07-10, operator-directed). Resolves the open direction sketched in `docs/analysis/the-layout-mode-collapse-2026-07-10.md`. The two layout modes (**canvas** = focus, **desktop** = spatial) are **kept**, but the framing collapses: they are no longer a single unresolved paradigm war (ADR-358's hedge) — they are **two settled tools with non-overlapping jobs**. Orthogonal to them, **"open a file" is ratified as a single context-derived contract** that is already ~90% built and already mode-independent. The only net-new build is desktop-mode file-open, which **reuses the existing `FileOpenModal`** — zero window-manager change.
>
> **This is a re-derivation of Candidate A**, not B (collapse-to-focus) or C (collapse-to-spatial). The operator's "willingness to compromise the two modes for a singular path" is honored not by *deleting a mode* but by **collapsing the pretense** that layout-mode and file-open are one coupled question. They are two orthogonal axes; naming them so is the singular path.
>
> **Precondition met**: [ADR-436](ADR-436-the-app-registry-frame-agnostic-renderers.md) (frame-agnostic renderer apps behind a registry). Because apps render into *mounts* and mounts are frame-agnostic, "where a file opens" is a placement decision addable with zero app changes — which is what makes this a small ratification, not a coupled rewrite.

**Date**: 2026-07-10
**Dimension**: Channel (Axiom 6 — the operator-facing spatial arrangement of the system, and how a file is framed when opened)

**Extends / builds on**:
- [ADR-358](ADR-358-layout-mode-canvas-vs-desktop.md) — introduced `layoutMode ∈ {canvas, desktop}` as an operator preference. This ADR **amends its framing**: the two modes stop being "two whole design languages the operator must choose between" and become "two tools with distinct jobs." The mechanism (the mode discriminator, the persistence, the chat-rail-vs-overlay branch) is preserved byte-for-byte.
- [ADR-436](ADR-436-the-app-registry-frame-agnostic-renderers.md) §5 (the mount catalog) + §8 (this ADR was named the known-next). The mount contract is the substrate this decision places file-open onto.
- [ADR-435](ADR-435-delete-the-home-surface.md) — the empty workspace now anchors on **chat** ("what do you want to do," an active operating surface — explicitly *not* a passive browser). This ADR keeps that: canvas-focus remains the default; the spatial desktop is the opt-in power mode, never the cold-start landing.
- [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D15 (the window manager) + [ADR-316](ADR-316-chat-as-dockable-rail.md) (chat as chrome). Both preserved unchanged.

**Amends**:
- **ADR-358's framing** (as above) — not its code.

**Preserves** (the three settled invariants, held exactly):
- **Window = surface, never a file.** No per-file window, no per-file slug. The window manager's unit stays `KernelSurfaceSlug`. A file opens into a *mount* (a surface's inline detail, or an overlay) — never a WM window of its own.
- **No second window manager.** yarnnn has one (ADR-297 D15). Desktop file-open floats *above* the WM via the existing `position: fixed` overlay primitive (`FileOpenModal`), it does not nest a new WM and does not register in `WindowStateMap`.
- **Arrange-not-edit.** Every mount renders attributed content; none becomes an editor. Mutation is through chat ([ADR-236](ADR-236-frontend-cockpit-coherence-pass.md)).

---

## 1. The problem — two questions were tangled into one

The direction doc (`the-layout-mode-collapse-2026-07-10.md`) held one question open: *which singular layout path — per-context two-mode synthesis (A), focus-only (B), or one spatial model (C)?* The operator's own sharp observation was that **"canvas mode winning does not by itself fix what 'open a file' means per surface"** — the layout mode and the open-behavior are *separable*.

The receipts confirm the separability is not aspirational — **it is already realized in code, and the two axes are already independent**:

| Axis | What it governs | Reads `layoutMode`? | State today |
|---|---|---|---|
| **Open-a-file** | how a single file is framed when opened | **No** | Files → on-surface master-detail (`selectedPath` state, `files/page.tsx:335`); Chat → `FileOpenModal` overlay (`FileOpenModal.tsx`, a `position: fixed` overlay, ADR-436 §7). Neither branch reads `layoutMode`. |
| **Surface arrangement** | how many surfaces are on screen and whether they float | **Yes** | Canvas → exactly one full-bleed surface (`SurfaceViewport.tsx:75,153` — `singleSurface = isMobile \|\| canvasMode`); Desktop → N floating z-stacked *surface* windows (the ADR-297 D15 WM). |

So the tangle was conceptual, not structural. The code already treats them as two axes; ADR-358's *narrative* (two competing paradigms) implied one axis and left the operator feeling the collapse would be a large coupled rewrite. It is not.

A second, real gap surfaces from the same receipts: **desktop mode has no file-open at all.** In canvas, a file opens via the Files window's inline detail or via a chat artifact's modal. In desktop, there is no floating file view — a file is reachable *only* through the Files *window's* internal master-detail. The desktop's own idiom (open a thing, place it) has no file expression. Candidate A must close this.

## 2. The decision — collapse the *pretense*, not a mode

> **Layout-mode and file-open are two orthogonal axes. The singular path is to name them so.**
> **Axis 1 (open-a-file) is one context-derived contract, already ~90% built, ratified here as invariant.**
> **Axis 2 (surface arrangement) keeps both modes — canvas (focus) and desktop (spatial) — with non-overlapping jobs, not a hedge.**

This is **Candidate A, re-derived**. Rejected alternatives and why (recorded so the thread is closed):

- **B (collapse to focus, delete desktop)** — throws away the one paradigm the operator said "really works as a full desktop," and destroys the *only* place two surfaces coexist (Files + Activity side by side — the literal spatial expression of "the commons where work settles," ESSENCE v15). B optimizes the word "singular" past honesty. **Rejected.**
- **C (collapse to spatial, generalize the WM unit surface → {surface \| file-tile})** — the biggest build (touches `useSurfacePreferences`, `WindowState`, `WindowFrame`, `SurfaceViewport`); *inverts* the just-ratified ADR-435 chat-anchor default (a spatial-desktop cold-start IS the passive browser ADR-435 rejected); and courts the Muse "where did I put it" failure. C fights two ratified decisions to win the hardest build. **Rejected.**

### D1 — Axis 1: the file-open contract (ratified, already built)

**"Open a file" resolves from the mount's context, by one rule:**

> A surface that has an **inline detail region** opens a file **on-surface** (master-detail). A context that has **no inline detail region** opens a file into the **shared `FileOpenModal` overlay** (its own frame, floating above everything via `position: fixed`).

Applied:

| Context | Has inline detail? | Open-behavior | Built? |
|---|---|---|---|
| **Files surface** | Yes (the explorer detail area) | on-surface master-detail (`ContentViewer` → `FileBody`) | ✅ exists |
| **Chat lane / artifact** | No | `FileOpenModal` (ADR-436 §7) | ✅ exists |
| **Desktop mode** | No (the desktop is a wallpaper of floating *surface* windows; it has no file detail region) | `FileOpenModal` — **the same overlay** | 🔲 **D2 (the one net-new wiring)** |

This is the whole "per-context" model, and it is now a **contract, not three ad-hoc behaviors**: the mount decides its frame (ADR-436 D2), and the frame is derived from one property (does this context own a detail region), not from `layoutMode`. Files keeps master-detail because it *has* a detail region; everything else that opens a bare file reaches for the modal. **The modal is the default file-open frame; on-surface detail is the Files-only specialization.**

### D2 — Axis 1, the one build: desktop file-open reuses `FileOpenModal`

Desktop mode gains file-open by mounting the **existing** `FileOpenModal` — the same centered overlay chat already uses. Concretely: the desktop layer (or its file-triggering affordances — a Recents tile, a search result, a "reveal" action) opens a file by setting the same modal path state chat sets. One chat-open mount, two callers (chat + desktop).

Why this and not a bespoke floating file-tile (the operator's ratified choice):
- **Zero window-manager change.** The modal floats *above* the WM via `position: fixed`; it never enters `WindowStateMap`. The "window = surface" and "no second window manager" invariants hold **trivially** — nothing about the WM is touched.
- **A distinct draggable-but-unmanaged tile would be a net-new component and a soft step toward C.** The moment a file gets a *placed, persistent, draggable* frame, the pressure to remember its position, z-order, and lifecycle re-creates the WM's problems outside the WM. Reusing the modal refuses that gradient.
- **Singular Implementation.** `FileOpenModal`'s own docstring already anticipates this: *"a later layout ADR can reframe this without touching apps"* (`FileOpenModal.tsx:24-25`). This ADR is that reframe, and the honest answer is: it does not need reframing — it needs a second caller.

**Consequence:** "per-context" precisely means "per-context-that-lacks-an-inline-detail-region." Both chat and desktop lack one → both get the modal. Files has one → keeps master-detail. The contract is one sentence (D1); the modal is its default limb.

### D3 — Axis 2: two modes, honest jobs (kept, reframed)

Both modes survive, with the framing corrected from "two rival design languages" (ADR-358) to **"two tools for two operator intents":**

| Mode | Operator intent | Arrangement | Chat |
|---|---|---|---|
| **Canvas** (default) | "I am doing one thing." | exactly one full-bleed surface | docked right rail |
| **Desktop** (opt-in) | "I am arranging several things side by side." | N floating z-stacked *surface* windows (ADR-297 D15 WM) | summoned `position: fixed` overlay |

- **Canvas stays the default** — consistent with ADR-435's chat-anchored, active-operating-surface cold start. A first-time or empty workspace lands in focus, not on a spatial wallpaper.
- **Desktop is the power mode** — the operator's "full out desktop." Its job (side-by-side surfaces) is genuinely distinct from canvas's job (focus), so keeping both is *not* a hedge: neither answers the other's question. This is the exact distinction ADR-358 already implemented; this ADR only relabels the two modes from "paradigms you pick between" to "tools you switch between by intent," and confirms neither is scheduled for deletion.
- **The UserMenu Canvas·Desktop toggle** (`UserMenu.tsx:256-290`, desktop-viewport-only) is preserved unchanged.

### D4 — the spatial-artifact-canvas horizon (named, not built, arrange-not-edit)

A tldraw/Muse-style board where *files* float as arrangeable tiles remains a future candidate — **not built here.** If it is ever built, it is either a third mode or a generalization of desktop, and it is scoped **hard as arrange-not-edit**: tiles are frame-agnostic renderers you *position*; mutation stays through chat; editing-in-place is the OpenDoc/Figma feature-race the app-seam frame refuses. Provenance-on-every-tile (the attributed-substrate wedge Figma cannot offer) is the only reason it would ever be worth building. Recorded so the thread survives; **no code, no commitment.** D2's modal-reuse deliberately does *not* start down this path.

## 3. Scope — what this ADR changes

**Ratification (no code):**
- Axis 1 file-open contract (D1) — describes behavior that already exists.
- Axis 2 two-mode framing (D3) — relabels ADR-358's modes; the code is unchanged.

**The one build (small, FE-only, byte-identical to existing rendering):**
- D2 — wire desktop-mode file-open to the existing `FileOpenModal`. A file-open trigger + the shared modal-path state, reused. No new component, no WM change, no backend, no schema.

**Named, deferred (each its own future ADR if demanded):**
- D4 — the spatial-artifact-canvas.
- The Open-With picker (ADR-436 D2 — still deferred until a type has two apps).

## 4. Migration

The persisted `layoutMode` (`yarnnn:shell:layout-mode` in localStorage, mirrored to member-state) needs **no normalization** — both `canvas` and `desktop` remain valid values with unchanged semantics. This is the payoff of keeping both modes: unlike ADR-435's slug deletion (which needed the legacy-slug normalization path), no persisted value becomes invalid. An operator mid-session in either mode sees identical behavior after this ADR ships, except that desktop mode gains a file-open it did not have (D2).

## 5. Consequences

- **Positive**: the tangled question resolves into two orthogonal axes, each singular in its own right; the file-open model is ratified as a one-sentence contract already built; desktop mode gains its missing file-open at the cost of one wiring; the three settled invariants hold trivially (nothing touches the WM); no persisted state is invalidated; the ADR-435 chat-anchor default is preserved.
- **Cost**: one small FE wiring (D2). The "compromise" the operator offered (deleting a mode) is spent instead on *deleting a false coupling* — a better trade.
- **Risk**: low. D2 reuses an existing, shipped overlay; the rest is ratification. No backend, no schema, no window-manager change, byte-identical rendering.

## 6. The one-line statement

**The layout-mode collapse is not the deletion of a mode but the deletion of a false coupling: "open a file" and "how surfaces are arranged" are two orthogonal axes — the first is one context-derived contract (Files → on-surface master-detail; everything else → the shared `FileOpenModal` overlay) already ~90% built and mode-independent, the second keeps both canvas (focus, default) and desktop (spatial, opt-in) as non-overlapping tools; the only net-new build is desktop file-open, which reuses `FileOpenModal` so the window manager is never touched and every settled invariant (window = surface, no second WM, arrange-not-edit) holds trivially.**
