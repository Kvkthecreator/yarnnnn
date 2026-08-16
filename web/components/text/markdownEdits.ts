/**
 * Markdown source edits — the honest half of Docs' insert menu (ADR-572).
 *
 * ## What separates this from a block insert
 *
 * Docs' slash palette and `StudioBlockInsertMenu` insert BLOCKS: a `<section
 * data-block="…" data-block-id="…">` node into a structured document. That
 * mechanism is forbidden here (ADR-456 D1) and none of it appears below.
 *
 * These functions take a string and a caret range and return a string and a
 * caret range. They wrap characters in other characters. The result is the
 * same plain markdown a member would have typed by hand, and a connector
 * reading the file back cannot tell a toolbar press from a keystroke — which
 * is the exact property that makes them legal here.
 *
 * Pure and total: no React, no DOM, no I/O. That is deliberate — the gate
 * transpiles and CALLS them, because a gate that greps for a symbol proves
 * nothing about behaviour (the lesson this arc paid for twice).
 */

export interface Edit {
  /** The full new source. */
  text: string;
  /** Where the caret/selection lands afterwards. */
  selectionStart: number;
  selectionEnd: number;
}

/** The span of whole lines covering [start, end). */
function lineSpan(text: string, start: number, end: number): [number, number] {
  const from = text.lastIndexOf('\n', start - 1) + 1;
  let to = text.indexOf('\n', end);
  if (to === -1) to = text.length;
  return [from, to];
}

/**
 * Wrap the selection in a marker, or unwrap it if already wrapped (a toggle,
 * the way ⌘B behaves in every editor). With no selection, insert the marker
 * pair and place the caret between them so typing continues inside.
 */
export function toggleWrap(text: string, start: number, end: number, marker: string): Edit {
  const sel = text.slice(start, end);
  const m = marker.length;

  // Already wrapped INSIDE the selection → strip.
  if (sel.length >= 2 * m && sel.startsWith(marker) && sel.endsWith(marker)) {
    const inner = sel.slice(m, -m);
    return {
      text: text.slice(0, start) + inner + text.slice(end),
      selectionStart: start,
      selectionEnd: start + inner.length,
    };
  }
  // Wrapped just OUTSIDE the selection → strip those.
  if (text.slice(start - m, start) === marker && text.slice(end, end + m) === marker) {
    return {
      text: text.slice(0, start - m) + sel + text.slice(end + m),
      selectionStart: start - m,
      selectionEnd: start - m + sel.length,
    };
  }
  const wrapped = marker + sel + marker;
  return {
    text: text.slice(0, start) + wrapped + text.slice(end),
    selectionStart: start + m,
    selectionEnd: start + m + sel.length,
  };
}

/**
 * Set (or clear) the ATX heading level on every line the selection touches.
 * Re-applying the same level clears it — the Docs "turn into" reflex, spelled
 * in characters.
 */
export function toggleHeading(text: string, start: number, end: number, level: number): Edit {
  const [from, to] = lineSpan(text, start, end);
  const prefix = '#'.repeat(level) + ' ';
  const lines = text.slice(from, to).split('\n');
  const allAtLevel = lines.every((l) => new RegExp(`^ {0,3}#{${level}} `).test(l));
  const next = lines
    .map((l) => {
      const bare = l.replace(/^ {0,3}#{1,6}\s+/, '');
      return allAtLevel ? bare : prefix + bare;
    })
    .join('\n');
  return {
    text: text.slice(0, from) + next + text.slice(to),
    selectionStart: from,
    selectionEnd: from + next.length,
  };
}

/**
 * Toggle a list over the selected lines. `ordered` renumbers from 1 — a list
 * whose numbers are all "1." is a markdown idiom, but a member pressing the
 * button expects to see 1, 2, 3.
 */
export function toggleList(text: string, start: number, end: number, ordered: boolean): Edit {
  const [from, to] = lineSpan(text, start, end);
  const lines = text.slice(from, to).split('\n');
  const marked = ordered
    ? lines.every((l) => /^ {0,3}\d+\.\s+/.test(l) || !l.trim())
    : lines.every((l) => /^ {0,3}[-*+]\s+/.test(l) || !l.trim());
  let n = 0;
  const next = lines
    .map((l) => {
      const bare = l.replace(/^ {0,3}(?:[-*+]|\d+\.)\s+/, '');
      if (marked) return bare;
      if (!bare.trim()) return bare;
      n += 1;
      return ordered ? `${n}. ${bare}` : `- ${bare}`;
    })
    .join('\n');
  return {
    text: text.slice(0, from) + next + text.slice(to),
    selectionStart: from,
    selectionEnd: from + next.length,
  };
}

/**
 * Toggle a GFM task list (`- [ ] item`) over the selected lines.
 *
 * This is Docs' `checklist` block kind, which Docs persists as
 * `<ul data-block="checklist">` plus a kernel CSS rule painting a `☐`
 * pseudo-element. Markdown expresses the same thing natively, and `remark-gfm`
 * — already in the shared renderer — renders it as real checkboxes. So the
 * affordance survives the medium translation with no annotation at all: the
 * bytes are `- [ ] `, which any connector reads back as a task list.
 *
 * Toggling off strips the marker AND the box, returning ordinary lines —
 * the round-trip property every function in this file holds to.
 */
export function toggleChecklist(text: string, start: number, end: number): Edit {
  const [from, to] = lineSpan(text, start, end);
  const lines = text.slice(from, to).split('\n');
  const checked = lines.every((l) => /^ {0,3}[-*+]\s+\[[ xX]\]\s?/.test(l) || !l.trim());
  const next = lines
    .map((l) => {
      if (checked) return l.replace(/^( {0,3})[-*+]\s+\[[ xX]\]\s?/, '$1');
      if (!l.trim()) return l;
      // An existing bullet becomes a task; a bare line gets both.
      const bare = l.replace(/^ {0,3}(?:[-*+]|\d+\.)\s+/, '');
      return `- [ ] ${bare}`;
    })
    .join('\n');
  return {
    text: text.slice(0, from) + next + text.slice(to),
    selectionStart: from,
    selectionEnd: from + next.length,
  };
}

/** Toggle a `> ` blockquote over the selected lines. */
export function toggleQuote(text: string, start: number, end: number): Edit {
  const [from, to] = lineSpan(text, start, end);
  const lines = text.slice(from, to).split('\n');
  const quoted = lines.every((l) => /^ {0,3}> ?/.test(l) || !l.trim());
  const next = lines
    .map((l) => (quoted ? l.replace(/^ {0,3}> ?/, '') : l.trim() ? `> ${l}` : l))
    .join('\n');
  return {
    text: text.slice(0, from) + next + text.slice(to),
    selectionStart: from,
    selectionEnd: from + next.length,
  };
}

/**
 * A link. With a selection, the selected words become the link TEXT and the
 * caret lands in the empty target — the member already said what it's called,
 * so the only thing left to type is where it goes.
 */
export function insertLink(text: string, start: number, end: number): Edit {
  const sel = text.slice(start, end) || 'link text';
  const snippet = `[${sel}]()`;
  const caret = start + snippet.length - 1; // inside the ()
  return {
    text: text.slice(0, start) + snippet + text.slice(end),
    selectionStart: caret,
    selectionEnd: caret,
  };
}

/**
 * Insert a GFM table skeleton on its own lines, caret in the first header
 * cell. Blank-line padding is added only where it is missing, so pressing the
 * button twice does not accumulate whitespace.
 */
export function insertTable(text: string, start: number, end: number): Edit {
  const before = text.slice(0, start);
  const after = text.slice(end);
  const lead = before && !before.endsWith('\n\n') ? (before.endsWith('\n') ? '\n' : '\n\n') : '';
  const tail = after && !after.startsWith('\n') ? '\n' : '';
  const table =
    '| Column | Column |\n' +
    '| --- | --- |\n' +
    '|  |  |\n';
  const snippet = lead + table + tail;
  const caret = start + lead.length + 2; // just inside the first header cell
  return {
    text: before + snippet + after,
    selectionStart: caret,
    selectionEnd: caret + 6, // select the word "Column"
  };
}

/** A thematic break on its own line. */
export function insertRule(text: string, start: number, end: number): Edit {
  const before = text.slice(0, start);
  const after = text.slice(end);
  const lead = before && !before.endsWith('\n\n') ? (before.endsWith('\n') ? '\n' : '\n\n') : '';
  const snippet = `${lead}---\n\n`;
  const caret = before.length + snippet.length;
  return { text: before + snippet + after, selectionStart: caret, selectionEnd: caret };
}

/** The character offset at which 0-based `line` begins. */
export function offsetOfLine(text: string, line: number): number {
  let off = 0;
  for (let i = 0; i < line; i++) {
    const nl = text.indexOf('\n', off);
    if (nl === -1) return off;
    off = nl + 1;
  }
  return off;
}
