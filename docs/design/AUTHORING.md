# AUTHORING — the interaction contract

> **Renamed from `STUDIO.md`, 2026-08-06.** The file was named for one of its two
> consumers while being the authoritative contract for both — and after ADR-525 (the
> selection's tier) and ADR-526 (the document's heading tree) that name had become a lie
> a Docs reader had to see through. **Docs and Studio are peers here**; neither hosts the
> other, and IMAGES is a third consumer of the same machinery.
>
> **What was NOT done, and why.** The doc was not split in two. The measurement:
> Docs-specific content is ~16% of the file, and **~44% of the `document` column is `—` /
> `🚫` cells that carry no meaning once the `deck` column is removed** — a cell reading
> "flow has no containers by derivation" is a statement *about the contrast*. Eight of
> twelve normative rules and thirteen of eighteen refusals are global; the two sections a
> split would have to duplicate (§The one write path, §Vocabulary/templates/skins) are
> exactly the shape the refusal list forbids ("no forked machinery per app"). And **rule
> 11 is a recorded incident of what happens when one contract is derived in two places**:
> the pane offered Move up/down on a Docs paragraph while the menu refused it on the same
> block. The adjacency in this file is load-bearing — it is what made ADR-525 and ADR-526
> findable. If a split is ever revisited, the defensible cut is *shared contract + thin
> per-medium appendices*, never two parallel docs.

> **Full rewrite, 2026-08-04** (the rewrite ADR-511 D6 owed, landed with ADR-516). The
> pre-rewrite doc was the accreted history of ADR-440→509 — correct decisions narrated in
> the order they were made, which meant every new affordance was designed against partial
> memory of the whole. This doc inverts that: the **grain × medium matrix** is the
> contract, every cell is *shipped*, *declared*, or *refused* — no blank cells — and the
> history lives in the ADRs (ADR-LEDGER routes). Where an old section is gone, its ruling
> survives as a matrix cell or a normative rule; nothing was un-decided by this rewrite.

> **Housing amendment, 2026-08-04 ([ADR-518](../adr/ADR-518-docs-and-studio-the-writing-app-and-the-layout-app.md))**:
> the authoring housing is TWO apps over this one contract — **Docs** (`/docs`) houses the
> flow medium (`document`, the matrix's document column); **Studio** (`/studio`) houses the
> paged media (`deck` · `web`); **Images** (`/images`) houses `image`. Everything in this
> doc — the matrix, the grammar, the one write door, the registries — is the SHARED
> machinery all three apps mount; a medium's column is also its app's interaction
> contract. Where this doc says "Studio" of shared machinery, read "the authoring apps".

This doc is the interaction contract of yarnnn's authoring apps (ADR-440 · ADR-518),
governed by the axiomatic model (ADR-443):
**HTML-native** (the artifact IS the file — no shadow/JSON model, R1), **AI-native** (the
lane co-authors in its pretraining tongue), one kernel vocabulary that teaches and never
validates (R4). Since ADR-511 the substrate is **conventional HTML/CSS plus exactly three
annotations** — identity (`data-block-id`, on blocks AND structural containers),
provenance (`data-ref`), grammar (`data-block="<kind>"`, vocabulary blocks only). Every
other `data-*` the file may carry is an **inert name** (ADR-511 D8): skins style it,
labels read it, nothing gates on it, nothing writes it.

> **`data-block-id` is a BROWSER-SIDE handle and has never crossed the write door**
> (ADR-528 §2, measured). `authored_substrate.py` reads it zero times; `write_revision`
> takes no block parameter; the ADR-448 citation lift is **path-grain** (`_DATA_REF_RX` →
> `normalize_workspace_ref`); no `workspace_file_versions` column is block-aware. The 72
> Python occurrences are seed markup and lane-posture prose. **Attribution, revisions,
> parent pointers and reference edges are whole-FILE facts.** What identity actually buys
> is *referability across a boundary* — the OS clipboard (`isInternalPaste`), the ADR-524
> patch channel's async round-trip, and `mergeBlock`'s frame/source edge. Those three are
> why stripping prose ids is refused; none of them is about provenance. Per-block
> attribution does not exist and is a separate bet (the "synced blocks" refusal below
> names where its mechanism would live).

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
object*; selecting a real container was never the refused thing). Persistent grouping
is **Group as a verb** (ADR-519 D2, declared — Phase B): wrap the multi-selection in a
real `<div data-block-id>` as one authored revision; Ungroup unwraps. The wrapper *is*
a structural container — Figma's Group ≡ a container with no layout declared; no group
node type exists. **A group is durable until the arrangement is re-declared: re-arranging
a slide DISSOLVES its groups** (ADR-519 D2.1, 2026-08-06) — `applyArrangement` ends in
`page.replaceWith(el)`, so the wrapper dies with the page that held it and can never be
orphaned. A slot is DECLARED by the arrangement, a group is AUTHORED ad hoc; the ad-hoc
structure yields. The surface must SAY so before the re-arrange — a group vanishing
silently is the defect that rule must not produce.

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
**A deck edits on the STAGE** (ADR-520 D1): the canvas shows ONE slide (the
PowerPoint/Figma norm; view state, never bytes — the zoom rule); the navigator filmstrip
is the sequence; ‹ › chrome + PgUp/PgDn page the stage. Web stays a scroll.

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
| container | ✅ **staged: box + 8 resize handles, NO move band** (ADR-520 D2 — w/h through the same two-clamp measures + numeric fields; move stays reorder-shaped) | — | ✅ static box — border only (ADR-516 D5; no frame off the stage) |
| page | ✅ Design-tab scope + strip highlight | — | ✅ |
| group | ✅ same neutral rule on every member | 🚫 (browser range-selection owns flow) | ✅ |

### Drag

| | deck | document | web |
|---|---|---|---|
| block | ✅ drag → positioned (`data-x/y`, absolute — the stage's grammar); frame-clamped; snap to column dividers | 🚫 positional drag (no frame) — reorder is **⌥↑/⌥↓** (ADR-526 D3, structure tier) or cut/paste; the D7 no-drag refusal is unchanged, because a chord asserts no box | 🚫 positional (viewport ≠ frame, ADR-461 D4 — the per-breakpoint refusal); 🔜 reorder-drag between bands |
| container | 🔜 **Phase 3: drag = REORDER within flow, per medium** (extends ADR-509 "the gesture follows the medium" — never positional on any medium) | — | 🔜 same |
| resize | ✅ blocks: 8 handles, `w/h` measures (deck; media anywhere — an image's intrinsic ratio is its own frame); group resize scales the bounding box (Figma) | media only | media only |
| snap guides | 🔜 Phase 3 (siblings + frame during drag) | — | 🔜 |

### Keyboard

| | deck | document | web |
|---|---|---|---|
| verbs | ✅ ⌫ delete · ⌘C/⌘V/⌘D · Esc lifts caret→block | ✅ **objects only** — figure/table/chart/gallery/divider keep the unit verb; on prose the keys belong to the platform (ADR-521 D6: a unit verb on a paragraph is the enclosure re-asserting itself, and it deleted whole paragraphs on an emptied block or a cross-block range). Text keys stay caret-guarded (ADR-482 D2) | ✅ |
| Esc-walk | ✅ editing → block → container → … → page → clear (the real ancestor chain, ADR-511 D3; no drill-down gesture — down is clicking the thing) | ✅ caret → block → clear | ✅ |
| undo | ✅ ⌘Z/⇧⌘Z — a lineage stack in the SURFACE (ADR-523 D1; the runtime only forwards the key, and yields it entirely to the browser while a flow caret is live per ADR-482 D2). An entry carries `structural`, so a non-structural undo does not reload the frame; text edits coalesce at the member's pauses (600ms, D3), so ⌘Z rewinds a phrase, not the whole blur-batched revision. Bounded by bytes (D2); cleared only by a FOREIGN write (D4) | ✅ | ✅ |
| list indent | — (deck Tab is block-cycle territory, owed) | ✅ Tab/⇧Tab in a list nests/unnests (ADR-521 D4); Tab in prose = a literal tab; Tab never ends the session | — |
| move block | 🔜 (arrows nudge — owed) | ✅ **⌥↑/⌥↓** → the existing `moveBlock`, one op N entrances (ADR-526 D3). Subject = the block holding the caret (structure tier), NOT `selectedBlock()` (the object gate). Yields to a live range | 🔜 band reorder keys |
| owed | arrows nudge/resize, ⌘]/[ z-order, Tab cycle (declared since ADR-477) | — | band reorder keys |

### Inline format (the text tier follows the selection — ADR-521)

| | deck | document | web |
|---|---|---|---|
| bar + ⌘B/⌘I | ✅ within the editing block (the enclosure grain caps the range) | ✅ follows the range, cross-block: per-block-intersection, deterministic toggle (any eligible part unformatted → apply everywhere), heading-aware (bold on a heading is a no-op, never an un-bold) | ✅ as deck |
| paste | ✅ `text/html` behind the allowlist — allowed tags only, every attribute stripped (`href` survives, `javascript:` rejected), media dropped (media enters as cited figures, never pasted bytes), plain-text fallback; commit-time `sanitizeInner` is the second gate (ADR-446 D2) | ✅ same | ✅ same |
| emphasis set | ✅ B · I · code · link (the bar) | ✅ **B · I · U · S · code · link · colour · highlight · clear** — the ADR-527 D1/D2 set, read off the Google Slides bar. U/S ride `applyToggle` unchanged (one row each, not a mechanism); clear keeps STRUCTURE (a heading stays a heading) | ✅ as deck |
| colour | 🚫 (block `tone` only) | ✅ **palette ROLES at range grain** — `data-mark` / `data-highlight` spans, one kernel rule per role, so a design-system swap re-themes the document. Never a picker (ADR-449) | 🚫 |
| home | the bar (at the caret) | **both**: the bar at the caret, the full set in the PANE's Text section (ADR-527 D4) — two entrances, one `applyFmt` | the bar |
| refused | 🚫 caret-state formatting pipeline (collapsed ⌘B stays browser-native) · 🚫 block-set selection mode on flow (the browser range IS the selection) | 🚫 point size · line spacing · per-block font family · a colour picker — **metrics belong to the design system** (ADR-527 §4); the ruler presumes a page (ADR-480 D6) | |

### Insert (the route follows the medium — ADR-509)

| | deck | document | web |
|---|---|---|---|
| routes | ✅ toolbar **Insert** (discovery) + right-click row (located) — one menu, two mounts; target resolved and NAMED ("Insert into slide 3"): selected block → after it; selected CONTAINER → into it; else the page's first leaf container (`firstLeafContainer` — position, not name) | ✅ `/` at the caret (the linear-flow gesture) + right-click; toolbar Insert | ✅ as deck |
| page grain | ✅ **New slide** + **Re-arrange** (the gallery's one mount, toolbar) | — (no page unit) | ✅ New band |
| refused | 🚫 slash as sole route on paged · 🚫 the hover gutter (deleted every mode, ADR-505 D4) · 🚫 per-medium menu subsetting (both doors offer every kind — what differs is which door, never what's in it) | | |

### The pane (Design tab) — one spine, scope follows selection (ADR-519 D3)

**The spine is fixed**: Identity → Position → Layout → Style → Content. A scope renders
only the sections its grain has — it never re-orders or renames a section. The member
learns the panel once.

**On flow the scope set is `document | range | object` (ADR-528 D2) — `block` is not a
scope a continuous document can produce.** On a stage `block` genuinely IS a selection
scope: a slide object is a thing with a box. On a continuous surface the selection is a
**range**, which may cover half a paragraph or six; there is no "the selected block." One
word doing two jobs across two media was the grammar collision ADR-519 D3 imported from
Figma, where selection *is* object selection.

Scope is **derived from the tier** the runtime declares (ADR-525 D1) at the one site that
computes it — the pane reads, never re-derives (rule 11). It previously committed scope
from `blockId && blockKind` and consulted the tier only afterwards, where it could just
subtract; the `block (text)` column below was therefore a column of *absences*, which is
the shape of a scope never meant to be entered.

**`range`** = a text selection on flow, collapsed (a caret) or spanning many blocks.
**`object`** = a figure/table/chart/gallery/divider anywhere, and every block on a paged
medium. `container`/`page` never applied to flow (ADR-481 D1 — no containers by
derivation, no page unit).

| section | document | page | container | range (flow text) | object | mechanism |
|---|---|---|---|---|---|---|
| **Identity** — label + **path + Contents** (ADR-520 D4: the structure's ONE home; the navigator is the filmstrip) + verb row | name + file verbs (every scope) · **OUTLINE on flow** (ADR-526 D2 — the document's headings in order, click-to-jump; derived client-side, empty state says so) | ✅ verbs · Contents | ✅ path · verbs · Contents | ✅ **enclosing-heading crumb** (ADR-526 D2 — flow's one honest ancestry rung, from `headingId`; withdraws over a multi-block range) · label names the **count** over a span, never a stale block · 🚫 no path, no verb row — **not composed** (ADR-528 D4: a range has no box and no single subject; the suppression guards are DELETED, not re-gated) | ✅ path · verbs — **move verbs withheld on flow** (a figure has a box but sits in continuous prose; the menu always refused them there) | existing id-addressed ops; path = the breadcrumb's climbChain |
| **Position** — In flow \| Positioned · X/Y **fields** (ADR-520 D3: numeric entry, two-clamp) | — | — | — | 🚫 not composed | ✅ deck-staged only | measures, two-clamp |
| **Layout** | — | ✅ padding + vertical-align glyphs (slide) / spacing (band) · columns ratio | ✅ padding/gap/**align+justify glyph rows**/width Hug\|Fill · **W/H fields (staged — ADR-520 D2)** (direction = Phase C) | 🚫 **not composed** — rule 10's "no layout surface", now true by non-composition rather than by suppression. (align + indent were ADR-527 D3's `block-flow` rows in the old `block (text)` column; they return as range-tier rows when a span-aware op exists — see the roster) | size Hug\|Fill · width/align tokens · **W/H fields** | **inline-CSS presets, one op** (ADR-516) · tokens |
| **Text** (ADR-527 D4 — range emphasis) | — | — | — | ✅ **B · I · U · S · code · clear · colour · highlight** — palette roles, never a picker. The **primary** section of this scope (ADR-528), and the one that does NOT withdraw over a span: every control acts on the selection | — | one `applyFmt`, two entrances (bar + pane) |
| **Style** | typography faces · measure/pagenum · design system (worn, not listed — ADR-487 D9) | tone · scrim/focus | — | ✅ typography ramp (**structure tier** — addresses the block the caret is in; withdraws over a multi-block range and says so) | ✅ typography ramp · tone/variant swatches | tokens (meaning — ADR-516 D6 boundary) |
| **Content** | — | background citation | media picker (media-role regions) | ✅ turn-into (**structure tier** — ADR-521 D2; same single-block withdrawal) | ✅ turn-into | existing |

> **The two structure-tier sections are one implementation, two entrances** (rule 7 /
> ADR-518 D2): `rampSection` and `turnIntoSection` are lifted out of the render so `range`
> and `object` mount the same values. Both address a single `selectedEl`, which is why
> range scope gates them on `!multiBlockRange` and **explains the withdrawal** rather than
> answering for one block of six — the `d878242` defect. Span-aware structure ops (N
> blocks, one revision) are owed, not shipped.

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

> Per-app layout tables register into these shared registries (ADR-472 D2 via ADR-518 D3):
> `services/docs.py` carries `document`; `services/studio.py` carries `deck` · `web`;
> `services/images/stage.py` carries `image`. The app boundary is the module; the
> machinery below is one implementation, three consumers.

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
10. **The flow benchmark is two-axis** (ADR-521) — scope is Notion-class (the vocabulary,
    no pagination, no layout surface); mechanics are continuous-surface class (Google
    Docs / Word): text-tier affordances follow the selection wherever it runs;
    structure-tier affordances address the blocks the selection intersects. There is no
    second selection mode.
11. **The selection carries its tier; no surface re-derives it** (ADR-525) — the
    projection runtime is the only party that can see both the DOM and the medium, so it
    declares `text | object | structure` on the selection payload, and the pane, the
    right-click menu and the keyboard all READ that one field. The rule this replaced was
    real but scattered: ADR-484 guarded the cue at two click sites, so five other
    selection routes boxed prose, and three parent-side surfaces each derived their own
    answer — the pane offered Move up/down on a Docs paragraph while the menu on the same
    block refused it. **One chokepoint may paint the selection cue** (`__yarnnnSelect`),
    defended by a completeness assertion, because a per-site invariant cannot be defended
    by executing one site. **ADR-528 extends this**: the tier is not merely read, it is
    what the pane's *scope* is DERIVED from. A surface that commits a scope first and
    consults the tier afterwards can only subtract, and subtraction is how a scope
    accumulates a column of absences.
14. **A range is not a block** (ADR-528) — on a continuous surface the selection is a
    range, which has no box and no single subject; on a stage a block is an object, which
    has both. The flow scope set is therefore `document | range | object` and `block` is
    not a scope Docs can produce. The corollary is a **deletion** rule: when a scope stops
    being reachable, the guards that used to suppress its sections are deleted, never
    re-gated — a guard behind an unreachable scope reads as live policy and is the shape
    stale canon takes in code. **Blocks themselves are RETAINED** — `data-block-id`,
    `data-block="kind"`, `normalizeStructure`. Google Docs is itself block-structured, and
    a flow "block" is a paragraph or heading with a name written on it (`PROMOTE_KIND`).
    What was wrong was never the unit; it was the chrome treating prose as addressable
    because the paragraph happened to carry an id.
12. **A document's structure is the heading tree, derived and never authored** (ADR-526) —
    Docs' structural grain is the HEADING, and a "section" is the span from one heading to
    the next. There is no `<section>` wrapper and no section node: the span is computed by
    document position, the way ADR-519 D2 dissolved Group into "a container with no
    declared layout" rather than adding a node type. The outline is therefore a
    *projection* of the prose — it cannot drift, because it has no independent existence.
    **What the system derives about structure, the member sees**: the outline and the
    enclosing heading were both computed and routed only to the lane posture until
    ADR-526 gave each a second consumer. A derivation with exactly one reader is a
    question about who else should be reading it.
13. **Metrics belong to the design system; emphasis belongs to the member** (ADR-527) —
    the line every benchmark question resolves to. Notion says the system decides what
    Heading 1 measures; Word and Google Docs give the writer a point-size box. yarnnn is
    Notion here, because a document wears a WORKSPACE design system (ADR-449) rather than
    being self-contained. **But holding that line was never a reason to be thin on
    emphasis** — Notion holds it *and* ships underline, strikethrough, highlight and
    colour. Docs had inherited the restriction without the richness. Colour therefore
    ships as palette ROLES (one kernel rule each, so a skin swap re-themes the document),
    never as a picker; point size, line spacing, per-block font and the ruler stay
    refused, with the reason recorded rather than the absence left to look accidental.

## Standing refusals

No raw CSS pane · no DOM-inspector depth · no preview-then-describe edit loop (revisions,
not NL round-trips) · no fourth type / no positioned web (ADR-505) · no pagination
(ADR-480 D6) · no keystroke CRDT · no per-breakpoint editing · no web-font CDNs · no
forms · no JS carousels · no databases/linked views · no synced blocks (that is `data-ref`
at block grain, later) · no second source format (markdown is a projection — ADR-456 D1)
· **no `<section>` wrapper in Docs** (ADR-526 D1/§6 — a section IS the span between
headings; the wrapper is what collapsible headings and move-a-whole-section would
need, and those two are the stated evidence that would reopen it) · **no outline
rail** (ADR-526 D2 — the pane is the structure's home, ADR-520 D4; a second
structural view is the tree ADR-520 D5 refused)
· **no colour picker / point size / line spacing / margin ruler in Docs** (ADR-527 §4 — metrics
are the design system's; the ruler presumes a page, ADR-480 D6) · no editing viewer-owned formats · no owned render engine (ADR-417) · no forked
machinery per app (ADR-518 D2 — the split is housing; a second write path or a forked
runtime is the refused shape) · no block-set selection mode on flow (ADR-521 — the
browser range IS the selection; a second selection mode would rebuild the deleted
editor). The standing drift test (ADR-440 §7, held by Docs and
Studio alike): *does this force a definitional question about the app format, or is
it just a better editor?*

## The forward roster (re-based onto ADR-519's phases, 2026-08-05)

> **Scope note (2026-08-06)**: this roster is **Studio's** — ADR-519's phases are the
> object-hierarchy arc, and D1 scoped them explicitly (*"document is Docs' housing
> (ADR-518) and outside this ADR"*). It names Docs nowhere. Docs' own arc is ADR-521
> (mechanics) → ADR-525 (the tier) → ADR-526 (the heading tree) → **ADR-528 (the scope
> set)**, which closed the premise the first three were each paying interest on. What
> Docs owes now: **span-aware structure ops** (the ramp and turn-into over a multi-block
> range — N blocks, one revision), and the two affordances §6 of ADR-526 names as
> reopening the `<section>` question (collapsible headings, move-a-whole-section) — both
> awaiting evidence, neither scheduled. **Phase A shipped; Phase B is 0/6 and Phase C is 2/6** (numeric entry +
> alignment glyphs, both pulled forward by ADR-520 D3).

The standing Phase-3 cells are absorbed into ADR-519's schedule; cells are marked
shipped here only as they land.

- ✅ **ADR-520 (2026-08-05)** — the stage view (deck shows one slide) · staged
  containers adjustable (w/h handles + fields; amends ADR-516 D7 to *unstaged*
  containers) · numeric X/Y/W/H entry (lands ADR-519 Phase C's item early) ·
  alignment glyph rows · path + Contents in the pane's Identity; the navigator's
  structure tree DELETED (the rail is the sequence).

- **Phase A — the spine** (pure FE recomposition): the pane matrix above · container
  verb-row parity · X/Y readback. ✅ shipped 2026-08-05 — **with a defect fixed
  2026-08-06**: the verb row mounted, but `moveBlock`'s sibling walk stepped by
  `data-block`, so a container was invisible to its own reorder and Move up/down
  answered with silence (`moveBlockTo` returned null; the button never disabled). The
  walk now tests `data-block-id` — what `moveBlockTo` addresses by, so walk and move
  agree on what a sibling is. It survived a green 16/16 gate because that gate asserts
  the row MOUNTS; a grep cannot see an op return null. New executing gate:
  `adr519_container_reorder.mjs`.
- **Phase B — selection completion**: onGroup wiring + multi scope (align/distribute) ·
  Group/Ungroup verbs · ⌘-click deep select · **page identity stamped at the normalize
  seam** (retires the ADR-516 page-anchor resolver by use) · chrome/breadcrumb/
  navigator multi-select consistency.
- **Phase C — layout completion**: Direction row (containers only) · align-self ·
  numeric X/Y/W/H entry (two-clamp) · then the standing pair: snap/alignment guides on
  block drag · container drag = reorder per medium (drop indicators, never positional).
- ✅ **Breadcrumb at the selection** — shipped 2026-08-05: `SelectionBreadcrumb` over
  the canvas, paged media only (flow's chain is caret → block → clear); segments select
  through the navigator's existing paths (rule 7 — a new reach, not a new op).
- Owed keyboard rows (arrows/nudge/Tab-cycle on deck · band reorder keys). ✅ ⌘B/⌘I on
  flow + Tab list indent + `text/html` paste — shipped 2026-08-05 (ADR-521).
- ✅ **The pointer-runtime block-verb residue audit** (ADR-521 D6, deferred around the
  concurrent ADR-520 lane) — executed 2026-08-05. Finding: the verb keys asked only
  "is a block selected, does the caret claim it", never the KIND, while the flow click
  handler makes every block — prose included — a live subject (it withholds only the
  cue, ADR-484). Backspace therefore deleted a whole paragraph in two reachable
  windows: an **emptied** block (the caret guard requires non-empty text) and a
  **cross-block range** (the range's `startContainer` sits in its first block, so the
  in-block test fails for the selected one). Fixed at `selectedBlock()`, the single
  gate every verb reads: on flow the tier is an OBJECT tier; paged is untouched.
- Carried follow-ons: h1-rename-in-place (needs dependent-rewriting on the ADR-448
  edge) · rename does not rewrite dependents (every mover's gap, not Studio's) ·
  measures deriving their posture line · `applies` → `(scope, grain)`.
