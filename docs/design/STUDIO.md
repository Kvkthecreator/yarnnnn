# STUDIO — the interaction contract

> **Full rewrite, 2026-08-04** (the rewrite ADR-511 D6 owed, landed with ADR-516). The
> pre-rewrite doc was the accreted history of ADR-440→509 — correct decisions narrated in
> the order they were made, which meant every new affordance was designed against partial
> memory of the whole. This doc inverts that: the **grain × medium matrix** is the
> contract, every cell is *shipped*, *declared*, or *refused* — no blank cells — and the
> history lives in the ADRs (ADR-LEDGER routes). Where an old section is gone, its ruling
> survives as a matrix cell or a normative rule; nothing was un-decided by this rewrite.

Studio is yarnnn's authoring app (ADR-440) governed by the axiomatic model (ADR-443):
**HTML-native** (the artifact IS the file — no shadow/JSON model, R1), **AI-native** (the
lane co-authors in its pretraining tongue), one kernel vocabulary that teaches and never
validates (R4). Since ADR-511 the substrate is **conventional HTML/CSS plus exactly three
annotations** — identity (`data-block-id`, on blocks AND structural containers),
provenance (`data-ref`), grammar (`data-block="<kind>"`, vocabulary blocks only). Every
other `data-*` the file may carry is an **inert name** (ADR-511 D8): skins style it,
labels read it, nothing gates on it, nothing writes it.

## The objects

Four, all real DOM elements; there is no parallel tree.

| Object | DOM anchor | Selection scope | Carries |
|---|---|---|---|
| **Artifact root** | `<html>` | `document` (nothing selected) | `data-template` (document/deck/web — ADR-505's three, one per medium), document-grain tokens (`font`/`measure`/`pagenum`), the marked `<style data-kernel>`/`<style data-skin>` elements |
| **Page** | `STRUCTURAL_PAGE_SEL` — a deck slide (`section.slide`) or a top-level body/main/article section. Position-addressed, never attribute-gated | `page` | inline layout style (ADR-516), meaning tokens (`tone`, `ratio`, `scrim`, `bg-pos`), the background citation |
| **Structural container** | `div[data-block-id]:not([data-block])` — a column, a columns row, a named region. Identity without vocabulary (ADR-511 D3), stamped by `normalizeStructure` at load + write | `container` | inline layout style; a *name* (a `data-slot` inert name, or class `cols`/`col`) feeding the label map; a media *role* via the registry |
| **Block** | `[data-block]` + `data-block-id` | `block` | block tokens (`size`/`align`/`tone`/`variant`, media tokens), measures (`data-w/h/x/y` — deck-staged), `data-ref` citations |

**The group is a transient selection, never markup** — shift/⌘-click on staged frames;
the set moves as one revision (`setGeometryMany`); ungroup is deselection. A persisted
group wrapper would be a second structural layer competing with the real tree (ADR-462
D3's refusal, clarified by ADR-511: what it refuses is the *synthetic editor-side
object*; selecting a real container was never the refused thing). Persistent grouping,
if ever wanted, is wrap-in-a-real-`<div>` — a revision.

**The selection floor is the attribution floor** (ADR-511 D3, normative): text nodes,
`<br>`, inline spans are never selection subjects — selection bottoms out at what can
carry identity. No DOM-inspector depth.

**Operator words, everywhere** (ADR-443 D3, normative): the file says
`<section>`/`<div>`/`<h2>`; the chrome says *slide / columns / column / heading* — one
label map, `structureLabels.ts`, consumed by the canvas runtimes, the navigator, the
Design tab and the menus. The chrome never says "div".

## THE INTERACTION CONTRACT — grain × medium

The three media (one per type, ADR-505): **deck** (`paged`, 16:9 staged frame — the only
coordinate space), **document** (`flow`, one continuous writing surface), **web**
(`paged`, full-width bands, viewport — band-first, never object-first). `mode` answers
*does this type have page units*; the FRAME answers *is there a coordinate space*
(`block-staged` = `.slide` ancestry) — two axes, deliberately not one (ADR-505 D3).

Legend: ✅ shipped · 🔜 declared (built when its phase lands, never by accident) ·
🚫 refused (a decision, not a gap).

### Click / hit-test (one ladder — innermost addressable wins, ADR-511 D3)

| | deck | document | web |
|---|---|---|---|
| text | ✅ second click on selected block enters caret (P10 object grammar: FIRST click selects — box + handles; dblclick enters directly) | ✅ click = caret, natively (the root is `contenteditable`; blocks are annotations, not walls — ADR-480) | ✅ as deck, minus geometry |
| block | ✅ first click selects (box, handles, move band) | ✅ click places caret; objects (figure/table/…) select as units | ✅ selects (box, static — no coordinate space) |
| container | ✅ click on its own surface (padding/gap, not a child) selects; static box (ADR-516 D5) | — (flow has no containers by derivation, ADR-481 D1) | ✅ as deck |
| page | ✅ click on the page margin selects the slide | — (no page unit) | ✅ selects the band |
| empty space | ✅ clears selection | ✅ caret follows | ✅ clears |

### Hover cue (the cue lights what the click would select — the 2026-07-21 rule)

| | deck | document | web |
|---|---|---|---|
| block | ✅ dashed outline, innermost only | ✅ NONE on prose (the I-beam/caret is the cue — ADR-481 D3); objects keep a quiet cue | ✅ as deck |
| container | ✅ outline + green operator-word label | — | ✅ |
| empty leaf container | ✅ "+ Add" placeholder, dashed bounds always (the PowerPoint placeholder grammar; imported HTML included — ADR-511 Ph2) | — | ✅ |

### Selection chrome

| | deck | document | web |
|---|---|---|---|
| block | ✅ accented box + 8 handles + border-band move; persists through editing (dashed = text mode, P11); `positioned` corner tag when out of flow (ADR-511 D4) | ✅ neutral outline on OBJECT kinds only; prose selection is the caret/range | ✅ box, static variant (no move — no stage) |
| container | ✅ static box — border only, NO handles, NO move band (ADR-516 D5: the chrome must not promise gestures the grain lacks) | — | ✅ same |
| page | ✅ Design-tab scope + strip highlight | — | ✅ |
| group | ✅ same neutral rule on every member | 🚫 (browser range-selection owns flow) | ✅ |

### Drag

| | deck | document | web |
|---|---|---|---|
| block | ✅ drag → positioned (`data-x/y`, absolute — the stage's grammar); frame-clamped; snap to column dividers | 🚫 positional drag (no frame); reorder = cut/paste in continuous prose (the medium's own reorder) | 🚫 positional (viewport ≠ frame, ADR-461 D4 — the per-breakpoint refusal); 🔜 reorder-drag between bands |
| container | 🔜 **Phase 3: drag = REORDER within flow, per medium** (extends ADR-509 "the gesture follows the medium" — never positional on any medium) | — | 🔜 same |
| resize | ✅ blocks: 8 handles, `w/h` measures (deck; media anywhere — an image's intrinsic ratio is its own frame); group resize scales the bounding box (Figma) | media only | media only |
| snap guides | 🔜 Phase 3 (siblings + frame during drag) | — | 🔜 |

### Keyboard

| | deck | document | web |
|---|---|---|---|
| verbs | ✅ ⌫ delete · ⌘C/⌘V/⌘D · Esc lifts caret→block | ✅ same, caret-guarded (the caret owns text keys — ADR-482 D2) | ✅ |
| Esc-walk | ✅ editing → block → container → … → page → clear (the real ancestor chain, ADR-511 D3; no drill-down gesture — down is clicking the thing) | ✅ caret → block → clear | ✅ |
| undo | ✅ ⌘Z/⇧⌘Z — snapshot stack in the pointer runtime (both modes) | ✅ | ✅ |
| owed | arrows nudge/resize, ⌘]/[ z-order, Tab cycle (declared since ADR-477) | ⌘B/⌘I, Tab list indent | band reorder keys |

### Insert (the route follows the medium — ADR-509)

| | deck | document | web |
|---|---|---|---|
| routes | ✅ toolbar **Insert** (discovery) + right-click row (located) — one menu, two mounts; target resolved and NAMED ("Insert into slide 3"): selected block → after it; selected CONTAINER → into it; else the page's first leaf container (`firstLeafContainer` — position, not name) | ✅ `/` at the caret (the linear-flow gesture) + right-click; toolbar Insert | ✅ as deck |
| page grain | ✅ **New slide** + **Re-arrange** (the gallery's one mount, toolbar) | — (no page unit) | ✅ New band |
| refused | 🚫 slash as sole route on paged · 🚫 the hover gutter (deleted every mode, ADR-505 D4) · 🚫 per-medium menu subsetting (both doors offer every kind — what differs is which door, never what's in it) | | |

### The pane (Design tab) — scope follows selection

| scope | rows | mechanism |
|---|---|---|
| document | typography faces, measure/pagenum, design system (worn, not listed — ADR-487 D9), File/Share/Export tail (every scope) | tokens (meaning) |
| page | verbs (dup/up/down/delete) · **LAYOUT: padding + vertical-align presets** (slide) / spacing (band) · tone · columns ratio · background + scrim/focus | **inline-CSS presets, one op** (ADR-516 D1/D3) · tokens for meaning |
| container | media picker (media-role regions) · **LAYOUT: padding/gap/align/justify/width Hug\|Fill** | inline-CSS presets, same op (ADR-511 D4 + ADR-516 D4) |
| block | typography ramp · tone/variant swatches · turn-into · width/align tokens · size readback · **Position: In flow \| Positioned** (deck) | tokens + measures |

**The layout boundary (ADR-516 D6, normative): geometry converges on inline CSS; meaning
stays tokens.** A layout value means itself (`padding: 3.5rem 4rem`); a meaning value is
themed indirection (`data-tone="accent"` resolves through the skin's custom properties).
`ratio` is the named holdout — a stop over a sibling *pair*, the divider gesture's
grammar. Legacy `data-valign`/`data-pad` are inert names: kernel CSS honors them on
untouched artifacts; a layout write strips them from the element it touches. **No raw
CSS pane, ever** — the property surface is a bounded allowlist at every grain (D7).

## The one write path

Every mechanical op is a compute over the artifact's source, landing through
`POST /studio/artifacts/write` as ONE attributed CAS-guarded revision (`authored_by=
"operator"`); the lane's judgment edits land through the same door. `normalizeStructure`
runs at the serialize seam, every mode, every depth: bare text elements are promoted into
the grammar (tag-derived kinds), structural containers are stamped with identity, ids are
preserved/deduped first-wins, citation islands untouched. **Unannotated HTML — imports,
agent output, legacy — is editable by definition**; an artifact opened un-normalized
converges on its first write (migration-by-use, never a fleet sweep — ADR-209).

The feel contract: **pixels never wait for the network** (optimistic override, ADR-466
P8) · a member's own write never reloads the canvas · a 409 is courteous (refetch,
recompute on top, retry once — ADR-466 D7) · every op is byte-identical-no-op safe.
Direct editing maps to the SOURCE, never the projection; the revision is the atom — no
keystroke CRDT (ADR-406). Editing grain per medium (ADR-480): on `paged` the block is an
ENCLOSURE (runtime owns the caret); on `flow` the block is an ANNOTATION
(`contenteditable` on the root; the browser owns selection/undo/⌘F; ids reconstructed at
the write seam, not enforced).

## Vocabulary, templates, skins (the kernel registries — `services/studio.py`)

- **Block vocabulary**: 13 kinds (prose · callout · quote · checklist · divider · toggle
  · button | table · metrics · chart | figure · gallery), served on
  `GET /studio/vocabulary`. Grammar, not schema — unannotated content stays valid.
- **Arrangements are STARTER TEMPLATES** (ADR-511 D2): applying one is an authored
  transformation whose result is live, editable structure — selectable containers whose
  layout is CSS — never a frozen master. Role-aware content carry (media seeks media,
  same-name preserves position intent, headings anchor and are NOT carried); a slotless
  target moves content to a new page rather than dead-ending (ADR-466 D5).
- **Skins / design systems** (ADR-449/487): the ~14-slot custom-property families
  contract; worn inside an artifact, listed inside the manage state (`studio.system=`);
  the kernel `<style data-kernel>` (versioned, write-door retrofit) names categories,
  never instances.
- **Measures** (ADR-461): value-carrying geometry (`data-w/h` + `--yw/--yh` anywhere
  media; `data-x/y` deck-staged only) — the bounded exception for continuous values;
  two-clamp rule (preview + write) from the served spec.
- **The name is ONE fact** (ADR-459/469/483): `<title>` first, titleized meaning-folder
  as fallback; rename is the crumb, renames the folder (per-file attributed moves),
  IME-composition-guarded; only a flow h1 is a title and only an untouched placeholder
  is ever replaced.

## Normative rules (settled — do not re-litigate without an ADR)

1. **The DOM is the model** (ADR-443 R1) — no shadow layer; the interaction contract is
   the DOM tree, not a registry (ADR-511 superseding ADR-453 D5).
2. **Selection floor = attribution floor** — blocks and identity-carrying containers,
   never inline nodes.
3. **No shadow group object** — transient selection or a real wrapper div.
4. **Operator words** — the label map is the one vocabulary seam; "div" is a word the
   trace never uses.
5. **Geometry = CSS, meaning = tokens** (ADR-516 D6) — a new layout need is a new
   allowlist value, not a new token row; a new meaning needs the themed indirection.
6. **The chrome promises only what the grain has** — hover, selection and cursor cues
   must agree with the ladder and with the available gestures ("honest about
   inertness").
7. **One write door, one op per intent** — a new affordance is an existing op reached
   through a new grain before it is ever a new op (ADR-462 D1).
8. **The gesture follows the medium** (ADR-509, extended by the drag row above) — drag
   means position on a stage, reorder in a flow, and nothing positional on a viewport.
9. **Inert names are tolerated, never load-bearing** (ADR-511 D8) — singular LOGIC,
   tolerant DATA; attribute stripping happens per-element at an authored write only.

## Standing refusals

No raw CSS pane · no DOM-inspector depth · no preview-then-describe edit loop (revisions,
not NL round-trips) · no fourth type / no positioned web (ADR-505) · no pagination
(ADR-480 D6) · no keystroke CRDT · no per-breakpoint editing · no web-font CDNs · no
forms · no JS carousels · no databases/linked views · no synced blocks (that is `data-ref`
at block grain, later) · no second source format (markdown is a projection — ADR-456 D1)
· no editing viewer-owned formats · no owned render engine (ADR-417). The standing drift
test (ADR-440 §7): *does this force a definitional question about the app format, or is
it just a better editor?*

## Phase 3 (declared, in order) + named follow-ons

1. **Container drag = reorder, per medium** (the matrix's 🔜 cells) — with drop
   indicators; never positional.
2. **Snap/alignment guides** on block drag (siblings + frame).
3. **Breadcrumb at the selection** (the ancestor chain the Esc-walk already walks) —
   the one industry-standard affordance not yet declared elsewhere.
4. Owed keyboard rows (arrows/nudge/Tab-cycle · ⌘B/⌘I on flow · band reorder keys).
5. Carried follow-ons: h1-rename-in-place (needs dependent-rewriting on the ADR-448
   edge) · rename does not rewrite dependents (every mover's gap, not Studio's) ·
   `text/html` paste (a security carve — allow-list sanitizer first) · measures deriving
   their posture line · `applies` → `(scope, grain)`.
