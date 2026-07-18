# Design systems in the Studio — the housing, the import, and the apply model

**Status**: the housing + import are live (ADR-449 + ADR-462 D11/D13/D14, 2026-07-16).
**The apply model is decided (§5, 2026-07-16) and not yet built** — a coverage probe turned
the "why does a correct apply barely change anything" question into a measurement, and the
measurement drew the fix: widen the kernel token contract from five point-vars to a small
*families* vocabulary, plus a declarative `maps:` synonym bridge. Read §5 for the decision;
§3 has the receipts.

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

### The apply-gap coverage probe (2026-07-16 — the measurement §5 rests on)

`probe_design_system_coverage.py` flattens the real YARNNN export (the same bytes the live
import consumed) and classifies every custom property the skin **defines** against the five the
kernel chrome **consumes**. It is the honest first move the apply question demanded — a
histogram, not a prediction:

```
flattened skin        5,687 bytes, 6 sources
kernel consumes       --ink --paper --muted --accent --radius
custom properties defined by the skin        119
  (a) paints today                             4  (3%)   --ink --paper --muted --accent
  (b) 1:1 synonym, an adapter bridges         10 (→11%)  --yarn-orange --background --primary …
  (c) needs a wider contract slot             89         the type SCALE, the --ink-NN ramp,
                                                          --radius-* family, --space-*, --surface-*,
                                                          semantic --fresh/--danger/--warn
  (d) never consumable (component/util)       16         --shadow-* --ease-* --tracking-* --leading-*
```

Two facts the probe made concrete, both verified against code:

- **The skin defines a `--radius` *family* (`--radius-sm|md|lg|xl|pill`) and no bare `--radius`.**
  So the kernel's single `--radius` slot is fed *nothing* — every kernel button falls back to its
  hard-coded `6px`, while the `9999px` pill that defines every YARNNN button sits unconsumed.
- **The kernel hard-codes ~15 distinct font-size literals** (`0.85rem` … `4rem`) — none themable.

The decisive read: a 1:1 adapter bridges only **11%**, and that 11% is color-at-full-strength —
it does **not** include the geometry (hairline borders, pill radii, type rhythm) that makes an
artifact *look* like YARNNN. That differentiating brand is **75% of the tokens, and it lives in
(c)** — the bucket the five-var contract has no slots for. This is why §5 grows the contract
rather than shipping an adapter alone.

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

## 5. THE APPLY MODEL — how a skin reaches the pixels (decided, not yet built)

Everything above gets a design system *into* the workspace and *cited by* an artifact.
**Whether it visibly changes anything** was the open question. The coverage probe (§3) answered
it by measurement: the five-var contract paints 3% of the brand and misses the geometry.
**The decision below follows from that histogram, not from prediction.**

### The decision, in one line

**Widen the kernel token contract from five point-vars to a small *families* vocabulary, and add
a declarative `maps:` synonym bridge in the manifest.** The kernel still names *categories, never
instances* (ADR-222) — it gains slots for a type scale, a radius scale, and an ink ramp, but it
never learns a vendor's private names. The `maps:` block is where a vendor's private name
(`--yarn-orange`) is declared to *be* a kernel category (`--accent`).

### Move 1 — the widened contract (the (c)-bucket fix)

The kernel chrome CSS references its theme vars with hard-coded fallbacks (`var(--radius, 6px)`,
15 literal font-sizes). Widening = **giving those literals a themable slot**, chosen so the
*geometry* the eye reads (hairlines, pill buttons, type rhythm) themes — not so that all 119
tokens do. The vocabulary the kernel consumes grows to roughly:

| Category | Slots the kernel consumes | What it themes today (hard-coded) |
|---|---|---|
| Ink + ramp | `--ink`, `--ink-06`, `--ink-10` (a **ramp convention**, not every step) | hairline borders — the brand's *entire* structural signature |
| Surfaces | `--paper`, `--muted`, `--accent` | already the five; unchanged |
| Radius | `--radius-sm \| md \| lg \| pill` (a **scale**, replacing the lone `--radius`) | every button/card corner — the `9999px` pill |
| Type | `--text-sm \| base \| lg \| xl \| 2xl \| 3xl` (a **scale**) | the 15 hard-coded `font-size` literals |
| Semantic | `--fresh`, `--danger`, `--warn` | status color (fresh green / danger red) |

Slot count goes from 5 → ~14, still a *category* contract: the kernel names a radius *scale*, it
does not name `--radius-pill: 9999px` (that is the skin's instance of the category). A skin that
ships none of these still renders — every slot keeps its fallback (the skin-agnostic default is
preserved; a plain artifact is byte-identical). **This is the load-bearing move**: it is what
takes a correct apply from "4 colors change" to "the deck reads as YARNNN."

The `--ink-NN` ramp is named as a **convention, not an enumeration** — the kernel consumes a
small fixed set (`06`, `10` — the two that draw hairlines), not the skin's full `02…90`. Naming
the whole ramp would drift toward consuming an instance; naming the two the chrome reads keeps it
a category. (The (d) bucket — `--shadow-*`, `--ease-*`, `--tracking-*` — stays dead, correctly:
component/util scaffolding has no artifact chrome to paint.)

### Move 2 — the `maps:` synonym bridge (the (b)-bucket fix)

Even a wider contract cannot guess that `--yarn-orange` means `--accent`. The 11% of tokens that
are 1:1 synonyms get an **explicit, declarative bridge in the manifest** — versioned,
operator-legible, no CSS rewrite:

```yaml
name: YARNNN Design System
css:
  - styles.css
maps:              # a vendor's private name → a kernel category
  accent: --yarn-orange
  paper:  --background
  ink:    --foreground
```

- **The importer seeds it** by matching defined names against the kernel categories (the same
  synonym heuristic the coverage probe uses), and **a human confirms** — the seed is evidence,
  never a silent auto-map. An unmapped synonym is a warning in the import receipt, not a failure.
- **`resolve` emits the bridge** as a `:root { --accent: var(--yarn-orange); … }` block **prepended**
  to the composed skin, so it sits *before* the skin's own declarations and *after* nothing —
  the vendor's value flows into the kernel category, and the skin's later rules still win where
  they set the kernel name directly. No `!important`, cascade order only, consistent with the
  marked-element contract.
- **Why the manifest, not an import-time byte rewrite or a lane turn**: a `maps:` block is a fact
  the operator can read and correct; a byte rewrite is invisible after import; a lane turn is
  non-deterministic and costs a metered turn per apply. The declarative field is the
  mirror-once, legible-owner choice (DP29).

### Move 3 — the mechanical var-editor + its permission decision (§Q4)

Editing a theme value from the Design tab (STUDIO.md §Theme, named-deferred) writes to a
design-system folder, which the `PATCH /workspace/file` editable-prefix surface does not currently
admit. **The apply model forces the decision: design-system folders become an editable prefix**
for the mechanical var-editor — the same two-write-path shape the Studio already uses (edit the
projection, write the source). This is a *permission* widening, not a new write path; it rides the
existing mechanical door. Scoped here, built with the var-editor, not before.

### The two questions this does NOT reopen

- **Does the skin restyle blocks, or only chrome?** (former Q2) — **Only through the token
  vocabulary.** The block/arrangement CSS lives in the versioned `data-kernel` element and reads
  the same themable slots; a skin reaches a block's *look* exactly as far as the block's CSS reads
  a contract var, never by the skin selecting block elements directly. The marked skin sets
  *values*; the kernel owns *which selectors read them*. This keeps the retrofit story intact (a
  block kind lights up in old artifacts because the kernel element is versioned, ADR-456 W1) — a
  design system cannot fork it.
- **Supply vs select** (§4) — unchanged. Widening the type-*scale* contract does not merge with
  the ADR-455 `font` token: the scale sizes text; the token selects a face. A skin supplies faces
  and sizes; the per-artifact `font` token still selects among them.

### What is safe to build on, and what to build next

- **Safe** (housing + import, settled): the `_design.yaml` convention, the marked cited element,
  the cascade order, the flatten, the binary lane, the import door. Unchanged by this decision.
- **The build order** the decision implies (each its own ADR/commit, breach-tested gate,
  named gap): **(1)** widen `STUDIO_KERNEL_CSS` + the layout skins to the ~14-slot vocabulary,
  fallbacks preserved (prove byte-identical on a skin-less artifact); **(2)** the `maps:` field —
  parse in `parse_design_manifest`, seed in `plan_import`, emit in `resolve_design_system`;
  **(3)** the var-editor + the editable-prefix widening. Re-run the coverage probe after (1)+(2)
  as the acceptance receipt — the (a) bucket should absorb most of (b) and the geometry rows of
  (c).

**The ground truth to build against is §3's coverage histogram.** The acceptance test is not
"does it apply" (it always did) but "does the (a) bucket now hold the pill, the hairline, and the
type scale" — measured, the same way the gap was.

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
| The apply-gap coverage probe (§5 evidence) | `api/probe_design_system_coverage.py` |
| Gates | `api/test_adr449_design_system.py` · `api/test_adr462_context_menu.py` (D13) |
