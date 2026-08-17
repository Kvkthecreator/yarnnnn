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
 * Is every line in this span already carrying the marker?
 *
 * The blank-line clause is why this is a named helper rather than an inline
 * `.every()`. A blank line inside a MULTI-line selection must not veto the
 * "already marked" verdict — you toggle a list off even though the paragraph
 * gap between two items carries no `- `. But when the span is blank ENTIRELY
 * (the member put the caret on an empty line and pressed the button), the
 * permissive clause made `.every()` vacuously true, so the toggle took the
 * UN-mark branch and stripped a marker that was never there. The button did
 * nothing, on precisely the line where pressing a button beats typing `- `.
 *
 * So: a span with no content at all is NOT marked. Found by driving the
 * surface — every gate and `next build` were green over it (ADR-572 D10).
 */
function allLinesMarked(lines: string[], re: RegExp): boolean {
  if (lines.every((l) => !l.trim())) return false;
  return lines.every((l) => re.test(l) || !l.trim());
}

/**
 * Does this gesture mean "start a NEW line here" rather than "convert the line
 * I'm on"? (ADR-572 D11)
 *
 * Docs keeps these as two separate acts — **Insert** mints a new block,
 * **Turn into** converts the current one, and they live in different sections
 * of the Properties pane. Text collapsed them into one toolbar, so a button
 * that reads as *insert* behaved as *turn into*: with the caret resting at the
 * end of a finished paragraph, pressing Quote glued `> ` onto that paragraph
 * instead of opening a quote beneath it. The operator's screenshot shows
 * exactly that — a `> dddd` welded to the end of a body paragraph.
 *
 * Rather than double the toolbar, the CARET disambiguates, which is how
 * Notion and Obsidian read the same gesture:
 *
 *   - a selection, or a caret anywhere INSIDE the line → convert it
 *   - a caret at the END of a non-empty, unmarked line → open a new line
 *   - an empty line → mark it in place (D10's fix; there is nothing to convert)
 *
 * The "unmarked" clause matters: at the end of `- item` the member is
 * continuing a list, and toggling should still turn that item off rather than
 * silently appending a second bullet.
 */
export function shouldOpenNewLine(
  text: string,
  start: number,
  end: number,
  markerRe: RegExp,
): boolean {
  if (start !== end) return false; // a selection always means "convert this"
  const [from, to] = lineSpan(text, start, end);
  const line = text.slice(from, to);
  if (!line.trim()) return false; // empty line → mark in place (D10)
  if (markerRe.test(line)) return false; // already marked → toggle it off
  return start === to; // at the very end of the line → open a new one
}

/** Insert a fresh line carrying `marker` directly below the caret's line. */
function openNewLine(text: string, start: number, end: number, marker: string): Edit {
  const [, to] = lineSpan(text, start, end);
  const snippet = `\n${marker}`;
  const caret = to + snippet.length;
  return {
    text: text.slice(0, to) + snippet + text.slice(to),
    selectionStart: caret,
    selectionEnd: caret,
  };
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
  const prefix = '#'.repeat(level) + ' ';
  if (shouldOpenNewLine(text, start, end, /^ {0,3}#{1,6}\s+/)) {
    return openNewLine(text, start, end, prefix);
  }
  const [from, to] = lineSpan(text, start, end);
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
  const listRe = ordered ? /^ {0,3}\d+\.\s+/ : /^ {0,3}[-*+]\s+/;
  if (shouldOpenNewLine(text, start, end, listRe)) {
    return openNewLine(text, start, end, ordered ? '1. ' : '- ');
  }
  const [from, to] = lineSpan(text, start, end);
  const lines = text.slice(from, to).split('\n');
  const blankSpan = lines.every((l) => !l.trim());
  const marked = allLinesMarked(lines, ordered ? /^ {0,3}\d+\.\s+/ : /^ {0,3}[-*+]\s+/);
  let n = 0;
  const next = lines
    .map((l) => {
      const bare = l.replace(/^ {0,3}(?:[-*+]|\d+\.)\s+/, '');
      if (marked) return bare;
      // A blank line inside a mixed span stays blank (it is the gap between
      // items); a span that is blank THROUGHOUT is the member asking to start
      // a list here, so it gets the marker and the caret.
      if (!bare.trim() && !blankSpan) return bare;
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
  if (shouldOpenNewLine(text, start, end, /^ {0,3}[-*+]\s+\[[ xX]\]\s?/)) {
    return openNewLine(text, start, end, '- [ ] ');
  }
  const [from, to] = lineSpan(text, start, end);
  const lines = text.slice(from, to).split('\n');
  const blankSpan = lines.every((l) => !l.trim());
  const checked = allLinesMarked(lines, /^ {0,3}[-*+]\s+\[[ xX]\]\s?/);
  const next = lines
    .map((l) => {
      if (checked) return l.replace(/^( {0,3})[-*+]\s+\[[ xX]\]\s?/, '$1');
      if (!l.trim() && !blankSpan) return l;
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
  if (shouldOpenNewLine(text, start, end, /^ {0,3}> ?/)) {
    return openNewLine(text, start, end, '> ');
  }
  const [from, to] = lineSpan(text, start, end);
  const lines = text.slice(from, to).split('\n');
  const blankSpan = lines.every((l) => !l.trim());
  const quoted = allLinesMarked(lines, /^ {0,3}> ?/);
  const next = lines
    .map((l) =>
      quoted ? l.replace(/^ {0,3}> ?/, '') : l.trim() || blankSpan ? `> ${l}` : l,
    )
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

/**
 * A fenced code block (ADR-572 D17).
 *
 * Docs has NO code block — `blockRows.tsx` maps a code icon for a registry row
 * that does not exist, so code there is an inline mark plus a `<pre>` that
 * parses as prose. Markdown has had fences since CommonMark, the shared
 * renderer already highlights them, and prose documents routinely quote
 * commands. So this exceeds the reference app rather than matching it —
 * taken because the medium carries it for free.
 */
export function insertFence(text: string, start: number, end: number, lang = ''): Edit {
  const sel = text.slice(start, end);
  const before = text.slice(0, start);
  const after = text.slice(end);
  const lead = before && !before.endsWith('\n\n') ? (before.endsWith('\n') ? '\n' : '\n\n') : '';
  const body = sel || '';
  const snippet = `${lead}\`\`\`${lang}\n${body}\n\`\`\`\n`;
  // With a selection the caret lands after it; with none, inside the fence
  // ready to type.
  const caret = before.length + lead.length + 3 + lang.length + 1 + body.length;
  return { text: before + snippet + after, selectionStart: caret, selectionEnd: caret };
}

/**
 * A mermaid diagram — a fenced block the shared renderer ALREADY paints
 * (`MermaidBlock`), which Insert simply never offered (ADR-572 D17).
 *
 * The whole diagram is text in the file, so a connector reads and edits it as
 * source. That is the property Docs' `chart` block lacks: a chart there is an
 * empty `<div data-ref="…csv">` whose bars are manufactured at render time.
 */
export function insertMermaid(text: string, start: number, end: number): Edit {
  const before = text.slice(0, start);
  const after = text.slice(end);
  const lead = before && !before.endsWith('\n\n') ? (before.endsWith('\n') ? '\n' : '\n\n') : '';
  const body = 'graph TD\n  A[Start] --> B[Next]';
  const snippet = `${lead}\`\`\`mermaid\n${body}\n\`\`\`\n`;
  const caret = before.length + lead.length + 11; // just inside, on the first line
  return {
    text: before + snippet + after,
    selectionStart: caret,
    selectionEnd: caret + body.length,
  };
}

/**
 * An image, by workspace PATH (ADR-572 D17).
 *
 * `![alt](path)` — the native form, and the only one that keeps the document
 * portable. Docs writes `<figure data-block="figure"><img data-ref="…"
 * data-ref-rev="…">`, which pins the cited revision but is unreadable as
 * markdown and, being `data-*` on a minted element, is the shape ADR-456 D1
 * forbids here.
 *
 * **The pin is the deliberate loss.** Docs can fall back to a cited revision
 * when an image moves; markdown has nowhere to keep a revision id, so a moved
 * image renders as "not found" and names the path. Recorded rather than
 * worked around: the alternative is HTML in the file.
 */
export function insertImage(text: string, start: number, end: number, path: string, alt = ''): Edit {
  const before = text.slice(0, start);
  const after = text.slice(end);
  const lead = before && !before.endsWith('\n\n') ? (before.endsWith('\n') ? '\n' : '\n\n') : '';
  const label = alt || path.split('/').pop()?.replace(/\.[^.]+$/, '') || 'image';
  const snippet = `${lead}![${label}](${path})\n`;
  const caret = before.length + snippet.length;
  return { text: before + snippet + after, selectionStart: caret, selectionEnd: caret };
}

/**
 * Parse CSV into rows of cells (ADR-572 D18).
 *
 * Quote-aware, because a naive `split(',')` corrupts exactly the data most
 * worth tabulating: `"Kim, Kevin"` becomes two cells and every column after it
 * shifts. Handles quoted commas, quoted NEWLINES (a cell may span source
 * lines), and the `""` escape for a literal quote.
 *
 * Two parsers for this already existed in the tree — `viewers/projection.ts`
 * (line-split, so a quoted newline breaks it) and `StringsSurface.tsx` (this
 * shape, but private to a component file). This is the Strings shape, lifted
 * into the pure module where the gate can CALL it, and re-exported to Strings
 * so a third copy is not created. The projection one is left alone: it feeds
 * `csvToTableHtml` for the Docs artifact path, which this app does not use.
 */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { cell += '"'; i++; }
        else inQuotes = false;
      } else cell += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); cell = '';
      if (row.some((v) => v.trim() !== '')) rows.push(row);
      row = [];
    } else cell += c;
  }
  row.push(cell);
  if (row.some((v) => v.trim() !== '')) rows.push(row);
  return rows;
}

/**
 * Escape one cell for a GFM table row.
 *
 * A `|` inside a cell ENDS the cell — so an unescaped pipe silently splits one
 * column into two and knocks every later column out of alignment. A newline
 * inside a quoted CSV cell ends the ROW for the same reason. Both are folded
 * rather than dropped: the data stays visible and the grid stays intact.
 */
function csvCellToMarkdown(cell: string): string {
  return cell.trim().replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
}

/** How many data rows a snapshot writes before it stops. */
export const CSV_SNAPSHOT_ROW_CAP = 200;

export interface CsvSnapshot {
  /** The GFM table (header + delimiter + body), newline-terminated. */
  table: string;
  /** Data rows written (excludes the header). */
  rows: number;
  /** Data rows in the source that were NOT written, because of the cap. */
  omitted: number;
}

/**
 * Render CSV as a GFM table — rows as REAL TEXT (ADR-572 D18).
 *
 * This is the whole reason a CSV table is legal in this app while Docs' is
 * not. Docs writes `<div data-block="table" data-ref="…/data.csv"></div>` —
 * an EMPTY element whose rows are manufactured at render time from a separate
 * file, so a connector reading the artifact gets a container with no data in
 * it (a named reason ADR-574 paused Docs). Here the numbers are in the `.md`:
 * ChatGPT reads them, `git diff` shows them changing, and any markdown tool
 * renders a table because it IS one.
 *
 * The trade this makes, stated so it is not mistaken for an oversight: the
 * data is a SNAPSHOT and does not track the source. That is why the caller
 * writes a provenance line above it (`csvSourceNote`) — the freeze is only
 * dishonest if the document does not admit to it.
 *
 * Ragged rows are padded to the header's width rather than rejected: a short
 * row is a real thing in real CSV, and a table that renders is worth more than
 * a refusal that does not.
 */
export function csvToMarkdownTable(csv: string, cap = CSV_SNAPSHOT_ROW_CAP): CsvSnapshot {
  const all = parseCsv(csv);
  if (all.length === 0) return { table: '', rows: 0, omitted: 0 };
  const [head, ...body] = all;
  const width = Math.max(1, head.length);
  const kept = body.slice(0, cap);
  const line = (cells: string[]) => {
    const padded = Array.from({ length: width }, (_, i) => csvCellToMarkdown(cells[i] ?? ''));
    return `| ${padded.join(' | ')} |`;
  };
  const rows = [
    line(head),
    `| ${Array.from({ length: width }, () => '---').join(' | ')} |`,
    ...kept.map(line),
  ];
  return { table: `${rows.join('\n')}\n`, rows: kept.length, omitted: body.length - kept.length };
}

/**
 * The provenance line written above a snapshot (ADR-572 D18).
 *
 * Italic prose, not an annotation — it carries no `data-*`, parses as ordinary
 * emphasis everywhere, and a member may edit or delete it like any sentence.
 * It exists because a snapshot's defect is SILENCE: rows that look live and
 * are not. Naming the source and the date makes the freeze a stated fact, and
 * tells the next reader where to look to refresh it.
 */
export function csvSourceNote(path: string, on: Date, omitted = 0): string {
  const stamp = `${on.getFullYear()}-${String(on.getMonth() + 1).padStart(2, '0')}-${String(on.getDate()).padStart(2, '0')}`;
  const more = omitted > 0 ? ` · first ${CSV_SNAPSHOT_ROW_CAP} rows, ${omitted} more in the source` : '';
  return `_From \`${path}\` · snapshot ${stamp}${more}_`;
}

/**
 * Insert a CSV's rows as a GFM table, under a source note (ADR-572 D18).
 *
 * The second two-step insert (the picker supplies the path, a read supplies
 * the content), and the shape is deliberately identical to `insertImage`'s so
 * the two doors behave the same way.
 */
export function insertCsvTable(
  text: string,
  start: number,
  end: number,
  path: string,
  csv: string,
  now: Date,
): Edit {
  const before = text.slice(0, start);
  const after = text.slice(end);
  const lead = before && !before.endsWith('\n\n') ? (before.endsWith('\n') ? '\n' : '\n\n') : '';
  const tail = after && !after.startsWith('\n') ? '\n' : '';
  const { table, omitted } = csvToMarkdownTable(csv);
  // An unreadable or empty CSV writes the note alone rather than a broken
  // grid — the member sees which file came back empty instead of a `| |`.
  const body = table
    ? `${csvSourceNote(path, now, omitted)}\n\n${table}`
    : `${csvSourceNote(path, now)}\n\n_(that file has no rows)_\n`;
  const snippet = lead + body + tail;
  const caret = before.length + snippet.length;
  return { text: before + snippet + after, selectionStart: caret, selectionEnd: caret };
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
