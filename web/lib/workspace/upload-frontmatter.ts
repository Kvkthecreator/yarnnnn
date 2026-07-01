/**
 * Upload-frontmatter parsing — the `---\n…\n---` YAML header that
 * `_build_upload_workspace_file()` (api/services/documents.py) prepends to an
 * uploaded document's extracted-text `.md`.
 *
 * 2026-07-01 (operator-observed KVK): the Files viewer rendered this header as
 * visible BODY TEXT at the top of the file ("original_filename: … mime_type: …
 * storage_path: …"), because the markdown viewer has no frontmatter stripping —
 * it only handles the `<!-- inference-meta -->` HTML-comment trailer, not the
 * `---`-delimited YAML that uploads write. This helper strips the header block
 * for rendering and surfaces the operator-meaningful fields (the original
 * filename + type) as a clean Source caption instead of a raw dump.
 *
 * This is a COSMETIC fix, orthogonal to ADR-395 (which retires frontmatter-in-
 * body entirely by landing the raw blob + a separate derived projection). It
 * lives until that refactor ships; it deliberately does not add a content-shape
 * registry entry (over-engineering for a transitional formatter).
 */

export interface UploadFrontmatter {
  /** The parsed key→value map from the YAML header (string values only). */
  fields: Record<string, string>;
  /** The document body with the leading `---…---` block removed. */
  body: string;
  /** True when a leading frontmatter block was found and stripped. */
  hasFrontmatter: boolean;
}

// Matches a leading `---\n<yaml>\n---\n` block at the very start of the content.
// [\s\S] so `.` spanning newlines isn't needed; non-greedy body; tolerant of
// a trailing blank line after the closing fence.
const LEADING_FRONTMATTER = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

/**
 * Split a `.md` string into its (flat, string-valued) frontmatter fields and
 * the remaining body. If there is no leading `---…---` block, returns the
 * content unchanged as `body` with an empty `fields` map.
 *
 * Intentionally a SHALLOW line parser (no nested YAML) — the upload header is a
 * flat `key: value` block by construction (documents.py). Values keep their raw
 * string form; no coercion.
 */
export function parseUploadFrontmatter(content: string): UploadFrontmatter {
  const match = content.match(LEADING_FRONTMATTER);
  if (!match) {
    return { fields: {}, body: content, hasFrontmatter: false };
  }

  const fields: Record<string, string> = {};
  for (const line of match[1].split(/\r?\n/)) {
    const idx = line.indexOf(':');
    if (idx <= 0) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim();
    if (key) fields[key] = value;
  }

  return {
    fields,
    body: content.slice(match[0].length),
    hasFrontmatter: true,
  };
}

/**
 * Build the operator-facing "Source" caption for an uploaded file from its
 * frontmatter fields — e.g. "배출증 출력.pdf · PDF". Returns null when there is
 * nothing meaningful to show (a non-upload `.md`, or a header with no known
 * fields). Machine plumbing (storage_path, size_bytes, extraction_method) is
 * deliberately NOT surfaced — it's provenance for the Get-Info modal, not the
 * reading view.
 */
export function uploadSourceCaption(fields: Record<string, string>): string | null {
  const original = fields.original_filename;
  if (!original) return null;

  // mime_type is written as `application/{file_type}` (e.g. application/pdf);
  // show the short, human form of the type.
  const mime = fields.mime_type || '';
  const short = mime.split('/').pop() || '';
  const type = short ? short.toUpperCase() : '';

  return type ? `${original} · ${type}` : original;
}
