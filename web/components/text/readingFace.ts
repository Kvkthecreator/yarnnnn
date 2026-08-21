/**
 * The reading face — ONE declaration, two renderers (ADR-572 D10).
 *
 * ## The defect this exists to make impossible
 *
 * Text renders the same document through two different engines:
 *
 *   - `PROSE_READING_SKIN` (Tailwind typography) → the landing thumbnail and
 *     the print sheet, via `ProseReader` → `MarkdownRenderer`
 *   - `PROSE_HIGHLIGHT` (a CodeMirror `HighlightStyle`) → the canvas you
 *     actually type in
 *
 * Those were two independent, hand-maintained descriptions of one face, and
 * they had already drifted: the skin styled tables, task checkboxes, quotes
 * and rules; the highlight styled none of them. **The card thumbnail and the
 * print output were more styled than the canvas** — the operator found it by
 * inserting a table from the toolbar and seeing it render as raw pipes.
 *
 * A second, subtler cause sat underneath. `@lezer/markdown` styles a table
 * header with the GENERIC `tags.heading` tag, while `PROSE_HIGHLIGHT` mapped
 * `heading1…heading6`. Those are CHILDREN of `heading` (`heading1: t(heading)`),
 * and tag inheritance flows parent→child only — so a rule on the child never
 * matches the parent node, and the table header resolved to no class at all.
 * A rule that LOOKS like it covers the case and doesn't: the same shape as the
 * `prose-sm`/`prose-base` collision this arc already paid for.
 *
 * ## The rule
 *
 * This module owns the numbers. Both renderers import them; neither restates
 * them. Adding a treatment to the reading face means editing one table here,
 * and the gate (§10) renders BOTH engines and compares the result — so a
 * future divergence fails a check rather than shipping as a quiet asymmetry.
 *
 * ## Why this is still not a block model (ADR-456 D1)
 *
 * Nothing here writes. These are presentation constants consumed by a
 * decoration layer and by CSS classes on rendered HTML. No block ids, no
 * `data-*` in the source, no node↔offset map. Delete this file and the `.md`
 * on disk is byte-identical.
 */

/**
 * The document type scale, in `em` so the zoom control scales everything from
 * one place. The rendered skin expresses these as `rem` at a 16px root, which
 * is the same size — the gate asserts the two agree rather than trusting it.
 */
export const HEADING_SCALE = {
  h1: { em: '1.9em', rem: '2rem', weight: '600', leading: '1.2' },
  h2: { em: '1.45em', rem: '1.5rem', weight: '600', leading: '1.3' },
  h3: { em: '1.2em', rem: '1.2rem', weight: '600', leading: '1.35' },
  h4: { em: '1.05em', rem: '1.05rem', weight: '600', leading: '1.4' },
} as const;

/** The serif document face and the mono code face — the app type tokens. */
export const FACE = {
  serif: 'var(--font-serif)',
  mono: 'var(--font-mono)',
  /**
   * The UI face — for CHROME the canvas draws over the document (ADR-590 D3's
   * diagram edit control, a code fence's language label). Never for content:
   * a document is set in `serif`, and anything wearing `ui` is by construction
   * an affordance rather than part of the file.
   */
  ui: 'var(--font-sans)',
  /** Body measure and rhythm, shared by canvas and reader. */
  measure: '46rem',
  /** The canvas's horizontal padding, inside the measure. Declared here rather
   *  than inline so the CHROME above the canvas can compose the same column. */
  gutter: '1.5rem',
  /**
   * The full column the canvas occupies: `measure` + both gutters.
   *
   * The chrome rows (the crumb + name, the Insert toolbar) centre on THIS, so
   * the document's identity and its verbs sit over the document itself. They
   * were flush-left in a full-width row, which meant the file name drifted
   * every time the right pane opened or closed — the page had no stable spine.
   * Google Docs is the reference: the title and the toolbar are centred over
   * the page, and the page does not move when a side panel appears.
   */
  column: '49rem',
  lineHeight: '1.75',
  /** Code renders a shade smaller inside a serif document. */
  codeSize: '0.88em',
  /** Tables read at body size in a document, not at chat size. */
  cellSize: '0.9rem',
} as const;

/**
 * Table treatment. The canvas cannot draw real cell walls (that needs a
 * decoration layer over a parsed grid), but it CAN carry the border colour,
 * the header weight and the delimiter dimming so a table reads as a table
 * rather than as punctuation. The rendered face draws the full grid.
 */
export const TABLE = {
  borderColor: 'var(--table-rule, rgba(128,128,128,0.35))',
  headerWeight: '600',
  cellPadding: '0.35em 0.6em',
} as const;

/**
 * How visible the markdown marks are. Dimmed, never hidden — hiding them needs
 * the banned node↔offset map (ADR-572 §"The honest limitation").
 */
export const MARK_OPACITY = {
  /** `#`, `**`, `>` — the syntax you are allowed to see. */
  syntax: '0.35',
  /** `---`, table pipes — structural punctuation. */
  structural: '0.45',
  /** A URL target beside its link text. */
  url: '0.6',
} as const;
