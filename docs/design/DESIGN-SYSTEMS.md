# Design systems in the Studio — the housing, the import, the apply model, and the surface

**Status**: the housing + import + apply are live (ADR-449 + ADR-462 D11/D13/D14 + §5, 2026-07-16).
**The apply model is DECIDED AND BUILT (§5)** — a coverage probe turned the "why does a correct
apply barely change anything" question into a measurement, and the measurement drew and then
landed the fix: the kernel token contract widened from five point-vars to a ~14-slot *families*
vocabulary (Move 1), a declarative `maps:` synonym bridge (Move 2), and the `PATCH` editability
the mechanical var-editor needs (Move 3). Acceptance: the coverage probe's "paints today" bucket
went **4 → 17**, now holding the pill, the hairline, and the type scale.
**The FE surface is DECIDED, not yet built (§6, 2026-07-18)** — design systems become first-order
on the Studio landing; a third render state (`studio.system=`) holds the manage panel; the three
operations split by shape (import = modal, derive = learn-from, manage = panel). Read §5 for what
shipped, §6 for what's next; §3 has the receipts.

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

## 5. THE APPLY MODEL — how a skin reaches the pixels (decided and built)

Everything above gets a design system *into* the workspace and *cited by* an artifact.
**Whether it visibly changes anything** was the open question. The coverage probe (§3) answered
it by measurement: the five-var contract paints 3% of the brand and misses the geometry.
**The model below follows from that histogram, not from prediction — and it is now built.**

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

### Move 3 — the var-editor's permission decision (§Q4 — the permission SHIPPED)

Editing a theme value from the Design tab writes to a design-system folder, which the
`PATCH /workspace/file` editable-prefix surface did not admit. **The apply model forced the
decision, and it is made: a design-system token file is editable via `PATCH`.** The identity is
the *manifest convention*, not a fixed prefix — a design system lives at an operator-chosen path,
so the check (`_is_design_system_editable`, `routes/workspace.py`) allows a `.css` or
`_design.yaml` leaf **iff its folder holds a `_design.yaml`** (the same discovery contract
`find_design_systems` uses). It is *additive* to the fixed `editable_prefixes` safety list, gated
on the folder manifest, and scoped to text tokens — the binary lane (fonts/images) is never
editable this way. This is a permission widening, not a new write path; it rides the existing
mechanical door.

**What this does NOT include** (the honest gap): the var-editor *UI* is unblocked but not built.
The theme panel (STUDIO.md §Theme) shows the applied skin's variables read-only, now with the
kernel-consumed vocabulary surfaced first. Making a value *editable inline* needs a design pass
for one unresolved question the flatten creates: **which of the N flattened source files does a
value write back to?** A skin is composed from 6 sources (`fonts → colors → typography → …`); an
edit to `--accent` must land in the file that *defines* it, and the projection reads the flattened
result. That mapping (var → owning source) is the var-editor's real design problem, deferred to
its own pass rather than guessed here.

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

### What shipped, and what remains

- **Safe** (housing + import, settled): the `_design.yaml` convention, the marked cited element,
  the cascade order, the flatten, the binary lane, the import door. Unchanged.
- **Shipped (2026-07-16)**: **(1)** `STUDIO_KERNEL_CSS` v9 + the layout skins widened to the
  ~14-slot vocabulary, every literal now `var(--slot, LITERAL)` — byte-identical on a skin-less
  artifact (gate + probe verified); **(2)** the `maps:` field — parsed in `parse_design_manifest`,
  seeded conservatively in the import, emitted as a prepended `:root` bridge in
  `resolve_design_system`; **(3)** the `PATCH` editability decision (`_is_design_system_editable`).
  The derive recipe (`derive_recipes.py`) now names the full vocabulary so Freddie authors systems
  that hit the new slots.
- **The acceptance receipt** (the same measurement that found the gap): the coverage probe's (a)
  "paints today" bucket went **4 → 17**, and it holds `--ink-10` (hairline), `--radius-pill`
  (pill), and the full `--text-xs…5xl` scale — the geometry that makes an artifact read as its
  brand. A finding the build surfaced: the real YARNNN export *already* names `--accent`/`--paper`/
  `--radius-*` directly, so `seed_maps` returns empty for it — **Move 1 is its whole fix**; the
  bridge is for the export that names its accent `--brand` without also defining `--accent`.
- **Remaining** (named, deferred): the var-editor *UI* (unblocked, needs the var→owning-source
  design pass, above); semantic `--fresh/--danger/--warn` are in the contract but wire no kernel
  selector yet (no chrome reads status color — inventing one would be behavior, not a widen); and
  **no browser render of a themed deck yet** — the probe proves the *contract*, not the pixels.

**The ground truth remains §3's coverage histogram.** The acceptance test was never "does it
apply" (it always did) but "does the (a) bucket hold the pill, the hairline, and the type scale" —
and it now does, measured the same way the gap was.

---

## 6. THE SURFACE — where design-system UI lives (decided 2026-07-18, not yet built)

The apply model (§5) got the skin *into* the workspace and *onto* the pixels. This section is the
front-end question that follows: **where does a member see, create, and manage a design system?**
Decided as a shape here; built against this doc, not ahead of it.

### The problem the audit found

Today all design-system UI is trapped **inside an open artifact** — the right column's Design
tab (document scope) holds the picker (apply/remove), the import button, and the read-only theme
panel. But a design system is a **workspace-level identity worn by many artifacts** (§4), not an
artifact-scoped setting. So the Studio landing (`StudioStart`) shows recents and templates and
**zero design-system UI** — to import or even *see* the workspace's systems, a member must first
open some artifact, find the Design tab, and scroll. The identity that should greet them is three
clicks deep inside one deck. This is a mirror/composition mismatch in DP29 terms: a workspace
concern surfaced only as an artifact affordance.

### The decision: first-order on the landing, split by job

A design system is a **first-order Studio object**, co-equal with artifacts, surfaced on the
landing. But two distinct *jobs* pull toward two placements, and forcing them into one is the
mistake the Claude Design reference avoids (it has both a `Design systems` tab AND a composer
selector):

- **Job A — "wear our style"** (frequent, per-artifact, authoring-time). **Stays where it is**:
  the open-artifact Design tab's picker. The artifact *applies* the identity. Optionally surfaced
  earlier (at create-time, like a composer selector) so a new artifact is born wearing it.
- **Job B — "manage our identity"** (rare, workspace-level). **Gets the new landing home.** This
  is the surface that has no home today.

### The landing section ("Design systems", first-order, below recents)

- **Empty** → one card, two create paths (below).
- **Populated** → one card per system (name · an `--accent` swatch · "worn by N artifacts"),
  plus a quiet **"+ Import / Derive"** affordance. Clicking a card opens the **manage panel**.

### The three operations, and their distinct shapes

The operations are NOT one shape — the honest cut (measured against the learn-from flow, which is
a *source→target→lane creation modal*):

| Operation | Shape | Why this shape |
|---|---|---|
| **Create — import a `.zip`** | a **modal** (upload + receipt) | Bounded, one-shot, deterministic (flatten/classify/write → "15 files · 5 stylesheets · 61 skipped"). The existing Design-tab import, **promoted to the landing**. Not learn-from — there is no source to choose and no lane to run. |
| **Create — derive from a source** | **learn-from itself** (already wired) | It *is* source→target→lane: a brand guide → "Design system" → the ADR-450 `design-system` derive recipe on a chat lane. `LEARN_TARGETS` **already carries** `{recipe: 'design-system', template: null}` — the derive path exists; the landing just needs to route to it. |
| **Manage — the overview** | a **dedicated Studio panel** (not a modal, not a canvas) | Reading a thing that *exists* — dependents, files, re-import, the theme panel, and the future token-editor. Revisit-able and roomy; a modal is a poor home for it and cannot hold the inline var-editor. |

**The empty→populated toggle resolves the "manage or create" question**: empty section = the two
create paths; a populated card = a click into the manage panel. Create is a modal-or-learn-from;
manage is a view.

### The manage panel — a THIRD Studio state (the honest surface cost)

The Studio has two render states today, keyed on the `studio.file` param: **absent → the landing**
(`StudioStart`), **set → the artifact workbench** (canvas + Chat/Design tabs). The manage panel is
a deliberate **third state** — not the landing, not an artifact workbench — keyed on a **new
sibling param** (proposed `studio.system=<manifest-path>`, mirroring `studio.file=`). It needs its
own render branch in `StudioSurface` and its own crumb (`Studio › ‹System Name›`).

This **grows Studio's surface by one state** — the cost "mirror once, compose few" usually
resists. It is accepted here deliberately: a first-order object earns a composed act-surface, and
the panel is the only clean home for the deferred token-editor (a modal is not). Recorded as a
choice, not an accident.

**What the panel shows** (all data already exists):

- **Worn by N artifacts** — the ADR-448 reference edge (`GET /api/workspace/file/dependents` on
  the manifest), each openable. This is the payoff the whole citation contract was built for.
- **The files** — manifest + stylesheets + fonts/images (the import receipt, persisted).
- **The theme panel** — the §5 widened vocabulary, kernel-consumed slots first, read-only for now
  (the same `skinVars` parse the Design tab already does, relocated/shared).
- **Re-import** — the same import modal, re-run against the folder (ADR-292 reapply shape).
- **The token-editor slot** — the deferred var-editor lands here (the §5 Q4 `PATCH` permission is
  already shipped; the UI needs the var→owning-source design pass named in §5 Move 3).

### What is decided vs still open

- **Decided**: first-order landing section; Job A stays in the Design tab; the three operation
  shapes (import=modal, derive=learn-from, manage=panel); the manage panel as a third Studio state
  on a new param.
- **Still open (do not build ahead of it)**: the token-editor UI (its var→source mapping); whether
  the create-time "wear this" selector (Job A at creation) ships with this or later; the exact
  card visual. These are named so the build stops at the decided line.

### The build order the decision implies (each its own commit + gate)

1. **The landing section** — list systems (`find_design_systems` via a `GET`), the empty/populated
   states, the "+ Import / Derive" affordance. Reuses the existing import endpoint + learn-from.
2. **The manage panel** — the third render state on `studio.system=`, composing dependents + files
   + the shared theme panel + re-import. No new backend (all endpoints exist).
3. **(Deferred)** the inline token-editor, against the shipped `PATCH` permission.

---

## 7. File map

| Concern | Location |
|---|---|
| Contract (parse/discover/resolve/compose/apply) | `api/services/design_systems.py` |
| Flatten + url-rewrite | `api/services/design_systems.py::flatten_css` / `rewrite_urls` |
| Import (classify/plan/write/binary lane) | `api/services/design_system_import.py` |
| Import door (zip → folder) | `api/routes/studio.py::import_design_system_route` |
| The bound-lane posture section | `api/services/lane_runner.py` (the `artifact_path` branch) |
| The derive recipe (AI authors one) | `api/services/derive_recipes.py::DERIVE_RECIPES["design-system"]` |
| FE picker + import UI (Job A — apply, in an open artifact) | `web/components/studio/StudioDesignTab.tsx` (document scope) |
| FE landing + render states (Job B home — §6, to build) | `web/components/studio/StudioSurface.tsx` (`StudioStart` = landing; `studio.file` = workbench; `studio.system` = the new manage state) |
| FE learn-from (the derive-create path) | `web/components/studio/LearnFromFlowModal.tsx` + `LEARN_TARGETS` in `StudioSurface.tsx` (already carries `design-system`) |
| FE skin url() resolution | `web/components/workspace/viewers/projection.ts::resolveStyleUrls` |
| The theme contract (the apply seam) | `docs/design/STUDIO.md` §Theme + the layer table |
| The apply-gap coverage probe (§5 evidence) | `api/probe_design_system_coverage.py` |
| Gates | `api/test_adr449_design_system.py` · `api/test_adr462_context_menu.py` (D13) |
