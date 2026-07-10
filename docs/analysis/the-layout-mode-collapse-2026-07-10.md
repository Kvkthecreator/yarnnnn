# The Layout-Mode Collapse — an OPEN direction

*Canvas, desktop, and "open a file" — the known-next after the app registry. Scoped, deliberately undecided. Needs its own discourse.*

> **Status**: Direction sketch (2026-07-10). **OPEN — not decided, not an ADR.** This doc scopes the layout-mode question so a future session can discourse it from a real frame; it does **not** choose an endpoint. Every "decision" below is a *candidate*, tagged as such. No code rides this document.
> **Authors**: KVK, Claude
> **Hat**: A (system canon). Vocabulary: operator, surface, mount, layout mode, canvas, desktop, window manager, tile.
> **Precondition met**: ADR-436 (the app registry — frame-agnostic renderers) is Implemented. That is what makes this question *approachable*: the layout modes arrange mounts, and the mounts are now frame-agnostic apps, so this is a placement problem, not a coupled rewrite.
> **Why open**: the operator stated a willingness to compromise the two existing layout modes for a more singular, streamlined path — but the singular endpoint is genuinely undecided, and the honest read (operator's own) is that "canvas mode winning" does NOT by itself fix what "open a file" means per surface. That is a real design question deserving its own session, not a decision to slide into here.

---

## 0. What this doc is FOR

- To **record the question** so it survives (the app-registry ADR named it the known-next; this is that thread, held open).
- To **scope the candidates** — the endpoints, their tradeoffs, the receipts — so the eventual discourse starts from a map, not a blank page.
- To **name the one hard constraint** every candidate must respect (window = surface; no second window manager; arrange-not-edit).

It is **NOT** a decision, a recommendation, or an ADR. When the discourse happens, it produces the ADR. This is the pre-read.

---

## 1. The current state (receipts @ `683ced2`)

Two layout modes today (`ShellChromeContext.tsx:69-71`, default `canvas`):

- **canvas** = chat rail + **one full-bleed surface** (the ChatGPT/Claude focus convention). Only the foregrounded surface renders; window geometry suppressed (`SurfaceViewport.tsx:74-75, 153-174`).
- **desktop** = the ADR-297 D15 **floating window manager** — absolute-positioned, draggable, z-stacked *surface* windows on a wallpaper (`SurfaceViewport.tsx:176-223`, `WindowFrame.tsx:117-126`).

Load-bearing facts the discourse must hold:
- **Window = surface, never a file.** No per-file window, no per-file slug. A file opens as an inline detail view *inside* the Files surface. (This is an invariant, not a candidate — see §4.)
- **Canvas is NOT a freeform artifact board.** The freeform/floating behavior is desktop mode, and its unit is a surface.
- **"open a file" is currently one behavior** (inline in Files-detail) — but the operator's insight is that it *should* be per-context.

---

## 2. The operator's framing (recorded, not ratified)

From the discourse that produced ADR-436, the operator's own words shaped the candidates. Recorded verbatim-in-spirit so the next session inherits the actual reasoning:

- *"On my web-app based I can see canvas mode winning."* — canvas (focus) as the likely default.
- *"However, that decision doesn't necessarily FIX the openings into focused surface. On Files it can mean show on surface, on Chat it can mean new surface (or modal-like)."* — **"open a file" resolves per-context**, not by a global rule. This is the sharp part: the layout mode and the open-behavior are *separable*.
- *"The desktop mode, I can see really working as a full out desktop."* — desktop stops being a hedge; it becomes a genuine spatial workspace.
- *"I'm willing to compromise existing two layout modes for the most singular, most streamlined implementation path."* — the two modes are on the table, not fixed.

> **The synthesis this framing points at** (a candidate, not a decision): canvas (focus) is the default; desktop (spatial) is the power mode; and **"open" derives from context** — Files → on-surface, Chat → its own frame, desktop → a floating tile. This is NOT "pick one endpoint"; it is two modes with *distinct honest jobs* plus a context-derived open behavior. Whether that is the right singular path is the discourse.

---

## 3. The candidate endpoints (the space to discourse)

Three coherent directions. **None is chosen.** The discourse weighs them.

### Candidate A — the per-context synthesis (the operator's lean)
Keep both modes but give each a distinct job; "open" derives from context.
- canvas = focus default (one full-bleed surface + chat).
- desktop = a real spatial desktop (floating windows, genuine side-by-side).
- open-a-file: Files → on-surface detail (today); Chat → `FileOpenModal` (ADR-436 §7, already built) or a dedicated frame; desktop → a floating tile.
- **Pro**: honest jobs, not a hedge; reuses everything; the chat-open mount already exists.
- **Con**: still two modes — is that "singular"? The operator's compromise-willingness suggests appetite for fewer.

### Candidate B — collapse to focus (canvas wins, desktop retires)
One full-bleed model. No floating windows. A file opens INTO the focused surface.
- **Pro**: maximally simple, focused, mobile-native by default.
- **Con**: loses side-by-side arrangement entirely; "the commons where work settles" loses its spatial expression; power users lose the desktop.

### Candidate C — collapse to spatial (desktop wins, generalize the unit)
One spatial model. Generalize the floating WM (`WindowState {x,y,z}`) so its unit is **{surface | file-tile}** — a file viewer becomes a tile that floats alongside Files/Chat windows.
- **Pro**: one placement model; a canvas of *attributed* tiles is the most literal expression of the commons thesis (provenance on every object — the wedge Figma cannot offer).
- **Con**: pure spatial = "where did I put it" (the Muse failure mode); loses the focus default; the biggest build.

### The spatial-artifact-canvas note (spans B/C)
A tldraw/Muse-style board where files float as tiles is either a *third* mode or the C generalization. If it is ever built, it is scoped **arrange-not-edit**: tiles are frame-agnostic renderers you *position*; mutation stays through chat (ADR-236); editing-in-place is the OpenDoc/Figma feature-race the app-seam frame refuses. **Arrange = substrate (housed, OS-bet). Edit = Figma's business (built, feature-race).** This line is not optional in any candidate that touches a canvas.

---

## 4. The one hard constraint (NOT a candidate — an invariant)

Whatever the discourse decides:

- **Window = surface.** A file does not get its own window-manager window (it would need a per-file slug against a closed union, or a second WM). A file opens into a *mount* (a surface's detail, a modal, a tile) — never a WM window of its own.
- **No second window manager.** yarnnn has one (ADR-297 D15). A canvas/tile model *generalizes* it (Candidate C) or uses the existing overlay primitive (the `FileOpenModal` path) — it never nests a second WM. (`ArtifactCard`'s ratified "we do not build a window manager" — preserved through ADR-436.)
- **Arrange-not-edit.** Any spatial surface arranges attributed renderers; it never becomes an editor. Mutation is through chat.

These three are settled. The discourse operates *within* them.

---

## 5. What the discourse must answer

1. **Is "singular" one mode or two-with-distinct-jobs?** (B/C vs A.) The operator's compromise-willingness leans toward fewer; the per-context insight leans toward keeping both honestly.
2. **If canvas wins — what does "open" mean per surface?** (The operator's own unresolved point.) Files → on-surface; Chat → `FileOpenModal` or a surface; desktop → ? This needs the mode decision first.
3. **Does desktop become a real spatial desktop, or retire?** If it stays, is its unit still surface-only, or generalized to {surface | file-tile} (Candidate C)?
4. **Is there ever a spatial artifact canvas?** If yes, third mode or C-generalization — and the arrange-not-edit line held.
5. **Migration**: the two modes have persisted state (`layoutMode` in localStorage/member-state). A collapse needs a normalization path (the ADR-435 legacy-slug precedent).

---

## 6. What is already built that this can lean on

- **ADR-436**: frame-agnostic apps + the mount catalog + contract. Adding a mount is zero app changes — so any candidate's open-behavior is a *mount*, addable cheaply.
- **`FileOpenModal`** (ADR-436 §7): the chat-open frame already exists. Candidate A's "Chat → own frame" is done; the discourse only decides whether it stays a modal or becomes a surface.
- **The window manager** (ADR-297 D15): `WindowState {x,y,z,minimized,prevGeometry}`, cascade, maximize, LRU. Candidate C generalizes this; it does not rebuild it.
- **Layout-mode plumbing** (`ShellChromeContext`, `SurfaceViewport`): the toggle, the persistence, the single-vs-multi branch. A collapse edits these, doesn't invent them.

---

## 7. The one-line statement

**The layout modes arrange mounts and the mounts are now frame-agnostic apps (ADR-436), so the collapse is a placement decision — but which singular path (per-context two-mode synthesis, focus-only, or one spatial model with a generalized unit) is genuinely undecided and needs its own discourse; all that is settled is the frame: window = surface, no second window manager, arrange-never-edit.**
