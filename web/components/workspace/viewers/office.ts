/**
 * Office renderers' library glue — ADR-395 am.2 D15, phase 2.
 *
 * The three office view kinds (`spreadsheet` / `wordprocessing` /
 * `presentation`) are DRAWN by components in `./index`; this module is the
 * only place that talks to a parser. Every parser is reached through a
 * DYNAMIC `import()` inside the function that needs it, so neither library
 * rides in the shell bundle — a member who never opens a workbook never
 * downloads SheetJS.
 *
 * Why these libraries (recorded in ADR-395 §11.10):
 *   - xlsx  → SheetJS CE 0.20.3, Apache-2.0, installed from the maintainers'
 *     own CDN tarball. The npm-registry `xlsx` is frozen at 0.18.5 and carries
 *     two published advisories (prototype pollution, ReDoS) fixed only in the
 *     CDN line. Chosen over exceljs (a Node-first library whose browser build
 *     drags stream polyfills) and read-excel-file (small, but it returns raw
 *     values — a `0.25` formatted as `25%` would read `0.25`): a viewer shows
 *     what the cell SAYS, which is the formatted text of the cached value.
 *   - docx  → docx-preview 0.4, Apache-2.0 (+ jszip). Page-faithful layout,
 *     tables, headers/footers. Chosen over mammoth, which emits semantic HTML
 *     by design and drops the page. Its output is untrusted markup, so it is
 *     never mounted into the app's DOM: it is serialised into a sandboxed
 *     iframe exactly as `WebViewer` isolates html (see `renderDocx`).
 *   - pptx  → NO parser. See `slidesFromProjection`.
 */

/** A drawn sheet — formatted cell text, already bounded. */
export interface SheetGrid {
  name: string;
  /** Row-major formatted cell text, at most `maxRows` × `maxCols`. */
  rows: string[][];
  /** Column letters for the drawn columns (A, B, … AA). */
  columns: string[];
  /** Spreadsheet row number of `rows[0]` (a sheet's range need not start at 1). */
  firstRow: number;
  totalRows: number;
  totalCols: number;
}

/**
 * Read a workbook's sheets as formatted text — CACHED VALUES, never formulas.
 *
 * `cellFormula: false` means a formula cell is read as the value Excel last
 * computed and stored beside it; nothing is recalculated here. `sheetRows`
 * bounds the parse itself, not only the render, so a 100k-row sheet costs a
 * bounded amount of work; `!fullref` still carries the real extent, which is
 * what lets the viewer say how much it left out.
 */
export async function readWorkbook(
  bytes: ArrayBuffer,
  maxRows: number,
  maxCols: number,
): Promise<SheetGrid[]> {
  const XLSX = await import('xlsx');
  const wb = XLSX.read(bytes, {
    type: 'array',
    sheetRows: maxRows,
    cellFormula: false,
    cellHTML: false,
    cellStyles: false,
  });
  return wb.SheetNames.map((name) => {
    const ws = wb.Sheets[name];
    const ref = ws?.['!ref'];
    if (!ws || !ref) {
      return { name, rows: [], columns: [], firstRow: 1, totalRows: 0, totalCols: 0 };
    }
    const full = XLSX.utils.decode_range(ws['!fullref'] || ref);
    const drawn = XLSX.utils.decode_range(ref);
    drawn.e.c = Math.min(drawn.e.c, drawn.s.c + maxCols - 1);
    const rows = XLSX.utils.sheet_to_json<string[]>(ws, {
      header: 1,
      raw: false,
      defval: '',
      blankrows: true,
      range: drawn,
    });
    const columns: string[] = [];
    for (let c = drawn.s.c; c <= drawn.e.c; c++) columns.push(XLSX.utils.encode_col(c));
    return {
      name,
      rows: rows.map((r) => r.map((cell) => String(cell ?? ''))),
      columns,
      firstRow: drawn.s.r + 1,
      totalRows: full.e.r - full.s.r + 1,
      totalCols: full.e.c - full.s.c + 1,
    };
  });
}

/**
 * Render a .docx to a self-contained HTML document for a sandboxed iframe.
 *
 * docx-preview builds DOM nodes, so it renders into DETACHED elements here and
 * the result is serialised — the untrusted markup never enters the app's own
 * document. The caller mounts it with `sandbox=""` (no script, opaque origin),
 * and the document carries its own CSP as a second wall: nothing inside may
 * fetch anything, because a .docx can LINK an external image, and a viewer
 * that fetched it would tell a third party the file was opened.
 *
 * Images are inlined as data: URLs (`useBase64URL`) — a blob: URL minted by the
 * app's origin is not reachable from the iframe's opaque one. Embedded fonts
 * are skipped for the same reason. altChunks (embedded foreign HTML/RTF) are
 * not rendered at all.
 */
export async function renderDocx(bytes: ArrayBuffer): Promise<string> {
  const { renderAsync } = await import('docx-preview');
  const body = document.createElement('div');
  const style = document.createElement('div');
  await renderAsync(bytes, body, style, {
    inWrapper: true,
    breakPages: true,
    ignoreFonts: true,
    useBase64URL: true,
    renderAltChunks: false,
    renderComments: false,
    renderChanges: false,
    experimental: false,
  });
  if (!body.textContent?.trim() && !body.querySelector('img')) {
    throw new Error('docx rendered empty');
  }
  const csp =
    "default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:";
  return (
    '<!doctype html><html><head><meta charset="utf-8">' +
    `<meta http-equiv="Content-Security-Policy" content="${csp}">` +
    '<style>html,body{margin:0}.docx-wrapper{padding:24px 0!important}</style>' +
    style.innerHTML +
    '</head><body>' +
    body.innerHTML +
    '</body></html>'
  );
}

/** One slide, as the projection spelled it. */
export interface SlideText {
  n: number;
  /** The slide's text blocks, in shape order (a table block is TSV). */
  blocks: string[];
  notes: string | null;
}

/**
 * The presentation view: the deck's OWN extracted words, laid out per slide.
 *
 * ⭐ No pptx parser is used, deliberately (ADR-395 §11.10). Client-side pptx
 * rendering is a positioned-shape layout engine (masters, layouts, theme
 * colours, autofit, charts, SmartArt); the libraries that attempt it are
 * single-maintainer, pull a charting library (~1 MB) and still draw most real
 * decks wrongly. A wrong picture of a slide is worse than its true words, so
 * this view reads the projection the server already wrote — one
 * `## Slide {n}` section per slide, speaker notes labelled — and draws each
 * slide as a card. Returns [] when the text carries no slide sections, which
 * the caller treats as "cannot draw" and falls back to the terminal.
 */
export function slidesFromProjection(text: string | null | undefined): SlideText[] {
  if (!text) return [];
  const slides: SlideText[] = [];
  const parts = text.split(/^## Slide (\d+)[ \t]*$/m);
  // parts = [preamble, n, body, n, body, …]
  for (let i = 1; i + 1 < parts.length; i += 2) {
    const blocks: string[] = [];
    let notes: string | null = null;
    for (const raw of parts[i + 1].split(/\n{2,}/)) {
      // Trim line breaks and spaces, never tabs: a TSV row may open with an
      // empty cell, and its leading tab is that cell.
      const block = raw.replace(/^[ \r\n]+|[ \r\n]+$/g, '');
      if (!block) continue;
      const m = /^Speaker notes:\s*([\s\S]*)$/.exec(block);
      if (m) {
        notes = m[1].trim();
        continue;
      }
      // The extractor writes a table shape one TSV row per line and joins
      // every line of a slide with a blank line — so a table arrives as a RUN
      // of tab-bearing blocks. Re-join the run into one block, which the
      // viewer draws as a table.
      const prev = blocks[blocks.length - 1];
      if (block.includes('\t') && prev !== undefined && prev.split('\n').every((l) => l.includes('\t'))) {
        blocks[blocks.length - 1] = `${prev}\n${block}`;
      } else {
        blocks.push(block);
      }
    }
    slides.push({ n: Number(parts[i]), blocks, notes });
  }
  return slides;
}
