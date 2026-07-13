/**
 * Type → Viewer Association — ADR-309 (the Applications register).
 *
 * This is the OS-native "which application opens this file type" layer —
 * macOS UTI + default-application binding; Unix MIME + xdg-open; the
 * thing ADR-222 named the "per-user customization layer" and marked
 * "Not yet built". ADR-309 makes it concrete.
 *
 * A userspace file has a *type* (derived from path + content-type). The
 * type binds to a viewer — the renderer that opens it. Every mount
 * dispatches through this single table; no mount re-implements type
 * detection. The Files surface (the Finder), the Recents view, the
 * Context surface, and the chat surface's artifact card all resolve here.
 *
 * ── THE THREE TIERS (the conformance fallback; ADR-245's L3/L2/L1) ─────
 *
 *   tier 1  path-exact  → a bespoke renderer for one known path. Today
 *                         this is the IDENTITY inference view, resolved by
 *                         `inferenceTarget()` inside `FileBody`, NOT here.
 *                         Named seam: when a path→component table becomes
 *                         warranted it belongs ABOVE this function, never
 *                         inside it. (`content-shapes/shapeForPath` is the
 *                         parser-side half of that tier and currently has
 *                         no consumer.)
 *   tier 2  type-exact  → this function's specific branches.
 *   tier 3  terminal    → `text` (the L1 raw view) for anything text-shaped,
 *                         `download` for anything else.
 *
 * The terminal is the escape hatch that makes an open type system safe: an
 * unknown type ALWAYS resolves to something. What it must never do is
 * resolve a 25 MB `.mp4` to `text` and paint the bytes — which is exactly
 * what the pre-2026-07-09 flat switch did (no video node, and `download`
 * was a hardcoded four-extension allowlist rather than a real terminal).
 *
 * ── THE TYPE IS DERIVED, NEVER TRUSTED (ADR-427 D5) ───────────────────
 *
 * `contentType` is a caller-supplied hint (`services/workspace.py:33`
 * defaults it to `text/markdown`). The path extension is the stronger
 * signal and is checked first. When ADR-427 D5 lands magic-byte sniffing
 * server-side, `contentType` becomes derived and this ordering can relax.
 * Until then: extension wins, MIME informs, and the terminal is COMPUTED
 * from text-ness rather than enumerated.
 *
 * Distinct from `web/lib/content-shapes/` (ADR-245 L2 parsers), which read
 * the *content* of specific governance files. That module answers "what
 * does this file mean"; this one answers "what opens it".
 */

/**
 * The viewers a file type can bind to. Each value names the renderer that
 * `FileBody` mounts for that type.
 *
 *   - `markdown`  — prose renderer (governance docs, narrative reports)
 *   - `html`      — composed-artifact iframe (compose-pipeline output.html)
 *   - `image`     — image viewer (charts, favicons, generated assets)
 *   - `video`     — <video> player (ADR-420 lane-generated media)
 *   - `audio`     — <audio> player
 *   - `pdf`       — PDF viewer (exported reports)
 *   - `csv`       — tabular data preview
 *   - `text`      — plain-text raw view (yaml, json, txt, unknown text)
 *   - `download`  — the BINARY TERMINAL: no inline view; offer the bytes
 */
export type ViewerApplication =
  | 'markdown'
  | 'html'
  | 'image'
  | 'video'
  | 'audio'
  | 'pdf'
  | 'csv'
  | 'text'
  | 'download';

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.avif', '.bmp', '.ico'] as const;
const VIDEO_EXTENSIONS = ['.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'] as const;
const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'] as const;

/** Extensions whose bytes are not text, absent a content-type that says so. */
const BINARY_EXTENSIONS = [
  // office + archives
  '.xlsx', '.xls', '.pptx', '.ppt', '.docx', '.doc',
  '.zip', '.gz', '.tar', '.tgz', '.7z', '.rar',
  // fonts + binaries
  '.woff', '.woff2', '.ttf', '.otf', '.eot',
  '.wasm', '.so', '.dylib', '.dll', '.exe', '.bin',
  // design sources
  '.psd', '.ai', '.sketch', '.fig',
  // data
  '.parquet', '.db', '.sqlite',
] as const;

const endsWithAny = (p: string, exts: readonly string[]) => exts.some((e) => p.endsWith(e));

/**
 * Is this content-type text-shaped? `text/*` plus the structured-text
 * application types every text editor opens (including the `+json` /
 * `+xml` / `+yaml` structured-suffix convention, RFC 6839).
 */
function isTextualContentType(t: string): boolean {
  if (!t) return false;
  if (t.startsWith('text/')) return true;
  if (/^application\/(json|yaml|x-yaml|xml|javascript|ecmascript|toml|x-sh|x-ndjson)\b/.test(t)) return true;
  if (/\+(json|xml|yaml)\b/.test(t)) return true;
  return false;
}

/**
 * Kernel-default type → viewer association. The first matching rule wins.
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

  // ── tier 2: type-exact ──────────────────────────────────────────────
  if (p.endsWith('.md') || p.endsWith('.markdown')) return 'markdown';
  if (p.endsWith('.html') || p.endsWith('.htm') || t.includes('text/html')) return 'html';
  if (endsWithAny(p, IMAGE_EXTENSIONS) || t.startsWith('image/')) return 'image';
  if (endsWithAny(p, VIDEO_EXTENSIONS) || t.startsWith('video/')) return 'video';
  if (endsWithAny(p, AUDIO_EXTENSIONS) || t.startsWith('audio/')) return 'audio';
  if (p.endsWith('.pdf') || t.includes('application/pdf')) return 'pdf';
  if (p.endsWith('.csv') || p.endsWith('.tsv') || t.includes('text/csv')) return 'csv';

  // ── tier 3: the terminal, DERIVED from text-ness (never enumerated) ──
  //
  // A known-binary extension, or a content-type that is PRESENT and NOT
  // textual, terminates at `download`. Everything else is the L1 raw view,
  // which stays correct for `.yaml` / `.json` / `.log` / extension-less.
  if (endsWithAny(p, BINARY_EXTENSIONS)) return 'download';
  if (t && !isTextualContentType(t)) return 'download';
  return 'text';
}

/**
 * ADR-451 — the surface-owning app layer, ABOVE the viewer table.
 *
 * A row here claims a format for an app that owns a whole SURFACE: opening
 * such a file from the Finder (the Files surface) routes to the app —
 * `navigateToSurface(surface, {[param]: path})` — instead of rendering it
 * flat in the inline viewer (which remains the Quick Look analog for
 * everything unclaimed). One row in v1: the Studio owns its artifact format.
 *
 * The "Open with" picker stays deferred until a second installed app claims
 * the same format (ADR-436 — the resolver-is-an-ordered-list stance).
 */
export interface SurfaceApplication {
  /** The surface slug the app owns (navigateToSurface target). */
  surface: string;
  /** The window-namespaced param carrying the file path. */
  param: string;
  /** Operator-readable app name ("Opens in Studio"). */
  label: string;
}

export function resolveSurfaceApplication(
  path: string,
  contentType?: string,
): SurfaceApplication | null {
  const p = path.toLowerCase();
  const t = (contentType || '').toLowerCase();
  // Studio claims html artifacts — EXCEPT arrivals (inbound/): a retained
  // observation is a record to preview, not an authoring canvas (ADR-451 D1).
  const isHtml = p.endsWith('.html') || p.endsWith('.htm') || t.includes('text/html');
  const isArrival = p.includes('/inbound/') || p.startsWith('inbound/');
  if (isHtml && !isArrival) {
    return { surface: 'studio', param: 'file', label: 'Studio' };
  }
  return null;
}

/**
 * Does this viewer read the blob (`content_url`) rather than the `content`
 * text column? Mirrors the ADR-427 §8 read-side split: a binary revision's
 * text column is empty by construction.
 */
export function viewerNeedsBlob(kind: ViewerApplication): boolean {
  return kind === 'video' || kind === 'audio' || kind === 'pdf' || kind === 'download';
}

/** Operator-readable label for a viewer (the file-metadata strip). */
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
    case 'video':
      return 'Video';
    case 'audio':
      return 'Audio';
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
