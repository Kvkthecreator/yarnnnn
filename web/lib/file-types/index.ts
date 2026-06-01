/**
 * Type → Application Association — ADR-309 (the Applications register).
 *
 * This is the OS-native "which application opens this file type" layer —
 * macOS UTI + default-application binding; Unix MIME + xdg-open; the
 * thing ADR-222 named the "per-user customization layer" and marked
 * "Not yet built". ADR-309 makes it concrete.
 *
 * A userspace file has a *type* (derived from path + content-type). The
 * type binds to a viewer **application** — the renderer that opens it in a
 * window. Applications dispatch through this single table; they do NOT
 * each re-implement type detection. Files (the Finder application)
 * dispatches on open; Cockpit (Activity-Monitor) embeds the same viewers;
 * any future Application reads the same table.
 *
 * Distinct from `web/lib/content-shapes/` (ADR-245): content-shapes parse
 * the *content* of governance files for the **Settings register** (Mandate,
 * Autonomy, …). This module maps file *type* → *viewer application* for the
 * **Applications register** (reports, PDFs, images, data). Two registers,
 * two layers — see ADR-309.
 *
 * Kernel defaults only (ADR-309 §Open question 1): operator/agent override
 * of the default application per type is a named horizon, not built here.
 *
 * Singular Implementation: this lifts the `getFileKind` + kind-switch that
 * previously lived privately inside `ContentViewer.tsx` into the named,
 * shared association layer. ContentViewer now dispatches through it.
 */

/**
 * The viewer applications a file type can bind to. Each value names the
 * renderer an Application mounts for that type.
 *
 *   - `markdown`  — prose renderer (governance docs, narrative reports)
 *   - `html`      — composed-artifact iframe (compose-pipeline output.html)
 *   - `image`     — image viewer (generated charts, favicons, assets)
 *   - `pdf`       — PDF viewer (exported reports)
 *   - `csv`       — tabular data preview
 *   - `text`      — plain-text fallback (yaml, json, txt, unknown text)
 *   - `download`  — binary download affordance (xlsx, pptx — no inline view)
 */
export type ViewerApplication =
  | 'markdown'
  | 'html'
  | 'image'
  | 'pdf'
  | 'csv'
  | 'text'
  | 'download';

/**
 * Kernel-default type → application association. Order matters: the first
 * matching rule wins (path-extension checks before content-type fallbacks).
 *
 * This is the single authoritative table. A new file type gets a new rule
 * here, not a new branch inside a viewer component.
 */
export function resolveViewerApplication(
  path: string,
  contentType?: string,
): ViewerApplication {
  const p = path.toLowerCase();
  const t = (contentType || '').toLowerCase();

  if (p.endsWith('.md')) return 'markdown';
  if (p.endsWith('.html') || t.includes('text/html')) return 'html';
  if (
    p.endsWith('.png') ||
    p.endsWith('.jpg') ||
    p.endsWith('.jpeg') ||
    p.endsWith('.gif') ||
    p.endsWith('.webp') ||
    p.endsWith('.svg') ||
    t.startsWith('image/')
  ) {
    return 'image';
  }
  if (p.endsWith('.pdf') || t.includes('application/pdf')) return 'pdf';
  if (p.endsWith('.csv') || t.includes('text/csv')) return 'csv';
  if (
    p.endsWith('.xlsx') ||
    p.endsWith('.xls') ||
    p.endsWith('.pptx') ||
    p.endsWith('.ppt')
  ) {
    return 'download';
  }
  return 'text';
}

/** Operator-readable label for a viewer application (file-metadata strip). */
export function describeViewerApplication(
  path: string,
  contentType?: string,
): string {
  switch (resolveViewerApplication(path, contentType)) {
    case 'markdown':
      return 'Markdown';
    case 'html':
      return 'HTML report';
    case 'image':
      return 'Image';
    case 'pdf':
      return 'PDF';
    case 'csv':
      return 'CSV';
    case 'download':
      return 'Binary file';
    default:
      return 'Text';
  }
}
