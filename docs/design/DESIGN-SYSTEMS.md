# Design systems in the Studio — the housing, the import, and the open apply question

**Status**: the housing + import are live (ADR-449 + ADR-462 D11/D13/D14, 2026-07-16).
**The apply half is under active reconsideration** — this doc parks what is built so the
apply discourse has a clean record to revise against. Read §5 before proposing changes.

> One-line map: a design system is an ordinary meaning-folder identified by `_design.yaml`;
> an artifact wears it as a marked, cited `<style>` element; the import is a flatten + a
> binary lane, not a schema interpreter; **how the skin actually reaches the pixels is the
> part still in question.**

---

## 1. The housing (ADR-449 — ratified, live)

A design system is **not** a kernel file-type, a protected folder class, or a registry row.
It is an ordinary workspace folder that happens to contain a `_design.yaml` manifest:

```yaml
name: YARNNN Design System
css:
  - styles.css          # ordered, folder-relative CSS sources
```

- **Discovery** = the manifest search (`find_design_systems`). No registry to maintain.
- **Placement carries no meaning.** `design-system/yarnnn/`, or inside a project folder —
  the path is the operator's business (ADR-320 topology is unrelated; the folder is just
  substrate). Nothing is seeded (ADR-414 pure genesis: the kernel names the *category*,
  the operator authors the *instance*).
- **Scope is one workspace.** A design system is substrate, so it is scoped like every
  other file. Sharing across workspaces is not a design-system question — it is ADR-378
  (the workspace is the outermost unit; federation is deliberately unbuilt). Many systems
  *per* workspace, yes; one system *across* workspaces, no.

### How an artifact wears it

The artifact's `<head>` carries two style regions with distinct owners:

| Element | Owner | Replaced by |
|---|---|---|
| `<style>` (unmarked) | the kernel layout skin (`STUDIO_LAYOUTS[…].skin`) | a **layout** switch |
| `<style data-kernel="true">` | the kernel token CSS (ADR-453, self-retrofitting) | a kernel version bump |
| `<style data-skin="true" data-ref="<manifest>">` | the **workspace design system** | a **design-system** apply |

The cascade order is the whole mechanism: unmarked layout < `data-kernel` tokens <
`data-skin`. The marked skin sits **last in `<head>`**, so it overrides by cascade order
with **no `!important`**. A layout switch replaces only the unmarked element and never
touches the skin; a design-system apply replaces only the skin.

Because the skin's `data-ref` points at the manifest, the **ADR-448 write-door lift records
the reference edge automatically** on every artifact write: the manifest's dependents are
the artifacts wearing it, Files warns before it is trashed, and `trace` walks
artifact → design system. The contract costs one attribute.

**Code**: `services/design_systems.py` — `find` · `resolve` · `compose_skin_element` ·
`apply_skin_to_html` · `remove_skin_from_html`, all pure/read-only. The apply lands through
the one mechanical write door (`applySkin`, the FE mirror), never a second path.

---

## 2. The import (ADR-462 D11/D13/D14 — live)

The mechanism ADR-449 D1 *assumed* ("drop the folder in, get a manifest written") but never
built. Driven against the operator's real export, which taught more than the reading did.

### What an export actually is — measured, not assumed

The live YARNNN + Concorn folders are **11 items each, and mostly NOT skin**: `components/`,
`ui_kits/`, `guidelines/*.card.html`, a 508 KB `_ds_bundle.js`, a lint config, per-kit
prompt files, and a vendor `_ds_manifest.json`. What the ADR-449 contract consumes is **one
CSS string.**

So the import is a **search for the entry point plus a flatten** — never an interpretation
of the vendor's schema. `_ds_manifest.json` is read for exactly one field (a display name we
would otherwise ask for) and is **never a second contract**. Parsing one schema per vendor
is the road not taken.

### The flatten — the bug v1 would have shipped silently

`styles.css` is an `@import` manifest and nothing else:

```css
@import "./tokens/fonts.css";
@import "./tokens/colors.css";
…
```

ADR-449 v1 concatenated the manifest's `css:` list **verbatim** into an inline `<style>` —
where a relative `@import` cannot resolve. Naming `styles.css` (the file every export tells
you to consume) would have produced a skin of dead import lines: **silently no styling**, the
worst failure shape because it looks applied.

`flatten_css` inlines the `@import` graph depth-first in cascade order, cycle-safe, and
reports what it could not read. Three sub-bugs the real bytes caught:

- **A CSS comment is not code.** The live `styles.css` header says *"It is an @import
  manifest;"* — the first run tried to import a file named `manifest;`. Comments strip first.
- **A `url()` resolves against its own file, not the entry.** `tokens/fonts.css` reaches
  the font as `../assets/fonts/…`; rewriting once over the merged blob put it one directory
  too high. Rewriting is per-file, before the merge.
- **A vendor id is not a name.** The export's only name field is
  `namespace: YARNNNDesignSystem_36fab3`. The folder / filename is the better evidence.

### The binary lane — fonts and images (ADR-462 D13)

A design system's `@font-face` is a **citation, not an inline** — arithmetic, not taste:
Pacifico is 411 KB base64 against a 120 KB skin ceiling (3.4× over). But two walls:

1. `workspace_blobs.content` is **TEXT** (ADR-427 Phase 1; the object-store driver is
   Phase 2/3, reserved and unbuilt) — a TTF cannot go down the ordinary substrate path.
2. The `documents` bucket enforces `allowed_mime_types`.

So binaries ride the **ADR-395 lane images already use**: the `documents` bucket, with
`workspace_files.content_url` pointing at the stable blob endpoint. `content` stays empty
(the raw-upload shape); the row carries the address. Classification (`design_system_import.py`):

- `skin` (`.css`) + `doc` (`.md`, `.svg` — SVG is TEXT, no bucket) → ordinary substrate.
- `font` / `image` (`.ttf/.woff2/.png/…`) → the bucket, one `content_url` row each.
- `vendor` (everything else: bundles, components, lint configs) → skipped, named in the receipt.

**The font gap that was, and is closed**: the bucket shipped no font MIME types, so an upload
was a 415. `FONT_UPLOAD_SUPPORTED` gated it — the import *warned* rather than half-landing a
skin whose `@font-face` points at nothing. On 2026-07-16 the operator added
`font/woff2|woff|ttf|otf` to the bucket; the flag flipped `True`; Pacifico now round-trips
byte-identical. **The flag stays a named constant** — if the bucket policy ever narrows, the
import goes back to warning.

### Serving the font (ADR-462 D13, projection side)

Opening the bucket got the bytes in; it did not make the font render. The projection resolved
`data-ref` on **elements** (`<img>`, backgrounds) and skipped `<style>` elements outright —
correctly, since resolving *into* a marked skin caused the ADR-456 W3 skin-stomp. So the
font's `url()` was invisible to it. The fix rewrites the `url()`s **inside** the skin's text
(`resolveStyleUrls`), swapping each workspace path for a signed blob URL — an `<img data-ref>`
and an `@font-face src` reach the same signed URL by different roads. (A style element is
never `data-src-html` stamped: it would URI-encode the whole skin and hand the restore path
signed URLs to bake into source.)

### The door (ADR-462 D14 — the UX)

`POST /api/studio/design-systems/import` (multipart, a `.zip`). A zip because a design system
**is a folder** on the way over, and a folder reaches a browser as an archive. The entry point
is the Design tab's document scope — **"Import a design system…"** / **"Import another…"** —
and the **receipt renders in the picker, warnings included**: *"YARNNN Design System — 15
files · 5 stylesheets flattened · 61 vendor files skipped."* A warning is the product; an
import that half-lands silently is the failure the whole arc prevents.

Zip handling learned two more real-archive facts: the live export **has no wrapper folder**
(files at the zip root → the display name falls back to the filename), but a **wrapped** zip
is the common case (strip the shared root, or `styles.css` lands one directory deep and the
manifest resolves nothing). `__MACOSX/` forks are dropped.

---

## 3. Receipts (2026-07-16)

The real 1.3 MB YARNNN export, end-to-end through the live path:

```
display name  "YARNNN Design System"   (from the filename — no wrapper folder)
written       15 files                 61 vendor files skipped
flatten       6 sources, 0 @import left, 0 warnings
              styles → fonts → colors → typography → spacing → effects
font          Pacifico-Regular.ttf → the bucket, 315,408 bytes back byte-identical
              TTF magic \x00\x01\x00\x00 · content_type font/ttf · content_url present
discovery     find_design_systems → "YARNNN Design System"
posture       build_design_system_section now names it (dead code until the first system existed)
```

Gates: `test_adr449_design_system.py` (housing + flatten + import, 36 checks),
`test_adr462_context_menu.py` (the projection D13 checks). Both breach-tested.

Probes (Hat-B, receipts in-file): `probe_design_system_import.py` (import, 11/11),
`probe_studio_deck_quality.py` (the lane that authors artifacts to wear a skin).

---

## 4. The division of labor (why this shape)

| Layer | Who | What |
|---|---|---|
| **Kernel** | ships grammar | the `_design.yaml` convention, the marked-element contract, the cascade rule, the flatten, the one door — categories, never instances of taste |
| **Import** | mechanical | flatten + classify + write. Zero LLM where deterministic; the entry-point search and the manifest are mechanical facts |
| **AI (bound lane)** | authors instances | the design system a member *asks Freddie to derive* from a source (ADR-450 `design-system` recipe); registry-uncovered bespoke CSS on a metered turn |
| **Member** | composes free | picks Apply; imports the zip |

**Supply vs select** — the seam that keeps typography and design systems distinct: a design
system *supplies* faces (its `@font-face`s, the stacks it names); the ADR-455 `font` token
*selects* among what is available. One is the workspace's identity worn by many artifacts;
the other is a per-artifact choice. They must not merge — merged, picking "Mono" on one deck
would fight the skin.

---

## 5. THE OPEN QUESTION — how a skin reaches the pixels (parked for revision)

Everything above is about getting a design system *into* the workspace and *cited by* an
artifact. **Whether it visibly changes anything is a separate, still-open question**, and it
is why this discourse is parked rather than closed.

### The theme contract, and the gap it leaves

The kernel chrome (buttons, galleries, toggles, tone fills) themes through **five custom
properties** (STUDIO.md §Theme, ADR-456 W3): `--ink` · `--paper` · `--muted` · `--accent` ·
`--radius`. The derive recipe names them; the Design tab shows the applied skin's variables
read-only.

**A design system's tokens only paint where its names match those five.** The imported YARNNN
system defines `--ink` (so that one bites) but also `--yarn-orange`, `--cream`, an entire
`--c-*` palette — none of which the kernel consumes. So a correct apply can land 5.7 KB of
valid CSS and leave a deck looking almost unchanged. **This is not a bug in the import; it is
the apply model being thinner than the systems it now accepts.**

### The questions the apply discourse must answer

1. **Whose names win?** Does the kernel keep a fixed five-variable contract and expect design
   systems to map onto it (an *adapter* at import: "this system's `--yarn-orange` is your
   `--accent`")? Or does the kernel consume more of what a real system ships?
2. **Does the skin restyle blocks, or only the chrome?** Today the marked element overrides by
   cascade, but the block/arrangement CSS lives in the `data-kernel` element with its own
   variables. How much of a block's look is a design system *allowed* to reach?
3. **Where does the mapping live if there is one?** An import-time adapter (rewrite the CSS),
   a manifest field (`maps: {accent: --yarn-orange}`), or a lane judgment (Freddie authors the
   bridge)? Each has a different cost and a different owner.
4. **The mechanical var-editor** (STUDIO.md §Theme, named-deferred) — editing a theme value
   from the Design tab needs the `PATCH /workspace/file` editable-prefix surface widened to
   design-system folders. A permission decision that the apply model may force.

### What is safe to build on, and what is not

- **Safe** (the housing + import are settled): the `_design.yaml` convention, the marked
  cited element, the cascade order, the flatten, the binary lane, the import door. Downstream
  work can assume a design system arrives correctly and is cited correctly.
- **Not settled** (do not build on): the five-variable theme contract as the *final* apply
  surface, and the assumption that a well-formed skin visibly restyles an artifact. The
  apply discourse may revise `resolve`/`compose`/`apply_skin_to_html`, add an import-time
  adapter, or widen the theme contract — any of which reshapes what "apply" means.

**When the apply discourse opens, start here** and at STUDIO.md §Theme. The receipts in §3
are the ground truth to revise against.

---

## 6. File map

| Concern | Location |
|---|---|
| Contract (parse/discover/resolve/compose/apply) | `api/services/design_systems.py` |
| Flatten + url-rewrite | `api/services/design_systems.py::flatten_css` / `rewrite_urls` |
| Import (classify/plan/write/binary lane) | `api/services/design_system_import.py` |
| Import door (zip → folder) | `api/routes/studio.py::import_design_system_route` |
| The bound-lane posture section | `api/services/lane_runner.py` (the `artifact_path` branch) |
| The derive recipe (AI authors one) | `api/services/derive_recipes.py::DERIVE_RECIPES["design-system"]` |
| FE picker + import UI | `web/components/studio/StudioDesignTab.tsx` (document scope) |
| FE skin url() resolution | `web/components/workspace/viewers/projection.ts::resolveStyleUrls` |
| The theme contract (the apply seam) | `docs/design/STUDIO.md` §Theme + the layer table |
| Gates | `api/test_adr449_design_system.py` · `api/test_adr462_context_menu.py` (D13) |
