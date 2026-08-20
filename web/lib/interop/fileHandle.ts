/**
 * fileHandle — the ADR-512 D5 handle grammar, browser side (ADR-587).
 *
 * `yarnnn://workspace/{workspace-relative-path}` is the canonical
 * cross-boundary name for a file. This module is the TypeScript twin of
 * `api/services/mcp_composition.py::parse_file_reference` /
 * `format_file_reference` — the SAME three spellings, the same refusals.
 *
 * Why a twin and not a fetch: a name is not a lookup. Resolving
 * `yarnnn://workspace/x.md` to `/workspace/x.md` is pure string grammar with
 * no workspace state in it, and the surfaces that need it (the Files arrival
 * door, quick-open) need it BEFORE any request is in flight. Round-tripping
 * to the server to learn how to spell a path would make every deep-link wait
 * on the network to discover it was well-formed.
 *
 * The asymmetry this closes (ADR-587 §1): before this file, `yarnnn://`
 * appeared in `web/` exactly twice, both EMITTING it. The app handed out a
 * name in a grammar it could not itself read back — the interop loop broken
 * on its return leg. Any surface that accepts a file name from outside
 * (paste, deep-link, drop) parses it HERE, so the accepted grammar cannot
 * drift per surface.
 *
 * Keep in lockstep with the Python. If the grammar gains a spelling (the
 * reserved `@{revision_id}` form, say), both halves move in one commit —
 * `api/test_adr587_handle_grammar_parity.py` asserts the pair agree.
 */

/** The canonical scheme prefix (ADR-512 D5). Lowercase; matching is case-insensitive. */
export const YARNNN_REF_SCHEME = 'yarnnn://workspace/';

/** The ledger's absolute root. Every stored path begins with this. */
export const WORKSPACE_PREFIX = '/workspace/';

/**
 * Normalize any honest spelling of a file's name to a workspace-relative path.
 *
 * Accepts (ADR-512 D5):
 *   · `yarnnn://workspace/marketing/gtm.md`  — the canonical handle
 *   · `/workspace/marketing/gtm.md`          — the ledger's absolute form
 *   · `marketing/gtm.md`                     — bare workspace-relative
 *
 * Returns the workspace-relative path (no leading slash), or `null` when the
 * reference is empty, carries another scheme, or escapes the workspace (`..`).
 *
 * A `null` return is a REFUSAL, not an error to swallow: the caller shows the
 * operator that the thing they pasted is not a file name, rather than
 * searching for it and reporting a confident miss.
 */
export function parseFileReference(reference: string | null | undefined): string | null {
  let ref = (reference ?? '').trim().replace(/^["']|["']$/g, '');
  if (!ref) return null;

  const lowered = ref.toLowerCase();
  if (lowered.startsWith(YARNNN_REF_SCHEME)) {
    ref = ref.slice(YARNNN_REF_SCHEME.length);
  } else if (ref.includes('://')) {
    // Some other scheme — an http(s) link, a file:// path. Not a yarnnn name.
    return null;
  } else if (ref.startsWith(WORKSPACE_PREFIX)) {
    ref = ref.slice(WORKSPACE_PREFIX.length);
  }

  ref = ref.replace(/^\/+/, '').trim();
  if (!ref) return null;
  // Refuse traversal: a name that climbs out of the workspace is not a name in it.
  if (ref.split('/').includes('..')) return null;
  return ref;
}

/**
 * The absolute ledger path for any honest spelling — what `workspace_files.path`
 * actually stores, and therefore what every read path wants.
 *
 * Returns `null` on the same refusals as `parseFileReference`.
 */
export function toWorkspacePath(reference: string | null | undefined): string | null {
  const rel = parseFileReference(reference);
  return rel === null ? null : `${WORKSPACE_PREFIX}${rel}`;
}

/**
 * The workspace-relative path — the form the operator reads and pastes back.
 *
 * Unlike `parseFileReference` this never refuses: it is for DISPLAYING a path
 * the workspace already gave us, where a refusal would blank the UI. Callers
 * holding untrusted input want `parseFileReference`.
 */
export function relPath(path: string): string {
  return path.startsWith(WORKSPACE_PREFIX) ? path.slice(WORKSPACE_PREFIX.length) : path;
}

/**
 * The canonical handle for a workspace path (ADR-512 D5) — the emit half.
 *
 * Mirrors `format_file_reference`: normalize if we can, else fall back to the
 * de-slashed input, so a display path always yields SOMETHING nameable.
 */
export function formatFileReference(path: string): string {
  const rel = parseFileReference(path) ?? (path || '').replace(/^\/+/, '');
  return `${YARNNN_REF_SCHEME}${rel}`;
}

/**
 * The handle wrapped in host guidance — what goes on the clipboard when the
 * destination is another AI's chat box.
 *
 * The handle is kernel grammar; this sentence is host guidance, and the two
 * are deliberately separable (ADR-512 D5). Built ONCE here because it shipped
 * hand-written in two apps that had already drifted apart: Studio said
 * "`trace` shows who changed it", Text said "`history` shows who changed it"
 * — and `history` is the verb that exists (ADR-543/545). A duplicated
 * sentence is a sentence that goes stale in one copy.
 */
export function formatAiReference(path: string, name: string): string {
  return (
    `"${name}" — ${formatFileReference(path)} ` +
    '(with the yarnnn connector, `open` this reference to read the exact ' +
    'current version; `history` shows who changed it and when).'
  );
}
