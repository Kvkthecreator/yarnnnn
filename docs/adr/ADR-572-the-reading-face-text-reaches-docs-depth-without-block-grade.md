# ADR-572: The reading face — Text reaches Docs' depth without block grade

> **Status**: **Accepted + Implemented** (2026-08-16, operator-directed:
> *"essentially all the Docs features and look-and-feel that can sensibly apply
> to plain prose. A direct comparison against the Docs implementation is fine —
> mimic it."*)
> **Date**: 2026-08-16
> **Dimension**: **Channel** (the surface's depth) primary.
> **Relates to**: ADR-571 (the app whose depth this completes), ADR-456 D1 (the
> grade constraint — the one thing this ADR must not break), ADR-518 (Docs, the
> app being mirrored), ADR-526 D2 (the outline's home is the pane, not a rail),
> ADR-542 D5 (flow ships no nav tab), ADR-466 D6 (the print-as-projection
> technique), ADR-570 (the write door, unchanged).
> **Amends**: ADR-571 D1 (the app's affordance set), and retires ADR-571's
> stated reason for withholding Print/PDF.

---

## 1. Context — the gap ADR-571 left

ADR-571 gave prose a dedicated app with the right *shape*: a landing, a naming
dialog, a renaming crumb, boundary acts, a Properties|Chat rail. Every gate was
green. Beside Docs it still read as thin, and the operator named why with a
screenshot: **the canvas showed raw monospace source.** `# Creative Brief`,
`**not**`, `---` — a 1,062-word brief rendered as a source dump while Docs
renders a document with serif headings and styled tables.

That is a *look-and-feel* gap on the surface and a *depth* gap behind it: Docs
is ~5,600 lines across 26 modules, Text was ~1,100 across 4.

### The audit, and two corrections to the premise

Before building, Docs was audited feature by feature. Two findings changed the
target:

1. **Most of the 5,600 lines are ineligible by construction.** `StudioDesignTab`
   alone is 2,856 lines of design-system/skin/token machinery — the machinery
   ADR-456 D1 forbids here. The line-count gap overstates the *feature* gap
   badly.
2. **Docs itself lacks several things the gap was assumed to include.** Docs has
   **no find/replace anywhere**, **no left navigator on flow** (ADR-542 D5
   deleted the outline tab as "a dead doorway"), **no markdown export** (its own
   panel says so), and its right-click **"History" row is a dead end** — the
   handler just calls `setRightTab('design')` onto a pane with no history
   section. Parity with Docs would have meant *not* building some of these.

So "mimic Docs" resolved to: **take everything that survives the medium
translation, decline the block machinery out loud, and add the two things the
medium genuinely needs that Docs happens not to have.**

## 2. Decisions

### D1 — The canvas has two faces, and a rendered view is not a block model

**Read** renders the markdown (`ProseReader`); **Write** is the textarea ADR-456
D1 requires. One source of truth (`text`), one direction of flow (source →
render). **Read is the default on open** — an existing document is something you
arrive to read.

The grade constraint is honored *because the render never writes*: it holds no
ids, mints nothing, annotates nothing, and maps no node back to an offset.
Delete `ProseReader` and the file is byte-identical. That is the test a view
passes and a block model fails, and it is gated as an absence over the whole app
directory (`data-block-id`, `data-block=`, `StudioCanvas`, `FlowEditor`,
`prosemirror`, `resolveArtifactHtml` — §6L).

**Live-render/edit-in-place was considered and rejected**: transforming markdown
in place as you type requires mapping every rendered node back to a source
offset, which is the annotation table this app is not allowed to keep. The
toggle was chosen precisely because it needs no such map.

**One pipeline, not two.** `MarkdownRenderer` is the workspace's single markdown
implementation and stays that; Text adds a *skin*, not a parser.

> **The scale collision (found by rendering, invisible to every other check).**
> `MarkdownRenderer`'s resting face is `prose-sm` — tuned for chat bubbles.
> Passing `prose-base` alongside it put **two font-size rules on one element**,
> and CSS resolves that by **stylesheet order, not class order**. Measured in
> the compiled sheet: `prose-base` was emitted later and won — *by luck*. Any
> unrelated file changing which utilities Tailwind emits could have silently
> dropped every document to chat size. Fixed by adding an opt-in
> `scale?: 'chat' | 'inherit'` prop that **withholds** the scale classes rather
> than out-specifying them. `'chat'` is the default, so all ~20 existing mounts
> are byte-identical (gated, §7o). `next build`, `tsc`, and all 83 source-level
> checks were green across this defect.

### D2 — View controls: zoom, and a thumbnail that tells the truth

Zoom is ported with Docs' own clamp (0.25–2, click-to-reset), applied to both
faces. It rides CSS `zoom` rather than `transform: scale` so the column reflows
at its scaled measure — a "zoom" that needs horizontal scrolling to read one
line is a crop.

The landing's `ProseThumb` now **renders** its preview as markdown instead of
showing raw source, which is the honest analog of Docs' scaled-iframe
`ArtifactThumb`. A card reading `# Creative Brief` while the document it opens
reads *Creative Brief* is the landing telling a small lie about the app. No
extra fetch — `recent-revisions` already computes `preview`.

### D3 — The outline is addressed by SOURCE LINE, not by block id

Docs carries an outline in its Properties pane (ADR-526 D2: "the pane is the
structure's home" — the same reading that deleted Studio's navigator rail). Text
mirrors it, and **must not mirror its addressing**: Docs walks
`data-block-id`, the banned mechanism.

**A line number is a coordinate into the bytes; a block id is an annotation on
them.** The outline is parsed from the source (ATX + setext, fence-aware,
CommonMark's space rule), and jumping selects a character range in the textarea.
Nothing is written. This is the distinction that lets the feature exist at all,
and it is gated by execution (§6ah).

No navigator rail is built. Docs deliberately has none on flow, and adding one
would exceed the app being mirrored.

### D4 — The boundary acts reach full parity; Print/PDF becomes possible

ADR-571 withheld Print/PDF on honest grounds — *"a prose document has no
rendered form, so print-to-PDF would be printing a textarea."* D1 removes that
blocker, so Docs' technique (ADR-466 D6: render to an HTML string, inject an A4
print sheet, hand it to a hidden iframe's `print()`) ports directly. What you
print is what you were reading — the same renderer produces both.

The print sheet is a **paper** face, not the screen face: real serif families
(the screen's `font-serif` token does not exist inside the iframe), black on
white, and the orphan/widow/`break-after` rules a screen never needs.

Markdown export needs no row: **the file already is markdown**, so Download
answers the sentence Docs' own panel defers to "the interchange wave."

### D5 — Source affordances Docs does not have, taken because the medium needs them

- **Find/replace (⌘F).** Docs has none. Text's documents are the long ones, and
  a 1,000-word brief without find is worse to work in than a 200-word artifact.
  It searches the **source**, and reveals matches by *selecting* them — the
  browser's own position map — rather than painting a highlight layer, which
  would need exactly the offset table D1 forbids.
- **A markdown toolbar (⌘B/⌘I/⌘K + heading/list/quote/table/link/rule).** This
  is the legal half of Docs' Insert menu: Docs inserts *blocks*; this inserts
  *characters*. Every button routes through pure `string → string` functions,
  and the result is the markdown a member would have typed by hand — a connector
  cannot tell a toolbar press from a keystroke. That property is why it is
  allowed, and it is gated by **calling** the functions, not by grepping them.

### D6 — What stays deliberately UNLIKE Docs

**Docs autosaves** (2s idle + blur + beforeunload, no Save button, no dirty
state, 409 auto-retried silently). **Text keeps explicit Save + ⌘S + a dirty
indicator**, because the CAS conflict here is a *product surface*: a connector
may hold the same file, and ADR-570's 409 names who moved the head. A member
needs to know which bytes are theirs before that conversation starts. Recorded
as a divergence rather than drifted into.

## 3. Not done / explicitly out of scope

Named rather than worked around, per the operator's instruction.

### 3.1 The Properties pane's typography / colour / alignment controls

**Audited at control grain, not module grain** (2026-08-16, after the operator
asked whether dismissing `StudioDesignTab` wholesale was too coarse — it was).
The finding is a clean split, and the line it falls on is not a coincidence:

| Docs control | Persists as | Verdict |
|---|---|---|
| Bold / Italic / Strike / Code | **HTML tag** (`<strong>`/`<em>`/`<s>`/`<code>`) | ✅ **shipped** as `**` `_` `~~` `` ` `` |
| Typography ramp (H1/H2/H3 ↔ Text) | **tag swap** `p ↔ h1..h6` — sets no token | ✅ **shipped** as `#`/`##`/`###` |
| Turn into → list / numbered / checklist / quote | tag + `data-block` | ✅ **shipped** (the tag half) |
| Underline | `<u>` | ❌ markdown has no underline |
| **Colour** (5 roles) | `<span data-mark="accent">` | ❌ `data-*` on a minted span |
| **Highlight** (4 roles) | `<span data-highlight="warn">` | ❌ `data-*` on a minted span |
| **Align / Indent** | `data-align="center"` / `data-indent="2"` | ❌ `data-*` on the block |
| **Document font face** | `data-font` **on the artifact's `<html>`** | ❌ markdown has no root element |
| Document width (`measure`) | `data-measure="wide"` on `<html>` | ❌ same |
| Design system apply/remove | a `<style data-skin>` element in `<head>` | ❌ the machinery ADR-456 D1 names |
| W/H measure fields | `data-w` marker + inline `style="--yw: 60%"` | ❌ (also media-blocks-only on flow) |

**Everything that is a tag or a semantic type has a markdown equivalent and is
shipped. Everything that is presentation persists as `data-*`, an inline
custom property, or a `<head>` stylesheet — the mechanisms this app may not
write.** That is the same line ADR-456 D1 drew, arrived at independently from
the write paths.

Two details worth keeping, because they are load-bearing and non-obvious:

1. **Bold is a tag only because a flag says so.** `projection.ts` forces
   `execCommand('styleWithCSS', false, 'false')`, so the engine emits `<b>`
   rather than `<span style="font-weight:bold">`, and `artifactOps.ts`
   normalizes `B→strong`. Flip that flag and even bold becomes inline-style and
   loses its markdown equivalent. The parity here rests on a deliberate choice
   upstream, not on a property of rich text.
2. **Docs already refuses this category from itself.** `StudioDesignTab.tsx`:
   *"Deliberately NOT here: point size, line spacing, font family. Those are
   METRICS and the design system owns them (ADR-449) — §4 records the refusal
   rather than leaving the absence to look like an oversight."* And colour is
   *"a ROLE, never a value … ADR-449 forbids a picker."* Giving Text these
   controls would mean giving it what Docs withholds from itself, in a medium
   with nowhere to store them.

**A prose document has no element to carry presentation.** A `.md` has no root,
no class attribute, no stylesheet. Expressing a colour role would mean writing
raw `<span data-mark>` HTML into the markdown — which forfeits the
byte-for-byte connector round-trip that is the product thesis. **The refusal is
the feature.** If the reading face needs to look different, that is the app's
skin to change (one place, every document), never per-span state in the file.

### 3.2 The Insert palette, kind by kind

Docs' palette serves 16 kinds. Classified by the markup each writes:

- ✅ **Shipped**: heading, list, numbered, quote, divider, table — and
  **checklist**, added by this audit (`- [ ] `; GFM, and `remark-gfm` was
  already in the pipeline rendering real checkboxes). Docs persists checklist
  as `<ul data-block="checklist">` plus a kernel `☐` CSS rule; markdown says
  the same thing natively with no annotation. **Leaving it out was an
  oversight, not a constraint** — corrected here.
- ❌ **Out, with reason**: `callout` (`<aside data-block>`), `button`
  (`<p data-block="button">`), `metrics` (`<div class="metric">`), `component`,
  and the citation kinds `figure` / `gallery` / `chart` / `table`-from-source
  (all carry `data-ref` + `data-ref-rev` — the citation machinery). `toggle` is
  `<details><summary>`, expressible only as raw embedded HTML.

### 3.3 The rest

- **Design systems, skins, tokens** — that IS Studio machinery (ADR-456 D1).
- **Block insertion, per-block Properties, arrangements, citation pins** — all
  require annotating the source.
- **Live edit-in-place rendering** — needs a node→offset map (D1).
- **In-surface revision history** — Docs' own affordance is a dead end; Text
  continues to point at Files → Get Info, which works.
- **Learn-from-a-source on the landing.** The `context-brief` derive recipe
  exists in the kernel registry, targets markdown, and has **zero FE consumers** —
  Text is its natural home. Deferred deliberately: it is a creation flow, not a
  reading/editing gap, and it deserves its own decision about where a derived
  brief lands. Noted here so it is not re-discovered as novel.

## 4. Falsifiers / click-pass

(1) A 1,000-word `.md` opens in Read and renders as a document — serif headings,
a real table, no visible `#` or `**`. (2) Write shows the source; the toggle
round-trips with no byte change. (3) ⌘B over a selection wraps it; pressing
again unwraps to the original bytes. (4) ⌘F finds, ⏎/⇧⏎ cycles, Replace All
works. (5) The Properties outline lists the headings and jumping selects the
right line. (6) Export → Print/PDF produces an A4 document that looks like the
Read view. (7) A landing card shows rendered prose, not `# `. (8) At a phone
width the bottom bar switches Document|Editor and neither pane is unreachable.
(9) Saving still lands a signed revision; a concurrent MCP edit still 409s with
the connector's attribution.

## 5. Verification

`api/test_adr571_text_app.py` (script-style — `python3 test_adr571_text_app.py`;
pytest reports a false pass) extends 37 → **98 checks**. §6 gates the depth and
the grade constraint; §7 **renders the real pipeline** and inspects the output —
the only check that could have caught the D1 scale collision.

Every new section was **falsified**: breaking fence handling fails 6ai; a
smuggled `data-block-id` fails 6L; dropping `scale="inherit"` fails 7n. The
first spelling of 7n asserted its own argument and stayed green through that
last falsification — it now renders `ProseReader` itself, so it checks the
wiring rather than the probe's own input.
