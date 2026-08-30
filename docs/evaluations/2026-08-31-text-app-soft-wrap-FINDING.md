# Finding — the Text canvas preserves soft wraps the reading face joins

**Date**: 2026-08-31 · **Hat**: B (evaluation; the fix lands in Hat A)
**Subject**: `operation/ir-deck-v3/deck-cleanup-notes.md` at `/text`

## Ask

Audit the shipped document for formatting defects "due for updating", and
check whether the prompt envelope scaffolds a NEW document correctly.

## Answer to the first half: the document is not defective

The stored bytes are clean CommonMark — verified by reading the file through
MCP `open` (1,754 chars, `complete_for_write: true`, one revision authored
`KVKtheCreator's Claude (via MCP)`). Hard-wrapped at ~78 columns, which is
what every LLM emits by default and what CommonMark explicitly reflows.

**There is nothing to fix in the file.** What the member sees is a RENDERER
divergence, and editing the document to look right in the canvas would push
a reflow into the substrate to satisfy a display bug.

## The divergence, measured

The same bytes render two ways, and both surfaces ship:

| Surface | Engine | Mount | Result |
|---|---|---|---|
| **Canvas** (`/text`, what the member reads) | CodeMirror + `@lezer/markdown` | `TextEditor.tsx:1287` | **one line box per source line** |
| Thumbnail | react-markdown + remark-gfm | `TextSurface.tsx:341` | one reflowed `<p>` |
| Print / PDF | react-markdown + remark-gfm | `printProse.ts:99` | one reflowed `<p>` |

Independently probed against the real components (jsdom harness from
`test_adr590_rendered_face.py`), on the real bytes:

- Canvas: `sourceLineCount: 12` → `canvasLineCount: 12`. The three prose lines
  stay three boxes. Marks ARE correctly hidden (`deck.html — cleanup notes`,
  not `# deck.html …`), so the live-preview layer works as designed.
- `MarkdownRenderer`, same bytes: `<p>Working notes … rather than a re-read.</p>`
  — one paragraph; the bullet's two continuation lines fold into one `<li>`.

### Why the canvas cannot join them

CodeMirror's document is a plain string and renders one `.cm-line` per `\n`
(`ProseCanvas.tsx:20-23`). `EditorView.lineWrapping` (`:1392`) wraps OVERLONG
lines; it never JOINS short ones. `@lezer/markdown` is a real parser here but
is used only to locate byte ranges to hide or replace — its block structure
never reaches layout.

Three observed symptoms, one cause:

1. **Paragraphs don't reflow** — source hard wraps show as hard breaks.
2. **Lazy continuations orphan** — a bullet's continuation lines become
   separate boxes carrying their literal two leading spaces, with no hanging
   indent. `:164-171`'s `inline-block; width: 1.25em` only indents SOFT-wrapped
   rows of ONE source line; it cannot reach the next line box.
3. **The "stray vertical bar"** — a blank source line is a `.cm-line`
   containing literally `<br>`, with `padding: 0` (`:161`). It is an empty
   full-height line box with the caret in it, not paragraph spacing.

## Why this shipped

`readingFace.ts` exists precisely to keep the two faces identical, and
`TextSurface.tsx:339` / `printProse.ts:93` both claim "the same typography /
the same renderer the canvas uses". **That is true of fonts and sizes and
false of block structure.** `test_adr590_rendered_face.py` asserts tables and
fences; nothing compares PARAGRAPH structure between the two engines, so the
one axis that diverged is the one axis unguarded.

## The consequence is asymmetric, and it propagates

An agent writes correct CommonMark via MCP `save` → thumbnail and PDF are
right → the canvas, the surface the member actually reads, shows a ragged
transcript. A member who "fixes" it by joining lines writes that reflow back
byte-exactly (round-trip is lossless and correct — `TextEditor.tsx:259-285`,
`byteIdentical: true` under mount). **The display limitation then lives in the
commons**, and the next agent `open` reads the rewritten bytes.

## Second half: the envelope scaffolds correctly

- `NameDocumentModal` writes `# {name}\n\n` through the same member door every
  save uses (ADR-570 D4) — one write path, no second door.
- `build_text_posture` renders correctly for both a seeded head and a truly
  empty one (the `— EMPTY (nothing written yet)` branch fires).
- Composition is the single ADR-606 site (`lane_runner._compose_focus_section`).

**One gap, and it is the envelope's half of this same finding**: neither
`build_text_posture` nor `PARTICIPANT_FORMAT_DISCIPLINE` ("Prose documents are
.md") says anything about LINE WRAPPING. The posture says "plain markdown,
WHOLE and honest", which an LLM satisfies by hard-wrapping at 78 columns — the
default that renders badly. The envelope is not wrong; it is silent on the one
convention the canvas is sensitive to.

**Do not fix this in the prompt.** Adding a wrap instruction would be prompt
accretion (ADR-306 / DP22) to compensate for a renderer defect, and it would
bind every participant — including MCP connectors the posture never reaches —
to a convention CommonMark says is meaningless. Fix the renderer; the envelope
then needs no clause.

## Recommendation (Hat A, not taken here)

Join soft wraps in the canvas as a DECORATION over the newline offsets inside
one `Paragraph` node — the identical mechanism already shipping for hidden
`##` marks, writing nothing to the document and preserving byte-identity
(ADR-456 D1 permits this on the argument `ProseCanvas.tsx:36-56` already
makes). It interacts with caret movement and selection across a joined
boundary, so it wants DRIVING, not asserting.

`ProseCanvas.tsx:57` — *"Twice now, a limitation this app 'had' was a
constraint I under-read."* This is the third instance of that shape.

## Separate, unrelated, real

`MarkdownRenderer.tsx:244-289` spreads `{...props}` onto DOM elements. Under
react-markdown v10 that object carries `node` (the hast AST), so shipped HTML
contains `<code node="[object Object]">` on **every inline code span, link and
image** — in chat, file previews, thumbnails and PDFs workspace-wide.
Reproduced above. Fix is destructuring `node` out. Own commit.
