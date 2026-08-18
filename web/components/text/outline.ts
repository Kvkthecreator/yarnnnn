/**
 * The prose outline — a document's headings, read back in order (ADR-572).
 *
 * ## The addressing rule that keeps this legal
 *
 * Docs derives the same list, but addresses each heading by its
 * `data-block-id` (`StudioDesignTab.tsx::walkOutline`) — the block-grade
 * mechanism ADR-456 D1 forbids Text. So the two outlines look alike and are
 * built on opposite foundations: **this one addresses by SOURCE LINE**.
 *
 * A line number is a coordinate INTO the bytes, not an annotation ON them.
 * Nothing is written, nothing is minted, and the `.md` a connector reads back
 * is byte-identical whether or not this function ever ran. That is what makes
 * an outline a view rather than a block model — and it is why "jump to a
 * heading" can work in the source editor (scroll to a line) without the file
 * ever learning that headings have identity.
 *
 * ## Why a hand-rolled scan and not the markdown AST
 *
 * The renderer's AST gives nodes, not source offsets — mapping back would need
 * exactly the node→offset table this app is not allowed to keep. A line scan
 * answers the only question asked (which line, what level, what text) and
 * cannot drift out of sync with the textarea, because the textarea IS lines.
 */

export interface OutlineEntry {
  /** 0-based index into the source's lines — the address. */
  line: number;
  /** 1–6, the ATX level. Drives indentation, exactly as Docs' `depth` does. */
  level: number;
  /** The heading's text, trailing `#`s and inline markup stripped for reading. */
  text: string;
}

/** ``` or ~~~ opening/closing a fence. Headings inside fences are code. */
const FENCE_RE = /^\s{0,3}(`{3,}|~{3,})/;
/** ATX heading: up to 3 spaces indent, 1–6 `#`, then a space (CommonMark). */
const ATX_RE = /^ {0,3}(#{1,6})\s+(.*)$/;
/** Setext underline: `===` (h1) or `---` (h2) under a non-blank line. */
const SETEXT_RE = /^ {0,3}(=+|-+)\s*$/;
/**
 * A list item: `- `, `* `, `+ `, or `1. ` — INCLUDING an empty one (ADR-575
 * D8.b). The trailing space is optional because `- ` with nothing after it is
 * a real, empty list item, which is exactly the case that broke this.
 */
const LIST_ITEM_RE = /^ {0,3}([-*+]|\d{1,9}[.)])(\s|$)/;

/**
 * Strip the inline markup a heading may carry so the outline row reads as
 * words. Deliberately shallow — this is a LABEL, not a render.
 */
function plain(s: string): string {
  return s
    .replace(/\s+#+\s*$/, '') // closing ATX sequence
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1') // links / images → their text
    .replace(/[*_~`]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Scan markdown source for its headings.
 *
 * Handles both heading forms and skips fenced code — a `# ` inside a fence is
 * a comment in someone's shell snippet, not a section of the document.
 */
export function parseOutline(source: string): OutlineEntry[] {
  const lines = source.split('\n');
  const out: OutlineEntry[] = [];
  let fence: string | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Fence bookkeeping first — everything inside is literal.
    const fenceHit = FENCE_RE.exec(line);
    if (fenceHit) {
      const marker = fenceHit[1][0];
      if (fence === null) fence = marker;
      else if (fence === marker) fence = null;
      continue;
    }
    if (fence !== null) continue;

    const atx = ATX_RE.exec(line);
    if (atx) {
      const text = plain(atx[2]);
      // An empty heading names nothing (Docs' own rule).
      if (text) out.push({ line: i, level: atx[1].length, text });
      continue;
    }

    // Setext: this line is the underline, the PREVIOUS one is the heading.
    //
    // ⭐ ADR-575 D8.b — a LIST is not a heading. Found by driving the canvas:
    // pressing Enter at the end of a bulleted list leaves
    //
    //     - second item
    //     - ⏎
    //
    // and `- ` matched SETEXT_RE, so the outline listed "- second item" as an
    // H2 and the Properties pane counted two headings in a document with one.
    // Measured against @lezer/markdown: the real parser sees THREE list items
    // and ZERO headings there.
    //
    // Both sides of the pair are guarded, because either alone is wrong:
    //   - an underline may not itself be a list item (`- ` continuing a list)
    //   - a heading may not be a list item (a bullet is not a title)
    const setext = SETEXT_RE.exec(line);
    if (setext && i > 0 && !LIST_ITEM_RE.test(line)) {
      const prev = lines[i - 1];
      // Must follow a real paragraph line, and `---` after a blank line is a
      // thematic break, not a heading.
      if (prev.trim() && !ATX_RE.test(prev) && !FENCE_RE.test(prev) && !LIST_ITEM_RE.test(prev)) {
        const text = plain(prev);
        if (text) out.push({ line: i - 1, level: setext[1][0] === '=' ? 1 : 2, text });
      }
    }
  }
  return out;
}

/**
 * Reading time in minutes, at 238 wpm (Brysbaert 2019's silent-reading mean
 * for English prose). Floored at 1 — "0 min read" is not an answer.
 */
export function readingMinutes(wordCount: number): number {
  return Math.max(1, Math.round(wordCount / 238));
}
