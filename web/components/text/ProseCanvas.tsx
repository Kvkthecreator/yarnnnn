'use client';

/**
 * ProseCanvas — Text's ONE canvas (ADR-572 D8).
 *
 * ## Why one canvas and not two
 *
 * ADR-572 first shipped a Read/Write toggle: a rendered view you could not type
 * into, and a monospace textarea you could. The operator's correction — *"do we
 * need to split the modes? like docs app can we just have one mode"* — is
 * right, and the reasoning behind the split was mine, not the constraint's.
 *
 * ADR-456 D1 permits **"textarea/CodeMirror-grade, never block-grade"**. I read
 * that ceiling as a floor and built the textarea. CodeMirror *is* the named
 * option, and it is exactly the thing that gives one always-editable canvas
 * with styled text — because of the property below.
 *
 * ## Why this is not a block model
 *
 * CodeMirror's document is a **plain string**. Styling is a `Decoration` layer
 * computed FROM the string on each update and thrown away on the next — it
 * never enters the document, is never serialized, and has no identity. The
 * bytes CodeMirror holds are byte-identical to the `.md` on disk.
 *
 * That is the same test `ProseReader` passes, applied continuously instead of
 * behind a toggle:
 *
 *   - no block ids, no `data-*` written into the text
 *   - no node→offset map (decorations are derived from offsets, never the
 *     reverse — nothing maps a rendered node back to a source position)
 *   - delete this component and the file is unchanged
 *
 * A block editor stores a tree with identity and serializes it back out. This
 * stores a string and paints over it. The distinction is the whole product
 * thesis, and it is gated (§6L, §9).
 *
 * ## Live preview (D13, re-cut by D14) — and a claim this file made wrongly
 *
 * The markdown marks are **hidden**, and tables render as a real cell grid.
 * This header previously called the visible marks an "honest limitation",
 * asserting that hiding them needed the node↔offset map ADR-456 D1 bans.
 * **That was wrong** — the same misreading D8 had just corrected one section
 * above. D13 then hid them everywhere EXCEPT the caret's line; the operator
 * drove that and rejected it too (*"i don't want the hashtags visible"*), so
 * D14 hides them unconditionally.
 *
 * D1 constrains the document **MODEL**: a string, never a tree of identified
 * blocks. It says nothing about rendered appearance. Hiding a mark is
 * `Decoration.replace()` over a range read from the syntax tree and recomputed
 * each update — nothing is written to the document, nothing maps a rendered
 * node back for serialization, and the `.md` stays byte-identical. Exactly the
 * test the table decoration already passed.
 *
 * **Twice now, a limitation this app "had" was a constraint I under-read.**
 * Before recording the next one, execute the thing you are calling impossible.
 */

import { useEffect, useMemo, useRef } from 'react';
import { EditorSelection, EditorState, RangeSetBuilder, StateEffect, StateField, type Extension } from '@codemirror/state';
import {
  Decoration,
  EditorView,
  ViewPlugin,
  WidgetType,
  keymap,
  drawSelection,
  highlightActiveLine,
  rectangularSelection,
  type DecorationSet,
  type ViewUpdate,
} from '@codemirror/view';
import { defaultKeymap, history, historyKeymap, isolateHistory } from '@codemirror/commands';
import { markdown, markdownLanguage } from '@codemirror/lang-markdown';
import { HighlightStyle, syntaxHighlighting, syntaxTree } from '@codemirror/language';
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search';
import { tags } from '@lezer/highlight';
import { FACE, HEADING_SCALE, MARK_OPACITY, TABLE } from '@/components/text/readingFace';
import { cn } from '@/lib/utils';

/**
 * The document reading face, expressed as syntax highlighting.
 *
 * Every number comes from `readingFace.ts` — the ONE declaration the rendered
 * skin also derives from (ADR-572 D10). This file no longer restates the type
 * scale; restating it is what let the canvas and the print sheet drift apart.
 *
 * ## The parent-tag trap, named so it is not re-set
 *
 * `tags.heading1` is defined as `t(heading)` — a CHILD of `tags.heading`. Tag
 * inheritance flows parent→child, so a rule on `heading1` does NOT match a
 * node tagged with the bare `heading`. `@lezer/markdown` tags a **table
 * header** with exactly that bare `heading`, so before D10 a table header
 * resolved to no class at all and the whole table rendered as raw pipes.
 *
 * The bare `tags.heading` rule below is therefore load-bearing, and it must
 * stay FIRST: `HighlightStyle` resolves the most specific matching rule, so
 * the numbered rules still win for real headings while the generic rule
 * catches table headers. Verified by executing the parser, not by reading it.
 */
const PROSE_HIGHLIGHT = HighlightStyle.define([
  // The GENERIC heading tag — a table header, and any node the grammar tags
  // as a heading without a level. Must not inherit a document H1's size.
  { tag: tags.heading, fontWeight: TABLE.headerWeight, fontFamily: FACE.serif },
  // Headings — the loudest signal that this is a document, not a code file.
  { tag: tags.heading1, fontSize: HEADING_SCALE.h1.em, fontWeight: HEADING_SCALE.h1.weight, fontFamily: FACE.serif, lineHeight: HEADING_SCALE.h1.leading },
  { tag: tags.heading2, fontSize: HEADING_SCALE.h2.em, fontWeight: HEADING_SCALE.h2.weight, fontFamily: FACE.serif, lineHeight: HEADING_SCALE.h2.leading },
  { tag: tags.heading3, fontSize: HEADING_SCALE.h3.em, fontWeight: HEADING_SCALE.h3.weight, fontFamily: FACE.serif, lineHeight: HEADING_SCALE.h3.leading },
  { tag: tags.heading4, fontSize: HEADING_SCALE.h4.em, fontWeight: HEADING_SCALE.h4.weight, fontFamily: FACE.serif, lineHeight: HEADING_SCALE.h4.leading },
  { tag: tags.heading5, fontWeight: '600' },
  { tag: tags.heading6, fontWeight: '600' },
  { tag: tags.strong, fontWeight: '700' },
  { tag: tags.emphasis, fontStyle: 'italic' },
  { tag: tags.strikethrough, textDecoration: 'line-through', opacity: '0.7' },
  { tag: tags.link, textDecoration: 'underline', textUnderlineOffset: '2px' },
  { tag: tags.url, opacity: MARK_OPACITY.url },
  // Code is the one thing whose glyph width carries meaning.
  { tag: tags.monospace, fontFamily: FACE.mono, fontSize: FACE.codeSize },
  { tag: tags.quote, fontStyle: 'normal', opacity: '0.8' },
  // A table CELL is ordinary body content — tagged `tags.content`, which had
  // no rule at all before D10, so cells fell through to the editor default.
  { tag: tags.content, fontFamily: 'inherit' },
  // A task marker (`[ ]` / `[x]`) is tagged `tags.atom`. Give it the mono face
  // so the box reads as a box and its glyphs line up down the list.
  { tag: tags.atom, fontFamily: FACE.mono, opacity: '0.85' },
  // The MARKS themselves. The `livePreview` plugin (D14) hides them outright,
  // so this rule only paints the transient frames before the syntax tree has
  // parsed a mark the member is mid-way through typing.
  { tag: tags.processingInstruction, opacity: MARK_OPACITY.syntax, fontWeight: '400', fontSize: '0.85em' },
  { tag: tags.contentSeparator, opacity: MARK_OPACITY.structural },
  { tag: tags.list, opacity: '1' },
]);

/** The canvas chrome: a document page, not a code editor. */
const PROSE_THEME = EditorView.theme({
  '&': {
    // The app type token (ADR-572 D10) — the same stack Tailwind's
    // `font-serif` now resolves to, so the canvas and the print sheet wear
    // one face. Previously this read a Docs ARTIFACT-SKIN var that a `.md`
    // can never define, so the inline fallback always won and diverged.
    fontFamily: FACE.serif,
    fontSize: '16px',
    backgroundColor: 'transparent',
    height: '100%',
  },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': {
    fontFamily: 'inherit',
    lineHeight: FACE.lineHeight,
    overflow: 'auto',
    // The reading measure, centred — the same column ProseReader gives.
    padding: '2.5rem 0',
  },
  '.cm-content': {
    maxWidth: FACE.measure,
    margin: '0 auto',
    // The gutter is declared in `FACE` so the chrome above can compose the same
    // column (`FACE.column` = measure + both gutters) and stay aligned with it.
    padding: `0 ${FACE.gutter}`,
    caretColor: 'var(--foreground, #111)',
  },
  '.cm-line': { padding: '0' },
  // ── ADR-575 D8 — the block markers, drawn rather than shown ─────────────
  // A bullet is a glyph in the gutter of its own line, not a literal `- `.
  // `inline-block` with a fixed width gives the hanging indent a list needs
  // without any per-line measurement.
  '.cm-mdBullet': {
    display: 'inline-block',
    width: '1.25em',
    marginLeft: '-0.15em',
    color: 'var(--muted-foreground, #666)',
    // Tabular so `9.`/`10.` do not shift the text after them.
    fontVariantNumeric: 'tabular-nums',
  },
  '.cm-mdTask': {
    display: 'inline-block',
    width: '1.35em',
    fontFamily: FACE.mono,
    color: 'var(--muted-foreground, #666)',
  },
  '.cm-mdTaskDone': { opacity: '0.65' },
  // A thematic break is a RULE. Drawn as a border on an inline-block so it
  // occupies the replaced range without becoming a block decoration — a block
  // widget from this plugin would throw ("Block decorations may not be
  // specified via plugins", the D15 lesson).
  // ⭐ LONGHANDS, not the `borderTop` shorthand. Driven after the first cut:
  // the rule rendered with `borderTopWidth: 0px` and was invisible — a blank
  // gap where a divider should be, which is worse than the literal `---` it
  // replaced. CodeMirror's theme compiler did not carry the shorthand through;
  // `.cm-cursor` in this same theme already uses longhands for exactly this.
  // ⭐ ADR-575 D8.c — the rule needs a BODY, not just a border. Driven after
  // D8.a: an EMPTY inline-block with only `borderTopWidth` has a content box
  // of height 0, so the element's entire hit target is the 1px border itself.
  // It rendered correctly and could not be clicked, dragged over, or
  // rubber-band selected — the operator's "objects like divider aren't
  // grabbable, or selectable via mouse clicks". A line-height's worth of
  // height makes the rule occupy the band it visually sits in, and the border
  // is centred inside it so the drawn line does not move a pixel.
  '.cm-mdRule': {
    display: 'inline-block',
    width: '100%',
    height: '0.75em',
    // The border is drawn at the BOX's vertical middle rather than at its top
    // edge, so growing the hit target leaves the visible line where D8.a put
    // it. `verticalAlign` then re-centres the taller box on the text baseline.
    marginTop: '-0.375em',
    marginBottom: '-0.375em',
    verticalAlign: 'middle',
    borderTopStyle: 'solid',
    borderTopWidth: '1px',
    borderTopColor: 'var(--border, rgba(128,128,128,0.35))',
    // The band above/below the line belongs to the rule, not to the text
    // around it: a click anywhere in it selects the divider.
    boxSizing: 'content-box',
  },
  // A selected block object reads as SELECTED — the tint CodeMirror gives
  // selected text does not reach a widget, so without this a divider inside a
  // selection was the one thing on the line that looked untouched.
  '.cm-mdRule.cm-mdObjSelected': {
    borderTopColor: 'var(--foreground, #111)',
    backgroundColor: 'var(--muted, rgba(128,128,128,0.18))',
  },
  '.cm-activeLine': { backgroundColor: 'transparent' },
  // ⭐ ADR-575 D9 — a blockquote reads as SET ASIDE. The `>` is hidden, so
  // without a bar and an indent a quote was a slightly-grey paragraph with a
  // stray leading space. Longhand borders for the D8.a reason: the theme
  // compiler drops the `borderLeft` shorthand and the bar would be invisible.
  '.cm-line.cm-mdQuote': {
    paddingLeft: '1rem',
    borderLeftStyle: 'solid',
    borderLeftWidth: '3px',
    borderLeftColor: 'var(--border, rgba(128,128,128,0.45))',
    fontStyle: 'italic',
  },
  // ⭐ ADR-575 D9 — the selector must MATCH CodeMirror's own specificity.
  //
  // Measured on the deployed canvas: the computed background was
  // `rgb(215,212,240)` — the library's OPAQUE default — not the translucent
  // tint declared here. CodeMirror ships
  //
  //   .ͼ2.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground
  //
  // which outranks a bare `&.cm-focused .cm-selectionBackground`, so this rule
  // never applied. An opaque slab COVERS the glyphs instead of tinting them,
  // which is what made a selection read as a block painted over the text
  // rather than as text that is selected.
  //
  // The child-combinator path is reproduced verbatim so the two rules tie on
  // specificity and ours wins on order. `!important` would also work and is
  // deliberately avoided: it would silently outrank a future theme too.
  '.cm-selectionBackground, ::selection': { backgroundColor: 'rgba(120,150,255,0.22)' },
  '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'rgba(120,150,255,0.28)',
  },
  '& > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'rgba(120,150,255,0.20)',
  },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--foreground, #111)', borderLeftWidth: '2px' },
  // Find/replace match highlighting (the @codemirror/search extension).
  '.cm-selectionMatch': { backgroundColor: 'rgba(250,200,80,0.30)' },
  '.cm-searchMatch': { backgroundColor: 'rgba(250,200,80,0.35)' },
  '.cm-searchMatch.cm-searchMatch-selected': { backgroundColor: 'rgba(250,160,40,0.55)' },
  '.cm-placeholder': { color: 'var(--muted-foreground, #888)', fontStyle: 'italic' },

  // ── Tables (ADR-572 D10 → D14 → D15) ────────────────────────────────────
  // D10 styled the table LINES; D14 hid the pipes and boxed each cell with
  // mark decorations. Both were driven and both looked wrong, for one
  // structural reason: a line decoration styles ONE LINE, lines lay out
  // independently, so cells in different rows share no column box and the
  // dividers land at different x. D15 replaces the range with a real <table>,
  // so alignment comes from the browser's own table layout.
  '.cm-mdTableWrap': { margin: '1em 0', overflowX: 'auto' },
  '.cm-mdTable': {
    borderCollapse: 'collapse',
    width: '100%',
    fontFamily: 'inherit',
    fontSize: FACE.cellSize,
  },
  '.cm-mdTable th, .cm-mdTable td': {
    border: `1px solid ${TABLE.borderColor}`,
    padding: TABLE.cellPadding,
    textAlign: 'left',
    verticalAlign: 'top',
  },
  '.cm-mdTable th': {
    fontWeight: TABLE.headerWeight,
    backgroundColor: 'var(--table-head, rgba(128,128,128,0.06))',
  },
  // ⭐ ADR-590 D2 — a cell is a text field, and it must LOOK like one when it
  // has focus. Without this the member cannot tell which cell they are typing
  // into, since the browser's default outline is suppressed inside the editor.
  '.cm-mdTable th:focus, .cm-mdTable td:focus': {
    outline: '2px solid var(--ring, rgba(80,120,255,0.55))',
    outlineOffset: '-2px',
    borderRadius: '2px',
  },
  // ── ADR-590 D3: the fences ──────────────────────────────────────────────
  '.cm-mdDiagram': {
    position: 'relative',
    margin: '1em 0',
    padding: '0.75em',
    borderRadius: '6px',
    border: '1px solid var(--border, rgba(128,128,128,0.25))',
    backgroundColor: 'var(--table-tint, rgba(128,128,128,0.03))',
    overflowX: 'auto',
  },
  '.cm-mdDiagramBody svg': { maxWidth: '100%', height: 'auto' },
  '.cm-mdDiagramRaw': {
    fontFamily: FACE.mono,
    fontSize: FACE.codeSize,
    whiteSpace: 'pre-wrap',
    margin: '0',
  },
  // The edit affordance — the DECLARED gesture that reaches a diagram's
  // source. Quiet until the diagram is hovered, so it does not compete with
  // the picture it sits on.
  '.cm-mdDiagramEdit': {
    position: 'absolute',
    top: '6px',
    right: '6px',
    padding: '2px 8px',
    fontFamily: FACE.ui,
    fontSize: '11px',
    lineHeight: '1.6',
    color: 'var(--muted-foreground, #666)',
    backgroundColor: 'var(--background, #fff)',
    border: '1px solid var(--border, rgba(128,128,128,0.3))',
    borderRadius: '4px',
    cursor: 'pointer',
    opacity: '0',
    transition: 'opacity 120ms',
  },
  '.cm-mdDiagram:hover .cm-mdDiagramEdit, .cm-mdDiagramEdit:focus': { opacity: '1' },
  // A mermaid fence the member OPENED reads as source, deliberately — this is
  // the one place source is meant to be visible, and it should look like it.
  '.cm-line.cm-mdFenceOpen': {
    fontFamily: FACE.mono,
    fontSize: FACE.codeSize,
    backgroundColor: 'var(--table-tint, rgba(128,128,128,0.045))',
  },
  // A code fence: one block, mono, with the language as a small label where
  // the ```lang line used to read.
  '.cm-line.cm-mdCode': {
    fontFamily: FACE.mono,
    fontSize: FACE.codeSize,
    backgroundColor: 'var(--table-tint, rgba(128,128,128,0.045))',
    paddingLeft: '0.75em',
    paddingRight: '0.75em',
  },
  '.cm-line.cm-mdCodeFirst': {
    borderTopLeftRadius: '6px',
    borderTopRightRadius: '6px',
    paddingTop: '0.4em',
  },
  '.cm-line.cm-mdCodeLast': {
    borderBottomLeftRadius: '6px',
    borderBottomRightRadius: '6px',
    paddingBottom: '0.4em',
  },
  '.cm-mdCodeLang': {
    fontFamily: FACE.ui,
    fontSize: '10px',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--muted-foreground, #888)',
  },
});
/**
 * Live preview — hide the markdown marks except on the line being edited
 * (ADR-572 D13).
 *
 * ## The correction this represents
 *
 * ADR-572 D8 shipped the marks permanently VISIBLE and called it an "honest
 * limitation", claiming that hiding them needs the node↔offset map ADR-456 D1
 * bans. **That was wrong, and it is the same misreading D8 itself corrected**:
 * D1 constrains the document MODEL ("textarea/CodeMirror-grade, never
 * block-grade") — a string rather than a tree of identified blocks. It says
 * nothing about rendered appearance.
 *
 * Hiding a mark is `Decoration.replace()` over a range read from the syntax
 * tree and recomputed each update. Nothing is written to the document, nothing
 * maps a rendered node back for serialization, and the `.md` stays
 * byte-identical — the same test the table decoration passes. Verified by
 * executing it before the claim was made, which is what D8's version lacked.
 *
 * ## Marks are hidden ALWAYS, not "except on the active line" (D14)
 *
 * D13 shipped the Obsidian compromise — marks revealed on the line the caret
 * occupied — on my reasoning that editing syntax you cannot see is
 * disorienting. **The operator drove it and rejected it**: *"i don't want the
 * hashtags visible."* On a surface being promoted to the primary writing app
 * (ADR-574), a `##` appearing the moment you click into a heading is the
 * source leaking through the document, which is exactly the thing the reading
 * face exists to stop.
 *
 * The concern behind D13 is answered structurally instead of by revealing
 * source: the heading's SIZE already says which level it is, the toolbar
 * changes it, and the outline lists it. A member never needs to read `##` to
 * know they are in an H2.
 *
 * Hiding is still pure decoration — nothing is written, the `.md` is
 * byte-identical, and deleting this plugin restores the raw source.
 */
const HIDDEN_MARKS = new Set([
  'HeaderMark',
  'EmphasisMark',
  'StrikethroughMark',
  'CodeMark',
  'QuoteMark',
  'LinkMark',
  'URL',
]);

/**
 * ⭐ ADR-575 D8 — the BLOCK markers, which this set never covered.
 *
 * Found by driving the canvas: every mark in `HIDDEN_MARKS` above is an
 * INLINE mark, so `#`, `**` and `` ` `` were hidden while every block-level
 * marker leaked through as literal source. Measured on the deployed surface:
 *
 *   - a bulleted list rendered `- first item`, dash and all
 *   - a task list rendered `- [ ] `, with no checkbox
 *   - Divider rendered `---` as three dashes, with no rule
 *   - an EMPTY list line (`- ` with nothing after it) rendered as a blank
 *     line with no bullet at all — the "inserted formatting disappears"
 *     the operator reported
 *
 * The reading face was therefore only half-built: inline marks were being
 * suppressed while the structure they sit inside was still showing its source.
 *
 * These are NOT added to `HIDDEN_MARKS`, because hiding a `- ` outright is
 * what produced the invisible-bullet case: a list item with its marker
 * replaced by nothing is indistinguishable from an empty paragraph. A list
 * needs a GLYPH, and a thematic break needs a RULE, so each is replaced by a
 * widget rather than erased.
 *
 * Still pure decoration: the widgets are rebuilt from the syntax tree on every
 * update, hold no id, and are never serialized. Delete this and the `.md` is
 * byte-identical — the same test D13/D15 pass.
 */
class BulletWidget extends WidgetType {
  constructor(readonly label: string) { super(); }
  eq(other: BulletWidget) { return other.label === this.label; }
  toDOM() {
    const s = document.createElement('span');
    s.className = 'cm-mdBullet';
    s.textContent = this.label;
    return s;
  }
  ignoreEvent() { return false; }
}

/**
 * ⭐ ADR-575 D8.c — a divider is an OBJECT, and an object must be hittable.
 *
 * The first cut returned a bare `<span class="cm-mdRule">` with no content and
 * no height, styled only with a top border. It rendered — and it was the one
 * widget on the canvas that could not be clicked, dragged across, or selected,
 * because an empty inline-block's content box is 0px tall and the border is
 * the only pixel the mouse can land on. Every OTHER widget here (bullet, task
 * box, table) ships real content and was hittable for free, which is why this
 * one defect survived a 249-check gate.
 *
 * `selected` paints the object's own selected state: CodeMirror's selection
 * tint is drawn for TEXT, so a widget inside a selection otherwise stays
 * visually untouched while everything around it highlights.
 */
class RuleWidget extends WidgetType {
  constructor(readonly selected: boolean) { super(); }
  eq(other: RuleWidget) { return other.selected === this.selected; }
  toDOM(view: EditorView) {
    const doc = view.dom.ownerDocument;
    const s = doc.createElement('span');
    s.className = 'cm-mdRule' + (this.selected ? ' cm-mdObjSelected' : '');
    // A widget with no content is unreachable by the mouse. A zero-width space
    // gives the box a real inline content node to hit-test against, while
    // adding nothing visible and nothing to the document.
    s.textContent = '​';
    return s;
  }
  ignoreEvent() { return false; }
}

class TaskBoxWidget extends WidgetType {
  constructor(readonly checked: boolean) { super(); }
  eq(other: TaskBoxWidget) { return other.checked === this.checked; }
  toDOM() {
    const s = document.createElement('span');
    s.className = 'cm-mdTask' + (this.checked ? ' cm-mdTaskDone' : '');
    s.textContent = this.checked ? '☑' : '☐';
    return s;
  }
  ignoreEvent() { return false; }
}

const livePreview = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;
    constructor(view: EditorView) {
      this.decorations = buildPreviewDecorations(view);
    }
    update(u: ViewUpdate) {
      // `selectionSet` is in the list for D8.c: the rule widget paints its own
      // selected state, and a selection change alone moves no doc and no
      // viewport — so without it, dragging across a divider highlighted every
      // character around it and left the divider itself unchanged.
      if (u.docChanged || u.viewportChanged || u.selectionSet) {
        this.decorations = buildPreviewDecorations(u.view);
      }
    }
  },
  { decorations: (v) => v.decorations },
);

function buildPreviewDecorations(view: EditorView): DecorationSet {
  const { state } = view;
  const doc = state.doc;

  // Collected then sorted: `RangeSetBuilder` requires ascending order, and the
  // tree does not guarantee it across nested inline nodes.
  // `deco` is null for a plain hide, or the replacement widget (ADR-575 D8).
  const marks: Array<[number, number, Decoration | null]> = [];
  // Line decorations are kept apart: they are zero-length and must be added at
  // the line start, BEFORE any mark that begins on the same offset, or
  // `RangeSetBuilder` throws on out-of-order input (ADR-575 D9).
  const lineDecos: Array<[number, Decoration]> = [];
  for (const { from, to } of view.visibleRanges) {
    syntaxTree(state).iterate({
      from,
      to,
      enter(node) {
        // A table's range is REPLACED wholesale by the widget (D15), so a mark
        // decoration inside it has nothing to attach to — CodeMirror rejects
        // the overlap outright (`RangeSet.spans`). Tables own their own
        // rendering; this plugin stays out of them.
        if (node.name === 'Table') return false;

        // Same reason for a fenced block (ADR-590 D3): a mermaid fence is
        // REPLACED wholesale by the diagram widget, and a code fence has its
        // own line treatment — an inline mark inside either has nothing to
        // attach to. Fences own their own rendering; this plugin stays out.
        if (node.name === 'FencedCode') return false;

        // ⭐ ADR-575 D9 — a blockquote is a SET-ASIDE, not italics.
        //
        // The `>` is hidden (it is in HIDDEN_MARKS), and the only remaining
        // treatment was `opacity: 0.8` on the text — so a quote rendered as a
        // slightly grey paragraph with a stray leading space, indistinguishable
        // from body copy. Driven: "the quote feature doesn't look much
        // different in terms of applied layout."
        //
        // A LINE decoration, because the bar and the indent belong to the line
        // box, not to a character range. Every line the quote spans gets it,
        // so a multi-line quote reads as one block.
        if (node.name === 'Blockquote') {
          const first = doc.lineAt(node.from).number;
          const last = doc.lineAt(node.to).number;
          for (let n = first; n <= last; n++) {
            const l = doc.line(n);
            lineDecos.push([l.from, Decoration.line({ class: 'cm-mdQuote' })]);
          }
          return; // keep descending: the QuoteMark inside still needs hiding
        }

        // ── ADR-575 D8: the block markers ────────────────────────────────
        // A thematic break becomes a RULE. Replacing it with nothing would
        // leave a blank line that reads as an accident.
        if (node.name === 'HorizontalRule') {
          // Selected when the selection COVERS the rule's range — the same
          // test a member's eye applies when they drag across it (D8.c).
          const sel = state.selection.main;
          const covered = sel.from <= node.from && sel.to >= node.to && !sel.empty;
          marks.push([
            node.from,
            node.to,
            Decoration.replace({ widget: new RuleWidget(covered) }),
          ]);
          return false;
        }
        // A list marker becomes a GLYPH. `ListMark` covers `-`/`*`/`+` and
        // the `1.` of an ordered list; an ordered marker keeps its own number
        // so the sequence the source states is the sequence shown.
        if (node.name === 'ListMark') {
          let end = node.to;
          if (doc.sliceString(end, end + 1) === ' ') end += 1;
          const raw = doc.sliceString(node.from, node.to);
          const ordered = /\d/.test(raw);
          // A task item's `[ ]` follows the marker; it is rendered by the
          // Task branch below, so the bullet is dropped for those lines to
          // avoid painting a bullet AND a checkbox.
          const after = doc.sliceString(end, end + 4);
          if (/^\[[ xX]\]/.test(after)) {
            marks.push([node.from, end, Decoration.replace({})]);
            return false;
          }
          marks.push([
            node.from,
            end,
            Decoration.replace({ widget: new BulletWidget(ordered ? raw : '•') }),
          ]);
          return false;
        }
        // `[ ]` / `[x]` — a real box. Tagged `Task`/`TaskMarker` by
        // @lezer/markdown's GFM task-list extension.
        if (node.name === 'TaskMarker') {
          let end = node.to;
          if (doc.sliceString(end, end + 1) === ' ') end += 1;
          const checked = /[xX]/.test(doc.sliceString(node.from, node.to));
          marks.push([
            node.from,
            end,
            Decoration.replace({ widget: new TaskBoxWidget(checked) }),
          ]);
          return false;
        }

        if (!HIDDEN_MARKS.has(node.name)) return;
        let end = node.to;
        // `# ` / `> ` — swallow the trailing space too, or the line keeps a
        // hanging indent. The quote case is visible in the operator's D9
        // screenshot as a stray space before "a quote" (ADR-575 D9).
        if (
          (node.name === 'HeaderMark' || node.name === 'QuoteMark') &&
          doc.sliceString(end, end + 1) === ' '
        ) {
          end += 1;
        }
        if (end > node.from) marks.push([node.from, end, null]);
      },
    });
  }
  marks.sort((a, b) => a[0] - b[0] || a[1] - b[1]);

  const b = new RangeSetBuilder<Decoration>();
  // Merge the two streams in ascending order. At an equal offset the LINE
  // decoration goes first — it is zero-length, and `RangeSetBuilder` requires
  // a non-decreasing sequence of (from, to).
  lineDecos.sort((a, b2) => a[0] - b2[0]);
  let li = 0;
  let prevEnd = -1;
  const flushLinesUpTo = (offset: number) => {
    while (li < lineDecos.length && lineDecos[li][0] <= offset) {
      b.add(lineDecos[li][0], lineDecos[li][0], lineDecos[li][1]);
      li++;
    }
  };
  for (const [from, to, deco] of marks) {
    if (from < prevEnd) continue; // skip overlaps (nested inline marks)
    flushLinesUpTo(from);
    b.add(from, to, deco ?? Decoration.replace({}));
    prevEnd = to;
  }
  flushLinesUpTo(Infinity);
  return b.finish();
}

/**
 * Mark every line belonging to a GFM table, so the theme above can draw a
 * grid around it (ADR-572 D10).
 *
 * ## Why this is not the banned node↔offset map
 *
 * ADR-456 D1 forbids a map from a RENDERED NODE back to a source position —
 * the thing a block editor needs to write an edit back out. This is the
 * opposite direction and it never round-trips: the syntax tree is read to
 * decide which LINES get a CSS class, the classes are thrown away on the next
 * update, and nothing they touch is ever serialized. Take this away and the
 * `.md` is byte-identical. The test is the same one the file header states:
 * decorations are derived FROM offsets, never the reverse.
 */
/**
 * The table renderer is a **StateField, not a ViewPlugin** (ADR-572 D15).
 *
 * CodeMirror refuses block-level decorations from a plugin outright — *"Block
 * decorations may not be specified via plugins"* — because a plugin's
 * decorations are computed after layout, and a block widget changes layout.
 * The first cut of D15 was a ViewPlugin and threw on mount. A StateField is
 * computed from the state before the view measures anything, which is exactly
 * what a range-replacing widget needs.
 *
 * It is still derived, still transient, and still writes nothing: the field
 * holds a decoration set recomputed from the document, never part of it.
 */
const tableField = StateField.define<DecorationSet>({
  create: (state) => buildTableDecorations(state),
  update(deco, tr) {
    // ⭐ ADR-590 D1 — the table no longer depends on the SELECTION at all: it
    // renders whether or not the caret is in it, so only a document change can
    // change the decorations. (Before D1 a bare selection change had to
    // recompute, because it swapped the grid for raw source.)
    if (!tr.docChanged) return deco.map(tr.changes);
    return buildTableDecorations(tr.state);
  },
  provide: (f) => EditorView.decorations.from(f),
});

/**
 * A real `<table>` painted over the source rows (ADR-572 D15).
 *
 * ## Why a widget, and why the previous two attempts failed
 *
 * D10 styled the table LINES (mono, a tint, a left border) so the source pipes
 * would align. D14 hid the pipes and drew per-cell boxes with mark decorations.
 * The operator drove both: *"the table rendering still looks off… these should
 * be rather conventional approaches"* — and the screenshot showed exactly why.
 * **Every row's column divider sat at a different x.**
 *
 * That is not a CSS bug to chase. A line decoration styles ONE LINE, and each
 * line is laid out independently, so cells in different rows share no column
 * box. With a proportional face, "Verse 1" and "Final chorus" can never line
 * up. **No refinement of a line-based approach can align columns**; a table
 * needs the rows in one grid, which means one element spanning them.
 *
 * So the whole table range is replaced by a `<table>` built from the parsed
 * rows. Alignment then comes from the browser's own table layout — the
 * conventional thing the operator asked for.
 *
 * ## Why this is still not a block model (ADR-456 D1)
 *
 * The widget is rendered FROM the source on each update and thrown away on the
 * next. It holds no id, is never serialized, and nothing maps a cell back to a
 * source position for writing. The document remains the plain `.md` — clicking
 * the table dismisses the widget and hands back the raw rows to edit. Delete
 * this class and the file is unchanged, which is the same test every other
 * decoration here passes.
 */
/** One source row of a GFM table: its line number, and its cells. */
interface TableRow {
  /** 1-based line number in the document — the row an edit rewrites. */
  line: number;
  cells: string[];
}

/**
 * Escape a cell's text for a GFM table cell (ADR-590 D2).
 *
 * A cell is one line by construction, so a pasted newline becomes a space
 * rather than silently breaking the table into prose. A literal `|` must be
 * escaped or it reads as a column boundary on the way back in — the round-trip
 * property `splitRow` already honours in the other direction.
 */
function escapeCell(text: string): string {
  return text.replace(/\r?\n/g, ' ').replace(/\|/g, '\\|').trim();
}

/**
 * Re-emit a whole GFM table from its rows (ADR-590 D2).
 *
 * The WHOLE table is rewritten on every cell commit, never a per-cell splice:
 * a table's rows are interdependent (the delimiter row must match the column
 * count), so a character-grained diff would have to reason about machinery the
 * member never edits. Re-emitting is one obviously-correct operation.
 */
function serializeTable(rows: TableRow[]): string {
  const [head, ...body] = rows;
  if (!head) return '';
  const width = head.cells.length;
  const line = (cells: string[]) => {
    const padded = Array.from({ length: width }, (_, i) => cells[i] ?? '');
    return `| ${padded.join(' | ')} |`;
  };
  return [
    line(head.cells),
    `| ${Array.from({ length: width }, () => '---').join(' | ')} |`,
    ...body.map((r) => line(r.cells)),
  ].join('\n');
}

/**
 * A real `<table>` painted over the source rows, whose cells are the text
 * fields (ADR-572 D15.b + ADR-590 D2).
 *
 * ## Why an editable widget is still not a block model
 *
 * The docstring this replaces said *"nothing maps a cell back to a source
 * position for writing"* — true of that code, but written as though ADR-456 D1
 * required it. **It does not**, and ADR-590 §2 records this as the THIRD time
 * that misreading has been caught in this app (ADR-572 D8 and D13 are the
 * other two). D1 constrains the document MODEL — a persisted tree of
 * identified blocks — and says nothing about where keystrokes land.
 *
 * The test that separates a view from a block model is unchanged, and this
 * passes it: the widget is built FROM the source each update, holds no id, is
 * never serialized, and the document stays the plain `.md`. An edit is not
 * stored here and flushed later — it is dispatched immediately and comes back
 * as a fresh render, so there is no second copy of the table at any instant.
 * Delete this class and the file is unchanged.
 */
class TableWidget extends WidgetType {
  constructor(
    private readonly rows: TableRow[],
    private readonly src: string,
    /** Document offsets of the table's source range — an edit's write target. */
    private readonly from: number,
    private readonly to: number,
  ) {
    super();
  }

  // CodeMirror reuses a widget when `eq` says the content is unchanged, so
  // comparing the SOURCE keeps the DOM — and the caret inside a cell being
  // typed into — stable while the member works elsewhere in the document.
  eq(other: TableWidget) {
    return other.src === this.src && other.from === this.from;
  }

  /**
   * Commit one cell: re-emit the table with that cell replaced, and dispatch
   * the change over the table's own range.
   *
   * Returns false when nothing changed, so an ordinary blur (tabbing through,
   * clicking away) does not push an empty transaction onto the undo stack.
   */
  private commit(view: EditorView, row: number, col: number, text: string): boolean {
    const next = escapeCell(text);
    if (this.rows[row]?.cells[col] === next) return false;
    const rows = this.rows.map((r, i) =>
      i === row ? { ...r, cells: r.cells.map((c, j) => (j === col ? next : c)) } : r,
    );
    view.dispatch({
      changes: { from: this.from, to: this.to, insert: serializeTable(rows) },
    });
    return true;
  }

  toDOM(view: EditorView) {
    // The view's OWN document, never the global one: the canvas may be
    // rendered into another window (a popped-out surface, a print frame), and
    // `document.createElement` there builds nodes the view cannot adopt.
    const document = view.dom.ownerDocument;
    const wrap = document.createElement('div');
    wrap.className = 'cm-mdTableWrap';
    const table = document.createElement('table');
    table.className = 'cm-mdTable';

    /** Every cell in visual order, so Tab can walk them. */
    const cells: HTMLElement[] = [];

    const mkCell = (el: HTMLElement, row: number, col: number, text: string) => {
      el.textContent = text;
      // ⭐ ADR-590 D2 — the cell IS the text field. `plaintext-only` keeps a
      // paste from carrying markup into a construct that can only hold text.
      //
      // `setAttribute`, not the `contentEditable` PROPERTY: the property
      // setter is a no-op in jsdom (it does not reflect to the attribute and
      // `isContentEditable` reads `undefined`), so the gate that mounts this
      // canvas could never observe the one thing D2 is about. The attribute is
      // what the browser reads either way — this is the portable spelling, not
      // a concession to the test.
      el.setAttribute('contenteditable', 'plaintext-only');
      el.spellcheck = true;
      el.dataset.row = String(row);
      el.dataset.col = String(col);
      cells.push(el);

      el.addEventListener('blur', () => {
        this.commit(view, row, col, el.textContent ?? '');
      });

      el.addEventListener('keydown', (e: KeyboardEvent) => {
        // These keys belong to the table while a cell has focus. CodeMirror's
        // own keymap does not reach inside a widget's DOM, so the widget owns
        // them or nothing does.
        if (e.key === 'Escape') {
          e.preventDefault();
          el.textContent = this.rows[row]?.cells[col] ?? '';
          el.blur();
          view.focus();
          return;
        }
        if (e.key === 'Tab' || e.key === 'Enter') {
          e.preventDefault();
          const i = cells.indexOf(el);
          // Enter moves DOWN a row (the spreadsheet reflex); Tab moves across.
          const width = this.rows[0]?.cells.length ?? 1;
          const step = e.key === 'Enter' ? width : 1;
          const target = cells[e.shiftKey ? i - step : i + step];
          // Commit FIRST: the dispatch re-renders the widget, so the node we
          // hand focus to must be located after that by its row/col address,
          // never by a reference into the DOM the render replaced.
          const changed = this.commit(view, row, col, el.textContent ?? '');
          if (!target) return;
          if (!changed) {
            target.focus();
            return;
          }
          const r = target.dataset.row;
          const c = target.dataset.col;
          requestAnimationFrame(() => {
            view.dom
              .querySelector<HTMLElement>(`.cm-mdTable [data-row="${r}"][data-col="${c}"]`)
              ?.focus();
          });
        }
      });
    };

    const [head, ...body] = this.rows;
    if (head) {
      const thead = table.createTHead();
      const tr = thead.insertRow();
      head.cells.forEach((cell, col) => {
        const th = document.createElement('th');
        mkCell(th, 0, col, cell);
        tr.appendChild(th);
      });
    }
    const tbody = table.createTBody();
    body.forEach((row, i) => {
      const tr = tbody.insertRow();
      row.cells.forEach((cell, col) => {
        mkCell(tr.insertCell(), i + 1, col, cell);
      });
    });
    wrap.appendChild(table);
    return wrap;
  }

  /**
   * The widget handles its OWN events (ADR-590 D2).
   *
   * Returning true keeps CodeMirror from mapping a click inside a cell to a
   * document position — which would move the caret into the source behind the
   * table and, before D1, swapped the whole grid for raw pipes. The cells are
   * `contenteditable`, so the browser gives them a caret directly.
   */
  ignoreEvent() {
    return true;
  }
}

/** Split a GFM row on unescaped pipes, dropping the leading/trailing empties. */
function splitRow(line: string): string[] {
  const cells: string[] = [];
  let cur = '';
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '\\' && line[i + 1] === '|') { cur += '|'; i++; continue; }
    if (ch === '|') { cells.push(cur); cur = ''; continue; }
    cur += ch;
  }
  cells.push(cur);
  if (cells.length && !cells[0].trim()) cells.shift();
  if (cells.length && !cells[cells.length - 1].trim()) cells.pop();
  return cells.map((c) => c.trim());
}

const DELIMITER_RE = /^\s*\|?[\s:|-]*\|[\s:|-]*$/;

function buildTableDecorations(state: EditorState): DecorationSet {
  const doc = state.doc;
  const out: Array<{ from: number; to: number; deco: Decoration }> = [];

  {
    // A StateField has no viewport, so the whole tree is walked. Tables are
    // sparse in prose and `iterate` skips non-matching subtrees, so this is
    // cheaper than it reads.
    syntaxTree(state).iterate({
      enter(node) {
        if (node.name !== 'Table') return;
        const start = doc.lineAt(node.from);
        const end = doc.lineAt(node.to);

        // ⭐ ADR-590 D1 — there is no editing branch. A table renders, and the
        // caret arriving does NOT hand back raw pipes. The source-revealing
        // path that used to live here is DELETED, not conditioned: a second
        // rendering of one construct, reachable by an ordinary click, is the
        // dual-approach shape, and it was D13's reversed reveal rule surviving
        // in the one place D14.a never reached.
        //
        // Replace the whole range with a real <table>. One element spanning
        // every row is the only way columns can align — what the two
        // line-based attempts could never do (D15.b).
        //
        // `rows` carries each cell's SOURCE LINE NUMBER so an edit knows which
        // row to rewrite; the delimiter row is dropped from the grid, because
        // rewriting the table re-emits it from the column count.
        const rows: TableRow[] = [];
        for (let n = start.number; n <= end.number; n++) {
          const text = doc.line(n).text;
          if (DELIMITER_RE.test(text) && text.includes('-')) continue;
          rows.push({ line: n, cells: splitRow(text) });
        }
        if (rows.length === 0) return;
        const src = doc.sliceString(start.from, end.to);
        out.push({
          from: start.from,
          to: end.to,
          deco: Decoration.replace({
            widget: new TableWidget(rows, src, start.from, end.to),
            block: true,
          }),
        });
      },
    });
  }

  out.sort((a, b2) => a.from - b2.from || a.to - b2.to);
  const b = new RangeSetBuilder<Decoration>();
  for (const r of out) b.add(r.from, r.to, r.deco);
  return b.finish();
}

/**
 * ⭐ ADR-590 D3 — the fences render as themselves.
 *
 * Before this, the canvas rendered NO fence at all: a ```mermaid block was
 * three backticks, the word "mermaid", and a graph definition, all set in the
 * reading face's serif body copy. The operator's screenshot shows exactly that
 * — a diagram reading as broken prose, because nothing claimed it.
 *
 * ## The two fences are different, and only one is an exception to D1
 *
 * A CODE fence's content IS its source: editing the code and editing the
 * markdown are the same act. So it renders as a highlighted block that is
 * still ordinary editable text underneath — no reveal is needed, and D1 holds
 * with nothing special done.
 *
 * A MERMAID fence's source is a DIFFERENT LANGUAGE from its picture, and no
 * in-place gesture edits a rendered graph. It is the one genuine exception in
 * ADR-590 — and it is an exception to HOW the source is reached, never to
 * whether the caret reaches it. The diagram carries an explicit edit
 * affordance; caret entry still does nothing. D1 bans the INCIDENTAL gesture
 * (clicking where you meant to read), not a control the member pressed.
 */
const revealFence = StateEffect.define<number>();
const collapseFence = StateEffect.define<number>();

/** Line numbers of mermaid fences the member has opened for editing (D3). */
const revealedFences = StateField.define<Set<number>>({
  create: () => new Set(),
  update(set, tr) {
    let next = set;
    for (const e of tr.effects) {
      if (e.is(revealFence)) {
        next = new Set(next);
        next.add(e.value);
      } else if (e.is(collapseFence)) {
        next = new Set(next);
        next.delete(e.value);
      }
    }
    // A revealed fence is keyed by the line its ``` opens on. A document edit
    // can move that line, so the set is remapped rather than silently pointing
    // at whatever now occupies the old number.
    if (tr.docChanged && next.size) {
      const moved = new Set<number>();
      // `forEach` rather than `for…of`: the build target predates downlevel
      // Set iteration, and this is the codebase's idiom for it.
      next.forEach((line) => {
        const oldDoc = tr.startState.doc;
        if (line < 1 || line > oldDoc.lines) return;
        const pos = tr.changes.mapPos(oldDoc.line(line).from, 1);
        moved.add(tr.state.doc.lineAt(pos).number);
      });
      next = moved;
    }
    return next;
  },
});

/**
 * A rendered mermaid diagram (D3).
 *
 * The SVG is produced by the same `mermaid` module the workspace's one
 * `MarkdownRenderer` uses — dynamically imported, so a document with no
 * diagram never pays for the bundle. Rendering is async and the widget's DOM
 * is returned synchronously, so the node is filled in when the promise
 * settles; a failed parse shows the source rather than an empty box, because a
 * blank space where a diagram should be reads as a bug in the document.
 */
class MermaidWidget extends WidgetType {
  constructor(
    private readonly code: string,
    /** Line the fence opens on — the key an edit affordance reveals. */
    private readonly line: number,
  ) {
    super();
  }

  eq(other: MermaidWidget) {
    return other.code === this.code && other.line === this.line;
  }

  toDOM(view: EditorView) {
    const document = view.dom.ownerDocument;
    const wrap = document.createElement('div');
    wrap.className = 'cm-mdDiagram';

    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'cm-mdDiagramEdit';
    edit.textContent = 'Edit diagram';
    // ⭐ D3 — the DECLARED gesture. Caret entry does nothing; this does.
    edit.addEventListener('mousedown', (e) => {
      e.preventDefault();
      view.dispatch({ effects: revealFence.of(this.line) });
    });
    wrap.appendChild(edit);

    const host = document.createElement('div');
    host.className = 'cm-mdDiagramBody';
    wrap.appendChild(host);

    void (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'strict' });
        const id = `cm-mermaid-${Math.random().toString(36).slice(2, 9)}`;
        const { svg } = await mermaid.render(id, this.code);
        host.innerHTML = svg;
      } catch {
        // A diagram that will not parse shows its SOURCE. The member is
        // mid-edit on a graph definition far more often than they are looking
        // at a broken one, and an empty box tells them nothing.
        const pre = document.createElement('pre');
        pre.className = 'cm-mdDiagramRaw';
        pre.textContent = this.code;
        host.appendChild(pre);
      }
    })();

    return wrap;
  }

  ignoreEvent() {
    // The edit button is the widget's own; a click anywhere else must not map
    // to a document position behind the diagram.
    return true;
  }
}

function buildFenceDecorations(state: EditorState): DecorationSet {
  const doc = state.doc;
  const revealed = state.field(revealedFences);
  const out: Array<{ from: number; to: number; deco: Decoration }> = [];

  syntaxTree(state).iterate({
    enter(node) {
      if (node.name !== 'FencedCode') return;
      const openLine = doc.lineAt(node.from).number;
      const endLine = doc.lineAt(node.to).number;

      let info = '';
      let body: { from: number; to: number } | null = null;
      const cur = node.node.cursor();
      if (cur.firstChild()) {
        do {
          if (cur.name === 'CodeInfo') info = doc.sliceString(cur.from, cur.to).trim();
          else if (cur.name === 'CodeText') body = { from: cur.from, to: cur.to };
        } while (cur.nextSibling());
      }

      // ── A MERMAID fence: the diagram, unless the member opened it. ──
      if (info.toLowerCase() === 'mermaid') {
        if (revealed.has(openLine)) {
          // Opened for editing: the raw fence, marked so the theme can set it
          // in mono and show it is open.
          for (let n = openLine; n <= endLine; n++) {
            const l = doc.line(n);
            out.push({ from: l.from, to: l.from, deco: Decoration.line({ class: 'cm-mdFenceOpen' }) });
          }
          return false;
        }
        const code = body ? doc.sliceString(body.from, body.to) : '';
        if (!code.trim()) return false; // an empty fence is still being typed
        out.push({
          from: node.from,
          to: node.to,
          deco: Decoration.replace({ widget: new MermaidWidget(code, openLine), block: true }),
        });
        return false;
      }

      // ── A CODE fence: a styled block whose text stays editable. ──
      // No widget and no replace: the content IS the source (D3), so the
      // lines are simply given a face. The ``` marks and the language are
      // hidden the way every other mark is, leaving the code and its label.
      for (let n = openLine; n <= endLine; n++) {
        const l = doc.line(n);
        const first = n === openLine;
        const last = n === endLine;
        out.push({
          from: l.from,
          to: l.from,
          deco: Decoration.line({
            class:
              'cm-mdCode' +
              (first ? ' cm-mdCodeFirst' : '') +
              (last ? ' cm-mdCodeLast' : ''),
          }),
        });
      }
      // The fence lines themselves carry no content the member should read.
      const openL = doc.line(openLine);
      const closeL = doc.line(endLine);
      if (info) {
        // Keep the language visible as a small label rather than as ```lang.
        out.push({
          from: openL.from,
          to: openL.to,
          deco: Decoration.replace({ widget: new CodeLabelWidget(info) }),
        });
      } else if (openL.to > openL.from) {
        out.push({ from: openL.from, to: openL.to, deco: Decoration.replace({}) });
      }
      if (endLine !== openLine && closeL.to > closeL.from) {
        out.push({ from: closeL.from, to: closeL.to, deco: Decoration.replace({}) });
      }
      return false;
    },
  });

  out.sort((a, b2) => a.from - b2.from || a.to - b2.to);
  const b = new RangeSetBuilder<Decoration>();
  for (const r of out) b.add(r.from, r.to, r.deco);
  return b.finish();
}

/** The language label drawn where ```lang used to read (D3). */
class CodeLabelWidget extends WidgetType {
  constructor(private readonly lang: string) { super(); }
  eq(other: CodeLabelWidget) { return other.lang === this.lang; }
  toDOM(view: EditorView) {
    const s = view.dom.ownerDocument.createElement('span');
    s.className = 'cm-mdCodeLang';
    s.textContent = this.lang;
    return s;
  }
  ignoreEvent() { return false; }
}

const fenceField = StateField.define<DecorationSet>({
  create: (state) => buildFenceDecorations(state),
  update(deco, tr) {
    const toggled = tr.effects.some((e) => e.is(revealFence) || e.is(collapseFence));
    if (!tr.docChanged && !toggled) return deco.map(tr.changes);
    return buildFenceDecorations(tr.state);
  },
  provide: (f) => EditorView.decorations.from(f),
});

export interface ProseCanvasHandle {
  /** [from, to) of the current selection, in source offsets. */
  selection: () => [number, number];
  /**
   * The document as the VIEW currently holds it (ADR-572 D18).
   *
   * Every other insert computes from React's `text`, which is safe because the
   * gesture is synchronous. The CSV insert awaits a fetch, and the member can
   * type while it is in flight — applying the string captured at pick time
   * would delete those keystrokes (the D12 stale-prop shape). This reads the
   * truth at apply time instead.
   */
  text: () => string;
  /** Replace the whole document and place the selection — the toolbar path. */
  apply: (text: string, from: number, to: number) => void;
  /** Reveal a source range (outline jump, find). */
  /**
   * Move to a source position and scroll it into view — a NAVIGATION, so the
   * caret lands COLLAPSED (ADR-572 D20). See the implementation for why this
   * does not select the range it was pointed at.
   */
  reveal: (from: number, to: number) => void;
  focus: () => void;
  /** Delete a source range (the slash run, once a pick lands). */
  deleteRange: (from: number, to: number) => void;
  /** Viewport coordinates of a source offset, for anchoring the palette. */
  coordsAt: (pos: number) => { left: number; top: number; bottom: number } | null;
}

/**
 * The `/` run behind the caret, or null (ADR-572 D14).
 *
 * A run is live only when `/` sits at the very start of a line or after
 * whitespace — otherwise `and/or` would open a palette mid-word. Any space in
 * the filter closes it: a slash command is one token, and "/table of contents"
 * is prose the member is typing, not a filter that happens to match nothing.
 */
export interface SlashRun {
  /** Offset of the `/` itself — the start of the range a pick replaces. */
  from: number;
  /** The caret; the run is `[from, to)`. */
  to: number;
  /** What was typed after the `/`. */
  filter: string;
}

export function readSlashRun(doc: string, caret: number): SlashRun | null {
  let i = caret - 1;
  while (i >= 0) {
    const ch = doc[i];
    if (ch === '/') break;
    // A newline or a space ends the search: the run must be one token, and a
    // `/` on a previous line is not behind this caret in any useful sense.
    if (ch === '\n' || ch === ' ' || ch === '\t') return null;
    i--;
  }
  if (i < 0 || doc[i] !== '/') return null;
  const before = i === 0 ? '\n' : doc[i - 1];
  if (before !== '\n' && before !== ' ' && before !== '\t') return null;
  return { from: i, to: caret, filter: doc.slice(i + 1, caret) };
}

export function ProseCanvas({
  value,
  onChange,
  onSlashRun,
  handleRef,
  zoom = 1,
  className,
}: {
  value: string;
  onChange: (next: string) => void;
  /** The `/` run behind the caret, or null when there is none (D14). */
  onSlashRun?: (run: SlashRun | null) => void;
  handleRef?: (h: ProseCanvasHandle | null) => void;
  zoom?: number;
  className?: string;
}) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);
  // The change handler is read through a ref so the extension list stays
  // stable — rebuilding the EditorState on every render would drop the caret.
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const onCaretRef = useRef(onSlashRun);
  onCaretRef.current = onSlashRun;

  /**
   * Every document this canvas has EMITTED since the last external write —
   * the echo guard (ADR-572 D12).
   *
   * A SET, not a single "last emitted" value. The first spelling held only the
   * most recent emission and still lost the keystroke: by the time React
   * re-rendered with the toolbar's queued value, the member's own typing had
   * already overwritten the ref, so the stale prop no longer matched and was
   * applied anyway. Any prop we have ever produced is an echo, however many
   * edits ago — cleared on a genuine external write, so it cannot grow without
   * bound during a session.
   */
  const emittedRef = useRef<Set<string>>(new Set([value]));

  const extensions = useMemo<Extension[]>(
    () => [
      history(),
      drawSelection(),
      rectangularSelection(),
      highlightActiveLine(),
      highlightSelectionMatches(),
      // `codeLanguages` is deliberately omitted: a fenced block highlights as
      // plain text rather than pulling a language bundle per fence.
      markdown({ base: markdownLanguage }),
      syntaxHighlighting(PROSE_HIGHLIGHT),
      // Hides the markdown marks off the line being edited (D13) — must come
      // BEFORE tableRows so a table's own pipes are never hidden.
      livePreview,
      // Renders tables as real <table> elements (D15) — a StateField, because
      // CodeMirror forbids block decorations from a plugin.
      tableField,
      // ⭐ ADR-590 D3 — the fences render as themselves: a mermaid diagram, a
      // code block with its language. Also a StateField, for the same reason
      // the table is one (block decorations may not come from a plugin).
      revealedFences,
      fenceField,
      PROSE_THEME,
      EditorView.lineWrapping,
      keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap]),
      EditorView.updateListener.of((u) => {
        if (u.docChanged) {
          const next = u.state.doc.toString();
          // Record what we EMIT, so the echo arriving back as `value` a render
          // later is recognised as ours and not re-applied over newer typing
          // (ADR-572 D12).
          emittedRef.current.add(next);
          onChangeRef.current(next);
        }
        // The slash palette lives in the SURFACE, but only the view knows the
        // caret — so every doc/selection change reports the run behind it
        // (ADR-572 D14). Read here rather than in the surface because the
        // surface's `text` lags a render, and a palette anchored to stale
        // coordinates points at the wrong line.
        if (u.docChanged || u.selectionSet) {
          const sel = u.state.selection.main;
          onCaretRef.current?.(
            sel.empty ? readSlashRun(u.state.doc.toString(), sel.head) : null,
          );
        }
      }),
    ],
    [],
  );

  // Mount once. A callback ref would re-run on every render; the effect keys on
  // nothing so the view survives parent re-renders and keeps the caret.
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const view = new EditorView({
      state: EditorState.create({ doc: value, extensions }),
      parent: host,
    });
    viewRef.current = view;

    const handle: ProseCanvasHandle = {
      selection: () => {
        const r = view.state.selection.main;
        return [r.from, r.to];
      },
      text: () => view.state.doc.toString(),
      apply: (text, from, to) => {
        // A MINIMAL change, not a whole-document replace (ADR-572 D12). The
        // edit functions return a full new string, but dispatching that as
        // `{from: 0, to: doc.length}` makes every toolbar press one
        // document-sized undo step and rewrites lines the edit never touched.
        // Diffing to the changed span keeps undo per-edit and leaves the rest
        // of the document — and any decoration over it — untouched.
        const cur = view.state.doc.toString();
        if (cur === text) {
          view.dispatch({ selection: { anchor: from, head: to } });
          view.focus();
          return;
        }
        let head = 0;
        const max = Math.min(cur.length, text.length);
        while (head < max && cur[head] === text[head]) head++;
        let tail = 0;
        while (
          tail < max - head &&
          cur[cur.length - 1 - tail] === text[text.length - 1 - tail]
        ) {
          tail++;
        }
        view.dispatch({
          changes: {
            from: head,
            to: cur.length - tail,
            insert: text.slice(head, text.length - tail),
          },
          selection: { anchor: from, head: to },
          // A toolbar press is ONE deliberate act, so it gets its own history
          // entry. Without this, `history()` coalesces it with the typing that
          // follows within ~500ms, and a single ⌘Z swallows both the character
          // just typed and the button press before it.
          annotations: isolateHistory.of('full'),
        });
        view.focus();
      },
      reveal: (from, to) => {
        // ⭐ ADR-572 D20 — GOING somewhere is not SELECTING something.
        //
        // This used to dispatch `{anchor: from, head: to}`, leaving a live
        // range in a focused editor. Two things were wrong with that, and the
        // second is the serious one:
        //
        //   - the range was MIS-MEASURED. Its only caller sized it by the
        //     outline's stripped LABEL (`plain()` drops `#`, `**`, link
        //     targets) against an offset into the RAW line, so it always fell
        //     short by the markup — visibly ending mid-word, and further off
        //     the more markup a heading carried.
        //   - a focused range is a PENDING DELETE. The next keystroke replaces
        //     it. Clicking the outline armed a destructive state, so a member
        //     who navigated and then typed lost the heading.
        //
        // Fixing only the arithmetic would have kept the second defect and
        // made it harder to see, since a correctly-sized selection looks
        // deliberate. So the gesture is answered instead: navigation puts the
        // caret at the destination and scrolls, which is what Studio's own
        // outline does (`FlowEditor` → `TextSelection.near`, never a range).
        //
        // `to` stays in the signature: it is where the destination ENDS, which
        // is what `scrollIntoView` needs to keep a long heading fully on
        // screen rather than parking its first line at the centre.
        const at = Math.min(from, view.state.doc.length);
        view.dispatch({
          selection: { anchor: at, head: at },
          effects: EditorView.scrollIntoView(
            EditorSelection.range(at, Math.min(Math.max(to, from), view.state.doc.length)),
            { y: 'center' },
          ),
        });
        view.focus();
      },
      focus: () => view.focus(),
      deleteRange: (from, to) => {
        view.dispatch({ changes: { from, to, insert: '' }, selection: { anchor: from } });
        view.focus();
      },
      coordsAt: (pos) => {
        const c = view.coordsAtPos(pos);
        return c ? { left: c.left, top: c.top, bottom: c.bottom } : null;
      },
    };
    handleRef?.(handle);

    return () => {
      handleRef?.(null);
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * The last document this canvas EMITTED. Anything else arriving as `value`
   * is genuinely external (ADR-572 D12).
   *
   * ## The defect this fixes — typing after a toolbar insert was destroyed
   *
   * The old guard was `if (current === value) return`, i.e. "push it in
   * whenever the prop differs from the doc". That cannot tell an EXTERNAL
   * write from a STALE RENDER of the member's own text, and after a toolbar
   * insert the two are guaranteed to diverge:
   *
   *   1. the toolbar dispatches the edit → doc is `"abc\n- "`, and the
   *      update listener fires `onChange`, so a `setText` is queued;
   *   2. the member immediately types `x` → doc is `"abc\n- x"`;
   *   3. React re-renders with the QUEUED value, `"abc\n- "`;
   *   4. `current !== value`, so this effect dispatched the stale prop and
   *      **deleted the typed character**, snapping the caret back.
   *
   * The member sees: press a toolbar button, type, and the text vanishes onto
   * the previous line. Reproduced against a real `EditorView`; the fix is to
   * compare against what this canvas last emitted rather than against the doc,
   * so an echo of our own text is recognised and ignored.
   */
  // External changes (a load, a lane write, a conflict resolution) are pushed
  // in as a transaction — never by recreating the state, which would lose the
  // caret and the undo history.
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    // An echo of something we emitted — the member has simply typed on since.
    if (emittedRef.current.has(value)) return;
    const current = view.state.doc.toString();
    if (current === value) return;
    // A genuine external write: this is the new baseline, so the echo set is
    // reset to it rather than accumulating across the session.
    emittedRef.current = new Set([value]);
    // Preserve the caret across an external replace: hold its offset from the
    // END of the document, so text arriving above it does not strand it.
    const sel = view.state.selection.main;
    const tailOffset = current.length - sel.head;
    const nextHead = Math.max(0, Math.min(value.length, value.length - tailOffset));
    view.dispatch({
      changes: { from: 0, to: current.length, insert: value },
      selection: { anchor: nextHead, head: nextHead },
    });
  }, [value]);

  return (
    <div
      ref={hostRef}
      // `zoom` (not transform) so the reading column reflows at its scaled
      // measure instead of overflowing — the ADR-572 D2 rule.
      style={zoom === 1 ? undefined : { zoom }}
      className={cn('min-h-0 flex-1 overflow-hidden', className)}
    />
  );
}
