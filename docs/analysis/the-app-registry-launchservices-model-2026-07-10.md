# The App Registry — the LaunchServices model, frame-agnostic renderers, and the mount catalog

*The 7 apps become rows behind a code-seeded table; a renderer never decides its frame; the mount decides. Layout collapse is the known-next, not this doc.*

> **Status**: Scoping analysis (2026-07-10). Doc-first, receipts-backed @ `683ced2`. **No ADR rides this yet** — this doc scopes the app registry so an ADR can be written against a real map. It is the third implementation-companion in the OS arc, after `the-powerbox-scope-audit-implementation-fe-2026-07-10.md` (the permission gate) and `the-viewer-app-scope-audit-fe-2026-07-10.md` (which found the monolith this doc splits). It follows the *direction* set by `the-app-seam-first-party-viewer-vs-third-party-principal-2026-07-10.md`.
> **Authors**: KVK, Claude
> **Hat**: A (system canon). Vocabulary: operator, app, renderer, mount, registry, resolver, launch, frame, layout mode, powerbox.
> **Method**: two code audits @ `683ced2` — the viewer factoring (prior doc) and the layout/window/view-mode machinery (this doc §2). Every load-bearing claim carries a `file:line` or an ADR.
> **Decisions locked in the discourse that produced this doc** (operator-directed): (1) **code-seeded registry** — the shape admits a third party's row; only yarnnn adds rows (demand-gate honest); (2) **frame-agnostic renderers** — an app never decides its frame, the mount does; (3) **resolver returns an ordered list, picker UI deferred** until a type has >1 app; (4) **the mount catalog is named, not all built**; (5) **chat-open becomes a real mount, superseding the ArtifactCard redirect-only stance** (§7); (6) **the layout-mode collapse is the explicit known-next**, its own ADR, with this registry as its precondition (§8).
> **Positioning**: unchanged. Full LaunchServices *shape* now; third-party *principals* stay demand-gated (app-seam §8). We build the table that could hold a stranger's app, seeded only with our own.

---

## 0. Read this first — what an "app" IS and IS NOT here

- **IS**: a **frame-agnostic renderer** that owns a set of file types and draws their content into whatever container mounts it. A row in a code-seeded registry. The macOS "default app for this type," minus the process/window/principal machinery.
- **IS NOT**: a window, a surface, a principal, a runtime, an editor. It does not decide where it renders (the mount does — §5). It does not hold a grant (that's App(principal), deferred — app-seam §5). It does not edit (mutation is through chat — ADR-236, preserved).
- **The two "app" words, held apart** (from the viewer-scope doc): **App(composition)** = a surface whose interior is `kind`-dispatched (Home was the one instance — now deleted, ADR-435); **App(principal)** = a third party's program with a grant (deferred). **A viewer app is neither** — it is a first-party in-shell *renderer*, the reference app (Preview.app) that makes App(principal) expressible later.

---

## 1. The 7 apps — the map, made concrete

`FileBody` today is one monolith: a flat 9-branch `{kind === '…'}` run (`FileBody.tsx:112-202`), type detection cleanly factored into a closed 9-kind union (`file-types/index.ts:63-72`) but rendering co-located as in-file helpers. This doc splits the monolith into **7 named renderer apps** behind a table:

| # | App | Owns kinds | macOS analog | Blob? | Notes |
|---|---|---|---|---|---|
| 1 | **Text Viewer** | `text` | TextEdit (read) | no | The L1 raw-view escape hatch; every unknown-but-textual type falls here |
| 2 | **Markdown Viewer** | `markdown` | Quick Look / Marked | no | Reuses `MarkdownRenderer`; the tier-1 IDENTITY special-case lives *inside* this app |
| 3 | **Web Viewer** | `html` | Safari (sandboxed) | no | The `sandbox=""` iframe; compose output + agent HTML |
| 4 | **Image Viewer** | `image` | Preview | yes | `useSignedBlobUrl`; the SVG-as-text special case |
| 5 | **Media Player** | `video`, `audio` | QuickTime | yes | Owns the `BlobMissing` honest-state until ADR-427 Phase 2 |
| 6 | **PDF Viewer** | `pdf` | Preview (PDF) | yes | Iframe-based today |
| 7 | **Table Viewer** | `csv` | Numbers (read) | yes | Owns the CSV row-limit hint |
| — | **Download Terminal** | `download` | Finder "no preview" | maybe | Not an app — the *terminal* of the resolver chain; also the future "Open With…" home (§6) |

> **7 apps + 1 terminal.** `download` is not a viewer app — it is the resolver's binary terminal (`file-types/index.ts:129-136`), the honest "no in-shell renderer" fallthrough. It stays a terminal, and it is where a future launch-out verb (App(principal) redirect) surfaces.

---

## 2. The audit that shapes the mount model — window = surface, not file

The prior doc established the monolith. This doc adds the *display* machinery audit (@ `683ced2`), because "how an app is surfaced/launched" is decided by it. Four findings, all with receipts:

**Finding A — the unit of "window" is a SURFACE, never a file.** Everything the window manager mounts is a kernel surface slug (`SurfaceRegistry.tsx:84-104`; `KERNEL_SURFACE_REGISTRY`). `WindowStateMap` is keyed by slug (`surface-preferences.ts:393`). **There is no per-file window and no per-file slug.** A file opens as an *inline detail view inside the Files surface* (`files/page.tsx:923-955`, `ContentViewer.tsx` → `FileView` → `FileBody`), selection held as component state, deliberately not a URL/window write (`files/page.tsx:566-577`).

**Finding B — two layout modes, distinct jobs** (`ShellChromeContext.tsx:69-71`, default `canvas`):
- **canvas** = chat rail + **one full-bleed surface** (the ChatGPT/Claude focus convention). Geometry suppressed; only the foregrounded surface renders (`SurfaceViewport.tsx:74-75, 153-174`).
- **desktop** = the ADR-297 D15 **floating window manager** — absolute-positioned, draggable, resizable, z-stacked surface windows on a wallpaper (`SurfaceViewport.tsx:176-223`, `WindowFrame.tsx:117-126`).
- **Canvas is NOT a freeform artifact board.** The freeform/floating behavior is *desktop mode*, and its unit is a *surface*, not a file.

**Finding C — `FileBody` is already frame-agnostic.** It is "THE one file renderer, mounted by every surface that opens a file" (`FileBody.tsx:3-29`), with a `compact` display hint that is "not a different renderer" (`:26-28`). Two live mounts: Files-detail (`ContentViewer.tsx:517`) and chat `ArtifactCard` (`ArtifactCard.tsx:141`). **The frame-agnostic renderer pattern this doc formalizes already exists — it is just monolithic and two-mounted.**

**Finding D — a ratified stance this doc will supersede (narrowly).** The `ArtifactCard` docstring makes two claims (`ArtifactCard.tsx:24-33`): (1) *"'Open in Files' hands off to the real window… never by nesting a second pane inside the chat window"*, and (2) *"We do not build a window manager."* **§7 supersedes only (1); (2) is preserved.**

> **The load-bearing consequence**: because window = surface and a file is not a surface, a viewer app **must not** get its own WM window (that would need a per-file slug — impossible against a closed union — or a second parallel windowing system, which claim (2) forbids). **The app is a renderer; the frame is the mount's; the mount is the surface + layout mode.** This is *more* macOS-faithful, not less: Preview.app does not decide whether it is windowed or fullscreen — the window server does.

---

## 3. The registry — shape, and where it lives

**A code-seeded table** (operator decision 1), modeled on `SurfaceRegistry`'s static-import pattern but for renderers instead of surfaces. The row shape:

```ts
interface AppRegistration {
  id: AppId;                       // opaque id (NOT a closed union — see below)
  ownsTypes: ViewerApplication[];  // the kinds this app renders (today's 9-kind vocabulary)
  mount: 'in-shell';               // 'redirect' | 'local' reserved for App(principal), unbuilt
  renderer: ViewerComponent;       // the frame-agnostic component
  needsBlob: boolean;              // drives useSignedBlobUrl (from viewerNeedsBlob today)
}

const APPS: Record<AppId, AppRegistration> = { /* the 7 kernel rows, seeded */ };
```

**Why code-seeded is the honest "open registry" at this stage** (app-seam §8, app-layer §12): a third party cannot write to our code, so "open" here means **the shape admits a stranger's row** — not that strangers can add rows yet. The registry is *one edit* from data-backed (the row becomes a DB/manifest row) when App(principal) ships. Building the data-backed write path *now* would be building the third-party principal before anyone asks — the demand-gate violation. **Code-seeded is the shape without the premature capability.**

**The one type change that flips the ratchet** (app-layer §12): `ViewerApplication` stops being a closed union of *kinds* and `AppId` becomes an **opaque id**; `APPS` is a mutable lookup seeded with the 7 kernel rows, indistinguishable from a third party's. This doc does **not** flip it (the union stays closed until a third party asks) — but it **confines the flip to one file** (`file-types` + the `APPS` table), so the ratchet can run red as a one-line fact.

---

## 4. The resolver — an ordered list, picker deferred

Today `resolveViewerApplication(path, contentType)` returns **one** `ViewerApplication` (`file-types/index.ts:113`). Operator decision 3: **return an ordered list**, render the picker only when `length > 1`.

```ts
resolveApps(path, contentType): AppId[]   // ordered: default first, alternatives after
```

- Today every type has exactly one app, so `resolveApps` returns a singleton and the caller mounts `apps[0]` — **byte-identical behavior**, no picker.
- The **Open-With picker** (§6) renders only when a type has ≥2 apps — the app-layer §11 falsification boundary ("the moment a second app claims the same derived type"). **Mechanism now; UI on demand.**
- The three-tier fallback chain is preserved (`file-types/index.ts`): tier-1 path-exact (IDENTITY, routed through the table per the viewer-scope doc D.3), tier-2 type-exact, tier-3 terminal (`text` / `download`, derived from text-ness, never enumerated).

---

## 5. The mount catalog — named, not all built (operator decision 4)

A **mount** is a container that asks the registry for a renderer and frames it. The renderer is frame-agnostic (Finding C); the mount owns the frame. **This is the whole architecture** — every "where does a file open" question is "which mount, in which context," answered without touching apps.

| Mount | Context | Status | Frame it provides |
|---|---|---|---|
| **Files-detail** | Files surface, a node selected | ✅ exists (`ContentViewer` → `FileBody`) | the two-pane explorer's detail area |
| **Chat-open** | Chat lane, opening an artifact | 🔲 §7 (the one new mount) | a new surface / modal-like frame (supersedes redirect-to-Files) |
| **Recents tile** | Files/Recents grid | ✅ exists (`FileTile`) | a compact card |
| **Chat ArtifactCard** | Chat lane, inline on write | ✅ exists (`ArtifactCard`) | a bounded inline card |
| **Desktop tile** | desktop layout mode | 🔲 future (layout collapse, §8) | a floating placed tile |

**The mount contract** (what every mount honors, so mounts are addable without touching apps):

```
a mount:  resolveApps(file) → pick appId → <renderer file={file} {...displayHints} />
          + owns its own frame (header/chrome/bounds)
          + owns its own data-load (or shares useFileLoad, viewer-scope D.2)
          + NEVER edits (mutation through chat, ADR-236)
```

> **The renderer is the same across all five mounts.** `compact` today proves it (a display hint, not a fork). Adding a mount = writing a frame + calling `resolveApps` + mounting the renderer. **Zero app changes.** That is the payoff of frame-agnostic: the layout question (§8) becomes a *mount* question, orthogonal to the apps.

---

## 6. "Open With" — the launch surface (seam built, UI deferred)

macOS: right-click → Open With → default + alternatives. Ours:

- **The seam** (build now): `resolveApps` returns the ordered list; a mount can offer "Open With…" from it.
- **The UI** (defer): render the picker only when `resolveApps(file).length > 1`. Today: invisible (one app per type). The first time two apps claim a type (e.g. a second Markdown renderer, or a third-party image editor), the picker lights up **with no kernel change** — the falsification boundary made cheap.
- **The launch verb** (App(principal), deferred): a `mount: 'redirect'` app launches *out* (redirect + scoped token via the powerbox minted capability, app-seam §3). The **Download Terminal** (§1) is its natural home — "no in-shell renderer → offer Open With → a redirect app." Not built; the terminal is where it lands.

---

## 7. The one new mount — Chat-open (supersedes ArtifactCard redirect-only)

Operator decision 5. Today, opening an artifact from chat is **redirect-to-Files**: `ArtifactCard`'s "Open in Files" is a `SurfaceLink to="files" params={{path}}` (`ArtifactCard.tsx:104-111`) that foregrounds the Files surface seeded to the file. The docstring ratified this as *"never nest a second pane inside the chat window"* (`:24-33`).

**This doc supersedes that — narrowly and with reason.** Opening an artifact from chat gives it **its own frame** (a new surface or modal-like mount), not a redirect. The rationale is exactly the frame-agnostic result: **"redirect to Files" was a workaround for not having a clean mount model.** Once the renderer is frame-agnostic and the mount contract exists (§5), a chat-open mount is cheap and *honest* — the artifact opens where you are looking, carrying its attribution, without teleporting you to a different surface.

**What is superseded vs. preserved:**
- **Superseded**: ArtifactCard claim (1) — "opening hands off to Files, never its own frame in chat." Chat-open is now a real mount.
- **Preserved**: ArtifactCard claim (2) — *"We do not build a window manager."* **Chat-open uses the existing surface/modal machinery, not a new WM.** We are not nesting a second window *manager* inside chat; we are adding a *mount* that uses the surface/modal primitives that already exist. The distinction is load-bearing and keeps the supersession honest.
- **Preserved**: the inline `ArtifactCard` (render-on-write) stays — chat-open is the *explicit-open* action, not a replacement for the inline card.
- **Preserved**: mutation-through-chat (ADR-236). Chat-open *renders*; it never edits.

> **Whether chat-open is a new surface or a modal is a §8 (layout) decision**, because it depends on the settled layout model (in canvas mode, "a new surface" and "a modal" may be the same thing). This doc names chat-open as a *required mount* and defers its exact frame to the layout collapse. The app registry is mount-agnostic either way.

---

## 8. The known-next — the layout-mode collapse (named, not designed here)

Operator decision 6. The layout modes are now understood as **arrangers of mounts**, and the mounts are apps — so the layout collapse is *downstream* of this registry, not upstream. Named here so the thread does not evaporate; **designed in its own ADR.**

The direction the discourse surfaced (operator's framing, recorded, not ratified):
- **canvas (focus) is the default** — one full-bleed surface + chat; the "I'm doing one thing" model.
- **desktop is a real desktop** — the floating spatial WM, for genuine side-by-side arrangement; it stops being a hedge and becomes the power mode.
- **"open a file" resolves against context, not a global rule** — on **Files** → open *on the surface* (Files-detail mount); on **Chat** → open as *its own frame* (Chat-open mount, §7); in **desktop** → a floating tile.

> **Why this waits for the registry, not the reverse**: every open-behavior above is "which mount, in which context." That question is only *clean* once the thing being mounted is a frame-agnostic renderer (this doc). Designing the layout collapse first would couple the container redesign to a monolithic renderer — building the board before the tiles are portable. **Apps first makes the layout collapse a placement problem instead of a coupled rewrite.**

**A spatial-artifact-canvas** (files as floating tiles, tldraw/Muse-shaped) was considered and is **not** this: it would be a *third* layout mode or a generalization of desktop-mode's unit from surface to {surface | file-tile}. It stays a candidate for the layout ADR, scoped hard as **arrange-not-edit** (tiles are renderers you position; mutation stays through chat; provenance-on-every-tile is the wedge Figma cannot offer) — never an editor (the OpenDoc/Figma feature-race the app-seam doc refuses).

---

## 9. Scope — debt now vs. capability later

| | **Debt half (build now)** | **Capability half (deferred)** |
|---|---|---|
| Registry | code-seeded `APPS` table, 7 rows | data-backed (App(principal) writes rows) |
| Renderers | split monolith → 7 frame-agnostic apps (viewer-scope D.1) | third-party renderers (opaque `AppId` flip) |
| Resolver | returns ordered list; picker deferred | picker UI when a type has >1 app |
| Mounts | Files-detail (exists) + Chat-open (§7) + shared `useFileLoad`/`<FileMeta>` (D.2) | Desktop tile (layout ADR) + redirect launch (App(principal)) |
| ADR-427 dep | **none** (non-media renders today) | media round-trip (Phase 2/3) + minted serving |
| Ships as | Finder-parity + pre-app-ratchet + the one new chat mount | App(principal) + layout collapse, both their own ADRs |

**The debt half is self-contained and shippable** with no ADR-427 dependency (the viewer-scope doc proved this — the split needs nothing from binary/serving; only the media *round-trip* waits). The capability half is app-seam-sequenced and layout-sequenced.

---

## 10. What this document does NOT do

- **Does not build App(principal).** Code-seeded registry only; the third-party write path stays demand-gated (§3).
- **Does not flip the closed union to opaque ids.** It confines the flip to one file so the ratchet can run red when a third party asks (§3).
- **Does not design the layout collapse.** Names it as the known-next with the registry as precondition (§8); the ADR is separate.
- **Does not build a spatial artifact canvas.** Records it as a layout-ADR candidate, scoped arrange-not-edit (§8).
- **Does not give a file its own window.** Window = surface is a load-bearing invariant; the app is a renderer, the frame is the mount's (§2).
- **Does not build a second window manager.** Chat-open uses existing surface/modal primitives; ArtifactCard claim (2) is preserved (§7).
- **Does not change mutation.** Through chat, always (ADR-236).

---

## 11. The one-line statement

**The 7 viewer apps become rows in a code-seeded registry of frame-agnostic renderers — an app owns types and draws content, but never decides its frame; the mount does, and the mount is a surface plus a layout mode, so a file never gets its own window (window = surface, an invariant); the resolver returns an ordered list with the Open-With picker deferred until a type has two apps; opening from chat becomes a real mount (superseding the redirect-only stance while preserving "no second window manager"); and the layout-mode collapse is the known-next, downstream of this registry because it arranges mounts and the mounts are apps.**

---

## Appendix A — receipts index

| Claim | Receipt |
|---|---|
| Monolith: one flat 9-branch run, no per-type components | `FileBody.tsx:112-202` · viewer-scope doc §1 |
| Type detection is a closed 9-kind union | `file-types/index.ts:63-72,113` |
| `FileBody` is already frame-agnostic (two mounts, `compact` hint) | `FileBody.tsx:3-29` · `ContentViewer.tsx:517` · `ArtifactCard.tsx:141` |
| Window = surface; `WindowStateMap` keyed by slug | `surface-preferences.ts:393` · `SurfaceRegistry.tsx:84-104` |
| A file opens as an inline Files-detail view, not a window | `files/page.tsx:566-577,923-955` · `ContentViewer.tsx` |
| Two layout modes: canvas (full-bleed) / desktop (floating WM) | `ShellChromeContext.tsx:69-71` · `SurfaceViewport.tsx:74-75,153-223` |
| Canvas is NOT a freeform board; floating is desktop mode | `ShellChromeContext.tsx:33-42` · `SurfaceViewport.tsx:176-223` |
| ArtifactCard: "Open in Files" is a redirect; "no 2nd WM" | `ArtifactCard.tsx:24-33,104-111` |
| Window vs pane = `pane_of` in the registry | `useSurfacePreferences.tsx:662-692` · `SurfaceViewport.tsx:94-114` |
| The pre-app ratchet (closed union → mutable table) is one file | app-layer §12 · `file-types` + the `APPS` table |
| Powerbox minted capability = the redirect-launch capability | app-seam §3 · ADR-427 D4 |
| Third-party principals demand-gated | app-seam §8 · ADR-380 §5 |
| Mutation is through chat; inline edit deleted | ADR-236 |

## Appendix B — the mount contract, as a checklist for adding a mount

To add a mount (e.g. Chat-open, or a future Desktop tile) without touching any app:

1. Call `resolveApps(file)` → pick `apps[0]` (or offer Open-With if `length > 1`).
2. Mount `<Renderer file={file} {...displayHints} />` where `Renderer = APPS[appId].renderer`.
3. Provide the **frame** (header/chrome/bounds) — the mount owns this, the app does not.
4. Provide or share the **data-load** (`useFileLoad`, viewer-scope D.2).
5. Honor `needsBlob` (route through `useSignedBlobUrl` for blob-backed apps).
6. **Never edit** — no mutation affordance; "change it" routes to chat.
7. Respect the **powerbox** — the mount renders only files the viewer principal may read (ADR-434); out-of-scope files never reach a mount.
