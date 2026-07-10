# ADR-436 — The App Registry: frame-agnostic renderers behind a code-seeded table

> **Status**: **Accepted + debt-half Implemented** (2026-07-10, operator-directed). The monolithic file viewer (`FileBody`'s flat 9-branch switch) is refactored into **7 named, frame-agnostic renderer apps** behind a **code-seeded registry table** — the first-party half of yarnnn's LaunchServices layer (OS primitive #2, the type→app association; the app-seam four-primitive frame). An **app is a renderer, not a window**: it owns file types and draws their content into whatever container mounts it; the frame belongs to the mount, never the app. This ratifies the debt-half of `docs/analysis/the-app-registry-launchservices-model-2026-07-10.md` and names the capability-half seams.
>
> **⚡ DEBT HALF IMPLEMENTED.** Landed: `components/workspace/viewers/` (7 apps + `DownloadTerminal` + shared `blob.tsx`), `lib/file-types/apps.tsx` (`APPS` code-seeded table + opaque `AppId` + `resolveApps` ordered list + `resolveApp`), `FileBody` reduced to a ~30-line dispatcher (D1/D2), `useFileLoad` + `<FileMeta>` shared chrome adopted by both `ContentViewer` and `ArtifactCard` (D4), and `chat-surface/FileOpenModal` — the chat-open mount — wired into `ArtifactCard`'s "Open" button, superseding the redirect-only stance (D5). Verified: `tsc --noEmit` 0 errors + `next build` clean; rendering byte-identical (one app per type → singleton resolver). **Capability half** (opaque-id ratchet flip, Open-With picker UI, redirect-launch, Desktop-tile, media round-trip) remains named + deferred (§9).
>
> **This ADR is the mechanism, not the app store.** The registry's *shape* admits a third party's row; only yarnnn adds rows (code-seeded). Third-party **App(principal)** — a stranger's program holding a grant, launched into its own origin — stays demand-gated (app-seam §8 / ADR-380 §5). We build the table that could one day hold a stranger's app, seeded only with our own.

**Date**: 2026-07-10
**Dimension**: Channel (Axiom 6 — how substrate is rendered) + Substrate (Axiom 1 — the file the renderer draws)

**Extends / builds on**:
- **The app-seam frame** (`docs/analysis/the-app-seam-*`, `the-viewer-app-scope-audit-*`, `the-app-registry-launchservices-model-*`) — the four-primitive OS lens; this ADR builds primitive #2 (type→app), first-party.
- **ADR-245** — three-layer content rendering (L1 raw / L2 shape / L3 affordance). The resolver's tier-1/2/3 fallback IS ADR-245's depth strata; this ADR preserves it.
- **ADR-236** — chat is the canonical mutation surface. Apps **render**, never edit. Preserved.
- **ADR-434** — the powerbox. A mount renders only files the viewer principal may read; out-of-scope files never reach a renderer.
- **ADR-427 D4** — the minted serving capability. The blob-backed apps' media round-trip and the future redirect-launch derive from it. Named, deferred.

**Amends**:
- **ADR-435-adjacent (the ArtifactCard ratified stance)** — `ArtifactCard.tsx`'s docstring claim *"opening hands off to Files, never its own frame in chat."* **This ADR supersedes that claim narrowly** (D6): opening an artifact from chat becomes a real mount with its own frame. The sibling claim *"we do not build a window manager"* is **preserved** — the chat-open mount uses existing surface/modal primitives, not a new WM.

**Preserves**:
- **Window = surface** (the load-bearing invariant). No per-file window, no per-file slug. The renderer is frame-agnostic; the mount owns the frame (D2).
- **Byte-identical rendering today.** One app per type → the resolver returns a singleton → the caller mounts `apps[0]` → the same pixels render as before the split. No user-visible change from the debt half except consistency.
- **Mutation through chat (ADR-236); the powerbox (ADR-434); the ADR-245 fallback chain; the closed 9-kind type vocabulary** (the union stays closed until a third party asks — D3).

---

## 1. The problem — one LaunchServices, one monolithic app

The audit (`the-viewer-app-scope-audit-*` §1) established: type **detection** is cleanly factored — `resolveViewerApplication(path, contentType)` returns a closed 9-kind union (`file-types/index.ts:63-72,113`) — but type **rendering** is a monolith: `FileBody` runs a flat sequence of nine `{kind === '…'}` branches (`FileBody.tsx:112-202`), with blob-backed kinds as in-file helpers. **There is no `ImageViewer` / `VideoViewer` / `MarkdownViewer` — one grep confirms only `FileBody` exists.**

In OS terms: yarnnn has **one LaunchServices** (the resolver) dispatching into **one monolithic app**, where macOS dispatches into Preview / QuickTime / TextEdit as independently-replaceable binaries. The dispatch table is real; the apps behind it are not separable. That is the precise gap between *"has a type system"* and *"has apps."* Closing it is simultaneously Finder-parity hygiene and the pre-app ratchet (app-layer §12): the same refactor that pays the monolith debt seeds the third-party app platform.

A second, smaller defect: the **chrome is hand-duplicated** across the two mounts — each of `ContentViewer` and `ArtifactCard` re-implements its own header, its own `getFile` state machine, and calls `describeViewerApplication` independently.

## 2. The decision — an app is a frame-agnostic renderer; the mount owns the frame

The governing audit finding (`the-app-registry-launchservices-model-*` §2): **the unit of "window" is a SURFACE, never a file.** Everything the window manager mounts is a kernel surface slug; `WindowStateMap` is keyed by slug (`surface-preferences.ts:393`). There is no per-file window and no per-file slug. A file opens as an inline detail view *inside* the Files surface.

Therefore a viewer app **must not** get its own window — that would require a per-file slug (impossible against a closed union) or a second parallel windowing system (which `ArtifactCard`'s ratified *"we do not build a window manager"* forbids). The decision:

> **An app is a renderer. It owns file types and draws their content. It does NOT decide its frame — the mount does. The mount is a surface plus a layout mode. This is more macOS-faithful, not less: Preview.app does not decide whether it is windowed or fullscreen; the window server does.**

`FileBody` already proves the pattern — it is "THE one file renderer, mounted by every surface that opens a file" (`FileBody.tsx:3-29`), with `compact` as a display hint, "not a different renderer." The refactor splits the one renderer into seven, behind a table; the mount model is unchanged.

## 3. D1 — the 7 apps, the code-seeded registry, the closed union held

**The 7 apps + 1 terminal:**

| App | Owns kinds | Blob? |
|---|---|---|
| Text Viewer | `text` | no |
| Markdown Viewer | `markdown` (IDENTITY tier-1 case lives inside) | no |
| Web Viewer | `html` (sandboxed iframe) | no |
| Image Viewer | `image` | yes |
| Media Player | `video`, `audio` (owns `BlobMissing` until ADR-427 Ph2) | yes |
| PDF Viewer | `pdf` | yes |
| Table Viewer | `csv` | yes |
| *Download Terminal* | `download` — **not an app**, the resolver's binary terminal + future Open-With/launch home | maybe |

**The registry is a code-seeded table** (`web/lib/file-types/apps.tsx` or adjacent), modeled on `SurfaceRegistry`'s static-import pattern:

```ts
interface AppRegistration {
  id: AppId;                       // opaque id (a string; NOT re-narrowed to a union)
  ownsTypes: ViewerApplication[];  // today's 9-kind vocabulary
  renderer: ViewerComponent;       // the frame-agnostic component
  needsBlob: boolean;              // from today's viewerNeedsBlob
}
const APPS: Record<AppId, AppRegistration> = { /* 7 seeded kernel rows */ };
```

**The closed union is HELD.** `ViewerApplication` stays a closed 9-kind union in the debt half; `AppId` is an opaque string so the table's *shape* admits a stranger's row, but no third-party row is added. **The one-file ratchet-flip** (union → opaque, `APPS` → mutable seeded, app-layer §12) is *confined to* `file-types` + the `APPS` table and **not performed** here — so a future App(principal) ADR flips it in one place, and the CI ratchet ("can a third party replace your viewer with no kernel change?") runs red until then, correctly (ESSENCE v15 positioning).

## 4. D2 — the resolver returns an ordered list; the Open-With picker is deferred

`resolveViewerApplication` (single return) becomes `resolveApps(path, contentType): AppId[]` — an **ordered list** (default first, alternatives after).

- Today every type has exactly one app → `resolveApps` returns a singleton → the caller mounts `apps[0]` → **byte-identical**.
- The **Open-With picker** (the multi-app chooser) renders **only when `resolveApps(file).length > 1`** — the app-layer §11 falsification boundary ("the moment a second app claims the same derived type"). Mechanism now; UI on demand. The first two-app type lights the picker with **no kernel change**.
- The ADR-245 tier chain is preserved: tier-1 path-exact (IDENTITY, routed through the table, not an inline `if`), tier-2 type-exact, tier-3 terminal (`text` / `download`, derived from text-ness).

## 5. D3 — the mount catalog + contract (the whole architecture)

A **mount** is a container that asks the registry for a renderer and frames it. Every "where does a file open" question is "which mount, in which context," answered without touching apps.

| Mount | Status | Frame |
|---|---|---|
| Files-detail | ✅ exists (`ContentViewer` → `FileBody`) | the explorer's detail area |
| Recents tile | ✅ exists (`FileTile`) | a compact card |
| Chat ArtifactCard (render-on-write) | ✅ exists (`ArtifactCard`) | a bounded inline card |
| **Chat-open (explicit open)** | 🔲 **D6** | its own surface/modal frame |
| Desktop tile | 🔲 future (layout ADR — D7) | a floating placed tile |

**The mount contract** (every mount honors it; mounts are addable with zero app changes):

```
resolveApps(file) → pick appId (or Open-With if >1) → <Renderer file={file} {...displayHints} />
  + the mount owns its frame (header/chrome/bounds)
  + the mount owns or shares the data-load (useFileLoad — D4)
  + NEVER edits (mutation → chat, ADR-236)
  + respects the powerbox (ADR-434 — out-of-scope files never reach a mount)
```

## 6. D4 — the shared chrome extraction

Kill the two hand-written `getFile` state machines and the double `describeViewerApplication` call:
- `useFileLoad(path) → { file, revisions?, loading, notFound, error }` — one hook, consumed by both existing mounts.
- `<FileMeta>` — the shared icon + filename + type-label + attribution strip. The *frame* stays per-mount (a document header ≠ a compact card — correct); only the data-load and meta are de-duplicated.

## 7. D5 — Chat-open supersedes the ArtifactCard redirect (narrow, honest)

Today, "Open in Files" from a chat artifact is a redirect (`ArtifactCard.tsx:104-111`) — foreground the Files surface, seeded to the file. This ADR makes **chat-open a real mount**: opening an artifact from chat gives it **its own frame** (a new surface or modal-like container), not a teleport to Files.

**Rationale:** "redirect to Files" was a workaround for *not having a clean mount model.* Once the renderer is frame-agnostic and the mount contract exists (D3), a chat-open mount is cheap and honest — the artifact opens where the operator is looking, carrying its attribution.

- **Superseded**: the ArtifactCard claim "opening hands off to Files, never its own frame in chat."
- **Preserved**: the sibling claim *"we do not build a window manager"* — chat-open uses existing surface/modal primitives, **not** a new WM.
- **Preserved**: the inline `ArtifactCard` (render-on-write) stays; chat-open is the *explicit* open action.
- **Deferred to the layout ADR** (D7): whether chat-open's frame is a new surface or a modal — it depends on the settled layout model (in canvas mode the two may be identical). The app registry is mount-agnostic either way.

## 8. D6 — the known-next: the layout-mode collapse (named, its own ADR)

The layout modes are **arrangers of mounts**, and the mounts are apps — so the layout collapse is *downstream* of this registry. Recorded here so the thread survives; **designed in a separate ADR.** Operator's recorded direction (not ratified in this ADR): canvas (focus) as default, desktop as a *real* spatial desktop, and "open a file" resolving per-context (Files → on-surface; Chat → its own frame; desktop → a floating tile). A spatial-artifact-canvas is a layout-ADR candidate scoped **arrange-not-edit** (provenance-on-every-tile is the wedge Figma cannot offer; editing is the OpenDoc/Figma feature-race the app-seam frame refuses).

## 9. Scope — debt half (this ADR builds) vs. capability half (named)

**Debt half — build now, no ADR-427 dependency:**
- D1 split the monolith → 7 frame-agnostic renderer apps behind `APPS`.
- D2 `resolveApps` returns an ordered list (picker deferred).
- D3 mount contract + the Chat-open mount (D5).
- D4 `useFileLoad` + `<FileMeta>` extraction.
- Tier-1 IDENTITY routed through the table (no inline `if`); `shapeForPath` NOT wired (invention until a second bespoke path-renderer exists).

**Capability half — named, deferred (each its own ADR):**
- The union→opaque ratchet-flip + a data-backed registry (App(principal)).
- The redirect-launch verb + the ADR-427 D4 minted serving capability.
- The Desktop-tile mount + the layout-mode collapse (D6).
- Media round-trip for the blob-backed apps (ADR-427 Phase 2/3).

## 10. Consequences

- **Positive**: the OS's type→app dispatch gains real, replaceable apps; Finder-parity consistency (one renderer, N frames); the pre-app ratchet is one-file-confined; chat gets an honest open; `content_url`'s single FE consumer stays single (`useSignedBlobUrl` inside the blob-backed apps), so ADR-427 Phase 3's column retirement lands in one place.
- **Cost**: `FileBody` splits into ~10 small files (7 apps + terminal + dispatcher + shared meta); one new mount (Chat-open) to build + a `SubstrateEditor`-era stance superseded (D5). Bounded, FE-only, byte-identical rendering.
- **Risk**: low — the debt half is byte-identical for rendering (singleton resolver), touches no backend, no schema, no ADR-427 dependency.

## 11. The one-line statement

**The monolithic file viewer becomes 7 named frame-agnostic renderer apps behind a code-seeded registry whose shape admits a stranger's row but seeds only ours; an app owns types and draws content while the mount owns the frame (window = surface, an invariant); the resolver returns an ordered list with the Open-With picker deferred until a type has two apps; chat gains a real open mount superseding the redirect-only stance while preserving "no second window manager"; and the layout-mode collapse is the named known-next, downstream of this registry because it arranges mounts and the mounts are apps.**
