# The Viewer-as-App — Audit, Scope, and FE Surfacing

*The Finder is factored; the viewer is a monolith; Home is already a composition. What "reference apps" actually means, made buildable.*

> **Status**: Scoping analysis (2026-07-10). Doc-first, receipts-backed @ `7a03a8c`. **No ADR rides this yet** — this doc scopes the work so a viewer/reference-app ADR can be written against a real map. It is the implementation companion to `the-app-seam-first-party-viewer-vs-third-party-principal-2026-07-10.md` (the *direction*), the way `the-powerbox-scope-audit-implementation-fe-2026-07-10.md` was the companion to the commons-is-the-OS thesis. **This is a genre shift**: the three prior docs answered *should we / in what order*; this one answers *what exactly ships, in what FE surfaces, at what blast radius.*
> **Authors**: KVK, Claude
> **Hat**: A (system canon). Vocabulary: operator, surface, viewer, app, mount, chrome, composition, registry, reference app, launch verb.
> **Method**: two parallel code audits @ `7a03a8c` (the viewer factoring; the surface registry vs. Home). Every structural claim carries a `file:line`. Where a prior doc asserted a shape, this doc marks it CONFIRMED or REFUTED against the audit.
> **The one-sentence frame**: the OS's *type→app dispatch* is real but its *apps* are one monolith; the OS's *surface≠app* line is real and already drawn; the reference-app work is **splitting the monolith into per-type viewers behind the resolver** — which is simultaneously Finder-parity hygiene *and* the pre-app ratchet the canon already named.

---

## 0. Read this first — what this doc IS and IS NOT

- **IS**: an audit of how the shipped viewer is factored, a scoping of the "reference apps" work (per-type viewers, shared chrome, the launch-verb seam), and an adjudication of "should surfaces — even Home — become apps?"
- **IS NOT**: an app-principal ABI, a third-party runtime, the minted capability, or binary Category-1. Those are the app-seam doc's §5/§6 (deferred, ordered after this). This doc is the *first-party reference viewer* only — the thing the app-seam doc §6 says comes **before** any third-party principal.
- **The debt vs. the capability**: like the powerbox audit, the work splits into a **debt half** (the viewer is mis-factored against its own stated design — derivable, shippable now) and a **capability half** (per-type apps as replaceable units + the launch verb — shaped by the app-seam sequencing, gated on ADR-427). This doc scopes the debt fully and sketches the capability's seam.

---

## 1. The audit — three findings, verified @ `7a03a8c`

### Finding 1 — type *detection* is cleanly factored; type *rendering* is a monolith. (CONFIRMED, sharper than the app-seam doc claimed)

The app-seam doc said "one viewer, two mounts" and left it there. The audit sharpens it: the "one viewer" is **one component with nine inline render branches**, not a dispatcher over per-type viewers.

- **Detection is clean.** `resolveViewerApplication(path, content_type)` (`web/lib/file-types/index.ts:113`) returns a **closed 9-kind union** — `'markdown' | 'html' | 'image' | 'video' | 'audio' | 'pdf' | 'csv' | 'text' | 'download'` (`:63-72`) — via a real tier-2/tier-3 fallback chain (`:120-136`). `FileBody` calls it exactly once (`FileBody.tsx:103`).
- **Rendering is monolithic.** `FileBody.tsx` then runs a **flat sequence of nine `{kind === '…' && (…)}` blocks** (`:112-202`), with blob-backed kinds delegating to helper function-components defined *lower in the same file* (`ImagePreview:211`, `VideoPreview:219`, `AudioPreview:233`, `PdfPreview:244`, `CsvPreview:296`). **There is no `ImageViewer.tsx`, `VideoViewer.tsx`, `MarkdownViewer.tsx` anywhere in the tree** — a grep for `*Viewer|*Preview` across `web/` returns only `FileBody.tsx`.

> **The OS reading**: yarnnn has **one LaunchServices** (`resolveViewerApplication`) dispatching into **one monolithic app**, where macOS dispatches into Preview / QuickTime / TextEdit as independently-replaceable binaries. The dispatch table is real; the apps behind it are not separable. **This is the precise gap between "has a type system" and "has apps."**

### Finding 2 — the chrome is hand-duplicated across the two mounts. (CONFIRMED, new)

The body is genuinely singular (one `FileBody`), but each mount **re-implements overlapping chrome from scratch** rather than sharing a chrome primitive:

- **Mount A — `ContentViewer.tsx`** (Files document chrome): its own header (`:429-501`), its own `getFile` + `listRevisions` fetch with its own loading/404/error/empty state machine (`:315-345`, `:377-423`), the delete/Move-to-Trash verb (`:484-498`), `EditInChatButton`, `FileActions`.
- **Mount B — `ArtifactCard.tsx`** (chat mount): its own compact header (`:88-112`), its own `getFile` fetch with its own loading/404/error states (`:62-77`), a collapse/expand affordance (`:137-157`), "Open in Files" handoff. No delete, no edit, no FileActions.
- **The duplication**: both build a header from `FileIcon` + filename + a metadata strip; **both call `describeViewerApplication(...)` independently** (`ContentViewer.tsx:445`, `ArtifactCard.tsx:100`); both run their own `getFile` state machine. This is copy-paste, not a shared `<FileChrome>` / `useFileLoad()` primitive.

> **This matches the codebase's own stated design** (the `FileBody` and `ContentViewer` header comments say chrome is intentionally per-mount) — but "intentionally per-mount chrome" and "two hand-written `getFile` state machines" are different claims. The *frame* being per-mount is correct (a card ≠ a document header); the *data-load + type-label* being re-implemented is incidental duplication.

### Finding 3 — "surfaces are apps" is FALSE; but Home is already a composition. (REFUTED with a twist — the load-bearing adjudication)

The operator's intuition — *"couldn't Home evolve from a primitive surface to an app?"* — splits into a false blunt claim and a true deeper one.

**The blunt claim is false, on the code's own terms.** The `register` field is **not** the `mirror`/`composition` enum a prior mental model assumed — it is an **unvalidated string with three de-facto values**: `application | intent | os-config` (`kernel_surfaces.py`, validated by `test_adr309_two_registers.py:59`). Crucially, **`home` and `files` both carry `register: "application"`** (`kernel_surfaces.py:238,543`) — the register does *not* distinguish Home's compositional nature from Files' flat-mirror nature. The registry is heterogeneous: of 26 rows, ~10 are window-grade mountable components, 4 are panes-inside-a-parent, 3 are non-navigable chrome, ~6 are dormant/routeless. `KernelSurfaceSlug` is a **closed, CI-parsed union** (`desk.ts:26-70`; the three-way parity gate `test_adr338_surface_registry_parity.py`). A surface is a **substrate-mirror viewport keyed by a closed-union slug**; an app is a **principal with a grant**. These are architecturally distinct, and the app-layer doc's F7 finding ("apps are not surfaces at all") holds.

**But the twist vindicates the deeper instinct: Home is *already* not a primitive surface.** It is the **only** surface whose middle content is a two-layer composition (`home/page.tsx:6-8`: *"a composition over the workspace's present constituents"*):
- A fixed kernel half (`HomeFrontPage` — six slots, static imports, self-hiding when empty).
- A dynamic program half (`ProgramCockpit` — renders program-declared `home.program_sections` from `SURFACES.yaml` through `dispatchComponent({ kind })`, `ProgramCockpit.tsx:48-52`).

And that composition runs through a **second, separate registry** — `LIBRARY_COMPONENTS` / `dispatchComponent` (`web/components/library/registry.tsx:86,156`), a free-form `kind`-string → renderer table, distinct from the closed-union `KERNEL_SURFACE_REGISTRY` (`SurfaceRegistry.tsx:85`). Two registries, two kinds:

| | `KERNEL_SURFACE_REGISTRY` | `LIBRARY_COMPONENTS` |
|---|---|---|
| Keys | `KernelSurfaceSlug` (closed union) | free-form `kind` strings |
| Values | full page components | middle-band section renderers |
| Resolution | static, exhaustive dict | `kind` dispatch, warns on miss |
| Populated by | code (imports) | code + program `SURFACES.yaml` |

> **The adjudication**: *"Home should become an app"* is a **vocabulary error for a real thing that already exists.** The app-like layer — dynamic, declared, `kind`-dispatched composition — is **already shipped**, confined to one surface (Home's program tab), on its own registry. The correct statement is **"Home is a composition, and the composition layer is underused"** — not "Home is an app." Promoting Home to an `app` (a principal? a launched process?) would break the surface-registry invariants for nothing. The genuine opportunity is the inverse: **more surfaces could become compositions** over the already-shipped `LIBRARY_COMPONENTS` registry — but that is a *surface-composition* thread (ADR-340 "mirror once, compose few"), **not the app-seam thread**, and it must not be renamed into it.

---

## 2. The two "app" words, kept separate (the discipline this doc enforces)

The audit forces a vocabulary the rest of the doc holds to, because fusing these two is the exact drift the last three docs fought:

- **App(composition)** — a surface whose interior is *assembled* from `kind`-dispatched sub-components (`dispatchComponent`), rather than a single hardcoded body. **First-party, kernel/program-authored, in-shell, no grant, no principal.** Home is the one live instance. This is ADR-312/340 territory.
- **App(principal)** — a *third party's program* that holds a `principal_grants` row and attributes revisions as itself, launched (redirect + scoped token) into its own window. **Deferred, demand-gated, needs the powerbox's minted capability + `role='app'`.** Zero live instances. This is the app-seam doc's §5/§6 territory.

> **The per-type viewer work in this doc is neither of those yet.** A per-type viewer (an `ImageViewer` component behind the resolver) is a **first-party in-shell renderer** — App(composition)-shaped in its factoring, but it is not a composition surface and not a principal. It is the **reference app** (Preview.app): the thing that, built correctly, makes App(principal) *expressible later* by turning the closed union into a table. That is why it comes first (app-seam §6).

---

## 3. Scope — the debt half (ready now, all first-party, no ADR-427 dependency)

Three pieces, in dependency order. All are FE + thin backend, byte-neutral to the substrate, shippable independently.

### D.1 — Split the monolith into per-type viewers behind the resolver

Turn `FileBody`'s nine inline branches into a **dispatch over per-type viewer components**, seeded with the nine kernel defaults. Concretely:

- Extract `MarkdownViewer`, `HtmlViewer`, `ImageViewer`, `VideoViewer`, `AudioViewer`, `PdfViewer`, `CsvViewer`, `TextViewer`, `DownloadTerminal` as standalone components (the `*Preview` helpers already in `FileBody.tsx` are 80% of this — they just move out and gain the non-blob kinds).
- `FileBody` becomes a **~30-line dispatcher**: `resolveViewerApplication` → a `VIEWERS: Record<ViewerApplication, ViewerComponent>` lookup → mount. The `compact` prop threads through unchanged.
- **This is the app-layer doc §12 pre-app ratchet, done as hygiene.** Today the ratchet runs red ("can a third party replace your viewer with no kernel change?" — no, closed union + static switch). D.1 makes the switch a **table**; the nine viewers become **ordinary rows**. The union stays closed *for now* (no third party yet), but the shape is one edit from opaque-app-id. **The refactor that pays the Finder-parity debt is the same refactor that seeds the app platform.**

> **Blast radius**: one file split into ten small ones (`FileBody.tsx` → `viewers/*.tsx` + a dispatcher). No backend, no schema, no resolver change (the union is unchanged in D.1). `tsc` exhaustiveness on `Record<ViewerApplication, …>` *guarantees* every kind has a viewer — a strictly stronger invariant than the current flat branch run.

### D.2 — Extract shared chrome (`useFileLoad` + `<FileChrome>`)

Kill the two hand-written `getFile` state machines and the double `describeViewerApplication` call:

- `useFileLoad(path) → { file, revisions?, loading, notFound, error }` — one hook, both mounts consume it. Removes `ContentViewer.tsx:315-345` and `ArtifactCard.tsx:62-77` as parallel implementations.
- The *frame* stays per-mount (a document header ≠ a compact card — correctly per the codebase's stated design), but the **metadata strip** (icon + filename + `describeViewerApplication` label + attribution) becomes a shared `<FileMeta>` the two frames compose. Each frame keeps its own outer shell + verbs.

> **Blast radius**: two components lose their private data-load; one new hook + one small shared meta component. Pure FE. This is the "how bolted-on is it" answer made clean: **the body was singular, the chrome was copy-pasted, D.2 de-duplicates the copy-paste without merging the two genuinely-different frames.**

### D.3 — The tier-1 seam (name it, don't wire it)

Tier-1 (path-exact → bespoke renderer) is today a **hardcoded `IDENTITY_PATH` const inside `FileBody`** (`:46-50,112-116`), and `content-shapes/shapeForPath` — a real path-glob resolver — has **zero consumers**. D.1 should route the IDENTITY special-case through the same `VIEWERS` table (a path-tier lookup *before* the type-tier lookup), so tier-1 stops being an inline `if` and becomes the first stratum of the dispatcher. **Do not wire `shapeForPath`** — a path→component table is invention until a second bespoke path-renderer exists. Just make the IDENTITY case a table row, not an inline branch.

---

## 4. Sketch — the capability half (leave the seams; gated on the app-seam sequence)

Held for after ADR-427 Phase 2/3, per the app-seam doc §6. Named so D.1–D.3 don't foreclose them:

- **`ViewerApplication` → opaque app id.** The app-layer doc §12's flip: the closed union becomes an opaque id; `VIEWERS` becomes a **mutable table seeded with the nine kernel rows**; a third party's viewer is an indistinguishable row. **Seam left in D.1**: because D.1 already makes `VIEWERS` a `Record`-lookup, this is a *type change + a seed*, not a re-architecture. The switch never comes back.
- **The launch verb.** A viewer for a type you *can't render in-shell* (a proprietary format) launches out (redirect + scoped token). **Seam left**: the dispatcher's terminal (`download`) is the natural home for a future "Open With…" that offers a launch instead of a byte-dump. Not built; the terminal is where it lands.
- **The minted serving capability (ADR-427 D4).** A per-type *media* viewer round-tripping a real blob needs the minted, object-scoped, expiring serving URL. `FileBody.useSignedBlobUrl` is **already the single FE consumer of `content_url`** (the app-seam doc §11 dividend) — so when Phase 3 replaces the stored column with a minted field, the change lands in **one hook**, and D.1 keeps it that way (every blob-backed viewer routes through it).

> **The sequencing knot, resolved.** The app-seam doc §6 listed "ADR-427 Phase 2/3 → read-only viewer," which *reads* as "build serving before the viewer." The audit resolves it: **D.1–D.3 (the split + chrome) need nothing from ADR-427** and should ship now — they make the viewer *replaceable* and pay the Finder debt. The viewer's *media* capability (round-tripping a real versioned blob) is what waits for Phase 2/3. So: **split now (debt), serve later (capability), and the split makes the serve land in one hook.** No knot — two independently-shippable halves.

---

## 5. FE surfacing — what the operator actually sees

The debt half is **invisible as a concept** — the operator sees the same Files surface and the same chat cards, just consistent. Three visible dividends, mapped to existing homes (no new surface — DP29):

- **6.1 — Consistent card↔detail identity.** After D.1 (shared radius/ground tokens already landed in `18979c8`) + D.2, a file looks *identical* in its Recents tile, its chat artifact card, and its full detail view — one viewer, one meta strip, three frames. The Finder-parity pass started this; D.1/D.2 finish it.
- **6.2 — Honest per-type states.** `BlobMissing` (a versioned `.mp4` with no bytes yet — the honest state until ADR-427 Phase 2) becomes a **per-viewer** concern, so a `VideoViewer` can say *"this video has no stored bytes yet"* with video-appropriate chrome, not a generic empty box. Each viewer owns its empty/loading/error states.
- **6.3 — The "Open With" affordance (sketch only).** The `download` terminal is where a future launch verb surfaces. **Not built in the debt half** — named so the terminal isn't designed to preclude it.

**What the FE does NOT get in the debt half**: no third-party viewers (App(principal) deferred), no launch-out (the terminal stays a byte-dump), no media round-trip (waits for Phase 2/3), no surface-composition changes (Home stays as-is; §1 Finding 3).

---

## 6. Sequencing summary

```
1. D.1  split the monolith → per-type viewers behind a VIEWERS table   ── FE; pays the Finder debt AND seeds the app platform (one refactor)
2. D.2  extract useFileLoad + <FileMeta>                                ── FE; de-dupes the two hand-written chromes
3. D.3  route tier-1 (IDENTITY) through the table, don't wire shapeForPath
4. → the viewer/reference-app ADR (debt half ratified; capability seams named)
   ── THEN ADR-427 Phase 2/3 (binary Cat-1 + minted serving) — the app-seam sequence
   ── THEN ViewerApplication → opaque id + the launch verb (App(principal) territory, demand-gated)
```

The debt half (D.1–D.3) is a **self-contained, shippable Finder-parity + pre-app-ratchet refactor** with no ADR-427 dependency. The capability half is **app-seam-sequenced** and waits for binary + serving. The viewer ADR can be written after the debt half with the capability seams named — the same "build the debt now, shape the capability against the sequence" split the powerbox took.

---

## 7. What this document does NOT do

- **Does not build the per-type viewers.** It scopes them (§3) and names the seam to App(principal) (§4).
- **Does not promote Home (or any surface) to an app.** It refutes that framing (§1 Finding 3) and names the real thing (Home is a composition; the composition layer is underused — a *separate*, ADR-340 thread).
- **Does not wire `shapeForPath` or invent a path→component table.** Tier-1 stays a table row for the one bespoke path (IDENTITY); a general path-renderer table is invention until a second one exists (§3 D.3).
- **Does not touch the minted capability or binary Category-1.** Those are ADR-427 Phase 2/3, sequenced after the debt half (§4, §6).
- **Does not merge the two mount frames.** A document header and a compact card are genuinely different; D.2 shares the *data-load and meta*, not the frame (§3 D.2).
- **Does not reopen positioning or the app-principal ABI.** The demand gate holds (app-seam §8); this doc completes the *first-party viewer* map that precedes it.

---

## 8. The one-line statement

**The OS's type→app dispatch is real but its apps are one monolith and its chrome is copy-pasted twice — so the reference-app work is a three-step first-party refactor (split the monolith into per-type viewers behind a table, extract the shared file-load and meta, route tier-1 through the table) that pays the Finder-parity debt today and, in the same edit, seeds the App(principal) platform for later; and "Home should become an app" is a vocabulary error for a real thing already shipped — Home is a composition, the composition layer is underused, and that is a different thread than apps, kept separate on purpose.**

---

## Appendix A — receipts index

| Claim | Receipt |
|---|---|
| `resolveViewerApplication` returns a closed 9-kind union | `web/lib/file-types/index.ts:63-72,113` |
| `FileBody` calls the resolver once, then a flat 9-branch run | `FileBody.tsx:103,112-202` |
| No per-type viewer components exist (grep `*Viewer/*Preview` → only FileBody) | audit §4 |
| Blob kinds delegate to in-file helpers, not separate modules | `FileBody.tsx:211,219,233,244,296` |
| `compact` is a display hint (heights + CSV limit), not a different tree | `FileBody.tsx:108,254,297` |
| Two mounts, each with its own header + getFile + states | `ContentViewer.tsx:315-345,429-501` · `ArtifactCard.tsx:62-77,88-112` |
| `describeViewerApplication` called independently in both mounts | `ContentViewer.tsx:445` · `ArtifactCard.tsx:100` |
| Only ContentViewer carries the delete/Move-to-Trash verb | `ContentViewer.tsx:484-498` |
| `register` is an unvalidated string, 3 values `application/intent/os-config` | `kernel_surfaces.py` · `test_adr309_two_registers.py:59` |
| `home` and `files` BOTH carry `register: "application"` | `kernel_surfaces.py:238,543` |
| `KernelSurfaceSlug` is a closed, CI-parsed union | `desk.ts:26-70` · `test_adr338_surface_registry_parity.py:103-155` |
| `SurfaceRegistry` static-imports every window-grade surface | `SurfaceRegistry.tsx:35-106` |
| Home is "a composition over the workspace's present constituents" | `home/page.tsx:6-8` · `HomeRenderer.tsx:9-13` |
| Home's program tab dispatches program_sections through `dispatchComponent` | `ProgramCockpit.tsx:48-52` · `alpha-trader/SURFACES.yaml:31-45` |
| `LIBRARY_COMPONENTS`/`dispatchComponent` is a SEPARATE registry from the surface registry | `library/registry.tsx:86,156` vs `SurfaceRegistry.tsx:85` |
| Home is the only surface feeding program-declared kinds into that registry | audit §4-5 |
| `useSignedBlobUrl` is the single FE consumer of `content_url` | app-seam doc §11 · `FileBody.tsx` |
| The pre-app ratchet (closed union → mutable table) is one file | app-layer doc §12 · `FileBody.tsx` |
| Shared radius/ground tokens landed in the Finder-parity pass | commit `18979c8` (TILE_PREVIEW_RADIUS/GROUND) |

## Appendix B — the debt/capability split, as a decision table

| | **Debt half (D.1–D.3)** | **Capability half (§4)** |
|---|---|---|
| Findings | 1 (monolith) + 2 (dup chrome) | per-type apps as replaceable units + launch verb |
| Correct behavior is… | **derivable** from the viewer's own stated design | **shaped** by the app-seam sequence + ADR-427 |
| ADR-427 dependency | **none** | Phase 2/3 (binary + minted serving) |
| Blast radius | one file → ten small; two hooks | type change + seed + a launch verb |
| Ships as | a Finder-parity + pre-app-ratchet refactor | App(principal) territory, demand-gated |
| Safe to build now? | **yes** | **no — after the debt half + ADR-427** |
