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
 * ## The honest limitation
 *
 * The markdown marks stay **visible** — `## Heading` renders large and serif
 * with a dimmed `##` still present, the way Obsidian and iA Writer do it.
 * Hiding the marks entirely requires knowing which rendered node corresponds to
 * which source range, i.e. the node↔offset map that is the banned shape. Named
 * here so the absence does not read as an oversight.
 */

import { useEffect, useMemo, useRef } from 'react';
import { EditorState, RangeSetBuilder, type Extension } from '@codemirror/state';
import {
  Decoration,
  EditorView,
  ViewPlugin,
  keymap,
  drawSelection,
  highlightActiveLine,
  rectangularSelection,
  type DecorationSet,
  type ViewUpdate,
} from '@codemirror/view';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
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
  // The MARKS themselves — dimmed, never hidden. Hiding them is the banned
  // shape (it needs the node↔offset map); dimming is pure presentation.
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
    padding: '0 1.5rem',
    caretColor: 'var(--foreground, #111)',
  },
  '.cm-line': { padding: '0' },
  '.cm-activeLine': { backgroundColor: 'transparent' },
  '.cm-selectionBackground, ::selection': { backgroundColor: 'rgba(120,150,255,0.22)' },
  '&.cm-focused .cm-selectionBackground': { backgroundColor: 'rgba(120,150,255,0.28)' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--foreground, #111)', borderLeftWidth: '2px' },
  // Find/replace match highlighting (the @codemirror/search extension).
  '.cm-selectionMatch': { backgroundColor: 'rgba(250,200,80,0.30)' },
  '.cm-searchMatch': { backgroundColor: 'rgba(250,200,80,0.35)' },
  '.cm-searchMatch.cm-searchMatch-selected': { backgroundColor: 'rgba(250,160,40,0.55)' },
  '.cm-placeholder': { color: 'var(--muted-foreground, #888)', fontStyle: 'italic' },

  // ── Table rows (ADR-572 D10) ────────────────────────────────────────────
  // Syntax highlighting alone cannot make a table read as a table: it can
  // colour the pipes but not draw the grid, so a table rendered as raw
  // punctuation on the canvas while the print sheet and the landing thumbnail
  // drew a real bordered table. This is a LINE decoration, applied to the
  // lines the parser identifies as table rows — presentation only, computed
  // from offsets, nothing written into the document.
  //
  // Mono for the cells, so the pipes of consecutive rows line up vertically
  // and the columns read as columns while you type. That is the honest
  // canvas-grade answer: an aligned source table, not a rendered one.
  '.cm-line.cm-tableRow': {
    fontFamily: FACE.mono,
    fontSize: FACE.codeSize,
    backgroundColor: 'var(--table-tint, rgba(128,128,128,0.045))',
    borderLeft: `2px solid ${TABLE.borderColor}`,
    paddingLeft: '0.5em',
  },
  '.cm-line.cm-tableRow-first': {
    borderTop: `1px solid ${TABLE.borderColor}`,
    paddingTop: '0.15em',
  },
  '.cm-line.cm-tableRow-last': {
    borderBottom: `1px solid ${TABLE.borderColor}`,
    paddingBottom: '0.15em',
  },
  // The header row of a table carries the header weight the rendered face
  // gives its `<th>`.
  '.cm-line.cm-tableRow-header': { fontWeight: TABLE.headerWeight },
});

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
const tableRows = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;
    constructor(view: EditorView) {
      this.decorations = buildTableDecorations(view);
    }
    update(u: ViewUpdate) {
      if (u.docChanged || u.viewportChanged) {
        this.decorations = buildTableDecorations(u.view);
      }
    }
  },
  { decorations: (v) => v.decorations },
);

function buildTableDecorations(view: EditorView): DecorationSet {
  const b = new RangeSetBuilder<Decoration>();
  const doc = view.state.doc;
  for (const { from, to } of view.visibleRanges) {
    syntaxTree(view.state).iterate({
      from,
      to,
      enter(node) {
        if (node.name !== 'Table') return;
        const first = doc.lineAt(node.from).number;
        const last = doc.lineAt(node.to).number;
        for (let n = first; n <= last; n++) {
          const line = doc.line(n);
          // The delimiter row (`| --- |`) is structural punctuation: it stays
          // in the grid but is dimmed by the `contentSeparator` tag rule.
          const cls = [
            'cm-tableRow',
            n === first ? 'cm-tableRow-first cm-tableRow-header' : '',
            n === last ? 'cm-tableRow-last' : '',
          ]
            .filter(Boolean)
            .join(' ');
          b.add(line.from, line.from, Decoration.line({ class: cls }));
        }
      },
    });
  }
  return b.finish();
}

export interface ProseCanvasHandle {
  /** [from, to) of the current selection, in source offsets. */
  selection: () => [number, number];
  /** Replace the whole document and place the selection — the toolbar path. */
  apply: (text: string, from: number, to: number) => void;
  /** Reveal a source range (outline jump, find). */
  reveal: (from: number, to: number) => void;
  focus: () => void;
}

export function ProseCanvas({
  value,
  onChange,
  handleRef,
  zoom = 1,
  className,
}: {
  value: string;
  onChange: (next: string) => void;
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
      // Draws the table grid the highlight layer structurally cannot (D10).
      tableRows,
      PROSE_THEME,
      EditorView.lineWrapping,
      keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap]),
      EditorView.updateListener.of((u) => {
        if (u.docChanged) onChangeRef.current(u.state.doc.toString());
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
      apply: (text, from, to) => {
        view.dispatch({
          changes: { from: 0, to: view.state.doc.length, insert: text },
          selection: { anchor: from, head: to },
        });
        view.focus();
      },
      reveal: (from, to) => {
        view.dispatch({
          selection: { anchor: from, head: to },
          effects: EditorView.scrollIntoView(from, { y: 'center' }),
        });
        view.focus();
      },
      focus: () => view.focus(),
    };
    handleRef?.(handle);

    return () => {
      handleRef?.(null);
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // External changes (a load, a lane write, a conflict resolution) are pushed
  // in as a transaction — never by recreating the state, which would lose the
  // caret and the undo history. Guarded on inequality so the member's own
  // keystrokes don't round-trip back through here.
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current === value) return;
    view.dispatch({ changes: { from: 0, to: current.length, insert: value } });
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
