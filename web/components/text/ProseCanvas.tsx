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
 * ## Live preview (ADR-572 D13) — and a claim this file used to make wrongly
 *
 * The marks are **hidden off the line being edited** and revealed on it, the
 * Obsidian "live preview" face. This header previously called the visible
 * marks an "honest limitation", asserting that hiding them needed the
 * node↔offset map ADR-456 D1 bans. **That was wrong** — and it was the same
 * misreading D8 had just corrected one section above.
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
  // The MARKS themselves — dimmed on the line being edited, and HIDDEN
  // elsewhere by the `livePreview` plugin (D13). This rule is what the member
  // sees when a line is active and its source is revealed for editing.
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
 * ## Why "except on the active line"
 *
 * Hiding marks unconditionally (Typora's default) means editing a heading or a
 * link while unable to see the syntax you are editing, and a malformed link
 * reads as plain text. Revealing the marks on the line the caret occupies is
 * the Obsidian "live preview" behaviour: the document reads as a document, and
 * the moment you enter a line its source appears so it can be edited honestly.
 * The operator asked for "closest to Notion" — this is the closest reachable
 * without adopting the block model the format cannot carry.
 */
const REVEALED_ON_ACTIVE_LINE = new Set([
  'HeaderMark',
  'EmphasisMark',
  'StrikethroughMark',
  'CodeMark',
  'QuoteMark',
  'LinkMark',
  'URL',
]);

const livePreview = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;
    constructor(view: EditorView) {
      this.decorations = buildPreviewDecorations(view);
    }
    update(u: ViewUpdate) {
      // `selectionSet` matters as much as `docChanged`: moving the caret onto
      // a line must reveal that line's marks.
      if (u.docChanged || u.selectionSet || u.viewportChanged) {
        this.decorations = buildPreviewDecorations(u.view);
      }
    }
  },
  { decorations: (v) => v.decorations },
);

function buildPreviewDecorations(view: EditorView): DecorationSet {
  const { state } = view;
  const doc = state.doc;
  // Every line touched by a selection stays in source form, so a multi-line
  // selection does not half-hide the text being worked on.
  const active = new Set<number>();
  for (const r of state.selection.ranges) {
    const first = doc.lineAt(r.from).number;
    const last = doc.lineAt(r.to).number;
    for (let n = first; n <= last; n++) active.add(n);
  }

  // Collected then sorted: `RangeSetBuilder` requires ascending order, and the
  // tree does not guarantee it across nested inline nodes.
  const marks: Array<[number, number]> = [];
  for (const { from, to } of view.visibleRanges) {
    syntaxTree(state).iterate({
      from,
      to,
      enter(node) {
        if (!REVEALED_ON_ACTIVE_LINE.has(node.name)) return;
        if (active.has(doc.lineAt(node.from).number)) return;
        let end = node.to;
        // `# ` — swallow the space too, or the heading keeps a hanging indent.
        if (node.name === 'HeaderMark' && doc.sliceString(end, end + 1) === ' ') {
          end += 1;
        }
        if (end > node.from) marks.push([node.from, end]);
      },
    });
  }
  marks.sort((a, b) => a[0] - b[0] || a[1] - b[1]);

  const b = new RangeSetBuilder<Decoration>();
  let prevEnd = -1;
  for (const [from, to] of marks) {
    if (from < prevEnd) continue; // skip overlaps (nested inline marks)
    b.add(from, to, Decoration.replace({}));
    prevEnd = to;
  }
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
      // Draws the table grid the highlight layer structurally cannot (D10).
      tableRows,
      PROSE_THEME,
      EditorView.lineWrapping,
      keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap]),
      EditorView.updateListener.of((u) => {
        if (!u.docChanged) return;
        const next = u.state.doc.toString();
        // Record what we EMIT, so the echo arriving back as `value` a render
        // later is recognised as ours and not re-applied over newer typing
        // (ADR-572 D12).
        emittedRef.current.add(next);
        onChangeRef.current(next);
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
